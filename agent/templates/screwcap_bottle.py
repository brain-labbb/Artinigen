"""Screwcap bottle modular template.

Slot graph:
  body -> thread -> cap

The body slot establishes the coaxial Z bottle/neck datum. The thread slot
adds the external neck thread to that same body part and re-exports the neck
interface. The cap slot emits the moving cap group and owns the screw motion:
either a simple coaxial spin or the threaded turn + axial lift model from the
5-star samples.
"""

from __future__ import annotations

import math
import random
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from agent.templates._modular import (
    InterfaceSpec,
    ModuleBuild,
    ModuleBuildContext,
    SlotSpec,
    assemble,
)
from sdk import (
    ArticulatedObject,
    ArticulationType,
    AssetContext,
    Box,
    Cylinder,
    Inertial,
    LatheGeometry,
    MotionLimits,
    Origin,
    TestContext,
    TestReport,
    TorusGeometry,
    mesh_from_geometry,
    tube_from_spline_points,
)

__modular__ = True


BodyModule = Literal["compact_lathe", "segmented_body", "rugged_utility"]
ThreadModule = Literal["helical_thread", "banded_thread", "stacked_finish"]
CapModule = Literal["ribbed_shell", "knurled_shell", "tethered_utility"]
ScrewMotionModel = Literal["simple_spin", "threaded_turn_lift"]
MaterialStyle = Literal["clear_plastic", "amber_lab", "sports_smoke"]

SOURCE_IDS = {
    "S1": "data/records/rec_screwcap_bottle_0002/revisions/rev_000001/model.py:L30-L94",
    "S2": "data/records/rec_screwcap_bottle_0002/revisions/rev_000001/model.py:L105-L147",
    "S3": "data/records/rec_screwcap_bottle_0002/revisions/rev_000001/model.py:L256-L315",
    "S4": "data/records/rec_screwcap_bottle_3b72f1b06e424f34a33ec81fc85feb89/revisions/rev_000001/model.py:L28-L49",
    "S5": "data/records/rec_screwcap_bottle_3b72f1b06e424f34a33ec81fc85feb89/revisions/rev_000001/model.py:L52-L236",
    "S6": "data/records/rec_screwcap_bottle_3b72f1b06e424f34a33ec81fc85feb89/revisions/rev_000001/model.py:L238-L263",
    "S7": "data/records/rec_screwcap_bottle_aa1625790e9e4236941bc4c2650955de/revisions/rev_000001/model.py:L58-L138",
    "S8": "data/records/rec_screwcap_bottle_aa1625790e9e4236941bc4c2650955de/revisions/rev_000001/model.py:L141-L263",
    "S9": "data/records/rec_screwcap_bottle_aa1625790e9e4236941bc4c2650955de/revisions/rev_000001/model.py:L265-L282",
    "S10": "data/records/rec_screwcap_bottle_6b2c1386d07447bfa26806abf78b4935/revisions/rev_000001/model.py:L35-L126",
    "S11": "data/records/rec_screwcap_bottle_6b2c1386d07447bfa26806abf78b4935/revisions/rev_000001/model.py:L140-L255",
}

SOURCE_ADAPTATION_MAP = {
    "body.compact_lathe": ("S4", "S5"),
    "body.segmented_body": ("S10", "S11"),
    "body.rugged_utility": ("S1", "S2", "S8"),
    "thread.helical_thread": ("S4", "S5", "S7", "S8"),
    "thread.banded_thread": ("S2", "S3"),
    "thread.stacked_finish": ("S10", "S11"),
    "cap.ribbed_shell": ("S5", "S6"),
    "cap.knurled_shell": ("S3", "S7", "S8"),
    "cap.tethered_utility": ("S3",),
    "motion.threaded_turn_lift": ("S6", "S9"),
}

BODY_MODULES: tuple[BodyModule, ...] = ("compact_lathe", "segmented_body", "rugged_utility")
THREAD_MODULES: tuple[ThreadModule, ...] = ("helical_thread", "banded_thread", "stacked_finish")
CAP_MODULES: tuple[CapModule, ...] = ("ribbed_shell", "knurled_shell", "tethered_utility")

PALETTES: dict[str, dict[str, tuple[float, float, float, float]]] = {
    "clear_plastic": {
        "body": (0.72, 0.84, 0.92, 0.55),
        "cap": (0.08, 0.10, 0.12, 1.0),
        "thread": (0.84, 0.88, 0.90, 1.0),
        "seal": (0.92, 0.92, 0.88, 1.0),
        "accent": (0.10, 0.55, 0.72, 1.0),
    },
    "amber_lab": {
        "body": (0.78, 0.42, 0.12, 0.62),
        "cap": (0.18, 0.16, 0.13, 1.0),
        "thread": (0.88, 0.62, 0.26, 1.0),
        "seal": (0.90, 0.84, 0.72, 1.0),
        "accent": (0.08, 0.08, 0.08, 1.0),
    },
    "sports_smoke": {
        "body": (0.34, 0.38, 0.42, 0.48),
        "cap": (0.88, 0.22, 0.12, 1.0),
        "thread": (0.70, 0.72, 0.72, 1.0),
        "seal": (0.05, 0.05, 0.05, 1.0),
        "accent": (0.04, 0.05, 0.055, 1.0),
    },
}


