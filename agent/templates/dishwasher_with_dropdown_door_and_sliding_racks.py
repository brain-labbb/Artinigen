"""Dishwasher with dropdown door and sliding racks — modular procedural template.

Category identity: a grounded tub/cabinet carries one or two PRISMATIC wire racks
that slide toward the user (-Y), plus a REVOLUTE dropdown front door hinged at the
tub sill (opens downward from a closed service pose).

PRIMARY_ANCHOR: ``rec_dishwasher_with_dropdown_door_and_sliding_racks_aece8961933f436dae93467c4bf49035``

Canonical spec:
``articraft_template_authoring/specs_modular_v1/dishwasher_with_dropdown_door_and_sliding_racks.md``
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
    MotionLimits,
    Origin,
    Part,
    TestContext,
    TestReport,
)

__modular__ = True

CabinetStyle = Literal["under_counter_tub", "panel_ready_shell", "integrated_dark"]
MaterialStyle = Literal["brushed_stainless", "dark_integrated", "panel_ready", "warm_panel"]
DoorHandleStyle = Literal["recessed_handle", "flush_pull", "bar_handle"]

CABINET_STYLES: tuple[CabinetStyle, ...] = (
    "under_counter_tub",
    "panel_ready_shell",
    "integrated_dark",
)
MATERIAL_STYLES: tuple[MaterialStyle, ...] = (
    "brushed_stainless",
    "dark_integrated",
    "panel_ready",
    "warm_panel",
)
DOOR_HANDLE_STYLES: tuple[DoorHandleStyle, ...] = (
    "recessed_handle",
    "flush_pull",
    "bar_handle",
)

PALETTES: dict[MaterialStyle, dict[str, tuple[float, float, float, float]]] = {
    "brushed_stainless": {
        "shell": (0.68, 0.70, 0.68, 1.0),
        "dark": (0.08, 0.085, 0.09, 1.0),
        "liner": (0.70, 0.74, 0.76, 1.0),
        "rack": (0.88, 0.90, 0.88, 1.0),
        "accent": (0.35, 0.43, 0.47, 1.0),
        "hardware": (0.03, 0.034, 0.04, 1.0),
    },
    "dark_integrated": {
        "shell": (0.16, 0.17, 0.18, 1.0),
        "dark": (0.035, 0.037, 0.04, 1.0),
        "liner": (0.55, 0.58, 0.60, 1.0),
        "rack": (0.23, 0.25, 0.26, 1.0),
        "accent": (0.42, 0.44, 0.46, 1.0),
        "hardware": (0.11, 0.12, 0.13, 1.0),
    },
    "panel_ready": {
        "shell": (0.86, 0.84, 0.78, 1.0),
        "dark": (0.10, 0.10, 0.11, 1.0),
        "liner": (0.74, 0.76, 0.78, 1.0),
        "rack": (0.30, 0.32, 0.34, 1.0),
        "accent": (0.05, 0.52, 0.22, 1.0),
        "hardware": (0.60, 0.08, 0.06, 1.0),
    },
    "warm_panel": {
        "shell": (0.78, 0.72, 0.64, 1.0),
        "dark": (0.12, 0.11, 0.10, 1.0),
        "liner": (0.68, 0.66, 0.62, 1.0),
        "rack": (0.82, 0.80, 0.76, 1.0),
        "accent": (0.44, 0.36, 0.28, 1.0),
        "hardware": (0.18, 0.19, 0.20, 1.0),
    },
}


@dataclass(frozen=True)
class DishwasherWithDropdownDoorAndSlidingRacksConfig:
    cabinet_style: CabinetStyle = "under_counter_tub"
    material_style: MaterialStyle = "brushed_stainless"
    door_handle_style: DoorHandleStyle = "recessed_handle"
    rack_count: int = 2
    has_detergent_cover: bool = True
    cabinet_width: float = 0.62
    cabinet_depth: float = 0.68
    cabinet_height: float = 0.86
    name: str = "reference_dishwasher_with_dropdown_door_and_sliding_racks"


@dataclass(frozen=True)
class ResolvedDishwasherWithDropdownDoorAndSlidingRacksConfig:
    cabinet_style: CabinetStyle
    material_style: MaterialStyle
    door_handle_style: DoorHandleStyle
    rack_count: int
    has_detergent_cover: bool
    cabinet_width: float
    cabinet_depth: float
    cabinet_height: float
    tub_depth: float
    tub_height: float
    door_hinge_y: float
    door_hinge_z: float
    lower_rack_z: float
    upper_rack_z: float
    lower_travel: float
    upper_travel: float
    name: str


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def config_from_seed(seed: int) -> DishwasherWithDropdownDoorAndSlidingRacksConfig:
    if seed == 0:
        return DishwasherWithDropdownDoorAndSlidingRacksConfig()

    rng = random.Random(seed)
    return DishwasherWithDropdownDoorAndSlidingRacksConfig(
        cabinet_style=rng.choice(CABINET_STYLES),
        material_style=rng.choice(MATERIAL_STYLES),
        door_handle_style=rng.choice(DOOR_HANDLE_STYLES),
        rack_count=rng.choice((1, 2)),
        has_detergent_cover=rng.choice((True, False)),
        cabinet_width=round(rng.uniform(0.52, 0.72), 3),
        cabinet_depth=round(rng.uniform(0.58, 0.76), 3),
        cabinet_height=round(rng.uniform(0.78, 0.92), 3),
        name=f"seeded_dishwasher_with_dropdown_door_and_sliding_racks_{seed}",
    )


def resolve_config(
    config: DishwasherWithDropdownDoorAndSlidingRacksConfig,
) -> ResolvedDishwasherWithDropdownDoorAndSlidingRacksConfig:
    if config.cabinet_style not in CABINET_STYLES:
        raise ValueError(f"Unsupported cabinet_style: {config.cabinet_style}")
    if config.material_style not in PALETTES:
        raise ValueError(f"Unsupported material_style: {config.material_style}")

    rack_count = max(1, min(2, int(config.rack_count)))
    width = _clamp(config.cabinet_width, 0.50, 0.76)
    depth = _clamp(config.cabinet_depth, 0.54, 0.80)
    height = _clamp(config.cabinet_height, 0.74, 0.96)

    tub_depth = depth * 0.86
    tub_height = height * 0.90
    hinge_y = -(tub_depth / 2.0) + 0.02
    hinge_z = tub_height * 0.12
    lower_z = tub_height * 0.24
    upper_z = tub_height * 0.58
    lower_travel = round(min(0.40, tub_depth * 0.52), 3)
    upper_travel = round(min(0.34, tub_depth * 0.44), 3)

    return ResolvedDishwasherWithDropdownDoorAndSlidingRacksConfig(
        cabinet_style=config.cabinet_style,
        material_style=config.material_style,
        door_handle_style=config.door_handle_style,
        rack_count=rack_count,
        has_detergent_cover=bool(config.has_detergent_cover),
        cabinet_width=width,
        cabinet_depth=depth,
        cabinet_height=height,
        tub_depth=tub_depth,
        tub_height=tub_height,
        door_hinge_y=hinge_y,
        door_hinge_z=hinge_z,
        lower_rack_z=lower_z,
        upper_rack_z=upper_z,
        lower_travel=lower_travel,
        upper_travel=upper_travel,
        name=config.name,
    )


def _box(part: Part, name: str, size, xyz, material) -> None:
    part.visual(Box(size), origin=Origin(xyz=xyz), material=material, name=name)


def _rack_wirework(
    part: Part,
    *,
    width: float,
    depth: float,
    wall_height: float,
    wire: float,
    runner_z: float,
    material,
    shallow: bool,
) -> None:
    half_w = width / 2.0
    half_d = depth / 2.0

    _box(
        part,
        "runner_0",
        (0.024, depth + 0.035, 0.012),
        (-(half_w + 0.018), 0.0, runner_z),
        material,
    )
    _box(part, "runner_1", (0.024, depth + 0.035, 0.012), (half_w + 0.018, 0.0, runner_z), material)

    z0 = 0.0
    _box(part, "front_floor_wire", (width, wire, wire), (0.0, -half_d, z0), material)
    _box(part, "rear_floor_wire", (width, wire, wire), (0.0, half_d, z0), material)
    _box(part, "side_floor_wire_0", (wire, depth, wire), (-half_w, 0.0, z0), material)
    _box(part, "side_floor_wire_1", (wire, depth, wire), (half_w, 0.0, z0), material)

    for idx, y in enumerate((-0.15, -0.075, 0.0, 0.075, 0.15)):
        _box(part, f"floor_cross_{idx}", (width, wire, wire), (0.0, y, z0), material)
    for idx, x in enumerate((-0.18, -0.09, 0.0, 0.09, 0.18)):
        _box(part, f"floor_long_{idx}", (wire, depth, wire), (x, 0.0, z0 + 0.001), material)

    for i, sx in enumerate((-1.0, 1.0)):
        _box(
            part,
            f"upper_side_wire_{i}",
            (wire, depth, wire),
            (sx * half_w, 0.0, wall_height),
            material,
        )
        for j, y in enumerate((-half_d, -half_d / 2.0, 0.0, half_d / 2.0, half_d)):
            _box(
                part,
                f"side_upright_{i}_{j}",
                (wire, wire, wall_height),
                (sx * half_w, y, wall_height / 2.0),
                material,
            )
    _box(part, "upper_front_wire", (width, wire, wire), (0.0, -half_d, wall_height), material)
    _box(part, "upper_rear_wire", (width, wire, wire), (0.0, half_d, wall_height), material)

    if shallow:
        for idx, x in enumerate((-0.15, -0.05, 0.05, 0.15)):
            _box(
                part,
                f"cutlery_divider_{idx}",
                (wire, depth - 0.035, wall_height * 0.75),
                (x, 0.0, wall_height * 0.38),
                material,
            )
    else:
        for row, y in enumerate((-0.15, -0.075, 0.0, 0.075)):
            for col, x in enumerate((-0.18, -0.09, 0.0, 0.09, 0.18)):
                _box(part, f"tine_{row}_{col}", (wire, wire, 0.072), (x, y, 0.036), material)


def _build_tub(
    model: ArticulatedObject, r: ResolvedDishwasherWithDropdownDoorAndSlidingRacksConfig, palette
) -> Part:
    tub = model.part("tub")
    w = r.cabinet_width
    d = r.tub_depth
    h = r.tub_height
    shell = palette["shell"]
    dark = palette["dark"]
    liner = palette["liner"]
    accent = palette["accent"]

    half_w = w / 2.0
    half_d = d / 2.0

    if r.cabinet_style == "integrated_dark":
        _box(
            tub,
            "side_shell_0",
            (0.025, r.cabinet_depth, h),
            (-(half_w + 0.012), 0.0, h / 2.0),
            dark,
        )
        _box(tub, "side_shell_1", (0.025, r.cabinet_depth, h), (half_w + 0.012, 0.0, h / 2.0), dark)
        _box(tub, "rear_shell", (w + 0.05, 0.025, h), (0.0, half_d + 0.02, h / 2.0), dark)
        _box(tub, "toe_kick", (w + 0.05, r.cabinet_depth, 0.08), (0.0, 0.0, 0.04), dark)

    _box(tub, "tub_floor", (w, d, 0.020), (0.0, 0.0, 0.010), liner)
    _box(tub, "tub_ceiling", (w, d, 0.020), (0.0, 0.0, h - 0.010), liner)
    _box(tub, "tub_rear", (w, 0.025, h), (0.0, half_d - 0.0125, h / 2.0), liner)
    _box(tub, "tub_side_0", (0.025, d, h), (-(half_w - 0.0125), 0.0, h / 2.0), liner)
    _box(tub, "tub_side_1", (0.025, d, h), (half_w - 0.0125, 0.0, h / 2.0), liner)
    _box(tub, "front_sill", (w, 0.026, 0.055), (0.0, -half_d, h * 0.10), shell)
    _box(tub, "front_header", (w, 0.026, 0.060), (0.0, -half_d, h * 0.94), shell)

    for idx, x in enumerate((-(half_w - 0.04), half_w - 0.04)):
        _box(tub, f"lower_rail_{idx}", (0.035, d * 0.76, 0.012), (x, 0.0, r.lower_rack_z), shell)
        if r.rack_count > 1:
            _box(
                tub, f"upper_rail_{idx}", (0.035, d * 0.72, 0.012), (x, 0.0, r.upper_rack_z), shell
            )
        _box(
            tub, f"roller_{idx}", (0.035, 0.045, 0.028), (x, -half_d + 0.05, r.lower_rack_z), shell
        )

    tub.visual(
        Cylinder(radius=0.008, length=w * 0.95),
        origin=Origin(xyz=(0.0, r.door_hinge_y, r.door_hinge_z), rpy=(0.0, math.pi / 2.0, 0.0)),
        material=dark,
        name="door_hinge_pin",
    )
    for idx, x in enumerate((-(half_w - 0.03), half_w - 0.03)):
        _box(
            tub,
            f"hinge_bracket_{idx}",
            (0.040, 0.055, 0.050),
            (x, r.door_hinge_y, r.door_hinge_z),
            dark,
        )

    _box(
        tub,
        "lower_spray_pedestal",
        (0.036, 0.036, 0.034),
        (0.0, 0.0, r.lower_rack_z - 0.06),
        accent,
    )
    if r.rack_count > 1:
        _box(
            tub,
            "upper_spray_nipple",
            (0.024, 0.024, 0.012),
            (0.0, 0.0, r.upper_rack_z - 0.05),
            accent,
        )

    if r.cabinet_style == "panel_ready_shell":
        _box(tub, "counter_shadow", (w + 0.04, r.cabinet_depth, 0.035), (0.0, 0.0, h + 0.02), shell)

    return tub


def _build_door(
    model: ArticulatedObject,
    r: ResolvedDishwasherWithDropdownDoorAndSlidingRacksConfig,
    palette,
) -> Part:
    door = model.part("door")
    w = r.cabinet_width
    shell = palette["shell"]
    liner = palette["liner"]
    dark = palette["dark"]
    accent = palette["accent"]
    hardware = palette["hardware"]

    panel_y = r.door_hinge_y - 0.0325
    _box(door, "stainless_panel", (w * 0.97, 0.715, 0.043), (0.0, panel_y, -0.0185), shell)
    _box(
        door,
        "inner_liner",
        (w * 0.87, r.tub_depth * 0.85, 0.018),
        (0.0, panel_y + 0.0225, 0.009),
        liner,
    )
    _box(door, "control_strip", (w * 0.90, 0.090, 0.020), (0.0, panel_y - 0.3125, 0.018), dark)

    if r.door_handle_style == "recessed_handle":
        _box(door, "recess_handle", (w * 0.48, 0.030, 0.016), (0.0, panel_y - 0.2475, -0.043), dark)
    elif r.door_handle_style == "flush_pull":
        _box(door, "flush_pull", (w * 0.55, 0.018, 0.010), (0.0, panel_y - 0.20, -0.040), hardware)
    else:
        _box(door, "bar_handle", (w * 0.62, 0.022, 0.022), (0.0, panel_y - 0.24, -0.050), hardware)

    door.visual(
        Cylinder(radius=0.014, length=w * 0.80),
        origin=Origin(xyz=(0.0, 0.0, 0.0), rpy=(0.0, math.pi / 2.0, 0.0)),
        material=shell,
        name="door_hinge_knuckle",
    )
    _box(door, "hinge_leaf", (w * 0.84, 0.050, 0.008), (0.0, 0.025, -0.018), shell)

    if r.cabinet_style == "panel_ready_shell":
        _box(door, "start_button", (0.060, 0.030, 0.010), (-0.20, panel_y - 0.3125, 0.028), accent)
        _box(
            door, "cancel_button", (0.060, 0.030, 0.010), (-0.12, panel_y - 0.3125, 0.028), hardware
        )

    if r.has_detergent_cover:
        _box(
            door, "detergent_recess", (0.18, 0.13, 0.012), (-0.14, panel_y + 0.0675, 0.020), accent
        )

    return door


def build_dishwasher_with_dropdown_door_and_sliding_racks(
    config: DishwasherWithDropdownDoorAndSlidingRacksConfig,
    *,
    assets: AssetContext | None = None,
) -> ArticulatedObject:
    r = resolve_config(config)
    model = ArticulatedObject(name=r.name, assets=assets)
    palette = PALETTES[r.material_style]
    for key, rgba in palette.items():
        model.material(key, rgba=rgba)

    tub = _build_tub(model, r, palette)
    door = _build_door(model, r, palette)

    door_limits = MotionLimits(effort=80.0, velocity=1.0, lower=-1.45, upper=0.0)
    model.articulation(
        "tub_to_door",
        ArticulationType.REVOLUTE,
        parent=tub,
        child=door,
        origin=Origin(xyz=(0.0, r.door_hinge_y, r.door_hinge_z)),
        axis=(1.0, 0.0, 0.0),
        motion_limits=door_limits,
    )

    if r.has_detergent_cover:
        cover = model.part("detergent_cover")
        _box(cover, "cover_panel", (0.155, 0.105, 0.008), (0.0, -0.0525, 0.004), palette["accent"])
        model.articulation(
            "door_to_detergent_cover",
            ArticulationType.REVOLUTE,
            parent=door,
            child=cover,
            origin=Origin(xyz=(-0.14, r.door_hinge_y + 0.12, 0.026)),
            axis=(-1.0, 0.0, 0.0),
            motion_limits=MotionLimits(effort=1.5, velocity=1.5, lower=0.0, upper=1.2),
        )

    rack_w = r.cabinet_width * 0.82
    rack_d = r.tub_depth * 0.68
    lower = model.part("lower_rack")
    _rack_wirework(
        lower,
        width=rack_w,
        depth=rack_d,
        wall_height=0.135,
        wire=0.008,
        runner_z=0.0,
        material=palette["rack"],
        shallow=False,
    )
    model.articulation(
        "tub_to_lower_rack",
        ArticulationType.PRISMATIC,
        parent=tub,
        child=lower,
        origin=Origin(xyz=(0.0, 0.0, r.lower_rack_z)),
        axis=(0.0, -1.0, 0.0),
        motion_limits=MotionLimits(
            effort=25.0,
            velocity=0.35,
            lower=0.0,
            upper=r.lower_travel,
        ),
    )

    if r.rack_count > 1:
        upper = model.part("upper_rack")
        _rack_wirework(
            upper,
            width=rack_w,
            depth=rack_d * 0.94,
            wall_height=0.115,
            wire=0.007,
            runner_z=0.0,
            material=palette["rack"],
            shallow=True,
        )
        model.articulation(
            "tub_to_upper_rack",
            ArticulationType.PRISMATIC,
            parent=tub,
            child=upper,
            origin=Origin(xyz=(0.0, 0.0, r.upper_rack_z)),
            axis=(0.0, -1.0, 0.0),
            motion_limits=MotionLimits(
                effort=20.0,
                velocity=0.30,
                lower=0.0,
                upper=r.upper_travel,
            ),
        )

    model.meta["slot_choices"] = slot_choices_for_config(r)
    return model


def build_seeded_dishwasher_with_dropdown_door_and_sliding_racks(
    seed: int,
    *,
    assets: AssetContext | None = None,
) -> ArticulatedObject:
    return build_dishwasher_with_dropdown_door_and_sliding_racks(
        config_from_seed(seed), assets=assets
    )


def slot_choices_for_config(
    r: ResolvedDishwasherWithDropdownDoorAndSlidingRacksConfig,
) -> list[tuple[str, str]]:
    return [
        ("cabinet_body", r.cabinet_style),
        ("material_palette", r.material_style),
        ("door_handle", r.door_handle_style),
        ("rack_multiplicity", f"{r.rack_count}_racks"),
        ("detergent_cover", "with_cover" if r.has_detergent_cover else "no_cover"),
    ]


def slot_choices_for_seed(seed: int) -> list[tuple[str, str]]:
    return slot_choices_for_config(resolve_config(config_from_seed(seed)))


def run_dishwasher_with_dropdown_door_and_sliding_racks_tests(
    object_model: ArticulatedObject,
    config: DishwasherWithDropdownDoorAndSlidingRacksConfig,
) -> TestReport:
    r = resolve_config(config)
    ctx = TestContext(object_model)
    part_names = {p.name for p in object_model.parts}
    joint_names = {j.name for j in object_model.articulations}

    ctx.check("tub part present", "tub" in part_names)
    ctx.check("door part present", "door" in part_names)
    ctx.check("tub_to_door joint present", "tub_to_door" in joint_names)
    ctx.check("lower_rack part present", "lower_rack" in part_names)
    ctx.check("tub_to_lower_rack joint present", "tub_to_lower_rack" in joint_names)

    door_joint = object_model.get_articulation("tub_to_door")
    ctx.check(
        "door hinge axis is +X",
        tuple(abs(v) for v in door_joint.axis) == (1.0, 0.0, 0.0),
        details=str(door_joint.axis),
    )

    lower_joint = object_model.get_articulation("tub_to_lower_rack")
    ctx.check(
        "lower rack slides along -Y",
        tuple(abs(v) for v in lower_joint.axis) == (0.0, 1.0, 0.0),
        details=str(lower_joint.axis),
    )

    if r.rack_count > 1:
        ctx.check("upper_rack part present", "upper_rack" in part_names)
        ctx.check("tub_to_upper_rack joint present", "tub_to_upper_rack" in joint_names)
    else:
        ctx.check("no upper rack when single-rack config", "upper_rack" not in part_names)

    if r.has_detergent_cover:
        ctx.check("detergent_cover present", "detergent_cover" in part_names)
    else:
        ctx.check("no detergent cover when disabled", "detergent_cover" not in part_names)

    tub = object_model.get_part("tub")
    door = object_model.get_part("door")
    lower_rack = object_model.get_part("lower_rack")

    ctx.allow_overlap(
        tub,
        door,
        elem_a="door_hinge_pin",
        elem_b="door_hinge_knuckle",
        reason="hinge pin captured inside door knuckle",
    )
    ctx.allow_overlap(tub, lower_rack, reason="rack slides inside tub cavity")
    if r.rack_count > 1:
        upper_rack = object_model.get_part("upper_rack")
        ctx.allow_overlap(tub, upper_rack, reason="upper rack slides inside tub cavity")

    ctx.fail_if_articulation_origin_far_from_geometry(tol=0.020)
    return ctx.report()


__all__ = [
    "DishwasherWithDropdownDoorAndSlidingRacksConfig",
    "ResolvedDishwasherWithDropdownDoorAndSlidingRacksConfig",
    "build_dishwasher_with_dropdown_door_and_sliding_racks",
    "build_seeded_dishwasher_with_dropdown_door_and_sliding_racks",
    "config_from_seed",
    "resolve_config",
    "run_dishwasher_with_dropdown_door_and_sliding_racks_tests",
    "slot_choices_for_config",
    "slot_choices_for_seed",
]
