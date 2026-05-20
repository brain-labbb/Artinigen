from __future__ import annotations

import math
import random
import tempfile
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Literal

from sdk import (
    ArticulatedObject,
    ArticulationType,
    AssetContext,
    Box,
    Cylinder,
    Mimic,
    MotionLimits,
    Origin,
    TestContext,
    TestReport,
    TorusGeometry,
    mesh_from_geometry,
)

GondolaStyle = Literal[
    "box_cabin",
    "open_basket",
    "glass_capsule",
    "bucket_seat",
    "rounded_pod",
]
SupportStyle = Literal["a_frame", "truss_tower", "inclined_legs"]
RimStyle = Literal["double_torus", "single_torus", "twin_rings"]
ScaleMode = Literal["compact", "normal", "landmark"]
BaseStyle = Literal["platform"]
HangerStyle = Literal["pivot_bar", "yoke_fork", "between_rims"]
GondolaMotionMode = Literal["free_swing", "counter_rotate_mimic"]

GONDOLA_WIDTH_Y = 0.132
GONDOLA_LOWEST_POINT_BELOW_PIVOT = 0.249
SUPPORT_RAIL_TOP_Z = 0.205
GROUND_CLEARANCE = 0.025
DEFAULT_RIM_RADIUS = 0.78
DEFAULT_WHEEL_HALF_WIDTH = 0.105
DEFAULT_AXLE_Z = (
    DEFAULT_RIM_RADIUS + GONDOLA_LOWEST_POINT_BELOW_PIVOT + SUPPORT_RAIL_TOP_Z + GROUND_CLEARANCE
)
SEED_RIM_RADIUS_MIN = DEFAULT_RIM_RADIUS
SEED_RIM_RADIUS_MAX = 1.10
SEED_COMPACT_RIM_RADIUS_MIN = 0.66
SEED_COMPACT_RIM_RADIUS_MAX = 0.90
SEED_LANDMARK_RIM_RADIUS_MIN = 1.10
SEED_LANDMARK_RIM_RADIUS_MAX = 1.65
SCALE_MODE_SEED_RANGES: dict[ScaleMode, tuple[float, float]] = {
    "compact": (SEED_COMPACT_RIM_RADIUS_MIN, SEED_COMPACT_RIM_RADIUS_MAX),
    "normal": (SEED_RIM_RADIUS_MIN, SEED_RIM_RADIUS_MAX),
    "landmark": (SEED_LANDMARK_RIM_RADIUS_MIN, SEED_LANDMARK_RIM_RADIUS_MAX),
}
SCALE_MODE_BASE_RIM_RADIUS: dict[ScaleMode, float] = {
    "compact": 0.66,
    "normal": DEFAULT_RIM_RADIUS,
    "landmark": 1.10,
}
SCALE_MODE_WHEEL_HALF_WIDTH_RANGES: dict[ScaleMode, tuple[float, float]] = {
    "compact": (0.090, 0.112),
    "normal": (0.095, 0.125),
    "landmark": (0.118, 0.155),
}


@dataclass(frozen=True)
class GondolaCollisionProfile:
    width_y: float
    lowest_point_below_pivot: float


GONDOLA_COLLISION_PROFILES: dict[GondolaStyle, GondolaCollisionProfile] = {
    "box_cabin": GondolaCollisionProfile(width_y=0.132, lowest_point_below_pivot=0.249),
    "open_basket": GondolaCollisionProfile(width_y=0.140, lowest_point_below_pivot=0.235),
    "glass_capsule": GondolaCollisionProfile(width_y=0.138, lowest_point_below_pivot=0.228),
    "bucket_seat": GondolaCollisionProfile(width_y=0.152, lowest_point_below_pivot=0.265),
    "rounded_pod": GondolaCollisionProfile(width_y=0.140, lowest_point_below_pivot=0.236),
}


@dataclass(frozen=True)
class FerrisWheelConfig:
    num_gondolas: int = 16
    spoke_count: int = 32
    gondola_style: GondolaStyle = "box_cabin"
    support_style: SupportStyle = "a_frame"
    rim_style: RimStyle = "double_torus"
    scale_mode: ScaleMode = "normal"
    base_style: BaseStyle = "platform"
    hanger_style: HangerStyle = "pivot_bar"
    gondola_motion_mode: GondolaMotionMode = "free_swing"
    railing_enabled: bool = True
    rim_radius: float | None = None
    inner_rim_radius: float | None = None
    wheel_half_width: float = DEFAULT_WHEEL_HALF_WIDTH
    axle_z: float | None = None
    name: str = "reference_ferris_wheel"


@dataclass(frozen=True)
class ResolvedFerrisWheelConfig:
    num_gondolas: int
    spoke_count: int
    gondola_style: GondolaStyle
    support_style: SupportStyle
    rim_style: RimStyle
    scale_mode: ScaleMode
    base_style: BaseStyle
    hanger_style: HangerStyle
    gondola_motion_mode: GondolaMotionMode
    railing_enabled: bool
    rim_radius: float
    inner_rim_radius: float
    wheel_half_width: float
    axle_z: float
    support_scale: float
    name: str


def config_from_seed(seed: int) -> FerrisWheelConfig:
    rng = random.Random(seed)
    num_gondolas = rng.choice(tuple(range(4, 21)))
    spoke_multiplier = rng.choice((2, 3))
    spoke_count = num_gondolas * spoke_multiplier
    if spoke_count % 2 != 0:
        spoke_count += 1
    scale_mode = rng.choices(
        ("compact", "normal", "landmark"),
        weights=(0.25, 0.55, 0.20),
        k=1,
    )[0]
    rim_min, rim_max = SCALE_MODE_SEED_RANGES[scale_mode]
    width_min, width_max = SCALE_MODE_WHEEL_HALF_WIDTH_RANGES[scale_mode]
    rim_style = rng.choice(("double_torus", "single_torus", "twin_rings"))
    if rim_style == "twin_rings":
        hanger_style: HangerStyle = rng.choice(("pivot_bar", "yoke_fork", "between_rims"))
    else:
        hanger_style = rng.choice(("pivot_bar", "yoke_fork"))
    return FerrisWheelConfig(
        num_gondolas=num_gondolas,
        spoke_count=spoke_count,
        gondola_style=rng.choice(
            ("box_cabin", "open_basket", "glass_capsule", "bucket_seat", "rounded_pod")
        ),
        support_style=rng.choice(("a_frame", "truss_tower", "inclined_legs")),
        rim_style=rim_style,
        scale_mode=scale_mode,
        base_style="platform",
        hanger_style=hanger_style,
        gondola_motion_mode=rng.choices(
            ("free_swing", "counter_rotate_mimic"), weights=(0.70, 0.30), k=1
        )[0],
        railing_enabled=(rng.random() > 0.20),
        rim_radius=round(rng.uniform(rim_min, rim_max), 3),
        wheel_half_width=round(rng.uniform(width_min, width_max), 3),
        name=f"seeded_ferris_wheel_{seed}",
    )


