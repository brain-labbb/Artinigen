"""Modular procedural template for elevators."""

from __future__ import annotations

import random
from dataclasses import dataclass, replace
from typing import Literal

from sdk import (
    ArticulatedObject,
    ArticulationType,
    AssetContext,
    Box,
    Cylinder,
    MotionLimits,
    Origin,
    TestContext,
    TestReport,
)

__modular__ = True

ShaftStyle = Literal[
    "open_steel_hoistway",
    "concrete_core",
    "glass_observation_tower",
]
CabinStyle = Literal[
    "box_cab",
    "glass_cab",
    "service_freight_cab",
]
DoorStyle = Literal[
    "center_split_doors",
    "telescopic_side_doors",
    "manual_scissor_gate",
]
DriveStyle = Literal[
    "traction_machine_room",
    "machine_room_less_sheave",
    "hydraulic_piston",
]
GuideStyle = Literal[
    "twin_t_rails",
    "boxed_guide_rails",
    "roller_guide_clusters",
]
CounterweightStyle = Literal["none", "rear_counterweight"]
BankStyle = Literal["single_car", "dual_car_bank"]
LandingStyle = Literal[
    "plain_landings",
    "numbered_call_panels",
    "industrial_thresholds",
]
MaterialStyle = Literal[
    "brushed_steel",
    "painted_cream",
    "industrial_gray",
    "blue_glass",
]

SHAFT_STYLES: tuple[ShaftStyle, ...] = (
    "open_steel_hoistway",
    "concrete_core",
    "glass_observation_tower",
)
CABIN_STYLES: tuple[CabinStyle, ...] = (
    "box_cab",
    "glass_cab",
    "service_freight_cab",
)
DOOR_STYLES: tuple[DoorStyle, ...] = (
    "center_split_doors",
    "telescopic_side_doors",
    "manual_scissor_gate",
)
DRIVE_STYLES: tuple[DriveStyle, ...] = (
    "traction_machine_room",
    "machine_room_less_sheave",
    "hydraulic_piston",
)
GUIDE_STYLES: tuple[GuideStyle, ...] = (
    "twin_t_rails",
    "boxed_guide_rails",
    "roller_guide_clusters",
)
COUNTERWEIGHT_STYLES: tuple[CounterweightStyle, ...] = ("none", "rear_counterweight")
BANK_STYLES: tuple[BankStyle, ...] = ("single_car", "dual_car_bank")
LANDING_STYLES: tuple[LandingStyle, ...] = (
    "plain_landings",
    "numbered_call_panels",
    "industrial_thresholds",
)
MATERIAL_STYLES: tuple[MaterialStyle, ...] = (
    "brushed_steel",
    "painted_cream",
    "industrial_gray",
    "blue_glass",
)

PALETTES: dict[MaterialStyle, dict[str, tuple[float, float, float, float]]] = {
    "brushed_steel": {
        "shaft": (0.54, 0.55, 0.53, 1.0),
        "cab": (0.70, 0.70, 0.66, 1.0),
        "rail": (0.18, 0.19, 0.20, 1.0),
        "door": (0.62, 0.64, 0.64, 1.0),
        "glass": (0.20, 0.34, 0.42, 0.32),
        "accent": (0.12, 0.18, 0.26, 1.0),
        "dark": (0.04, 0.045, 0.05, 1.0),
    },
    "painted_cream": {
        "shaft": (0.70, 0.68, 0.60, 1.0),
        "cab": (0.86, 0.82, 0.70, 1.0),
        "rail": (0.20, 0.20, 0.19, 1.0),
        "door": (0.78, 0.76, 0.66, 1.0),
        "glass": (0.18, 0.32, 0.38, 0.30),
        "accent": (0.60, 0.12, 0.08, 1.0),
        "dark": (0.07, 0.07, 0.06, 1.0),
    },
    "industrial_gray": {
        "shaft": (0.38, 0.39, 0.38, 1.0),
        "cab": (0.50, 0.51, 0.49, 1.0),
        "rail": (0.10, 0.11, 0.11, 1.0),
        "door": (0.44, 0.45, 0.43, 1.0),
        "glass": (0.16, 0.28, 0.34, 0.28),
        "accent": (0.86, 0.66, 0.12, 1.0),
        "dark": (0.035, 0.038, 0.040, 1.0),
    },
    "blue_glass": {
        "shaft": (0.32, 0.34, 0.36, 1.0),
        "cab": (0.42, 0.47, 0.50, 1.0),
        "rail": (0.10, 0.12, 0.14, 1.0),
        "door": (0.45, 0.52, 0.56, 1.0),
        "glass": (0.10, 0.32, 0.50, 0.36),
        "accent": (0.78, 0.84, 0.86, 1.0),
        "dark": (0.025, 0.035, 0.045, 1.0),
    },
}


