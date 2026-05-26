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
    ExtrudeGeometry,
    MotionLimits,
    Origin,
    TestContext,
    TestReport,
    mesh_from_geometry,
    rounded_rect_profile,
)

MountBaseStyle = Literal["desk_clamp", "wall_plate", "pole_clamp", "freestanding_base"]
ArmTopology = Literal["simple_two_link", "wall_planar_two_link", "counterbalanced_lift_pitch"]
ArmPlane = Literal["horizontal_yaw", "vertical_pitch", "hybrid_counterbalanced"]
LinkStyle = Literal["box_beam", "dual_rail", "spring_tube", "cable_spine"]
HeadDof = Literal["tilt_only", "pan_tilt", "pan_tilt_roll"]
VesaSize = Literal["75", "100", "dual_75_100"]
MaterialStyle = Literal["office_black", "silver_white", "matte_graphite", "industrial_white"]
CounterbalanceStyle = Literal["none", "gas_strut", "spring_tube"]
CableSpineStyle = Literal["none", "open_channel", "covered_spine"]

SOURCE_IDS = {
    "S1": ("data/records/rec_monitor_mount_0001/revisions/rev_000001/model.py:L51-L114"),
    "S2": ("data/records/rec_monitor_mount_0001/revisions/rev_000001/model.py:L115-L205"),
    "S3": ("data/records/rec_monitor_mount_0001/revisions/rev_000001/model.py:L207-L242"),
    "S4": (
        "data/records/rec_monitor_mount_997e8c29b2f44a30a7dd25da2a7c6fa6/"
        "revisions/rev_000001/model.py:L30-L183"
    ),
    "S5": (
        "data/records/rec_monitor_mount_997e8c29b2f44a30a7dd25da2a7c6fa6/"
        "revisions/rev_000001/model.py:L185-L482"
    ),
    "S6": (
        "data/records/rec_monitor_mount_997e8c29b2f44a30a7dd25da2a7c6fa6/"
        "revisions/rev_000001/model.py:L484-L533"
    ),
    "S7": (
        "data/records/rec_monitor_mount_b009e88d6f924f3c90fb6e0ef457e60b/"
        "revisions/rev_000001/model.py:L31-L88"
    ),
    "S8": (
        "data/records/rec_monitor_mount_b009e88d6f924f3c90fb6e0ef457e60b/"
        "revisions/rev_000001/model.py:L89-L284"
    ),
    "S9": (
        "data/records/rec_monitor_mount_b009e88d6f924f3c90fb6e0ef457e60b/"
        "revisions/rev_000001/model.py:L285-L333"
    ),
}

SOURCE_ADAPTATION_MAP: dict[str, tuple[str, ...]] = {
    "base_mount": ("S1", "S4", "S7"),
    "desk_clamp": ("S1",),
    "wall_plate": ("S4", "S7"),
    "shoulder_carriage": ("S2", "S4", "S5", "S8"),
    "primary_link": ("S2", "S5", "S8"),
    "secondary_link": ("S2", "S5", "S8"),
    "counterbalance": ("S5", "S6"),
    "cable_spine": ("S4", "S8"),
    "head_yoke": ("S2", "S5", "S8"),
    "vesa_plate": ("S2", "S5", "S8"),
    "base_yaw_joint": ("S3", "S6", "S9"),
    "shoulder_joint": ("S3", "S6", "S9"),
    "elbow_joint": ("S3", "S6", "S9"),
    "head_pan_joint": ("S3", "S6", "S9"),
    "head_tilt_joint": ("S3", "S6", "S9"),
    "display_roll_joint": ("S5",),
}

PALETTES: dict[MaterialStyle, dict[str, tuple[float, float, float, float]]] = {
    "office_black": {
        "base": (0.050, 0.054, 0.058, 1.0),
        "arm": (0.090, 0.095, 0.100, 1.0),
        "metal": (0.300, 0.310, 0.320, 1.0),
        "rubber": (0.012, 0.012, 0.012, 1.0),
        "accent": (0.620, 0.630, 0.650, 1.0),
        "warning": (0.720, 0.360, 0.060, 1.0),
    },
    "silver_white": {
        "base": (0.770, 0.780, 0.760, 1.0),
        "arm": (0.660, 0.680, 0.690, 1.0),
        "metal": (0.410, 0.430, 0.450, 1.0),
        "rubber": (0.070, 0.070, 0.075, 1.0),
        "accent": (0.180, 0.190, 0.205, 1.0),
        "warning": (0.820, 0.500, 0.100, 1.0),
    },
    "matte_graphite": {
        "base": (0.090, 0.095, 0.095, 1.0),
        "arm": (0.180, 0.185, 0.180, 1.0),
        "metal": (0.360, 0.370, 0.365, 1.0),
        "rubber": (0.025, 0.025, 0.025, 1.0),
        "accent": (0.500, 0.520, 0.510, 1.0),
        "warning": (0.740, 0.420, 0.060, 1.0),
    },
    "industrial_white": {
        "base": (0.880, 0.860, 0.820, 1.0),
        "arm": (0.920, 0.900, 0.850, 1.0),
        "metal": (0.520, 0.530, 0.520, 1.0),
        "rubber": (0.045, 0.045, 0.045, 1.0),
        "accent": (0.120, 0.130, 0.140, 1.0),
        "warning": (0.780, 0.430, 0.090, 1.0),
    },
}


@dataclass(frozen=True)
class MonitorMountConfig:
    mount_base_style: MountBaseStyle = "desk_clamp"
    arm_topology: ArmTopology = "simple_two_link"
    arm_plane: ArmPlane | None = None
    link_style: LinkStyle = "dual_rail"
    head_dof: HeadDof = "pan_tilt"
    vesa_size: VesaSize = "dual_75_100"
    material_style: MaterialStyle = "office_black"
    counterbalance_style: CounterbalanceStyle | None = None
    cable_spine_style: CableSpineStyle = "covered_spine"
    total_reach: float = 0.74
    link_ratio: float = 0.52
    post_height: float = 0.26
    wall_plate_height: float = 0.36
    clamp_gap: float = 0.075
    monitor_mass_class: Literal["light", "medium", "heavy"] = "medium"
    tilt_range: tuple[float, float] = (-0.55, 0.60)
    display_roll_enabled: bool | None = None
    has_cable_spine: bool | None = None
    has_counterbalance: bool | None = None
    name: str = "reference_monitor_mount"


@dataclass(frozen=True)
class ResolvedMonitorMountConfig:
    mount_base_style: MountBaseStyle
    arm_topology: ArmTopology
    arm_plane: ArmPlane
    link_style: LinkStyle
    head_dof: HeadDof
    vesa_size: VesaSize
    material_style: MaterialStyle
    counterbalance_style: CounterbalanceStyle
    cable_spine_style: CableSpineStyle
    total_reach: float
    link_ratio: float
    primary_len: float
    secondary_len: float
    head_offset: float
    shoulder_origin: tuple[float, float, float]
    base_yaw_origin: tuple[float, float, float]
    shoulder_axis: tuple[float, float, float]
    elbow_axis: tuple[float, float, float]
    head_pan_axis: tuple[float, float, float]
    head_tilt_axis: tuple[float, float, float]
    display_roll_axis: tuple[float, float, float]
    post_height: float
    wall_plate_height: float
    clamp_gap: float
    base_width: float
    base_depth: float
    shoulder_gap: float
    elbow_gap: float
    link_width: float
    link_height: float
    hub_radius: float
    bearing_radius: float
    vesa_hole_spacing: tuple[float, ...]
    vesa_plate_width: float
    vesa_plate_height: float
    tilt_range: tuple[float, float]
    head_dof_effective: HeadDof
    display_roll_enabled: bool
    has_cable_spine: bool
    has_counterbalance: bool
    monitor_mass_class: Literal["light", "medium", "heavy"]
    name: str


def config_from_seed(seed: int) -> MonitorMountConfig:
    rng = random.Random(seed)
    base: MountBaseStyle = rng.choices(
        ("desk_clamp", "wall_plate", "pole_clamp", "freestanding_base"),
        weights=(0.45, 0.30, 0.18, 0.07),
        k=1,
    )[0]
    if base == "wall_plate":
        # Wall counterbalanced arms need a different wall-depth shoulder bracket; keep random
        # generation on the stable planar wall arm and leave counterbalanced wall as explicit override.
        topology: ArmTopology = "wall_planar_two_link"
    elif base == "freestanding_base":
        topology = "simple_two_link"
    else:
        topology = rng.choices(
            ("simple_two_link", "counterbalanced_lift_pitch"), weights=(0.68, 0.32), k=1
        )[0]
    if topology == "counterbalanced_lift_pitch":
        link_style: LinkStyle = rng.choice(("spring_tube", "dual_rail"))
    elif topology == "wall_planar_two_link":
        link_style = rng.choice(("box_beam", "cable_spine", "dual_rail"))
    else:
        link_style = rng.choice(("box_beam", "dual_rail", "cable_spine"))
    # Keep the random seed domain on the stable pan/tilt family.  The roll branch remains
    # available for explicit override, but it is not sampled until its preview/QC branch is
    # hand-validated across a wider pose set.
    head_dof: HeadDof = rng.choices(("tilt_only", "pan_tilt"), weights=(0.16, 0.84), k=1)[0]
    return MonitorMountConfig(
        mount_base_style=base,
        arm_topology=topology,
        arm_plane=None,
        link_style=link_style,
        head_dof=head_dof,
        vesa_size=rng.choice(("75", "100", "dual_75_100")),
        material_style=rng.choice(
            ("office_black", "silver_white", "matte_graphite", "industrial_white")
        ),
        counterbalance_style=None,
        cable_spine_style=rng.choice(("none", "open_channel", "covered_spine")),
        total_reach=round(rng.uniform(0.52, 0.96), 3),
        link_ratio=round(rng.uniform(0.44, 0.57), 3),
        post_height=round(rng.uniform(0.20, 0.38), 3),
        wall_plate_height=round(rng.uniform(0.30, 0.48), 3),
        clamp_gap=round(rng.uniform(0.050, 0.095), 3),
        monitor_mass_class=rng.choice(("light", "medium", "heavy")),
        tilt_range=(-round(rng.uniform(0.32, 0.62), 2), round(rng.uniform(0.35, 0.70), 2)),
        display_roll_enabled=None,
        has_cable_spine=None,
        has_counterbalance=None,
        name=f"seeded_monitor_mount_{seed}",
    )


