"""Modular procedural template for a sluice gate with a vertical lift panel."""

from __future__ import annotations

import math
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

FoundationStyle = Literal[
    "plain_concrete_channel",
    "flared_wing_wall",
    "inspection_deck",
]
FrameStyle = Literal[
    "twin_u_channel",
    "heavy_portal_frame",
    "braced_side_towers",
]
PanelStyle = Literal[
    "flat_steel_plate",
    "ribbed_plate",
    "open_grate_panel",
]
LiftDrive = Literal[
    "handwheel_screw",
    "gearbox_chain",
    "overhead_winch",
]
SealStyle = Literal[
    "rubber_side_seals",
    "bronze_slide_shoes",
    "brush_wipers",
]
CounterweightStyle = Literal["none", "twin_counterweights"]
MaterialStyle = Literal[
    "weathered_concrete",
    "galvanized_steel",
    "painted_blue",
    "industrial_green",
]

FOUNDATION_STYLES: tuple[FoundationStyle, ...] = (
    "plain_concrete_channel",
    "flared_wing_wall",
    "inspection_deck",
)
FRAME_STYLES: tuple[FrameStyle, ...] = (
    "twin_u_channel",
    "heavy_portal_frame",
    "braced_side_towers",
)
PANEL_STYLES: tuple[PanelStyle, ...] = (
    "flat_steel_plate",
    "ribbed_plate",
    "open_grate_panel",
)
LIFT_DRIVES: tuple[LiftDrive, ...] = (
    "handwheel_screw",
    "gearbox_chain",
    "overhead_winch",
)
SEAL_STYLES: tuple[SealStyle, ...] = (
    "rubber_side_seals",
    "bronze_slide_shoes",
    "brush_wipers",
)
COUNTERWEIGHT_STYLES: tuple[CounterweightStyle, ...] = ("none", "twin_counterweights")
MATERIAL_STYLES: tuple[MaterialStyle, ...] = (
    "weathered_concrete",
    "galvanized_steel",
    "painted_blue",
    "industrial_green",
)

PALETTES: dict[MaterialStyle, dict[str, tuple[float, float, float, float]]] = {
    "weathered_concrete": {
        "concrete": (0.48, 0.49, 0.46, 1.0),
        "metal": (0.44, 0.46, 0.45, 1.0),
        "panel": (0.32, 0.35, 0.36, 1.0),
        "dark": (0.06, 0.065, 0.065, 1.0),
        "accent": (0.78, 0.58, 0.18, 1.0),
        "water": (0.10, 0.28, 0.36, 0.36),
    },
    "galvanized_steel": {
        "concrete": (0.56, 0.56, 0.52, 1.0),
        "metal": (0.66, 0.68, 0.66, 1.0),
        "panel": (0.54, 0.57, 0.58, 1.0),
        "dark": (0.10, 0.11, 0.11, 1.0),
        "accent": (0.18, 0.22, 0.24, 1.0),
        "water": (0.08, 0.24, 0.32, 0.34),
    },
    "painted_blue": {
        "concrete": (0.47, 0.48, 0.45, 1.0),
        "metal": (0.34, 0.38, 0.40, 1.0),
        "panel": (0.04, 0.22, 0.46, 1.0),
        "dark": (0.04, 0.055, 0.07, 1.0),
        "accent": (0.92, 0.72, 0.12, 1.0),
        "water": (0.08, 0.30, 0.42, 0.36),
    },
    "industrial_green": {
        "concrete": (0.46, 0.47, 0.44, 1.0),
        "metal": (0.30, 0.34, 0.32, 1.0),
        "panel": (0.05, 0.30, 0.20, 1.0),
        "dark": (0.04, 0.06, 0.05, 1.0),
        "accent": (0.82, 0.70, 0.18, 1.0),
        "water": (0.07, 0.25, 0.30, 0.34),
    },
}


