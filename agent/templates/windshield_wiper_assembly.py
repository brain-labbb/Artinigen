"""Modular procedural template for windshield wiper assemblies."""

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
    MatingContract,
    MotionLimits,
    Origin,
    TestContext,
    TestReport,
)

__modular__ = True

BaseModule = Literal[
    "compact_motor_pod",
    "wide_cowl_plate",
    "service_tray_cowl",
    "dual_bearing_tube",
]
WiperLayout = Literal[
    "single_center",
    "single_offset",
    "dual_parallel",
    "dual_splayed",
    "compact_dual",
    "triple_bus_row",
    "quad_train_row",
    "single_twin_blade",
]
DriveModule = Literal[
    "direct_spindle",
    "exposed_crank_stub",
    "covered_linkage_boss",
    "cross_tube_drive",
]
ArmProfile = Literal[
    "straight_stamped_arm",
    "tapered_steel_arm",
    "spring_braced_arm",
    "boxy_service_arm",
]
BladeProfile = Literal[
    "straight_rubber_blade",
    "spoiler_blade",
    "multi_claw_frame",
    "chunky_winter_blade",
]
MaterialStyle = Literal["satin_black", "brushed_steel", "dark_polymer", "fleet_gray"]

BASE_MODULES: tuple[BaseModule, ...] = (
    "compact_motor_pod",
    "wide_cowl_plate",
    "service_tray_cowl",
    "dual_bearing_tube",
)
WIPER_LAYOUTS: tuple[WiperLayout, ...] = (
    "single_center",
    "single_offset",
    "dual_parallel",
    "dual_splayed",
    "compact_dual",
    "triple_bus_row",
    "quad_train_row",
    "single_twin_blade",
)
DRIVE_MODULES: tuple[DriveModule, ...] = (
    "direct_spindle",
    "exposed_crank_stub",
    "covered_linkage_boss",
    "cross_tube_drive",
)
ARM_PROFILES: tuple[ArmProfile, ...] = (
    "straight_stamped_arm",
    "tapered_steel_arm",
    "spring_braced_arm",
    "boxy_service_arm",
)
BLADE_PROFILES: tuple[BladeProfile, ...] = (
    "straight_rubber_blade",
    "spoiler_blade",
    "multi_claw_frame",
    "chunky_winter_blade",
)
MATERIAL_STYLES: tuple[MaterialStyle, ...] = (
    "satin_black",
    "brushed_steel",
    "dark_polymer",
    "fleet_gray",
)

PALETTES: dict[MaterialStyle, dict[str, tuple[float, float, float, float]]] = {
    "satin_black": {
        "base": (0.08, 0.085, 0.09, 1.0),
        "body": (0.015, 0.016, 0.018, 1.0),
        "metal": (0.56, 0.58, 0.60, 1.0),
        "rubber": (0.004, 0.004, 0.004, 1.0),
        "accent": (0.20, 0.22, 0.23, 1.0),
        "glass": (0.20, 0.32, 0.38, 0.34),
    },
    "brushed_steel": {
        "base": (0.42, 0.43, 0.42, 1.0),
        "body": (0.18, 0.19, 0.20, 1.0),
        "metal": (0.70, 0.71, 0.68, 1.0),
        "rubber": (0.010, 0.010, 0.010, 1.0),
        "accent": (0.10, 0.18, 0.28, 1.0),
        "glass": (0.20, 0.34, 0.42, 0.34),
    },
    "dark_polymer": {
        "base": (0.11, 0.12, 0.13, 1.0),
        "body": (0.035, 0.038, 0.040, 1.0),
        "metal": (0.46, 0.47, 0.46, 1.0),
        "rubber": (0.004, 0.004, 0.004, 1.0),
        "accent": (0.18, 0.18, 0.17, 1.0),
        "glass": (0.16, 0.28, 0.34, 0.32),
    },
    "fleet_gray": {
        "base": (0.36, 0.37, 0.36, 1.0),
        "body": (0.08, 0.09, 0.095, 1.0),
        "metal": (0.62, 0.62, 0.59, 1.0),
        "rubber": (0.006, 0.006, 0.006, 1.0),
        "accent": (0.58, 0.58, 0.52, 1.0),
        "glass": (0.18, 0.30, 0.36, 0.30),
    },
}


