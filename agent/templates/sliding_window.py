from __future__ import annotations

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

WindowOrientation = Literal["horizontal", "vertical"]
FrameAspectClass = Literal["wide", "square", "tall"]
RailStyle = Literal["single", "double", "recessed"]
HandleStyle = Literal["tab", "bar", "recessed"]
GlassOpacityStyle = Literal["clear", "frosted", "tinted"]
LockStyle = Literal["none", "small_latch", "central_lock"]
MaterialStyle = Literal["aluminum", "pvc", "wood", "black_metal"]

# Aspect class continuous ranges (width range, height range), measured in meters
# for the **outer** window envelope. Buckets nudge geometry but seed-time
# continuous values give per-sample variation within the bucket.
ASPECT_WIDTH_RANGES: dict[FrameAspectClass, tuple[float, float]] = {
    "wide": (1.40, 2.20),
    "square": (0.95, 1.20),
    "tall": (0.60, 0.95),
}
ASPECT_HEIGHT_RANGES: dict[FrameAspectClass, tuple[float, float]] = {
    "wide": (0.85, 1.10),
    "square": (0.95, 1.20),
    "tall": (1.20, 1.60),
}

FRAME_DEPTH_MIN = 0.06
FRAME_DEPTH_MAX = 0.11
PERIMETER_MIN = 0.045
PERIMETER_MAX = 0.075
SASH_DEPTH = 0.022
SASH_STILE = 0.048
SASH_RAIL = 0.048
GLASS_DEPTH = 0.006
GUIDE_LIP_DEPTH = 0.008
GUIDE_LIP_HEIGHT = 0.034
SASH_GAP = 0.010  # axial gap between adjacent sashes along slide axis

MATERIAL_PALETTES: dict[
    MaterialStyle, tuple[tuple[float, float, float, float], tuple[float, float, float, float]]
] = {
    # (frame_rgba, accent_rgba)
    "aluminum": ((0.76, 0.78, 0.80, 1.0), (0.40, 0.42, 0.44, 1.0)),
    "pvc": ((0.94, 0.94, 0.92, 1.0), (0.65, 0.66, 0.65, 1.0)),
    "wood": ((0.55, 0.36, 0.20, 1.0), (0.32, 0.20, 0.10, 1.0)),
    "black_metal": ((0.13, 0.13, 0.14, 1.0), (0.05, 0.05, 0.06, 1.0)),
}

GLASS_PALETTES: dict[GlassOpacityStyle, tuple[float, float, float, float]] = {
    "clear": (0.72, 0.83, 0.92, 0.35),
    "frosted": (0.92, 0.94, 0.96, 0.25),
    "tinted": (0.32, 0.48, 0.40, 0.40),
}


@dataclass(frozen=True)
class SlidingWindowConfig:
    window_orientation: WindowOrientation = "horizontal"
    sash_count: int = 2
    sliding_sash_count: int = 1
    frame_aspect_ratio: FrameAspectClass = "wide"
    rail_style: RailStyle = "double"
    handle_style: HandleStyle = "bar"
    grid_muntin_count: int = 0
    glass_opacity: GlassOpacityStyle = "clear"
    lock_style: LockStyle = "small_latch"
    material_style: MaterialStyle = "aluminum"
    outer_width: float | None = None
    outer_height: float | None = None
    frame_depth: float | None = None
    perimeter: float | None = None
    name: str = "reference_sliding_window"


@dataclass(frozen=True)
class ResolvedSlidingWindowConfig:
    window_orientation: WindowOrientation
    sash_count: int
    sliding_sash_count: int
    frame_aspect_ratio: FrameAspectClass
    rail_style: RailStyle
    handle_style: HandleStyle
    grid_muntin_count: int
    glass_opacity: GlassOpacityStyle
    lock_style: LockStyle
    material_style: MaterialStyle
    outer_width: float
    outer_height: float
    frame_depth: float
    perimeter: float
    inner_width: float
    inner_height: float
    sash_axial_length: float  # along slide axis (X for horizontal, Z for vertical)
    sash_cross_length: float  # cross axis
    name: str


