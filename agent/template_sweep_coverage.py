"""Coverage gates for `articraft template compile-sweep`.

Three independent gates feed into the top-level verdict:

1. `line_floor` — template file must be at least N lines (default 1000).
2. `enum_coverage` — every Literal[...] value declared on the template's
   input Config dataclass must be exercised by at least one **passing** seed
   in the sweep. If a declared enum value never appears in the sample (or
   appears only in failing seeds), the gate fails and reports the missing
   pairs.
3. `adopted_source` — if the corresponding spec markdown has an "Adopted
   Source Index" table, every `source_id` declared there must appear in the
   template as a `# adopted: <id>` marker (so structural reuse of 5-star
   sample code is auditable). If the spec is absent or has no table, the
   gate reports `status="skipped"` rather than failing.

All gates produce structured per-gate JSON; the suite-level verdict is set
elsewhere (in `run_sweep`) based on `gate.status` plus pass-rate.
"""

from __future__ import annotations

import importlib
import re
import typing
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

from agent.template_sweep import SeedOutcome
from agent.template_sweep_anchor import (
    AnchorMatchReport,
    compare_fingerprints,
    extract_fingerprint_from_anchor,
    extract_fingerprint_from_template,
)

DEFAULT_LINE_FLOOR = 1000

# Temporary kill-switches for the new coverage gates.
# Set to False while existing templates are grandfathered: the conventions
# below were introduced together with this sweep CLI, so every pre-sweep
# template fails by construction.
# - adopted_source: requires `# adopted: <Sxx>` markers matching the spec's
#   Adopted Source Index. New convention, no existing template has them.
# - enum_coverage:  requires every Literal value on the Config to be exercised
#   by a passing seed. Most templates declare Literal options that
#   `config_from_seed` does not yet sample.
# The check functions (`check_adopted_source`, `check_enum_coverage`) stay
# importable and unit-tested; only `evaluate_gates` skips them when disabled.
ADOPTED_SOURCE_GATE_ENABLED: bool = False
ENUM_COVERAGE_GATE_ENABLED: bool = False


@dataclass(slots=True)
class CoverageGateResult:
    name: str
    status: str  # "pass" | "fail" | "skipped"
    details: dict[str, Any] = field(default_factory=dict)
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "details": self.details,
            "reason": self.reason,
        }


@dataclass(slots=True)
class CoverageGates:
    line_floor: CoverageGateResult
    enum_coverage: CoverageGateResult
    adopted_source: CoverageGateResult
    anchor_geometry_match: CoverageGateResult

    def _iter_gates(self):
        return (
            self.line_floor,
            self.enum_coverage,
            self.adopted_source,
            self.anchor_geometry_match,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "line_floor": self.line_floor.to_dict(),
            "enum_coverage": self.enum_coverage.to_dict(),
            "adopted_source": self.adopted_source.to_dict(),
            "anchor_geometry_match": self.anchor_geometry_match.to_dict(),
        }

    def all_pass_or_skipped(self) -> bool:
        return all(gate.status in {"pass", "skipped"} for gate in self._iter_gates())

    def failing_gates(self) -> list[str]:
        return [gate.name for gate in self._iter_gates() if gate.status == "fail"]


# --------------------------------------------------------------------------- #
# Gate 1: line floor
# --------------------------------------------------------------------------- #


def check_line_floor(line_count: int, *, floor: int = DEFAULT_LINE_FLOOR) -> CoverageGateResult:
    if line_count >= floor:
        return CoverageGateResult(
            name="line_floor",
            status="pass",
            details={"line_count": line_count, "floor": floor},
        )
    return CoverageGateResult(
        name="line_floor",
        status="fail",
        details={"line_count": line_count, "floor": floor},
        reason=(
            f"template has {line_count} lines, below the {floor}-line floor; "
            "templates at this stage almost always need more parametric branches "
            "or richer _build_* coverage to be production-quality."
        ),
    )


# --------------------------------------------------------------------------- #
# Gate 2: enum coverage
# --------------------------------------------------------------------------- #


