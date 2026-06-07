"""Modular procedural template for vane arrays with independent pivots.

The category identity is an array of vanes carried by one grounded frame,
where every vane is a separate revolute child.  The template keeps the pivot
interface explicit: each parent socket exposes a visible face and each vane
has a mating hub face at the joint origin.
"""

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
    MatingContract,
    MotionLimits,
    Origin,
    TestContext,
    TestReport,
)

__modular__ = True

FrameModule = Literal[
    "rectangular_duct_frame",
    "open_side_rail_frame",
    "cassette_backplate_frame",
    "curved_cowl_frame",
]
ArrayLayout = Literal[
    "horizontal_stack",
    "vertical_bank",
    "twin_column_stack",
    "staggered_grid",
]
VaneProfile = Literal[
    "flat_plate_vanes",
    "airfoil_lipped_vanes",
    "perforated_light_vanes",
    "split_panel_vanes",
]
PivotHardware = Literal[
    "plain_end_pin_blocks",
    "round_bearing_buttons",
    "comb_rail_saddles",
    "serviceable_bolted_bosses",
]
MaterialStyle = Literal["brushed_aluminum", "dark_hvac", "safety_yellow", "white_lab"]
AxisKind = Literal["x_axis", "z_axis"]

FRAME_MODULES: tuple[FrameModule, ...] = (
    "rectangular_duct_frame",
    "open_side_rail_frame",
    "cassette_backplate_frame",
    "curved_cowl_frame",
)
ARRAY_LAYOUTS: tuple[ArrayLayout, ...] = (
    "horizontal_stack",
    "vertical_bank",
    "twin_column_stack",
    "staggered_grid",
)
VANE_PROFILES: tuple[VaneProfile, ...] = (
    "flat_plate_vanes",
    "airfoil_lipped_vanes",
    "perforated_light_vanes",
    "split_panel_vanes",
)
PIVOT_HARDWARE: tuple[PivotHardware, ...] = (
    "plain_end_pin_blocks",
    "round_bearing_buttons",
    "comb_rail_saddles",
    "serviceable_bolted_bosses",
)
MATERIAL_STYLES: tuple[MaterialStyle, ...] = (
    "brushed_aluminum",
    "dark_hvac",
    "safety_yellow",
    "white_lab",
)

PALETTES: dict[MaterialStyle, dict[str, tuple[float, float, float, float]]] = {
    "brushed_aluminum": {
        "frame": (0.58, 0.60, 0.60, 1.0),
        "frame_dark": (0.28, 0.30, 0.31, 1.0),
        "vane": (0.72, 0.74, 0.73, 1.0),
        "edge": (0.38, 0.40, 0.41, 1.0),
        "pivot": (0.16, 0.17, 0.18, 1.0),
        "accent": (0.10, 0.32, 0.58, 1.0),
    },
    "dark_hvac": {
        "frame": (0.12, 0.13, 0.14, 1.0),
        "frame_dark": (0.035, 0.038, 0.040, 1.0),
        "vane": (0.24, 0.26, 0.27, 1.0),
        "edge": (0.42, 0.44, 0.45, 1.0),
        "pivot": (0.63, 0.64, 0.62, 1.0),
        "accent": (0.82, 0.44, 0.10, 1.0),
    },
    "safety_yellow": {
        "frame": (0.80, 0.62, 0.13, 1.0),
        "frame_dark": (0.28, 0.24, 0.12, 1.0),
        "vane": (0.92, 0.75, 0.18, 1.0),
        "edge": (0.20, 0.20, 0.18, 1.0),
        "pivot": (0.10, 0.10, 0.09, 1.0),
        "accent": (0.70, 0.12, 0.10, 1.0),
    },
    "white_lab": {
        "frame": (0.86, 0.87, 0.84, 1.0),
        "frame_dark": (0.54, 0.55, 0.52, 1.0),
        "vane": (0.94, 0.95, 0.92, 1.0),
        "edge": (0.66, 0.68, 0.66, 1.0),
        "pivot": (0.28, 0.30, 0.31, 1.0),
        "accent": (0.18, 0.48, 0.56, 1.0),
    },
}