@dataclass(frozen=True)
class WindshieldWiperAssemblyConfig:
    base_module: BaseModule | None = None
    wiper_layout: WiperLayout | None = None
    drive_module: DriveModule | None = None
    arm_profile: ArmProfile | None = None
    blade_profile: BladeProfile | None = None
    arm_reach_scale: float = 1.0
    blade_length_scale: float = 1.0
    station_spacing_scale: float = 1.0
    material_style: MaterialStyle = "satin_black"
    name: str = "windshield_wiper_assembly"


@dataclass(frozen=True)
class WiperStation:
    index: int
    origin: tuple[float, float, float]
    reach: float
    blade_length: float
    sweep_lower: float
    sweep_upper: float
    blade_roll: float
    side_sign: int


@dataclass(frozen=True)
class ResolvedWindshieldWiperAssemblyConfig:
    base_module: BaseModule
    wiper_layout: WiperLayout
    drive_module: DriveModule
    arm_profile: ArmProfile
    blade_profile: BladeProfile
    material_style: MaterialStyle
    width: float
    depth: float
    base_height: float
    pivot_z: float
    arm_count: int
    blades_per_arm: int
    stations: tuple[WiperStation, ...]
    name: str


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _choice(value: str | None, allowed: tuple[str, ...], fallback: str, field: str) -> str:
    if value is None:
        return fallback
    if value not in allowed:
        raise ValueError(f"Unsupported {field}: {value}")
    return value


def config_from_seed(seed: int) -> WindshieldWiperAssemblyConfig:
    rng = random.Random(seed)
    layout: WiperLayout = rng.choice(WIPER_LAYOUTS)
    return WindshieldWiperAssemblyConfig(
        base_module=rng.choice(BASE_MODULES),
        wiper_layout=layout,
        drive_module=rng.choice(DRIVE_MODULES),
        arm_profile=rng.choice(ARM_PROFILES),
        blade_profile=rng.choice(BLADE_PROFILES),
        arm_reach_scale=round(rng.uniform(0.86, 1.18), 3),
        blade_length_scale=round(rng.uniform(0.86, 1.20), 3),
        station_spacing_scale=round(rng.uniform(0.88, 1.16), 3),
        material_style=rng.choice(MATERIAL_STYLES),
        name=f"seeded_windshield_wiper_assembly_{seed}",
    )