@dataclass(frozen=True)
class ElevatorConfig:
    shaft_style: ShaftStyle | None = None
    cabin_style: CabinStyle | None = None
    door_style: DoorStyle | None = None
    drive_style: DriveStyle | None = None
    guide_style: GuideStyle | None = None
    counterweight_style: CounterweightStyle | None = None
    bank_style: BankStyle | None = None
    landing_style: LandingStyle | None = None
    floor_count: int = 3
    cabin_width_scale: float = 1.0
    cabin_height_scale: float = 1.0
    floor_spacing_scale: float = 1.0
    material_style: MaterialStyle = "brushed_steel"
    name: str = "elevator"


@dataclass(frozen=True)
class ResolvedElevatorConfig:
    shaft_style: ShaftStyle
    cabin_style: CabinStyle
    door_style: DoorStyle
    drive_style: DriveStyle
    guide_style: GuideStyle
    counterweight_style: CounterweightStyle
    bank_style: BankStyle
    landing_style: LandingStyle
    material_style: MaterialStyle
    floor_count: int
    car_count: int
    car_offsets: tuple[float, ...]
    cabin_width: float
    cabin_depth: float
    cabin_height: float
    shaft_width: float
    shaft_depth: float
    shaft_height: float
    floor_spacing: float
    car_base_z: float
    travel: float
    rail_x: float
    counterweight_x: float
    name: str


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _choice(value: str | None, allowed: tuple[str, ...], fallback: str, field: str) -> str:
    if value is None:
        return fallback
    if value not in allowed:
        raise ValueError(f"Unsupported {field}: {value}")
    return value


def config_from_seed(seed: int) -> ElevatorConfig:
    rng = random.Random(seed)
    return ElevatorConfig(
        shaft_style=rng.choice(SHAFT_STYLES),
        cabin_style=rng.choice(CABIN_STYLES),
        door_style=rng.choice(DOOR_STYLES),
        drive_style=rng.choice(DRIVE_STYLES),
        guide_style=rng.choice(GUIDE_STYLES),
        counterweight_style=rng.choice(COUNTERWEIGHT_STYLES),
        bank_style=rng.choice(BANK_STYLES),
        landing_style=rng.choice(LANDING_STYLES),
        floor_count=rng.choice((2, 3, 4, 5, 6)),
        cabin_width_scale=round(rng.uniform(0.88, 1.16), 3),
        cabin_height_scale=round(rng.uniform(0.88, 1.14), 3),
        floor_spacing_scale=round(rng.uniform(0.92, 1.12), 3),
        material_style=rng.choice(MATERIAL_STYLES),
        name=f"seeded_elevator_{seed}",
    )


def resolve_config(config: ElevatorConfig) -> ResolvedElevatorConfig:
    shaft = _choice(config.shaft_style, SHAFT_STYLES, "open_steel_hoistway", "shaft_style")
    cabin = _choice(config.cabin_style, CABIN_STYLES, "box_cab", "cabin_style")
    door = _choice(config.door_style, DOOR_STYLES, "center_split_doors", "door_style")
    drive = _choice(config.drive_style, DRIVE_STYLES, "traction_machine_room", "drive_style")
    guide = _choice(config.guide_style, GUIDE_STYLES, "twin_t_rails", "guide_style")
    counterweight = _choice(
        config.counterweight_style,
        COUNTERWEIGHT_STYLES,
        "none",
        "counterweight_style",
    )
    bank = _choice(config.bank_style, BANK_STYLES, "single_car", "bank_style")
    landing = _choice(config.landing_style, LANDING_STYLES, "plain_landings", "landing_style")
    material = _choice(config.material_style, MATERIAL_STYLES, "brushed_steel", "material_style")
    if drive == "hydraulic_piston":
        counterweight = "none"
    floor_count = max(2, min(6, int(config.floor_count)))
    car_count = 2 if bank == "dual_car_bank" else 1
    cabin_width = 0.88 * _clamp(config.cabin_width_scale, 0.76, 1.26)
    cabin_height = 1.12 * _clamp(config.cabin_height_scale, 0.78, 1.24)
    cabin_depth = 0.72 if cabin != "service_freight_cab" else 0.82
    floor_spacing = max(cabin_height + 0.28, 1.36 * _clamp(config.floor_spacing_scale, 0.84, 1.20))
    car_base_z = 0.120
    travel = floor_spacing * (floor_count - 1)
    bank_gap = 0.30
    bank_width = car_count * cabin_width + (car_count - 1) * bank_gap
    shaft_width = bank_width + (1.12 if counterweight == "rear_counterweight" else 0.46)
    shaft_depth = cabin_depth + 0.44
    shaft_height = car_base_z + travel + cabin_height + 0.54
    rail_x = cabin_width * 0.5 + 0.105
    car_offsets = (
        (-(cabin_width + bank_gap) * 0.5, (cabin_width + bank_gap) * 0.5)
        if car_count == 2
        else (0.0,)
    )
    counterweight_x = bank_width * 0.5 + 0.335
    return ResolvedElevatorConfig(
        shaft_style=shaft,
        cabin_style=cabin,
        door_style=door,
        drive_style=drive,
        guide_style=guide,
        counterweight_style=counterweight,
        bank_style=bank,
        landing_style=landing,
        material_style=material,
        floor_count=floor_count,
        car_count=car_count,
        car_offsets=car_offsets,
        cabin_width=cabin_width,
        cabin_depth=cabin_depth,
        cabin_height=cabin_height,
        shaft_width=shaft_width,
        shaft_depth=shaft_depth,
        shaft_height=shaft_height,
        floor_spacing=floor_spacing,
        car_base_z=car_base_z,
        travel=travel,
        rail_x=rail_x,
        counterweight_x=counterweight_x,
        name=config.name or "elevator",
    )