@dataclass(frozen=True)
class VaneArrayWithIndependentPivotsConfig:
    frame_module: FrameModule | None = None
    array_layout: ArrayLayout | None = None
    vane_profile: VaneProfile | None = None
    pivot_hardware: PivotHardware | None = None
    vane_count: int | None = None
    width_scale: float = 1.0
    height_scale: float = 1.0
    pitch_scale: float = 1.0
    opening_angle: float = 0.0
    material_style: MaterialStyle = "brushed_aluminum"
    name: str = "vane_array_with_independent_pivots"


@dataclass(frozen=True)
class VaneSpec:
    index: int
    origin: tuple[float, float, float]
    axis: tuple[float, float, float]
    axis_kind: AxisKind
    length: float
    height: float
    pitch_angle: float
    parent_socket_size: tuple[float, float, float]
    socket_name: str


@dataclass(frozen=True)
class ResolvedVaneArrayWithIndependentPivotsConfig:
    frame_module: FrameModule
    array_layout: ArrayLayout
    vane_profile: VaneProfile
    pivot_hardware: PivotHardware
    material_style: MaterialStyle
    width: float
    height: float
    depth: float
    rail: float
    backplate_depth: float
    blade_depth: float
    blade_thickness: float
    vane_count: int
    opening_angle: float
    specs: tuple[VaneSpec, ...]
    name: str


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _choice(value: str | None, allowed: tuple[str, ...], fallback: str, field: str) -> str:
    if value is None:
        return fallback
    if value not in allowed:
        raise ValueError(f"Unsupported {field}: {value}")
    return value


def config_from_seed(seed: int) -> VaneArrayWithIndependentPivotsConfig:
    rng = random.Random(seed)
    layout: ArrayLayout = rng.choice(ARRAY_LAYOUTS)
    count_pool = {
        "horizontal_stack": (3, 4, 5, 6, 7, 8, 10, 12),
        "vertical_bank": (3, 4, 5, 6, 7, 8, 10, 12),
        "twin_column_stack": (4, 6, 8, 10, 12),
        "staggered_grid": (4, 6, 8, 10, 12),
    }[layout]
    return VaneArrayWithIndependentPivotsConfig(
        frame_module=rng.choice(FRAME_MODULES),
        array_layout=layout,
        vane_profile=rng.choice(VANE_PROFILES),
        pivot_hardware=rng.choice(PIVOT_HARDWARE),
        vane_count=rng.choice(count_pool),
        width_scale=round(rng.uniform(0.86, 1.22), 3),
        height_scale=round(rng.uniform(0.86, 1.20), 3),
        pitch_scale=round(rng.uniform(0.90, 1.12), 3),
        opening_angle=round(rng.uniform(-0.22, 0.22), 3),
        material_style=rng.choice(MATERIAL_STYLES),
        name=f"seeded_vane_array_with_independent_pivots_{seed}",
    )