def _input_config_class(slug: str) -> type | None:
    try:
        module = importlib.import_module(f"agent.templates.{slug}")
    except ImportError:
        return None
    fn = getattr(module, "config_from_seed", None)
    if not callable(fn):
        return None
    try:
        sample = fn(0)
    except Exception:
        return None
    return type(sample)


def _literal_fields(cls: type) -> dict[str, list[Any]]:
    """Return {field_name: [declared_literal_values, ...]} for Literal-typed fields."""
    try:
        hints = typing.get_type_hints(cls)
    except Exception:
        hints = getattr(cls, "__annotations__", {}) or {}
    result: dict[str, list[Any]] = {}
    for field_name, hint in hints.items():
        origin = typing.get_origin(hint)
        # Unwrap Optional[Literal[...]] -> Literal[...]
        if origin is typing.Union:
            for arg in typing.get_args(hint):
                if typing.get_origin(arg) is typing.Literal:
                    result[field_name] = list(typing.get_args(arg))
                    break
            continue
        if origin is typing.Literal:
            result[field_name] = list(typing.get_args(hint))
    return result


def check_enum_coverage(slug: str, outcomes: Sequence[SeedOutcome]) -> CoverageGateResult:
    cls = _input_config_class(slug)
    if cls is None:
        return CoverageGateResult(
            name="enum_coverage",
            status="skipped",
            details={},
            reason="could not import template config dataclass for enum inspection",
        )
    enums = _literal_fields(cls)
    if not enums:
        return CoverageGateResult(
            name="enum_coverage",
            status="skipped",
            details={"declared_enum_fields": []},
            reason="template Config has no Literal-typed enum fields to cover",
        )

    passing = [o for o in outcomes if o.verdict == "pass"]
    per_field: dict[str, dict[str, Any]] = {}
    missing: list[dict[str, Any]] = []
    for field_name, declared in enums.items():
        declared_set = list(declared)
        exercised = {o.config.get(field_name) for o in passing if isinstance(o.config, Mapping)}
        exercised = {v for v in exercised if v is not None}
        missing_values = [v for v in declared_set if v not in exercised]
        per_field[field_name] = {
            "declared": declared_set,
            "exercised_by_passing": sorted(
                exercised, key=lambda x: ("", x) if isinstance(x, str) else ("", repr(x))
            ),
            "missing": missing_values,
        }
        for v in missing_values:
            missing.append({"field": field_name, "value": v})

    if not missing:
        return CoverageGateResult(
            name="enum_coverage",
            status="pass",
            details={"fields": per_field},
        )
    return CoverageGateResult(
        name="enum_coverage",
        status="fail",
        details={"fields": per_field, "missing": missing},
        reason=(
            f"{len(missing)} Literal value(s) declared on the Config but never "
            "exercised by a passing seed. Either widen the seed range so the "
            "value gets sampled and passes baseline, or fix the corresponding "
            "_build_<value> branch so the value works when sampled."
        ),
    )


# --------------------------------------------------------------------------- #
# Gate 3: adopted source lint
# --------------------------------------------------------------------------- #

_SOURCE_ID_RE = re.compile(r"^\|\s*(S\d+)\s*\|", re.MULTILINE)
_ADOPTED_MARKER_RE = re.compile(r"#\s*adopted:\s*(S\d+)", re.MULTILINE)


def _spec_path(slug: str, *, repo_root: Path) -> Path:
    return repo_root / "articraft_template_authoring" / "specs" / f"{slug}.md"


def _template_path(slug: str, *, repo_root: Path) -> Path:
    return repo_root / "agent" / "templates" / f"{slug}.py"


def _extract_adopted_source_ids(spec_text: str) -> list[str]:
    """Extract source_ids from the 'Adopted Source Index' table.

    Looks at the section between '## 采用源码索引' (or 'Adopted Source Index')
    and the next '## ' heading.
    """
    section_re = re.compile(
        r"(##\s*(?:采用源码索引|Adopted Source Index)[^\n]*\n)([\s\S]*?)(?=\n## |\Z)",
        re.MULTILINE,
    )
    match = section_re.search(spec_text)
    if not match:
        return []
    section = match.group(2)
    ids = _SOURCE_ID_RE.findall(section)
    # Dedup while preserving order; skip the table column header which won't match.
    seen: set[str] = set()
    out: list[str] = []
    for sid in ids:
        if sid not in seen:
            seen.add(sid)
            out.append(sid)
    return out


