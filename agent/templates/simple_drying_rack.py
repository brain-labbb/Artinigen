"""Simple drying rack — modular procedural template.

Category identity: a grounded main frame with a fixed center drying deck and two
independently foldable side wings (REVOLUTE), each carrying hanging rails.

PRIMARY_ANCHOR: ``rec_simple_drying_rack_e2af1c3dabb14ad984c3855349f1dffb``

Canonical spec: ``articraft_template_authoring/specs_modular_v1/simple_drying_rack.md``
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Literal

from sdk import (
    ArticulatedObject,
    ArticulationType,
    AssetContext,
    Box,
    Cylinder,
    Inertial,
    MotionLimits,
    Origin,
    Part,
    TestContext,
    TestReport,
)

__modular__ = True

FrameStyle = Literal["standard_tower", "compact_legs", "wide_deck"]
MaterialStyle = Literal["frame_powder", "white_coat", "dark_metal", "teal_coat"]

FRAME_STYLES: tuple[FrameStyle, ...] = (
    "standard_tower",
    "compact_legs",
    "wide_deck",
)
MATERIAL_STYLES: tuple[MaterialStyle, ...] = (
    "frame_powder",
    "white_coat",
    "dark_metal",
    "teal_coat",
)

PALETTES: dict[MaterialStyle, dict[str, tuple[float, float, float, float]]] = {
    "frame_powder": {
        "frame": (0.86, 0.87, 0.88, 1.0),
        "hinge": (0.27, 0.29, 0.31, 1.0),
        "foot": (0.18, 0.19, 0.20, 1.0),
        "fastener": (0.65, 0.67, 0.70, 1.0),
    },
    "white_coat": {
        "frame": (0.92, 0.93, 0.91, 1.0),
        "hinge": (0.34, 0.38, 0.40, 1.0),
        "foot": (0.22, 0.23, 0.24, 1.0),
        "fastener": (0.05, 0.05, 0.045, 1.0),
    },
    "dark_metal": {
        "frame": (0.22, 0.24, 0.26, 1.0),
        "hinge": (0.12, 0.13, 0.14, 1.0),
        "foot": (0.08, 0.09, 0.10, 1.0),
        "fastener": (0.55, 0.57, 0.58, 1.0),
    },
    "teal_coat": {
        "frame": (0.42, 0.62, 0.58, 1.0),
        "hinge": (0.18, 0.36, 0.34, 1.0),
        "foot": (0.14, 0.28, 0.26, 1.0),
        "fastener": (0.72, 0.74, 0.70, 1.0),
    },
}

TUBE_RADIUS = 0.012
RAIL_RADIUS = 0.0045
HINGE_BARREL_RADIUS = 0.010
HINGE_OFFSET = 0.046


@dataclass(frozen=True)
class SimpleDryingRackConfig:
    frame_style: FrameStyle = "standard_tower"
    material_style: MaterialStyle = "frame_powder"
    hanging_rail_count: int = 5
    deck_half_width: float = 0.34
    deck_half_depth: float = 0.25
    deck_height: float = 0.88
    wing_width: float = 0.46
    name: str = "reference_simple_drying_rack"


@dataclass(frozen=True)
class ResolvedSimpleDryingRackConfig:
    frame_style: FrameStyle
    material_style: MaterialStyle
    hanging_rail_count: int
    deck_half_width: float
    deck_half_depth: float
    deck_height: float
    wing_width: float
    wing_half_depth: float
    tube_radius: float
    rail_radius: float
    name: str


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def config_from_seed(seed: int) -> SimpleDryingRackConfig:
    if seed == 0:
        return SimpleDryingRackConfig()

    rng = random.Random(seed)
    frame_style = rng.choice(FRAME_STYLES)
    deck_hw = 0.34 if frame_style != "wide_deck" else round(rng.uniform(0.36, 0.44), 3)
    wing_w = 0.46 if frame_style != "compact_legs" else round(rng.uniform(0.36, 0.42), 3)
    deck_h = 0.88 if frame_style != "compact_legs" else round(rng.uniform(0.62, 0.78), 3)

    return SimpleDryingRackConfig(
        frame_style=frame_style,
        material_style=rng.choice(MATERIAL_STYLES),
        hanging_rail_count=rng.randint(3, 6),
        deck_half_width=deck_hw,
        deck_half_depth=round(rng.uniform(0.20, 0.30), 3),
        deck_height=deck_h,
        wing_width=wing_w,
        name=f"seeded_simple_drying_rack_{seed}",
    )


def resolve_config(config: SimpleDryingRackConfig) -> ResolvedSimpleDryingRackConfig:
    if config.frame_style not in FRAME_STYLES:
        raise ValueError(f"Unsupported frame_style: {config.frame_style}")
    if config.material_style not in PALETTES:
        raise ValueError(f"Unsupported material_style: {config.material_style}")

    rail_count = max(3, min(6, int(config.hanging_rail_count)))
    deck_hw = _clamp(config.deck_half_width, 0.26, 0.46)
    deck_hd = _clamp(config.deck_half_depth, 0.18, 0.32)
    deck_h = _clamp(config.deck_height, 0.58, 0.96)
    wing_w = _clamp(config.wing_width, 0.32, 0.52)

    if config.frame_style == "compact_legs":
        deck_h = min(deck_h, 0.78)
        wing_w = min(wing_w, 0.42)
    elif config.frame_style == "wide_deck":
        deck_hw = max(deck_hw, 0.36)

    return ResolvedSimpleDryingRackConfig(
        frame_style=config.frame_style,
        material_style=config.material_style,
        hanging_rail_count=rail_count,
        deck_half_width=deck_hw,
        deck_half_depth=deck_hd,
        deck_height=deck_h,
        wing_width=wing_w,
        wing_half_depth=deck_hd,
        tube_radius=TUBE_RADIUS,
        rail_radius=RAIL_RADIUS,
        name=config.name,
    )


def _add_rod_x(
    part: Part, name: str, x0: float, x1: float, y: float, z: float, radius: float, material
) -> None:
    part.visual(
        Cylinder(radius=radius, length=abs(x1 - x0)),
        origin=Origin(xyz=((x0 + x1) * 0.5, y, z), rpy=(0.0, math.pi / 2.0, 0.0)),
        material=material,
        name=name,
    )


def _add_rod_y(
    part: Part, name: str, x: float, y0: float, y1: float, z: float, radius: float, material
) -> None:
    part.visual(
        Cylinder(radius=radius, length=abs(y1 - y0)),
        origin=Origin(xyz=(x, (y0 + y1) * 0.5, z), rpy=(-math.pi / 2.0, 0.0, 0.0)),
        material=material,
        name=name,
    )


def _add_rod_z(
    part: Part, name: str, x: float, y: float, z0: float, z1: float, radius: float, material
) -> None:
    part.visual(
        Cylinder(radius=radius, length=abs(z1 - z0)),
        origin=Origin(xyz=(x, y, (z0 + z1) * 0.5)),
        material=material,
        name=name,
    )


def _add_leg_yz(
    part: Part,
    name: str,
    x: float,
    y0: float,
    z0: float,
    y1: float,
    z1: float,
    radius: float,
    material,
) -> None:
    dy = y1 - y0
    dz = z1 - z0
    part.visual(
        Cylinder(radius=radius, length=math.sqrt(dy * dy + dz * dz)),
        origin=Origin(
            xyz=(x, (y0 + y1) * 0.5, (z0 + z1) * 0.5),
            rpy=(-math.atan2(dy, dz), 0.0, 0.0),
        ),
        material=material,
        name=name,
    )


def _build_hinge_link(
    model: ArticulatedObject,
    name: str,
    *,
    side_sign: float,
    r: ResolvedSimpleDryingRackConfig,
    hinge_material,
    fastener_material,
) -> Part:
    part = model.part(name)
    part.inertial = Inertial.from_geometry(
        Box((0.09, 0.54, 0.09)),
        mass=0.35,
        origin=Origin(xyz=(-side_sign * 0.018, 0.0, 0.0)),
    )
    part.visual(
        Box((0.016, 0.36, 0.024)),
        origin=Origin(xyz=(-side_sign * 0.026, 0.0, 0.0)),
        material=hinge_material,
        name="clamp_saddle",
    )
    part.visual(
        Box((0.020, 0.52, 0.070)),
        origin=Origin(xyz=(-side_sign * 0.022, 0.0, 0.0)),
        material=hinge_material,
        name="backplate",
    )
    part.visual(
        Box((0.012, 0.40, 0.018)),
        origin=Origin(xyz=(-side_sign * 0.018, 0.0, -0.014)),
        material=hinge_material,
        name="bridge_arm",
    )
    part.visual(
        Box((0.030, 0.012, 0.054)),
        origin=Origin(xyz=(-side_sign * 0.005, r.wing_half_depth + 0.006, 0.0)),
        material=hinge_material,
        name="front_cheek",
    )
    part.visual(
        Box((0.030, 0.012, 0.054)),
        origin=Origin(xyz=(-side_sign * 0.005, -(r.wing_half_depth + 0.006), 0.0)),
        material=hinge_material,
        name="rear_cheek",
    )
    part.visual(
        Box((0.028, 0.10, 0.010)),
        origin=Origin(xyz=(0.0, 0.0, -0.021)),
        material=hinge_material,
        name="lower_stop",
    )
    part.visual(
        Box((0.024, 0.10, 0.010)),
        origin=Origin(xyz=(-side_sign * 0.010, 0.0, 0.025)),
        material=hinge_material,
        name="upper_guide",
    )
    for visual_name, y_pos in (("front_bolt", 0.14), ("rear_bolt", -0.14)):
        part.visual(
            Cylinder(radius=0.006, length=0.020),
            origin=Origin(xyz=(-side_sign * 0.028, y_pos, 0.0), rpy=(0.0, math.pi / 2.0, 0.0)),
            material=fastener_material,
            name=visual_name,
        )
    return part


def _wing_rail_x_positions(side_sign: float, wing_width: float, count: int) -> list[float]:
    if count <= 1:
        return [side_sign * wing_width * 0.5]
    spacing = wing_width / (count + 1)
    return [side_sign * spacing * (index + 1) for index in range(count)]


def _build_wing(
    model: ArticulatedObject,
    name: str,
    *,
    side_sign: float,
    r: ResolvedSimpleDryingRackConfig,
    frame_material,
    stop_material,
) -> Part:
    part = model.part(name)
    part.inertial = Inertial.from_geometry(
        Box((r.wing_width, 0.52, 0.05)),
        mass=1.4,
        origin=Origin(xyz=(side_sign * r.wing_width * 0.5, 0.0, 0.0)),
    )
    _add_rod_y(
        part,
        "hinge_barrel",
        x=0.0,
        y0=-r.wing_half_depth,
        y1=r.wing_half_depth,
        z=0.0,
        radius=HINGE_BARREL_RADIUS,
        material=frame_material,
    )
    _add_rod_y(
        part,
        "outer_rail",
        x=side_sign * r.wing_width,
        y0=-r.wing_half_depth,
        y1=r.wing_half_depth,
        z=0.0,
        radius=r.tube_radius,
        material=frame_material,
    )
    _add_rod_x(
        part,
        "front_frame_rail",
        x0=0.0,
        x1=side_sign * r.wing_width,
        y=r.wing_half_depth * 0.92,
        z=0.0,
        radius=r.tube_radius,
        material=frame_material,
    )
    _add_rod_x(
        part,
        "rear_frame_rail",
        x0=0.0,
        x1=side_sign * r.wing_width,
        y=-r.wing_half_depth * 0.92,
        z=0.0,
        radius=r.tube_radius,
        material=frame_material,
    )
    for index, x_pos in enumerate(
        _wing_rail_x_positions(side_sign, r.wing_width, r.hanging_rail_count), start=1
    ):
        _add_rod_y(
            part,
            f"hanging_rail_{index}",
            x=x_pos,
            y0=-r.wing_half_depth * 0.92,
            y1=r.wing_half_depth * 0.92,
            z=0.0,
            radius=r.rail_radius,
            material=frame_material,
        )
    part.visual(
        Box((0.020, 0.10, 0.010)),
        origin=Origin(xyz=(0.0, 0.0, -0.011)),
        material=stop_material,
        name="lower_stop_pad",
    )
    part.visual(
        Box((0.018, 0.08, 0.010)),
        origin=Origin(xyz=(0.0, 0.0, 0.011)),
        material=stop_material,
        name="upper_stop_pad",
    )
    return part


def _center_rail_x_positions(half_width: float, count: int) -> list[float]:
    if count <= 1:
        return [0.0]
    span = half_width * 1.28
    step = (2.0 * span) / (count - 1)
    return [-span + step * index for index in range(count)]


def _build_main_frame(model: ArticulatedObject, r: ResolvedSimpleDryingRackConfig, palette) -> Part:
    frame_mat = palette["frame"]
    foot_mat = palette["foot"]
    main = model.part("main_frame")
    main.inertial = Inertial.from_geometry(
        Box((r.deck_half_width * 2.0 + 0.30, r.deck_half_depth * 2.0 + 0.18, r.deck_height)),
        mass=6.5,
        origin=Origin(xyz=(0.0, 0.0, r.deck_height * 0.5)),
    )

    hw = r.deck_half_width
    hd = r.deck_half_depth
    h = r.deck_height

    _add_rod_y(main, "left_side_rail", hw, -hd, hd, h, r.tube_radius, frame_mat)
    _add_rod_y(main, "right_side_rail", -hw, -hd, hd, h, r.tube_radius, frame_mat)
    _add_rod_x(main, "front_top_rail", -hw, hw, hd, h, r.tube_radius, frame_mat)
    _add_rod_x(main, "rear_top_rail", -hw, hw, -hd, h, r.tube_radius, frame_mat)

    for index, x_pos in enumerate(_center_rail_x_positions(hw, r.hanging_rail_count), start=1):
        _add_rod_y(
            main,
            f"center_hanging_rail_{index}",
            x_pos,
            -hd,
            hd,
            h,
            r.rail_radius,
            frame_mat,
        )

    leg_scale = 0.72 if r.frame_style == "compact_legs" else 1.0
    for leg_name, x_pos, y0, y1 in (
        ("front_left_leg", hw, 0.31 * leg_scale, hd - 0.01),
        ("rear_left_leg", hw, -0.31 * leg_scale, -(hd - 0.01)),
        ("front_right_leg", -hw, 0.31 * leg_scale, hd - 0.01),
        ("rear_right_leg", -hw, -0.31 * leg_scale, -(hd - 0.01)),
    ):
        _add_leg_yz(main, leg_name, x_pos, y0, 0.03, y1, h - 0.01, r.tube_radius, frame_mat)

    _add_rod_y(main, "left_lower_tie", hw, -0.29, 0.29, h * 0.41, r.rail_radius, frame_mat)
    _add_rod_y(main, "right_lower_tie", -hw, -0.29, 0.29, h * 0.41, r.rail_radius, frame_mat)
    _add_rod_x(main, "front_stabilizer", -hw, hw, 0.28, h * 0.25, r.rail_radius, frame_mat)
    _add_rod_x(main, "rear_stabilizer", -hw, hw, -0.28, h * 0.25, r.rail_radius, frame_mat)

    for visual_name, x_pos, y_pos in (
        ("front_left_foot", hw, 0.31 * leg_scale),
        ("rear_left_foot", hw, -0.31 * leg_scale),
        ("front_right_foot", -hw, 0.31 * leg_scale),
        ("rear_right_foot", -hw, -0.31 * leg_scale),
    ):
        main.visual(
            Box((0.05, 0.025, 0.030)),
            origin=Origin(xyz=(x_pos, y_pos, 0.015)),
            material=foot_mat,
            name=visual_name,
        )
    return main


def build_simple_drying_rack(
    config: SimpleDryingRackConfig,
    *,
    assets: AssetContext | None = None,
) -> ArticulatedObject:
    r = resolve_config(config)
    model = ArticulatedObject(name=r.name, assets=assets)
    palette = PALETTES[r.material_style]
    for key, rgba in palette.items():
        model.material(key, rgba=rgba)

    main_frame = _build_main_frame(model, r, palette)
    left_hinge = _build_hinge_link(
        model,
        "left_hinge_link",
        side_sign=1.0,
        r=r,
        hinge_material=palette["hinge"],
        fastener_material=palette["fastener"],
    )
    right_hinge = _build_hinge_link(
        model,
        "right_hinge_link",
        side_sign=-1.0,
        r=r,
        hinge_material=palette["hinge"],
        fastener_material=palette["fastener"],
    )
    left_wing = _build_wing(
        model,
        "left_wing_frame",
        side_sign=1.0,
        r=r,
        frame_material=palette["frame"],
        stop_material=palette["hinge"],
    )
    right_wing = _build_wing(
        model,
        "right_wing_frame",
        side_sign=-1.0,
        r=r,
        frame_material=palette["frame"],
        stop_material=palette["hinge"],
    )

    model.articulation(
        "main_to_left_hinge",
        ArticulationType.FIXED,
        parent=main_frame,
        child=left_hinge,
        origin=Origin(xyz=(r.deck_half_width + HINGE_OFFSET, 0.0, r.deck_height)),
    )
    model.articulation(
        "main_to_right_hinge",
        ArticulationType.FIXED,
        parent=main_frame,
        child=right_hinge,
        origin=Origin(xyz=(-(r.deck_half_width + HINGE_OFFSET), 0.0, r.deck_height)),
    )
    model.articulation(
        "left_wing_hinge",
        ArticulationType.REVOLUTE,
        parent=left_hinge,
        child=left_wing,
        origin=Origin(),
        axis=(0.0, -1.0, 0.0),
        motion_limits=MotionLimits(effort=4.0, velocity=2.0, lower=0.0, upper=1.30),
    )
    model.articulation(
        "right_wing_hinge",
        ArticulationType.REVOLUTE,
        parent=right_hinge,
        child=right_wing,
        origin=Origin(),
        axis=(0.0, 1.0, 0.0),
        motion_limits=MotionLimits(effort=4.0, velocity=2.0, lower=0.0, upper=1.30),
    )

    model.meta["slot_choices"] = slot_choices_for_config(r)
    return model


def build_seeded_simple_drying_rack(
    seed: int,
    *,
    assets: AssetContext | None = None,
) -> ArticulatedObject:
    return build_simple_drying_rack(config_from_seed(seed), assets=assets)


def slot_choices_for_config(r: ResolvedSimpleDryingRackConfig) -> list[tuple[str, str]]:
    return [
        ("frame_style", r.frame_style),
        ("material_palette", r.material_style),
        ("wing_multiplicity", "2_foldable_wings"),
        ("hanging_rail_count", f"{r.hanging_rail_count}_rails"),
    ]


def slot_choices_for_seed(seed: int) -> list[tuple[str, str]]:
    return slot_choices_for_config(resolve_config(config_from_seed(seed)))


def run_simple_drying_rack_tests(
    object_model: ArticulatedObject,
    config: SimpleDryingRackConfig,
) -> TestReport:
    r = resolve_config(config)
    ctx = TestContext(object_model)
    part_names = {p.name for p in object_model.parts}
    joint_names = {j.name for j in object_model.articulations}

    ctx.check("main_frame present", "main_frame" in part_names)
    ctx.check("left wing present", "left_wing_frame" in part_names)
    ctx.check("right wing present", "right_wing_frame" in part_names)
    ctx.check("left wing hinge present", "left_wing_hinge" in joint_names)
    ctx.check("right wing hinge present", "right_wing_hinge" in joint_names)
    ctx.check(
        "slot_choices match config",
        object_model.meta.get("slot_choices") == slot_choices_for_config(r),
    )

    main_frame = object_model.get_part("main_frame")
    left_hinge = object_model.get_part("left_hinge_link")
    right_hinge = object_model.get_part("right_hinge_link")
    left_wing = object_model.get_part("left_wing_frame")
    right_wing = object_model.get_part("right_wing_frame")

    ctx.allow_overlap(
        main_frame,
        left_hinge,
        elem_a="left_side_rail",
        elem_b="clamp_saddle",
        reason="hinge clamp captures side rail",
    )
    ctx.allow_overlap(
        main_frame,
        right_hinge,
        elem_a="right_side_rail",
        elem_b="clamp_saddle",
        reason="hinge clamp captures side rail",
    )
    ctx.allow_overlap(
        left_hinge,
        left_wing,
        elem_a="front_cheek",
        elem_b="hinge_barrel",
        reason="wing barrel retained by hinge cheeks",
    )
    ctx.allow_overlap(
        right_hinge,
        right_wing,
        elem_a="front_cheek",
        elem_b="hinge_barrel",
        reason="wing barrel retained by hinge cheeks",
    )

    ctx.fail_if_isolated_parts()
    ctx.fail_if_articulation_origin_far_from_geometry(tol=0.020)
    return ctx.report()


__all__ = [
    "SimpleDryingRackConfig",
    "ResolvedSimpleDryingRackConfig",
    "build_seeded_simple_drying_rack",
    "build_simple_drying_rack",
    "config_from_seed",
    "resolve_config",
    "run_simple_drying_rack_tests",
    "slot_choices_for_config",
    "slot_choices_for_seed",
]