def config_from_seed(seed: int) -> SlidingWindowConfig:
    rng = random.Random(seed)
    orientation: WindowOrientation = rng.choices(
        ("horizontal", "vertical"), weights=(0.65, 0.35), k=1
    )[0]
    sash_count = rng.choices((2, 3, 4), weights=(0.50, 0.32, 0.18), k=1)[0]
    sliding_sash_count = rng.choices((1, 2), weights=(0.70, 0.30), k=1)[0]
    # auto-clamp at config_from_seed too; resolve_config also clamps
    sliding_sash_count = min(sliding_sash_count, sash_count)
    aspect: FrameAspectClass = rng.choices(
        ("wide", "square", "tall"), weights=(0.45, 0.30, 0.25), k=1
    )[0]
    width_min, width_max = ASPECT_WIDTH_RANGES[aspect]
    height_min, height_max = ASPECT_HEIGHT_RANGES[aspect]
    outer_width = round(rng.uniform(width_min, width_max), 3)
    outer_height = round(rng.uniform(height_min, height_max), 3)
    frame_depth = round(rng.uniform(FRAME_DEPTH_MIN, FRAME_DEPTH_MAX), 3)
    perimeter = round(rng.uniform(PERIMETER_MIN, PERIMETER_MAX), 3)
    rail_style: RailStyle = rng.choices(
        ("single", "double", "recessed"), weights=(0.25, 0.50, 0.25), k=1
    )[0]
    handle_style: HandleStyle = rng.choice(("tab", "bar", "recessed"))
    grid_muntin_count = rng.choices((0, 2, 4, 6), weights=(0.50, 0.20, 0.18, 0.12), k=1)[0]
    glass_opacity: GlassOpacityStyle = rng.choices(
        ("clear", "frosted", "tinted"), weights=(0.55, 0.20, 0.25), k=1
    )[0]
    lock_style: LockStyle = rng.choices(
        ("none", "small_latch", "central_lock"), weights=(0.30, 0.45, 0.25), k=1
    )[0]
    material_style: MaterialStyle = rng.choices(
        ("aluminum", "pvc", "wood", "black_metal"),
        weights=(0.36, 0.24, 0.20, 0.20),
        k=1,
    )[0]
    return SlidingWindowConfig(
        window_orientation=orientation,
        sash_count=sash_count,
        sliding_sash_count=sliding_sash_count,
        frame_aspect_ratio=aspect,
        rail_style=rail_style,
        handle_style=handle_style,
        grid_muntin_count=grid_muntin_count,
        glass_opacity=glass_opacity,
        lock_style=lock_style,
        material_style=material_style,
        outer_width=outer_width,
        outer_height=outer_height,
        frame_depth=frame_depth,
        perimeter=perimeter,
        name=f"seeded_sliding_window_{seed}",
    )