def resolve_config(
    config: VaneArrayWithIndependentPivotsConfig,
) -> ResolvedVaneArrayWithIndependentPivotsConfig:
    frame = _choice(config.frame_module, FRAME_MODULES, "rectangular_duct_frame", "frame_module")
    layout = _choice(config.array_layout, ARRAY_LAYOUTS, "horizontal_stack", "array_layout")
    profile = _choice(config.vane_profile, VANE_PROFILES, "airfoil_lipped_vanes", "vane_profile")
    pivot = _choice(config.pivot_hardware, PIVOT_HARDWARE, "plain_end_pin_blocks", "pivot_hardware")
    material = _choice(config.material_style, MATERIAL_STYLES, "brushed_aluminum", "material_style")

    width = 1.02 * _clamp(config.width_scale, 0.72, 1.36)
    height = 0.92 * _clamp(config.height_scale, 0.72, 1.34)
    depth = 0.105
    rail = _clamp(min(width, height) * 0.065, 0.040, 0.072)
    backplate_depth = 0.014
    if profile == "flat_plate_vanes":
        blade_depth, blade_thickness = 0.056, 0.014
    elif profile == "perforated_light_vanes":
        blade_depth, blade_thickness = 0.050, 0.012
    elif profile == "split_panel_vanes":
        blade_depth, blade_thickness = 0.060, 0.013
    else:
        blade_depth, blade_thickness = 0.064, 0.015
    angle = _clamp(config.opening_angle, -0.28, 0.28)
    count = _legal_count(layout, config.vane_count)
    specs = _derive_vane_specs(
        layout=layout,
        count=count,
        width=width,
        height=height,
        rail=rail,
        blade_depth=blade_depth,
        blade_thickness=blade_thickness,
        angle=angle,
        pitch_scale=_clamp(config.pitch_scale, 0.84, 1.20),
    )
    return ResolvedVaneArrayWithIndependentPivotsConfig(
        frame_module=frame,
        array_layout=layout,
        vane_profile=profile,
        pivot_hardware=pivot,
        material_style=material,
        width=width,
        height=height,
        depth=depth,
        rail=rail,
        backplate_depth=backplate_depth,
        blade_depth=blade_depth,
        blade_thickness=blade_thickness,
        vane_count=count,
        opening_angle=angle,
        specs=tuple(specs),
        name=config.name or "vane_array_with_independent_pivots",
    )


def _legal_count(layout: ArrayLayout, requested: int | None) -> int:
    if layout == "horizontal_stack":
        return max(3, min(12, int(requested if requested is not None else 6)))
    if layout == "vertical_bank":
        return max(3, min(12, int(requested if requested is not None else 5)))
    if layout == "twin_column_stack":
        value = max(4, min(12, int(requested if requested is not None else 8)))
        return value if value % 2 == 0 else min(12, value + 1)
    value = max(4, min(12, int(requested if requested is not None else 8)))
    return value if value % 2 == 0 else min(12, value + 1)


def _derive_vane_specs(
    *,
    layout: ArrayLayout,
    count: int,
    width: float,
    height: float,
    rail: float,
    blade_depth: float,
    blade_thickness: float,
    angle: float,
    pitch_scale: float,
) -> list[VaneSpec]:
    inner_w = width - 2.0 * rail
    inner_h = height - 2.0 * rail
    socket_y = 0.0
    specs: list[VaneSpec] = []
    if layout == "horizontal_stack":
        pitch = inner_h / count
        blade_len = inner_w * 0.92
        for i in range(count):
            z = rail + (i + 0.5) * pitch
            specs.append(
                _vane_spec(i, (0.0, socket_y, z), "x_axis", blade_len, blade_thickness, angle)
            )
    elif layout == "vertical_bank":
        pitch = inner_w / count
        blade_h = inner_h * 0.88
        for i in range(count):
            x = -inner_w * 0.5 + (i + 0.5) * pitch
            specs.append(
                _vane_spec(
                    i, (x, socket_y, height * 0.5), "z_axis", blade_thickness, blade_h, angle
                )
            )
    elif layout == "twin_column_stack":
        rows = count // 2
        col_w = (inner_w - rail * 0.55) / 2.0
        pitch = inner_h / rows
        blade_len = col_w * 0.86
        idx = 0
        for col, x in enumerate((-col_w * 0.52, col_w * 0.52)):
            col_angle = angle if col == 0 else -angle * 0.72
            for row in range(rows):
                z = rail + (row + 0.5) * pitch
                specs.append(
                    _vane_spec(
                        idx, (x, socket_y, z), "x_axis", blade_len, blade_thickness, col_angle
                    )
                )
                idx += 1
    else:
        rows = 2
        cols = count // rows
        pitch_x = inner_w / cols
        pitch_z = inner_h / rows
        blade_h = min(pitch_z * 0.68 * pitch_scale, inner_h * 0.42)
        idx = 0
        for row in range(rows):
            z = rail + (row + 0.5) * pitch_z
            for col in range(cols):
                x = -inner_w * 0.5 + (col + 0.5) * pitch_x
                stagger = (0.5 if row % 2 else 0.0) * min(pitch_x * 0.16, rail * 0.35)
                local_angle = angle if (row + col) % 2 == 0 else -angle * 0.75
                specs.append(
                    _vane_spec(
                        idx,
                        (x + stagger, socket_y, z),
                        "z_axis",
                        blade_thickness,
                        blade_h,
                        local_angle,
                    )
                )
                idx += 1
    return specs