def check_adopted_source(slug: str, *, repo_root: Path) -> CoverageGateResult:
    spec_path = _spec_path(slug, repo_root=repo_root)
    template_path = _template_path(slug, repo_root=repo_root)
    if not spec_path.exists():
        return CoverageGateResult(
            name="adopted_source",
            status="skipped",
            details={"spec_path": str(spec_path)},
            reason="spec markdown not found; adopted-source lint requires the spec",
        )
    spec_text = spec_path.read_text(encoding="utf-8")
    declared_ids = _extract_adopted_source_ids(spec_text)
    if not declared_ids:
        return CoverageGateResult(
            name="adopted_source",
            status="skipped",
            details={"spec_path": str(spec_path), "declared_source_ids": []},
            reason="spec has no Adopted Source Index entries to enforce",
        )
    if not template_path.exists():
        return CoverageGateResult(
            name="adopted_source",
            status="fail",
            details={
                "spec_path": str(spec_path),
                "declared_source_ids": declared_ids,
                "template_path": str(template_path),
            },
            reason="template file not found while spec declares Adopted Source Index entries",
        )
    template_text = template_path.read_text(encoding="utf-8")
    referenced = set(_ADOPTED_MARKER_RE.findall(template_text))
    missing = [sid for sid in declared_ids if sid not in referenced]
    details = {
        "spec_path": str(spec_path),
        "declared_source_ids": declared_ids,
        "template_referenced": sorted(referenced),
        "missing": missing,
    }
    if not missing:
        return CoverageGateResult(
            name="adopted_source",
            status="pass",
            details=details,
        )
    return CoverageGateResult(
        name="adopted_source",
        status="fail",
        details=details,
        reason=(
            f"{len(missing)} adopted-source id(s) declared in the spec are not "
            "referenced by any `# adopted: <Sxx>` marker in the template. Add "
            "the markers above the helper code that adapts the corresponding "
            "5-star sample snippet, or remove the unused source_id from the spec."
        ),
    )


# --------------------------------------------------------------------------- #
# Gate 4: anchor_geometry_match
# --------------------------------------------------------------------------- #

_PRIMARY_ANCHOR_RE = re.compile(
    r"^\|\s*primary[_ ]anchor\s*\|\s*`?(?P<value>[^|`]+?)`?\s*\|",
    re.MULTILINE | re.IGNORECASE,
)


def parse_spec_primary_anchor(slug: str, *, repo_root: Path) -> str | None:
    """Read `articraft_template_authoring/specs/<slug>.md` and extract the
    `primary_anchor` value declared in the 元信息 table, e.g.:

        | primary_anchor | rec_dj_equipment_xxx:rev_000001 |
    """
    spec_path = _spec_path(slug, repo_root=repo_root)
    if not spec_path.exists():
        return None
    text = spec_path.read_text(encoding="utf-8")
    match = _PRIMARY_ANCHOR_RE.search(text)
    if not match:
        return None
    value = match.group("value").strip()
    if not value or value.lower() in {"none", "tbd", "n/a"}:
        return None
    return value