def resolve_config(
    config: WindshieldWiperAssemblyConfig,
) -> ResolvedWindshieldWiperAssemblyConfig:
    base = _choice(config.base_module, BASE_MODULES, "compact_motor_pod", "base_module")
    layout = _choice(config.wiper_layout, WIPER_LAYOUTS, "single_center", "wiper_layout")
    drive = _choice(config.drive_module, DRIVE_MODULES, "direct_spindle", "drive_module")
    arm = _choice(config.arm_profile, ARM_PROFILES, "tapered_steel_arm", "arm_profile")
    blade = _choice(config.blade_profile, BLADE_PROFILES, "straight_rubber_blade", "blade_profile")
    material = _choice(config.material_style, MATERIAL_STYLES, "satin_black", "material_style")

    reach = 0.56 * _clamp(config.arm_reach_scale, 0.74, 1.30)
    blade_len = 0.56 * _clamp(config.blade_length_scale, 0.72, 1.30)
    spacing = 0.34 * _clamp(config.station_spacing_scale, 0.70, 1.32)
    pivot_z = 0.090
    width = (
        1.50
        if layout == "quad_train_row"
        else 1.32
        if layout == "triple_bus_row"
        else 1.10
        if layout.startswith("dual") or layout == "compact_dual"
        else 0.76
        if layout == "single_twin_blade"
        else 0.62
    )
    if base in {"wide_cowl_plate", "dual_bearing_tube"}:
        width += 0.16
    depth = 0.18 if base != "compact_motor_pod" else 0.15
    stations: list[WiperStation] = []
    if layout == "single_center":
        stations.append(_station(0, 0.0, reach, blade_len, pivot_z, 1))
    elif layout == "single_offset":
        stations.append(_station(0, -spacing * 0.52, reach * 0.96, blade_len * 0.94, pivot_z, 1))
    elif layout == "single_twin_blade":
        stations.append(_station(0, 0.0, reach * 0.92, blade_len * 0.88, pivot_z, 1))
    elif layout == "compact_dual":
        for i, x in enumerate((-spacing * 0.46, spacing * 0.46)):
            stations.append(
                _station(i, x, reach * 0.82, blade_len * 0.82, pivot_z, -1 if i == 0 else 1)
            )
    elif layout == "triple_bus_row":
        for i, x in enumerate((-spacing * 1.08, 0.0, spacing * 1.08)):
            side = -1 if i == 0 else 1 if i == 2 else 0
            stations.append(_station(i, x, reach * 0.70, blade_len * 0.70, pivot_z, side))
    elif layout == "quad_train_row":
        for i, (x, side) in enumerate(
            (
                (-spacing * 1.65, -2),
                (-spacing * 0.55, -1),
                (spacing * 0.55, 1),
                (spacing * 1.65, 2),
            )
        ):
            stations.append(_station(i, x, reach * 0.58, blade_len * 0.50, pivot_z, side))
    elif layout == "dual_splayed":
        for i, x in enumerate((-spacing, spacing)):
            stations.append(
                _station(
                    i,
                    x,
                    reach * (0.96 + i * 0.04),
                    blade_len * (0.92 + i * 0.06),
                    pivot_z,
                    -1 if i == 0 else 1,
                )
            )
    else:
        for i, x in enumerate((-spacing, spacing)):
            stations.append(_station(i, x, reach, blade_len, pivot_z, -1 if i == 0 else 1))
    return ResolvedWindshieldWiperAssemblyConfig(
        base_module=base,
        wiper_layout=layout,
        drive_module=drive,
        arm_profile=arm,
        blade_profile=blade,
        material_style=material,
        width=width,
        depth=depth,
        base_height=0.042,
        pivot_z=pivot_z,
        arm_count=len(stations),
        blades_per_arm=2 if layout == "single_twin_blade" else 1,
        stations=tuple(stations),
        name=config.name or "windshield_wiper_assembly",
    )


def _station(
    index: int,
    x: float,
    reach: float,
    blade_len: float,
    pivot_z: float,
    side_sign: int,
) -> WiperStation:
    return WiperStation(
        index=index,
        origin=(x, 0.0, pivot_z),
        reach=reach,
        blade_length=blade_len,
        sweep_lower=-0.78 if side_sign > 0 else -0.56,
        sweep_upper=0.98 if side_sign > 0 else 0.78,
        blade_roll=0.34,
        side_sign=side_sign,
    )


def with_overrides(
    config: WindshieldWiperAssemblyConfig, **kwargs: object
) -> WindshieldWiperAssemblyConfig:
    return replace(config, **kwargs)


def slot_choices_for_config(
    config: WindshieldWiperAssemblyConfig | ResolvedWindshieldWiperAssemblyConfig,
) -> tuple[tuple[str, str], ...]:
    r = (
        config
        if isinstance(config, ResolvedWindshieldWiperAssemblyConfig)
        else resolve_config(config)
    )
    return (
        ("base", r.base_module),
        ("layout", r.wiper_layout),
        ("drive", r.drive_module),
        ("arm_profile", r.arm_profile),
        ("blade_profile", r.blade_profile),
        ("wiper_multiplicity", f"{r.arm_count}_wiper_arms"),
        ("blade_multiplicity", f"{r.blades_per_arm}_blades_per_arm"),
        ("material_style", r.material_style),
    )


def slot_choices_for_seed(seed: int) -> tuple[tuple[str, str], ...]:
    return slot_choices_for_config(config_from_seed(seed))


def _mat(model: ArticulatedObject, r: ResolvedWindshieldWiperAssemblyConfig, key: str):
    return model.material(f"wiper_{key}", rgba=PALETTES[r.material_style][key])


