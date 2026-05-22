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

# ---------------------------------------------------------------------------
# Type aliases for the discrete style knobs (from spec section 6).
# ---------------------------------------------------------------------------

BoxSize = Literal["compact", "standard", "jobsite_large"]
WheelSize = Literal["small", "medium", "rugged_large"]
WheelTread = Literal["smooth", "ribbed", "chunky"]
HandleShape = Literal["U_shape", "twin_rod", "suitcase_style"]
LidStyle = Literal["flat", "raised", "split"]
FrontSupport = Literal["feet", "small_casters"]
CornerGuard = Literal["none", "reinforced"]
MaterialStyle = Literal["yellow_black", "red_black", "gray"]

# ---------------------------------------------------------------------------
# Discrete bucket + per-bucket continuous ranges (Section 0 requirement).
# Bucket is the spine class; continuous values inside each bucket break
# "same-class clone" duplicates across seeds.
# ---------------------------------------------------------------------------

BOX_SIZE_WIDTH_RANGES: dict[BoxSize, tuple[float, float]] = {
    "compact": (0.34, 0.42),
    "standard": (0.46, 0.56),
    "jobsite_large": (0.58, 0.72),
}
BOX_SIZE_DEPTH_RANGES: dict[BoxSize, tuple[float, float]] = {
    "compact": (0.22, 0.28),
    "standard": (0.28, 0.36),
    "jobsite_large": (0.36, 0.46),
}
BOX_SIZE_HEIGHT_RANGES: dict[BoxSize, tuple[float, float]] = {
    "compact": (0.24, 0.32),
    "standard": (0.32, 0.42),
    "jobsite_large": (0.42, 0.56),
}

WHEEL_SIZE_RADIUS_RANGES: dict[WheelSize, tuple[float, float]] = {
    "small": (0.045, 0.060),
    "medium": (0.062, 0.085),
    "rugged_large": (0.090, 0.120),
}
WHEEL_SIZE_WIDTH_RANGES: dict[WheelSize, tuple[float, float]] = {
    "small": (0.022, 0.032),
    "medium": (0.034, 0.048),
    "rugged_large": (0.052, 0.072),
}

# Material palettes for the three style buckets.
MATERIAL_PALETTES: dict[MaterialStyle, dict[str, tuple[float, float, float, float]]] = {
    "yellow_black": {
        "body": (0.94, 0.74, 0.10, 1.0),
        "trim": (0.10, 0.10, 0.10, 1.0),
        "lid": (0.10, 0.10, 0.10, 1.0),
        "hardware": (0.55, 0.55, 0.56, 1.0),
        "rubber": (0.07, 0.07, 0.07, 1.0),
        "rim": (0.30, 0.30, 0.31, 1.0),
    },
    "red_black": {
        "body": (0.78, 0.16, 0.13, 1.0),
        "trim": (0.08, 0.08, 0.08, 1.0),
        "lid": (0.12, 0.12, 0.12, 1.0),
        "hardware": (0.62, 0.62, 0.63, 1.0),
        "rubber": (0.06, 0.06, 0.06, 1.0),
        "rim": (0.28, 0.28, 0.29, 1.0),
    },
    "gray": {
        "body": (0.45, 0.46, 0.48, 1.0),
        "trim": (0.20, 0.21, 0.22, 1.0),
        "lid": (0.32, 0.33, 0.34, 1.0),
        "hardware": (0.70, 0.70, 0.71, 1.0),
        "rubber": (0.09, 0.09, 0.10, 1.0),
        "rim": (0.30, 0.30, 0.31, 1.0),
    },
}

# Geometry constants (proportions, not absolute dimensions).
WALL_THICKNESS = 0.014
LID_THICKNESS = 0.022
RIM_HEIGHT = 0.008
SLEEVE_OUTER_DIAMETER = 0.028
SLEEVE_INNER_DIAMETER = 0.020
HANDLE_BAR_THICKNESS = 0.018
LATCH_PIVOT_RADIUS = 0.004
HINGE_KNUCKLE_RADIUS = 0.0065
GROUND_CLEARANCE = 0.010

# Backward tilt of the telescoping handle from vertical (≤ 15 degrees).
HANDLE_BACK_TILT_DEG = 8.0


@dataclass(frozen=True)
class RollingToolboxConfig:
    box_size: BoxSize = "standard"
    wheel_size: WheelSize = "medium"
    wheel_tread: WheelTread = "ribbed"
    handle_stage_count: int = 1
    handle_shape: HandleShape = "U_shape"
    latch_count: int = 2
    lid_style: LidStyle = "flat"
    front_support: FrontSupport = "feet"
    corner_guard: CornerGuard = "none"
    material_style: MaterialStyle = "yellow_black"
    has_drawer: bool = False
    # Continuous bucket-derived values; resolved when None.
    box_width: float | None = None
    box_depth: float | None = None
    box_height: float | None = None
    wheel_radius: float | None = None
    wheel_width: float | None = None
    name: str = "reference_rolling_toolbox"


@dataclass(frozen=True)
class ResolvedRollingToolboxConfig:
    box_size: BoxSize
    wheel_size: WheelSize
    wheel_tread: WheelTread
    handle_stage_count: int
    handle_shape: HandleShape
    latch_count: int
    lid_style: LidStyle
    front_support: FrontSupport
    corner_guard: CornerGuard
    material_style: MaterialStyle
    has_drawer: bool
    box_width: float  # along Y (left-right)
    box_depth: float  # along X (front-back) -- front is +X
    box_height: float  # along Z
    wheel_radius: float
    wheel_width: float
    handle_inner_length: float
    handle_outer_sleeve_length: float
    handle_grip_span: float
    handle_travel: float
    name: str


