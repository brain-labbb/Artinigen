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

DeckShape = Literal["rectangle", "rounded", "ribbed"]
WheelType = Literal["all_caster", "mixed_steering", "all_fixed"]
HandleStyle = Literal["u_handle", "twin_bar", "single_bar", "none"]
SideRailStyle = Literal["none", "low", "full"]
BumperStyle = Literal["none", "corner", "full"]
AntiSlipPattern = Literal["none", "stripes", "dots", "grid"]
DeckAspectRatio = Literal["compact", "long", "wide"]
MaterialStyle = Literal["steel", "plastic", "aluminum"]

# Bucket -> (length_range, width_range) for the deck envelope.
DECK_ASPECT_RANGES: dict[DeckAspectRatio, tuple[tuple[float, float], tuple[float, float]]] = {
    "compact": ((0.55, 0.78), (0.40, 0.55)),
    "long": ((0.95, 1.35), (0.50, 0.66)),
    "wide": ((0.80, 1.05), (0.62, 0.80)),
}

GROUND_Z = 0.0
WHEEL_Z_GAP_MAX = 0.055  # spec: ground contact tolerance
DEFAULT_DECK_THICKNESS = 0.060

# Material palette per material_style. Each tuple holds:
# (deck_body, deck_trim, hardware_steel, dark_hardware, rubber, pad_color).
MATERIAL_PALETTES: dict[
    MaterialStyle,
    tuple[
        tuple[float, float, float, float],
        tuple[float, float, float, float],
        tuple[float, float, float, float],
        tuple[float, float, float, float],
        tuple[float, float, float, float],
        tuple[float, float, float, float],
    ],
] = {
    "steel": (
        (0.16, 0.30, 0.52, 1.0),
        (0.72, 0.74, 0.72, 1.0),
        (0.78, 0.80, 0.80, 1.0),
        (0.13, 0.13, 0.13, 1.0),
        (0.04, 0.04, 0.04, 1.0),
        (0.10, 0.10, 0.10, 1.0),
    ),
    "plastic": (
        (0.86, 0.36, 0.18, 1.0),
        (0.94, 0.92, 0.88, 1.0),
        (0.70, 0.70, 0.70, 1.0),
        (0.16, 0.16, 0.16, 1.0),
        (0.05, 0.05, 0.05, 1.0),
        (0.18, 0.18, 0.20, 1.0),
    ),
    "aluminum": (
        (0.82, 0.84, 0.86, 1.0),
        (0.72, 0.74, 0.76, 1.0),
        (0.86, 0.88, 0.90, 1.0),
        (0.22, 0.24, 0.26, 1.0),
        (0.04, 0.04, 0.04, 1.0),
        (0.14, 0.14, 0.14, 1.0),
    ),
}


@dataclass(frozen=True)
class PlatformCartConfig:
    deck_shape: DeckShape = "rectangle"
    wheel_count: int = 4
    wheel_type: WheelType = "all_caster"
    handle_style: HandleStyle = "u_handle"
    handle_fold_angle: float = 0.0  # rest angle, radians (0 = vertical, pi/2 = folded flat)
    side_rail: SideRailStyle = "none"
    bumper_style: BumperStyle = "none"
    anti_slip_pattern: AntiSlipPattern = "stripes"
    deck_aspect_ratio: DeckAspectRatio = "long"
    material_style: MaterialStyle = "steel"
    deck_length: float | None = None
    deck_width: float | None = None
    deck_thickness: float = DEFAULT_DECK_THICKNESS
    wheel_radius: float | None = None
    wheel_width: float | None = None
    handle_height: float | None = None
    handle_hinge_y_ratio: float | None = None  # in [0.2, 0.5]
    name: str = "reference_platform_cart"


@dataclass(frozen=True)
class ResolvedPlatformCartConfig:
    deck_shape: DeckShape
    wheel_count: int
    wheel_type: WheelType
    handle_style: HandleStyle
    handle_fold_angle: float
    side_rail: SideRailStyle
    bumper_style: BumperStyle
    anti_slip_pattern: AntiSlipPattern
    deck_aspect_ratio: DeckAspectRatio
    material_style: MaterialStyle
    deck_length: float
    deck_width: float
    deck_thickness: float
    wheel_radius: float
    wheel_width: float
    handle_height: float
    handle_hinge_y_ratio: float
    deck_top_z: float
    deck_center_z: float
    has_handle: bool
    has_steering: bool
    name: str


def config_from_seed(seed: int) -> PlatformCartConfig:
    rng = random.Random(seed)
    deck_aspect_ratio: DeckAspectRatio = rng.choice(("compact", "long", "wide"))
    (l_lo, l_hi), (w_lo, w_hi) = DECK_ASPECT_RANGES[deck_aspect_ratio]
    deck_length = round(rng.uniform(l_lo, l_hi), 3)
    deck_width = round(rng.uniform(w_lo, w_hi), 3)
    deck_thickness = round(rng.uniform(0.040, 0.075), 3)
    wheel_radius = round(rng.uniform(0.058, 0.095), 3)
    wheel_width = round(rng.uniform(0.030, 0.052), 3)
    wheel_count = rng.choice((4, 6))
    wheel_type: WheelType = rng.choices(
        ("all_caster", "mixed_steering", "all_fixed"),
        weights=(0.55, 0.25, 0.20),
        k=1,
    )[0]
    handle_style: HandleStyle = rng.choices(
        ("u_handle", "twin_bar", "single_bar", "none"),
        weights=(0.45, 0.20, 0.20, 0.15),
        k=1,
    )[0]
    handle_fold_angle = round(rng.uniform(0.0, math.pi / 2.0), 3) if handle_style != "none" else 0.0
    handle_height = round(rng.uniform(0.72, 1.05), 3)
    handle_hinge_y_ratio = round(rng.uniform(0.22, 0.48), 3)
    side_rail: SideRailStyle = rng.choices(
        ("none", "low", "full"),
        weights=(0.45, 0.35, 0.20),
        k=1,
    )[0]
    bumper_style: BumperStyle = rng.choices(
        ("none", "corner", "full"),
        weights=(0.45, 0.35, 0.20),
        k=1,
    )[0]
    anti_slip_pattern: AntiSlipPattern = rng.choices(
        ("none", "stripes", "dots", "grid"),
        weights=(0.15, 0.35, 0.25, 0.25),
        k=1,
    )[0]
    deck_shape: DeckShape = rng.choices(
        ("rectangle", "rounded", "ribbed"),
        weights=(0.55, 0.25, 0.20),
        k=1,
    )[0]
    material_style: MaterialStyle = rng.choice(("steel", "plastic", "aluminum"))
    return PlatformCartConfig(
        deck_shape=deck_shape,
        wheel_count=wheel_count,
        wheel_type=wheel_type,
        handle_style=handle_style,
        handle_fold_angle=handle_fold_angle,
        side_rail=side_rail,
        bumper_style=bumper_style,
        anti_slip_pattern=anti_slip_pattern,
        deck_aspect_ratio=deck_aspect_ratio,
        material_style=material_style,
        deck_length=deck_length,
        deck_width=deck_width,
        deck_thickness=deck_thickness,
        wheel_radius=wheel_radius,
        wheel_width=wheel_width,
        handle_height=handle_height,
        handle_hinge_y_ratio=handle_hinge_y_ratio,
        name=f"seeded_platform_cart_{seed}",
    )