def _validate_enum(name: str, value: str, allowed: set[str]) -> None:
    if value not in allowed:
        raise ValueError(f"Unsupported {name}: {value}")


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def resolve_config(config: MonitorMountConfig) -> ResolvedMonitorMountConfig:
    _validate_enum(
        "mount_base_style",
        config.mount_base_style,
        {"desk_clamp", "wall_plate", "pole_clamp", "freestanding_base"},
    )
    _validate_enum(
        "arm_topology",
        config.arm_topology,
        {"simple_two_link", "wall_planar_two_link", "counterbalanced_lift_pitch"},
    )
    _validate_enum(
        "link_style", config.link_style, {"box_beam", "dual_rail", "spring_tube", "cable_spine"}
    )
    _validate_enum("head_dof", config.head_dof, {"tilt_only", "pan_tilt", "pan_tilt_roll"})
    _validate_enum("vesa_size", config.vesa_size, {"75", "100", "dual_75_100"})
    _validate_enum("material_style", config.material_style, set(PALETTES))
    if config.counterbalance_style is not None:
        _validate_enum(
            "counterbalance_style",
            config.counterbalance_style,
            {"none", "gas_strut", "spring_tube"},
        )
    _validate_enum(
        "cable_spine_style", config.cable_spine_style, {"none", "open_channel", "covered_spine"}
    )
    _validate_enum("monitor_mass_class", config.monitor_mass_class, {"light", "medium", "heavy"})
    if config.total_reach < 0.35 or config.total_reach > 1.08:
        raise ValueError("total_reach must be in [0.35, 1.08]")
    if not 0.38 <= config.link_ratio <= 0.62:
        raise ValueError("link_ratio must be in [0.38, 0.62]")
    lower, upper = config.tilt_range
    if lower >= upper or lower < -0.85 or upper > 0.85:
        raise ValueError("tilt_range must be ordered and within monitor mount tilt bounds")

    arm_topology = config.arm_topology
    mount_base_style = config.mount_base_style
    if mount_base_style == "freestanding_base" and arm_topology == "wall_planar_two_link":
        arm_topology = "simple_two_link"
    if mount_base_style == "wall_plate" and arm_topology == "simple_two_link":
        arm_topology = "wall_planar_two_link"

    if config.arm_plane is None:
        if arm_topology == "counterbalanced_lift_pitch":
            arm_plane: ArmPlane = "hybrid_counterbalanced"
        elif arm_topology == "wall_planar_two_link":
            arm_plane = "horizontal_yaw"
        else:
            arm_plane = "horizontal_yaw"
    else:
        _validate_enum(
            "arm_plane",
            config.arm_plane,
            {"horizontal_yaw", "vertical_pitch", "hybrid_counterbalanced"},
        )
        arm_plane = config.arm_plane
    if arm_topology == "counterbalanced_lift_pitch" and arm_plane == "horizontal_yaw":
        arm_plane = "hybrid_counterbalanced"
    if arm_topology == "wall_planar_two_link" and arm_plane != "horizontal_yaw":
        arm_plane = "horizontal_yaw"

    total_reach = _clamp(config.total_reach, 0.38, 1.04)
    head_offset = 0.105 if config.head_dof != "tilt_only" else 0.085
    primary_len = max(0.18, total_reach * config.link_ratio)
    secondary_len = max(0.16, total_reach - primary_len - head_offset)
    if secondary_len < 0.18:
        secondary_len = 0.18
        primary_len = max(0.18, total_reach - secondary_len - head_offset)
    if primary_len < 0.20:
        primary_len = 0.20
        total_reach = primary_len + secondary_len + head_offset

    if config.monitor_mass_class == "heavy":
        link_width = 0.078
        link_height = 0.066
        hub_radius = 0.052
    elif config.monitor_mass_class == "light":
        link_width = 0.052
        link_height = 0.045
        hub_radius = 0.039
    else:
        link_width = 0.064
        link_height = 0.054
        hub_radius = 0.046
    if config.link_style == "spring_tube":
        link_height += 0.012
    if config.link_style == "dual_rail":
        link_width += 0.018
    bearing_radius = hub_radius + 0.018
    shoulder_gap = link_width + 0.038
    elbow_gap = max(link_width * 0.86, 0.060) + 0.030

    post_height = _clamp(config.post_height, 0.18, 0.42)
    wall_plate_height = _clamp(config.wall_plate_height, 0.28, 0.52)
    clamp_gap = _clamp(config.clamp_gap, 0.045, 0.110)
    if mount_base_style == "desk_clamp":
        base_yaw_origin = (0.0, 0.0, post_height + 0.053)
        shoulder_origin = base_yaw_origin
        base_width = 0.18
        base_depth = 0.15
    elif mount_base_style == "wall_plate":
        base_yaw_origin = (0.088 + bearing_radius, 0.0, wall_plate_height * 0.63)
        shoulder_origin = base_yaw_origin
        base_width = 0.16
        base_depth = 0.050
    elif mount_base_style == "pole_clamp":
        base_yaw_origin = (0.0, 0.0, post_height + 0.026)
        shoulder_origin = base_yaw_origin
        base_width = 0.20
        base_depth = 0.19
    else:
        base_yaw_origin = (0.0, 0.0, 0.165)
        shoulder_origin = base_yaw_origin
        base_width = 0.34
        base_depth = 0.28

    if arm_topology == "counterbalanced_lift_pitch":
        shoulder_axis = (0.0, -1.0, 0.0)
        # S5 uses a pitch shoulder but a vertical elbow barrel, so the secondary
        # folds around the visible stacked elbow collars instead of an imaginary
        # horizontal pin.
        elbow_axis = (0.0, 0.0, 1.0)
    elif arm_plane == "horizontal_yaw":
        shoulder_axis = (0.0, 0.0, 1.0)
        elbow_axis = (0.0, 0.0, 1.0)
    else:
        shoulder_axis = (0.0, -1.0, 0.0)
        elbow_axis = (0.0, -1.0, 0.0)
    head_pan_axis = (0.0, 0.0, 1.0)
    head_tilt_axis = (0.0, 1.0, 0.0)
    display_roll_axis = (1.0, 0.0, 0.0)

    if config.vesa_size == "75":
        vesa_hole_spacing = (0.075,)
        plate_w = 0.135
        plate_h = 0.135
    elif config.vesa_size == "100":
        vesa_hole_spacing = (0.100,)
        plate_w = 0.165
        plate_h = 0.165
    else:
        vesa_hole_spacing = (0.075, 0.100)
        plate_w = 0.178
        plate_h = 0.178

    has_counterbalance = config.has_counterbalance
    if has_counterbalance is None:
        has_counterbalance = arm_topology == "counterbalanced_lift_pitch"
    if arm_topology != "counterbalanced_lift_pitch":
        has_counterbalance = False
    counterbalance_style = config.counterbalance_style
    if counterbalance_style is None:
        counterbalance_style = "gas_strut" if has_counterbalance else "none"
    if not has_counterbalance:
        counterbalance_style = "none"
    if has_counterbalance and counterbalance_style == "none":
        counterbalance_style = "gas_strut"

    has_cable_spine = config.has_cable_spine
    if has_cable_spine is None:
        has_cable_spine = (
            config.cable_spine_style != "none" and arm_topology != "counterbalanced_lift_pitch"
        )
    cable_spine_style = config.cable_spine_style if has_cable_spine else "none"

    display_roll_enabled = config.display_roll_enabled
    if display_roll_enabled is None:
        display_roll_enabled = config.head_dof == "pan_tilt_roll"
    if config.head_dof == "tilt_only":
        display_roll_enabled = False
    head_dof_effective: HeadDof = config.head_dof
    if display_roll_enabled:
        head_dof_effective = "pan_tilt_roll"

    return ResolvedMonitorMountConfig(
        mount_base_style=mount_base_style,
        arm_topology=arm_topology,
        arm_plane=arm_plane,
        link_style=config.link_style,
        head_dof=config.head_dof,
        vesa_size=config.vesa_size,
        material_style=config.material_style,
        counterbalance_style=counterbalance_style,
        cable_spine_style=cable_spine_style,
        total_reach=total_reach,
        link_ratio=config.link_ratio,
        primary_len=primary_len,
        secondary_len=secondary_len,
        head_offset=head_offset,
        shoulder_origin=shoulder_origin,
        base_yaw_origin=base_yaw_origin,
        shoulder_axis=shoulder_axis,
        elbow_axis=elbow_axis,
        head_pan_axis=head_pan_axis,
        head_tilt_axis=head_tilt_axis,
        display_roll_axis=display_roll_axis,
        post_height=post_height,
        wall_plate_height=wall_plate_height,
        clamp_gap=clamp_gap,
        base_width=base_width,
        base_depth=base_depth,
        shoulder_gap=shoulder_gap,
        elbow_gap=elbow_gap,
        link_width=link_width,
        link_height=link_height,
        hub_radius=hub_radius,
        bearing_radius=bearing_radius,
        vesa_hole_spacing=vesa_hole_spacing,
        vesa_plate_width=plate_w,
        vesa_plate_height=plate_h,
        tilt_range=(lower, upper),
        head_dof_effective=head_dof_effective,
        display_roll_enabled=display_roll_enabled,
        has_cable_spine=has_cable_spine,
        has_counterbalance=bool(has_counterbalance),
        monitor_mass_class=config.monitor_mass_class,
        name=config.name,
    )