def gondola_collision_profile(style: GondolaStyle) -> GondolaCollisionProfile:
    return GONDOLA_COLLISION_PROFILES[style]


def support_scale_for_radius(rim_radius: float) -> float:
    return max(1.0, rim_radius / DEFAULT_RIM_RADIUS)


def hub_geometry(wheel_half_width: float) -> tuple[float, float, float, float]:
    width_ratio = wheel_half_width / DEFAULT_WHEEL_HALF_WIDTH
    return (
        2.0 * wheel_half_width * 0.96,
        wheel_half_width * 0.92,
        0.074 * width_ratio,
        0.055 * width_ratio,
    )


def resolve_config(config: FerrisWheelConfig) -> ResolvedFerrisWheelConfig:
    if config.num_gondolas < 4:
        raise ValueError("num_gondolas must be at least 4")
    if config.spoke_count < config.num_gondolas:
        raise ValueError("spoke_count should be >= num_gondolas")
    if config.gondola_style not in GONDOLA_COLLISION_PROFILES:
        raise ValueError(f"Unsupported gondola_style: {config.gondola_style}")
    if config.support_style not in {"a_frame", "truss_tower", "inclined_legs"}:
        raise ValueError(f"Unsupported support_style: {config.support_style}")
    if config.rim_style not in {"double_torus", "single_torus", "twin_rings"}:
        raise ValueError(f"Unsupported rim_style: {config.rim_style}")
    if config.scale_mode not in {"compact", "normal", "landmark"}:
        raise ValueError(f"Unsupported scale_mode: {config.scale_mode}")
    if config.base_style not in {"platform"}:
        raise ValueError(f"Unsupported base_style: {config.base_style}")
    if config.hanger_style not in {"pivot_bar", "yoke_fork", "between_rims"}:
        raise ValueError(f"Unsupported hanger_style: {config.hanger_style}")
    if config.gondola_motion_mode not in {"free_swing", "counter_rotate_mimic"}:
        raise ValueError(f"Unsupported gondola_motion_mode: {config.gondola_motion_mode}")
    if not isinstance(config.railing_enabled, bool):
        raise ValueError("railing_enabled must be a bool")
    if config.hanger_style == "between_rims" and config.rim_style != "twin_rings":
        raise ValueError("between_rims hanger_style requires rim_style='twin_rings'")

    profile = gondola_collision_profile(config.gondola_style)
    min_spacing = max(profile.width_y + 0.018, profile.lowest_point_below_pivot + 0.050)
    required_radius = min_spacing / (2.0 * math.sin(math.pi / config.num_gondolas))
    if config.rim_radius is None:
        rim_radius = max(SCALE_MODE_BASE_RIM_RADIUS[config.scale_mode], required_radius)
    else:
        rim_radius = max(config.rim_radius, required_radius)
    inner_rim_radius = (
        rim_radius * 0.74
        if config.inner_rim_radius is None
        else min(config.inner_rim_radius, rim_radius - 0.10)
    )
    scale = support_scale_for_radius(rim_radius)
    support_rail_top_z = SUPPORT_RAIL_TOP_Z * scale
    required_axle_z = (
        rim_radius + profile.lowest_point_below_pivot + support_rail_top_z + GROUND_CLEARANCE
    )
    axle_z = required_axle_z if config.axle_z is None else max(config.axle_z, required_axle_z)
    return ResolvedFerrisWheelConfig(
        num_gondolas=config.num_gondolas,
        spoke_count=config.spoke_count,
        gondola_style=config.gondola_style,
        support_style=config.support_style,
        rim_style=config.rim_style,
        scale_mode=config.scale_mode,
        base_style=config.base_style,
        hanger_style=config.hanger_style,
        gondola_motion_mode=config.gondola_motion_mode,
        railing_enabled=config.railing_enabled,
        rim_radius=rim_radius,
        inner_rim_radius=inner_rim_radius,
        wheel_half_width=config.wheel_half_width,
        axle_z=axle_z,
        support_scale=scale,
        name=config.name,
    )


def _mesh(assets: AssetContext, name: str, geometry):
    return mesh_from_geometry(geometry, assets.mesh_path(name))


def _midpoint(
    a: tuple[float, float, float], b: tuple[float, float, float]
) -> tuple[float, float, float]:
    return ((a[0] + b[0]) * 0.5, (a[1] + b[1]) * 0.5, (a[2] + b[2]) * 0.5)


