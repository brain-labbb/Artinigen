"""Procedural template for the
``standing_desk_with_synchronous_telescoping_legs_and_articulated_controls``
category.

Implementation notes
--------------------

* Uses spec **mode B** (multi-leg Mimic).  One leg is designated as the
  *primary* leg and drives every other leg's first-stage prismatic via
  ``Mimic(joint=<primary first-stage joint>, multiplier=1.0, offset=0.0)``.
* For ``stage_count = N`` (per leg), each leg has ``N - 1`` prismatic joints:
  outer -> mid (if N >= 3) -> inner.  Same-leg downstream prismatics Mimic
  to the leg's first stage; across legs, every other leg's first stage
  Mimics to the primary leg's first stage.
* Desktop is FIXED to the primary leg's innermost stage.  All other legs'
  innermost stages have Mimic prismatic chains, so the synced rise produces
  ``max(Delta z) - min(Delta z) < 1 mm`` by construction.
* ``crossbar_style = integrated_into_desktop_apron`` adds the cross beam as
  a ``desktop.visual(...)`` and creates **no** crossbar part/joint.  The
  other styles attach a ``crossbar`` part FIXED to the primary leg's
  innermost stage so it tracks the desktop.
* Buttons are prismatic, parented on ``control_panel`` (which is FIXED to
  the desktop).  Axis direction follows the panel mounting orientation so
  positive ``q`` always presses the button into the panel.
* All decorative sub-parts (foot pads, cable management, screen badges,
  apron crossbar) are attached via ``parent.visual(...)``, never separate
  parts and never separate FIXED articulations.
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
    Mimic,
    MotionLimits,
    Origin,
    TestContext,
    TestReport,
)

# ---------------------------------------------------------------------------
# Discrete parameter literals
# ---------------------------------------------------------------------------

DesktopShape = Literal["rectangle", "rounded", "L_shape"]
DesktopSize = Literal["small", "medium", "large"]
LegCrossSection = Literal["rectangular", "round", "oval"]
CrossbarStyle = Literal["front", "rear", "double", "integrated_into_desktop_apron"]
FootStyle = Literal["T_foot", "rectangular", "wide"]
ControlPanelPosition = Literal["left", "right", "center", "front_underside"]
MaterialStyle = Literal["wood_metal", "black", "white"]

# ---------------------------------------------------------------------------
# Spine ranges (per bucket).  Continuous values are sampled from these.
# ---------------------------------------------------------------------------

# Desktop size buckets: (length_x_range, width_y_range)
DESKTOP_SIZE_RANGES: dict[DesktopSize, tuple[tuple[float, float], tuple[float, float]]] = {
    "small": ((1.00, 1.20), (0.55, 0.65)),
    "medium": ((1.30, 1.60), (0.65, 0.75)),
    "large": ((1.70, 2.10), (0.75, 0.85)),
}

DESKTOP_THICKNESS = 0.030

# Outer leg envelope (x_size_outer, y_size_outer) before cross-section reshape.
OUTER_LEG_X_RANGE = (0.075, 0.105)
OUTER_LEG_Y_RANGE = (0.075, 0.105)

# Outer leg vertical length (without inner stages extended).
OUTER_LEG_HEIGHT_RANGE = (0.55, 0.75)

# Each stage shrinks the cross-section by this much.
STAGE_SHRINK = 0.78

# Each inner stage vertical length: fraction of outer leg height (covers
# overlap and travel).  Larger -> more travel and more overlap reserve.
STAGE_LENGTH_FACTOR = 0.95

# Useful travel of a single prismatic step.  Total max desktop rise =
# (stage_count - 1) * SINGLE_STAGE_TRAVEL.
SINGLE_STAGE_TRAVEL_RANGE = (0.22, 0.34)

# Base / foot constants (the "feet" are visuals on the base part).
BASE_PLATE_THICKNESS = 0.022

# Materials (outer_leg, inner_leg, accent, desktop_top, button, panel).
MATERIAL_PALETTES: dict[
    MaterialStyle,
    dict[str, tuple[float, float, float, float]],
] = {
    "wood_metal": {
        "outer_leg": (0.30, 0.32, 0.34, 1.0),
        "inner_leg": (0.60, 0.62, 0.64, 1.0),
        "accent": (0.18, 0.19, 0.21, 1.0),
        "desktop_top": (0.63, 0.49, 0.30, 1.0),
        "panel": (0.18, 0.18, 0.20, 1.0),
        "button": (0.78, 0.79, 0.80, 1.0),
    },
    "black": {
        "outer_leg": (0.10, 0.10, 0.11, 1.0),
        "inner_leg": (0.18, 0.18, 0.20, 1.0),
        "accent": (0.07, 0.07, 0.08, 1.0),
        "desktop_top": (0.13, 0.13, 0.14, 1.0),
        "panel": (0.06, 0.06, 0.07, 1.0),
        "button": (0.56, 0.57, 0.60, 1.0),
    },
    "white": {
        "outer_leg": (0.94, 0.94, 0.93, 1.0),
        "inner_leg": (0.86, 0.86, 0.85, 1.0),
        "accent": (0.70, 0.70, 0.72, 1.0),
        "desktop_top": (0.97, 0.95, 0.92, 1.0),
        "panel": (0.84, 0.84, 0.86, 1.0),
        "button": (0.34, 0.34, 0.36, 1.0),
    },
}


# ---------------------------------------------------------------------------
# Config dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StandingDeskConfig:
    leg_count: int = 2
    stage_count_per_leg: int = 2
    desktop_shape: DesktopShape = "rectangle"
    desktop_size: DesktopSize = "medium"
    leg_cross_section: LegCrossSection = "rectangular"
    crossbar_style: CrossbarStyle = "front"
    foot_style: FootStyle = "T_foot"
    control_panel_position: ControlPanelPosition = "right"
    button_count: int = 4
    material_style: MaterialStyle = "wood_metal"

    # Spine values - if None they are filled in resolve_config from bucket defaults.
    desktop_length: float | None = None
    desktop_width: float | None = None
    outer_leg_x: float | None = None
    outer_leg_y: float | None = None
    outer_leg_height: float | None = None
    single_stage_travel: float | None = None

    name: str = "reference_standing_desk"


@dataclass(frozen=True)
class ResolvedStandingDeskConfig:
    leg_count: int
    stage_count_per_leg: int
    desktop_shape: DesktopShape
    desktop_size: DesktopSize
    leg_cross_section: LegCrossSection
    crossbar_style: CrossbarStyle
    foot_style: FootStyle
    control_panel_position: ControlPanelPosition
    button_count: int
    material_style: MaterialStyle
    # Derived geometry.
    desktop_length: float
    desktop_width: float
    outer_leg_x: float
    outer_leg_y: float
    outer_leg_height: float
    single_stage_travel: float
    # Derived per-stage sizes; stage 0 is the outer leg.
    stage_dims_xy: tuple[tuple[float, float], ...]  # (x, y) per stage
    stage_length: float  # length along Z of each inner stage tube
    primary_leg_index: int
    leg_x_positions: tuple[float, ...]
    name: str


# ---------------------------------------------------------------------------
# Seed-based config sampler
# ---------------------------------------------------------------------------


def config_from_seed(seed: int) -> StandingDeskConfig:
    rng = random.Random(seed)
    leg_count = rng.choices((2, 3), weights=(0.65, 0.35), k=1)[0]
    stage_count_per_leg = rng.choices((2, 3), weights=(0.60, 0.40), k=1)[0]
    desktop_shape: DesktopShape = rng.choices(
        ("rectangle", "rounded", "L_shape"), weights=(0.55, 0.30, 0.15), k=1
    )[0]
    desktop_size: DesktopSize = rng.choices(
        ("small", "medium", "large"), weights=(0.30, 0.45, 0.25), k=1
    )[0]
    leg_cross_section: LegCrossSection = rng.choices(
        ("rectangular", "round", "oval"), weights=(0.55, 0.30, 0.15), k=1
    )[0]
    crossbar_style: CrossbarStyle = rng.choices(
        ("front", "rear", "double", "integrated_into_desktop_apron"),
        weights=(0.30, 0.25, 0.15, 0.30),
        k=1,
    )[0]
    foot_style: FootStyle = rng.choices(
        ("T_foot", "rectangular", "wide"), weights=(0.45, 0.30, 0.25), k=1
    )[0]
    control_panel_position: ControlPanelPosition = rng.choices(
        ("left", "right", "center", "front_underside"),
        weights=(0.25, 0.30, 0.20, 0.25),
        k=1,
    )[0]
    button_count = rng.choices((2, 4, 6), weights=(0.30, 0.45, 0.25), k=1)[0]
    material_style: MaterialStyle = rng.choices(
        ("wood_metal", "black", "white"), weights=(0.45, 0.30, 0.25), k=1
    )[0]

    length_range, width_range = DESKTOP_SIZE_RANGES[desktop_size]
    desktop_length = round(rng.uniform(*length_range), 3)
    desktop_width = round(rng.uniform(*width_range), 3)
    outer_leg_x = round(rng.uniform(*OUTER_LEG_X_RANGE), 3)
    outer_leg_y = round(rng.uniform(*OUTER_LEG_Y_RANGE), 3)
    outer_leg_height = round(rng.uniform(*OUTER_LEG_HEIGHT_RANGE), 3)
    single_stage_travel = round(rng.uniform(*SINGLE_STAGE_TRAVEL_RANGE), 3)

    return StandingDeskConfig(
        leg_count=leg_count,
        stage_count_per_leg=stage_count_per_leg,
        desktop_shape=desktop_shape,
        desktop_size=desktop_size,
        leg_cross_section=leg_cross_section,
        crossbar_style=crossbar_style,
        foot_style=foot_style,
        control_panel_position=control_panel_position,
        button_count=button_count,
        material_style=material_style,
        desktop_length=desktop_length,
        desktop_width=desktop_width,
        outer_leg_x=outer_leg_x,
        outer_leg_y=outer_leg_y,
        outer_leg_height=outer_leg_height,
        single_stage_travel=single_stage_travel,
        name=f"seeded_standing_desk_{seed}",
    )


# ---------------------------------------------------------------------------
# resolve_config: derive per-stage sizes, leg layout, primary index.
# ---------------------------------------------------------------------------


def resolve_config(config: StandingDeskConfig) -> ResolvedStandingDeskConfig:
    if config.leg_count not in {2, 3}:
        raise ValueError(f"leg_count must be in {{2, 3}}, got {config.leg_count}")
    if config.stage_count_per_leg not in {2, 3}:
        raise ValueError(
            f"stage_count_per_leg must be in {{2, 3}}, got {config.stage_count_per_leg}"
        )
    if config.desktop_shape not in {"rectangle", "rounded", "L_shape"}:
        raise ValueError(f"Unsupported desktop_shape: {config.desktop_shape}")
    if config.desktop_size not in DESKTOP_SIZE_RANGES:
        raise ValueError(f"Unsupported desktop_size: {config.desktop_size}")
    if config.leg_cross_section not in {"rectangular", "round", "oval"}:
        raise ValueError(f"Unsupported leg_cross_section: {config.leg_cross_section}")
    if config.crossbar_style not in {
        "front",
        "rear",
        "double",
        "integrated_into_desktop_apron",
    }:
        raise ValueError(f"Unsupported crossbar_style: {config.crossbar_style}")
    if config.foot_style not in {"T_foot", "rectangular", "wide"}:
        raise ValueError(f"Unsupported foot_style: {config.foot_style}")
    if config.control_panel_position not in {"left", "right", "center", "front_underside"}:
        raise ValueError(f"Unsupported control_panel_position: {config.control_panel_position}")
    if config.button_count not in {2, 4, 6}:
        raise ValueError(f"button_count must be in {{2, 4, 6}}, got {config.button_count}")
    if config.material_style not in MATERIAL_PALETTES:
        raise ValueError(f"Unsupported material_style: {config.material_style}")

    length_range, width_range = DESKTOP_SIZE_RANGES[config.desktop_size]
    if config.desktop_length is None:
        desktop_length = (length_range[0] + length_range[1]) * 0.5
    else:
        desktop_length = float(config.desktop_length)
        if not (length_range[0] - 1e-6 <= desktop_length <= length_range[1] + 1e-6):
            raise ValueError(
                f"desktop_length {desktop_length} outside bucket {config.desktop_size} "
                f"range {length_range}"
            )
    if config.desktop_width is None:
        desktop_width = (width_range[0] + width_range[1]) * 0.5
    else:
        desktop_width = float(config.desktop_width)
        if not (width_range[0] - 1e-6 <= desktop_width <= width_range[1] + 1e-6):
            raise ValueError(
                f"desktop_width {desktop_width} outside bucket {config.desktop_size} "
                f"range {width_range}"
            )

    outer_leg_x = (
        float(config.outer_leg_x)
        if config.outer_leg_x is not None
        else (OUTER_LEG_X_RANGE[0] + OUTER_LEG_X_RANGE[1]) * 0.5
    )
    outer_leg_y = (
        float(config.outer_leg_y)
        if config.outer_leg_y is not None
        else (OUTER_LEG_Y_RANGE[0] + OUTER_LEG_Y_RANGE[1]) * 0.5
    )
    outer_leg_height = (
        float(config.outer_leg_height)
        if config.outer_leg_height is not None
        else (OUTER_LEG_HEIGHT_RANGE[0] + OUTER_LEG_HEIGHT_RANGE[1]) * 0.5
    )
    single_stage_travel = (
        float(config.single_stage_travel)
        if config.single_stage_travel is not None
        else (SINGLE_STAGE_TRAVEL_RANGE[0] + SINGLE_STAGE_TRAVEL_RANGE[1]) * 0.5
    )

    # Per-stage XY dims.  Stage 0 = outer leg; each successive stage shrinks.
    stage_dims_xy_list: list[tuple[float, float]] = [(outer_leg_x, outer_leg_y)]
    for _i in range(1, config.stage_count_per_leg):
        prev_x, prev_y = stage_dims_xy_list[-1]
        new_x = prev_x * STAGE_SHRINK
        new_y = prev_y * STAGE_SHRINK
        if new_x < 0.020 or new_y < 0.020:
            raise ValueError(
                f"derived stage {_i} too narrow ({new_x:.3f}, {new_y:.3f}); increase outer_leg_x/y."
            )
        stage_dims_xy_list.append((new_x, new_y))

    # Each inner stage tube spans the full outer leg height (less a small
    # margin) so it can extend up while keeping retained insertion.
    stage_length = outer_leg_height * STAGE_LENGTH_FACTOR

    # Layout the legs along world +X around the desktop centre.
    # Use a generous inset so feet fit under the desktop comfortably.
    leg_inset = max(0.16, min(outer_leg_x, outer_leg_y) * 1.4)
    half_span = desktop_length * 0.5 - leg_inset
    if half_span < 0.15:
        # Too small a desk; clamp.
        half_span = 0.15
    if config.leg_count == 2:
        leg_x_positions = (-half_span, half_span)
        primary_leg_index = 0
    else:
        leg_x_positions = (-half_span, 0.0, half_span)
        primary_leg_index = 1  # centre leg

    return ResolvedStandingDeskConfig(
        leg_count=config.leg_count,
        stage_count_per_leg=config.stage_count_per_leg,
        desktop_shape=config.desktop_shape,
        desktop_size=config.desktop_size,
        leg_cross_section=config.leg_cross_section,
        crossbar_style=config.crossbar_style,
        foot_style=config.foot_style,
        control_panel_position=config.control_panel_position,
        button_count=config.button_count,
        material_style=config.material_style,
        desktop_length=desktop_length,
        desktop_width=desktop_width,
        outer_leg_x=outer_leg_x,
        outer_leg_y=outer_leg_y,
        outer_leg_height=outer_leg_height,
        single_stage_travel=single_stage_travel,
        stage_dims_xy=tuple(stage_dims_xy_list),
        stage_length=stage_length,
        primary_leg_index=primary_leg_index,
        leg_x_positions=tuple(leg_x_positions),
        name=config.name,
    )


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _build_leg_stage_visual(
    part,
    *,
    cross_section: LegCrossSection,
    dim_x: float,
    dim_y: float,
    length_z: float,
    z_centre: float,
    material,
    prefix: str,
) -> None:
    """Authoring helper: add the stage tube visual along local +Z.

    The visual is centred at ``z_centre`` and spans ``length_z`` along world Z.
    Cross-section dictates whether the visual is a Box, Cylinder, or Box+Box
    (oval ~ scaled cylinder, approximated as a wider Box for stability).
    """
    if cross_section == "rectangular":
        part.visual(
            Box((dim_x, dim_y, length_z)),
            origin=Origin(xyz=(0.0, 0.0, z_centre)),
            material=material,
            name=f"{prefix}_tube",
        )
    elif cross_section == "round":
        radius = min(dim_x, dim_y) * 0.5
        part.visual(
            Cylinder(radius=radius, length=length_z),
            origin=Origin(xyz=(0.0, 0.0, z_centre)),
            material=material,
            name=f"{prefix}_tube",
        )
    else:  # oval - approximate via a chamfered Box (visual-only).
        part.visual(
            Box((dim_x * 1.05, dim_y * 0.85, length_z)),
            origin=Origin(xyz=(0.0, 0.0, z_centre)),
            material=material,
            name=f"{prefix}_tube",
        )
        # Small accent caps to read more like an oval cap.
        for sx, label in ((-1, "left"), (1, "right")):
            part.visual(
                Cylinder(radius=dim_y * 0.45, length=0.012),
                origin=Origin(
                    xyz=(sx * dim_x * 0.45, 0.0, z_centre + length_z * 0.5 - 0.008),
                    rpy=(math.pi / 2.0, 0.0, 0.0),
                ),
                material=material,
                name=f"{prefix}_oval_cap_{label}",
            )


def _add_foot_visual(
    base,
    *,
    x_position: float,
    foot_style: FootStyle,
    desktop_width: float,
    material,
    accent_material,
    index: int,
) -> None:
    """Foot pad / foot bar visual attached to the base part below a leg."""
    z_centre = BASE_PLATE_THICKNESS * 0.5
    if foot_style == "T_foot":
        # Wide bar across Y plus a small platform under the leg.
        base.visual(
            Box((0.16, desktop_width * 0.78, BASE_PLATE_THICKNESS)),
            origin=Origin(xyz=(x_position, 0.0, z_centre)),
            material=material,
            name=f"foot_{index}_bar",
        )
        base.visual(
            Box((0.12, 0.12, BASE_PLATE_THICKNESS + 0.006)),
            origin=Origin(xyz=(x_position, 0.0, z_centre + 0.003)),
            material=accent_material,
            name=f"foot_{index}_pad",
        )
    elif foot_style == "rectangular":
        # Thin rectangular slab.
        base.visual(
            Box((0.20, desktop_width * 0.55, BASE_PLATE_THICKNESS)),
            origin=Origin(xyz=(x_position, 0.0, z_centre)),
            material=material,
            name=f"foot_{index}_slab",
        )
        for sy, label in ((-1, "rear"), (1, "front")):
            base.visual(
                Cylinder(radius=0.012, length=0.010),
                origin=Origin(
                    xyz=(x_position, sy * desktop_width * 0.22, BASE_PLATE_THICKNESS),
                ),
                material=accent_material,
                name=f"foot_{index}_glide_{label}",
            )
    else:  # wide
        base.visual(
            Box((0.30, desktop_width * 0.85, BASE_PLATE_THICKNESS)),
            origin=Origin(xyz=(x_position, 0.0, z_centre)),
            material=material,
            name=f"foot_{index}_wide",
        )
        base.visual(
            Box((0.30, 0.05, BASE_PLATE_THICKNESS + 0.005)),
            origin=Origin(xyz=(x_position, 0.0, z_centre + 0.004)),
            material=accent_material,
            name=f"foot_{index}_strap",
        )


def _add_desktop_visuals(
    desktop,
    resolved: ResolvedStandingDeskConfig,
    *,
    top_material,
    accent_material,
) -> None:
    """Author the desktop visuals based on shape.  Desktop is FIXED to the
    primary leg's innermost stage; its local origin is on the desktop top
    centre with z-zero at the desktop underside.
    """
    L = resolved.desktop_length
    W = resolved.desktop_width
    top_thickness = DESKTOP_THICKNESS

    if resolved.desktop_shape == "rectangle":
        desktop.visual(
            Box((L, W, top_thickness)),
            origin=Origin(xyz=(0.0, 0.0, top_thickness * 0.5)),
            material=top_material,
            name="top",
        )
    elif resolved.desktop_shape == "rounded":
        # Main top slightly inset on length, plus rounded end caps (cylinders).
        inner_L = L * 0.86
        desktop.visual(
            Box((inner_L, W, top_thickness)),
            origin=Origin(xyz=(0.0, 0.0, top_thickness * 0.5)),
            material=top_material,
            name="top",
        )
        # Rounded ends.
        cap_radius = W * 0.5
        cap_x = inner_L * 0.5
        desktop.visual(
            Cylinder(radius=cap_radius, length=top_thickness),
            origin=Origin(xyz=(cap_x, 0.0, top_thickness * 0.5)),
            material=top_material,
            name="top_cap_right",
        )
        desktop.visual(
            Cylinder(radius=cap_radius, length=top_thickness),
            origin=Origin(xyz=(-cap_x, 0.0, top_thickness * 0.5)),
            material=top_material,
            name="top_cap_left",
        )
    else:  # L_shape
        # Main board along +X, plus a wing along -Y at one end.
        main_L = L * 0.80
        wing_L = L * 0.40
        wing_W = W * 0.60
        desktop.visual(
            Box((main_L, W, top_thickness)),
            origin=Origin(xyz=(0.0, 0.0, top_thickness * 0.5)),
            material=top_material,
            name="top",
        )
        # Wing extends along -Y attached to the right (+X) end of main.
        desktop.visual(
            Box((wing_L, wing_W, top_thickness)),
            origin=Origin(
                xyz=(
                    main_L * 0.5 - wing_L * 0.5,
                    -W * 0.5 - wing_W * 0.5,
                    top_thickness * 0.5,
                ),
            ),
            material=top_material,
            name="top_wing",
        )

    # Aprons / cable strip under the desktop.  These are visuals on the
    # desktop, never separate parts.
    desktop.visual(
        Box((L * 0.92, 0.04, 0.045)),
        origin=Origin(xyz=(0.0, W * 0.42, -0.023)),
        material=accent_material,
        name="rear_apron",
    )
    desktop.visual(
        Box((L * 0.92, 0.04, 0.045)),
        origin=Origin(xyz=(0.0, -W * 0.42, -0.023)),
        material=accent_material,
        name="front_apron",
    )

    if resolved.crossbar_style == "integrated_into_desktop_apron":
        # The crossbar is added as a hidden beam visual on the desktop
        # underside, spanning between leg positions.
        if resolved.leg_count >= 2:
            span_left = resolved.leg_x_positions[0]
            span_right = resolved.leg_x_positions[-1]
            cb_length = (span_right - span_left) * 0.96
            desktop.visual(
                Box((cb_length, 0.05, 0.05)),
                origin=Origin(
                    xyz=((span_left + span_right) * 0.5, 0.0, -0.028),
                ),
                material=accent_material,
                name="integrated_crossbar",
            )


def _add_control_panel_visuals(panel, *, material, accent_material, panel_size_xy) -> None:
    """The control panel is a flat housing under the desktop."""
    px, py = panel_size_xy
    panel.visual(
        Box((px, py, 0.022)),
        origin=Origin(xyz=(0.0, 0.0, -0.011)),
        material=material,
        name="body",
    )
    panel.visual(
        Box((px * 0.94, py * 0.78, 0.006)),
        origin=Origin(xyz=(0.0, 0.0, -0.025)),
        material=accent_material,
        name="bezel",
    )


# ---------------------------------------------------------------------------
# Crossbar geometry helper for separate-part crossbars.
# ---------------------------------------------------------------------------


def _add_crossbar_visual(
    crossbar_part,
    *,
    style: CrossbarStyle,
    leg_x_positions: tuple[float, ...],
    desktop_width: float,
    desktop_thickness: float,
    z_offset_from_desktop: float,
    material,
) -> None:
    """Author the crossbar visuals.  ``z_offset_from_desktop`` is the local Z
    coordinate at which the bar sits below the desktop underside (typically
    a small negative value).  The crossbar part frame is at the desktop
    underside-centre and moves with the desktop.
    """
    span_left = leg_x_positions[0]
    span_right = leg_x_positions[-1]
    length = (span_right - span_left) * 0.94
    bar_y_front = -desktop_width * 0.30
    bar_y_rear = desktop_width * 0.30

    if style == "front":
        crossbar_part.visual(
            Box((length, 0.045, 0.045)),
            origin=Origin(xyz=((span_left + span_right) * 0.5, bar_y_front, z_offset_from_desktop)),
            material=material,
            name="front_bar",
        )
    elif style == "rear":
        crossbar_part.visual(
            Box((length, 0.045, 0.045)),
            origin=Origin(xyz=((span_left + span_right) * 0.5, bar_y_rear, z_offset_from_desktop)),
            material=material,
            name="rear_bar",
        )
    else:  # double
        crossbar_part.visual(
            Box((length, 0.040, 0.040)),
            origin=Origin(xyz=((span_left + span_right) * 0.5, bar_y_front, z_offset_from_desktop)),
            material=material,
            name="front_bar",
        )
        crossbar_part.visual(
            Box((length, 0.040, 0.040)),
            origin=Origin(xyz=((span_left + span_right) * 0.5, bar_y_rear, z_offset_from_desktop)),
            material=material,
            name="rear_bar",
        )


# ---------------------------------------------------------------------------
# Main builder
# ---------------------------------------------------------------------------


def _leg_name(leg_index: int) -> str:
    return f"leg_{leg_index}"


def _stage_part_name(leg_index: int, stage_index: int) -> str:
    """Stage index 0 is the outer leg sleeve; higher indices are inner stages."""
    if stage_index == 0:
        return f"leg_{leg_index}_outer"
    return f"leg_{leg_index}_stage_{stage_index}"


def _stage_joint_name(leg_index: int, stage_index: int) -> str:
    """Joint that drives stage_index relative to (stage_index - 1).

    Indices: stage_index >= 1.  This is the prismatic joint name.
    """
    return f"leg_{leg_index}_lift_joint_{stage_index}"


def build_standing_desk(
    config: StandingDeskConfig | None = None, *, assets: AssetContext | None = None
) -> ArticulatedObject:
    config = config or StandingDeskConfig()
    resolved = resolve_config(config)
    if assets is None:
        assets = AssetContext(Path(tempfile.mkdtemp(prefix="articraft-standing-desk-assets-")))
    model = ArticulatedObject(name=resolved.name, assets=assets)

    palette = MATERIAL_PALETTES[resolved.material_style]
    outer_leg_mat = model.material(
        f"desk_outer_leg_{resolved.material_style}", rgba=palette["outer_leg"]
    )
    inner_leg_mat = model.material(
        f"desk_inner_leg_{resolved.material_style}", rgba=palette["inner_leg"]
    )
    accent_mat = model.material(f"desk_accent_{resolved.material_style}", rgba=palette["accent"])
    top_mat = model.material(f"desk_top_{resolved.material_style}", rgba=palette["desktop_top"])
    panel_mat = model.material(f"desk_panel_{resolved.material_style}", rgba=palette["panel"])
    button_mat = model.material(f"desk_button_{resolved.material_style}", rgba=palette["button"])

    # ----- base + feet -----
    base = model.part("base")
    for i, x_pos in enumerate(resolved.leg_x_positions):
        _add_foot_visual(
            base,
            x_position=x_pos,
            foot_style=resolved.foot_style,
            desktop_width=resolved.desktop_width,
            material=outer_leg_mat,
            accent_material=accent_mat,
            index=i,
        )

    # ----- legs (per leg: an outer part + inner stage parts) -----
    # For each leg create the outer part FIXED to base at its x_position.  Then
    # create stage_count_per_leg - 1 inner stages, each PRISMATIC to its
    # parent stage.  Same-leg downstream stages Mimic to that leg's first
    # stage joint; non-primary legs' first-stage joints Mimic to the primary
    # leg's first-stage joint.
    stage_count = resolved.stage_count_per_leg
    primary_idx = resolved.primary_leg_index
    primary_first_joint_name = _stage_joint_name(primary_idx, 1)

    # Limits: same for every leg.
    lift_limits = MotionLimits(
        effort=900.0,
        velocity=0.05,
        lower=0.0,
        upper=resolved.single_stage_travel,
    )

    # Build leg parts and stage articulations.
    leg_outer_parts: dict[int, object] = {}
    leg_top_parts: dict[int, object] = {}  # innermost stage part (where desktop attaches)
    for leg_index, x_pos in enumerate(resolved.leg_x_positions):
        # Outer leg part.
        outer_part = model.part(_stage_part_name(leg_index, 0))
        leg_outer_parts[leg_index] = outer_part
        outer_x, outer_y = resolved.stage_dims_xy[0]
        # Visual is centred along +Z from z=0 (outer leg origin is at the
        # base-plate top) up to z=outer_leg_height.
        _build_leg_stage_visual(
            outer_part,
            cross_section=resolved.leg_cross_section,
            dim_x=outer_x,
            dim_y=outer_y,
            length_z=resolved.outer_leg_height,
            z_centre=resolved.outer_leg_height * 0.5,
            material=outer_leg_mat,
            prefix=f"leg_{leg_index}_outer",
        )

        # FIXED articulation: base -> outer leg.  Place at the base plate top.
        model.articulation(
            f"base_to_leg_{leg_index}_outer",
            ArticulationType.FIXED,
            parent=base,
            child=outer_part,
            origin=Origin(xyz=(x_pos, 0.0, BASE_PLATE_THICKNESS)),
        )

        # Inner stages.
        prev_part = outer_part
        for stage_index in range(1, stage_count):
            stage_part = model.part(_stage_part_name(leg_index, stage_index))
            stage_x, stage_y = resolved.stage_dims_xy[stage_index]
            # The stage visual is anchored so its CENTRE is at z = -stage_length/2.
            # Choosing a negative z origin means: when the joint is at q=0,
            # the inner stage's top sits at the joint origin (z=0 in the
            # joint frame, which equals z=outer_leg_height in the parent
            # part frame).  Increasing q moves the inner stage upward,
            # carrying its visual upward and keeping the bottom retained
            # inside the parent stage.
            _build_leg_stage_visual(
                stage_part,
                cross_section=resolved.leg_cross_section,
                dim_x=stage_x,
                dim_y=stage_y,
                length_z=resolved.stage_length,
                z_centre=-resolved.stage_length * 0.5,
                material=inner_leg_mat,
                prefix=f"leg_{leg_index}_stage_{stage_index}",
            )

            # Joint origin: at the top of the previous stage.  For the first
            # inner stage, that's at z=outer_leg_height in the outer-leg
            # part frame.  For subsequent stages, it's at z=0 in the
            # previous (inner) stage part frame, which itself is at the
            # parent's top - this means we place subsequent joint origins
            # at z=0 (the previous stage's top edge is at z=0 by the
            # negative-centre convention).
            if stage_index == 1:
                joint_origin_z = resolved.outer_leg_height
            else:
                joint_origin_z = 0.0

            # Determine mimic.  The first inner stage of non-primary legs
            # mimics the primary leg's first joint.  Same-leg downstream
            # stages mimic that leg's own first joint.
            mimic: Mimic | None = None
            if stage_index == 1:
                if leg_index != primary_idx:
                    mimic = Mimic(joint=primary_first_joint_name, multiplier=1.0, offset=0.0)
            else:
                # Downstream stage on the same leg.
                mimic = Mimic(
                    joint=_stage_joint_name(leg_index, 1),
                    multiplier=1.0,
                    offset=0.0,
                )

            model.articulation(
                _stage_joint_name(leg_index, stage_index),
                ArticulationType.PRISMATIC,
                parent=prev_part,
                child=stage_part,
                origin=Origin(xyz=(0.0, 0.0, joint_origin_z)),
                axis=(0.0, 0.0, 1.0),
                motion_limits=lift_limits,
                mimic=mimic,
            )
            prev_part = stage_part

        leg_top_parts[leg_index] = prev_part

    # ----- desktop -----
    desktop = model.part("desktop")
    _add_desktop_visuals(
        desktop,
        resolved,
        top_material=top_mat,
        accent_material=accent_mat,
    )
    # FIXED to the primary leg's innermost (top) stage.  The desktop's local
    # origin is on the desktop underside; the primary stage's "top" in its
    # local frame is at z=0 (by the negative-centre convention).  So
    # place desktop origin at z=0 in the primary stage frame.
    model.articulation(
        "primary_stage_to_desktop",
        ArticulationType.FIXED,
        parent=leg_top_parts[primary_idx],
        child=desktop,
        origin=Origin(xyz=(-resolved.leg_x_positions[primary_idx], 0.0, 0.0)),
    )

    # ----- crossbar (separate part for non-integrated styles) -----
    if resolved.crossbar_style != "integrated_into_desktop_apron" and resolved.leg_count >= 2:
        crossbar = model.part("crossbar")
        _add_crossbar_visual(
            crossbar,
            style=resolved.crossbar_style,
            leg_x_positions=resolved.leg_x_positions,
            desktop_width=resolved.desktop_width,
            desktop_thickness=DESKTOP_THICKNESS,
            z_offset_from_desktop=-0.06,
            material=accent_mat,
        )
        # FIXED to the desktop so the crossbar travels in sync.
        model.articulation(
            "desktop_to_crossbar",
            ArticulationType.FIXED,
            parent=desktop,
            child=crossbar,
            origin=Origin(xyz=(0.0, 0.0, 0.0)),
        )

    # ----- control panel + buttons -----
    panel = model.part("control_panel")
    panel_size = (max(0.14, 0.022 * resolved.button_count + 0.10), 0.08)
    _add_control_panel_visuals(
        panel,
        material=panel_mat,
        accent_material=accent_mat,
        panel_size_xy=panel_size,
    )

    # Determine panel mounting xyz relative to desktop underside.
    # Desktop underside is at z=0 (in desktop part frame), since top centre is
    # at z=top_thickness/2 with origin at underside.
    panel_y_front = -resolved.desktop_width * 0.42 + panel_size[1] * 0.5 + 0.005
    if resolved.control_panel_position == "left":
        panel_xy = (-resolved.desktop_length * 0.35, panel_y_front)
    elif resolved.control_panel_position == "right":
        panel_xy = (resolved.desktop_length * 0.35, panel_y_front)
    elif resolved.control_panel_position == "center":
        panel_xy = (0.0, panel_y_front)
    else:  # front_underside - centred but further forward
        panel_xy = (0.0, -resolved.desktop_width * 0.42 + panel_size[1] * 0.5)

    model.articulation(
        "desktop_to_control_panel",
        ArticulationType.FIXED,
        parent=desktop,
        child=panel,
        origin=Origin(xyz=(panel_xy[0], panel_xy[1], -0.005)),
    )

    # Buttons: equally spaced along panel local +X, prismatic into panel
    # along the panel local -Z axis (so positive q presses into panel).
    button_travel = 0.005
    if resolved.button_count == 2:
        button_xs = (-panel_size[0] * 0.22, panel_size[0] * 0.22)
    elif resolved.button_count == 4:
        button_xs = (
            -panel_size[0] * 0.30,
            -panel_size[0] * 0.10,
            panel_size[0] * 0.10,
            panel_size[0] * 0.30,
        )
    else:  # 6
        button_xs = (
            -panel_size[0] * 0.36,
            -panel_size[0] * 0.22,
            -panel_size[0] * 0.08,
            panel_size[0] * 0.08,
            panel_size[0] * 0.22,
            panel_size[0] * 0.36,
        )

    for i, bx in enumerate(button_xs):
        button = model.part(f"button_{i}")
        button.visual(
            Box((0.022, 0.022, 0.010)),
            origin=Origin(xyz=(0.0, 0.0, -0.005)),
            material=button_mat,
            name="cap",
        )
        model.articulation(
            f"button_joint_{i}",
            ArticulationType.PRISMATIC,
            parent=panel,
            child=button,
            origin=Origin(xyz=(bx, 0.0, -0.028)),
            # Press into the panel: panel underside is at -0.028; pressing
            # *up* (+Z) buries the button into the panel face.
            axis=(0.0, 0.0, 1.0),
            motion_limits=MotionLimits(
                effort=4.0,
                velocity=0.05,
                lower=0.0,
                upper=button_travel,
            ),
        )

    return model


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------


def run_standing_desk_tests(
    object_model: ArticulatedObject, config: StandingDeskConfig
) -> TestReport:
    resolved = resolve_config(config)
    ctx = TestContext(object_model)

    base = object_model.get_part("base")
    desktop = object_model.get_part("desktop")
    panel = object_model.get_part("control_panel")

    primary_idx = resolved.primary_leg_index
    stage_count = resolved.stage_count_per_leg

    # Allow nested-proxy overlap for every (parent_stage, child_stage) pair on
    # every leg.  These are intentional sleeve-in-sleeve representations.
    for leg_index in range(resolved.leg_count):
        for stage_index in range(stage_count - 1):
            parent_part = object_model.get_part(_stage_part_name(leg_index, stage_index))
            child_part = object_model.get_part(_stage_part_name(leg_index, stage_index + 1))
            ctx.allow_overlap(
                parent_part,
                child_part,
                reason=(
                    "Inner telescoping stage is intentionally represented as sliding "
                    "inside the parent stage proxy."
                ),
            )

    # Allow desktop to overlap with control panel mount and with crossbar
    # part (visuals share the desktop underside region).
    if resolved.crossbar_style != "integrated_into_desktop_apron":
        try:
            crossbar = object_model.get_part("crossbar")
            ctx.allow_overlap(
                desktop,
                crossbar,
                reason="Crossbar visuals hang below the desktop apron and may touch.",
            )
        except Exception:
            crossbar = None

    # Allow button -> panel overlap (button cap sits flush against the panel).
    for i in range(resolved.button_count):
        button = object_model.get_part(f"button_{i}")
        ctx.allow_overlap(
            panel,
            button,
            reason="Button cap retracts into the panel proxy when pressed.",
        )

    # --- 1. At least one prismatic lift joint and at least one button joint.
    prismatic_joints = [
        j for j in object_model.articulations if j.articulation_type == ArticulationType.PRISMATIC
    ]
    lift_joints = [j for j in prismatic_joints if "lift_joint" in j.name]
    button_joints = [j for j in prismatic_joints if j.name.startswith("button_joint_")]
    ctx.check(
        "at_least_one_prismatic_lift_joint",
        len(lift_joints) >= 1,
        details=f"lift_joints={[j.name for j in lift_joints]}",
    )
    expected_lift_joint_count = resolved.leg_count * (stage_count - 1)
    ctx.check(
        "lift_joint_count_matches_legs_times_stages_minus_one",
        len(lift_joints) == expected_lift_joint_count,
        details=(
            f"got {len(lift_joints)}, expected "
            f"{resolved.leg_count}*({stage_count}-1)={expected_lift_joint_count}"
        ),
    )
    ctx.check(
        "button_joint_count_matches",
        len(button_joints) == resolved.button_count,
        details=f"got {len(button_joints)}, expected {resolved.button_count}",
    )

    # --- 2. Every lift joint has axis (0, 0, 1) and parallel.
    for j in lift_joints:
        ax = tuple(j.axis)
        ctx.check(
            f"{j.name}_axis_is_world_z",
            abs(ax[0]) < 1e-6 and abs(ax[1]) < 1e-6 and abs(ax[2] - 1.0) < 1e-6,
            details=f"axis={ax}",
        )

    # --- 3. Mimic chain: every non-primary first-stage joint mimics the primary
    #        first-stage joint.  Every downstream stage joint mimics its own
    #        leg's first-stage joint.  Both with multiplier=1.0, offset=0.0.
    primary_first_joint_name = _stage_joint_name(primary_idx, 1)
    for leg_index in range(resolved.leg_count):
        first_joint_name = _stage_joint_name(leg_index, 1)
        first_joint = object_model.get_articulation(first_joint_name)
        if leg_index == primary_idx:
            ctx.check(
                f"primary_leg_{leg_index}_first_joint_has_no_mimic",
                first_joint.mimic is None,
                details=f"mimic={first_joint.mimic}",
            )
        else:
            ctx.check(
                f"non_primary_leg_{leg_index}_first_joint_mimics_primary",
                first_joint.mimic is not None
                and first_joint.mimic.joint == primary_first_joint_name
                and abs(first_joint.mimic.multiplier - 1.0) < 1e-6
                and abs(first_joint.mimic.offset) < 1e-6,
                details=f"mimic={first_joint.mimic}",
            )
        # Downstream stages.
        for stage_index in range(2, stage_count):
            joint_name = _stage_joint_name(leg_index, stage_index)
            joint = object_model.get_articulation(joint_name)
            ctx.check(
                f"{joint_name}_mimics_same_leg_first_stage",
                joint.mimic is not None
                and joint.mimic.joint == first_joint_name
                and abs(joint.mimic.multiplier - 1.0) < 1e-6
                and abs(joint.mimic.offset) < 1e-6,
                details=f"mimic={joint.mimic}",
            )

    # --- 4. Desktop level: at rest the desktop top normal aligns with world +Z.
    #        Use AABB extents: the top thickness should be the smallest extent
    #        and the largest extents are the X/Y dimensions of the desktop.
    desktop_aabb = ctx.part_world_aabb(desktop)
    if desktop_aabb is not None:
        ex = desktop_aabb[1][0] - desktop_aabb[0][0]
        ey = desktop_aabb[1][1] - desktop_aabb[0][1]
        ez = desktop_aabb[1][2] - desktop_aabb[0][2]
        ctx.check(
            "desktop_thickness_along_z_is_smallest_extent",
            ez < ex and ez < ey,
            details=f"extents=({ex:.3f},{ey:.3f},{ez:.3f})",
        )

    # --- 5. Leg alignment: each leg outer is centred under its slot in X
    #        and the inner stages sit inside the outer leg footprint at rest.
    for leg_index in range(resolved.leg_count):
        outer = object_model.get_part(_stage_part_name(leg_index, 0))
        for stage_index in range(1, stage_count):
            inner = object_model.get_part(_stage_part_name(leg_index, stage_index))
            ctx.expect_within(
                inner,
                outer,
                axes="xy",
                inner_elem=f"leg_{leg_index}_stage_{stage_index}_tube",
                outer_elem=f"leg_{leg_index}_outer_tube",
                margin=0.010,
                name=f"leg_{leg_index}_stage_{stage_index}_centred_in_outer_at_rest",
            )

    # --- 6. Nesting: the outer leg AABB (yz extents) strictly contains every
    #        inner stage AABB.
    for leg_index in range(resolved.leg_count):
        outer = object_model.get_part(_stage_part_name(leg_index, 0))
        outer_aabb = ctx.part_world_aabb(outer)
        if outer_aabb is None:
            continue
        outer_x_extent = outer_aabb[1][0] - outer_aabb[0][0]
        outer_y_extent = outer_aabb[1][1] - outer_aabb[0][1]
        for stage_index in range(1, stage_count):
            inner = object_model.get_part(_stage_part_name(leg_index, stage_index))
            inner_aabb = ctx.part_world_aabb(inner)
            if inner_aabb is None:
                continue
            inner_x_extent = inner_aabb[1][0] - inner_aabb[0][0]
            inner_y_extent = inner_aabb[1][1] - inner_aabb[0][1]
            ctx.check(
                f"leg_{leg_index}_stage_{stage_index}_section_smaller_than_outer",
                inner_x_extent < outer_x_extent - 1e-4 and inner_y_extent < outer_y_extent - 1e-4,
                details=(
                    f"outer=({outer_x_extent:.3f},{outer_y_extent:.3f}); "
                    f"inner=({inner_x_extent:.3f},{inner_y_extent:.3f})"
                ),
            )

    # --- 7. Sync check: at full lift, all legs' tops and the desktop rise by
    #        the same amount (within 1 mm).
    primary_first_joint = object_model.get_articulation(primary_first_joint_name)
    upper = (
        primary_first_joint.motion_limits.upper
        if primary_first_joint.motion_limits is not None
        else 0.0
    )

    rest_positions: dict[str, tuple[float, float, float] | None] = {
        "desktop": ctx.part_world_position(desktop),
    }
    for leg_index in range(resolved.leg_count):
        top_part = object_model.get_part(_stage_part_name(leg_index, stage_count - 1))
        rest_positions[f"leg_{leg_index}_top"] = ctx.part_world_position(top_part)

    with ctx.pose({primary_first_joint: upper}):
        raised_positions: dict[str, tuple[float, float, float] | None] = {
            "desktop": ctx.part_world_position(desktop),
        }
        for leg_index in range(resolved.leg_count):
            top_part = object_model.get_part(_stage_part_name(leg_index, stage_count - 1))
            raised_positions[f"leg_{leg_index}_top"] = ctx.part_world_position(top_part)

    # Compute Z deltas across legs + desktop.
    deltas_z: list[float] = []
    for key in rest_positions:
        rest = rest_positions[key]
        raised = raised_positions[key]
        if rest is None or raised is None:
            ctx.fail(f"{key}_world_position_available", "position is None")
            continue
        deltas_z.append(raised[2] - rest[2])

    if deltas_z:
        ctx.check(
            "lift_actually_rises",
            min(deltas_z) > max(0.02, upper * 0.5),
            details=f"deltas_z={deltas_z}, upper={upper}",
        )
        ctx.check(
            "sync_check_max_minus_min_delta_z_under_1mm",
            max(deltas_z) - min(deltas_z) < 1e-3,
            details=f"deltas_z={deltas_z}",
        )

    # --- 8. Stability: foot footprint covers the desktop on each leg axis.
    #        Just sanity-check the base part exists and has visuals.
    ctx.check(
        "base_has_feet_visuals",
        any(v.name and v.name.startswith("foot_") for v in base.visuals),
        details=f"visuals={[v.name for v in base.visuals]}",
    )

    # --- 9. Control panel sits under the desktop (z is below the desktop top).
    panel_pos = ctx.part_world_position(panel)
    desktop_pos = ctx.part_world_position(desktop)
    if panel_pos is not None and desktop_pos is not None:
        ctx.check(
            "control_panel_below_desktop_top",
            panel_pos[2] < desktop_pos[2] + DESKTOP_THICKNESS * 0.5 + 1e-6,
            details=f"panel_z={panel_pos[2]}, desktop_z={desktop_pos[2]}",
        )

    # --- 10. Buttons attach to control panel (parent == panel name).
    for i in range(resolved.button_count):
        joint = object_model.get_articulation(f"button_joint_{i}")
        ctx.check(
            f"button_{i}_parented_to_control_panel",
            joint.parent == panel.name,
            details=f"parent={joint.parent}",
        )

    # --- 11. Identity: desktop has a 'top' visual; every leg has an outer
    #         tube; control panel has a 'body' visual.
    desktop_visual_names = {v.name for v in desktop.visuals if v.name is not None}
    ctx.check(
        "desktop_has_top_visual",
        "top" in desktop_visual_names,
        details=f"desktop_visuals={sorted(desktop_visual_names)}",
    )
    panel_visual_names = {v.name for v in panel.visuals if v.name is not None}
    ctx.check(
        "control_panel_has_body_visual",
        "body" in panel_visual_names,
        details=f"panel_visuals={sorted(panel_visual_names)}",
    )
    for leg_index in range(resolved.leg_count):
        outer = object_model.get_part(_stage_part_name(leg_index, 0))
        outer_visual_names = {v.name for v in outer.visuals if v.name is not None}
        ctx.check(
            f"leg_{leg_index}_has_outer_tube_visual",
            f"leg_{leg_index}_outer_tube" in outer_visual_names,
            details=f"visuals={sorted(outer_visual_names)}",
        )

    # --- 12. One button actually presses in: drive button_0 to upper limit.
    if resolved.button_count >= 1:
        button_0_joint = object_model.get_articulation("button_joint_0")
        button_upper = (
            button_0_joint.motion_limits.upper if button_0_joint.motion_limits is not None else 0.0
        )
        button_0 = object_model.get_part("button_0")
        rest_button_pos = ctx.part_world_position(button_0)
        with ctx.pose({button_0_joint: button_upper}):
            pressed_button_pos = ctx.part_world_position(button_0)
        if rest_button_pos is not None and pressed_button_pos is not None:
            travel_z = pressed_button_pos[2] - rest_button_pos[2]
            ctx.check(
                "button_0_translates_into_panel",
                abs(travel_z) > button_upper * 0.5,
                details=(
                    f"rest_z={rest_button_pos[2]:.4f}, pressed_z={pressed_button_pos[2]:.4f}, "
                    f"upper={button_upper}"
                ),
            )

    return ctx.report()


# ---------------------------------------------------------------------------
# Seeded entry point + override helper.
# ---------------------------------------------------------------------------


def build_seeded_standing_desk(
    seed: int, *, assets: AssetContext | None = None
) -> ArticulatedObject:
    return build_standing_desk(config_from_seed(seed), assets=assets)


def with_overrides(config: StandingDeskConfig, **kwargs: object) -> StandingDeskConfig:
    return replace(config, **kwargs)
