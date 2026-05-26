"""Anchor geometry fingerprint extraction and comparison.

The `anchor_geometry_match` gate is the central mechanism enforcing that a
template's geometry inherits structurally from a single nominated 5-star
record (the PRIMARY_ANCHOR). It compares two GeometryFingerprints:

- The anchor's, computed once from the 5-star record's `model.py`.
- The template's, computed at `seed=0` from `build_<stem>(config_from_seed(0))`.

The fingerprint deliberately captures only the structural skeleton of a
model — part names (with `_i` suffix normalization for indexed families),
joint topology, per-part visual counts, per-part primitive-type histograms,
overall bbox aspect ratio. It does not look at source code, exact
coordinates, or literal parameter values. That way an agent can legitimately
parameterize an anchor (replace literals with `config.*`, expand a
hard-coded 3-blade loop into N blades) without breaking the gate, but
cannot:

- Replace anchor's `LatheGeometry` / `mesh_from_geometry` with a crude
  `Box`/`Cylinder` (caught by primitive_complexity_lower_bound).
- Split anchor's decorative `parent.visual(...)` into separate parts
  joined by FIXED joints (caught by visual_count + joint_topology).
- Introduce parts the anchor doesn't have, or drop required joints
  (caught by part_name_set / joint_topology).
- Generate a geometry with a fundamentally different overall shape
  (caught by bbox_ratio).
"""

from __future__ import annotations

import importlib
import math
import re
import runpy
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Pre-compiled regexes for normalising indexed names.
# blade_0, blade_12 → blade_i
# fan_head_0_collar_0 → fan_head_i_collar_i (greedy, multi-suffix)
_INDEX_SUFFIX_RE = re.compile(r"_\d+(?=_|$)")


def normalize_indexed_name(name: str | None) -> str:
    """Strip trailing/embedded `_<digit+>` and replace with `_i`.

    Examples:
        blade_0     -> blade_i
        blade_12    -> blade_i
        fan_head_0_collar_0 -> fan_head_i_collar_i
        housing     -> housing
    """
    if not name:
        return ""
    return _INDEX_SUFFIX_RE.sub("_i", str(name))


def _axis_to_principal(axis: Any) -> str:
    """Convert a (x, y, z) axis vector to its principal-axis label or 'none'."""
    if axis is None:
        return "none"
    try:
        components = (float(axis[0]), float(axis[1]), float(axis[2]))
    except (TypeError, IndexError, ValueError):
        return "none"
    magnitudes = [(abs(c), label) for c, label in zip(components, ("x", "y", "z"))]
    magnitudes.sort(reverse=True)
    if magnitudes[0][0] < 1e-6:
        return "none"
    return magnitudes[0][1]


def _geometry_type_label(geometry: Any) -> str:
    """Return the geometry-class name as a string tag ('Box', 'Cylinder', 'Sphere', 'Mesh')."""
    return type(geometry).__name__


@dataclass(slots=True)
class PartFingerprint:
    name: str  # normalized
    visual_count: int
    primitives: dict[str, int] = field(default_factory=dict)
    # AABB extent (x_size, y_size, z_size) of all visuals in this part's local frame.
    # None when the part has no measurable visuals (e.g., only meshes whose AABB
    # we don't load).
    local_aabb_extent: tuple[float, float, float] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "visual_count": self.visual_count,
            "primitives": dict(self.primitives),
            "local_aabb_extent": (
                list(self.local_aabb_extent) if self.local_aabb_extent is not None else None
            ),
        }


@dataclass(slots=True)
class JointFingerprint:
    parent: str  # normalized
    child: str  # normalized
    type: str  # 'FIXED' / 'REVOLUTE' / 'CONTINUOUS' / 'PRISMATIC' / 'FLOATING'
    axis: str  # 'x' / 'y' / 'z' / 'none'

    def to_dict(self) -> dict[str, Any]:
        return {"parent": self.parent, "child": self.child, "type": self.type, "axis": self.axis}

    def as_topology_triple(self) -> tuple[str, str, str]:
        return (self.parent, self.child, self.type)