def with_overrides(config: ElevatorConfig, **kwargs: object) -> ElevatorConfig:
    return replace(config, **kwargs)


def slot_choices_for_config(
    config: ElevatorConfig | ResolvedElevatorConfig,
) -> tuple[tuple[str, str], ...]:
    r = config if isinstance(config, ResolvedElevatorConfig) else resolve_config(config)
    return (
        ("shaft", r.shaft_style),
        ("cabin", r.cabin_style),
        ("door_system", r.door_style),
        ("drive", r.drive_style),
        ("guide", r.guide_style),
        ("counterweight", r.counterweight_style),
        ("bank_multiplicity", r.bank_style),
        ("landings", f"{r.floor_count}_floor_{r.landing_style}"),
        ("material_style", r.material_style),
    )


def slot_choices_for_seed(seed: int) -> tuple[tuple[str, str], ...]:
    return slot_choices_for_config(config_from_seed(seed))


def _mat(model: ArticulatedObject, r: ResolvedElevatorConfig, key: str):
    return model.material(f"elevator_{key}", rgba=PALETTES[r.material_style][key])


def _box(part, size, xyz, material, name, rpy=(0.0, 0.0, 0.0)) -> None:
    part.visual(Box(size), origin=Origin(xyz=xyz, rpy=rpy), material=material, name=name)


def _cyl(part, radius, length, xyz, material, name, rpy=(0.0, 0.0, 0.0)) -> None:
    part.visual(
        Cylinder(radius=radius, length=length),
        origin=Origin(xyz=xyz, rpy=rpy),
        material=material,
        name=name,
    )


def _car_label(index: int, r: ResolvedElevatorConfig) -> str:
    if r.car_count == 1:
        return "main"
    return "left" if index == 0 else "right"