def _distance(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return math.sqrt((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2 + (b[2] - a[2]) ** 2)


def _rpy_for_cylinder(
    a: tuple[float, float, float], b: tuple[float, float, float]
) -> tuple[float, float, float]:
    dx = b[0] - a[0]
    dy = b[1] - a[1]
    dz = b[2] - a[2]
    yaw = math.atan2(dy, dx)
    pitch = math.atan2(math.hypot(dx, dy), dz)
    return (0.0, pitch, yaw)


def _member(
    part,
    a: tuple[float, float, float],
    b: tuple[float, float, float],
    *,
    radius: float,
    material,
    name: str,
) -> None:
    part.visual(
        Cylinder(radius=radius, length=_distance(a, b)),
        origin=Origin(xyz=_midpoint(a, b), rpy=_rpy_for_cylinder(a, b)),
        material=material,
        name=name,
    )


def _wheel_point(radius: float, angle: float, x: float = 0.0) -> tuple[float, float, float]:
    return (x, radius * math.cos(angle), radius * math.sin(angle))


def _add_platform_railings(base, *, material, scale: float, enabled: bool) -> None:
    if not enabled:
        return
    post_positions: list[tuple[float, float]] = []
    for x in (-0.42, -0.24, 0.0, 0.24, 0.42):
        post_positions.append((x * scale, -0.34 * scale))
        post_positions.append((x * scale, 0.34 * scale))
    for y in (-0.18, 0.0, 0.18):
        post_positions.append((-0.52 * scale, y * scale))
        post_positions.append((0.52 * scale, y * scale))
    for idx, (x, y) in enumerate(post_positions):
        base.visual(
            Cylinder(radius=0.008 * scale, length=0.115 * scale),
            origin=Origin(xyz=(x, y, 0.147 * scale)),
            material=material,
            name=f"rail_post_{idx}",
        )
    for y, label in ((-0.34, "rear"), (0.34, "front")):
        for z, level in ((0.154, "lower"), (0.200, "upper")):
            base.visual(
                Box((1.08 * scale, 0.010, 0.010)),
                origin=Origin(xyz=(0.0, y * scale, z * scale)),
                material=material,
                name=f"{label}_{level}_rail",
            )
    for x, label in ((-0.52, "left"), (0.52, "right")):
        for z, level in ((0.154, "lower"), (0.200, "upper")):
            base.visual(
                Box((0.010, 0.68 * scale, 0.010)),
                origin=Origin(xyz=(x * scale, 0.0, z * scale)),
                material=material,
                name=f"{label}_{level}_rail",
            )


def _add_platform_base(support, *, material, scale: float, railing_enabled: bool) -> None:
    support.visual(
        Box((1.18 * scale, 0.82 * scale, 0.085)),
        origin=Origin(xyz=(0.0, 0.0, 0.0425 * scale)),
        material=material,
        name="platform_slab",
    )
    support.visual(
        Box((1.22 * scale, 0.045, 0.085)),
        origin=Origin(xyz=(0.0, 0.432 * scale, 0.082 * scale)),
        material=material,
        name="front_curbstone",
    )
    support.visual(
        Box((1.22 * scale, 0.045, 0.085)),
        origin=Origin(xyz=(0.0, -0.432 * scale, 0.082 * scale)),
        material=material,
        name="rear_curbstone",
    )
    _add_platform_railings(support, material=material, scale=scale, enabled=railing_enabled)


def _add_support_base(
    support,
    resolved: ResolvedFerrisWheelConfig,
    *,
    material,
) -> None:
    _add_platform_base(
        support,
        material=material,
        scale=resolved.support_scale,
        railing_enabled=resolved.railing_enabled,
    )


def _build_support_a_frame(
    support,
    resolved: ResolvedFerrisWheelConfig,
    *,
    white,
    dark,
) -> tuple[tuple[float, float, float], float]:
    scale = resolved.support_scale
    bearing_x = 0.155 * scale
    for x, label in ((-bearing_x, "left"), (bearing_x, "right")):
        support.visual(
            Box((0.038 * scale, 0.060 * scale, resolved.axle_z + 0.040 * scale)),
            origin=Origin(xyz=(x, 0.0, resolved.axle_z / 2.0 + 0.020 * scale)),
            material=white,
            name=f"{label}_hidden_core",
        )
        support.visual(
            Box((0.060 * scale, 0.070 * scale, 0.030 * scale)),
            origin=Origin(xyz=(x, 0.0, resolved.axle_z - 0.055 * scale)),
            material=white,
            name=f"{label}_bearing_web",
        )

    axle = (0.0, 0.0, resolved.axle_z)
    foot_y = 0.310 * scale
    platform_top_z = 0.085
    brace_z = 0.50 + (resolved.axle_z - DEFAULT_AXLE_Z) * 0.35
    for x, side in ((-bearing_x, "left"), (bearing_x, "right")):
        front_foot = (x, foot_y, platform_top_z)
        rear_foot = (x, -foot_y, platform_top_z)
        top = (x, 0.0, resolved.axle_z)
        _member(
            support,
            front_foot,
            top,
            radius=0.018 * scale,
            material=white,
            name=f"{side}_front_a_leg",
        )
        _member(
            support, rear_foot, top, radius=0.018 * scale, material=white, name=f"{side}_rear_a_leg"
        )
        _member(
            support,
            front_foot,
            (x, 0.0, brace_z),
            radius=0.011 * scale,
            material=white,
            name=f"{side}_front_cross",
        )
        _member(
            support,
            rear_foot,
            (x, 0.0, brace_z),
            radius=0.011 * scale,
            material=white,
            name=f"{side}_rear_cross",
        )
        _member(
            support,
            (x, foot_y * 0.55, brace_z - 0.12 * scale),
            (x, -foot_y * 0.55, brace_z - 0.12 * scale),
            radius=0.010 * scale,
            material=white,
            name=f"{side}_mid_spreader",
        )
        support.visual(
            Box((0.078 * scale, 0.096 * scale, 0.092 * scale)),
            origin=Origin(xyz=(x, 0.0, resolved.axle_z)),
            material=dark,
            name=f"{side}_bearing_block",
        )
    _member(
        support,
        (-bearing_x, 0.0, resolved.axle_z),
        (bearing_x, 0.0, resolved.axle_z),
        radius=0.020 * scale,
        material=dark,
        name="fixed_axle",
    )
    return axle, bearing_x


def _build_support_truss_tower(
    support,
    resolved: ResolvedFerrisWheelConfig,
    *,
    white,
    dark,
) -> tuple[tuple[float, float, float], float]:
    scale = resolved.support_scale
    bearing_x = 0.155 * scale
    platform_top_z = 0.085
    tower_inset_y = 0.260 * scale
    crown_z = resolved.axle_z - 0.030 * scale
    mid_z = platform_top_z + (crown_z - platform_top_z) * 0.52

    for x, side in ((-bearing_x, "left"), (bearing_x, "right")):
        support.visual(
            Box((0.038 * scale, 0.060 * scale, resolved.axle_z + 0.040 * scale)),
            origin=Origin(xyz=(x, 0.0, resolved.axle_z / 2.0 + 0.020 * scale)),
            material=white,
            name=f"{side}_hidden_core",
        )
        support.visual(
            Box((0.060 * scale, 0.070 * scale, 0.030 * scale)),
            origin=Origin(xyz=(x, 0.0, resolved.axle_z - 0.055 * scale)),
            material=white,
            name=f"{side}_bearing_web",
        )
        _member(
            support,
            (x, 0.0, platform_top_z),
            (x, 0.0, resolved.axle_z),
            radius=0.020 * scale,
            material=white,
            name=f"{side}_center_tower_post",
        )
        for y, label in ((tower_inset_y, "front"), (-tower_inset_y, "rear")):
            _member(
                support,
                (x, y, platform_top_z),
                (x, y, crown_z),
                radius=0.014 * scale,
                material=white,
                name=f"{side}_{label}_tower_post",
            )
            _member(
                support,
                (x, y, mid_z),
                (x, 0.0, mid_z),
                radius=0.010 * scale,
                material=white,
                name=f"{side}_{label}_diagonal_brace",
            )
        _member(
            support,
            (x, tower_inset_y, crown_z),
            (x, -tower_inset_y, crown_z),
            radius=0.012 * scale,
            material=white,
            name=f"{side}_tower_spreader",
        )
        _member(
            support,
            (x, tower_inset_y, platform_top_z + 0.10 * scale),
            (x, -tower_inset_y, platform_top_z + 0.10 * scale),
            radius=0.010 * scale,
            material=white,
            name=f"{side}_base_spreader",
        )
        _member(
            support,
            (x, 0.0, crown_z),
            (x, 0.0, resolved.axle_z),
            radius=0.014 * scale,
            material=white,
            name=f"{side}_center_crown_strut",
        )
        support.visual(
            Box((0.078 * scale, 0.120 * scale, 0.092 * scale)),
            origin=Origin(xyz=(x, 0.0, resolved.axle_z)),
            material=dark,
            name=f"{side}_bearing_block",
        )
    _member(
        support,
        (-bearing_x, 0.0, resolved.axle_z),
        (bearing_x, 0.0, resolved.axle_z),
        radius=0.020 * scale,
        material=dark,
        name="fixed_axle",
    )
    return (0.0, 0.0, resolved.axle_z), bearing_x


def _build_support_inclined_legs(
    support,
    resolved: ResolvedFerrisWheelConfig,
    *,
    white,
    dark,
) -> tuple[tuple[float, float, float], float]:
    scale = resolved.support_scale
    bearing_x = 0.155 * scale
    platform_top_z = 0.085
    foot_y = 0.335 * scale
    axle = (0.0, 0.0, resolved.axle_z)
    shoulder_z = resolved.axle_z * 0.76

    for x, side in ((-bearing_x, "left"), (bearing_x, "right")):
        support.visual(
            Box((0.038 * scale, 0.060 * scale, resolved.axle_z + 0.040 * scale)),
            origin=Origin(xyz=(x, 0.0, resolved.axle_z / 2.0 + 0.020 * scale)),
            material=white,
            name=f"{side}_hidden_core",
        )
        support.visual(
            Box((0.060 * scale, 0.070 * scale, 0.030 * scale)),
            origin=Origin(xyz=(x, 0.0, resolved.axle_z - 0.055 * scale)),
            material=white,
            name=f"{side}_bearing_web",
        )
        front_foot = (x, foot_y, platform_top_z)
        rear_foot = (x, -foot_y, platform_top_z)
        top = (x, 0.0, resolved.axle_z)
        shoulder_front = (x, foot_y * 0.36, shoulder_z)
        shoulder_rear = (x, -foot_y * 0.36, shoulder_z)
        _member(
            support,
            front_foot,
            top,
            radius=0.018 * scale,
            material=white,
            name=f"{side}_front_inclined_leg",
        )
        _member(
            support,
            rear_foot,
            top,
            radius=0.018 * scale,
            material=white,
            name=f"{side}_rear_inclined_leg",
        )
        _member(
            support,
            front_foot,
            shoulder_rear,
            radius=0.010 * scale,
            material=white,
            name=f"{side}_cross_diagonal_a",
        )
        _member(
            support,
            rear_foot,
            shoulder_front,
            radius=0.010 * scale,
            material=white,
            name=f"{side}_cross_diagonal_b",
        )
        _member(
            support,
            shoulder_front,
            shoulder_rear,
            radius=0.011 * scale,
            material=white,
            name=f"{side}_shoulder_spreader",
        )
        support.visual(
            Box((0.082 * scale, 0.110 * scale, 0.092 * scale)),
            origin=Origin(xyz=(x, 0.0, resolved.axle_z)),
            material=dark,
            name=f"{side}_bearing_block",
        )
    _member(
        support,
        (-bearing_x, 0.0, resolved.axle_z),
        (bearing_x, 0.0, resolved.axle_z),
        radius=0.020 * scale,
        material=dark,
        name="fixed_axle",
    )
    return axle, bearing_x


SUPPORT_STYLE_BUILDERS = {
    "a_frame": _build_support_a_frame,
    "truss_tower": _build_support_truss_tower,
    "inclined_legs": _build_support_inclined_legs,
}


def add_gondola_box_cabin(gondola, *, body_mat, trim_mat, glass_mat, index: int) -> None:
    """Default enclosed cabin style. Origin is the hanger pivot."""
    gondola.visual(
        Cylinder(radius=0.010, length=0.145),
        origin=Origin(rpy=(0.0, math.pi / 2.0, 0.0)),
        material=trim_mat,
        name="hanger_pin",
    )
    for x, label in ((-0.052, "rear"), (0.052, "front")):
        gondola.visual(
            Box((0.010, 0.012, 0.155)),
            origin=Origin(xyz=(x, 0.0, -0.077)),
            material=trim_mat,
            name=f"hanger_{label}",
        )
    gondola.visual(
        Box((0.112, 0.118, 0.100)),
        origin=Origin(xyz=(0.0, 0.0, -0.177)),
        material=body_mat,
        name="cabin_body",
    )
    gondola.visual(
        Box((0.126, 0.128, 0.026)),
        origin=Origin(xyz=(0.0, 0.0, -0.107)),
        material=trim_mat,
        name="cabin_roof",
    )
    gondola.visual(
        Box((0.130, 0.132, 0.022)),
        origin=Origin(xyz=(0.0, 0.0, -0.238)),
        material=trim_mat,
        name="cabin_floor",
    )
    for y, label in ((-0.062, "rear"), (0.062, "front")):
        gondola.visual(
            Box((0.038, 0.006, 0.052)),
            origin=Origin(xyz=(-0.028, y, -0.158)),
            material=glass_mat,
            name=f"{label}_window_left",
        )
        gondola.visual(
            Box((0.038, 0.006, 0.052)),
            origin=Origin(xyz=(0.028, y, -0.158)),
            material=glass_mat,
            name=f"{label}_window_right",
        )
        gondola.visual(
            Box((0.006, 0.008, 0.068)),
            origin=Origin(xyz=(0.0, y, -0.158)),
            material=trim_mat,
            name=f"{label}_center_mullion",
        )
    gondola.visual(
        Box((0.130, 0.012, 0.016)),
        origin=Origin(xyz=(0.0, 0.059, -0.214)),
        material=trim_mat,
        name="front_guard_bar",
    )
    gondola.visual(
        Box((0.130, 0.012, 0.016)),
        origin=Origin(xyz=(0.0, -0.059, -0.214)),
        material=trim_mat,
        name="rear_guard_bar",
    )


def add_gondola_open_basket(gondola, *, body_mat, trim_mat, glass_mat, index: int) -> None:
    """Open basket style: low floor, railings, and benches instead of a closed cabin."""
    gondola.visual(
        Cylinder(radius=0.010, length=0.145),
        origin=Origin(rpy=(0.0, math.pi / 2.0, 0.0)),
        material=trim_mat,
        name="hanger_pin",
    )
    for x, label in ((-0.052, "rear"), (0.052, "front")):
        gondola.visual(
            Box((0.010, 0.012, 0.198)),
            origin=Origin(xyz=(x, 0.0, -0.099)),
            material=trim_mat,
            name=f"hanger_{label}",
        )
    for x, side in ((-0.052, "rear"), (0.052, "front")):
        for y, face in ((0.034, "front"), (-0.034, "rear")):
            gondola.visual(
                Box((0.008, 0.070, 0.012)),
                origin=Origin(xyz=(x, y, -0.150)),
                material=trim_mat,
                name=f"{side}_{face}_top_spreader",
            )
    gondola.visual(
        Box((0.140, 0.136, 0.022)),
        origin=Origin(xyz=(0.0, 0.0, -0.230)),
        material=body_mat,
        name="basket_floor",
    )
    for y, label in ((0.064, "front"), (-0.064, "rear")):
        gondola.visual(
            Box((0.138, 0.010, 0.016)),
            origin=Origin(xyz=(0.0, y, -0.176)),
            material=trim_mat,
            name=f"{label}_top_rail",
        )
        gondola.visual(
            Box((0.138, 0.010, 0.014)),
            origin=Origin(xyz=(0.0, y, -0.208)),
            material=trim_mat,
            name=f"{label}_lower_rail",
        )
    for x, label in ((-0.064, "rear"), (0.064, "front")):
        gondola.visual(
            Box((0.010, 0.126, 0.016)),
            origin=Origin(xyz=(x, 0.0, -0.176)),
            material=trim_mat,
            name=f"{label}_side_rail",
        )
    for x, side in ((-0.052, "rear"), (0.052, "front")):
        for y, face in ((0.058, "front"), (-0.058, "rear")):
            gondola.visual(
                Box((0.008, 0.008, 0.088)),
                origin=Origin(xyz=(x, y, -0.186)),
                material=trim_mat,
                name=f"{side}_{face}_hanger_leg",
            )
    for x in (-0.046, 0.046):
        for y, label in ((0.064, "front"), (-0.064, "rear")):
            gondola.visual(
                Box((0.008, 0.010, 0.065)),
                origin=Origin(xyz=(x, y, -0.204)),
                material=trim_mat,
                name=f"{label}_stanchion_{'left' if x < 0 else 'right'}",
            )
    for y, label in ((0.030, "front"), (-0.030, "rear")):
        gondola.visual(
            Box((0.104, 0.020, 0.018)),
            origin=Origin(xyz=(0.0, y, -0.196)),
            material=body_mat,
            name=f"{label}_bench",
        )
        for x, side in ((-0.040, "left"), (0.040, "right")):
            gondola.visual(
                Box((0.010, 0.010, 0.046)),
                origin=Origin(xyz=(x, y, -0.220)),
                material=trim_mat,
                name=f"{label}_{side}_bench_leg",
            )


def add_gondola_glass_capsule(gondola, *, body_mat, trim_mat, glass_mat, index: int) -> None:
    """Transparent capsule style with a larger panoramic shell and rounded end caps."""
    gondola.visual(
        Cylinder(radius=0.010, length=0.145),
        origin=Origin(rpy=(0.0, math.pi / 2.0, 0.0)),
        material=trim_mat,
        name="hanger_pin",
    )
    for x, label in ((-0.052, "rear"), (0.052, "front")):
        gondola.visual(
            Box((0.010, 0.012, 0.132)),
            origin=Origin(xyz=(x, 0.0, -0.066)),
            material=trim_mat,
            name=f"hanger_{label}",
        )
    gondola.visual(
        Box((0.120, 0.104, 0.058)),
        origin=Origin(xyz=(0.0, 0.0, -0.168)),
        material=glass_mat,
        name="panoramic_glass_shell",
    )
    gondola.visual(
        Cylinder(radius=0.052, length=0.010),
        origin=Origin(xyz=(-0.064, 0.0, -0.168), rpy=(0.0, math.pi / 2.0, 0.0)),
        material=glass_mat,
        name="rear_round_end",
    )
    gondola.visual(
        Cylinder(radius=0.052, length=0.010),
        origin=Origin(xyz=(0.064, 0.0, -0.168), rpy=(0.0, math.pi / 2.0, 0.0)),
        material=glass_mat,
        name="front_round_end",
    )
    gondola.visual(
        Box((0.138, 0.126, 0.018)),
        origin=Origin(xyz=(0.0, 0.0, -0.226)),
        material=trim_mat,
        name="capsule_floor_ring",
    )
    gondola.visual(
        Box((0.132, 0.118, 0.014)),
        origin=Origin(xyz=(0.0, 0.0, -0.118)),
        material=trim_mat,
        name="capsule_roof_frame",
    )
    for x, label in ((-0.064, "rear"), (0.064, "front")):
        gondola.visual(
            Cylinder(radius=0.056, length=0.006),
            origin=Origin(xyz=(x, 0.0, -0.168), rpy=(0.0, math.pi / 2.0, 0.0)),
            material=trim_mat,
            name=f"{label}_end_frame",
        )
    for y, label in ((0.056, "front"), (-0.056, "rear")):
        gondola.visual(
            Box((0.126, 0.008, 0.012)),
            origin=Origin(xyz=(0.0, y, -0.126)),
            material=trim_mat,
            name=f"{label}_upper_window_frame",
        )
        gondola.visual(
            Box((0.126, 0.008, 0.012)),
            origin=Origin(xyz=(0.0, y, -0.212)),
            material=trim_mat,
            name=f"{label}_lower_window_frame",
        )
        for x, side in ((-0.040, "left"), (0.040, "right")):
            gondola.visual(
                Box((0.006, 0.008, 0.088)),
                origin=Origin(xyz=(x, y, -0.168)),
                material=trim_mat,
                name=f"{label}_{side}_mullion",
            )
    for x, side in ((-0.050, "rear"), (0.050, "front")):
        gondola.visual(
            Box((0.010, 0.112, 0.010)),
            origin=Origin(xyz=(x, 0.0, -0.112)),
            material=trim_mat,
            name=f"{side}_yoke_crossbar",
        )
        for y, face in ((0.052, "front"), (-0.052, "rear")):
            gondola.visual(
                Box((0.010, 0.010, 0.090)),
                origin=Origin(xyz=(x, y, -0.154)),
                material=trim_mat,
                name=f"{side}_{face}_yoke_leg",
            )
    gondola.visual(
        Box((0.092, 0.024, 0.018)),
        origin=Origin(xyz=(0.0, 0.0, -0.200)),
        material=body_mat,
        name="center_bench",
    )
    for x, side in ((-0.032, "left"), (0.032, "right")):
        gondola.visual(
            Box((0.008, 0.010, 0.044)),
            origin=Origin(xyz=(x, 0.0, -0.222)),
            material=trim_mat,
            name=f"{side}_bench_leg",
        )


def add_gondola_bucket_seat(gondola, *, body_mat, trim_mat, glass_mat, index: int) -> None:
    """Open bucket seat adapted from high-quality fairground wheel samples."""
    gondola.visual(
        Cylinder(radius=0.010, length=0.145),
        origin=Origin(rpy=(0.0, math.pi / 2.0, 0.0)),
        material=trim_mat,
        name="hanger_pin",
    )
    for x, label in ((-0.056, "rear"), (0.056, "front")):
        gondola.visual(
            Box((0.010, 0.012, 0.178)),
            origin=Origin(xyz=(x, 0.0, -0.088)),
            material=trim_mat,
            name=f"hanger_{label}",
        )
    gondola.visual(
        Box((0.156, 0.146, 0.024)),
        origin=Origin(xyz=(0.0, 0.0, -0.250)),
        material=body_mat,
        name="bucket_floor",
    )
    gondola.visual(
        Box((0.042, 0.140, 0.088)),
        origin=Origin(xyz=(-0.074, 0.0, -0.206)),
        material=body_mat,
        name="bucket_back",
    )
    gondola.visual(
        Box((0.038, 0.140, 0.070)),
        origin=Origin(xyz=(0.074, 0.0, -0.214)),
        material=body_mat,
        name="bucket_front_lip",
    )
    for y, label in ((-0.068, "rear"), (0.068, "front")):
        gondola.visual(
            Box((0.136, 0.010, 0.062)),
            origin=Origin(xyz=(0.0, y, -0.212)),
            material=trim_mat,
            name=f"{label}_bucket_side",
        )
    gondola.visual(
        Box((0.122, 0.010, 0.014)),
        origin=Origin(xyz=(0.0, 0.0, -0.168)),
        material=trim_mat,
        name="safety_bar",
    )
    for x, side in ((-0.030, "left"), (0.030, "right")):
        gondola.visual(
            Box((0.008, 0.012, 0.044)),
            origin=Origin(xyz=(x, 0.0, -0.188)),
            material=trim_mat,
            name=f"{side}_safety_bar_stanchion",
        )


def add_gondola_rounded_pod(gondola, *, body_mat, trim_mat, glass_mat, index: int) -> None:
    """Rounded pod inspired by robust capsule/pod wheel records."""
    gondola.visual(
        Cylinder(radius=0.010, length=0.145),
        origin=Origin(rpy=(0.0, math.pi / 2.0, 0.0)),
        material=trim_mat,
        name="hanger_pin",
    )
    for x, label in ((-0.052, "rear"), (0.052, "front")):
        gondola.visual(
            Box((0.010, 0.012, 0.142)),
            origin=Origin(xyz=(x, 0.0, -0.071)),
            material=trim_mat,
            name=f"hanger_{label}",
        )
    gondola.visual(
        Cylinder(radius=0.060, length=0.114),
        origin=Origin(xyz=(0.0, 0.0, -0.165), rpy=(0.0, math.pi / 2.0, 0.0)),
        material=body_mat,
        name="pod_shell",
    )
    gondola.visual(
        Cylinder(radius=0.060, length=0.008),
        origin=Origin(xyz=(-0.061, 0.0, -0.165), rpy=(0.0, math.pi / 2.0, 0.0)),
        material=trim_mat,
        name="rear_pod_endcap",
    )
    gondola.visual(
        Cylinder(radius=0.060, length=0.008),
        origin=Origin(xyz=(0.061, 0.0, -0.165), rpy=(0.0, math.pi / 2.0, 0.0)),
        material=trim_mat,
        name="front_pod_endcap",
    )
    gondola.visual(
        Box((0.130, 0.116, 0.020)),
        origin=Origin(xyz=(0.0, 0.0, -0.230)),
        material=trim_mat,
        name="pod_floor_ring",
    )
    for y, label in ((0.056, "front"), (-0.056, "rear")):
        gondola.visual(
            Box((0.120, 0.006, 0.060)),
            origin=Origin(xyz=(0.0, y, -0.168)),
            material=glass_mat,
            name=f"{label}_pod_glass",
        )
    gondola.visual(
        Box((0.084, 0.020, 0.018)),
        origin=Origin(xyz=(0.0, 0.0, -0.206)),
        material=body_mat,
        name="pod_bench",
    )


GONDOLA_STYLE_BUILDERS = {
    "box_cabin": add_gondola_box_cabin,
    "open_basket": add_gondola_open_basket,
    "glass_capsule": add_gondola_glass_capsule,
    "bucket_seat": add_gondola_bucket_seat,
    "rounded_pod": add_gondola_rounded_pod,
}


def _add_twin_ring_rim(wheel, resolved: ResolvedFerrisWheelConfig, *, white) -> None:
    segs = max(20, resolved.spoke_count)
    inner_radius = max(resolved.rim_radius * 0.86, resolved.rim_radius - 0.12)
    for i in range(segs):
        a0 = 2.0 * math.pi * i / segs
        a1 = 2.0 * math.pi * ((i + 1) % segs) / segs
        for x, side in ((-resolved.wheel_half_width, "left"), (resolved.wheel_half_width, "right")):
            _member(
                wheel,
                _wheel_point(resolved.rim_radius, a0, x),
                _wheel_point(resolved.rim_radius, a1, x),
                radius=0.012,
                material=white,
                name=f"{side}_outer_rim_segment_{i}",
            )
            _member(
                wheel,
                _wheel_point(inner_radius, a0, x),
                _wheel_point(inner_radius, a1, x),
                radius=0.0085,
                material=white,
                name=f"{side}_inner_rim_segment_{i}",
            )
    for i in range(resolved.num_gondolas):
        angle = (2.0 * math.pi * i) / resolved.num_gondolas
        p0 = _wheel_point(resolved.rim_radius, angle, -resolved.wheel_half_width)
        p1 = _wheel_point(resolved.rim_radius, angle, resolved.wheel_half_width)
        _member(
            wheel,
            p0,
            p1,
            radius=0.0075,
            material=white,
            name=f"rim_bridge_{i}",
        )


def _gondola_pivot_radius(resolved: ResolvedFerrisWheelConfig) -> float:
    if resolved.hanger_style == "between_rims":
        return max(resolved.rim_radius * 0.86, resolved.rim_radius - 0.12)
    if resolved.hanger_style == "yoke_fork":
        return resolved.rim_radius - 0.018
    return resolved.rim_radius


def _add_gondola_mounting(
    wheel,
    resolved: ResolvedFerrisWheelConfig,
    *,
    angle: float,
    index: int,
    white,
    dark,
) -> tuple[float, float, float]:
    pivot_radius = _gondola_pivot_radius(resolved)
    p0 = _wheel_point(pivot_radius, angle, -resolved.wheel_half_width)
    p1 = _wheel_point(pivot_radius, angle, resolved.wheel_half_width)
    anchor_name = f"gondola_pivot_bar_{index}"

    if resolved.hanger_style == "pivot_bar":
        _member(wheel, p0, p1, radius=0.008, material=white, name=anchor_name)
    elif resolved.hanger_style == "yoke_fork":
        _member(wheel, p0, p1, radius=0.0072, material=white, name=anchor_name)
        for point, side in ((p0, "rear"), (p1, "front")):
            wheel.visual(
                Box((0.028, 0.014, 0.060)),
                origin=Origin(
                    xyz=(point[0], point[1] * 0.996, point[2] * 0.996),
                    rpy=(0.0, 0.0, math.atan2(point[2], point[1])),
                ),
                material=dark,
                name=f"{side}_fork_cheek_{index}",
            )
    else:
        outer0 = _wheel_point(resolved.rim_radius, angle, -resolved.wheel_half_width)
        outer1 = _wheel_point(resolved.rim_radius, angle, resolved.wheel_half_width)
        _member(wheel, p0, p1, radius=0.0070, material=white, name=anchor_name)
        _member(wheel, outer0, p0, radius=0.0060, material=white, name=f"rear_hanger_strut_{index}")
        _member(
            wheel,
            outer1,
            p1,
            radius=0.0060,
            material=white,
            name=f"front_hanger_strut_{index}",
        )
        _member(
            wheel,
            outer0,
            outer1,
            radius=0.0058,
            material=white,
            name=f"rim_hanger_bridge_{index}",
        )

    wheel.visual(
        Cylinder(radius=0.020, length=0.018),
        origin=Origin(xyz=p0, rpy=(0.0, math.pi / 2.0, 0.0)),
        material=dark,
        name=f"rear_hanger_boss_{index}",
    )
    wheel.visual(
        Cylinder(radius=0.020, length=0.018),
        origin=Origin(xyz=p1, rpy=(0.0, math.pi / 2.0, 0.0)),
        material=dark,
        name=f"front_hanger_boss_{index}",
    )
    return _wheel_point(pivot_radius, angle, 0.0)


def build_ferris_wheel(
    config: FerrisWheelConfig | None = None, *, assets: AssetContext | None = None
) -> ArticulatedObject:
    config = config or FerrisWheelConfig()
    resolved = resolve_config(config)
    if assets is None:
        assets = AssetContext(Path(tempfile.mkdtemp(prefix="articraft-ferris-assets-")))
    model = ArticulatedObject(name=resolved.name, assets=assets)

    white = model.material("painted_white_steel", rgba=(0.90, 0.90, 0.86, 1.0))
    dark = model.material("dark_bearing_steel", rgba=(0.32, 0.33, 0.34, 1.0))
    platform_mat = model.material("platform_panels", rgba=(0.76, 0.75, 0.70, 1.0))
    cabin_mat = model.material("cream_cabin_panels", rgba=(0.92, 0.88, 0.78, 1.0))
    trim_mat = model.material("cabin_white_trim", rgba=(0.96, 0.96, 0.92, 1.0))
    glass = model.material("smoky_window_glass", rgba=(0.55, 0.68, 0.72, 0.40))

    rim_mesh = None
    inner_rim_mesh = None
    if resolved.rim_style in {"single_torus", "double_torus"}:
        rim_mesh = _mesh(
            assets,
            "large_outer_rim.obj",
            TorusGeometry(
                radius=resolved.rim_radius,
                tube=0.018,
                radial_segments=18,
                tubular_segments=144,
            ).rotate_y(math.pi / 2.0),
        )
    if resolved.rim_style == "double_torus":
        inner_rim_mesh = _mesh(
            assets,
            "inner_stiffening_rim.obj",
            TorusGeometry(
                radius=resolved.inner_rim_radius,
                tube=0.010,
                radial_segments=14,
                tubular_segments=128,
            ).rotate_y(math.pi / 2.0),
        )

    support = model.part("support_frame")
    _add_support_base(
        support,
        resolved,
        material=platform_mat,
    )
    support_builder = SUPPORT_STYLE_BUILDERS[resolved.support_style]
    axle, _bearing_x = support_builder(support, resolved, white=white, dark=dark)

    hub_length, hub_cap_x, hub_cap_radius, central_hub_radius = hub_geometry(
        resolved.wheel_half_width
    )
    hub_cap_length = 0.026 * (resolved.wheel_half_width / DEFAULT_WHEEL_HALF_WIDTH)

    wheel = model.part("wheel")
    if resolved.rim_style == "twin_rings":
        _add_twin_ring_rim(wheel, resolved, white=white)
    else:
        for x, label in (
            (-resolved.wheel_half_width, "left"),
            (resolved.wheel_half_width, "right"),
        ):
            wheel.visual(
                rim_mesh,
                origin=Origin(xyz=(x, 0.0, 0.0)),
                material=white,
                name=f"{label}_outer_rim",
            )
            if resolved.rim_style == "double_torus":
                wheel.visual(
                    inner_rim_mesh,
                    origin=Origin(xyz=(x, 0.0, 0.0)),
                    material=white,
                    name=f"{label}_inner_rim",
                )
    wheel.visual(
        Cylinder(radius=central_hub_radius, length=hub_length),
        origin=Origin(rpy=(0.0, math.pi / 2.0, 0.0)),
        material=dark,
        name="central_hub",
    )
    wheel.visual(
        Cylinder(radius=hub_cap_radius, length=hub_cap_length),
        origin=Origin(xyz=(hub_cap_x, 0.0, 0.0), rpy=(0.0, math.pi / 2.0, 0.0)),
        material=white,
        name="front_hub_cap",
    )
    wheel.visual(
        Cylinder(radius=hub_cap_radius, length=hub_cap_length),
        origin=Origin(xyz=(-hub_cap_x, 0.0, 0.0), rpy=(0.0, math.pi / 2.0, 0.0)),
        material=white,
        name="rear_hub_cap",
    )

    for i in range(resolved.spoke_count):
        angle = (2.0 * math.pi * i) / resolved.spoke_count
        for x, side in ((-resolved.wheel_half_width, "rear"), (resolved.wheel_half_width, "front")):
            _member(
                wheel,
                (x, 0.0, 0.0),
                _wheel_point(resolved.rim_radius - 0.020, angle, x),
                radius=0.0065 if i % 2 else 0.008,
                material=white,
                name=f"{side}_spoke_{i}",
            )
    gondola_pivots: dict[int, tuple[float, float, float]] = {}
    for i in range(resolved.num_gondolas):
        angle = (2.0 * math.pi * i) / resolved.num_gondolas - math.pi / 2.0
        gondola_pivots[i + 1] = _add_gondola_mounting(
            wheel,
            resolved,
            angle=angle,
            index=i + 1,
            white=white,
            dark=dark,
        )

    model.articulation(
        "wheel_rotation",
        ArticulationType.REVOLUTE,
        parent=support,
        child=wheel,
        origin=Origin(xyz=axle),
        axis=(1.0, 0.0, 0.0),
        motion_limits=MotionLimits(effort=250.0, velocity=0.35, lower=0.0, upper=6.28),
    )

    gondola_builder = GONDOLA_STYLE_BUILDERS[resolved.gondola_style]
    for i in range(1, resolved.num_gondolas + 1):
        gondola = model.part(f"gondola_{i}")
        gondola_builder(gondola, body_mat=cabin_mat, trim_mat=trim_mat, glass_mat=glass, index=i)
        pivot = gondola_pivots[i]
        model.articulation(
            f"gondola_pivot_{i}",
            ArticulationType.REVOLUTE,
            parent=wheel,
            child=gondola,
            origin=Origin(xyz=pivot),
            axis=(1.0, 0.0, 0.0),
            motion_limits=MotionLimits(effort=24.0, velocity=1.0, lower=-3.14, upper=3.14),
            mimic=(
                Mimic(joint="wheel_rotation", multiplier=-1.0, offset=0.0)
                if resolved.gondola_motion_mode == "counter_rotate_mimic"
                else None
            ),
        )
    return model


def run_ferris_wheel_tests(
    object_model: ArticulatedObject, config: FerrisWheelConfig
) -> TestReport:
    resolved = resolve_config(config)
    ctx = TestContext(object_model)
    support = object_model.get_part("support_frame")
    wheel = object_model.get_part("wheel")
    wheel_joint = object_model.get_articulation("wheel_rotation")

    for elem in ("central_hub", "front_hub_cap", "rear_hub_cap"):
        ctx.allow_overlap(
            wheel,
            support,
            elem_a=elem,
            elem_b="fixed_axle",
            reason="The rotating hub is carried on the fixed axle.",
        )
    for elem, bearing in (
        ("rear_hub_cap", "left_bearing_block"),
        ("central_hub", "left_bearing_block"),
        ("central_hub", "right_bearing_block"),
        ("front_hub_cap", "right_bearing_block"),
    ):
        ctx.allow_overlap(
            wheel,
            support,
            elem_a=elem,
            elem_b=bearing,
            reason="The hub assembly is captured by the bearing support.",
        )
    for elem, bearing in (
        ("rear_hub_cap", "left_bearing_web"),
        ("front_hub_cap", "right_bearing_web"),
        ("rear_hub_cap", "left_hidden_core"),
        ("front_hub_cap", "right_hidden_core"),
    ):
        ctx.allow_overlap(
            wheel,
            support,
            elem_a=elem,
            elem_b=bearing,
            reason="The hub assembly is captured by the bearing support.",
        )
    if resolved.support_style == "truss_tower":
        for elem in ("central_hub", "front_hub_cap", "rear_hub_cap"):
            for support_elem in (
                "left_center_tower_post",
                "right_center_tower_post",
                "left_center_crown_strut",
                "right_center_crown_strut",
            ):
                ctx.allow_overlap(
                    wheel,
                    support,
                    elem_a=elem,
                    elem_b=support_elem,
                    reason="The truss crown and center posts capture the rotating hub assembly.",
                )
    for spoke_index in range(resolved.spoke_count):
        ctx.allow_overlap(
            wheel,
            support,
            elem_a=f"rear_spoke_{spoke_index}",
            elem_b="fixed_axle",
            reason="Rear spoke root passes through the central axle/hub region.",
        )
        ctx.allow_overlap(
            wheel,
            support,
            elem_a=f"front_spoke_{spoke_index}",
            elem_b="fixed_axle",
            reason="Front spoke root passes through the central axle/hub region.",
        )
    for i in range(1, resolved.num_gondolas + 1):
        gondola = object_model.get_part(f"gondola_{i}")
        joint = object_model.get_articulation(f"gondola_pivot_{i}")
        for elem in ("hanger_pin", "hanger_rear", "hanger_front"):
            ctx.allow_overlap(
                gondola,
                wheel,
                elem_a=elem,
                elem_b=f"gondola_pivot_bar_{i}",
                reason="The gondola hanger is captured on the pivot bar.",
            )
        ctx.check(
            f"gondola_{i}_range",
            joint.motion_limits is not None
            and abs(joint.motion_limits.lower + 3.14) < 1e-6
            and abs(joint.motion_limits.upper - 3.14) < 1e-6,
        )
        if resolved.gondola_motion_mode == "counter_rotate_mimic":
            ctx.check(
                f"gondola_{i}_mimic",
                joint.mimic is not None
                and joint.mimic.joint == "wheel_rotation"
                and abs((joint.mimic.multiplier or 0.0) + 1.0) < 1e-6,
            )
        else:
            ctx.check(f"gondola_{i}_no_mimic", joint.mimic is None)

    ctx.check(
        "wheel_rotation_range",
        wheel_joint.motion_limits is not None
        and abs(wheel_joint.motion_limits.lower - 0.0) < 1e-6
        and abs(wheel_joint.motion_limits.upper - 6.28) < 1e-6,
    )
    ctx.check(
        "configured_gondola_count",
        len([p for p in object_model.parts if p.name.startswith("gondola_")])
        == resolved.num_gondolas,
    )
    ctx.expect_gap(
        wheel,
        support,
        axis="z",
        min_gap=0.18,
        positive_elem="central_hub",
        negative_elem="platform_slab",
        name="hub_high_above_platform",
    )
    ctx.expect_overlap(
        wheel,
        support,
        axes="yz",
        min_overlap=0.030,
        elem_a="central_hub",
        elem_b="fixed_axle",
        name="hub_centered_on_axle",
    )
    with ctx.pose({wheel_joint: 3.14}):
        ctx.check("wheel_can_rotate_half_turn", ctx.part_world_position(wheel) is not None)
    if resolved.gondola_motion_mode == "free_swing":
        with ctx.pose({"gondola_pivot_1": 1.2}):
            ctx.check(
                "gondola_1_can_swing",
                ctx.part_world_position(object_model.get_part("gondola_1")) is not None,
            )
    else:
        with ctx.pose({"wheel_rotation": math.pi / 2.0}):
            ctx.check(
                "gondola_1_can_counter_rotate",
                ctx.part_world_position(object_model.get_part("gondola_1")) is not None,
            )
    return ctx.report()


def build_seeded_ferris_wheel(
    seed: int, *, assets: AssetContext | None = None
) -> ArticulatedObject:
    return build_ferris_wheel(config_from_seed(seed), assets=assets)


def with_overrides(config: FerrisWheelConfig, **kwargs: object) -> FerrisWheelConfig:
    return replace(config, **kwargs)