@dataclass(frozen=True)
class SluiceGateWithVerticalLiftPanelConfig:
    foundation_style: FoundationStyle | None = None
    frame_style: FrameStyle | None = None
    panel_style: PanelStyle | None = None
    lift_drive: LiftDrive | None = None
    seal_style: SealStyle | None = None
    counterweight_style: CounterweightStyle | None = None
    opening_width_scale: float = 1.0
    panel_height_scale: float = 1.0
    lift_travel_scale: float = 1.0
    material_style: MaterialStyle = "weathered_concrete"
    name: str = "sluice_gate_with_vertical_lift_panel"


@dataclass(frozen=True)
class ResolvedSluiceGateWithVerticalLiftPanelConfig:
    foundation_style: FoundationStyle
    frame_style: FrameStyle
    panel_style: PanelStyle
    lift_drive: LiftDrive
    seal_style: SealStyle
    counterweight_style: CounterweightStyle
    material_style: MaterialStyle
    opening_width: float
    channel_depth: float
    sill_height: float
    panel_width: float
    panel_height: float
    panel_thickness: float
    frame_height: float
    lift_travel: float
    column_x: float
    name: str


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _choice(value: str | None, allowed: tuple[str, ...], fallback: str, field: str) -> str:
    if value is None:
        return fallback
    if value not in allowed:
        raise ValueError(f"Unsupported {field}: {value}")
    return value


def config_from_seed(seed: int) -> SluiceGateWithVerticalLiftPanelConfig:
    rng = random.Random(seed)
    return SluiceGateWithVerticalLiftPanelConfig(
        foundation_style=rng.choice(FOUNDATION_STYLES),
        frame_style=rng.choice(FRAME_STYLES),
        panel_style=rng.choice(PANEL_STYLES),
        lift_drive=rng.choice(LIFT_DRIVES),
        seal_style=rng.choice(SEAL_STYLES),
        counterweight_style=rng.choice(COUNTERWEIGHT_STYLES),
        opening_width_scale=round(rng.uniform(0.88, 1.18), 3),
        panel_height_scale=round(rng.uniform(0.88, 1.16), 3),
        lift_travel_scale=round(rng.uniform(0.84, 1.18), 3),
        material_style=rng.choice(MATERIAL_STYLES),
        name=f"seeded_sluice_gate_with_vertical_lift_panel_{seed}",
    )


def resolve_config(
    config: SluiceGateWithVerticalLiftPanelConfig,
) -> ResolvedSluiceGateWithVerticalLiftPanelConfig:
    foundation = _choice(
        config.foundation_style,
        FOUNDATION_STYLES,
        "plain_concrete_channel",
        "foundation_style",
    )
    frame = _choice(config.frame_style, FRAME_STYLES, "twin_u_channel", "frame_style")
    panel = _choice(config.panel_style, PANEL_STYLES, "ribbed_plate", "panel_style")
    drive = _choice(config.lift_drive, LIFT_DRIVES, "handwheel_screw", "lift_drive")
    seal = _choice(config.seal_style, SEAL_STYLES, "rubber_side_seals", "seal_style")
    counterweight = _choice(
        config.counterweight_style,
        COUNTERWEIGHT_STYLES,
        "none",
        "counterweight_style",
    )
    material = _choice(
        config.material_style, MATERIAL_STYLES, "weathered_concrete", "material_style"
    )

    opening_width = 1.18 * _clamp(config.opening_width_scale, 0.78, 1.28)
    panel_height = 1.08 * _clamp(config.panel_height_scale, 0.78, 1.24)
    lift_travel = 0.72 * _clamp(config.lift_travel_scale, 0.74, 1.28)
    frame_extra = 0.28 if drive == "overhead_winch" else 0.18
    if frame == "heavy_portal_frame":
        frame_extra += 0.08
    frame_height = panel_height + lift_travel + frame_extra
    panel_width = opening_width - 0.18
    channel_depth = 0.62 if foundation != "inspection_deck" else 0.70
    column_x = opening_width * 0.5 + 0.105
    return ResolvedSluiceGateWithVerticalLiftPanelConfig(
        foundation_style=foundation,
        frame_style=frame,
        panel_style=panel,
        lift_drive=drive,
        seal_style=seal,
        counterweight_style=counterweight,
        material_style=material,
        opening_width=opening_width,
        channel_depth=channel_depth,
        sill_height=0.070,
        panel_width=panel_width,
        panel_height=panel_height,
        panel_thickness=0.070,
        frame_height=frame_height,
        lift_travel=lift_travel,
        column_x=column_x,
        name=config.name or "sluice_gate_with_vertical_lift_panel",
    )