@dataclass(slots=True)
class GeometryFingerprint:
    """Structured fingerprint of an ArticulatedObject."""

    source: str  # e.g., 'anchor:rec_xxx:rev_yyy' or 'template:dj_equipment:seed_0'
    part_count: int
    parts: dict[str, PartFingerprint]  # normalized name -> stats
    joints: list[JointFingerprint]
    bbox_ratio: tuple[float, float, float] | None  # normalized so max(component)=1

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "part_count": self.part_count,
            "parts": {name: p.to_dict() for name, p in self.parts.items()},
            "joints": [j.to_dict() for j in self.joints],
            "bbox_ratio": list(self.bbox_ratio) if self.bbox_ratio is not None else None,
        }


# --------------------------------------------------------------------------- #
# Geometry AABB helpers (local-frame, primitive-only)
# --------------------------------------------------------------------------- #


def _primitive_local_aabb(geometry: Any, origin: Any) -> tuple[float, float, float] | None:
    """Approximate the AABB extent (xs, ys, zs) of a primitive visual in part-local frame.

    Returns None for meshes (would require loading the asset; we deliberately
    skip that to keep fingerprint extraction cheap and side-effect-free).
    """
    gname = _geometry_type_label(geometry)
    if gname == "Box":
        size = getattr(geometry, "size", None)
        if size is None or len(size) != 3:
            return None
        return (abs(float(size[0])), abs(float(size[1])), abs(float(size[2])))
    if gname == "Cylinder":
        radius = float(getattr(geometry, "radius", 0.0))
        length = float(getattr(geometry, "length", 0.0))
        # cylinder axis is along z by SDK convention.
        return (2.0 * radius, 2.0 * radius, length)
    if gname == "Sphere":
        radius = float(getattr(geometry, "radius", 0.0))
        return (2.0 * radius, 2.0 * radius, 2.0 * radius)
    return None  # Mesh / unknown


def _union_aabb(
    accum: tuple[float, float, float] | None,
    visual_extent: tuple[float, float, float],
    visual_origin: Any,
) -> tuple[float, float, float]:
    """Loose union of two AABB extents around the part-local origin.

    Each visual contributes |origin.xyz| + half_extent. We sum half-extents
    centered on the origin to approximate the overall part bbox. This is a
    rough proxy — it overestimates when visuals straddle the origin — but
    it's deterministic and sufficient for fingerprint comparison.
    """
    half = tuple(0.5 * v for v in visual_extent)
    try:
        ox, oy, oz = (
            float(visual_origin.xyz[0]),
            float(visual_origin.xyz[1]),
            float(visual_origin.xyz[2]),
        )
    except (AttributeError, TypeError, IndexError, ValueError):
        ox = oy = oz = 0.0
    extents = (
        abs(ox) + half[0],
        abs(oy) + half[1],
        abs(oz) + half[2],
    )
    if accum is None:
        return (extents[0] * 2, extents[1] * 2, extents[2] * 2)
    return (
        max(accum[0], extents[0] * 2),
        max(accum[1], extents[1] * 2),
        max(accum[2], extents[2] * 2),
    )


def _bbox_ratio(extents: tuple[float, float, float]) -> tuple[float, float, float] | None:
    """Normalize an (x, y, z) extent so max component = 1."""
    longest = max(extents)
    if longest <= 1e-9:
        return None
    return tuple(v / longest for v in extents)  # type: ignore[return-value]


# --------------------------------------------------------------------------- #
# Fingerprint extraction
# --------------------------------------------------------------------------- #