def resolve_config(config: SlidingWindowConfig) -> ResolvedSlidingWindowConfig:
    if config.window_orientation not in {"horizontal", "vertical"}:
        raise ValueError(f"Unsupported window_orientation: {config.window_orientation}")
    if config.sash_count not in {2, 3, 4}:
        raise ValueError(f"sash_count must be in {{2,3,4}}, got {config.sash_count}")
    if config.sliding_sash_count not in {1, 2}:
        raise ValueError(f"sliding_sash_count must be in {{1,2}}, got {config.sliding_sash_count}")
    if config.frame_aspect_ratio not in ASPECT_WIDTH_RANGES:
        raise ValueError(f"Unsupported frame_aspect_ratio: {config.frame_aspect_ratio}")
    if config.rail_style not in {"single", "double", "recessed"}:
        raise ValueError(f"Unsupported rail_style: {config.rail_style}")
    if config.handle_style not in {"tab", "bar", "recessed"}:
        raise ValueError(f"Unsupported handle_style: {config.handle_style}")
    if config.grid_muntin_count not in {0, 2, 4, 6}:
        raise ValueError(f"Unsupported grid_muntin_count: {config.grid_muntin_count}")
    if config.glass_opacity not in GLASS_PALETTES:
        raise ValueError(f"Unsupported glass_opacity: {config.glass_opacity}")
    if config.lock_style not in {"none", "small_latch", "central_lock"}:
        raise ValueError(f"Unsupported lock_style: {config.lock_style}")
    if config.material_style not in MATERIAL_PALETTES:
        raise ValueError(f"Unsupported material_style: {config.material_style}")

    sliding_sash_count = min(config.sliding_sash_count, config.sash_count)

    aspect = config.frame_aspect_ratio
    width_min, width_max = ASPECT_WIDTH_RANGES[aspect]
    height_min, height_max = ASPECT_HEIGHT_RANGES[aspect]
    if config.outer_width is None:
        outer_width = (width_min + width_max) * 0.5
    else:
        outer_width = max(width_min * 0.9, min(width_max * 1.1, config.outer_width))
    if config.outer_height is None:
        outer_height = (height_min + height_max) * 0.5
    else:
        outer_height = max(height_min * 0.9, min(height_max * 1.1, config.outer_height))
    frame_depth = config.frame_depth if config.frame_depth is not None else 0.085
    frame_depth = max(FRAME_DEPTH_MIN, min(FRAME_DEPTH_MAX, frame_depth))
    perimeter = config.perimeter if config.perimeter is not None else 0.055
    perimeter = max(PERIMETER_MIN, min(PERIMETER_MAX, perimeter))

    inner_width = outer_width - 2.0 * perimeter
    inner_height = outer_height - 2.0 * perimeter
    if inner_width <= 0.30 or inner_height <= 0.30:
        raise ValueError(
            "inner aperture too small after applying perimeter; "
            f"inner_width={inner_width:.3f}, inner_height={inner_height:.3f}"
        )

    # Sashes overlap by SASH_GAP along the slide axis when the slider closes
    # against its neighbor.  Each sash spans (inner_axial - (n-1)*SASH_GAP) / n.
    if config.window_orientation == "horizontal":
        sash_axial_length = (inner_width - (config.sash_count - 1) * SASH_GAP) / config.sash_count
        sash_cross_length = inner_height
    else:
        sash_axial_length = (inner_height - (config.sash_count - 1) * SASH_GAP) / config.sash_count
        sash_cross_length = inner_width
    # Auto-clamp: if too many sashes for the envelope, reduce sash_count.
    min_sash_axial = 0.14
    final_sash_count = config.sash_count
    final_sliding = sliding_sash_count
    while sash_axial_length < min_sash_axial and final_sash_count > 2:
        final_sash_count -= 1
        final_sliding = min(final_sliding, final_sash_count)
        axial_envelope = inner_width if config.window_orientation == "horizontal" else inner_height
        sash_axial_length = (axial_envelope - (final_sash_count - 1) * SASH_GAP) / final_sash_count
    if sash_axial_length < min_sash_axial:
        raise ValueError(
            f"derived sash axial length too small even at sash_count=2: {sash_axial_length:.3f}m"
        )

    return ResolvedSlidingWindowConfig(
        window_orientation=config.window_orientation,
        sash_count=final_sash_count,
        sliding_sash_count=final_sliding,
        frame_aspect_ratio=aspect,
        rail_style=config.rail_style,
        handle_style=config.handle_style,
        grid_muntin_count=config.grid_muntin_count,
        glass_opacity=config.glass_opacity,
        lock_style=config.lock_style,
        material_style=config.material_style,
        outer_width=outer_width,
        outer_height=outer_height,
        frame_depth=frame_depth,
        perimeter=perimeter,
        inner_width=inner_width,
        inner_height=inner_height,
        sash_axial_length=sash_axial_length,
        sash_cross_length=sash_cross_length,
        name=config.name,
    )


# ---------------------------------------------------------------------------
# Frame builders
# ---------------------------------------------------------------------------


def _depth_offsets_for_sashes(
    sash_count: int, sliding_sash_count: int, sash_depth: float
) -> list[float]:
    """Return per-sash Y offset (depth axis) so sliding sashes do not collide.

    Sliding sashes share the front plane (positive Y); fixed sashes share the
    rear plane.  We give every sash a unique Y so adjacent sliders can pass
    each other along the slide axis.
    """
    offsets: list[float] = []
    slot = sash_depth + 0.006  # 6mm clearance between adjacent depth slots
    for i in range(sash_count):
        if i < sliding_sash_count:
            # sliding sashes occupy front slots: 0, +slot, +2*slot ...
            offsets.append((sliding_sash_count - 1 - i) * slot * 0.0 + i * slot)
        else:
            # fixed sashes occupy rear slots, behind the slider plane
            rear_index = i - sliding_sash_count
            offsets.append(-(rear_index + 1) * slot)
    # center the cluster on Y=0
    mean = sum(offsets) / len(offsets)
    return [o - mean for o in offsets]