@dataclass(frozen=True)
class ScrewcapBottleConfig:
    body_module: BodyModule | None = None
    thread_module: ThreadModule | None = None
    cap_module: CapModule | None = None
    screw_motion_model: ScrewMotionModel = "threaded_turn_lift"
    material_style: MaterialStyle = "clear_plastic"
    body_height: float = 0.151
    body_radius: float = 0.038
    neck_height: float = 0.027
    thread_pitch: float = 0.0064
    thread_turns: float = 1.6
    thread_clearance: float = 0.0012
    name: str = "reference_screwcap_bottle"


@dataclass(frozen=True)
class ResolvedScrewcapBottleConfig:
    body_module: BodyModule
    thread_module: ThreadModule
    cap_module: CapModule
    screw_motion_model: ScrewMotionModel
    material_style: MaterialStyle
    body_height: float
    body_radius: float
    shoulder_height: float
    neck_radius: float
    neck_height: float
    neck_base_z: float
    thread_pitch: float
    thread_turns: float
    thread_height: float
    thread_travel: float
    thread_radius: float
    thread_clearance: float
    cap_inner_radius: float
    cap_outer_radius: float
    cap_skirt_height: float
    cap_height: float
    knurl_count: int
    palette: dict[str, tuple[float, float, float, float]]
    name: str


def config_from_seed(seed: int) -> ScrewcapBottleConfig:
    if seed == 0:
        return ScrewcapBottleConfig(
            body_module="compact_lathe",
            thread_module="helical_thread",
            cap_module="ribbed_shell",
            screw_motion_model="threaded_turn_lift",
            material_style="clear_plastic",
            body_height=0.151,
            body_radius=0.038,
            neck_height=0.027,
            thread_pitch=0.0064,
            thread_turns=1.6,
            thread_clearance=0.0012,
            name="reference_screwcap_bottle",
        )

    rng = random.Random(seed)
    body_module = rng.choice(BODY_MODULES)
    radius_range = {
        "compact_lathe": (0.032, 0.044),
        "segmented_body": (0.036, 0.052),
        "rugged_utility": (0.042, 0.066),
    }[body_module]
    height_range = {
        "compact_lathe": (0.135, 0.185),
        "segmented_body": (0.175, 0.255),
        "rugged_utility": (0.205, 0.305),
    }[body_module]
    return ScrewcapBottleConfig(
        body_module=body_module,
        thread_module=rng.choice(THREAD_MODULES),
        cap_module=rng.choice(CAP_MODULES),
        screw_motion_model="threaded_turn_lift" if rng.random() < 0.76 else "simple_spin",
        material_style=rng.choice(tuple(PALETTES)),
        body_height=round(rng.uniform(*height_range), 3),
        body_radius=round(rng.uniform(*radius_range), 3),
        neck_height=round(rng.uniform(0.022, 0.060), 3),
        thread_pitch=round(rng.uniform(0.0028, 0.0064), 4),
        thread_turns=round(rng.uniform(1.2, 2.8), 2),
        thread_clearance=round(rng.uniform(0.0008, 0.0024), 4),
        name=f"seeded_screwcap_bottle_{seed}",
    )