def config_from_seed(seed: int) -> RollingToolboxConfig:
    rng = random.Random(seed)
    box_size = rng.choices(
        ("compact", "standard", "jobsite_large"),
        weights=(0.30, 0.45, 0.25),
        k=1,
    )[0]
    box_width = round(rng.uniform(*BOX_SIZE_WIDTH_RANGES[box_size]), 3)
    box_depth = round(rng.uniform(*BOX_SIZE_DEPTH_RANGES[box_size]), 3)
    box_height = round(rng.uniform(*BOX_SIZE_HEIGHT_RANGES[box_size]), 3)

    wheel_size = rng.choices(
        ("small", "medium", "rugged_large"),
        weights=(0.25, 0.50, 0.25),
        k=1,
    )[0]
    wheel_radius = round(rng.uniform(*WHEEL_SIZE_RADIUS_RANGES[wheel_size]), 3)
    wheel_width = round(rng.uniform(*WHEEL_SIZE_WIDTH_RANGES[wheel_size]), 3)

    wheel_tread = rng.choice(("smooth", "ribbed", "chunky"))
    handle_stage_count = rng.choices((1, 2, 3), weights=(0.55, 0.30, 0.15), k=1)[0]
    handle_shape = rng.choice(("U_shape", "twin_rod", "suitcase_style"))
    latch_count = rng.choices((1, 2, 3), weights=(0.30, 0.50, 0.20), k=1)[0]
    lid_style = rng.choice(("flat", "raised", "split"))
    front_support = rng.choices(("feet", "small_casters"), weights=(0.55, 0.45), k=1)[0]
    corner_guard = rng.choices(("none", "reinforced"), weights=(0.55, 0.45), k=1)[0]
    material_style = rng.choice(("yellow_black", "red_black", "gray"))
    has_drawer = rng.random() < 0.35

    return RollingToolboxConfig(
        box_size=box_size,
        wheel_size=wheel_size,
        wheel_tread=wheel_tread,
        handle_stage_count=handle_stage_count,
        handle_shape=handle_shape,
        latch_count=latch_count,
        lid_style=lid_style,
        front_support=front_support,
        corner_guard=corner_guard,
        material_style=material_style,
        has_drawer=has_drawer,
        box_width=box_width,
        box_depth=box_depth,
        box_height=box_height,
        wheel_radius=wheel_radius,
        wheel_width=wheel_width,
        name=f"seeded_rolling_toolbox_{seed}",
    )


def resolve_config(config: RollingToolboxConfig) -> ResolvedRollingToolboxConfig:
    if config.box_size not in BOX_SIZE_WIDTH_RANGES:
        raise ValueError(f"Unsupported box_size: {config.box_size}")
    if config.wheel_size not in WHEEL_SIZE_RADIUS_RANGES:
        raise ValueError(f"Unsupported wheel_size: {config.wheel_size}")
    if config.wheel_tread not in {"smooth", "ribbed", "chunky"}:
        raise ValueError(f"Unsupported wheel_tread: {config.wheel_tread}")
    if config.handle_stage_count not in (1, 2, 3):
        raise ValueError("handle_stage_count must be 1, 2, or 3")
    if config.handle_shape not in {"U_shape", "twin_rod", "suitcase_style"}:
        raise ValueError(f"Unsupported handle_shape: {config.handle_shape}")
    if config.latch_count not in (1, 2, 3):
        raise ValueError("latch_count must be 1, 2, or 3")
    if config.lid_style not in {"flat", "raised", "split"}:
        raise ValueError(f"Unsupported lid_style: {config.lid_style}")
    if config.front_support not in {"feet", "small_casters"}:
        raise ValueError(f"Unsupported front_support: {config.front_support}")
    if config.corner_guard not in {"none", "reinforced"}:
        raise ValueError(f"Unsupported corner_guard: {config.corner_guard}")
    if config.material_style not in MATERIAL_PALETTES:
        raise ValueError(f"Unsupported material_style: {config.material_style}")

    box_width = (
        config.box_width
        if config.box_width is not None
        else sum(BOX_SIZE_WIDTH_RANGES[config.box_size]) / 2.0
    )
    box_depth = (
        config.box_depth
        if config.box_depth is not None
        else sum(BOX_SIZE_DEPTH_RANGES[config.box_size]) / 2.0
    )
    box_height = (
        config.box_height
        if config.box_height is not None
        else sum(BOX_SIZE_HEIGHT_RANGES[config.box_size]) / 2.0
    )

    wheel_radius = (
        config.wheel_radius
        if config.wheel_radius is not None
        else sum(WHEEL_SIZE_RADIUS_RANGES[config.wheel_size]) / 2.0
    )
    wheel_width = (
        config.wheel_width
        if config.wheel_width is not None
        else sum(WHEEL_SIZE_WIDTH_RANGES[config.wheel_size]) / 2.0
    )
    # Constrain wheel proportions against the envelope so wheels physically fit.
    wheel_radius = min(wheel_radius, box_height * 0.40)
    wheel_radius = max(0.035, wheel_radius)
    wheel_width = min(wheel_width, box_depth * 0.30)
    wheel_width = max(0.018, wheel_width)

    # Telescoping handle geometry derives from the box envelope (spine).
    handle_outer_sleeve_length = max(0.32, box_height * 0.85)
    handle_inner_length = handle_outer_sleeve_length * 1.10
    handle_travel = handle_outer_sleeve_length * 0.70
    handle_grip_span = box_width * 0.62

    return ResolvedRollingToolboxConfig(
        box_size=config.box_size,
        wheel_size=config.wheel_size,
        wheel_tread=config.wheel_tread,
        handle_stage_count=config.handle_stage_count,
        handle_shape=config.handle_shape,
        latch_count=config.latch_count,
        lid_style=config.lid_style,
        front_support=config.front_support,
        corner_guard=config.corner_guard,
        material_style=config.material_style,
        has_drawer=config.has_drawer,
        box_width=box_width,
        box_depth=box_depth,
        box_height=box_height,
        wheel_radius=wheel_radius,
        wheel_width=wheel_width,
        handle_inner_length=handle_inner_length,
        handle_outer_sleeve_length=handle_outer_sleeve_length,
        handle_grip_span=handle_grip_span,
        handle_travel=handle_travel,
        name=config.name,
    )


# ---------------------------------------------------------------------------
# Coordinate convention notes
# ---------------------------------------------------------------------------
# - World/body frame: +X is FRONT of the toolbox (latches face here).
#   -X is the REAR (handle and wheels live here).
#   +Y is RIGHT, -Y is LEFT, +Z is UP.
# - Box body origin is on the ground directly under the box center.
# - The body floor sits at z = wheel_radius + GROUND_CLEARANCE so the wheels
#   still kiss the ground (z=0).
# ---------------------------------------------------------------------------


def _member(part, a, b, *, radius: float, material, name: str) -> None:
    """Add a Cylinder visual that spans from world point a to world point b."""
    dx = b[0] - a[0]
    dy = b[1] - a[1]
    dz = b[2] - a[2]
    length = math.sqrt(dx * dx + dy * dy + dz * dz)
    if length < 1e-9:
        return
    yaw = math.atan2(dy, dx)
    pitch = math.atan2(math.hypot(dx, dy), dz)
    midpoint = ((a[0] + b[0]) * 0.5, (a[1] + b[1]) * 0.5, (a[2] + b[2]) * 0.5)
    part.visual(
        Cylinder(radius=radius, length=length),
        origin=Origin(xyz=midpoint, rpy=(0.0, pitch, yaw)),
        material=material,
        name=name,
    )


def _floor_z(resolved: ResolvedRollingToolboxConfig) -> float:
    """Bottom-of-body Z coordinate (top of wheel zone + ground clearance)."""
    return resolved.wheel_radius + GROUND_CLEARANCE