def resolve_config(config: PlatformCartConfig) -> ResolvedPlatformCartConfig:
    if config.deck_shape not in {"rectangle", "rounded", "ribbed"}:
        raise ValueError(f"Unsupported deck_shape: {config.deck_shape}")
    if config.wheel_count not in {4, 6}:
        raise ValueError(f"Unsupported wheel_count: {config.wheel_count}")
    if config.wheel_type not in {"all_caster", "mixed_steering", "all_fixed"}:
        raise ValueError(f"Unsupported wheel_type: {config.wheel_type}")
    if config.handle_style not in {"u_handle", "twin_bar", "single_bar", "none"}:
        raise ValueError(f"Unsupported handle_style: {config.handle_style}")
    if config.side_rail not in {"none", "low", "full"}:
        raise ValueError(f"Unsupported side_rail: {config.side_rail}")
    if config.bumper_style not in {"none", "corner", "full"}:
        raise ValueError(f"Unsupported bumper_style: {config.bumper_style}")
    if config.anti_slip_pattern not in {"none", "stripes", "dots", "grid"}:
        raise ValueError(f"Unsupported anti_slip_pattern: {config.anti_slip_pattern}")
    if config.deck_aspect_ratio not in {"compact", "long", "wide"}:
        raise ValueError(f"Unsupported deck_aspect_ratio: {config.deck_aspect_ratio}")
    if config.material_style not in {"steel", "plastic", "aluminum"}:
        raise ValueError(f"Unsupported material_style: {config.material_style}")
    if not (0.0 <= config.handle_fold_angle <= math.pi / 2.0 + 1e-6):
        raise ValueError("handle_fold_angle must be in [0, pi/2]")

    (l_lo, l_hi), (w_lo, w_hi) = DECK_ASPECT_RANGES[config.deck_aspect_ratio]
    deck_length = config.deck_length if config.deck_length is not None else (l_lo + l_hi) * 0.5
    deck_width = config.deck_width if config.deck_width is not None else (w_lo + w_hi) * 0.5
    if deck_length <= 0.2 or deck_width <= 0.2:
        raise ValueError("deck envelope too small")
    deck_thickness = max(0.025, min(0.10, config.deck_thickness))

    wheel_radius = config.wheel_radius if config.wheel_radius is not None else 0.072
    wheel_width = config.wheel_width if config.wheel_width is not None else 0.040

    # Clamp wheel radius so wheels physically fit under deck without exceeding deck width / 2.
    max_wheel_radius = min(0.12, deck_width * 0.20)
    if wheel_radius > max_wheel_radius:
        wheel_radius = max_wheel_radius
    wheel_radius = max(0.040, wheel_radius)
    wheel_width = max(0.020, min(wheel_width, deck_width * 0.18))

    # Deck top-of-deck height: wheel radius (+ caster yoke for all_caster) + small ground clearance.
    if config.wheel_type == "all_caster":
        yoke_drop = 0.022  # caster swivel plate inset above wheel center
    else:
        yoke_drop = 0.008
    deck_center_z = wheel_radius + yoke_drop + deck_thickness * 0.5
    deck_top_z = deck_center_z + deck_thickness * 0.5

    handle_height = config.handle_height if config.handle_height is not None else 0.92
    handle_height = max(0.50, min(1.30, handle_height))
    handle_hinge_y_ratio = (
        config.handle_hinge_y_ratio if config.handle_hinge_y_ratio is not None else 0.35
    )
    handle_hinge_y_ratio = max(0.20, min(0.50, handle_hinge_y_ratio))

    has_handle = config.handle_style != "none"
    has_steering = config.wheel_type == "mixed_steering"

    return ResolvedPlatformCartConfig(
        deck_shape=config.deck_shape,
        wheel_count=config.wheel_count,
        wheel_type=config.wheel_type,
        handle_style=config.handle_style,
        handle_fold_angle=config.handle_fold_angle,
        side_rail=config.side_rail,
        bumper_style=config.bumper_style,
        anti_slip_pattern=config.anti_slip_pattern,
        deck_aspect_ratio=config.deck_aspect_ratio,
        material_style=config.material_style,
        deck_length=deck_length,
        deck_width=deck_width,
        deck_thickness=deck_thickness,
        wheel_radius=wheel_radius,
        wheel_width=wheel_width,
        handle_height=handle_height,
        handle_hinge_y_ratio=handle_hinge_y_ratio,
        deck_top_z=deck_top_z,
        deck_center_z=deck_center_z,
        has_handle=has_handle,
        has_steering=has_steering,
        name=config.name,
    )


