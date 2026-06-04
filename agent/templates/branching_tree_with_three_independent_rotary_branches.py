"""Modular procedural template for `branching_tree_with_three_independent_rotary_branches`.

Implements
`articraft_template_authoring/specs_modular_v1/branching_tree_with_three_independent_rotary_branches.md`.

The category identity is exactly three independent rotary branch leaves carried
by one grounded support.  The template uses procedural-first sampling: seed 0 is
ordinary, and `slot_choices_for_seed` reports the actual support/layout/branch
modules selected by the deterministic sampler.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Literal

from sdk import (
    ArticulatedObject,
    ArticulationType,
    AssetContext,
    Box,
    Cylinder,
    MatingContract,
    MotionLimits,
    Origin,
    TestContext,
    TestReport,
)

__modular__ = True

SupportCarrier = Literal[
    "radial_hub_plate",
    "tower_pedestal_collar_stack",
    "rack_spine_side_saddles",
    "mixed_axis_rect_spine",
    "service_panel_backplate_pods",
    "underslung_top_bridge",
]
AxisLayout = Literal[
    "planar_radial_z_axes",
    "stacked_column_z_axes",
    "rack_alternating_side_axes",
    "mixed_xyz_station_axes",
    "panel_pod_x_axes",
    "underslung_hanger_y_axes",
]
BranchArmSet = Literal[
    "flat_linkage_eye_arms",
    "collar_gusseted_tower_arms",
    "pad_fork_tab_rack_set",
    "fork_plate_yoke_tooling_set",
    "metrology_pad_rect_fork_set",
    "underslung_blade_arms",
]
JointLimitStyle = Literal["compact", "medium", "wide"]
TerminalDetailDensity = Literal["plain", "machined", "service_fasteners"]
MaterialStyle = Literal["shop_steel", "dark_fixture", "blue_tooling", "warm_machined"]
FaceSide = Literal[
    "positive_x",
    "negative_x",
    "positive_y",
    "negative_y",
    "positive_z",
    "negative_z",
]

SUPPORT_CARRIERS: tuple[SupportCarrier, ...] = (
    "radial_hub_plate",
    "tower_pedestal_collar_stack",
    "rack_spine_side_saddles",
    "mixed_axis_rect_spine",
    "service_panel_backplate_pods",
    "underslung_top_bridge",
)
AXIS_LAYOUTS: tuple[AxisLayout, ...] = (
    "planar_radial_z_axes",
    "stacked_column_z_axes",
    "rack_alternating_side_axes",
    "mixed_xyz_station_axes",
    "panel_pod_x_axes",
    "underslung_hanger_y_axes",
)
BRANCH_ARM_SETS: tuple[BranchArmSet, ...] = (
    "flat_linkage_eye_arms",
    "collar_gusseted_tower_arms",
    "pad_fork_tab_rack_set",
    "fork_plate_yoke_tooling_set",
    "metrology_pad_rect_fork_set",
    "underslung_blade_arms",
)
JOINT_LIMIT_STYLES: tuple[JointLimitStyle, ...] = ("compact", "medium", "wide")
TERMINAL_DETAIL_DENSITIES: tuple[TerminalDetailDensity, ...] = (
    "plain",
    "machined",
    "service_fasteners",
)
MATERIAL_STYLES: tuple[MaterialStyle, ...] = (
    "shop_steel",
    "dark_fixture",
    "blue_tooling",
    "warm_machined",
)

LEGAL_LAYOUTS: dict[SupportCarrier, tuple[AxisLayout, ...]] = {
    "radial_hub_plate": ("planar_radial_z_axes",),
    "tower_pedestal_collar_stack": ("stacked_column_z_axes",),
    "rack_spine_side_saddles": ("rack_alternating_side_axes", "stacked_column_z_axes"),
    "mixed_axis_rect_spine": ("mixed_xyz_station_axes",),
    "service_panel_backplate_pods": ("panel_pod_x_axes",),
    "underslung_top_bridge": ("underslung_hanger_y_axes",),
}

LEGAL_BRANCHES: dict[SupportCarrier, tuple[BranchArmSet, ...]] = {
    "radial_hub_plate": ("flat_linkage_eye_arms", "pad_fork_tab_rack_set"),
    "tower_pedestal_collar_stack": (
        "collar_gusseted_tower_arms",
        "metrology_pad_rect_fork_set",
    ),
    "rack_spine_side_saddles": ("pad_fork_tab_rack_set", "metrology_pad_rect_fork_set"),
    "mixed_axis_rect_spine": (
        "fork_plate_yoke_tooling_set",
        "pad_fork_tab_rack_set",
        "metrology_pad_rect_fork_set",
    ),
    "service_panel_backplate_pods": ("metrology_pad_rect_fork_set", "underslung_blade_arms"),
    "underslung_top_bridge": ("underslung_blade_arms", "fork_plate_yoke_tooling_set"),
}

PALETTES: dict[MaterialStyle, dict[str, tuple[float, float, float, float]]] = {
    "shop_steel": {
        "support": (0.48, 0.50, 0.52, 1.0),
        "support_dark": (0.20, 0.22, 0.24, 1.0),
        "bearing": (0.68, 0.70, 0.70, 1.0),
        "branch": (0.34, 0.38, 0.42, 1.0),
        "branch_alt": (0.24, 0.30, 0.36, 1.0),
        "terminal": (0.76, 0.78, 0.78, 1.0),
        "rubber": (0.035, 0.035, 0.038, 1.0),
        "accent": (0.90, 0.58, 0.14, 1.0),
    },
    "dark_fixture": {
        "support": (0.16, 0.17, 0.18, 1.0),
        "support_dark": (0.055, 0.058, 0.062, 1.0),
        "bearing": (0.42, 0.44, 0.46, 1.0),
        "branch": (0.62, 0.64, 0.65, 1.0),
        "branch_alt": (0.44, 0.48, 0.50, 1.0),
        "terminal": (0.78, 0.80, 0.80, 1.0),
        "rubber": (0.015, 0.015, 0.018, 1.0),
        "accent": (0.86, 0.68, 0.16, 1.0),
    },
    "blue_tooling": {
        "support": (0.16, 0.23, 0.32, 1.0),
        "support_dark": (0.06, 0.10, 0.16, 1.0),
        "bearing": (0.60, 0.62, 0.64, 1.0),
        "branch": (0.08, 0.30, 0.56, 1.0),
        "branch_alt": (0.52, 0.56, 0.58, 1.0),
        "terminal": (0.82, 0.84, 0.82, 1.0),
        "rubber": (0.020, 0.025, 0.030, 1.0),
        "accent": (0.93, 0.45, 0.12, 1.0),
    },
    "warm_machined": {
        "support": (0.43, 0.35, 0.22, 1.0),
        "support_dark": (0.18, 0.14, 0.09, 1.0),
        "bearing": (0.74, 0.62, 0.36, 1.0),
        "branch": (0.42, 0.39, 0.32, 1.0),
        "branch_alt": (0.58, 0.50, 0.34, 1.0),
        "terminal": (0.82, 0.76, 0.62, 1.0),
        "rubber": (0.05, 0.04, 0.03, 1.0),
        "accent": (0.25, 0.36, 0.48, 1.0),
    },
}


@dataclass(frozen=True)
class BranchingTreeWithThreeIndependentRotaryBranchesConfig:
    support_carrier: SupportCarrier | None = None
    three_station_axis_layout: AxisLayout | None = None
    branch_arm_set: BranchArmSet | None = None
    station_spacing_scale: float = 1.0
    arm_reach_scale: float = 1.0
    joint_limit_style: JointLimitStyle = "medium"
    terminal_detail_density: TerminalDetailDensity = "machined"
    material_style: MaterialStyle = "shop_steel"
    palette: dict[str, tuple[float, float, float, float]] = field(
        default_factory=lambda: dict(PALETTES["shop_steel"])
    )


@dataclass(frozen=True)
class ResolvedBranchingTreeWithThreeIndependentRotaryBranchesConfig:
    support_carrier: SupportCarrier
    three_station_axis_layout: AxisLayout
    branch_arm_set: BranchArmSet
    station_spacing_scale: float
    arm_reach_scale: float
    joint_limit_style: JointLimitStyle
    terminal_detail_density: TerminalDetailDensity
    material_style: MaterialStyle
    palette: dict[str, tuple[float, float, float, float]]
    branch_count: int = 3


@dataclass(frozen=True)
class _Station:
    name: str
    origin: tuple[float, float, float]
    axis: tuple[float, float, float]
    parent_visual: str
    parent_face_side: FaceSide
    child_face_side: FaceSide
    child_mate_axis: str
    child_mate_sign: int
    arm_axis: str
    arm_sign: int
    role: str


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(value)))


def _axis_rpy(axis: str) -> tuple[float, float, float]:
    if axis == "x":
        return (0.0, math.pi / 2.0, 0.0)
    if axis == "y":
        return (math.pi / 2.0, 0.0, 0.0)
    return (0.0, 0.0, 0.0)


def _normal(face_side: FaceSide) -> tuple[float, float, float]:
    axis = face_side[-1]
    sign = 1.0 if face_side.startswith("positive") else -1.0
    if axis == "x":
        return (sign, 0.0, 0.0)
    if axis == "y":
        return (0.0, sign, 0.0)
    return (0.0, 0.0, sign)


def _add_vec(
    a: tuple[float, float, float], b: tuple[float, float, float]
) -> tuple[float, float, float]:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _mul_vec(v: tuple[float, float, float], scalar: float) -> tuple[float, float, float]:
    return (v[0] * scalar, v[1] * scalar, v[2] * scalar)


def _box_size_along(
    axis: str, length: float, width: float, height: float
) -> tuple[float, float, float]:
    if axis == "x":
        return (length, width, height)
    if axis == "y":
        return (width, length, height)
    return (width, height, length)


def _dimension_along(size: tuple[float, float, float], axis: str) -> float:
    return {"x": size[0], "y": size[1], "z": size[2]}[axis]


def _center_along(axis: str, sign: int, distance: float) -> tuple[float, float, float]:
    if axis == "x":
        return (sign * distance, 0.0, 0.0)
    if axis == "y":
        return (0.0, sign * distance, 0.0)
    return (0.0, 0.0, sign * distance)


def _offset_away_from_mating_face(
    station: _Station,
    size: tuple[float, float, float],
) -> tuple[float, float, float]:
    if station.child_mate_axis == station.arm_axis:
        return (0.0, 0.0, 0.0)
    return _center_along(
        station.child_mate_axis,
        station.child_mate_sign,
        _dimension_along(size, station.child_mate_axis) * 0.5 + 0.001,
    )


def _cylinder_axis(
    part,
    *,
    axis: str,
    radius: float,
    length: float,
    center: tuple[float, float, float],
    material: str,
    name: str,
) -> None:
    part.visual(
        Cylinder(radius=radius, length=length),
        origin=Origin(xyz=center, rpy=_axis_rpy(axis)),
        material=material,
        name=name,
    )


def _box_visual(
    part,
    size: tuple[float, float, float],
    center: tuple[float, float, float],
    *,
    material: str,
    name: str,
    rpy: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> None:
    part.visual(Box(size), origin=Origin(xyz=center, rpy=rpy), material=material, name=name)


def _socket_box_center(
    origin: tuple[float, float, float], face_side: FaceSide, thickness: float
) -> tuple[float, float, float]:
    return _add_vec(origin, _mul_vec(_normal(face_side), -0.5 * thickness))


def _add_socket(
    support,
    *,
    station: str,
    origin: tuple[float, float, float],
    face_side: FaceSide,
    size: tuple[float, float, float],
    material: str,
) -> str:
    visual_name = f"{station}_socket"
    axis = face_side[-1]
    thickness = {"x": size[0], "y": size[1], "z": size[2]}[axis]
    _box_visual(
        support,
        size,
        _socket_box_center(origin, face_side, thickness),
        material=material,
        name=visual_name,
    )
    return visual_name


def _motion_limits(style: JointLimitStyle, index: int) -> MotionLimits:
    ranges = {
        "compact": (-0.45, 0.55, 1.0),
        "medium": (-0.75, 0.85, 1.4),
        "wide": (-1.05, 1.10, 1.8),
    }
    lower, upper, velocity = ranges[style]
    offset = (index - 1) * 0.05
    return MotionLimits(
        lower=lower - offset,
        upper=upper + offset,
        effort=14.0 + 3.0 * index,
        velocity=velocity,
    )


def config_from_seed(seed: int) -> BranchingTreeWithThreeIndependentRotaryBranchesConfig:
    rng = random.Random(seed)
    support = rng.choice(SUPPORT_CARRIERS)
    layout = rng.choice(LEGAL_LAYOUTS[support])
    branch = rng.choice(LEGAL_BRANCHES[support])
    return BranchingTreeWithThreeIndependentRotaryBranchesConfig(
        support_carrier=support,
        three_station_axis_layout=layout,
        branch_arm_set=branch,
        station_spacing_scale=rng.uniform(0.88, 1.16),
        arm_reach_scale=rng.uniform(0.84, 1.18),
        joint_limit_style=rng.choice(JOINT_LIMIT_STYLES),
        terminal_detail_density=rng.choice(TERMINAL_DETAIL_DENSITIES),
        material_style=rng.choice(MATERIAL_STYLES),
    )


def resolve_config(
    config: BranchingTreeWithThreeIndependentRotaryBranchesConfig,
) -> ResolvedBranchingTreeWithThreeIndependentRotaryBranchesConfig:
    support = config.support_carrier or "radial_hub_plate"
    if support not in SUPPORT_CARRIERS:
        raise ValueError(f"Unsupported support_carrier: {support!r}")

    legal_layouts = LEGAL_LAYOUTS[support]
    layout = config.three_station_axis_layout or legal_layouts[0]
    if layout not in legal_layouts:
        layout = legal_layouts[0]

    legal_branches = LEGAL_BRANCHES[support]
    branch = config.branch_arm_set or legal_branches[0]
    if branch not in legal_branches:
        branch = legal_branches[0]

    limit_style = config.joint_limit_style
    if limit_style not in JOINT_LIMIT_STYLES:
        raise ValueError(f"Unsupported joint_limit_style: {limit_style!r}")
    detail = config.terminal_detail_density
    if detail not in TERMINAL_DETAIL_DENSITIES:
        raise ValueError(f"Unsupported terminal_detail_density: {detail!r}")
    material_style = config.material_style
    if material_style not in MATERIAL_STYLES:
        raise ValueError(f"Unsupported material_style: {material_style!r}")
    return ResolvedBranchingTreeWithThreeIndependentRotaryBranchesConfig(
        support_carrier=support,
        three_station_axis_layout=layout,
        branch_arm_set=branch,
        station_spacing_scale=_clamp(config.station_spacing_scale, 0.85, 1.20),
        arm_reach_scale=_clamp(config.arm_reach_scale, 0.80, 1.25),
        joint_limit_style=limit_style,
        terminal_detail_density=detail,
        material_style=material_style,
        palette=dict(config.palette or PALETTES[material_style]),
    )


def _register_materials(
    model: ArticulatedObject,
    r: ResolvedBranchingTreeWithThreeIndependentRotaryBranchesConfig,
) -> None:
    palette = dict(PALETTES[r.material_style])
    palette.update(r.palette)
    for name, rgba in palette.items():
        model.material(name, rgba=rgba)


def _build_radial_support(support, r) -> list[_Station]:
    _cylinder_axis(
        support,
        axis="z",
        radius=0.155,
        length=0.030,
        center=(0.0, 0.0, 0.015),
        material="support",
        name="base_disc",
    )
    _cylinder_axis(
        support,
        axis="z",
        radius=0.072,
        length=0.034,
        center=(0.0, 0.0, 0.047),
        material="support_dark",
        name="center_boss",
    )
    stations: list[_Station] = []
    radius = 0.215 * r.station_spacing_scale
    for i, angle in enumerate((0.0, 2.0 * math.pi / 3.0, 4.0 * math.pi / 3.0)):
        c = math.cos(angle)
        s = math.sin(angle)
        _box_visual(
            support,
            (radius, 0.040, 0.026),
            (0.5 * radius * c, 0.5 * radius * s, 0.043),
            material="support_dark",
            name=f"spoke_{i}",
            rpy=(0.0, 0.0, angle),
        )
        origin = (radius * c, radius * s, 0.073)
        visual = _add_socket(
            support,
            station=f"station_{i}",
            origin=origin,
            face_side="positive_z",
            size=(0.078, 0.078, 0.030),
            material="bearing",
        )
        stations.append(
            _Station(
                f"branch_{i}",
                origin,
                (0.0, 0.0, 1.0),
                visual,
                "positive_z",
                "negative_z",
                "z",
                1,
                "x",
                1,
                ("lower", "middle", "upper")[i],
            )
        )
    return stations


def _build_tower_support(support, r) -> list[_Station]:
    _cylinder_axis(
        support,
        axis="z",
        radius=0.150,
        length=0.038,
        center=(0.0, 0.0, 0.019),
        material="support_dark",
        name="round_foot",
    )
    _cylinder_axis(
        support,
        axis="z",
        radius=0.070,
        length=0.064,
        center=(0.0, 0.0, 0.070),
        material="support",
        name="plinth",
    )
    _cylinder_axis(
        support,
        axis="z",
        radius=0.036,
        length=0.640,
        center=(0.0, 0.0, 0.370),
        material="support_dark",
        name="tower_shaft",
    )
    stations: list[_Station] = []
    z_values = [0.230, 0.405, 0.580]
    for i, z in enumerate(z_values):
        angle = (0.35, 2.45, 4.55)[i]
        radius = 0.112 * r.station_spacing_scale
        x = radius * math.cos(angle)
        y = radius * math.sin(angle)
        _cylinder_axis(
            support,
            axis="z",
            radius=0.066,
            length=0.018,
            center=(0.0, 0.0, z - 0.016),
            material="support",
            name=f"collar_flange_{i}",
        )
        if abs(x) >= abs(y):
            _box_visual(
                support,
                (abs(x) + 0.050, 0.046, 0.030),
                (x * 0.5, y * 0.5, z - 0.024),
                material="support_dark",
                name=f"station_bridge_{i}",
            )
            arm_axis = "x"
            arm_sign = 1 if x >= 0.0 else -1
        else:
            _box_visual(
                support,
                (0.046, abs(y) + 0.050, 0.030),
                (x * 0.5, y * 0.5, z - 0.024),
                material="support_dark",
                name=f"station_bridge_{i}",
            )
            arm_axis = "y"
            arm_sign = 1 if y >= 0.0 else -1
        origin = (x, y, z)
        visual = _add_socket(
            support,
            station=f"station_{i}",
            origin=origin,
            face_side="positive_z",
            size=(0.090, 0.090, 0.026),
            material="bearing",
        )
        stations.append(
            _Station(
                f"{('lower', 'middle', 'upper')[i]}_branch",
                origin,
                (0.0, 0.0, 1.0),
                visual,
                "positive_z",
                "negative_z",
                "z",
                1,
                arm_axis,
                arm_sign,
                ("lower", "middle", "upper")[i],
            )
        )
    return stations


def _build_rack_support(support, r) -> list[_Station]:
    _box_visual(
        support, (0.460, 0.160, 0.040), (0.0, 0.0, 0.020), material="support_dark", name="long_foot"
    )
    _box_visual(
        support, (0.090, 0.100, 0.700), (0.0, 0.0, 0.375), material="support", name="upright_spine"
    )
    _box_visual(
        support, (0.120, 0.115, 0.040), (0.0, 0.0, 0.725), material="support_dark", name="top_cap"
    )
    stations: list[_Station] = []
    data = ((0.110, 0.205, 1), (-0.110, 0.395, -1), (0.110, 0.585, 1))
    for i, (x, z, side) in enumerate(data):
        _box_visual(
            support,
            (abs(x) + 0.050, 0.070, 0.032),
            (x * 0.5, 0.0, z - 0.020),
            material="support_dark",
            name=f"side_bridge_{i}",
        )
        origin = (x, 0.0, z)
        visual = _add_socket(
            support,
            station=f"station_{i}",
            origin=origin,
            face_side="positive_z",
            size=(0.082, 0.076, 0.026),
            material="bearing",
        )
        stations.append(
            _Station(
                f"{('lower', 'middle', 'upper')[i]}_branch",
                origin,
                (0.0, 0.0, 1.0),
                visual,
                "positive_z",
                "negative_z",
                "z",
                1,
                "x",
                side,
                ("lower", "middle", "upper")[i],
            )
        )
    return stations


def _build_mixed_spine_support(support, r) -> list[_Station]:
    _box_visual(
        support,
        (0.260, 0.210, 0.035),
        (0.0, 0.0, 0.0175),
        material="support_dark",
        name="base_plate",
    )
    _box_visual(
        support, (0.080, 0.070, 0.620), (0.0, 0.0, 0.330), material="support", name="rect_spine"
    )
    raw = [
        ((0.095, 0.0, 0.165), (0.0, 1.0, 0.0), "positive_y", "negative_y", "y", "x", 1, "lower"),
        ((0.0, -0.100, 0.350), (0.0, 0.0, 1.0), "positive_z", "negative_z", "z", "y", -1, "middle"),
        ((0.095, 0.0, 0.525), (1.0, 0.0, 0.0), "positive_x", "negative_x", "x", "x", 1, "upper"),
    ]
    stations: list[_Station] = []
    for i, (origin, axis, pface, cface, mate_axis, arm_axis, arm_sign, role) in enumerate(raw):
        if pface == "positive_y":
            bridge_size = (0.130, 0.110, 0.050)
        elif pface == "positive_z":
            bridge_size = (0.090, 0.200, 0.035)
        else:
            bridge_size = (0.070, 0.110, 0.050)
        _box_visual(
            support,
            bridge_size,
            _socket_box_center(
                origin,
                pface,
                {"x": bridge_size[0], "y": bridge_size[1], "z": bridge_size[2]}[pface[-1]],
            ),
            material="support_dark",
            name=f"bearing_block_{i}",
        )
        visual = f"bearing_block_{i}"
        stations.append(
            _Station(
                f"{role}_branch",
                origin,
                axis,
                visual,
                pface,
                cface,
                mate_axis,
                1,
                arm_axis,
                arm_sign,
                role,
            )
        )
    return stations


def _build_panel_support(support, r) -> list[_Station]:
    _box_visual(
        support, (0.040, 0.520, 0.700), (0.0, 0.0, 0.350), material="support", name="wall_plate"
    )
    _box_visual(
        support,
        (0.070, 0.090, 0.640),
        (0.040, 0.0, 0.350),
        material="support_dark",
        name="vertical_spine",
    )
    stations: list[_Station] = []
    data = (
        (0.085, -0.165, 0.555, "upper"),
        (0.085, 0.185, 0.350, "middle"),
        (0.085, -0.165, 0.145, "lower"),
    )
    for i, (x, y, z, role) in enumerate(data):
        _box_visual(
            support,
            (0.080, abs(y) + 0.090, 0.045),
            (0.045, y * 0.5, z),
            material="support_dark",
            name=f"pod_bridge_{i}",
        )
        _cylinder_axis(
            support,
            axis="x",
            radius=0.036,
            length=0.034,
            center=(x - 0.017, y, z),
            material="bearing",
            name=f"station_{i}_socket",
        )
        stations.append(
            _Station(
                f"{role}_branch",
                (x, y, z),
                (1.0, 0.0, 0.0),
                f"station_{i}_socket",
                "positive_x",
                "negative_x",
                "x",
                1,
                "y",
                1 if y <= 0.0 else -1,
                role,
            )
        )
    return stations


def _build_underslung_support(support, r) -> list[_Station]:
    _box_visual(
        support,
        (0.420, 0.135, 0.045),
        (0.0, 0.0, 0.720),
        material="support_dark",
        name="top_bridge",
    )
    _box_visual(
        support, (0.360, 0.045, 0.050), (0.0, 0.0, 0.675), material="support", name="bridge_spine"
    )
    stations: list[_Station] = []
    for i, x in enumerate((-0.145, 0.0, 0.145)):
        _box_visual(
            support,
            (0.065, 0.055, 0.092),
            (x, 0.0, 0.632),
            material="support",
            name=f"hanger_web_{i}",
        )
        origin = (x, 0.0, 0.580)
        visual = _add_socket(
            support,
            station=f"station_{i}",
            origin=origin,
            face_side="negative_z",
            size=(0.070, 0.060, 0.030),
            material="bearing",
        )
        stations.append(
            _Station(
                f"{('left', 'middle', 'right')[i]}_branch",
                origin,
                (0.0, 1.0, 0.0),
                visual,
                "negative_z",
                "positive_z",
                "z",
                -1,
                "z",
                -1,
                ("lower", "middle", "upper")[i],
            )
        )
    return stations


def _build_support(model: ArticulatedObject, r) -> list[_Station]:
    support = model.part("support")
    if r.support_carrier == "radial_hub_plate":
        return _build_radial_support(support, r)
    if r.support_carrier == "tower_pedestal_collar_stack":
        return _build_tower_support(support, r)
    if r.support_carrier == "rack_spine_side_saddles":
        return _build_rack_support(support, r)
    if r.support_carrier == "mixed_axis_rect_spine":
        return _build_mixed_spine_support(support, r)
    if r.support_carrier == "service_panel_backplate_pods":
        return _build_panel_support(support, r)
    return _build_underslung_support(support, r)


def _hub_center(station: _Station, hub_len: float) -> tuple[float, float, float]:
    axis = station.child_mate_axis
    sign = station.child_mate_sign
    return _center_along(axis, sign, 0.5 * hub_len)


def _add_branch_hub(
    part, station: _Station, *, material: str, name: str, radius: float, length: float
) -> None:
    _cylinder_axis(
        part,
        axis=station.child_mate_axis,
        radius=radius,
        length=length,
        center=_hub_center(station, length),
        material=material,
        name=name,
    )
    root_size = _box_size_along(station.arm_axis, 0.070, radius * 1.18, radius * 1.10)
    root_center = _add_vec(
        _center_along(station.arm_axis, station.arm_sign, 0.035),
        _offset_away_from_mating_face(station, root_size),
    )
    _box_visual(part, root_size, root_center, material=material, name="root_neck")


def _add_beam(
    part,
    station: _Station,
    *,
    length: float,
    width: float,
    height: float,
    offset: float,
    material: str,
    name: str,
) -> None:
    size = _box_size_along(station.arm_axis, length, width, height)
    center = _add_vec(
        _center_along(station.arm_axis, station.arm_sign, offset + 0.5 * length),
        _offset_away_from_mating_face(station, size),
    )
    _box_visual(
        part,
        size,
        center,
        material=material,
        name=name,
    )


def _add_terminal_box(
    part,
    station: _Station,
    *,
    reach: float,
    size: tuple[float, float, float],
    material: str,
    name: str,
) -> None:
    center = _add_vec(
        _center_along(station.arm_axis, station.arm_sign, reach),
        _offset_away_from_mating_face(station, size),
    )
    _box_visual(part, size, center, material=material, name=name)


def _add_terminal_cylinder(
    part,
    station: _Station,
    *,
    reach: float,
    radius: float,
    length: float,
    material: str,
    name: str,
) -> None:
    size = _box_size_along(station.child_mate_axis, length, radius * 2.0, radius * 2.0)
    center = _add_vec(
        _center_along(station.arm_axis, station.arm_sign, reach),
        _offset_away_from_mating_face(station, size),
    )
    _cylinder_axis(
        part,
        axis=station.child_mate_axis,
        radius=radius,
        length=length,
        center=center,
        material=material,
        name=name,
    )


def _build_flat_linkage(
    part, station: _Station, reach: float, detail: TerminalDetailDensity
) -> None:
    _add_branch_hub(
        part, station, material="bearing", name="branch_hub", radius=0.036, length=0.038
    )
    _add_beam(
        part,
        station,
        length=reach * 0.78,
        width=0.046,
        height=0.026,
        offset=0.030,
        material="branch",
        name="flat_link",
    )
    _add_terminal_cylinder(
        part,
        station,
        reach=reach,
        radius=0.032,
        length=0.026,
        material="terminal",
        name="distal_pad",
    )
    if detail != "plain":
        _add_beam(
            part,
            station,
            length=reach * 0.30,
            width=0.018,
            height=0.032,
            offset=reach * 0.32,
            material="support_dark",
            name="lightening_slot_bar",
        )


def _build_collar_gusset(
    part, station: _Station, reach: float, detail: TerminalDetailDensity
) -> None:
    _add_branch_hub(
        part, station, material="bearing", name="branch_hub", radius=0.042, length=0.050
    )
    _add_beam(
        part,
        station,
        length=reach * 0.74,
        width=0.040,
        height=0.030,
        offset=0.045,
        material="branch_alt",
        name="tapered_arm",
    )
    _add_beam(
        part,
        station,
        length=reach * 0.24,
        width=0.018,
        height=0.060,
        offset=0.070,
        material="support_dark",
        name="root_gusset",
    )
    _add_terminal_box(
        part, station, reach=reach, size=(0.048, 0.075, 0.050), material="terminal", name="tip_stop"
    )
    if detail == "service_fasteners":
        _add_terminal_cylinder(
            part,
            station,
            reach=reach + 0.018,
            radius=0.008,
            length=0.010,
            material="rubber",
            name="tip_fastener",
        )


def _build_pad_fork_tab(
    part, station: _Station, reach: float, detail: TerminalDetailDensity, index: int
) -> None:
    _add_branch_hub(
        part, station, material="bearing", name="branch_hub", radius=0.034, length=0.040
    )
    _add_beam(
        part,
        station,
        length=reach * 0.88,
        width=0.040,
        height=0.026,
        offset=0.034,
        material="branch",
        name="ribbed_beam",
    )
    if index == 0:
        _add_terminal_box(
            part,
            station,
            reach=reach,
            size=(0.048, 0.082, 0.052),
            material="terminal",
            name="rect_pad",
        )
    elif index == 1:
        _add_terminal_box(
            part,
            station,
            reach=reach,
            size=(0.070, 0.070, 0.044),
            material="terminal",
            name="fork_bridge",
        )
        _add_terminal_box(
            part,
            station,
            reach=reach + 0.040,
            size=(0.078, 0.015, 0.032),
            material="terminal",
            name="fork_tine_a",
        )
        _add_terminal_box(
            part,
            station,
            reach=reach - 0.040,
            size=(0.078, 0.015, 0.032),
            material="terminal",
            name="fork_tine_b",
        )
    else:
        _add_terminal_box(
            part,
            station,
            reach=reach,
            size=(0.040, 0.066, 0.110),
            material="terminal",
            name="clamp_tab",
        )
    if detail != "plain":
        _add_beam(
            part,
            station,
            length=reach * 0.20,
            width=0.018,
            height=0.045,
            offset=0.060,
            material="accent",
            name="root_index_mark",
        )


def _build_fork_plate_yoke(
    part, station: _Station, reach: float, detail: TerminalDetailDensity, index: int
) -> None:
    _add_branch_hub(
        part, station, material="bearing", name="branch_hub", radius=0.030, length=0.044
    )
    if index == 0:
        _add_beam(
            part,
            station,
            length=reach * 0.86,
            width=0.036,
            height=0.024,
            offset=0.032,
            material="branch",
            name="fork_stem",
        )
        _add_terminal_box(
            part,
            station,
            reach=reach,
            size=(0.030, 0.112, 0.034),
            material="terminal",
            name="fork_tip_bridge",
        )
    elif index == 1:
        _add_beam(
            part,
            station,
            length=reach * 0.82,
            width=0.026,
            height=0.066,
            offset=0.025,
            material="branch_alt",
            name="profile_plate",
        )
        if detail != "plain":
            _add_terminal_cylinder(
                part,
                station,
                reach=reach * 0.78,
                radius=0.014,
                length=0.012,
                material="rubber",
                name="plate_bore",
            )
    else:
        _add_beam(
            part,
            station,
            length=reach * 0.86,
            width=0.034,
            height=0.026,
            offset=0.030,
            material="branch",
            name="short_yoke_arm",
        )
        _add_terminal_box(
            part,
            station,
            reach=reach,
            size=(0.030, 0.090, 0.050),
            material="terminal",
            name="yoke_bridge",
        )


def _build_metrology_set(
    part, station: _Station, reach: float, detail: TerminalDetailDensity, index: int
) -> None:
    _add_branch_hub(
        part, station, material="bearing", name="branch_hub", radius=0.032, length=0.050
    )
    _add_beam(
        part,
        station,
        length=reach * (0.55 if index == 0 else 0.78),
        width=0.030,
        height=0.028,
        offset=0.036,
        material="branch_alt",
        name="journal_arm",
    )
    if index == 0:
        _add_terminal_cylinder(
            part,
            station,
            reach=reach * 0.72,
            radius=0.038,
            length=0.018,
            material="terminal",
            name="round_pad",
        )
    elif index == 1:
        _add_terminal_box(
            part,
            station,
            reach=reach,
            size=(0.060, 0.088, 0.030),
            material="terminal",
            name="rect_pad",
        )
    else:
        _add_terminal_box(
            part,
            station,
            reach=reach,
            size=(0.032, 0.086, 0.036),
            material="terminal",
            name="angled_fork_base",
        )
    if detail == "service_fasteners":
        screw_reach = reach * 0.72 if index == 0 else reach
        _add_terminal_cylinder(
            part,
            station,
            reach=screw_reach,
            radius=0.006,
            length=0.008,
            material="rubber",
            name="terminal_screw",
        )


def _build_underslung_blade(
    part, station: _Station, reach: float, detail: TerminalDetailDensity, index: int
) -> None:
    _add_branch_hub(
        part, station, material="bearing", name="branch_hub", radius=0.026, length=0.040
    )
    _add_beam(
        part,
        station,
        length=reach * (0.72 + index * 0.06),
        width=0.034,
        height=0.026,
        offset=0.030,
        material="branch",
        name="hanging_blade",
    )
    _add_terminal_box(
        part,
        station,
        reach=reach * (0.85 + index * 0.04),
        size=(0.040, 0.070, 0.038),
        material="terminal",
        name="blade_end_pad",
    )
    if detail != "plain":
        _add_beam(
            part,
            station,
            length=reach * 0.22,
            width=0.018,
            height=0.038,
            offset=0.050,
            material="support_dark",
            name="blade_rib",
        )


def _build_branch_part(model: ArticulatedObject, r, station: _Station, index: int) -> None:
    part = model.part(station.name)
    reach = (0.175 + 0.025 * index) * r.arm_reach_scale
    if r.branch_arm_set == "flat_linkage_eye_arms":
        _build_flat_linkage(part, station, reach, r.terminal_detail_density)
    elif r.branch_arm_set == "collar_gusseted_tower_arms":
        _build_collar_gusset(part, station, reach, r.terminal_detail_density)
    elif r.branch_arm_set == "pad_fork_tab_rack_set":
        _build_pad_fork_tab(part, station, reach, r.terminal_detail_density, index)
    elif r.branch_arm_set == "fork_plate_yoke_tooling_set":
        _build_fork_plate_yoke(part, station, reach, r.terminal_detail_density, index)
    elif r.branch_arm_set == "metrology_pad_rect_fork_set":
        _build_metrology_set(part, station, reach, r.terminal_detail_density, index)
    else:
        _build_underslung_blade(part, station, reach, r.terminal_detail_density, index)


def build_branching_tree_with_three_independent_rotary_branches(
    config: BranchingTreeWithThreeIndependentRotaryBranchesConfig,
    *,
    assets: AssetContext | None = None,
) -> ArticulatedObject:
    r = resolve_config(config)
    model = ArticulatedObject(
        name="branching_tree_with_three_independent_rotary_branches",
        assets=assets,
    )
    _register_materials(model, r)

    stations = _build_support(model, r)
    support = model.get_part("support")
    for index, station in enumerate(stations):
        _build_branch_part(model, r, station, index)
        branch = model.get_part(station.name)
        model.articulation(
            f"support_to_{station.name}",
            ArticulationType.REVOLUTE,
            parent=support,
            child=branch,
            origin=Origin(xyz=station.origin),
            axis=station.axis,
            motion_limits=_motion_limits(r.joint_limit_style, index),
            mating=MatingContract(
                station.parent_visual,
                station.parent_face_side,
                "branch_hub",
                station.child_face_side,
                contact_tol=0.002,
            ),
        )
    model.meta["slot_choices"] = slot_choices_for_config(r)
    return model


def build_seeded_branching_tree_with_three_independent_rotary_branches(
    seed: int,
    *,
    assets: AssetContext | None = None,
) -> ArticulatedObject:
    return build_branching_tree_with_three_independent_rotary_branches(
        config_from_seed(seed),
        assets=assets,
    )


def slot_choices_for_config(
    r: ResolvedBranchingTreeWithThreeIndependentRotaryBranchesConfig,
) -> list[tuple[str, str]]:
    return [
        ("support_carrier", r.support_carrier),
        ("three_station_axis_layout", r.three_station_axis_layout),
        ("branch_arm_set", r.branch_arm_set),
        ("terminal_detail_density", r.terminal_detail_density),
        ("branch_multiplicity", f"{r.branch_count}_independent_branches"),
    ]


def slot_choices_for_seed(seed: int) -> list[tuple[str, str]]:
    return slot_choices_for_config(resolve_config(config_from_seed(seed)))


def run_branching_tree_with_three_independent_rotary_branches_tests(
    object_model: ArticulatedObject,
    config: BranchingTreeWithThreeIndependentRotaryBranchesConfig,
) -> TestReport:
    r = resolve_config(config)
    ctx = TestContext(object_model)
    names = {p.name for p in object_model.parts}
    joints = {j.name: j for j in object_model.articulations}
    branch_names = [
        name for name in names if name.endswith("_branch") or name.startswith("branch_")
    ]
    branch_joints = [j for j in joints.values() if j.articulation_type == ArticulationType.REVOLUTE]

    ctx.check("modular_three_branch_count", len(branch_names) == 3)
    ctx.check("exactly_three_revolute_branch_joints", len(branch_joints) == 3)
    ctx.check("support_present", "support" in names)
    ctx.check(
        "slot_choices_match_config",
        object_model.meta.get("slot_choices") == slot_choices_for_config(r),
    )
    for joint in branch_joints:
        ctx.check(f"{joint.name}_parent_support", joint.parent == "support")
        ctx.check(f"{joint.name}_has_mating_contract", joint.mating is not None)

    for branch_name in branch_names:
        ctx.expect_origin_distance(branch_name, "support", axes="xyz", max_dist=0.90)
        ctx.expect_aabb_overlap(branch_name, "support", axes="xyz", min_overlap=0.0)

    ctx.fail_if_isolated_parts()
    ctx.fail_if_articulation_origin_far_from_geometry(tol=0.020)
    ctx.fail_if_joint_mating_has_gap()
    return ctx.report()