def _box(part, size, xyz, material, name, rpy=(0.0, 0.0, 0.0)) -> None:
    part.visual(Box(size), origin=Origin(xyz=xyz, rpy=rpy), material=material, name=name)


def _cyl(part, radius, length, xyz, material, name, rpy=(0.0, 0.0, 0.0)) -> None:
    part.visual(
        Cylinder(radius=radius, length=length),
        origin=Origin(xyz=xyz, rpy=rpy),
        material=material,
        name=name,
    )


def _build_base(
    model: ArticulatedObject,
    r: ResolvedWindshieldWiperAssemblyConfig,
    mats: dict[str, object],
):
    base = model.part("cowl_base")
    W, D = r.width, r.depth
    _box(base, (W, D, 0.026), (0.0, 0.0, 0.013), mats["base"], "cowl_mount_plate")
    _box(base, (W * 0.92, D * 0.32, 0.022), (0.0, -D * 0.37, 0.042), mats["body"], "rear_cowl_lip")
    _box(
        base, (W * 0.86, 0.006, 0.006), (0.0, D * 0.49, 0.029), mats["accent"], "front_weather_seam"
    )
    if r.base_module in {"wide_cowl_plate", "service_tray_cowl"}:
        _box(
            base,
            (W * 0.78, D * 0.18, 0.010),
            (0.0, D * 0.16, 0.036),
            mats["accent"],
            "service_access_panel",
        )
    if r.base_module == "compact_motor_pod":
        _box(
            base,
            (0.22, 0.12, 0.050),
            (r.stations[0].origin[0], -0.010, 0.051),
            mats["body"],
            "compact_motor_gearbox",
        )
    if r.base_module == "dual_bearing_tube":
        _cyl(
            base,
            0.015,
            W * 0.82,
            (0.0, -0.055, 0.060),
            mats["metal"],
            "cross_torsion_tube",
            (0.0, 1.5708, 0.0),
        )
    if r.base_module == "service_tray_cowl":
        _box(
            base,
            (W * 0.94, D * 0.84, 0.006),
            (0.0, 0.0, 0.049),
            mats["glass"],
            "low_windshield_reference",
        )
    for station in r.stations:
        _build_spindle_socket(base, r, station, mats)
    _build_drive_details(base, r, mats)
    return base


def _build_spindle_socket(
    base,
    r: ResolvedWindshieldWiperAssemblyConfig,
    station: WiperStation,
    mats: dict[str, object],
) -> None:
    x, y, z = station.origin
    _cyl(base, 0.044, 0.030, (x, y, 0.041), mats["body"], f"bearing_pedestal_{station.index}")
    _cyl(base, 0.028, 0.032, (x, y, 0.062), mats["metal"], f"bearing_sleeve_{station.index}")
    _cyl(base, 0.017, 0.024, (x, y, z - 0.012), mats["metal"], f"spindle_post_{station.index}")
    _box(
        base,
        (0.090, 0.026, 0.026),
        (x, -0.040, 0.050),
        mats["body"],
        f"bearing_gusset_{station.index}",
    )
    for k, ox in enumerate((-0.044, 0.044)):
        _cyl(
            base,
            0.006,
            0.004,
            (x + ox, y + 0.036, 0.028),
            mats["metal"],
            f"bearing_bolt_{station.index}_{k}",
        )