def check_anchor_geometry_match(
    slug: str,
    *,
    repo_root: Path,
    template_seed: int = 0,
) -> CoverageGateResult:
    primary_anchor = parse_spec_primary_anchor(slug, repo_root=repo_root)
    if primary_anchor is None:
        return CoverageGateResult(
            name="anchor_geometry_match",
            status="skipped",
            details={"primary_anchor": None},
            reason=(
                "spec does not declare `primary_anchor` in the 元信息 table. Add a "
                "row `| primary_anchor | rec_<id>:rev_<n> |` to enforce structural "
                "fidelity to a 5-star sample. Existing pre-sweep templates are "
                "grandfathered (gate skipped) until they migrate."
            ),
        )
    try:
        anchor_fp = extract_fingerprint_from_anchor(primary_anchor, repo_root=repo_root)
    except (FileNotFoundError, ValueError) as exc:
        return CoverageGateResult(
            name="anchor_geometry_match",
            status="fail",
            details={"primary_anchor": primary_anchor, "error_kind": type(exc).__name__},
            reason=(
                f"could not load anchor `{primary_anchor}`: {exc}. "
                "Verify the spec's primary_anchor points to an existing record."
            ),
        )
    try:
        template_fp = extract_fingerprint_from_template(slug, seed=template_seed)
    except Exception as exc:  # noqa: BLE001 — fingerprint of broken template is itself a failure
        return CoverageGateResult(
            name="anchor_geometry_match",
            status="fail",
            details={
                "primary_anchor": primary_anchor,
                "template_seed": template_seed,
                "error_kind": type(exc).__name__,
            },
            reason=(
                f"could not extract template fingerprint at seed {template_seed}: "
                f"{type(exc).__name__}: {exc}"
            ),
        )
    report: AnchorMatchReport = compare_fingerprints(anchor_fp, template_fp)
    deviations_payload: list[dict[str, Any]] = []
    for subcheck in report.subchecks:
        if subcheck.status == "fail":
            deviations_payload.append(
                {"subcheck": subcheck.name, "deviations": subcheck.deviations}
            )
    details = {
        "primary_anchor": primary_anchor,
        "template_seed": template_seed,
        "anchor_source": report.anchor_source,
        "template_source": report.template_source,
        "subchecks": [sc.to_dict() for sc in report.subchecks],
    }
    if report.overall_status == "pass":
        return CoverageGateResult(
            name="anchor_geometry_match",
            status="pass",
            details=details,
        )
    return CoverageGateResult(
        name="anchor_geometry_match",
        status="fail",
        details={**details, "failing_subchecks": deviations_payload},
        reason=(
            f"template at seed {template_seed} diverges from PRIMARY_ANCHOR "
            f"{primary_anchor!r} on "
            f"{len([sc for sc in report.subchecks if sc.status == 'fail'])} of "
            f"{len(report.subchecks)} subchecks "
            f"({', '.join(sc.name for sc in report.subchecks if sc.status == 'fail')}). "
            "Refer to subchecks[].deviations[].reason for per-deviation explanations. "
            "Adopt the anchor's helper code with parameter substitution; do not "
            "freehand structure that the anchor doesn't have."
        ),
    )


# --------------------------------------------------------------------------- #
# Aggregate
# --------------------------------------------------------------------------- #


def evaluate_gates(
    *,
    slug: str,
    line_count: int,
    outcomes: Sequence[SeedOutcome],
    repo_root: Path,
    line_floor: int = DEFAULT_LINE_FLOOR,
) -> CoverageGates:
    if ADOPTED_SOURCE_GATE_ENABLED:
        adopted_source = check_adopted_source(slug, repo_root=repo_root)
    else:
        adopted_source = CoverageGateResult(
            name="adopted_source",
            status="skipped",
            details={"gate_disabled": True},
            reason=(
                "adopted_source gate temporarily disabled while existing "
                "templates are grandfathered (see ADOPTED_SOURCE_GATE_ENABLED "
                "in agent/template_sweep_coverage.py)."
            ),
        )
    if ENUM_COVERAGE_GATE_ENABLED:
        enum_coverage = check_enum_coverage(slug, outcomes)
    else:
        enum_coverage = CoverageGateResult(
            name="enum_coverage",
            status="skipped",
            details={"gate_disabled": True},
            reason=(
                "enum_coverage gate temporarily disabled while existing "
                "templates are grandfathered (see ENUM_COVERAGE_GATE_ENABLED "
                "in agent/template_sweep_coverage.py)."
            ),
        )
    anchor_geometry_match = check_anchor_geometry_match(slug, repo_root=repo_root)
    return CoverageGates(
        line_floor=check_line_floor(line_count, floor=line_floor),
        enum_coverage=enum_coverage,
        adopted_source=adopted_source,
        anchor_geometry_match=anchor_geometry_match,
    )