def _latch_y_positions(resolved: ResolvedRollingToolboxConfig) -> list[float]:
    n = resolved.latch_count
    usable = resolved.box_width * 0.6
    if n == 1:
        return [0.0]
    step = usable / (n - 1)
    return [-usable / 2.0 + i * step for i in range(n)]


# ---------------------------------------------------------------------------
# Body / lid construction
# ---------------------------------------------------------------------------


def _build_body_shell(body, resolved: ResolvedRollingToolboxConfig, *, body_mat, trim_mat) -> None:
    W = resolved.box_width
    D = resolved.box_depth
    H = resolved.box_height
    wall = WALL_THICKNESS
    floor_z = _floor_z(resolved)

    # Floor
    body.visual(
        Box((D, W, wall)),
        origin=Origin(xyz=(0.0, 0.0, floor_z + wall / 2.0)),
        material=body_mat,
        name="body_floor",
    )
    # Front wall (+X side)
    body.visual(
        Box((wall, W, H)),
        origin=Origin(xyz=(D / 2.0 - wall / 2.0, 0.0, floor_z + H / 2.0)),
        material=body_mat,
        name="body_front_wall",
    )
    # Rear wall (-X side)
    body.visual(
        Box((wall, W, H)),
        origin=Origin(xyz=(-D / 2.0 + wall / 2.0, 0.0, floor_z + H / 2.0)),
        material=body_mat,
        name="body_rear_wall",
    )
    # Left/right walls
    body.visual(
        Box((D, wall, H)),
        origin=Origin(xyz=(0.0, -W / 2.0 + wall / 2.0, floor_z + H / 2.0)),
        material=body_mat,
        name="body_left_wall",
    )
    body.visual(
        Box((D, wall, H)),
        origin=Origin(xyz=(0.0, W / 2.0 - wall / 2.0, floor_z + H / 2.0)),
        material=body_mat,
        name="body_right_wall",
    )

    # Decorative top rim (visual only on body part)
    rim_z = floor_z + H + RIM_HEIGHT / 2.0
    body.visual(
        Box((D, wall, RIM_HEIGHT)),
        origin=Origin(xyz=(0.0, W / 2.0 - wall / 2.0, rim_z)),
        material=trim_mat,
        name="rim_right",
    )
    body.visual(
        Box((D, wall, RIM_HEIGHT)),
        origin=Origin(xyz=(0.0, -W / 2.0 + wall / 2.0, rim_z)),
        material=trim_mat,
        name="rim_left",
    )
    body.visual(
        Box((wall, W, RIM_HEIGHT)),
        origin=Origin(xyz=(D / 2.0 - wall / 2.0, 0.0, rim_z)),
        material=trim_mat,
        name="rim_front",
    )
    body.visual(
        Box((wall, W, RIM_HEIGHT)),
        origin=Origin(xyz=(-D / 2.0 + wall / 2.0, 0.0, rim_z)),
        material=trim_mat,
        name="rim_rear",
    )

    # Side ribs (always present, attached as visuals on body) ----------------
    rib_height = H * 0.40
    for x_frac, idx in ((-0.20, 0), (0.20, 1)):
        body.visual(
            Box((0.010, wall, rib_height)),
            origin=Origin(
                xyz=(x_frac * D, W / 2.0 - wall / 2.0 + 0.005, floor_z + H * 0.55),
            ),
            material=trim_mat,
            name=f"side_rib_right_{idx}",
        )
        body.visual(
            Box((0.010, wall, rib_height)),
            origin=Origin(
                xyz=(x_frac * D, -W / 2.0 + wall / 2.0 - 0.005, floor_z + H * 0.55),
            ),
            material=trim_mat,
            name=f"side_rib_left_{idx}",
        )

    # Corner guards (visual only on body) ------------------------------------
    if resolved.corner_guard == "reinforced":
        guard_thickness = 0.012
        guard_height = H * 0.30
        for sign_x in (-1.0, 1.0):
            for sign_y in (-1.0, 1.0):
                # Vertical strip in X direction at this corner
                body.visual(
                    Box((guard_thickness, wall + 0.006, guard_height)),
                    origin=Origin(
                        xyz=(
                            sign_x * (D / 2.0 - guard_thickness / 2.0),
                            sign_y * (W / 2.0 - wall / 2.0 - 0.003),
                            floor_z + guard_height / 2.0,
                        )
                    ),
                    material=trim_mat,
                    name=f"corner_guard_x_{'p' if sign_x > 0 else 'm'}{'p' if sign_y > 0 else 'm'}",
                )
                body.visual(
                    Box((wall + 0.006, guard_thickness, guard_height)),
                    origin=Origin(
                        xyz=(
                            sign_x * (D / 2.0 - wall / 2.0 - 0.003),
                            sign_y * (W / 2.0 - guard_thickness / 2.0),
                            floor_z + guard_height / 2.0,
                        )
                    ),
                    material=trim_mat,
                    name=f"corner_guard_y_{'p' if sign_x > 0 else 'm'}{'p' if sign_y > 0 else 'm'}",
                )


def _build_lid(lid, resolved: ResolvedRollingToolboxConfig, *, lid_mat, trim_mat) -> None:
    """Lid local frame: origin sits at the rear hinge axis. Lid extends +X.

    The lid panel is centered at +D/2 along local +X so that at q=0 the lid
    sits flat over the body opening.
    """
    W = resolved.box_width
    D = resolved.box_depth

    lid.visual(
        Box((D, W, LID_THICKNESS)),
        origin=Origin(xyz=(D / 2.0, 0.0, LID_THICKNESS / 2.0)),
        material=lid_mat,
        name="lid_panel",
    )

    if resolved.lid_style == "raised":
        lid.visual(
            Box((D * 0.78, W * 0.80, 0.014)),
            origin=Origin(xyz=(D / 2.0, 0.0, LID_THICKNESS + 0.007)),
            material=lid_mat,
            name="lid_raised_top",
        )
    elif resolved.lid_style == "split":
        # Two visible halves separated by a center seam ridge.
        lid.visual(
            Box((D * 0.85, 0.010, 0.010)),
            origin=Origin(xyz=(D / 2.0, 0.0, LID_THICKNESS + 0.004)),
            material=trim_mat,
            name="lid_split_seam",
        )

    # Hinge knuckles (visual only on lid part).
    knuckle_length = W * 0.20
    for idx, y in enumerate((-W * 0.30, W * 0.30)):
        lid.visual(
            Cylinder(radius=HINGE_KNUCKLE_RADIUS, length=knuckle_length),
            origin=Origin(xyz=(0.0, y, 0.0), rpy=(math.pi / 2.0, 0.0, 0.0)),
            material=trim_mat,
            name=f"lid_hinge_knuckle_{idx}",
        )

    # Carry handle visual on top of the lid (front-center).
    handle_y_half = W * 0.18
    grip_z = LID_THICKNESS + 0.026
    for idx, y in enumerate((-handle_y_half, handle_y_half)):
        lid.visual(
            Box((0.022, 0.014, 0.020)),
            origin=Origin(xyz=(D * 0.55, y, LID_THICKNESS + 0.010)),
            material=trim_mat,
            name=f"carry_handle_post_{idx}",
        )
    lid.visual(
        Box((0.090, 2.0 * handle_y_half + 0.020, HANDLE_BAR_THICKNESS)),
        origin=Origin(xyz=(D * 0.55, 0.0, grip_z)),
        material=trim_mat,
        name="carry_handle_bar",
    )