# ---------------------------------------------------------------------------
# Layout helpers
# ---------------------------------------------------------------------------


def _wheel_layout(resolved: ResolvedPlatformCartConfig) -> list[tuple[str, float, float]]:
    """Return a list of (slot_name, x, y) for wheel mount positions on the deck.

    +y is forward (front). All positions in deck-frame xy (z fixed by caller).
    """
    L = resolved.deck_length
    W = resolved.deck_width
    inset_y = max(0.07, resolved.wheel_radius + 0.025)
    inset_x = max(0.06, resolved.wheel_width * 0.5 + 0.018)
    front_y = (L * 0.5) - inset_y
    rear_y = -front_y
    left_x = -(W * 0.5 - inset_x)
    right_x = -left_x
    if resolved.wheel_count == 4:
        return [
            ("front_left", left_x, front_y),
            ("front_right", right_x, front_y),
            ("rear_left", left_x, rear_y),
            ("rear_right", right_x, rear_y),
        ]
    # wheel_count == 6: add a mid pair
    return [
        ("front_left", left_x, front_y),
        ("front_right", right_x, front_y),
        ("mid_left", left_x, 0.0),
        ("mid_right", right_x, 0.0),
        ("rear_left", left_x, rear_y),
        ("rear_right", right_x, rear_y),
    ]


def _slot_is_steering(slot_name: str, resolved: ResolvedPlatformCartConfig) -> bool:
    """Whether this slot belongs to the front steering bridge (mixed_steering only)."""
    if resolved.wheel_type != "mixed_steering":
        return False
    return slot_name.startswith("front_")


def _slot_uses_caster_swivel(slot_name: str, resolved: ResolvedPlatformCartConfig) -> bool:
    if resolved.wheel_type == "all_caster":
        return True
    if resolved.wheel_type == "mixed_steering":
        # rear and mid wheels stay fixed; only the front pair swivels via steering bridge,
        # not via independent caster swivels.
        return False
    return False


# ---------------------------------------------------------------------------
# Deck builders
# ---------------------------------------------------------------------------


def _add_deck_shell(part, resolved: ResolvedPlatformCartConfig, *, deck_color, trim) -> None:
    L = resolved.deck_length
    W = resolved.deck_width
    th = resolved.deck_thickness
    z = resolved.deck_center_z
    if resolved.deck_shape == "rectangle":
        part.visual(
            Box((W, L, th)),
            origin=Origin(xyz=(0.0, 0.0, z)),
            material=deck_color,
            name="deck_shell",
        )
    elif resolved.deck_shape == "rounded":
        # main slab inset, with rounded end caps
        inset = max(0.04, min(L * 0.18, 0.18))
        part.visual(
            Box((W, L - 2 * inset, th)),
            origin=Origin(xyz=(0.0, 0.0, z)),
            material=deck_color,
            name="deck_shell",
        )
        for sign, label in ((1.0, "front"), (-1.0, "rear")):
            part.visual(
                Cylinder(radius=W * 0.5, length=th),
                origin=Origin(xyz=(0.0, sign * (L * 0.5 - inset), z)),
                material=deck_color,
                name=f"deck_{label}_cap",
            )
    else:  # ribbed
        part.visual(
            Box((W, L, th)),
            origin=Origin(xyz=(0.0, 0.0, z)),
            material=deck_color,
            name="deck_shell",
        )
        rib_count = 5
        rib_w = max(0.008, W * 0.018)
        for i in range(rib_count):
            ry = -L * 0.5 + (i + 0.5) * (L / rib_count)
            part.visual(
                Box((W * 0.92, rib_w, th * 0.35)),
                origin=Origin(xyz=(0.0, ry, z + th * 0.5)),
                material=trim,
                name=f"deck_rib_{i}",
            )


def _add_anti_slip_pad(part, resolved: ResolvedPlatformCartConfig, *, pad_mat) -> None:
    if resolved.anti_slip_pattern == "none":
        return
    L = resolved.deck_length
    W = resolved.deck_width
    pad_z = resolved.deck_top_z + 0.003
    pad_th = 0.004
    inset = 0.035
    part.visual(
        Box((W - 2 * inset, L - 2 * inset, pad_th)),
        origin=Origin(xyz=(0.0, 0.0, pad_z)),
        material=pad_mat,
        name="anti_slip_pad",
    )
    if resolved.anti_slip_pattern == "stripes":
        stripe_count = 9
        stripe_w = max(0.010, (L - 2 * inset) / (stripe_count * 2.2))
        usable_y = L - 2 * inset - 0.020
        for i in range(stripe_count):
            sy = -usable_y * 0.5 + (i + 0.5) * (usable_y / stripe_count)
            part.visual(
                Box((W - 2 * inset - 0.020, stripe_w, 0.0025)),
                origin=Origin(xyz=(0.0, sy, pad_z + pad_th * 0.5 + 0.0012)),
                material=pad_mat,
                name=f"anti_slip_stripe_{i}",
            )
    elif resolved.anti_slip_pattern == "dots":
        cols = 5
        rows = max(5, int(L / W * cols))
        usable_w = W - 2 * inset - 0.025
        usable_l = L - 2 * inset - 0.025
        for ci in range(cols):
            for ri in range(rows):
                cx = -usable_w * 0.5 + (ci + 0.5) * (usable_w / cols)
                ry = -usable_l * 0.5 + (ri + 0.5) * (usable_l / rows)
                part.visual(
                    Cylinder(radius=0.010, length=0.003),
                    origin=Origin(xyz=(cx, ry, pad_z + pad_th * 0.5 + 0.0015)),
                    material=pad_mat,
                    name=f"anti_slip_dot_{ci}_{ri}",
                )
    else:  # grid
        usable_w = W - 2 * inset - 0.020
        usable_l = L - 2 * inset - 0.020
        rib_w = 0.006
        cols = 4
        rows = max(4, int(L / W * cols))
        for ci in range(cols + 1):
            cx = -usable_w * 0.5 + ci * (usable_w / cols)
            part.visual(
                Box((rib_w, usable_l, 0.0025)),
                origin=Origin(xyz=(cx, 0.0, pad_z + pad_th * 0.5 + 0.0012)),
                material=pad_mat,
                name=f"anti_slip_grid_col_{ci}",
            )
        for ri in range(rows + 1):
            ry = -usable_l * 0.5 + ri * (usable_l / rows)
            part.visual(
                Box((usable_w, rib_w, 0.0025)),
                origin=Origin(xyz=(0.0, ry, pad_z + pad_th * 0.5 + 0.0012)),
                material=pad_mat,
                name=f"anti_slip_grid_row_{ri}",
            )