def _build_window_frame(
    frame_part,
    resolved: ResolvedSlidingWindowConfig,
    *,
    frame_mat,
    accent_mat,
) -> None:
    ow = resolved.outer_width
    oh = resolved.outer_height
    fd = resolved.frame_depth
    p = resolved.perimeter
    iw = resolved.inner_width
    ih = resolved.inner_height

    # Four perimeter members
    frame_part.visual(
        Box((p, fd, oh)),
        origin=Origin(xyz=(-ow / 2.0 + p / 2.0, 0.0, 0.0)),
        material=frame_mat,
        name="left_jamb",
    )
    frame_part.visual(
        Box((p, fd, oh)),
        origin=Origin(xyz=(ow / 2.0 - p / 2.0, 0.0, 0.0)),
        material=frame_mat,
        name="right_jamb",
    )
    frame_part.visual(
        Box((iw, fd, p)),
        origin=Origin(xyz=(0.0, 0.0, oh / 2.0 - p / 2.0)),
        material=frame_mat,
        name="top_rail",
    )
    frame_part.visual(
        Box((iw, fd, p)),
        origin=Origin(xyz=(0.0, 0.0, -oh / 2.0 + p / 2.0)),
        material=frame_mat,
        name="bottom_rail",
    )

    # Rail / guide channel decoration -- always present, geometry depends on style.
    rail_style = resolved.rail_style
    if resolved.window_orientation == "horizontal":
        # Long lips run left-right inside the top and bottom of the frame.
        if rail_style == "single":
            lip_pairs = ((0.0, "center"),)
        elif rail_style == "double":
            lip_pairs = ((-0.014, "rear"), (0.014, "front"))
        else:  # recessed
            lip_pairs = ((-0.020, "rear"), (0.020, "front"))
        for y_off, side in lip_pairs:
            for z, label in (
                (ih / 2.0 - GUIDE_LIP_HEIGHT / 2.0, "top"),
                (-ih / 2.0 + GUIDE_LIP_HEIGHT / 2.0, "bottom"),
            ):
                frame_part.visual(
                    Box((iw, GUIDE_LIP_DEPTH, GUIDE_LIP_HEIGHT)),
                    origin=Origin(xyz=(0.0, y_off, z)),
                    material=accent_mat,
                    name=f"{label}_{side}_track_lip",
                )
    else:
        # Vertical orientation: lips run top-bottom along left and right jambs.
        if rail_style == "single":
            lip_pairs = ((0.0, "center"),)
        elif rail_style == "double":
            lip_pairs = ((-0.014, "rear"), (0.014, "front"))
        else:
            lip_pairs = ((-0.020, "rear"), (0.020, "front"))
        for y_off, side in lip_pairs:
            for x, label in (
                (iw / 2.0 - GUIDE_LIP_HEIGHT / 2.0, "right"),
                (-iw / 2.0 + GUIDE_LIP_HEIGHT / 2.0, "left"),
            ):
                frame_part.visual(
                    Box((GUIDE_LIP_HEIGHT, GUIDE_LIP_DEPTH, ih)),
                    origin=Origin(xyz=(x, y_off, 0.0)),
                    material=accent_mat,
                    name=f"{label}_{side}_track_lip",
                )

    # Travel stops / keeper block decoration on the frame at the two ends of
    # the slide axis.
    if resolved.window_orientation == "horizontal":
        for x, label in (
            (-ow / 2.0 + p + 0.012, "left"),
            (ow / 2.0 - p - 0.012, "right"),
        ):
            frame_part.visual(
                Box((0.010, fd * 0.55, 0.060)),
                origin=Origin(xyz=(x, 0.0, -ih / 2.0 + 0.060)),
                material=accent_mat,
                name=f"{label}_travel_stop",
            )
    else:
        for z, label in (
            (-oh / 2.0 + p + 0.012, "lower"),
            (oh / 2.0 - p - 0.012, "upper"),
        ):
            frame_part.visual(
                Box((0.060, fd * 0.55, 0.010)),
                origin=Origin(xyz=(-iw / 2.0 + 0.060, 0.0, z)),
                material=accent_mat,
                name=f"{label}_travel_stop",
            )

    # Optional frame-level lock keeper (parent visual, non-articulated child).
    if resolved.lock_style != "none":
        if resolved.window_orientation == "horizontal":
            keeper_origin = Origin(xyz=(0.0, fd * 0.5 + 0.003, 0.0))
        else:
            keeper_origin = Origin(xyz=(-iw / 2.0 + 0.030, fd * 0.5 + 0.003, 0.0))
        size = (
            (0.040, 0.012, 0.060)
            if resolved.lock_style == "small_latch"
            else (
                0.090,
                0.014,
                0.060,
            )
        )
        frame_part.visual(
            Box(size),
            origin=keeper_origin,
            material=accent_mat,
            name="lock_keeper_mount",
        )


# ---------------------------------------------------------------------------
# Sash builder
# ---------------------------------------------------------------------------