def _build_fixed_shaft(
    model: ArticulatedObject,
    r: ResolvedElevatorConfig,
    mats: dict[str, object],
):
    shaft = model.part("fixed_elevator_shaft")
    W, D, H = r.shaft_width, r.shaft_depth, r.shaft_height
    back_y = D * 0.5 - 0.040
    front_y = -D * 0.5 + 0.040
    _box(
        shaft, (W + 0.22, D + 0.18, 0.060), (0.0, 0.0, 0.030), mats["shaft"], "pit_foundation_slab"
    )
    for index, xoff in enumerate(r.car_offsets):
        label = _car_label(index, r)
        _box(
            shaft,
            (r.cabin_width + 0.10, r.cabin_depth + 0.08, 0.060),
            (xoff, 0.0, r.car_base_z - 0.030),
            mats["dark"],
            f"{label}_car_buffer_pad",
        )
    _box(shaft, (W + 0.08, 0.060, H), (0.0, back_y, H * 0.5), mats["shaft"], "rear_shaft_wall")
    if r.shaft_style == "concrete_core":
        for x, label in ((-W * 0.5, "left"), (W * 0.5, "right")):
            _box(
                shaft,
                (0.105, D, H),
                (x, 0.0, H * 0.5),
                mats["shaft"],
                f"{label}_concrete_side_wall",
            )
        _box(
            shaft,
            (W + 0.10, 0.085, 0.150),
            (0.0, front_y, H - 0.075),
            mats["shaft"],
            "front_lintel_band",
        )
    else:
        for x, label in ((-W * 0.5, "left"), (W * 0.5, "right")):
            _box(
                shaft,
                (0.075, 0.080, H),
                (x, back_y, H * 0.5),
                mats["rail"],
                f"{label}_rear_upright",
            )
            _box(
                shaft,
                (0.075, 0.080, H),
                (x, front_y, H * 0.5),
                mats["rail"],
                f"{label}_front_upright",
            )
        for i in range(r.floor_count + 1):
            z = r.car_base_z + min(i, r.floor_count - 1) * r.floor_spacing
            if i == r.floor_count:
                z = H - 0.120
            _box(
                shaft,
                (W + 0.08, 0.055, 0.055),
                (0.0, back_y, z),
                mats["rail"],
                f"rear_crossbeam_{i}",
            )
            _box(
                shaft,
                (W + 0.08, 0.055, 0.055),
                (0.0, front_y, z),
                mats["rail"],
                f"front_crossbeam_{i}",
            )
        if r.shaft_style == "glass_observation_tower":
            for side, x in (("left", -W * 0.5 + 0.020), ("right", W * 0.5 - 0.020)):
                _box(
                    shaft,
                    (0.020, D * 0.94, H * 0.86),
                    (x, 0.0, H * 0.50),
                    mats["glass"],
                    f"{side}_glass_wall_panel",
                )
    _build_guide_rails(shaft, r, mats)
    _box(
        shaft,
        (r.shaft_width + 0.02, 0.050, 0.050),
        (0.0, 0.030, 0.085),
        mats["rail"],
        "lower_guide_rail_tie",
    )
    _box(
        shaft,
        (r.shaft_width + 0.02, 0.050, 0.055),
        (0.0, 0.030, r.shaft_height - 0.135),
        mats["rail"],
        "upper_guide_rail_tie",
    )
    _build_landings(shaft, r, mats, front_y)
    _build_drive(shaft, r, mats)
    if r.counterweight_style == "rear_counterweight":
        _build_counterweight_guides(shaft, r, mats)
    return shaft


def _build_guide_rails(shaft, r: ResolvedElevatorConfig, mats: dict[str, object]) -> None:
    for index, xoff in enumerate(r.car_offsets):
        car_label = _car_label(index, r)
        for side, label in ((-1, "left"), (1, "right")):
            x = xoff + side * r.rail_x
            rail_label = f"{car_label}_{label}"
            if r.guide_style == "boxed_guide_rails":
                _box(
                    shaft,
                    (0.065, 0.062, r.shaft_height - 0.170),
                    (x, 0.045, r.shaft_height * 0.5),
                    mats["rail"],
                    f"{rail_label}_boxed_guide_rail",
                )
                _box(
                    shaft,
                    (0.030, 0.020, r.shaft_height - 0.200),
                    (x - side * 0.030, 0.010, r.shaft_height * 0.5),
                    mats["dark"],
                    f"{rail_label}_rail_slot_shadow",
                )
            else:
                _box(
                    shaft,
                    (0.032, 0.050, r.shaft_height - 0.160),
                    (x, 0.030, r.shaft_height * 0.5),
                    mats["rail"],
                    f"{rail_label}_main_t_rail_web",
                )
                _box(
                    shaft,
                    (0.085, 0.050, r.shaft_height - 0.160),
                    (x, 0.000, r.shaft_height * 0.5),
                    mats["rail"],
                    f"{rail_label}_main_t_rail_flange",
                )
                if r.guide_style == "roller_guide_clusters":
                    for i in range(r.floor_count):
                        z = r.car_base_z + i * r.floor_spacing + 0.18
                        _cyl(
                            shaft,
                            0.020,
                            0.040,
                            (x, -0.025, z),
                            mats["accent"],
                            f"{rail_label}_rail_check_roller_{i}",
                            (1.5708, 0.0, 0.0),
                        )