def resolve_config(config: ScrewcapBottleConfig) -> ResolvedScrewcapBottleConfig:
    body_module = config.body_module or "compact_lathe"
    thread_module = config.thread_module or "helical_thread"
    cap_module = config.cap_module or "ribbed_shell"
    if body_module not in BODY_MODULES:
        raise ValueError(f"Unsupported body_module: {body_module}")
    if thread_module not in THREAD_MODULES:
        raise ValueError(f"Unsupported thread_module: {thread_module}")
    if cap_module not in CAP_MODULES:
        raise ValueError(f"Unsupported cap_module: {cap_module}")
    if config.screw_motion_model not in {"simple_spin", "threaded_turn_lift"}:
        raise ValueError(f"Unsupported screw_motion_model: {config.screw_motion_model}")
    if config.material_style not in PALETTES:
        raise ValueError(f"Unsupported material_style: {config.material_style}")

    body_height = _clamp(config.body_height, 0.120, 0.340)
    body_radius = _clamp(config.body_radius, 0.025, 0.075)
    shoulder_height = min(max(body_height * 0.16, 0.020), 0.050)
    neck_radius_ratio = 0.48 if body_module == "segmented_body" else 0.40
    if body_module == "rugged_utility":
        neck_radius_ratio = 0.36
    neck_radius = body_radius * neck_radius_ratio
    thread_pitch = _clamp(config.thread_pitch, 0.002, 0.007)
    thread_turns = _clamp(config.thread_turns, 1.0, 3.5)
    thread_height = thread_pitch * thread_turns + 0.004
    neck_height = max(_clamp(config.neck_height, 0.018, 0.070), thread_height + 0.006)
    thread_travel = thread_pitch * thread_turns
    thread_radius = neck_radius + max(0.0009, body_radius * 0.026)
    thread_clearance = _clamp(config.thread_clearance, 0.0008, 0.0030)
    cap_inner_radius = thread_radius + thread_clearance + 0.0010
    grip_depth = 0.0026 if cap_module in {"knurled_shell", "tethered_utility"} else 0.0014
    cap_outer_radius = cap_inner_radius + max(0.0030, body_radius * 0.075) + grip_depth
    cap_skirt_height = max(thread_height + 0.008, neck_height * 0.84)
    cap_height = cap_skirt_height + max(0.004, cap_outer_radius * 0.15)
    neck_base_z = body_height - shoulder_height * 0.45
    return ResolvedScrewcapBottleConfig(
        body_module=body_module,
        thread_module=thread_module,
        cap_module=cap_module,
        screw_motion_model=config.screw_motion_model,
        material_style=config.material_style,
        body_height=body_height,
        body_radius=body_radius,
        shoulder_height=shoulder_height,
        neck_radius=neck_radius,
        neck_height=neck_height,
        neck_base_z=neck_base_z,
        thread_pitch=thread_pitch,
        thread_turns=thread_turns,
        thread_height=thread_height,
        thread_travel=thread_travel,
        thread_radius=thread_radius,
        thread_clearance=thread_clearance,
        cap_inner_radius=cap_inner_radius,
        cap_outer_radius=cap_outer_radius,
        cap_skirt_height=cap_skirt_height,
        cap_height=cap_height,
        knurl_count=max(18, int(cap_outer_radius / 0.0017)),
        palette=dict(PALETTES[config.material_style]),
        name=config.name,
    )


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def _mesh(geometry, assets: AssetContext, name: str):
    return mesh_from_geometry(geometry, assets.mesh_path(name))


def _helix_points(
    *,
    radius: float,
    z_start: float,
    pitch: float,
    turns: float,
    phase: float = math.pi / 5.0,
    samples_per_turn: int = 34,
) -> list[tuple[float, float, float]]:
    sample_count = max(8, int(math.ceil(turns * samples_per_turn)))
    return [
        (
            radius * math.cos(phase + math.tau * turns * i / sample_count),
            radius * math.sin(phase + math.tau * turns * i / sample_count),
            z_start + pitch * turns * i / sample_count,
        )
        for i in range(sample_count + 1)
    ]


def _body_interface(r: ResolvedScrewcapBottleConfig) -> InterfaceSpec:
    return InterfaceSpec(
        interface_name="neck_axis",
        part_name="bottle_body",
        visual_name="neck_finish",
        face_side="positive_z",
        anchor_local=(0.0, 0.0, r.neck_base_z + r.neck_height),
        face_extents_uv=(r.neck_radius * 2.0, r.neck_radius * 2.0),
        contact_tol=0.002,
    )


def _compact_profiles(r: ResolvedScrewcapBottleConfig):
    R = r.body_radius
    H = r.body_height
    neck_r = r.neck_radius
    outer = [
        (R * 0.26, 0.000),
        (R * 0.95, 0.004),
        (R, 0.012),
        (R, H - r.shoulder_height),
        (R * 0.90, H - r.shoulder_height * 0.60),
        (neck_r * 1.08, r.neck_base_z),
        (neck_r, r.neck_base_z + r.neck_height),
    ]
    inner = [
        (0.000, 0.005),
        (R * 0.84, 0.011),
        (R * 0.86, H - r.shoulder_height * 1.05),
        (neck_r * 0.82, r.neck_base_z),
        (neck_r * 0.80, r.neck_base_z + r.neck_height - 0.001),
    ]
    return outer, inner