def with_overrides(
    config: SluiceGateWithVerticalLiftPanelConfig, **kwargs: object
) -> SluiceGateWithVerticalLiftPanelConfig:
    return replace(config, **kwargs)


def slot_choices_for_config(
    config: SluiceGateWithVerticalLiftPanelConfig | ResolvedSluiceGateWithVerticalLiftPanelConfig,
) -> tuple[tuple[str, str], ...]:
    r = (
        config
        if isinstance(config, ResolvedSluiceGateWithVerticalLiftPanelConfig)
        else resolve_config(config)
    )
    return (
        ("foundation", r.foundation_style),
        ("frame", r.frame_style),
        ("lift_panel", r.panel_style),
        ("lift_drive", r.lift_drive),
        ("guide_seal", r.seal_style),
        ("counterweight", r.counterweight_style),
        ("material_style", r.material_style),
    )


def slot_choices_for_seed(seed: int) -> tuple[tuple[str, str], ...]:
    return slot_choices_for_config(config_from_seed(seed))


def _mat(model: ArticulatedObject, r: ResolvedSluiceGateWithVerticalLiftPanelConfig, key: str):
    return model.material(f"sluice_{key}", rgba=PALETTES[r.material_style][key])


def _box(part, size, xyz, material, name, rpy=(0.0, 0.0, 0.0)) -> None:
    part.visual(Box(size), origin=Origin(xyz=xyz, rpy=rpy), material=material, name=name)


def _cyl(part, radius, length, xyz, material, name, rpy=(0.0, 0.0, 0.0)) -> None:
    part.visual(
        Cylinder(radius=radius, length=length),
        origin=Origin(xyz=xyz, rpy=rpy),
        material=material,
        name=name,
    )