def _build_landings(
    shaft, r: ResolvedElevatorConfig, mats: dict[str, object], front_y: float
) -> None:
    door_w = r.cabin_width * 0.72
    for floor in range(r.floor_count):
        z0 = r.car_base_z + floor * r.floor_spacing
        _box(
            shaft,
            (r.shaft_width + 0.04, 0.080, 0.070),
            (0.0, front_y, z0 + 0.035),
            mats["shaft"],
            f"landing_{floor}_threshold",
        )
        for index, xoff in enumerate(r.car_offsets):
            bay = _car_label(index, r)
            _box(
                shaft,
                (door_w + 0.26, 0.070, 0.060),
                (xoff, front_y, z0 + r.cabin_height + 0.030),
                mats["shaft"],
                f"landing_{floor}_{bay}_header",
            )
            for side, label in ((-1, "left"), (1, "right")):
                _box(
                    shaft,
                    (0.065, 0.070, r.cabin_height),
                    (xoff + side * (door_w * 0.5 + 0.055), front_y, z0 + r.cabin_height * 0.5),
                    mats["shaft"],
                    f"landing_{floor}_{bay}_{label}_jamb",
                )
            if r.door_style == "center_split_doors":
                _box(
                    shaft,
                    (door_w * 0.5, 0.026, r.cabin_height * 0.78),
                    (xoff - door_w * 0.25, front_y - 0.030, z0 + r.cabin_height * 0.47),
                    mats["door"],
                    f"landing_{floor}_{bay}_left_center_door",
                )
                _box(
                    shaft,
                    (door_w * 0.5, 0.026, r.cabin_height * 0.78),
                    (xoff + door_w * 0.25, front_y - 0.030, z0 + r.cabin_height * 0.47),
                    mats["door"],
                    f"landing_{floor}_{bay}_right_center_door",
                )
            elif r.door_style == "telescopic_side_doors":
                for idx, x in enumerate((-0.28, -0.08, 0.12)):
                    _box(
                        shaft,
                        (door_w * 0.32, 0.026, r.cabin_height * 0.78),
                        (xoff + door_w * x, front_y - 0.030, z0 + r.cabin_height * 0.47),
                        mats["door"],
                        f"landing_{floor}_{bay}_telescopic_leaf_{idx}",
                    )
            else:
                for idx, x in enumerate((-0.33, -0.16, 0.0, 0.16, 0.33)):
                    _box(
                        shaft,
                        (0.030, 0.026, r.cabin_height * 0.76),
                        (xoff + door_w * x, front_y - 0.030, z0 + r.cabin_height * 0.47),
                        mats["door"],
                        f"landing_{floor}_{bay}_scissor_bar_{idx}",
                        rpy=(0.0, 0.0, 0.20 if idx % 2 == 0 else -0.20),
                    )
            if r.landing_style == "numbered_call_panels":
                panel_x = xoff + door_w * 0.60
                _box(
                    shaft,
                    (0.060, 0.020, 0.180),
                    (panel_x, front_y - 0.045, z0 + r.cabin_height * 0.60),
                    mats["dark"],
                    f"landing_{floor}_{bay}_call_panel",
                )
                _cyl(
                    shaft,
                    0.012,
                    0.008,
                    (panel_x, front_y - 0.058, z0 + r.cabin_height * 0.62),
                    mats["accent"],
                    f"landing_{floor}_{bay}_call_button",
                    (1.5708, 0.0, 0.0),
                )
            elif r.landing_style == "industrial_thresholds":
                _box(
                    shaft,
                    (door_w + 0.18, 0.030, 0.035),
                    (xoff, front_y - 0.035, z0 + 0.092),
                    mats["accent"],
                    f"landing_{floor}_{bay}_hazard_threshold",
                )
            _box(
                shaft,
                (door_w + 0.13, 0.030, 0.035),
                (xoff, front_y - 0.030, z0 + 0.135),
                mats["rail"],
                f"landing_{floor}_{bay}_door_bottom_track",
            )
            _box(
                shaft,
                (door_w + 0.13, 0.030, 0.035),
                (xoff, front_y - 0.030, z0 + r.cabin_height * 0.86),
                mats["rail"],
                f"landing_{floor}_{bay}_door_top_track",
            )