def _build_lid_latch_strikes(lid, resolved: ResolvedRollingToolboxConfig, *, trim_mat) -> None:
    D = resolved.box_depth
    for i, y in enumerate(_latch_y_positions(resolved)):
        lid.visual(
            Box((0.012, 0.034, 0.014)),
            origin=Origin(xyz=(D - 0.014, y, LID_THICKNESS / 2.0)),
            material=trim_mat,
            name=f"latch_strike_{i}",
        )


# ---------------------------------------------------------------------------
# Handle (telescoping pull bar)
# ---------------------------------------------------------------------------


def _add_outer_sleeves(
    body,
    resolved: ResolvedRollingToolboxConfig,
    *,
    sleeve_origin_xyz: tuple[float, float, float],
    tilt: float,
    hardware_mat,
) -> None:
    """Attach the two handle outer sleeves as visuals on the body.

    The sleeves are visual decorations on the body. The articulated inner part
    moves inside them via prismatic motion along the tilted local +Z axis.
    """
    L = resolved.handle_outer_sleeve_length
    half = resolved.handle_grip_span / 2.0
    cos_t = math.cos(tilt)
    sin_t = math.sin(tilt)
    # The sleeves rise upward and slightly backward from sleeve_origin_xyz.
    # Up axis under tilt: (sin_t*-1 along X, 0, cos_t along Z) — back is -X.
    up_dx = -sin_t
    up_dz = cos_t
    base_x, base_y, base_z = sleeve_origin_xyz
    for sign, side in ((-1.0, "l"), (1.0, "r")):
        # Sleeve cylinder center at half-length along the up axis.
        cx = base_x + 0.5 * L * up_dx
        cz = base_z + 0.5 * L * up_dz
        cy = base_y + sign * half
        body.visual(
            Cylinder(radius=SLEEVE_OUTER_DIAMETER / 2.0, length=L),
            origin=Origin(
                xyz=(cx, cy, cz),
                rpy=(0.0, -tilt, 0.0),
            ),
            material=hardware_mat,
            name=f"handle_outer_sleeve_{side}",
        )
        # Sleeve top collar
        top_x = base_x + L * up_dx
        top_z = base_z + L * up_dz
        body.visual(
            Cylinder(radius=SLEEVE_OUTER_DIAMETER / 2.0 + 0.004, length=0.012),
            origin=Origin(
                xyz=(top_x, cy, top_z),
                rpy=(0.0, -tilt, 0.0),
            ),
            material=hardware_mat,
            name=f"handle_sleeve_collar_top_{side}",
        )
        # Sleeve base collar
        body.visual(
            Cylinder(radius=SLEEVE_OUTER_DIAMETER / 2.0 + 0.004, length=0.012),
            origin=Origin(
                xyz=(base_x, cy, base_z),
                rpy=(0.0, -tilt, 0.0),
            ),
            material=hardware_mat,
            name=f"handle_sleeve_collar_base_{side}",
        )


def _build_handle_inner(
    inner,
    resolved: ResolvedRollingToolboxConfig,
    *,
    hardware_mat,
    grip_mat,
) -> None:
    """Inner handle local frame.

    Origin = at the entry plane of the sleeve. Local +Z points UP along the
    sleeve (no tilt within this frame; the prismatic joint applies the
    backward tilt via its origin.rpy).

    The two rods extend along local +Z. The grip cross-bar sits at the top.
    """
    L = resolved.handle_inner_length
    half = resolved.handle_grip_span / 2.0
    shape = resolved.handle_shape

    # Two parallel rods (left and right) along local +Z. They start
    # below z=0 so they remain captured in the sleeve at full extension.
    rod_radius = SLEEVE_INNER_DIAMETER / 2.0
    rod_center_z = (L / 2.0) - (L * 0.10)  # tail extends below origin
    for sign, side in ((-1.0, "l"), (1.0, "r")):
        inner.visual(
            Cylinder(radius=rod_radius, length=L),
            origin=Origin(xyz=(0.0, sign * half, rod_center_z)),
            material=hardware_mat,
            name=f"handle_inner_rod_{side}",
        )

    grip_z = rod_center_z + L / 2.0 - 0.010

    if shape == "U_shape":
        # Cross-bar at the top spanning the rods.
        inner.visual(
            Box((HANDLE_BAR_THICKNESS, 2.0 * half + 0.020, HANDLE_BAR_THICKNESS)),
            origin=Origin(xyz=(0.0, 0.0, grip_z + 0.010)),
            material=grip_mat,
            name="handle_grip_bar",
        )
    elif shape == "twin_rod":
        # Twin separate grip caps on each rod.
        for sign, side in ((-1.0, "l"), (1.0, "r")):
            inner.visual(
                Cylinder(radius=rod_radius + 0.006, length=0.060),
                origin=Origin(xyz=(0.0, sign * half, grip_z + 0.020)),
                material=grip_mat,
                name=f"handle_grip_cap_{side}",
            )
    else:  # suitcase_style
        # Wider rectangular grab plate connecting the two rods.
        inner.visual(
            Box((0.040, 2.0 * half + 0.030, 0.030)),
            origin=Origin(xyz=(0.0, 0.0, grip_z + 0.015)),
            material=grip_mat,
            name="handle_grip_bar",
        )
        # Plus the cross-bar so the shape is mechanically a U on the inside.
        inner.visual(
            Box((HANDLE_BAR_THICKNESS, 2.0 * half + 0.020, HANDLE_BAR_THICKNESS)),
            origin=Origin(xyz=(0.0, 0.0, grip_z - 0.004)),
            material=grip_mat,
            name="handle_grip_undercrossbar",
        )

    # Decorative ferrule at the cross-bar where rods join.
    if shape != "twin_rod":
        for sign, side in ((-1.0, "l"), (1.0, "r")):
            inner.visual(
                Cylinder(radius=rod_radius + 0.004, length=0.010),
                origin=Origin(xyz=(0.0, sign * half, grip_z)),
                material=hardware_mat,
                name=f"handle_rod_ferrule_{side}",
            )