def _vane_spec(
    index: int,
    origin: tuple[float, float, float],
    axis_kind: AxisKind,
    length: float,
    height: float,
    angle: float,
) -> VaneSpec:
    if axis_kind == "x_axis":
        socket_size = (0.040, 0.006, 0.032)
        axis = (1.0, 0.0, 0.0)
    else:
        socket_size = (0.032, 0.006, 0.040)
        axis = (0.0, 0.0, 1.0)
    return VaneSpec(
        index=index,
        origin=origin,
        axis=axis,
        axis_kind=axis_kind,
        length=length,
        height=height,
        pitch_angle=angle,
        parent_socket_size=socket_size,
        socket_name=f"pivot_socket_{index}",
    )


def with_overrides(
    config: VaneArrayWithIndependentPivotsConfig, **kwargs: object
) -> VaneArrayWithIndependentPivotsConfig:
    return replace(config, **kwargs)


def slot_choices_for_config(
    config: VaneArrayWithIndependentPivotsConfig | ResolvedVaneArrayWithIndependentPivotsConfig,
) -> tuple[tuple[str, str], ...]:
    r = (
        config
        if isinstance(config, ResolvedVaneArrayWithIndependentPivotsConfig)
        else resolve_config(config)
    )
    return (
        ("frame", r.frame_module),
        ("array_layout", r.array_layout),
        ("vane_profile", r.vane_profile),
        ("pivot_hardware", r.pivot_hardware),
        ("vane_multiplicity", f"{r.vane_count}_independent_vanes"),
        ("axis_family", r.specs[0].axis_kind if r.specs else "x_axis"),
        ("material_style", r.material_style),
    )


def slot_choices_for_seed(seed: int) -> tuple[tuple[str, str], ...]:
    return slot_choices_for_config(config_from_seed(seed))


def _mat(model: ArticulatedObject, r: ResolvedVaneArrayWithIndependentPivotsConfig, key: str):
    return model.material(f"vane_array_{key}", rgba=PALETTES[r.material_style][key])


def _box(part, size, xyz, material, name, rpy=(0.0, 0.0, 0.0)) -> None:
    part.visual(Box(size), origin=Origin(xyz=xyz, rpy=rpy), material=material, name=name)


def _cyl(part, radius, length, xyz, material, name, rpy=(0.0, 0.0, 0.0)) -> None:
    part.visual(
        Cylinder(radius=radius, length=length),
        origin=Origin(xyz=xyz, rpy=rpy),
        material=material,
        name=name,
    )