def _build_drive(shaft, r: ResolvedElevatorConfig, mats: dict[str, object]) -> None:
    if r.drive_style == "traction_machine_room":
        machine_z = r.shaft_height - 0.035
        _box(
            shaft,
            (r.shaft_width * 0.82, r.shaft_depth * 0.70, 0.180),
            (0.0, 0.070, machine_z),
            mats["shaft"],
            "machine_room_box",
        )
        _cyl(
            shaft,
            0.105,
            0.090,
            (-r.cabin_width * 0.18, -0.060, machine_z + 0.040),
            mats["dark"],
            "traction_drive_sheave",
            (1.5708, 0.0, 0.0),
        )
        _box(
            shaft,
            (0.190, 0.100, 0.090),
            (r.cabin_width * 0.18, -0.060, machine_z + 0.035),
            mats["dark"],
            "traction_motor",
        )
    elif r.drive_style == "machine_room_less_sheave":
        sheave_width = max(r.cabin_width * 0.80, r.shaft_width * 0.66)
        _cyl(
            shaft,
            0.075,
            sheave_width,
            (0.0, 0.010, r.shaft_height - 0.105),
            mats["dark"],
            "overhead_mrl_sheave",
            (0.0, 1.5708, 0.0),
        )
        _box(
            shaft,
            (sheave_width + 0.10, 0.040, 0.060),
            (0.0, 0.010, r.shaft_height - 0.175),
            mats["rail"],
            "mrl_sheave_beam",
        )
        _box(
            shaft,
            (sheave_width + 0.10, r.shaft_depth * 0.42, 0.042),
            (0.0, r.shaft_depth * 0.24, r.shaft_height - 0.175),
            mats["rail"],
            "mrl_sheave_beam_rear_bracket",
        )
    else:
        hydraulic_y = r.cabin_depth * 0.5 + 0.100
        for index, xoff in enumerate(r.car_offsets):
            label = _car_label(index, r)
            _cyl(
                shaft,
                0.060,
                r.car_base_z + r.travel + 0.080,
                (xoff, hydraulic_y, (r.car_base_z + r.travel + 0.080) * 0.5),
                mats["dark"],
                f"{label}_hydraulic_lift_piston",
            )
            _cyl(
                shaft,
                0.075,
                r.travel + 0.180,
                (xoff, hydraulic_y, (r.travel + 0.180) * 0.5),
                mats["rail"],
                f"{label}_hydraulic_outer_cylinder",
            )
        _box(
            shaft,
            (0.260, 0.120, 0.090),
            (r.shaft_width * 0.34, hydraulic_y, 0.095),
            mats["dark"],
            "hydraulic_pump_unit",
        )
    if r.drive_style != "hydraulic_piston":
        for index, xoff in enumerate(r.car_offsets):
            car_label = _car_label(index, r)
            for x, label in ((xoff - r.rail_x, "left"), (xoff + r.rail_x, "right")):
                _box(
                    shaft,
                    (0.012, 0.012, r.shaft_height - r.car_base_z + 0.060),
                    (x, 0.105, r.shaft_height * 0.5 + 0.010),
                    mats["dark"],
                    f"{car_label}_{label}_hoist_rope_run",
                )


def _build_counterweight_guides(shaft, r: ResolvedElevatorConfig, mats: dict[str, object]) -> None:
    guide_height = r.shaft_height - 0.260
    x = r.counterweight_x
    for side, label in ((-1, "inner"), (1, "outer")):
        _box(
            shaft,
            (0.030, 0.040, guide_height),
            (x + side * 0.075, 0.315, guide_height * 0.5 + 0.090),
            mats["rail"],
            f"counterweight_{label}_guide",
        )
    _box(
        shaft,
        (0.230, 0.040, guide_height),
        (x, 0.315, guide_height * 0.5 + 0.090),
        mats["dark"],
        "counterweight_backing_rail",
    )
    _box(
        shaft,
        (0.210, 0.270, 0.055),
        (x, 0.425, r.shaft_height - 0.115),
        mats["rail"],
        "counterweight_top_bridge",
    )
    _box(
        shaft, (0.210, 0.270, 0.050), (x, 0.425, 0.115), mats["rail"], "counterweight_bottom_bridge"
    )


def _build_cabin(
    model: ArticulatedObject,
    r: ResolvedElevatorConfig,
    mats: dict[str, object],
    *,
    part_name: str = "elevator_car",
):
    cab = model.part(part_name)
    W, D, H = r.cabin_width, r.cabin_depth, r.cabin_height
    front_y = -D * 0.5 - 0.014
    _box(cab, (W, D, 0.075), (0.0, 0.0, 0.0375), mats["cab"], "car_floor")
    _box(cab, (W, D, 0.060), (0.0, 0.0, H - 0.030), mats["cab"], "car_roof")
    for side, label in ((-1, "left"), (1, "right")):
        _box(
            cab,
            (0.060, D, H),
            (side * (W * 0.5 - 0.030), 0.0, H * 0.5),
            mats["cab"],
            f"{label}_car_side_frame",
        )
    _box(cab, (W, 0.055, H), (0.0, D * 0.5 - 0.0275, H * 0.5), mats["cab"], "rear_car_wall")
    if r.cabin_style == "glass_cab":
        for side, label in ((-1, "left"), (1, "right")):
            _box(
                cab,
                (0.034, D * 0.70, H * 0.72),
                (side * (W * 0.5 - 0.072), 0.0, H * 0.50),
                mats["glass"],
                f"{label}_glass_cab_side",
            )
        _box(
            cab,
            (W * 0.52, 0.020, H * 0.70),
            (0.0, -D * 0.5 + 0.010, H * 0.50),
            mats["glass"],
            "front_glass_transom",
        )
    elif r.cabin_style == "service_freight_cab":
        for x in (-0.32, -0.16, 0.0, 0.16, 0.32):
            _box(
                cab,
                (0.030, 0.030, H * 0.78),
                (x * W, D * 0.5 - 0.060, H * 0.48),
                mats["rail"],
                f"rear_protective_bar_{x:.2f}",
            )
        _box(
            cab,
            (W * 0.82, 0.050, 0.060),
            (0.0, D * 0.5 - 0.060, H * 0.74),
            mats["rail"],
            "rear_load_guard",
        )
    else:
        _box(
            cab,
            (W * 0.72, 0.022, H * 0.20),
            (0.0, -D * 0.5 + 0.012, H * 0.82),
            mats["accent"],
            "car_header_indicator",
        )
    _build_cabin_doors(cab, r, mats, front_y)
    for side, label in ((-1, "left"), (1, "right")):
        _box(
            cab,
            (0.060, 0.080, 0.150),
            (side * (W * 0.5 + 0.030), 0.040, H * 0.30),
            mats["dark"],
            f"{label}_lower_guide_shoe",
        )
        _box(
            cab,
            (0.060, 0.080, 0.150),
            (side * (W * 0.5 + 0.030), 0.040, H * 0.78),
            mats["dark"],
            f"{label}_upper_guide_shoe",
        )
    return cab