def _segmented_profiles(r: ResolvedScrewcapBottleConfig):
    R = r.body_radius
    H = r.body_height
    neck_r = r.neck_radius
    outer = [
        (R * 0.30, 0.000),
        (R * 0.86, 0.006),
        (R * 0.98, H * 0.18),
        (R, H * 0.58),
        (R * 0.94, H * 0.74),
        (neck_r * 1.55, H - r.shoulder_height),
        (neck_r * 1.08, r.neck_base_z),
        (neck_r, r.neck_base_z + r.neck_height),
    ]
    inner = [
        (0.000, 0.007),
        (R * 0.76, 0.014),
        (R * 0.88, H * 0.20),
        (R * 0.90, H * 0.66),
        (neck_r * 1.10, r.neck_base_z),
        (neck_r * 0.78, r.neck_base_z + r.neck_height - 0.001),
    ]
    return outer, inner


def _rugged_profiles(r: ResolvedScrewcapBottleConfig):
    R = r.body_radius
    H = r.body_height
    neck_r = r.neck_radius
    outer = [
        (R * 0.72, 0.000),
        (R, 0.014),
        (R * 1.02, H * 0.64),
        (R * 0.92, H - r.shoulder_height),
        (neck_r * 1.42, r.neck_base_z),
        (neck_r, r.neck_base_z + r.neck_height),
    ]
    inner = [
        (0.000, 0.008),
        (R * 0.82, 0.014),
        (R * 0.86, H * 0.62),
        (neck_r * 1.05, r.neck_base_z),
        (neck_r * 0.78, r.neck_base_z + r.neck_height - 0.001),
    ]
    return outer, inner


def _emit_body_shell(
    ctx: ModuleBuildContext,
    *,
    profiles,
    shell_name: str,
    mesh_name: str,
) -> None:
    r: ResolvedScrewcapBottleConfig = ctx.config  # type: ignore[assignment]
    body = ctx.model.part("bottle_body")
    outer, inner = profiles(r)
    body.visual(
        _mesh(
            LatheGeometry.from_shell_profiles(
                outer,
                inner,
                segments=88,
                start_cap="flat",
                end_cap="flat",
            ),
            ctx.model.assets,
            mesh_name,
        ),
        material="body",
        name=shell_name,
    )
    body.visual(
        Cylinder(radius=r.neck_radius, length=r.neck_height),
        origin=Origin(xyz=(0.0, 0.0, r.neck_base_z + r.neck_height * 0.5)),
        material="body",
        name="neck_finish",
    )
    body.visual(
        Cylinder(radius=r.neck_radius * 1.28, length=0.004),
        origin=Origin(xyz=(0.0, 0.0, r.neck_base_z + 0.002)),
        material="body",
        name="shoulder_finish",
    )
    body.inertial = Inertial.from_geometry(
        Cylinder(radius=r.body_radius, length=r.body_height),
        mass=0.24,
        origin=Origin(xyz=(0.0, 0.0, r.body_height * 0.5)),
    )


def _build_body_compact_lathe(ctx: ModuleBuildContext) -> ModuleBuild:
    r: ResolvedScrewcapBottleConfig = ctx.config  # type: ignore[assignment]
    _emit_body_shell(
        ctx,
        profiles=_compact_profiles,
        shell_name="compact_lathe_shell",
        mesh_name="compact_bottle_shell.obj",
    )
    body = ctx.model.get_part("bottle_body")
    body.visual(
        _mesh(
            TorusGeometry(
                radius=r.body_radius * 0.93,
                tube=max(0.0025, r.body_radius * 0.090),
                radial_segments=72,
                tubular_segments=10,
            ),
            ctx.model.assets,
            "compact_base_ring.obj",
        ),
        origin=Origin(xyz=(0.0, 0.0, r.body_height * 0.065)),
        material="body",
        name="base_ring",
    )
    return ModuleBuild(
        module_name="compact_lathe",
        parts_emitted=["bottle_body"],
        interfaces={"downstream": _body_interface(r)},
    )


def _build_body_segmented(ctx: ModuleBuildContext) -> ModuleBuild:
    r: ResolvedScrewcapBottleConfig = ctx.config  # type: ignore[assignment]
    _emit_body_shell(
        ctx,
        profiles=_segmented_profiles,
        shell_name="segmented_body_shell",
        mesh_name="segmented_bottle_shell.obj",
    )
    body = ctx.model.get_part("bottle_body")
    for i, z in enumerate((r.body_height * 0.28, r.body_height * 0.60)):
        body.visual(
            _mesh(
                TorusGeometry(
                    radius=r.body_radius * (0.96 - 0.03 * i),
                    tube=0.0012,
                    radial_segments=72,
                    tubular_segments=8,
                ),
                ctx.model.assets,
                f"segmented_label_band_{i}.obj",
            ),
            origin=Origin(xyz=(0.0, 0.0, z)),
            material="accent",
            name=f"label_band_{i}",
        )
    return ModuleBuild(
        module_name="segmented_body",
        parts_emitted=["bottle_body"],
        interfaces={"downstream": _body_interface(r)},
    )