# ---------------------------------------------------------------------------
# Latches
# ---------------------------------------------------------------------------


def _build_latch_visuals(latch, *, hardware_mat) -> None:
    """Latch local frame.

    Origin = pivot pin (Y axis). Closed pose hangs the latch plate toward -Z.
    """
    latch.visual(
        Cylinder(radius=LATCH_PIVOT_RADIUS, length=0.036),
        origin=Origin(rpy=(math.pi / 2.0, 0.0, 0.0)),
        material=hardware_mat,
        name="latch_pivot_pin",
    )
    latch.visual(
        Box((0.010, 0.034, 0.046)),
        origin=Origin(xyz=(0.004, 0.0, -0.024)),
        material=hardware_mat,
        name="latch_plate",
    )
    latch.visual(
        Box((0.018, 0.034, 0.008)),
        origin=Origin(xyz=(0.005, 0.0, -0.050)),
        material=hardware_mat,
        name="latch_hook",
    )


# ---------------------------------------------------------------------------
# Front support (feet or small_casters)
# ---------------------------------------------------------------------------


def _build_front_feet(body, resolved: ResolvedRollingToolboxConfig, *, hardware_mat) -> None:
    """Static feet attached as visuals on the body (front side)."""
    D = resolved.box_depth
    W = resolved.box_width
    floor_z = _floor_z(resolved)
    foot_height = floor_z  # spans from the ground up to body floor
    foot_radius = max(0.012, resolved.wheel_radius * 0.35)
    foot_x = D / 2.0 - foot_radius - 0.010
    foot_y = W / 2.0 - foot_radius - 0.010
    for sign, label in ((-1.0, "l"), (1.0, "r")):
        body.visual(
            Cylinder(radius=foot_radius, length=foot_height),
            origin=Origin(xyz=(foot_x, sign * foot_y, foot_height / 2.0)),
            material=hardware_mat,
            name=f"front_foot_{label}",
        )


def _add_wheel_geometry(
    wheel_part,
    *,
    radius: float,
    width: float,
    wheel_tread: WheelTread,
    rubber_mat,
    rim_mat,
    hardware_mat,
) -> None:
    """Wheel local frame: spin axis along +X; cylinder rotated to align."""
    wheel_part.visual(
        Cylinder(radius=radius, length=width),
        origin=Origin(rpy=(0.0, math.pi / 2.0, 0.0)),
        material=rubber_mat,
        name="tire",
    )
    wheel_part.visual(
        Cylinder(radius=radius * 0.58, length=width * 1.04),
        origin=Origin(rpy=(0.0, math.pi / 2.0, 0.0)),
        material=rim_mat,
        name="rim",
    )
    wheel_part.visual(
        Cylinder(radius=radius * 0.20, length=width * 1.10),
        origin=Origin(rpy=(0.0, math.pi / 2.0, 0.0)),
        material=hardware_mat,
        name="hub",
    )
    # Tread decoration: visual ribs on the tire (no separate part).
    if wheel_tread == "ribbed":
        for i in range(6):
            ang = (2.0 * math.pi * i) / 6.0
            wheel_part.visual(
                Box((width * 1.02, radius * 0.04, radius * 0.10)),
                origin=Origin(
                    xyz=(0.0, math.cos(ang) * radius * 0.96, math.sin(ang) * radius * 0.96),
                    rpy=(ang, 0.0, 0.0),
                ),
                material=rubber_mat,
                name=f"tread_rib_{i}",
            )
    elif wheel_tread == "chunky":
        for i in range(8):
            ang = (2.0 * math.pi * i) / 8.0
            wheel_part.visual(
                Box((width * 0.90, radius * 0.16, radius * 0.16)),
                origin=Origin(
                    xyz=(0.0, math.cos(ang) * radius * 0.94, math.sin(ang) * radius * 0.94),
                    rpy=(ang, 0.0, 0.0),
                ),
                material=rubber_mat,
                name=f"tread_lug_{i}",
            )


# ---------------------------------------------------------------------------
# Drawer (optional)
# ---------------------------------------------------------------------------


def _build_drawer_visuals(
    drawer, resolved: ResolvedRollingToolboxConfig, *, body_mat, trim_mat
) -> None:
    """Drawer local frame: origin is the rear face of the drawer in closed pose.

    Drawer extends along +X (front direction). At q=0 it sits inside the body
    cavity. Positive prismatic q slides it outward (+X).
    """
    W = resolved.box_width
    drawer_depth = resolved.box_depth * 0.32
    drawer_width = W * 0.84
    drawer_height = resolved.box_height * 0.18
    # Front face of drawer
    drawer.visual(
        Box((0.012, drawer_width, drawer_height)),
        origin=Origin(xyz=(drawer_depth - 0.006, 0.0, drawer_height / 2.0)),
        material=trim_mat,
        name="drawer_front",
    )
    # Drawer floor
    drawer.visual(
        Box((drawer_depth, drawer_width, 0.008)),
        origin=Origin(xyz=(drawer_depth / 2.0, 0.0, 0.004)),
        material=body_mat,
        name="drawer_floor",
    )
    # Side walls
    drawer.visual(
        Box((drawer_depth, 0.008, drawer_height * 0.7)),
        origin=Origin(
            xyz=(drawer_depth / 2.0, drawer_width / 2.0 - 0.004, drawer_height * 0.35),
        ),
        material=body_mat,
        name="drawer_right_wall",
    )
    drawer.visual(
        Box((drawer_depth, 0.008, drawer_height * 0.7)),
        origin=Origin(
            xyz=(drawer_depth / 2.0, -drawer_width / 2.0 + 0.004, drawer_height * 0.35),
        ),
        material=body_mat,
        name="drawer_left_wall",
    )
    drawer.visual(
        Box((0.060, 0.018, 0.012)),
        origin=Origin(xyz=(drawer_depth - 0.014, 0.0, drawer_height * 0.65)),
        material=trim_mat,
        name="drawer_pull",
    )


# ---------------------------------------------------------------------------
# Caster (front_support == small_casters)
# ---------------------------------------------------------------------------


def _build_caster_yoke(caster, *, radius: float, hardware_mat) -> None:
    """Caster yoke local frame: origin = swivel pin on body underside; yoke
    legs descend to the wheel axle along local -Z."""
    drop = radius + 0.012
    caster.visual(
        Cylinder(radius=0.012, length=0.020),
        origin=Origin(xyz=(0.0, 0.0, -0.010)),
        material=hardware_mat,
        name="caster_swivel_post",
    )
    for sign, side in ((-1.0, "l"), (1.0, "r")):
        caster.visual(
            Box((0.008, 0.006, drop)),
            origin=Origin(xyz=(0.0, sign * (radius * 0.55), -drop / 2.0 - 0.010)),
            material=hardware_mat,
            name=f"caster_yoke_leg_{side}",
        )


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------


