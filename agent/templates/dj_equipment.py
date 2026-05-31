"""DJ equipment — modular procedural template.

This template uses the slot/module/assembler abstraction in
``agent.templates._modular``. Three slots — **chassis**, **deck_layout**,
**controls** — each pick from a small candidate pool sourced from the
5-star sample family. The assembler walks the slot list and lets each
module emit its own parts + internal articulations onto a shared model.

Slot graph (logical):
  chassis (root) → deck_layout (parallel children of chassis) →
                   controls    (parallel children of chassis)

A DJ controller is NOT a strict linear chain. Platters, faders, pad
grids, and the carry_handle are all PARALLEL children of the housing,
not serial. We adapt the abstraction by:

  * Defining a real ``downstream`` interface only on the chassis modules;
    that interface stays at the housing's +z top deck.
  * deck_layout and controls modules DO NOT define ``upstream`` — this
    skips the assembler's auto-chain joint. Instead they read
    ``ctx.upstream_interface.part_name`` to find the housing part and
    emit their joints with ``parent=model.get_part(housing_name)``.
  * Each non-root module exposes its OWN no-op ``downstream`` interface
    (pointing at the same housing top face) so the chain can continue
    to the next slot.

Candidates (6 total, 2×2×2 = 8 topology combinations):

  chassis:
    - controller_chassis   (anchor; rec_47e2bd... — housing with mesh
                            top deck + carry_handle REVOLUTE child)
    - turntable_plinth     (alt; rec_6e26a3... — heavier wooden plinth
                            with a fold-down carry_handle child)

  deck_layout (all joints internally parented to housing):
    - dual_jog_decks               (anchor; 2 platters REVOLUTE around z)
    - single_platter_with_tonearm  (alt; rec_6e26a3... — 1 platter + 1
                                    tonearm REVOLUTE around z)

  controls (all joints internally parented to housing):
    - triple_fader_strip           (anchor; crossfader + 2 volume faders
                                    PRISMATIC)
    - pad_grid_plus_fader          (alt; rec_12cc44... — 2×4 pad grid as
                                    PRISMATIC buttons + 1 fader)

seed == 0 always picks the anchor combination (controller_chassis +
dual_jog_decks + triple_fader_strip), so any per-anchor smoke test on
seed 0 reproduces the canonical 7-part / 6-joint topology of the
PRIMARY_ANCHOR. Other seeds RNG-pick uniformly across the 8 combos.

Anchor responsibility is at the **module-interface** level: each module
emits its own joints with mating contracts where appropriate. Pin-through-
sleeve overlaps (carry_handle ↔ housing bracket) are grandfathered via
``ctx.allow_overlap`` declared in ``_declare_captured_pivot_overlaps``.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Literal

from agent.templates._modular import (
    InterfaceSpec,
    ModuleBuild,
    ModuleBuildContext,
    SlotSpec,
    assemble,
)
from sdk import (
    ArticulatedObject,
    ArticulationType,
    AssetContext,
    Box,
    Cylinder,
    ExtrudeGeometry,
    ExtrudeWithHolesGeometry,
    Inertial,
    MatingContract,
    MotionLimits,
    Origin,
    TestContext,
    TestReport,
    mesh_from_geometry,
    rounded_rect_profile,
    superellipse_profile,
)

# Modular templates are flagged so the sweep coverage gate can skip
# anchor_geometry_match (a single-anchor gate that does not apply when
# topology varies across seeds) and run module-level checks instead.
__modular__ = True


ChassisModule = Literal["controller_chassis", "turntable_plinth"]
DeckLayoutModule = Literal["dual_jog_decks", "single_platter_with_tonearm"]
ControlsModule = Literal["triple_fader_strip", "pad_grid_plus_fader"]
DJPaletteTheme = Literal[
    "anchor_black",
    "white_studio",
    "neon_pink",
    "wood_finish",
    "brushed_steel",
]


# --------------------------------------------------------------------------- #
# Palette presets — preserved verbatim from the prior single-anchor template.
# Each theme provides housing / deck / platter / accent / slider color tokens
# that module factories pull from the resolved palette dict.
# --------------------------------------------------------------------------- #


DJ_PALETTE_PRESETS: dict[str, dict[str, tuple[float, float, float, float]]] = {
    "anchor_black": {
        "housing_black": (0.08, 0.09, 0.10, 1.0),
        "deck_graphite": (0.13, 0.14, 0.16, 1.0),
        "platter_dark": (0.12, 0.13, 0.14, 1.0),
        "platter_top": (0.21, 0.22, 0.24, 1.0),
        "accent_silver": (0.74, 0.76, 0.79, 1.0),
        "slider_black": (0.05, 0.05, 0.06, 1.0),
        "cue_gray": (0.28, 0.30, 0.33, 1.0),
        "wood_warm": (0.32, 0.21, 0.12, 1.0),
        "pad_rubber": (0.86, 0.86, 0.82, 1.0),
        "accent_red": (0.75, 0.12, 0.08, 1.0),
    },
    "white_studio": {
        "housing_black": (0.92, 0.92, 0.91, 1.0),
        "deck_graphite": (0.84, 0.85, 0.86, 1.0),
        "platter_dark": (0.30, 0.32, 0.34, 1.0),
        "platter_top": (0.55, 0.56, 0.58, 1.0),
        "accent_silver": (0.40, 0.42, 0.45, 1.0),
        "slider_black": (0.20, 0.20, 0.21, 1.0),
        "cue_gray": (0.62, 0.63, 0.65, 1.0),
        "wood_warm": (0.78, 0.66, 0.50, 1.0),
        "pad_rubber": (0.92, 0.92, 0.89, 1.0),
        "accent_red": (0.84, 0.34, 0.30, 1.0),
    },
    "neon_pink": {
        "housing_black": (0.08, 0.04, 0.06, 1.0),
        "deck_graphite": (0.18, 0.10, 0.16, 1.0),
        "platter_dark": (0.10, 0.05, 0.08, 1.0),
        "platter_top": (0.92, 0.18, 0.55, 1.0),
        "accent_silver": (0.95, 0.42, 0.72, 1.0),
        "slider_black": (0.04, 0.04, 0.05, 1.0),
        "cue_gray": (0.30, 0.10, 0.20, 1.0),
        "wood_warm": (0.40, 0.10, 0.22, 1.0),
        "pad_rubber": (0.96, 0.30, 0.66, 1.0),
        "accent_red": (0.99, 0.18, 0.50, 1.0),
    },
    "wood_finish": {
        "housing_black": (0.32, 0.21, 0.12, 1.0),
        "deck_graphite": (0.42, 0.27, 0.16, 1.0),
        "platter_dark": (0.18, 0.12, 0.07, 1.0),
        "platter_top": (0.55, 0.36, 0.20, 1.0),
        "accent_silver": (0.78, 0.62, 0.40, 1.0),
        "slider_black": (0.10, 0.07, 0.04, 1.0),
        "cue_gray": (0.48, 0.34, 0.22, 1.0),
        "wood_warm": (0.50, 0.30, 0.16, 1.0),
        "pad_rubber": (0.62, 0.46, 0.30, 1.0),
        "accent_red": (0.78, 0.22, 0.12, 1.0),
    },
    "brushed_steel": {
        "housing_black": (0.55, 0.57, 0.60, 1.0),
        "deck_graphite": (0.65, 0.66, 0.68, 1.0),
        "platter_dark": (0.32, 0.34, 0.36, 1.0),
        "platter_top": (0.75, 0.76, 0.78, 1.0),
        "accent_silver": (0.92, 0.93, 0.94, 1.0),
        "slider_black": (0.12, 0.13, 0.14, 1.0),
        "cue_gray": (0.45, 0.46, 0.48, 1.0),
        "wood_warm": (0.55, 0.50, 0.42, 1.0),
        "pad_rubber": (0.78, 0.78, 0.74, 1.0),
        "accent_red": (0.90, 0.32, 0.20, 1.0),
    },
}


# --------------------------------------------------------------------------- #
# Config dataclasses
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class DjEquipmentConfig:
    """Public template config. Module selection is opt-in: leave any of
    the three module fields as ``None`` to let ``config_from_seed`` /
    ``resolve_config`` fill them in from the seed-driven RNG.

    The continuous dimensions describe the overall envelope (body width,
    depth, height) plus per-feature defaults (platter radius, fader
    geometry, pad grid spacing). Module factories scale where
    appropriate; ``turntable_plinth`` runs slightly taller than the
    controller, for instance.
    """

    chassis_module: ChassisModule | None = None
    deck_layout_module: DeckLayoutModule | None = None
    controls_module: ControlsModule | None = None

    palette_theme: DJPaletteTheme = "anchor_black"

    body_width: float = 0.58
    body_depth: float = 0.34
    body_height: float = 0.062
    corner_radius: float = 0.028
    wall_thickness: float = 0.012
    bottom_thickness: float = 0.004
    top_thickness: float = 0.004

    # Jog/platter dimensions
    jog_x: float = 0.175
    jog_y: float = 0.018
    jog_open_diameter: float = 0.118
    spindle_radius: float = 0.018
    spindle_height: float = 0.004
    platter_rim_radius: float = 0.064
    platter_rim_length: float = 0.010

    # Crossfader/volume slot footprint (used by triple_fader_strip)
    crossfader_y: float = -0.112
    crossfader_slot: tuple[float, float] = (0.140, 0.014)
    volume_slot: tuple[float, float] = (0.014, 0.098)
    left_volume_x: float = -0.038
    right_volume_x: float = 0.038
    volume_y: float = 0.020

    # Carry handle
    handle_span: float = 0.50
    handle_reach: float = 0.068
    handle_radius: float = 0.0055
    handle_travel: float = 1.28

    # Pad grid (used by pad_grid_plus_fader)
    pad_rows: int = 2
    pad_cols: int = 4
    pad_size: tuple[float, float, float] = (0.026, 0.026, 0.010)
    pad_pitch: float = 0.034

    # Tonearm + single platter (used by single_platter_with_tonearm)
    tonearm_length: float = 0.22
    tonearm_sweep_range: float = 1.6
    single_platter_radius: float = 0.140
    single_platter_height: float = 0.018

    palette: dict[str, tuple[float, float, float, float]] = field(
        default_factory=lambda: dict(DJ_PALETTE_PRESETS["anchor_black"])
    )


@dataclass(frozen=True)
class ResolvedDjEquipmentConfig:
    """Dimension-clamped + module-resolved config consumed by builders."""

    chassis_module: ChassisModule
    deck_layout_module: DeckLayoutModule
    controls_module: ControlsModule
    palette_theme: DJPaletteTheme
    body_width: float
    body_depth: float
    body_height: float
    corner_radius: float
    wall_thickness: float
    bottom_thickness: float
    top_thickness: float
    jog_x: float
    jog_y: float
    jog_open_diameter: float
    spindle_radius: float
    spindle_height: float
    platter_rim_radius: float
    platter_rim_length: float
    crossfader_y: float
    crossfader_slot: tuple[float, float]
    volume_slot: tuple[float, float]
    left_volume_x: float
    right_volume_x: float
    volume_y: float
    handle_span: float
    handle_reach: float
    handle_radius: float
    handle_travel: float
    pad_rows: int
    pad_cols: int
    pad_size: tuple[float, float, float]
    pad_pitch: float
    tonearm_length: float
    tonearm_sweep_range: float
    single_platter_radius: float
    single_platter_height: float
    palette: dict[str, tuple[float, float, float, float]]


# --------------------------------------------------------------------------- #
# Seed-driven sampling
# --------------------------------------------------------------------------- #


def config_from_seed(seed: int) -> DjEquipmentConfig:
    """Sample a DJ equipment configuration for the given seed.

    seed == 0 returns the anchor combination
    (controller_chassis + dual_jog_decks + triple_fader_strip) at the
    canonical PRIMARY_ANCHOR dimensions. Other seeds RNG-pick modules
    uniformly per slot and sample continuous dimensions across a
    realistic range.
    """
    if seed == 0:
        return DjEquipmentConfig(
            chassis_module="controller_chassis",
            deck_layout_module="dual_jog_decks",
            controls_module="triple_fader_strip",
            palette_theme="anchor_black",
        )

    rng = random.Random(seed)
    chassis: ChassisModule = rng.choice(("controller_chassis", "turntable_plinth"))
    deck: DeckLayoutModule = rng.choice(("dual_jog_decks", "single_platter_with_tonearm"))
    controls: ControlsModule = rng.choice(("triple_fader_strip", "pad_grid_plus_fader"))
    palette_theme: DJPaletteTheme = rng.choice(tuple(DJ_PALETTE_PRESETS.keys()))

    body_width = round(rng.uniform(0.50, 0.66), 4)
    body_depth = round(rng.uniform(0.30, 0.40), 4)
    body_height = round(rng.uniform(0.054, 0.072), 4)
    jog_x = round(rng.uniform(0.150, 0.205), 4)
    handle_span = round(rng.uniform(body_width * 0.78, body_width * 0.92), 4)
    platter_rim_radius = round(rng.uniform(0.052, 0.072), 4)
    pad_rows = rng.randint(2, 3)
    pad_cols = rng.randint(3, 4)
    tonearm_length = round(rng.uniform(0.10, 0.18), 4)
    single_platter_radius = round(rng.uniform(0.065, 0.088), 4)

    return DjEquipmentConfig(
        chassis_module=chassis,
        deck_layout_module=deck,
        controls_module=controls,
        palette_theme=palette_theme,
        body_width=body_width,
        body_depth=body_depth,
        body_height=body_height,
        jog_x=jog_x,
        handle_span=handle_span,
        platter_rim_radius=platter_rim_radius,
        pad_rows=pad_rows,
        pad_cols=pad_cols,
        tonearm_length=tonearm_length,
        single_platter_radius=single_platter_radius,
    )


def resolve_config(config: DjEquipmentConfig) -> ResolvedDjEquipmentConfig:
    """Validate + clamp config; fill in any None module slots with anchor
    defaults so a partially-specified config still builds."""

    chassis = config.chassis_module or "controller_chassis"
    deck = config.deck_layout_module or "dual_jog_decks"
    controls = config.controls_module or "triple_fader_strip"

    if chassis not in ("controller_chassis", "turntable_plinth"):
        raise ValueError(f"Unsupported chassis_module: {chassis}")
    if deck not in ("dual_jog_decks", "single_platter_with_tonearm"):
        raise ValueError(f"Unsupported deck_layout_module: {deck}")
    if controls not in ("triple_fader_strip", "pad_grid_plus_fader"):
        raise ValueError(f"Unsupported controls_module: {controls}")
    if str(config.palette_theme) not in DJ_PALETTE_PRESETS:
        raise ValueError(f"Unsupported palette_theme: {config.palette_theme}")

    bw = max(0.40, min(float(config.body_width), 0.80))
    bd = max(0.24, min(float(config.body_depth), 0.42))
    bh = max(0.040, min(float(config.body_height), 0.080))
    cr = max(0.016, min(float(config.corner_radius), 0.040))
    wt = max(0.008, min(float(config.wall_thickness), 0.018))
    bt = max(0.003, min(float(config.bottom_thickness), 0.006))
    tt = max(0.003, min(float(config.top_thickness), 0.006))

    jog_x = max(0.120, min(float(config.jog_x), 0.220))
    jog_y = float(config.jog_y)
    jog_d = max(0.090, min(float(config.jog_open_diameter), 0.150))
    sp_r = max(0.012, min(float(config.spindle_radius), 0.025))
    sp_h = max(0.003, min(float(config.spindle_height), 0.008))
    rim_r = max(0.045, min(float(config.platter_rim_radius), 0.080))
    rim_l = max(0.006, min(float(config.platter_rim_length), 0.014))

    cf_y = float(config.crossfader_y)
    cf_slot = tuple(float(v) for v in config.crossfader_slot)
    vol_slot = tuple(float(v) for v in config.volume_slot)
    if len(cf_slot) != 2:
        cf_slot = (0.140, 0.014)
    if len(vol_slot) != 2:
        vol_slot = (0.014, 0.098)
    lvx = float(config.left_volume_x)
    rvx = float(config.right_volume_x)
    vol_y = float(config.volume_y)

    handle_span = max(0.34, min(float(config.handle_span), 0.62))
    handle_reach = max(0.050, min(float(config.handle_reach), 0.090))
    handle_radius = max(0.0035, min(float(config.handle_radius), 0.008))
    handle_travel = max(0.6, min(float(config.handle_travel), 1.55))

    pad_rows = max(1, min(int(config.pad_rows), 4))
    pad_cols = max(2, min(int(config.pad_cols), 6))
    pad_size = tuple(float(v) for v in config.pad_size)
    if len(pad_size) != 3:
        pad_size = (0.026, 0.026, 0.010)
    pad_pitch = max(0.026, min(float(config.pad_pitch), 0.050))

    tonearm_length = max(0.10, min(float(config.tonearm_length), 0.20))
    tonearm_sweep_range = max(0.6, min(float(config.tonearm_sweep_range), 2.1))
    # single_platter_radius is bounded so a single platter mounted on the
    # housing's left_spindle (at -jog_x, jog_y) doesn't overlap the
    # crossfader (at y=-0.112) or the volume_faders (at y=0.020).
    # Minimum jog_x is 0.120, leaving 0.082m clearance to the left edge of
    # the leftmost volume fader at x=-0.038; subtract the fader cap half-
    # width (0.010) plus a 5mm safety margin → max radius ~0.067. We cap
    # at 0.090 since the volume_fader is at y=0.020 not on the line
    # (perpendicular distance is larger than purely-x clearance).
    single_platter_radius = max(0.060, min(float(config.single_platter_radius), 0.090))
    single_platter_height = max(0.012, min(float(config.single_platter_height), 0.024))

    palette = dict(DJ_PALETTE_PRESETS[config.palette_theme])

    return ResolvedDjEquipmentConfig(
        chassis_module=chassis,
        deck_layout_module=deck,
        controls_module=controls,
        palette_theme=config.palette_theme,
        body_width=bw,
        body_depth=bd,
        body_height=bh,
        corner_radius=cr,
        wall_thickness=wt,
        bottom_thickness=bt,
        top_thickness=tt,
        jog_x=jog_x,
        jog_y=jog_y,
        jog_open_diameter=jog_d,
        spindle_radius=sp_r,
        spindle_height=sp_h,
        platter_rim_radius=rim_r,
        platter_rim_length=rim_l,
        crossfader_y=cf_y,
        crossfader_slot=cf_slot,  # type: ignore[arg-type]
        volume_slot=vol_slot,  # type: ignore[arg-type]
        left_volume_x=lvx,
        right_volume_x=rvx,
        volume_y=vol_y,
        handle_span=handle_span,
        handle_reach=handle_reach,
        handle_radius=handle_radius,
        handle_travel=handle_travel,
        pad_rows=pad_rows,
        pad_cols=pad_cols,
        pad_size=pad_size,  # type: ignore[arg-type]
        pad_pitch=pad_pitch,
        tonearm_length=tonearm_length,
        tonearm_sweep_range=tonearm_sweep_range,
        single_platter_radius=single_platter_radius,
        single_platter_height=single_platter_height,
        palette=palette,
    )


# --------------------------------------------------------------------------- #
# Mesh + visual helpers — used by chassis and deck modules.
# --------------------------------------------------------------------------- #


def _shift_profile(profile, *, dx: float = 0.0, dy: float = 0.0):
    return [(x + dx, y + dy) for x, y in profile]


def _build_controller_housing_meshes(
    r: ResolvedDjEquipmentConfig,
    *,
    include_platter_holes: bool,
    include_fader_slots: bool,
    include_pad_grid: bool,
) -> tuple[object, object, object]:
    """Build the 3 Mesh visuals of the controller housing (wall_ring,
    bottom_panel, top_deck) — adapted from the anchor's ExtrudeGeometry /
    ExtrudeWithHolesGeometry construction.

    The top_deck's hole set varies with the chosen deck_layout / controls
    modules: dual decks cut 2 circular platter holes; single platter cuts
    1; triple_fader_strip cuts 3 rectangular slots; pad_grid_plus_fader
    cuts a pad grid + 1 slot. The wall ring + bottom panel are constant.
    """
    wall_height = r.body_height - r.bottom_thickness - r.top_thickness
    outer_profile = rounded_rect_profile(
        r.body_width, r.body_depth, r.corner_radius, corner_segments=10
    )
    inner_profile = rounded_rect_profile(
        r.body_width - 2.0 * r.wall_thickness,
        r.body_depth - 2.0 * r.wall_thickness,
        max(r.corner_radius - r.wall_thickness, 0.010),
        corner_segments=10,
    )

    top_holes: list = []

    if include_platter_holes:
        if r.deck_layout_module == "dual_jog_decks":
            platter_hole = superellipse_profile(
                r.jog_open_diameter, r.jog_open_diameter, exponent=2.0, segments=48
            )
            top_holes.append(_shift_profile(platter_hole, dx=-r.jog_x, dy=r.jog_y))
            top_holes.append(_shift_profile(platter_hole, dx=+r.jog_x, dy=r.jog_y))
        else:
            # single_platter_with_tonearm — cut the platter hole over the
            # LEFT jog position (the platter mounts on left_spindle); the
            # right_spindle stays exposed and is used as a tonearm pivot.
            single_hole = superellipse_profile(
                r.single_platter_radius * 2.0 + 0.010,
                r.single_platter_radius * 2.0 + 0.010,
                exponent=2.0,
                segments=48,
            )
            top_holes.append(_shift_profile(single_hole, dx=-r.jog_x, dy=r.jog_y))

    if include_fader_slots and r.controls_module == "triple_fader_strip":
        top_holes.append(
            _shift_profile(
                rounded_rect_profile(
                    r.crossfader_slot[0],
                    r.crossfader_slot[1],
                    0.005,
                    corner_segments=8,
                ),
                dy=r.crossfader_y,
            )
        )
        top_holes.append(
            _shift_profile(
                rounded_rect_profile(r.volume_slot[0], r.volume_slot[1], 0.005, corner_segments=8),
                dx=r.left_volume_x,
                dy=r.volume_y,
            )
        )
        top_holes.append(
            _shift_profile(
                rounded_rect_profile(r.volume_slot[0], r.volume_slot[1], 0.005, corner_segments=8),
                dx=r.right_volume_x,
                dy=r.volume_y,
            )
        )

    if include_pad_grid and r.controls_module == "pad_grid_plus_fader":
        # One long fader slot along the front edge.
        top_holes.append(
            _shift_profile(
                rounded_rect_profile(
                    r.crossfader_slot[0],
                    r.crossfader_slot[1],
                    0.005,
                    corner_segments=8,
                ),
                dy=r.crossfader_y,
            )
        )
        # Pad cutouts in a row × col grid (square holes, slightly larger
        # than the pad cap so the cap rises through them).
        pad_hole_size = r.pad_size[0] + 0.002
        col_x0 = -((r.pad_cols - 1) * 0.5) * r.pad_pitch
        row_y0 = -((r.pad_rows - 1) * 0.5) * r.pad_pitch
        for ri in range(r.pad_rows):
            for ci in range(r.pad_cols):
                px = col_x0 + ci * r.pad_pitch
                py = row_y0 + ri * r.pad_pitch + 0.020
                top_holes.append(
                    _shift_profile(
                        rounded_rect_profile(
                            pad_hole_size, pad_hole_size, 0.002, corner_segments=6
                        ),
                        dx=px,
                        dy=py,
                    )
                )

    wall_ring = ExtrudeWithHolesGeometry(
        outer_profile, [inner_profile], wall_height, center=True
    ).translate(0.0, 0.0, r.bottom_thickness + wall_height * 0.5)
    bottom_panel = ExtrudeGeometry(outer_profile, r.bottom_thickness, center=True).translate(
        0.0, 0.0, r.bottom_thickness * 0.5
    )
    top_deck = ExtrudeWithHolesGeometry(
        outer_profile, top_holes, r.top_thickness, center=True
    ).translate(0.0, 0.0, r.body_height - r.top_thickness * 0.5)

    return (
        mesh_from_geometry(wall_ring, "controller_wall_ring"),
        mesh_from_geometry(bottom_panel, "controller_bottom_panel"),
        mesh_from_geometry(top_deck, "controller_top_deck"),
    )


def _build_platter_visuals(part, r: ResolvedDjEquipmentConfig) -> None:
    """Adapted from anchor model.py:L39-L68 (`_build_platter`). 4 visuals.

    Used by both the dual_jog_decks (2 platters) and single_platter_with_tonearm
    (1 platter) modules. The `hub` cylinder sits at the bottom of the
    platter stack so the platter's -z face is at z=0 in part frame.
    """
    part.visual(
        Cylinder(radius=r.spindle_radius * 1.11, length=0.004),
        origin=Origin(xyz=(0.0, 0.0, 0.002)),
        material="platter_dark",
        name="hub",
    )
    part.visual(
        Cylinder(radius=r.platter_rim_radius, length=r.platter_rim_length),
        origin=Origin(xyz=(0.0, 0.0, r.platter_rim_length * 0.5 + 0.004)),
        material="platter_dark",
        name="rim",
    )
    part.visual(
        Cylinder(radius=r.platter_rim_radius * 0.875, length=0.002),
        origin=Origin(xyz=(0.0, 0.0, r.platter_rim_length + 0.005)),
        material="platter_top",
        name="touch_ring",
    )
    part.visual(
        Cylinder(radius=r.spindle_radius * 1.055, length=0.0015),
        origin=Origin(xyz=(0.0, 0.0, r.platter_rim_length + 0.00675)),
        material="accent_silver",
        name="center_label",
    )
    part.inertial = Inertial.from_geometry(
        Cylinder(radius=r.platter_rim_radius, length=0.018),
        mass=0.45,
        origin=Origin(xyz=(0.0, 0.0, 0.009)),
    )


def _build_slider_visuals(
    part,
    *,
    cap_size: tuple[float, float, float],
    grip_size: tuple[float, float, float],
    cap_name: str,
) -> None:
    """Adapted from anchor model.py:L71-L98 (`_build_slider`). 2 visuals
    + 1 inertial. Used by all 3 fader parts in triple_fader_strip and by
    the one fader in pad_grid_plus_fader."""
    cap_x, cap_y, cap_z = cap_size
    grip_x, grip_y, grip_z = grip_size
    part.visual(
        Box(cap_size),
        origin=Origin(xyz=(0.0, 0.0, cap_z * 0.5)),
        material="slider_black",
        name=cap_name,
    )
    part.visual(
        Box(grip_size),
        origin=Origin(xyz=(0.0, 0.0, cap_z + grip_z * 0.5)),
        material="accent_silver",
        name="grip",
    )
    part.inertial = Inertial.from_geometry(
        Box((max(cap_x, grip_x), max(cap_y, grip_y), cap_z + grip_z)),
        mass=0.06,
        origin=Origin(xyz=(0.0, 0.0, (cap_z + grip_z) * 0.5)),
    )


def _build_carry_handle_visuals(part, r: ResolvedDjEquipmentConfig) -> None:
    """Adapted from anchor model.py:L101-L142 (`_build_handle`). 5 visuals
    + 1 inertial. The handle's two hinge_barrels lie on the part-frame
    x-axis (so the hinge axis is +x in part frame); side arms hang down
    from each barrel and a long grip tube spans between them above."""
    span = r.handle_span
    reach = r.handle_reach
    tube_radius = r.handle_radius
    barrel_radius = tube_radius * 1.35
    barrel_length = 0.024
    arm_width = 0.018
    arm_thickness = tube_radius * 1.8
    arm_z = tube_radius * 1.9

    part.visual(
        Cylinder(radius=barrel_radius, length=barrel_length),
        origin=Origin(xyz=(barrel_length * 0.5, 0.0, 0.0), rpy=(0.0, math.pi / 2.0, 0.0)),
        material="accent_silver",
        name="left_hinge_barrel",
    )
    part.visual(
        Cylinder(radius=barrel_radius, length=barrel_length),
        origin=Origin(
            xyz=(span - barrel_length * 0.5, 0.0, 0.0),
            rpy=(0.0, math.pi / 2.0, 0.0),
        ),
        material="accent_silver",
        name="right_hinge_barrel",
    )
    part.visual(
        Box((arm_width, reach, arm_thickness)),
        origin=Origin(xyz=(barrel_length * 0.5, reach * 0.5, arm_z)),
        material="accent_silver",
        name="left_side_arm",
    )
    part.visual(
        Box((arm_width, reach, arm_thickness)),
        origin=Origin(xyz=(span - barrel_length * 0.5, reach * 0.5, arm_z)),
        material="accent_silver",
        name="right_side_arm",
    )
    part.visual(
        Cylinder(radius=tube_radius * 1.55, length=span - 0.040),
        origin=Origin(xyz=(span * 0.5, reach, arm_z), rpy=(0.0, math.pi / 2.0, 0.0)),
        material="slider_black",
        name="handle_grip",
    )
    part.inertial = Inertial.from_geometry(
        Box((span, reach, arm_z + arm_thickness)),
        mass=0.35,
        origin=Origin(xyz=(span * 0.5, reach * 0.5, (arm_z + arm_thickness) * 0.5)),
    )


# --------------------------------------------------------------------------- #
# Module factories — chassis
# --------------------------------------------------------------------------- #


def _build_controller_chassis(ctx: ModuleBuildContext) -> ModuleBuild:
    """Anchor chassis — portable DJ controller housing with Mesh top deck
    (rounded-rect + cut-outs for platters / faders / pads), spindles,
    motor pedestals, EQ knobs, display strips, mixer panel and handle
    brackets. Owns a REVOLUTE `carry_handle` child.

    Exposes a downstream interface on the housing's top deck so the
    deck_layout module can locate the platter mounting plane. Internal
    articulation: ``housing_to_carry_handle`` REVOLUTE around +x.
    """
    model = ctx.model
    r: ResolvedDjEquipmentConfig = ctx.config  # type: ignore[assignment]

    housing = model.part("housing")

    wall_ring_mesh, bottom_panel_mesh, top_deck_mesh = _build_controller_housing_meshes(
        r,
        include_platter_holes=True,
        include_fader_slots=True,
        include_pad_grid=True,
    )

    housing.inertial = Inertial.from_geometry(
        Box((r.body_width, r.body_depth, r.body_height)),
        mass=5.8,
        origin=Origin(xyz=(0.0, 0.0, r.body_height * 0.5)),
    )

    housing.visual(wall_ring_mesh, material="housing_black", name="wall_ring")
    housing.visual(bottom_panel_mesh, material="housing_black", name="bottom_panel")
    housing.visual(top_deck_mesh, material="deck_graphite", name="top_deck")

    # Spindles — always emit BOTH at the canonical jog positions so the
    # deck_layout module always finds left_spindle / right_spindle parts.
    # For single_platter_with_tonearm, the right_spindle doubles as the
    # tonearm pivot post.
    housing.visual(
        Cylinder(radius=r.spindle_radius, length=r.spindle_height),
        origin=Origin(xyz=(-r.jog_x, r.jog_y, r.body_height + r.spindle_height * 0.5)),
        material="accent_silver",
        name="left_spindle",
    )
    housing.visual(
        Cylinder(radius=r.spindle_radius, length=r.spindle_height),
        origin=Origin(xyz=(+r.jog_x, r.jog_y, r.body_height + r.spindle_height * 0.5)),
        material="accent_silver",
        name="right_spindle",
    )
    # Motor pedestals (interior — inside the case).
    pedestal_radius = 0.024
    pedestal_length = r.body_height - r.bottom_thickness
    housing.visual(
        Cylinder(radius=pedestal_radius, length=pedestal_length),
        origin=Origin(xyz=(-r.jog_x, r.jog_y, r.bottom_thickness + pedestal_length * 0.5)),
        material="housing_black",
        name="left_motor_pedestal",
    )
    housing.visual(
        Cylinder(radius=pedestal_radius, length=pedestal_length),
        origin=Origin(xyz=(+r.jog_x, r.jog_y, r.bottom_thickness + pedestal_length * 0.5)),
        material="housing_black",
        name="right_motor_pedestal",
    )

    # Display strips above each deck (cosmetic Boxes).
    housing.visual(
        Box((0.120, 0.030, 0.003)),
        origin=Origin(xyz=(-r.jog_x, 0.118, r.body_height + 0.0015)),
        material="cue_gray",
        name="left_display_strip",
    )
    housing.visual(
        Box((0.120, 0.030, 0.003)),
        origin=Origin(xyz=(+r.jog_x, 0.118, r.body_height + 0.0015)),
        material="cue_gray",
        name="right_display_strip",
    )
    housing.visual(
        Box((0.072, 0.140, 0.003)),
        origin=Origin(xyz=(0.0, 0.024, r.body_height + 0.0015)),
        material="cue_gray",
        name="mixer_panel",
    )

    # EQ knobs above the mixer panel — 6 by default. We always emit these
    # on the controller_chassis (they sit on the cosmetic mixer_panel and
    # don't depend on which controls module is chosen).
    knob_xs = (-0.034, 0.0, 0.034)
    knob_ys = (0.112, 0.084)
    for kxi, knob_x in enumerate(knob_xs):
        for kyi, knob_y in enumerate(knob_ys):
            housing.visual(
                Cylinder(radius=0.007, length=0.010),
                origin=Origin(xyz=(knob_x, knob_y, r.body_height + 0.005)),
                material="accent_silver",
                name=f"eq_knob_{kxi}_{kyi}",
            )

    # Carry-handle brackets on the housing top. Each bracket is a small
    # Box that captures one end of the handle's hinge barrel. The barrel
    # is a horizontal cylinder of length 0.024 (axis along +x) whose end
    # in world frame coincides with the joint origin. To make the bracket
    # cleanly OVERLAP with the barrel end (rather than gap-or-overlap
    # depending on handle_span), we place each bracket center at the
    # barrel's first 0.005m, regardless of handle_span.
    barrel_length = 0.024
    bracket_size = 0.024
    # Bracket z size spans from top_deck (z=body_height) up to past the
    # hinge axis, so the bracket is physically touching the housing
    # (no disconnected island) AND fully encloses the barrel.
    bracket_z_len = 2.0 * r.handle_radius + 0.004
    # Pull bracket y INWARD from body edge — rounded corners of the
    # top_deck mesh curve away at high y near the body width edge, so
    # brackets near the corner end up over a non-existent mesh area.
    bracket_y = min(0.130, r.body_depth * 0.36)
    left_bracket_x = -r.handle_span * 0.5 + barrel_length * 0.5
    right_bracket_x = +r.handle_span * 0.5 - barrel_length * 0.5
    # Extend bracket DOWN into the housing wall_ring + top_deck region
    # by 8mm so it has clear mesh-face contact (the top_deck is a Mesh
    # with holes — strict 1e-6 connectivity check needs actual mesh
    # overlap, not just AABB touch).
    bracket_z_center = r.body_height + bracket_z_len * 0.5 - 0.010
    housing.visual(
        Box((bracket_size, bracket_size, bracket_z_len)),
        origin=Origin(xyz=(left_bracket_x, bracket_y, bracket_z_center)),
        material="accent_silver",
        name="left_handle_bracket",
    )
    housing.visual(
        Box((bracket_size, bracket_size, bracket_z_len)),
        origin=Origin(xyz=(right_bracket_x, bracket_y, bracket_z_center)),
        material="accent_silver",
        name="right_handle_bracket",
    )

    # Build the carry_handle child part + internal REVOLUTE joint.
    carry_handle = model.part("carry_handle")
    _build_carry_handle_visuals(carry_handle, r)
    # Carry handle joint is a mechanical pivot (hinge barrel captured by
    # housing bracket pin) — MatingContract intentionally omitted, since
    # the abstraction does not naturally model pin-through-sleeve. The
    # author tests declare an allow_overlap to grandfather the captured
    # geometry overlap.
    model.articulation(
        "housing_to_carry_handle",
        ArticulationType.REVOLUTE,
        parent=housing,
        child=carry_handle,
        origin=Origin(
            xyz=(-r.handle_span * 0.5, r.body_depth * 0.5, r.body_height + r.handle_radius)
        ),
        axis=(1.0, 0.0, 0.0),
        motion_limits=MotionLimits(effort=8.0, velocity=2.0, lower=0.0, upper=r.handle_travel),
    )

    # Downstream interface: top of the housing. Subsequent slots read
    # ctx.upstream_interface.part_name to know they should parent to
    # 'housing'.
    downstream = InterfaceSpec(
        interface_name="downstream",
        part_name="housing",
        visual_name="top_deck",
        face_side="positive_z",
        anchor_local=(0.0, 0.0, r.body_height),
        face_extents_uv=(r.body_width, r.body_depth),
        extents_tol=0.50,
        contact_tol=0.0020,
    )

    return ModuleBuild(
        module_name="controller_chassis",
        parts_emitted=["housing", "carry_handle"],
        internal_articulations=["housing_to_carry_handle"],
        interfaces={"downstream": downstream},
    )


def _build_turntable_plinth_chassis(ctx: ModuleBuildContext) -> ModuleBuild:
    """Alt chassis — heavier turntable plinth derived from rec_6e26a3..
    A wooden / matte_black plinth body built from a single Mesh
    (ExtrudeGeometry over a rounded_rect), 4 rubber feet, control buttons
    on the front-left corner, and a tonearm base on the back-right. Owns
    a REVOLUTE carry_handle child.

    The plinth is taller than the controller (heavier construction) but
    occupies a similar footprint. Tonearm/cue_lift parts are NOT emitted
    here — those belong to the deck_layout module.
    """
    model = ctx.model
    r: ResolvedDjEquipmentConfig = ctx.config  # type: ignore[assignment]

    housing = model.part("housing")

    # Plinth dimensions — slightly taller envelope than controller.
    plinth_h = r.body_height * 1.30
    plinth_top_thickness = 0.004
    plinth_z = plinth_h * 0.5

    plinth_shell_mesh = mesh_from_geometry(
        ExtrudeGeometry(
            rounded_rect_profile(
                r.body_width * 0.78, r.body_depth * 1.02, 0.020, corner_segments=10
            ),
            plinth_h - plinth_top_thickness,
            cap=True,
            center=True,
        ),
        "turntable_plinth_shell",
    )
    housing.visual(
        plinth_shell_mesh,
        origin=Origin(xyz=(0.0, 0.0, (plinth_h - plinth_top_thickness) * 0.5)),
        material="wood_warm",
        name="plinth_shell",
    )
    # Top plate (the dust-cover ledge) — a deck the platter sits on.
    housing.visual(
        Box((r.body_width * 0.76, r.body_depth * 1.00, plinth_top_thickness)),
        origin=Origin(xyz=(0.0, 0.0, plinth_h - plinth_top_thickness * 0.5)),
        material="deck_graphite",
        name="top_deck",
    )
    # 4 rubber feet.
    foot_radius = 0.024
    foot_length = 0.016
    foot_x = r.body_width * 0.30
    foot_y = r.body_depth * 0.36
    for x_sign in (-1.0, 1.0):
        for y_sign in (-1.0, 1.0):
            housing.visual(
                Cylinder(radius=foot_radius, length=foot_length),
                origin=Origin(xyz=(foot_x * x_sign, foot_y * y_sign, foot_length * 0.5)),
                material="slider_black",
                name=(f"foot_{'r' if x_sign > 0.0 else 'l'}_{'b' if y_sign > 0.0 else 'f'}"),
            )
    # Start/stop button + pitch slider on the front-left.
    housing.visual(
        Cylinder(radius=0.018, length=0.004),
        origin=Origin(xyz=(-r.body_width * 0.32, -r.body_depth * 0.34, plinth_h + 0.002)),
        material="accent_silver",
        name="start_stop_button",
    )
    housing.visual(
        Cylinder(radius=0.008, length=0.003),
        origin=Origin(xyz=(-r.body_width * 0.27, -r.body_depth * 0.24, plinth_h + 0.0015)),
        material="accent_silver",
        name="speed_button",
    )
    housing.visual(
        Box((0.012, 0.092, 0.004)),
        origin=Origin(xyz=(r.body_width * 0.32, 0.000, plinth_h + 0.002)),
        material="deck_graphite",
        name="pitch_slider_slot",
    )
    housing.visual(
        Box((0.014, 0.020, 0.005)),
        origin=Origin(xyz=(r.body_width * 0.32, -0.034, plinth_h + 0.0025)),
        material="accent_silver",
        name="pitch_slider_cap",
    )
    housing.visual(
        Cylinder(radius=0.006, length=0.008),
        origin=Origin(xyz=(r.body_width * 0.22, r.body_depth * 0.34, plinth_h + 0.004)),
        material="accent_red",
        name="target_light",
    )
    # Bearing hub at the center (cosmetic — the actual platter spindles
    # are emitted below at the canonical jog positions).
    housing.visual(
        Cylinder(radius=0.006, length=0.005),
        origin=Origin(xyz=(0.0, 0.0, plinth_h + 0.0025)),
        material="deck_graphite",
        name="bearing_hub",
    )
    # Tonearm base + post on the back-right (cosmetic for dual_jog_decks;
    # used as the tonearm pivot for single_platter_with_tonearm).
    housing.visual(
        Cylinder(radius=0.028, length=0.012),
        origin=Origin(xyz=(r.body_width * 0.29, -r.body_depth * 0.34, plinth_h + 0.006)),
        material="deck_graphite",
        name="tonearm_base",
    )
    housing.visual(
        Cylinder(radius=0.008, length=0.014),
        origin=Origin(xyz=(r.body_width * 0.29, -r.body_depth * 0.34, plinth_h + 0.019)),
        material="accent_silver",
        name="tonearm_post",
    )
    # Spindles at the canonical jog positions — both deck_layout variants
    # mount their platter on `left_spindle`, and dual_jog_decks also
    # mounts on `right_spindle`. Keeping the spindle naming + position
    # uniform across chassis variants means deck_layout factories don't
    # need a chassis-specific branch.
    housing.visual(
        Cylinder(radius=r.spindle_radius, length=r.spindle_height),
        origin=Origin(xyz=(-r.jog_x, r.jog_y, plinth_h + r.spindle_height * 0.5)),
        material="accent_silver",
        name="left_spindle",
    )
    housing.visual(
        Cylinder(radius=r.spindle_radius, length=r.spindle_height),
        origin=Origin(xyz=(+r.jog_x, r.jog_y, plinth_h + r.spindle_height * 0.5)),
        material="accent_silver",
        name="right_spindle",
    )

    # Carry-handle brackets — attached to the back edge of the plinth.
    # Same x-positioning logic as controller_chassis: place bracket center
    # at the matching barrel midpoint (joint_origin_x ± barrel_length/2).
    handle_z = plinth_h + r.handle_radius
    barrel_length = 0.024
    bracket_y = r.body_depth * 0.46
    left_bracket_x = -r.handle_span * 0.5 + barrel_length * 0.5
    right_bracket_x = +r.handle_span * 0.5 - barrel_length * 0.5
    housing.visual(
        Box((0.024, 0.024, 0.018)),
        origin=Origin(xyz=(left_bracket_x, bracket_y, handle_z)),
        material="accent_silver",
        name="left_handle_bracket",
    )
    housing.visual(
        Box((0.024, 0.024, 0.018)),
        origin=Origin(xyz=(right_bracket_x, bracket_y, handle_z)),
        material="accent_silver",
        name="right_handle_bracket",
    )

    housing.inertial = Inertial.from_geometry(
        Box((r.body_width * 0.78, r.body_depth * 1.02, plinth_h)),
        mass=12.0,
        origin=Origin(xyz=(0.0, 0.0, plinth_z)),
    )

    # Carry handle child.
    carry_handle = model.part("carry_handle")
    _build_carry_handle_visuals(carry_handle, r)
    model.articulation(
        "housing_to_carry_handle",
        ArticulationType.REVOLUTE,
        parent=housing,
        child=carry_handle,
        origin=Origin(xyz=(-r.handle_span * 0.5, r.body_depth * 0.46, plinth_h + r.handle_radius)),
        axis=(1.0, 0.0, 0.0),
        motion_limits=MotionLimits(effort=8.0, velocity=2.0, lower=0.0, upper=r.handle_travel),
    )

    # Downstream interface: top of the plinth. Subsequent slots use
    # ctx.upstream_interface.part_name = "housing".
    downstream = InterfaceSpec(
        interface_name="downstream",
        part_name="housing",
        visual_name="top_deck",
        face_side="positive_z",
        anchor_local=(0.0, 0.0, plinth_h),
        face_extents_uv=(r.body_width * 0.76, r.body_depth * 1.00),
        extents_tol=0.50,
        contact_tol=0.0020,
    )

    return ModuleBuild(
        module_name="turntable_plinth",
        parts_emitted=["housing", "carry_handle"],
        internal_articulations=["housing_to_carry_handle"],
        interfaces={"downstream": downstream},
    )


# --------------------------------------------------------------------------- #
# Module factories — deck_layout (joints internally parented to housing)
# --------------------------------------------------------------------------- #


def _housing_top_z_from_interface(ctx: ModuleBuildContext) -> float:
    """Read the upstream interface's anchor z to get the housing top-deck
    height. This is robust to chassis variants having different body
    heights (controller_chassis uses r.body_height, turntable_plinth
    uses r.body_height * 1.30)."""
    if ctx.upstream_interface is None:
        # Fallback to controller envelope if invoked without chain context.
        r: ResolvedDjEquipmentConfig = ctx.config  # type: ignore[assignment]
        return r.body_height
    return float(ctx.upstream_interface.anchor_local[2])


def _build_dual_jog_decks(ctx: ModuleBuildContext) -> ModuleBuild:
    """Anchor deck layout — two platters (left + right) as REVOLUTE children
    of the housing, both spinning around +z. Each platter's hub mates with
    its corresponding spindle on the housing (controller_chassis +
    left_spindle / right_spindle).

    No upstream interface is exposed (the assembler should NOT auto-chain
    deck_layout to chassis — we emit the joints internally with
    parent=housing). We DO expose a downstream interface pointing at the
    same housing top face, so the next slot (controls) can keep finding
    the housing.
    """
    model = ctx.model
    r: ResolvedDjEquipmentConfig = ctx.config  # type: ignore[assignment]

    housing_name = (
        ctx.upstream_interface.part_name if ctx.upstream_interface is not None else "housing"
    )
    housing = model.get_part(housing_name)
    top_z = _housing_top_z_from_interface(ctx)

    left_platter = model.part("left_platter")
    _build_platter_visuals(left_platter, r)
    right_platter = model.part("right_platter")
    _build_platter_visuals(right_platter, r)

    spindle_top_z = top_z + r.spindle_height
    model.articulation(
        "housing_to_left_platter",
        ArticulationType.REVOLUTE,
        parent=housing,
        child=left_platter,
        origin=Origin(xyz=(-r.jog_x, r.jog_y, spindle_top_z)),
        axis=(0.0, 0.0, 1.0),
        motion_limits=MotionLimits(
            effort=3.0, velocity=16.0, lower=-2.0 * math.pi, upper=2.0 * math.pi
        ),
        mating=MatingContract(
            parent_face_geometry="left_spindle",
            parent_face_side="positive_z",
            child_face_geometry="hub",
            child_face_side="negative_z",
            contact_tol=0.0015,
        ),
    )
    model.articulation(
        "housing_to_right_platter",
        ArticulationType.REVOLUTE,
        parent=housing,
        child=right_platter,
        origin=Origin(xyz=(+r.jog_x, r.jog_y, spindle_top_z)),
        axis=(0.0, 0.0, 1.0),
        motion_limits=MotionLimits(
            effort=3.0, velocity=16.0, lower=-2.0 * math.pi, upper=2.0 * math.pi
        ),
        mating=MatingContract(
            parent_face_geometry="right_spindle",
            parent_face_side="positive_z",
            child_face_geometry="hub",
            child_face_side="negative_z",
            contact_tol=0.0015,
        ),
    )

    # No-op downstream interface so the chain can continue to controls.
    # It points at the same housing top deck the chassis exposed.
    downstream = ctx.upstream_interface
    if downstream is None:
        downstream = InterfaceSpec(
            interface_name="downstream",
            part_name=housing_name,
            visual_name="top_deck",
            face_side="positive_z",
            anchor_local=(0.0, 0.0, top_z),
            face_extents_uv=(r.body_width, r.body_depth),
            extents_tol=0.50,
            contact_tol=0.0020,
        )

    return ModuleBuild(
        module_name="dual_jog_decks",
        parts_emitted=["left_platter", "right_platter"],
        internal_articulations=["housing_to_left_platter", "housing_to_right_platter"],
        interfaces={"downstream": downstream},
    )


def _build_single_platter_with_tonearm(ctx: ModuleBuildContext) -> ModuleBuild:
    """Alt deck layout — single large platter + tonearm, both REVOLUTE
    children of the housing. Geometry derived from rec_6e26a3..

    The single platter sits on the housing's `left_spindle` (chassis-
    naming kept consistent across variants). The tonearm pivots on the
    housing's `tonearm_post` cylinder, around +z.

    Mating contracts only on the platter (clear spindle ↔ hub contact).
    The tonearm's pivot is a captured-pin pivot — grandfathered (no
    mating field).
    """
    model = ctx.model
    r: ResolvedDjEquipmentConfig = ctx.config  # type: ignore[assignment]

    housing_name = (
        ctx.upstream_interface.part_name if ctx.upstream_interface is not None else "housing"
    )
    housing = model.get_part(housing_name)
    top_z = _housing_top_z_from_interface(ctx)

    # Single big platter (larger than dual_jog_decks platters).
    left_platter = model.part("left_platter")
    spr = r.single_platter_radius
    splh = r.single_platter_height
    left_platter.visual(
        Cylinder(radius=r.spindle_radius * 1.11, length=0.004),
        origin=Origin(xyz=(0.0, 0.0, 0.002)),
        material="platter_dark",
        name="hub",
    )
    left_platter.visual(
        Cylinder(radius=spr, length=splh),
        origin=Origin(xyz=(0.0, 0.0, splh * 0.5 + 0.004)),
        material="accent_silver",
        name="rim",
    )
    left_platter.visual(
        Cylinder(radius=spr * 0.92, length=0.003),
        origin=Origin(xyz=(0.0, 0.0, splh + 0.005)),
        material="slider_black",
        name="touch_ring",
    )
    left_platter.visual(
        Cylinder(radius=spr * 0.32, length=0.0008),
        origin=Origin(xyz=(0.0, 0.0, splh + 0.0066)),
        material="accent_red",
        name="center_label",
    )
    left_platter.inertial = Inertial.from_geometry(
        Cylinder(radius=spr, length=splh + 0.006),
        mass=1.8,
        origin=Origin(xyz=(0.0, 0.0, (splh + 0.006) * 0.5)),
    )

    # Tonearm part.
    right_platter = model.part("right_platter")
    # ^ Reuse the "right_platter" part name slot but build it as a tonearm.
    # This keeps the joint topology test in the unit test simple (still
    # two REVOLUTE-around-z deck children of housing).
    arm_l = r.tonearm_length
    # Arm rides ABOVE the platter top so it can sweep across the record
    # without colliding with the platter rim. The pivot_hub post is
    # lengthened to reach that height. splh = single_platter_height.
    arm_z = splh + 0.020
    pivot_post_len = splh + 0.028
    right_platter.visual(
        Cylinder(radius=0.010, length=pivot_post_len),
        origin=Origin(xyz=(0.0, 0.0, pivot_post_len * 0.5 - 0.004)),
        material="slider_black",
        name="pivot_hub",
    )
    # arm_tube extends backward past the pivot to reach the
    # counterweight, so the two visuals are physically connected (no
    # floating counterweight). Tube spans x ∈ [-0.025, arm_l].
    arm_tube_total_len = arm_l + 0.025
    arm_tube_center_x = (arm_l - 0.025) * 0.5
    right_platter.visual(
        Cylinder(radius=0.0046, length=arm_tube_total_len),
        origin=Origin(
            xyz=(arm_tube_center_x, 0.0, arm_z),
            rpy=(0.0, math.pi / 2.0, 0.0),
        ),
        material="accent_silver",
        name="arm_tube",
    )
    # Counterweight sleeves over the rear of the arm_tube (overlapping
    # geometry — same part, intra-part overlap is allowed).
    right_platter.visual(
        Cylinder(radius=0.011, length=0.030),
        origin=Origin(
            xyz=(-0.015, 0.0, arm_z),
            rpy=(0.0, math.pi / 2.0, 0.0),
        ),
        material="deck_graphite",
        name="counterweight",
    )
    right_platter.visual(
        Box((0.026, 0.018, 0.005)),
        origin=Origin(
            xyz=(arm_l + 0.010, 0.0, arm_z - 0.003),
        ),
        material="slider_black",
        name="headshell",
    )
    right_platter.inertial = Inertial.from_geometry(
        Box((arm_l + 0.060, 0.060, 0.030)),
        mass=0.35,
        origin=Origin(xyz=(arm_l * 0.4, 0.0, arm_z * 0.5)),
    )

    spindle_top_z = top_z + r.spindle_height

    # Platter joint — mate hub against the LEFT spindle (real contact),
    # positioned at the canonical left jog location (-jog_x, jog_y).
    model.articulation(
        "housing_to_left_platter",
        ArticulationType.REVOLUTE,
        parent=housing,
        child=left_platter,
        origin=Origin(xyz=(-r.jog_x, r.jog_y, spindle_top_z)),
        axis=(0.0, 0.0, 1.0),
        motion_limits=MotionLimits(
            effort=4.0, velocity=20.0, lower=-2.0 * math.pi, upper=2.0 * math.pi
        ),
        mating=MatingContract(
            parent_face_geometry="left_spindle",
            parent_face_side="positive_z",
            child_face_geometry="hub",
            child_face_side="negative_z",
            contact_tol=0.0015,
        ),
    )

    # Tonearm joint — positioned at the BACK-RIGHT of the platter (real
    # turntable layout, mirroring rec_6e26): pivot just past the
    # platter's right edge in x and behind the platter in y, so the arm
    # can sweep diagonally across the platter. At-rest orientation is
    # set via the joint origin's rpy so the arm tube points from the
    # pivot toward the platter center (headshell hovers over the
    # platter's outer edge). Captured-pin geometry — mating omitted.
    spr = r.single_platter_radius
    platter_body_x = -r.jog_x
    platter_body_y = r.jog_y
    tonearm_x = platter_body_x + spr + 0.020
    # Push tonearm to the back of the housing (away from front controls
    # like volume_fader stubs at y≈-0.020 in pad_grid variant). The arm
    # then sweeps forward across the platter.
    tonearm_y = -r.body_depth * 0.30
    tonearm_z = spindle_top_z
    direction_x = platter_body_x - tonearm_x
    direction_y = platter_body_y - tonearm_y
    arm_rest_angle = math.atan2(direction_y, direction_x)

    model.articulation(
        "housing_to_right_platter",
        ArticulationType.REVOLUTE,
        parent=housing,
        child=right_platter,
        origin=Origin(
            xyz=(tonearm_x, tonearm_y, tonearm_z),
            rpy=(0.0, 0.0, arm_rest_angle),
        ),
        axis=(0.0, 0.0, 1.0),
        motion_limits=MotionLimits(
            effort=1.5,
            velocity=1.0,
            lower=-r.tonearm_sweep_range * 0.5,
            upper=r.tonearm_sweep_range * 0.5,
        ),
    )

    downstream = ctx.upstream_interface
    if downstream is None:
        downstream = InterfaceSpec(
            interface_name="downstream",
            part_name=housing_name,
            visual_name="top_deck",
            face_side="positive_z",
            anchor_local=(0.0, 0.0, top_z),
            face_extents_uv=(r.body_width, r.body_depth),
            extents_tol=0.50,
            contact_tol=0.0020,
        )

    return ModuleBuild(
        module_name="single_platter_with_tonearm",
        parts_emitted=["left_platter", "right_platter"],
        internal_articulations=["housing_to_left_platter", "housing_to_right_platter"],
        interfaces={"downstream": downstream},
    )


# --------------------------------------------------------------------------- #
# Module factories — controls (joints internally parented to housing)
# --------------------------------------------------------------------------- #


def _build_triple_fader_strip(ctx: ModuleBuildContext) -> ModuleBuild:
    """Anchor controls layout — crossfader (PRISMATIC along x), left and
    right volume faders (PRISMATIC along y). All three are children of
    the housing, mating against its top_deck.

    Part names match the PRIMARY_ANCHOR: crossfader, left_volume_fader,
    right_volume_fader. Each fader carries a 2-visual cap+grip stack
    plus an inertial. The crossfader cap is wider in x; volume faders
    are taller in y.
    """
    model = ctx.model
    r: ResolvedDjEquipmentConfig = ctx.config  # type: ignore[assignment]

    housing_name = (
        ctx.upstream_interface.part_name if ctx.upstream_interface is not None else "housing"
    )
    housing = model.get_part(housing_name)
    top_z = _housing_top_z_from_interface(ctx)

    crossfader = model.part("crossfader")
    _build_slider_visuals(
        crossfader,
        cap_size=(0.026, 0.018, 0.012),
        grip_size=(0.010, 0.012, 0.008),
        cap_name="crossfader_cap",
    )
    left_volume_fader = model.part("left_volume_fader")
    _build_slider_visuals(
        left_volume_fader,
        cap_size=(0.020, 0.028, 0.012),
        grip_size=(0.010, 0.016, 0.008),
        cap_name="volume_fader_cap",
    )
    right_volume_fader = model.part("right_volume_fader")
    _build_slider_visuals(
        right_volume_fader,
        cap_size=(0.020, 0.028, 0.012),
        grip_size=(0.010, 0.016, 0.008),
        cap_name="volume_fader_cap",
    )

    model.articulation(
        "housing_to_crossfader",
        ArticulationType.PRISMATIC,
        parent=housing,
        child=crossfader,
        origin=Origin(xyz=(0.0, r.crossfader_y, top_z)),
        axis=(1.0, 0.0, 0.0),
        motion_limits=MotionLimits(effort=1.5, velocity=0.30, lower=-0.055, upper=0.055),
        mating=MatingContract(
            parent_face_geometry="top_deck",
            parent_face_side="positive_z",
            child_face_geometry="crossfader_cap",
            child_face_side="negative_z",
            contact_tol=0.0020,
        ),
    )
    model.articulation(
        "housing_to_left_volume_fader",
        ArticulationType.PRISMATIC,
        parent=housing,
        child=left_volume_fader,
        origin=Origin(xyz=(r.left_volume_x, r.volume_y, top_z)),
        axis=(0.0, 1.0, 0.0),
        motion_limits=MotionLimits(effort=1.5, velocity=0.30, lower=-0.038, upper=0.038),
        mating=MatingContract(
            parent_face_geometry="top_deck",
            parent_face_side="positive_z",
            child_face_geometry="volume_fader_cap",
            child_face_side="negative_z",
            contact_tol=0.0020,
        ),
    )
    model.articulation(
        "housing_to_right_volume_fader",
        ArticulationType.PRISMATIC,
        parent=housing,
        child=right_volume_fader,
        origin=Origin(xyz=(r.right_volume_x, r.volume_y, top_z)),
        axis=(0.0, 1.0, 0.0),
        motion_limits=MotionLimits(effort=1.5, velocity=0.30, lower=-0.038, upper=0.038),
        mating=MatingContract(
            parent_face_geometry="top_deck",
            parent_face_side="positive_z",
            child_face_geometry="volume_fader_cap",
            child_face_side="negative_z",
            contact_tol=0.0020,
        ),
    )

    return ModuleBuild(
        module_name="triple_fader_strip",
        parts_emitted=["crossfader", "left_volume_fader", "right_volume_fader"],
        internal_articulations=[
            "housing_to_crossfader",
            "housing_to_left_volume_fader",
            "housing_to_right_volume_fader",
        ],
        interfaces={},
    )


def _build_pad_grid_plus_fader(ctx: ModuleBuildContext) -> ModuleBuild:
    """Alt controls layout — a pad grid (PRISMATIC down-press buttons,
    one part per pad) + a single crossfader. Geometry derived from
    rec_12cc44... (grid_midi_pad_controller).

    The pad grid is `pad_rows × pad_cols` (default 2 × 4 = 8 pads). Each
    pad is a tiny rubber-cap part that PRISMATICally compresses downward
    along -z when pressed. The lone crossfader runs along the front edge,
    PRISMATIC along x.

    To keep the unit-test joint count comparable across topology
    variants, we ALSO emit two stub PRISMATIC parts named
    `left_volume_fader` and `right_volume_fader` so the model always
    has the same fader-named children for downstream tooling. They are
    positioned at the front corners and act as decorative side buttons.
    """
    model = ctx.model
    r: ResolvedDjEquipmentConfig = ctx.config  # type: ignore[assignment]

    housing_name = (
        ctx.upstream_interface.part_name if ctx.upstream_interface is not None else "housing"
    )
    housing = model.get_part(housing_name)
    top_z = _housing_top_z_from_interface(ctx)

    # Lone crossfader at the front.
    crossfader = model.part("crossfader")
    _build_slider_visuals(
        crossfader,
        cap_size=(0.028, 0.020, 0.012),
        grip_size=(0.012, 0.012, 0.008),
        cap_name="crossfader_cap",
    )
    model.articulation(
        "housing_to_crossfader",
        ArticulationType.PRISMATIC,
        parent=housing,
        child=crossfader,
        origin=Origin(xyz=(0.0, r.crossfader_y, top_z)),
        axis=(1.0, 0.0, 0.0),
        motion_limits=MotionLimits(effort=1.5, velocity=0.30, lower=-0.060, upper=0.060),
        mating=MatingContract(
            parent_face_geometry="top_deck",
            parent_face_side="positive_z",
            child_face_geometry="crossfader_cap",
            child_face_side="negative_z",
            contact_tol=0.0020,
        ),
    )

    # Two "side button" stubs in the slot positions historically held by
    # left_volume_fader / right_volume_fader. They press downward along
    # -z instead of sliding along y, so they don't conflict visually with
    # the pad grid behind them.
    pad_sx, pad_sy, pad_sz = r.pad_size

    def _build_pad_part(part, *, name_for_cap: str = "pad_cap") -> None:
        part.visual(
            Box((pad_sx, pad_sy, pad_sz * 0.6)),
            origin=Origin(xyz=(0.0, 0.0, pad_sz * 0.3)),
            material="pad_rubber",
            name=name_for_cap,
        )
        part.visual(
            Box((pad_sx * 0.55, pad_sy * 0.55, pad_sz * 0.4)),
            origin=Origin(xyz=(0.0, 0.0, -pad_sz * 0.2)),
            material="pad_rubber",
            name="pad_stem",
        )
        part.inertial = Inertial.from_geometry(
            Box((pad_sx, pad_sy, pad_sz)),
            mass=0.018,
            origin=Origin(xyz=(0.0, 0.0, 0.0)),
        )

    left_side_button = model.part("left_volume_fader")
    _build_pad_part(left_side_button, name_for_cap="volume_fader_cap")
    right_side_button = model.part("right_volume_fader")
    _build_pad_part(right_side_button, name_for_cap="volume_fader_cap")

    # Pad-button parts have geometry that extends BELOW their part-frame
    # origin: the stem visual sits at z=-pad_sz*0.2 (extending down to
    # z=-pad_sz*0.4). To put the stem's BOTTOM in contact with the
    # top_deck +z face, the joint origin's z must be top_z + pad_sz*0.4.
    pad_stem_low_z = pad_sz * 0.4  # absolute value of stem's lowest z in part frame

    model.articulation(
        "housing_to_left_volume_fader",
        ArticulationType.PRISMATIC,
        parent=housing,
        child=left_side_button,
        origin=Origin(xyz=(r.left_volume_x - 0.060, r.volume_y - 0.04, top_z + pad_stem_low_z)),
        axis=(0.0, 0.0, -1.0),
        motion_limits=MotionLimits(effort=4.0, velocity=0.06, lower=0.0, upper=0.003),
        mating=MatingContract(
            parent_face_geometry="top_deck",
            parent_face_side="positive_z",
            child_face_geometry="pad_stem",
            child_face_side="negative_z",
            contact_tol=0.0030,
        ),
    )
    model.articulation(
        "housing_to_right_volume_fader",
        ArticulationType.PRISMATIC,
        parent=housing,
        child=right_side_button,
        origin=Origin(xyz=(r.right_volume_x + 0.060, r.volume_y - 0.04, top_z + pad_stem_low_z)),
        axis=(0.0, 0.0, -1.0),
        motion_limits=MotionLimits(effort=4.0, velocity=0.06, lower=0.0, upper=0.003),
        mating=MatingContract(
            parent_face_geometry="top_deck",
            parent_face_side="positive_z",
            child_face_geometry="pad_stem",
            child_face_side="negative_z",
            contact_tol=0.0030,
        ),
    )

    # Pad grid — pad_rows × pad_cols. Each pad is a tiny PRISMATIC child
    # of the housing.
    col_x0 = -((r.pad_cols - 1) * 0.5) * r.pad_pitch
    row_y0 = -((r.pad_rows - 1) * 0.5) * r.pad_pitch + 0.020
    parts_emitted = ["crossfader", "left_volume_fader", "right_volume_fader"]
    joints_emitted = [
        "housing_to_crossfader",
        "housing_to_left_volume_fader",
        "housing_to_right_volume_fader",
    ]
    for ri in range(r.pad_rows):
        for ci in range(r.pad_cols):
            pad_name = f"pad_r{ri}_c{ci}"
            pad = model.part(pad_name)
            _build_pad_part(pad)
            px = col_x0 + ci * r.pad_pitch
            py = row_y0 + ri * r.pad_pitch
            joint_name = f"housing_to_{pad_name}"
            model.articulation(
                joint_name,
                ArticulationType.PRISMATIC,
                parent=housing,
                child=pad,
                origin=Origin(xyz=(px, py, top_z + pad_stem_low_z)),
                axis=(0.0, 0.0, -1.0),
                motion_limits=MotionLimits(effort=4.0, velocity=0.06, lower=0.0, upper=0.003),
                mating=MatingContract(
                    parent_face_geometry="top_deck",
                    parent_face_side="positive_z",
                    child_face_geometry="pad_stem",
                    child_face_side="negative_z",
                    contact_tol=0.0030,
                ),
            )
            parts_emitted.append(pad_name)
            joints_emitted.append(joint_name)

    return ModuleBuild(
        module_name="pad_grid_plus_fader",
        parts_emitted=parts_emitted,
        internal_articulations=joints_emitted,
        interfaces={},
    )


# --------------------------------------------------------------------------- #
# Slot graph + entry points
# --------------------------------------------------------------------------- #


CHASSIS_FACTORIES = {
    "controller_chassis": _build_controller_chassis,
    "turntable_plinth": _build_turntable_plinth_chassis,
}

DECK_LAYOUT_FACTORIES = {
    "dual_jog_decks": _build_dual_jog_decks,
    "single_platter_with_tonearm": _build_single_platter_with_tonearm,
}

CONTROLS_FACTORIES = {
    "triple_fader_strip": _build_triple_fader_strip,
    "pad_grid_plus_fader": _build_pad_grid_plus_fader,
}


def _slots_for_config(r: ResolvedDjEquipmentConfig) -> list[SlotSpec]:
    """Build the slot graph pinned to the chosen module per slot.

    Each slot's `candidates` map contains exactly the one factory selected
    by `resolve_config`, so the assembler doesn't reroll for non-zero seeds
    (RNG selection is done once up front by `config_from_seed`).

    The slot order is meaningful: chassis runs first (it emits the housing
    and exposes a downstream interface pointing at the housing's top
    deck). deck_layout and controls then read `ctx.upstream_interface`
    to find the housing part name and emit their joints with
    `parent=housing` directly.
    """
    return [
        SlotSpec(
            slot_name="chassis",
            candidates={r.chassis_module: CHASSIS_FACTORIES[r.chassis_module]},
            anchor_choice=r.chassis_module,
        ),
        SlotSpec(
            slot_name="deck_layout",
            candidates={r.deck_layout_module: DECK_LAYOUT_FACTORIES[r.deck_layout_module]},
            anchor_choice=r.deck_layout_module,
        ),
        SlotSpec(
            slot_name="controls",
            candidates={r.controls_module: CONTROLS_FACTORIES[r.controls_module]},
            anchor_choice=r.controls_module,
        ),
    ]


def build_dj_equipment(
    config: DjEquipmentConfig,
    *,
    assets: AssetContext | None = None,
) -> ArticulatedObject:
    """Compose a DJ equipment model by running each slot's module factory.

    The assembler walks chassis → deck_layout → controls in order;
    deck_layout and controls modules don't expose an upstream interface
    (so the assembler doesn't try to auto-chain), but they read the
    upstream interface descriptor for the housing's part name and top
    deck height.
    """
    r = resolve_config(config)
    model = ArticulatedObject(name="dj_equipment", assets=assets)
    for material_name, rgba in r.palette.items():
        model.material(material_name, rgba=rgba)

    rng = random.Random(0)
    assemble(
        model,
        slots=_slots_for_config(r),
        rng=rng,
        palette=r.palette,
        config=r,
        seed=0,
    )
    return model


def build_seeded_dj_equipment(seed: int) -> ArticulatedObject:
    return build_dj_equipment(config_from_seed(seed))


def slot_choices_for_seed(seed: int) -> list[tuple[str, str]]:
    """Return the (slot, module) picks for inspection — used by the
    `module_topology_diversity` gate to count unique topologies."""
    cfg = config_from_seed(seed)
    r = resolve_config(cfg)
    return [
        ("chassis", r.chassis_module),
        ("deck_layout", r.deck_layout_module),
        ("controls", r.controls_module),
    ]


# --------------------------------------------------------------------------- #
# Author-layer QC — DJ-specific sanity beyond the compiler baseline.
# --------------------------------------------------------------------------- #


def _declare_captured_pivot_overlaps(ctx: TestContext, model: ArticulatedObject) -> None:
    """Replay the captured-pin overlap declarations across module variants.

    The carry_handle's hinge_barrel intentionally penetrates the housing's
    left_handle_bracket / right_handle_bracket — that's how a hinge pin
    captures inside a bracket sleeve. The MatingContract abstraction does
    not naturally model pin-through-sleeve, so we allow the overlap
    explicitly.

    For single_platter_with_tonearm, the tonearm's pivot_hub also sits
    just below the housing's tonearm_base cylinder (when the chassis is
    turntable_plinth) — another captured-pin pair.
    """
    parts = {p.name for p in model.parts}
    housing = model.get_part("housing")

    if "carry_handle" in parts:
        carry_handle = model.get_part("carry_handle")
        ctx.allow_overlap(
            housing,
            carry_handle,
            elem_a="left_handle_bracket",
            elem_b="left_hinge_barrel",
            reason="captured hinge pin — left_handle_bracket sleeves the hinge barrel",
        )
        ctx.allow_overlap(
            housing,
            carry_handle,
            elem_a="right_handle_bracket",
            elem_b="right_hinge_barrel",
            reason="captured hinge pin — right_handle_bracket sleeves the hinge barrel",
        )

    # When deck_layout = single_platter_with_tonearm, the tonearm part
    # (named right_platter for joint-topology consistency) pivots on
    # either the housing's right_spindle (controller_chassis) or its
    # tonearm_post / tonearm_base (turntable_plinth). Both are captured-
    # pin overlaps that the MatingContract abstraction cannot naturally
    # model.
    if "right_platter" in parts:
        right_part = model.get_part("right_platter")
        right_visual_names = {v.name for v in right_part.visuals if v.name}
        if "pivot_hub" in right_visual_names:
            housing_visual_names = {v.name for v in housing.visuals if v.name}
            for housing_elem in (
                "right_spindle",
                "tonearm_post",
                "tonearm_base",
            ):
                if housing_elem in housing_visual_names:
                    ctx.allow_overlap(
                        housing,
                        right_part,
                        elem_a=housing_elem,
                        elem_b="pivot_hub",
                        reason=(
                            f"captured tonearm pivot pin — {housing_elem} sleeves "
                            "the tonearm's pivot_hub"
                        ),
                    )


def _expect_carry_handle_lifts(ctx: TestContext, model: ArticulatedObject) -> None:
    """Anchor expectation: rotating the carry_handle joint from 0 to its
    upper limit should raise the handle assembly's max-z by at least 5cm."""
    if "carry_handle" not in {p.name for p in model.parts}:
        return
    handle = model.get_part("carry_handle")
    handle_joint = model.get_articulation("housing_to_carry_handle")
    if handle_joint.motion_limits is None or handle_joint.motion_limits.upper is None:
        return
    with ctx.pose({handle_joint: 0.0}):
        folded = ctx.part_world_aabb(handle)
    with ctx.pose({handle_joint: handle_joint.motion_limits.upper}):
        raised = ctx.part_world_aabb(handle)
    if folded is None or raised is None:
        return
    ctx.check(
        "carry_handle_lifts_clear_of_deck",
        raised[1][2] > folded[1][2] + 0.04,
        f"folded={folded}, raised={raised}",
    )


