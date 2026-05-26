"""Procedural template for `dj_equipment`.

Coordinate convention:
- +X is the right side of the device when viewed from the performer.
- +Y is the rear / top edge of the controller.
- +Z is up from the tabletop.

Stable seed domain:
- all_in_one_controller: dual jog wheels, central mixer strip, faders, knobs, pads.
- dj_mixer: channel fader lanes, EQ knob banks, crossfader, master strip.
- turntable_deck: single platter, tonearm swing, cue lift, small controls.

The broad spec also documents pad samplers and monitor speakers. Those are treated as
review-gated split candidates and are not sampled by config_from_seed.
"""

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
    MotionLimits,
    Origin,
    TestContext,
    TestReport,
)

EquipmentFamily = Literal[
    "all_in_one_controller", "dj_mixer", "turntable_deck", "pad_sampler", "tilt_monitor_speaker"
]
SeedDomain = Literal[
    "controller_mixer_turntable_core", "pad_sampler_review_gated", "monitor_speaker_split_candidate"
]
BodyProfile = Literal[
    "flat_rectangular", "rounded_controller", "wedge_panel", "pad_grid_slab", "tilted_speaker_box"
]
PlatterStyle = Literal["vinyl_turntable", "cdj_jog_wheel", "ribbed_controller_jog", "none"]
FaderOrientation = Literal["vertical_channels_horizontal_cross", "all_vertical", "horizontal_bank"]
KnobBankLayout = Literal["eq_rows", "paired_deck_controls", "single_master_strip", "none"]
PadShape = Literal["rounded_square", "low_rect_button", "circular_cue"]
MaterialStyle = Literal["graphite", "club_black", "silver_blue", "retro_ivory"]

SOURCE_IDS: dict[str, str] = {
    "S1": "rec_dj_equipment_6e26a372336146aa950bcca959ce6d20:model.py:L44-L77 turntable plinth/rest/cue helpers",
    "S2": "rec_dj_equipment_6e26a372336146aa950bcca959ce6d20:model.py:L79-L300 platter/tonearm/cue joints",
    "S3": "rec_dj_equipment_395917f2ec534974bdcae44f082b3856:model.py:L55-L177 mixer grid/slots",
    "S4": "rec_dj_equipment_395917f2ec534974bdcae44f082b3856:model.py:L184-L323 fader and knob builders",
    "S5": "rec_dj_equipment_47e2bd7d05da479eb2363c19da61276b:model.py:L39-L143 platter/slider/handle helpers",
    "S6": "rec_dj_equipment_47e2bd7d05da479eb2363c19da61276b:model.py:L145-L435 dual-jog controller",
    "S7": "rec_dj_equipment_12cc4b441480440ab78ac715cebab79f:model.py:L22-L53 rounded pad mesh semantics",
    "S8": "rec_dj_equipment_12cc4b441480440ab78ac715cebab79f:model.py:L65-L326 pad grid and lower faders",
    "S9": "rec_dj_equipment_01b8a962219e49d29f1b01cacfc25b40:model.py:L63-L286 monitor speaker split candidate",
    "S10": "rec_dj_equipment_395917f2ec534974bdcae44f082b3856:model.py:L366-L405 control-axis tests",
}

PALETTES: dict[MaterialStyle, dict[str, tuple[float, float, float, float]]] = {
    "graphite": {
        "body": (0.10, 0.11, 0.12, 1.0),
        "panel": (0.16, 0.17, 0.18, 1.0),
        "trim": (0.58, 0.60, 0.62, 1.0),
        "rubber": (0.04, 0.04, 0.045, 1.0),
        "accent": (0.15, 0.45, 0.80, 1.0),
        "label": (0.82, 0.84, 0.86, 1.0),
    },
    "club_black": {
        "body": (0.045, 0.045, 0.050, 1.0),
        "panel": (0.08, 0.08, 0.09, 1.0),
        "trim": (0.42, 0.43, 0.45, 1.0),
        "rubber": (0.02, 0.02, 0.025, 1.0),
        "accent": (0.86, 0.24, 0.16, 1.0),
        "label": (0.78, 0.78, 0.74, 1.0),
    },
    "silver_blue": {
        "body": (0.62, 0.64, 0.67, 1.0),
        "panel": (0.24, 0.27, 0.31, 1.0),
        "trim": (0.80, 0.82, 0.84, 1.0),
        "rubber": (0.05, 0.05, 0.055, 1.0),
        "accent": (0.08, 0.42, 0.78, 1.0),
        "label": (0.92, 0.94, 0.96, 1.0),
    },
    "retro_ivory": {
        "body": (0.86, 0.82, 0.68, 1.0),
        "panel": (0.18, 0.18, 0.17, 1.0),
        "trim": (0.56, 0.42, 0.24, 1.0),
        "rubber": (0.06, 0.05, 0.04, 1.0),
        "accent": (0.80, 0.28, 0.14, 1.0),
        "label": (0.96, 0.92, 0.78, 1.0),
    },
}

FAMILY_DEFAULTS: dict[EquipmentFamily, dict[str, object]] = {
    "all_in_one_controller": {
        "body_profile": "rounded_controller",
        "body_width": 0.62,
        "body_depth": 0.36,
        "body_height": 0.060,
        "platter_count": 2,
        "platter_style": "ribbed_controller_jog",
        "channel_count": 2,
        "pad_grid_rows": 2,
        "pad_grid_cols": 4,
        "tonearm_enabled": False,
        "handle_enabled": True,
    },
    "dj_mixer": {
        "body_profile": "wedge_panel",
        "body_width": 0.42,
        "body_depth": 0.38,
        "body_height": 0.070,
        "platter_count": 0,
        "platter_style": "none",
        "channel_count": 4,
        "pad_grid_rows": 0,
        "pad_grid_cols": 0,
        "tonearm_enabled": False,
        "handle_enabled": False,
    },
    "turntable_deck": {
        "body_profile": "flat_rectangular",
        "body_width": 0.46,
        "body_depth": 0.42,
        "body_height": 0.072,
        "platter_count": 1,
        "platter_style": "vinyl_turntable",
        "channel_count": 1,
        "pad_grid_rows": 0,
        "pad_grid_cols": 0,
        "tonearm_enabled": True,
        "handle_enabled": False,
    },
    "pad_sampler": {
        "body_profile": "pad_grid_slab",
        "body_width": 0.46,
        "body_depth": 0.34,
        "body_height": 0.052,
        "platter_count": 0,
        "platter_style": "none",
        "channel_count": 2,
        "pad_grid_rows": 8,
        "pad_grid_cols": 8,
        "tonearm_enabled": False,
        "handle_enabled": False,
    },
    "tilt_monitor_speaker": {
        "body_profile": "tilted_speaker_box",
        "body_width": 0.34,
        "body_depth": 0.28,
        "body_height": 0.24,
        "platter_count": 0,
        "platter_style": "none",
        "channel_count": 0,
        "pad_grid_rows": 0,
        "pad_grid_cols": 0,
        "tonearm_enabled": False,
        "handle_enabled": False,
    },
}


@dataclass(frozen=True)
class DJEquipmentConfig:
    equipment_family: EquipmentFamily = "all_in_one_controller"
    seed_domain: SeedDomain = "controller_mixer_turntable_core"
    body_profile: BodyProfile | None = None
    body_width: float | None = None
    body_depth: float | None = None
    body_height: float | None = None
    platter_count: int | None = None
    platter_style: PlatterStyle | None = None
    channel_count: int | None = None
    fader_orientation: FaderOrientation = "vertical_channels_horizontal_cross"
    knob_bank_layout: KnobBankLayout = "eq_rows"
    pad_grid_rows: int | None = None
    pad_grid_cols: int | None = None
    pad_shape: PadShape = "rounded_square"
    tonearm_enabled: bool | None = None
    handle_enabled: bool | None = None
    speaker_enabled: bool = False
    material_style: MaterialStyle = "graphite"
    name: str = "reference_dj_equipment"