def _build_drive_details(
    base,
    r: ResolvedWindshieldWiperAssemblyConfig,
    mats: dict[str, object],
) -> None:
    mid_x = sum(station.origin[0] for station in r.stations) / len(r.stations)
    if r.drive_module == "direct_spindle":
        _box(
            base, (0.12, 0.060, 0.018), (mid_x, -0.056, 0.033), mats["accent"], "direct_drive_cover"
        )
    elif r.drive_module == "exposed_crank_stub":
        _cyl(base, 0.014, 0.046, (mid_x, -0.070, 0.049), mats["metal"], "exposed_crank_stanchion")
        _cyl(base, 0.034, 0.014, (mid_x, -0.070, 0.070), mats["metal"], "exposed_crank_disc")
        _box(
            base,
            (0.086, 0.016, 0.010),
            (mid_x + 0.024, -0.070, 0.081),
            mats["metal"],
            "exposed_crank_arm",
        )
    elif r.drive_module == "covered_linkage_boss":
        _box(
            base,
            (0.22, 0.070, 0.034),
            (mid_x, -0.060, 0.057),
            mats["body"],
            "covered_linkage_housing",
        )
        _box(base, (0.18, 0.008, 0.006), (mid_x, -0.024, 0.073), mats["accent"], "cover_split_line")
    else:
        _cyl(
            base,
            0.012,
            r.width * 0.72,
            (0.0, -0.050, 0.074),
            mats["metal"],
            "visible_cross_drive_tube",
            (0.0, 1.5708, 0.0),
        )
        for station in r.stations:
            _box(
                base,
                (0.024, 0.042, 0.014),
                (station.origin[0], -0.050, 0.074),
                mats["metal"],
                f"tube_clevis_{station.index}",
            )


def _build_arm_part(
    model: ArticulatedObject,
    r: ResolvedWindshieldWiperAssemblyConfig,
    station: WiperStation,
    mats: dict[str, object],
):
    arm = model.part(f"wiper_arm_{station.index}")
    reach = station.reach
    _cyl(arm, 0.033, 0.018, (0.0, 0.0, 0.009), mats["metal"], "arm_hub")
    _cyl(arm, 0.018, 0.010, (0.0, 0.0, 0.023), mats["accent"], "retaining_nut")
    if r.arm_profile == "boxy_service_arm":
        _box(arm, (0.040, reach, 0.016), (0.0, reach * 0.50, 0.017), mats["body"], "main_arm_beam")
        _box(arm, (0.064, 0.090, 0.020), (0.0, 0.060, 0.017), mats["body"], "root_bridge")
    elif r.arm_profile == "spring_braced_arm":
        _box(arm, (0.026, reach, 0.010), (0.0, reach * 0.50, 0.016), mats["body"], "main_arm_beam")
        _box(
            arm,
            (0.010, reach * 0.72, 0.008),
            (-0.026, reach * 0.48, 0.024),
            mats["metal"],
            "left_spring_brace",
        )
        _box(
            arm,
            (0.010, reach * 0.72, 0.008),
            (0.026, reach * 0.48, 0.024),
            mats["metal"],
            "right_spring_brace",
        )
        _box(arm, (0.060, 0.026, 0.010), (0.0, reach * 0.30, 0.024), mats["metal"], "brace_clip")
    elif r.arm_profile == "straight_stamped_arm":
        _box(arm, (0.030, reach, 0.010), (0.0, reach * 0.50, 0.016), mats["body"], "main_arm_beam")
        _box(
            arm,
            (0.012, reach * 0.78, 0.012),
            (0.0, reach * 0.52, 0.026),
            mats["accent"],
            "pressed_center_rib",
        )
    else:
        _box(
            arm,
            (0.044, reach * 0.34, 0.014),
            (0.0, reach * 0.20, 0.017),
            mats["body"],
            "wide_root_arm",
        )
        _box(
            arm,
            (0.026, reach * 0.70, 0.012),
            (0.0, reach * 0.63, 0.017),
            mats["body"],
            "narrow_tip_arm",
        )
        _box(
            arm,
            (0.012, reach * 0.56, 0.010),
            (0.0, reach * 0.56, 0.027),
            mats["accent"],
            "raised_spine",
        )
    _box(arm, (0.060, 0.018, 0.032), (0.0, reach - 0.009, 0.018), mats["metal"], "tip_socket")
    return arm