def _build_sash(
    sash_part,
    resolved: ResolvedSlidingWindowConfig,
    *,
    frame_mat,
    accent_mat,
    glass_mat,
    is_sliding: bool,
    sash_index: int,
) -> None:
    """Author one sash (fixed or sliding) into ``sash_part``.

    The sash is authored centered on its own local origin.  Its outer extent
    along the slide axis is ``sash_axial_length`` and the cross axis is
    ``sash_cross_length``.
    """
    sash_depth = SASH_DEPTH
    stile = SASH_STILE
    rail = SASH_RAIL
    if resolved.window_orientation == "horizontal":
        sash_w = resolved.sash_axial_length
        sash_h = resolved.sash_cross_length
    else:
        sash_w = resolved.sash_cross_length
        sash_h = resolved.sash_axial_length

    # 4 stiles+rails plus glass
    sash_part.visual(
        Box((sash_w, sash_depth, rail)),
        origin=Origin(xyz=(0.0, 0.0, sash_h / 2.0 - rail / 2.0)),
        material=frame_mat,
        name="sash_top_rail",
    )
    sash_part.visual(
        Box((sash_w, sash_depth, rail)),
        origin=Origin(xyz=(0.0, 0.0, -sash_h / 2.0 + rail / 2.0)),
        material=frame_mat,
        name="sash_bottom_rail",
    )
    inner_stile_h = max(0.04, sash_h - 2.0 * rail + 0.008)
    sash_part.visual(
        Box((stile, sash_depth, inner_stile_h)),
        origin=Origin(xyz=(-sash_w / 2.0 + stile / 2.0, 0.0, 0.0)),
        material=frame_mat,
        name="sash_left_stile",
    )
    sash_part.visual(
        Box((stile, sash_depth, inner_stile_h)),
        origin=Origin(xyz=(sash_w / 2.0 - stile / 2.0, 0.0, 0.0)),
        material=frame_mat,
        name="sash_right_stile",
    )
    glass_w = max(0.04, sash_w - 2.0 * stile + 0.010)
    glass_h = max(0.04, sash_h - 2.0 * rail + 0.010)
    sash_part.visual(
        Box((glass_w, GLASS_DEPTH, glass_h)),
        origin=Origin(xyz=(0.0, 0.0, 0.0)),
        material=glass_mat,
        name="sash_glass",
    )

    # Muntins: equally-spaced thin members.  Half horizontal, half vertical
    # (rounded so that count matches grid_muntin_count exactly).
    n_muntin = resolved.grid_muntin_count
    if n_muntin > 0:
        n_horizontal = n_muntin // 2
        n_vertical = n_muntin - n_horizontal
        m_thickness = 0.010
        # horizontal muntins (constant z)
        for j in range(n_horizontal):
            frac = (j + 1) / (n_horizontal + 1)
            z = -glass_h / 2.0 + frac * glass_h
            sash_part.visual(
                Box((glass_w, m_thickness, m_thickness)),
                origin=Origin(xyz=(0.0, 0.0, z)),
                material=frame_mat,
                name=f"muntin_h_{j}",
            )
        # vertical muntins (constant x)
        for j in range(n_vertical):
            frac = (j + 1) / (n_vertical + 1)
            x = -glass_w / 2.0 + frac * glass_w
            sash_part.visual(
                Box((m_thickness, m_thickness, glass_h)),
                origin=Origin(xyz=(x, 0.0, 0.0)),
                material=frame_mat,
                name=f"muntin_v_{j}",
            )

    # Handle (only on sliding sashes per spec: "handle 必须附着在滑动窗扇上").
    if is_sliding:
        handle = resolved.handle_style
        # Handle Y placement: front face of sash
        front_y = sash_depth / 2.0
        if resolved.window_orientation == "horizontal":
            # Handle near the meeting stile (the stile that meets the neighbor).
            # For sash_index 0 the handle is on the right edge; for index 1 on
            # the left edge.  This makes the handle near the joint between the
            # two sashes, which matches double-hung / dual-slide reality.
            handle_x_offset = (
                sash_w / 2.0 - stile - 0.020 if sash_index == 0 else -sash_w / 2.0 + stile + 0.020
            )
            handle_z = 0.0
        else:
            # Vertical orientation: place the handle on the meeting rail
            # (between sashes vertically) of the bottom slider, or the top slider.
            handle_x_offset = 0.0
            handle_z = (
                sash_h / 2.0 - rail - 0.020 if sash_index == 0 else -sash_h / 2.0 + rail + 0.020
            )

        if handle == "tab":
            sash_part.visual(
                Box((0.040, 0.012, 0.045)),
                origin=Origin(xyz=(handle_x_offset, front_y + 0.006, handle_z)),
                material=accent_mat,
                name="handle",
            )
        elif handle == "bar":
            if resolved.window_orientation == "horizontal":
                sash_part.visual(
                    Box((0.022, 0.010, 0.130)),
                    origin=Origin(xyz=(handle_x_offset, front_y + 0.005, handle_z)),
                    material=accent_mat,
                    name="handle_plate",
                )
                sash_part.visual(
                    Cylinder(radius=0.010, length=0.150),
                    origin=Origin(xyz=(handle_x_offset, front_y + 0.022, handle_z)),
                    material=accent_mat,
                    name="handle",
                )
            else:
                sash_part.visual(
                    Box((0.130, 0.010, 0.022)),
                    origin=Origin(xyz=(handle_x_offset, front_y + 0.005, handle_z)),
                    material=accent_mat,
                    name="handle_plate",
                )
                sash_part.visual(
                    Cylinder(radius=0.010, length=0.150),
                    origin=Origin(
                        xyz=(handle_x_offset, front_y + 0.022, handle_z),
                        rpy=(0.0, 1.5707963, 0.0),
                    ),
                    material=accent_mat,
                    name="handle",
                )
        else:  # recessed
            sash_part.visual(
                Box((0.075, 0.008, 0.035)),
                origin=Origin(xyz=(handle_x_offset, front_y - 0.001, handle_z)),
                material=accent_mat,
                name="handle",
            )

        # Lock body attached to sliding sash if lock_style != "none".
        if resolved.lock_style != "none":
            lock_size = (
                (0.040, 0.014, 0.030)
                if resolved.lock_style == "small_latch"
                else (0.070, 0.014, 0.040)
            )
            sash_part.visual(
                Box(lock_size),
                origin=Origin(xyz=(0.0, front_y + 0.006, 0.0)),
                material=accent_mat,
                name="lock_body",
            )

        # Guide shoes / slider pads -- thin pads that ride in the track.  These
        # are decorative children of the sash (parent.visual).
        pad_thickness = 0.012
        if resolved.window_orientation == "horizontal":
            sash_part.visual(
                Box((0.080, sash_depth * 0.7, pad_thickness)),
                origin=Origin(xyz=(0.0, 0.0, sash_h / 2.0 - rail - pad_thickness / 2.0 - 0.002)),
                material=accent_mat,
                name="guide_shoe_top",
            )
            sash_part.visual(
                Box((0.080, sash_depth * 0.7, pad_thickness)),
                origin=Origin(xyz=(0.0, 0.0, -sash_h / 2.0 + rail + pad_thickness / 2.0 + 0.002)),
                material=accent_mat,
                name="guide_shoe_bottom",
            )
        else:
            sash_part.visual(
                Box((pad_thickness, sash_depth * 0.7, 0.080)),
                origin=Origin(xyz=(sash_w / 2.0 - stile - pad_thickness / 2.0 - 0.002, 0.0, 0.0)),
                material=accent_mat,
                name="guide_shoe_right",
            )
            sash_part.visual(
                Box((pad_thickness, sash_depth * 0.7, 0.080)),
                origin=Origin(xyz=(-sash_w / 2.0 + stile + pad_thickness / 2.0 + 0.002, 0.0, 0.0)),
                material=accent_mat,
                name="guide_shoe_left",
            )