def _build_fixed_frame(
    model: ArticulatedObject,
    r: ResolvedSluiceGateWithVerticalLiftPanelConfig,
    mats: dict[str, object],
):
    fixed = model.part("fixed_sluice_frame")
    total_width = r.opening_width + 0.48
    D = r.channel_depth
    _box(
        fixed, (total_width, D + 0.28, 0.050), (0.0, 0.0, 0.025), mats["concrete"], "concrete_apron"
    )
    _box(
        fixed,
        (r.opening_width + 0.30, D, 0.038),
        (0.0, 0.0, 0.046),
        mats["dark"],
        "recessed_water_channel",
    )
    _box(
        fixed,
        (r.opening_width - 0.16, D * 0.78, 0.012),
        (0.0, 0.0, 0.058),
        mats["water"],
        "upstream_water_plane",
    )
    _box(
        fixed,
        (r.opening_width - 0.10, 0.070, 0.060),
        (0.0, -D * 0.42, 0.090),
        mats["dark"],
        "downstream_sill_lip",
    )
    _box(
        fixed,
        (r.opening_width - 0.04, 0.085, 0.070),
        (0.0, 0.0, r.sill_height * 0.5),
        mats["metal"],
        "bottom_gate_sill",
    )
    if r.foundation_style == "flared_wing_wall":
        for side, label in ((-1, "left"), (1, "right")):
            _box(
                fixed,
                (0.16, D * 0.86, 0.42),
                (side * (r.opening_width * 0.5 + 0.27), 0.0, 0.230),
                mats["concrete"],
                f"{label}_flared_wing_wall",
                rpy=(0.0, 0.0, side * 0.16),
            )
    elif r.foundation_style == "inspection_deck":
        _box(
            fixed,
            (total_width + 0.18, 0.17, 0.040),
            (0.0, D * 0.48, 0.290),
            mats["metal"],
            "rear_inspection_deck",
        )
        for x in (-r.opening_width * 0.42, 0.0, r.opening_width * 0.42):
            _box(
                fixed,
                (0.035, 0.17, 0.250),
                (x, D * 0.48, 0.175),
                mats["metal"],
                f"deck_support_{x:.2f}",
            )
        for x in (-r.opening_width * 0.50, r.opening_width * 0.50):
            _box(
                fixed,
                (0.030, 0.025, 0.300),
                (x, D * 0.57, 0.460),
                mats["metal"],
                f"deck_guard_post_{x:.2f}",
            )
        _box(
            fixed,
            (r.opening_width + 0.25, 0.026, 0.040),
            (0.0, D * 0.57, 0.620),
            mats["metal"],
            "deck_guard_rail",
        )
    else:
        for x in (-r.opening_width * 0.40, r.opening_width * 0.40):
            _box(
                fixed,
                (0.075, 0.045, 0.050),
                (x, -D * 0.48, 0.090),
                mats["concrete"],
                f"front_anchor_block_{x:.2f}",
            )

    column_w = 0.125 if r.frame_style == "heavy_portal_frame" else 0.105
    column_d = 0.160 if r.frame_style != "twin_u_channel" else 0.130
    for side, label in ((-1, "left"), (1, "right")):
        x = side * r.column_x
        _box(
            fixed,
            (column_w, column_d, r.frame_height),
            (x, 0.0, r.frame_height * 0.5),
            mats["metal"],
            f"{label}_guide_column",
        )
        _box(
            fixed,
            (0.028, 0.072, r.panel_height + r.lift_travel * 0.72),
            (
                side * (r.opening_width * 0.5 - 0.020),
                -0.066,
                (r.panel_height + r.lift_travel * 0.72) * 0.5 + r.sill_height,
            ),
            mats["dark"],
            f"{label}_inner_guide_slot",
        )
        _box(
            fixed,
            (0.070, 0.050, 0.150),
            (x, 0.086, r.sill_height + 0.075),
            mats["dark"],
            f"{label}_heel_stop",
        )
        if r.frame_style == "braced_side_towers":
            _box(
                fixed,
                (0.046, 0.040, r.frame_height * 0.74),
                (x - side * 0.090, 0.063, r.frame_height * 0.46),
                mats["metal"],
                f"{label}_diagonal_tower_brace",
                rpy=(0.0, side * 0.20, 0.0),
            )
    top_depth = 0.180 if r.frame_style != "twin_u_channel" else 0.140
    _box(
        fixed,
        (r.opening_width + 0.42, top_depth, 0.085),
        (0.0, 0.0, r.frame_height + 0.0425),
        mats["metal"],
        "portal_top_crosshead",
    )
    if r.frame_style == "heavy_portal_frame":
        _box(
            fixed,
            (r.opening_width + 0.28, 0.055, 0.060),
            (0.0, -0.098, r.frame_height * 0.68),
            mats["metal"],
            "front_stiffener_beam",
        )
        _box(
            fixed,
            (r.opening_width + 0.28, 0.055, 0.060),
            (0.0, 0.098, r.frame_height * 0.68),
            mats["metal"],
            "rear_stiffener_beam",
        )
    if r.seal_style == "rubber_side_seals":
        for side, label in ((-1, "left"), (1, "right")):
            _box(
                fixed,
                (0.026, 0.030, r.panel_height * 0.88),
                (
                    side * (r.panel_width * 0.5 + 0.040),
                    -0.045,
                    r.sill_height + r.panel_height * 0.44,
                ),
                mats["dark"],
                f"{label}_rubber_side_seal",
            )
    elif r.seal_style == "brush_wipers":
        for side, label in ((-1, "left"), (1, "right")):
            for z in (0.26, 0.48, 0.70, 0.92):
                _box(
                    fixed,
                    (0.038, 0.018, 0.100),
                    (
                        side * (r.panel_width * 0.5 + 0.045),
                        -0.047,
                        r.sill_height + min(z, 0.96) * r.panel_height,
                    ),
                    mats["dark"],
                    f"{label}_brush_wiper_{z:.2f}",
                )
    if r.counterweight_style == "twin_counterweights":
        for side, label in ((-1, "left"), (1, "right")):
            x = side * (r.column_x + 0.180)
            _box(
                fixed,
                (0.150, 0.030, r.lift_travel + 0.520),
                (x, 0.190, r.frame_height - (r.lift_travel + 0.520) * 0.5 + 0.030),
                mats["dark"],
                f"{label}_counterweight_back_guide",
            )
            _box(
                fixed,
                (0.020, 0.080, r.lift_travel + 0.460),
                (x - side * 0.070, 0.150, r.frame_height - (r.lift_travel + 0.460) * 0.5),
                mats["metal"],
                f"{label}_counterweight_side_keeper",
            )
            _box(
                fixed,
                (0.170, 0.220, 0.040),
                (x, 0.145, r.frame_height + 0.050),
                mats["metal"],
                f"{label}_counterweight_top_bridge",
            )
    _build_lift_drive_details(fixed, r, mats)
    return fixed