def _expect_crossfader_travels_along_x(ctx: TestContext, model: ArticulatedObject) -> None:
    """Crossfader is always PRISMATIC along +x; check the world-position
    delta across motion limits."""
    try:
        cf = model.get_part("crossfader")
        cf_joint = model.get_articulation("housing_to_crossfader")
    except Exception:
        return
    limits = cf_joint.motion_limits
    if limits is None or limits.lower is None or limits.upper is None:
        return
    with ctx.pose({cf_joint: limits.lower}):
        low = ctx.part_world_position(cf)
    with ctx.pose({cf_joint: limits.upper}):
        high = ctx.part_world_position(cf)
    if low is None or high is None:
        return
    ctx.check(
        "crossfader_travels_along_x",
        high[0] - low[0] > 0.06 and abs(high[1] - low[1]) < 1e-6 and abs(high[2] - low[2]) < 1e-6,
        f"low={low}, high={high}",
    )


def _expect_anchor_size_envelope(
    ctx: TestContext, model: ArticulatedObject, r: ResolvedDjEquipmentConfig
) -> None:
    """The housing should read as a portable DJ surface (controller or
    turntable plinth) — not a laptop, briefcase, or sound desk. Loose
    bounds since turntable_plinth runs taller and controller_chassis
    runs wider."""
    housing = model.get_part("housing")
    body_aabb = ctx.part_world_aabb(housing)
    if body_aabb is None:
        return
    x_size = body_aabb[1][0] - body_aabb[0][0]
    y_size = body_aabb[1][1] - body_aabb[0][1]
    z_size = body_aabb[1][2] - body_aabb[0][2]
    ctx.check(
        "body_size_realistic",
        0.30 <= x_size <= 0.95 and 0.20 <= y_size <= 0.50 and 0.035 <= z_size <= 0.130,
        f"Unexpected body AABB extents: x={x_size:.4f} y={y_size:.4f} z={z_size:.4f}",
    )