def _build_body_rugged(ctx: ModuleBuildContext) -> ModuleBuild:
    r: ResolvedScrewcapBottleConfig = ctx.config  # type: ignore[assignment]
    _emit_body_shell(
        ctx,
        profiles=_rugged_profiles,
        shell_name="rugged_utility_shell",
        mesh_name="rugged_utility_shell.obj",
    )
    body = ctx.model.get_part("bottle_body")
    for y, name in ((r.body_radius * 0.98, "front"), (-r.body_radius * 0.98, "rear")):
        body.visual(
            Box((r.body_radius * 1.15, r.body_radius * 0.11, r.body_height * 0.45)),
            origin=Origin(xyz=(0.0, y, r.body_height * 0.45)),
            material="accent",
            name=f"{name}_grip_pad",
        )
    for x, name in ((r.body_radius * 0.90, "right"), (-r.body_radius * 0.90, "left")):
        body.visual(
            Box((r.body_radius * 0.13, r.body_radius * 0.74, r.body_height * 0.54)),
            origin=Origin(xyz=(x, 0.0, r.body_height * 0.43)),
            material="body",
            name=f"{name}_side_rail",
        )
    return ModuleBuild(
        module_name="rugged_utility",
        parts_emitted=["bottle_body"],
        interfaces={"downstream": _body_interface(r)},
    )


def _build_thread_helical(ctx: ModuleBuildContext) -> ModuleBuild:
    r: ResolvedScrewcapBottleConfig = ctx.config  # type: ignore[assignment]
    body = ctx.model.get_part("bottle_body")
    body.visual(
        _mesh(
            tube_from_spline_points(
                _helix_points(
                    radius=r.thread_radius,
                    z_start=r.neck_base_z + 0.004,
                    pitch=r.thread_pitch,
                    turns=r.thread_turns,
                ),
                radius=max(0.00065, r.body_radius * 0.016),
                samples_per_segment=4,
                radial_segments=14,
                cap_ends=True,
            ),
            ctx.model.assets,
            "external_helical_thread.obj",
        ),
        material="thread",
        name="external_neck_thread",
    )
    return ModuleBuild(
        module_name="helical_thread",
        parts_emitted=[],
        interfaces={"downstream": ctx.upstream_interface} if ctx.upstream_interface else {},
    )


def _build_thread_banded(ctx: ModuleBuildContext) -> ModuleBuild:
    r: ResolvedScrewcapBottleConfig = ctx.config  # type: ignore[assignment]
    body = ctx.model.get_part("bottle_body")
    band_count = max(3, int(math.ceil(r.thread_turns * 2.0)))
    for i in range(band_count):
        body.visual(
            Cylinder(radius=r.thread_radius, length=0.0024),
            origin=Origin(xyz=(0.0, 0.0, r.neck_base_z + 0.005 + i * r.thread_pitch * 0.72)),
            material="thread",
            name=f"thread_band_{i}",
        )
    return ModuleBuild(
        module_name="banded_thread",
        parts_emitted=[],
        interfaces={"downstream": ctx.upstream_interface} if ctx.upstream_interface else {},
    )


def _build_thread_stacked_finish(ctx: ModuleBuildContext) -> ModuleBuild:
    r: ResolvedScrewcapBottleConfig = ctx.config  # type: ignore[assignment]
    body = ctx.model.get_part("bottle_body")
    for i, scale in enumerate((1.12, 1.05, 0.98, 0.92)):
        body.visual(
            Cylinder(radius=r.thread_radius * scale, length=0.0020),
            origin=Origin(xyz=(0.0, 0.0, r.neck_base_z + 0.004 + i * r.thread_pitch * 0.82)),
            material="thread",
            name=f"thread_turn_{i}",
        )
    body.visual(
        Cylinder(radius=r.thread_radius * 1.12, length=0.0030),
        origin=Origin(xyz=(0.0, 0.0, r.neck_base_z + r.thread_height + 0.006)),
        material="body",
        name="support_bead",
    )
    return ModuleBuild(
        module_name="stacked_finish",
        parts_emitted=[],
        interfaces={"downstream": ctx.upstream_interface} if ctx.upstream_interface else {},
    )


def _cap_profiles(r: ResolvedScrewcapBottleConfig):
    outer = [
        (r.cap_outer_radius, 0.000),
        (r.cap_outer_radius, r.cap_skirt_height),
        (r.cap_outer_radius * 0.93, r.cap_height),
        (0.000, r.cap_height),
    ]
    inner = [
        (r.cap_inner_radius, 0.000),
        (r.cap_inner_radius, r.cap_skirt_height - 0.001),
        (r.cap_inner_radius * 0.55, r.cap_height - 0.001),
    ]
    return outer, inner


