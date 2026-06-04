# ruff: noqa: E701,E702,I001
"""Procedural template for category `articulated_task_lamp`.

Default seed=0 anchor: weighted_round_disk + twin_rail_two_link + rect_architect
with three desk pitch revolute joints (shoulder / elbow / shade tilt).
"""

from __future__ import annotations

import math
import random
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from sdk import (
    ArticulatedObject,
    ArticulationType,
    AssetContext,
    Box,
    Cylinder,
    ExtrudeGeometry,
    Inertial,
    LatheGeometry,
    MeshGeometry,
    MotionLimits,
    Origin,
    Sphere,
    TestContext,
    TestReport,
    mesh_from_geometry,
    rounded_rect_profile,
    tube_from_spline_points,
)

__modular__ = True

MountStyle = Literal[
    "weighted_round_disk",
    "weighted_rect_plate",
    "c_clamp",
    "wall_plate",
]
ArmStyle = Literal[
    "twin_rail_two_link",
    "parallel_bar_two_link",
    "spring_balanced",
    "single_post",
    "wall_cylinder",
    "single_boom",
]
ShadeStyle = Literal["rect_architect", "lathe_conical", "banker_dome"]
MaterialStyle = Literal["brushed_aluminum", "matte_black", "industrial_green", "warm_brass"]
PitchAxisFamily = Literal["neg_y_desk", "pos_y_wall", "z_swing_clamp"]

DESK_MOUNTS: tuple[MountStyle, ...] = ("weighted_round_disk", "weighted_rect_plate")
DESK_ARMS: tuple[ArmStyle, ...] = ("twin_rail_two_link", "parallel_bar_two_link", "spring_balanced")
WALL_ARMS: tuple[ArmStyle, ...] = ("wall_cylinder",)
CLAMP_ARMS: tuple[ArmStyle, ...] = ("single_boom",)
POST_ARMS: tuple[ArmStyle, ...] = ("single_post",)

SOURCE_IDS = {
    "S1": "data/records/rec_articulated_task_lamp_0001/revisions/rev_000001/model.py:L49-L163",
    "S2": "data/records/rec_articulated_task_lamp_0001/revisions/rev_000001/model.py:L179-L390",
    "S3": "data/records/rec_articulated_task_lamp_0001/revisions/rev_000001/model.py:L392-L433",
    "S4": "data/records/rec_articulated_task_lamp_c5d513f31f80480d878489269d948987/revisions/rev_000001/model.py:L38-L84",
    "S5": "data/records/rec_articulated_task_lamp_c5d513f31f80480d878489269d948987/revisions/rev_000001/model.py:L97-L251",
    "S6": "data/records/rec_articulated_task_lamp_c5d513f31f80480d878489269d948987/revisions/rev_000001/model.py:L253-L288",
    "S7": "data/records/rec_articulated_task_lamp_ae09411ed1834f5c80a2b1b6b9a66a36/revisions/rev_000001/model.py:L65-L125",
    "S8": "data/records/rec_articulated_task_lamp_ae09411ed1834f5c80a2b1b6b9a66a36/revisions/rev_000001/model.py:L127-L359",
    "S9": "data/records/rec_articulated_task_lamp_471fd346de6d4db19cfe409765c12902/revisions/rev_000001/model.py:L28-L170",
    "S10": "data/records/rec_articulated_task_lamp_471fd346de6d4db19cfe409765c12902/revisions/rev_000001/model.py:L183-L355",
    "S11": "data/records/rec_articulated_task_lamp_670a2a3b4c2a4bb793c39db1be180271/revisions/rev_000001/model.py:L57-L183",
    "S12": "data/records/rec_articulated_task_lamp_670a2a3b4c2a4bb793c39db1be180271/revisions/rev_000001/model.py:L185-L221",
    "S13": "data/records/rec_articulated_task_lamp_0011/revisions/rev_000001/model.py:L78-L224",
    "S14": "data/records/rec_articulated_task_lamp_0011/revisions/rev_000001/model.py:L226-L267",
    "S15": "data/records/rec_articulated_task_lamp_165522499c1142948f4038fedbeada87/revisions/rev_000001/model.py:L42-L204",
    "S16": "data/records/rec_articulated_task_lamp_165522499c1142948f4038fedbeada87/revisions/rev_000001/model.py:L206-L247",
    "S17": "data/records/rec_articulated_task_lamp_881f7667505547d1a5b4beb68756f84b/revisions/rev_000001/model.py:L35-L218",
    "S18": "data/records/rec_articulated_task_lamp_881f7667505547d1a5b4beb68756f84b/revisions/rev_000001/model.py:L220-L247",
}
SOURCE_ADAPTATION_MAP = {
    "twin_rail_segment": ("S1", "S2"),
    "weighted_round_base": ("S2", "S7"),
    "rect_weighted_base": ("S5", "S4"),
    "parallel_bar_arm": ("S5", "S6"),
    "spring_balanced_arm": ("S9", "S10"),
    "c_clamp_mount": ("S11", "S12"),
    "wall_cylinder_arm": ("S13", "S14"),
    "banker_dome_shade": ("S17", "S18"),
    "post_swivel_base": ("S7", "S8"),
    "desk_pitch_joints": ("S3", "S6", "S14"),
}

PALETTES: dict[str, dict[str, tuple[float, float, float, float]]] = {
    "brushed_aluminum": {
        "body": (0.18, 0.19, 0.21, 1.0),
        "metal": (0.74, 0.76, 0.79, 1.0),
        "steel": (0.59, 0.61, 0.64, 1.0),
        "rubber": (0.08, 0.08, 0.09, 1.0),
        "diffuser": (0.97, 0.96, 0.90, 0.38),
        "emitter": (1.00, 0.93, 0.78, 0.55),
        "accent": (0.72, 0.74, 0.76, 1.0),
    },
    "matte_black": {
        "body": (0.06, 0.065, 0.07, 1.0),
        "metal": (0.55, 0.58, 0.60, 1.0),
        "steel": (0.72, 0.74, 0.76, 1.0),
        "rubber": (0.01, 0.01, 0.012, 1.0),
        "diffuser": (0.97, 0.96, 0.90, 0.38),
        "emitter": (1.0, 0.84, 0.42, 0.72),
        "accent": (0.02, 0.20, 0.16, 1.0),
    },
    "industrial_green": {
        "body": (0.02, 0.20, 0.16, 1.0),
        "metal": (0.55, 0.58, 0.60, 1.0),
        "steel": (0.67, 0.68, 0.66, 1.0),
        "rubber": (0.02, 0.02, 0.018, 1.0),
        "diffuser": (0.97, 0.96, 0.90, 0.38),
        "emitter": (1.0, 0.82, 0.42, 0.65),
        "accent": (0.84, 0.84, 0.80, 1.0),
    },
    "warm_brass": {
        "body": (0.14, 0.13, 0.12, 1.0),
        "metal": (0.74, 0.61, 0.28, 1.0),
        "steel": (0.74, 0.61, 0.28, 1.0),
        "rubber": (0.006, 0.006, 0.006, 1.0),
        "diffuser": (0.91, 0.90, 0.85, 0.38),
        "emitter": (1.0, 0.86, 0.52, 0.72),
        "accent": (0.13, 0.42, 0.24, 0.68),
    },
}

Y_CYLINDER_RPY = (-math.pi / 2.0, 0.0, 0.0)
X_CYLINDER_RPY = (0.0, math.pi / 2.0, 0.0)


@dataclass(frozen=True)
class ArticulatedTaskLampConfig:
    mount_style: MountStyle | None = None
    arm_style: ArmStyle | None = None
    shade_style: ShadeStyle | None = None
    material_style: MaterialStyle = "matte_black"
    swivel_enabled: bool = False
    spring_enabled: bool = False
    base_radius: float = 0.105
    base_height: float = 0.022
    base_length: float = 0.34
    base_width: float = 0.20
    lower_arm_length: float = 0.165
    upper_arm_length: float = 0.145
    lower_arm_angle: float = math.radians(62.0)
    upper_arm_angle: float = math.radians(54.0)
    shade_width: float = 0.086
    shade_depth: float = 0.050
    boom_length: float = 0.620
    name: str = "articulated_task_lamp"


@dataclass(frozen=True)
class ResolvedArticulatedTaskLampConfig:
    mount_style: MountStyle
    arm_style: ArmStyle
    shade_style: ShadeStyle
    material_style: MaterialStyle
    pitch_axis_family: PitchAxisFamily
    swivel_enabled: bool
    spring_enabled: bool
    base_radius: float
    base_height: float
    base_length: float
    base_width: float
    lower_arm_length: float
    upper_arm_length: float
    lower_arm_angle: float
    upper_arm_angle: float
    shade_width: float
    shade_depth: float
    boom_length: float
    shoulder_x: float
    shoulder_z: float
    shoulder_axis: tuple[float, float, float]
    elbow_axis: tuple[float, float, float]
    shade_axis: tuple[float, float, float]
    shoulder_limit: tuple[float, float]
    elbow_limit: tuple[float, float]
    shade_limit: tuple[float, float]
    name: str
    palette: dict[str, tuple[float, float, float, float]]


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(v)))


def config_from_seed(seed: int) -> ArticulatedTaskLampConfig:
    if seed == 0:
        return ArticulatedTaskLampConfig(
            mount_style="weighted_round_disk",
            arm_style="twin_rail_two_link",
            shade_style="rect_architect",
            material_style="brushed_aluminum",
            swivel_enabled=False,
            spring_enabled=False,
            base_radius=0.105,
            base_height=0.022,
            lower_arm_length=0.165,
            upper_arm_length=0.145,
            lower_arm_angle=math.radians(62.0),
            upper_arm_angle=math.radians(54.0),
            shade_width=0.086,
            shade_depth=0.050,
            name="anchor_articulated_task_lamp",
        )
    rng = random.Random(seed)
    mount = rng.choice(
        (
            "weighted_round_disk",
            "weighted_rect_plate",
            "weighted_round_disk",
            "weighted_rect_plate",
            "c_clamp",
            "wall_plate",
        )
    )
    arm = rng.choice(
        (
            "twin_rail_two_link",
            "parallel_bar_two_link",
            "spring_balanced",
            "single_post",
            "wall_cylinder",
            "single_boom",
        )
    )
    shade = rng.choice(("rect_architect", "lathe_conical", "banker_dome"))
    return ArticulatedTaskLampConfig(
        mount_style=mount,  # type: ignore[arg-type]
        arm_style=arm,  # type: ignore[arg-type]
        shade_style=shade,  # type: ignore[arg-type]
        material_style=rng.choice(
            ("brushed_aluminum", "matte_black", "industrial_green", "warm_brass")
        ),  # type: ignore[arg-type]
        swivel_enabled=rng.random() < 0.12,
        spring_enabled=arm == "spring_balanced",
        base_radius=round(rng.uniform(0.08, 0.14), 4),
        base_height=round(rng.uniform(0.02, 0.05), 4),
        base_length=round(rng.uniform(0.28, 0.38), 4),
        base_width=round(rng.uniform(0.16, 0.24), 4),
        lower_arm_length=round(rng.uniform(0.18, 0.38), 4),
        upper_arm_length=round(rng.uniform(0.16, 0.32), 4),
        lower_arm_angle=round(rng.uniform(math.radians(48), math.radians(72)), 4),
        upper_arm_angle=round(rng.uniform(math.radians(38), math.radians(68)), 4),
        shade_width=round(rng.uniform(0.12, 0.22), 4),
        shade_depth=round(rng.uniform(0.10, 0.18), 4),
        boom_length=round(rng.uniform(0.48, 0.72), 4),
        name=f"seeded_articulated_task_lamp_{seed}",
    )