# ---------------------------------------------------------------------------
# Top-level build
# ---------------------------------------------------------------------------


def _sash_closed_offset(resolved: ResolvedSlidingWindowConfig, sash_index: int) -> float:
    """Return the per-sash axial offset (X for horizontal, Z for vertical) of
    the sash centre when the window is in its **closed** (rest) configuration.

    Sashes are laid out from the negative side toward the positive side of the
    slide axis: index 0 sits at the negative end, index sash_count-1 at the
    positive end.
    """
    L = resolved.sash_axial_length
    inner = (
        resolved.inner_width
        if resolved.window_orientation == "horizontal"
        else resolved.inner_height
    )
    start = -inner / 2.0 + L / 2.0
    return start + sash_index * (L + SASH_GAP)


def build_sliding_window(
    config: SlidingWindowConfig | None = None,
    *,
    assets: AssetContext | None = None,
) -> ArticulatedObject:
    config = config or SlidingWindowConfig()
    resolved = resolve_config(config)
    if assets is None:
        assets = AssetContext(Path(tempfile.mkdtemp(prefix="articraft-sliding-window-assets-")))
    model = ArticulatedObject(name=resolved.name, assets=assets)

    frame_rgba, accent_rgba = MATERIAL_PALETTES[resolved.material_style]
    frame_mat = model.material(f"frame_{resolved.material_style}", rgba=frame_rgba)
    accent_mat = model.material(f"accent_{resolved.material_style}", rgba=accent_rgba)
    glass_mat = model.material(
        f"glass_{resolved.glass_opacity}", rgba=GLASS_PALETTES[resolved.glass_opacity]
    )

    window_frame = model.part("window_frame")
    _build_window_frame(
        window_frame,
        resolved,
        frame_mat=frame_mat,
        accent_mat=accent_mat,
    )

    depth_offsets = _depth_offsets_for_sashes(
        resolved.sash_count, resolved.sliding_sash_count, SASH_DEPTH
    )

    # The first ``sliding_sash_count`` indices are sliding sashes; the
    # remainder are fixed sashes.  The physical layout along the slide axis
    # has fixed and sliding sashes interleaved by their layout index (i.e.
    # sashes are placed in spatial slots 0..sash_count-1 along the slide axis,
    # but the **logical** index determines which is sliding).
    #
    # Layout convention: the leftmost (or bottom) sash is the slider when
    # there is one slider; with two sliders, the two extreme sashes slide
    # inward (typical dual-slide).  All non-sliding sashes are FIXED-jointed
    # to the frame at their respective slot.
    n = resolved.sash_count
    s = resolved.sliding_sash_count

    # slot_to_logical: maps spatial slot index -> logical sash index
    if s == 1:
        # slider is leftmost/bottom slot 0
        slot_to_logical = {0: 0}
        next_fixed = 1
        for slot in range(1, n):
            slot_to_logical[slot] = next_fixed
            next_fixed += 1
    else:
        # two sliders: slot 0 and slot n-1
        slot_to_logical = {0: 0, n - 1: 1}
        next_fixed = s
        for slot in range(1, n - 1):
            slot_to_logical[slot] = next_fixed
            next_fixed += 1

    # Travel budget: each slider can move along the slide axis until it would
    # leave the frame envelope.  Conservative upper bound:
    travel = max(
        0.05,
        resolved.sash_axial_length - 0.02 if s == 1 else (resolved.sash_axial_length * 0.95),
    )
    # But travel must not let the slider exit the inner aperture.  Each slider
    # starts at slot k; in the slide direction (toward the centre / opposite
    # end), at most it can move ``(inner_axial / 2) - (sash_axial / 2)`` if the
    # other sashes are fixed.  Use the conservative formula:
    inner_axial = (
        resolved.inner_width
        if resolved.window_orientation == "horizontal"
        else resolved.inner_height
    )
    max_safe_travel = inner_axial - resolved.sash_axial_length - 0.02
    travel = max(0.05, min(travel, max_safe_travel))

    # Build sashes
    for spatial_slot in range(n):
        logical_index = slot_to_logical[spatial_slot]
        is_sliding = logical_index < s
        sash_name = (
            f"sliding_sash_{logical_index}" if is_sliding else f"fixed_sash_{logical_index - s}"
        )
        sash_part = model.part(sash_name)
        _build_sash(
            sash_part,
            resolved,
            frame_mat=frame_mat,
            accent_mat=accent_mat,
            glass_mat=glass_mat,
            is_sliding=is_sliding,
            sash_index=logical_index if is_sliding else 0,
        )

        depth_y = depth_offsets[logical_index]
        slot_offset = _sash_closed_offset(resolved, spatial_slot)

        if resolved.window_orientation == "horizontal":
            origin = Origin(xyz=(slot_offset, depth_y, 0.0))
            axis = (1.0, 0.0, 0.0) if spatial_slot == 0 else (-1.0, 0.0, 0.0)
        else:
            origin = Origin(xyz=(0.0, depth_y, slot_offset))
            axis = (0.0, 0.0, 1.0) if spatial_slot == 0 else (0.0, 0.0, -1.0)

        if is_sliding:
            model.articulation(
                f"sliding_sash_{logical_index}_joint",
                ArticulationType.PRISMATIC,
                parent=window_frame,
                child=sash_part,
                origin=origin,
                axis=axis,
                motion_limits=MotionLimits(
                    effort=80.0,
                    velocity=0.45,
                    lower=0.0,
                    upper=travel,
                ),
            )
        else:
            model.articulation(
                f"fixed_sash_{logical_index - s}_joint",
                ArticulationType.FIXED,
                parent=window_frame,
                child=sash_part,
                origin=origin,
            )

    return model


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def run_sliding_window_tests(
    object_model: ArticulatedObject, config: SlidingWindowConfig
) -> TestReport:
    resolved = resolve_config(config)
    ctx = TestContext(object_model)
    window_frame = object_model.get_part("window_frame")

    # 1. At least one prismatic joint exists for the sliding sash(es).
    prismatic_joints = [
        j for j in object_model.articulations if j.articulation_type == ArticulationType.PRISMATIC
    ]
    ctx.check(
        "at_least_one_prismatic_joint",
        len(prismatic_joints) >= 1,
        details=f"found {len(prismatic_joints)} prismatic joints",
    )
    ctx.check(
        "prismatic_joint_count_matches_sliding_sash_count",
        len(prismatic_joints) == resolved.sliding_sash_count,
        details=(
            f"prismatic_joint_count={len(prismatic_joints)}, "
            f"sliding_sash_count={resolved.sliding_sash_count}"
        ),
    )

    # 2. Axis check: each prismatic axis aligned with the slide direction.
    if resolved.window_orientation == "horizontal":
        expected_abs_axis = (1.0, 0.0, 0.0)
    else:
        expected_abs_axis = (0.0, 0.0, 1.0)
    for joint in prismatic_joints:
        ax = joint.axis
        abs_ax = (abs(ax[0]), abs(ax[1]), abs(ax[2]))
        ctx.check(
            f"{joint.name}_axis_along_slide_direction",
            all(abs(a - e) < 1e-6 for a, e in zip(abs_ax, expected_abs_axis)),
            details=f"axis={ax}",
        )
        # Range check: travel must not exceed inner aperture along slide axis
        if joint.motion_limits is not None:
            upper = joint.motion_limits.upper or 0.0
            inner_axial = (
                resolved.inner_width
                if resolved.window_orientation == "horizontal"
                else resolved.inner_height
            )
            ctx.check(
                f"{joint.name}_travel_within_rail",
                upper > 0.01 and upper < inner_axial - 0.01,
                details=f"upper={upper}, inner_axial={inner_axial}",
            )

    # 3. Containment: every sash stays within the frame envelope at rest.
    for joint in object_model.articulations:
        if joint.parent != "window_frame":
            continue
        sash = object_model.get_part(joint.child)
        ctx.expect_within(
            sash,
            window_frame,
            axes="xz",
            margin=0.005,
            name=f"{sash.name}_contained_in_frame_rest",
        )

    # 4. Handle / lock not floating: ensure handle visuals are attached to
    #    sliding sash parts (by being present as visuals on those parts).
    for joint in prismatic_joints:
        sash = object_model.get_part(joint.child)
        visual_names = {v.name for v in sash.visuals if v.name is not None}
        ctx.check(
            f"{sash.name}_has_handle_visual",
            any(n == "handle" or n.startswith("handle") for n in visual_names),
            details=f"visuals={sorted(visual_names)}",
        )
        ctx.check(
            f"{sash.name}_has_glass_panel",
            "sash_glass" in visual_names,
            details=f"visuals={sorted(visual_names)}",
        )

    # 5. Muntin geometry matches grid_muntin_count.
    if resolved.grid_muntin_count > 0:
        for joint in object_model.articulations:
            if joint.parent != "window_frame":
                continue
            sash = object_model.get_part(joint.child)
            muntin_count = sum(
                1 for v in sash.visuals if v.name is not None and v.name.startswith("muntin_")
            )
            ctx.check(
                f"{sash.name}_muntin_count_matches_spec",
                muntin_count == resolved.grid_muntin_count,
                details=(f"muntin_count={muntin_count}, expected={resolved.grid_muntin_count}"),
            )

    # 6. Sliding-sash translates along the slide axis when posed at upper limit.
    for joint in prismatic_joints:
        sash = object_model.get_part(joint.child)
        rest_pos = ctx.part_world_position(sash)
        upper = joint.motion_limits.upper if joint.motion_limits else 0.0
        with ctx.pose({joint: upper}):
            open_pos = ctx.part_world_position(sash)
            ctx.expect_within(
                sash,
                window_frame,
                axes="xz",
                margin=0.020,
                name=f"{sash.name}_remains_in_frame_at_upper_limit",
            )
        if rest_pos is None or open_pos is None:
            continue
        if resolved.window_orientation == "horizontal":
            moved = abs(open_pos[0] - rest_pos[0])
        else:
            moved = abs(open_pos[2] - rest_pos[2])
        ctx.check(
            f"{joint.name}_actually_translates",
            moved > 0.04,
            details=f"rest={rest_pos}, open={open_pos}, moved={moved:.3f}",
        )

    # 7. Identity: at least window_frame + one sliding sash exist.
    sash_parts = [p for p in object_model.parts if p.name.startswith("sliding_sash_")]
    ctx.check(
        "has_window_frame_and_sliding_sashes",
        any(p.name == "window_frame" for p in object_model.parts) and len(sash_parts) >= 1,
        details=(
            f"window_frame_present={any(p.name == 'window_frame' for p in object_model.parts)}, "
            f"sliding_sash_count={len(sash_parts)}"
        ),
    )

    return ctx.report()


def build_seeded_sliding_window(
    seed: int, *, assets: AssetContext | None = None
) -> ArticulatedObject:
    return build_sliding_window(config_from_seed(seed), assets=assets)


def with_overrides(config: SlidingWindowConfig, **kwargs: object) -> SlidingWindowConfig:
    return replace(config, **kwargs)