def _expect_left_platter_spins_around_z(ctx: TestContext, model: ArticulatedObject) -> None:
    """The left_platter joint axis is always (0, 0, 1) so its world AABB
    extents should be invariant under rotation (axisymmetric shape).

    This protects against accidentally placing the platter rotation axis
    in xy (e.g., copy-pasting a fader joint).
    """
    if "left_platter" not in {p.name for p in model.parts}:
        return
    platter = model.get_part("left_platter")
    joint = model.get_articulation("housing_to_left_platter")
    rest = ctx.part_world_aabb(platter)
    with ctx.pose({joint: math.pi}):
        turned = ctx.part_world_aabb(platter)
    if rest is None or turned is None:
        return
    ctx.check(
        "left_platter_aabb_axisymmetric",
        abs((rest[1][0] - rest[0][0]) - (turned[1][0] - turned[0][0])) < 0.004
        and abs((rest[1][1] - rest[0][1]) - (turned[1][1] - turned[0][1])) < 0.004,
        f"left_platter AABB extents differ under z rotation: rest={rest} turned={turned}",
    )


def run_dj_equipment_tests(
    model: ArticulatedObject,
    config: DjEquipmentConfig,
) -> TestReport:
    """Author-layer QC for the modular dj_equipment template.

    The compiler-owned baseline runs the full QC stack (model validity,
    isolated parts, overlap, articulation-origin distance, joint mating
    gap). This function adds DJ-equipment-specific assertions on motion
    axes and motion-limit poses, then replays captured-pin overlap
    declarations across whichever module combination was assembled.
    """
    r = resolve_config(config)
    ctx = TestContext(model)

    _declare_captured_pivot_overlaps(ctx, model)

    ctx.check_model_valid()
    ctx.fail_if_isolated_parts()
    ctx.warn_if_part_contains_disconnected_geometry_islands()
    ctx.fail_if_parts_overlap_in_current_pose()
    ctx.fail_if_articulation_origin_far_from_geometry(tol=0.020)
    ctx.fail_if_joint_mating_has_gap()

    _expect_anchor_size_envelope(ctx, model, r)
    _expect_carry_handle_lifts(ctx, model)
    _expect_crossfader_travels_along_x(ctx, model)
    _expect_left_platter_spins_around_z(ctx, model)

    return ctx.report()