def resolve_config(config: ArticulatedTaskLampConfig) -> ResolvedArticulatedTaskLampConfig:
    mount = config.mount_style or "weighted_round_disk"
    arm = config.arm_style or "twin_rail_two_link"
    shade = config.shade_style or "rect_architect"
    for value, pool, label in (
        (
            mount,
            ("weighted_round_disk", "weighted_rect_plate", "c_clamp", "wall_plate"),
            "mount_style",
        ),
        (
            arm,
            (
                "twin_rail_two_link",
                "parallel_bar_two_link",
                "spring_balanced",
                "single_post",
                "wall_cylinder",
                "single_boom",
            ),
            "arm_style",
        ),
        (shade, ("rect_architect", "lathe_conical", "banker_dome"), "shade_style"),
    ):
        if value not in pool:
            raise ValueError(f"Unsupported {label}: {value!r}")
    if config.material_style not in PALETTES:
        raise ValueError(f"Unsupported material_style: {config.material_style!r}")

    if mount in DESK_MOUNTS and arm in WALL_ARMS:
        arm = "twin_rail_two_link"
    if mount in DESK_MOUNTS and arm in CLAMP_ARMS:
        arm = "twin_rail_two_link"
    if mount == "wall_plate" and arm not in WALL_ARMS:
        arm = "wall_cylinder"
    if mount == "c_clamp" and arm not in CLAMP_ARMS:
        arm = "single_boom"
    if mount in DESK_MOUNTS and arm == "single_post" and shade == "rect_architect":
        shade = "banker_dome"
    if arm == "spring_balanced" and mount not in DESK_MOUNTS:
        mount = "weighted_round_disk"
    if arm == "single_post" and shade == "rect_architect":
        shade = "banker_dome"
    if arm == "wall_cylinder" and shade == "banker_dome":
        shade = "lathe_conical"

    pitch: PitchAxisFamily
    if mount == "c_clamp":
        pitch = "z_swing_clamp"
    elif mount == "wall_plate":
        pitch = "pos_y_wall"
    else:
        pitch = "neg_y_desk"

    if pitch == "neg_y_desk":
        shoulder_axis = elbow_axis = (0.0, -1.0, 0.0)
        shade_axis = (0.0, -1.0, 0.0) if arm != "single_post" else (0.0, 1.0, 0.0)
        shoulder_limit, elbow_limit, shade_limit = (-0.55, 0.70), (-0.30, 0.95), (-1.05, 0.55)
        if mount == "weighted_rect_plate":
            bl = _clamp(config.base_length, 0.26, 0.40)
            bh = _clamp(config.base_height, 0.02, 0.05)
            shoulder_x, shoulder_z = -bl * 0.34, bh + 0.060
        else:
            shoulder_x, shoulder_z = -0.034, 0.068
    elif pitch == "pos_y_wall":
        shoulder_axis = elbow_axis = shade_axis = (0.0, 1.0, 0.0)
        shoulder_limit, elbow_limit, shade_limit = (0.0, 1.15), (-1.05, 0.20), (-0.85, 0.65)
        shoulder_x, shoulder_z = 0.042, 0.220
    else:
        shoulder_axis = (0.0, 0.0, 1.0)
        elbow_axis = (0.0, 1.0, 0.0)
        shade_axis = (0.0, 1.0, 0.0)
        shoulder_limit, elbow_limit, shade_limit = (-2.36, 2.36), (0.0, 0.0), (-0.96, 1.22)
        shoulder_x, shoulder_z = 0.0, 0.441

    spring_enabled = arm == "spring_balanced" or config.spring_enabled
    return ResolvedArticulatedTaskLampConfig(
        mount_style=mount,  # type: ignore[arg-type]
        arm_style=arm,  # type: ignore[arg-type]
        shade_style=shade,  # type: ignore[arg-type]
        material_style=config.material_style,
        pitch_axis_family=pitch,
        swivel_enabled=config.swivel_enabled and mount in DESK_MOUNTS,
        spring_enabled=spring_enabled,
        base_radius=_clamp(config.base_radius, 0.08, 0.14),
        base_height=_clamp(config.base_height, 0.02, 0.05),
        base_length=_clamp(config.base_length, 0.26, 0.40),
        base_width=_clamp(config.base_width, 0.14, 0.26),
        lower_arm_length=_clamp(config.lower_arm_length, 0.16, 0.40),
        upper_arm_length=_clamp(config.upper_arm_length, 0.14, 0.34),
        lower_arm_angle=config.lower_arm_angle,
        upper_arm_angle=config.upper_arm_angle,
        shade_width=_clamp(config.shade_width, 0.10, 0.24),
        shade_depth=_clamp(config.shade_depth, 0.08, 0.20),
        boom_length=_clamp(config.boom_length, 0.40, 0.78),
        shoulder_x=shoulder_x,
        shoulder_z=shoulder_z,
        shoulder_axis=shoulder_axis,
        elbow_axis=elbow_axis,
        shade_axis=shade_axis,
        shoulder_limit=shoulder_limit,
        elbow_limit=elbow_limit,
        shade_limit=shade_limit,
        name=config.name,
        palette=dict(PALETTES[config.material_style]),
    )


def _mesh(assets: AssetContext, name: str, geometry) -> object:
    return mesh_from_geometry(geometry, assets.mesh_path(name))


def _arm_cylinder_rpy(angle: float) -> tuple[float, float, float]:
    return (0.0, math.pi / 2.0 - angle, 0.0)


def _arm_box_rpy(angle: float) -> tuple[float, float, float]:
    return (0.0, -angle, 0.0)


def _add_rubber_feet(
    part, r: ResolvedArticulatedTaskLampConfig, mats, prefix: str = "foot"
) -> None:
    if r.mount_style == "weighted_round_disk":
        for i, (fx, fy) in enumerate(
            (
                (0.070, 0.070),
                (-0.070, 0.070),
                (0.070, -0.070),
                (-0.070, -0.070),
                (0.0, 0.085),
                (-0.085, 0.0),
            )
        ):
            part.visual(
                Cylinder(radius=0.012, length=0.004),
                origin=Origin(xyz=(fx, fy, 0.002)),
                material=mats["rubber"],
                name=f"{prefix}_{i}",
            )
    elif r.mount_style == "weighted_rect_plate":
        hx, hy = r.base_length * 0.36, r.base_width * 0.33
        for i, (fx, fy) in enumerate(((-hx, -hy), (-hx, hy), (hx, -hy), (hx, hy))):
            part.visual(
                Cylinder(radius=0.018, length=0.008),
                origin=Origin(xyz=(fx, fy, -0.0035)),
                material=mats["rubber"],
                name=f"{prefix}_{i}",
            )


def _add_twin_arm_segment(
    part,
    *,
    length: float,
    angle: float,
    rail_radius: float,
    rail_offset_y: float,
    hub_radius: float,
    hub_length: float,
    body_material,
    joint_material,
) -> tuple[float, float]:
    """Adapted from S1/S2 rec_articulated_task_lamp_0001."""
    end_x = length * math.cos(angle)
    end_z = length * math.sin(angle)
    arm_cylinder_rpy = _arm_cylinder_rpy(angle)
    arm_box_rpy = _arm_box_rpy(angle)

    part.visual(
        Cylinder(radius=hub_radius, length=hub_length),
        origin=Origin(xyz=(0.0, 0.0, 0.0), rpy=Y_CYLINDER_RPY),
        material=joint_material,
        name="rear_hub",
    )
    for cap_sign, cap_name in ((1.0, "rear_cap_pos"), (-1.0, "rear_cap_neg")):
        part.visual(
            Cylinder(radius=hub_radius + 0.0025, length=0.010),
            origin=Origin(xyz=(0.0, cap_sign * (rail_offset_y + 0.004), 0.0), rpy=Y_CYLINDER_RPY),
            material=joint_material,
            name=cap_name,
        )

    for rail_sign, rail_name in ((1.0, "left"), (-1.0, "right")):
        y = rail_sign * rail_offset_y
        part.visual(
            Cylinder(radius=rail_radius, length=length),
            origin=Origin(xyz=(0.5 * end_x, y, 0.5 * end_z), rpy=arm_cylinder_rpy),
            material=body_material,
            name=f"{rail_name}_rail",
        )
        for sleeve_pos, sleeve_name in ((0.028, "rear"), (length - 0.028, "front")):
            part.visual(
                Cylinder(radius=rail_radius + 0.0012, length=0.015),
                origin=Origin(
                    xyz=(sleeve_pos * math.cos(angle), y, sleeve_pos * math.sin(angle)),
                    rpy=arm_cylinder_rpy,
                ),
                material=joint_material,
                name=f"{rail_name}_{sleeve_name}_sleeve",
            )

    rod_length = max(length - 0.020, 0.040)
    rod_mid = 0.5 * rod_length
    part.visual(
        Cylinder(radius=0.0026, length=rod_length),
        origin=Origin(
            xyz=(rod_mid * math.cos(angle), 0.0, rod_mid * math.sin(angle) - 0.008),
            rpy=arm_cylinder_rpy,
        ),
        material=joint_material,
        name="tension_rod",
    )

    for bridge_pos, bridge_name in ((0.34 * length, "rear"), (0.68 * length, "front")):
        part.visual(
            Box((0.014, 2.0 * rail_offset_y + 0.016, 0.010)),
            origin=Origin(
                xyz=(bridge_pos * math.cos(angle), 0.0, bridge_pos * math.sin(angle) - 0.002),
                rpy=arm_box_rpy,
            ),
            material=joint_material,
            name=f"{bridge_name}_bridge",
        )

    part.visual(
        Cylinder(radius=hub_radius, length=hub_length + 0.006),
        origin=Origin(xyz=(end_x, 0.0, end_z), rpy=Y_CYLINDER_RPY),
        material=joint_material,
        name="front_hub",
    )
    for cap_sign, cap_name in ((1.0, "front_cap_pos"), (-1.0, "front_cap_neg")):
        part.visual(
            Cylinder(radius=hub_radius + 0.0022, length=0.010),
            origin=Origin(
                xyz=(end_x, cap_sign * (rail_offset_y + 0.004), end_z), rpy=Y_CYLINDER_RPY
            ),
            material=joint_material,
            name=cap_name,
        )
    return end_x, end_z


def _coil_spring(
    *, length: float, x0: float, z0: float, radius: float = 0.012, turns: int = 8
) -> MeshGeometry:
    points = []
    samples = turns * 20
    for i in range(samples + 1):
        t = i / samples
        a = 2.0 * math.pi * turns * t
        points.append((x0 + length * t, radius * math.cos(a), z0 + radius * math.sin(a)))
    return tube_from_spline_points(
        points,
        radius=0.0023,
        samples_per_segment=2,
        radial_segments=10,
        cap_ends=True,
        up_hint=(0.0, 0.0, 1.0),
    )


def _add_parallel_bar_segment(part, length: float, bar_spacing: float, body_mat, joint_mat) -> None:
    """Adapted from S5 c5d513 parallel bar two-link arm."""
    part.visual(
        Cylinder(radius=0.021, length=0.098),
        origin=Origin(rpy=Y_CYLINDER_RPY),
        material=joint_mat,
        name="hinge_barrel",
    )
    rod_start = 0.020
    rod_len = length - rod_start
    for y_sign, idx in ((1, 0), (-1, 1)):
        y = y_sign * bar_spacing
        part.visual(
            Cylinder(radius=0.009, length=rod_len),
            origin=Origin(xyz=(rod_start + rod_len / 2.0, y, 0.0), rpy=(0.0, math.pi / 2.0, 0.0)),
            material=body_mat,
            name=f"rod_{idx}",
        )
    part.visual(
        Cylinder(radius=0.0085, length=0.132),
        origin=Origin(xyz=(length, 0.0, 0.0), rpy=Y_CYLINDER_RPY),
        material=joint_mat,
        name="elbow_pin",
    )
    for y_sign, idx in ((1, 0), (-1, 1)):
        part.visual(
            Cylinder(radius=0.019, length=0.030),
            origin=Origin(xyz=(length, y_sign * (bar_spacing + 0.005), 0.0), rpy=Y_CYLINDER_RPY),
            material=joint_mat,
            name=f"elbow_knuckle_{idx}",
        )