def _build_lift_drive_details(
    fixed,
    r: ResolvedSluiceGateWithVerticalLiftPanelConfig,
    mats: dict[str, object],
) -> None:
    top_z = r.frame_height + 0.085
    if r.lift_drive == "handwheel_screw":
        _cyl(
            fixed,
            0.018,
            r.frame_height - r.sill_height + 0.12,
            (0.0, -0.140, r.frame_height * 0.50 + 0.060),
            mats["dark"],
            "vertical_lift_screw",
        )
        _cyl(
            fixed,
            0.125,
            0.020,
            (0.0, -0.168, top_z + 0.030),
            mats["accent"],
            "handwheel_ring",
            (math.pi / 2.0, 0.0, 0.0),
        )
        for angle in (0.0, math.pi / 2.0, math.pi, math.pi * 1.5):
            _box(
                fixed,
                (0.012, 0.018, 0.118),
                (math.cos(angle) * 0.040, -0.171, top_z + 0.030 + math.sin(angle) * 0.040),
                mats["accent"],
                f"handwheel_spoke_{angle:.2f}",
                rpy=(0.0, angle, 0.0),
            )
    elif r.lift_drive == "gearbox_chain":
        _box(
            fixed,
            (0.240, 0.155, 0.140),
            (0.0, -0.100, top_z + 0.025),
            mats["dark"],
            "chain_gearbox",
        )
        _cyl(
            fixed,
            0.014,
            r.opening_width * 0.64,
            (0.0, -0.120, top_z + 0.070),
            mats["metal"],
            "chain_sprocket_drive_shaft",
            (0.0, math.pi / 2.0, 0.0),
        )
        for side, label in ((-1, "left"), (1, "right")):
            x = side * (r.opening_width * 0.25)
            _cyl(
                fixed,
                0.038,
                0.034,
                (x, -0.120, top_z + 0.070),
                mats["metal"],
                f"{label}_chain_sprocket",
                (math.pi / 2.0, 0.0, 0.0),
            )
            chain_len = r.lift_travel + 0.42
            _box(
                fixed,
                (0.018, 0.018, chain_len),
                (x, -0.123, top_z + 0.032 - chain_len * 0.5),
                mats["dark"],
                f"{label}_hanging_chain_run",
            )
    else:
        _cyl(
            fixed,
            0.068,
            r.opening_width * 0.62,
            (0.0, -0.105, top_z + 0.040),
            mats["dark"],
            "winch_drum",
            (0.0, math.pi / 2.0, 0.0),
        )
        _box(
            fixed,
            (0.170, 0.110, 0.110),
            (r.opening_width * 0.40, -0.105, top_z + 0.040),
            mats["dark"],
            "winch_motor_box",
        )
        for x, label in ((-r.opening_width * 0.22, "left"), (r.opening_width * 0.22, "right")):
            cable_len = r.lift_travel + 0.32
            _box(
                fixed,
                (0.014, 0.014, cable_len),
                (x, -0.110, top_z - 0.028 - cable_len * 0.5),
                mats["metal"],
                f"{label}_lift_cable",
            )