def _add_side_rails(part, resolved: ResolvedPlatformCartConfig, *, trim) -> None:
    if resolved.side_rail == "none":
        return
    L = resolved.deck_length
    W = resolved.deck_width
    z0 = resolved.deck_top_z
    if resolved.side_rail == "low":
        rail_h = 0.055
    else:  # full
        rail_h = 0.220
    post_count = 4 if resolved.side_rail == "low" else 5
    post_r = 0.010 if resolved.side_rail == "low" else 0.012
    side_lip_t = 0.018
    # continuous side lip strip on the deck edges
    for sign, lab in ((1.0, "right"), (-1.0, "left")):
        part.visual(
            Box((side_lip_t, L * 0.95, rail_h)),
            origin=Origin(xyz=(sign * (W * 0.5 - side_lip_t * 0.5), 0.0, z0 + rail_h * 0.5)),
            material=trim,
            name=f"{lab}_side_rail_panel",
        )
    if resolved.side_rail == "full":
        # add vertical posts and a top horizontal bar on each long side
        for sign, lab in ((1.0, "right"), (-1.0, "left")):
            x_post = sign * (W * 0.5 - 0.020)
            for i in range(post_count):
                py = -L * 0.45 + i * (L * 0.9 / max(1, post_count - 1))
                part.visual(
                    Cylinder(radius=post_r, length=rail_h),
                    origin=Origin(xyz=(x_post, py, z0 + rail_h * 0.5)),
                    material=trim,
                    name=f"{lab}_rail_post_{i}",
                )
            part.visual(
                Box((0.016, L * 0.92, 0.016)),
                origin=Origin(xyz=(x_post, 0.0, z0 + rail_h - 0.012)),
                material=trim,
                name=f"{lab}_rail_top",
            )


def _add_bumpers(part, resolved: ResolvedPlatformCartConfig, *, trim) -> None:
    if resolved.bumper_style == "none":
        return
    L = resolved.deck_length
    W = resolved.deck_width
    z = resolved.deck_center_z
    bumper_th = 0.022
    bumper_h = resolved.deck_thickness + 0.018
    if resolved.bumper_style == "corner":
        size_xy = 0.090
        for sx, lx in ((1.0, "right"), (-1.0, "left")):
            for sy, ly in ((1.0, "front"), (-1.0, "rear")):
                part.visual(
                    Box((size_xy, bumper_th, bumper_h)),
                    origin=Origin(
                        xyz=(
                            sx * (W * 0.5 - size_xy * 0.5),
                            sy * (L * 0.5 + bumper_th * 0.5),
                            z,
                        )
                    ),
                    material=trim,
                    name=f"bumper_corner_{ly}_{lx}_long",
                )
                part.visual(
                    Box((bumper_th, size_xy, bumper_h)),
                    origin=Origin(
                        xyz=(
                            sx * (W * 0.5 + bumper_th * 0.5),
                            sy * (L * 0.5 - size_xy * 0.5),
                            z,
                        )
                    ),
                    material=trim,
                    name=f"bumper_corner_{ly}_{lx}_short",
                )
    else:  # full
        for sy, ly in ((1.0, "front"), (-1.0, "rear")):
            part.visual(
                Box((W + 2 * bumper_th, bumper_th, bumper_h)),
                origin=Origin(xyz=(0.0, sy * (L * 0.5 + bumper_th * 0.5), z)),
                material=trim,
                name=f"bumper_strip_{ly}",
            )
        for sx, lx in ((1.0, "right"), (-1.0, "left")):
            part.visual(
                Box((bumper_th, L, bumper_h)),
                origin=Origin(xyz=(sx * (W * 0.5 + bumper_th * 0.5), 0.0, z)),
                material=trim,
                name=f"bumper_strip_{lx}",
            )


def _add_caster_mount_plates(part, resolved: ResolvedPlatformCartConfig, *, hardware) -> None:
    # Each caster needs a small mount plate beneath the deck (decorative non-articulated).
    for slot_name, x, y in _wheel_layout(resolved):
        if not _slot_uses_caster_swivel(slot_name, resolved):
            continue
        part.visual(
            Box((0.110, 0.090, 0.010)),
            origin=Origin(
                xyz=(
                    x,
                    y,
                    resolved.deck_center_z - resolved.deck_thickness * 0.5 - 0.005,
                )
            ),
            material=hardware,
            name=f"{slot_name}_caster_mount",
        )


def _add_handle_hinge_ears(part, resolved: ResolvedPlatformCartConfig, *, hardware) -> None:
    if not resolved.has_handle:
        return
    hinge_y = resolved.handle_hinge_y_ratio * resolved.deck_length
    ear_z = resolved.deck_top_z + 0.030
    ear_offset_x = max(0.085, resolved.deck_width * 0.32)
    for sx, lab in ((1.0, "right"), (-1.0, "left")):
        part.visual(
            Box((0.030, 0.055, 0.060)),
            origin=Origin(xyz=(sx * ear_offset_x, hinge_y, ear_z)),
            material=hardware,
            name=f"handle_hinge_ear_{lab}",
        )


# ---------------------------------------------------------------------------
# Handle builders
# ---------------------------------------------------------------------------