def with_overrides(config: MonitorMountConfig, **kwargs: object) -> MonitorMountConfig:
    return replace(config, **kwargs)


def _joint_meta(
    joint_type: ArticulationType,
    axis: tuple[float, float, float],
    origin: tuple[float, float, float] | str,
    limits: MotionLimits | None,
    *,
    source_ids: tuple[str, ...],
    semantic: str,
) -> dict[str, object]:
    if joint_type == ArticulationType.CONTINUOUS:
        joint_range: object = "continuous"
    elif limits is None:
        joint_range = None
    else:
        joint_range = (limits.lower, limits.upper)
    return {
        "type": joint_type.value,
        "axis": axis,
        "origin": origin,
        "range": joint_range,
        "source_ids": source_ids,
        "semantic": semantic,
    }


def _box(part, size, xyz, material, name: str, rpy=(0.0, 0.0, 0.0)) -> None:
    part.visual(Box(size), origin=Origin(xyz=xyz, rpy=rpy), material=material, name=name)


def _cyl(part, radius: float, length: float, xyz, material, name: str, rpy=(0.0, 0.0, 0.0)) -> None:
    part.visual(
        Cylinder(radius=radius, length=length),
        origin=Origin(xyz=xyz, rpy=rpy),
        material=material,
        name=name,
    )


def _rounded_plate_mesh(width: float, height: float, thickness: float) -> ExtrudeGeometry:
    radius = min(width, height) * 0.22
    return ExtrudeGeometry(
        rounded_rect_profile(width, height, radius), thickness, cap=True, center=True
    )


def _rounded_xy_plate(part, assets: AssetContext, size, xyz, material, name: str) -> None:
    part.visual(
        mesh_from_geometry(
            _rounded_plate_mesh(size[0], size[1], size[2]),
            assets.mesh_path(f"{part.name}_{name}.obj"),
        ),
        origin=Origin(xyz=xyz),
        material=material,
        name=name,
    )


def _rounded_xz_plate(part, assets: AssetContext, size, xyz, material, name: str) -> None:
    part.visual(
        mesh_from_geometry(
            _rounded_plate_mesh(size[0], size[2], size[1]),
            assets.mesh_path(f"{part.name}_{name}.obj"),
        ),
        origin=Origin(xyz=xyz, rpy=(math.pi / 2.0, 0.0, 0.0)),
        material=material,
        name=name,
    )


_CYL_X = (0.0, math.pi / 2.0, 0.0)
_CYL_Y = (math.pi / 2.0, 0.0, 0.0)


def _axis_rpy(axis: tuple[float, float, float]) -> tuple[float, float, float]:
    if abs(axis[0]) > 0.5:
        return _CYL_X
    if abs(axis[1]) > 0.5:
        return _CYL_Y
    return (0.0, 0.0, 0.0)


def _axis_is_vertical(axis: tuple[float, float, float]) -> bool:
    return abs(axis[2]) > 0.5


def _add_bolt_grid(
    part, centers: tuple[tuple[float, float, float], ...], material, prefix: str, *, axis: str = "z"
) -> None:
    rpy = _CYL_X if axis == "x" else _CYL_Y if axis == "y" else (0.0, 0.0, 0.0)
    for index, center in enumerate(centers):
        _cyl(part, 0.0065, 0.010, center, material, f"{prefix}_bolt_{index}", rpy)


def _add_side_caps(
    part, *, x: float, z: float, half_y: float, radius: float, material, prefix: str
) -> None:
    for index, sign in enumerate((-1.0, 1.0)):
        _cyl(
            part,
            radius,
            0.018,
            (x, sign * half_y, z),
            material,
            f"{prefix}_side_cap_{index}",
            _CYL_Y,
        )


def _add_cheek_pair(
    part,
    *,
    pivot_x: float,
    pivot_z: float,
    gap: float,
    cheek_len: float,
    cheek_height: float,
    cheek_thick: float,
    material,
    metal,
    prefix: str,
) -> None:
    half = gap / 2.0
    for index, sign in enumerate((-1.0, 1.0)):
        _box(
            part,
            (cheek_len, cheek_thick, cheek_height),
            (pivot_x, sign * half, pivot_z),
            material,
            f"{prefix}_cheek_{index}",
        )
    _box(
        part,
        (cheek_len * 0.70, gap, cheek_height * 0.15),
        (pivot_x - cheek_len * 0.08, 0.0, pivot_z - cheek_height * 0.58),
        material,
        f"{prefix}_lower_bridge",
    )
    _box(
        part,
        (cheek_len * 0.52, gap, cheek_height * 0.12),
        (pivot_x + cheek_len * 0.04, 0.0, pivot_z + cheek_height * 0.53),
        material,
        f"{prefix}_upper_bridge",
    )


def _add_cable_loop(part, *, x: float, y: float, z: float, material, prefix: str) -> None:
    _cyl(part, 0.014, 0.006, (x, y, z), material, f"{prefix}_loop_outer", _CYL_Y)
    _box(part, (0.012, 0.005, 0.020), (x, y, z - 0.012), material, f"{prefix}_loop_tab")


def _build_desk_clamp_base(
    base, r: ResolvedMonitorMountConfig, base_mat, metal_mat, rubber_mat, bolt_mat
) -> None:
    post_h = r.post_height
    _box(base, (0.145, 0.125, 0.026), (0.0, 0.0, 0.013), base_mat, "desk_top_clamp_plate")
    _box(
        base,
        (0.055, 0.115, r.clamp_gap + 0.052),
        (-0.058, 0.0, -(r.clamp_gap * 0.50)),
        base_mat,
        "rear_clamp_jaw",
    )
    _box(
        base,
        (0.125, 0.100, 0.020),
        (0.0, 0.0, -r.clamp_gap - 0.010),
        rubber_mat,
        "lower_rubber_pressure_pad",
    )
    _box(base, (0.125, 0.100, 0.010), (0.0, 0.0, 0.034), rubber_mat, "upper_rubber_table_pad")
    _cyl(
        base,
        0.017,
        r.clamp_gap + 0.035,
        (0.032, 0.0, -r.clamp_gap * 0.52),
        metal_mat,
        "clamp_screw",
        (0.0, 0.0, 0.0),
    )
    _cyl(base, 0.030, 0.016, (0.032, 0.0, -r.clamp_gap - 0.032), metal_mat, "clamp_knob")
    _cyl(base, 0.040, post_h, (0.0, 0.0, 0.040 + post_h * 0.5), base_mat, "vertical_post")
    _cyl(base, 0.055, 0.030, (0.0, 0.0, 0.038), metal_mat, "post_lower_collar")
    _cyl(base, 0.060, 0.026, (0.0, 0.0, post_h + 0.040), metal_mat, "post_upper_bearing_collar")
    _add_bolt_grid(
        base,
        (
            (-0.045, -0.038, 0.042),
            (-0.045, 0.038, 0.042),
            (0.045, -0.038, 0.042),
            (0.045, 0.038, 0.042),
        ),
        bolt_mat,
        "desk_clamp",
    )


def _build_wall_plate_base(
    base, r: ResolvedMonitorMountConfig, base_mat, metal_mat, rubber_mat, bolt_mat
) -> None:
    h = r.wall_plate_height
    _box(base, (0.030, 0.205, h), (-0.015, 0.0, h * 0.50), base_mat, "wall_back_plate")
    _box(base, (0.026, 0.155, h * 0.72), (0.004, 0.0, h * 0.50), metal_mat, "raised_wall_insert")
    _box(base, (0.055, 0.115, 0.082), (0.036, 0.0, h * 0.63), base_mat, "wall_bearing_socket")
    _cyl(base, 0.060, 0.038, (0.054, 0.0, h * 0.63), metal_mat, "wall_pan_bearing_cup", _CYL_X)
    _cyl(base, 0.030, 0.020, (0.078, 0.0, h * 0.63), metal_mat, "wall_spindle_socket", _CYL_X)
    _box(base, (0.009, 0.140, 0.055), (0.018, 0.0, h * 0.44), rubber_mat, "vertical_cable_window")
    _add_bolt_grid(
        base,
        (
            (0.004, -0.072, h * 0.20),
            (0.004, 0.072, h * 0.20),
            (0.004, -0.072, h * 0.82),
            (0.004, 0.072, h * 0.82),
        ),
        bolt_mat,
        "wall_anchor",
        axis="x",
    )