def _build_frame(
    model: ArticulatedObject,
    r: ResolvedVaneArrayWithIndependentPivotsConfig,
    mats: dict[str, object],
):
    body = model.part("frame")
    W, H, D, R = r.width, r.height, r.depth, r.rail
    back_y = -0.006 - r.backplate_depth * 0.5
    _box(
        body,
        (R, r.backplate_depth, H),
        (-W * 0.5 + R * 0.5, back_y, H * 0.5),
        mats["frame_dark"],
        "rear_left_reveal",
    )
    _box(
        body,
        (R, r.backplate_depth, H),
        (W * 0.5 - R * 0.5, back_y, H * 0.5),
        mats["frame_dark"],
        "rear_right_reveal",
    )
    _box(
        body,
        (W - 2.0 * R, r.backplate_depth, R),
        (0.0, back_y, R * 0.5),
        mats["frame_dark"],
        "rear_bottom_reveal",
    )
    _box(
        body,
        (W - 2.0 * R, r.backplate_depth, R),
        (0.0, back_y, H - R * 0.5),
        mats["frame_dark"],
        "rear_top_reveal",
    )
    _box(body, (R, D, H), (-W * 0.5 + R * 0.5, -D * 0.46, H * 0.5), mats["frame"], "left_side_rail")
    _box(body, (R, D, H), (W * 0.5 - R * 0.5, -D * 0.46, H * 0.5), mats["frame"], "right_side_rail")
    _box(body, (W, D, R), (0.0, -D * 0.46, R * 0.5), mats["frame"], "bottom_rail")
    _box(body, (W, D, R), (0.0, -D * 0.46, H - R * 0.5), mats["frame"], "top_rail")
    if r.frame_module in {"cassette_backplate_frame", "curved_cowl_frame"}:
        _box(
            body,
            (W * 0.74, 0.018, R * 0.45),
            (0.0, -D * 0.16, H - R * 0.24),
            mats["edge"],
            "top_service_lip",
        )
        _box(
            body,
            (W * 0.74, 0.018, R * 0.45),
            (0.0, -D * 0.16, R * 0.24),
            mats["edge"],
            "bottom_service_lip",
        )
    if r.frame_module == "open_side_rail_frame":
        _box(
            body,
            (R * 0.44, 0.014, H - 1.80 * R),
            (0.0, -0.006 - 0.007, H * 0.5),
            mats["edge"],
            "center_open_spine",
        )
    if r.frame_module == "curved_cowl_frame":
        _cyl(
            body,
            R * 0.34,
            W * 0.92,
            (0.0, -D * 0.78, H - R * 0.18),
            mats["frame"],
            "upper_rolled_cowl",
            (0.0, math.pi / 2.0, 0.0),
        )
        _cyl(
            body,
            R * 0.28,
            W * 0.88,
            (0.0, -D * 0.78, R * 0.18),
            mats["frame"],
            "lower_rolled_cowl",
            (0.0, math.pi / 2.0, 0.0),
        )
    if r.array_layout == "twin_column_stack":
        _box(
            body,
            (R * 0.42, D * 0.92, H - 2.0 * R),
            (0.0, -D * 0.46, H * 0.5),
            mats["frame"],
            "center_mullion",
        )
    for spec in r.specs:
        _build_parent_socket(body, r, spec, mats)
    return body


