"""Procedural template for ``studio_spotlight_on_yoke``.

The category currently has no reviewed spec file under
``articraft_template_authoring/specs_modular_v1/``. This implementation follows the
repository's modular template contract using the prompt family found in the
checked-in batch specs:

* a stable floor, desktop, tripod, or rolling stand/base,
* a vertical pan stage at the stand head,
* a U-shaped side yoke with visible bearing plates and friction locks,
* a cylindrical studio spotlight can captured between the yoke arms,
* a horizontal tilt axis through the side trunnions,
* optional non-moving studio-light details such as barn doors, gel frames,
  focus knobs, rain lips, vents, handles, and safety cages.

Core motion spine:

``stand --yoke_pan(Z)--> yoke --can_tilt(X)--> spotlight_can``

The yoke owns the side plates, upper bridge, lower saddle, pan spigot, and
friction knobs. The can owns the lamp body, front lens/bezel, rear cap,
trunnion boss, and all non-moving accessories. Captured pin overlaps are
declared in the author tests because they are the real mechanical interface.
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
    Sphere,
    TestContext,
    TestReport,
)

__modular__ = True


StandStyle = Literal["round_floor", "tripod", "desktop_plate", "rolling_low_base"]
YokeStyle = Literal["flat_side_plates", "tubular_u_bracket", "heavy_friction_yoke"]
CanStyle = Literal["fresnel_short_can", "par_can", "long_throw_snoot", "vented_cylinder"]
AccessoryStyle = Literal[
    "none",
    "barn_doors",
    "gel_frame",
    "safety_cage",
    "top_handle",
    "weather_hood",
]
MaterialStyle = Literal[
    "matte_black_stage",
    "brushed_silver",
    "cream_studio",
    "safety_yellow",
    "weatherproof_gray",
]


STAND_STYLES: tuple[StandStyle, ...] = (
    "round_floor",
    "tripod",
    "desktop_plate",
    "rolling_low_base",
)
YOKE_STYLES: tuple[YokeStyle, ...] = (
    "flat_side_plates",
    "tubular_u_bracket",
    "heavy_friction_yoke",
)
CAN_STYLES: tuple[CanStyle, ...] = (
    "fresnel_short_can",
    "par_can",
    "long_throw_snoot",
    "vented_cylinder",
)
ACCESSORY_STYLES: tuple[AccessoryStyle, ...] = (
    "none",
    "barn_doors",
    "gel_frame",
    "safety_cage",
    "top_handle",
    "weather_hood",
)
MATERIAL_STYLES: tuple[MaterialStyle, ...] = (
    "matte_black_stage",
    "brushed_silver",
    "cream_studio",
    "safety_yellow",
    "weatherproof_gray",
)


PALETTES: dict[MaterialStyle, dict[str, tuple[float, float, float, float]]] = {
    "matte_black_stage": {
        "base": (0.035, 0.037, 0.040, 1.0),
        "base_dark": (0.010, 0.011, 0.013, 1.0),
        "metal": (0.42, 0.43, 0.45, 1.0),
        "can": (0.025, 0.027, 0.030, 1.0),
        "bezel": (0.10, 0.105, 0.11, 1.0),
        "glass": (0.72, 0.82, 0.90, 0.42),
        "emitter": (1.00, 0.86, 0.48, 0.70),
        "accent": (0.92, 0.67, 0.12, 1.0),
        "rubber": (0.005, 0.005, 0.006, 1.0),
    },
    "brushed_silver": {
        "base": (0.54, 0.56, 0.58, 1.0),
        "base_dark": (0.22, 0.23, 0.24, 1.0),
        "metal": (0.73, 0.75, 0.78, 1.0),
        "can": (0.62, 0.64, 0.66, 1.0),
        "bezel": (0.38, 0.39, 0.40, 1.0),
        "glass": (0.70, 0.84, 0.96, 0.42),
        "emitter": (1.00, 0.88, 0.52, 0.70),
        "accent": (0.12, 0.36, 0.65, 1.0),
        "rubber": (0.04, 0.04, 0.045, 1.0),
    },
    "cream_studio": {
        "base": (0.75, 0.73, 0.66, 1.0),
        "base_dark": (0.38, 0.36, 0.31, 1.0),
        "metal": (0.58, 0.56, 0.50, 1.0),
        "can": (0.82, 0.80, 0.72, 1.0),
        "bezel": (0.30, 0.29, 0.26, 1.0),
        "glass": (0.78, 0.88, 0.96, 0.42),
        "emitter": (1.00, 0.89, 0.54, 0.70),
        "accent": (0.64, 0.20, 0.12, 1.0),
        "rubber": (0.05, 0.045, 0.04, 1.0),
    },
    "safety_yellow": {
        "base": (0.13, 0.13, 0.12, 1.0),
        "base_dark": (0.025, 0.025, 0.025, 1.0),
        "metal": (0.56, 0.58, 0.60, 1.0),
        "can": (0.92, 0.70, 0.10, 1.0),
        "bezel": (0.05, 0.05, 0.055, 1.0),
        "glass": (0.68, 0.82, 0.95, 0.40),
        "emitter": (1.00, 0.88, 0.46, 0.72),
        "accent": (0.08, 0.08, 0.08, 1.0),
        "rubber": (0.012, 0.012, 0.014, 1.0),
    },
    "weatherproof_gray": {
        "base": (0.40, 0.43, 0.44, 1.0),
        "base_dark": (0.15, 0.16, 0.17, 1.0),
        "metal": (0.60, 0.63, 0.63, 1.0),
        "can": (0.33, 0.36, 0.37, 1.0),
        "bezel": (0.17, 0.18, 0.19, 1.0),
        "glass": (0.70, 0.84, 0.92, 0.44),
        "emitter": (1.00, 0.86, 0.44, 0.70),
        "accent": (0.16, 0.42, 0.52, 1.0),
        "rubber": (0.025, 0.026, 0.028, 1.0),
    },
}


X_CYLINDER_RPY = (0.0, math.pi / 2.0, 0.0)
Y_CYLINDER_RPY = (-math.pi / 2.0, 0.0, 0.0)
Z_CYLINDER_RPY = (0.0, 0.0, 0.0)


@dataclass(frozen=True)
class StudioSpotlightOnYokeConfig:
    stand_style: StandStyle | None = None
    yoke_style: YokeStyle | None = None
    can_style: CanStyle | None = None
    accessory_style: AccessoryStyle | None = None
    material_style: MaterialStyle = "matte_black_stage"
    mast_height: float = 0.58
    base_radius: float = 0.145
    can_radius: float = 0.105
    can_length: float = 0.300
    yoke_pan_limit: float = math.pi
    can_tilt_limit: float = math.radians(68.0)
    name: str = "reference_studio_spotlight_on_yoke"


@dataclass(frozen=True)
class ResolvedStudioSpotlightOnYokeConfig:
    stand_style: StandStyle
    yoke_style: YokeStyle
    can_style: CanStyle
    accessory_style: AccessoryStyle
    material_style: MaterialStyle
    mast_height: float
    base_radius: float
    base_height: float
    can_radius: float
    can_length: float
    can_rear_depth: float
    yoke_half_width: float
    yoke_tilt_z: float
    yoke_side_height: float
    yoke_plate_thickness: float
    yoke_pan_limit: float
    can_tilt_limit: float
    name: str


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, float(value)))


def _choice(value: str | None, choices: tuple[str, ...], fallback: str) -> str:
    if value in choices:
        return value
    return fallback


def resolve_config(config: StudioSpotlightOnYokeConfig) -> ResolvedStudioSpotlightOnYokeConfig:
    stand_style = _choice(config.stand_style, STAND_STYLES, "round_floor")
    yoke_style = _choice(config.yoke_style, YOKE_STYLES, "flat_side_plates")
    can_style = _choice(config.can_style, CAN_STYLES, "fresnel_short_can")
    accessory_style = _choice(config.accessory_style, ACCESSORY_STYLES, "barn_doors")
    material_style = _choice(config.material_style, MATERIAL_STYLES, "matte_black_stage")

    base_radius = _clamp(config.base_radius, 0.105, 0.220)
    can_radius = _clamp(config.can_radius, 0.075, 0.135)
    can_length = _clamp(config.can_length, 0.220, 0.420)
    mast_height = _clamp(config.mast_height, 0.230, 0.820)
    if stand_style == "desktop_plate":
        mast_height = _clamp(mast_height, 0.230, 0.420)
        base_radius = _clamp(base_radius, 0.110, 0.170)
    elif stand_style == "rolling_low_base":
        mast_height = _clamp(mast_height, 0.360, 0.620)
        base_radius = _clamp(base_radius, 0.150, 0.230)
    elif stand_style == "tripod":
        mast_height = _clamp(mast_height, 0.500, 0.840)
        base_radius = _clamp(base_radius, 0.135, 0.190)

    if can_style == "par_can":
        can_length = max(can_length, can_radius * 2.75)
        can_rear_depth = 0.050
    elif can_style == "long_throw_snoot":
        can_length = max(can_length, can_radius * 3.55)
        can_rear_depth = 0.055
    elif can_style == "vented_cylinder":
        can_length = max(can_length, can_radius * 3.05)
        can_rear_depth = 0.070
    else:
        can_length = max(can_length, can_radius * 2.45)
        can_rear_depth = 0.060

    yoke_half_width = can_radius + 0.048
    yoke_tilt_z = 0.205 + can_radius * 0.24
    yoke_side_height = can_radius * 2.65 + 0.055
    yoke_plate_thickness = 0.034 if yoke_style != "tubular_u_bracket" else 0.026
    if yoke_style == "heavy_friction_yoke":
        yoke_side_height += 0.035
        yoke_plate_thickness = 0.044

    return ResolvedStudioSpotlightOnYokeConfig(
        stand_style=stand_style,  # type: ignore[arg-type]
        yoke_style=yoke_style,  # type: ignore[arg-type]
        can_style=can_style,  # type: ignore[arg-type]
        accessory_style=accessory_style,  # type: ignore[arg-type]
        material_style=material_style,  # type: ignore[arg-type]
        mast_height=mast_height,
        base_radius=base_radius,
        base_height=0.030 if stand_style != "rolling_low_base" else 0.040,
        can_radius=can_radius,
        can_length=can_length,
        can_rear_depth=can_rear_depth,
        yoke_half_width=yoke_half_width,
        yoke_tilt_z=yoke_tilt_z,
        yoke_side_height=yoke_side_height,
        yoke_plate_thickness=yoke_plate_thickness,
        yoke_pan_limit=_clamp(config.yoke_pan_limit, math.radians(120), math.tau),
        can_tilt_limit=_clamp(config.can_tilt_limit, math.radians(40), math.radians(82)),
        name=str(config.name or "studio_spotlight_on_yoke"),
    )


def slot_choices_for_config(config: StudioSpotlightOnYokeConfig) -> list[tuple[str, str]]:
    r = resolve_config(config)
    return [
        ("stand_style", r.stand_style),
        ("yoke_style", r.yoke_style),
        ("can_style", r.can_style),
        ("accessory_style", r.accessory_style),
        ("material_style", r.material_style),
    ]


def slot_choices_for_seed(seed: int) -> list[tuple[str, str]]:
    return slot_choices_for_config(config_from_seed(seed))


def config_from_seed(seed: int) -> StudioSpotlightOnYokeConfig:
    if seed == 0:
        return StudioSpotlightOnYokeConfig(
            stand_style="round_floor",
            yoke_style="flat_side_plates",
            can_style="fresnel_short_can",
            accessory_style="barn_doors",
            material_style="matte_black_stage",
            mast_height=0.58,
            base_radius=0.145,
            can_radius=0.105,
            can_length=0.300,
            name="seeded_studio_spotlight_on_yoke_0",
        )
    rng = random.Random(seed)
    stand_style = rng.choice(STAND_STYLES)
    yoke_style = rng.choice(YOKE_STYLES)
    can_style = rng.choice(CAN_STYLES)
    accessory_style = rng.choice(ACCESSORY_STYLES)
    material_style = rng.choice(MATERIAL_STYLES)
    mast_height = rng.uniform(0.36, 0.74)
    if stand_style == "desktop_plate":
        mast_height = rng.uniform(0.24, 0.38)
    elif stand_style == "tripod":
        mast_height = rng.uniform(0.56, 0.80)
    elif stand_style == "rolling_low_base":
        mast_height = rng.uniform(0.38, 0.58)
    return StudioSpotlightOnYokeConfig(
        stand_style=stand_style,
        yoke_style=yoke_style,
        can_style=can_style,
        accessory_style=accessory_style,
        material_style=material_style,
        mast_height=mast_height,
        base_radius=rng.uniform(0.125, 0.205),
        can_radius=rng.uniform(0.085, 0.125),
        can_length=rng.uniform(0.250, 0.385),
        yoke_pan_limit=rng.uniform(math.radians(150), math.tau),
        can_tilt_limit=rng.uniform(math.radians(55), math.radians(76)),
        name=f"seeded_studio_spotlight_on_yoke_{seed}",
    )


def _register_materials(model: ArticulatedObject, material_style: MaterialStyle) -> dict[str, str]:
    palette = PALETTES[material_style]
    return {name: model.material(name, rgba=rgba) for name, rgba in palette.items()}


def _box(
    part: Part,
    name: str,
    size: tuple[float, float, float],
    xyz: tuple[float, float, float],
    material: str,
    rpy: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> None:
    part.visual(Box(size), origin=Origin(xyz=xyz, rpy=rpy), material=material, name=name)


def _cyl(
    part: Part,
    name: str,
    radius: float,
    length: float,
    xyz: tuple[float, float, float],
    material: str,
    rpy: tuple[float, float, float] = Z_CYLINDER_RPY,
) -> None:
    part.visual(
        Cylinder(radius=radius, length=length),
        origin=Origin(xyz=xyz, rpy=rpy),
        material=material,
        name=name,
    )


def _sphere(
    part: Part, name: str, radius: float, xyz: tuple[float, float, float], material: str
) -> None:
    part.visual(Sphere(radius=radius), origin=Origin(xyz=xyz), material=material, name=name)


def _build_round_floor_stand(
    stand: Part, r: ResolvedStudioSpotlightOnYokeConfig, m: dict[str, str]
) -> None:
    _cyl(
        stand,
        "round_weighted_base",
        r.base_radius,
        r.base_height,
        (0.0, 0.0, r.base_height * 0.5),
        m["base"],
    )
    _cyl(stand, "base_rubber_ring", r.base_radius * 0.93, 0.010, (0.0, 0.0, 0.006), m["rubber"])
    _cyl(
        stand,
        "lower_mast",
        0.026,
        r.mast_height * 0.70,
        (0.0, 0.0, r.base_height + r.mast_height * 0.35),
        m["metal"],
    )
    _cyl(
        stand,
        "upper_mast",
        0.019,
        r.mast_height * 0.42,
        (0.0, 0.0, r.base_height + r.mast_height * 0.79),
        m["metal"],
    )
    _cyl(
        stand,
        "height_lock_collar",
        0.034,
        0.045,
        (0.0, 0.0, r.base_height + r.mast_height * 0.62),
        m["base_dark"],
    )
    _box(
        stand,
        "height_lock_tab",
        (0.052, 0.018, 0.022),
        (0.044, 0.0, r.base_height + r.mast_height * 0.62),
        m["accent"],
    )
    _cyl(
        stand, "stand_top_bearing", 0.046, 0.052, (0.0, 0.0, r.mast_height - 0.006), m["base_dark"]
    )


def _build_desktop_plate_stand(
    stand: Part, r: ResolvedStudioSpotlightOnYokeConfig, m: dict[str, str]
) -> None:
    plate_w = r.base_radius * 2.10
    plate_d = r.base_radius * 1.42
    _box(
        stand,
        "desktop_weighted_plate",
        (plate_w, plate_d, r.base_height),
        (0.0, 0.0, r.base_height * 0.5),
        m["base"],
    )
    _box(
        stand,
        "desktop_front_rubber",
        (plate_w * 0.78, 0.020, 0.012),
        (0.0, plate_d * 0.42, 0.008),
        m["rubber"],
    )
    _box(
        stand,
        "desktop_rear_rubber",
        (plate_w * 0.78, 0.020, 0.012),
        (0.0, -plate_d * 0.42, 0.008),
        m["rubber"],
    )
    _cyl(
        stand, "short_stand_socket", 0.044, 0.060, (0.0, 0.0, r.base_height + 0.026), m["base_dark"]
    )
    _cyl(
        stand,
        "short_mast",
        0.024,
        r.mast_height,
        (0.0, 0.0, r.base_height + r.mast_height * 0.5),
        m["metal"],
    )
    _cyl(
        stand, "stand_top_bearing", 0.046, 0.052, (0.0, 0.0, r.mast_height - 0.006), m["base_dark"]
    )


def _build_tripod_stand(
    stand: Part, r: ResolvedStudioSpotlightOnYokeConfig, m: dict[str, str]
) -> None:
    hub_z = r.base_height + 0.030
    _cyl(stand, "tripod_center_hub", 0.052, 0.058, (0.0, 0.0, hub_z), m["base_dark"])
    leg_len = r.base_radius * 1.95
    for i in range(3):
        angle = i * math.tau / 3.0 + math.radians(18.0)
        cx = math.cos(angle) * leg_len * 0.42
        cy = math.sin(angle) * leg_len * 0.42
        fx = math.cos(angle) * leg_len * 0.86
        fy = math.sin(angle) * leg_len * 0.86
        _box(
            stand,
            f"tripod_leg_{i}",
            (leg_len, 0.030, 0.024),
            (cx, cy, 0.032),
            m["base"],
            rpy=(0.0, 0.0, angle),
        )
        _box(
            stand,
            f"tripod_foot_{i}",
            (0.090, 0.045, 0.018),
            (fx, fy, 0.015),
            m["rubber"],
            rpy=(0.0, 0.0, angle),
        )
    _cyl(
        stand,
        "tripod_lower_mast",
        0.028,
        r.mast_height * 0.74,
        (0.0, 0.0, hub_z + r.mast_height * 0.37),
        m["metal"],
    )
    _cyl(
        stand,
        "tripod_upper_mast",
        0.020,
        r.mast_height * 0.43,
        (0.0, 0.0, hub_z + r.mast_height * 0.78),
        m["metal"],
    )
    _cyl(
        stand,
        "tripod_height_collar",
        0.036,
        0.048,
        (0.0, 0.0, hub_z + r.mast_height * 0.58),
        m["base_dark"],
    )
    _box(
        stand,
        "tripod_collar_knob",
        (0.060, 0.020, 0.024),
        (0.050, 0.0, hub_z + r.mast_height * 0.58),
        m["accent"],
    )
    _cyl(
        stand, "stand_top_bearing", 0.047, 0.054, (0.0, 0.0, r.mast_height - 0.006), m["base_dark"]
    )


def _build_rolling_low_base(
    stand: Part, r: ResolvedStudioSpotlightOnYokeConfig, m: dict[str, str]
) -> None:
    w = r.base_radius * 2.05
    d = r.base_radius * 1.55
    _box(stand, "rolling_weighted_tray", (w, d, r.base_height), (0.0, 0.0, 0.052), m["base"])
    _box(
        stand, "rolling_tray_spine", (w * 0.48, d * 0.78, 0.030), (0.0, 0.0, 0.088), m["base_dark"]
    )
    for i, sx in enumerate((-1, 1)):
        for j, sy in enumerate((-1, 1)):
            x = sx * w * 0.39
            y = sy * d * 0.35
            idx = i * 2 + j
            _box(stand, f"caster_fork_{idx}", (0.032, 0.050, 0.035), (x, y, 0.027), m["base_dark"])
            _cyl(
                stand,
                f"caster_wheel_{idx}",
                0.020,
                0.036,
                (x, y, 0.015),
                m["rubber"],
                rpy=X_CYLINDER_RPY,
            )
    _cyl(stand, "rolling_mast_socket", 0.050, 0.070, (0.0, 0.0, 0.105), m["base_dark"])
    _cyl(
        stand,
        "rolling_short_mast",
        0.027,
        r.mast_height,
        (0.0, 0.0, 0.095 + r.mast_height * 0.5),
        m["metal"],
    )
    _cyl(
        stand,
        "rolling_height_collar",
        0.037,
        0.046,
        (0.0, 0.0, 0.095 + r.mast_height * 0.62),
        m["base_dark"],
    )
    _cyl(
        stand, "stand_top_bearing", 0.048, 0.054, (0.0, 0.0, r.mast_height - 0.006), m["base_dark"]
    )


def _build_stand(
    model: ArticulatedObject, r: ResolvedStudioSpotlightOnYokeConfig, m: dict[str, str]
) -> Part:
    stand = model.part("stand")
    if r.stand_style == "tripod":
        _build_tripod_stand(stand, r, m)
    elif r.stand_style == "desktop_plate":
        _build_desktop_plate_stand(stand, r, m)
    elif r.stand_style == "rolling_low_base":
        _build_rolling_low_base(stand, r, m)
    else:
        _build_round_floor_stand(stand, r, m)
    return stand


def _build_flat_side_plate_yoke(
    yoke: Part, r: ResolvedStudioSpotlightOnYokeConfig, m: dict[str, str]
) -> None:
    hw = r.yoke_half_width
    zc = r.yoke_tilt_z
    side_h = r.yoke_side_height
    th = r.yoke_plate_thickness
    _cyl(yoke, "yaw_spigot", 0.040, 0.085, (0.0, 0.0, 0.010), m["base_dark"])
    _cyl(yoke, "pan_index_collar", 0.055, 0.036, (0.0, 0.0, 0.068), m["metal"])
    _box(yoke, "yoke_neck_block", (0.060, 0.060, 0.046), (0.0, 0.0, 0.078), m["metal"])
    _box(
        yoke,
        "lower_yoke_saddle",
        (hw * 2.0 + th, 0.072, 0.040),
        (0.0, 0.0, zc - side_h * 0.50),
        m["metal"],
    )
    _box(
        yoke,
        "upper_yoke_bridge",
        (hw * 2.0 + th, 0.066, 0.036),
        (0.0, 0.0, zc + side_h * 0.50),
        m["metal"],
    )
    for side, sx in (("left", -1), ("right", 1)):
        x = sx * hw
        _box(yoke, f"{side}_side_plate", (th, 0.080, side_h), (x, 0.0, zc), m["metal"])
        _cyl(
            yoke,
            f"{side}_bearing_cup",
            0.042,
            th + 0.020,
            (x, 0.0, zc),
            m["base_dark"],
            rpy=X_CYLINDER_RPY,
        )
        _cyl(
            yoke,
            f"{side}_friction_knob",
            0.034,
            0.040,
            (sx * (hw + th * 0.72), 0.0, zc),
            m["accent"],
            rpy=X_CYLINDER_RPY,
        )
    _cyl(yoke, "tilt_axis_pin", 0.021, hw * 2.24, (0.0, 0.0, zc), m["metal"], rpy=X_CYLINDER_RPY)


def _build_tubular_u_yoke(
    yoke: Part, r: ResolvedStudioSpotlightOnYokeConfig, m: dict[str, str]
) -> None:
    hw = r.yoke_half_width
    zc = r.yoke_tilt_z
    side_h = r.yoke_side_height
    _cyl(yoke, "yaw_spigot", 0.038, 0.084, (0.0, 0.0, 0.010), m["base_dark"])
    _cyl(yoke, "pan_index_collar", 0.053, 0.034, (0.0, 0.0, 0.068), m["metal"])
    _cyl(yoke, "round_yoke_stem", 0.030, 0.046, (0.0, 0.0, 0.080), m["metal"])
    _cyl(
        yoke,
        "lower_tube_bridge",
        0.020,
        hw * 2.08,
        (0.0, 0.0, zc - side_h * 0.48),
        m["metal"],
        rpy=X_CYLINDER_RPY,
    )
    _cyl(
        yoke,
        "upper_tube_bridge",
        0.022,
        hw * 2.10,
        (0.0, 0.0, zc + side_h * 0.50),
        m["metal"],
        rpy=X_CYLINDER_RPY,
    )
    for side, sx in (("left", -1), ("right", 1)):
        x = sx * hw
        _cyl(yoke, f"{side}_upright_tube", 0.021, side_h, (x, 0.0, zc), m["metal"])
        _cyl(
            yoke,
            f"{side}_bearing_cup",
            0.038,
            0.052,
            (x, 0.0, zc),
            m["base_dark"],
            rpy=X_CYLINDER_RPY,
        )
        _cyl(
            yoke,
            f"{side}_friction_knob",
            0.031,
            0.038,
            (sx * (hw + 0.036), 0.0, zc),
            m["accent"],
            rpy=X_CYLINDER_RPY,
        )
    _cyl(yoke, "tilt_axis_pin", 0.020, hw * 2.22, (0.0, 0.0, zc), m["metal"], rpy=X_CYLINDER_RPY)


def _build_heavy_friction_yoke(
    yoke: Part, r: ResolvedStudioSpotlightOnYokeConfig, m: dict[str, str]
) -> None:
    hw = r.yoke_half_width
    zc = r.yoke_tilt_z
    side_h = r.yoke_side_height
    th = r.yoke_plate_thickness
    _cyl(yoke, "yaw_spigot", 0.043, 0.090, (0.0, 0.0, 0.012), m["base_dark"])
    _cyl(yoke, "pan_index_collar", 0.062, 0.045, (0.0, 0.0, 0.072), m["metal"])
    _box(yoke, "heavy_neck_block", (0.075, 0.078, 0.048), (0.0, 0.0, 0.080), m["metal"])
    _box(
        yoke,
        "heavy_lower_saddle",
        (hw * 2.05 + th, 0.090, 0.052),
        (0.0, 0.0, zc - side_h * 0.50),
        m["metal"],
    )
    _box(
        yoke,
        "heavy_upper_bridge",
        (hw * 2.10 + th, 0.086, 0.044),
        (0.0, 0.0, zc + side_h * 0.50),
        m["metal"],
    )
    index_z = zc - side_h * 0.43
    _box(
        yoke, "rear_index_arc_proxy", (hw * 1.55, 0.030, 0.030), (0.0, -0.050, index_z), m["accent"]
    )
    for i, x in enumerate((-hw * 0.55, 0.0, hw * 0.55)):
        _box(yoke, f"index_tick_{i}", (0.010, 0.035, 0.042), (x, -0.059, index_z), m["rubber"])
    for side, sx in (("left", -1), ("right", 1)):
        x = sx * hw
        _box(yoke, f"{side}_side_plate", (th, 0.094, side_h), (x, 0.0, zc), m["metal"])
        _box(
            yoke,
            f"{side}_front_gusset",
            (th * 0.90, 0.046, side_h * 0.42),
            (x, 0.036, zc - side_h * 0.25),
            m["base_dark"],
        )
        _box(
            yoke,
            f"{side}_rear_gusset",
            (th * 0.90, 0.046, side_h * 0.42),
            (x, -0.036, zc - side_h * 0.25),
            m["base_dark"],
        )
        _cyl(
            yoke,
            f"{side}_bearing_cup",
            0.047,
            th + 0.026,
            (x, 0.0, zc),
            m["base_dark"],
            rpy=X_CYLINDER_RPY,
        )
        _cyl(
            yoke,
            f"{side}_large_lock_wheel",
            0.046,
            0.046,
            (sx * (hw + th * 0.76), 0.0, zc),
            m["accent"],
            rpy=X_CYLINDER_RPY,
        )
        for j in range(6):
            a = j * math.tau / 6.0
            _box(
                yoke,
                f"{side}_lock_grip_{j}",
                (0.010, 0.028, 0.008),
                (sx * (hw + th * 0.92), math.cos(a) * 0.035, zc + math.sin(a) * 0.035),
                m["rubber"],
                rpy=(0.0, 0.0, 0.0),
            )
    _cyl(yoke, "tilt_axis_pin", 0.023, hw * 2.28, (0.0, 0.0, zc), m["metal"], rpy=X_CYLINDER_RPY)


def _build_yoke(
    model: ArticulatedObject, r: ResolvedStudioSpotlightOnYokeConfig, m: dict[str, str]
) -> Part:
    yoke = model.part("yoke")
    if r.yoke_style == "tubular_u_bracket":
        _build_tubular_u_yoke(yoke, r, m)
    elif r.yoke_style == "heavy_friction_yoke":
        _build_heavy_friction_yoke(yoke, r, m)
    else:
        _build_flat_side_plate_yoke(yoke, r, m)
    return yoke


def _add_can_body(can: Part, r: ResolvedStudioSpotlightOnYokeConfig, m: dict[str, str]) -> None:
    cr = r.can_radius
    cl = r.can_length
    front_y = cl * 0.5
    rear_y = -cl * 0.5
    if r.can_style == "long_throw_snoot":
        body_len = cl * 0.88
        snoot_len = cl * 0.35
        _cyl(
            can, "main_can_body", cr, body_len, (0.0, -cl * 0.08, 0.0), m["can"], rpy=Y_CYLINDER_RPY
        )
        _cyl(
            can,
            "front_snoot",
            cr * 0.72,
            snoot_len,
            (0.0, front_y - snoot_len * 0.45, 0.0),
            m["can"],
            rpy=Y_CYLINDER_RPY,
        )
        _cyl(
            can,
            "snoot_bezel",
            cr * 0.77,
            0.026,
            (0.0, front_y + 0.004, 0.0),
            m["bezel"],
            rpy=Y_CYLINDER_RPY,
        )
    elif r.can_style == "par_can":
        _cyl(can, "main_can_body", cr, cl, (0.0, 0.0, 0.0), m["can"], rpy=Y_CYLINDER_RPY)
        _cyl(
            can,
            "rear_deep_cap",
            cr * 0.92,
            r.can_rear_depth,
            (0.0, rear_y - r.can_rear_depth * 0.34, 0.0),
            m["bezel"],
            rpy=Y_CYLINDER_RPY,
        )
        _cyl(
            can,
            "par_lamp_bulge",
            cr * 0.58,
            0.032,
            (0.0, front_y - 0.036, 0.0),
            m["emitter"],
            rpy=Y_CYLINDER_RPY,
        )
    elif r.can_style == "vented_cylinder":
        _cyl(can, "main_can_body", cr, cl, (0.0, 0.0, 0.0), m["can"], rpy=Y_CYLINDER_RPY)
        for i in range(6):
            z = -cr * 0.42 + i * cr * 0.17
            _box(
                can,
                f"left_vent_slot_{i}",
                (0.014, 0.078, 0.010),
                (-cr * 0.80, -cl * 0.30, z),
                m["base_dark"],
            )
            _box(
                can,
                f"right_vent_slot_{i}",
                (0.014, 0.078, 0.010),
                (cr * 0.80, -cl * 0.30, z),
                m["base_dark"],
            )
        _cyl(
            can,
            "rear_vented_cap",
            cr * 0.92,
            r.can_rear_depth,
            (0.0, rear_y - r.can_rear_depth * 0.30, 0.0),
            m["bezel"],
            rpy=Y_CYLINDER_RPY,
        )
    else:
        _cyl(can, "main_can_body", cr, cl, (0.0, 0.0, 0.0), m["can"], rpy=Y_CYLINDER_RPY)
        _cyl(
            can,
            "fresnel_step_inner",
            cr * 0.70,
            0.018,
            (0.0, front_y - 0.018, 0.0),
            m["bezel"],
            rpy=Y_CYLINDER_RPY,
        )
        _cyl(
            can,
            "fresnel_step_outer",
            cr * 0.90,
            0.020,
            (0.0, front_y - 0.006, 0.0),
            m["bezel"],
            rpy=Y_CYLINDER_RPY,
        )
    _cyl(
        can,
        "front_bezel",
        cr * 1.07,
        0.030,
        (0.0, front_y + 0.006, 0.0),
        m["bezel"],
        rpy=Y_CYLINDER_RPY,
    )
    _cyl(
        can,
        "front_lens",
        cr * 0.82,
        0.012,
        (0.0, front_y + 0.022, 0.0),
        m["glass"],
        rpy=Y_CYLINDER_RPY,
    )
    _cyl(
        can,
        "warm_lamp_core",
        cr * 0.46,
        0.015,
        (0.0, front_y + 0.010, 0.0),
        m["emitter"],
        rpy=Y_CYLINDER_RPY,
    )
    _cyl(
        can,
        "rear_cap",
        cr * 0.92,
        0.036,
        (0.0, rear_y + 0.006, 0.0),
        m["bezel"],
        rpy=Y_CYLINDER_RPY,
    )
    _cyl(
        can,
        "can_trunnion_boss",
        0.028,
        r.yoke_half_width * 2.04,
        (0.0, 0.0, 0.0),
        m["metal"],
        rpy=X_CYLINDER_RPY,
    )
    _cyl(
        can,
        "left_trunnion_washer",
        0.036,
        0.018,
        (-r.yoke_half_width + 0.006, 0.0, 0.0),
        m["bezel"],
        rpy=X_CYLINDER_RPY,
    )
    _cyl(
        can,
        "right_trunnion_washer",
        0.036,
        0.018,
        (r.yoke_half_width - 0.006, 0.0, 0.0),
        m["bezel"],
        rpy=X_CYLINDER_RPY,
    )
    focus_y = -cl * 0.34
    _cyl(
        can,
        "left_focus_knob_boss",
        0.022,
        0.044,
        (-cr - 0.008, focus_y, 0.020),
        m["metal"],
        rpy=X_CYLINDER_RPY,
    )
    _cyl(
        can,
        "left_focus_knob",
        0.028,
        0.030,
        (-cr - 0.040, focus_y, 0.020),
        m["accent"],
        rpy=X_CYLINDER_RPY,
    )


def _add_barn_doors(can: Part, r: ResolvedStudioSpotlightOnYokeConfig, m: dict[str, str]) -> None:
    cr = r.can_radius
    y = r.can_length * 0.5 + 0.038
    _box(
        can,
        "barn_top_hinge_bar",
        (cr * 1.75, 0.018, 0.014),
        (0.0, y - 0.013, cr * 1.03),
        m["bezel"],
    )
    _box(
        can,
        "barn_bottom_hinge_bar",
        (cr * 1.75, 0.018, 0.014),
        (0.0, y - 0.013, -cr * 1.03),
        m["bezel"],
    )
    _box(
        can,
        "barn_left_hinge_bar",
        (0.014, 0.018, cr * 1.75),
        (-cr * 1.03, y - 0.013, 0.0),
        m["bezel"],
    )
    _box(
        can,
        "barn_right_hinge_bar",
        (0.014, 0.018, cr * 1.75),
        (cr * 1.03, y - 0.013, 0.0),
        m["bezel"],
    )
    _box(can, "barn_top_leaf", (cr * 1.74, 0.018, cr * 0.58), (0.0, y, cr * 1.30), m["base_dark"])
    _box(
        can, "barn_bottom_leaf", (cr * 1.74, 0.018, cr * 0.58), (0.0, y, -cr * 1.30), m["base_dark"]
    )
    _box(can, "barn_left_leaf", (cr * 0.56, 0.018, cr * 1.70), (-cr * 1.30, y, 0.0), m["base_dark"])
    _box(can, "barn_right_leaf", (cr * 0.56, 0.018, cr * 1.70), (cr * 1.30, y, 0.0), m["base_dark"])


def _add_gel_frame(can: Part, r: ResolvedStudioSpotlightOnYokeConfig, m: dict[str, str]) -> None:
    cr = r.can_radius
    y = r.can_length * 0.5 + 0.022
    _box(can, "gel_frame_top", (cr * 1.92, 0.018, 0.018), (0.0, y, cr * 0.94), m["accent"])
    _box(can, "gel_frame_bottom", (cr * 1.92, 0.018, 0.018), (0.0, y, -cr * 0.94), m["accent"])
    _box(can, "gel_frame_left", (0.018, 0.018, cr * 1.90), (-cr * 0.94, y, 0.0), m["accent"])
    _box(can, "gel_frame_right", (0.018, 0.018, cr * 1.90), (cr * 0.94, y, 0.0), m["accent"])
    _box(can, "gel_pull_tab", (0.055, 0.020, 0.022), (cr * 0.82, y, cr * 0.74), m["rubber"])


def _add_safety_cage(can: Part, r: ResolvedStudioSpotlightOnYokeConfig, m: dict[str, str]) -> None:
    cr = r.can_radius
    y0 = r.can_length * 0.5 + 0.038
    _cyl(
        can,
        "cage_front_ring_proxy",
        cr * 1.10,
        0.012,
        (0.0, y0 + 0.030, 0.0),
        m["metal"],
        rpy=Y_CYLINDER_RPY,
    )
    _cyl(
        can,
        "cage_rear_ring_proxy",
        cr * 1.06,
        0.012,
        (0.0, y0 - 0.005, 0.0),
        m["metal"],
        rpy=Y_CYLINDER_RPY,
    )
    for i in range(8):
        a = i * math.tau / 8.0
        x = math.cos(a) * cr * 0.82
        z = math.sin(a) * cr * 0.82
        _box(can, f"cage_bar_{i}", (0.010, 0.050, 0.010), (x, y0 + 0.014, z), m["metal"])


def _add_top_handle(can: Part, r: ResolvedStudioSpotlightOnYokeConfig, m: dict[str, str]) -> None:
    cr = r.can_radius
    y = -r.can_length * 0.32
    _box(
        can, "handle_left_riser", (0.024, 0.040, cr * 1.20), (-cr * 0.48, y, cr * 1.42), m["metal"]
    )
    _box(
        can, "handle_right_riser", (0.024, 0.040, cr * 1.20), (cr * 0.48, y, cr * 1.42), m["metal"]
    )
    _box(can, "handle_cross_grip", (cr * 1.16, 0.045, 0.032), (0.0, y, cr * 1.90), m["rubber"])


def _add_weather_hood(can: Part, r: ResolvedStudioSpotlightOnYokeConfig, m: dict[str, str]) -> None:
    cr = r.can_radius
    y = r.can_length * 0.5 + 0.018
    _box(
        can,
        "weather_top_lip",
        (cr * 2.04, 0.085, 0.028),
        (0.0, y + 0.024, cr * 1.12),
        m["base_dark"],
    )
    _box(
        can,
        "weather_left_lip",
        (0.030, 0.075, cr * 1.24),
        (-cr * 1.08, y + 0.016, cr * 0.36),
        m["base_dark"],
    )
    _box(
        can,
        "weather_right_lip",
        (0.030, 0.075, cr * 1.24),
        (cr * 1.08, y + 0.016, cr * 0.36),
        m["base_dark"],
    )
    _box(
        can, "lower_drip_tab", (cr * 1.35, 0.036, 0.018), (0.0, y + 0.012, -cr * 1.00), m["accent"]
    )


def _build_spotlight_can(
    model: ArticulatedObject, r: ResolvedStudioSpotlightOnYokeConfig, m: dict[str, str]
) -> Part:
    can = model.part("spotlight_can")
    _add_can_body(can, r, m)
    if r.accessory_style == "barn_doors":
        _add_barn_doors(can, r, m)
    elif r.accessory_style == "gel_frame":
        _add_gel_frame(can, r, m)
    elif r.accessory_style == "safety_cage":
        _add_safety_cage(can, r, m)
    elif r.accessory_style == "top_handle":
        _add_top_handle(can, r, m)
    elif r.accessory_style == "weather_hood":
        _add_weather_hood(can, r, m)
    return can


def build_studio_spotlight_on_yoke(
    config: StudioSpotlightOnYokeConfig | None = None,
    *,
    assets: AssetContext | None = None,
) -> ArticulatedObject:
    _ = assets
    config = config or StudioSpotlightOnYokeConfig()
    r = resolve_config(config)
    model = ArticulatedObject(r.name)
    m = _register_materials(model, r.material_style)
    stand = _build_stand(model, r, m)
    yoke = _build_yoke(model, r, m)
    can = _build_spotlight_can(model, r, m)
    model.articulation(
        "yoke_pan",
        ArticulationType.REVOLUTE,
        parent=stand,
        child=yoke,
        origin=Origin(xyz=(0.0, 0.0, r.mast_height)),
        axis=(0.0, 0.0, 1.0),
        motion_limits=MotionLimits(
            effort=90.0, velocity=1.2, lower=-r.yoke_pan_limit, upper=r.yoke_pan_limit
        ),
    )
    model.articulation(
        "can_tilt",
        ArticulationType.REVOLUTE,
        parent=yoke,
        child=can,
        origin=Origin(xyz=(0.0, 0.0, r.yoke_tilt_z)),
        axis=(1.0, 0.0, 0.0),
        motion_limits=MotionLimits(
            effort=80.0, velocity=1.0, lower=-r.can_tilt_limit, upper=r.can_tilt_limit
        ),
    )
    return model


def build_seeded_studio_spotlight_on_yoke(
    seed: int,
    *,
    assets: AssetContext | None = None,
) -> ArticulatedObject:
    return build_studio_spotlight_on_yoke(config_from_seed(seed), assets=assets)


def _allow_expected_overlaps(ctx: TestContext, model: ArticulatedObject) -> None:
    names = {p.name for p in model.parts}
    if "stand" in names and "yoke" in names:
        stand = model.get_part("stand")
        yoke = model.get_part("yoke")
        for elem_a in (
            "stand_top_bearing",
            "upper_mast",
            "short_mast",
            "tripod_upper_mast",
            "rolling_short_mast",
        ):
            for elem_b in (
                "yaw_spigot",
                "pan_index_collar",
                "lower_yoke_saddle",
                "lower_tube_bridge",
                "heavy_lower_saddle",
                "yoke_neck_block",
                "round_yoke_stem",
                "heavy_neck_block",
            ):
                try:
                    ctx.allow_overlap(
                        stand,
                        yoke,
                        elem_a=elem_a,
                        elem_b=elem_b,
                        reason="pan spigot is intentionally seated inside the stand head bearing",
                    )
                except Exception:
                    pass
    if "yoke" in names and "spotlight_can" in names:
        yoke = model.get_part("yoke")
        can = model.get_part("spotlight_can")
        yoke_elems = (
            "tilt_axis_pin",
            "left_bearing_cup",
            "right_bearing_cup",
            "left_side_plate",
            "right_side_plate",
            "left_upright_tube",
            "right_upright_tube",
            "left_front_gusset",
            "right_front_gusset",
            "left_rear_gusset",
            "right_rear_gusset",
        )
        can_elems = (
            "can_trunnion_boss",
            "left_trunnion_washer",
            "right_trunnion_washer",
            "main_can_body",
        )
        for elem_a in yoke_elems:
            for elem_b in can_elems:
                try:
                    ctx.allow_overlap(
                        yoke,
                        can,
                        elem_a=elem_a,
                        elem_b=elem_b,
                        reason="spotlight trunnion boss is captured through the yoke tilt bearing",
                    )
                except Exception:
                    pass


def run_studio_spotlight_on_yoke_tests(
    object_model: ArticulatedObject,
    config: StudioSpotlightOnYokeConfig,
) -> TestReport:
    r = resolve_config(config)
    ctx = TestContext(object_model)
    _allow_expected_overlaps(ctx, object_model)
    ctx.check_model_valid()
    ctx.fail_if_isolated_parts()
    ctx.warn_if_part_contains_disconnected_geometry_islands()
    ctx.fail_if_parts_overlap_in_current_pose()
    ctx.fail_if_articulation_origin_far_from_geometry(tol=0.015)
    part_names = {p.name for p in object_model.parts}
    joint_names = {j.name for j in object_model.joints}
    for required in ("stand", "yoke", "spotlight_can"):
        if required not in part_names:
            ctx.fail("identity_parts", f"missing {required}")
    for required in ("yoke_pan", "can_tilt"):
        if required not in joint_names:
            ctx.fail("identity_joints", f"missing {required}")
    if "yoke_pan" in joint_names:
        joint = object_model.get_articulation("yoke_pan")
        ctx.check("yoke_pan_axis_vertical", joint.axis == (0.0, 0.0, 1.0), details=f"{joint.axis}")
    if "can_tilt" in joint_names:
        joint = object_model.get_articulation("can_tilt")
        ctx.check(
            "can_tilt_axis_horizontal", joint.axis == (1.0, 0.0, 0.0), details=f"{joint.axis}"
        )
    if "spotlight_can" in part_names:
        can = object_model.get_part("spotlight_can")
        body_box = ctx.part_element_world_aabb(can, elem="main_can_body")
        if body_box is not None:
            center_z = (body_box[0][2] + body_box[1][2]) * 0.5
            ctx.check(
                "can_center_above_base",
                center_z > r.mast_height + r.yoke_tilt_z - 0.030,
                details=f"center_z={center_z:.3f} mast={r.mast_height:.3f}",
            )
    if "can_tilt" in joint_names and "spotlight_can" in part_names:
        can = object_model.get_part("spotlight_can")
        rest = ctx.part_element_world_aabb(can, elem="front_bezel")
        with ctx.pose(can_tilt=r.can_tilt_limit * 0.62):
            tilted = ctx.part_element_world_aabb(can, elem="front_bezel")
        if rest is not None and tilted is not None:
            rest_z = (rest[0][2] + rest[1][2]) * 0.5
            tilted_z = (tilted[0][2] + tilted[1][2]) * 0.5
            ctx.check(
                "tilt_changes_front_height",
                abs(tilted_z - rest_z) > 0.055,
                details=f"rest_z={rest_z:.3f}, tilted_z={tilted_z:.3f}",
            )
    if "yoke_pan" in joint_names and "spotlight_can" in part_names:
        can = object_model.get_part("spotlight_can")
        rest = ctx.part_element_world_aabb(can, elem="front_bezel")
        with ctx.pose(yoke_pan=min(r.yoke_pan_limit * 0.45, math.radians(82.0))):
            turned = ctx.part_element_world_aabb(can, elem="front_bezel")
        if rest is not None and turned is not None:
            rest_x = (rest[0][0] + rest[1][0]) * 0.5
            turned_x = (turned[0][0] + turned[1][0]) * 0.5
            ctx.check(
                "pan_moves_lamp_front",
                abs(turned_x - rest_x) > 0.060,
                details=f"rest_x={rest_x:.3f}, turned_x={turned_x:.3f}",
            )
    if "yoke" in part_names and "spotlight_can" in part_names:
        yoke = object_model.get_part("yoke")
        can = object_model.get_part("spotlight_can")
        left = ctx.part_element_world_aabb(
            yoke, elem="left_side_plate"
        ) or ctx.part_element_world_aabb(yoke, elem="left_upright_tube")
        right = ctx.part_element_world_aabb(
            yoke, elem="right_side_plate"
        ) or ctx.part_element_world_aabb(yoke, elem="right_upright_tube")
        body = ctx.part_element_world_aabb(can, elem="main_can_body")
        if left is not None and right is not None and body is not None:
            ctx.check(
                "yoke_captures_can_sides",
                left[1][0] < body[0][0] + 0.020 and right[0][0] > body[1][0] - 0.020,
                details=f"left={left}, body={body}, right={right}",
            )
    return ctx.report()


__all__ = [
    "StudioSpotlightOnYokeConfig",
    "ResolvedStudioSpotlightOnYokeConfig",
    "build_studio_spotlight_on_yoke",
    "build_seeded_studio_spotlight_on_yoke",
    "config_from_seed",
    "resolve_config",
    "run_studio_spotlight_on_yoke_tests",
    "slot_choices_for_config",
    "slot_choices_for_seed",
]