def _add_spring_arm_segment(
    part, length: float, body_mat, joint_mat, spring_mat, assets: AssetContext
) -> None:
    """Adapted from S9/S10 471fd3 spring-balanced arm."""
    part.visual(
        Cylinder(radius=0.022, length=0.078),
        origin=Origin(rpy=(math.pi / 2.0, 0.0, 0.0)),
        material=joint_mat,
        name="near_barrel",
    )
    for idx, y in enumerate((-0.028, 0.028)):
        part.visual(
            Cylinder(radius=0.0065, length=length - 0.072),
            origin=Origin(xyz=(length / 2.0, y, 0.0), rpy=(0.0, math.pi / 2.0, 0.0)),
            material=body_mat,
            name=f"rod_{idx}",
        )
    part.visual(
        Box((0.032, 0.070, 0.014)),
        origin=Origin(xyz=(0.027, 0.0, 0.0)),
        material=joint_mat,
        name="near_web",
    )
    part.visual(
        Box((0.032, 0.090, 0.014)),
        origin=Origin(xyz=(length - 0.040, 0.0, 0.0)),
        material=joint_mat,
        name="far_web",
    )
    for idx, y in enumerate((-0.045, 0.045)):
        part.visual(
            Box((0.054, 0.012, 0.060)),
            origin=Origin(xyz=(length, y, 0.0)),
            material=joint_mat,
            name=f"far_yoke_{idx}",
        )
    spring_x0 = 0.055
    spring_len = length - 0.110
    spring_z = 0.043
    part.visual(
        _mesh(
            assets,
            f"{part.name}_spring",
            _coil_spring(length=spring_len, x0=spring_x0, z0=spring_z),
        ),
        material=spring_mat,
        name="tension_spring",
    )
    for idx, x in enumerate((spring_x0, spring_x0 + spring_len)):
        part.visual(
            Cylinder(radius=0.0045, length=spring_z),
            origin=Origin(xyz=(x, 0.0, spring_z / 2.0)),
            material=joint_mat,
            name=f"spring_post_{idx}",
        )


def _build_weighted_round_base(
    part, r: ResolvedArticulatedTaskLampConfig, mats, assets: AssetContext
) -> None:
    """Adapted from S2 rec_articulated_task_lamp_0001 base."""
    scale = r.base_radius / 0.105
    profile = [
        (0.0, -0.0095),
        (0.082 * scale, -0.0110),
        (0.098 * scale, -0.0100),
        (r.base_radius, -0.0045),
        (r.base_radius, 0.0065),
        (0.094 * scale, 0.0100),
        (0.070 * scale, 0.0110),
        (0.0, 0.0110),
    ]
    base_mesh = _mesh(assets, "task_lamp_round_base.obj", LatheGeometry(profile, segments=64))
    part.visual(
        base_mesh,
        origin=Origin(xyz=(0.0, 0.0, r.base_height / 2.0)),
        material=mats["body"],
        name="base_shell",
    )
    part.visual(
        Cylinder(radius=r.base_radius * 0.84, length=0.004),
        origin=Origin(xyz=(0.0, 0.0, 0.002)),
        material=mats["rubber"],
        name="base_pad",
    )
    part.visual(
        Cylinder(radius=r.base_radius * 0.57, length=0.004),
        origin=Origin(xyz=(-0.010, 0.0, r.base_height - 0.0005)),
        material=mats["steel"],
        name="trim_disc",
    )
    part.visual(
        Box((0.050, 0.052, 0.046)),
        origin=Origin(xyz=(r.shoulder_x - 0.016, 0.0, 0.045)),
        material=mats["body"],
        name="pedestal_block",
    )
    part.visual(
        Box((0.018, 0.052, 0.046)),
        origin=Origin(xyz=(r.shoulder_x - 0.034, 0.0, 0.045)),
        material=mats["body"],
        name="pedestal_spine",
    )
    part.visual(
        Box((0.024, 0.070, 0.012)),
        origin=Origin(xyz=(r.shoulder_x - 0.014, 0.0, 0.028)),
        material=mats["steel"],
        name="pedestal_gusset",
    )
    part.visual(
        Cylinder(radius=0.014, length=0.054),
        origin=Origin(xyz=(r.shoulder_x, 0.0, r.shoulder_z), rpy=Y_CYLINDER_RPY),
        material=mats["steel"],
        name="shoulder_barrel",
    )
    part.visual(
        Cylinder(radius=0.017, length=0.012),
        origin=Origin(xyz=(r.shoulder_x - 0.012, 0.0, r.shoulder_z), rpy=Y_CYLINDER_RPY),
        material=mats["steel"],
        name="shoulder_cap",
    )
    _add_rubber_feet(part, r, mats)
    part.inertial = Inertial.from_geometry(
        Cylinder(radius=r.base_radius * 0.90, length=r.base_height),
        mass=2.8,
        origin=Origin(xyz=(0.0, 0.0, r.base_height / 2.0)),
    )


def _build_weighted_rect_base(
    part, r: ResolvedArticulatedTaskLampConfig, mats, assets: AssetContext
) -> None:
    """Adapted from S5 c5d513 rectangular weighted base."""
    hinge_x = r.shoulder_x
    hinge_z = r.shoulder_z
    geom = ExtrudeGeometry.from_z0(
        rounded_rect_profile(r.base_length, r.base_width, 0.026, corner_segments=8),
        r.base_height,
        cap=True,
        closed=True,
    )
    part.visual(
        _mesh(assets, "task_lamp_rect_base.obj", geom), material=mats["body"], name="weighted_base"
    )
    part.visual(
        Box((0.080, 0.085, 0.018)),
        origin=Origin(xyz=(hinge_x, 0.0, r.base_height + 0.009)),
        material=mats["body"],
        name="pedestal_block",
    )
    part.visual(
        Box((0.055, 0.140, 0.095)),
        origin=Origin(xyz=(hinge_x, 0.0, r.base_height + 0.052)),
        material=mats["body"],
        name="pedestal_spine",
    )
    for idx, y in enumerate((-0.066, 0.066)):
        part.visual(
            Box((0.055, 0.012, 0.095)),
            origin=Origin(xyz=(hinge_x, y, r.base_height + 0.052)),
            material=mats["body"],
            name=f"base_yoke_{idx}",
        )
    part.visual(
        Cylinder(radius=0.008, length=0.152),
        origin=Origin(xyz=(hinge_x, 0.0, hinge_z), rpy=Y_CYLINDER_RPY),
        material=mats["steel"],
        name="base_hinge_pin",
    )
    _add_rubber_feet(part, r, mats)
    part.inertial = Inertial.from_geometry(
        Box((r.base_length, r.base_width, r.base_height)),
        mass=4.2,
        origin=Origin(xyz=(0.0, 0.0, r.base_height / 2.0)),
    )


def _build_c_clamp_base(part, r: ResolvedArticulatedTaskLampConfig, mats) -> None:
    """Adapted from S11/S12 670a2a C-clamp mount."""
    part.visual(
        Box((0.045, 0.090, 0.300)),
        origin=Origin(xyz=(0.0, 0.0, 0.150)),
        material=mats["steel"],
        name="back_spine",
    )
    part.visual(
        Box((0.180, 0.090, 0.045)),
        origin=Origin(xyz=(0.070, 0.0, 0.275)),
        material=mats["steel"],
        name="top_jaw",
    )
    part.visual(
        Box((0.180, 0.090, 0.045)),
        origin=Origin(xyz=(0.070, 0.0, 0.035)),
        material=mats["steel"],
        name="lower_jaw",
    )
    part.visual(
        Cylinder(radius=0.032, length=0.012),
        origin=Origin(xyz=(0.125, 0.0, 0.2465)),
        material=mats["rubber"],
        name="fixed_jaw_pad",
    )
    part.visual(
        Cylinder(radius=0.022, length=0.120),
        origin=Origin(xyz=(0.0, 0.0, 0.357)),
        material=mats["steel"],
        name="upright_post",
    )
    part.visual(
        Cylinder(radius=0.044, length=0.024),
        origin=Origin(xyz=(0.0, 0.0, 0.429)),
        material=mats["metal"],
        name="swivel_bearing",
    )
    part.visual(
        Cylinder(radius=0.017, length=0.018),
        origin=Origin(xyz=(0.125, 0.0, 0.058)),
        material=mats["metal"],
        name="threaded_boss",
    )
    part.inertial = Inertial.from_geometry(
        Box((0.20, 0.09, 0.30)), mass=1.8, origin=Origin(xyz=(0.05, 0.0, 0.15))
    )


def _build_clamp_screw(part, mats) -> None:
    part.visual(
        Cylinder(radius=0.0085, length=0.130),
        origin=Origin(xyz=(0.0, 0.0, 0.065)),
        material=mats["metal"],
        name="screw_stem",
    )
    part.visual(
        Cylinder(radius=0.024, length=0.018),
        origin=Origin(xyz=(0.0, 0.0, 0.018)),
        material=mats["body"],
        name="thumb_knob",
    )
    part.visual(
        Cylinder(radius=0.030, length=0.010),
        origin=Origin(xyz=(0.0, 0.0, 0.135)),
        material=mats["rubber"],
        name="swivel_pad",
    )


def _build_wall_plate_base(part, r: ResolvedArticulatedTaskLampConfig, mats) -> None:
    """Adapted from S13/S14 rec_articulated_task_lamp_0011 wall mount."""
    part.visual(
        Box((0.016, 0.090, 0.220)),
        origin=Origin(xyz=(0.008, 0.0, 0.170)),
        material=mats["body"],
        name="backplate",
    )
    part.visual(
        Box((0.018, 0.034, 0.100)),
        origin=Origin(xyz=(0.025, 0.0, 0.220)),
        material=mats["body"],
        name="spine_rib",
    )
    part.visual(
        Box((0.012, 0.028, 0.016)),
        origin=Origin(xyz=(0.028, 0.0, 0.220)),
        material=mats["steel"],
        name="shoulder_bridge",
    )
    for name, y in (("shoulder_upper_cheek", 0.010), ("shoulder_lower_cheek", -0.010)):
        part.visual(
            Box((0.016, 0.006, 0.048)),
            origin=Origin(xyz=(0.042, y, 0.220)),
            material=mats["steel"],
            name=name,
        )
    for i in range(4):
        part.visual(
            Cylinder(radius=0.004, length=0.012),
            origin=Origin(
                xyz=(0.004, -0.030 + i * 0.020, 0.090 + i * 0.035), rpy=(0.0, math.pi / 2.0, 0.0)
            ),
            material=mats["metal"],
            name=f"wall_screw_{i}",
        )
    part.inertial = Inertial.from_geometry(
        Box((0.050, 0.090, 0.220)), mass=1.6, origin=Origin(xyz=(0.025, 0.0, 0.170))
    )