def _build_parent_socket(
    body, r: ResolvedVaneArrayWithIndependentPivotsConfig, spec: VaneSpec, mats: dict[str, object]
) -> None:
    x, y, z = spec.origin
    size = spec.parent_socket_size
    center = (x, y - size[1] * 0.5, z)
    backing_y = -0.006 - r.backplate_depth * 0.5
    if spec.axis_kind == "x_axis":
        _box(
            body,
            (r.width - 2.0 * r.rail, r.backplate_depth, 0.008),
            (0.0, backing_y, z),
            mats["frame_dark"],
            f"rear_open_backing_bar_{spec.index}",
        )
    else:
        _box(
            body,
            (0.008, r.backplate_depth, r.height - 2.0 * r.rail),
            (x, backing_y, r.height * 0.5),
            mats["frame_dark"],
            f"rear_open_backing_bar_{spec.index}",
        )
    _box(body, size, center, mats["pivot"], spec.socket_name)
    if r.pivot_hardware in {"round_bearing_buttons", "serviceable_bolted_bosses"}:
        if spec.axis_kind == "x_axis":
            _cyl(
                body,
                size[2] * 0.34,
                size[1] * 1.12,
                center,
                mats["edge"],
                f"bearing_button_{spec.index}",
                (math.pi / 2.0, 0.0, 0.0),
            )
        else:
            _cyl(
                body,
                size[0] * 0.34,
                size[1] * 1.12,
                center,
                mats["edge"],
                f"bearing_button_{spec.index}",
                (math.pi / 2.0, 0.0, 0.0),
            )
    if r.pivot_hardware in {"comb_rail_saddles", "serviceable_bolted_bosses"}:
        if spec.axis_kind == "x_axis":
            _box(
                body,
                (spec.length * 0.92, 0.005, 0.007),
                (x, -0.006 - 0.0025, z),
                mats["edge"],
                f"comb_crossbar_{spec.index}",
            )
        else:
            _box(
                body,
                (0.007, 0.005, spec.height * 0.86),
                (x, -0.006 - 0.0025, z),
                mats["edge"],
                f"comb_upright_{spec.index}",
            )
    if r.pivot_hardware == "serviceable_bolted_bosses":
        bolt_dx = size[0] * 0.34
        bolt_dz = size[2] * 0.34
        for k, (ox, oz) in enumerate(
            ((-bolt_dx, -bolt_dz), (bolt_dx, -bolt_dz), (-bolt_dx, bolt_dz), (bolt_dx, bolt_dz))
        ):
            _box(
                body,
                (0.006, 0.003, 0.006),
                (x + ox, -0.0015, z + oz),
                mats["accent"],
                f"socket_bolt_{spec.index}_{k}",
            )


def _build_vane_part(
    model: ArticulatedObject,
    r: ResolvedVaneArrayWithIndependentPivotsConfig,
    spec: VaneSpec,
    mats: dict[str, object],
):
    vane = model.part(f"vane_{spec.index}")
    _box(
        vane,
        spec.parent_socket_size,
        (0.0, spec.parent_socket_size[1] * 0.5, 0.0),
        mats["pivot"],
        "pivot_hub",
    )
    blade_y = r.blade_depth * 0.5 + spec.parent_socket_size[1] - 0.001
    if spec.axis_kind == "x_axis":
        _build_horizontal_vane(vane, r, spec, mats, blade_y)
    else:
        _build_vertical_vane(vane, r, spec, mats, blade_y)
    return vane


def _build_horizontal_vane(
    vane,
    r: ResolvedVaneArrayWithIndependentPivotsConfig,
    spec: VaneSpec,
    mats: dict[str, object],
    blade_y: float,
) -> None:
    rpy = (spec.pitch_angle, 0.0, 0.0)
    _box(
        vane,
        (spec.length, r.blade_depth, r.blade_thickness),
        (0.0, blade_y, 0.0),
        mats["vane"],
        "vane_blade",
        rpy,
    )
    _cyl(
        vane,
        r.blade_thickness * 0.38,
        spec.length * 1.03,
        (0.0, spec.parent_socket_size[1] * 0.52, 0.0),
        mats["pivot"],
        "through_pin",
        (0.0, math.pi / 2.0, 0.0),
    )
    _decorate_vane(vane, r, spec, mats, axis="x", blade_y=blade_y)


def _build_vertical_vane(
    vane,
    r: ResolvedVaneArrayWithIndependentPivotsConfig,
    spec: VaneSpec,
    mats: dict[str, object],
    blade_y: float,
) -> None:
    rpy = (0.0, 0.0, spec.pitch_angle)
    _box(
        vane,
        (r.blade_thickness, r.blade_depth, spec.height),
        (0.0, blade_y, 0.0),
        mats["vane"],
        "vane_blade",
        rpy,
    )
    _cyl(
        vane,
        r.blade_thickness * 0.42,
        spec.height * 1.03,
        (0.0, spec.parent_socket_size[1] * 0.52, 0.0),
        mats["pivot"],
        "through_pin",
    )
    _decorate_vane(vane, r, spec, mats, axis="z", blade_y=blade_y)


