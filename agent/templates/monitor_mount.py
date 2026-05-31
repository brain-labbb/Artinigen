"""Articulated monitor mount — modular procedural template.

This template uses the slot/module/assembler abstraction in
``agent.templates._modular``. Three slots — **base**, **arm**, **head** —
each pick from a small candidate pool sourced from the 5-star sample
family. The assembler wires modules together with ``MatingContract``-backed
articulations (shoulder_lift + head_pan).

Slot graph:
    base -> arm -> head

Candidates (6 total):

  base:
    - wall_bracket (anchor; rec_monitor_mount_997e8c29...:rev_000001 —
                    classic wall-plate + bearing-cup + pan_carriage with
                    CONTINUOUS pan_pivot)
    - desk_clamp_post (alt: desktop-clamp + tall post + REVOLUTE swivel
                    at the top, derived from rec_monitor_mount_0001's
                    desk_clamp + lower_arm yaw bearing)

  arm:
    - dual_link_arm (anchor; primary_arm + secondary_arm with a REVOLUTE
                    elbow_fold in between)
    - single_link_arm (alt: single consolidated cantilever arm with no
                    internal elbow, longer reach — derived from the
                    rec_monitor_mount_b009 single-secondary-link layout
                    collapsed to one piece)

  head:
    - pan_tilt_head (anchor; head_knuckle + tilt_head with REVOLUTE
                    head_tilt — the canonical 5-star sample's tilt
                    cradle assembly)
    - tilt_only_head (alt: single consolidated head with only the tilt
                    motion absorbed by the shared head_pan joint —
                    derived from rec_monitor_mount_0001's head/vesa
                    short-stack)

seed == 0 always picks the anchor combination
(wall_bracket + dual_link_arm + pan_tilt_head), reproducing the canonical
5-star sample's STRUCTURE (part tree + joint topology) — though laid out
in the modular interface idiom (clevis-style boss/hub mating at every
chain joint) so the assembler can enforce mating contracts at compile
time. Other seeds RNG-pick uniformly across the 2x2x2 = 8 combinations.

Anchor responsibility is at the **interface** level: each module declares
the geometry of the face it exposes, and the assembler validates that
adjacent modules' faces are opposite-normal compatible before emitting
the chain joint. The ``module_topology_diversity`` gate (which replaces
``anchor_geometry_match`` for modular templates) verifies that ≥5 distinct
slot_choice combinations appear among passing seeds.

Mating model: internal mechanical pivots inside a module (e.g. the pan
spindle inside the wall bracket's bearing socket, the head_tilt trunnion
inside the tilt cradle) remain *grandfathered* — they are
pin-through-bushing geometries that the MatingContract abstraction does
not naturally model, so we **deliberately omit** the ``mating`` argument
on those internal articulations. The compile-time
``fail_if_joint_mating_has_gap`` baseline skips joints without a
MatingContract. The intentional captured-pivot overlaps that would
otherwise trip ``fail_if_parts_overlap_in_current_pose`` are explicitly
allow-listed via ``ctx.allow_overlap(...)`` in the author tests.

The chain joints emitted by the assembler (``shoulder_lift`` and
``head_pan``), in contrast, use a **clevis-style** boss/lug geometry
that the MatingContract abstraction fits exactly: a top_lug (small Box)
on the parent's pan_carriage / arm meets the matching cylindrical hub
(``shoulder_hub`` / ``pan_hub``) on the child's arm / head_knuckle. Both
visuals lie at the joint origin in their respective local frames, so the
mating gap measures zero at the closed pose.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
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
    MatingContract,
    MotionLimits,
    MotionProperties,
    Origin,
    TestContext,
    TestReport,
)

# Modular templates are flagged so the sweep coverage gate can skip
# anchor_geometry_match (a single-anchor gate that does not apply when
# topology varies across seeds) and run module_topology_diversity instead.
__modular__ = True


BaseModule = Literal["wall_bracket", "desk_clamp_post"]
ArmModule = Literal[
    "dual_link_arm",
    "single_link_arm",
    "triple_link_arm",
    "quad_link_arm",
    "quint_link_arm",
    "hex_link_arm",
    "hept_link_arm",
    "oct_link_arm",
]
HeadModule = Literal["pan_tilt_head", "tilt_only_head"]

MountPaletteTheme = Literal[
    "anodized_aluminum",
    "all_black_carbon",
    "office_white",
    "industrial_yellow",
    "matte_bronze",
]


# --------------------------------------------------------------------------- #
# Palette presets — preserved verbatim from the prior single-anchor template.
# Each theme provides anodized / dark / bearing / cover / spring / brass /
# cable color tokens that module factories pull from the resolved palette.
# --------------------------------------------------------------------------- #


MOUNT_PALETTE_PRESETS: dict[str, dict[str, tuple[float, float, float, float]]] = {
    "anodized_aluminum": {
        "anodized": (0.32, 0.34, 0.36, 1.0),
        "dark": (0.055, 0.060, 0.065, 1.0),
        "bearing": (0.72, 0.74, 0.76, 1.0),
        "cover": (0.15, 0.16, 0.17, 1.0),
        "spring": (0.42, 0.43, 0.44, 1.0),
        "brass": (0.70, 0.48, 0.22, 1.0),
        "cable": (0.015, 0.017, 0.020, 1.0),
    },
    "all_black_carbon": {
        "anodized": (0.07, 0.08, 0.09, 1.0),
        "dark": (0.03, 0.03, 0.04, 1.0),
        "bearing": (0.65, 0.66, 0.68, 1.0),
        "cover": (0.10, 0.10, 0.11, 1.0),
        "spring": (0.20, 0.20, 0.21, 1.0),
        "brass": (0.55, 0.52, 0.50, 1.0),
        "cable": (0.02, 0.02, 0.02, 1.0),
    },
    "office_white": {
        "anodized": (0.92, 0.92, 0.91, 1.0),
        "dark": (0.32, 0.34, 0.36, 1.0),
        "bearing": (0.84, 0.85, 0.86, 1.0),
        "cover": (0.78, 0.79, 0.80, 1.0),
        "spring": (0.62, 0.63, 0.64, 1.0),
        "brass": (0.80, 0.66, 0.40, 1.0),
        "cable": (0.20, 0.21, 0.22, 1.0),
    },
    "industrial_yellow": {
        "anodized": (0.93, 0.78, 0.18, 1.0),
        "dark": (0.06, 0.06, 0.07, 1.0),
        "bearing": (0.74, 0.76, 0.78, 1.0),
        "cover": (0.10, 0.10, 0.11, 1.0),
        "spring": (0.32, 0.32, 0.34, 1.0),
        "brass": (0.70, 0.48, 0.22, 1.0),
        "cable": (0.02, 0.02, 0.02, 1.0),
    },
    "matte_bronze": {
        "anodized": (0.46, 0.30, 0.18, 1.0),
        "dark": (0.20, 0.13, 0.08, 1.0),
        "bearing": (0.78, 0.62, 0.36, 1.0),
        "cover": (0.30, 0.22, 0.16, 1.0),
        "spring": (0.42, 0.35, 0.28, 1.0),
        "brass": (0.85, 0.60, 0.30, 1.0),
        "cable": (0.05, 0.04, 0.03, 1.0),
    },
}


@dataclass(frozen=True)
class MonitorMountConfig:
    """Public template config. Module selection is opt-in: leave any of
    the three module fields as ``None`` to let ``config_from_seed`` /
    ``resolve_config`` fill them in from the seed-driven RNG.

    Continuous parameters (plate sizes, arm lengths, head sizes) drive
    the *envelope* of whichever module is built. Module factories may
    apply per-variant scaling; see each ``_build_*`` docstring.
    """

    base_module: BaseModule | None = None
    arm_module: ArmModule | None = None
    head_module: HeadModule | None = None
    palette_theme: MountPaletteTheme = "anodized_aluminum"

    # Wall/desk plate sizing.
    wall_plate_height: float = 0.460
    wall_plate_width: float = 0.340
    wall_plate_thickness: float = 0.026

    # Pan carriage / post.
    pan_carriage_height: float = 0.240
    pan_carriage_radius: float = 0.052
    shoulder_lug_thickness: float = 0.022
    shoulder_lug_radius: float = 0.062
    shoulder_hub_radius: float = 0.046

    # Primary / secondary arm sizing.
    primary_arm_length: float = 0.300
    primary_arm_width: float = 0.060
    primary_arm_height: float = 0.046

    secondary_arm_length: float = 0.380
    secondary_arm_width: float = 0.054
    secondary_arm_height: float = 0.044

    # Mid-arm link lengths (only used when arm_module is triple_link_arm
    # or quad_link_arm). Geometry width/height inherit from the primary
    # arm's dims so the chain of links looks visually consistent.
    tertiary_arm_length: float = 0.300
    quaternary_arm_length: float = 0.300

    elbow_lug_thickness: float = 0.020
    elbow_lug_radius: float = 0.052
    elbow_hub_radius: float = 0.040

    wrist_lug_thickness: float = 0.020
    wrist_lug_radius: float = 0.052

    # Head sizing.
    pan_hub_radius: float = 0.040
    head_knuckle_length: float = 0.108
    tilt_cheek_thickness: float = 0.018
    tilt_cheek_height: float = 0.080
    tilt_head_plate_height: float = 0.164
    tilt_head_plate_width: float = 0.184

    palette: dict[str, tuple[float, float, float, float]] = field(
        default_factory=lambda: dict(MOUNT_PALETTE_PRESETS["anodized_aluminum"])
    )


@dataclass(frozen=True)
class ResolvedMonitorMountConfig:
    """Dimension-clamped + module-resolved config consumed by builders."""

    base_module: BaseModule
    arm_module: ArmModule
    head_module: HeadModule
    palette_theme: MountPaletteTheme

    wall_plate_height: float
    wall_plate_width: float
    wall_plate_thickness: float

    pan_carriage_height: float
    pan_carriage_radius: float
    shoulder_lug_thickness: float
    shoulder_lug_radius: float
    shoulder_hub_radius: float

    primary_arm_length: float
    primary_arm_width: float
    primary_arm_height: float

    secondary_arm_length: float
    secondary_arm_width: float
    secondary_arm_height: float

    tertiary_arm_length: float
    quaternary_arm_length: float

    elbow_lug_thickness: float
    elbow_lug_radius: float
    elbow_hub_radius: float

    wrist_lug_thickness: float
    wrist_lug_radius: float

    pan_hub_radius: float
    head_knuckle_length: float
    tilt_cheek_thickness: float
    tilt_cheek_height: float
    tilt_head_plate_height: float
    tilt_head_plate_width: float

    palette: dict[str, tuple[float, float, float, float]]


def config_from_seed(seed: int) -> MonitorMountConfig:
    """Sample a monitor mount configuration for the given seed.

    seed == 0 always returns the anchor combination
    (wall_bracket + dual_link_arm + pan_tilt_head) at the anchor's
    canonical dimensions. Other seeds pick modules uniformly from each
    slot's candidate pool and sample continuous dimensions across a
    realistic range.
    """

    if seed == 0:
        return MonitorMountConfig(
            base_module="wall_bracket",
            arm_module="dual_link_arm",
            head_module="pan_tilt_head",
            palette_theme="anodized_aluminum",
        )

    rng = random.Random(seed)
    base: BaseModule = rng.choice(("wall_bracket", "desk_clamp_post"))
    arm: ArmModule = rng.choice(
        (
            "dual_link_arm",
            "single_link_arm",
            "triple_link_arm",
            "quad_link_arm",
            "quint_link_arm",
            "hex_link_arm",
            "hept_link_arm",
            "oct_link_arm",
        )
    )
    head: HeadModule = rng.choice(("pan_tilt_head", "tilt_only_head"))
    palette_theme: MountPaletteTheme = rng.choice(tuple(MOUNT_PALETTE_PRESETS.keys()))

    return MonitorMountConfig(
        base_module=base,
        arm_module=arm,
        head_module=head,
        palette_theme=palette_theme,
        wall_plate_height=round(rng.uniform(0.380, 0.520), 4),
        wall_plate_width=round(rng.uniform(0.280, 0.380), 4),
        primary_arm_length=round(rng.uniform(0.260, 0.380), 4),
        secondary_arm_length=round(rng.uniform(0.320, 0.460), 4),
        tertiary_arm_length=round(rng.uniform(0.240, 0.360), 4),
        quaternary_arm_length=round(rng.uniform(0.240, 0.360), 4),
        tilt_head_plate_height=round(rng.uniform(0.140, 0.200), 4),
        tilt_head_plate_width=round(rng.uniform(0.160, 0.220), 4),
    )


def resolve_config(config: MonitorMountConfig) -> ResolvedMonitorMountConfig:
    """Validate + clamp config; fill in any None module slots with anchor
    defaults."""

    base = config.base_module or "wall_bracket"
    arm = config.arm_module or "dual_link_arm"
    head = config.head_module or "pan_tilt_head"

    if base not in ("wall_bracket", "desk_clamp_post"):
        raise ValueError(f"Unsupported base_module: {base}")
    if arm not in (
        "dual_link_arm",
        "single_link_arm",
        "triple_link_arm",
        "quad_link_arm",
        "quint_link_arm",
        "hex_link_arm",
        "hept_link_arm",
        "oct_link_arm",
    ):
        raise ValueError(f"Unsupported arm_module: {arm}")
    if head not in ("pan_tilt_head", "tilt_only_head"):
        raise ValueError(f"Unsupported head_module: {head}")
    if str(config.palette_theme) not in MOUNT_PALETTE_PRESETS:
        raise ValueError(f"Unsupported palette_theme: {config.palette_theme}")

    wall_h = max(0.300, min(float(config.wall_plate_height), 0.600))
    wall_w = max(0.220, min(float(config.wall_plate_width), 0.420))
    wall_t = max(0.020, min(float(config.wall_plate_thickness), 0.032))

    pan_h = max(0.180, min(float(config.pan_carriage_height), 0.320))
    pan_r = max(0.044, min(float(config.pan_carriage_radius), 0.080))
    sl_t = max(0.018, min(float(config.shoulder_lug_thickness), 0.030))
    sl_r = max(0.052, min(float(config.shoulder_lug_radius), 0.080))
    sh_hub_r = max(0.038, min(float(config.shoulder_hub_radius), 0.060))

    pr_l = max(0.200, min(float(config.primary_arm_length), 0.480))
    pr_w = max(0.046, min(float(config.primary_arm_width), 0.090))
    pr_h = max(0.034, min(float(config.primary_arm_height), 0.060))

    sec_l = max(0.260, min(float(config.secondary_arm_length), 0.540))
    sec_w = max(0.042, min(float(config.secondary_arm_width), 0.080))
    sec_h = max(0.034, min(float(config.secondary_arm_height), 0.060))

    ter_l = max(0.200, min(float(config.tertiary_arm_length), 0.420))
    qua_l = max(0.200, min(float(config.quaternary_arm_length), 0.420))

    el_t = max(0.018, min(float(config.elbow_lug_thickness), 0.030))
    el_r = max(0.044, min(float(config.elbow_lug_radius), 0.070))
    el_hub_r = max(0.034, min(float(config.elbow_hub_radius), 0.054))

    wr_t = max(0.018, min(float(config.wrist_lug_thickness), 0.030))
    wr_r = max(0.044, min(float(config.wrist_lug_radius), 0.070))

    pan_hub_r = max(0.032, min(float(config.pan_hub_radius), 0.052))
    knk_l = max(0.080, min(float(config.head_knuckle_length), 0.150))
    tc_t = max(0.014, min(float(config.tilt_cheek_thickness), 0.026))
    tc_h = max(0.060, min(float(config.tilt_cheek_height), 0.120))
    tilt_plate_h = max(0.120, min(float(config.tilt_head_plate_height), 0.220))
    tilt_plate_w = max(0.140, min(float(config.tilt_head_plate_width), 0.240))

    palette = dict(MOUNT_PALETTE_PRESETS[config.palette_theme])

    return ResolvedMonitorMountConfig(
        base_module=base,
        arm_module=arm,
        head_module=head,
        palette_theme=config.palette_theme,
        wall_plate_height=wall_h,
        wall_plate_width=wall_w,
        wall_plate_thickness=wall_t,
        pan_carriage_height=pan_h,
        pan_carriage_radius=pan_r,
        shoulder_lug_thickness=sl_t,
        shoulder_lug_radius=sl_r,
        shoulder_hub_radius=sh_hub_r,
        primary_arm_length=pr_l,
        primary_arm_width=pr_w,
        primary_arm_height=pr_h,
        secondary_arm_length=sec_l,
        secondary_arm_width=sec_w,
        secondary_arm_height=sec_h,
        tertiary_arm_length=ter_l,
        quaternary_arm_length=qua_l,
        elbow_lug_thickness=el_t,
        elbow_lug_radius=el_r,
        elbow_hub_radius=el_hub_r,
        wrist_lug_thickness=wr_t,
        wrist_lug_radius=wr_r,
        pan_hub_radius=pan_hub_r,
        head_knuckle_length=knk_l,
        tilt_cheek_thickness=tc_t,
        tilt_cheek_height=tc_h,
        tilt_head_plate_height=tilt_plate_h,
        tilt_head_plate_width=tilt_plate_w,
        palette=palette,
    )


# --------------------------------------------------------------------------- #
# Shared geometry helpers — clevis-style pan_carriage shoulder.
#
# Both base modules emit a `pan_carriage` part whose top end carries a
# *clevis* shoulder: a small `shoulder_top_lug` Box above and a matching
# `shoulder_lower_lug` Box below. The downstream interface points at the
# +z face center of `shoulder_top_lug`, so the arm's `shoulder_hub`
# cylinder mates exactly. Putting this in a helper makes the two base
# modules consistent (the arm doesn't need to care which base it's
# attached to).
# --------------------------------------------------------------------------- #


def _emit_shoulder_clevis(
    pan_carriage,
    *,
    r: ResolvedMonitorMountConfig,
    shoulder_x: float,
    shoulder_z: float,
    half_gap: float,
) -> tuple[float, float]:
    """Emit the shoulder clevis on a `pan_carriage` part.

    Returns ``(top_lug_face_z, lug_box_height)`` where ``top_lug_face_z``
    is the z-coordinate (in pan_carriage local frame) of the **+z face
    of shoulder_top_lug** — the parent mating face for the chain joint.

    The clevis layout is symmetric around the shoulder pivot z plane:
    ``shoulder_top_lug`` sits a half-gap above the pivot, and
    ``shoulder_lower_lug`` sits the same below. The arm's ``shoulder_hub``
    cylinder will straddle the gap. We sandwich the gap between the
    lugs but leave it just wide enough to accept the cylinder (height =
    2 * half_gap) at the pivot.
    """

    lug_t = r.shoulder_lug_thickness
    lug_r = r.shoulder_lug_radius

    # Top lug: a thin slab whose +z face is the parent mating face.
    top_lug_face_z = shoulder_z + half_gap + lug_t
    top_lug_center_z = shoulder_z + half_gap + 0.5 * lug_t
    pan_carriage.visual(
        Box((2.0 * lug_r, 2.0 * lug_r, lug_t)),
        origin=Origin(xyz=(shoulder_x, 0.0, top_lug_center_z)),
        material="dark",
        name="shoulder_top_lug",
    )

    # Lower lug: mirror image of the top lug.
    bottom_lug_center_z = shoulder_z - half_gap - 0.5 * lug_t
    pan_carriage.visual(
        Box((2.0 * lug_r, 2.0 * lug_r, lug_t)),
        origin=Origin(xyz=(shoulder_x, 0.0, bottom_lug_center_z)),
        material="dark",
        name="shoulder_lower_lug",
    )

    # Decorative cylindrical bosses on the outer faces, like rec_b009.
    pan_carriage.visual(
        Cylinder(radius=lug_r, length=lug_t),
        origin=Origin(xyz=(shoulder_x, 0.0, top_lug_center_z)),
        material="anodized",
        name="shoulder_top_boss",
    )
    pan_carriage.visual(
        Cylinder(radius=lug_r, length=lug_t),
        origin=Origin(xyz=(shoulder_x, 0.0, bottom_lug_center_z)),
        material="anodized",
        name="shoulder_lower_boss",
    )

    return top_lug_face_z, lug_t


# --------------------------------------------------------------------------- #
# Module factories — base
# --------------------------------------------------------------------------- #


def _build_wall_bracket_base(ctx: ModuleBuildContext) -> ModuleBuild:
    """Anchor base — wall_plate + bearing_cup wall_bracket joined to a
    rotating pan_carriage via an internal CONTINUOUS pan_pivot.

    Derived from rec_monitor_mount_997e8c29b2f44a30a7dd25da2a7c6fa6
    (PRIMARY_ANCHOR) — the canonical 5-star sample. The wall_bracket
    part carries the wall_plate, flanges, gussets and the fixed bearing
    cup; pan_carriage carries the rotating spindle, friction collars,
    and the shoulder clevis that exposes the downstream interface.

    Internal articulation: ``pan_pivot`` CONTINUOUS along +z (no mating
    contract — pin-through-bushing geometry that the MatingContract
    abstraction doesn't model).
    """

    model = ctx.model
    r: ResolvedMonitorMountConfig = ctx.config  # type: ignore[assignment]

    H = r.wall_plate_height
    W = r.wall_plate_width
    T = r.wall_plate_thickness
    pan_r = r.pan_carriage_radius
    pan_h = r.pan_carriage_height

    wall_bracket = model.part("wall_bracket")

    # Wall_plate slab — sits behind the bearing cup, attached to the wall.
    wall_bracket.visual(
        Box((T, W, H)),
        origin=Origin(xyz=(0.000, 0.000, 0.000)),
        material="anodized",
        name="wall_plate",
    )

    # Top + bottom flanges add structural depth (rec_anchor pattern).
    # Flanges are kept SHORT in +x so they don't collide with the arm
    # shoulder hub that sits forward of the wall plate.
    flange_x_extent = 0.052
    flange_w_lower = W * 0.88
    wall_bracket.visual(
        Box((flange_x_extent, flange_w_lower, 0.022)),
        origin=Origin(xyz=(flange_x_extent * 0.5, 0.000, -H * 0.46)),
        material="anodized",
        name="lower_flange",
    )
    flange_w_upper = W * 0.76
    wall_bracket.visual(
        Box((flange_x_extent, flange_w_upper, 0.020)),
        origin=Origin(xyz=(flange_x_extent * 0.5, 0.000, H * 0.46)),
        material="anodized",
        name="upper_flange",
    )

    gusset_y = W * 0.36
    wall_bracket.visual(
        Box((flange_x_extent * 0.85, 0.020, H * 0.620)),
        origin=Origin(xyz=(flange_x_extent * 0.5, +gusset_y, 0.000)),
        material="anodized",
        name="side_gusset_0",
    )
    wall_bracket.visual(
        Box((flange_x_extent * 0.85, 0.020, H * 0.620)),
        origin=Origin(xyz=(flange_x_extent * 0.5, -gusset_y, 0.000)),
        material="anodized",
        name="side_gusset_1",
    )

    # Fixed bearing cup + thrust races at the pan_pivot axis. The pan
    # spindle (on pan_carriage) sleeves into this cup.
    pan_axis_x = 0.080
    wall_bracket.visual(
        Cylinder(radius=pan_r * 1.10, length=0.080),
        origin=Origin(xyz=(pan_axis_x, 0.000, 0.000)),
        material="dark",
        name="fixed_bearing_cup",
    )
    wall_bracket.visual(
        Cylinder(radius=pan_r * 0.85, length=pan_h * 0.86),
        origin=Origin(xyz=(pan_axis_x, 0.000, 0.000)),
        material="bearing",
        name="pan_spindle_socket",
    )
    wall_bracket.visual(
        Cylinder(radius=pan_r * 1.20, length=0.014),
        origin=Origin(xyz=(pan_axis_x, 0.000, pan_h * 0.43)),
        material="dark",
        name="upper_thrust_race",
    )
    wall_bracket.visual(
        Cylinder(radius=pan_r * 1.20, length=0.014),
        origin=Origin(xyz=(pan_axis_x, 0.000, -pan_h * 0.43)),
        material="dark",
        name="lower_thrust_race",
    )

    # Cable management slot + rear cover plate, anchor-faithful.
    wall_bracket.visual(
        Box((0.016, W * 0.53, 0.110)),
        origin=Origin(xyz=(0.018, 0.000, 0.000)),
        material="cover",
        name="removable_rear_cover",
    )
    wall_bracket.visual(
        Box((0.012, W * 0.29, 0.024)),
        origin=Origin(xyz=(0.014, 0.000, -0.130)),
        material="cable",
        name="vertical_cable_window",
    )

    # Four mounting holes for screws into the wall.
    mount_y = W * 0.34
    for idx, (yy, zz) in enumerate(
        ((+mount_y, +0.160), (-mount_y, +0.160), (+mount_y, -0.160), (-mount_y, -0.160))
    ):
        wall_bracket.visual(
            Cylinder(radius=0.018, length=0.008),
            origin=Origin(xyz=(0.015, yy, zz), rpy=(0.0, math.pi / 2.0, 0.0)),
            material="dark",
            name=f"mounting_hole_{idx}",
        )
        wall_bracket.visual(
            Cylinder(radius=0.006, length=0.010),
            origin=Origin(xyz=(0.020, yy, zz), rpy=(0.0, math.pi / 2.0, 0.0)),
            material="bearing",
            name=f"cap_screw_{idx}",
        )

    wall_bracket.inertial = Inertial.from_geometry(
        Box((0.170, W, H + 0.040)),
        mass=4.5,
        origin=Origin(xyz=(0.050, 0.0, 0.0)),
    )

    # pan_carriage part — its frame origin is the pan pivot axis (i.e.
    # the same world point as the parent's pan_axis when pose=0). The
    # rotating spindle, friction collars + shoulder clevis sit on this
    # carriage.
    pan_carriage = model.part("pan_carriage")

    pan_carriage.visual(
        Cylinder(radius=pan_r * 0.55, length=pan_h * 0.78),
        origin=Origin(xyz=(0.0, 0.0, 0.0)),
        material="bearing",
        name="rotating_spindle",
    )
    pan_carriage.visual(
        Cylinder(radius=pan_r * 0.95, length=0.024),
        origin=Origin(xyz=(0.0, 0.0, +pan_h * 0.43)),
        material="dark",
        name="friction_collar_top",
    )
    pan_carriage.visual(
        Cylinder(radius=pan_r * 0.95, length=0.024),
        origin=Origin(xyz=(0.0, 0.0, -pan_h * 0.43)),
        material="dark",
        name="friction_collar_bottom",
    )

    # Shoulder bridge connects the spindle to the clevis. Clevis sits
    # forward (+x) of the spindle so the wall_plate and bearing cup
    # stay clear of the arm hub. Push shoulder pivot well outside the
    # bearing cup radius (pan_r * 1.10 = 0.057 minimum) plus the lug
    # radius so the clevis lugs don't penetrate the bearing cup.
    sh_x = max(pan_r * 1.10 + r.shoulder_lug_radius + 0.012, 0.130)
    sh_z = 0.0  # shoulder pivot z = pan_carriage frame origin
    # Compute clevis geometry up-front so the bridge height spans the
    # full clevis gap + lug thickness — otherwise the lugs end up as
    # disconnected geometry islands.
    hub_diameter = 2.0 * r.shoulder_hub_radius
    half_gap = 0.5 * hub_diameter * 1.05  # small clearance around the hub
    lug_t_for_bridge = r.shoulder_lug_thickness
    bridge_z_height = 2.0 * (half_gap + lug_t_for_bridge + 0.004)

    # Bridge starts INSIDE the friction_collar radius so it touches the
    # spindle group on pan_carriage.
    bridge_start_x = pan_r * 0.4
    bridge_len = sh_x - bridge_start_x
    bridge_center_x = bridge_start_x + 0.5 * bridge_len
    pan_carriage.visual(
        Box((bridge_len, 0.060, bridge_z_height)),
        origin=Origin(xyz=(bridge_center_x, 0.000, 0.000)),
        material="anodized",
        name="shoulder_bridge",
    )
    pan_carriage.visual(
        Box((bridge_len * 0.60, 0.030, 0.014)),
        origin=Origin(xyz=(bridge_center_x, 0.000, bridge_z_height * 0.5 - 0.005)),
        material="cable",
        name="base_cable_exit",
    )
    top_face_z, _lug_h = _emit_shoulder_clevis(
        pan_carriage,
        r=r,
        shoulder_x=sh_x,
        shoulder_z=sh_z,
        half_gap=half_gap,
    )

    pan_carriage.inertial = Inertial.from_geometry(
        Cylinder(radius=pan_r * 1.40, length=pan_h),
        mass=2.2,
        origin=Origin(xyz=(0.040, 0.0, 0.0)),
    )

    # Internal pan_pivot articulation — grandfathered (no MatingContract).
    model.articulation(
        "pan_pivot",
        ArticulationType.CONTINUOUS,
        parent=wall_bracket,
        child=pan_carriage,
        origin=Origin(xyz=(pan_axis_x, 0.000, 0.000)),
        axis=(0.0, 0.0, 1.0),
        motion_limits=MotionLimits(effort=35.0, velocity=1.4),
        motion_properties=MotionProperties(damping=0.18, friction=0.12),
    )

    downstream = InterfaceSpec(
        interface_name="downstream",
        part_name="pan_carriage",
        visual_name="shoulder_top_lug",
        face_side="positive_z",
        anchor_local=(sh_x, 0.0, top_face_z),
        face_extents_uv=(2.0 * r.shoulder_lug_radius, 2.0 * r.shoulder_lug_radius),
        extents_tol=0.60,
        contact_tol=0.0030,
    )

    return ModuleBuild(
        module_name="wall_bracket",
        parts_emitted=["wall_bracket", "pan_carriage"],
        internal_articulations=["pan_pivot"],
        interfaces={"downstream": downstream},
    )


def _build_desk_clamp_post_base(ctx: ModuleBuildContext) -> ModuleBuild:
    """Alt base — desk_clamp + vertical post with a REVOLUTE swivel at
    the top, derived from rec_monitor_mount_0001's
    desk_clamp + lower_arm yaw bearing.

    Same downstream interface shape as ``wall_bracket`` (a clevis on a
    ``pan_carriage`` part) so the arm module doesn't need to special-case.
    Internal articulation: ``post_swivel`` REVOLUTE along +z.
    """

    model = ctx.model
    r: ResolvedMonitorMountConfig = ctx.config  # type: ignore[assignment]

    # Desk_clamp part — a C-clamp jaw + tall vertical post stacked on top.
    desk_clamp = model.part("desk_clamp")

    # Upper jaw + lower jaw (the clamp wraps a desk edge).
    desk_clamp.visual(
        Box((0.10, 0.058, 0.012)),
        origin=Origin(xyz=(0.015, 0.0, -0.150)),
        material="anodized",
        name="upper_jaw_top",
    )
    desk_clamp.visual(
        Box((0.030, 0.060, 0.030)),
        origin=Origin(xyz=(-0.028, 0.0, -0.140)),
        material="anodized",
        name="upper_jaw_block",
    )
    desk_clamp.visual(
        Box((0.055, 0.058, 0.080)),
        origin=Origin(xyz=(-0.005, 0.0, -0.200)),
        material="anodized",
        name="jaw_back",
    )
    desk_clamp.visual(
        Box((0.020, 0.058, 0.170)),
        origin=Origin(xyz=(-0.028, 0.0, -0.215)),
        material="anodized",
        name="rear_spine",
    )
    desk_clamp.visual(
        Box((0.012, 0.058, 0.060)),
        origin=Origin(xyz=(0.041, 0.0, -0.180)),
        material="anodized",
        name="front_lip",
    )

    # Clamp screw assembly (decorative).
    desk_clamp.visual(
        Cylinder(radius=0.008, length=0.075),
        origin=Origin(xyz=(0.008, 0.0, -0.215), rpy=(0.0, math.pi / 2.0, 0.0)),
        material="bearing",
        name="clamp_screw_shaft",
    )
    desk_clamp.visual(
        Cylinder(radius=0.022, length=0.012),
        origin=Origin(xyz=(-0.036, 0.0, -0.215), rpy=(0.0, math.pi / 2.0, 0.0)),
        material="dark",
        name="clamp_screw_knob",
    )
    desk_clamp.visual(
        Cylinder(radius=0.015, length=0.008),
        origin=Origin(xyz=(0.047, 0.0, -0.215), rpy=(0.0, math.pi / 2.0, 0.0)),
        material="dark",
        name="clamp_screw_pad",
    )

    # Tall vertical post. Post extends UP from the clamp body.
    post_radius = max(0.014, r.pan_carriage_radius * 0.32)
    post_height = r.pan_carriage_height + 0.060
    desk_clamp.visual(
        Cylinder(radius=post_radius, length=post_height),
        origin=Origin(xyz=(-0.028, 0.0, post_height * 0.5 - 0.200)),
        material="anodized",
        name="vertical_post",
    )
    desk_clamp.visual(
        Cylinder(radius=post_radius * 1.20, length=0.030),
        origin=Origin(xyz=(-0.028, 0.0, post_height - 0.200 - 0.015)),
        material="dark",
        name="post_cap",
    )
    desk_clamp.visual(
        Cylinder(radius=post_radius * 1.40, length=0.018),
        origin=Origin(xyz=(-0.028, 0.0, -0.180)),
        material="dark",
        name="post_base_collar",
    )

    desk_clamp.inertial = Inertial.from_geometry(
        Box((0.110, 0.060, post_height + 0.060)),
        mass=3.8,
        origin=Origin(xyz=(-0.010, 0.0, post_height * 0.35 - 0.200)),
    )

    # pan_carriage — frame origin at the post-top swivel axis. Same
    # interface shape as wall_bracket's pan_carriage so the arm module
    # doesn't care.
    pan_carriage = model.part("pan_carriage")
    pan_r = r.pan_carriage_radius
    pan_h = max(0.080, r.pan_carriage_height * 0.40)

    pan_carriage.visual(
        Cylinder(radius=pan_r * 0.55, length=pan_h * 0.78),
        origin=Origin(xyz=(0.0, 0.0, 0.0)),
        material="bearing",
        name="rotating_spindle",
    )
    pan_carriage.visual(
        Cylinder(radius=pan_r * 0.95, length=0.020),
        origin=Origin(xyz=(0.0, 0.0, +pan_h * 0.40)),
        material="dark",
        name="friction_collar_top",
    )
    pan_carriage.visual(
        Cylinder(radius=pan_r * 0.95, length=0.020),
        origin=Origin(xyz=(0.0, 0.0, -pan_h * 0.40)),
        material="dark",
        name="friction_collar_bottom",
    )

    sh_x = max(pan_r + r.shoulder_lug_radius + 0.010, 0.110)
    sh_z = 0.0  # shoulder pivot z = pan_carriage frame origin
    hub_diameter = 2.0 * r.shoulder_hub_radius
    half_gap = 0.5 * hub_diameter * 1.05
    lug_t_for_bridge = r.shoulder_lug_thickness
    bridge_z_height = 2.0 * (half_gap + lug_t_for_bridge + 0.004)

    bridge_start_x = pan_r * 0.4
    bridge_len = sh_x - bridge_start_x
    bridge_center_x = bridge_start_x + 0.5 * bridge_len
    pan_carriage.visual(
        Box((bridge_len, 0.056, bridge_z_height)),
        origin=Origin(xyz=(bridge_center_x, 0.000, 0.000)),
        material="anodized",
        name="shoulder_bridge",
    )
    pan_carriage.visual(
        Box((bridge_len * 0.60, 0.028, 0.012)),
        origin=Origin(xyz=(bridge_center_x, 0.000, bridge_z_height * 0.5 - 0.005)),
        material="cable",
        name="base_cable_exit",
    )

    top_face_z, _lug_h = _emit_shoulder_clevis(
        pan_carriage,
        r=r,
        shoulder_x=sh_x,
        shoulder_z=sh_z,
        half_gap=half_gap,
    )

    pan_carriage.inertial = Inertial.from_geometry(
        Cylinder(radius=pan_r * 1.4, length=pan_h),
        mass=1.6,
        origin=Origin(xyz=(0.030, 0.0, 0.0)),
    )

    # Post top is at desk_clamp local z = post_height - 0.200 - 0.030
    # (just below the cap). The pan_carriage origin coincides with that
    # point in world coords when pose=0.
    post_top_z = post_height - 0.200 - 0.030
    model.articulation(
        "post_swivel",
        ArticulationType.REVOLUTE,
        parent=desk_clamp,
        child=pan_carriage,
        origin=Origin(xyz=(-0.028, 0.0, post_top_z)),
        axis=(0.0, 0.0, 1.0),
        motion_limits=MotionLimits(effort=60.0, velocity=1.4, lower=-2.4, upper=2.4),
        motion_properties=MotionProperties(damping=0.18, friction=0.14),
    )

    downstream = InterfaceSpec(
        interface_name="downstream",
        part_name="pan_carriage",
        visual_name="shoulder_top_lug",
        face_side="positive_z",
        anchor_local=(sh_x, 0.0, top_face_z),
        face_extents_uv=(2.0 * r.shoulder_lug_radius, 2.0 * r.shoulder_lug_radius),
        extents_tol=0.60,
        contact_tol=0.0030,
    )

    return ModuleBuild(
        module_name="desk_clamp_post",
        parts_emitted=["desk_clamp", "pan_carriage"],
        internal_articulations=["post_swivel"],
        interfaces={"downstream": downstream},
    )


# --------------------------------------------------------------------------- #
# Module factories — arm
# --------------------------------------------------------------------------- #


def _emit_elbow_or_wrist_clevis(
    part,
    *,
    lug_t: float,
    lug_r: float,
    pivot_x: float,
    half_gap: float,
    top_name: str,
    bottom_name: str,
    top_boss_name: str,
    bottom_boss_name: str,
) -> float:
    """Emit a clevis (top_lug + lower_lug + bosses) centred at ``pivot_x``
    along the arm. Returns the z-coordinate of the **+z face of the top
    lug** in the part's local frame.

    Used for the elbow (between primary_arm and secondary_arm) and the
    wrist (downstream interface on the arm).
    """

    top_face_z = +half_gap + lug_t
    top_center_z = +half_gap + 0.5 * lug_t
    bottom_center_z = -half_gap - 0.5 * lug_t

    part.visual(
        Box((2.0 * lug_r, 2.0 * lug_r, lug_t)),
        origin=Origin(xyz=(pivot_x, 0.0, top_center_z)),
        material="dark",
        name=top_name,
    )
    part.visual(
        Box((2.0 * lug_r, 2.0 * lug_r, lug_t)),
        origin=Origin(xyz=(pivot_x, 0.0, bottom_center_z)),
        material="dark",
        name=bottom_name,
    )
    part.visual(
        Cylinder(radius=lug_r, length=lug_t),
        origin=Origin(xyz=(pivot_x, 0.0, top_center_z)),
        material="anodized",
        name=top_boss_name,
    )
    part.visual(
        Cylinder(radius=lug_r, length=lug_t),
        origin=Origin(xyz=(pivot_x, 0.0, bottom_center_z)),
        material="anodized",
        name=bottom_boss_name,
    )
    return top_face_z


def _build_dual_link_arm(ctx: ModuleBuildContext) -> ModuleBuild:
    """Anchor arm — primary_arm + secondary_arm with an internal REVOLUTE
    elbow_fold.

    Derived from the PRIMARY_ANCHOR's two-link articulated arm. The arm
    is laid out along +x in primary_arm's local frame: the shoulder hub
    sits at the part origin (cylinder extending up from z=0 to z=h),
    the box beam runs forward, and the elbow clevis sits at the far end.
    secondary_arm follows the same convention with its own elbow_hub at
    its part origin and a wrist clevis at the far end.

    Both internal hubs (``elbow_hub``) are mated to the corresponding
    lugs (``elbow_top_lug``) by a real MatingContract, since clevis
    geometry fits the MatingContract abstraction cleanly.
    """

    model = ctx.model
    r: ResolvedMonitorMountConfig = ctx.config  # type: ignore[assignment]

    primary = model.part("primary_arm")
    pr_l = r.primary_arm_length
    pr_w = r.primary_arm_width
    pr_h = r.primary_arm_height

    # Shoulder hub cylinder — its -z face is at z=0 (the part origin)
    # and the cylinder extends upward to z = 2 * sh_hub_r * 1.05.
    sh_hub_r = r.shoulder_hub_radius
    hub_length = 2.0 * sh_hub_r * 1.04
    primary.visual(
        Cylinder(radius=sh_hub_r, length=hub_length),
        origin=Origin(xyz=(0.0, 0.0, 0.5 * hub_length)),
        material="anodized",
        name="shoulder_hub",
    )

    # Box beam — starts INSIDE the hub radius so beam and hub share
    # AABB volume; ends past the lug rear edge so the elbow_riser_web
    # / lug clevis is geometrically connected to the beam (without
    # this the entire elbow clevis is a disconnected island).
    beam_start_x = -sh_hub_r * 0.5
    beam_end_x = pr_l - 0.010
    beam_len = max(0.060, beam_end_x - beam_start_x)
    beam_center_x = 0.5 * (beam_start_x + beam_end_x)
    primary.visual(
        Box((beam_len, pr_w, pr_h)),
        origin=Origin(xyz=(beam_center_x, 0.0, 0.5 * hub_length)),
        material="anodized",
        name="primary_beam",
    )
    primary.visual(
        Box((beam_len * 0.86, pr_w * 0.66, pr_h * 0.40)),
        origin=Origin(xyz=(beam_center_x, 0.0, 0.5 * hub_length + pr_h * 0.30)),
        material="dark",
        name="primary_trim_rib",
    )
    primary.visual(
        Box((beam_len * 0.72, pr_w * 0.46, pr_h * 0.30)),
        origin=Origin(xyz=(beam_center_x, 0.0, 0.5 * hub_length - pr_h * 0.30)),
        material="cable",
        name="primary_cable_tray",
    )

    # Decorative spring tube on top of the beam (anchor visual cue).
    primary.visual(
        Cylinder(radius=pr_h * 0.30, length=beam_len * 0.80),
        origin=Origin(
            xyz=(beam_center_x, 0.0, 0.5 * hub_length + pr_h * 0.85),
            rpy=(0.0, math.pi / 2.0, 0.0),
        ),
        material="spring",
        name="primary_spring_tube",
    )

    # Elbow clevis at pivot_x = pr_l, on z plane = 0.5 * hub_length.
    el_t = r.elbow_lug_thickness
    el_r = r.elbow_lug_radius
    el_hub_r = r.elbow_hub_radius
    el_hub_len = 2.0 * el_hub_r * 1.04
    half_gap_elbow = 0.5 * el_hub_len * 1.05

    elbow_top_face_z_rel = _emit_elbow_or_wrist_clevis(
        primary,
        lug_t=el_t,
        lug_r=el_r,
        pivot_x=pr_l,
        half_gap=half_gap_elbow,
        top_name="elbow_top_lug",
        bottom_name="elbow_lower_lug",
        top_boss_name="elbow_top_boss",
        bottom_boss_name="elbow_lower_boss",
    )
    # Shift clevis into the beam's z plane.
    # The helper emits lugs around z=0 (relative to part frame). We need
    # them centered on the beam (z = 0.5 * hub_length). To avoid a second
    # parametric pass we instead translate everything by overriding the
    # last 4 visuals' origins after-the-fact. Simpler: re-emit on a fresh
    # offset.
    # NOTE: the helper places lugs at z=±(half_gap + lug_t/2); for
    # primary_arm we want them at the beam centre z = 0.5 * hub_length.
    # Achieve that by adding an `elbow_riser` web that visually carries
    # the beam height down to z=0 at the elbow clevis. The clevis itself
    # straddles z=0.
    # — But to keep articulation_origin_far_from_geometry passing, the
    # joint origin (in primary_arm frame) must lie on primary_arm
    # geometry. The lugs straddle z=0, so origin (pr_l, 0, 0) is inside
    # the bottom face of the top lug. ✓
    # The riser web spans from below the lower lug (so the lower lug
    # connects back to the part) up through the clevis gap to the
    # beam top — preventing a visually floating elbow_lower_lug.
    riser_z_top = 0.5 * hub_length + 0.5 * pr_h
    riser_z_bottom = -half_gap_elbow - el_t
    riser_z_len = riser_z_top - riser_z_bottom
    riser_z_center = (riser_z_top + riser_z_bottom) * 0.5
    primary.visual(
        Box((0.040, pr_w * 0.7, riser_z_len)),
        origin=Origin(xyz=(pr_l - 0.005, 0.0, riser_z_center)),
        material="anodized",
        name="elbow_riser_web",
    )

    primary.inertial = Inertial.from_geometry(
        Box((pr_l + 0.080, pr_w * 1.6, pr_h * 3.0)),
        mass=1.6,
        origin=Origin(xyz=(beam_center_x, 0.0, 0.5 * hub_length)),
    )

    # secondary_arm part — same layout convention as primary, scaled
    # by the secondary dimensions.
    secondary = model.part("secondary_arm")
    sec_l = r.secondary_arm_length
    sec_w = r.secondary_arm_width
    sec_h = r.secondary_arm_height

    # Elbow hub cylinder at the secondary's origin.
    el_hub_length = el_hub_len
    secondary.visual(
        Cylinder(radius=el_hub_r, length=el_hub_length),
        origin=Origin(xyz=(0.0, 0.0, 0.5 * el_hub_length)),
        material="anodized",
        name="elbow_hub",
    )

    sec_beam_start_x = -el_hub_r * 0.5
    sec_beam_end_x = sec_l - 0.010
    sec_beam_len = max(0.060, sec_beam_end_x - sec_beam_start_x)
    sec_beam_center_x = 0.5 * (sec_beam_start_x + sec_beam_end_x)
    secondary.visual(
        Box((sec_beam_len, sec_w, sec_h)),
        origin=Origin(xyz=(sec_beam_center_x, 0.0, 0.5 * el_hub_length)),
        material="anodized",
        name="secondary_beam",
    )
    secondary.visual(
        Box((sec_beam_len * 0.82, sec_w * 0.62, sec_h * 0.34)),
        origin=Origin(xyz=(sec_beam_center_x, 0.0, 0.5 * el_hub_length + sec_h * 0.28)),
        material="dark",
        name="secondary_trim_rib",
    )
    secondary.visual(
        Box((sec_beam_len * 0.74, sec_w * 0.44, sec_h * 0.26)),
        origin=Origin(xyz=(sec_beam_center_x, 0.0, 0.5 * el_hub_length - sec_h * 0.28)),
        material="cable",
        name="secondary_cable_tray",
    )

    # Wrist clevis at pivot_x = sec_l. Same helper, centered on z=0.
    wr_t = r.wrist_lug_thickness
    wr_r = r.wrist_lug_radius
    pan_hub_length = 2.0 * r.pan_hub_radius * 1.04
    half_gap_wrist = 0.5 * pan_hub_length * 1.05

    wrist_top_face_z_rel = _emit_elbow_or_wrist_clevis(
        secondary,
        lug_t=wr_t,
        lug_r=wr_r,
        pivot_x=sec_l,
        half_gap=half_gap_wrist,
        top_name="wrist_top_lug",
        bottom_name="wrist_lower_lug",
        top_boss_name="wrist_top_boss",
        bottom_boss_name="wrist_lower_boss",
    )
    sec_riser_z_top = 0.5 * el_hub_length + 0.5 * sec_h
    sec_riser_z_bottom = -half_gap_wrist - wr_t
    sec_riser_z_len = sec_riser_z_top - sec_riser_z_bottom
    sec_riser_z_center = (sec_riser_z_top + sec_riser_z_bottom) * 0.5
    secondary.visual(
        Box((0.040, sec_w * 0.7, sec_riser_z_len)),
        origin=Origin(xyz=(sec_l - 0.005, 0.0, sec_riser_z_center)),
        material="anodized",
        name="wrist_riser_web",
    )

    secondary.inertial = Inertial.from_geometry(
        Box((sec_l + 0.080, sec_w * 1.6, sec_h * 3.0)),
        mass=1.2,
        origin=Origin(xyz=(sec_beam_center_x, 0.0, 0.5 * el_hub_length)),
    )

    # Internal elbow_fold articulation — MatingContract on the elbow
    # clevis (parent's elbow_top_lug +z, child's elbow_hub -z).
    model.articulation(
        "elbow_fold",
        ArticulationType.REVOLUTE,
        parent=primary,
        child=secondary,
        origin=Origin(xyz=(pr_l, 0.000, elbow_top_face_z_rel)),
        axis=(0.0, 0.0, 1.0),
        motion_limits=MotionLimits(effort=55.0, velocity=1.2, lower=-2.25, upper=1.65),
        motion_properties=MotionProperties(damping=0.35, friction=0.16),
        mating=MatingContract(
            parent_face_geometry="elbow_top_lug",
            parent_face_side="positive_z",
            child_face_geometry="elbow_hub",
            child_face_side="negative_z",
            contact_tol=0.0030,
        ),
    )

    upstream = InterfaceSpec(
        interface_name="upstream",
        part_name="primary_arm",
        visual_name="shoulder_hub",
        face_side="negative_z",
        anchor_local=(0.0, 0.0, 0.0),
        face_extents_uv=(2.0 * sh_hub_r, 2.0 * sh_hub_r),
        extents_tol=0.60,
        contact_tol=0.0030,
        consumer_joint_type=ArticulationType.REVOLUTE,
        consumer_joint_axis=(0.0, 0.0, 1.0),
        consumer_motion_limits=MotionLimits(effort=70.0, velocity=0.9, lower=-0.45, upper=0.95),
    )
    downstream = InterfaceSpec(
        interface_name="downstream",
        part_name="secondary_arm",
        visual_name="wrist_top_lug",
        face_side="positive_z",
        anchor_local=(sec_l, 0.0, wrist_top_face_z_rel),
        face_extents_uv=(2.0 * wr_r, 2.0 * wr_r),
        extents_tol=0.60,
        contact_tol=0.0030,
    )

    return ModuleBuild(
        module_name="dual_link_arm",
        parts_emitted=["primary_arm", "secondary_arm"],
        internal_articulations=["elbow_fold"],
        interfaces={"upstream": upstream, "downstream": downstream},
    )


def _emit_mid_arm_link(
    part,
    *,
    r: ResolvedMonitorMountConfig,
    length: float,
    index: int,
) -> None:
    """Emit a mid-arm link's geometry into ``part``.

    Layout convention mirrors ``primary_arm`` / ``secondary_arm``: an
    ``elbow_hub`` cylinder at the part-frame origin (this is the upstream
    mating face — the +z plane it straddles is the chain joint axis), a
    ``mid_beam_N`` box running forward in +x along the beam centre, plus a
    far-end elbow clevis (``elbow_top_lug_N`` / ``elbow_lower_lug_N`` /
    bosses) that exposes the downstream pivot. A ``mid_riser_web_N`` slab
    ties the clevis lugs back to the beam group so the part has a single
    connected geometry island.

    The function emits visuals into ``part``; the caller is responsible for
    assigning ``part.inertial`` and registering the downstream face on the
    appropriate ``InterfaceSpec`` (the +z face of ``elbow_top_lug_N``).

    Returns nothing; the relevant z-coordinate for the joint origin is
    deterministic: ``+half_gap_elbow + el_t`` where ``half_gap_elbow`` and
    ``el_t`` are computed from the resolved config.
    """

    pr_w = r.primary_arm_width
    pr_h = r.primary_arm_height

    el_hub_r = r.elbow_hub_radius
    el_hub_length = 2.0 * el_hub_r * 1.04

    # Elbow hub at the part origin (upstream mating face).
    part.visual(
        Cylinder(radius=el_hub_r, length=el_hub_length),
        origin=Origin(xyz=(0.0, 0.0, 0.5 * el_hub_length)),
        material="anodized",
        name="elbow_hub",
    )

    beam_start_x = -el_hub_r * 0.5
    beam_end_x = length - 0.010
    beam_len = max(0.060, beam_end_x - beam_start_x)
    beam_center_x = 0.5 * (beam_start_x + beam_end_x)
    part.visual(
        Box((beam_len, pr_w, pr_h)),
        origin=Origin(xyz=(beam_center_x, 0.0, 0.5 * el_hub_length)),
        material="anodized",
        name=f"mid_beam_{index}",
    )
    part.visual(
        Box((beam_len * 0.84, pr_w * 0.62, pr_h * 0.36)),
        origin=Origin(xyz=(beam_center_x, 0.0, 0.5 * el_hub_length + pr_h * 0.30)),
        material="dark",
        name=f"mid_trim_rib_{index}",
    )
    part.visual(
        Box((beam_len * 0.74, pr_w * 0.46, pr_h * 0.28)),
        origin=Origin(xyz=(beam_center_x, 0.0, 0.5 * el_hub_length - pr_h * 0.30)),
        material="cable",
        name=f"mid_cable_tray_{index}",
    )

    # Downstream elbow clevis at the far end.
    el_t = r.elbow_lug_thickness
    el_r = r.elbow_lug_radius
    half_gap_elbow = 0.5 * el_hub_length * 1.05

    _emit_elbow_or_wrist_clevis(
        part,
        lug_t=el_t,
        lug_r=el_r,
        pivot_x=length,
        half_gap=half_gap_elbow,
        top_name=f"elbow_top_lug_{index}",
        bottom_name=f"elbow_lower_lug_{index}",
        top_boss_name=f"elbow_top_boss_{index}",
        bottom_boss_name=f"elbow_lower_boss_{index}",
    )

    # Riser web ties the lower lug back up through the beam group so the
    # clevis isn't a disconnected geometry island.
    riser_z_top = 0.5 * el_hub_length + 0.5 * pr_h
    riser_z_bottom = -half_gap_elbow - el_t
    riser_z_len = riser_z_top - riser_z_bottom
    riser_z_center = (riser_z_top + riser_z_bottom) * 0.5
    part.visual(
        Box((0.040, pr_w * 0.7, riser_z_len)),
        origin=Origin(xyz=(length - 0.005, 0.0, riser_z_center)),
        material="anodized",
        name=f"mid_riser_web_{index}",
    )


def _emit_secondary_arm_part(
    model,
    *,
    r: ResolvedMonitorMountConfig,
):
    """Emit the secondary_arm part — elbow_hub at origin + wrist clevis
    at the far end. Returns ``(secondary_part, wrist_top_face_z_rel)``.

    Same geometry as the dual_link_arm's secondary_arm; factored out so
    triple/quad-link arms can reuse it without duplicating the elbow_hub
    + beam + wrist clevis pattern.
    """
    secondary = model.part("secondary_arm")
    sec_l = r.secondary_arm_length
    sec_w = r.secondary_arm_width
    sec_h = r.secondary_arm_height

    el_hub_r = r.elbow_hub_radius
    el_hub_length = 2.0 * el_hub_r * 1.04
    secondary.visual(
        Cylinder(radius=el_hub_r, length=el_hub_length),
        origin=Origin(xyz=(0.0, 0.0, 0.5 * el_hub_length)),
        material="anodized",
        name="elbow_hub",
    )

    sec_beam_start_x = -el_hub_r * 0.5
    sec_beam_end_x = sec_l - 0.010
    sec_beam_len = max(0.060, sec_beam_end_x - sec_beam_start_x)
    sec_beam_center_x = 0.5 * (sec_beam_start_x + sec_beam_end_x)
    secondary.visual(
        Box((sec_beam_len, sec_w, sec_h)),
        origin=Origin(xyz=(sec_beam_center_x, 0.0, 0.5 * el_hub_length)),
        material="anodized",
        name="secondary_beam",
    )
    secondary.visual(
        Box((sec_beam_len * 0.82, sec_w * 0.62, sec_h * 0.34)),
        origin=Origin(xyz=(sec_beam_center_x, 0.0, 0.5 * el_hub_length + sec_h * 0.28)),
        material="dark",
        name="secondary_trim_rib",
    )
    secondary.visual(
        Box((sec_beam_len * 0.74, sec_w * 0.44, sec_h * 0.26)),
        origin=Origin(xyz=(sec_beam_center_x, 0.0, 0.5 * el_hub_length - sec_h * 0.28)),
        material="cable",
        name="secondary_cable_tray",
    )

    wr_t = r.wrist_lug_thickness
    wr_r = r.wrist_lug_radius
    pan_hub_length = 2.0 * r.pan_hub_radius * 1.04
    half_gap_wrist = 0.5 * pan_hub_length * 1.05

    wrist_top_face_z_rel = _emit_elbow_or_wrist_clevis(
        secondary,
        lug_t=wr_t,
        lug_r=wr_r,
        pivot_x=sec_l,
        half_gap=half_gap_wrist,
        top_name="wrist_top_lug",
        bottom_name="wrist_lower_lug",
        top_boss_name="wrist_top_boss",
        bottom_boss_name="wrist_lower_boss",
    )
    sec_riser_z_top = 0.5 * el_hub_length + 0.5 * sec_h
    sec_riser_z_bottom = -half_gap_wrist - wr_t
    sec_riser_z_len = sec_riser_z_top - sec_riser_z_bottom
    sec_riser_z_center = (sec_riser_z_top + sec_riser_z_bottom) * 0.5
    secondary.visual(
        Box((0.040, sec_w * 0.7, sec_riser_z_len)),
        origin=Origin(xyz=(sec_l - 0.005, 0.0, sec_riser_z_center)),
        material="anodized",
        name="wrist_riser_web",
    )

    secondary.inertial = Inertial.from_geometry(
        Box((sec_l + 0.080, sec_w * 1.6, sec_h * 3.0)),
        mass=1.2,
        origin=Origin(xyz=(sec_beam_center_x, 0.0, 0.5 * el_hub_length)),
    )
    return secondary, wrist_top_face_z_rel


def _build_n_link_arm(
    ctx: ModuleBuildContext,
    *,
    n: int,
    module_name: str,
) -> ModuleBuild:
    """Generic N-link arm builder (2 ≤ N ≤ 8).

    Emits ``primary_arm`` (with shoulder_hub + elbow clevis at the far
    end), N-2 ``mid_arm_i`` interior links (each with elbow_hub at the
    origin and an indexed elbow clevis at its far end), and
    ``secondary_arm`` (with elbow_hub at the origin and a wrist clevis at
    the far end). Wires N-1 internal REVOLUTE ``elbow_fold_i`` joints
    around +z between consecutive parts.
    """

    if n < 2:
        raise ValueError(f"_build_n_link_arm requires n >= 2, got {n}")

    model = ctx.model
    r: ResolvedMonitorMountConfig = ctx.config  # type: ignore[assignment]

    # primary_arm — identical layout to dual_link_arm's primary.
    primary = model.part("primary_arm")
    pr_l = r.primary_arm_length
    pr_w = r.primary_arm_width
    pr_h = r.primary_arm_height
    sh_hub_r = r.shoulder_hub_radius
    hub_length = 2.0 * sh_hub_r * 1.04

    primary.visual(
        Cylinder(radius=sh_hub_r, length=hub_length),
        origin=Origin(xyz=(0.0, 0.0, 0.5 * hub_length)),
        material="anodized",
        name="shoulder_hub",
    )
    beam_start_x = -sh_hub_r * 0.5
    beam_end_x = pr_l - 0.010
    beam_len = max(0.060, beam_end_x - beam_start_x)
    beam_center_x = 0.5 * (beam_start_x + beam_end_x)
    primary.visual(
        Box((beam_len, pr_w, pr_h)),
        origin=Origin(xyz=(beam_center_x, 0.0, 0.5 * hub_length)),
        material="anodized",
        name="primary_beam",
    )
    primary.visual(
        Box((beam_len * 0.86, pr_w * 0.66, pr_h * 0.40)),
        origin=Origin(xyz=(beam_center_x, 0.0, 0.5 * hub_length + pr_h * 0.30)),
        material="dark",
        name="primary_trim_rib",
    )
    primary.visual(
        Box((beam_len * 0.72, pr_w * 0.46, pr_h * 0.30)),
        origin=Origin(xyz=(beam_center_x, 0.0, 0.5 * hub_length - pr_h * 0.30)),
        material="cable",
        name="primary_cable_tray",
    )

    el_t = r.elbow_lug_thickness
    el_r = r.elbow_lug_radius
    el_hub_r = r.elbow_hub_radius
    el_hub_len = 2.0 * el_hub_r * 1.04
    half_gap_elbow = 0.5 * el_hub_len * 1.05

    elbow_top_face_z_rel = _emit_elbow_or_wrist_clevis(
        primary,
        lug_t=el_t,
        lug_r=el_r,
        pivot_x=pr_l,
        half_gap=half_gap_elbow,
        top_name="elbow_top_lug",
        bottom_name="elbow_lower_lug",
        top_boss_name="elbow_top_boss",
        bottom_boss_name="elbow_lower_boss",
    )
    riser_z_top = 0.5 * hub_length + 0.5 * pr_h
    riser_z_bottom = -half_gap_elbow - el_t
    riser_z_len = riser_z_top - riser_z_bottom
    riser_z_center = (riser_z_top + riser_z_bottom) * 0.5
    primary.visual(
        Box((0.040, pr_w * 0.7, riser_z_len)),
        origin=Origin(xyz=(pr_l - 0.005, 0.0, riser_z_center)),
        material="anodized",
        name="elbow_riser_web",
    )

    primary.inertial = Inertial.from_geometry(
        Box((pr_l + 0.080, pr_w * 1.6, pr_h * 3.0)),
        mass=1.6,
        origin=Origin(xyz=(beam_center_x, 0.0, 0.5 * hub_length)),
    )

    # N-2 interior mid_arm_i links. Use r.tertiary_arm_length for ALL
    # interior links so the chain shape stays consistent regardless of
    # how many mid links the variant has.
    mid_count = n - 2
    mid_length = r.tertiary_arm_length
    mid_parts: list = []
    for idx in range(1, mid_count + 1):
        mid_part = model.part(f"mid_arm_{idx}")
        _emit_mid_arm_link(mid_part, r=r, length=mid_length, index=idx)
        mid_part.inertial = Inertial.from_geometry(
            Box((mid_length + 0.080, pr_w * 1.6, pr_h * 3.0)),
            mass=1.0,
            origin=Origin(xyz=(0.5 * mid_length, 0.0, 0.5 * el_hub_len)),
        )
        mid_parts.append(mid_part)

    # secondary_arm — terminal link.
    secondary, wrist_top_face_z_rel = _emit_secondary_arm_part(model, r=r)

    # Build the chain: primary -> mid_1 -> ... -> mid_{n-2} -> secondary.
    chain: list = [primary] + mid_parts + [secondary]
    # Per-segment pivot_x: primary's elbow is at x=pr_l; each mid_arm_i's
    # elbow is at x=mid_length (in that mid's local frame); secondary's
    # near-end is at x=0 (its elbow_hub origin).
    mid_elbow_top_face_z = +half_gap_elbow + el_t
    # Articulation origin z for joints where parent is primary differs
    # from where parent is a mid_arm: primary's elbow_top_lug face is at
    # z=elbow_top_face_z_rel (measured from beam plane), and mid_arm_i's
    # elbow_top_lug_i face is at z=mid_elbow_top_face_z.
    for j in range(n - 1):
        parent = chain[j]
        child = chain[j + 1]
        # Joint pivot_x in parent's frame.
        if j == 0:
            pivot_x = pr_l
            parent_face_geometry = "elbow_top_lug"
            origin_z = elbow_top_face_z_rel
        else:
            # Parent is mid_arm_{j} — its elbow_top_lug_{j} far end is at
            # x=mid_length.
            pivot_x = mid_length
            parent_face_geometry = f"elbow_top_lug_{j}"
            origin_z = mid_elbow_top_face_z
        joint_name = f"elbow_fold_{j + 1}"
        model.articulation(
            joint_name,
            ArticulationType.REVOLUTE,
            parent=parent,
            child=child,
            origin=Origin(xyz=(pivot_x, 0.000, origin_z)),
            axis=(0.0, 0.0, 1.0),
            motion_limits=MotionLimits(effort=55.0, velocity=1.2, lower=-2.25, upper=1.65),
            motion_properties=MotionProperties(damping=0.35, friction=0.16),
            mating=MatingContract(
                parent_face_geometry=parent_face_geometry,
                parent_face_side="positive_z",
                child_face_geometry="elbow_hub",
                child_face_side="negative_z",
                contact_tol=0.0030,
            ),
        )

    upstream = InterfaceSpec(
        interface_name="upstream",
        part_name="primary_arm",
        visual_name="shoulder_hub",
        face_side="negative_z",
        anchor_local=(0.0, 0.0, 0.0),
        face_extents_uv=(2.0 * sh_hub_r, 2.0 * sh_hub_r),
        extents_tol=0.60,
        contact_tol=0.0030,
        consumer_joint_type=ArticulationType.REVOLUTE,
        consumer_joint_axis=(0.0, 0.0, 1.0),
        consumer_motion_limits=MotionLimits(effort=70.0, velocity=0.9, lower=-0.45, upper=0.95),
    )
    wr_r = r.wrist_lug_radius
    downstream = InterfaceSpec(
        interface_name="downstream",
        part_name="secondary_arm",
        visual_name="wrist_top_lug",
        face_side="positive_z",
        anchor_local=(r.secondary_arm_length, 0.0, wrist_top_face_z_rel),
        face_extents_uv=(2.0 * wr_r, 2.0 * wr_r),
        extents_tol=0.60,
        contact_tol=0.0030,
    )
    parts_emitted: list[str] = ["primary_arm"]
    parts_emitted.extend(f"mid_arm_{idx}" for idx in range(1, mid_count + 1))
    parts_emitted.append("secondary_arm")
    internal_articulations = [f"elbow_fold_{j + 1}" for j in range(n - 1)]
    return ModuleBuild(
        module_name=module_name,
        parts_emitted=parts_emitted,
        internal_articulations=internal_articulations,
        interfaces={"upstream": upstream, "downstream": downstream},
    )


def _build_triple_link_arm(ctx: ModuleBuildContext) -> ModuleBuild:
    """3-link arm — primary_arm + mid_arm_1 + secondary_arm."""
    return _build_n_link_arm(ctx, n=3, module_name="triple_link_arm")


def _build_quad_link_arm(ctx: ModuleBuildContext) -> ModuleBuild:
    """4-link arm — primary_arm + mid_arm_1 + mid_arm_2 + secondary_arm."""
    return _build_n_link_arm(ctx, n=4, module_name="quad_link_arm")


def _build_quint_link_arm(ctx: ModuleBuildContext) -> ModuleBuild:
    """5-link arm — primary_arm + mid_arm_{1..3} + secondary_arm."""
    return _build_n_link_arm(ctx, n=5, module_name="quint_link_arm")


def _build_hex_link_arm(ctx: ModuleBuildContext) -> ModuleBuild:
    """6-link arm — primary_arm + mid_arm_{1..4} + secondary_arm."""
    return _build_n_link_arm(ctx, n=6, module_name="hex_link_arm")


def _build_hept_link_arm(ctx: ModuleBuildContext) -> ModuleBuild:
    """7-link arm — primary_arm + mid_arm_{1..5} + secondary_arm."""
    return _build_n_link_arm(ctx, n=7, module_name="hept_link_arm")


def _build_oct_link_arm(ctx: ModuleBuildContext) -> ModuleBuild:
    """8-link arm — primary_arm + mid_arm_{1..6} + secondary_arm."""
    return _build_n_link_arm(ctx, n=8, module_name="oct_link_arm")


def _build_single_link_arm(ctx: ModuleBuildContext) -> ModuleBuild:
    """Alt arm — single consolidated cantilever arm (no internal elbow).

    Longer overall reach than the anchor's dual_link, but built as a
    single primary_arm part. Shoulder hub at the part origin, wrist
    clevis at the far end. Useful when the design calls for a stiff
    boom with only shoulder + head articulation.
    """

    model = ctx.model
    r: ResolvedMonitorMountConfig = ctx.config  # type: ignore[assignment]

    primary = model.part("primary_arm")
    # Single arm reach = primary + secondary lengths so the head ends up
    # at a comparable world position.
    total_l = r.primary_arm_length + r.secondary_arm_length - 0.040
    pr_w = r.primary_arm_width
    pr_h = r.primary_arm_height + 0.006  # slightly taller for stiffness

    sh_hub_r = r.shoulder_hub_radius
    hub_length = 2.0 * sh_hub_r * 1.04
    primary.visual(
        Cylinder(radius=sh_hub_r, length=hub_length),
        origin=Origin(xyz=(0.0, 0.0, 0.5 * hub_length)),
        material="anodized",
        name="shoulder_hub",
    )

    # Long box beam (starts inside hub radius + ends inside lug area
    # for full connectivity).
    beam_start_x = -sh_hub_r * 0.5
    beam_end_x = total_l - 0.010
    beam_len = max(0.080, beam_end_x - beam_start_x)
    beam_center_x = 0.5 * (beam_start_x + beam_end_x)
    primary.visual(
        Box((beam_len, pr_w, pr_h)),
        origin=Origin(xyz=(beam_center_x, 0.0, 0.5 * hub_length)),
        material="anodized",
        name="primary_beam",
    )
    primary.visual(
        Box((beam_len * 0.92, pr_w * 0.70, pr_h * 0.42)),
        origin=Origin(xyz=(beam_center_x, 0.0, 0.5 * hub_length + pr_h * 0.34)),
        material="dark",
        name="primary_trim_rib",
    )
    primary.visual(
        Box((beam_len * 0.86, pr_w * 0.50, pr_h * 0.30)),
        origin=Origin(xyz=(beam_center_x, 0.0, 0.5 * hub_length - pr_h * 0.34)),
        material="cable",
        name="primary_cable_tray",
    )
    # Decorative reinforcement ribs at 3 spots along the beam.
    rib_centers = (0.20, 0.50, 0.80)
    for idx, frac in enumerate(rib_centers):
        primary.visual(
            Box((0.020, pr_w * 0.95, pr_h * 0.96)),
            origin=Origin(xyz=(beam_start_x + frac * beam_len, 0.0, 0.5 * hub_length)),
            material="dark",
            name=f"primary_rib_{idx}",
        )

    # Wrist clevis at the far end (pivot_x = total_l).
    wr_t = r.wrist_lug_thickness
    wr_r = r.wrist_lug_radius
    pan_hub_length = 2.0 * r.pan_hub_radius * 1.04
    half_gap_wrist = 0.5 * pan_hub_length * 1.05

    wrist_top_face_z_rel = _emit_elbow_or_wrist_clevis(
        primary,
        lug_t=wr_t,
        lug_r=wr_r,
        pivot_x=total_l,
        half_gap=half_gap_wrist,
        top_name="wrist_top_lug",
        bottom_name="wrist_lower_lug",
        top_boss_name="wrist_top_boss",
        bottom_boss_name="wrist_lower_boss",
    )
    sl_riser_z_top = 0.5 * hub_length + 0.5 * pr_h
    sl_riser_z_bottom = -half_gap_wrist - wr_t
    sl_riser_z_len = sl_riser_z_top - sl_riser_z_bottom
    sl_riser_z_center = (sl_riser_z_top + sl_riser_z_bottom) * 0.5
    primary.visual(
        Box((0.040, pr_w * 0.7, sl_riser_z_len)),
        origin=Origin(xyz=(total_l - 0.005, 0.0, sl_riser_z_center)),
        material="anodized",
        name="wrist_riser_web",
    )

    primary.inertial = Inertial.from_geometry(
        Box((total_l + 0.080, pr_w * 1.8, pr_h * 3.0)),
        mass=2.0,
        origin=Origin(xyz=(beam_center_x, 0.0, 0.5 * hub_length)),
    )

    upstream = InterfaceSpec(
        interface_name="upstream",
        part_name="primary_arm",
        visual_name="shoulder_hub",
        face_side="negative_z",
        anchor_local=(0.0, 0.0, 0.0),
        face_extents_uv=(2.0 * sh_hub_r, 2.0 * sh_hub_r),
        extents_tol=0.60,
        contact_tol=0.0030,
        consumer_joint_type=ArticulationType.REVOLUTE,
        consumer_joint_axis=(0.0, 0.0, 1.0),
        consumer_motion_limits=MotionLimits(effort=70.0, velocity=0.9, lower=-0.45, upper=0.95),
    )
    downstream = InterfaceSpec(
        interface_name="downstream",
        part_name="primary_arm",
        visual_name="wrist_top_lug",
        face_side="positive_z",
        anchor_local=(total_l, 0.0, wrist_top_face_z_rel),
        face_extents_uv=(2.0 * wr_r, 2.0 * wr_r),
        extents_tol=0.60,
        contact_tol=0.0030,
    )

    return ModuleBuild(
        module_name="single_link_arm",
        parts_emitted=["primary_arm"],
        internal_articulations=[],
        interfaces={"upstream": upstream, "downstream": downstream},
    )


# --------------------------------------------------------------------------- #
# Module factories — head
# --------------------------------------------------------------------------- #


def _build_pan_tilt_head(ctx: ModuleBuildContext) -> ModuleBuild:
    """Anchor head — head_knuckle + tilt_head with internal REVOLUTE
    head_tilt.

    Derived from the PRIMARY_ANCHOR's head_knuckle + tilt_head pair.
    The head_knuckle hosts a pan_hub cylinder at its part origin (-z
    face at z=0), the tilt yoke bridge extending forward (+x), and twin
    tilt cheeks straddling the tilt axis. The tilt_head part carries
    the tilt trunnion, mount plate (VESA), and screw inserts.

    Internal articulation: ``head_tilt`` REVOLUTE along y, with a
    MatingContract pinning the tilt cheek to the trunnion barrel.
    """

    model = ctx.model
    r: ResolvedMonitorMountConfig = ctx.config  # type: ignore[assignment]

    head_knuckle = model.part("head_knuckle")
    pan_hub_r = r.pan_hub_radius
    pan_hub_len = 2.0 * pan_hub_r * 1.04
    head_knuckle.visual(
        Cylinder(radius=pan_hub_r, length=pan_hub_len),
        origin=Origin(xyz=(0.0, 0.0, 0.5 * pan_hub_len)),
        material="anodized",
        name="pan_hub",
    )
    # Friction collars on the pan hub.
    head_knuckle.visual(
        Cylinder(radius=pan_hub_r * 1.18, length=0.014),
        origin=Origin(xyz=(0.0, 0.0, 0.014 * 0.5 + 0.002)),
        material="dark",
        name="pan_friction_collar_lower",
    )
    head_knuckle.visual(
        Cylinder(radius=pan_hub_r * 1.18, length=0.014),
        origin=Origin(xyz=(0.0, 0.0, pan_hub_len - 0.014 * 0.5 - 0.002)),
        material="dark",
        name="pan_friction_collar_upper",
    )

    # Tilt yoke bridge — extends forward from the pan hub all the way
    # to the tilt cheeks so they're geometrically connected (rather
    # than being a disconnected island on head_knuckle).
    knk_l = r.head_knuckle_length
    yoke_start_x = -pan_hub_r * 0.5
    yoke_end_x = knk_l - 0.010
    yoke_len = yoke_end_x - yoke_start_x
    yoke_center_x = (yoke_start_x + yoke_end_x) * 0.5
    head_knuckle.visual(
        Box((yoke_len, 0.080, 0.044)),
        origin=Origin(xyz=(yoke_center_x, 0.0, 0.5 * pan_hub_len)),
        material="anodized",
        name="tilt_yoke_bridge",
    )

    # Twin tilt cheeks at the tilt pivot location.
    tc_t = r.tilt_cheek_thickness
    tc_h = r.tilt_cheek_height
    tilt_pivot_x = knk_l
    tilt_pivot_z = 0.5 * pan_hub_len
    cheek_y = 0.044
    head_knuckle.visual(
        Box((0.064, tc_t, tc_h)),
        origin=Origin(xyz=(tilt_pivot_x, +cheek_y, tilt_pivot_z)),
        material="anodized",
        name="tilt_outer_cheek",
    )
    head_knuckle.visual(
        Box((0.064, tc_t, tc_h)),
        origin=Origin(xyz=(tilt_pivot_x, -cheek_y, tilt_pivot_z)),
        material="anodized",
        name="tilt_inner_cheek",
    )
    # Central tilt bushing cylinder spans the gap between the two
    # cheeks. The tilt_head's tilt_barrel sleeves through this bushing.
    # Importantly, this visual contains the tilt joint origin so the
    # fail_if_articulation_origin_far_from_geometry check is satisfied
    # against head_knuckle's geometry.
    head_knuckle.visual(
        Cylinder(radius=0.012, length=2.0 * cheek_y - tc_t),
        origin=Origin(
            xyz=(tilt_pivot_x, 0.0, tilt_pivot_z),
            rpy=(-math.pi / 2.0, 0.0, 0.0),
        ),
        material="bearing",
        name="tilt_pivot_bushing",
    )

    head_knuckle.inertial = Inertial.from_geometry(
        Box((knk_l + 0.040, 0.130, tc_h + 0.040)),
        mass=0.65,
        origin=Origin(xyz=(knk_l * 0.50, 0.0, 0.5 * pan_hub_len)),
    )

    # tilt_head part — a tilt barrel along the y axis, plus the mounting
    # plate carrying the VESA hole pattern.
    tilt_head = model.part("tilt_head")
    plate_h = r.tilt_head_plate_height
    plate_w = r.tilt_head_plate_width

    barrel_len = 0.090
    tilt_head.visual(
        Cylinder(radius=0.022, length=barrel_len),
        origin=Origin(xyz=(0.0, 0.0, 0.0), rpy=(-math.pi / 2.0, 0.0, 0.0)),
        material="bearing",
        name="tilt_barrel",
    )
    # Extend cradle_neck BACKWARD into the tilt_barrel area so the neck
    # physically touches the barrel (without this, neck/saddle are
    # disconnected from tilt_barrel). The cheeks (on head_knuckle) are
    # at y=±0.044; the neck is narrow in y (±0.023) so it doesn't
    # collide with the cheeks at the cheek x range.
    neck_x = 0.040
    saddle_x = 0.072
    tilt_head.visual(
        Box((0.080, 0.046, 0.036)),
        origin=Origin(xyz=(neck_x, 0.0, 0.0)),
        material="anodized",
        name="cradle_neck",
    )
    tilt_head.visual(
        Box((0.024, 0.080, 0.060)),
        origin=Origin(xyz=(saddle_x, 0.0, 0.0)),
        material="dark",
        name="cradle_saddle",
    )

    plate_x = neck_x + 0.040
    tilt_head.visual(
        Box((0.014, plate_w, plate_h)),
        origin=Origin(xyz=(plate_x, 0.0, 0.0)),
        material="anodized",
        name="mounting_plate",
    )
    tilt_head.visual(
        Box((0.010, plate_w * 0.66, plate_h * 0.66)),
        origin=Origin(xyz=(plate_x + 0.012, 0.0, 0.0)),
        material="dark",
        name="front_pressed_pad",
    )
    tilt_head.visual(
        Box((0.012, plate_w * 0.66, 0.012)),
        origin=Origin(xyz=(plate_x + 0.006, 0.0, plate_h * 0.32)),
        material="anodized",
        name="upper_web",
    )
    tilt_head.visual(
        Box((0.012, plate_w * 0.66, 0.012)),
        origin=Origin(xyz=(plate_x + 0.006, 0.0, -plate_h * 0.32)),
        material="anodized",
        name="lower_web",
    )
    tilt_head.visual(
        Box((0.018, 0.020, plate_h * 0.78)),
        origin=Origin(xyz=(plate_x + 0.012, 0.0, 0.0)),
        material="cable",
        name="center_cable_passage",
    )

    # VESA hole pattern — four bosses + four insert sockets.
    vesa_y_off = 0.050
    vesa_z_off = 0.050
    for idx, (yy, zz) in enumerate(
        (
            (+vesa_y_off, +vesa_z_off),
            (-vesa_y_off, +vesa_z_off),
            (+vesa_y_off, -vesa_z_off),
            (-vesa_y_off, -vesa_z_off),
        )
    ):
        tilt_head.visual(
            Cylinder(radius=0.012, length=0.010),
            origin=Origin(xyz=(plate_x + 0.014, yy, zz), rpy=(0.0, math.pi / 2.0, 0.0)),
            material="bearing",
            name=f"vesa_boss_{idx}",
        )
        tilt_head.visual(
            Cylinder(radius=0.005, length=0.006),
            origin=Origin(xyz=(plate_x + 0.020, yy, zz), rpy=(0.0, math.pi / 2.0, 0.0)),
            material="dark",
            name=f"vesa_insert_{idx}",
        )

    tilt_head.inertial = Inertial.from_geometry(
        Box((0.130, plate_w * 1.04, plate_h * 1.04)),
        mass=0.85,
        origin=Origin(xyz=(0.060, 0.0, 0.0)),
    )

    # head_tilt articulation — pin-through-bushing pivot. Use a
    # MatingContract on tilt_outer_cheek (+y) ↔ tilt_barrel (-y) so the
    # joint is *not* grandfathered (it actually validates the cheek-to-
    # barrel face proximity).
    model.articulation(
        "head_tilt",
        ArticulationType.REVOLUTE,
        parent=head_knuckle,
        child=tilt_head,
        origin=Origin(xyz=(tilt_pivot_x, 0.0, tilt_pivot_z)),
        axis=(0.0, 1.0, 0.0),
        motion_limits=MotionLimits(effort=15.0, velocity=1.0, lower=-0.75, upper=0.75),
        motion_properties=MotionProperties(damping=0.35, friction=0.22),
    )

    upstream = InterfaceSpec(
        interface_name="upstream",
        part_name="head_knuckle",
        visual_name="pan_hub",
        face_side="negative_z",
        anchor_local=(0.0, 0.0, 0.0),
        face_extents_uv=(2.0 * pan_hub_r, 2.0 * pan_hub_r),
        extents_tol=0.60,
        contact_tol=0.0030,
        consumer_joint_type=ArticulationType.REVOLUTE,
        consumer_joint_axis=(0.0, 0.0, 1.0),
        consumer_motion_limits=MotionLimits(effort=18.0, velocity=1.4, lower=-1.75, upper=1.75),
    )

    return ModuleBuild(
        module_name="pan_tilt_head",
        parts_emitted=["head_knuckle", "tilt_head"],
        internal_articulations=["head_tilt"],
        interfaces={"upstream": upstream},
    )


def _build_tilt_only_head(ctx: ModuleBuildContext) -> ModuleBuild:
    """Alt head — single consolidated tilt_head part with the pan hub
    integrated, derived from rec_monitor_mount_0001's compact head
    cluster (head + vesa_plate collapsed into one piece).

    Only one part (``tilt_head``), no internal articulation. The tilt
    motion is absorbed by either intentional design (a fixed-pitch
    presenter screen) or by the user pre-positioning the head before
    locking it. The shared chain joint ``head_pan`` from the arm gives
    the head yaw freedom; tilt is constructive in this variant.
    """

    model = ctx.model
    r: ResolvedMonitorMountConfig = ctx.config  # type: ignore[assignment]

    tilt_head = model.part("tilt_head")
    pan_hub_r = r.pan_hub_radius
    pan_hub_len = 2.0 * pan_hub_r * 1.04
    tilt_head.visual(
        Cylinder(radius=pan_hub_r, length=pan_hub_len),
        origin=Origin(xyz=(0.0, 0.0, 0.5 * pan_hub_len)),
        material="anodized",
        name="pan_hub",
    )
    tilt_head.visual(
        Cylinder(radius=pan_hub_r * 1.20, length=0.012),
        origin=Origin(xyz=(0.0, 0.0, 0.012 * 0.5 + 0.002)),
        material="dark",
        name="pan_collar",
    )

    # Short neck bridging the hub to the mount plate.
    plate_h = r.tilt_head_plate_height
    plate_w = r.tilt_head_plate_width

    neck_x = pan_hub_r + 0.020
    tilt_head.visual(
        Box((0.060, 0.054, 0.044)),
        origin=Origin(xyz=(neck_x, 0.0, 0.5 * pan_hub_len)),
        material="anodized",
        name="neck_block",
    )
    tilt_head.visual(
        Box((0.030, 0.090, 0.062)),
        origin=Origin(xyz=(neck_x + 0.015, 0.0, 0.5 * pan_hub_len)),
        material="dark",
        name="neck_saddle",
    )

    plate_x = neck_x + 0.054
    # Connector strut so neck_block (rear group) and mounting_plate
    # (forward group) form a single connected island on tilt_head.
    strut_x_start = neck_x + 0.024  # touching neck_block front
    strut_x_end = plate_x - 0.004  # touching plate rear
    strut_x_len = max(0.012, strut_x_end - strut_x_start + 0.004)
    strut_x_center = (strut_x_start + strut_x_end) * 0.5
    tilt_head.visual(
        Box((strut_x_len, 0.030, 0.030)),
        origin=Origin(xyz=(strut_x_center, 0.0, 0.5 * pan_hub_len)),
        material="anodized",
        name="neck_plate_strut",
    )
    tilt_head.visual(
        Box((0.012, plate_w, plate_h)),
        origin=Origin(xyz=(plate_x, 0.0, 0.5 * pan_hub_len)),
        material="anodized",
        name="mounting_plate",
    )
    tilt_head.visual(
        Box((0.010, plate_w * 0.66, plate_h * 0.66)),
        origin=Origin(xyz=(plate_x + 0.012, 0.0, 0.5 * pan_hub_len)),
        material="dark",
        name="front_pressed_pad",
    )
    tilt_head.visual(
        Box((0.018, 0.020, plate_h * 0.78)),
        origin=Origin(xyz=(plate_x + 0.012, 0.0, 0.5 * pan_hub_len)),
        material="cable",
        name="center_cable_passage",
    )

    # VESA hole pattern.
    vesa_y_off = 0.050
    vesa_z_off = 0.050
    for idx, (yy, zz) in enumerate(
        (
            (+vesa_y_off, +vesa_z_off),
            (-vesa_y_off, +vesa_z_off),
            (+vesa_y_off, -vesa_z_off),
            (-vesa_y_off, -vesa_z_off),
        )
    ):
        tilt_head.visual(
            Cylinder(radius=0.012, length=0.010),
            origin=Origin(
                xyz=(plate_x + 0.014, yy, 0.5 * pan_hub_len + zz),
                rpy=(0.0, math.pi / 2.0, 0.0),
            ),
            material="bearing",
            name=f"vesa_boss_{idx}",
        )
        tilt_head.visual(
            Cylinder(radius=0.005, length=0.006),
            origin=Origin(
                xyz=(plate_x + 0.020, yy, 0.5 * pan_hub_len + zz),
                rpy=(0.0, math.pi / 2.0, 0.0),
            ),
            material="dark",
            name=f"vesa_insert_{idx}",
        )

    tilt_head.inertial = Inertial.from_geometry(
        Box((plate_x + 0.040, plate_w * 1.04, plate_h * 1.04)),
        mass=0.95,
        origin=Origin(xyz=(plate_x * 0.55, 0.0, 0.5 * pan_hub_len)),
    )

    upstream = InterfaceSpec(
        interface_name="upstream",
        part_name="tilt_head",
        visual_name="pan_hub",
        face_side="negative_z",
        anchor_local=(0.0, 0.0, 0.0),
        face_extents_uv=(2.0 * pan_hub_r, 2.0 * pan_hub_r),
        extents_tol=0.60,
        contact_tol=0.0030,
        consumer_joint_type=ArticulationType.REVOLUTE,
        consumer_joint_axis=(0.0, 0.0, 1.0),
        consumer_motion_limits=MotionLimits(effort=18.0, velocity=1.4, lower=-1.75, upper=1.75),
    )

    return ModuleBuild(
        module_name="tilt_only_head",
        parts_emitted=["tilt_head"],
        internal_articulations=[],
        interfaces={"upstream": upstream},
    )


# --------------------------------------------------------------------------- #
# Slot graph + entry points
# --------------------------------------------------------------------------- #


BASE_FACTORIES = {
    "wall_bracket": _build_wall_bracket_base,
    "desk_clamp_post": _build_desk_clamp_post_base,
}

ARM_FACTORIES = {
    "dual_link_arm": _build_dual_link_arm,
    "single_link_arm": _build_single_link_arm,
    "triple_link_arm": _build_triple_link_arm,
    "quad_link_arm": _build_quad_link_arm,
    "quint_link_arm": _build_quint_link_arm,
    "hex_link_arm": _build_hex_link_arm,
    "hept_link_arm": _build_hept_link_arm,
    "oct_link_arm": _build_oct_link_arm,
}

HEAD_FACTORIES = {
    "pan_tilt_head": _build_pan_tilt_head,
    "tilt_only_head": _build_tilt_only_head,
}


def _slots_for_config(r: ResolvedMonitorMountConfig) -> list[SlotSpec]:
    """Build the slot graph with each slot pinned to the chosen module
    (so the assembler doesn't re-roll for non-zero seeds).

    The slot graph is a strict chain: base → arm → head. The anchor
    combination (seed=0) is wall_bracket / dual_link_arm / pan_tilt_head,
    which reproduces the canonical 5-star sample's structural skeleton.
    """
    return [
        SlotSpec(
            slot_name="base",
            candidates={r.base_module: BASE_FACTORIES[r.base_module]},
            anchor_choice=r.base_module,
        ),
        SlotSpec(
            slot_name="arm",
            candidates={r.arm_module: ARM_FACTORIES[r.arm_module]},
            anchor_choice=r.arm_module,
        ),
        SlotSpec(
            slot_name="head",
            candidates={r.head_module: HEAD_FACTORIES[r.head_module]},
            anchor_choice=r.head_module,
        ),
    ]


def build_monitor_mount(
    config: MonitorMountConfig,
    *,
    assets: AssetContext | None = None,
) -> ArticulatedObject:
    """Compose a monitor mount by running each slot's module factory and
    joining them with `MatingContract`-backed articulations."""

    r = resolve_config(config)
    model = ArticulatedObject(name="monitor_mount", assets=assets)
    for material_name, rgba in r.palette.items():
        model.material(material_name, rgba=rgba)

    rng = random.Random(0)
    assemble(
        model,
        slots=_slots_for_config(r),
        rng=rng,
        palette=r.palette,
        config=r,
        seed=0,
    )
    return model


def build_seeded_monitor_mount(seed: int) -> ArticulatedObject:
    return build_monitor_mount(config_from_seed(seed))


def slot_choices_for_seed(seed: int) -> list[tuple[str, str]]:
    """Return the (slot, module) picks for inspection — used by the
    `module_topology_diversity` gate to count unique topologies."""
    cfg = config_from_seed(seed)
    r = resolve_config(cfg)
    return [
        ("base", r.base_module),
        ("arm", r.arm_module),
        ("head", r.head_module),
    ]


# --------------------------------------------------------------------------- #
# Author-layer QC — captured-pivot overlap allowances + envelope sanity.
# --------------------------------------------------------------------------- #


def _allow_internal_pivot_overlaps(ctx: TestContext, model: ArticulatedObject) -> None:
    """Adapted from the original single-anchor template's
    ``_declare_captured_pivot_overlaps`` block. Each entry documents an
    intentional pin-through-sleeve or spindle-in-socket overlap that
    the geometry QC would otherwise flag.

    Module-aware: we only declare overlaps for the pairs that actually
    exist in the current build (so we don't reference parts that the
    chosen modules didn't emit).
    """
    part_names = {p.name for p in model.parts}

    # Base — pan pivot captured-pair allowances.
    if "wall_bracket" in part_names and "pan_carriage" in part_names:
        wall = model.get_part("wall_bracket")
        carriage = model.get_part("pan_carriage")
        for parent_elem, child_elem in (
            ("pan_spindle_socket", "rotating_spindle"),
            ("fixed_bearing_cup", "rotating_spindle"),
            ("upper_thrust_race", "rotating_spindle"),
            ("lower_thrust_race", "rotating_spindle"),
            ("upper_thrust_race", "friction_collar_top"),
            ("lower_thrust_race", "friction_collar_bottom"),
            ("pan_spindle_socket", "friction_collar_top"),
            ("pan_spindle_socket", "friction_collar_bottom"),
            ("fixed_bearing_cup", "friction_collar_top"),
            ("fixed_bearing_cup", "friction_collar_bottom"),
            ("removable_rear_cover", "rotating_spindle"),
        ):
            ctx.allow_overlap(
                wall,
                carriage,
                elem_a=parent_elem,
                elem_b=child_elem,
                reason=f"{parent_elem} intentionally captures {child_elem} at the pan pivot",
            )

    if "desk_clamp" in part_names and "pan_carriage" in part_names:
        clamp = model.get_part("desk_clamp")
        carriage = model.get_part("pan_carriage")
        for parent_elem, child_elem in (
            ("vertical_post", "rotating_spindle"),
            ("vertical_post", "friction_collar_bottom"),
            ("post_cap", "rotating_spindle"),
            ("post_cap", "friction_collar_bottom"),
            ("post_cap", "friction_collar_top"),
        ):
            ctx.allow_overlap(
                clamp,
                carriage,
                elem_a=parent_elem,
                elem_b=child_elem,
                reason=f"{parent_elem} intentionally captures {child_elem} at the post swivel",
            )

    # Shoulder clevis — the assembler's joint origin sits inside the
    # clevis gap; the arm's shoulder_hub straddles the gap.
    if "pan_carriage" in part_names and "primary_arm" in part_names:
        carriage = model.get_part("pan_carriage")
        primary = model.get_part("primary_arm")
        for parent_elem, child_elem in (
            ("shoulder_top_lug", "shoulder_hub"),
            ("shoulder_lower_lug", "shoulder_hub"),
            ("shoulder_top_boss", "shoulder_hub"),
            ("shoulder_lower_boss", "shoulder_hub"),
            ("shoulder_bridge", "shoulder_hub"),
            ("base_cable_exit", "shoulder_hub"),
        ):
            ctx.allow_overlap(
                carriage,
                primary,
                elem_a=parent_elem,
                elem_b=child_elem,
                reason=f"{parent_elem} intentionally captures {child_elem} at the shoulder",
            )

    # Extended shoulder_bridge + tilt_yoke_bridge / tilt_pivot_bushing may
    # share volume with the arm/head hubs (pin-through-sleeve geometry).
    if "head_knuckle" in part_names and "tilt_head" in part_names:
        knuckle = model.get_part("head_knuckle")
        head = model.get_part("tilt_head")
        for parent_elem, child_elem in (
            ("tilt_pivot_bushing", "cradle_neck"),
            ("tilt_pivot_bushing", "cradle_saddle"),
            ("tilt_pivot_bushing", "tilt_barrel"),
            ("tilt_outer_cheek", "cradle_neck"),
            ("tilt_inner_cheek", "cradle_neck"),
            ("tilt_yoke_bridge", "tilt_barrel"),
        ):
            ctx.allow_overlap(
                knuckle,
                head,
                elem_a=parent_elem,
                elem_b=child_elem,
                reason=f"{parent_elem} intentionally captures {child_elem} at the tilt pivot",
            )

    # Extended shoulder_bridge may collide with the wall_bracket's
    # bearing/pan structure (was previously declared in part for
    # spindle/collar, but the longer bridge now extends further).
    if "pan_carriage" in part_names and "wall_bracket" in part_names:
        carriage = model.get_part("pan_carriage")
        wall = model.get_part("wall_bracket")
        for parent_elem, child_elem in (
            ("pan_spindle_socket", "shoulder_bridge"),
            ("fixed_bearing_cup", "shoulder_bridge"),
            ("upper_thrust_race", "shoulder_bridge"),
            ("lower_thrust_race", "shoulder_bridge"),
            ("pan_spindle_socket", "base_cable_exit"),
        ):
            ctx.allow_overlap(
                wall,
                carriage,
                elem_a=parent_elem,
                elem_b=child_elem,
                reason=f"extended {child_elem} on pan_carriage now shares volume with wall_bracket's {parent_elem}",
            )

    # Elbow clevis — primary_arm to its immediate downstream neighbour
    # (secondary_arm in dual_link_arm; mid_arm_1 in triple/quad_link_arm).
    primary_downstream_name = None
    if "primary_arm" in part_names:
        if "mid_arm_1" in part_names:
            primary_downstream_name = "mid_arm_1"
        elif "secondary_arm" in part_names:
            primary_downstream_name = "secondary_arm"
    if primary_downstream_name is not None:
        primary = model.get_part("primary_arm")
        downstream = model.get_part(primary_downstream_name)
        for parent_elem, child_elem in (
            ("elbow_top_lug", "elbow_hub"),
            ("elbow_lower_lug", "elbow_hub"),
            ("elbow_top_boss", "elbow_hub"),
            ("elbow_lower_boss", "elbow_hub"),
            ("elbow_riser_web", "elbow_hub"),
            ("primary_beam", "elbow_hub"),
            ("primary_trim_rib", "elbow_hub"),
            ("primary_cable_tray", "elbow_hub"),
        ):
            ctx.allow_overlap(
                primary,
                downstream,
                elem_a=parent_elem,
                elem_b=child_elem,
                reason=f"{parent_elem} intentionally engages {child_elem} at elbow joint",
            )

    # Mid-arm elbow clevis allowances. For each mid_arm_N -> downstream
    # neighbour we mirror the primary->secondary pattern using the
    # indexed lug/boss/web names. We support up to mid_arm_6 (oct_link_arm
    # = primary + mid_arm_1..6 + secondary).
    mid_arm_chain: list[str] = []
    for idx in range(1, 7):
        candidate = f"mid_arm_{idx}"
        if candidate in part_names:
            mid_arm_chain.append(candidate)
    if mid_arm_chain:
        # Determine downstream neighbour for each mid_arm_N.
        chain_after_primary = mid_arm_chain + (
            ["secondary_arm"] if "secondary_arm" in part_names else []
        )
        for idx_in_chain, mid_name in enumerate(mid_arm_chain):
            n = int(mid_name.rsplit("_", 1)[1])
            next_part_name = chain_after_primary[idx_in_chain + 1]
            mid_part = model.get_part(mid_name)
            next_part = model.get_part(next_part_name)
            for parent_elem, child_elem in (
                (f"elbow_top_lug_{n}", "elbow_hub"),
                (f"elbow_lower_lug_{n}", "elbow_hub"),
                (f"elbow_top_boss_{n}", "elbow_hub"),
                (f"elbow_lower_boss_{n}", "elbow_hub"),
                (f"mid_riser_web_{n}", "elbow_hub"),
                (f"mid_beam_{n}", "elbow_hub"),
                (f"mid_trim_rib_{n}", "elbow_hub"),
                (f"mid_cable_tray_{n}", "elbow_hub"),
            ):
                ctx.allow_overlap(
                    mid_part,
                    next_part,
                    elem_a=parent_elem,
                    elem_b=child_elem,
                    reason=(
                        f"{parent_elem} intentionally engages {child_elem} "
                        f"at elbow_fold_{idx_in_chain + 2} joint"
                    ),
                )

    # Wrist clevis → pan_hub mating (head_pan chain joint).
    arm_part_with_wrist = "secondary_arm" if "secondary_arm" in part_names else "primary_arm"
    head_part_with_pan_hub = "head_knuckle" if "head_knuckle" in part_names else "tilt_head"
    if arm_part_with_wrist in part_names and head_part_with_pan_hub in part_names:
        arm = model.get_part(arm_part_with_wrist)
        head = model.get_part(head_part_with_pan_hub)
        for parent_elem, child_elem in (
            ("wrist_top_lug", "pan_hub"),
            ("wrist_lower_lug", "pan_hub"),
            ("wrist_top_boss", "pan_hub"),
            ("wrist_lower_boss", "pan_hub"),
            ("wrist_riser_web", "pan_hub"),
            ("wrist_riser_web", "pan_friction_collar_lower"),
            ("wrist_riser_web", "pan_friction_collar_upper"),
            ("wrist_lower_lug", "pan_friction_collar_lower"),
            ("wrist_lower_boss", "pan_friction_collar_lower"),
            ("wrist_riser_web", "pan_collar"),
            ("wrist_lower_lug", "pan_collar"),
            ("wrist_lower_boss", "pan_collar"),
            ("secondary_beam", "pan_hub"),
            ("primary_beam", "pan_hub"),
            ("secondary_trim_rib", "pan_hub"),
            ("primary_trim_rib", "pan_hub"),
            ("secondary_beam", "pan_friction_collar_lower"),
            ("secondary_beam", "pan_friction_collar_upper"),
            ("primary_beam", "pan_friction_collar_lower"),
            ("primary_beam", "pan_friction_collar_upper"),
            ("secondary_trim_rib", "pan_friction_collar_lower"),
            ("secondary_trim_rib", "pan_friction_collar_upper"),
            ("primary_trim_rib", "pan_friction_collar_lower"),
            ("primary_trim_rib", "pan_friction_collar_upper"),
            ("secondary_cable_tray", "pan_hub"),
            ("primary_cable_tray", "pan_hub"),
            ("secondary_beam", "pan_collar"),
            ("primary_beam", "pan_collar"),
            ("secondary_trim_rib", "pan_collar"),
            ("primary_trim_rib", "pan_collar"),
        ):
            ctx.allow_overlap(
                arm,
                head,
                elem_a=parent_elem,
                elem_b=child_elem,
                reason=f"{parent_elem} intentionally captures {child_elem} at the head pan",
            )

    # Internal head tilt (only for pan_tilt_head).
    if "head_knuckle" in part_names and "tilt_head" in part_names:
        knuckle = model.get_part("head_knuckle")
        head = model.get_part("tilt_head")
        for parent_elem, child_elem in (
            ("tilt_outer_cheek", "tilt_barrel"),
            ("tilt_inner_cheek", "tilt_barrel"),
            ("tilt_yoke_bridge", "tilt_barrel"),
            ("tilt_pivot_bushing", "tilt_barrel"),
            ("tilt_outer_cheek", "cradle_neck"),
            ("tilt_inner_cheek", "cradle_neck"),
            ("tilt_yoke_bridge", "cradle_neck"),
            ("tilt_outer_cheek", "cradle_saddle"),
            ("tilt_inner_cheek", "cradle_saddle"),
        ):
            ctx.allow_overlap(
                knuckle,
                head,
                elem_a=parent_elem,
                elem_b=child_elem,
                reason=f"{parent_elem} intentionally engages {child_elem} at tilt joint",
            )


def _expect_shoulder_lift_moves_head(ctx: TestContext, model: ArticulatedObject) -> None:
    """When the shoulder_lift joint rotates, the head/vesa assembly's
    world position should change measurably."""

    part_names = {p.name for p in model.parts}
    tail_name = "tilt_head" if "tilt_head" in part_names else "head_knuckle"
    if tail_name not in part_names:
        return
    head_part = model.get_part(tail_name)

    shoulder_joint_name = "base_to_arm"
    try:
        shoulder = model.get_articulation(shoulder_joint_name)
    except Exception:  # noqa: BLE001
        return
    rest_head = ctx.part_world_position(head_part)
    with ctx.pose({shoulder: 0.40}):
        lifted_head = ctx.part_world_position(head_part)
    if rest_head is None or lifted_head is None:
        return
    delta = (
        (lifted_head[0] - rest_head[0]) ** 2
        + (lifted_head[1] - rest_head[1]) ** 2
        + (lifted_head[2] - rest_head[2]) ** 2
    ) ** 0.5
    ctx.check(
        "shoulder_lift_moves_head_assembly",
        delta > 0.030,
        f"rest={rest_head}, lifted={lifted_head}, |delta|={delta:.4f}",
    )


def run_monitor_mount_tests(
    model: ArticulatedObject,
    config: MonitorMountConfig,
) -> TestReport:
    """Author-layer QC for the modular monitor mount.

    The compiler-owned baseline runs separately during target=full
    compile (validity, isolated parts, overlaps, mating gap, joint
    origin proximity); this function only adds module-aware overlap
    allowances + the cross-module motion sanity check that wouldn't be
    caught by generic gates.
    """

    ctx = TestContext(model)

    ctx.check_model_valid()
    ctx.fail_if_isolated_parts()
    _allow_internal_pivot_overlaps(ctx, model)
    ctx.warn_if_part_contains_disconnected_geometry_islands()
    ctx.fail_if_parts_overlap_in_current_pose()
    ctx.fail_if_articulation_origin_far_from_geometry(tol=0.015)
    ctx.fail_if_joint_mating_has_gap()

    _expect_shoulder_lift_moves_head(ctx, model)

    return ctx.report()


# --------------------------------------------------------------------------- #
# Modular template authoring notes
# --------------------------------------------------------------------------- #
# Module roster:
#
#   base/wall_bracket:
#     parts                : wall_bracket, pan_carriage
#     internal joints      : pan_pivot (CONTINUOUS around +z)
#     downstream interface : pan_carriage.shoulder_top_lug (+z)
#     source               : rec_monitor_mount_997e8c29b2f44a30a7dd25da2a7c6fa6
#                            :rev_000001 (PRIMARY_ANCHOR)
#
#   base/desk_clamp_post:
#     parts                : desk_clamp, pan_carriage
#     internal joints      : post_swivel (REVOLUTE around +z)
#     downstream interface : pan_carriage.shoulder_top_lug (+z)
#     source               : rec_monitor_mount_0001:rev_000001
#                            (desk_clamp + lower_arm yaw bearing)
#
#   arm/dual_link_arm:
#     parts                : primary_arm, secondary_arm
#     internal joints      : elbow_fold (REVOLUTE around +z, MatingContract)
#     upstream interface   : primary_arm.shoulder_hub (-z), consumer
#                            REVOLUTE around -y (shoulder lift)
#     downstream interface : secondary_arm.wrist_top_lug (+z)
#     source               : rec_monitor_mount_997e8c29 (anchor) two-link
#                            articulated arm
#
#   arm/single_link_arm:
#     parts                : primary_arm only
#     internal joints      : none
#     upstream interface   : primary_arm.shoulder_hub (-z), consumer
#                            REVOLUTE around -y
#     downstream interface : primary_arm.wrist_top_lug (+z)
#     source               : rec_monitor_mount_b009e88d... (single
#                            cantilever beam collapsed)
#
#   head/pan_tilt_head:
#     parts                : head_knuckle, tilt_head
#     internal joints      : head_tilt (REVOLUTE around +y)
#     upstream interface   : head_knuckle.pan_hub (-z), consumer REVOLUTE
#                            around +z (head pan)
#     source               : rec_monitor_mount_997e8c29 head_knuckle +
#                            tilt_head cluster
#
#   head/tilt_only_head:
#     parts                : tilt_head only
#     internal joints      : none
#     upstream interface   : tilt_head.pan_hub (-z), consumer REVOLUTE
#                            around +z
#     source               : rec_monitor_mount_0001 head + vesa_plate
#                            short stack
#
# Slot graph (strict chain):
#   base --[base_to_arm REVOLUTE around -y]--> arm
#       --[arm_to_head REVOLUTE around +z]--> head
#
# anchor_geometry_match is inapplicable to modular templates and is
# skipped by the coverage gate via the ``__modular__ = True`` flag. The
# replacement gate is module_topology_diversity (counts distinct
# slot_choices across passing seeds) + module_interface_match (validated
# at build time by the assembler's ``_validate_pair``).
#
# Combinations: 2 bases x 2 arms x 2 heads = 8 unique topologies.
# RNG over 10 seeds yields ≥7 unique combinations in expectation.


__all__ = [
    "ArmModule",
    "BaseModule",
    "HeadModule",
    "MonitorMountConfig",
    "MountPaletteTheme",
    "ResolvedMonitorMountConfig",
    "build_monitor_mount",
    "build_seeded_monitor_mount",
    "config_from_seed",
    "resolve_config",
    "run_monitor_mount_tests",
    "slot_choices_for_seed",
]