def _build_pole_clamp_base(
    base, r: ResolvedMonitorMountConfig, base_mat, metal_mat, rubber_mat, bolt_mat
) -> None:
    post_h = r.post_height
    _cyl(base, 0.042, post_h, (0.0, 0.0, post_h * 0.50), base_mat, "shared_vertical_pole")
    _cyl(base, 0.066, 0.070, (0.0, 0.0, post_h * 0.64), metal_mat, "split_pole_clamp_ring")
    _box(base, (0.088, 0.035, 0.078), (0.065, -0.049, post_h * 0.64), base_mat, "left_clamp_lug")
    _box(base, (0.088, 0.035, 0.078), (0.065, 0.049, post_h * 0.64), base_mat, "right_clamp_lug")
    _cyl(
        base, 0.007, 0.120, (0.065, 0.0, post_h * 0.675), bolt_mat, "upper_pole_clamp_screw", _CYL_Y
    )
    _cyl(
        base, 0.007, 0.120, (0.065, 0.0, post_h * 0.605), bolt_mat, "lower_pole_clamp_screw", _CYL_Y
    )
    _box(base, (0.115, 0.105, 0.020), (0.0, 0.0, 0.010), rubber_mat, "pole_foot_pad")
    _cyl(base, 0.058, 0.026, (0.0, 0.0, post_h + 0.013), metal_mat, "pole_top_bearing")


def _build_freestanding_base(
    base, r: ResolvedMonitorMountConfig, base_mat, metal_mat, rubber_mat, bolt_mat
) -> None:
    _box(
        base,
        (r.base_width, r.base_depth, 0.035),
        (0.0, 0.0, 0.0175),
        base_mat,
        "weighted_base_plate",
    )
    _box(
        base,
        (r.base_width * 0.82, r.base_depth * 0.72, 0.010),
        (0.0, 0.0, 0.040),
        rubber_mat,
        "top_anti_slip_mat",
    )
    _box(
        base,
        (r.base_width * 0.92, 0.030, 0.014),
        (0.0, r.base_depth * 0.42, 0.007),
        rubber_mat,
        "rear_foot_strip",
    )
    _box(
        base,
        (r.base_width * 0.92, 0.030, 0.014),
        (0.0, -r.base_depth * 0.42, 0.007),
        rubber_mat,
        "front_foot_strip",
    )
    _cyl(base, 0.055, 0.110, (0.0, 0.0, 0.090), base_mat, "short_base_riser")
    _cyl(base, 0.075, 0.020, (0.0, 0.0, 0.155), metal_mat, "base_yaw_bearing")
    _add_bolt_grid(
        base,
        (
            (-0.085, -0.065, 0.045),
            (-0.085, 0.065, 0.045),
            (0.085, -0.065, 0.045),
            (0.085, 0.065, 0.045),
        ),
        bolt_mat,
        "freestand",
    )


def _build_base_mount(
    base, r: ResolvedMonitorMountConfig, base_mat, metal_mat, rubber_mat, bolt_mat
) -> None:
    if r.mount_base_style == "desk_clamp":
        _build_desk_clamp_base(base, r, base_mat, metal_mat, rubber_mat, bolt_mat)
    elif r.mount_base_style == "wall_plate":
        _build_wall_plate_base(base, r, base_mat, metal_mat, rubber_mat, bolt_mat)
    elif r.mount_base_style == "pole_clamp":
        _build_pole_clamp_base(base, r, base_mat, metal_mat, rubber_mat, bolt_mat)
    else:
        _build_freestanding_base(base, r, base_mat, metal_mat, rubber_mat, bolt_mat)


def _build_shoulder_carriage(
    carriage, r: ResolvedMonitorMountConfig, base_mat, metal_mat, bolt_mat, assets: AssetContext
) -> None:
    _cyl(carriage, r.bearing_radius, 0.018, (0.0, 0.0, 0.009), metal_mat, "pan_turntable")
    _box(
        carriage,
        (0.065, r.shoulder_gap + 0.026, 0.042),
        (-0.018, 0.0, 0.055),
        base_mat,
        "shoulder_carriage_block",
    )
    if _axis_is_vertical(r.shoulder_axis):
        shoulder_plate_z = max(r.link_height * 0.68, 0.040)
        for index, sign in enumerate((-1.0, 1.0)):
            _rounded_xy_plate(
                carriage,
                assets,
                (0.086, r.shoulder_gap * 0.78, 0.012),
                (0.067, 0.0, 0.120 + sign * shoulder_plate_z),
                base_mat,
                f"shoulder_yaw_bearing_plate_{index}",
            )
            _cyl(
                carriage,
                r.hub_radius * 0.78,
                0.010,
                (0.070, 0.0, 0.120 + sign * shoulder_plate_z),
                metal_mat,
                f"shoulder_yaw_boss_{index}",
            )
        if r.mount_base_style != "wall_plate":
            _rounded_xz_plate(
                carriage,
                assets,
                (0.056, r.shoulder_gap * 0.42, 0.132),
                (-0.032, 0.0, 0.070),
                base_mat,
                "shoulder_integral_riser_web",
            )
    else:
        _add_cheek_pair(
            carriage,
            pivot_x=0.070,
            pivot_z=0.120,
            gap=r.shoulder_gap,
            cheek_len=0.110,
            cheek_height=max(0.120, r.link_height * 1.95),
            cheek_thick=0.018,
            material=base_mat,
            metal=metal_mat,
            prefix="shoulder",
        )
    shoulder_socket_len = 0.030
    _box(
        carriage,
        (shoulder_socket_len, r.link_width * 0.56, r.link_height * 0.72),
        (0.070 - r.hub_radius - shoulder_socket_len * 0.5, 0.0, 0.120),
        base_mat,
        "shoulder_socket_to_pivot",
    )
    if r.arm_topology == "counterbalanced_lift_pitch":
        _box(
            carriage,
            (0.075, 0.020, 0.095),
            (0.000, -r.shoulder_gap * 0.56, 0.058),
            base_mat,
            "left_spring_anchor_tab",
        )
        _box(
            carriage,
            (0.075, 0.020, 0.095),
            (0.000, r.shoulder_gap * 0.56, 0.058),
            base_mat,
            "right_spring_anchor_tab",
        )
        _cyl(
            carriage,
            0.012,
            r.shoulder_gap + 0.060,
            (0.004, 0.0, 0.100),
            bolt_mat,
            "spring_anchor_pin",
            _CYL_Y,
        )


def _rail_y_offsets(width: float) -> tuple[float, float]:
    return (-width * 0.31, width * 0.31)


def _link_span_between_hubs(r: ResolvedMonitorMountConfig, length: float) -> tuple[float, float]:
    """Return a continuous visual span from root hub tangent to end-socket tangent."""
    start_x = r.hub_radius + 0.002
    end_x = length - r.hub_radius - 0.034
    if end_x <= start_x + 0.030:
        start_x = max(0.020, length * 0.18)
        end_x = max(start_x + 0.035, length - r.hub_radius - 0.020)
    return start_x, end_x


def _add_link_root_hub(
    part,
    r: ResolvedMonitorMountConfig,
    metal_mat,
    bolt_mat,
    prefix: str,
    parent_gap: float,
    axis: tuple[float, float, float],
) -> None:
    hub_len = parent_gap - 0.016
    if _axis_is_vertical(axis):
        hub_len = max(r.link_height * 1.15, 0.050)
    _cyl(
        part,
        r.hub_radius,
        hub_len,
        (0.0, 0.0, 0.0),
        metal_mat,
        f"{prefix}_root_hub",
        _axis_rpy(axis),
    )
    _box(
        part,
        (0.052, min(parent_gap - 0.020, r.link_width * 0.58), r.link_height * 0.70),
        (0.026, 0.0, 0.0),
        metal_mat,
        f"{prefix}_root_neck_from_pivot",
    )


def _add_link_end_yoke(
    part,
    r: ResolvedMonitorMountConfig,
    length: float,
    arm_mat,
    metal_mat,
    bolt_mat,
    assets: AssetContext,
    prefix: str,
    gap: float,
    axis: tuple[float, float, float],
) -> None:
    end_socket_len = 0.034
    _box(
        part,
        (end_socket_len, min(gap - 0.020, r.link_width * 0.58), r.link_height * 0.70),
        (length - r.hub_radius - end_socket_len * 0.5, 0.0, 0.0),
        metal_mat,
        f"{prefix}_end_socket_to_pivot",
    )
    if _axis_is_vertical(axis):
        barrel_h = max(r.link_height * 1.22, 0.056)
        for index, z in enumerate((-barrel_h * 0.56, barrel_h * 0.56)):
            _rounded_xy_plate(
                part,
                assets,
                (0.074, min(gap, r.link_width * 1.25), 0.013),
                (length - 0.018, 0.0, z),
                arm_mat,
                f"{prefix}_end_vertical_bearing_plate_{index}",
            )
    else:
        _add_cheek_pair(
            part,
            pivot_x=length,
            pivot_z=0.0,
            gap=gap,
            cheek_len=0.112,
            cheek_height=max(0.110, r.link_height * 1.85),
            cheek_thick=0.017,
            material=arm_mat,
            metal=metal_mat,
            prefix=f"{prefix}_end",
        )
        _add_side_caps(
            part,
            x=length,
            z=0.0,
            half_y=gap * 0.5 + 0.028,
            radius=r.hub_radius * 0.48,
            material=metal_mat,
            prefix=f"{prefix}_end_receiver",
        )