def _decorate_vane(
    vane,
    r: ResolvedVaneArrayWithIndependentPivotsConfig,
    spec: VaneSpec,
    mats: dict[str, object],
    *,
    axis: str,
    blade_y: float,
) -> None:
    if axis == "x":
        if r.vane_profile == "airfoil_lipped_vanes":
            _box(
                vane,
                (spec.length * 0.94, 0.010, r.blade_thickness * 0.70),
                (0.0, blade_y + r.blade_depth * 0.39, r.blade_thickness * 0.35),
                mats["edge"],
                "front_airfoil_lip",
            )
            _box(
                vane,
                (spec.length * 0.90, 0.008, r.blade_thickness * 0.55),
                (0.0, blade_y - r.blade_depth * 0.36, -r.blade_thickness * 0.32),
                mats["edge"],
                "rear_airfoil_lip",
            )
        elif r.vane_profile == "perforated_light_vanes":
            for k, x in enumerate((-0.30, -0.10, 0.10, 0.30)):
                _box(
                    vane,
                    (spec.length * 0.07, 0.004, r.blade_thickness * 0.50),
                    (spec.length * x, blade_y + r.blade_depth * 0.18, 0.0),
                    mats["edge"],
                    f"pressed_slot_{k}",
                )
        elif r.vane_profile == "split_panel_vanes":
            _box(
                vane,
                (0.010, r.blade_depth * 0.86, r.blade_thickness * 1.15),
                (0.0, blade_y, 0.0),
                mats["edge"],
                "split_center_rib",
            )
            _box(
                vane,
                (spec.length * 0.92, 0.006, r.blade_thickness * 0.70),
                (0.0, blade_y, r.blade_thickness * 0.72),
                mats["edge"],
                "raised_top_seam",
            )
    else:
        if r.vane_profile == "airfoil_lipped_vanes":
            _box(
                vane,
                (r.blade_thickness * 0.70, 0.010, spec.height * 0.94),
                (r.blade_thickness * 0.35, blade_y + r.blade_depth * 0.39, 0.0),
                mats["edge"],
                "front_airfoil_lip",
            )
            _box(
                vane,
                (r.blade_thickness * 0.55, 0.008, spec.height * 0.90),
                (-r.blade_thickness * 0.32, blade_y - r.blade_depth * 0.36, 0.0),
                mats["edge"],
                "rear_airfoil_lip",
            )
        elif r.vane_profile == "perforated_light_vanes":
            for k, z in enumerate((-0.30, -0.10, 0.10, 0.30)):
                _box(
                    vane,
                    (r.blade_thickness * 0.50, 0.004, spec.height * 0.07),
                    (0.0, blade_y + r.blade_depth * 0.18, spec.height * z),
                    mats["edge"],
                    f"pressed_slot_{k}",
                )
        elif r.vane_profile == "split_panel_vanes":
            _box(
                vane,
                (r.blade_thickness * 1.15, r.blade_depth * 0.86, 0.010),
                (0.0, blade_y, 0.0),
                mats["edge"],
                "split_center_rib",
            )
            _box(
                vane,
                (r.blade_thickness * 0.70, 0.006, spec.height * 0.92),
                (r.blade_thickness * 0.72, blade_y, 0.0),
                mats["edge"],
                "raised_side_seam",
            )


def build_vane_array_with_independent_pivots(
    config: VaneArrayWithIndependentPivotsConfig | None = None,
    *,
    assets: AssetContext | None = None,
) -> ArticulatedObject:
    cfg = config or VaneArrayWithIndependentPivotsConfig()
    r = resolve_config(cfg)
    model = ArticulatedObject(name=r.name, assets=assets)
    mats = {
        key: _mat(model, r, key)
        for key in ("frame", "frame_dark", "vane", "edge", "pivot", "accent")
    }
    frame = _build_frame(model, r, mats)
    limits = MotionLimits(effort=1.2, velocity=1.6, lower=-0.95, upper=0.95)
    for spec in r.specs:
        vane = _build_vane_part(model, r, spec, mats)
        model.articulation(
            f"vane_{spec.index}_independent_pivot",
            ArticulationType.REVOLUTE,
            parent=frame,
            child=vane,
            origin=Origin(xyz=spec.origin),
            axis=spec.axis,
            motion_limits=limits,
            mating=MatingContract(
                parent_face_geometry=spec.socket_name,
                parent_face_side="positive_y",
                child_face_geometry="pivot_hub",
                child_face_side="negative_y",
                contact_tol=0.002,
            ),
        )
    model.meta["slot_choices"] = slot_choices_for_config(r)
    return model