def extract_fingerprint_from_model(model: Any, *, source: str) -> GeometryFingerprint:
    """Extract a GeometryFingerprint from a live ArticulatedObject instance.

    Indexed-family parts (e.g., blade_0, blade_1, blade_2) collapse to a
    single entry under their normalized name (blade_i) with the FIRST seen
    member's stats. Well-formed indexed families have identical visual
    structure across members, so this loses nothing meaningful; if members
    happen to differ, the first one anchors the fingerprint.
    """
    parts_dict: dict[str, PartFingerprint] = {}
    overall_aabb: tuple[float, float, float] | None = None
    for part in getattr(model, "parts", []):
        raw_name = getattr(part, "name", "") or ""
        norm_name = normalize_indexed_name(raw_name)
        if norm_name in parts_dict:
            continue
        primitives: dict[str, int] = {}
        part_local_aabb: tuple[float, float, float] | None = None
        for visual in getattr(part, "visuals", []) or []:
            geom = getattr(visual, "geometry", None)
            if geom is None:
                continue
            gname = _geometry_type_label(geom)
            primitives[gname] = primitives.get(gname, 0) + 1
            extent = _primitive_local_aabb(geom, getattr(visual, "origin", None))
            if extent is not None:
                part_local_aabb = _union_aabb(
                    part_local_aabb, extent, getattr(visual, "origin", None)
                )
        parts_dict[norm_name] = PartFingerprint(
            name=norm_name,
            visual_count=sum(primitives.values()),
            primitives=primitives,
            local_aabb_extent=part_local_aabb,
        )
        if part_local_aabb is not None:
            if overall_aabb is None:
                overall_aabb = part_local_aabb
            else:
                overall_aabb = (
                    max(overall_aabb[0], part_local_aabb[0]),
                    max(overall_aabb[1], part_local_aabb[1]),
                    max(overall_aabb[2], part_local_aabb[2]),
                )

    joints: list[JointFingerprint] = []
    for art in getattr(model, "articulations", []) or []:
        parent = normalize_indexed_name(getattr(art, "parent", "") or "")
        child = normalize_indexed_name(getattr(art, "child", "") or "")
        atype_obj = getattr(art, "articulation_type", None)
        atype = (
            atype_obj.name.upper()
            if hasattr(atype_obj, "name")
            else str(atype_obj).upper().lstrip("ARTICULATIONTYPE.").rstrip("'>")
        )
        axis = _axis_to_principal(getattr(art, "axis", None))
        joints.append(JointFingerprint(parent=parent, child=child, type=atype, axis=axis))

    bbox_ratio = _bbox_ratio(overall_aabb) if overall_aabb is not None else None
    return GeometryFingerprint(
        source=source,
        part_count=len(parts_dict),
        parts=parts_dict,
        joints=joints,
        bbox_ratio=bbox_ratio,
    )


def _resolve_anchor_record_path(record_id: str, rev_id: str, *, repo_root: Path) -> Path:
    return repo_root / "data" / "records" / record_id / "revisions" / rev_id / "model.py"


def parse_anchor_reference(anchor_ref: str) -> tuple[str, str]:
    """Parse 'rec_xxx:rev_yyy' into (record_id, rev_id). rev defaults to rev_000001."""
    s = (anchor_ref or "").strip()
    if not s:
        raise ValueError("anchor reference is empty")
    if ":" in s:
        rec, rev = s.split(":", 1)
        return rec.strip(), rev.strip()
    return s, "rev_000001"


def extract_fingerprint_from_anchor(
    anchor_ref: str,
    *,
    repo_root: Path | None = None,
) -> GeometryFingerprint:
    """Run an anchor record's model.py and extract its fingerprint."""
    repo_root = repo_root or Path(__file__).resolve().parents[1]
    record_id, rev_id = parse_anchor_reference(anchor_ref)
    model_py = _resolve_anchor_record_path(record_id, rev_id, repo_root=repo_root)
    if not model_py.exists():
        raise FileNotFoundError(f"anchor model.py not found at {model_py} (anchor={anchor_ref!r})")
    # Use runpy so the record's model.py executes with its asset_root relative paths.
    repo_root_str = str(repo_root)
    sys_path_added = False
    if repo_root_str not in sys.path:
        sys.path.insert(0, repo_root_str)
        sys_path_added = True
    try:
        globals_dict = runpy.run_path(str(model_py))
    finally:
        if sys_path_added and sys.path[0] == repo_root_str:
            sys.path.pop(0)
    model = globals_dict.get("object_model")
    if model is None:
        raise ValueError(
            f"anchor model.py did not define top-level `object_model` (anchor={anchor_ref!r})"
        )
    return extract_fingerprint_from_model(model, source=f"anchor:{record_id}:{rev_id}")