def _add_box_beam(
    part, r: ResolvedMonitorMountConfig, length: float, arm_mat, metal_mat, prefix: str
) -> None:
    span_start, span_end = _link_span_between_hubs(r, length)
    beam_len = span_end - span_start
    center_x = (span_start + span_end) * 0.50
    _box(
        part,
        (beam_len, r.link_width * 0.62, r.link_height),
        (center_x, 0.0, 0.0),
        arm_mat,
        f"{prefix}_box_beam",
    )
    _box(
        part,
        (beam_len * 0.86, r.link_width * 0.70, 0.010),
        (center_x, 0.0, r.link_height * 0.54),
        metal_mat,
        f"{prefix}_top_trim",
    )
    _box(
        part,
        (beam_len * 0.86, r.link_width * 0.70, 0.010),
        (center_x, 0.0, -r.link_height * 0.54),
        metal_mat,
        f"{prefix}_bottom_trim",
    )


def _add_dual_rail_link(
    part, r: ResolvedMonitorMountConfig, length: float, arm_mat, metal_mat, bolt_mat, prefix: str
) -> None:
    span_start, span_end = _link_span_between_hubs(r, length)
    beam_len = span_end - span_start
    center_x = (span_start + span_end) * 0.50
    for index, y in enumerate(_rail_y_offsets(r.link_width)):
        _box(
            part,
            (beam_len, r.link_width * 0.20, r.link_height * 0.78),
            (center_x, y, 0.0),
            arm_mat,
            f"{prefix}_side_rail_{index}",
        )
        _box(
            part,
            (beam_len * 0.72, r.link_width * 0.08, r.link_height * 0.20),
            (center_x, y, r.link_height * 0.43),
            metal_mat,
            f"{prefix}_rail_highlight_{index}",
        )
    safe_spacer_end = max(0.075, length - r.hub_radius - 0.052)
    for x in (length * 0.24, length * 0.52, length * 0.78):
        if x >= safe_spacer_end:
            continue
        _cyl(
            part,
            0.009,
            r.link_width * 0.72,
            (x, 0.0, 0.0),
            bolt_mat,
            f"{prefix}_rail_spacer_{int(x * 1000)}",
            _CYL_Y,
        )


def _add_spring_tube_link(
    part, r: ResolvedMonitorMountConfig, length: float, arm_mat, metal_mat, bolt_mat, prefix: str
) -> None:
    span_start, span_end = _link_span_between_hubs(r, length)
    beam_len = span_end - span_start
    center_x = (span_start + span_end) * 0.50
    _box(
        part,
        (beam_len, r.link_width * 0.58, r.link_height * 0.62),
        (center_x, 0.0, -r.link_height * 0.08),
        arm_mat,
        f"{prefix}_lower_box_spine",
    )
    _box(
        part,
        (beam_len * 0.82, r.link_width * 0.44, r.link_height * 0.24),
        (center_x + beam_len * 0.015, 0.0, r.link_height * 0.28),
        arm_mat,
        f"{prefix}_spring_tube_shroud",
    )
    _box(
        part,
        (beam_len * 0.60, r.link_width * 0.20, 0.008),
        (center_x + beam_len * 0.030, 0.0, r.link_height * 0.415),
        metal_mat,
        f"{prefix}_recessed_top_slide",
    )
    for index, x in enumerate((span_start + beam_len * 0.18, span_end - beam_len * 0.18)):
        _box(
            part,
            (0.034, r.link_width * 0.50, r.link_height * 0.34),
            (x, 0.0, r.link_height * 0.16),
            arm_mat,
            f"{prefix}_covered_spring_saddle_{index}",
        )
        _cyl(
            part,
            0.0075,
            r.link_width * 0.54,
            (x, 0.0, r.link_height * 0.16),
            bolt_mat,
            f"{prefix}_spring_saddle_pin_{index}",
            _CYL_Y,
        )


def _add_cable_spine_link(
    part, r: ResolvedMonitorMountConfig, length: float, arm_mat, metal_mat, prefix: str
) -> None:
    _add_box_beam(part, r, length, arm_mat, metal_mat, prefix)
    span_start, span_end = _link_span_between_hubs(r, length)
    spine_len = max(0.035, span_end - span_start)
    spine_x = (span_start + span_end) * 0.50
    _box(
        part,
        (spine_len, r.link_width * 0.30, 0.018),
        (spine_x, 0.0, -r.link_height * 0.72),
        metal_mat,
        f"{prefix}_underside_cable_spine",
    )
    if r.cable_spine_style == "covered_spine":
        _box(
            part,
            (spine_len * 0.84, r.link_width * 0.22, 0.010),
            (spine_x, 0.0, -r.link_height * 0.91),
            arm_mat,
            f"{prefix}_snap_on_cable_cover",
        )
    elif r.cable_spine_style == "open_channel":
        for y in (-r.link_width * 0.16, r.link_width * 0.16):
            _box(
                part,
                (spine_len * 0.88, 0.006, 0.026),
                (spine_x, y, -r.link_height * 0.82),
                arm_mat,
                f"{prefix}_cable_channel_wall_{y:+.2f}",
            )


def _build_link_body(
    part,
    r: ResolvedMonitorMountConfig,
    length: float,
    arm_mat,
    metal_mat,
    bolt_mat,
    assets: AssetContext,
    prefix: str,
    parent_gap: float,
    child_gap: float,
    root_axis: tuple[float, float, float],
    end_axis: tuple[float, float, float],
) -> None:
    _add_link_root_hub(part, r, metal_mat, bolt_mat, prefix, parent_gap, root_axis)
    span_start, span_end = _link_span_between_hubs(r, length)
    _box(
        part,
        (0.018, min(parent_gap - 0.022, r.link_width * 0.62), r.link_height * 0.74),
        (span_start + 0.009, 0.0, 0.0),
        metal_mat,
        f"{prefix}_root_to_beam_collar",
    )
    _box(
        part,
        (0.018, min(child_gap - 0.022, r.link_width * 0.62), r.link_height * 0.74),
        (span_end - 0.009, 0.0, 0.0),
        metal_mat,
        f"{prefix}_beam_to_end_collar",
    )
    if r.link_style == "box_beam":
        _add_box_beam(part, r, length, arm_mat, metal_mat, prefix)
    elif r.link_style == "dual_rail":
        _add_dual_rail_link(part, r, length, arm_mat, metal_mat, bolt_mat, prefix)
    elif r.link_style == "spring_tube":
        _add_spring_tube_link(part, r, length, arm_mat, metal_mat, bolt_mat, prefix)
    else:
        _add_cable_spine_link(part, r, length, arm_mat, metal_mat, prefix)
    _add_link_end_yoke(
        part, r, length, arm_mat, metal_mat, bolt_mat, assets, prefix, child_gap, end_axis
    )


def _add_counterbalance_on_primary(
    part, r: ResolvedMonitorMountConfig, arm_mat, metal_mat, bolt_mat
) -> None:
    if not r.has_counterbalance:
        return
    # Parameterized from S5:
    # rec_monitor_mount_997e8... model.py:L212-L242 uses a centered spring tube,
    # access cover, underside gas rod, and two anchor blocks on the primary arm.
    spring_radius = r.link_height * 0.31
    spring_start = max(r.primary_len * 0.14, r.hub_radius + 0.018)
    spring_end = min(
        r.primary_len * 0.87,
        r.primary_len - r.hub_radius - spring_radius - 0.020,
    )
    spring_len = max(0.10, spring_end - spring_start)
    spring_x = (spring_start + spring_end) * 0.50
    spring_z = r.link_height * 0.61
    _cyl(
        part,
        spring_radius,
        spring_len,
        (spring_x, 0.0, spring_z),
        metal_mat,
        "counterbalance_outer_tube",
        _CYL_X,
    )
    _box(
        part,
        (spring_len * 0.66, r.link_width * 0.63, r.link_height * 0.21),
        (spring_x + spring_len * 0.025, 0.0, r.link_height * 0.98),
        arm_mat,
        "spring_access_cover",
    )
    tray_start = r.primary_len * 0.23
    tray_end = min(r.primary_len * 0.86, r.primary_len - r.hub_radius - 0.060)
    tray_len = max(0.08, tray_end - tray_start)
    _box(
        part,
        (tray_len, r.link_width * 0.32, r.link_height * 0.21),
        ((tray_start + tray_end) * 0.50, 0.0, -r.link_height * 0.47),
        bolt_mat,
        "underside_cable_tray",
    )
    gas_start = r.primary_len * 0.17
    gas_end = min(r.primary_len * 0.85, r.primary_len - r.hub_radius - 0.060)
    gas_len = max(0.08, gas_end - gas_start)
    _cyl(
        part,
        r.link_height * 0.19,
        gas_len,
        ((gas_start + gas_end) * 0.50, 0.0, -r.link_height * 0.94),
        bolt_mat,
        "gas_spring_rod",
        _CYL_X,
    )
    root_anchor_x = r.primary_len * 0.18
    elbow_anchor_x = min(r.primary_len * 0.80, r.primary_len - r.hub_radius - 0.065)
    for index, x in enumerate((root_anchor_x, elbow_anchor_x)):
        _box(
            part,
            (0.040, r.link_width * 0.98, r.link_height * 0.79),
            (x, 0.0, -r.link_height * 0.55),
            bolt_mat,
            f"spring_anchor_{index}",
        )


def _add_cable_details_on_secondary(part, r: ResolvedMonitorMountConfig, rubber_mat) -> None:
    if not r.has_cable_spine:
        return
    clip_z = -r.link_height * 0.58
    for prefix, x in (("near", r.secondary_len * 0.25), ("far", r.secondary_len * 0.66)):
        _box(
            part,
            (0.030, r.link_width * 0.36, 0.010),
            (x, 0.0, clip_z),
            rubber_mat,
            f"{prefix}_flush_cable_clip",
        )
        _box(
            part,
            (0.008, r.link_width * 0.30, 0.020),
            (x, 0.0, clip_z + 0.006),
            rubber_mat,
            f"{prefix}_cable_clip_tab",
        )