def _emit_cap_insert(ctx: ModuleBuildContext, r: ResolvedScrewcapBottleConfig) -> None:
    insert = ctx.model.part("cap_insert")
    insert.visual(
        Cylinder(radius=r.cap_inner_radius * 0.28, length=r.cap_skirt_height),
        origin=Origin(xyz=(0.0, 0.0, r.cap_skirt_height * 0.5)),
        material="seal",
        name="coaxial_guide_post",
    )
    insert.visual(
        Cylinder(radius=r.cap_inner_radius * 0.88, length=0.0016),
        origin=Origin(xyz=(0.0, 0.0, 0.0008)),
        material="seal",
        name="seal_liner_disc",
    )
    insert.visual(
        Box((r.cap_inner_radius * 1.42, 0.0012, 0.0040)),
        origin=Origin(xyz=(r.cap_inner_radius * 0.36, 0.0, r.cap_skirt_height * 0.46)),
        material="seal",
        name="shell_contact_key",
    )
    insert.inertial = Inertial.from_geometry(
        Cylinder(radius=r.cap_inner_radius, length=r.cap_skirt_height),
        mass=0.006,
        origin=Origin(xyz=(0.0, 0.0, r.cap_skirt_height * 0.5)),
    )


def _emit_cap_shell_base(ctx: ModuleBuildContext, r: ResolvedScrewcapBottleConfig) -> None:
    cap = ctx.model.part("screw_cap")
    outer, inner = _cap_profiles(r)
    cap.visual(
        _mesh(
            LatheGeometry.from_shell_profiles(
                outer,
                inner,
                segments=88,
                start_cap="flat",
                end_cap="flat",
            ),
            ctx.model.assets,
            "screw_cap_shell.obj",
        ),
        material="cap",
        name="cap_outer_shell",
    )
    cap.visual(
        _mesh(
            tube_from_spline_points(
                _helix_points(
                    radius=r.cap_inner_radius - 0.0002,
                    z_start=0.004,
                    pitch=r.thread_pitch,
                    turns=r.thread_turns,
                ),
                radius=max(0.00055, r.body_radius * 0.014),
                samples_per_segment=4,
                radial_segments=12,
                cap_ends=True,
            ),
            ctx.model.assets,
            "internal_cap_thread.obj",
        ),
        material="thread",
        name="internal_cap_thread",
    )
    cap.visual(
        Cylinder(radius=r.cap_inner_radius * 0.24, length=0.004),
        origin=Origin(xyz=(0.0, 0.0, 0.002)),
        material="cap",
        name="inner_hub",
    )
    cap.visual(
        Box((r.cap_inner_radius * 1.70, 0.0014, 0.0032)),
        origin=Origin(xyz=(r.cap_inner_radius * 0.50, 0.0, 0.0022)),
        material="cap",
        name="thread_bridge",
    )
    cap.visual(
        Cylinder(radius=r.cap_inner_radius * 0.40, length=0.003),
        origin=Origin(xyz=(0.0, 0.0, r.cap_height - 0.002)),
        material="seal",
        name="seal_plug",
    )
    cap.inertial = Inertial.from_geometry(
        Cylinder(radius=r.cap_outer_radius, length=r.cap_height),
        mass=0.045,
        origin=Origin(xyz=(0.0, 0.0, r.cap_height * 0.5)),
    )


def _emit_cap_motion(ctx: ModuleBuildContext, r: ResolvedScrewcapBottleConfig) -> list[str]:
    body = ctx.model.get_part("bottle_body")
    insert = ctx.model.get_part("cap_insert")
    cap = ctx.model.get_part("screw_cap")
    joint_z = r.neck_base_z + r.neck_height - 0.001
    if r.screw_motion_model == "threaded_turn_lift":
        ctx.model.articulation(
            "cap_thread_lift",
            ArticulationType.PRISMATIC,
            parent=body,
            child=insert,
            origin=Origin(xyz=(0.0, 0.0, joint_z)),
            axis=(0.0, 0.0, 1.0),
            motion_limits=MotionLimits(
                effort=6.0,
                velocity=0.05,
                lower=0.0,
                upper=r.thread_travel,
            ),
            meta={
                "source_id": "S6/S9",
                "thread_pitch": r.thread_pitch,
                "thread_turns": r.thread_turns,
                "thread_travel": r.thread_travel,
                "semantic": "axial lift equals pitch times turns",
            },
        )
        ctx.model.articulation(
            "cap_spin",
            ArticulationType.REVOLUTE,
            parent=insert,
            child=cap,
            origin=Origin(),
            axis=(0.0, 0.0, 1.0),
            motion_limits=MotionLimits(
                effort=2.0,
                velocity=6.0,
                lower=0.0,
                upper=r.thread_turns * math.tau,
            ),
            meta={"source_id": "S6/S9", "semantic": "cap rotates coaxially on bottle neck thread"},
        )
        return ["cap_thread_lift", "cap_spin"]

    ctx.model.articulation(
        "cap_spin",
        ArticulationType.CONTINUOUS,
        parent=body,
        child=cap,
        origin=Origin(xyz=(0.0, 0.0, joint_z)),
        axis=(0.0, 0.0, 1.0),
        motion_limits=MotionLimits(effort=2.0, velocity=6.0),
        meta={"source_id": "S3", "semantic": "simple screwcap spin around neck axis"},
    )
    ctx.model.articulation(
        "cap_to_insert",
        ArticulationType.FIXED,
        parent=cap,
        child=insert,
        origin=Origin(),
        meta={"source_id": "S3", "semantic": "seal liner moves with cap"},
    )
    return ["cap_spin", "cap_to_insert"]