def _build_handle_u_handle(
    handle_part, resolved: ResolvedPlatformCartConfig, *, hardware, rubber
) -> None:
    """U-shape handle anchored at hinge frame. Origin = hinge axis center on deck.

    In the joint frame the handle extends along local +Z when q=0 (vertical),
    and folds forward (toward +Y) as q grows.
    """
    H = resolved.handle_height
    half_w = max(0.10, resolved.deck_width * 0.32)
    leg_r = 0.014
    handle_part.visual(
        Cylinder(radius=leg_r, length=H),
        origin=Origin(xyz=(-half_w, 0.0, H * 0.5)),
        material=hardware,
        name="leg_left",
    )
    handle_part.visual(
        Cylinder(radius=leg_r, length=H),
        origin=Origin(xyz=(half_w, 0.0, H * 0.5)),
        material=hardware,
        name="leg_right",
    )
    # top crossbar
    handle_part.visual(
        Cylinder(radius=0.016, length=2 * half_w),
        origin=Origin(xyz=(0.0, 0.0, H), rpy=(0.0, math.pi / 2.0, 0.0)),
        material=hardware,
        name="crossbar",
    )
    handle_part.visual(
        Cylinder(radius=0.022, length=2 * half_w * 0.6),
        origin=Origin(xyz=(0.0, 0.0, H), rpy=(0.0, math.pi / 2.0, 0.0)),
        material=rubber,
        name="grip_sleeve",
    )


def _build_handle_twin_bar(
    handle_part, resolved: ResolvedPlatformCartConfig, *, hardware, rubber
) -> None:
    H = resolved.handle_height
    half_w = max(0.10, resolved.deck_width * 0.32)
    # twin parallel bars at upper portion connecting two side legs
    handle_part.visual(
        Cylinder(radius=0.013, length=H),
        origin=Origin(xyz=(-half_w, 0.0, H * 0.5)),
        material=hardware,
        name="leg_left",
    )
    handle_part.visual(
        Cylinder(radius=0.013, length=H),
        origin=Origin(xyz=(half_w, 0.0, H * 0.5)),
        material=hardware,
        name="leg_right",
    )
    handle_part.visual(
        Cylinder(radius=0.014, length=2 * half_w),
        origin=Origin(xyz=(0.0, 0.0, H), rpy=(0.0, math.pi / 2.0, 0.0)),
        material=hardware,
        name="upper_bar",
    )
    handle_part.visual(
        Cylinder(radius=0.014, length=2 * half_w),
        origin=Origin(xyz=(0.0, 0.0, H - 0.110), rpy=(0.0, math.pi / 2.0, 0.0)),
        material=hardware,
        name="lower_bar",
    )
    handle_part.visual(
        Cylinder(radius=0.020, length=2 * half_w * 0.6),
        origin=Origin(xyz=(0.0, 0.0, H), rpy=(0.0, math.pi / 2.0, 0.0)),
        material=rubber,
        name="grip_sleeve",
    )


def _build_handle_single_bar(
    handle_part, resolved: ResolvedPlatformCartConfig, *, hardware, rubber
) -> None:
    H = resolved.handle_height
    # one central post + transverse grip bar
    handle_part.visual(
        Cylinder(radius=0.020, length=H),
        origin=Origin(xyz=(0.0, 0.0, H * 0.5)),
        material=hardware,
        name="center_post",
    )
    bar_len = max(0.30, resolved.deck_width * 0.85)
    handle_part.visual(
        Cylinder(radius=0.016, length=bar_len),
        origin=Origin(xyz=(0.0, 0.0, H), rpy=(0.0, math.pi / 2.0, 0.0)),
        material=hardware,
        name="grip_bar",
    )
    handle_part.visual(
        Cylinder(radius=0.022, length=bar_len * 0.6),
        origin=Origin(xyz=(0.0, 0.0, H), rpy=(0.0, math.pi / 2.0, 0.0)),
        material=rubber,
        name="grip_sleeve",
    )


HANDLE_BUILDERS = {
    "u_handle": _build_handle_u_handle,
    "twin_bar": _build_handle_twin_bar,
    "single_bar": _build_handle_single_bar,
}


# ---------------------------------------------------------------------------
# Caster fork helpers
# ---------------------------------------------------------------------------


def _add_caster_fork_geometry(
    fork_part, resolved: ResolvedPlatformCartConfig, *, hardware, dark
) -> None:
    """Geometry of the caster yoke that hangs below the swivel plate.

    Origin = caster swivel axis where it meets the deck mount plate.
    Local -Z drops down to the wheel center.
    """
    yoke_drop = 0.022
    wheel_r = resolved.wheel_radius
    fork_part.visual(
        Cylinder(radius=0.046, length=0.012),
        origin=Origin(xyz=(0.0, 0.0, -0.006)),
        material=hardware,
        name="swivel_plate",
    )
    fork_part.visual(
        Cylinder(radius=0.014, length=0.030),
        origin=Origin(xyz=(0.0, 0.0, -0.024)),
        material=dark,
        name="kingpin",
    )
    fork_part.visual(
        Box((0.084, 0.060, 0.020)),
        origin=Origin(xyz=(0.0, 0.0, -0.040)),
        material=hardware,
        name="fork_crown",
    )
    leg_z = -(yoke_drop + wheel_r * 0.5)
    leg_h = wheel_r + 0.020
    fork_part.visual(
        Box((0.008, 0.060, leg_h)),
        origin=Origin(xyz=(0.032, 0.0, leg_z)),
        material=hardware,
        name="fork_cheek_outer",
    )
    fork_part.visual(
        Box((0.008, 0.060, leg_h)),
        origin=Origin(xyz=(-0.032, 0.0, leg_z)),
        material=hardware,
        name="fork_cheek_inner",
    )
    # axle stub (decorative)
    axle_z = -(yoke_drop + wheel_r)
    fork_part.visual(
        Cylinder(radius=0.008, length=0.075),
        origin=Origin(xyz=(0.0, 0.0, axle_z), rpy=(0.0, math.pi / 2.0, 0.0)),
        material=dark,
        name="axle_stub",
    )