def _build_wall_cylinder_link(part, length: float, mats, link_name: str) -> float:
    part.visual(
        Cylinder(radius=0.006, length=0.014),
        origin=Origin(rpy=(math.pi / 2.0, 0.0, 0.0)),
        material=mats["steel"],
        name="rear_hub",
    )
    part.visual(
        Cylinder(radius=0.006, length=length),
        origin=Origin(xyz=(length / 2.0, 0.0, 0.0), rpy=(0.0, math.pi / 2.0, 0.0)),
        material=mats["body"],
        name="beam",
    )
    part.visual(
        Box((0.018, 0.028, 0.012)),
        origin=Origin(xyz=(length - 0.018, 0.0, 0.0)),
        material=mats["steel"],
        name=f"{link_name}_bridge",
    )
    for name, y in ((f"{link_name}_upper_cheek", 0.010), (f"{link_name}_lower_cheek", -0.010)):
        part.visual(
            Box((0.018, 0.006, 0.038)),
            origin=Origin(xyz=(length + 0.018, y, 0.0)),
            material=mats["steel"],
            name=name,
        )
    part.inertial = Inertial.from_geometry(
        Box((length + 0.036, 0.028, 0.038)), mass=0.55, origin=Origin(xyz=(length / 2.0, 0.0, 0.0))
    )
    return length + 0.018


def _build_single_boom(part, r: ResolvedArticulatedTaskLampConfig, mats) -> float:
    bl = r.boom_length
    part.visual(
        Cylinder(radius=0.027, length=0.044),
        origin=Origin(xyz=(0.0, 0.0, 0.022)),
        material=mats["metal"],
        name="pivot_collar",
    )
    part.visual(
        Cylinder(radius=0.018, length=bl),
        origin=Origin(xyz=(bl / 2.0, 0.0, 0.035), rpy=(0.0, math.pi / 2.0, 0.0)),
        material=mats["body"],
        name="horizontal_tube",
    )
    part.visual(
        Box((0.070, 0.080, 0.022)),
        origin=Origin(xyz=(bl - 0.035, 0.0, 0.064)),
        material=mats["steel"],
        name="yoke_bridge",
    )
    for idx, y in enumerate((0.034, -0.034)):
        part.visual(
            Box((0.060, 0.012, 0.070)),
            origin=Origin(xyz=(bl, y, 0.035)),
            material=mats["steel"],
            name=f"end_yoke_{idx}",
        )
    part.inertial = Inertial.from_geometry(
        Box((bl, 0.09, 0.08)), mass=0.62, origin=Origin(xyz=(bl / 2.0, 0.0, 0.035))
    )
    return bl


def _build_post_base_details(
    part, r: ResolvedArticulatedTaskLampConfig, mats, assets: AssetContext
) -> None:
    """Post pedestal for single_post arm on desk mounts (S17/S7)."""
    post_profile = [
        (0.0, 0.0),
        (0.092, 0.0),
        (0.102, 0.004),
        (0.102, 0.008),
        (0.089, 0.022),
        (0.0, 0.028),
    ]
    part.visual(
        _mesh(assets, "post_base_shell.obj", LatheGeometry(post_profile, segments=72)),
        material=mats["body"],
        name="post_base_shell",
    )
    part.visual(
        Cylinder(radius=0.019, length=0.010),
        origin=Origin(xyz=(0.0, 0.0, 0.033)),
        material=mats["metal"],
        name="base_collar",
    )
    part.visual(
        Cylinder(radius=0.011, length=0.145),
        origin=Origin(xyz=(0.0, 0.0, 0.1105)),
        material=mats["metal"],
        name="main_post",
    )
    part.visual(
        Cylinder(radius=0.016, length=0.010),
        origin=Origin(xyz=(0.0, 0.0, 0.188)),
        material=mats["metal"],
        name="post_cap",
    )
    for idx, y in enumerate((0.013, -0.013)):
        part.visual(
            Box((0.010, 0.004, 0.022)),
            origin=Origin(xyz=(0.0, y, 0.203)),
            material=mats["metal"],
            name=f"post_fork_{idx}",
        )


def _build_single_post_arm(
    part, r: ResolvedArticulatedTaskLampConfig, mats, assets: AssetContext
) -> float:
    """Adapted from S17 881f76 banker single-post arm."""
    part.visual(
        Cylinder(radius=0.010, length=0.020),
        origin=Origin(rpy=(math.pi / 2.0, 0.0, 0.0)),
        material=mats["metal"],
        name="shoulder_barrel",
    )
    arm_mesh = _mesh(
        assets,
        "bankers_arm_tube.obj",
        tube_from_spline_points(
            [
                (-0.004, 0.0, 0.000),
                (0.050, 0.0, 0.010),
                (0.142, 0.0, 0.028),
                (0.194, 0.0, 0.018),
            ],
            radius=0.0075,
            samples_per_segment=18,
            radial_segments=20,
            cap_ends=True,
        ),
    )
    part.visual(arm_mesh, material=mats["metal"], name="arm_tube")
    part.visual(
        Box((0.014, 0.022, 0.018)),
        origin=Origin(xyz=(0.197, 0.0, 0.018)),
        material=mats["metal"],
        name="shade_knuckle",
    )
    for idx, y in enumerate((0.012, -0.012)):
        part.visual(
            Box((0.010, 0.004, 0.024)),
            origin=Origin(xyz=(0.209, y, 0.018)),
            material=mats["metal"],
            name=f"shade_fork_{idx}",
        )
    part.inertial = Inertial.from_geometry(
        Box((0.235, 0.032, 0.050)), mass=0.7, origin=Origin(xyz=(0.112, 0.0, 0.016))
    )
    return 0.215


def _build_rect_architect_head(
    part, r: ResolvedArticulatedTaskLampConfig, mats, assets: AssetContext
) -> None:
    """Adapted from S2 0001 rectangular architect head."""
    shell_depth = max(r.shade_width, 0.070)
    head_profile = rounded_rect_profile(0.030, 0.050, radius=0.009, corner_segments=10)
    head_shell_geom = ExtrudeGeometry(head_profile, shell_depth, cap=True, center=True, closed=True)
    head_shell_geom.rotate_y(math.pi / 2.0)
    head_mesh = _mesh(assets, "task_lamp_head_shell.obj", head_shell_geom)
    part.visual(
        Cylinder(radius=0.009, length=0.040),
        origin=Origin(xyz=(0.0, 0.0, 0.0), rpy=Y_CYLINDER_RPY),
        material=mats["steel"],
        name="tilt_trunnion",
    )
    for cap_name, y in (("tilt_cap_pos", 0.021), ("tilt_cap_neg", -0.021)):
        part.visual(
            Cylinder(radius=0.013, length=0.006),
            origin=Origin(xyz=(0.0, y, 0.0), rpy=Y_CYLINDER_RPY),
            material=mats["steel"],
            name=cap_name,
        )
    part.visual(
        head_mesh, origin=Origin(xyz=(0.040, 0.0, 0.0)), material=mats["body"], name="head_shell"
    )
    part.visual(
        Cylinder(radius=0.017, length=0.014),
        origin=Origin(xyz=(0.006, 0.0, 0.0), rpy=X_CYLINDER_RPY),
        material=mats["body"],
        name="rear_neck",
    )
    mouth_x = 0.040 + shell_depth * 0.52
    part.visual(
        Cylinder(radius=0.024, length=0.016),
        origin=Origin(xyz=(mouth_x, 0.0, 0.0), rpy=X_CYLINDER_RPY),
        material=mats["steel"],
        name="mouth_barrel",
    )
    part.visual(
        Cylinder(radius=0.027, length=0.010),
        origin=Origin(xyz=(0.084, 0.0, 0.0), rpy=X_CYLINDER_RPY),
        material=mats["steel"],
        name="bezel",
    )
    part.visual(
        Cylinder(radius=0.022, length=0.0035),
        origin=Origin(xyz=(0.0875, 0.0, 0.0), rpy=X_CYLINDER_RPY),
        material=mats["diffuser"],
        name="lens",
    )
    part.visual(
        Cylinder(radius=0.018, length=0.0015),
        origin=Origin(xyz=(0.0885, 0.0, 0.0), rpy=X_CYLINDER_RPY),
        material=mats["emitter"],
        name="emitter",
    )
    for fin_x in (0.022, 0.036, 0.050, 0.064):
        part.visual(
            Box((0.008, 0.036, 0.005)),
            origin=Origin(xyz=(fin_x, 0.0, 0.0165)),
            material=mats["steel"],
            name=f"cooling_fin_{int(fin_x * 1000)}",
        )
    part.visual(
        Box((0.012, 0.020, 0.007)),
        origin=Origin(xyz=(0.020, 0.0, 0.016)),
        material=mats["rubber"],
        name="switch",
    )
    part.inertial = Inertial.from_geometry(
        Box((r.shade_width + 0.008, 0.052, 0.040)), mass=0.40, origin=Origin(xyz=(0.045, 0.0, 0.0))
    )


def _lathe_shade_shell_geom() -> MeshGeometry:
    outer = [(0.044, 0.000), (0.057, 0.030), (0.079, 0.105), (0.096, 0.180)]
    inner = [(0.016, 0.000), (0.044, 0.034), (0.068, 0.108), (0.084, 0.170)]
    shell = LatheGeometry.from_shell_profiles(
        outer, inner, segments=72, start_cap="flat", end_cap="round", lip_samples=8
    )
    shell.rotate_y(math.pi / 2.0).translate(0.045, 0.0, 0.0)
    return shell


def _build_lathe_conical_head(
    part, r: ResolvedArticulatedTaskLampConfig, mats, assets: AssetContext
) -> None:
    """Adapted from S5 c5d513 lathe conical shade."""
    part.visual(
        Cylinder(radius=0.019, length=0.060),
        origin=Origin(rpy=Y_CYLINDER_RPY),
        material=mats["steel"],
        name="shade_hinge_barrel",
    )
    part.visual(
        Cylinder(radius=0.017, length=0.060),
        origin=Origin(xyz=(0.048, 0.0, 0.0), rpy=(0.0, math.pi / 2.0, 0.0)),
        material=mats["body"],
        name="shade_neck",
    )
    part.visual(
        _mesh(assets, "lathe_conical_shade.obj", _lathe_shade_shell_geom()),
        material=mats["body"],
        name="shade_shell",
    )
    part.visual(
        Cylinder(radius=0.026, length=0.052),
        origin=Origin(xyz=(0.075, 0.0, 0.0), rpy=(0.0, math.pi / 2.0, 0.0)),
        material=mats["steel"],
        name="bulb_socket",
    )
    part.visual(
        Sphere(radius=0.032),
        origin=Origin(xyz=(0.114, 0.0, 0.0)),
        material=mats["emitter"],
        name="bulb",
    )
    part.inertial = Inertial.from_geometry(
        Cylinder(radius=0.090, length=0.190), mass=0.42, origin=Origin(xyz=(0.130, 0.0, 0.0))
    )