def extract_fingerprint_from_template(
    slug: str,
    *,
    seed: int = 0,
    sdk_package: str = "sdk",
) -> GeometryFingerprint:
    """Build the template at the given seed and extract its fingerprint.

    Mirrors the runtime path that `compile-sweep` uses for compilation but
    stops after `build_<stem>(...)` returns the ArticulatedObject — no
    URDF export or QC needed for fingerprinting.
    """
    module = importlib.import_module(f"agent.templates.{slug}")
    config_from_seed = getattr(module, "config_from_seed", None)
    if not callable(config_from_seed):
        raise AttributeError(f"agent.templates.{slug} missing callable config_from_seed")
    config = config_from_seed(seed)
    stem = _infer_stem_from_module(module, slug)
    builder = getattr(module, f"build_{stem}", None)
    if not callable(builder):
        raise AttributeError(f"agent.templates.{slug} missing callable build_{stem}")
    # AssetContext: provide a no-op so build_* doesn't write files for fingerprinting.
    from sdk import AssetContext

    repo_root = Path(__file__).resolve().parents[1]
    assets = AssetContext.from_script(repo_root / "agent" / "templates" / f"{slug}.py")
    model = builder(config, assets=assets)
    return extract_fingerprint_from_model(model, source=f"template:{slug}:seed_{seed}")


def _infer_stem_from_module(module: Any, slug: str) -> str:
    """Find the function stem by looking for the `build_<stem>` and `run_<stem>_tests`
    functions exported by the template module."""
    candidates: list[str] = []
    for attr_name in dir(module):
        if not attr_name.startswith("build_"):
            continue
        rest = attr_name[len("build_") :]
        if not rest:
            continue
        if hasattr(module, f"run_{rest}_tests"):
            candidates.append(rest)
    if not candidates:
        raise AttributeError(
            f"agent.templates.{slug} exports no `build_<stem>` paired with `run_<stem>_tests`"
        )
    # Heuristic: longest match (most specific) wins.
    candidates.sort(key=len, reverse=True)
    return candidates[0]


# --------------------------------------------------------------------------- #
# Fingerprint comparison (the 5 sub-checks)
# --------------------------------------------------------------------------- #

DEFAULT_VISUAL_COUNT_RATIO = 0.5
DEFAULT_BBOX_RATIO_MAX_DEV = 0.30
DEFAULT_PRIMITIVE_HISTOGRAM_COSINE_MIN = 0.7
DEFAULT_MAX_EXTRA_PARTS = 0  # how many parts can appear in template that anchor doesn't have


@dataclass(slots=True)
class SubcheckResult:
    name: str
    status: str  # 'pass' | 'fail'
    details: dict[str, Any] = field(default_factory=dict)
    deviations: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "details": self.details,
            "deviations": self.deviations,
        }


@dataclass(slots=True)
class AnchorMatchReport:
    overall_status: str
    anchor_source: str
    template_source: str
    subchecks: list[SubcheckResult]

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall_status": self.overall_status,
            "anchor_source": self.anchor_source,
            "template_source": self.template_source,
            "subchecks": [sc.to_dict() for sc in self.subchecks],
        }