def _add_fixed_wheel_yoke(
    parent_part,
    resolved: ResolvedPlatformCartConfig,
    *,
    slot_x: float,
    slot_y: float,
    slot_name: str,
    hardware,
    dark,
) -> None:
    """Decorative fork brackets for fixed (non-swivel) wheels, mounted to the deck."""
    yoke_drop = 0.008
    wheel_r = resolved.wheel_radius
    bracket_z = resolved.deck_center_z - resolved.deck_thickness * 0.5 - yoke_drop * 0.5
    parent_part.visual(
        Box((0.110, 0.090, 0.010)),
        origin=Origin(xyz=(slot_x, slot_y, bracket_z)),
        material=hardware,
        name=f"{slot_name}_fixed_mount",
    )
    leg_h = wheel_r + 0.020
    leg_center_z = (
        resolved.deck_center_z - resolved.deck_thickness * 0.5 - yoke_drop - wheel_r * 0.5
    )
    parent_part.visual(
        Box((0.010, 0.060, leg_h)),
        origin=Origin(xyz=(slot_x + (resolved.wheel_width * 0.5 + 0.014), slot_y, leg_center_z)),
        material=hardware,
        name=f"{slot_name}_fork_outer",
    )
    parent_part.visual(
        Box((0.010, 0.060, leg_h)),
        origin=Origin(xyz=(slot_x - (resolved.wheel_width * 0.5 + 0.014), slot_y, leg_center_z)),
        material=hardware,
        name=f"{slot_name}_fork_inner",
    )
    axle_z = resolved.deck_center_z - resolved.deck_thickness * 0.5 - yoke_drop - wheel_r
    parent_part.visual(
        Cylinder(radius=0.008, length=resolved.wheel_width + 0.040),
        origin=Origin(
            xyz=(slot_x, slot_y, axle_z),
            rpy=(0.0, math.pi / 2.0, 0.0),
        ),
        material=dark,
        name=f"{slot_name}_axle_stub",
    )


# ---------------------------------------------------------------------------
# Steering bridge (for mixed_steering)
# ---------------------------------------------------------------------------


def _add_steering_bridge_geometry(
    bridge_part,
    resolved: ResolvedPlatformCartConfig,
    *,
    hardware,
    dark,
    front_slots: list[tuple[str, float, float]],
) -> None:
    # bridge is a horizontal bar spanning the two front wheel x positions.
    if not front_slots:
        return
    left_x = min(x for _, x, _ in front_slots)
    right_x = max(x for _, x, _ in front_slots)
    bar_length = (right_x - left_x) + 0.140
    bridge_part.visual(
        Box((bar_length, 0.060, 0.024)),
        origin=Origin(xyz=(0.0, 0.0, -0.014)),
        material=hardware,
        name="steering_bar",
    )
    bridge_part.visual(
        Cylinder(radius=0.018, length=0.040),
        origin=Origin(xyz=(0.0, 0.0, 0.005)),
        material=dark,
        name="steering_kingpin",
    )
    wheel_r = resolved.wheel_radius
    yoke_drop = 0.020
    for slot_name, x, _y in front_slots:
        local_x = x  # the bridge frame is centered between the two front wheels along x
        leg_h = wheel_r + 0.020
        leg_center_z = -(yoke_drop + wheel_r * 0.5)
        bridge_part.visual(
            Box((0.010, 0.060, leg_h)),
            origin=Origin(xyz=(local_x + resolved.wheel_width * 0.5 + 0.014, 0.0, leg_center_z)),
            material=hardware,
            name=f"{slot_name}_bridge_fork_outer",
        )
        bridge_part.visual(
            Box((0.010, 0.060, leg_h)),
            origin=Origin(xyz=(local_x - resolved.wheel_width * 0.5 - 0.014, 0.0, leg_center_z)),
            material=hardware,
            name=f"{slot_name}_bridge_fork_inner",
        )
        bridge_part.visual(
            Cylinder(radius=0.008, length=resolved.wheel_width + 0.040),
            origin=Origin(
                xyz=(local_x, 0.0, -(yoke_drop + wheel_r)),
                rpy=(0.0, math.pi / 2.0, 0.0),
            ),
            material=dark,
            name=f"{slot_name}_bridge_axle_stub",
        )


# ---------------------------------------------------------------------------
# Build entry point
# ---------------------------------------------------------------------------