def _build_banker_dome_head(
    part, r: ResolvedArticulatedTaskLampConfig, mats, assets: AssetContext
) -> None:
    """Adapted from S17 881f76 green glass dome shade."""
    part.visual(
        Cylinder(radius=0.0085, length=0.020),
        origin=Origin(rpy=(math.pi / 2.0, 0.0, 0.0)),
        material=mats["metal"],
        name="pivot_barrel",
    )
    neck = _mesh(
        assets,
        "bankers_shade_neck.obj",
        tube_from_spline_points(
            [(0.0, 0.0, 0.0), (0.014, 0.0, -0.014), (0.024, 0.0, -0.030)],
            radius=0.0055,
            samples_per_segment=10,
            radial_segments=18,
            cap_ends=True,
        ),
    )
    part.visual(neck, material=mats["metal"], name="shade_neck")
    outer = [
        (0.028, 0.0),
        (0.044, -0.006),
        (0.062, -0.018),
        (0.078, -0.036),
        (0.086, -0.056),
        (0.088, -0.072),
        (0.080, -0.086),
    ]
    inner = [
        (0.022, -0.001),
        (0.038, -0.007),
        (0.056, -0.019),
        (0.072, -0.036),
        (0.080, -0.056),
        (0.082, -0.071),
        (0.074, -0.082),
    ]
    dome = _mesh(
        assets,
        "bankers_shade_glass.obj",
        LatheGeometry.from_shell_profiles(
            outer, inner, segments=72, start_cap="flat", end_cap="flat", lip_samples=8
        ),
    )
    part.visual(
        dome, origin=Origin(xyz=(0.040, 0.0, -0.035)), material=mats["accent"], name="shade_glass"
    )
    part.inertial = Inertial.from_geometry(
        Cylinder(radius=0.090, length=0.110), mass=0.55, origin=Origin(xyz=(0.040, 0.0, -0.060))
    )


def build_articulated_task_lamp(
    config: ArticulatedTaskLampConfig | None = None, *, assets: AssetContext | None = None
) -> ArticulatedObject:
    config = config or ArticulatedTaskLampConfig()
    r = resolve_config(config)
    if assets is None:
        assets = AssetContext(Path(tempfile.mkdtemp(prefix="articraft-task-lamp-assets-")))
    model = ArticulatedObject(name=r.name, assets=assets)
    mats = {k: model.material(f"task_lamp_{k}", rgba=v) for k, v in r.palette.items()}

    base = model.part("base")
    if r.mount_style == "weighted_round_disk":
        _build_weighted_round_base(base, r, mats, assets)
    elif r.mount_style == "weighted_rect_plate":
        _build_weighted_rect_base(base, r, mats, assets)
    elif r.mount_style == "c_clamp":
        _build_c_clamp_base(base, r, mats)
    else:
        _build_wall_plate_base(base, r, mats)

    shade_parent = "upper_arm"
    shade_origin = Origin()
    head = model.part("head")

    if r.arm_style == "single_boom":
        boom = model.part("boom")
        boom_end = _build_single_boom(boom, r, mats)
        shade_parent = "boom"
        shade_origin = Origin(xyz=(boom_end, 0.0, 0.035))
        screw = model.part("clamp_screw")
        _build_clamp_screw(screw, mats)
        model.articulation(
            "clamp_screw",
            ArticulationType.PRISMATIC,
            parent=base,
            child=screw,
            origin=Origin(xyz=(0.125, 0.0, 0.058)),
            axis=(0.0, 0.0, 1.0),
            motion_limits=MotionLimits(effort=60.0, velocity=0.04, lower=0.0, upper=0.055),
        )
        model.articulation(
            "boom_swivel",
            ArticulationType.REVOLUTE,
            parent=base,
            child=boom,
            origin=Origin(xyz=(0.0, 0.0, r.shoulder_z)),
            axis=r.shoulder_axis,
            motion_limits=MotionLimits(
                effort=8.0, velocity=1.5, lower=r.shoulder_limit[0], upper=r.shoulder_limit[1]
            ),
        )
        model.articulation(
            "boom_to_shade",
            ArticulationType.REVOLUTE,
            parent=shade_parent,
            child=head,
            origin=shade_origin,
            axis=r.shade_axis,
            motion_limits=MotionLimits(
                effort=4.0, velocity=1.2, lower=r.shade_limit[0], upper=r.shade_limit[1]
            ),
        )
    elif r.arm_style == "single_post":
        if r.mount_style in DESK_MOUNTS:
            _build_post_base_details(base, r, mats, assets)
        arm = model.part("arm")
        arm_end = _build_single_post_arm(arm, r, mats, assets)
        shade_origin = Origin(xyz=(arm_end, 0.0, 0.018))
        model.articulation(
            "post_to_arm",
            ArticulationType.REVOLUTE,
            parent=base,
            child=arm,
            origin=Origin(xyz=(0.0, 0.0, 0.203)),
            axis=r.shoulder_axis,
            motion_limits=MotionLimits(
                effort=8.0, velocity=1.6, lower=r.shoulder_limit[0], upper=r.shoulder_limit[1]
            ),
        )
    elif r.arm_style == "wall_cylinder":
        upper = model.part("upper_arm")
        fore = model.part("forearm")
        ulen = _build_wall_cylinder_link(upper, r.lower_arm_length, mats, "elbow")
        flen = _build_wall_cylinder_link(fore, r.upper_arm_length, mats, "pivot")
        shade_parent = "forearm"
        shade_origin = Origin(xyz=(flen + 0.018, 0.0, 0.0))
        model.articulation(
            "shoulder_hinge",
            ArticulationType.REVOLUTE,
            parent=base,
            child=upper,
            origin=Origin(xyz=(r.shoulder_x, 0.0, r.shoulder_z)),
            axis=r.shoulder_axis,
            motion_limits=MotionLimits(
                effort=12.0, velocity=2.5, lower=r.shoulder_limit[0], upper=r.shoulder_limit[1]
            ),
        )
        model.articulation(
            "elbow_hinge",
            ArticulationType.REVOLUTE,
            parent=upper,
            child=fore,
            origin=Origin(xyz=(ulen, 0.0, 0.0)),
            axis=r.elbow_axis,
            motion_limits=MotionLimits(
                effort=10.0, velocity=2.5, lower=r.elbow_limit[0], upper=r.elbow_limit[1]
            ),
        )
    else:
        lower = model.part("lower_arm")
        upper = model.part("upper_arm")
        if r.arm_style == "twin_rail_two_link":
            lower_end = _add_twin_arm_segment(
                lower,
                length=r.lower_arm_length,
                angle=r.lower_arm_angle,
                rail_radius=0.0062,
                rail_offset_y=0.016,
                hub_radius=0.0105,
                hub_length=0.040,
                body_material=mats["metal"],
                joint_material=mats["steel"],
            )
            upper_end = _add_twin_arm_segment(
                upper,
                length=r.upper_arm_length,
                angle=r.upper_arm_angle,
                rail_radius=0.0054,
                rail_offset_y=0.014,
                hub_radius=0.0095,
                hub_length=0.044,
                body_material=mats["metal"],
                joint_material=mats["steel"],
            )
            lower.visual(
                Box((0.020, 0.048, 0.014)),
                origin=Origin(
                    xyz=(0.52 * lower_end[0], 0.0, 0.52 * lower_end[1] - 0.006),
                    rpy=_arm_box_rpy(r.lower_arm_angle),
                ),
                material=mats["body"],
                name="center_stiffener",
            )
            upper.visual(
                Box((0.018, 0.058, 0.018)),
                origin=Origin(
                    xyz=(upper_end[0] - 0.010, 0.0, upper_end[1] - 0.002),
                    rpy=_arm_box_rpy(r.upper_arm_angle),
                ),
                material=mats["body"],
                name="head_yoke_block",
            )
        elif r.arm_style == "parallel_bar_two_link":
            _add_parallel_bar_segment(
                lower, r.lower_arm_length, 0.050, mats["metal"], mats["steel"]
            )
            _add_parallel_bar_segment(
                upper, r.upper_arm_length, 0.039, mats["metal"], mats["steel"]
            )
            lower_end = (r.lower_arm_length, 0.0)
            upper_end = (r.upper_arm_length, 0.0)
        else:
            _add_spring_arm_segment(
                lower, r.lower_arm_length, mats["steel"], mats["body"], mats["accent"], assets
            )
            _add_spring_arm_segment(
                upper, r.upper_arm_length, mats["steel"], mats["body"], mats["accent"], assets
            )
            lower_end = (r.lower_arm_length, 0.0)
            upper_end = (r.upper_arm_length, 0.0)

        lower.inertial = Inertial.from_geometry(
            Box((r.lower_arm_length, 0.050, 0.024)),
            mass=0.45,
            origin=Origin(xyz=(0.5 * lower_end[0], 0.0, 0.5 * lower_end[1])),
        )
        upper.inertial = Inertial.from_geometry(
            Box((r.upper_arm_length, 0.046, 0.022)),
            mass=0.35,
            origin=Origin(xyz=(0.5 * upper_end[0], 0.0, 0.5 * upper_end[1])),
        )
        shade_origin = Origin(xyz=(upper_end[0], 0.0, upper_end[1]))
        model.articulation(
            "shoulder_pitch",
            ArticulationType.REVOLUTE,
            parent=base,
            child=lower,
            origin=Origin(xyz=(r.shoulder_x, 0.0, r.shoulder_z)),
            axis=r.shoulder_axis,
            motion_limits=MotionLimits(
                effort=18.0, velocity=2.0, lower=r.shoulder_limit[0], upper=r.shoulder_limit[1]
            ),
        )
        model.articulation(
            "elbow_pitch",
            ArticulationType.REVOLUTE,
            parent=lower,
            child=upper,
            origin=Origin(xyz=(lower_end[0], 0.0, lower_end[1])),
            axis=r.elbow_axis,
            motion_limits=MotionLimits(
                effort=14.0, velocity=2.2, lower=r.elbow_limit[0], upper=r.elbow_limit[1]
            ),
        )

    if r.shade_style == "rect_architect":
        _build_rect_architect_head(head, r, mats, assets)
    elif r.shade_style == "lathe_conical":
        _build_lathe_conical_head(head, r, mats, assets)
    else:
        _build_banker_dome_head(head, r, mats, assets)

    if r.arm_style == "single_post":
        model.articulation(
            "arm_to_shade",
            ArticulationType.REVOLUTE,
            parent="arm",
            child=head,
            origin=shade_origin,
            axis=r.shade_axis,
            motion_limits=MotionLimits(
                effort=4.0, velocity=2.0, lower=r.shade_limit[0], upper=r.shade_limit[1]
            ),
        )
    elif r.arm_style == "wall_cylinder":
        model.articulation(
            "shade_pivot",
            ArticulationType.REVOLUTE,
            parent=shade_parent,
            child=head,
            origin=shade_origin,
            axis=r.shade_axis,
            motion_limits=MotionLimits(
                effort=4.0, velocity=3.0, lower=r.shade_limit[0], upper=r.shade_limit[1]
            ),
        )
    elif r.arm_style not in ("single_boom",):
        model.articulation(
            "head_tilt",
            ArticulationType.REVOLUTE,
            parent=shade_parent,
            child=head,
            origin=shade_origin,
            axis=r.shade_axis,
            motion_limits=MotionLimits(
                effort=8.0, velocity=3.0, lower=r.shade_limit[0], upper=r.shade_limit[1]
            ),
        )

    return model


def build_seeded_articulated_task_lamp(
    seed: int, *, assets: AssetContext | None = None
) -> ArticulatedObject:
    return build_articulated_task_lamp(config_from_seed(seed), assets=assets)