def _check_part_name_set(
    anchor: GeometryFingerprint,
    template: GeometryFingerprint,
    *,
    max_extra: int = DEFAULT_MAX_EXTRA_PARTS,
) -> SubcheckResult:
    anchor_names = set(anchor.parts.keys())
    template_names = set(template.parts.keys())
    extra = sorted(template_names - anchor_names)
    missing = sorted(anchor_names - template_names)
    deviations: list[dict[str, Any]] = []
    if len(extra) > max_extra:
        deviations.append(
            {
                "kind": "extra_parts",
                "names": extra,
                "reason": (
                    f"Template introduces {len(extra)} part(s) the anchor does not have: "
                    f"{extra}. Likely cause: agent split decorative visuals into separate "
                    "parts (the dj_knob anti-pattern). Refactor to attach decorations as "
                    "`parent.visual(...)` instead of new parts joined by FIXED articulations."
                ),
            }
        )
    if missing:
        deviations.append(
            {
                "kind": "missing_parts",
                "names": missing,
                "reason": (
                    f"Template is missing {len(missing)} part(s) the anchor has: {missing}. "
                    "Either implement them, or — if intentional (e.g., this slug is a "
                    "narrow variant) — discuss splitting/narrowing in the spec."
                ),
            }
        )
    status = "pass" if not deviations else "fail"
    return SubcheckResult(
        name="part_name_set",
        status=status,
        details={
            "anchor_parts": sorted(anchor_names),
            "template_parts": sorted(template_names),
            "max_extra_allowed": max_extra,
        },
        deviations=deviations,
    )


def _check_joint_topology(
    anchor: GeometryFingerprint, template: GeometryFingerprint
) -> SubcheckResult:
    anchor_triples = {j.as_topology_triple() for j in anchor.joints}
    template_triples = {j.as_topology_triple() for j in template.joints}
    extra = [list(t) for t in sorted(template_triples - anchor_triples)]
    missing = [list(t) for t in sorted(anchor_triples - template_triples)]
    deviations: list[dict[str, Any]] = []
    if extra:
        deviations.append(
            {
                "kind": "extra_joints",
                "joints": extra,
                "reason": (
                    f"Template introduces {len(extra)} joint topolog(ies) the anchor "
                    f"does not have. Common cause: agent attached a decorative cylinder "
                    "as a separate part via FIXED joint instead of `parent.visual(...)`."
                ),
            }
        )
    if missing:
        deviations.append(
            {
                "kind": "missing_joints",
                "joints": missing,
                "reason": (
                    f"Template is missing {len(missing)} joint topolog(ies) the anchor "
                    "has. Add the joint or — for an enum branch that legitimately omits "
                    "this joint — document in the spec."
                ),
            }
        )
    return SubcheckResult(
        name="joint_topology",
        status="pass" if not deviations else "fail",
        details={
            "anchor_joints": [list(t) for t in sorted(anchor_triples)],
            "template_joints": [list(t) for t in sorted(template_triples)],
        },
        deviations=deviations,
    )


def _check_visual_count_per_part(
    anchor: GeometryFingerprint,
    template: GeometryFingerprint,
    *,
    min_ratio: float = DEFAULT_VISUAL_COUNT_RATIO,
) -> SubcheckResult:
    deviations: list[dict[str, Any]] = []
    detail_pairs: dict[str, dict[str, Any]] = {}
    for name, anchor_part in anchor.parts.items():
        template_part = template.parts.get(name)
        anchor_count = anchor_part.visual_count
        template_count = 0 if template_part is None else template_part.visual_count
        ratio = (template_count / anchor_count) if anchor_count > 0 else 1.0
        detail_pairs[name] = {
            "anchor": anchor_count,
            "template": template_count,
            "ratio": round(ratio, 3),
        }
        if anchor_count > 0 and ratio < min_ratio:
            deviations.append(
                {
                    "part": name,
                    "anchor_count": anchor_count,
                    "template_count": template_count,
                    "ratio": round(ratio, 3),
                    "min_ratio": min_ratio,
                    "reason": (
                        f"Part '{name}' has {template_count} visual(s) in the template "
                        f"but {anchor_count} in the anchor (ratio {ratio:.2f} < {min_ratio:.2f}). "
                        "Likely cause: agent collapsed multiple decorative visuals into "
                        "a single primitive (e.g., 5 cylinders → 1 box). Adopt anchor's "
                        "decorative visuals as additional `parent.visual(...)` entries."
                    ),
                }
            )
    return SubcheckResult(
        name="visual_count_per_part",
        status="pass" if not deviations else "fail",
        details={"per_part": detail_pairs, "min_ratio": min_ratio},
        deviations=deviations,
    )