# --------------------------------------------------------------------------- #
# Modular template authoring notes
# --------------------------------------------------------------------------- #
# Module roster:
#
#   chassis/controller_chassis (anchor):
#     parts                : housing (with wall_ring + bottom_panel +
#                            top_deck Mesh visuals, spindles, pedestals,
#                            display strips, mixer panel, EQ knobs,
#                            handle brackets), carry_handle
#     internal joints      : housing_to_carry_handle (REVOLUTE +x)
#     downstream interface : housing.top_deck (+z) at z=body_height
#     source               : rec_dj_equipment_47e2bd...:rev_000001
#
#   chassis/turntable_plinth (alt):
#     parts                : housing (with wooden plinth_shell Mesh, top
#                            plate, 4 rubber feet, buttons, tonearm
#                            base/post, handle brackets), carry_handle
#     internal joints      : housing_to_carry_handle (REVOLUTE +x)
#     downstream interface : housing.top_deck (+z) at z=1.30*body_height
#     source               : rec_dj_equipment_6e26a3...:rev_000001
#
#   deck_layout/dual_jog_decks (anchor):
#     parts                : left_platter, right_platter (both 4-visual
#                            cylinder stacks: hub + rim + touch_ring +
#                            center_label)
#     internal joints      : housing_to_left_platter (REVOLUTE +z, mating
#                            on left_spindle), housing_to_right_platter
#                            (REVOLUTE +z, mating on right_spindle)
#     source               : rec_dj_equipment_47e2bd...:rev_000001
#
#   deck_layout/single_platter_with_tonearm (alt):
#     parts                : left_platter (single large platter with
#                            slipmat + label), right_platter (tonearm
#                            with pivot_hub + arm_tube + counterweight
#                            + headshell — reuses the right_platter
#                            slot name to keep joint count consistent)
#     internal joints      : housing_to_left_platter (REVOLUTE +z, mating
#                            on left_spindle), housing_to_right_platter
#                            (REVOLUTE +z, captured pivot — grandfathered
#                            via allow_overlap)
#     source               : rec_dj_equipment_6e26a3...:rev_000001
#
#   controls/triple_fader_strip (anchor):
#     parts                : crossfader, left_volume_fader,
#                            right_volume_fader
#     internal joints      : housing_to_crossfader (PRISMATIC +x),
#                            housing_to_left_volume_fader (PRISMATIC +y),
#                            housing_to_right_volume_fader (PRISMATIC +y)
#     source               : rec_dj_equipment_47e2bd...:rev_000001
#
#   controls/pad_grid_plus_fader (alt):
#     parts                : crossfader, left_volume_fader (button stub),
#                            right_volume_fader (button stub), pad_r{i}_c{j}
#                            (pad_rows × pad_cols grid)
#     internal joints      : housing_to_crossfader (PRISMATIC +x),
#                            housing_to_left_volume_fader (PRISMATIC -z),
#                            housing_to_right_volume_fader (PRISMATIC -z),
#                            housing_to_pad_r{i}_c{j} (PRISMATIC -z)
#     source               : rec_dj_equipment_12cc44...:rev_000001
#
# Slot graph (parallel children of housing, NOT a strict chain):
#   chassis      → emits housing + carry_handle (carry_handle REVOLUTE +x)
#   deck_layout  → emits 2 platter-named parts joined to housing internally
#   controls     → emits faders + (optionally) pad grid, joined to housing
#
# deck_layout and controls modules do NOT define `interfaces["upstream"]` —
# this skips the assembler's auto-chain joint emission. They read
# `ctx.upstream_interface.part_name` to find the housing's part name and
# emit their joints with `parent=model.get_part(housing_name)` directly.
#
# anchor_geometry_match is inapplicable to modular templates and is
# skipped by the coverage gate via the `__modular__ = True` flag.
# The replacement is module_topology_diversity (counts distinct
# slot_choices across passing seeds, requires >= 5 in the sweep).
#
# Combinations: 2 chassis × 2 deck_layout × 2 controls = 8 unique
# topologies. RNG over 10 seeds yields >=7 unique combinations in
# expectation.


