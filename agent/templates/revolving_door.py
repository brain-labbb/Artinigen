"""Procedural Articraft template for ``revolving_door``.

Spec source: ``0_revised.md`` section 8 ("Revolving Door | 旋转门").

Identity: a single central_post carrying 2/3/4 radial wings (equal-angle) that
rotate together as one rigid unit around a vertical axis. The whole rotor lives
inside (or in front of) a static outer_drum that may be a full cylinder, a
partial cylinder, or an open frame. When ``wing_count == 2`` a bypass sliding
panel is added: parent is the static outer_drum and axis is along the door
opening width (perpendicular to the wing rotation plane).

Key invariants (enforced by ``resolve_config`` + ``run_revolving_door_tests``):

* Exactly one CONTINUOUS joint about ``(0, 0, 1)`` (the central rotation).
* Exactly one rotor (one central_post + one wing group) per record.
* Wings are placed at angles ``2*pi*i/N`` (within 1 deg).
* Wing radial extent / panel height derive from drum_inner_radius and
  drum_inner_height (resolved once) - never sampled inside ``_build_*``.
* Non-articulated decoration (top_cap, bottom_ring, side glass panels,
  push_bars, sensor blocks) is attached as ``parent.visual(...)`` on either
  outer_drum or central_post, not as independent parts.
* bypass_sliding_joint (only for wing_count==2) is parented to outer_drum,
  type PRISMATIC, axis along door opening width.
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

# ---------------------------------------------------------------------------
# Discrete parameter literals
# ---------------------------------------------------------------------------

DrumType = Literal["full_cylinder", "partial", "open_frame"]
DoorRadiusClass = Literal["small", "medium", "large"]
DoorHeightClass = Literal["low", "standard", "tall"]
WingMaterial = Literal["glass", "metal_frame", "wood_panel"]
PushBarStyle = Literal["straight", "curved", "none"]
TopCapStyle = Literal["flat", "thick", "decorative"]
BottomRingStyle = Literal["none", "low", "full"]
SensorModuleStyle = Literal["none", "small_blocks"]
MaterialStyle = Literal["glass", "dark_metal", "aluminum"]

# ---------------------------------------------------------------------------
# Bucket continuous ranges (door_radius and door_height are buckets + ranges).
# ---------------------------------------------------------------------------

DOOR_RADIUS_RANGES: dict[DoorRadiusClass, tuple[float, float]] = {
    # Inner radius of the drum, in meters. Wings reach approximately this far
    # minus a small clearance.
    "small": (0.85, 1.05),
    "medium": (1.05, 1.30),
    "large": (1.30, 1.70),
}
DOOR_HEIGHT_RANGES: dict[DoorHeightClass, tuple[float, float]] = {
    # Drum inner height in meters (floor of drum to bottom of top_cap).
    "low": (2.00, 2.40),
    "standard": (2.40, 2.90),
    "tall": (2.90, 3.50),
}

# ---------------------------------------------------------------------------
# Geometry constants (spine derives every wing dimension from these).
# ---------------------------------------------------------------------------

FLOOR_THICKNESS = 0.040  # outer_drum floor disc thickness
TOP_CAP_THICKNESS = {  # outer_drum top cap thickness, by style
    "flat": 0.060,
    "thick": 0.150,
    "decorative": 0.220,
}
WING_RADIAL_CLEARANCE = 0.020  # gap between wing tip and drum_inner_radius
WING_PANEL_THICKNESS = 0.035  # wing panel thickness
WING_TOP_BOTTOM_CLEARANCE = 0.030  # vertical clearance from drum floor/cap
CENTRAL_POST_RADIUS_RATIO = 0.050  # central post radius as fraction of drum radius
DRUM_WALL_THICKNESS = 0.040  # outer wall thickness of full/partial drum
PUSH_BAR_OFFSET = 0.55  # fraction of wing radial extent where push bar mounts
PUSH_BAR_THICKNESS = 0.035
BOTTOM_RING_HEIGHT_LOW = 0.080
BOTTOM_RING_HEIGHT_FULL = 0.200

MATERIAL_PALETTES: dict[
    MaterialStyle,
    tuple[
        tuple[float, float, float, float],  # frame_rgba
        tuple[float, float, float, float],  # accent_rgba
        tuple[float, float, float, float],  # glass_rgba (always translucent)
    ],
] = {
    "glass": (
        (0.78, 0.80, 0.82, 1.0),
        (0.38, 0.40, 0.44, 1.0),
        (0.55, 0.72, 0.85, 0.30),
    ),
    "dark_metal": (
        (0.20, 0.20, 0.22, 1.0),
        (0.10, 0.10, 0.11, 1.0),
        (0.42, 0.58, 0.72, 0.40),
    ),
    "aluminum": (
        (0.84, 0.85, 0.87, 1.0),
        (0.46, 0.48, 0.50, 1.0),
        (0.62, 0.76, 0.88, 0.30),
    ),
}

WING_BODY_PALETTES: dict[
    WingMaterial, tuple[tuple[float, float, float, float], tuple[float, float, float, float]]
] = {
    # (panel_rgba, stile_rgba) - the panel is the wing face, the stile is the
    # narrow vertical edge piece. ``glass`` keeps the existing translucent
    # glass material from the model palette.
    "glass": ((0.62, 0.78, 0.88, 0.30), (0.40, 0.42, 0.46, 1.0)),
    "metal_frame": ((0.72, 0.74, 0.76, 1.0), (0.30, 0.32, 0.36, 1.0)),
    "wood_panel": ((0.55, 0.36, 0.20, 1.0), (0.30, 0.20, 0.10, 1.0)),
}


# ---------------------------------------------------------------------------
# Config dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RevolvingDoorConfig:
    wing_count: int = 3
    drum_type: DrumType = "full_cylinder"
    door_radius: DoorRadiusClass = "medium"
    door_height: DoorHeightClass = "standard"
    wing_material: WingMaterial = "glass"
    push_bar_style: PushBarStyle = "straight"
    top_cap_style: TopCapStyle = "flat"
    bottom_ring: BottomRingStyle = "low"
    sensor_module: SensorModuleStyle = "small_blocks"
    material_style: MaterialStyle = "aluminum"
    # Optional continuous overrides; defaulted by ``resolve_config`` when None.
    drum_inner_radius: float | None = None
    drum_inner_height: float | None = None
    name: str = "reference_revolving_door"


@dataclass(frozen=True)
class ResolvedRevolvingDoorConfig:
    wing_count: int
    drum_type: DrumType
    door_radius: DoorRadiusClass
    door_height: DoorHeightClass
    wing_material: WingMaterial
    push_bar_style: PushBarStyle
    top_cap_style: TopCapStyle
    bottom_ring: BottomRingStyle
    sensor_module: SensorModuleStyle
    material_style: MaterialStyle
    drum_inner_radius: float
    drum_inner_height: float
    central_post_radius: float
    wing_radial_extent: float  # wing length from central axis to tip
    wing_panel_height: float  # wing vertical extent (panel)
    top_cap_thickness: float
    bottom_ring_thickness: float  # 0 if "none"
    drum_floor_z: float  # world Z of the top of the floor disc
    name: str


# ---------------------------------------------------------------------------
# Seed sampling
# ---------------------------------------------------------------------------


def config_from_seed(seed: int) -> RevolvingDoorConfig:
    """Sample a RevolvingDoorConfig from ``seed``.

    The seed-time sampler is the single source of structural / stylistic
    diversity. ``door_radius`` and ``door_height`` are picked first as
    discrete buckets; their continuous values are drawn inside
    ``resolve_config`` so that geometry stays consistent.
    """

    rng = random.Random(seed)

    # Spec text says wing_count in {2, 3, 4}. Weight 3 a bit higher because it
    # is the canonical revolving-door silhouette and easiest to validate.
    wing_count = rng.choices((2, 3, 4), weights=(0.20, 0.45, 0.35), k=1)[0]

    drum_type: DrumType = rng.choices(
        ("full_cylinder", "partial", "open_frame"),
        weights=(0.55, 0.25, 0.20),
        k=1,
    )[0]

    door_radius: DoorRadiusClass = rng.choices(
        ("small", "medium", "large"),
        weights=(0.30, 0.50, 0.20),
        k=1,
    )[0]
    door_height: DoorHeightClass = rng.choices(
        ("low", "standard", "tall"),
        weights=(0.25, 0.55, 0.20),
        k=1,
    )[0]

    wing_material: WingMaterial = rng.choices(
        ("glass", "metal_frame", "wood_panel"),
        weights=(0.55, 0.30, 0.15),
        k=1,
    )[0]
    push_bar_style: PushBarStyle = rng.choices(
        ("straight", "curved", "none"),
        weights=(0.45, 0.30, 0.25),
        k=1,
    )[0]
    top_cap_style: TopCapStyle = rng.choices(
        ("flat", "thick", "decorative"),
        weights=(0.45, 0.35, 0.20),
        k=1,
    )[0]
    bottom_ring: BottomRingStyle = rng.choices(
        ("none", "low", "full"),
        weights=(0.30, 0.45, 0.25),
        k=1,
    )[0]
    sensor_module: SensorModuleStyle = rng.choices(
        ("none", "small_blocks"),
        weights=(0.50, 0.50),
        k=1,
    )[0]
    material_style: MaterialStyle = rng.choices(
        ("glass", "dark_metal", "aluminum"),
        weights=(0.35, 0.30, 0.35),
        k=1,
    )[0]

    # Bucket-class continuous values: drawn here so ``resolve_config`` stays
    # a pure mapping, but they're inside ``DOOR_RADIUS_RANGES[door_radius]``
    # so the spine is honoured.
    rmin, rmax = DOOR_RADIUS_RANGES[door_radius]
    drum_inner_radius = round(rng.uniform(rmin, rmax), 4)
    hmin, hmax = DOOR_HEIGHT_RANGES[door_height]
    drum_inner_height = round(rng.uniform(hmin, hmax), 4)

    return RevolvingDoorConfig(
        wing_count=wing_count,
        drum_type=drum_type,
        door_radius=door_radius,
        door_height=door_height,
        wing_material=wing_material,
        push_bar_style=push_bar_style,
        top_cap_style=top_cap_style,
        bottom_ring=bottom_ring,
        sensor_module=sensor_module,
        material_style=material_style,
        drum_inner_radius=drum_inner_radius,
        drum_inner_height=drum_inner_height,
        name=f"seeded_revolving_door_{seed}",
    )


# ---------------------------------------------------------------------------
# Config resolution (every wing/decoration dimension derives from here)
# ---------------------------------------------------------------------------


def resolve_config(config: RevolvingDoorConfig) -> ResolvedRevolvingDoorConfig:
    if config.wing_count not in (2, 3, 4):
        raise ValueError(f"wing_count must be 2, 3, or 4 (got {config.wing_count})")
    if config.drum_type not in {"full_cylinder", "partial", "open_frame"}:
        raise ValueError(f"Unsupported drum_type: {config.drum_type}")
    if config.door_radius not in DOOR_RADIUS_RANGES:
        raise ValueError(f"Unsupported door_radius bucket: {config.door_radius}")
    if config.door_height not in DOOR_HEIGHT_RANGES:
        raise ValueError(f"Unsupported door_height bucket: {config.door_height}")
    if config.wing_material not in WING_BODY_PALETTES:
        raise ValueError(f"Unsupported wing_material: {config.wing_material}")
    if config.push_bar_style not in {"straight", "curved", "none"}:
        raise ValueError(f"Unsupported push_bar_style: {config.push_bar_style}")
    if config.top_cap_style not in TOP_CAP_THICKNESS:
        raise ValueError(f"Unsupported top_cap_style: {config.top_cap_style}")
    if config.bottom_ring not in {"none", "low", "full"}:
        raise ValueError(f"Unsupported bottom_ring: {config.bottom_ring}")
    if config.sensor_module not in {"none", "small_blocks"}:
        raise ValueError(f"Unsupported sensor_module: {config.sensor_module}")
    if config.material_style not in MATERIAL_PALETTES:
        raise ValueError(f"Unsupported material_style: {config.material_style}")

    if config.drum_inner_radius is None:
        rmin, rmax = DOOR_RADIUS_RANGES[config.door_radius]
        drum_inner_radius = 0.5 * (rmin + rmax)
    else:
        drum_inner_radius = float(config.drum_inner_radius)
    if drum_inner_radius < 0.40:
        raise ValueError(f"drum_inner_radius too small: {drum_inner_radius}")

    if config.drum_inner_height is None:
        hmin, hmax = DOOR_HEIGHT_RANGES[config.door_height]
        drum_inner_height = 0.5 * (hmin + hmax)
    else:
        drum_inner_height = float(config.drum_inner_height)
    if drum_inner_height < 1.5:
        raise ValueError(f"drum_inner_height too small: {drum_inner_height}")

    top_cap_thickness = TOP_CAP_THICKNESS[config.top_cap_style]

    if config.bottom_ring == "none":
        bottom_ring_thickness = 0.0
    elif config.bottom_ring == "low":
        bottom_ring_thickness = BOTTOM_RING_HEIGHT_LOW
    else:
        bottom_ring_thickness = BOTTOM_RING_HEIGHT_FULL

    drum_floor_z = FLOOR_THICKNESS  # top surface of floor disc
    central_post_radius = max(0.035, min(0.12, drum_inner_radius * CENTRAL_POST_RADIUS_RATIO))
    wing_radial_extent = drum_inner_radius - WING_RADIAL_CLEARANCE
    # Wing panel height: from above the bottom ring (or floor) up to below the
    # top cap, with a small clearance on each side.
    panel_bottom = drum_floor_z + bottom_ring_thickness + WING_TOP_BOTTOM_CLEARANCE
    panel_top = drum_floor_z + drum_inner_height - WING_TOP_BOTTOM_CLEARANCE
    wing_panel_height = max(0.8, panel_top - panel_bottom)

    return ResolvedRevolvingDoorConfig(
        wing_count=config.wing_count,
        drum_type=config.drum_type,
        door_radius=config.door_radius,
        door_height=config.door_height,
        wing_material=config.wing_material,
        push_bar_style=config.push_bar_style,
        top_cap_style=config.top_cap_style,
        bottom_ring=config.bottom_ring,
        sensor_module=config.sensor_module,
        material_style=config.material_style,
        drum_inner_radius=drum_inner_radius,
        drum_inner_height=drum_inner_height,
        central_post_radius=central_post_radius,
        wing_radial_extent=wing_radial_extent,
        wing_panel_height=wing_panel_height,
        top_cap_thickness=top_cap_thickness,
        bottom_ring_thickness=bottom_ring_thickness,
        drum_floor_z=drum_floor_z,
        name=config.name,
    )


# ---------------------------------------------------------------------------
# Drum (static parent) construction
# ---------------------------------------------------------------------------


def _add_full_cylinder_wall(
    drum,
    resolved: ResolvedRevolvingDoorConfig,
    *,
    frame_material,
    glass_material,
) -> None:
    """Render the drum wall as a ring of tangential panel segments.

    Instead of a single hollow cylinder mesh (we avoid cadquery in templates),
    the wall is approximated by 12 tangential glass panels with bronze
    mullions between them. ``partial`` keeps only ~8 panels on one side so the
    drum is open in the door region.
    """

    panel_count = 12
    radius = resolved.drum_inner_radius + 0.5 * DRUM_WALL_THICKNESS
    panel_arc = 2.0 * math.pi / panel_count
    # tangent panel width: chord across one arc segment, with a margin so
    # adjacent panels don't intersect.
    panel_width = 2.0 * radius * math.sin(0.5 * panel_arc) * 0.94
    panel_height = resolved.drum_inner_height - resolved.bottom_ring_thickness - 0.020
    panel_center_z = resolved.drum_floor_z + resolved.bottom_ring_thickness + 0.5 * panel_height

    if resolved.drum_type == "full_cylinder":
        keep_indices = set(range(panel_count))
    else:
        # partial: drop a contiguous opening (~120 deg) on the +Y side so the
        # rotor face is exposed.
        opening = panel_count // 3
        skip_start = (panel_count - opening) // 2
        # opening centred on +Y means we skip panels around index = panel_count/4
        center_idx = panel_count // 4
        skip_indices = {
            (center_idx + d) % panel_count for d in range(-opening // 2, opening // 2 + 1)
        }
        keep_indices = set(range(panel_count)) - skip_indices
        # ensure at least 4 panels remain for a partial drum
        if len(keep_indices) < 4:
            keep_indices = {0, panel_count // 4, panel_count // 2, 3 * panel_count // 4}
        _ = skip_start  # silence linter; helper above is enough

    for i in range(panel_count):
        if i not in keep_indices:
            continue
        angle = (2.0 * math.pi * i) / panel_count
        cx = radius * math.cos(angle)
        cy = radius * math.sin(angle)
        yaw = angle + 0.5 * math.pi  # panel face points outward radially
        drum.visual(
            Box((panel_width, DRUM_WALL_THICKNESS, panel_height)),
            origin=Origin(xyz=(cx, cy, panel_center_z), rpy=(0.0, 0.0, yaw)),
            material=glass_material,
            name=f"side_glass_panel_{i}",
        )
        # Mullion (vertical post on the outside of the panel)
        mullion_radius = 0.030
        post_x = (radius + 0.5 * DRUM_WALL_THICKNESS) * math.cos(angle)
        post_y = (radius + 0.5 * DRUM_WALL_THICKNESS) * math.sin(angle)
        drum.visual(
            Cylinder(radius=mullion_radius, length=panel_height),
            origin=Origin(xyz=(post_x, post_y, panel_center_z)),
            material=frame_material,
            name=f"drum_mullion_{i}",
        )


def _add_open_frame(
    drum,
    resolved: ResolvedRevolvingDoorConfig,
    *,
    frame_material,
) -> None:
    """Render the drum as a skeletal frame: vertical posts and a top hoop."""

    post_count = 6
    radius = resolved.drum_inner_radius + 0.5 * DRUM_WALL_THICKNESS
    post_height = resolved.drum_inner_height - resolved.bottom_ring_thickness - 0.020
    post_z = resolved.drum_floor_z + resolved.bottom_ring_thickness + 0.5 * post_height
    for i in range(post_count):
        angle = (2.0 * math.pi * i) / post_count
        drum.visual(
            Cylinder(radius=0.025, length=post_height),
            origin=Origin(
                xyz=(radius * math.cos(angle), radius * math.sin(angle), post_z),
            ),
            material=frame_material,
            name=f"open_frame_post_{i}",
        )


def _add_top_cap(
    drum,
    resolved: ResolvedRevolvingDoorConfig,
    *,
    frame_material,
    accent_material,
) -> None:
    cap_radius = resolved.drum_inner_radius + DRUM_WALL_THICKNESS + 0.040
    cap_z = resolved.drum_floor_z + resolved.drum_inner_height + 0.5 * resolved.top_cap_thickness
    drum.visual(
        Cylinder(radius=cap_radius, length=resolved.top_cap_thickness),
        origin=Origin(xyz=(0.0, 0.0, cap_z)),
        material=frame_material,
        name="top_cap",
    )
    if resolved.top_cap_style == "decorative":
        # Add a smaller crown disc on top of the cap.
        crown_radius = cap_radius * 0.55
        crown_thickness = 0.060
        drum.visual(
            Cylinder(radius=crown_radius, length=crown_thickness),
            origin=Origin(
                xyz=(
                    0.0,
                    0.0,
                    cap_z + 0.5 * resolved.top_cap_thickness + 0.5 * crown_thickness,
                )
            ),
            material=accent_material,
            name="top_cap_crown",
        )


def _add_bottom_ring(
    drum,
    resolved: ResolvedRevolvingDoorConfig,
    *,
    accent_material,
) -> None:
    if resolved.bottom_ring == "none":
        return
    ring_radius = resolved.drum_inner_radius + DRUM_WALL_THICKNESS + 0.020
    ring_z = resolved.drum_floor_z + 0.5 * resolved.bottom_ring_thickness
    drum.visual(
        Cylinder(radius=ring_radius, length=resolved.bottom_ring_thickness),
        origin=Origin(xyz=(0.0, 0.0, ring_z)),
        material=accent_material,
        name="bottom_ring",
    )


def _add_sensor_module(
    drum,
    resolved: ResolvedRevolvingDoorConfig,
    *,
    accent_material,
) -> None:
    if resolved.sensor_module == "none":
        return
    cap_radius = resolved.drum_inner_radius + DRUM_WALL_THICKNESS + 0.040
    cap_z_top = resolved.drum_floor_z + resolved.drum_inner_height + resolved.top_cap_thickness
    # Two small motion-sensor blocks on the underside of the cap, on opposite
    # sides of the drum.
    block_size = (0.110, 0.080, 0.045)
    for i, angle in enumerate((math.pi / 2.0, -math.pi / 2.0)):
        bx = (cap_radius - 0.10) * math.cos(angle)
        by = (cap_radius - 0.10) * math.sin(angle)
        drum.visual(
            Box(block_size),
            origin=Origin(
                xyz=(bx, by, cap_z_top - resolved.top_cap_thickness - 0.5 * block_size[2]),
                rpy=(0.0, 0.0, angle),
            ),
            material=accent_material,
            name=f"sensor_block_{i}",
        )


def _build_drum(
    drum,
    resolved: ResolvedRevolvingDoorConfig,
    *,
    frame_material,
    accent_material,
    glass_material,
) -> None:
    # Floor disc - this is the "ground" of the assembly and ensures the
    # outer_drum part has at least one visual at the origin so it can host the
    # central rotation joint.
    floor_radius = resolved.drum_inner_radius + DRUM_WALL_THICKNESS + 0.060
    drum.visual(
        Cylinder(radius=floor_radius, length=FLOOR_THICKNESS),
        origin=Origin(xyz=(0.0, 0.0, 0.5 * FLOOR_THICKNESS)),
        material=accent_material,
        name="floor_disc",
    )

    if resolved.drum_type in ("full_cylinder", "partial"):
        _add_full_cylinder_wall(
            drum,
            resolved,
            frame_material=frame_material,
            glass_material=glass_material,
        )
    else:
        _add_open_frame(drum, resolved, frame_material=frame_material)

    _add_top_cap(
        drum,
        resolved,
        frame_material=frame_material,
        accent_material=accent_material,
    )
    _add_bottom_ring(drum, resolved, accent_material=accent_material)
    _add_sensor_module(drum, resolved, accent_material=accent_material)


# ---------------------------------------------------------------------------
# Bypass door (only for wing_count == 2)
# ---------------------------------------------------------------------------


def _add_bypass_panel(
    panel,
    resolved: ResolvedRevolvingDoorConfig,
    *,
    frame_material,
    glass_material,
) -> None:
    """Author the static bypass panel geometry in part-local coordinates.

    The panel's local origin is at the floor level, centred on the panel.
    """

    # Panel size: tall and narrow, similar to a bypass door leaf.
    panel_height = resolved.drum_inner_height - 0.080
    panel_width = max(0.85, 0.55 * resolved.drum_inner_radius)
    leaf_thickness = 0.060
    rail_h = 0.090
    stile_w = 0.080

    panel.visual(
        Box((panel_width - 2.0 * stile_w, leaf_thickness * 0.5, panel_height - 2.0 * rail_h)),
        origin=Origin(xyz=(0.0, 0.0, 0.5 * panel_height)),
        material=glass_material,
        name="bypass_glass",
    )
    panel.visual(
        Box((stile_w, leaf_thickness, panel_height)),
        origin=Origin(xyz=(-0.5 * panel_width + 0.5 * stile_w, 0.0, 0.5 * panel_height)),
        material=frame_material,
        name="bypass_left_stile",
    )
    panel.visual(
        Box((stile_w, leaf_thickness, panel_height)),
        origin=Origin(xyz=(0.5 * panel_width - 0.5 * stile_w, 0.0, 0.5 * panel_height)),
        material=frame_material,
        name="bypass_right_stile",
    )
    panel.visual(
        Box((panel_width, leaf_thickness, rail_h)),
        origin=Origin(xyz=(0.0, 0.0, 0.5 * rail_h)),
        material=frame_material,
        name="bypass_bottom_rail",
    )
    panel.visual(
        Box((panel_width, leaf_thickness, rail_h)),
        origin=Origin(xyz=(0.0, 0.0, panel_height - 0.5 * rail_h)),
        material=frame_material,
        name="bypass_top_rail",
    )


# ---------------------------------------------------------------------------
# Central post + wings (the single rotor)
# ---------------------------------------------------------------------------


def _add_wing(
    post,
    *,
    index: int,
    angle: float,
    resolved: ResolvedRevolvingDoorConfig,
    panel_material,
    stile_material,
    frame_material,
) -> None:
    """Add wing ``index`` at radial ``angle`` (radians) as visuals on
    ``central_post``. Wings rotate as part of the post; they are NOT separate
    parts and do not own articulations.
    """

    radial_length = resolved.wing_radial_extent - resolved.central_post_radius
    panel_height = resolved.wing_panel_height
    panel_center_z = (
        resolved.drum_floor_z
        + resolved.bottom_ring_thickness
        + WING_TOP_BOTTOM_CLEARANCE
        + 0.5 * panel_height
    )
    # Inner edge of the wing starts at the post surface; outer edge is at
    # wing_radial_extent. Local origin of the panel is at its centre.
    radial_center = resolved.central_post_radius + 0.5 * radial_length
    c = math.cos(angle)
    s = math.sin(angle)

    # Wing panel (the main visible face).
    post.visual(
        Box((radial_length, WING_PANEL_THICKNESS, panel_height)),
        origin=Origin(
            xyz=(c * radial_center, s * radial_center, panel_center_z),
            rpy=(0.0, 0.0, angle),
        ),
        material=panel_material,
        name=f"wing_{index}_panel",
    )

    # Top and bottom rails (decorative reinforcement strips).
    rail_h = 0.060
    for z_offset, label in (
        (-0.5 * panel_height + 0.5 * rail_h, "bottom"),
        (0.5 * panel_height - 0.5 * rail_h, "top"),
    ):
        post.visual(
            Box((radial_length, WING_PANEL_THICKNESS + 0.015, rail_h)),
            origin=Origin(
                xyz=(c * radial_center, s * radial_center, panel_center_z + z_offset),
                rpy=(0.0, 0.0, angle),
            ),
            material=stile_material,
            name=f"wing_{index}_{label}_rail",
        )

    # Outer stile (vertical post at the wing tip).
    stile_w = 0.060
    stile_thickness = 0.080
    outer_r = resolved.central_post_radius + radial_length - 0.5 * stile_w
    post.visual(
        Box((stile_w, stile_thickness, panel_height)),
        origin=Origin(
            xyz=(c * outer_r, s * outer_r, panel_center_z),
            rpy=(0.0, 0.0, angle),
        ),
        material=stile_material,
        name=f"wing_{index}_outer_stile",
    )

    # Push bar (door pull). Mounted on the wing at PUSH_BAR_OFFSET along the
    # radius. ``none`` means no visual; ``curved`` uses a thicker rounded bar.
    if resolved.push_bar_style != "none":
        bar_r = resolved.central_post_radius + PUSH_BAR_OFFSET * radial_length
        bar_z = panel_center_z
        bar_length = 0.50 * radial_length
        bar_radius = 0.022 if resolved.push_bar_style == "straight" else 0.030
        # Align bar along the wing's radial direction (its "length" axis is the
        # cylinder local +Z; we rotate so +Z points along the radial direction).
        # cylinder length axis local +Z; rpy here orients cylinder so its
        # length aligns with the radial direction in world frame.
        bar_yaw = angle
        bar_pitch = math.pi / 2.0
        post.visual(
            Cylinder(radius=bar_radius, length=bar_length),
            origin=Origin(
                xyz=(c * bar_r, s * bar_r, bar_z),
                rpy=(0.0, bar_pitch, bar_yaw),
            ),
            material=frame_material,
            name=f"wing_{index}_push_bar",
        )


def _build_central_post(
    post,
    resolved: ResolvedRevolvingDoorConfig,
    *,
    frame_material,
    accent_material,
) -> None:
    # Hub at the bottom (sits on the drum floor).
    hub_height = 0.120
    post.visual(
        Cylinder(radius=resolved.central_post_radius * 2.4, length=hub_height),
        origin=Origin(xyz=(0.0, 0.0, 0.5 * hub_height)),
        material=accent_material,
        name="bottom_hub",
    )
    # Main central shaft - origin local to the rotor part (joint frame).
    shaft_length = resolved.drum_inner_height - 0.040
    post.visual(
        Cylinder(radius=resolved.central_post_radius, length=shaft_length),
        origin=Origin(xyz=(0.0, 0.0, 0.5 * shaft_length + hub_height)),
        material=frame_material,
        name="central_shaft",
    )
    # Top hub (mirrors the bottom hub, sits just below the drum top_cap).
    post.visual(
        Cylinder(radius=resolved.central_post_radius * 2.4, length=hub_height),
        origin=Origin(
            xyz=(0.0, 0.0, resolved.drum_inner_height - 0.5 * hub_height - 0.020),
        ),
        material=accent_material,
        name="top_hub",
    )


def _add_wings(
    post,
    resolved: ResolvedRevolvingDoorConfig,
    *,
    panel_material,
    stile_material,
    frame_material,
) -> None:
    """Place the N wings on the central_post at equal angles ``2*pi*i/N``."""

    for i in range(resolved.wing_count):
        angle = (2.0 * math.pi * i) / resolved.wing_count
        _add_wing(
            post,
            index=i,
            angle=angle,
            resolved=resolved,
            panel_material=panel_material,
            stile_material=stile_material,
            frame_material=frame_material,
        )


# ---------------------------------------------------------------------------
# Top-level builder
# ---------------------------------------------------------------------------


def build_revolving_door(
    config: RevolvingDoorConfig | None = None,
    *,
    assets: AssetContext | None = None,
) -> ArticulatedObject:
    config = config or RevolvingDoorConfig()
    resolved = resolve_config(config)
    if assets is None:
        assets = AssetContext(Path(tempfile.mkdtemp(prefix="articraft-revolving-door-assets-")))

    model = ArticulatedObject(name=resolved.name, assets=assets)

    frame_rgba, accent_rgba, glass_rgba = MATERIAL_PALETTES[resolved.material_style]
    frame_material = model.material("door_frame", rgba=frame_rgba)
    accent_material = model.material("door_accent", rgba=accent_rgba)
    glass_material = model.material("door_glass", rgba=glass_rgba)
    panel_rgba, stile_rgba = WING_BODY_PALETTES[resolved.wing_material]
    panel_material = model.material("wing_panel", rgba=panel_rgba)
    stile_material = model.material("wing_stile", rgba=stile_rgba)

    drum = model.part("outer_drum")
    _build_drum(
        drum,
        resolved,
        frame_material=frame_material,
        accent_material=accent_material,
        glass_material=glass_material,
    )

    post = model.part("central_post")
    _build_central_post(
        post,
        resolved,
        frame_material=frame_material,
        accent_material=accent_material,
    )
    _add_wings(
        post,
        resolved,
        panel_material=panel_material,
        stile_material=stile_material,
        frame_material=frame_material,
    )

    # Central rotation joint: continuous, axis vertical. The joint origin is at
    # the centre of the drum floor; the rotor's local frame coincides with the
    # joint frame at rest.
    model.articulation(
        "central_rotation_joint",
        ArticulationType.CONTINUOUS,
        parent=drum,
        child=post,
        origin=Origin(xyz=(0.0, 0.0, resolved.drum_floor_z)),
        axis=(0.0, 0.0, 1.0),
        motion_limits=MotionLimits(effort=120.0, velocity=1.4),
    )

    # Bypass sliding panel: only for 2-wing bypass configuration. Parent is the
    # static drum (NOT the central_post). Axis is along the door opening width
    # (world +X), perpendicular to the wing rotation plane normal (Z).
    if resolved.wing_count == 2:
        bypass = model.part("bypass_panel")
        _add_bypass_panel(
            bypass,
            resolved,
            frame_material=frame_material,
            glass_material=glass_material,
        )
        # Anchor the panel at one side of the drum opening (+Y face), offset
        # to one side so its prismatic travel can slide it across the opening.
        opening_y = resolved.drum_inner_radius + DRUM_WALL_THICKNESS + 0.010
        panel_width = max(0.85, 0.55 * resolved.drum_inner_radius)
        anchor_x = -0.5 * panel_width
        slide_upper = panel_width  # full panel-width slide
        model.articulation(
            "bypass_sliding_joint",
            ArticulationType.PRISMATIC,
            parent=drum,
            child=bypass,
            origin=Origin(xyz=(anchor_x, opening_y, resolved.drum_floor_z)),
            axis=(1.0, 0.0, 0.0),
            motion_limits=MotionLimits(
                effort=80.0,
                velocity=0.40,
                lower=0.0,
                upper=slide_upper,
            ),
        )

    return model


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------


def run_revolving_door_tests(
    object_model: ArticulatedObject, config: RevolvingDoorConfig
) -> TestReport:
    resolved = resolve_config(config)
    ctx = TestContext(object_model)

    drum = object_model.get_part("outer_drum")
    post = object_model.get_part("central_post")
    rotation_joint = object_model.get_articulation("central_rotation_joint")

    # 1. Exactly one rotor: only one CONTINUOUS joint and only one
    # ``central_post`` part.
    continuous_joints = [
        j for j in object_model.articulations if j.articulation_type == ArticulationType.CONTINUOUS
    ]
    ctx.check(
        "single_continuous_rotation_joint",
        len(continuous_joints) == 1,
        details=f"continuous_joints={[j.name for j in continuous_joints]}",
    )
    central_post_parts = [p for p in object_model.parts if p.name == "central_post"]
    ctx.check(
        "single_central_post_per_record",
        len(central_post_parts) == 1,
        details=f"central_post_parts={[p.name for p in central_post_parts]}",
    )

    # 2. Rotation axis must be vertical (0, 0, +/-1).
    ax = rotation_joint.axis
    ctx.check(
        "central_rotation_axis_vertical",
        abs(ax[0]) < 1e-6 and abs(ax[1]) < 1e-6 and abs(abs(ax[2]) - 1.0) < 1e-6,
        details=f"axis={ax}",
    )

    # 3. Rotation joint connects outer_drum (parent) -> central_post (child).
    ctx.check(
        "rotation_parent_is_outer_drum",
        rotation_joint.parent == "outer_drum" and rotation_joint.child == "central_post",
        details=f"parent={rotation_joint.parent}, child={rotation_joint.child}",
    )

    # 4. Wings: there are exactly ``wing_count`` wing panels and they are
    # placed at equal angles 2*pi*i/N (tolerance < 1 deg) inferred from the
    # XY position of each panel's centre.
    wing_panel_visuals = [
        v
        for v in post.visuals
        if v.name is not None and v.name.startswith("wing_") and v.name.endswith("_panel")
    ]
    ctx.check(
        "wing_panel_count_matches",
        len(wing_panel_visuals) == resolved.wing_count,
        details=(f"wing_panel_count={len(wing_panel_visuals)}, expected={resolved.wing_count}"),
    )

    expected_angles = sorted(
        ((2.0 * math.pi * i) / resolved.wing_count) % (2.0 * math.pi)
        for i in range(resolved.wing_count)
    )
    observed_angles = []
    for v in wing_panel_visuals:
        x, y, _z = v.origin.xyz
        observed_angles.append(math.atan2(y, x) % (2.0 * math.pi))
    observed_angles.sort()
    tol_rad = math.radians(1.0)
    ang_ok = len(observed_angles) == len(expected_angles) and all(
        # circular difference
        min(abs(o - e), 2.0 * math.pi - abs(o - e)) < tol_rad
        for o, e in zip(observed_angles, expected_angles)
    )
    ctx.check(
        "wings_equal_angle_distribution",
        ang_ok,
        details=f"observed={observed_angles}, expected={expected_angles}",
    )

    # 5. Wings stay inside drum radius (tip radius <= drum_inner_radius).
    max_tip_radius = 0.0
    for i in range(resolved.wing_count):
        # outer_stile sits at the radial extent minus half the stile width
        outer_stile = next((v for v in post.visuals if v.name == f"wing_{i}_outer_stile"), None)
        if outer_stile is None:
            continue
        x, y, _z = outer_stile.origin.xyz
        max_tip_radius = max(max_tip_radius, math.hypot(x, y))
    ctx.check(
        "wings_within_drum_radius",
        max_tip_radius <= resolved.drum_inner_radius + 1e-3,
        details=(
            f"max_tip_radius={max_tip_radius:.3f}, "
            f"drum_inner_radius={resolved.drum_inner_radius:.3f}"
        ),
    )

    # 6. Wings actually rotate with the post: a half-turn pose moves wing_0's
    # outer_stile to the opposite side.
    stile_rest = ctx.part_element_world_aabb(post, elem="wing_0_outer_stile")
    with ctx.pose({rotation_joint: math.pi}):
        stile_half = ctx.part_element_world_aabb(post, elem="wing_0_outer_stile")
    if stile_rest is not None and stile_half is not None:
        rest_cx = 0.5 * (stile_rest[0][0] + stile_rest[1][0])
        rest_cy = 0.5 * (stile_rest[0][1] + stile_rest[1][1])
        half_cx = 0.5 * (stile_half[0][0] + stile_half[1][0])
        half_cy = 0.5 * (stile_half[0][1] + stile_half[1][1])
        moved = math.hypot(half_cx - rest_cx, half_cy - rest_cy)
        ctx.check(
            "wings_rotate_with_post",
            moved > 0.5 * resolved.wing_radial_extent,
            details=(
                f"rest=({rest_cx:.3f},{rest_cy:.3f}), "
                f"half=({half_cx:.3f},{half_cy:.3f}), moved={moved:.3f}"
            ),
        )
    else:
        ctx.check(
            "wings_rotate_with_post",
            False,
            details="missing wing_0_outer_stile element AABB",
        )

    # 7. central_shaft is centred on the drum axis and vertical.
    shaft = next((v for v in post.visuals if v.name == "central_shaft"), None)
    if shaft is not None:
        sx, sy, _sz = shaft.origin.xyz
        ctx.check(
            "central_shaft_on_drum_axis",
            abs(sx) < 1e-3 and abs(sy) < 1e-3,
            details=f"shaft xyz={shaft.origin.xyz}",
        )

    # 8. floor_disc present on the drum so the rotor sits on something.
    drum_visual_names = {v.name for v in drum.visuals if v.name is not None}
    ctx.check(
        "drum_has_floor_disc",
        "floor_disc" in drum_visual_names,
        details=f"drum_visuals={sorted(drum_visual_names)}",
    )

    # 9. top_cap present on the drum (mandated by spec when drum is present).
    ctx.check(
        "drum_has_top_cap",
        "top_cap" in drum_visual_names,
        details=f"drum_visuals={sorted(drum_visual_names)}",
    )

    # 10. Push-bar visuals match push_bar_style (none -> 0; otherwise == wing_count).
    push_bar_count = sum(
        1 for v in post.visuals if v.name is not None and v.name.endswith("_push_bar")
    )
    if resolved.push_bar_style == "none":
        ctx.check(
            "no_push_bars_when_style_none",
            push_bar_count == 0,
            details=f"push_bar_count={push_bar_count}",
        )
    else:
        ctx.check(
            "push_bar_count_matches_wing_count",
            push_bar_count == resolved.wing_count,
            details=(f"push_bar_count={push_bar_count}, expected={resolved.wing_count}"),
        )

    # 11. Bypass sliding joint: present iff wing_count == 2.
    bypass_joints = [j for j in object_model.articulations if j.name == "bypass_sliding_joint"]
    if resolved.wing_count == 2:
        ctx.check(
            "bypass_joint_present_for_2_wing",
            len(bypass_joints) == 1,
            details=f"bypass_joints={[j.name for j in bypass_joints]}",
        )
        if bypass_joints:
            bj = bypass_joints[0]
            ctx.check(
                "bypass_joint_parent_is_drum",
                bj.parent == "outer_drum",
                details=f"parent={bj.parent}",
            )
            ctx.check(
                "bypass_joint_type_prismatic",
                bj.articulation_type == ArticulationType.PRISMATIC,
                details=f"type={bj.articulation_type}",
            )
            # axis must be horizontal (zero Z), along the door opening width.
            bax = bj.axis
            ctx.check(
                "bypass_axis_horizontal_along_opening",
                abs(bax[2]) < 1e-6 and (abs(bax[0]) > 1e-6 or abs(bax[1]) > 1e-6),
                details=f"axis={bax}",
            )
    else:
        ctx.check(
            "no_bypass_joint_when_more_than_2_wings",
            len(bypass_joints) == 0,
            details=f"bypass_joints={[j.name for j in bypass_joints]}",
        )

    # 12. Identity: outer_drum + central_post exist.
    part_names = {p.name for p in object_model.parts}
    ctx.check(
        "has_outer_drum_and_central_post",
        "outer_drum" in part_names and "central_post" in part_names,
        details=f"parts={sorted(part_names)}",
    )

    return ctx.report()


# ---------------------------------------------------------------------------
# Convenience wrappers
# ---------------------------------------------------------------------------


def build_seeded_revolving_door(
    seed: int, *, assets: AssetContext | None = None
) -> ArticulatedObject:
    return build_revolving_door(config_from_seed(seed), assets=assets)


def with_overrides(config: RevolvingDoorConfig, **kwargs: object) -> RevolvingDoorConfig:
    return replace(config, **kwargs)