def build_rolling_toolbox(
    config: RollingToolboxConfig | None = None,
    *,
    assets: AssetContext | None = None,
) -> ArticulatedObject:
    config = config or RollingToolboxConfig()
    resolved = resolve_config(config)
    if assets is None:
        assets = AssetContext(Path(tempfile.mkdtemp(prefix="articraft-rolling-toolbox-assets-")))
    model = ArticulatedObject(name=resolved.name, assets=assets)

    palette = MATERIAL_PALETTES[resolved.material_style]
    body_mat = model.material("toolbox_body", rgba=palette["body"])
    trim_mat = model.material("toolbox_trim", rgba=palette["trim"])
    lid_mat = model.material("toolbox_lid", rgba=palette["lid"])
    hardware_mat = model.material("toolbox_hardware", rgba=palette["hardware"])
    rubber_mat = model.material("toolbox_rubber", rgba=palette["rubber"])
    rim_mat = model.material("toolbox_rim", rgba=palette["rim"])

    W = resolved.box_width
    D = resolved.box_depth
    H = resolved.box_height
    floor_z = _floor_z(resolved)

    body = model.part("toolbox_body")
    _build_body_shell(body, resolved, body_mat=body_mat, trim_mat=trim_mat)

    # ----- Telescoping handle: outer sleeves are visuals on the body --------
    # Mount the sleeves on the REAR face of the body. Their base sits just
    # above the body floor at the rear, extending upward with a small
    # backward tilt (≤15 deg).
    tilt = math.radians(HANDLE_BACK_TILT_DEG)
    sleeve_origin = (
        -D / 2.0 - SLEEVE_OUTER_DIAMETER / 2.0 - 0.002,
        0.0,
        floor_z + 0.030,
    )
    _add_outer_sleeves(
        body,
        resolved,
        sleeve_origin_xyz=sleeve_origin,
        tilt=tilt,
        hardware_mat=hardware_mat,
    )

    # ----- Front support: feet are visuals on body; casters are parts ------
    if resolved.front_support == "feet":
        _build_front_feet(body, resolved, hardware_mat=hardware_mat)

    # ----- Rear wheels (continuous joints) ----------------------------------
    # Two rear wheels mounted on the bottom-back, axle along world X.
    # Axle center sits at z = wheel_radius (so wheel touches ground at z=0).
    wheel_x = -D / 2.0 + resolved.wheel_radius + 0.010
    wheel_y_half = W / 2.0 + resolved.wheel_width / 2.0 + 0.004
    wheel_z = resolved.wheel_radius
    wheel_parts: list[str] = []
    for i, sign in enumerate((-1.0, 1.0)):
        wheel_part = model.part(f"rear_wheel_{i}")
        _add_wheel_geometry(
            wheel_part,
            radius=resolved.wheel_radius,
            width=resolved.wheel_width,
            wheel_tread=resolved.wheel_tread,
            rubber_mat=rubber_mat,
            rim_mat=rim_mat,
            hardware_mat=hardware_mat,
        )
        model.articulation(
            f"wheel_joint_{i}",
            ArticulationType.CONTINUOUS,
            parent=body,
            child=wheel_part,
            origin=Origin(xyz=(wheel_x, sign * wheel_y_half, wheel_z)),
            axis=(0.0, 1.0, 0.0),
            motion_limits=MotionLimits(effort=10.0, velocity=20.0),
        )
        # Decorative axle stub on the body so the wheel attaches plausibly.
        body.visual(
            Cylinder(radius=0.008, length=0.012),
            origin=Origin(
                xyz=(wheel_x, sign * (W / 2.0 - 0.006), wheel_z),
                rpy=(math.pi / 2.0, 0.0, 0.0),
            ),
            material=hardware_mat,
            name=f"rear_axle_stub_{i}",
        )
        wheel_parts.append(wheel_part.name)

    # ----- Front casters (optional, replace static feet) --------------------
    if resolved.front_support == "small_casters":
        caster_radius = max(0.025, resolved.wheel_radius * 0.6)
        caster_x = D / 2.0 - caster_radius - 0.020
        caster_y = W / 2.0 - caster_radius - 0.020
        for ci, sign in enumerate((-1.0, 1.0)):
            caster_part = model.part(f"front_caster_{ci}")
            _build_caster_yoke(caster_part, radius=caster_radius, hardware_mat=hardware_mat)
            model.articulation(
                f"front_caster_swivel_{ci}",
                ArticulationType.CONTINUOUS,
                parent=body,
                child=caster_part,
                origin=Origin(xyz=(caster_x, sign * caster_y, floor_z)),
                axis=(0.0, 0.0, 1.0),
                motion_limits=MotionLimits(effort=5.0, velocity=10.0),
            )
            # The actual caster wheel is a child of the caster yoke.
            caster_wheel = model.part(f"front_caster_wheel_{ci}")
            _add_wheel_geometry(
                caster_wheel,
                radius=caster_radius,
                width=max(0.020, resolved.wheel_width * 0.6),
                wheel_tread="smooth",
                rubber_mat=rubber_mat,
                rim_mat=rim_mat,
                hardware_mat=hardware_mat,
            )
            model.articulation(
                f"front_caster_spin_{ci}",
                ArticulationType.CONTINUOUS,
                parent=caster_part,
                child=caster_wheel,
                origin=Origin(xyz=(0.0, 0.0, -(caster_radius + 0.014))),
                axis=(1.0, 0.0, 0.0),
                motion_limits=MotionLimits(effort=6.0, velocity=20.0),
            )

    # ----- Lid + lid_joint --------------------------------------------------
    lid_hinge_x = -D / 2.0 - HINGE_KNUCKLE_RADIUS - 0.003
    lid_hinge_z = floor_z + H + RIM_HEIGHT + HINGE_KNUCKLE_RADIUS - 0.002

    lid = model.part("lid")
    _build_lid(lid, resolved, lid_mat=lid_mat, trim_mat=trim_mat)
    _build_lid_latch_strikes(lid, resolved, trim_mat=trim_mat)
    model.articulation(
        "lid_joint",
        ArticulationType.REVOLUTE,
        parent=body,
        child=lid,
        origin=Origin(xyz=(lid_hinge_x, 0.0, lid_hinge_z)),
        axis=(0.0, -1.0, 0.0),
        motion_limits=MotionLimits(effort=12.0, velocity=2.0, lower=0.0, upper=1.8),
    )

    # ----- Latches (revolute) -----------------------------------------------
    # Latches pivot on the BODY front edge (just below the rim) and the hook
    # reaches over the latch_strike on the lid.
    body_front_x = D / 2.0
    latch_pivot_z = floor_z + H - 0.020
    for i, y in enumerate(_latch_y_positions(resolved)):
        latch = model.part(f"latch_{i}")
        _build_latch_visuals(latch, hardware_mat=hardware_mat)
        # Body-side keeper plate (visual on body)
        body.visual(
            Box((0.006, 0.030, 0.020)),
            origin=Origin(xyz=(body_front_x + 0.003, y, latch_pivot_z - 0.010)),
            material=hardware_mat,
            name=f"latch_keeper_{i}",
        )
        model.articulation(
            f"latch_joint_{i}",
            ArticulationType.REVOLUTE,
            parent=body,
            child=latch,
            origin=Origin(xyz=(body_front_x + 0.008, y, latch_pivot_z)),
            axis=(0.0, -1.0, 0.0),
            motion_limits=MotionLimits(effort=2.5, velocity=3.0, lower=0.0, upper=1.4),
        )

    # ----- Handle inner (telescoping) --------------------------------------
    # The inner handle is a single articulated part that slides up the
    # tilted sleeve axis. Origin of the joint is at the sleeve entry plane,
    # and the joint axis tilts backward by HANDLE_BACK_TILT_DEG.
    inner_part = model.part("handle_inner")
    _build_handle_inner(inner_part, resolved, hardware_mat=hardware_mat, grip_mat=hardware_mat)
    model.articulation(
        "handle_stage_joint",
        ArticulationType.PRISMATIC,
        parent=body,
        child=inner_part,
        # Joint origin = base of sleeves on the body. The articulation rpy
        # tilts the local +Z axis backward (rotation about +Y means local +Z
        # rotates toward -X, i.e. toward the rear).
        origin=Origin(xyz=sleeve_origin, rpy=(0.0, -tilt, 0.0)),
        axis=(0.0, 0.0, 1.0),
        motion_limits=MotionLimits(
            effort=80.0,
            velocity=0.30,
            lower=0.0,
            upper=resolved.handle_travel,
        ),
    )

    # Optional second stage joint (the inner part already has its rods; the
    # second stage is modeled as a nested telescoping extension of the same
    # inner). The second stage child is a small extension cap above the grip.
    if resolved.handle_stage_count >= 2:
        stage2 = model.part("handle_stage_2")
        # Local frame inherits from inner_part: extension cap rises along +Z.
        half = resolved.handle_grip_span / 2.0
        ext_radius = SLEEVE_INNER_DIAMETER / 2.0 * 0.85
        ext_length = resolved.handle_outer_sleeve_length * 0.40
        for sign, side in ((-1.0, "l"), (1.0, "r")):
            stage2.visual(
                Cylinder(radius=ext_radius, length=ext_length),
                origin=Origin(xyz=(0.0, sign * half, ext_length / 2.0 - 0.040)),
                material=hardware_mat,
                name=f"handle_stage_2_rod_{side}",
            )
        stage2.visual(
            Box((HANDLE_BAR_THICKNESS * 0.9, 2.0 * half + 0.016, HANDLE_BAR_THICKNESS * 0.9)),
            origin=Origin(xyz=(0.0, 0.0, ext_length - 0.020)),
            material=hardware_mat,
            name="handle_stage_2_top_bar",
        )
        # Mount above the inner grip; joint origin sits near the top of the
        # inner rods so the nested extension slides upward along +Z too.
        grip_top_z = resolved.handle_inner_length * 0.85
        model.articulation(
            "handle_stage_2_joint",
            ArticulationType.PRISMATIC,
            parent=inner_part,
            child=stage2,
            origin=Origin(xyz=(0.0, 0.0, grip_top_z)),
            axis=(0.0, 0.0, 1.0),
            motion_limits=MotionLimits(
                effort=60.0,
                velocity=0.30,
                lower=0.0,
                upper=resolved.handle_outer_sleeve_length * 0.40,
            ),
        )

    # ----- Drawer (optional) ------------------------------------------------
    if resolved.has_drawer:
        drawer = model.part("drawer")
        _build_drawer_visuals(drawer, resolved, body_mat=body_mat, trim_mat=trim_mat)
        drawer_depth = resolved.box_depth * 0.32
        drawer_width = W * 0.84
        drawer_height = H * 0.18
        # Drawer origin at q=0: sits flush inside the body, near the front.
        # The articulation origin places the drawer rear face at
        # x = D/2 - drawer_depth (inside the body); +X is "out".
        drawer_y0 = floor_z + 0.014
        model.articulation(
            "drawer_joint",
            ArticulationType.PRISMATIC,
            parent=body,
            child=drawer,
            origin=Origin(xyz=(D / 2.0 - drawer_depth, 0.0, drawer_y0)),
            axis=(1.0, 0.0, 0.0),
            motion_limits=MotionLimits(
                effort=30.0,
                velocity=0.25,
                lower=0.0,
                upper=drawer_depth * 0.85,
            ),
        )
        # Silence unused warnings while keeping derived widths/heights.
        _ = drawer_width, drawer_height

    return model