def _build_blade_part(
    model: ArticulatedObject,
    r: ResolvedWindshieldWiperAssemblyConfig,
    station: WiperStation,
    mats: dict[str, object],
):
    blade = model.part(f"blade_carrier_{station.index}")
    length = station.blade_length
    x_shift = _blade_x_shift(r, station, length)
    _box(blade, (0.060, 0.018, 0.034), (0.0, 0.009, 0.0), mats["metal"], "roll_hub")
    bridge_y_size = 0.096 if r.blades_per_arm > 1 else 0.042
    bridge_y = 0.050 if r.blades_per_arm > 1 else 0.026
    _box(
        blade,
        (abs(x_shift) + 0.054, bridge_y_size, 0.024),
        (x_shift * 0.5, bridge_y, -0.020),
        mats["metal"],
        "blade_yoke_bridge",
    )
    lane_offsets = (0.032, 0.080) if r.blades_per_arm > 1 else (0.044,)
    for lane, lane_y in enumerate(lane_offsets):
        suffix = f"_{lane}" if r.blades_per_arm > 1 else ""
        if r.blade_profile == "chunky_winter_blade":
            _box(
                blade,
                (length, 0.034, 0.024),
                (x_shift, lane_y, -0.034),
                mats["body"],
                f"covered_blade_spine{suffix}",
            )
            _box(
                blade,
                (length * 0.92, 0.020, 0.034),
                (x_shift, lane_y, -0.066),
                mats["rubber"],
                f"wide_rubber_squeegee{suffix}",
            )
        else:
            _box(
                blade,
                (length, 0.018, 0.014),
                (x_shift, lane_y, -0.030),
                mats["metal"],
                f"blade_spine{suffix}",
            )
            _box(
                blade,
                (length * 0.96, 0.010, 0.034),
                (x_shift, lane_y, -0.054),
                mats["rubber"],
                f"rubber_squeegee{suffix}",
            )
        if r.blade_profile == "spoiler_blade":
            _box(
                blade,
                (length * 0.86, 0.012, 0.024),
                (x_shift, lane_y - 0.014, -0.012),
                mats["body"],
                f"aero_spoiler{suffix}",
            )
        elif r.blade_profile == "multi_claw_frame":
            for k, x in enumerate((-0.35, -0.16, 0.0, 0.16, 0.35)):
                _box(
                    blade,
                    (0.032, 0.030, 0.038),
                    (x_shift + length * x, lane_y, -0.038),
                    mats["body"],
                    f"blade_claw{suffix}_{k}",
                )
        else:
            for k, x in enumerate((-0.44, 0.44)):
                _box(
                    blade,
                    (0.026, 0.024, 0.034),
                    (x_shift + length * x, lane_y, -0.044),
                    mats["accent"],
                    f"blade_end_cap{suffix}_{k}",
                )
    return blade


def _blade_x_shift(
    r: ResolvedWindshieldWiperAssemblyConfig,
    station: WiperStation,
    length: float,
) -> float:
    if r.arm_count <= 1:
        return 0.0
    if r.wiper_layout == "triple_bus_row":
        factor = 0.56
    elif r.wiper_layout == "compact_dual":
        factor = 0.36
    elif r.wiper_layout == "quad_train_row":
        factor = 0.30
    else:
        factor = 0.28
    return station.side_sign * length * factor


def build_windshield_wiper_assembly(
    config: WindshieldWiperAssemblyConfig | None = None,
    *,
    assets: AssetContext | None = None,
) -> ArticulatedObject:
    cfg = config or WindshieldWiperAssemblyConfig()
    r = resolve_config(cfg)
    model = ArticulatedObject(name=r.name, assets=assets)
    mats = {
        key: _mat(model, r, key) for key in ("base", "body", "metal", "rubber", "accent", "glass")
    }
    base = _build_base(model, r, mats)
    for station in r.stations:
        arm = _build_arm_part(model, r, station, mats)
        model.articulation(
            f"arm_{station.index}_sweep",
            ArticulationType.REVOLUTE,
            parent=base,
            child=arm,
            origin=Origin(xyz=station.origin),
            axis=(0.0, 0.0, 1.0),
            motion_limits=MotionLimits(
                effort=18.0,
                velocity=2.4,
                lower=station.sweep_lower,
                upper=station.sweep_upper,
            ),
            mating=MatingContract(
                f"spindle_post_{station.index}",
                "positive_z",
                "arm_hub",
                "negative_z",
                contact_tol=0.002,
            ),
        )
        blade = _build_blade_part(model, r, station, mats)
        model.articulation(
            f"blade_{station.index}_roll",
            ArticulationType.REVOLUTE,
            parent=arm,
            child=blade,
            origin=Origin(xyz=(0.0, station.reach, 0.018)),
            axis=(1.0, 0.0, 0.0),
            motion_limits=MotionLimits(
                effort=3.0,
                velocity=1.6,
                lower=-station.blade_roll,
                upper=station.blade_roll,
            ),
            mating=MatingContract(
                "tip_socket",
                "positive_y",
                "roll_hub",
                "negative_y",
                contact_tol=0.002,
            ),
        )
    model.meta["slot_choices"] = slot_choices_for_config(r)
    return model


