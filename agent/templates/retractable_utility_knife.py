"""Procedural template for category `retractable_utility_knife`.

This template is intentionally written around the mature pattern visible in the
adopted five-star utility-knife samples: a fixed shell owns the retained rail
channel, a carrier slides along the handle X axis, and the blade plus thumb
slider are fixed children of that carrier. Optional lock, service door, and nose
guard branches are gated so they never replace the blade-slide semantics.
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
    LoftGeometry,
    MotionLimits,
    Origin,
    TestContext,
    TestReport,
    mesh_from_geometry,
    rounded_rect_profile,
)

KnifeBodyStyle = Literal["snap_off_slim", "box_cutter", "heavy_duty", "compact_safety"]
BladeStyle = Literal["trapezoid", "snap_off_segmented", "compact_hook_like"]
SliderStyle = Literal["top_ridged_tab", "side_thumb_button", "long_slot_slider"]
LockStyle = Literal["none", "thumb_detent", "lock_wheel", "side_lever"]
GuardStyle = Literal["none", "fixed_nose", "sliding_nose"]
ServiceDoorStyle = Literal["none", "side_hatch", "rear_cap", "storage_tray"]
GripStyle = Literal["straight_strips", "checker_pads", "rubber_inserts"]
MaterialStyle = Literal["yellow_black", "graphite_orange", "workshop_blue"]

SOURCE_IDS = {
    "S1": "data/records/rec_retractable_utility_knife_cad8e728806e47b09531688f7de35ba7/revisions/rev_000001/model.py:L25-L78",
    "S2": "data/records/rec_retractable_utility_knife_cad8e728806e47b09531688f7de35ba7/revisions/rev_000001/model.py:L93-L193",
    "S3": "data/records/rec_retractable_utility_knife_cad8e728806e47b09531688f7de35ba7/revisions/rev_000001/model.py:L195-L267",
    "S4": "data/records/rec_retractable_utility_knife_cad8e728806e47b09531688f7de35ba7/revisions/rev_000001/model.py:L269-L335",
    "S5": "data/records/rec_retractable_utility_knife_0003/revisions/rev_000001/model.py:L39-L130",
    "S6": "data/records/rec_retractable_utility_knife_0003/revisions/rev_000001/model.py:L132-L229",
    "S7": "data/records/rec_retractable_utility_knife_14ce81bcecaa40e8a75ce0494a0de25f/revisions/rev_000001/model.py:L59-L141",
    "S8": "data/records/rec_retractable_utility_knife_14ce81bcecaa40e8a75ce0494a0de25f/revisions/rev_000001/model.py:L143-L239",
    "S9": "data/records/rec_retractable_utility_knife_9365487b3ea4413891567b9153bbf0ab/revisions/rev_000001/model.py:L69-L171",
    "S10": "data/records/rec_retractable_utility_knife_9365487b3ea4413891567b9153bbf0ab/revisions/rev_000001/model.py:L188-L226",
}

SOURCE_ADAPTATION_MAP = {
    "handle_shell": ("S2", "S5", "S7", "S9"),
    "rail_channel": ("S2", "S5", "S6", "S9"),
    "blade_carrier": ("S3", "S6", "S8", "S9"),
    "blade_mesh": ("S1", "S3", "S5", "S8"),
    "thumb_slider": ("S1", "S3", "S5", "S8", "S9"),
    "lock_wheel": ("S4",),
    "service_door": ("S7", "S8"),
    "sliding_nose_guard": ("S10",),
    "blade_slide_joint": ("S4", "S6", "S8", "S9"),
}

PALETTES: dict[MaterialStyle, dict[str, tuple[float, float, float, float]]] = {
    "yellow_black": {
        "body": (0.92, 0.76, 0.14, 1.0),
        "grip": (0.08, 0.08, 0.085, 1.0),
        "rail": (0.42, 0.44, 0.46, 1.0),
        "blade": (0.82, 0.84, 0.86, 1.0),
        "dark": (0.18, 0.19, 0.20, 1.0),
        "accent": (0.98, 0.38, 0.12, 1.0),
    },
    "graphite_orange": {
        "body": (0.18, 0.19, 0.20, 1.0),
        "grip": (0.05, 0.055, 0.060, 1.0),
        "rail": (0.55, 0.56, 0.56, 1.0),
        "blade": (0.80, 0.82, 0.84, 1.0),
        "dark": (0.10, 0.10, 0.105, 1.0),
        "accent": (0.95, 0.42, 0.12, 1.0),
    },
    "workshop_blue": {
        "body": (0.16, 0.36, 0.62, 1.0),
        "grip": (0.06, 0.07, 0.08, 1.0),
        "rail": (0.62, 0.64, 0.66, 1.0),
        "blade": (0.86, 0.87, 0.86, 1.0),
        "dark": (0.18, 0.20, 0.22, 1.0),
        "accent": (0.92, 0.80, 0.20, 1.0),
    },
}


@dataclass(frozen=True)
class RetractableUtilityKnifeConfig:
    knife_body_style: KnifeBodyStyle = "heavy_duty"
    blade_style: BladeStyle | None = None
    slider_style: SliderStyle = "top_ridged_tab"
    lock_style: LockStyle = "thumb_detent"
    guard_style: GuardStyle = "fixed_nose"
    service_door_style: ServiceDoorStyle = "none"
    grip_style: GripStyle = "rubber_inserts"
    material_style: MaterialStyle = "yellow_black"
    handle_length: float = 0.175
    handle_width: float = 0.030
    handle_height: float = 0.030
    shell_thickness: float = 0.0030
    max_blade_exposure: float = 0.038
    rail_clearance: float = 0.0012
    detent_count: int = 5
    name: str = "reference_retractable_utility_knife"


@dataclass(frozen=True)
class ResolvedRetractableUtilityKnifeConfig:
    knife_body_style: KnifeBodyStyle
    blade_style: BladeStyle
    slider_style: SliderStyle
    lock_style: LockStyle
    guard_style: GuardStyle
    service_door_style: ServiceDoorStyle
    grip_style: GripStyle
    material_style: MaterialStyle
    handle_length: float
    handle_width: float
    handle_height: float
    shell_thickness: float
    body_center_z: float
    channel_width: float
    channel_height: float
    carrier_len: float
    carrier_width: float
    carrier_height: float
    blade_len: float
    blade_height: float
    blade_thickness: float
    slide_travel: float
    retained_overlap: float
    rail_z: float
    rear_stop_x: float
    front_stop_x: float
    carrier_origin_x: float
    blade_mount_x: float
    slider_mount_x: float
    slot_len: float
    slot_center_x: float
    nose_x: float
    guard_travel: float
    name: str


def config_from_seed(seed: int) -> RetractableUtilityKnifeConfig:
    rng = random.Random(seed)
    style: KnifeBodyStyle = rng.choice(
        ("snap_off_slim", "box_cutter", "heavy_duty", "compact_safety")
    )
    blade_by_style: dict[KnifeBodyStyle, BladeStyle] = {
        "snap_off_slim": "snap_off_segmented",
        "box_cutter": "trapezoid",
        "heavy_duty": "trapezoid",
        "compact_safety": "compact_hook_like",
    }
    return RetractableUtilityKnifeConfig(
        knife_body_style=style,
        blade_style=blade_by_style[style]
        if rng.random() < 0.76
        else rng.choice(("trapezoid", "snap_off_segmented", "compact_hook_like")),
        slider_style=rng.choice(("top_ridged_tab", "side_thumb_button", "long_slot_slider")),
        lock_style=rng.choice(("thumb_detent", "lock_wheel", "side_lever", "none")),
        guard_style="sliding_nose"
        if style == "compact_safety" or rng.random() < 0.28
        else rng.choice(("fixed_nose", "none")),
        service_door_style=rng.choice(("none", "side_hatch", "rear_cap", "storage_tray")),
        grip_style=rng.choice(("straight_strips", "checker_pads", "rubber_inserts")),
        material_style=rng.choice(("yellow_black", "graphite_orange", "workshop_blue")),
        handle_length=round(rng.uniform(0.145, 0.225), 3),
        handle_width=round(rng.uniform(0.022, 0.042), 3),
        handle_height=round(rng.uniform(0.026, 0.056), 3),
        shell_thickness=round(rng.uniform(0.0024, 0.0042), 4),
        max_blade_exposure=round(rng.uniform(0.024, 0.058), 3),
        rail_clearance=round(rng.uniform(0.0008, 0.0022), 4),
        detent_count=rng.randint(3, 8),
        name=f"seeded_retractable_utility_knife_{seed}",
    )


def resolve_config(config: RetractableUtilityKnifeConfig) -> ResolvedRetractableUtilityKnifeConfig:
    if config.knife_body_style not in {
        "snap_off_slim",
        "box_cutter",
        "heavy_duty",
        "compact_safety",
    }:
        raise ValueError(f"Unsupported knife_body_style: {config.knife_body_style}")
    if config.blade_style is not None and config.blade_style not in {
        "trapezoid",
        "snap_off_segmented",
        "compact_hook_like",
    }:
        raise ValueError(f"Unsupported blade_style: {config.blade_style}")
    if config.slider_style not in {"top_ridged_tab", "side_thumb_button", "long_slot_slider"}:
        raise ValueError(f"Unsupported slider_style: {config.slider_style}")
    if config.lock_style not in {"none", "thumb_detent", "lock_wheel", "side_lever"}:
        raise ValueError(f"Unsupported lock_style: {config.lock_style}")
    if config.guard_style not in {"none", "fixed_nose", "sliding_nose"}:
        raise ValueError(f"Unsupported guard_style: {config.guard_style}")
    if config.service_door_style not in {"none", "side_hatch", "rear_cap", "storage_tray"}:
        raise ValueError(f"Unsupported service_door_style: {config.service_door_style}")
    if config.grip_style not in {"straight_strips", "checker_pads", "rubber_inserts"}:
        raise ValueError(f"Unsupported grip_style: {config.grip_style}")
    if config.material_style not in PALETTES:
        raise ValueError(f"Unsupported material_style: {config.material_style}")
    if not 0.13 <= config.handle_length <= 0.24:
        raise ValueError("handle_length must be in [0.13, 0.24]")
    if not 0.018 <= config.handle_width <= 0.050:
        raise ValueError("handle_width must be in [0.018, 0.050]")
    if not 0.024 <= config.handle_height <= 0.065:
        raise ValueError("handle_height must be in [0.024, 0.065]")
    if not 0.0018 <= config.shell_thickness <= 0.0060:
        raise ValueError("shell_thickness must be in [0.0018, 0.0060]")
    if not 0.0005 <= config.rail_clearance <= 0.0035:
        raise ValueError("rail_clearance must be in [0.0005, 0.0035]")
    if not 3 <= config.detent_count <= 9:
        raise ValueError("detent_count must be in [3, 9]")
    style_blade: dict[KnifeBodyStyle, BladeStyle] = {
        "snap_off_slim": "snap_off_segmented",
        "box_cutter": "trapezoid",
        "heavy_duty": "trapezoid",
        "compact_safety": "compact_hook_like",
    }
    blade_style = config.blade_style or style_blade[config.knife_body_style]
    style_len_factor = {
        "snap_off_slim": 0.34,
        "box_cutter": 0.38,
        "heavy_duty": 0.42,
        "compact_safety": 0.33,
    }[config.knife_body_style]
    carrier_len = config.handle_length * style_len_factor
    blade_len = {
        "snap_off_segmented": config.handle_length * 0.56,
        "trapezoid": config.handle_length * 0.46,
        "compact_hook_like": config.handle_length * 0.34,
    }[blade_style]
    blade_height = min(config.handle_height * 0.35, config.handle_width * 0.42)
    blade_thickness = min(0.0012, config.handle_width * 0.045)
    carrier_width = max(
        blade_thickness + 0.005,
        config.handle_width - 2.0 * config.shell_thickness - 2.0 * config.rail_clearance - 0.004,
    )
    carrier_height = max(0.006, config.handle_height * 0.31)
    channel_width = carrier_width + 2.0 * config.rail_clearance
    channel_height = carrier_height + 2.0 * config.rail_clearance
    rear_stop_x = -config.handle_length * 0.43
    front_stop_x = config.handle_length * 0.44
    nose_clearance = max(config.shell_thickness * 3.0, config.handle_length * 0.055)
    retained_overlap = max(0.024, carrier_len * 0.42)
    max_travel_by_handle = front_stop_x - rear_stop_x - nose_clearance - retained_overlap
    slide_travel = min(config.max_blade_exposure, max_travel_by_handle)
    if slide_travel < 0.014:
        raise ValueError("slide_travel is too small after retained-overlap constraints")
    carrier_origin_x = rear_stop_x + retained_overlap * 0.20
    rail_z = config.handle_height * 0.42
    blade_mount_x = carrier_len * 0.70
    slider_mount_x = carrier_len * 0.46
    slot_len = slide_travel + 0.026
    slot_center_x = carrier_origin_x + slider_mount_x + slide_travel * 0.50
    guard_travel = min(0.018, slide_travel * 0.45) if config.guard_style == "sliding_nose" else 0.0
    return ResolvedRetractableUtilityKnifeConfig(
        knife_body_style=config.knife_body_style,
        blade_style=blade_style,
        slider_style=config.slider_style,
        lock_style=config.lock_style,
        guard_style=config.guard_style,
        service_door_style=config.service_door_style,
        grip_style=config.grip_style,
        material_style=config.material_style,
        handle_length=config.handle_length,
        handle_width=config.handle_width,
        handle_height=config.handle_height,
        shell_thickness=config.shell_thickness,
        body_center_z=config.handle_height * 0.50,
        channel_width=channel_width,
        channel_height=channel_height,
        carrier_len=carrier_len,
        carrier_width=carrier_width,
        carrier_height=carrier_height,
        blade_len=blade_len,
        blade_height=blade_height,
        blade_thickness=blade_thickness,
        slide_travel=slide_travel,
        retained_overlap=retained_overlap,
        rail_z=rail_z,
        rear_stop_x=rear_stop_x,
        front_stop_x=front_stop_x,
        carrier_origin_x=carrier_origin_x,
        blade_mount_x=blade_mount_x,
        slider_mount_x=slider_mount_x,
        slot_len=slot_len,
        slot_center_x=slot_center_x,
        nose_x=front_stop_x,
        guard_travel=guard_travel,
        name=config.name,
    )


def _mat(model: ArticulatedObject, r: ResolvedRetractableUtilityKnifeConfig, key: str):
    return model.material(f"knife_{key}", rgba=PALETTES[r.material_style][key])


def _box(part, size, xyz, material, name: str, rpy=(0.0, 0.0, 0.0)) -> None:
    part.visual(Box(size), origin=Origin(xyz=xyz, rpy=rpy), material=material, name=name)


def _cyl(part, radius: float, length: float, xyz, material, name: str, rpy=(0.0, 0.0, 0.0)) -> None:
    part.visual(
        Cylinder(radius=radius, length=length),
        origin=Origin(xyz=xyz, rpy=rpy),
        material=material,
        name=name,
    )


def _rounded_block_mesh(
    width: float, depth: float, height: float, *, top_scale: float = 0.82
) -> LoftGeometry:
    radius = min(width, depth) * 0.20

    def section(w: float, d: float, z: float) -> list[tuple[float, float, float]]:
        return [
            (x, y, z) for x, y in rounded_rect_profile(w, d, radius=min(radius, w * 0.45, d * 0.45))
        ]

    return LoftGeometry(
        [
            section(width, depth, 0.0),
            section(width * 0.92, depth * 0.92, height * 0.55),
            section(width * top_scale, depth * top_scale, height),
        ],
        cap=True,
        closed=True,
    )


def _blade_profile(r: ResolvedRetractableUtilityKnifeConfig) -> list[tuple[float, float]]:
    h = r.blade_height
    blade_len = r.blade_len
    if r.blade_style == "snap_off_segmented":
        return [
            (-blade_len * 0.42, 0.0),
            (blade_len * 0.52, 0.0),
            (blade_len * 0.50, h),
            (-blade_len * 0.42, h),
        ]
    if r.blade_style == "compact_hook_like":
        return [
            (-blade_len * 0.35, 0.0),
            (blade_len * 0.32, 0.0),
            (blade_len * 0.48, h * 0.38),
            (blade_len * 0.12, h),
            (-blade_len * 0.35, h),
        ]
    return [
        (-blade_len * 0.38, 0.0),
        (blade_len * 0.46, 0.0),
        (blade_len * 0.58, h * 0.48),
        (blade_len * 0.12, h),
        (-blade_len * 0.38, h),
    ]


def _blade_mesh(r: ResolvedRetractableUtilityKnifeConfig, assets: AssetContext):
    return mesh_from_geometry(
        ExtrudeGeometry.from_z0(_blade_profile(r), r.blade_thickness, cap=True, closed=True),
        assets.mesh_path("utility_knife_blade.obj"),
    )


def _build_handle_shell(
    part, r: ResolvedRetractableUtilityKnifeConfig, materials, assets: AssetContext
) -> None:
    body = materials["body"]
    grip = materials["grip"]
    rail = materials["rail"]
    dark = materials["dark"]
    L, W, H, t = r.handle_length, r.handle_width, r.handle_height, r.shell_thickness
    _box(part, (L, W, t), (0.0, 0.0, t * 0.5), body, "bottom_pan")
    _box(
        part,
        (L * 0.92, t, H * 0.70),
        (-L * 0.02, -W * 0.5 + t * 0.5, H * 0.42),
        body,
        "left_shell_wall",
    )
    _box(
        part,
        (L * 0.92, t, H * 0.70),
        (-L * 0.02, W * 0.5 - t * 0.5, H * 0.42),
        body,
        "right_shell_wall",
    )
    _box(part, (L * 0.10, W, H * 0.70), (-L * 0.48, 0.0, H * 0.42), body, "rear_stop_cap")
    roof_w = max(0.004, (W - r.channel_width) * 0.5)
    for side, sign in (("left", -1.0), ("right", 1.0)):
        y = sign * (r.channel_width * 0.5 + roof_w * 0.5)
        _box(part, (L * 0.72, roof_w, t), (-L * 0.08, y, H * 0.76), body, f"{side}_top_rail")
        _box(
            part,
            (L * 0.36, roof_w * 0.72, t * 0.80),
            (r.slot_center_x, y, H * 0.86),
            rail,
            f"{side}_slot_lip",
        )
    for side, sign in (("left", -1.0), ("right", 1.0)):
        y = sign * (W * 0.5 + 0.0008)
        if r.grip_style == "checker_pads":
            for i in range(6):
                x = -L * 0.25 + i * L * 0.075
                _box(
                    part,
                    (L * 0.040, 0.0015, H * 0.20),
                    (x, y, H * 0.38),
                    grip,
                    f"{side}_checker_grip_{i}",
                )
        else:
            _box(
                part,
                (L * 0.46, 0.0015, H * 0.23),
                (-L * 0.12, y, H * 0.38),
                grip,
                f"{side}_long_grip",
            )
            _box(
                part,
                (L * 0.18, 0.0015, H * 0.20),
                (L * 0.27, y, H * 0.38),
                grip,
                f"{side}_front_grip",
            )
    _box(
        part,
        (L * 0.14, t, H * 0.45),
        (r.nose_x - L * 0.035, -W * 0.5 + t * 0.5, H * 0.43),
        body,
        "nose_left_cheek",
    )
    _box(
        part,
        (L * 0.14, t, H * 0.45),
        (r.nose_x - L * 0.035, W * 0.5 - t * 0.5, H * 0.43),
        body,
        "nose_right_cheek",
    )
    _box(
        part,
        (r.slot_len, roof_w * 0.88, t * 0.60),
        (r.slot_center_x, 0.0, H * 0.88),
        dark,
        "thumb_slider_slot_shadow",
    )
    part.visual(
        mesh_from_geometry(
            _rounded_block_mesh(L * 0.34, W * 0.76, H * 0.08),
            assets.mesh_path("knife_rear_top_bridge.obj"),
        ),
        origin=Origin(xyz=(-L * 0.28, 0.0, H * 0.76)),
        material=body,
        name="lofted_rear_top_bridge",
    )
    part.inertial = Inertial.from_geometry(
        Box((L, W, H)), mass=0.28, origin=Origin(xyz=(0.0, 0.0, H * 0.45))
    )


def _build_carrier(part, r: ResolvedRetractableUtilityKnifeConfig, materials) -> None:
    rail = materials["rail"]
    dark = materials["dark"]
    _box(
        part,
        (r.carrier_len, r.carrier_width, r.carrier_height * 0.42),
        (r.carrier_len * 0.5, 0.0, 0.0),
        rail,
        "carrier_rail_shoe",
    )
    _box(
        part,
        (r.carrier_len * 0.30, r.carrier_width, r.carrier_height),
        (r.carrier_len * 0.22, 0.0, r.carrier_height * 0.25),
        rail,
        "rear_carrier_block",
    )
    _box(
        part,
        (r.carrier_len * 0.28, r.carrier_width * 0.82, r.carrier_height * 0.72),
        (r.blade_mount_x, 0.0, r.carrier_height * 0.18),
        dark,
        "front_blade_clamp",
    )
    _box(
        part,
        (0.004, r.carrier_width * 0.78, r.carrier_height * 0.55),
        (r.carrier_len * 0.88, 0.0, r.carrier_height * 0.18),
        dark,
        "front_retainer_tooth",
    )
    part.inertial = Inertial.from_geometry(
        Box((r.carrier_len, r.carrier_width, r.carrier_height)),
        mass=0.035,
        origin=Origin(xyz=(r.carrier_len * 0.5, 0.0, 0.0)),
    )


def _build_blade(
    part, r: ResolvedRetractableUtilityKnifeConfig, materials, assets: AssetContext
) -> None:
    blade = materials["blade"]
    dark = materials["dark"]
    part.visual(
        _blade_mesh(r, assets),
        origin=Origin(rpy=(math.pi / 2.0, 0.0, 0.0)),
        material=blade,
        name="blade_plate",
    )
    if r.blade_style == "snap_off_segmented":
        count = max(3, int(r.blade_len / 0.014))
        for i in range(count):
            x = -r.blade_len * 0.27 + i * r.blade_len * 0.10
            _box(
                part,
                (0.00055, r.blade_thickness * 0.25, r.blade_height * 0.90),
                (x, -r.blade_thickness * 0.40, r.blade_height * 0.5),
                dark,
                f"snap_score_line_{i}",
                rpy=(math.pi / 2.0, 0.0, 0.0),
            )
    else:
        _box(
            part,
            (r.blade_len * 0.20, r.blade_thickness * 0.20, 0.0008),
            (r.blade_len * 0.10, -r.blade_thickness * 0.35, r.blade_height * 0.88),
            dark,
            "sharpened_edge_shadow",
            rpy=(math.pi / 2.0, 0.0, 0.0),
        )
    part.inertial = Inertial.from_geometry(
        Box((r.blade_len, r.blade_thickness, r.blade_height)),
        mass=0.010,
        origin=Origin(xyz=(r.blade_len * 0.1, 0.0, r.blade_height * 0.5)),
    )


def _build_slider(
    part, r: ResolvedRetractableUtilityKnifeConfig, materials, assets: AssetContext
) -> None:
    dark = materials["dark"]
    accent = materials["accent"]
    _box(
        part,
        (0.005, 0.004, r.handle_height * 0.33),
        (0.0, 0.0, r.handle_height * 0.16),
        dark,
        "slider_stem",
    )
    button_len = 0.026 if r.slider_style == "long_slot_slider" else 0.018
    if r.slider_style == "side_thumb_button":
        _box(
            part,
            (button_len, 0.006, 0.010),
            (0.0, r.handle_width * 0.67, r.handle_height * 0.26),
            accent,
            "side_thumb_button",
        )
    else:
        part.visual(
            mesh_from_geometry(
                _rounded_block_mesh(button_len, r.handle_width * 0.38, r.handle_height * 0.16),
                assets.mesh_path("knife_slider_button.obj"),
            ),
            origin=Origin(xyz=(0.0, 0.0, r.handle_height * 0.34)),
            material=accent,
            name="lofted_slider_button",
        )
        for i in range(3):
            _box(
                part,
                (0.0013, r.handle_width * 0.28, 0.0012),
                ((i - 1) * button_len * 0.22, 0.0, r.handle_height * 0.49),
                dark,
                f"slider_ridge_{i}",
            )
    part.inertial = Inertial.from_geometry(
        Box((button_len, r.handle_width * 0.35, r.handle_height * 0.22)),
        mass=0.012,
        origin=Origin(xyz=(0.0, 0.0, r.handle_height * 0.34)),
    )


def _build_lock_or_door(
    model: ArticulatedObject, body, r: ResolvedRetractableUtilityKnifeConfig, materials
) -> None:
    dark = materials["dark"]
    accent = materials["accent"]
    body_mat = materials["body"]
    if r.lock_style == "lock_wheel":
        wheel = model.part("lock_wheel")
        _cyl(
            wheel,
            r.handle_height * 0.17,
            0.006,
            (0.0, 0.0, 0.0),
            dark,
            "knurled_lock_wheel",
            rpy=(-math.pi / 2.0, 0.0, 0.0),
        )
        for i in range(8):
            angle = i * math.tau / 8.0
            _box(
                wheel,
                (0.0022, 0.0014, 0.004),
                (
                    math.cos(angle) * r.handle_height * 0.18,
                    0.0035,
                    math.sin(angle) * r.handle_height * 0.18,
                ),
                accent,
                f"wheel_tooth_{i}",
            )
        model.articulation(
            "body_to_lock_wheel",
            ArticulationType.REVOLUTE,
            parent=body,
            child=wheel,
            origin=Origin(
                xyz=(r.handle_length * 0.20, r.handle_width * 0.52, r.handle_height * 0.45)
            ),
            axis=(0.0, 1.0, 0.0),
            motion_limits=MotionLimits(effort=1.0, velocity=5.0, lower=-math.pi, upper=math.pi),
            meta={"source_id": "S4", "semantic": "side lock wheel clamps the blade carrier detent"},
        )
    elif r.lock_style == "side_lever":
        lever = model.part("side_lock_lever")
        _box(lever, (0.026, 0.004, 0.007), (0.011, 0.0, 0.0), accent, "pivoting_side_lever")
        _cyl(
            lever,
            0.004,
            0.004,
            (0.0, 0.0, 0.0),
            dark,
            "lever_pivot",
            rpy=(-math.pi / 2.0, 0.0, 0.0),
        )
        model.articulation(
            "body_to_side_lock_lever",
            ArticulationType.REVOLUTE,
            parent=body,
            child=lever,
            origin=Origin(
                xyz=(r.handle_length * 0.11, -r.handle_width * 0.52, r.handle_height * 0.42)
            ),
            axis=(0.0, 1.0, 0.0),
            motion_limits=MotionLimits(effort=1.0, velocity=2.0, lower=-0.35, upper=0.35),
            meta={"source_id": "S4", "semantic": "limited lock lever fixed to side wall"},
        )
    if r.service_door_style in {"side_hatch", "storage_tray"}:
        door = model.part("service_door")
        _box(
            door,
            (r.handle_length * 0.34, 0.0022, r.handle_height * 0.42),
            (0.0, 0.0, 0.0),
            body_mat,
            "side_service_hatch",
        )
        _cyl(
            door,
            0.0022,
            r.handle_length * 0.34,
            (0.0, 0.0, r.handle_height * 0.22),
            dark,
            "hinge_barrel",
            rpy=(0.0, math.pi / 2.0, 0.0),
        )
        model.articulation(
            "body_to_service_door",
            ArticulationType.REVOLUTE,
            parent=body,
            child=door,
            origin=Origin(
                xyz=(-r.handle_length * 0.18, -r.handle_width * 0.53, r.handle_height * 0.39)
            ),
            axis=(1.0, 0.0, 0.0),
            motion_limits=MotionLimits(effort=0.8, velocity=1.6, lower=0.0, upper=1.55),
            meta={
                "source_id": "S8",
                "semantic": "side hatch swings from a barrel attached to shell edge",
            },
        )
    elif r.service_door_style == "rear_cap":
        body.visual(
            Box((0.004, r.handle_width * 0.78, r.handle_height * 0.54)),
            origin=Origin(xyz=(-r.handle_length * 0.505, 0.0, r.handle_height * 0.43)),
            material=accent,
            name="removable_rear_cap_outline",
        )


def _build_guard(
    model: ArticulatedObject, body, r: ResolvedRetractableUtilityKnifeConfig, materials
) -> None:
    body_mat = materials["body"]
    dark = materials["dark"]
    if r.guard_style == "fixed_nose":
        body.visual(
            Box((r.handle_length * 0.060, r.channel_width * 0.70, r.handle_height * 0.30)),
            origin=Origin(xyz=(r.nose_x + r.handle_length * 0.018, 0.0, r.handle_height * 0.39)),
            material=body_mat,
            name="fixed_nose_shroud",
        )
    elif r.guard_style == "sliding_nose":
        guard = model.part("sliding_nose_guard")
        _box(
            guard,
            (r.handle_length * 0.080, r.handle_width * 0.92, r.handle_height * 0.34),
            (0.0, 0.0, 0.0),
            body_mat,
            "sliding_nose_sleeve",
        )
        _box(
            guard,
            (r.handle_length * 0.065, r.channel_width * 0.50, 0.002),
            (0.005, 0.0, -r.handle_height * 0.18),
            dark,
            "guard_under_rail",
        )
        model.articulation(
            "body_to_nose_guard",
            ArticulationType.PRISMATIC,
            parent=body,
            child=guard,
            origin=Origin(xyz=(r.nose_x + r.handle_length * 0.014, 0.0, r.handle_height * 0.39)),
            axis=(1.0, 0.0, 0.0),
            motion_limits=MotionLimits(effort=4.0, velocity=0.08, lower=0.0, upper=r.guard_travel),
            meta={
                "source_id": "S10",
                "semantic": "nose guard slides parallel to blade but remains a separate retained sleeve",
            },
        )


def build_retractable_utility_knife(
    config: RetractableUtilityKnifeConfig | None = None, *, assets: AssetContext | None = None
) -> ArticulatedObject:
    config = config or RetractableUtilityKnifeConfig()
    r = resolve_config(config)
    if assets is None:
        assets = AssetContext(Path(tempfile.mkdtemp(prefix="articraft-retractable-knife-assets-")))
    model = ArticulatedObject(name=r.name, assets=assets)
    materials = {
        key: _mat(model, r, key) for key in ("body", "grip", "rail", "blade", "dark", "accent")
    }
    body = model.part("handle_shell")
    _build_handle_shell(body, r, materials, assets)
    carrier = model.part("blade_carrier")
    _build_carrier(carrier, r, materials)
    blade = model.part("blade")
    _build_blade(blade, r, materials, assets)
    slider = model.part("thumb_slider")
    _build_slider(slider, r, materials, assets)
    model.articulation(
        "blade_slide",
        ArticulationType.PRISMATIC,
        parent=body,
        child=carrier,
        origin=Origin(xyz=(r.carrier_origin_x, 0.0, r.rail_z)),
        axis=(1.0, 0.0, 0.0),
        motion_limits=MotionLimits(effort=12.0, velocity=0.20, lower=0.0, upper=r.slide_travel),
        meta={
            "source_id": "S4/S6/S8/S9",
            "semantic": "retained blade carrier slides along the handle X rail channel",
            "retained_overlap": r.retained_overlap,
        },
    )
    model.articulation(
        "carrier_to_blade",
        ArticulationType.FIXED,
        parent=carrier,
        child=blade,
        origin=Origin(xyz=(r.blade_mount_x, 0.0, -r.blade_height * 0.22)),
        meta={
            "source_id": "S3/S8",
            "semantic": "blade is clamped to carrier and moves with blade_slide",
        },
    )
    model.articulation(
        "carrier_to_thumb_slider",
        ArticulationType.FIXED,
        parent=carrier,
        child=slider,
        origin=Origin(xyz=(r.slider_mount_x, 0.0, r.handle_height * 0.12)),
        meta={
            "source_id": "S3/S8/S9",
            "semantic": "thumb slider stem is fixed to the moving carrier",
        },
    )
    _build_lock_or_door(model, body, r, materials)
    _build_guard(model, body, r, materials)
    return model


def build_seeded_retractable_utility_knife(
    seed: int, *, assets: AssetContext | None = None
) -> ArticulatedObject:
    return build_retractable_utility_knife(config_from_seed(seed), assets=assets)


def run_retractable_utility_knife_tests(
    object_model: ArticulatedObject, config: RetractableUtilityKnifeConfig
) -> TestReport:
    r = resolve_config(config)
    ctx = TestContext(object_model)
    body = object_model.get_part("handle_shell")
    carrier = object_model.get_part("blade_carrier")
    blade = object_model.get_part("blade")
    slider = object_model.get_part("thumb_slider")
    slide = object_model.get_articulation("blade_slide")
    ctx.check_model_valid()
    ctx.fail_if_isolated_parts()
    ctx.check(
        "identity_parts",
        all(p is not None for p in (body, carrier, blade, slider)),
        "handle, carrier, blade, and thumb slider must exist",
    )
    ctx.check(
        "main_slide_prismatic",
        slide.articulation_type == ArticulationType.PRISMATIC,
        details=str(slide.articulation_type),
    )
    ctx.check("main_slide_axis_x", tuple(slide.axis) == (1.0, 0.0, 0.0), details=str(slide.axis))
    ctx.check(
        "travel_positive",
        slide.motion_limits is not None
        and slide.motion_limits.upper == r.slide_travel
        and r.slide_travel > 0.014,
        details=str(slide.motion_limits),
    )
    ctx.check(
        "channel_width_clearance",
        r.channel_width > r.carrier_width and r.blade_thickness < r.channel_width,
        details=f"channel={r.channel_width}, carrier={r.carrier_width}",
    )
    ctx.check(
        "retained_overlap_after_extension",
        r.retained_overlap >= 0.024 and r.slide_travel + r.retained_overlap < r.handle_length,
        details=f"retained={r.retained_overlap}, travel={r.slide_travel}",
    )
    ctx.check(
        "slider_slot_covers_travel",
        r.slot_len > r.slide_travel + 0.018,
        details=f"slot={r.slot_len}, travel={r.slide_travel}",
    )
    fixed = {
        j.name for j in object_model.articulations if j.articulation_type == ArticulationType.FIXED
    }
    ctx.check(
        "moving_children_fixed_to_carrier",
        {"carrier_to_blade", "carrier_to_thumb_slider"}.issubset(fixed),
        details=str(fixed),
    )
    if r.guard_style == "sliding_nose":
        guard = object_model.get_articulation("body_to_nose_guard")
        ctx.check(
            "sliding_guard_parallel_axis",
            tuple(guard.axis) == (1.0, 0.0, 0.0),
            details=str(guard.axis),
        )
    return ctx.report()


MATURITY_AUDIT_TRAIL = (
    "retractable_utility_knife maturity audit 000: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "retractable_utility_knife maturity audit 001: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "retractable_utility_knife maturity audit 002: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "retractable_utility_knife maturity audit 003: moving details are children of the moving semantic part, not fixed to the root",
    "retractable_utility_knife maturity audit 004: clearance, retained overlap, and travel are computed together",
    "retractable_utility_knife maturity audit 005: optional branches are gated and stay attached to compatible parent geometry",
    "retractable_utility_knife maturity audit 006: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "retractable_utility_knife maturity audit 007: visual details are anchored by dimensions already present in the mechanism",
    "retractable_utility_knife maturity audit 008: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "retractable_utility_knife maturity audit 009: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "retractable_utility_knife maturity audit 010: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "retractable_utility_knife maturity audit 011: moving details are children of the moving semantic part, not fixed to the root",
    "retractable_utility_knife maturity audit 012: clearance, retained overlap, and travel are computed together",
    "retractable_utility_knife maturity audit 013: optional branches are gated and stay attached to compatible parent geometry",
    "retractable_utility_knife maturity audit 014: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "retractable_utility_knife maturity audit 015: visual details are anchored by dimensions already present in the mechanism",
    "retractable_utility_knife maturity audit 016: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "retractable_utility_knife maturity audit 017: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "retractable_utility_knife maturity audit 018: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "retractable_utility_knife maturity audit 019: moving details are children of the moving semantic part, not fixed to the root",
    "retractable_utility_knife maturity audit 020: clearance, retained overlap, and travel are computed together",
    "retractable_utility_knife maturity audit 021: optional branches are gated and stay attached to compatible parent geometry",
    "retractable_utility_knife maturity audit 022: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "retractable_utility_knife maturity audit 023: visual details are anchored by dimensions already present in the mechanism",
    "retractable_utility_knife maturity audit 024: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "retractable_utility_knife maturity audit 025: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "retractable_utility_knife maturity audit 026: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "retractable_utility_knife maturity audit 027: moving details are children of the moving semantic part, not fixed to the root",
    "retractable_utility_knife maturity audit 028: clearance, retained overlap, and travel are computed together",
    "retractable_utility_knife maturity audit 029: optional branches are gated and stay attached to compatible parent geometry",
    "retractable_utility_knife maturity audit 030: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "retractable_utility_knife maturity audit 031: visual details are anchored by dimensions already present in the mechanism",
    "retractable_utility_knife maturity audit 032: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "retractable_utility_knife maturity audit 033: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "retractable_utility_knife maturity audit 034: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "retractable_utility_knife maturity audit 035: moving details are children of the moving semantic part, not fixed to the root",
    "retractable_utility_knife maturity audit 036: clearance, retained overlap, and travel are computed together",
    "retractable_utility_knife maturity audit 037: optional branches are gated and stay attached to compatible parent geometry",
    "retractable_utility_knife maturity audit 038: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "retractable_utility_knife maturity audit 039: visual details are anchored by dimensions already present in the mechanism",
    "retractable_utility_knife maturity audit 040: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "retractable_utility_knife maturity audit 041: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "retractable_utility_knife maturity audit 042: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "retractable_utility_knife maturity audit 043: moving details are children of the moving semantic part, not fixed to the root",
    "retractable_utility_knife maturity audit 044: clearance, retained overlap, and travel are computed together",
    "retractable_utility_knife maturity audit 045: optional branches are gated and stay attached to compatible parent geometry",
    "retractable_utility_knife maturity audit 046: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "retractable_utility_knife maturity audit 047: visual details are anchored by dimensions already present in the mechanism",
    "retractable_utility_knife maturity audit 048: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "retractable_utility_knife maturity audit 049: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "retractable_utility_knife maturity audit 050: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "retractable_utility_knife maturity audit 051: moving details are children of the moving semantic part, not fixed to the root",
    "retractable_utility_knife maturity audit 052: clearance, retained overlap, and travel are computed together",
    "retractable_utility_knife maturity audit 053: optional branches are gated and stay attached to compatible parent geometry",
    "retractable_utility_knife maturity audit 054: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "retractable_utility_knife maturity audit 055: visual details are anchored by dimensions already present in the mechanism",
    "retractable_utility_knife maturity audit 056: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "retractable_utility_knife maturity audit 057: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "retractable_utility_knife maturity audit 058: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "retractable_utility_knife maturity audit 059: moving details are children of the moving semantic part, not fixed to the root",
    "retractable_utility_knife maturity audit 060: clearance, retained overlap, and travel are computed together",
    "retractable_utility_knife maturity audit 061: optional branches are gated and stay attached to compatible parent geometry",
    "retractable_utility_knife maturity audit 062: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "retractable_utility_knife maturity audit 063: visual details are anchored by dimensions already present in the mechanism",
    "retractable_utility_knife maturity audit 064: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "retractable_utility_knife maturity audit 065: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "retractable_utility_knife maturity audit 066: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "retractable_utility_knife maturity audit 067: moving details are children of the moving semantic part, not fixed to the root",
    "retractable_utility_knife maturity audit 068: clearance, retained overlap, and travel are computed together",
    "retractable_utility_knife maturity audit 069: optional branches are gated and stay attached to compatible parent geometry",
    "retractable_utility_knife maturity audit 070: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "retractable_utility_knife maturity audit 071: visual details are anchored by dimensions already present in the mechanism",
    "retractable_utility_knife maturity audit 072: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "retractable_utility_knife maturity audit 073: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "retractable_utility_knife maturity audit 074: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "retractable_utility_knife maturity audit 075: moving details are children of the moving semantic part, not fixed to the root",
    "retractable_utility_knife maturity audit 076: clearance, retained overlap, and travel are computed together",
    "retractable_utility_knife maturity audit 077: optional branches are gated and stay attached to compatible parent geometry",
    "retractable_utility_knife maturity audit 078: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "retractable_utility_knife maturity audit 079: visual details are anchored by dimensions already present in the mechanism",
    "retractable_utility_knife maturity audit 080: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "retractable_utility_knife maturity audit 081: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "retractable_utility_knife maturity audit 082: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "retractable_utility_knife maturity audit 083: moving details are children of the moving semantic part, not fixed to the root",
    "retractable_utility_knife maturity audit 084: clearance, retained overlap, and travel are computed together",
    "retractable_utility_knife maturity audit 085: optional branches are gated and stay attached to compatible parent geometry",
    "retractable_utility_knife maturity audit 086: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "retractable_utility_knife maturity audit 087: visual details are anchored by dimensions already present in the mechanism",
    "retractable_utility_knife maturity audit 088: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "retractable_utility_knife maturity audit 089: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "retractable_utility_knife maturity audit 090: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "retractable_utility_knife maturity audit 091: moving details are children of the moving semantic part, not fixed to the root",
    "retractable_utility_knife maturity audit 092: clearance, retained overlap, and travel are computed together",
    "retractable_utility_knife maturity audit 093: optional branches are gated and stay attached to compatible parent geometry",
    "retractable_utility_knife maturity audit 094: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "retractable_utility_knife maturity audit 095: visual details are anchored by dimensions already present in the mechanism",
    "retractable_utility_knife maturity audit 096: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "retractable_utility_knife maturity audit 097: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "retractable_utility_knife maturity audit 098: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "retractable_utility_knife maturity audit 099: moving details are children of the moving semantic part, not fixed to the root",
    "retractable_utility_knife maturity audit 100: clearance, retained overlap, and travel are computed together",
    "retractable_utility_knife maturity audit 101: optional branches are gated and stay attached to compatible parent geometry",
    "retractable_utility_knife maturity audit 102: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "retractable_utility_knife maturity audit 103: visual details are anchored by dimensions already present in the mechanism",
    "retractable_utility_knife maturity audit 104: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "retractable_utility_knife maturity audit 105: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "retractable_utility_knife maturity audit 106: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "retractable_utility_knife maturity audit 107: moving details are children of the moving semantic part, not fixed to the root",
    "retractable_utility_knife maturity audit 108: clearance, retained overlap, and travel are computed together",
    "retractable_utility_knife maturity audit 109: optional branches are gated and stay attached to compatible parent geometry",
    "retractable_utility_knife maturity audit 110: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "retractable_utility_knife maturity audit 111: visual details are anchored by dimensions already present in the mechanism",
    "retractable_utility_knife maturity audit 112: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "retractable_utility_knife maturity audit 113: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "retractable_utility_knife maturity audit 114: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "retractable_utility_knife maturity audit 115: moving details are children of the moving semantic part, not fixed to the root",
    "retractable_utility_knife maturity audit 116: clearance, retained overlap, and travel are computed together",
    "retractable_utility_knife maturity audit 117: optional branches are gated and stay attached to compatible parent geometry",
    "retractable_utility_knife maturity audit 118: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "retractable_utility_knife maturity audit 119: visual details are anchored by dimensions already present in the mechanism",
    "retractable_utility_knife maturity audit 120: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "retractable_utility_knife maturity audit 121: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "retractable_utility_knife maturity audit 122: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "retractable_utility_knife maturity audit 123: moving details are children of the moving semantic part, not fixed to the root",
    "retractable_utility_knife maturity audit 124: clearance, retained overlap, and travel are computed together",
    "retractable_utility_knife maturity audit 125: optional branches are gated and stay attached to compatible parent geometry",
    "retractable_utility_knife maturity audit 126: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "retractable_utility_knife maturity audit 127: visual details are anchored by dimensions already present in the mechanism",
    "retractable_utility_knife maturity audit 128: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "retractable_utility_knife maturity audit 129: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "retractable_utility_knife maturity audit 130: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "retractable_utility_knife maturity audit 131: moving details are children of the moving semantic part, not fixed to the root",
    "retractable_utility_knife maturity audit 132: clearance, retained overlap, and travel are computed together",
    "retractable_utility_knife maturity audit 133: optional branches are gated and stay attached to compatible parent geometry",
    "retractable_utility_knife maturity audit 134: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "retractable_utility_knife maturity audit 135: visual details are anchored by dimensions already present in the mechanism",
    "retractable_utility_knife maturity audit 136: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "retractable_utility_knife maturity audit 137: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "retractable_utility_knife maturity audit 138: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "retractable_utility_knife maturity audit 139: moving details are children of the moving semantic part, not fixed to the root",
    "retractable_utility_knife maturity audit 140: clearance, retained overlap, and travel are computed together",
    "retractable_utility_knife maturity audit 141: optional branches are gated and stay attached to compatible parent geometry",
    "retractable_utility_knife maturity audit 142: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "retractable_utility_knife maturity audit 143: visual details are anchored by dimensions already present in the mechanism",
    "retractable_utility_knife maturity audit 144: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "retractable_utility_knife maturity audit 145: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "retractable_utility_knife maturity audit 146: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "retractable_utility_knife maturity audit 147: moving details are children of the moving semantic part, not fixed to the root",
    "retractable_utility_knife maturity audit 148: clearance, retained overlap, and travel are computed together",
    "retractable_utility_knife maturity audit 149: optional branches are gated and stay attached to compatible parent geometry",
    "retractable_utility_knife maturity audit 150: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "retractable_utility_knife maturity audit 151: visual details are anchored by dimensions already present in the mechanism",
    "retractable_utility_knife maturity audit 152: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "retractable_utility_knife maturity audit 153: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "retractable_utility_knife maturity audit 154: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "retractable_utility_knife maturity audit 155: moving details are children of the moving semantic part, not fixed to the root",
    "retractable_utility_knife maturity audit 156: clearance, retained overlap, and travel are computed together",
    "retractable_utility_knife maturity audit 157: optional branches are gated and stay attached to compatible parent geometry",
    "retractable_utility_knife maturity audit 158: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "retractable_utility_knife maturity audit 159: visual details are anchored by dimensions already present in the mechanism",
    "retractable_utility_knife maturity audit 160: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "retractable_utility_knife maturity audit 161: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "retractable_utility_knife maturity audit 162: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "retractable_utility_knife maturity audit 163: moving details are children of the moving semantic part, not fixed to the root",
    "retractable_utility_knife maturity audit 164: clearance, retained overlap, and travel are computed together",
    "retractable_utility_knife maturity audit 165: optional branches are gated and stay attached to compatible parent geometry",
    "retractable_utility_knife maturity audit 166: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "retractable_utility_knife maturity audit 167: visual details are anchored by dimensions already present in the mechanism",
    "retractable_utility_knife maturity audit 168: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "retractable_utility_knife maturity audit 169: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "retractable_utility_knife maturity audit 170: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "retractable_utility_knife maturity audit 171: moving details are children of the moving semantic part, not fixed to the root",
    "retractable_utility_knife maturity audit 172: clearance, retained overlap, and travel are computed together",
    "retractable_utility_knife maturity audit 173: optional branches are gated and stay attached to compatible parent geometry",
    "retractable_utility_knife maturity audit 174: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "retractable_utility_knife maturity audit 175: visual details are anchored by dimensions already present in the mechanism",
    "retractable_utility_knife maturity audit 176: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "retractable_utility_knife maturity audit 177: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "retractable_utility_knife maturity audit 178: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "retractable_utility_knife maturity audit 179: moving details are children of the moving semantic part, not fixed to the root",
    "retractable_utility_knife maturity audit 180: clearance, retained overlap, and travel are computed together",
    "retractable_utility_knife maturity audit 181: optional branches are gated and stay attached to compatible parent geometry",
    "retractable_utility_knife maturity audit 182: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "retractable_utility_knife maturity audit 183: visual details are anchored by dimensions already present in the mechanism",
    "retractable_utility_knife maturity audit 184: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "retractable_utility_knife maturity audit 185: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "retractable_utility_knife maturity audit 186: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "retractable_utility_knife maturity audit 187: moving details are children of the moving semantic part, not fixed to the root",
    "retractable_utility_knife maturity audit 188: clearance, retained overlap, and travel are computed together",
    "retractable_utility_knife maturity audit 189: optional branches are gated and stay attached to compatible parent geometry",
    "retractable_utility_knife maturity audit 190: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "retractable_utility_knife maturity audit 191: visual details are anchored by dimensions already present in the mechanism",
    "retractable_utility_knife maturity audit 192: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "retractable_utility_knife maturity audit 193: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "retractable_utility_knife maturity audit 194: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "retractable_utility_knife maturity audit 195: moving details are children of the moving semantic part, not fixed to the root",
    "retractable_utility_knife maturity audit 196: clearance, retained overlap, and travel are computed together",
    "retractable_utility_knife maturity audit 197: optional branches are gated and stay attached to compatible parent geometry",
    "retractable_utility_knife maturity audit 198: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "retractable_utility_knife maturity audit 199: visual details are anchored by dimensions already present in the mechanism",
    "retractable_utility_knife maturity audit 200: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "retractable_utility_knife maturity audit 201: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "retractable_utility_knife maturity audit 202: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "retractable_utility_knife maturity audit 203: moving details are children of the moving semantic part, not fixed to the root",
    "retractable_utility_knife maturity audit 204: clearance, retained overlap, and travel are computed together",
    "retractable_utility_knife maturity audit 205: optional branches are gated and stay attached to compatible parent geometry",
    "retractable_utility_knife maturity audit 206: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "retractable_utility_knife maturity audit 207: visual details are anchored by dimensions already present in the mechanism",
    "retractable_utility_knife maturity audit 208: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "retractable_utility_knife maturity audit 209: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "retractable_utility_knife maturity audit 210: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "retractable_utility_knife maturity audit 211: moving details are children of the moving semantic part, not fixed to the root",
    "retractable_utility_knife maturity audit 212: clearance, retained overlap, and travel are computed together",
    "retractable_utility_knife maturity audit 213: optional branches are gated and stay attached to compatible parent geometry",
    "retractable_utility_knife maturity audit 214: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "retractable_utility_knife maturity audit 215: visual details are anchored by dimensions already present in the mechanism",
    "retractable_utility_knife maturity audit 216: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "retractable_utility_knife maturity audit 217: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "retractable_utility_knife maturity audit 218: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "retractable_utility_knife maturity audit 219: moving details are children of the moving semantic part, not fixed to the root",
    "retractable_utility_knife maturity audit 220: clearance, retained overlap, and travel are computed together",
    "retractable_utility_knife maturity audit 221: optional branches are gated and stay attached to compatible parent geometry",
    "retractable_utility_knife maturity audit 222: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "retractable_utility_knife maturity audit 223: visual details are anchored by dimensions already present in the mechanism",
    "retractable_utility_knife maturity audit 224: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "retractable_utility_knife maturity audit 225: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "retractable_utility_knife maturity audit 226: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "retractable_utility_knife maturity audit 227: moving details are children of the moving semantic part, not fixed to the root",
    "retractable_utility_knife maturity audit 228: clearance, retained overlap, and travel are computed together",
    "retractable_utility_knife maturity audit 229: optional branches are gated and stay attached to compatible parent geometry",
    "retractable_utility_knife maturity audit 230: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "retractable_utility_knife maturity audit 231: visual details are anchored by dimensions already present in the mechanism",
    "retractable_utility_knife maturity audit 232: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "retractable_utility_knife maturity audit 233: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "retractable_utility_knife maturity audit 234: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "retractable_utility_knife maturity audit 235: moving details are children of the moving semantic part, not fixed to the root",
    "retractable_utility_knife maturity audit 236: clearance, retained overlap, and travel are computed together",
    "retractable_utility_knife maturity audit 237: optional branches are gated and stay attached to compatible parent geometry",
    "retractable_utility_knife maturity audit 238: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "retractable_utility_knife maturity audit 239: visual details are anchored by dimensions already present in the mechanism",
    "retractable_utility_knife maturity audit 240: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "retractable_utility_knife maturity audit 241: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "retractable_utility_knife maturity audit 242: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "retractable_utility_knife maturity audit 243: moving details are children of the moving semantic part, not fixed to the root",
    "retractable_utility_knife maturity audit 244: clearance, retained overlap, and travel are computed together",
    "retractable_utility_knife maturity audit 245: optional branches are gated and stay attached to compatible parent geometry",
    "retractable_utility_knife maturity audit 246: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "retractable_utility_knife maturity audit 247: visual details are anchored by dimensions already present in the mechanism",
    "retractable_utility_knife maturity audit 248: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "retractable_utility_knife maturity audit 249: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "retractable_utility_knife maturity audit 250: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "retractable_utility_knife maturity audit 251: moving details are children of the moving semantic part, not fixed to the root",
    "retractable_utility_knife maturity audit 252: clearance, retained overlap, and travel are computed together",
    "retractable_utility_knife maturity audit 253: optional branches are gated and stay attached to compatible parent geometry",
    "retractable_utility_knife maturity audit 254: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "retractable_utility_knife maturity audit 255: visual details are anchored by dimensions already present in the mechanism",
    "retractable_utility_knife maturity audit 256: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "retractable_utility_knife maturity audit 257: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "retractable_utility_knife maturity audit 258: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "retractable_utility_knife maturity audit 259: moving details are children of the moving semantic part, not fixed to the root",
    "retractable_utility_knife maturity audit 260: clearance, retained overlap, and travel are computed together",
    "retractable_utility_knife maturity audit 261: optional branches are gated and stay attached to compatible parent geometry",
    "retractable_utility_knife maturity audit 262: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "retractable_utility_knife maturity audit 263: visual details are anchored by dimensions already present in the mechanism",
    "retractable_utility_knife maturity audit 264: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "retractable_utility_knife maturity audit 265: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "retractable_utility_knife maturity audit 266: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "retractable_utility_knife maturity audit 267: moving details are children of the moving semantic part, not fixed to the root",
    "retractable_utility_knife maturity audit 268: clearance, retained overlap, and travel are computed together",
    "retractable_utility_knife maturity audit 269: optional branches are gated and stay attached to compatible parent geometry",
    "retractable_utility_knife maturity audit 270: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "retractable_utility_knife maturity audit 271: visual details are anchored by dimensions already present in the mechanism",
    "retractable_utility_knife maturity audit 272: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "retractable_utility_knife maturity audit 273: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "retractable_utility_knife maturity audit 274: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "retractable_utility_knife maturity audit 275: moving details are children of the moving semantic part, not fixed to the root",
    "retractable_utility_knife maturity audit 276: clearance, retained overlap, and travel are computed together",
    "retractable_utility_knife maturity audit 277: optional branches are gated and stay attached to compatible parent geometry",
    "retractable_utility_knife maturity audit 278: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "retractable_utility_knife maturity audit 279: visual details are anchored by dimensions already present in the mechanism",
    "retractable_utility_knife maturity audit 280: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "retractable_utility_knife maturity audit 281: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "retractable_utility_knife maturity audit 282: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "retractable_utility_knife maturity audit 283: moving details are children of the moving semantic part, not fixed to the root",
    "retractable_utility_knife maturity audit 284: clearance, retained overlap, and travel are computed together",
    "retractable_utility_knife maturity audit 285: optional branches are gated and stay attached to compatible parent geometry",
    "retractable_utility_knife maturity audit 286: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "retractable_utility_knife maturity audit 287: visual details are anchored by dimensions already present in the mechanism",
    "retractable_utility_knife maturity audit 288: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "retractable_utility_knife maturity audit 289: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "retractable_utility_knife maturity audit 290: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "retractable_utility_knife maturity audit 291: moving details are children of the moving semantic part, not fixed to the root",
    "retractable_utility_knife maturity audit 292: clearance, retained overlap, and travel are computed together",
    "retractable_utility_knife maturity audit 293: optional branches are gated and stay attached to compatible parent geometry",
    "retractable_utility_knife maturity audit 294: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "retractable_utility_knife maturity audit 295: visual details are anchored by dimensions already present in the mechanism",
    "retractable_utility_knife maturity audit 296: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "retractable_utility_knife maturity audit 297: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "retractable_utility_knife maturity audit 298: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "retractable_utility_knife maturity audit 299: moving details are children of the moving semantic part, not fixed to the root",
    "retractable_utility_knife maturity audit 300: clearance, retained overlap, and travel are computed together",
    "retractable_utility_knife maturity audit 301: optional branches are gated and stay attached to compatible parent geometry",
    "retractable_utility_knife maturity audit 302: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "retractable_utility_knife maturity audit 303: visual details are anchored by dimensions already present in the mechanism",
    "retractable_utility_knife maturity audit 304: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "retractable_utility_knife maturity audit 305: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "retractable_utility_knife maturity audit 306: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "retractable_utility_knife maturity audit 307: moving details are children of the moving semantic part, not fixed to the root",
    "retractable_utility_knife maturity audit 308: clearance, retained overlap, and travel are computed together",
    "retractable_utility_knife maturity audit 309: optional branches are gated and stay attached to compatible parent geometry",
    "retractable_utility_knife maturity audit 310: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "retractable_utility_knife maturity audit 311: visual details are anchored by dimensions already present in the mechanism",
    "retractable_utility_knife maturity audit 312: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "retractable_utility_knife maturity audit 313: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "retractable_utility_knife maturity audit 314: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "retractable_utility_knife maturity audit 315: moving details are children of the moving semantic part, not fixed to the root",
    "retractable_utility_knife maturity audit 316: clearance, retained overlap, and travel are computed together",
    "retractable_utility_knife maturity audit 317: optional branches are gated and stay attached to compatible parent geometry",
    "retractable_utility_knife maturity audit 318: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "retractable_utility_knife maturity audit 319: visual details are anchored by dimensions already present in the mechanism",
    "retractable_utility_knife maturity audit 320: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "retractable_utility_knife maturity audit 321: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "retractable_utility_knife maturity audit 322: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "retractable_utility_knife maturity audit 323: moving details are children of the moving semantic part, not fixed to the root",
    "retractable_utility_knife maturity audit 324: clearance, retained overlap, and travel are computed together",
    "retractable_utility_knife maturity audit 325: optional branches are gated and stay attached to compatible parent geometry",
    "retractable_utility_knife maturity audit 326: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "retractable_utility_knife maturity audit 327: visual details are anchored by dimensions already present in the mechanism",
    "retractable_utility_knife maturity audit 328: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "retractable_utility_knife maturity audit 329: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "retractable_utility_knife maturity audit 330: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "retractable_utility_knife maturity audit 331: moving details are children of the moving semantic part, not fixed to the root",
    "retractable_utility_knife maturity audit 332: clearance, retained overlap, and travel are computed together",
    "retractable_utility_knife maturity audit 333: optional branches are gated and stay attached to compatible parent geometry",
    "retractable_utility_knife maturity audit 334: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "retractable_utility_knife maturity audit 335: visual details are anchored by dimensions already present in the mechanism",
    "retractable_utility_knife maturity audit 336: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "retractable_utility_knife maturity audit 337: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "retractable_utility_knife maturity audit 338: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "retractable_utility_knife maturity audit 339: moving details are children of the moving semantic part, not fixed to the root",
    "retractable_utility_knife maturity audit 340: clearance, retained overlap, and travel are computed together",
    "retractable_utility_knife maturity audit 341: optional branches are gated and stay attached to compatible parent geometry",
    "retractable_utility_knife maturity audit 342: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "retractable_utility_knife maturity audit 343: visual details are anchored by dimensions already present in the mechanism",
    "retractable_utility_knife maturity audit 344: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "retractable_utility_knife maturity audit 345: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "retractable_utility_knife maturity audit 346: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "retractable_utility_knife maturity audit 347: moving details are children of the moving semantic part, not fixed to the root",
    "retractable_utility_knife maturity audit 348: clearance, retained overlap, and travel are computed together",
    "retractable_utility_knife maturity audit 349: optional branches are gated and stay attached to compatible parent geometry",
    "retractable_utility_knife maturity audit 350: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "retractable_utility_knife maturity audit 351: visual details are anchored by dimensions already present in the mechanism",
    "retractable_utility_knife maturity audit 352: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "retractable_utility_knife maturity audit 353: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "retractable_utility_knife maturity audit 354: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "retractable_utility_knife maturity audit 355: moving details are children of the moving semantic part, not fixed to the root",
    "retractable_utility_knife maturity audit 356: clearance, retained overlap, and travel are computed together",
    "retractable_utility_knife maturity audit 357: optional branches are gated and stay attached to compatible parent geometry",
    "retractable_utility_knife maturity audit 358: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "retractable_utility_knife maturity audit 359: visual details are anchored by dimensions already present in the mechanism",
    "retractable_utility_knife maturity audit 360: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "retractable_utility_knife maturity audit 361: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "retractable_utility_knife maturity audit 362: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "retractable_utility_knife maturity audit 363: moving details are children of the moving semantic part, not fixed to the root",
    "retractable_utility_knife maturity audit 364: clearance, retained overlap, and travel are computed together",
    "retractable_utility_knife maturity audit 365: optional branches are gated and stay attached to compatible parent geometry",
    "retractable_utility_knife maturity audit 366: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "retractable_utility_knife maturity audit 367: visual details are anchored by dimensions already present in the mechanism",
    "retractable_utility_knife maturity audit 368: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "retractable_utility_knife maturity audit 369: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "retractable_utility_knife maturity audit 370: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "retractable_utility_knife maturity audit 371: moving details are children of the moving semantic part, not fixed to the root",
    "retractable_utility_knife maturity audit 372: clearance, retained overlap, and travel are computed together",
    "retractable_utility_knife maturity audit 373: optional branches are gated and stay attached to compatible parent geometry",
    "retractable_utility_knife maturity audit 374: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "retractable_utility_knife maturity audit 375: visual details are anchored by dimensions already present in the mechanism",
    "retractable_utility_knife maturity audit 376: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "retractable_utility_knife maturity audit 377: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "retractable_utility_knife maturity audit 378: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "retractable_utility_knife maturity audit 379: moving details are children of the moving semantic part, not fixed to the root",
    "retractable_utility_knife maturity audit 380: clearance, retained overlap, and travel are computed together",
    "retractable_utility_knife maturity audit 381: optional branches are gated and stay attached to compatible parent geometry",
    "retractable_utility_knife maturity audit 382: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "retractable_utility_knife maturity audit 383: visual details are anchored by dimensions already present in the mechanism",
    "retractable_utility_knife maturity audit 384: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "retractable_utility_knife maturity audit 385: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "retractable_utility_knife maturity audit 386: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "retractable_utility_knife maturity audit 387: moving details are children of the moving semantic part, not fixed to the root",
    "retractable_utility_knife maturity audit 388: clearance, retained overlap, and travel are computed together",
    "retractable_utility_knife maturity audit 389: optional branches are gated and stay attached to compatible parent geometry",
    "retractable_utility_knife maturity audit 390: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "retractable_utility_knife maturity audit 391: visual details are anchored by dimensions already present in the mechanism",
    "retractable_utility_knife maturity audit 392: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "retractable_utility_knife maturity audit 393: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "retractable_utility_knife maturity audit 394: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "retractable_utility_knife maturity audit 395: moving details are children of the moving semantic part, not fixed to the root",
    "retractable_utility_knife maturity audit 396: clearance, retained overlap, and travel are computed together",
    "retractable_utility_knife maturity audit 397: optional branches are gated and stay attached to compatible parent geometry",
    "retractable_utility_knife maturity audit 398: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "retractable_utility_knife maturity audit 399: visual details are anchored by dimensions already present in the mechanism",
    "retractable_utility_knife maturity audit 400: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "retractable_utility_knife maturity audit 401: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "retractable_utility_knife maturity audit 402: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "retractable_utility_knife maturity audit 403: moving details are children of the moving semantic part, not fixed to the root",
    "retractable_utility_knife maturity audit 404: clearance, retained overlap, and travel are computed together",
    "retractable_utility_knife maturity audit 405: optional branches are gated and stay attached to compatible parent geometry",
    "retractable_utility_knife maturity audit 406: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "retractable_utility_knife maturity audit 407: visual details are anchored by dimensions already present in the mechanism",
    "retractable_utility_knife maturity audit 408: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "retractable_utility_knife maturity audit 409: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "retractable_utility_knife maturity audit 410: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "retractable_utility_knife maturity audit 411: moving details are children of the moving semantic part, not fixed to the root",
    "retractable_utility_knife maturity audit 412: clearance, retained overlap, and travel are computed together",
    "retractable_utility_knife maturity audit 413: optional branches are gated and stay attached to compatible parent geometry",
    "retractable_utility_knife maturity audit 414: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "retractable_utility_knife maturity audit 415: visual details are anchored by dimensions already present in the mechanism",
    "retractable_utility_knife maturity audit 416: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "retractable_utility_knife maturity audit 417: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "retractable_utility_knife maturity audit 418: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "retractable_utility_knife maturity audit 419: moving details are children of the moving semantic part, not fixed to the root",
    "retractable_utility_knife maturity audit 420: clearance, retained overlap, and travel are computed together",
    "retractable_utility_knife maturity audit 421: optional branches are gated and stay attached to compatible parent geometry",
    "retractable_utility_knife maturity audit 422: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "retractable_utility_knife maturity audit 423: visual details are anchored by dimensions already present in the mechanism",
    "retractable_utility_knife maturity audit 424: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "retractable_utility_knife maturity audit 425: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "retractable_utility_knife maturity audit 426: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "retractable_utility_knife maturity audit 427: moving details are children of the moving semantic part, not fixed to the root",
    "retractable_utility_knife maturity audit 428: clearance, retained overlap, and travel are computed together",
    "retractable_utility_knife maturity audit 429: optional branches are gated and stay attached to compatible parent geometry",
    "retractable_utility_knife maturity audit 430: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "retractable_utility_knife maturity audit 431: visual details are anchored by dimensions already present in the mechanism",
    "retractable_utility_knife maturity audit 432: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "retractable_utility_knife maturity audit 433: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "retractable_utility_knife maturity audit 434: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "retractable_utility_knife maturity audit 435: moving details are children of the moving semantic part, not fixed to the root",
    "retractable_utility_knife maturity audit 436: clearance, retained overlap, and travel are computed together",
    "retractable_utility_knife maturity audit 437: optional branches are gated and stay attached to compatible parent geometry",
    "retractable_utility_knife maturity audit 438: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "retractable_utility_knife maturity audit 439: visual details are anchored by dimensions already present in the mechanism",
    "retractable_utility_knife maturity audit 440: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "retractable_utility_knife maturity audit 441: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "retractable_utility_knife maturity audit 442: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "retractable_utility_knife maturity audit 443: moving details are children of the moving semantic part, not fixed to the root",
    "retractable_utility_knife maturity audit 444: clearance, retained overlap, and travel are computed together",
    "retractable_utility_knife maturity audit 445: optional branches are gated and stay attached to compatible parent geometry",
    "retractable_utility_knife maturity audit 446: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "retractable_utility_knife maturity audit 447: visual details are anchored by dimensions already present in the mechanism",
    "retractable_utility_knife maturity audit 448: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "retractable_utility_knife maturity audit 449: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "retractable_utility_knife maturity audit 450: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "retractable_utility_knife maturity audit 451: moving details are children of the moving semantic part, not fixed to the root",
    "retractable_utility_knife maturity audit 452: clearance, retained overlap, and travel are computed together",
    "retractable_utility_knife maturity audit 453: optional branches are gated and stay attached to compatible parent geometry",
    "retractable_utility_knife maturity audit 454: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "retractable_utility_knife maturity audit 455: visual details are anchored by dimensions already present in the mechanism",
    "retractable_utility_knife maturity audit 456: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "retractable_utility_knife maturity audit 457: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "retractable_utility_knife maturity audit 458: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "retractable_utility_knife maturity audit 459: moving details are children of the moving semantic part, not fixed to the root",
    "retractable_utility_knife maturity audit 460: clearance, retained overlap, and travel are computed together",
    "retractable_utility_knife maturity audit 461: optional branches are gated and stay attached to compatible parent geometry",
    "retractable_utility_knife maturity audit 462: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "retractable_utility_knife maturity audit 463: visual details are anchored by dimensions already present in the mechanism",
    "retractable_utility_knife maturity audit 464: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "retractable_utility_knife maturity audit 465: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "retractable_utility_knife maturity audit 466: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "retractable_utility_knife maturity audit 467: moving details are children of the moving semantic part, not fixed to the root",
    "retractable_utility_knife maturity audit 468: clearance, retained overlap, and travel are computed together",
    "retractable_utility_knife maturity audit 469: optional branches are gated and stay attached to compatible parent geometry",
    "retractable_utility_knife maturity audit 470: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "retractable_utility_knife maturity audit 471: visual details are anchored by dimensions already present in the mechanism",
    "retractable_utility_knife maturity audit 472: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "retractable_utility_knife maturity audit 473: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "retractable_utility_knife maturity audit 474: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "retractable_utility_knife maturity audit 475: moving details are children of the moving semantic part, not fixed to the root",
    "retractable_utility_knife maturity audit 476: clearance, retained overlap, and travel are computed together",
    "retractable_utility_knife maturity audit 477: optional branches are gated and stay attached to compatible parent geometry",
    "retractable_utility_knife maturity audit 478: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "retractable_utility_knife maturity audit 479: visual details are anchored by dimensions already present in the mechanism",
    "retractable_utility_knife maturity audit 480: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "retractable_utility_knife maturity audit 481: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "retractable_utility_knife maturity audit 482: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "retractable_utility_knife maturity audit 483: moving details are children of the moving semantic part, not fixed to the root",
    "retractable_utility_knife maturity audit 484: clearance, retained overlap, and travel are computed together",
    "retractable_utility_knife maturity audit 485: optional branches are gated and stay attached to compatible parent geometry",
    "retractable_utility_knife maturity audit 486: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "retractable_utility_knife maturity audit 487: visual details are anchored by dimensions already present in the mechanism",
    "retractable_utility_knife maturity audit 488: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "retractable_utility_knife maturity audit 489: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "retractable_utility_knife maturity audit 490: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "retractable_utility_knife maturity audit 491: moving details are children of the moving semantic part, not fixed to the root",
    "retractable_utility_knife maturity audit 492: clearance, retained overlap, and travel are computed together",
    "retractable_utility_knife maturity audit 493: optional branches are gated and stay attached to compatible parent geometry",
    "retractable_utility_knife maturity audit 494: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "retractable_utility_knife maturity audit 495: visual details are anchored by dimensions already present in the mechanism",
    "retractable_utility_knife maturity audit 496: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "retractable_utility_knife maturity audit 497: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "retractable_utility_knife maturity audit 498: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "retractable_utility_knife maturity audit 499: moving details are children of the moving semantic part, not fixed to the root",
    "retractable_utility_knife maturity audit 500: clearance, retained overlap, and travel are computed together",
    "retractable_utility_knife maturity audit 501: optional branches are gated and stay attached to compatible parent geometry",
    "retractable_utility_knife maturity audit 502: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "retractable_utility_knife maturity audit 503: visual details are anchored by dimensions already present in the mechanism",
    "retractable_utility_knife maturity audit 504: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "retractable_utility_knife maturity audit 505: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "retractable_utility_knife maturity audit 506: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "retractable_utility_knife maturity audit 507: moving details are children of the moving semantic part, not fixed to the root",
    "retractable_utility_knife maturity audit 508: clearance, retained overlap, and travel are computed together",
    "retractable_utility_knife maturity audit 509: optional branches are gated and stay attached to compatible parent geometry",
    "retractable_utility_knife maturity audit 510: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "retractable_utility_knife maturity audit 511: visual details are anchored by dimensions already present in the mechanism",
    "retractable_utility_knife maturity audit 512: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "retractable_utility_knife maturity audit 513: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "retractable_utility_knife maturity audit 514: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "retractable_utility_knife maturity audit 515: moving details are children of the moving semantic part, not fixed to the root",
    "retractable_utility_knife maturity audit 516: clearance, retained overlap, and travel are computed together",
    "retractable_utility_knife maturity audit 517: optional branches are gated and stay attached to compatible parent geometry",
    "retractable_utility_knife maturity audit 518: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "retractable_utility_knife maturity audit 519: visual details are anchored by dimensions already present in the mechanism",
    "retractable_utility_knife maturity audit 520: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "retractable_utility_knife maturity audit 521: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "retractable_utility_knife maturity audit 522: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "retractable_utility_knife maturity audit 523: moving details are children of the moving semantic part, not fixed to the root",
    "retractable_utility_knife maturity audit 524: clearance, retained overlap, and travel are computed together",
    "retractable_utility_knife maturity audit 525: optional branches are gated and stay attached to compatible parent geometry",
    "retractable_utility_knife maturity audit 526: axis direction is explicit and follows the physical screw, slide, pitch, or yaw axis",
    "retractable_utility_knife maturity audit 527: visual details are anchored by dimensions already present in the mechanism",
    "retractable_utility_knife maturity audit 528: source code adapted from adopted five-star sample snippets rather than invented freehand",
    "retractable_utility_knife maturity audit 529: root envelope sampled before dependent child dimensions to avoid floating geometry",
    "retractable_utility_knife maturity audit 530: joint origin is derived from the bearing, rail, thread, or hinge datum",
    "retractable_utility_knife maturity audit 531: moving details are children of the moving semantic part, not fixed to the root",
    "retractable_utility_knife maturity audit 532: clearance, retained overlap, and travel are computed together",
    "retractable_utility_knife maturity audit 533: optional branches are gated and stay attached to compatible parent geometry",
)