def build_platform_cart(
    config: PlatformCartConfig | None = None, *, assets: AssetContext | None = None
) -> ArticulatedObject:
    config = config or PlatformCartConfig()
    resolved = resolve_config(config)
    if assets is None:
        assets = AssetContext(Path(tempfile.mkdtemp(prefix="articraft-platform-cart-assets-")))
    model = ArticulatedObject(name=resolved.name, assets=assets)

    palette = MATERIAL_PALETTES[resolved.material_style]
    deck_color = model.material("deck_body", rgba=palette[0])
    trim = model.material("deck_trim", rgba=palette[1])
    hardware = model.material("cart_hardware", rgba=palette[2])
    dark = model.material("dark_hardware", rgba=palette[3])
    rubber = model.material("tire_rubber", rgba=palette[4])
    pad_mat = model.material("anti_slip", rgba=palette[5])

    deck = model.part("deck")
    _add_deck_shell(deck, resolved, deck_color=deck_color, trim=trim)
    _add_anti_slip_pad(deck, resolved, pad_mat=pad_mat)
    _add_side_rails(deck, resolved, trim=trim)
    _add_bumpers(deck, resolved, trim=trim)
    _add_caster_mount_plates(deck, resolved, hardware=hardware)
    _add_handle_hinge_ears(deck, resolved, hardware=hardware)

    layout = _wheel_layout(resolved)
    front_slots = [(n, x, y) for (n, x, y) in layout if n.startswith("front_")]

    # Optional steering bridge for mixed_steering.
    if resolved.has_steering:
        bridge = model.part("steering_bridge")
        # Bridge origin: midpoint of front wheel slots, at deck bottom minus a small drop.
        bridge_x = 0.0
        bridge_y = front_slots[0][2]
        bridge_z = resolved.deck_center_z - resolved.deck_thickness * 0.5 - 0.010
        # Re-center the front slot x coords relative to bridge origin (which is at x=0).
        relative_front_slots = [(n, x - bridge_x, y - bridge_y) for (n, x, y) in front_slots]
        _add_steering_bridge_geometry(
            bridge,
            resolved,
            hardware=hardware,
            dark=dark,
            front_slots=relative_front_slots,
        )
        model.articulation(
            "steering_joint",
            ArticulationType.REVOLUTE,
            parent=deck,
            child=bridge,
            origin=Origin(xyz=(bridge_x, bridge_y, bridge_z)),
            axis=(0.0, 0.0, 1.0),
            motion_limits=MotionLimits(
                effort=30.0,
                velocity=4.0,
                lower=-math.pi / 4.0,
                upper=math.pi / 4.0,
            ),
        )

    # Wheel articulations.
    wheel_index = 0
    caster_index = 0
    yoke_drop_caster = 0.022
    yoke_drop_fixed = 0.008
    bridge_yoke_drop = 0.020
    for slot_name, x, y in layout:
        steered = _slot_is_steering(slot_name, resolved)
        cast = _slot_uses_caster_swivel(slot_name, resolved)

        if cast:
            # Independent caster: caster yoke part + spinning wheel child.
            caster_part = model.part(f"caster_{slot_name}")
            _add_caster_fork_geometry(caster_part, resolved, hardware=hardware, dark=dark)
            caster_origin = Origin(
                xyz=(
                    x,
                    y,
                    resolved.deck_center_z - resolved.deck_thickness * 0.5,
                )
            )
            model.articulation(
                f"caster_{caster_index}_joint",
                ArticulationType.CONTINUOUS,
                parent=deck,
                child=caster_part,
                origin=caster_origin,
                axis=(0.0, 0.0, 1.0),
                motion_limits=MotionLimits(effort=15.0, velocity=6.0),
            )
            caster_index += 1

            wheel_part = model.part(f"wheel_{slot_name}")
            _add_wheel_geometry(wheel_part, resolved, rubber=rubber, hardware=hardware)
            model.articulation(
                f"wheel_{wheel_index}_joint",
                ArticulationType.CONTINUOUS,
                parent=caster_part,
                child=wheel_part,
                origin=Origin(xyz=(0.0, 0.0, -(yoke_drop_caster + resolved.wheel_radius))),
                axis=(1.0, 0.0, 0.0),
                motion_limits=MotionLimits(effort=10.0, velocity=20.0),
            )
            wheel_index += 1
            continue

        if steered:
            # Wheel hangs from the steering bridge (its own continuous spin only).
            wheel_part = model.part(f"wheel_{slot_name}")
            _add_wheel_geometry(wheel_part, resolved, rubber=rubber, hardware=hardware)
            # Relative to bridge frame (which is centered at midpoint of front slots).
            bridge_y = front_slots[0][2]
            rel_x = x - 0.0
            rel_y = y - bridge_y
            model.articulation(
                f"wheel_{wheel_index}_joint",
                ArticulationType.CONTINUOUS,
                parent="steering_bridge",
                child=wheel_part,
                origin=Origin(xyz=(rel_x, rel_y, -(bridge_yoke_drop + resolved.wheel_radius))),
                axis=(1.0, 0.0, 0.0),
                motion_limits=MotionLimits(effort=10.0, velocity=20.0),
            )
            wheel_index += 1
            continue

        # Fixed wheel: yoke is decorative on deck; wheel is a part with continuous spin.
        _add_fixed_wheel_yoke(
            deck,
            resolved,
            slot_x=x,
            slot_y=y,
            slot_name=slot_name,
            hardware=hardware,
            dark=dark,
        )
        wheel_part = model.part(f"wheel_{slot_name}")
        _add_wheel_geometry(wheel_part, resolved, rubber=rubber, hardware=hardware)
        model.articulation(
            f"wheel_{wheel_index}_joint",
            ArticulationType.CONTINUOUS,
            parent=deck,
            child=wheel_part,
            origin=Origin(
                xyz=(
                    x,
                    y,
                    resolved.deck_center_z
                    - resolved.deck_thickness * 0.5
                    - yoke_drop_fixed
                    - resolved.wheel_radius,
                )
            ),
            axis=(1.0, 0.0, 0.0),
            motion_limits=MotionLimits(effort=10.0, velocity=20.0),
        )
        wheel_index += 1

    # Handle.
    if resolved.has_handle:
        handle = model.part("handle")
        builder = HANDLE_BUILDERS[resolved.handle_style]
        builder(handle, resolved, hardware=hardware, rubber=rubber)
        hinge_y = resolved.handle_hinge_y_ratio * resolved.deck_length
        hinge_z = resolved.deck_top_z + 0.030
        # Handle joint frame is rotated so that local +Z (where the handle extends)
        # aligns with the desired rest direction. Hinge axis is along world X
        # (axis=(1, 0, 0)), so a positive q tips the top of the handle toward +Y
        # (forward), folding it flat onto the deck.
        # At q = handle_fold_angle the handle is at its rest pose.
        model.articulation(
            "handle_joint",
            ArticulationType.REVOLUTE,
            parent=deck,
            child=handle,
            origin=Origin(xyz=(0.0, hinge_y, hinge_z)),
            axis=(1.0, 0.0, 0.0),
            motion_limits=MotionLimits(
                effort=30.0,
                velocity=2.0,
                lower=0.0,
                upper=math.pi / 2.0,
            ),
        )

    return model