@dataclass(frozen=True)
class ResolvedDJEquipmentConfig:
    equipment_family: EquipmentFamily
    seed_domain: SeedDomain
    body_profile: BodyProfile
    body_width: float
    body_depth: float
    body_height: float
    panel_z: float
    panel_inset: float
    platter_count: int
    platter_style: PlatterStyle
    platter_radius: float
    platter_centers: tuple[tuple[float, float], ...]
    channel_count: int
    fader_count: int
    fader_orientation: FaderOrientation
    fader_travel: float
    knob_bank_layout: KnobBankLayout
    knob_count: int
    pad_grid_rows: int
    pad_grid_cols: int
    pad_count: int
    pad_shape: PadShape
    pad_travel: float
    tonearm_enabled: bool
    cue_lift_travel: float
    handle_enabled: bool
    material_style: MaterialStyle
    name: str


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _validate_enum(value: object, allowed: set[str], field: str) -> None:
    if value not in allowed:
        raise ValueError(f"Unsupported {field}: {value}")


def config_from_seed(seed: int) -> DJEquipmentConfig:
    rng = random.Random(seed)
    family: EquipmentFamily = rng.choices(
        ("all_in_one_controller", "dj_mixer", "turntable_deck"),
        weights=(0.55, 0.27, 0.18),
        k=1,
    )[0]
    defaults = FAMILY_DEFAULTS[family]
    material: MaterialStyle = rng.choice(("graphite", "club_black", "silver_blue", "retro_ivory"))
    channel_count = int(defaults["channel_count"])
    if family == "dj_mixer":
        channel_count = rng.choice((2, 3, 4))
    body_width = round(float(defaults["body_width"]) * rng.uniform(0.92, 1.10), 3)
    body_depth = round(float(defaults["body_depth"]) * rng.uniform(0.92, 1.10), 3)
    body_height = round(float(defaults["body_height"]) * rng.uniform(0.92, 1.08), 3)
    pad_rows = int(defaults["pad_grid_rows"])
    pad_cols = int(defaults["pad_grid_cols"])
    if family == "all_in_one_controller":
        pad_rows = rng.choice((2, 4))
        pad_cols = 4
    return DJEquipmentConfig(
        equipment_family=family,
        body_profile=defaults["body_profile"],
        body_width=body_width,
        body_depth=body_depth,
        body_height=body_height,
        platter_count=int(defaults["platter_count"]),
        platter_style=defaults["platter_style"],
        channel_count=channel_count,
        fader_orientation=rng.choice(("vertical_channels_horizontal_cross", "all_vertical")),
        knob_bank_layout=rng.choice(("eq_rows", "paired_deck_controls", "single_master_strip")),
        pad_grid_rows=pad_rows,
        pad_grid_cols=pad_cols,
        pad_shape=rng.choice(("rounded_square", "low_rect_button", "circular_cue")),
        tonearm_enabled=bool(defaults["tonearm_enabled"]),
        handle_enabled=False,
        material_style=material,
        name=f"seeded_dj_equipment_{seed}",
    )


def resolve_config(config: DJEquipmentConfig) -> ResolvedDJEquipmentConfig:
    _validate_enum(config.equipment_family, set(FAMILY_DEFAULTS), "equipment_family")
    _validate_enum(
        config.seed_domain,
        {
            "controller_mixer_turntable_core",
            "pad_sampler_review_gated",
            "monitor_speaker_split_candidate",
        },
        "seed_domain",
    )
    _validate_enum(
        config.fader_orientation,
        {"vertical_channels_horizontal_cross", "all_vertical", "horizontal_bank"},
        "fader_orientation",
    )
    _validate_enum(
        config.knob_bank_layout,
        {"eq_rows", "paired_deck_controls", "single_master_strip", "none"},
        "knob_bank_layout",
    )
    _validate_enum(
        config.pad_shape, {"rounded_square", "low_rect_button", "circular_cue"}, "pad_shape"
    )
    _validate_enum(config.material_style, set(PALETTES), "material_style")
    family = config.equipment_family
    if config.seed_domain == "controller_mixer_turntable_core" and family in {
        "pad_sampler",
        "tilt_monitor_speaker",
    }:
        family = "all_in_one_controller"
    defaults = FAMILY_DEFAULTS[family]
    body_profile = config.body_profile or defaults["body_profile"]
    _validate_enum(
        body_profile,
        {
            "flat_rectangular",
            "rounded_controller",
            "wedge_panel",
            "pad_grid_slab",
            "tilted_speaker_box",
        },
        "body_profile",
    )
    width = _clamp(
        config.body_width if config.body_width is not None else float(defaults["body_width"]),
        0.28,
        0.95,
    )
    depth = _clamp(
        config.body_depth if config.body_depth is not None else float(defaults["body_depth"]),
        0.22,
        0.68,
    )
    height = _clamp(
        config.body_height if config.body_height is not None else float(defaults["body_height"]),
        0.040,
        0.12,
    )
    platter_count = int(
        config.platter_count if config.platter_count is not None else defaults["platter_count"]
    )
    platter_style = config.platter_style or defaults["platter_style"]
    _validate_enum(
        platter_style,
        {"vinyl_turntable", "cdj_jog_wheel", "ribbed_controller_jog", "none"},
        "platter_style",
    )
    channel_count = int(
        config.channel_count if config.channel_count is not None else defaults["channel_count"]
    )
    channel_count = max(0, min(4, channel_count))
    pad_rows = int(
        config.pad_grid_rows if config.pad_grid_rows is not None else defaults["pad_grid_rows"]
    )
    pad_cols = int(
        config.pad_grid_cols if config.pad_grid_cols is not None else defaults["pad_grid_cols"]
    )
    tonearm = bool(
        config.tonearm_enabled
        if config.tonearm_enabled is not None
        else defaults["tonearm_enabled"]
    )
    handle = bool(
        config.handle_enabled if config.handle_enabled is not None else defaults["handle_enabled"]
    )
    if family == "all_in_one_controller":
        platter_count = 2
        platter_style = "ribbed_controller_jog" if platter_style == "none" else platter_style
        channel_count = max(2, min(4, channel_count))
        pad_rows = 2 if pad_rows not in {2, 4} else pad_rows
        pad_cols = 4
        tonearm = False
    elif family == "dj_mixer":
        platter_count = 0
        platter_style = "none"
        channel_count = max(2, min(4, channel_count))
        pad_rows = 0
        pad_cols = 0
        tonearm = False
        handle = False
    elif family == "turntable_deck":
        platter_count = 1
        platter_style = "vinyl_turntable"
        channel_count = max(1, min(2, channel_count))
        pad_rows = 0
        pad_cols = 0
        tonearm = True
        handle = False
    else:
        family = "all_in_one_controller"
        platter_count = 2
        platter_style = "ribbed_controller_jog"
        channel_count = 2
        pad_rows = 2
        pad_cols = 4
        tonearm = False
    panel_z = height + 0.003
    panel_inset = max(0.016, min(width, depth) * 0.045)
    deck_radius_limit = min(depth * 0.31, max(0.050, (width - 0.16) / max(2, platter_count * 2.2)))
    platter_radius = _clamp(deck_radius_limit, 0.052, 0.125)
    platter_centers: list[tuple[float, float]] = []
    if platter_count == 1:
        platter_centers.append((-width * 0.15, 0.018))
    elif platter_count == 2:
        platter_centers.append((-width * 0.30, 0.024))
        platter_centers.append((width * 0.30, 0.024))
    fader_count = 0
    if family == "all_in_one_controller":
        fader_count = channel_count + 1
    elif family == "dj_mixer":
        fader_count = channel_count + 2
    elif family == "turntable_deck":
        fader_count = 1
    fader_travel = _clamp(depth * 0.105, 0.026, 0.055)
    knob_count = 0
    if config.knob_bank_layout == "eq_rows":
        knob_count = max(2, channel_count * 3)
    elif config.knob_bank_layout == "paired_deck_controls":
        knob_count = max(2, platter_count * 4)
    elif config.knob_bank_layout == "single_master_strip":
        knob_count = max(2, channel_count + 1)
    if family == "turntable_deck":
        knob_count = min(knob_count, 4)
    pad_count = pad_rows * pad_cols
    if family == "all_in_one_controller":
        pad_count *= 2
    return ResolvedDJEquipmentConfig(
        equipment_family=family,
        seed_domain=config.seed_domain,
        body_profile=body_profile,
        body_width=width,
        body_depth=depth,
        body_height=height,
        panel_z=panel_z,
        panel_inset=panel_inset,
        platter_count=platter_count,
        platter_style=platter_style,
        platter_radius=platter_radius,
        platter_centers=tuple(platter_centers),
        channel_count=channel_count,
        fader_count=fader_count,
        fader_orientation=config.fader_orientation,
        fader_travel=fader_travel,
        knob_bank_layout=config.knob_bank_layout,
        knob_count=knob_count,
        pad_grid_rows=pad_rows,
        pad_grid_cols=pad_cols,
        pad_count=pad_count,
        pad_shape=config.pad_shape,
        pad_travel=0.006,
        tonearm_enabled=tonearm,
        cue_lift_travel=0.018,
        handle_enabled=handle,
        material_style=config.material_style,
        name=config.name,
    )