def _check_primitive_complexity_lower_bound(
    anchor: GeometryFingerprint, template: GeometryFingerprint
) -> SubcheckResult:
    """For each anchor part with Mesh visuals, template's matching part must have
    at least the same number of Mesh visuals. Catches the case where agent
    replaces LatheGeometry / mesh_from_geometry / custom_polygon meshes with
    crude Box/Cylinder placeholders."""
    deviations: list[dict[str, Any]] = []
    detail_pairs: dict[str, dict[str, Any]] = {}
    for name, anchor_part in anchor.parts.items():
        anchor_mesh = anchor_part.primitives.get("Mesh", 0)
        if anchor_mesh == 0:
            continue
        template_part = template.parts.get(name)
        template_mesh = template_part.primitives.get("Mesh", 0) if template_part is not None else 0
        detail_pairs[name] = {
            "anchor_mesh_count": anchor_mesh,
            "template_mesh_count": template_mesh,
        }
        if template_mesh < anchor_mesh:
            deviations.append(
                {
                    "part": name,
                    "anchor_mesh_count": anchor_mesh,
                    "template_mesh_count": template_mesh,
                    "template_primitives": (
                        dict(template_part.primitives) if template_part else {}
                    ),
                    "reason": (
                        f"Anchor's '{name}' uses {anchor_mesh} Mesh visual(s) "
                        "(LatheGeometry / mesh_from_geometry / cadquery output) for "
                        f"sophisticated geometry; template's '{name}' has only "
                        f"{template_mesh} Mesh visual(s). DO NOT downgrade sophisticated "
                        "primitives to Box/Cylinder placeholders. Adopt the anchor's "
                        "helper code with parameter substitution, or re-implement the "
                        "LatheGeometry profile in the template."
                    ),
                }
            )
    return SubcheckResult(
        name="primitive_complexity_lower_bound",
        status="pass" if not deviations else "fail",
        details={"per_part": detail_pairs},
        deviations=deviations,
    )


def _cosine_similarity(a: dict[str, int], b: dict[str, int]) -> float:
    keys = set(a.keys()) | set(b.keys())
    if not keys:
        return 1.0
    dot = sum(a.get(k, 0) * b.get(k, 0) for k in keys)
    mag_a = math.sqrt(sum(a.get(k, 0) ** 2 for k in keys))
    mag_b = math.sqrt(sum(b.get(k, 0) ** 2 for k in keys))
    if mag_a == 0 or mag_b == 0:
        return 1.0 if mag_a == mag_b else 0.0
    return dot / (mag_a * mag_b)


def _check_primitive_histogram_similarity(
    anchor: GeometryFingerprint,
    template: GeometryFingerprint,
    *,
    cosine_min: float = DEFAULT_PRIMITIVE_HISTOGRAM_COSINE_MIN,
) -> SubcheckResult:
    deviations: list[dict[str, Any]] = []
    detail_pairs: dict[str, dict[str, Any]] = {}
    for name, anchor_part in anchor.parts.items():
        template_part = template.parts.get(name)
        template_primitives = dict(template_part.primitives) if template_part else {}
        sim = _cosine_similarity(anchor_part.primitives, template_primitives)
        detail_pairs[name] = {
            "anchor": dict(anchor_part.primitives),
            "template": template_primitives,
            "cosine_similarity": round(sim, 3),
        }
        if sim < cosine_min:
            deviations.append(
                {
                    "part": name,
                    "anchor_primitives": dict(anchor_part.primitives),
                    "template_primitives": template_primitives,
                    "cosine_similarity": round(sim, 3),
                    "cosine_min": cosine_min,
                    "reason": (
                        f"Part '{name}' primitive-type distribution differs from the "
                        f"anchor (cos {sim:.2f} < {cosine_min:.2f}). Common cause: agent "
                        "swapped primitives (Cylinder → Box, etc.). Adopt the anchor's "
                        "primitive choices."
                    ),
                }
            )
    return SubcheckResult(
        name="primitive_histogram_similarity",
        status="pass" if not deviations else "fail",
        details={"per_part": detail_pairs, "cosine_min": cosine_min},
        deviations=deviations,
    )