def build_seeded_rolling_toolbox(
    seed: int, *, assets: AssetContext | None = None
) -> ArticulatedObject:
    return build_rolling_toolbox(config_from_seed(seed), assets=assets)


def with_overrides(config: RollingToolboxConfig, **kwargs: object) -> RollingToolboxConfig:
    return replace(config, **kwargs)


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------


def run_rolling_toolbox_tests(
    object_model: ArticulatedObject, config: RollingToolboxConfig
) -> TestReport:
    resolved = resolve_config(config)
    ctx = TestContext(object_model)
    body = object_model.get_part("toolbox_body")
    lid = object_model.get_part("lid")

    # --- Required joints -----------------------------------------------------
    # Wheel joints: continuous spin on rear wheels.
    for i in range(2):
        wheel_part = object_model.get_part(f"rear_wheel_{i}")
        joint = object_model.get_articulation(f"wheel_joint_{i}")
        ctx.check(
            f"wheel_joint_{i}_is_continuous",
            joint.articulation_type == ArticulationType.CONTINUOUS,
            details=f"type={joint.articulation_type}",
        )
        # Allow the decorative axle stub to nest into the wheel hub.
        ctx.allow_overlap(
            body,
            wheel_part,
            elem_a=f"rear_axle_stub_{i}",
            elem_b="hub",
            reason="The rear axle stub on the body is captured by the wheel hub.",
        )
        # Rear wheels must be near the ground (bottom of tire close to z=0).
        wheel_aabb = ctx.part_world_aabb(wheel_part)
        ctx.check(
            f"rear_wheel_{i}_near_ground",
            wheel_aabb is not None and abs(wheel_aabb[0][2]) < 0.01,
            details=f"wheel_aabb={wheel_aabb}",
        )

    # Handle joint must be prismatic with axis tilt ≤ 15° from vertical.
    handle_joint = object_model.get_articulation("handle_stage_joint")
    ctx.check(
        "handle_stage_joint_is_prismatic",
        handle_joint.articulation_type == ArticulationType.PRISMATIC,
        details=f"type={handle_joint.articulation_type}",
    )
    # The articulation origin rpy tilts the joint frame; +Z in the joint frame
    # maps to a world direction. Check the tilt angle.
    tilt_y = handle_joint.origin.rpy[1]
    tilt_x = handle_joint.origin.rpy[0]
    tilt_total_deg = math.degrees(math.sqrt(tilt_y * tilt_y + tilt_x * tilt_x))
    ctx.check(
        "handle_axis_tilt_within_15_deg",
        tilt_total_deg <= 15.0 + 1e-3,
        details=f"tilt_total_deg={tilt_total_deg}",
    )

    # Handle inner must remain captured in the sleeves at full extension.
    handle_inner = object_model.get_part("handle_inner")
    # Sleeves are visuals on body; allow the inner rods to overlap the sleeves
    # (the sleeves are simplified solid proxies for hollow tubes).
    ctx.allow_overlap(
        body,
        handle_inner,
        elem_a="handle_outer_sleeve_l",
        elem_b="handle_inner_rod_l",
        reason="The inner rod slides inside the simplified solid sleeve proxy.",
    )
    ctx.allow_overlap(
        body,
        handle_inner,
        elem_a="handle_outer_sleeve_r",
        elem_b="handle_inner_rod_r",
        reason="The inner rod slides inside the simplified solid sleeve proxy.",
    )

    # Verify the handle actually extends upward when extended.
    rest_aabb = ctx.part_world_aabb(handle_inner)
    if handle_joint.motion_limits and handle_joint.motion_limits.upper is not None:
        with ctx.pose({handle_joint: handle_joint.motion_limits.upper}):
            extended_aabb = ctx.part_world_aabb(handle_inner)
        ctx.check(
            "handle_extends_upward",
            rest_aabb is not None
            and extended_aabb is not None
            and extended_aabb[1][2] > rest_aabb[1][2] + 0.05,
            details=f"rest={rest_aabb}, extended={extended_aabb}",
        )

    # --- Latches -------------------------------------------------------------
    latch_parts = [p for p in object_model.parts if p.name.startswith("latch_")]
    ctx.check(
        "latch_part_count_matches_config",
        len(latch_parts) == resolved.latch_count,
        details=f"expected={resolved.latch_count}, got={len(latch_parts)}",
    )
    for i in range(resolved.latch_count):
        joint = object_model.get_articulation(f"latch_joint_{i}")
        ctx.check(
            f"latch_joint_{i}_is_revolute",
            joint.articulation_type == ArticulationType.REVOLUTE,
            details=f"type={joint.articulation_type}",
        )
        # Latch keeper position: on the FRONT (+X) side of the body.
        keeper_aabb = ctx.part_element_world_aabb(body, elem=f"latch_keeper_{i}")
        ctx.check(
            f"latch_{i}_keeper_on_front_side",
            keeper_aabb is not None and keeper_aabb[0][0] > resolved.box_depth * 0.30,
            details=f"keeper_aabb={keeper_aabb}",
        )

    # --- Lid -----------------------------------------------------------------
    lid_joint = object_model.get_articulation("lid_joint")
    ctx.check(
        "lid_joint_is_revolute",
        lid_joint.articulation_type == ArticulationType.REVOLUTE,
        details=f"type={lid_joint.articulation_type}",
    )
    # Lid panel must sit above the body floor at rest.
    lid_panel_aabb = ctx.part_element_world_aabb(lid, elem="lid_panel")
    floor_z = _floor_z(resolved)
    ctx.check(
        "lid_above_body",
        lid_panel_aabb is not None
        and lid_panel_aabb[0][2] >= floor_z + resolved.box_height - 0.010,
        details=(
            f"lid_panel_aabb={lid_panel_aabb}, expected_min_z>={floor_z + resolved.box_height}"
        ),
    )
    # Lid hinge sits at the rear of the body (negative X).
    ctx.check(
        "lid_hinge_on_rear",
        lid_joint.origin.xyz[0] < -resolved.box_depth * 0.35,
        details=f"lid_hinge_x={lid_joint.origin.xyz[0]}",
    )
    # Allow lid hinge knuckles to lightly nest into the body rear rim.
    for i in range(2):
        ctx.allow_overlap(
            body,
            lid,
            elem_a="rim_rear",
            elem_b=f"lid_hinge_knuckle_{i}",
            reason="Lid hinge knuckles share the hinge axis with the body rear edge.",
        )

    # --- Optional drawer -----------------------------------------------------
    if resolved.has_drawer:
        drawer = object_model.get_part("drawer")
        drawer_joint = object_model.get_articulation("drawer_joint")
        ctx.check(
            "drawer_joint_is_prismatic",
            drawer_joint.articulation_type == ArticulationType.PRISMATIC,
            details=f"type={drawer_joint.articulation_type}",
        )
        # Drawer sits inside the body footprint at rest.
        ctx.allow_overlap(
            body,
            drawer,
            reason="The drawer slides inside the body cavity proxy.",
        )

    # --- Optional handle stage 2 --------------------------------------------
    if resolved.handle_stage_count >= 2:
        stage2 = object_model.get_part("handle_stage_2")
        stage2_joint = object_model.get_articulation("handle_stage_2_joint")
        ctx.check(
            "handle_stage_2_joint_is_prismatic",
            stage2_joint.articulation_type == ArticulationType.PRISMATIC,
            details=f"type={stage2_joint.articulation_type}",
        )
        ctx.allow_overlap(
            handle_inner,
            stage2,
            reason="Stage 2 telescoping extension is nested inside the handle inner.",
        )

    # --- Front support ------------------------------------------------------
    if resolved.front_support == "small_casters":
        for ci in range(2):
            caster_joint = object_model.get_articulation(f"front_caster_swivel_{ci}")
            spin_joint = object_model.get_articulation(f"front_caster_spin_{ci}")
            ctx.check(
                f"front_caster_swivel_{ci}_is_continuous",
                caster_joint.articulation_type == ArticulationType.CONTINUOUS,
                details=f"type={caster_joint.articulation_type}",
            )
            ctx.check(
                f"front_caster_spin_{ci}_is_continuous",
                spin_joint.articulation_type == ArticulationType.CONTINUOUS,
                details=f"type={spin_joint.articulation_type}",
            )

    return ctx.report()