def _build_cabin_doors(
    cab, r: ResolvedElevatorConfig, mats: dict[str, object], front_y: float
) -> None:
    W, H = r.cabin_width, r.cabin_height
    door_w = W * 0.74
    _box(
        cab,
        (door_w + 0.12, 0.035, 0.052),
        (0.0, front_y, 0.090),
        mats["rail"],
        "car_door_bottom_track",
    )
    _box(
        cab,
        (door_w + 0.12, 0.035, 0.052),
        (0.0, front_y, H * 0.86),
        mats["rail"],
        "car_door_top_track",
    )
    for side, label in ((-1, "left"), (1, "right")):
        _box(
            cab,
            (0.045, 0.040, H),
            (side * (door_w * 0.5 + 0.062), front_y, H * 0.5),
            mats["rail"],
            f"{label}_front_door_jamb",
        )
    if r.door_style == "center_split_doors":
        _box(
            cab,
            (door_w * 0.50, 0.032, H * 0.76),
            (-door_w * 0.25, front_y - 0.018, H * 0.48),
            mats["door"],
            "left_car_center_door",
        )
        _box(
            cab,
            (door_w * 0.50, 0.032, H * 0.76),
            (door_w * 0.25, front_y - 0.018, H * 0.48),
            mats["door"],
            "right_car_center_door",
        )
        _box(
            cab,
            (0.018, 0.040, H * 0.74),
            (0.0, front_y - 0.024, H * 0.48),
            mats["dark"],
            "center_door_meeting_strip",
        )
    elif r.door_style == "telescopic_side_doors":
        for idx, x in enumerate((-0.27, -0.06, 0.15)):
            _box(
                cab,
                (door_w * 0.31, 0.032, H * 0.76),
                (door_w * x, front_y - 0.018, H * 0.48),
                mats["door"],
                f"car_telescopic_door_leaf_{idx}",
            )
    else:
        for idx, x in enumerate((-0.34, -0.17, 0.0, 0.17, 0.34)):
            _box(
                cab,
                (0.030, 0.034, H * 0.72),
                (door_w * x, front_y - 0.018, H * 0.48),
                mats["door"],
                f"car_scissor_gate_bar_{idx}",
                rpy=(0.0, 0.0, 0.22 if idx % 2 == 0 else -0.22),
            )
        _box(
            cab,
            (door_w * 0.82, 0.030, 0.035),
            (0.0, front_y - 0.020, H * 0.58),
            mats["door"],
            "scissor_gate_crossbar",
        )


def _build_counterweight(
    model: ArticulatedObject,
    r: ResolvedElevatorConfig,
    mats: dict[str, object],
):
    cw = model.part("elevator_counterweight")
    _box(cw, (0.185, 0.120, 0.520), (0.0, 0.060, 0.0), mats["dark"], "counterweight_stack")
    _box(cw, (0.150, 0.028, 0.420), (0.0, 0.126, 0.0), mats["accent"], "counterweight_front_stripe")
    _box(cw, (0.220, 0.130, 0.050), (0.0, 0.065, 0.285), mats["rail"], "counterweight_top_cap")
    _box(cw, (0.220, 0.130, 0.050), (0.0, 0.065, -0.285), mats["rail"], "counterweight_bottom_cap")
    return cw