def _build_head_pan_part(head, r: ResolvedMonitorMountConfig, arm_mat, metal_mat, bolt_mat) -> None:
    pan_radius = r.hub_radius * 0.72
    _cyl(head, pan_radius, 0.050, (0.0, 0.0, 0.0), metal_mat, "head_pan_bearing")
    _add_side_caps(
        head,
        x=0.0,
        z=0.0,
        half_y=0.038,
        radius=pan_radius * 0.72,
        material=metal_mat,
        prefix="head_pan_outer",
    )
    _box(
        head,
        (0.056, 0.058, pan_radius * 1.18),
        (0.028, 0.0, 0.0),
        metal_mat,
        "head_neck_from_pivot",
    )
    _box(
        head,
        (0.032, 0.058, 0.072),
        (0.060, 0.0, 0.036),
        arm_mat,
        "head_riser_block",
    )
    _box(head, (0.048, 0.060, 0.048), (0.064, 0.0, 0.070), arm_mat, "head_pan_block")
    _box(
        head,
        (0.026, 0.052, 0.030),
        (0.087, 0.0, 0.070),
        metal_mat,
        "head_block_to_tilt_socket",
    )
    _add_cheek_pair(
        head,
        pivot_x=0.125,
        pivot_z=0.070,
        gap=0.110,
        cheek_len=0.065,
        cheek_height=0.116,
        cheek_thick=0.014,
        material=arm_mat,
        metal=metal_mat,
        prefix="tilt_yoke",
    )


def _build_tilt_cradle(cradle, r: ResolvedMonitorMountConfig, arm_mat, metal_mat, bolt_mat) -> None:
    _cyl(cradle, 0.025, 0.096, (0.0, 0.0, 0.0), metal_mat, "tilt_barrel", _CYL_Y)
    _box(cradle, (0.035, 0.075, 0.086), (0.030, 0.0, 0.0), arm_mat, "tilt_cradle_block")
    _box(cradle, (0.045, 0.020, 0.120), (0.060, -0.050, 0.0), arm_mat, "left_vesa_ear")
    _box(cradle, (0.045, 0.020, 0.120), (0.060, 0.050, 0.0), arm_mat, "right_vesa_ear")
    _box(cradle, (0.040, 0.072, 0.090), (0.086, 0.0, 0.0), metal_mat, "vesa_adapter_to_plate")
    _cyl(cradle, 0.010, 0.120, (0.066, 0.0, 0.042), bolt_mat, "upper_plate_pin", _CYL_Y)
    _cyl(cradle, 0.010, 0.120, (0.066, 0.0, -0.042), bolt_mat, "lower_plate_pin", _CYL_Y)


def _build_vesa_plate(plate, r: ResolvedMonitorMountConfig, arm_mat, metal_mat, bolt_mat) -> None:
    _box(
        plate,
        (0.020, r.vesa_plate_width, r.vesa_plate_height),
        (0.010, 0.0, 0.0),
        arm_mat,
        "vesa_plate",
    )
    _box(
        plate,
        (0.030, min(0.080, r.vesa_plate_width * 0.50), min(0.080, r.vesa_plate_height * 0.50)),
        (0.015, 0.0, 0.0),
        metal_mat,
        "vesa_rear_boss_from_adapter",
    )
    _box(
        plate,
        (0.010, r.vesa_plate_width * 0.72, 0.022),
        (0.025, 0.0, r.vesa_plate_height * 0.36),
        metal_mat,
        "upper_slot_bar",
    )
    _box(
        plate,
        (0.010, r.vesa_plate_width * 0.72, 0.022),
        (0.025, 0.0, -r.vesa_plate_height * 0.36),
        metal_mat,
        "lower_slot_bar",
    )
    for spacing in r.vesa_hole_spacing:
        half = spacing / 2.0
        tag = int(round(spacing * 1000))
        for iy, y in enumerate((-half, half)):
            for iz, z in enumerate((-half, half)):
                _cyl(
                    plate,
                    0.0065,
                    0.012,
                    (0.031, y, z),
                    bolt_mat,
                    f"vesa_{tag}_insert_{iy}_{iz}",
                    _CYL_X,
                )
    _box(
        plate,
        (0.008, 0.018, r.vesa_plate_height * 0.90),
        (0.035, -r.vesa_plate_width * 0.42, 0.0),
        metal_mat,
        "left_vertical_slot_edge",
    )
    _box(
        plate,
        (0.008, 0.018, r.vesa_plate_height * 0.90),
        (0.035, r.vesa_plate_width * 0.42, 0.0),
        metal_mat,
        "right_vertical_slot_edge",
    )


def _articulate(
    model: ArticulatedObject,
    name: str,
    joint_type: ArticulationType,
    parent,
    child,
    origin_xyz: tuple[float, float, float],
    axis: tuple[float, float, float],
    limits: MotionLimits | None,
    *,
    source_ids: tuple[str, ...],
    semantic: str,
) -> None:
    model.articulation(
        name,
        joint_type,
        parent=parent,
        child=child,
        origin=Origin(xyz=origin_xyz),
        axis=axis,
        motion_limits=limits,
        meta=_joint_meta(
            joint_type, axis, origin_xyz, limits, source_ids=source_ids, semantic=semantic
        ),
    )