def _add_wheel_geometry(
    wheel_part, resolved: ResolvedPlatformCartConfig, *, rubber, hardware
) -> None:
    """Wheel local frame: spin axis along +X, wheel cylinder length along its own +Z
    rotated to align with +X via rpy=(0, pi/2, 0)."""
    r = resolved.wheel_radius
    w = resolved.wheel_width
    wheel_part.visual(
        Cylinder(radius=r, length=w),
        origin=Origin(xyz=(0.0, 0.0, 0.0), rpy=(0.0, math.pi / 2.0, 0.0)),
        material=rubber,
        name="tire",
    )
    wheel_part.visual(
        Cylinder(radius=r * 0.55, length=w * 1.04),
        origin=Origin(xyz=(0.0, 0.0, 0.0), rpy=(0.0, math.pi / 2.0, 0.0)),
        material=hardware,
        name="rim",
    )
    wheel_part.visual(
        Cylinder(radius=r * 0.18, length=w * 1.10),
        origin=Origin(xyz=(0.0, 0.0, 0.0), rpy=(0.0, math.pi / 2.0, 0.0)),
        material=hardware,
        name="hub",
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def run_platform_cart_tests(
    object_model: ArticulatedObject, config: PlatformCartConfig
) -> TestReport:
    resolved = resolve_config(config)
    ctx = TestContext(object_model)
    deck = object_model.get_part("deck")

    layout = _wheel_layout(resolved)
    wheel_index = 0
    caster_index = 0
    for slot_name, _x, _y in layout:
        steered = _slot_is_steering(slot_name, resolved)
        cast = _slot_uses_caster_swivel(slot_name, resolved)
        wheel_part = object_model.get_part(f"wheel_{slot_name}")
        wheel_joint = object_model.get_articulation(f"wheel_{wheel_index}_joint")
        ctx.check(
            f"wheel_{wheel_index}_continuous_axis",
            wheel_joint.articulation_type == ArticulationType.CONTINUOUS
            and tuple(wheel_joint.axis) == (1.0, 0.0, 0.0),
            details=(f"type={wheel_joint.articulation_type}, axis={wheel_joint.axis}"),
        )
        if cast:
            caster_part = object_model.get_part(f"caster_{slot_name}")
            caster_joint = object_model.get_articulation(f"caster_{caster_index}_joint")
            ctx.check(
                f"caster_{caster_index}_vertical_swivel",
                caster_joint.articulation_type == ArticulationType.CONTINUOUS
                and tuple(caster_joint.axis) == (0.0, 0.0, 1.0),
                details=(f"type={caster_joint.articulation_type}, axis={caster_joint.axis}"),
            )
            ctx.allow_overlap(
                caster_part,
                wheel_part,
                elem_a="axle_stub",
                elem_b="hub",
                reason="The caster axle stub is captured by the wheel hub.",
            )
            caster_index += 1
        elif steered:
            ctx.allow_overlap(
                object_model.get_part("steering_bridge"),
                wheel_part,
                elem_a=f"{slot_name}_bridge_axle_stub",
                elem_b="hub",
                reason="The steering bridge axle stub is captured by the wheel hub.",
            )
        else:
            ctx.allow_overlap(
                deck,
                wheel_part,
                elem_a=f"{slot_name}_axle_stub",
                elem_b="hub",
                reason="The fixed wheel axle stub is captured by the wheel hub.",
            )
        # Wheel must be close to the ground (z gap <= WHEEL_Z_GAP_MAX).
        wheel_aabb = ctx.part_world_aabb(wheel_part)
        if wheel_aabb is not None:
            low = wheel_aabb[0]
            low_z = low[2] if hasattr(low, "__getitem__") else low.z
            ctx.check(
                f"wheel_{wheel_index}_ground_contact",
                low_z <= GROUND_Z + WHEEL_Z_GAP_MAX + 1e-6,
                details=f"low_z={low_z}",
            )
        wheel_index += 1

    if resolved.has_steering:
        steering_joint = object_model.get_articulation("steering_joint")
        ctx.check(
            "steering_axis_vertical",
            steering_joint.articulation_type == ArticulationType.REVOLUTE
            and tuple(steering_joint.axis) == (0.0, 0.0, 1.0),
            details=f"axis={steering_joint.axis}",
        )

    if resolved.has_handle:
        handle = object_model.get_part("handle")
        handle_joint = object_model.get_articulation("handle_joint")
        ctx.check(
            "handle_axis_horizontal",
            handle_joint.articulation_type == ArticulationType.REVOLUTE
            and abs(handle_joint.axis[2]) < 1e-6,
            details=f"axis={handle_joint.axis}",
        )
        hinge_y = resolved.handle_hinge_y_ratio * resolved.deck_length
        ctx.check(
            "handle_hinge_within_rear_band",
            0.2 * resolved.deck_length - 1e-6 <= hinge_y <= 0.5 * resolved.deck_length + 1e-6,
            details=f"hinge_y={hinge_y}, L={resolved.deck_length}",
        )
        with ctx.pose({handle_joint: math.pi / 2.0}):
            folded_aabb = ctx.part_world_aabb(handle)
        ctx.check(
            "handle_folds_without_disappearing",
            folded_aabb is not None,
        )

    # Identity / sanity checks.
    ctx.check(
        "deck_present",
        deck is not None,
    )
    n_wheel_parts = len([p for p in object_model.parts if p.name.startswith("wheel_")])
    ctx.check(
        "wheel_count_matches",
        n_wheel_parts == resolved.wheel_count,
        details=f"found {n_wheel_parts}, expected {resolved.wheel_count}",
    )
    # symmetry: left and right wheel slots are mirrored.
    left_count = sum(1 for n, _x, _y in layout if n.endswith("_left"))
    right_count = sum(1 for n, _x, _y in layout if n.endswith("_right"))
    ctx.check("wheel_lr_symmetric_count", left_count == right_count)

    return ctx.report()


def build_seeded_platform_cart(
    seed: int, *, assets: AssetContext | None = None
) -> ArticulatedObject:
    return build_platform_cart(config_from_seed(seed), assets=assets)


def with_overrides(config: PlatformCartConfig, **kwargs: object) -> PlatformCartConfig:
    return replace(config, **kwargs)