def _build_lift_panel(
    model: ArticulatedObject,
    r: ResolvedSluiceGateWithVerticalLiftPanelConfig,
    mats: dict[str, object],
):
    panel = model.part("vertical_lift_panel")
    W, H, T = r.panel_width, r.panel_height, r.panel_thickness
    if r.panel_style == "open_grate_panel":
        _box(panel, (W, T, 0.060), (0.0, 0.0, 0.030), mats["panel"], "panel_bottom_rail")
        _box(panel, (W, T, 0.060), (0.0, 0.0, H - 0.030), mats["panel"], "panel_top_rail")
        for side, label in ((-1, "left"), (1, "right")):
            _box(
                panel,
                (0.065, T, H),
                (side * (W * 0.5 - 0.0325), 0.0, H * 0.5),
                mats["panel"],
                f"{label}_panel_stile",
            )
        for i, x in enumerate((-0.30, -0.10, 0.10, 0.30)):
            _box(
                panel,
                (0.035, T * 0.78, H - 0.120),
                (x * W, 0.0, H * 0.50),
                mats["panel"],
                f"grate_vertical_bar_{i}",
            )
        for i, z in enumerate((0.30, 0.50, 0.70)):
            _box(
                panel,
                (W * 0.82, T * 0.72, 0.030),
                (0.0, 0.0, H * z),
                mats["panel"],
                f"grate_crossbar_{i}",
            )
    else:
        _box(panel, (W, T, H), (0.0, 0.0, H * 0.5), mats["panel"], "solid_lift_plate")
        _box(
            panel,
            (W * 0.90, T + 0.010, 0.035),
            (0.0, -0.004, H - 0.060),
            mats["metal"],
            "top_pickup_bar",
        )
        if r.panel_style == "ribbed_plate":
            for i, x in enumerate((-0.36, -0.18, 0.0, 0.18, 0.36)):
                _box(
                    panel,
                    (0.038, T + 0.020, H * 0.82),
                    (x * W, -0.006, H * 0.48),
                    mats["metal"],
                    f"vertical_stiffening_rib_{i}",
                )
            for i, z in enumerate((0.24, 0.46, 0.68)):
                _box(
                    panel,
                    (W * 0.86, T + 0.016, 0.034),
                    (0.0, -0.006, z * H),
                    mats["metal"],
                    f"horizontal_stiffening_rib_{i}",
                )
        else:
            _box(
                panel,
                (W * 0.74, T + 0.012, 0.030),
                (0.0, -0.006, H * 0.50),
                mats["metal"],
                "center_wale",
            )
    for side, label in ((-1, "left"), (1, "right")):
        _box(
            panel,
            (0.030, 0.032, H * 0.93),
            (side * (W * 0.5 + 0.015), -0.018, H * 0.495),
            mats["dark"],
            f"{label}_edge_slide_shoe",
        )
    if r.seal_style == "bronze_slide_shoes":
        for side, label in ((-1, "left"), (1, "right")):
            for z in (0.22, 0.50, 0.78):
                _box(
                    panel,
                    (0.052, 0.042, 0.080),
                    (side * (W * 0.5 + 0.045), 0.010, H * z),
                    mats["accent"],
                    f"{label}_bronze_shoe_{z:.2f}",
                )
    _box(
        panel,
        (0.170, T + 0.028, 0.055),
        (0.0, -0.032, H + 0.010),
        mats["dark"],
        "central_lifting_lug",
    )
    return panel


def _build_counterweight(
    model: ArticulatedObject,
    r: ResolvedSluiceGateWithVerticalLiftPanelConfig,
    mats: dict[str, object],
    *,
    side: int,
):
    label = "left" if side < 0 else "right"
    cw = model.part(f"{label}_counterweight")
    _box(cw, (0.115, 0.105, 0.300), (0.0, -0.0525, 0.0), mats["dark"], "counterweight_block")
    _box(
        cw, (0.090, 0.020, 0.210), (0.0, -0.1125, 0.0), mats["accent"], "counterweight_front_stripe"
    )
    _cyl(
        cw,
        0.018,
        0.090,
        (0.0, -0.0525, 0.168),
        mats["metal"],
        "counterweight_top_pin",
        (math.pi / 2.0, 0.0, 0.0),
    )
    return cw