def build_elevator(
    config: ElevatorConfig | None = None,
    *,
    assets: AssetContext | None = None,
) -> ArticulatedObject:
    cfg = config or ElevatorConfig()
    r = resolve_config(cfg)
    model = ArticulatedObject(name=r.name, assets=assets)
    mats = {
        key: _mat(model, r, key)
        for key in ("shaft", "cab", "rail", "door", "glass", "accent", "dark")
    }
    shaft = _build_fixed_shaft(model, r, mats)
    for index, xoff in enumerate(r.car_offsets):
        label = _car_label(index, r)
        part_name = "elevator_car" if r.car_count == 1 else f"{label}_elevator_car"
        joint_name = "car_vertical_travel" if r.car_count == 1 else f"{label}_car_vertical_travel"
        cabin = _build_cabin(model, r, mats, part_name=part_name)
        model.articulation(
            joint_name,
            ArticulationType.PRISMATIC,
            parent=shaft,
            child=cabin,
            origin=Origin(xyz=(xoff, 0.0, r.car_base_z)),
            axis=(0.0, 0.0, 1.0),
            motion_limits=MotionLimits(effort=120.0, velocity=1.2, lower=0.0, upper=r.travel),
        )
    if r.counterweight_style == "rear_counterweight":
        cw = _build_counterweight(model, r, mats)
        model.articulation(
            "counterweight_vertical_travel",
            ArticulationType.PRISMATIC,
            parent=shaft,
            child=cw,
            origin=Origin(xyz=(r.counterweight_x, 0.335, r.car_base_z + r.travel + 0.060)),
            axis=(0.0, 0.0, -1.0),
            motion_limits=MotionLimits(effort=70.0, velocity=1.2, lower=0.0, upper=r.travel * 0.86),
        )
    model.meta["slot_choices"] = slot_choices_for_config(r)
    return model


def build_seeded_elevator(seed: int, *, assets: AssetContext | None = None) -> ArticulatedObject:
    return build_elevator(config_from_seed(seed), assets=assets)


def run_elevator_tests(object_model: ArticulatedObject, config: ElevatorConfig) -> TestReport:
    r = resolve_config(config)
    ctx = TestContext(object_model)
    ctx.check_model_valid()
    ctx.check_mesh_assets_ready()
    ctx.fail_if_isolated_parts()
    ctx.fail_if_parts_overlap_in_current_pose()
    ctx.fail_if_articulation_origin_far_from_geometry(tol=0.020)
    ctx.fail_if_joint_mating_has_gap()

    part_names = {part.name for part in object_model.parts}
    ctx.check(
        "shaft_present", "fixed_elevator_shaft" in part_names, details=str(sorted(part_names))
    )
    car_parts = [
        name for name in part_names if name == "elevator_car" or name.endswith("_elevator_car")
    ]
    ctx.check(
        "car_count",
        len(car_parts) == r.car_count,
        details=f"expected {r.car_count}, got {sorted(car_parts)}",
    )
    car_joints = [
        joint
        for joint in object_model.joints
        if joint.name == "car_vertical_travel" or joint.name.endswith("_car_vertical_travel")
    ]
    ctx.check(
        "car_joint_count",
        len(car_joints) == r.car_count,
        details=f"expected {r.car_count}, got {len(car_joints)}",
    )
    for joint in car_joints:
        ctx.check(
            f"{joint.name}_prismatic",
            joint.articulation_type == ArticulationType.PRISMATIC,
            details=str(joint.articulation_type),
        )
        ctx.check(
            f"{joint.name}_axis", tuple(joint.axis) == (0.0, 0.0, 1.0), details=str(joint.axis)
        )
        ctx.check(
            f"{joint.name}_travel",
            joint.motion_limits.upper >= r.travel * 0.98,
            details=str(joint.motion_limits),
        )
    counter_joints = [
        joint for joint in object_model.joints if joint.name == "counterweight_vertical_travel"
    ]
    expected_counter = 1 if r.counterweight_style == "rear_counterweight" else 0
    ctx.check(
        "counterweight_joint_count",
        len(counter_joints) == expected_counter,
        details=f"expected {expected_counter}, got {len(counter_joints)}",
    )
    for joint in counter_joints:
        ctx.check(
            "counterweight_axis", tuple(joint.axis) == (0.0, 0.0, -1.0), details=str(joint.axis)
        )
    return ctx.report()


__all__ = [
    "ElevatorConfig",
    "ResolvedElevatorConfig",
    "build_elevator",
    "build_seeded_elevator",
    "config_from_seed",
    "resolve_config",
    "run_elevator_tests",
    "slot_choices_for_config",
    "slot_choices_for_seed",
    "with_overrides",
]