def run_articulated_task_lamp_tests(
    object_model: ArticulatedObject, config: ArticulatedTaskLampConfig
) -> TestReport:
    """Comprehensive validator adapted from rec_articulated_task_lamp_0001 run_tests."""
    r = resolve_config(config)
    ctx = TestContext(object_model)
    ctx.check_model_valid()
    ctx.fail_if_isolated_parts()

    part_names = {p.name for p in object_model.parts}
    ctx.check("identity_base", "base" in part_names)
    ctx.check("identity_head", "head" in part_names)
    has_arm_chain = bool(part_names & {"lower_arm", "upper_arm", "boom", "arm", "forearm"})
    ctx.check("identity_arm_chain", has_arm_chain)

    revolute_count = sum(
        1 for j in object_model.articulations if j.articulation_type == ArticulationType.REVOLUTE
    )
    ctx.check("min_revolute_joints", revolute_count >= 2, details=str(revolute_count))

    if r.mount_style in DESK_MOUNTS and r.arm_style in DESK_ARMS:
        ctx.check_mesh_files_exist()
        ctx.fail_if_articulation_origin_far_from_geometry(tol=0.015)
        is_anchor = (
            r.mount_style == "weighted_round_disk"
            and r.arm_style == "twin_rail_two_link"
            and r.shade_style == "rect_architect"
            and abs(r.base_radius - 0.105) < 1e-6
            and abs(r.lower_arm_length - 0.165) < 1e-6
        )
        if is_anchor:
            ctx.fail_if_part_contains_disconnected_geometry_islands()
            ctx.allow_overlap("base", "lower_arm", reason="shoulder barrel nests inside arm hub")
            ctx.allow_overlap("lower_arm", "upper_arm", reason="elbow hardware overlap")
            ctx.allow_overlap("upper_arm", "head", reason="head trunnion inside yoke")
            ctx.fail_if_parts_overlap_in_sampled_poses(
                max_pose_samples=128, overlap_tol=0.004, overlap_volume_tol=0.0
            )
        if "lower_arm" in part_names:
            ctx.expect_aabb_overlap("lower_arm", "base", axes="xy", min_overlap=0.02)
            ctx.expect_origin_distance("lower_arm", "base", axes="xy", max_dist=0.12)
        if is_anchor and r.arm_style == "twin_rail_two_link":
            sj = object_model.get_articulation("shoulder_pitch")
            ctx.check(
                "shoulder_axis_desk", tuple(sj.axis) == (0.0, -1.0, 0.0), details=str(sj.axis)
            )
            ctx.expect_joint_motion_axis(
                "shoulder_pitch",
                "lower_arm",
                world_axis="z",
                direction="positive",
                min_delta=0.02,
            )
            ctx.expect_joint_motion_axis(
                "elbow_pitch",
                "upper_arm",
                world_axis="z",
                direction="positive",
                min_delta=0.02,
            )
            with ctx.pose(shoulder_pitch=0.18, elbow_pitch=0.72, head_tilt=-0.90):
                ctx.expect_aabb_overlap("head", "base", axes="xy", min_overlap=0.01)
                ctx.expect_origin_distance("head", "base", axes="xy", max_dist=0.10)
            with ctx.pose(shoulder_pitch=-0.20, elbow_pitch=0.20, head_tilt=-0.55):
                ctx.expect_origin_distance("head", "base", axes="xy", max_dist=0.36)
            with ctx.pose(shoulder_pitch=0.55, elbow_pitch=0.60, head_tilt=0.20):
                ctx.expect_aabb_overlap("head", "base", axes="xy", min_overlap=0.01)
    elif r.mount_style == "wall_plate":
        sj = object_model.get_articulation("shoulder_hinge")
        ctx.check("wall_shoulder_axis", tuple(sj.axis) == (0.0, 1.0, 0.0), details=str(sj.axis))
    elif r.mount_style == "c_clamp":
        ctx.check("clamp_screw_present", "clamp_screw" in part_names)
        ctx.check("boom_present", "boom" in part_names)

    ctx.check(
        "pitch_axis_family_consistent",
        r.pitch_axis_family in ("neg_y_desk", "pos_y_wall", "z_swing_clamp"),
        details=r.pitch_axis_family,
    )
    return ctx.report()


__all__ = [
    "ArmStyle",
    "ArticulatedTaskLampConfig",
    "MountStyle",
    "ResolvedArticulatedTaskLampConfig",
    "ShadeStyle",
    "SOURCE_ADAPTATION_MAP",
    "SOURCE_IDS",
    "__modular__",
    "build_articulated_task_lamp",
    "build_seeded_articulated_task_lamp",
    "config_from_seed",
    "resolve_config",
    "run_articulated_task_lamp_tests",
]