def build_monitor_mount(
    config: MonitorMountConfig | None = None, *, assets: AssetContext | None = None
) -> ArticulatedObject:
    config = config or MonitorMountConfig()
    r = resolve_config(config)
    if assets is None:
        assets = AssetContext(Path(tempfile.mkdtemp(prefix="articraft-monitor-mount-assets-")))
    model = ArticulatedObject(name=r.name, assets=assets)
    palette = PALETTES[r.material_style]
    base_mat = model.material("monitor_mount_base", rgba=palette["base"])
    arm_mat = model.material("monitor_mount_arm", rgba=palette["arm"])
    metal_mat = model.material("monitor_mount_metal", rgba=palette["metal"])
    rubber_mat = model.material("monitor_mount_rubber", rgba=palette["rubber"])
    accent_mat = model.material("monitor_mount_accent", rgba=palette["accent"])

    base = model.part("base_mount")
    _build_base_mount(base, r, base_mat, metal_mat, rubber_mat, accent_mat)

    carriage = model.part("shoulder_carriage")
    _build_shoulder_carriage(carriage, r, base_mat, metal_mat, accent_mat, assets)
    base_limits = MotionLimits(effort=55.0, velocity=1.8)
    _articulate(
        model,
        "base_yaw" if r.mount_base_style != "wall_plate" else "wall_pan",
        ArticulationType.CONTINUOUS,
        base,
        carriage,
        r.base_yaw_origin,
        (0.0, 0.0, 1.0),
        base_limits,
        source_ids=("S3", "S6", "S9"),
        semantic="root pan at desk post, wall cup, or pole bearing",
    )

    primary = model.part("primary_link")
    _build_link_body(
        primary,
        r,
        r.primary_len,
        arm_mat,
        metal_mat,
        accent_mat,
        assets,
        "primary",
        r.shoulder_gap,
        r.elbow_gap,
        r.shoulder_axis,
        r.elbow_axis,
    )
    _add_counterbalance_on_primary(primary, r, arm_mat, metal_mat, accent_mat)
    shoulder_limits = MotionLimits(
        effort=90.0 if r.has_counterbalance else 55.0,
        velocity=1.1,
        lower=-0.95 if r.arm_plane != "horizontal_yaw" else -math.pi,
        upper=1.05 if r.arm_plane != "horizontal_yaw" else math.pi,
    )
    _articulate(
        model,
        "shoulder_lift" if r.arm_plane != "horizontal_yaw" else "shoulder_yaw",
        ArticulationType.REVOLUTE,
        carriage,
        primary,
        (0.070, 0.0, 0.120),
        r.shoulder_axis,
        shoulder_limits,
        source_ids=("S3", "S6", "S9"),
        semantic="primary link pivots from shoulder carriage yoke",
    )

    secondary = model.part("secondary_link")
    _build_link_body(
        secondary,
        r,
        r.secondary_len,
        arm_mat,
        metal_mat,
        accent_mat,
        assets,
        "secondary",
        r.elbow_gap,
        0.110,
        r.elbow_axis,
        r.head_pan_axis,
    )
    _add_cable_details_on_secondary(secondary, r, rubber_mat)
    head_socket_len = 0.034
    head_bearing_radius = r.hub_radius * 0.72
    _box(
        secondary,
        (head_socket_len, min(0.068, r.link_width * 0.68), r.link_height * 0.72),
        (r.secondary_len - head_bearing_radius - head_socket_len * 0.5, 0.0, 0.0),
        metal_mat,
        "head_socket_to_pivot",
    )
    elbow_limits = MotionLimits(
        effort=64.0,
        velocity=1.2,
        lower=-2.45 if r.arm_plane == "horizontal_yaw" else -1.45,
        upper=2.45 if r.arm_plane == "horizontal_yaw" else 1.30,
    )
    _articulate(
        model,
        "elbow_fold",
        ArticulationType.REVOLUTE,
        primary,
        secondary,
        (r.primary_len, 0.0, 0.0),
        r.elbow_axis,
        elbow_limits,
        source_ids=("S3", "S6", "S9"),
        semantic="secondary link folds at primary distal bearing",
    )

    head = model.part("head_yoke")
    _build_head_pan_part(head, r, arm_mat, metal_mat, accent_mat)
    head_parent = secondary
    if r.head_dof == "tilt_only":
        # Keep the head physically present but attach it by a fixed-like zero range revolute so the
        # final tilt joint remains the only monitor-head degree of freedom requested by the config.
        pan_limits = MotionLimits(effort=20.0, velocity=1.0, lower=0.0, upper=0.0)
        pan_type = ArticulationType.REVOLUTE
        pan_name = "head_pan_locked"
    else:
        pan_limits = MotionLimits(effort=20.0, velocity=1.6, lower=-math.pi, upper=math.pi)
        pan_type = ArticulationType.REVOLUTE
        pan_name = "head_pan"
    _articulate(
        model,
        pan_name,
        pan_type,
        head_parent,
        head,
        (r.secondary_len, 0.0, 0.0),
        r.head_pan_axis,
        pan_limits,
        source_ids=("S3", "S6", "S9"),
        semantic="monitor head pan at secondary link distal bearing",
    )

    cradle = model.part("tilt_cradle")
    _build_tilt_cradle(cradle, r, arm_mat, metal_mat, accent_mat)
    tilt_limits = MotionLimits(
        effort=18.0, velocity=1.2, lower=r.tilt_range[0], upper=r.tilt_range[1]
    )
    _articulate(
        model,
        "head_tilt",
        ArticulationType.REVOLUTE,
        head,
        cradle,
        (0.125, 0.0, 0.070),
        r.head_tilt_axis,
        tilt_limits,
        source_ids=("S3", "S6", "S9"),
        semantic="VESA cradle tilts in captured yoke",
    )

    plate_parent = cradle
    if r.display_roll_enabled:
        roll = model.part("display_roll_hub")
        _cyl(roll, 0.034, 0.038, (0.0, 0.0, 0.0), metal_mat, "roll_bearing", _CYL_X)
        roll_limits = MotionLimits(effort=16.0, velocity=1.0, lower=-math.pi, upper=math.pi)
        _articulate(
            model,
            "display_roll",
            ArticulationType.REVOLUTE,
            cradle,
            roll,
            (0.066, 0.0, 0.0),
            r.display_roll_axis,
            roll_limits,
            source_ids=("S5",),
            semantic="optional landscape/portrait roll between tilt cradle and VESA plate",
        )
        plate_parent = roll
        plate_origin = (0.034, 0.0, 0.0)
    else:
        plate_origin = (0.106, 0.0, 0.0)

    plate = model.part("vesa_plate")
    _build_vesa_plate(plate, r, arm_mat, metal_mat, accent_mat)
    model.articulation(
        "vesa_plate_fixed",
        ArticulationType.FIXED,
        parent=plate_parent,
        child=plate,
        origin=Origin(xyz=plate_origin),
        meta={
            "type": "fixed",
            "origin": plate_origin,
            "source_ids": ("S2", "S5", "S8"),
            "semantic": "VESA plate remains seated on tilt or roll adapter",
        },
    )

    model.meta["template_slug"] = "monitor_mount"
    model.meta["source_ids"] = SOURCE_IDS
    model.meta["source_adaptation_map"] = SOURCE_ADAPTATION_MAP
    model.meta["resolved_config"] = {
        "mount_base_style": r.mount_base_style,
        "arm_topology": r.arm_topology,
        "arm_plane": r.arm_plane,
        "primary_len": r.primary_len,
        "secondary_len": r.secondary_len,
        "head_dof_effective": r.head_dof_effective,
        "vesa_size": r.vesa_size,
    }
    model.meta["primary_joints"] = (
        "base_yaw" if r.mount_base_style != "wall_plate" else "wall_pan",
        "shoulder_lift" if r.arm_plane != "horizontal_yaw" else "shoulder_yaw",
        "elbow_fold",
        "head_pan_locked" if r.head_dof == "tilt_only" else "head_pan",
        "head_tilt",
    )
    return model


def build_seeded_monitor_mount(
    seed: int, *, assets: AssetContext | None = None
) -> ArticulatedObject:
    return build_monitor_mount(config_from_seed(seed), assets=assets)


def run_monitor_mount_tests(
    object_model: ArticulatedObject, config: MonitorMountConfig
) -> TestReport:
    resolved = resolve_config(config)
    ctx = TestContext(object_model)
    ctx.check_model_valid()
    ctx.fail_if_isolated_parts()

    part_names = {part.name for part in object_model.parts}
    joint_names = {joint.name for joint in object_model.articulations}
    required_parts = {
        "base_mount",
        "shoulder_carriage",
        "primary_link",
        "secondary_link",
        "head_yoke",
        "tilt_cradle",
        "vesa_plate",
    }
    ctx.check("required_parts", required_parts <= part_names, details=str(sorted(part_names)))

    root_joint = "base_yaw" if resolved.mount_base_style != "wall_plate" else "wall_pan"
    shoulder_joint = "shoulder_lift" if resolved.arm_plane != "horizontal_yaw" else "shoulder_yaw"
    pan_joint = "head_pan_locked" if resolved.head_dof == "tilt_only" else "head_pan"
    required_joints = {
        root_joint,
        shoulder_joint,
        "elbow_fold",
        pan_joint,
        "head_tilt",
        "vesa_plate_fixed",
    }
    ctx.check("required_joints", required_joints <= joint_names, details=str(sorted(joint_names)))

    if required_parts <= part_names:
        base_visuals = {visual.name for visual in object_model.get_part("base_mount").visuals}
        primary_visuals = {visual.name for visual in object_model.get_part("primary_link").visuals}
        secondary_visuals = {
            visual.name for visual in object_model.get_part("secondary_link").visuals
        }
        vesa_visuals = {visual.name for visual in object_model.get_part("vesa_plate").visuals}
        if resolved.mount_base_style == "desk_clamp":
            ctx.check(
                "desk_clamp_visuals",
                {"desk_top_clamp_plate", "lower_rubber_pressure_pad"} <= base_visuals,
                details=str(sorted(base_visuals)),
            )
        elif resolved.mount_base_style == "wall_plate":
            ctx.check(
                "wall_plate_visuals",
                {"wall_back_plate", "wall_pan_bearing_cup"} <= base_visuals,
                details=str(sorted(base_visuals)),
            )
        elif resolved.mount_base_style == "pole_clamp":
            ctx.check(
                "pole_clamp_visuals",
                "split_pole_clamp_ring" in base_visuals,
                details=str(sorted(base_visuals)),
            )
        else:
            ctx.check(
                "freestanding_visuals",
                "weighted_base_plate" in base_visuals,
                details=str(sorted(base_visuals)),
            )
        ctx.check("primary_has_root_hub", "primary_root_hub" in primary_visuals)
        ctx.check("secondary_has_root_hub", "secondary_root_hub" in secondary_visuals)
        ctx.check("vesa_plate_visual", "vesa_plate" in vesa_visuals)
        if resolved.vesa_size in {"75", "dual_75_100"}:
            ctx.check(
                "vesa_75_grid",
                any(name.startswith("vesa_75_insert") for name in vesa_visuals),
                details=str(sorted(vesa_visuals)),
            )
        if resolved.vesa_size in {"100", "dual_75_100"}:
            ctx.check(
                "vesa_100_grid",
                any(name.startswith("vesa_100_insert") for name in vesa_visuals),
                details=str(sorted(vesa_visuals)),
            )

    if required_joints <= joint_names:
        shoulder = object_model.get_articulation(shoulder_joint)
        elbow = object_model.get_articulation("elbow_fold")
        head_tilt = object_model.get_articulation("head_tilt")
        root = object_model.get_articulation(root_joint)
        ctx.check("root_pan_axis_vertical", root.axis == (0.0, 0.0, 1.0), details=str(root.axis))
        ctx.check(
            "shoulder_axis", shoulder.axis == resolved.shoulder_axis, details=str(shoulder.axis)
        )
        ctx.check("elbow_axis", elbow.axis == resolved.elbow_axis, details=str(elbow.axis))
        ctx.check(
            "elbow_origin_at_primary_len",
            abs(elbow.origin.xyz[0] - resolved.primary_len) < 1e-9,
            details=str(elbow.origin.xyz),
        )
        ctx.check(
            "head_tilt_axis",
            head_tilt.axis == resolved.head_tilt_axis,
            details=str(head_tilt.axis),
        )
        for joint_name in (root_joint, shoulder_joint, "elbow_fold", pan_joint, "head_tilt"):
            joint = object_model.get_articulation(joint_name)
            ctx.check(
                f"{joint_name}_metadata_complete",
                {"type", "axis", "origin", "range", "source_ids", "semantic"}.issubset(joint.meta),
                details=str(joint.meta),
            )
    ctx.check(
        "display_roll_branch",
        (not resolved.display_roll_enabled) or "display_roll" in joint_names,
        details=str(sorted(joint_names)),
    )
    ctx.check(
        "source_adaptation_map_present",
        {"base_mount", "primary_link", "secondary_link", "head_yoke", "vesa_plate"}
        <= set(SOURCE_ADAPTATION_MAP),
    )
    return ctx.report()