def build_seeded_vane_array_with_independent_pivots(
    seed: int,
    *,
    assets: AssetContext | None = None,
) -> ArticulatedObject:
    return build_vane_array_with_independent_pivots(config_from_seed(seed), assets=assets)


def _allow_expected_overlaps(ctx: TestContext, model: ArticulatedObject) -> None:
    if "frame" not in {p.name for p in model.parts}:
        return
    frame = model.get_part("frame")
    for part in model.parts:
        if not part.name.startswith("vane_"):
            continue
        index = part.name.rsplit("_", 1)[-1]
        for parent_elem in (f"rear_open_backing_bar_{index}", f"pivot_socket_{index}"):
            try:
                ctx.allow_overlap(
                    frame,
                    part,
                    elem_a=parent_elem,
                    elem_b="pivot_hub",
                    reason="vane hub is seated exactly at the visible pivot socket",
                )
            except Exception:
                pass


def run_vane_array_with_independent_pivots_tests(
    object_model: ArticulatedObject,
    config: VaneArrayWithIndependentPivotsConfig,
) -> TestReport:
    r = resolve_config(config)
    ctx = TestContext(object_model)
    _allow_expected_overlaps(ctx, object_model)
    ctx.check_model_valid()
    ctx.check_mesh_assets_ready()
    ctx.fail_if_isolated_parts()
    ctx.fail_if_parts_overlap_in_current_pose()
    ctx.fail_if_articulation_origin_far_from_geometry(tol=0.015)
    ctx.fail_if_joint_mating_has_gap()

    part_names = {part.name for part in object_model.parts}
    joint_names = {joint.name for joint in object_model.joints}
    ctx.check("frame_part_present", "frame" in part_names, details=str(sorted(part_names)))
    vane_parts = [name for name in part_names if name.startswith("vane_")]
    ctx.check(
        "vane_part_count",
        len(vane_parts) == r.vane_count,
        details=f"expected {r.vane_count}, got {len(vane_parts)}",
    )
    pivot_joints = [
        joint for joint in object_model.joints if joint.name.endswith("_independent_pivot")
    ]
    ctx.check(
        "pivot_joint_count",
        len(pivot_joints) == r.vane_count,
        details=f"expected {r.vane_count}, got {len(pivot_joints)}",
    )
    for spec in r.specs:
        joint_name = f"vane_{spec.index}_independent_pivot"
        ctx.check(f"{joint_name}_present", joint_name in joint_names, details=joint_name)
    for joint in pivot_joints:
        ctx.check(
            f"{joint.name}_revolute",
            joint.articulation_type == ArticulationType.REVOLUTE,
            details=str(joint.articulation_type),
        )
        ctx.check(
            f"{joint.name}_has_mating",
            joint.mating is not None,
            details="each independent vane must mate to a visible socket",
        )
    return ctx.report()


__all__ = [
    "VaneArrayWithIndependentPivotsConfig",
    "ResolvedVaneArrayWithIndependentPivotsConfig",
    "build_vane_array_with_independent_pivots",
    "build_seeded_vane_array_with_independent_pivots",
    "config_from_seed",
    "resolve_config",
    "run_vane_array_with_independent_pivots_tests",
    "slot_choices_for_config",
    "slot_choices_for_seed",
    "with_overrides",
]