def _check_bbox_ratio(
    anchor: GeometryFingerprint,
    template: GeometryFingerprint,
    *,
    max_deviation: float = DEFAULT_BBOX_RATIO_MAX_DEV,
) -> SubcheckResult:
    if anchor.bbox_ratio is None or template.bbox_ratio is None:
        return SubcheckResult(
            name="bbox_ratio",
            status="pass",
            details={
                "anchor_bbox_ratio": list(anchor.bbox_ratio) if anchor.bbox_ratio else None,
                "template_bbox_ratio": (list(template.bbox_ratio) if template.bbox_ratio else None),
                "skipped_reason": "one or both bbox_ratios unavailable (mesh-only model)",
            },
        )
    deviations_per_axis: list[dict[str, Any]] = []
    max_dev = 0.0
    for axis, (a_val, t_val) in zip("xyz", zip(anchor.bbox_ratio, template.bbox_ratio)):
        # Symmetric relative deviation.
        denom = max(abs(a_val), abs(t_val), 1e-9)
        dev = abs(a_val - t_val) / denom
        max_dev = max(max_dev, dev)
        if dev > max_deviation:
            deviations_per_axis.append(
                {
                    "axis": axis,
                    "anchor": a_val,
                    "template": t_val,
                    "deviation": round(dev, 3),
                    "max_deviation": max_deviation,
                }
            )
    deviations: list[dict[str, Any]] = []
    if deviations_per_axis:
        deviations.append(
            {
                "kind": "bbox_ratio_mismatch",
                "per_axis": deviations_per_axis,
                "max_observed": round(max_dev, 3),
                "max_allowed": max_deviation,
                "reason": (
                    "Overall bbox aspect ratio diverges from anchor by more than "
                    f"{max_deviation:.0%} on at least one axis. The template likely "
                    "produces a geometry of a fundamentally different overall shape "
                    "(e.g., anchor is a flat fan but template is an elongated stick)."
                ),
            }
        )
    return SubcheckResult(
        name="bbox_ratio",
        status="pass" if not deviations else "fail",
        details={
            "anchor_bbox_ratio": list(anchor.bbox_ratio),
            "template_bbox_ratio": list(template.bbox_ratio),
            "max_observed_dev": round(max_dev, 3),
            "max_allowed_dev": max_deviation,
        },
        deviations=deviations,
    )


def compare_fingerprints(
    anchor: GeometryFingerprint,
    template: GeometryFingerprint,
    *,
    visual_count_min_ratio: float = DEFAULT_VISUAL_COUNT_RATIO,
    primitive_histogram_cosine_min: float = DEFAULT_PRIMITIVE_HISTOGRAM_COSINE_MIN,
    bbox_ratio_max_dev: float = DEFAULT_BBOX_RATIO_MAX_DEV,
    max_extra_parts: int = DEFAULT_MAX_EXTRA_PARTS,
) -> AnchorMatchReport:
    """Run all 5 subchecks and aggregate into one AnchorMatchReport."""
    subchecks = [
        _check_part_name_set(anchor, template, max_extra=max_extra_parts),
        _check_joint_topology(anchor, template),
        _check_visual_count_per_part(anchor, template, min_ratio=visual_count_min_ratio),
        _check_primitive_complexity_lower_bound(anchor, template),
        _check_primitive_histogram_similarity(
            anchor, template, cosine_min=primitive_histogram_cosine_min
        ),
        _check_bbox_ratio(anchor, template, max_deviation=bbox_ratio_max_dev),
    ]
    overall = "pass" if all(sc.status == "pass" for sc in subchecks) else "fail"
    return AnchorMatchReport(
        overall_status=overall,
        anchor_source=anchor.source,
        template_source=template.source,
        subchecks=subchecks,
    )