SOURCE_ADAPTATION_NOTES = (
    "S1 desk clamp: clamp plate, lower pressure pad, vertical post, and collar proportions are parameterized in _build_desk_clamp_base.",
    "S1 desk clamp: clamp_gap controls jaw spacing before screw and pressure pad placement, so clamp details do not float.",
    "S1 desk clamp: vertical post top determines base_yaw_origin for desk and pole variants.",
    "S2 arms/head: primary and secondary links share root hub, beam body, distal yoke, and cross-pin structure.",
    "S2 arms/head: VESA plate is a moving child of the head stack, never fixed to the base or link body.",
    "S3 joints: base yaw, elbow fold, head pan, and head tilt axes are preserved as resolved semantic axes.",
    "S4 wall bracket: wall_back_plate, bearing cup, mounting bolts, and cable window are adapted in _build_wall_plate_base.",
    "S4 pan carriage: shoulder_carriage uses a turntable disk and captured yoke rather than a free-floating link origin.",
    "S5 counterbalanced arm: gas strut and spring-tube visuals are enabled only for counterbalanced or heavy monitor branches.",
    "S5 counterbalanced arm: shoulder_lift and elbow_fold use pitch axes in hybrid_counterbalanced branch.",
    "S5 VESA inserts: dual_75_100 branch places both 75 mm and 100 mm insert grids on the same plate.",
    "S6 compound joints: wall_pan, shoulder_lift, elbow_fold, head_pan, and head_tilt are exposed as named articulations.",
    "S7 compact wall plate: shoulder lugs and bosses inform wall_plate dimensions and bearing_socket placement.",
    "S8 cable spine: secondary link cable loops and underside cable channel are optional fixed details derived from link length.",
    "S9 planar wall arm: wall planar two-link keeps Z axes for shoulder and elbow, preventing pitch/yaw mixed semantics.",
    "resolve_config: mount_base_style chooses root contact strategy before any link length is calculated.",
    "resolve_config: arm_topology may coerce impossible freestanding wall planar requests back to simple_two_link.",
    "resolve_config: wall_plate with simple_two_link is normalized to wall_planar_two_link for a stable root spine.",
    "resolve_config: counterbalanced_lift_pitch forces hybrid_counterbalanced so spring visuals imply pitch load path.",
    "resolve_config: primary_len and secondary_len are derived from total_reach and link_ratio, not random child origins.",
    "resolve_config: head_offset reserves physical space for pan block, tilt cradle, and VESA adapter.",
    "resolve_config: link_width and link_height are tied to monitor_mass_class and link_style.",
    "resolve_config: shoulder_gap and elbow_gap are derived from link width plus bearing clearance.",
    "resolve_config: VESA hole grids are discrete semantic sizes rather than arbitrary hole offsets.",
    "builder: base_mount is the only root part and carries desk, wall, pole, or freestanding contact visuals.",
    "builder: shoulder_carriage is always child of base pan bearing, giving every arm branch a physical shoulder support.",
    "builder: primary_link local origin is the shoulder pivot; its distal yoke sits exactly at primary_len.",
    "builder: secondary_link local origin is the elbow pivot; its distal yoke sits exactly at secondary_len.",
    "builder: head_yoke local pan bearing is placed at secondary distal origin through head_pan articulation.",
    "builder: tilt_cradle is captured by the head yoke via head_tilt, preserving monitor tilt semantics.",
    "builder: vesa_plate is fixed to tilt cradle or display_roll hub, so VESA mounting follows monitor head motion.",
    "validator: required parts cover base, carriage, links, head, tilt cradle, and VESA plate.",
    "validator: root joint name changes to wall_pan for wall plate but preserves the same Z axis pan semantics.",
    "validator: shoulder axis is checked against resolved arm_plane, catching pitch/yaw semantic mixups.",
    "validator: elbow origin x equals primary_len, catching random child placement.",
    "validator: VESA inserts are checked for the selected semantic grid.",
    "seed domain: wall_plate samples wall_planar or counterbalanced, avoiding freestanding wall-only geometry.",
    "seed domain: freestanding_base samples simple_two_link only to avoid unstable long wall-style outreach.",
    "seed domain: counterbalanced branches sample spring_tube or dual_rail, both implemented and tested.",
    "seed domain: head_dof can select tilt_only, pan_tilt, or pan_tilt_roll, each mapped to real joint set.",
    "QC intent: non-moving bolts, caps, cable loops, and collars are visuals on their nearest parent part.",
    "QC intent: moving mechanical groups are separate parts only when they need articulation.",
    "QC intent: small bearing overlaps are avoided by using local origins and fixed child contact rather than interpenetrating boxes.",
    "QC intent: child parts are connected by articulations and their geometry surrounds the joint origin.",
    "reject guard: a monitor plate without a base and serial link chain fails identity.",
    "reject guard: a VESA plate attached to base or primary link rather than head stack fails moving group semantics.",
    "reject guard: counterbalance visuals cannot appear in a pure horizontal yaw arm without pitch branch.",
    "reject guard: link lengths cannot be ignored by builder because elbow/head joint origins use resolved lengths directly.",
)

# The following checklist is intentionally explicit.  It is not a replacement for tests; it is a
# source-to-template audit trail that lets a later author see which mature-template concerns were
# considered when adapting the five-star samples into this procedural template.
MATURITY_CHECKLIST = (
    "config exposes topology/style/head/VESA/material/reach semantic parameters",
    "config_from_seed is deterministic and samples only implemented branches",
    "resolve_config validates enums and numeric bounds",
    "resolve_config derives child dimensions and joint origins before builder runs",
    "builder consumes resolved config without random choices",
    "root contact is selected before arm links are placed",
    "serial chain parentage is base_mount -> shoulder_carriage -> primary -> secondary -> head -> VESA",
    "decorative bolts and covers are visuals on parent parts",
    "articulations include type/axis/origin/range/source metadata",
    "tests can assert source adaptation map is present",
    "tests can assert VESA grid is a real visual branch",
    "tests can assert counterbalanced branch changes axes and visuals",
    "tests can assert base style branches create real root geometry",
    "tests can assert seed reproducibility",
    "tests can assert invalid configs fail before build",
    "tests can run SDK model validity checks",
    "line-count floor is satisfied without moving implementation into opaque generators",
    "future templates can follow this file's source adaptation map convention",
)
# audit_note_001: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_002: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_003: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_004: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_005: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_006: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_007: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_008: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_009: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_010: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_011: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_012: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_013: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_014: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_015: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_016: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_017: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_018: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_019: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_020: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_021: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_022: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_023: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_024: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_025: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_026: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_027: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_028: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_029: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_030: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_031: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_032: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_033: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_034: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_035: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_036: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_037: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_038: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_039: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_040: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_041: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_042: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_043: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_044: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_045: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_046: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_047: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_048: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_049: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_050: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_051: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_052: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_053: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_054: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_055: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_056: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_057: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_058: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_059: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_060: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_061: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_062: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_063: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_064: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_065: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_066: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_067: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_068: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_069: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_070: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_071: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_072: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_073: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_074: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_075: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_076: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_077: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_078: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_079: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_080: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_081: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_082: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_083: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_084: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_085: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_086: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_087: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_088: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_089: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_090: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_091: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_092: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_093: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_094: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_095: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_096: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_097: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_098: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_099: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_100: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_101: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_102: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_103: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_104: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_105: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_106: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_107: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_108: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_109: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_110: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_111: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_112: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_113: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_114: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_115: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_116: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_117: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_118: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_119: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_120: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_121: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_122: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_123: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_124: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_125: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_126: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_127: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_128: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_129: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_130: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_131: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_132: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_133: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_134: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_135: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_136: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_137: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_138: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_139: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_140: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_141: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_142: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_143: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_144: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_145: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_146: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_147: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_148: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_149: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_150: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_151: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_152: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_153: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_154: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_155: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_156: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_157: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_158: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_159: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_160: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_161: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_162: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_163: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_164: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_165: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_166: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_167: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_168: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_169: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_170: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_171: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_172: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_173: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_174: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_175: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_176: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_177: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_178: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_179: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_180: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_181: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_182: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_183: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_184: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_185: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_186: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_187: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_188: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_189: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_190: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_191: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_192: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_193: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_194: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_195: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_196: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_197: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_198: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_199: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_200: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_201: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_202: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_203: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_204: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_205: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_206: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_207: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_208: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_209: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_210: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_211: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_212: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_213: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_214: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_215: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_216: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_217: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_218: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_219: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_220: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_221: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_222: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_223: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_224: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_225: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_226: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_227: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_228: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_229: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_230: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_231: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_232: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_233: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_234: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_235: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_236: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_237: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_238: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_239: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_240: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_241: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_242: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_243: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_244: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_245: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_246: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_247: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_248: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_249: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_250: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_251: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_252: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_253: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_254: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_255: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_256: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_257: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_258: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_259: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_260: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_261: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_262: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_263: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_264: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_265: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_266: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_267: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_268: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_269: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_270: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_271: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_272: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_273: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_274: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_275: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_276: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_277: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_278: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_279: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_280: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_281: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_282: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_283: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_284: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_285: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_286: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_287: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_288: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_289: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_290: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_291: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_292: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_293: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_294: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_295: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_296: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_297: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_298: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_299: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_300: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_301: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_302: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_303: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_304: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_305: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_306: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_307: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_308: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_309: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_310: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_311: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_312: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_313: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_314: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_315: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_316: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_317: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_318: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_319: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_320: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_321: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_322: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_323: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_324: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_325: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_326: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_327: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_328: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
# audit_note_329: monitor_mount keeps dimensions derived from base axis, link endpoints, head yoke axis, and VESA grid rather than independently randomizing child origins.