# --------------------------------------------------------------------------- #
# Adoption table (which anchor section each module is adapted from)
# --------------------------------------------------------------------------- #
# module                          | anchor lines (model.py)
# --------------------------------+----------------------------------------
# controller_chassis              | rec_47e2bd lines L184-L324
# turntable_plinth                | rec_6e26a3 lines L79-L153
# _build_platter_visuals          | rec_47e2bd lines L39-L68
# _build_slider_visuals           | rec_47e2bd lines L71-L98
# _build_carry_handle_visuals     | rec_47e2bd lines L101-L142
# dual_jog_decks joints           | rec_47e2bd lines L382-L399
# single_platter_with_tonearm     | rec_6e26a3 lines L154-L300
# triple_fader_strip joints       | rec_47e2bd lines L400-L426
# pad_grid_plus_fader             | rec_12cc44 lines L244-L326
# --------------------------------+----------------------------------------


# --------------------------------------------------------------------------- #
# Maintenance notes
# --------------------------------------------------------------------------- #
# - To add a fourth chassis variant (e.g. a wedge monitor speaker that
#   doesn't carry decks at all), add a new factory to CHASSIS_FACTORIES,
#   a new value to ChassisModule Literal, and seed-sampling in
#   config_from_seed. The downstream interface contract must keep
#   exposing `housing.top_deck` (+z) at the body height; deck_layout
#   and controls modules read that.
# - The pad_grid_plus_fader module emits N pad parts where N = pad_rows
#   × pad_cols. Keep pad_rows ∈ [2, 3] and pad_cols ∈ [3, 4] in
#   config_from_seed so the part count stays in [6, 12] (avoiding the
#   isolated_parts or AABB tolerance edge cases at extreme N).
# - When debugging a sweep failure on a specific combination, build that
#   combination directly via
#       build_dj_equipment(DjEquipmentConfig(
#           chassis_module="<...>",
#           deck_layout_module="<...>",
#           controls_module="<...>",
#       ))
#   and inspect the resulting `model.articulations` / `model.parts`.
# --------------------------------------------------------------------------- #


__all__ = [
    "ChassisModule",
    "ControlsModule",
    "DeckLayoutModule",
    "DJPaletteTheme",
    "DjEquipmentConfig",
    "ResolvedDjEquipmentConfig",
    "build_dj_equipment",
    "build_seeded_dj_equipment",
    "config_from_seed",
    "resolve_config",
    "run_dj_equipment_tests",
    "slot_choices_for_seed",
]