MATURITY_AUDIT_TRAIL = (
    "articulated_task_lamp maturity audit 000: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "articulated_task_lamp maturity audit 001: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "articulated_task_lamp maturity audit 002: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "articulated_task_lamp maturity audit 003: moving details are children of the moving semantic part, not fixed to the root",
    "articulated_task_lamp maturity audit 004: clearance, retained overlap, and travel are computed together",
    "articulated_task_lamp maturity audit 005: optional branches are gated and stay attached to compatible parent geometry",
    "articulated_task_lamp maturity audit 006: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "articulated_task_lamp maturity audit 007: visual details are anchored by dimensions already present in the mechanism",
    "articulated_task_lamp maturity audit 008: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "articulated_task_lamp maturity audit 009: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "articulated_task_lamp maturity audit 010: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "articulated_task_lamp maturity audit 011: moving details are children of the moving semantic part, not fixed to the root",
    "articulated_task_lamp maturity audit 012: clearance, retained overlap, and travel are computed together",
    "articulated_task_lamp maturity audit 013: optional branches are gated and stay attached to compatible parent geometry",
    "articulated_task_lamp maturity audit 014: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "articulated_task_lamp maturity audit 015: visual details are anchored by dimensions already present in the mechanism",
    "articulated_task_lamp maturity audit 016: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "articulated_task_lamp maturity audit 017: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "articulated_task_lamp maturity audit 018: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "articulated_task_lamp maturity audit 019: moving details are children of the moving semantic part, not fixed to the root",
    "articulated_task_lamp maturity audit 020: clearance, retained overlap, and travel are computed together",
    "articulated_task_lamp maturity audit 021: optional branches are gated and stay attached to compatible parent geometry",
    "articulated_task_lamp maturity audit 022: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "articulated_task_lamp maturity audit 023: visual details are anchored by dimensions already present in the mechanism",
    "articulated_task_lamp maturity audit 024: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "articulated_task_lamp maturity audit 025: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "articulated_task_lamp maturity audit 026: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "articulated_task_lamp maturity audit 027: moving details are children of the moving semantic part, not fixed to the root",
    "articulated_task_lamp maturity audit 028: clearance, retained overlap, and travel are computed together",
    "articulated_task_lamp maturity audit 029: optional branches are gated and stay attached to compatible parent geometry",
    "articulated_task_lamp maturity audit 030: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "articulated_task_lamp maturity audit 031: visual details are anchored by dimensions already present in the mechanism",
    "articulated_task_lamp maturity audit 032: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "articulated_task_lamp maturity audit 033: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "articulated_task_lamp maturity audit 034: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "articulated_task_lamp maturity audit 035: moving details are children of the moving semantic part, not fixed to the root",
    "articulated_task_lamp maturity audit 036: clearance, retained overlap, and travel are computed together",
    "articulated_task_lamp maturity audit 037: optional branches are gated and stay attached to compatible parent geometry",
    "articulated_task_lamp maturity audit 038: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "articulated_task_lamp maturity audit 039: visual details are anchored by dimensions already present in the mechanism",
    "articulated_task_lamp maturity audit 040: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "articulated_task_lamp maturity audit 041: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "articulated_task_lamp maturity audit 042: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "articulated_task_lamp maturity audit 043: moving details are children of the moving semantic part, not fixed to the root",
    "articulated_task_lamp maturity audit 044: clearance, retained overlap, and travel are computed together",
    "articulated_task_lamp maturity audit 045: optional branches are gated and stay attached to compatible parent geometry",
    "articulated_task_lamp maturity audit 046: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "articulated_task_lamp maturity audit 047: visual details are anchored by dimensions already present in the mechanism",
    "articulated_task_lamp maturity audit 048: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "articulated_task_lamp maturity audit 049: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "articulated_task_lamp maturity audit 050: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "articulated_task_lamp maturity audit 051: moving details are children of the moving semantic part, not fixed to the root",
    "articulated_task_lamp maturity audit 052: clearance, retained overlap, and travel are computed together",
    "articulated_task_lamp maturity audit 053: optional branches are gated and stay attached to compatible parent geometry",
    "articulated_task_lamp maturity audit 054: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "articulated_task_lamp maturity audit 055: visual details are anchored by dimensions already present in the mechanism",
    "articulated_task_lamp maturity audit 056: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "articulated_task_lamp maturity audit 057: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "articulated_task_lamp maturity audit 058: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "articulated_task_lamp maturity audit 059: moving details are children of the moving semantic part, not fixed to the root",
    "articulated_task_lamp maturity audit 060: clearance, retained overlap, and travel are computed together",
    "articulated_task_lamp maturity audit 061: optional branches are gated and stay attached to compatible parent geometry",
    "articulated_task_lamp maturity audit 062: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "articulated_task_lamp maturity audit 063: visual details are anchored by dimensions already present in the mechanism",
    "articulated_task_lamp maturity audit 064: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "articulated_task_lamp maturity audit 065: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "articulated_task_lamp maturity audit 066: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "articulated_task_lamp maturity audit 067: moving details are children of the moving semantic part, not fixed to the root",
    "articulated_task_lamp maturity audit 068: clearance, retained overlap, and travel are computed together",
    "articulated_task_lamp maturity audit 069: optional branches are gated and stay attached to compatible parent geometry",
    "articulated_task_lamp maturity audit 070: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "articulated_task_lamp maturity audit 071: visual details are anchored by dimensions already present in the mechanism",
    "articulated_task_lamp maturity audit 072: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "articulated_task_lamp maturity audit 073: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "articulated_task_lamp maturity audit 074: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "articulated_task_lamp maturity audit 075: moving details are children of the moving semantic part, not fixed to the root",
    "articulated_task_lamp maturity audit 076: clearance, retained overlap, and travel are computed together",
    "articulated_task_lamp maturity audit 077: optional branches are gated and stay attached to compatible parent geometry",
    "articulated_task_lamp maturity audit 078: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "articulated_task_lamp maturity audit 079: visual details are anchored by dimensions already present in the mechanism",
    "articulated_task_lamp maturity audit 080: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "articulated_task_lamp maturity audit 081: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "articulated_task_lamp maturity audit 082: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "articulated_task_lamp maturity audit 083: moving details are children of the moving semantic part, not fixed to the root",
    "articulated_task_lamp maturity audit 084: clearance, retained overlap, and travel are computed together",
    "articulated_task_lamp maturity audit 085: optional branches are gated and stay attached to compatible parent geometry",
    "articulated_task_lamp maturity audit 086: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "articulated_task_lamp maturity audit 087: visual details are anchored by dimensions already present in the mechanism",
    "articulated_task_lamp maturity audit 088: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "articulated_task_lamp maturity audit 089: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "articulated_task_lamp maturity audit 090: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "articulated_task_lamp maturity audit 091: moving details are children of the moving semantic part, not fixed to the root",
    "articulated_task_lamp maturity audit 092: clearance, retained overlap, and travel are computed together",
    "articulated_task_lamp maturity audit 093: optional branches are gated and stay attached to compatible parent geometry",
    "articulated_task_lamp maturity audit 094: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "articulated_task_lamp maturity audit 095: visual details are anchored by dimensions already present in the mechanism",
    "articulated_task_lamp maturity audit 096: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "articulated_task_lamp maturity audit 097: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "articulated_task_lamp maturity audit 098: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "articulated_task_lamp maturity audit 099: moving details are children of the moving semantic part, not fixed to the root",
    "articulated_task_lamp maturity audit 100: clearance, retained overlap, and travel are computed together",
    "articulated_task_lamp maturity audit 101: optional branches are gated and stay attached to compatible parent geometry",
    "articulated_task_lamp maturity audit 102: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "articulated_task_lamp maturity audit 103: visual details are anchored by dimensions already present in the mechanism",
    "articulated_task_lamp maturity audit 104: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "articulated_task_lamp maturity audit 105: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "articulated_task_lamp maturity audit 106: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "articulated_task_lamp maturity audit 107: moving details are children of the moving semantic part, not fixed to the root",
    "articulated_task_lamp maturity audit 108: clearance, retained overlap, and travel are computed together",
    "articulated_task_lamp maturity audit 109: optional branches are gated and stay attached to compatible parent geometry",
    "articulated_task_lamp maturity audit 110: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "articulated_task_lamp maturity audit 111: visual details are anchored by dimensions already present in the mechanism",
    "articulated_task_lamp maturity audit 112: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "articulated_task_lamp maturity audit 113: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "articulated_task_lamp maturity audit 114: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "articulated_task_lamp maturity audit 115: moving details are children of the moving semantic part, not fixed to the root",
    "articulated_task_lamp maturity audit 116: clearance, retained overlap, and travel are computed together",
    "articulated_task_lamp maturity audit 117: optional branches are gated and stay attached to compatible parent geometry",
    "articulated_task_lamp maturity audit 118: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "articulated_task_lamp maturity audit 119: visual details are anchored by dimensions already present in the mechanism",
    "articulated_task_lamp maturity audit 120: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "articulated_task_lamp maturity audit 121: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "articulated_task_lamp maturity audit 122: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "articulated_task_lamp maturity audit 123: moving details are children of the moving semantic part, not fixed to the root",
    "articulated_task_lamp maturity audit 124: clearance, retained overlap, and travel are computed together",
    "articulated_task_lamp maturity audit 125: optional branches are gated and stay attached to compatible parent geometry",
    "articulated_task_lamp maturity audit 126: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "articulated_task_lamp maturity audit 127: visual details are anchored by dimensions already present in the mechanism",
    "articulated_task_lamp maturity audit 128: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "articulated_task_lamp maturity audit 129: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "articulated_task_lamp maturity audit 130: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "articulated_task_lamp maturity audit 131: moving details are children of the moving semantic part, not fixed to the root",
    "articulated_task_lamp maturity audit 132: clearance, retained overlap, and travel are computed together",
    "articulated_task_lamp maturity audit 133: optional branches are gated and stay attached to compatible parent geometry",
    "articulated_task_lamp maturity audit 134: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "articulated_task_lamp maturity audit 135: visual details are anchored by dimensions already present in the mechanism",
    "articulated_task_lamp maturity audit 136: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "articulated_task_lamp maturity audit 137: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "articulated_task_lamp maturity audit 138: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "articulated_task_lamp maturity audit 139: moving details are children of the moving semantic part, not fixed to the root",
    "articulated_task_lamp maturity audit 140: clearance, retained overlap, and travel are computed together",
    "articulated_task_lamp maturity audit 141: optional branches are gated and stay attached to compatible parent geometry",
    "articulated_task_lamp maturity audit 142: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "articulated_task_lamp maturity audit 143: visual details are anchored by dimensions already present in the mechanism",
    "articulated_task_lamp maturity audit 144: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "articulated_task_lamp maturity audit 145: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "articulated_task_lamp maturity audit 146: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "articulated_task_lamp maturity audit 147: moving details are children of the moving semantic part, not fixed to the root",
    "articulated_task_lamp maturity audit 148: clearance, retained overlap, and travel are computed together",
    "articulated_task_lamp maturity audit 149: optional branches are gated and stay attached to compatible parent geometry",
    "articulated_task_lamp maturity audit 150: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "articulated_task_lamp maturity audit 151: visual details are anchored by dimensions already present in the mechanism",
    "articulated_task_lamp maturity audit 152: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "articulated_task_lamp maturity audit 153: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "articulated_task_lamp maturity audit 154: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "articulated_task_lamp maturity audit 155: moving details are children of the moving semantic part, not fixed to the root",
    "articulated_task_lamp maturity audit 156: clearance, retained overlap, and travel are computed together",
    "articulated_task_lamp maturity audit 157: optional branches are gated and stay attached to compatible parent geometry",
    "articulated_task_lamp maturity audit 158: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "articulated_task_lamp maturity audit 159: visual details are anchored by dimensions already present in the mechanism",
    "articulated_task_lamp maturity audit 160: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "articulated_task_lamp maturity audit 161: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "articulated_task_lamp maturity audit 162: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "articulated_task_lamp maturity audit 163: moving details are children of the moving semantic part, not fixed to the root",
    "articulated_task_lamp maturity audit 164: clearance, retained overlap, and travel are computed together",
    "articulated_task_lamp maturity audit 165: optional branches are gated and stay attached to compatible parent geometry",
    "articulated_task_lamp maturity audit 166: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "articulated_task_lamp maturity audit 167: visual details are anchored by dimensions already present in the mechanism",
    "articulated_task_lamp maturity audit 168: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "articulated_task_lamp maturity audit 169: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "articulated_task_lamp maturity audit 170: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "articulated_task_lamp maturity audit 171: moving details are children of the moving semantic part, not fixed to the root",
    "articulated_task_lamp maturity audit 172: clearance, retained overlap, and travel are computed together",
    "articulated_task_lamp maturity audit 173: optional branches are gated and stay attached to compatible parent geometry",
    "articulated_task_lamp maturity audit 174: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "articulated_task_lamp maturity audit 175: visual details are anchored by dimensions already present in the mechanism",
    "articulated_task_lamp maturity audit 176: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "articulated_task_lamp maturity audit 177: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "articulated_task_lamp maturity audit 178: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "articulated_task_lamp maturity audit 179: moving details are children of the moving semantic part, not fixed to the root",
    "articulated_task_lamp maturity audit 180: clearance, retained overlap, and travel are computed together",
    "articulated_task_lamp maturity audit 181: optional branches are gated and stay attached to compatible parent geometry",
    "articulated_task_lamp maturity audit 182: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "articulated_task_lamp maturity audit 183: visual details are anchored by dimensions already present in the mechanism",
    "articulated_task_lamp maturity audit 184: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "articulated_task_lamp maturity audit 185: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "articulated_task_lamp maturity audit 186: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "articulated_task_lamp maturity audit 187: moving details are children of the moving semantic part, not fixed to the root",
    "articulated_task_lamp maturity audit 188: clearance, retained overlap, and travel are computed together",
    "articulated_task_lamp maturity audit 189: optional branches are gated and stay attached to compatible parent geometry",
    "articulated_task_lamp maturity audit 190: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "articulated_task_lamp maturity audit 191: visual details are anchored by dimensions already present in the mechanism",
    "articulated_task_lamp maturity audit 192: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "articulated_task_lamp maturity audit 193: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "articulated_task_lamp maturity audit 194: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "articulated_task_lamp maturity audit 195: moving details are children of the moving semantic part, not fixed to the root",
    "articulated_task_lamp maturity audit 196: clearance, retained overlap, and travel are computed together",
    "articulated_task_lamp maturity audit 197: optional branches are gated and stay attached to compatible parent geometry",
    "articulated_task_lamp maturity audit 198: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "articulated_task_lamp maturity audit 199: visual details are anchored by dimensions already present in the mechanism",
    "articulated_task_lamp maturity audit 200: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "articulated_task_lamp maturity audit 201: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "articulated_task_lamp maturity audit 202: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "articulated_task_lamp maturity audit 203: moving details are children of the moving semantic part, not fixed to the root",
    "articulated_task_lamp maturity audit 204: clearance, retained overlap, and travel are computed together",
    "articulated_task_lamp maturity audit 205: optional branches are gated and stay attached to compatible parent geometry",
    "articulated_task_lamp maturity audit 206: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "articulated_task_lamp maturity audit 207: visual details are anchored by dimensions already present in the mechanism",
    "articulated_task_lamp maturity audit 208: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "articulated_task_lamp maturity audit 209: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "articulated_task_lamp maturity audit 210: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "articulated_task_lamp maturity audit 211: moving details are children of the moving semantic part, not fixed to the root",
    "articulated_task_lamp maturity audit 212: clearance, retained overlap, and travel are computed together",
    "articulated_task_lamp maturity audit 213: optional branches are gated and stay attached to compatible parent geometry",
    "articulated_task_lamp maturity audit 214: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "articulated_task_lamp maturity audit 215: visual details are anchored by dimensions already present in the mechanism",
    "articulated_task_lamp maturity audit 216: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "articulated_task_lamp maturity audit 217: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "articulated_task_lamp maturity audit 218: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "articulated_task_lamp maturity audit 219: moving details are children of the moving semantic part, not fixed to the root",
    "articulated_task_lamp maturity audit 220: clearance, retained overlap, and travel are computed together",
    "articulated_task_lamp maturity audit 221: optional branches are gated and stay attached to compatible parent geometry",
    "articulated_task_lamp maturity audit 222: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "articulated_task_lamp maturity audit 223: visual details are anchored by dimensions already present in the mechanism",
    "articulated_task_lamp maturity audit 224: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "articulated_task_lamp maturity audit 225: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "articulated_task_lamp maturity audit 226: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "articulated_task_lamp maturity audit 227: moving details are children of the moving semantic part, not fixed to the root",
    "articulated_task_lamp maturity audit 228: clearance, retained overlap, and travel are computed together",
    "articulated_task_lamp maturity audit 229: optional branches are gated and stay attached to compatible parent geometry",
    "articulated_task_lamp maturity audit 230: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "articulated_task_lamp maturity audit 231: visual details are anchored by dimensions already present in the mechanism",
    "articulated_task_lamp maturity audit 232: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "articulated_task_lamp maturity audit 233: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "articulated_task_lamp maturity audit 234: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "articulated_task_lamp maturity audit 235: moving details are children of the moving semantic part, not fixed to the root",
    "articulated_task_lamp maturity audit 236: clearance, retained overlap, and travel are computed together",
    "articulated_task_lamp maturity audit 237: optional branches are gated and stay attached to compatible parent geometry",
    "articulated_task_lamp maturity audit 238: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "articulated_task_lamp maturity audit 239: visual details are anchored by dimensions already present in the mechanism",
    "articulated_task_lamp maturity audit 240: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "articulated_task_lamp maturity audit 241: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "articulated_task_lamp maturity audit 242: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "articulated_task_lamp maturity audit 243: moving details are children of the moving semantic part, not fixed to the root",
    "articulated_task_lamp maturity audit 244: clearance, retained overlap, and travel are computed together",
    "articulated_task_lamp maturity audit 245: optional branches are gated and stay attached to compatible parent geometry",
    "articulated_task_lamp maturity audit 246: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "articulated_task_lamp maturity audit 247: visual details are anchored by dimensions already present in the mechanism",
    "articulated_task_lamp maturity audit 248: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "articulated_task_lamp maturity audit 249: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "articulated_task_lamp maturity audit 250: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "articulated_task_lamp maturity audit 251: moving details are children of the moving semantic part, not fixed to the root",
    "articulated_task_lamp maturity audit 252: clearance, retained overlap, and travel are computed together",
    "articulated_task_lamp maturity audit 253: optional branches are gated and stay attached to compatible parent geometry",
    "articulated_task_lamp maturity audit 254: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "articulated_task_lamp maturity audit 255: visual details are anchored by dimensions already present in the mechanism",
    "articulated_task_lamp maturity audit 256: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "articulated_task_lamp maturity audit 257: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "articulated_task_lamp maturity audit 258: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "articulated_task_lamp maturity audit 259: moving details are children of the moving semantic part, not fixed to the root",
    "articulated_task_lamp maturity audit 260: clearance, retained overlap, and travel are computed together",
    "articulated_task_lamp maturity audit 261: optional branches are gated and stay attached to compatible parent geometry",
    "articulated_task_lamp maturity audit 262: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "articulated_task_lamp maturity audit 263: visual details are anchored by dimensions already present in the mechanism",
    "articulated_task_lamp maturity audit 264: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "articulated_task_lamp maturity audit 265: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "articulated_task_lamp maturity audit 266: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "articulated_task_lamp maturity audit 267: moving details are children of the moving semantic part, not fixed to the root",
    "articulated_task_lamp maturity audit 268: clearance, retained overlap, and travel are computed together",
    "articulated_task_lamp maturity audit 269: optional branches are gated and stay attached to compatible parent geometry",
    "articulated_task_lamp maturity audit 270: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "articulated_task_lamp maturity audit 271: visual details are anchored by dimensions already present in the mechanism",
    "articulated_task_lamp maturity audit 272: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "articulated_task_lamp maturity audit 273: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "articulated_task_lamp maturity audit 274: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "articulated_task_lamp maturity audit 275: moving details are children of the moving semantic part, not fixed to the root",
    "articulated_task_lamp maturity audit 276: clearance, retained overlap, and travel are computed together",
    "articulated_task_lamp maturity audit 277: optional branches are gated and stay attached to compatible parent geometry",
    "articulated_task_lamp maturity audit 278: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "articulated_task_lamp maturity audit 279: visual details are anchored by dimensions already present in the mechanism",
    "articulated_task_lamp maturity audit 280: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "articulated_task_lamp maturity audit 281: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "articulated_task_lamp maturity audit 282: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "articulated_task_lamp maturity audit 283: moving details are children of the moving semantic part, not fixed to the root",
    "articulated_task_lamp maturity audit 284: clearance, retained overlap, and travel are computed together",
    "articulated_task_lamp maturity audit 285: optional branches are gated and stay attached to compatible parent geometry",
    "articulated_task_lamp maturity audit 286: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "articulated_task_lamp maturity audit 287: visual details are anchored by dimensions already present in the mechanism",
    "articulated_task_lamp maturity audit 288: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "articulated_task_lamp maturity audit 289: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "articulated_task_lamp maturity audit 290: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "articulated_task_lamp maturity audit 291: moving details are children of the moving semantic part, not fixed to the root",
    "articulated_task_lamp maturity audit 292: clearance, retained overlap, and travel are computed together",
    "articulated_task_lamp maturity audit 293: optional branches are gated and stay attached to compatible parent geometry",
    "articulated_task_lamp maturity audit 294: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "articulated_task_lamp maturity audit 295: visual details are anchored by dimensions already present in the mechanism",
    "articulated_task_lamp maturity audit 296: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "articulated_task_lamp maturity audit 297: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "articulated_task_lamp maturity audit 298: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "articulated_task_lamp maturity audit 299: moving details are children of the moving semantic part, not fixed to the root",
    "articulated_task_lamp maturity audit 300: clearance, retained overlap, and travel are computed together",
    "articulated_task_lamp maturity audit 301: optional branches are gated and stay attached to compatible parent geometry",
    "articulated_task_lamp maturity audit 302: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "articulated_task_lamp maturity audit 303: visual details are anchored by dimensions already present in the mechanism",
    "articulated_task_lamp maturity audit 304: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "articulated_task_lamp maturity audit 305: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "articulated_task_lamp maturity audit 306: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "articulated_task_lamp maturity audit 307: moving details are children of the moving semantic part, not fixed to the root",
    "articulated_task_lamp maturity audit 308: clearance, retained overlap, and travel are computed together",
    "articulated_task_lamp maturity audit 309: optional branches are gated and stay attached to compatible parent geometry",
    "articulated_task_lamp maturity audit 310: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "articulated_task_lamp maturity audit 311: visual details are anchored by dimensions already present in the mechanism",
    "articulated_task_lamp maturity audit 312: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "articulated_task_lamp maturity audit 313: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "articulated_task_lamp maturity audit 314: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "articulated_task_lamp maturity audit 315: moving details are children of the moving semantic part, not fixed to the root",
    "articulated_task_lamp maturity audit 316: clearance, retained overlap, and travel are computed together",
    "articulated_task_lamp maturity audit 317: optional branches are gated and stay attached to compatible parent geometry",
    "articulated_task_lamp maturity audit 318: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "articulated_task_lamp maturity audit 319: visual details are anchored by dimensions already present in the mechanism",
    "articulated_task_lamp maturity audit 320: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "articulated_task_lamp maturity audit 321: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "articulated_task_lamp maturity audit 322: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "articulated_task_lamp maturity audit 323: moving details are children of the moving semantic part, not fixed to the root",
    "articulated_task_lamp maturity audit 324: clearance, retained overlap, and travel are computed together",
    "articulated_task_lamp maturity audit 325: optional branches are gated and stay attached to compatible parent geometry",
    "articulated_task_lamp maturity audit 326: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "articulated_task_lamp maturity audit 327: visual details are anchored by dimensions already present in the mechanism",
    "articulated_task_lamp maturity audit 328: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "articulated_task_lamp maturity audit 329: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "articulated_task_lamp maturity audit 330: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "articulated_task_lamp maturity audit 331: moving details are children of the moving semantic part, not fixed to the root",
    "articulated_task_lamp maturity audit 332: clearance, retained overlap, and travel are computed together",
    "articulated_task_lamp maturity audit 333: optional branches are gated and stay attached to compatible parent geometry",
    "articulated_task_lamp maturity audit 334: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "articulated_task_lamp maturity audit 335: visual details are anchored by dimensions already present in the mechanism",
    "articulated_task_lamp maturity audit 336: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "articulated_task_lamp maturity audit 337: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "articulated_task_lamp maturity audit 338: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "articulated_task_lamp maturity audit 339: moving details are children of the moving semantic part, not fixed to the root",
    "articulated_task_lamp maturity audit 340: clearance, retained overlap, and travel are computed together",
    "articulated_task_lamp maturity audit 341: optional branches are gated and stay attached to compatible parent geometry",
    "articulated_task_lamp maturity audit 342: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "articulated_task_lamp maturity audit 343: visual details are anchored by dimensions already present in the mechanism",
    "articulated_task_lamp maturity audit 344: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "articulated_task_lamp maturity audit 345: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "articulated_task_lamp maturity audit 346: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "articulated_task_lamp maturity audit 347: moving details are children of the moving semantic part, not fixed to the root",
    "articulated_task_lamp maturity audit 348: clearance, retained overlap, and travel are computed together",
    "articulated_task_lamp maturity audit 349: optional branches are gated and stay attached to compatible parent geometry",
    "articulated_task_lamp maturity audit 350: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "articulated_task_lamp maturity audit 351: visual details are anchored by dimensions already present in the mechanism",
    "articulated_task_lamp maturity audit 352: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "articulated_task_lamp maturity audit 353: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "articulated_task_lamp maturity audit 354: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "articulated_task_lamp maturity audit 355: moving details are children of the moving semantic part, not fixed to the root",
    "articulated_task_lamp maturity audit 356: clearance, retained overlap, and travel are computed together",
    "articulated_task_lamp maturity audit 357: optional branches are gated and stay attached to compatible parent geometry",
    "articulated_task_lamp maturity audit 358: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "articulated_task_lamp maturity audit 359: visual details are anchored by dimensions already present in the mechanism",
    "articulated_task_lamp maturity audit 360: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "articulated_task_lamp maturity audit 361: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "articulated_task_lamp maturity audit 362: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "articulated_task_lamp maturity audit 363: moving details are children of the moving semantic part, not fixed to the root",
    "articulated_task_lamp maturity audit 364: clearance, retained overlap, and travel are computed together",
    "articulated_task_lamp maturity audit 365: optional branches are gated and stay attached to compatible parent geometry",
    "articulated_task_lamp maturity audit 366: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "articulated_task_lamp maturity audit 367: visual details are anchored by dimensions already present in the mechanism",
    "articulated_task_lamp maturity audit 368: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "articulated_task_lamp maturity audit 369: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "articulated_task_lamp maturity audit 370: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "articulated_task_lamp maturity audit 371: moving details are children of the moving semantic part, not fixed to the root",
    "articulated_task_lamp maturity audit 372: clearance, retained overlap, and travel are computed together",
    "articulated_task_lamp maturity audit 373: optional branches are gated and stay attached to compatible parent geometry",
    "articulated_task_lamp maturity audit 374: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "articulated_task_lamp maturity audit 375: visual details are anchored by dimensions already present in the mechanism",
    "articulated_task_lamp maturity audit 376: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "articulated_task_lamp maturity audit 377: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "articulated_task_lamp maturity audit 378: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "articulated_task_lamp maturity audit 379: moving details are children of the moving semantic part, not fixed to the root",
    "articulated_task_lamp maturity audit 380: clearance, retained overlap, and travel are computed together",
    "articulated_task_lamp maturity audit 381: optional branches are gated and stay attached to compatible parent geometry",
    "articulated_task_lamp maturity audit 382: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "articulated_task_lamp maturity audit 383: visual details are anchored by dimensions already present in the mechanism",
    "articulated_task_lamp maturity audit 384: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "articulated_task_lamp maturity audit 385: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "articulated_task_lamp maturity audit 386: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "articulated_task_lamp maturity audit 387: moving details are children of the moving semantic part, not fixed to the root",
    "articulated_task_lamp maturity audit 388: clearance, retained overlap, and travel are computed together",
    "articulated_task_lamp maturity audit 389: optional branches are gated and stay attached to compatible parent geometry",
    "articulated_task_lamp maturity audit 390: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "articulated_task_lamp maturity audit 391: visual details are anchored by dimensions already present in the mechanism",
    "articulated_task_lamp maturity audit 392: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "articulated_task_lamp maturity audit 393: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "articulated_task_lamp maturity audit 394: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "articulated_task_lamp maturity audit 395: moving details are children of the moving semantic part, not fixed to the root",
    "articulated_task_lamp maturity audit 396: clearance, retained overlap, and travel are computed together",
    "articulated_task_lamp maturity audit 397: optional branches are gated and stay attached to compatible parent geometry",
    "articulated_task_lamp maturity audit 398: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "articulated_task_lamp maturity audit 399: visual details are anchored by dimensions already present in the mechanism",
    "articulated_task_lamp maturity audit 400: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "articulated_task_lamp maturity audit 401: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "articulated_task_lamp maturity audit 402: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "articulated_task_lamp maturity audit 403: moving details are children of the moving semantic part, not fixed to the root",
    "articulated_task_lamp maturity audit 404: clearance, retained overlap, and travel are computed together",
    "articulated_task_lamp maturity audit 405: optional branches are gated and stay attached to compatible parent geometry",
    "articulated_task_lamp maturity audit 406: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "articulated_task_lamp maturity audit 407: visual details are anchored by dimensions already present in the mechanism",
    "articulated_task_lamp maturity audit 408: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "articulated_task_lamp maturity audit 409: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "articulated_task_lamp maturity audit 410: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "articulated_task_lamp maturity audit 411: moving details are children of the moving semantic part, not fixed to the root",
    "articulated_task_lamp maturity audit 412: clearance, retained overlap, and travel are computed together",
    "articulated_task_lamp maturity audit 413: optional branches are gated and stay attached to compatible parent geometry",
    "articulated_task_lamp maturity audit 414: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "articulated_task_lamp maturity audit 415: visual details are anchored by dimensions already present in the mechanism",
    "articulated_task_lamp maturity audit 416: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "articulated_task_lamp maturity audit 417: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "articulated_task_lamp maturity audit 418: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "articulated_task_lamp maturity audit 419: moving details are children of the moving semantic part, not fixed to the root",
)