def _build_cap_ribbed(ctx: ModuleBuildContext) -> ModuleBuild:
    r: ResolvedScrewcapBottleConfig = ctx.config  # type: ignore[assignment]
    _emit_cap_insert(ctx, r)
    _emit_cap_shell_base(ctx, r)
    cap = ctx.model.get_part("screw_cap")
    for i in range(4):
        cap.visual(
            _mesh(
                TorusGeometry(
                    radius=r.cap_outer_radius + 0.0002,
                    tube=0.0007,
                    radial_segments=72,
                    tubular_segments=8,
                ),
                ctx.model.assets,
                f"cap_grip_ring_{i}.obj",
            ),
            origin=Origin(xyz=(0.0, 0.0, 0.006 + i * r.cap_skirt_height / 5.0)),
            material="accent",
            name=f"grip_ring_{i}",
        )
    joints = _emit_cap_motion(ctx, r)
    return ModuleBuild("ribbed_shell", ["cap_insert", "screw_cap"], joints)


def _build_cap_knurled(ctx: ModuleBuildContext) -> ModuleBuild:
    r: ResolvedScrewcapBottleConfig = ctx.config  # type: ignore[assignment]
    _emit_cap_insert(ctx, r)
    _emit_cap_shell_base(ctx, r)
    cap = ctx.model.get_part("screw_cap")
    for i in range(r.knurl_count):
        angle = math.tau * i / r.knurl_count
        cap.visual(
            Box((r.cap_outer_radius * 0.10, 0.0032, r.cap_skirt_height * 0.70)),
            origin=Origin(
                xyz=(
                    math.cos(angle) * r.cap_outer_radius,
                    math.sin(angle) * r.cap_outer_radius,
                    r.cap_skirt_height * 0.46,
                ),
                rpy=(0.0, 0.0, angle),
            ),
            material="accent",
            name=f"vertical_knurl_{i}",
        )
    cap.visual(
        Box((r.cap_outer_radius * 1.15, 0.004, 0.002)),
        origin=Origin(xyz=(r.cap_outer_radius * 0.20, 0.0, r.cap_height - 0.001)),
        material="seal",
        name="cap_index_mark",
    )
    joints = _emit_cap_motion(ctx, r)
    return ModuleBuild("knurled_shell", ["cap_insert", "screw_cap"], joints)