def build_sluice_gate_with_vertical_lift_panel(
    config: SluiceGateWithVerticalLiftPanelConfig | None = None,
    *,
    assets: AssetContext | None = None,
) -> ArticulatedObject:
    cfg = config or SluiceGateWithVerticalLiftPanelConfig()
    r = resolve_config(cfg)
    model = ArticulatedObject(name=r.name, assets=assets)
    mats = {
        key: _mat(model, r, key)
        for key in ("concrete", "metal", "panel", "dark", "accent", "water")
    }
    fixed = _build_fixed_frame(model, r, mats)
    panel = _build_lift_panel(model, r, mats)
    model.articulation(
        "panel_vertical_lift",
        ArticulationType.PRISMATIC,
        parent=fixed,
        child=panel,
        origin=Origin(xyz=(0.0, 0.0, r.sill_height)),
        axis=(0.0, 0.0, 1.0),
        motion_limits=MotionLimits(
            effort=80.0,
            velocity=0.55,
            lower=0.0,
            upper=r.lift_travel,
        ),
    )
    if r.counterweight_style == "twin_counterweights":
        top_origin_z = r.frame_height - 0.200
        for side in (-1, 1):
            cw = _build_counterweight(model, r, mats, side=side)
            model.articulation(
                f"{'left' if side < 0 else 'right'}_counterweight_slide",
                ArticulationType.PRISMATIC,
                parent=fixed,
                child=cw,
                origin=Origin(xyz=(side * (r.column_x + 0.180), 0.175, top_origin_z)),
                axis=(0.0, 0.0, -1.0),
                motion_limits=MotionLimits(
                    effort=28.0,
                    velocity=0.55,
                    lower=0.0,
                    upper=r.lift_travel * 0.72,
                ),
            )
    model.meta["slot_choices"] = slot_choices_for_config(r)
    return model


def build_seeded_sluice_gate_with_vertical_lift_panel(
    seed: int,
    *,
    assets: AssetContext | None = None,
) -> ArticulatedObject:
    return build_sluice_gate_with_vertical_lift_panel(config_from_seed(seed), assets=assets)


def run_sluice_gate_with_vertical_lift_panel_tests(
    object_model: ArticulatedObject,
    config: SluiceGateWithVerticalLiftPanelConfig,
) -> TestReport:
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
        "fixed_frame_present", "fixed_sluice_frame" in part_names, details=str(sorted(part_names))
    )
    ctx.check(
        "lift_panel_present", "vertical_lift_panel" in part_names, details=str(sorted(part_names))
    )
    lift = object_model.get_articulation("panel_vertical_lift")
    ctx.check(
        "panel_joint_prismatic",
        lift.articulation_type == ArticulationType.PRISMATIC,
        details=str(lift.articulation_type),
    )
    ctx.check("panel_joint_axis", tuple(lift.axis) == (0.0, 0.0, 1.0), details=str(lift.axis))
    ctx.check(
        "panel_travel_positive",
        lift.motion_limits.upper >= r.lift_travel * 0.98,
        details=str(lift.motion_limits),
    )
    counter_joints = [
        joint for joint in object_model.joints if joint.name.endswith("_counterweight_slide")
    ]
    expected_counter = 2 if r.counterweight_style == "twin_counterweights" else 0
    ctx.check(
        "counterweight_joint_count",
        len(counter_joints) == expected_counter,
        details=f"expected {expected_counter}, got {len(counter_joints)}",
    )
    for joint in counter_joints:
        ctx.check(
            f"{joint.name}_axis", tuple(joint.axis) == (0.0, 0.0, -1.0), details=str(joint.axis)
        )
    return ctx.report()


__all__ = [
    "SluiceGateWithVerticalLiftPanelConfig",
    "ResolvedSluiceGateWithVerticalLiftPanelConfig",
    "build_sluice_gate_with_vertical_lift_panel",
    "build_seeded_sluice_gate_with_vertical_lift_panel",
    "config_from_seed",
    "resolve_config",
    "run_sluice_gate_with_vertical_lift_panel_tests",
    "slot_choices_for_config",
    "slot_choices_for_seed",
    "with_overrides",
]