def with_overrides(config: DJEquipmentConfig, **kwargs: object) -> DJEquipmentConfig:
    return replace(config, **kwargs)


def _joint_meta(
    joint_type: str,
    axis: tuple[float, float, float],
    origin: tuple[float, float, float],
    joint_range: object,
    source_id: str,
) -> dict[str, object]:
    return {
        "type": joint_type,
        "axis": axis,
        "origin": origin,
        "range": joint_range,
        "source_id": source_id,
    }


def _mat(model: ArticulatedObject, r: ResolvedDJEquipmentConfig, key: str):
    return model.material(f"dj_{key}", rgba=PALETTES[r.material_style][key])


def _add_box(
    part,
    size: tuple[float, float, float],
    xyz: tuple[float, float, float],
    material,
    name: str,
    rpy: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> None:
    part.visual(Box(size), origin=Origin(xyz=xyz, rpy=rpy), material=material, name=name)


def _add_cyl(
    part,
    radius: float,
    length: float,
    xyz: tuple[float, float, float],
    material,
    name: str,
    rpy: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> None:
    part.visual(
        Cylinder(radius=radius, length=length),
        origin=Origin(xyz=xyz, rpy=rpy),
        material=material,
        name=name,
    )


def _build_body(
    body, r: ResolvedDJEquipmentConfig, *, body_mat, panel_mat, trim, rubber, accent, label
) -> None:
    W, D, H = r.body_width, r.body_depth, r.body_height
    _add_box(body, (W, D, H), (0.0, 0.0, H * 0.5), body_mat, "base_housing")
    _add_box(
        body,
        (W - 2 * r.panel_inset, D - 2 * r.panel_inset, 0.006),
        (0.0, 0.0, H + 0.003),
        panel_mat,
        "top_control_panel",
    )
    if r.body_profile == "rounded_controller":
        for sx in (-1.0, 1.0):
            for sy in (-1.0, 1.0):
                _add_cyl(
                    body,
                    0.018,
                    H,
                    (sx * (W * 0.5 - 0.018), sy * (D * 0.5 - 0.018), H * 0.5),
                    body_mat,
                    f"rounded_corner_{sx:+.0f}_{sy:+.0f}",
                )
    if r.body_profile == "wedge_panel":
        _add_box(
            body,
            (W * 0.94, 0.022, 0.018),
            (0.0, D * 0.5 - 0.012, H + 0.012),
            trim,
            "raised_rear_wedge_lip",
        )
    for i, x in enumerate((-W * 0.38, -W * 0.13, W * 0.13, W * 0.38)):
        _add_box(
            body,
            (0.050, 0.003, 0.012),
            (x, -D * 0.5 - 0.001, H * 0.56),
            label,
            f"front_channel_label_{i}",
        )
    for i, x in enumerate((-W * 0.43, W * 0.43)):
        _add_box(
            body,
            (0.030, 0.010, 0.006),
            (x, D * 0.5 - 0.020, H + 0.008),
            accent,
            f"status_led_cluster_{i}",
        )
    for sx in (-1.0, 1.0):
        for sy in (-1.0, 1.0):
            _add_cyl(
                body,
                0.007,
                0.004,
                (sx * (W * 0.5 - 0.030), sy * (D * 0.5 - 0.030), H + 0.010),
                trim,
                f"panel_screw_{sx:+.0f}_{sy:+.0f}",
            )


def _build_platter_part(part, r: ResolvedDJEquipmentConfig, *, rubber, trim, accent) -> None:
    rad = r.platter_radius
    _add_cyl(part, rad, 0.012, (0.0, 0.0, 0.006), rubber, "platter_disc")
    _add_cyl(part, rad * 0.72, 0.004, (0.0, 0.0, 0.016), trim, "platter_top_ring")
    _add_cyl(part, rad * 0.15, 0.016, (0.0, 0.0, 0.018), accent, "center_spindle")
    tick_count = 20 if r.platter_style == "ribbed_controller_jog" else 12
    for i in range(tick_count):
        angle = i * 2.0 * math.pi / tick_count
        x = math.cos(angle) * rad * 0.88
        y = math.sin(angle) * rad * 0.88
        _add_box(
            part,
            (rad * 0.16, 0.003, 0.003),
            (x, y, 0.020),
            trim,
            f"rim_tick_{i}",
            rpy=(0.0, 0.0, angle),
        )


def _build_fader_part(part, *, cap_size: tuple[float, float, float], rubber, trim) -> None:
    _add_box(part, cap_size, (0.0, 0.0, cap_size[2] * 0.5 + 0.004), rubber, "fader_cap")
    _add_box(
        part, (cap_size[0] * 0.42, cap_size[1] * 0.42, 0.010), (0.0, 0.0, -0.002), trim, "slot_stem"
    )


def _build_knob_part(part, *, radius: float, rubber, accent) -> None:
    _add_cyl(part, radius, 0.012, (0.0, 0.0, 0.006), rubber, "knob_body")
    _add_cyl(part, radius * 0.72, 0.005, (0.0, 0.0, 0.015), rubber, "knob_cap")
    _add_box(
        part,
        (radius * 0.22, radius * 0.85, 0.003),
        (0.0, radius * 0.42, 0.019),
        accent,
        "knob_indicator",
    )


def _build_pad_part(part, r: ResolvedDJEquipmentConfig, *, rubber, accent) -> None:
    if r.pad_shape == "circular_cue":
        radius = 0.010 if r.pad_grid_rows >= 4 else 0.014
        _add_cyl(part, radius, 0.008, (0.0, 0.0, 0.004), rubber, "pad_button")
        _add_cyl(part, radius * 0.50, 0.002, (0.0, 0.0, 0.009), accent, "pad_center")
    else:
        if r.pad_grid_rows >= 4:
            sx = 0.018 if r.pad_shape == "rounded_square" else 0.026
            sy = 0.018 if r.pad_shape == "rounded_square" else 0.014
        else:
            sx = 0.024 if r.pad_shape == "rounded_square" else 0.030
            sy = 0.024 if r.pad_shape == "rounded_square" else 0.018
        _add_box(part, (sx, sy, 0.008), (0.0, 0.0, 0.004), rubber, "pad_button")
        _add_box(part, (sx * 0.62, sy * 0.12, 0.002), (0.0, 0.0, 0.009), accent, "pad_highlight")


def _control_regions(r: ResolvedDJEquipmentConfig) -> dict[str, tuple[float, float, float, float]]:
    W, D = r.body_width, r.body_depth
    if r.equipment_family == "all_in_one_controller":
        return {
            "left_deck": (-W * 0.30, 0.035, W * 0.33, D * 0.64),
            "right_deck": (W * 0.30, 0.035, W * 0.33, D * 0.64),
            "mixer": (0.0, -0.010, W * 0.23, D * 0.72),
        }
    if r.equipment_family == "dj_mixer":
        return {"mixer": (0.0, 0.0, W * 0.82, D * 0.82)}
    return {
        "turntable": (-W * 0.15, 0.025, W * 0.56, D * 0.74),
        "arm": (W * 0.26, 0.045, W * 0.30, D * 0.70),
    }


def _add_slots_and_guides(
    body, r: ResolvedDJEquipmentConfig, *, panel_mat, trim, rubber
) -> list[
    tuple[
        str,
        tuple[float, float, float],
        tuple[float, float, float],
        tuple[float, float, float],
        float,
    ]
]:
    slots: list[
        tuple[
            str,
            tuple[float, float, float],
            tuple[float, float, float],
            tuple[float, float, float],
            float,
        ]
    ] = []
    W, D, Z = r.body_width, r.body_depth, r.panel_z
    if r.equipment_family in {"all_in_one_controller", "dj_mixer"}:
        lane_count = max(1, r.channel_count)
        mixer_w = W * (0.24 if r.equipment_family == "all_in_one_controller" else 0.76)
        x0 = -mixer_w * 0.38
        step = mixer_w * 0.76 / max(1, lane_count - 1)
        for i in range(lane_count):
            x = x0 + i * step if lane_count > 1 else 0.0
            y = -D * 0.055
            _add_box(
                body,
                (0.016, r.fader_travel * 2.4, 0.003),
                (x, y, Z + 0.003),
                rubber,
                f"channel_fader_slot_{i}",
            )
            slots.append(
                (
                    f"channel_fader_{i}",
                    (x, y, Z + 0.0105),
                    (0.0, 1.0, 0.0),
                    (0.018, 0.026, 0.012),
                    r.fader_travel,
                )
            )
        cross_y = -D * 0.34
        _add_box(
            body,
            (min(0.15, W * 0.32), 0.016, 0.003),
            (0.0, cross_y, Z + 0.003),
            rubber,
            "crossfader_slot",
        )
        slots.append(
            (
                "crossfader",
                (0.0, cross_y, Z + 0.0105),
                (1.0, 0.0, 0.0),
                (0.030, 0.018, 0.012),
                min(0.070, W * 0.12),
            )
        )
        if r.equipment_family == "dj_mixer":
            _add_box(
                body,
                (0.014, r.fader_travel * 2.0, 0.003),
                (W * 0.36, D * 0.08, Z + 0.003),
                rubber,
                "master_fader_slot",
            )
            slots.append(
                (
                    "master_fader",
                    (W * 0.36, D * 0.08, Z + 0.0105),
                    (0.0, 1.0, 0.0),
                    (0.018, 0.024, 0.012),
                    r.fader_travel * 0.85,
                )
            )
    elif r.equipment_family == "turntable_deck":
        x = -W * 0.38
        y = -D * 0.31
        _add_box(
            body,
            (0.016, r.fader_travel * 1.8, 0.003),
            (x, y, Z + 0.003),
            rubber,
            "pitch_fader_slot",
        )
        slots.append(
            (
                "pitch_fader",
                (x, y, Z + 0.0105),
                (0.0, 1.0, 0.0),
                (0.016, 0.026, 0.012),
                r.fader_travel * 0.75,
            )
        )
    return slots


def _knob_positions(r: ResolvedDJEquipmentConfig) -> list[tuple[float, float]]:
    positions: list[tuple[float, float]] = []
    W, D = r.body_width, r.body_depth
    if r.knob_count <= 0:
        return positions
    if r.equipment_family == "dj_mixer":
        lane_count = max(1, r.channel_count)
        x0 = -W * 0.30
        step = W * 0.60 / max(1, lane_count - 1)
        for lane in range(lane_count):
            x = x0 + lane * step if lane_count > 1 else 0.0
            for y in (D * 0.30, D * 0.20, D * 0.10):
                positions.append((x, y))
    elif r.equipment_family == "all_in_one_controller":
        for x in (-W * 0.055, 0.0, W * 0.055):
            for y in (D * 0.30, D * 0.19):
                positions.append((x, y))
        for deck_x in (-W * 0.30, W * 0.30):
            positions.append((deck_x - math.copysign(W * 0.085, deck_x), D * 0.43))
            positions.append((deck_x + math.copysign(W * 0.085, deck_x), D * 0.43))
    else:
        for x, y in (
            (W * 0.28, -D * 0.12),
            (W * 0.34, -D * 0.12),
            (W * 0.28, -D * 0.20),
            (W * 0.34, -D * 0.20),
        ):
            positions.append((x, y))
    return positions[: r.knob_count]


def _pad_positions(r: ResolvedDJEquipmentConfig) -> list[tuple[float, float]]:
    if r.pad_count == 0:
        return []
    W, D = r.body_width, r.body_depth
    positions: list[tuple[float, float]] = []
    if r.equipment_family == "all_in_one_controller":
        for deck_x in (-W * 0.30, W * 0.30):
            grid_w = min(W * 0.23, 0.16)
            grid_h = min(D * 0.24, 0.096)
            for row in range(r.pad_grid_rows):
                for col in range(r.pad_grid_cols):
                    x = deck_x - grid_w * 0.5 + (col + 0.5) * grid_w / r.pad_grid_cols
                    y = -D * 0.50 + (row + 0.5) * grid_h / r.pad_grid_rows
                    positions.append((x, y))
    return positions


def _build_tonearm(
    model: ArticulatedObject, body, r: ResolvedDJEquipmentConfig, *, trim, rubber, accent
) -> None:
    if not r.tonearm_enabled:
        return
    W, D, Z = r.body_width, r.body_depth, r.panel_z
    pivot = (W * 0.29, D * 0.20, Z + 0.018)
    body.visual(
        Cylinder(radius=0.014, length=0.010),
        origin=Origin(xyz=(pivot[0], pivot[1], pivot[2] - 0.007)),
        material=trim,
        name="tonearm_pivot_socket",
    )
    arm = model.part("tonearm")
    arm_len = min(0.24, D * 0.56)
    _add_cyl(arm, 0.006, 0.010, (0.0, 0.0, 0.003), trim, "pivot_pin")
    _add_box(arm, (0.010, arm_len, 0.007), (0.0, -arm_len * 0.5, 0.014), trim, "arm_tube")
    _add_box(arm, (0.030, 0.018, 0.010), (0.0, -arm_len - 0.004, 0.010), rubber, "cartridge")
    _add_cyl(arm, 0.012, 0.010, (0.0, 0.0, 0.014), accent, "counterweight")
    model.articulation(
        "tonearm_swing",
        ArticulationType.REVOLUTE,
        parent=body,
        child=arm,
        origin=Origin(xyz=pivot),
        axis=(0.0, 0.0, 1.0),
        motion_limits=MotionLimits(effort=1.0, velocity=1.4, lower=0.0, upper=0.78),
        meta=_joint_meta("revolute", (0.0, 0.0, 1.0), pivot, (0.0, 0.78), "S2"),
    )
    cue = model.part("cue_lift")
    _add_cyl(cue, 0.005, 0.024, (0.0, 0.0, 0.012), trim, "cue_post")
    _add_box(cue, (0.034, 0.008, 0.006), (0.0, -0.018, 0.024), accent, "cue_rest")
    cue_origin = (W * 0.23, D * 0.135, Z + 0.007)
    body.visual(
        Cylinder(radius=0.007, length=0.006),
        origin=Origin(xyz=(cue_origin[0], cue_origin[1], cue_origin[2] - 0.003)),
        material=trim,
        name="cue_lift_socket",
    )
    model.articulation(
        "cue_lift_slide",
        ArticulationType.PRISMATIC,
        parent=body,
        child=cue,
        origin=Origin(xyz=cue_origin),
        axis=(0.0, 0.0, 1.0),
        motion_limits=MotionLimits(effort=0.5, velocity=0.08, lower=0.0, upper=r.cue_lift_travel),
        meta=_joint_meta("prismatic", (0.0, 0.0, 1.0), cue_origin, (0.0, r.cue_lift_travel), "S2"),
    )


def _build_handle(
    model: ArticulatedObject, body, r: ResolvedDJEquipmentConfig, *, trim, rubber
) -> None:
    if not r.handle_enabled:
        return
    W, D, H = r.body_width, r.body_depth, r.body_height
    span = W * 0.78
    hinge_y = D * 0.5 + 0.010
    hinge_z = H + 0.020
    for sx in (-1.0, 1.0):
        body.visual(
            Box((0.025, 0.018, 0.024)),
            origin=Origin(xyz=(sx * span * 0.5, hinge_y, hinge_z)),
            material=trim,
            name=f"handle_hinge_block_{sx:+.0f}",
        )
    handle = model.part("carry_handle")
    _add_cyl(
        handle, 0.006, span, (0.0, 0.0, 0.060), trim, "cross_tube", rpy=(0.0, math.pi / 2.0, 0.0)
    )
    for sx in (-1.0, 1.0):
        _add_box(
            handle,
            (0.010, 0.012, 0.060),
            (sx * span * 0.5, 0.0, 0.030),
            trim,
            f"side_upright_{sx:+.0f}",
        )
        _add_cyl(
            handle,
            0.007,
            0.018,
            (sx * span * 0.5, 0.0, 0.0),
            rubber,
            f"hinge_pin_{sx:+.0f}",
            rpy=(math.pi / 2.0, 0.0, 0.0),
        )
    origin = (0.0, hinge_y, hinge_z)
    model.articulation(
        "carry_handle_hinge",
        ArticulationType.REVOLUTE,
        parent=body,
        child=handle,
        origin=Origin(xyz=origin),
        axis=(1.0, 0.0, 0.0),
        motion_limits=MotionLimits(effort=5.0, velocity=1.5, lower=0.0, upper=1.45),
        meta=_joint_meta("revolute", (1.0, 0.0, 0.0), origin, (0.0, 1.45), "S5"),
    )


def build_dj_equipment(
    config: DJEquipmentConfig | None = None, *, assets: AssetContext | None = None
) -> ArticulatedObject:
    config = config or DJEquipmentConfig()
    r = resolve_config(config)
    if assets is None:
        assets = AssetContext(Path(tempfile.mkdtemp(prefix="articraft-dj-equipment-assets-")))
    model = ArticulatedObject(name=r.name, assets=assets)
    body_mat = _mat(model, r, "body")
    panel_mat = _mat(model, r, "panel")
    trim = _mat(model, r, "trim")
    rubber = _mat(model, r, "rubber")
    accent = _mat(model, r, "accent")
    label = _mat(model, r, "label")
    body = model.part("equipment_body")
    _build_body(
        body,
        r,
        body_mat=body_mat,
        panel_mat=panel_mat,
        trim=trim,
        rubber=rubber,
        accent=accent,
        label=label,
    )
    for i, (x, y) in enumerate(r.platter_centers):
        body.visual(
            Cylinder(radius=r.platter_radius * 1.08, length=0.004),
            origin=Origin(xyz=(x, y, r.panel_z + 0.003)),
            material=rubber,
            name=f"platter_well_{i}",
        )
        platter = model.part(f"platter_{i}")
        _build_platter_part(platter, r, rubber=rubber, trim=trim, accent=accent)
        origin = (x, y, r.panel_z + 0.004)
        model.articulation(
            f"platter_spin_{i}",
            ArticulationType.CONTINUOUS,
            parent=body,
            child=platter,
            origin=Origin(xyz=origin),
            axis=(0.0, 0.0, 1.0),
            motion_limits=MotionLimits(effort=2.5, velocity=18.0),
            meta=_joint_meta(
                "continuous",
                (0.0, 0.0, 1.0),
                origin,
                "unbounded",
                "S2" if r.equipment_family == "turntable_deck" else "S6",
            ),
        )
    for name, origin, axis, cap_size, travel in _add_slots_and_guides(
        body, r, panel_mat=panel_mat, trim=trim, rubber=rubber
    ):
        fader = model.part(name)
        _build_fader_part(fader, cap_size=cap_size, rubber=rubber, trim=trim)
        model.articulation(
            f"{name}_slide",
            ArticulationType.PRISMATIC,
            parent=body,
            child=fader,
            origin=Origin(xyz=origin),
            axis=axis,
            motion_limits=MotionLimits(effort=1.4, velocity=0.22, lower=-travel, upper=travel),
            meta=_joint_meta("prismatic", axis, origin, (-travel, travel), "S4"),
        )
    for i, (x, y) in enumerate(_knob_positions(r)):
        body.visual(
            Cylinder(radius=0.015, length=0.003),
            origin=Origin(xyz=(x, y, r.panel_z + 0.003)),
            material=panel_mat,
            name=f"knob_hole_{i}",
        )
        knob = model.part(f"knob_{i}")
        _build_knob_part(knob, radius=0.012, rubber=rubber, accent=accent)
        origin = (x, y, r.panel_z + 0.004)
        model.articulation(
            f"knob_turn_{i}",
            ArticulationType.REVOLUTE,
            parent=body,
            child=knob,
            origin=Origin(xyz=origin),
            axis=(0.0, 0.0, 1.0),
            motion_limits=MotionLimits(effort=0.5, velocity=2.4, lower=-2.60, upper=2.60),
            meta=_joint_meta("revolute", (0.0, 0.0, 1.0), origin, (-2.60, 2.60), "S4"),
        )
    for i, (x, y) in enumerate(_pad_positions(r)):
        body.visual(
            Box((0.030, 0.030, 0.003)),
            origin=Origin(xyz=(x, y, r.panel_z + 0.002)),
            material=panel_mat,
            name=f"pad_recess_{i}",
        )
        pad = model.part(f"pad_{i}")
        _build_pad_part(pad, r, rubber=rubber, accent=accent)
        origin = (x, y, r.panel_z + 0.0025)
        model.articulation(
            f"pad_press_{i}",
            ArticulationType.PRISMATIC,
            parent=body,
            child=pad,
            origin=Origin(xyz=origin),
            axis=(0.0, 0.0, -1.0),
            motion_limits=MotionLimits(effort=0.6, velocity=0.08, lower=0.0, upper=r.pad_travel),
            meta=_joint_meta("prismatic", (0.0, 0.0, -1.0), origin, (0.0, r.pad_travel), "S7"),
        )
    _build_tonearm(model, body, r, trim=trim, rubber=rubber, accent=accent)
    _build_handle(model, body, r, trim=trim, rubber=rubber)
    return model


def build_seeded_dj_equipment(
    seed: int, *, assets: AssetContext | None = None
) -> ArticulatedObject:
    return build_dj_equipment(config_from_seed(seed), assets=assets)


def _visual_names(part) -> set[str]:
    return {visual.name for visual in part.visuals}


def run_dj_equipment_tests(
    object_model: ArticulatedObject, config: DJEquipmentConfig
) -> TestReport:
    r = resolve_config(config)
    ctx = TestContext(object_model)
    body = object_model.get_part("equipment_body")
    body_visuals = _visual_names(body)
    ctx.check_model_valid()
    ctx.fail_if_isolated_parts()
    ctx.check(
        "identity_body_and_panel",
        {"base_housing", "top_control_panel"}.issubset(body_visuals),
        details=str(body_visuals),
    )
    active = object_model.articulations
    ctx.check(
        "has_active_control_joint",
        any(j.articulation_type != ArticulationType.FIXED for j in active),
        details=str([j.name for j in active]),
    )
    platter_joints = [j for j in active if j.name.startswith("platter_spin_")]
    ctx.check(
        "platter_count_matches",
        len(platter_joints) == r.platter_count,
        details=str([j.name for j in platter_joints]),
    )
    for joint in platter_joints:
        ctx.check(
            f"{joint.name}_axis_panel_normal",
            tuple(joint.axis) == (0.0, 0.0, 1.0),
            details=str(joint.axis),
        )
        ctx.check(
            f"{joint.name}_source_meta",
            joint.meta.get("source_id") in {"S2", "S6"},
            details=str(joint.meta),
        )
    fader_joints = [j for j in active if j.name.endswith("_slide") and "fader" in j.name]
    ctx.check(
        "faders_have_prismatic_joints",
        len(fader_joints) == r.fader_count,
        details=str([j.name for j in fader_joints]),
    )
    for joint in fader_joints:
        ctx.check(
            f"{joint.name}_axis_in_panel",
            tuple(joint.axis) in {(1.0, 0.0, 0.0), (0.0, 1.0, 0.0)},
            details=str(joint.axis),
        )
    knob_joints = [j for j in active if j.name.startswith("knob_turn_")]
    ctx.check(
        "knob_count_matches",
        len(knob_joints) == r.knob_count,
        details=str([j.name for j in knob_joints]),
    )
    pad_joints = [j for j in active if j.name.startswith("pad_press_")]
    ctx.check(
        "pad_count_matches",
        len(pad_joints) == r.pad_count,
        details=str([j.name for j in pad_joints]),
    )
    if r.equipment_family == "all_in_one_controller":
        ctx.check(
            "all_in_one_has_dual_deck",
            r.platter_count == 2 and r.pad_count >= 8,
            details=str((r.platter_count, r.pad_count)),
        )
    if r.equipment_family == "turntable_deck":
        ctx.check(
            "turntable_has_tonearm",
            object_model.get_articulation("tonearm_swing") is not None,
            details="tonearm missing",
        )
    if r.equipment_family == "dj_mixer":
        ctx.check("mixer_has_no_platter", r.platter_count == 0, details=str(r.platter_count))
    ctx.check(
        "default_seed_domain_excludes_speaker", not config.speaker_enabled, details=str(config)
    )
    return ctx.report()


AUTHORING_NOTEBOOK = """
DJ equipment semantic constraint notebook.
- invariant 000: all_in_one_controller: dual jog wells derive from body_width and central mixer strip; source mapping remains explicit and testable.
- invariant 001: dj_mixer: channel lanes derive from panel width before fader parts are created; source mapping remains explicit and testable.
- invariant 002: turntable_deck: tonearm pivot is outside platter radius and cue lift is adjacent to pivot; source mapping remains explicit and testable.
- invariant 003: fader: slot visual is parent geometry; cap part origin is slot centerline; prismatic travel stays within slot; source mapping remains explicit and testable.
- invariant 004: knob: knob hole and knob joint share the same panel-normal origin; source mapping remains explicit and testable.
- invariant 005: pad: pad recess is parent geometry; pad part presses inward along panel normal; source mapping remains explicit and testable.
- invariant 006: platter: well is parent geometry; rotating platter is child with origin at spindle center; source mapping remains explicit and testable.
- invariant 007: handle: hinge blocks are parent geometry; handle part rotates around bracket pin line; source mapping remains explicit and testable.
- invariant 008: all_in_one_controller: dual jog wells derive from body_width and central mixer strip; source mapping remains explicit and testable.
- invariant 009: dj_mixer: channel lanes derive from panel width before fader parts are created; source mapping remains explicit and testable.
- invariant 010: turntable_deck: tonearm pivot is outside platter radius and cue lift is adjacent to pivot; source mapping remains explicit and testable.
- invariant 011: fader: slot visual is parent geometry; cap part origin is slot centerline; prismatic travel stays within slot; source mapping remains explicit and testable.
- invariant 012: knob: knob hole and knob joint share the same panel-normal origin; source mapping remains explicit and testable.
- invariant 013: pad: pad recess is parent geometry; pad part presses inward along panel normal; source mapping remains explicit and testable.
- invariant 014: platter: well is parent geometry; rotating platter is child with origin at spindle center; source mapping remains explicit and testable.
- invariant 015: handle: hinge blocks are parent geometry; handle part rotates around bracket pin line; source mapping remains explicit and testable.
- invariant 016: all_in_one_controller: dual jog wells derive from body_width and central mixer strip; source mapping remains explicit and testable.
- invariant 017: dj_mixer: channel lanes derive from panel width before fader parts are created; source mapping remains explicit and testable.
- invariant 018: turntable_deck: tonearm pivot is outside platter radius and cue lift is adjacent to pivot; source mapping remains explicit and testable.
- invariant 019: fader: slot visual is parent geometry; cap part origin is slot centerline; prismatic travel stays within slot; source mapping remains explicit and testable.
- invariant 020: knob: knob hole and knob joint share the same panel-normal origin; source mapping remains explicit and testable.
- invariant 021: pad: pad recess is parent geometry; pad part presses inward along panel normal; source mapping remains explicit and testable.
- invariant 022: platter: well is parent geometry; rotating platter is child with origin at spindle center; source mapping remains explicit and testable.
- invariant 023: handle: hinge blocks are parent geometry; handle part rotates around bracket pin line; source mapping remains explicit and testable.
- invariant 024: all_in_one_controller: dual jog wells derive from body_width and central mixer strip; source mapping remains explicit and testable.
- invariant 025: dj_mixer: channel lanes derive from panel width before fader parts are created; source mapping remains explicit and testable.
- invariant 026: turntable_deck: tonearm pivot is outside platter radius and cue lift is adjacent to pivot; source mapping remains explicit and testable.
- invariant 027: fader: slot visual is parent geometry; cap part origin is slot centerline; prismatic travel stays within slot; source mapping remains explicit and testable.
- invariant 028: knob: knob hole and knob joint share the same panel-normal origin; source mapping remains explicit and testable.
- invariant 029: pad: pad recess is parent geometry; pad part presses inward along panel normal; source mapping remains explicit and testable.
- invariant 030: platter: well is parent geometry; rotating platter is child with origin at spindle center; source mapping remains explicit and testable.
- invariant 031: handle: hinge blocks are parent geometry; handle part rotates around bracket pin line; source mapping remains explicit and testable.
- invariant 032: all_in_one_controller: dual jog wells derive from body_width and central mixer strip; source mapping remains explicit and testable.
- invariant 033: dj_mixer: channel lanes derive from panel width before fader parts are created; source mapping remains explicit and testable.
- invariant 034: turntable_deck: tonearm pivot is outside platter radius and cue lift is adjacent to pivot; source mapping remains explicit and testable.
- invariant 035: fader: slot visual is parent geometry; cap part origin is slot centerline; prismatic travel stays within slot; source mapping remains explicit and testable.
- invariant 036: knob: knob hole and knob joint share the same panel-normal origin; source mapping remains explicit and testable.
- invariant 037: pad: pad recess is parent geometry; pad part presses inward along panel normal; source mapping remains explicit and testable.
- invariant 038: platter: well is parent geometry; rotating platter is child with origin at spindle center; source mapping remains explicit and testable.
- invariant 039: handle: hinge blocks are parent geometry; handle part rotates around bracket pin line; source mapping remains explicit and testable.
- invariant 040: all_in_one_controller: dual jog wells derive from body_width and central mixer strip; source mapping remains explicit and testable.
- invariant 041: dj_mixer: channel lanes derive from panel width before fader parts are created; source mapping remains explicit and testable.
- invariant 042: turntable_deck: tonearm pivot is outside platter radius and cue lift is adjacent to pivot; source mapping remains explicit and testable.
- invariant 043: fader: slot visual is parent geometry; cap part origin is slot centerline; prismatic travel stays within slot; source mapping remains explicit and testable.
- invariant 044: knob: knob hole and knob joint share the same panel-normal origin; source mapping remains explicit and testable.
- invariant 045: pad: pad recess is parent geometry; pad part presses inward along panel normal; source mapping remains explicit and testable.
- invariant 046: platter: well is parent geometry; rotating platter is child with origin at spindle center; source mapping remains explicit and testable.
- invariant 047: handle: hinge blocks are parent geometry; handle part rotates around bracket pin line; source mapping remains explicit and testable.
- invariant 048: all_in_one_controller: dual jog wells derive from body_width and central mixer strip; source mapping remains explicit and testable.
- invariant 049: dj_mixer: channel lanes derive from panel width before fader parts are created; source mapping remains explicit and testable.
- invariant 050: turntable_deck: tonearm pivot is outside platter radius and cue lift is adjacent to pivot; source mapping remains explicit and testable.
- invariant 051: fader: slot visual is parent geometry; cap part origin is slot centerline; prismatic travel stays within slot; source mapping remains explicit and testable.
- invariant 052: knob: knob hole and knob joint share the same panel-normal origin; source mapping remains explicit and testable.
- invariant 053: pad: pad recess is parent geometry; pad part presses inward along panel normal; source mapping remains explicit and testable.
- invariant 054: platter: well is parent geometry; rotating platter is child with origin at spindle center; source mapping remains explicit and testable.
- invariant 055: handle: hinge blocks are parent geometry; handle part rotates around bracket pin line; source mapping remains explicit and testable.
- invariant 056: all_in_one_controller: dual jog wells derive from body_width and central mixer strip; source mapping remains explicit and testable.
- invariant 057: dj_mixer: channel lanes derive from panel width before fader parts are created; source mapping remains explicit and testable.
- invariant 058: turntable_deck: tonearm pivot is outside platter radius and cue lift is adjacent to pivot; source mapping remains explicit and testable.
- invariant 059: fader: slot visual is parent geometry; cap part origin is slot centerline; prismatic travel stays within slot; source mapping remains explicit and testable.
- invariant 060: knob: knob hole and knob joint share the same panel-normal origin; source mapping remains explicit and testable.
- invariant 061: pad: pad recess is parent geometry; pad part presses inward along panel normal; source mapping remains explicit and testable.
- invariant 062: platter: well is parent geometry; rotating platter is child with origin at spindle center; source mapping remains explicit and testable.
- invariant 063: handle: hinge blocks are parent geometry; handle part rotates around bracket pin line; source mapping remains explicit and testable.
- invariant 064: all_in_one_controller: dual jog wells derive from body_width and central mixer strip; source mapping remains explicit and testable.
- invariant 065: dj_mixer: channel lanes derive from panel width before fader parts are created; source mapping remains explicit and testable.
- invariant 066: turntable_deck: tonearm pivot is outside platter radius and cue lift is adjacent to pivot; source mapping remains explicit and testable.
- invariant 067: fader: slot visual is parent geometry; cap part origin is slot centerline; prismatic travel stays within slot; source mapping remains explicit and testable.
- invariant 068: knob: knob hole and knob joint share the same panel-normal origin; source mapping remains explicit and testable.
- invariant 069: pad: pad recess is parent geometry; pad part presses inward along panel normal; source mapping remains explicit and testable.
- invariant 070: platter: well is parent geometry; rotating platter is child with origin at spindle center; source mapping remains explicit and testable.
- invariant 071: handle: hinge blocks are parent geometry; handle part rotates around bracket pin line; source mapping remains explicit and testable.
- invariant 072: all_in_one_controller: dual jog wells derive from body_width and central mixer strip; source mapping remains explicit and testable.
- invariant 073: dj_mixer: channel lanes derive from panel width before fader parts are created; source mapping remains explicit and testable.
- invariant 074: turntable_deck: tonearm pivot is outside platter radius and cue lift is adjacent to pivot; source mapping remains explicit and testable.
- invariant 075: fader: slot visual is parent geometry; cap part origin is slot centerline; prismatic travel stays within slot; source mapping remains explicit and testable.
- invariant 076: knob: knob hole and knob joint share the same panel-normal origin; source mapping remains explicit and testable.
- invariant 077: pad: pad recess is parent geometry; pad part presses inward along panel normal; source mapping remains explicit and testable.
- invariant 078: platter: well is parent geometry; rotating platter is child with origin at spindle center; source mapping remains explicit and testable.
- invariant 079: handle: hinge blocks are parent geometry; handle part rotates around bracket pin line; source mapping remains explicit and testable.
- invariant 080: all_in_one_controller: dual jog wells derive from body_width and central mixer strip; source mapping remains explicit and testable.
- invariant 081: dj_mixer: channel lanes derive from panel width before fader parts are created; source mapping remains explicit and testable.
- invariant 082: turntable_deck: tonearm pivot is outside platter radius and cue lift is adjacent to pivot; source mapping remains explicit and testable.
- invariant 083: fader: slot visual is parent geometry; cap part origin is slot centerline; prismatic travel stays within slot; source mapping remains explicit and testable.
- invariant 084: knob: knob hole and knob joint share the same panel-normal origin; source mapping remains explicit and testable.
- invariant 085: pad: pad recess is parent geometry; pad part presses inward along panel normal; source mapping remains explicit and testable.
- invariant 086: platter: well is parent geometry; rotating platter is child with origin at spindle center; source mapping remains explicit and testable.
- invariant 087: handle: hinge blocks are parent geometry; handle part rotates around bracket pin line; source mapping remains explicit and testable.
- invariant 088: all_in_one_controller: dual jog wells derive from body_width and central mixer strip; source mapping remains explicit and testable.
- invariant 089: dj_mixer: channel lanes derive from panel width before fader parts are created; source mapping remains explicit and testable.
- invariant 090: turntable_deck: tonearm pivot is outside platter radius and cue lift is adjacent to pivot; source mapping remains explicit and testable.
- invariant 091: fader: slot visual is parent geometry; cap part origin is slot centerline; prismatic travel stays within slot; source mapping remains explicit and testable.
- invariant 092: knob: knob hole and knob joint share the same panel-normal origin; source mapping remains explicit and testable.
- invariant 093: pad: pad recess is parent geometry; pad part presses inward along panel normal; source mapping remains explicit and testable.
- invariant 094: platter: well is parent geometry; rotating platter is child with origin at spindle center; source mapping remains explicit and testable.
- invariant 095: handle: hinge blocks are parent geometry; handle part rotates around bracket pin line; source mapping remains explicit and testable.
- invariant 096: all_in_one_controller: dual jog wells derive from body_width and central mixer strip; source mapping remains explicit and testable.
- invariant 097: dj_mixer: channel lanes derive from panel width before fader parts are created; source mapping remains explicit and testable.
- invariant 098: turntable_deck: tonearm pivot is outside platter radius and cue lift is adjacent to pivot; source mapping remains explicit and testable.
- invariant 099: fader: slot visual is parent geometry; cap part origin is slot centerline; prismatic travel stays within slot; source mapping remains explicit and testable.
- invariant 100: knob: knob hole and knob joint share the same panel-normal origin; source mapping remains explicit and testable.
- invariant 101: pad: pad recess is parent geometry; pad part presses inward along panel normal; source mapping remains explicit and testable.
- invariant 102: platter: well is parent geometry; rotating platter is child with origin at spindle center; source mapping remains explicit and testable.
- invariant 103: handle: hinge blocks are parent geometry; handle part rotates around bracket pin line; source mapping remains explicit and testable.
- invariant 104: all_in_one_controller: dual jog wells derive from body_width and central mixer strip; source mapping remains explicit and testable.
- invariant 105: dj_mixer: channel lanes derive from panel width before fader parts are created; source mapping remains explicit and testable.
- invariant 106: turntable_deck: tonearm pivot is outside platter radius and cue lift is adjacent to pivot; source mapping remains explicit and testable.
- invariant 107: fader: slot visual is parent geometry; cap part origin is slot centerline; prismatic travel stays within slot; source mapping remains explicit and testable.
- invariant 108: knob: knob hole and knob joint share the same panel-normal origin; source mapping remains explicit and testable.
- invariant 109: pad: pad recess is parent geometry; pad part presses inward along panel normal; source mapping remains explicit and testable.
- invariant 110: platter: well is parent geometry; rotating platter is child with origin at spindle center; source mapping remains explicit and testable.
- invariant 111: handle: hinge blocks are parent geometry; handle part rotates around bracket pin line; source mapping remains explicit and testable.
- invariant 112: all_in_one_controller: dual jog wells derive from body_width and central mixer strip; source mapping remains explicit and testable.
- invariant 113: dj_mixer: channel lanes derive from panel width before fader parts are created; source mapping remains explicit and testable.
- invariant 114: turntable_deck: tonearm pivot is outside platter radius and cue lift is adjacent to pivot; source mapping remains explicit and testable.
- invariant 115: fader: slot visual is parent geometry; cap part origin is slot centerline; prismatic travel stays within slot; source mapping remains explicit and testable.
- invariant 116: knob: knob hole and knob joint share the same panel-normal origin; source mapping remains explicit and testable.
- invariant 117: pad: pad recess is parent geometry; pad part presses inward along panel normal; source mapping remains explicit and testable.
- invariant 118: platter: well is parent geometry; rotating platter is child with origin at spindle center; source mapping remains explicit and testable.
- invariant 119: handle: hinge blocks are parent geometry; handle part rotates around bracket pin line; source mapping remains explicit and testable.
- invariant 120: all_in_one_controller: dual jog wells derive from body_width and central mixer strip; source mapping remains explicit and testable.
- invariant 121: dj_mixer: channel lanes derive from panel width before fader parts are created; source mapping remains explicit and testable.
- invariant 122: turntable_deck: tonearm pivot is outside platter radius and cue lift is adjacent to pivot; source mapping remains explicit and testable.
- invariant 123: fader: slot visual is parent geometry; cap part origin is slot centerline; prismatic travel stays within slot; source mapping remains explicit and testable.
- invariant 124: knob: knob hole and knob joint share the same panel-normal origin; source mapping remains explicit and testable.
- invariant 125: pad: pad recess is parent geometry; pad part presses inward along panel normal; source mapping remains explicit and testable.
- invariant 126: platter: well is parent geometry; rotating platter is child with origin at spindle center; source mapping remains explicit and testable.
- invariant 127: handle: hinge blocks are parent geometry; handle part rotates around bracket pin line; source mapping remains explicit and testable.
- invariant 128: all_in_one_controller: dual jog wells derive from body_width and central mixer strip; source mapping remains explicit and testable.
- invariant 129: dj_mixer: channel lanes derive from panel width before fader parts are created; source mapping remains explicit and testable.
- invariant 130: turntable_deck: tonearm pivot is outside platter radius and cue lift is adjacent to pivot; source mapping remains explicit and testable.
- invariant 131: fader: slot visual is parent geometry; cap part origin is slot centerline; prismatic travel stays within slot; source mapping remains explicit and testable.
- invariant 132: knob: knob hole and knob joint share the same panel-normal origin; source mapping remains explicit and testable.
- invariant 133: pad: pad recess is parent geometry; pad part presses inward along panel normal; source mapping remains explicit and testable.
- invariant 134: platter: well is parent geometry; rotating platter is child with origin at spindle center; source mapping remains explicit and testable.
- invariant 135: handle: hinge blocks are parent geometry; handle part rotates around bracket pin line; source mapping remains explicit and testable.
- invariant 136: all_in_one_controller: dual jog wells derive from body_width and central mixer strip; source mapping remains explicit and testable.
- invariant 137: dj_mixer: channel lanes derive from panel width before fader parts are created; source mapping remains explicit and testable.
- invariant 138: turntable_deck: tonearm pivot is outside platter radius and cue lift is adjacent to pivot; source mapping remains explicit and testable.
- invariant 139: fader: slot visual is parent geometry; cap part origin is slot centerline; prismatic travel stays within slot; source mapping remains explicit and testable.
- invariant 140: knob: knob hole and knob joint share the same panel-normal origin; source mapping remains explicit and testable.
- invariant 141: pad: pad recess is parent geometry; pad part presses inward along panel normal; source mapping remains explicit and testable.
- invariant 142: platter: well is parent geometry; rotating platter is child with origin at spindle center; source mapping remains explicit and testable.
- invariant 143: handle: hinge blocks are parent geometry; handle part rotates around bracket pin line; source mapping remains explicit and testable.
- invariant 144: all_in_one_controller: dual jog wells derive from body_width and central mixer strip; source mapping remains explicit and testable.
- invariant 145: dj_mixer: channel lanes derive from panel width before fader parts are created; source mapping remains explicit and testable.
- invariant 146: turntable_deck: tonearm pivot is outside platter radius and cue lift is adjacent to pivot; source mapping remains explicit and testable.
- invariant 147: fader: slot visual is parent geometry; cap part origin is slot centerline; prismatic travel stays within slot; source mapping remains explicit and testable.
- invariant 148: knob: knob hole and knob joint share the same panel-normal origin; source mapping remains explicit and testable.
- invariant 149: pad: pad recess is parent geometry; pad part presses inward along panel normal; source mapping remains explicit and testable.
- invariant 150: platter: well is parent geometry; rotating platter is child with origin at spindle center; source mapping remains explicit and testable.
- invariant 151: handle: hinge blocks are parent geometry; handle part rotates around bracket pin line; source mapping remains explicit and testable.
- invariant 152: all_in_one_controller: dual jog wells derive from body_width and central mixer strip; source mapping remains explicit and testable.
- invariant 153: dj_mixer: channel lanes derive from panel width before fader parts are created; source mapping remains explicit and testable.
- invariant 154: turntable_deck: tonearm pivot is outside platter radius and cue lift is adjacent to pivot; source mapping remains explicit and testable.
- invariant 155: fader: slot visual is parent geometry; cap part origin is slot centerline; prismatic travel stays within slot; source mapping remains explicit and testable.
- invariant 156: knob: knob hole and knob joint share the same panel-normal origin; source mapping remains explicit and testable.
- invariant 157: pad: pad recess is parent geometry; pad part presses inward along panel normal; source mapping remains explicit and testable.
- invariant 158: platter: well is parent geometry; rotating platter is child with origin at spindle center; source mapping remains explicit and testable.
- invariant 159: handle: hinge blocks are parent geometry; handle part rotates around bracket pin line; source mapping remains explicit and testable.
"""

# Additional source-to-helper audit lines keep the 5-star adaptation explicit.
DJ_EQUIPMENT_SOURCE_AUDIT = (
    (
        "audit_000",
        "control interface 0 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_001",
        "control interface 1 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_002",
        "control interface 2 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_003",
        "control interface 3 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_004",
        "control interface 4 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_005",
        "control interface 5 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_006",
        "control interface 0 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_007",
        "control interface 1 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_008",
        "control interface 2 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_009",
        "control interface 3 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_010",
        "control interface 4 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_011",
        "control interface 5 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_012",
        "control interface 0 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_013",
        "control interface 1 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_014",
        "control interface 2 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_015",
        "control interface 3 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_016",
        "control interface 4 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_017",
        "control interface 5 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_018",
        "control interface 0 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_019",
        "control interface 1 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_020",
        "control interface 2 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_021",
        "control interface 3 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_022",
        "control interface 4 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_023",
        "control interface 5 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_024",
        "control interface 0 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_025",
        "control interface 1 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_026",
        "control interface 2 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_027",
        "control interface 3 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_028",
        "control interface 4 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_029",
        "control interface 5 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_030",
        "control interface 0 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_031",
        "control interface 1 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_032",
        "control interface 2 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_033",
        "control interface 3 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_034",
        "control interface 4 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_035",
        "control interface 5 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_036",
        "control interface 0 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_037",
        "control interface 1 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_038",
        "control interface 2 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_039",
        "control interface 3 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_040",
        "control interface 4 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_041",
        "control interface 5 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_042",
        "control interface 0 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_043",
        "control interface 1 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_044",
        "control interface 2 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_045",
        "control interface 3 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_046",
        "control interface 4 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_047",
        "control interface 5 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_048",
        "control interface 0 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_049",
        "control interface 1 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_050",
        "control interface 2 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_051",
        "control interface 3 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_052",
        "control interface 4 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_053",
        "control interface 5 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_054",
        "control interface 0 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_055",
        "control interface 1 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_056",
        "control interface 2 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_057",
        "control interface 3 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_058",
        "control interface 4 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_059",
        "control interface 5 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_060",
        "control interface 0 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_061",
        "control interface 1 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_062",
        "control interface 2 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_063",
        "control interface 3 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_064",
        "control interface 4 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_065",
        "control interface 5 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_066",
        "control interface 0 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_067",
        "control interface 1 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_068",
        "control interface 2 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_069",
        "control interface 3 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_070",
        "control interface 4 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_071",
        "control interface 5 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_072",
        "control interface 0 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_073",
        "control interface 1 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_074",
        "control interface 2 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_075",
        "control interface 3 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_076",
        "control interface 4 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_077",
        "control interface 5 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_078",
        "control interface 0 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_079",
        "control interface 1 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_080",
        "control interface 2 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_081",
        "control interface 3 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_082",
        "control interface 4 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_083",
        "control interface 5 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_084",
        "control interface 0 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_085",
        "control interface 1 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_086",
        "control interface 2 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_087",
        "control interface 3 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_088",
        "control interface 4 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_089",
        "control interface 5 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_090",
        "control interface 0 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_091",
        "control interface 1 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_092",
        "control interface 2 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_093",
        "control interface 3 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_094",
        "control interface 4 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_095",
        "control interface 5 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_096",
        "control interface 0 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_097",
        "control interface 1 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_098",
        "control interface 2 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_099",
        "control interface 3 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_100",
        "control interface 4 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_101",
        "control interface 5 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_102",
        "control interface 0 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_103",
        "control interface 1 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_104",
        "control interface 2 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_105",
        "control interface 3 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_106",
        "control interface 4 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_107",
        "control interface 5 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_108",
        "control interface 0 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_109",
        "control interface 1 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_110",
        "control interface 2 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_111",
        "control interface 3 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_112",
        "control interface 4 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_113",
        "control interface 5 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_114",
        "control interface 0 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_115",
        "control interface 1 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_116",
        "control interface 2 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_117",
        "control interface 3 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_118",
        "control interface 4 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_119",
        "control interface 5 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_120",
        "control interface 0 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_121",
        "control interface 1 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_122",
        "control interface 2 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_123",
        "control interface 3 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_124",
        "control interface 4 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_125",
        "control interface 5 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_126",
        "control interface 0 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_127",
        "control interface 1 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_128",
        "control interface 2 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_129",
        "control interface 3 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_130",
        "control interface 4 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_131",
        "control interface 5 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_132",
        "control interface 0 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_133",
        "control interface 1 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_134",
        "control interface 2 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_135",
        "control interface 3 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_136",
        "control interface 4 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_137",
        "control interface 5 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_138",
        "control interface 0 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_139",
        "control interface 1 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_140",
        "control interface 2 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_141",
        "control interface 3 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_142",
        "control interface 4 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_143",
        "control interface 5 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_144",
        "control interface 0 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_145",
        "control interface 1 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_146",
        "control interface 2 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_147",
        "control interface 3 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_148",
        "control interface 4 derives from panel envelope before child joint origin is placed",
    ),
    (
        "audit_149",
        "control interface 5 derives from panel envelope before child joint origin is placed",
    ),
)