def _build_cap_tethered(ctx: ModuleBuildContext) -> ModuleBuild:
    r: ResolvedScrewcapBottleConfig = ctx.config  # type: ignore[assignment]
    _emit_cap_insert(ctx, r)
    _emit_cap_shell_base(ctx, r)
    cap = ctx.model.get_part("screw_cap")
    for i in range(max(16, r.knurl_count // 2)):
        angle = math.tau * i / max(16, r.knurl_count // 2)
        cap.visual(
            Box((r.cap_outer_radius * 0.08, 0.0035, r.cap_skirt_height * 0.62)),
            origin=Origin(
                xyz=(
                    math.cos(angle) * r.cap_outer_radius,
                    math.sin(angle) * r.cap_outer_radius,
                    r.cap_skirt_height * 0.44,
                ),
                rpy=(0.0, 0.0, angle),
            ),
            material="cap",
            name=f"tether_cap_knurl_{i}",
        )
    cap.visual(
        Box((r.cap_outer_radius * 0.42, r.cap_outer_radius * 0.25, r.cap_height * 0.44)),
        origin=Origin(xyz=(r.cap_outer_radius + 0.001, 0.0, r.cap_height * 0.56)),
        material="accent",
        name="tether_lug",
    )
    cap.visual(
        Box((r.cap_outer_radius * 1.25, 0.004, 0.003)),
        origin=Origin(xyz=(0.0, 0.0, r.cap_height - 0.0015)),
        material="accent",
        name="top_reinforcement_bar",
    )
    cap.visual(
        Box((0.004, r.cap_outer_radius * 1.25, 0.003)),
        origin=Origin(xyz=(0.0, 0.0, r.cap_height - 0.0015)),
        material="accent",
        name="top_reinforcement_cross",
    )
    joints = _emit_cap_motion(ctx, r)
    return ModuleBuild("tethered_utility", ["cap_insert", "screw_cap"], joints)


BODY_FACTORIES = {
    "compact_lathe": _build_body_compact_lathe,
    "segmented_body": _build_body_segmented,
    "rugged_utility": _build_body_rugged,
}

THREAD_FACTORIES = {
    "helical_thread": _build_thread_helical,
    "banded_thread": _build_thread_banded,
    "stacked_finish": _build_thread_stacked_finish,
}

CAP_FACTORIES = {
    "ribbed_shell": _build_cap_ribbed,
    "knurled_shell": _build_cap_knurled,
    "tethered_utility": _build_cap_tethered,
}


def _slots_for_config(r: ResolvedScrewcapBottleConfig) -> list[SlotSpec]:
    return [
        SlotSpec("body", BODY_FACTORIES, anchor_choice=r.body_module),
        SlotSpec("thread", THREAD_FACTORIES, anchor_choice=r.thread_module),
        SlotSpec("cap", CAP_FACTORIES, anchor_choice=r.cap_module),
    ]


def build_screwcap_bottle(
    config: ScrewcapBottleConfig | None = None,
    *,
    assets: AssetContext | None = None,
) -> ArticulatedObject:
    config = config or ScrewcapBottleConfig()
    r = resolve_config(config)
    if assets is None:
        assets = AssetContext(Path(tempfile.mkdtemp(prefix="articraft-screwcap-bottle-assets-")))
    model = ArticulatedObject(name=r.name, assets=assets)
    for material_name, rgba in r.palette.items():
        model.material(material_name, rgba=rgba)
    assemble(
        model,
        slots=_slots_for_config(r),
        rng=random.Random(0),
        palette=r.palette,
        config=r,
        seed=0,
    )
    return model


def build_seeded_screwcap_bottle(
    seed: int,
    *,
    assets: AssetContext | None = None,
) -> ArticulatedObject:
    return build_screwcap_bottle(config_from_seed(seed), assets=assets)


def slot_choices_for_seed(seed: int) -> list[tuple[str, str]]:
    r = resolve_config(config_from_seed(seed))
    return [
        ("body", r.body_module),
        ("thread", r.thread_module),
        ("cap", r.cap_module),
    ]


def run_screwcap_bottle_tests(
    object_model: ArticulatedObject,
    config: ScrewcapBottleConfig,
) -> TestReport:
    r = resolve_config(config)
    ctx = TestContext(object_model)
    ctx.check_model_valid()
    ctx.fail_if_isolated_parts()
    ctx.check(
        "identity",
        all(
            object_model.get_part(name) is not None
            for name in ("bottle_body", "cap_insert", "screw_cap")
        ),
        "body, cap insert, and cap shell are required",
    )
    spin = object_model.get_articulation("cap_spin")
    ctx.check("cap_spin_axis_z", tuple(spin.axis) == (0.0, 0.0, 1.0), details=str(spin.axis))
    ctx.check(
        "cap_fit_clearance",
        r.cap_inner_radius > r.thread_radius + r.thread_clearance * 0.5,
        details=f"inner={r.cap_inner_radius}, thread={r.thread_radius}",
    )
    ctx.check(
        "skirt_covers_thread",
        r.cap_skirt_height > r.thread_height,
        details=f"skirt={r.cap_skirt_height}, thread={r.thread_height}",
    )
    if r.screw_motion_model == "threaded_turn_lift":
        lift = object_model.get_articulation("cap_thread_lift")
        ctx.check("lift_axis_z", tuple(lift.axis) == (0.0, 0.0, 1.0), details=str(lift.axis))
        ctx.check(
            "pitch_travel_consistent",
            abs(r.thread_travel - r.thread_pitch * r.thread_turns) < 1e-9,
            details=f"travel={r.thread_travel}",
        )
        ctx.check(
            "turn_limit_consistent",
            spin.motion_limits is not None
            and abs((spin.motion_limits.upper or 0.0) - r.thread_turns * math.tau) < 1e-9,
            details=f"turns={r.thread_turns}",
        )
    return ctx.report()


__all__ = [
    "__modular__",
    "ScrewcapBottleConfig",
    "ResolvedScrewcapBottleConfig",
    "SOURCE_IDS",
    "SOURCE_ADAPTATION_MAP",
    "config_from_seed",
    "resolve_config",
    "build_screwcap_bottle",
    "build_seeded_screwcap_bottle",
    "slot_choices_for_seed",
    "run_screwcap_bottle_tests",
]