def build_seeded_windshield_wiper_assembly(
    seed: int,
    *,
    assets: AssetContext | None = None,
) -> ArticulatedObject:
    return build_windshield_wiper_assembly(config_from_seed(seed), assets=assets)


def run_windshield_wiper_assembly_tests(
    object_model: ArticulatedObject,
    config: WindshieldWiperAssemblyConfig,
) -> TestReport:
    r = resolve_config(config)
    ctx = TestContext(object_model)
    ctx.check_model_valid()
    ctx.check_mesh_assets_ready()
    ctx.fail_if_isolated_parts()
    ctx.fail_if_parts_overlap_in_current_pose()
    ctx.fail_if_articulation_origin_far_from_geometry(tol=0.015)
    ctx.fail_if_joint_mating_has_gap()

    part_names = {part.name for part in object_model.parts}
    ctx.check("base_present", "cowl_base" in part_names, details=str(sorted(part_names)))
    arm_parts = [name for name in part_names if name.startswith("wiper_arm_")]
    blade_parts = [name for name in part_names if name.startswith("blade_carrier_")]
    ctx.check(
        "arm_count",
        len(arm_parts) == r.arm_count,
        details=f"expected {r.arm_count}, got {len(arm_parts)}",
    )
    ctx.check(
        "blade_count",
        len(blade_parts) == r.arm_count,
        details=f"expected {r.arm_count}, got {len(blade_parts)}",
    )
    sweep_joints = [joint for joint in object_model.joints if joint.name.endswith("_sweep")]
    roll_joints = [joint for joint in object_model.joints if joint.name.endswith("_roll")]
    ctx.check(
        "sweep_joint_count",
        len(sweep_joints) == r.arm_count,
        details=f"expected {r.arm_count}, got {len(sweep_joints)}",
    )
    ctx.check(
        "roll_joint_count",
        len(roll_joints) == r.arm_count,
        details=f"expected {r.arm_count}, got {len(roll_joints)}",
    )
    for joint in sweep_joints:
        ctx.check(
            f"{joint.name}_revolute",
            joint.articulation_type == ArticulationType.REVOLUTE,
            details=str(joint.articulation_type),
        )
        ctx.check(
            f"{joint.name}_axis", tuple(joint.axis) == (0.0, 0.0, 1.0), details=str(joint.axis)
        )
        ctx.check(
            f"{joint.name}_mating",
            joint.mating is not None,
            details="sweep arm must mate to spindle",
        )
    for joint in roll_joints:
        ctx.check(
            f"{joint.name}_revolute",
            joint.articulation_type == ArticulationType.REVOLUTE,
            details=str(joint.articulation_type),
        )
        ctx.check(
            f"{joint.name}_axis", tuple(joint.axis) == (1.0, 0.0, 0.0), details=str(joint.axis)
        )
        ctx.check(
            f"{joint.name}_mating",
            joint.mating is not None,
            details="blade carrier must mate to arm tip socket",
        )
    return ctx.report()


__all__ = [
    "WindshieldWiperAssemblyConfig",
    "ResolvedWindshieldWiperAssemblyConfig",
    "build_windshield_wiper_assembly",
    "build_seeded_windshield_wiper_assembly",
    "config_from_seed",
    "resolve_config",
    "run_windshield_wiper_assembly_tests",
    "slot_choices_for_config",
    "slot_choices_for_seed",
    "with_overrides",
]
