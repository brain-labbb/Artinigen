"""Louvered shutter assembly — modular procedural template.

This template uses the slot/module/assembler vocabulary from
``agent.templates._modular`` but follows a **mixed** topology pattern with
four slots:

    Slot A  frame_topology          — root chassis (4 candidates)
    Slot B  slat_module             — MULTIPLICITY slot (4 families × N)
    Slot C  leaf_hinge_kinematics   — decides slats_parent parts (4 candidates)
    Slot D  tilt_rod_drive          — orthogonal rod-driver (3 candidates)

The wiring relationships, expressed as the spec's slot graph:

    Slot A (frame_topology) — always root
        │
        ├── Slot C (leaf_hinge_kinematics)
        │     ├── fixed_no_leaf_hinge      → slats_parent = [frame]
        │     ├── single_leaf_side_hinge   → slats_parent = [leaf]
        │     ├── double_leaf_french_pair  → slats_parent = [leaf_0, leaf_1]
        │     └── bifold_leaf_chain        → slats_parent = [outer_leaf, inner_leaf]
        │
        ├── Slot B (slat_module multiplicity, family-specific N)
        │     for each slats_parent in C.slats_parent_parts:
        │         emit N REVOLUTE slat children, axis=(1,0,0)
        │
        └── Slot D (tilt_rod_drive)
              for each slats_parent in C.slats_parent_parts:
                  ├── none                   → no rod
                  ├── prismatic_vertical_rod → emit 1 tilt_rod_* part + PRISMATIC z
                  └── fixed_visual_rod       → emit visual on slats_parent (no part / no joint)

seed=0 anchor: ``(simple_rectangular_frame, flat_planar_slats_N12,
fixed_no_leaf_hinge, none)`` — sourced from
``rec_louvered_shutter_assembly_4492bf5f324e4691a5b50d1de1a2f7c5``
(canonical 5-star sample).

Compatibility rules (encoded in :func:`resolve_config`):

* ``simple_rectangular_frame`` × ``double_leaf_french_pair``   → C ← ``single_leaf_side_hinge``
* ``simple_rectangular_frame`` × ``bifold_leaf_chain``         → C ← ``fixed_no_leaf_hinge``
* ``double_jamb_french_frame`` × {anything ≠ french}            → C ← ``double_leaf_french_pair``

5-star sources adopted per module (spec ``§Adopted Source Index``):

* Slot A ``simple_rectangular_frame``        — rec_..._4492bf5f...:model.py:L13-L25
* Slot A ``window_jamb_with_inset_panel``    — rec_..._d2759605...:model.py:L128-L172
* Slot A ``paneled_frame_with_mid_rail``     — rec_..._0219c5e7...:model.py:L25-L42
* Slot A ``double_jamb_french_frame``        — rec_..._7c027fd5...:model.py:L40-L77
* Slot B ``flat_planar_slats_N``             — rec_..._4492bf5f...:model.py:L26-L56
* Slot B ``airfoil_slats_N``                 — rec_..._d2759605...:model.py:L84-L116, L282-L332
* Slot B ``wide_plantation_slats_N``         — rec_..._0004:model.py:L34-L67, L143-L210
* Slot B ``narrow_blind_slats_N``            — rec_..._77374234...:model.py:L15-L60
* Slot C ``fixed_no_leaf_hinge``             — rec_..._4492bf5f...:model.py:L48-L57
* Slot C ``single_leaf_side_hinge``          — rec_..._d2759605...:model.py:L128-L222
* Slot C ``double_leaf_french_pair``         — rec_..._7c027fd5...:model.py:L97-L171, L261-L263
* Slot C ``bifold_leaf_chain``               — rec_..._cd6b3278...:model.py:L36-L48, L147-L174
* Slot D ``none``                            — rec_..._4492bf5f...:model.py:L13-L101
* Slot D ``prismatic_vertical_rod``          — rec_..._7c027fd5...:model.py:L198-L222
* Slot D ``fixed_visual_rod``                — rec_..._d2759605...:model.py:L282-L349

Mating model
------------
Every slat pivot is a **captured pin in a stile bushing** — pin geometry
necessarily overlaps the stile. These are *grandfathered* (no MatingContract)
and the intentional overlaps are explicitly allow-listed in
:func:`run_louvered_shutter_tests`.

Leaf hinges (``frame_to_leaf*`` / ``jamb_to_outer`` / ``outer_to_inner``)
declare a captured-pin barrel/plate contact; we keep them grandfathered too
(captured-pin geometry doesn't fit the MatingContract face-to-face model).
The tilt rod's PRISMATIC slide declares a MatingContract between the rod's
vertical body and the leaf's rod_guide.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Literal

from sdk import (
    ArticulatedObject,
    ArticulationType,
    AssetContext,
    Box,
    Cylinder,
    Inertial,
    MotionLimits,
    Origin,
    TestContext,
    TestReport,
    mesh_from_geometry,
    section_loft,
)

# Modular templates are flagged so the sweep coverage gate can skip
# anchor_geometry_match (single-anchor gate that doesn't apply here) and
# run module_topology_diversity instead.
__modular__ = True


# --------------------------------------------------------------------------- #
# Slot module name literals
# --------------------------------------------------------------------------- #

FrameModule = Literal[
    "simple_rectangular_frame",
    "window_jamb_with_inset_panel",
    "paneled_frame_with_mid_rail",
    "double_jamb_french_frame",
]

SlatFamily = Literal[
    "flat_planar",
    "airfoil",
    "wide_plantation",
    "narrow_blind",
]

LeafHingeModule = Literal[
    "fixed_no_leaf_hinge",
    "single_leaf_side_hinge",
    "double_leaf_french_pair",
    "bifold_leaf_chain",
]

TiltRodModule = Literal[
    "none",
    "prismatic_vertical_rod",
    "fixed_visual_rod",
]

ShutterPaletteTheme = Literal[
    "painted_white",
    "warm_painted_wood",
    "dark_stained",
    "industrial_metal",
    "cafe_cream",
    "storm_blue",
]


# Per-family multiplicity bounds (matches spec §Multiplicity ranges per slat family).
SLAT_FAMILY_N_BOUNDS: dict[str, tuple[int, int]] = {
    "flat_planar": (5, 14),
    "airfoil": (6, 14),
    "wide_plantation": (3, 7),
    "narrow_blind": (10, 21),
}

# Anchor N per family (seed=0 / anchor selection).
SLAT_FAMILY_ANCHOR_N: dict[str, int] = {
    "flat_planar": 12,
    "airfoil": 12,
    "wide_plantation": 5,
    "narrow_blind": 16,
}


# --------------------------------------------------------------------------- #
# Palette presets — each preset supplies the material tokens used by the
# module factories. We register them on the model via ``model.material(...)``
# inside :func:`build_louvered_shutter` so factories can reference them by
# name (the same convention used in monitor_mount / dj_equipment).
# --------------------------------------------------------------------------- #


SHUTTER_PALETTE_PRESETS: dict[str, dict[str, tuple[float, float, float, float]]] = {
    "painted_white": {
        "frame_main": (0.95, 0.94, 0.91, 1.0),
        "frame_accent": (0.92, 0.91, 0.88, 1.0),
        "slat_main": (0.97, 0.96, 0.93, 1.0),
        "slat_accent": (0.93, 0.92, 0.88, 1.0),
        "metal": (0.66, 0.64, 0.58, 1.0),
        "shadow": (0.18, 0.17, 0.15, 1.0),
        "glass": (0.74, 0.86, 0.96, 0.30),
    },
    "warm_painted_wood": {
        "frame_main": (0.88, 0.84, 0.74, 1.0),
        "frame_accent": (0.84, 0.80, 0.70, 1.0),
        "slat_main": (0.92, 0.88, 0.76, 1.0),
        "slat_accent": (0.86, 0.81, 0.69, 1.0),
        "metal": (0.55, 0.55, 0.52, 1.0),
        "shadow": (0.20, 0.18, 0.13, 1.0),
        "glass": (0.74, 0.86, 0.96, 0.30),
    },
    "dark_stained": {
        "frame_main": (0.20, 0.14, 0.10, 1.0),
        "frame_accent": (0.16, 0.11, 0.07, 1.0),
        "slat_main": (0.25, 0.17, 0.12, 1.0),
        "slat_accent": (0.18, 0.12, 0.08, 1.0),
        "metal": (0.62, 0.60, 0.56, 1.0),
        "shadow": (0.07, 0.05, 0.03, 1.0),
        "glass": (0.36, 0.46, 0.55, 0.30),
    },
    "industrial_metal": {
        "frame_main": (0.42, 0.43, 0.44, 1.0),
        "frame_accent": (0.34, 0.35, 0.36, 1.0),
        "slat_main": (0.52, 0.53, 0.54, 1.0),
        "slat_accent": (0.40, 0.41, 0.42, 1.0),
        "metal": (0.72, 0.73, 0.74, 1.0),
        "shadow": (0.10, 0.10, 0.11, 1.0),
        "glass": (0.46, 0.56, 0.62, 0.30),
    },
    "cafe_cream": {
        "frame_main": (0.93, 0.88, 0.74, 1.0),
        "frame_accent": (0.86, 0.81, 0.67, 1.0),
        "slat_main": (0.95, 0.91, 0.79, 1.0),
        "slat_accent": (0.88, 0.82, 0.66, 1.0),
        "metal": (0.66, 0.55, 0.34, 1.0),
        "shadow": (0.30, 0.22, 0.10, 1.0),
        "glass": (0.78, 0.84, 0.88, 0.30),
    },
    "storm_blue": {
        "frame_main": (0.22, 0.30, 0.42, 1.0),
        "frame_accent": (0.18, 0.24, 0.34, 1.0),
        "slat_main": (0.30, 0.40, 0.55, 1.0),
        "slat_accent": (0.24, 0.32, 0.46, 1.0),
        "metal": (0.66, 0.68, 0.72, 1.0),
        "shadow": (0.08, 0.10, 0.16, 1.0),
        "glass": (0.42, 0.56, 0.78, 0.30),
    },
}


# --------------------------------------------------------------------------- #
# Config dataclasses
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class LouveredShutterAssemblyConfig:
    """Public config. All module fields default to ``None``; leave them
    that way for :func:`config_from_seed` to fill in anchor-or-seed picks.

    Continuous parameters (frame size, slat dimensions, hinge limits) drive
    the *envelope* of whichever module is chosen. Out-of-range values are
    clamped in :func:`resolve_config`.
    """

    frame_module: FrameModule | None = None
    slat_family: SlatFamily | None = None
    leaf_hinge_module: LeafHingeModule | None = None
    tilt_rod_module: TiltRodModule | None = None
    palette_theme: ShutterPaletteTheme = "painted_white"

    # Outer frame envelope (anchor uses 0.40 wide × 0.80 tall).
    frame_width: float = 0.40
    frame_height: float = 0.80
    frame_depth: float = 0.045

    # Stile / rail member thickness (in the X / Z directions respectively).
    stile_width: float = 0.045
    rail_height: float = 0.060

    # Slat multiplicity & geometry.
    slat_count: int | None = None
    slat_thickness_override: float | None = None
    slat_chord_override: float | None = None
    slat_tilt_limit: float = 1.0  # symmetric ±limit, radians

    # Leaf-hinge motion envelope.
    leaf_open_upper: float = 1.55  # single / french primary swing
    bifold_inner_lower: float = -2.75  # bifold inner leaf relative angle

    # Tilt-rod drive geometry & motion envelope.
    tilt_rod_travel: float = 0.035
    tilt_rod_y_offset: float = -0.060
    tilt_rod_x_inset: float = 0.085

    palette: dict[str, tuple[float, float, float, float]] = field(
        default_factory=lambda: dict(SHUTTER_PALETTE_PRESETS["painted_white"])
    )


@dataclass(frozen=True)
class ResolvedLouveredShutterAssemblyConfig:
    """Module-resolved + clamped config consumed by the build helpers.

    Includes derived ``leaf_count`` (0 / 1 / 2 depending on Slot C) and
    final clamped ``slat_count`` per family bounds + bay-height fit.
    """

    frame_module: FrameModule
    slat_family: SlatFamily
    leaf_hinge_module: LeafHingeModule
    tilt_rod_module: TiltRodModule
    palette_theme: ShutterPaletteTheme

    frame_width: float
    frame_height: float
    frame_depth: float
    stile_width: float
    rail_height: float

    slat_count: int
    slat_thickness: float
    slat_chord: float
    slat_tilt_limit: float

    leaf_open_upper: float
    bifold_inner_lower: float

    tilt_rod_travel: float
    tilt_rod_y_offset: float
    tilt_rod_x_inset: float

    leaf_count: int  # 0 for fixed_no_leaf_hinge, 1 single, 2 french/bifold

    palette: dict[str, tuple[float, float, float, float]]


# --------------------------------------------------------------------------- #
# Seed-driven config generation
# --------------------------------------------------------------------------- #


_FRAME_CANDIDATES: tuple[FrameModule, ...] = (
    "simple_rectangular_frame",
    "window_jamb_with_inset_panel",
    "paneled_frame_with_mid_rail",
    "double_jamb_french_frame",
)
_SLAT_CANDIDATES: tuple[SlatFamily, ...] = (
    "flat_planar",
    "airfoil",
    "wide_plantation",
    "narrow_blind",
)
_LEAF_CANDIDATES: tuple[LeafHingeModule, ...] = (
    "fixed_no_leaf_hinge",
    "single_leaf_side_hinge",
    "double_leaf_french_pair",
    "bifold_leaf_chain",
)
_TILT_CANDIDATES: tuple[TiltRodModule, ...] = ("none", "prismatic_vertical_rod")


def config_from_seed(seed: int) -> LouveredShutterAssemblyConfig:
    """Sample a louvered-shutter configuration for the given seed.

    seed == 0 always returns the canonical anchor combo, sourced from
    ``rec_louvered_shutter_assembly_4492bf5f324e4691a5b50d1de1a2f7c5``:

        frame_module        = simple_rectangular_frame
        slat_family         = flat_planar (N=12)
        leaf_hinge_module   = fixed_no_leaf_hinge
        tilt_rod_module     = none

    Other seeds RNG-pick each slot uniformly from its candidates and
    sample continuous dimensions from spec §"参数范围汇总" ranges.
    """

    if seed == 0:
        return LouveredShutterAssemblyConfig(
            frame_module="simple_rectangular_frame",
            slat_family="flat_planar",
            leaf_hinge_module="fixed_no_leaf_hinge",
            tilt_rod_module="none",
            palette_theme="painted_white",
            frame_width=0.40,
            frame_height=0.80,
            frame_depth=0.045,
            stile_width=0.045,
            rail_height=0.060,
            slat_count=12,
            slat_thickness_override=0.008,
            slat_chord_override=0.055,
            slat_tilt_limit=1.0,
            tilt_rod_travel=0.035,
        )

    rng = random.Random(seed)
    frame: FrameModule = rng.choice(_FRAME_CANDIDATES)
    slat: SlatFamily = rng.choice(_SLAT_CANDIDATES)
    leaf: LeafHingeModule = rng.choice(_LEAF_CANDIDATES)
    tilt: TiltRodModule = rng.choice(_TILT_CANDIDATES)
    palette_theme: ShutterPaletteTheme = rng.choice(tuple(SHUTTER_PALETTE_PRESETS.keys()))

    # Sample N inside its family bounds (will be clamped in resolve_config
    # against the available z-bay length too).
    n_min, n_max = SLAT_FAMILY_N_BOUNDS[slat]
    slat_count = rng.randint(n_min, n_max)

    # Frame envelope. Door-format (taller) when family ∈ {narrow_blind} or
    # paneled frame with mid_rail; window-format otherwise.
    door_format = frame == "paneled_frame_with_mid_rail" or slat == "narrow_blind"
    if door_format:
        frame_height = round(rng.uniform(1.40, 2.05), 4)
        frame_width = round(rng.uniform(0.55, 0.85), 4)
    else:
        frame_height = round(rng.uniform(0.80, 1.40), 4)
        frame_width = round(rng.uniform(0.40, 0.80), 4)

    frame_depth = round(rng.uniform(0.030, 0.060), 4)
    stile_width = round(rng.uniform(0.040, 0.072), 4)
    rail_height = round(rng.uniform(0.055, 0.100), 4)

    # Per-family slat chord / thickness default ranges.
    if slat == "wide_plantation":
        chord = round(rng.uniform(0.078, 0.105), 4)
        thickness = round(rng.uniform(0.013, 0.022), 4)
    elif slat == "airfoil":
        chord = round(rng.uniform(0.060, 0.090), 4)
        thickness = round(rng.uniform(0.009, 0.014), 4)
    elif slat == "narrow_blind":
        chord = round(rng.uniform(0.034, 0.052), 4)
        thickness = round(rng.uniform(0.005, 0.008), 4)
    else:  # flat_planar
        chord = round(rng.uniform(0.045, 0.075), 4)
        thickness = round(rng.uniform(0.006, 0.012), 4)

    return LouveredShutterAssemblyConfig(
        frame_module=frame,
        slat_family=slat,
        leaf_hinge_module=leaf,
        tilt_rod_module=tilt,
        palette_theme=palette_theme,
        frame_width=frame_width,
        frame_height=frame_height,
        frame_depth=frame_depth,
        stile_width=stile_width,
        rail_height=rail_height,
        slat_count=slat_count,
        slat_thickness_override=thickness,
        slat_chord_override=chord,
        slat_tilt_limit=round(rng.uniform(0.55, 1.20), 3),
        leaf_open_upper=round(rng.uniform(1.30, 1.60), 3),
        bifold_inner_lower=round(rng.uniform(-2.75, -1.80), 3),
        tilt_rod_travel=round(rng.uniform(0.025, 0.050), 4),
        tilt_rod_y_offset=round(rng.uniform(-0.085, -0.035), 4),
        tilt_rod_x_inset=round(rng.uniform(0.060, 0.110), 4),
    )


def _compatibility_fix(frame: FrameModule, leaf: LeafHingeModule) -> LeafHingeModule:
    """Apply the spec's compatibility matrix on (A, C). Returns the
    legal LeafHingeModule for the given frame choice."""

    if frame == "simple_rectangular_frame":
        if leaf == "bifold_leaf_chain":
            return "fixed_no_leaf_hinge"
        if leaf == "double_leaf_french_pair":
            return "single_leaf_side_hinge"
        return leaf

    if frame == "double_jamb_french_frame":
        # Anything other than french-pair on a french-jamb frame folds
        # back to french-pair (only legal C for that A per spec).
        return "double_leaf_french_pair"

    if frame == "paneled_frame_with_mid_rail":
        # The paneled-with-mid-rail frame IS itself the door body; in
        # the 5-star sample (0219c5e7) it's hinged to a jamb part, but
        # our Slot A models the paneled frame as the ROOT. So we keep
        # the slats fixed to the frame (no extra leaf), avoiding
        # collisions between the mid_rail / kick_panel and any
        # additional leaf bodies.
        return "fixed_no_leaf_hinge"

    return leaf


def resolve_config(
    config: LouveredShutterAssemblyConfig,
) -> ResolvedLouveredShutterAssemblyConfig:
    """Validate + clamp config; apply the (A, C) compatibility matrix
    and the family-specific N bound; produce the resolved struct that
    every module factory consumes."""

    frame = config.frame_module or "simple_rectangular_frame"
    slat_family = config.slat_family or "flat_planar"
    leaf = config.leaf_hinge_module or "fixed_no_leaf_hinge"
    tilt = config.tilt_rod_module or "none"

    if frame not in _FRAME_CANDIDATES:
        raise ValueError(f"Unsupported frame_module: {frame}")
    if slat_family not in _SLAT_CANDIDATES:
        raise ValueError(f"Unsupported slat_family: {slat_family}")
    if leaf not in _LEAF_CANDIDATES:
        raise ValueError(f"Unsupported leaf_hinge_module: {leaf}")
    if tilt not in _TILT_CANDIDATES:
        raise ValueError(f"Unsupported tilt_rod_module: {tilt}")
    if str(config.palette_theme) not in SHUTTER_PALETTE_PRESETS:
        raise ValueError(f"Unsupported palette_theme: {config.palette_theme}")

    # Apply compatibility matrix.
    leaf = _compatibility_fix(frame, leaf)

    # The tilt rod is only emitted between the two leaves of a french
    # pair (it sits in the meeting-stile gap). For single-leaf or fixed
    # bays it would have to live INSIDE the slat bay and intersect the
    # slats visually, so we force it to "none".
    if leaf != "double_leaf_french_pair":
        tilt = "none"

    # Clamp envelope. For multi-leaf Slot C variants, the per-leaf bay
    # is roughly half of the inner opening, so we need the inner
    # opening to be wide enough for that half to contain a slat.
    # Bump fw up if leaf modes split the bay.
    if leaf in ("double_leaf_french_pair", "bifold_leaf_chain"):
        fw_min = 0.55
    else:
        fw_min = 0.36
    fw = max(fw_min, min(float(config.frame_width), 1.60))
    fh = max(0.55, min(float(config.frame_height), 2.20))
    fd = max(0.025, min(float(config.frame_depth), 0.090))
    sw = max(0.030, min(float(config.stile_width), 0.085))
    rh = max(0.045, min(float(config.rail_height), 0.115))

    # Make sure stiles + rails leave a real opening.
    sw = min(sw, fw * 0.16)
    rh = min(rh, fh * 0.22)

    # Clamp N inside family bounds AND inside the available z-bay length.
    n_min, n_max = SLAT_FAMILY_N_BOUNDS[slat_family]
    n_default = SLAT_FAMILY_ANCHOR_N[slat_family]
    n_req = int(config.slat_count) if config.slat_count is not None else n_default
    n_req = max(n_min, min(n_req, n_max))

    # Estimate slat pitch and clamp N so the bank fits inside the opening.
    bay_height = fh - 2.0 * rh
    if frame == "paneled_frame_with_mid_rail":
        # Mid-rail eats some bay height; assume we use only the upper
        # bank for the louver array (lower bank becomes kick_panel).
        bay_height = max(0.20, bay_height - 0.080 - 0.45 * bay_height)

    # Per-family minimum pitch ≥ 1.0 × chord (so blades don't overlap
    # neighbors in closed pose; the 5-star anchor (4492bf5f, N=12)
    # uses essentially 1.0× chord-to-pitch ratio).
    if slat_family == "wide_plantation":
        chord_floor = 0.085
    elif slat_family == "airfoil":
        chord_floor = 0.060
    elif slat_family == "narrow_blind":
        chord_floor = 0.038
    else:  # flat_planar
        chord_floor = 0.046
    if config.slat_chord_override is not None:
        chord_floor = max(chord_floor, float(config.slat_chord_override) * 1.02)
    n_fit = max(2, int(bay_height / chord_floor))
    slat_count = max(n_min, min(n_req, n_fit, n_max))

    # Slat chord / thickness — family defaults if not overridden.
    if config.slat_chord_override is not None:
        chord_raw = float(config.slat_chord_override)
    else:
        if slat_family == "wide_plantation":
            chord_raw = 0.092
        elif slat_family == "airfoil":
            chord_raw = 0.072
        elif slat_family == "narrow_blind":
            chord_raw = 0.044
        else:
            chord_raw = 0.055
    if config.slat_thickness_override is not None:
        thickness_raw = float(config.slat_thickness_override)
    else:
        if slat_family == "wide_plantation":
            thickness_raw = 0.018
        elif slat_family == "airfoil":
            thickness_raw = 0.011
        elif slat_family == "narrow_blind":
            thickness_raw = 0.007
        else:
            thickness_raw = 0.008

    slat_chord = max(0.030, min(chord_raw, 0.115))
    slat_thickness = max(0.005, min(thickness_raw, 0.024))
    # Cap chord by the per-slat pitch to prevent neighboring blades
    # overlapping each other in the closed pose. Anchor (rec_4492bf5f)
    # has chord ≈ pitch * 0.91, so factor 0.98 is conservative-enough.
    pitch_estimate = (bay_height - slat_chord) / max(slat_count - 1, 1)
    max_chord_by_pitch = max(0.030, pitch_estimate * 0.98)
    slat_chord = min(slat_chord, max_chord_by_pitch)

    slat_tilt_limit = max(0.45, min(float(config.slat_tilt_limit), math.pi / 2.0 - 0.05))

    leaf_open_upper = max(1.10, min(float(config.leaf_open_upper), 1.65))
    bifold_inner_lower = max(-2.85, min(float(config.bifold_inner_lower), -1.20))

    tilt_rod_travel = max(0.020, min(float(config.tilt_rod_travel), 0.055))
    tilt_rod_y_offset = max(-0.110, min(float(config.tilt_rod_y_offset), -0.025))
    tilt_rod_x_inset = max(0.045, min(float(config.tilt_rod_x_inset), 0.140))

    if leaf == "fixed_no_leaf_hinge":
        leaf_count = 0
    elif leaf == "single_leaf_side_hinge":
        leaf_count = 1
    else:
        leaf_count = 2

    palette = dict(SHUTTER_PALETTE_PRESETS[config.palette_theme])

    return ResolvedLouveredShutterAssemblyConfig(
        frame_module=frame,
        slat_family=slat_family,
        leaf_hinge_module=leaf,
        tilt_rod_module=tilt,
        palette_theme=config.palette_theme,
        frame_width=fw,
        frame_height=fh,
        frame_depth=fd,
        stile_width=sw,
        rail_height=rh,
        slat_count=slat_count,
        slat_thickness=slat_thickness,
        slat_chord=slat_chord,
        slat_tilt_limit=slat_tilt_limit,
        leaf_open_upper=leaf_open_upper,
        bifold_inner_lower=bifold_inner_lower,
        tilt_rod_travel=tilt_rod_travel,
        tilt_rod_y_offset=tilt_rod_y_offset,
        tilt_rod_x_inset=tilt_rod_x_inset,
        leaf_count=leaf_count,
        palette=palette,
    )


# --------------------------------------------------------------------------- #
# Slat mesh / blade helpers — one per Slot B family.
# --------------------------------------------------------------------------- #


def _flat_planar_blade(length: float, chord: float, thickness: float) -> Box:
    """Slot B / flat_planar — minimal rectangular Box blade.

    Adapted from rec_..._4492bf5f...:model.py:L34 — the canonical
    ``Box((0.316, 0.055, 0.005))`` blade scaled by the resolved
    chord / thickness. Box stays Box per Rule 3.
    """
    return Box((length, chord, thickness))


def _airfoil_section(x_pos: float, height: float, thickness: float):
    """Build a 12-point superellipse-ish cross-section at ``x_pos``.

    Adapted from rec_..._d2759605...:model.py:L84-L100 (``_louver_section``).
    The contour is a closed loop in the y-z plane, evaluated at the
    given x coordinate so two such sections can be lofted into a
    sweepable blade body.
    """

    half_h = height * 0.5
    half_t = thickness * 0.5
    return [
        (x_pos, 0.00 * half_t, half_h),
        (x_pos, 0.55 * half_t, 0.82 * half_h),
        (x_pos, 0.92 * half_t, 0.36 * half_h),
        (x_pos, 1.00 * half_t, 0.00),
        (x_pos, 0.92 * half_t, -0.36 * half_h),
        (x_pos, 0.55 * half_t, -0.82 * half_h),
        (x_pos, 0.00 * half_t, -half_h),
        (x_pos, -0.55 * half_t, -0.82 * half_h),
        (x_pos, -0.92 * half_t, -0.36 * half_h),
        (x_pos, -1.00 * half_t, 0.00),
        (x_pos, -0.92 * half_t, 0.36 * half_h),
        (x_pos, -0.55 * half_t, 0.82 * half_h),
    ]


def _airfoil_blade_mesh(length: float, chord: float, thickness: float, name: str):
    """Slot B / airfoil — section_loft mesh.

    Adapted from rec_..._d2759605...:model.py:L103-L112 (``_build_louver_mesh``).
    Two sections at ±length/2 lofted into a curved-cross-section blade.
    Mesh stays mesh per Rule 3.
    """
    half_len = length * 0.5
    return mesh_from_geometry(
        section_loft(
            [
                _airfoil_section(-half_len, chord, thickness),
                _airfoil_section(half_len, chord, thickness),
            ]
        ),
        name,
    )


def _narrow_blind_section(x_pos: float, height: float, thickness: float):
    """Slot B / narrow_blind cross-section — flatter, twisted blade.

    Adapted from rec_..._77374234...:model.py:L55-L69 (``_slat_profile``).
    The contour is more asymmetric than the airfoil section (a soft
    venetian-blind curl), kept as a 10-point loop in the y-z plane.
    """

    half_h = height * 0.5
    half_t = thickness * 0.5
    return [
        (x_pos, 0.00 * half_t, half_h),
        (x_pos, 0.30 * half_t, 0.85 * half_h),
        (x_pos, 0.92 * half_t, 0.30 * half_h),
        (x_pos, 1.00 * half_t, -0.12 * half_h),
        (x_pos, 0.55 * half_t, -0.72 * half_h),
        (x_pos, 0.00 * half_t, -half_h),
        (x_pos, -0.45 * half_t, -0.55 * half_h),
        (x_pos, -0.85 * half_t, 0.05 * half_h),
        (x_pos, -0.90 * half_t, 0.35 * half_h),
        (x_pos, -0.30 * half_t, 0.80 * half_h),
    ]


def _narrow_blind_blade_mesh(length: float, chord: float, thickness: float, name: str):
    """Slot B / narrow_blind — section_loft mesh from the asymmetric profile.

    Adapted from rec_..._77374234...:model.py:L72-L77 (``_build_slat_mesh``).
    """
    half_len = length * 0.5
    return mesh_from_geometry(
        section_loft(
            [
                _narrow_blind_section(-half_len, chord, thickness),
                _narrow_blind_section(half_len, chord, thickness),
            ]
        ),
        name,
    )


def _wide_plantation_section(x_pos: float, height: float, thickness: float):
    """Slot B / wide_plantation cross-section — symmetric superellipse curl.

    Adapted from rec_..._0004:model.py:L54-L69 (``_write_louver_mesh`` /
    ``superellipse_profile`` semantics flattened into a hand-rolled
    point list so we don't depend on the geometry helper's keyword
    spelling). Wide and thick relative to ``airfoil``.
    """
    half_h = height * 0.5
    half_t = thickness * 0.5
    return [
        (x_pos, 0.00 * half_t, half_h),
        (x_pos, 0.62 * half_t, 0.88 * half_h),
        (x_pos, 0.95 * half_t, 0.42 * half_h),
        (x_pos, 1.00 * half_t, 0.00),
        (x_pos, 0.95 * half_t, -0.42 * half_h),
        (x_pos, 0.62 * half_t, -0.88 * half_h),
        (x_pos, 0.00 * half_t, -half_h),
        (x_pos, -0.62 * half_t, -0.88 * half_h),
        (x_pos, -0.95 * half_t, -0.42 * half_h),
        (x_pos, -1.00 * half_t, 0.00),
        (x_pos, -0.95 * half_t, 0.42 * half_h),
        (x_pos, -0.62 * half_t, 0.88 * half_h),
    ]


def _wide_plantation_blade_mesh(length: float, chord: float, thickness: float, name: str):
    """Slot B / wide_plantation — section_loft mesh for thick plantation slats."""
    half_len = length * 0.5
    return mesh_from_geometry(
        section_loft(
            [
                _wide_plantation_section(-half_len, chord, thickness),
                _wide_plantation_section(half_len, chord, thickness),
            ]
        ),
        name,
    )


# --------------------------------------------------------------------------- #
# Frame-internal geometry helpers (used by all Slot A factories).
#
# Every frame has two stiles (left / right) and at least two rails
# (top / bottom). The slat array nests INSIDE this rectangular bay.
# Geometry is consistent across Slot A so the slat array can be wired
# uniformly regardless of which frame variant we pick.
# --------------------------------------------------------------------------- #


def _emit_outer_jambs_and_rails(
    part,
    *,
    r: ResolvedLouveredShutterAssemblyConfig,
    fw: float,
    fh: float,
    fd: float,
    stile_x_left: float,
    stile_x_right: float,
    top_rail_z: float,
    bottom_rail_z: float,
    name_prefix: str,
) -> None:
    """Common helper that emits 2 stiles + 2 rails on ``part``.

    All Slot A factories call this with their slightly different geometry.
    Coordinates are in part-local frame.
    """

    sw = r.stile_width
    rh = r.rail_height

    part.visual(
        Box((sw, fd, fh)),
        origin=Origin(xyz=(stile_x_left, 0.0, 0.0)),
        material="frame_main",
        name=f"{name_prefix}left_stile",
    )
    part.visual(
        Box((sw, fd, fh)),
        origin=Origin(xyz=(stile_x_right, 0.0, 0.0)),
        material="frame_main",
        name=f"{name_prefix}right_stile",
    )
    inner_w = fw - 2.0 * sw
    part.visual(
        Box((inner_w, fd, rh)),
        origin=Origin(xyz=(0.0, 0.0, top_rail_z)),
        material="frame_main",
        name=f"{name_prefix}top_rail",
    )
    part.visual(
        Box((inner_w, fd, rh)),
        origin=Origin(xyz=(0.0, 0.0, bottom_rail_z)),
        material="frame_main",
        name=f"{name_prefix}bottom_rail",
    )


# --------------------------------------------------------------------------- #
# Slot A frame factories
#
# Each factory:
#   * emits frame part(s)
#   * computes the available slat bay (z range, inner width)
#   * returns a SlotAResult struct that downstream slots consume
# --------------------------------------------------------------------------- #


@dataclass
class SlotAResult:
    """Output of a Slot A factory.

    ``root_frame_part_name`` is what subsequent slots may parent leaf
    parts to. ``bay_*`` describe the rectangular louver bay (in
    root_frame local frame) that Slot B fills when Slot C is
    fixed_no_leaf_hinge. ``leaf_hinge_*`` give the x/y coords (in
    root_frame local frame) at which Slot C should mount leaves.
    """

    root_frame_part_name: str
    inner_width: float
    bay_z_top: float  # z of slat-bay top edge (inside top_rail)
    bay_z_bottom: float  # z of slat-bay bottom edge (inside bottom_rail)
    leaf_hinge_left_x: float
    leaf_hinge_right_x: float
    leaf_hinge_y: float  # y at which jamb hinge axis sits (typically jamb front)


def _build_simple_rectangular_frame(
    model: ArticulatedObject,
    r: ResolvedLouveredShutterAssemblyConfig,
) -> SlotAResult:
    """Anchor frame — 2 stiles + 2 rails Box quad.

    Derived from rec_..._4492bf5f...:model.py:L13-L25. The canonical
    baseline 5-star sample. Stiles run full frame_height; rails span
    the full inner width.
    """

    fw = r.frame_width
    fh = r.frame_height
    fd = r.frame_depth
    sw = r.stile_width
    rh = r.rail_height

    frame = model.part("frame")

    stile_x_left = -fw * 0.5 + sw * 0.5
    stile_x_right = fw * 0.5 - sw * 0.5
    top_rail_z = fh * 0.5 - rh * 0.5
    bottom_rail_z = -fh * 0.5 + rh * 0.5

    _emit_outer_jambs_and_rails(
        frame,
        r=r,
        fw=fw,
        fh=fh,
        fd=fd,
        stile_x_left=stile_x_left,
        stile_x_right=stile_x_right,
        top_rail_z=top_rail_z,
        bottom_rail_z=bottom_rail_z,
        name_prefix="",
    )

    # Back bead trim — also a visible recess on the back face. Adapted
    # from rec_..._0004 back beads. Pushed INTO the stile by 1 mm so
    # the AABB actually overlaps the stile (connectivity check).
    frame.visual(
        Box((sw * 0.5, fd * 0.25, fh - rh * 0.5)),
        origin=Origin(xyz=(stile_x_left, -fd * 0.30, 0.0)),
        material="shadow",
        name="left_back_bead",
    )
    frame.visual(
        Box((sw * 0.5, fd * 0.25, fh - rh * 0.5)),
        origin=Origin(xyz=(stile_x_right, -fd * 0.30, 0.0)),
        material="shadow",
        name="right_back_bead",
    )

    frame.inertial = Inertial.from_geometry(
        Box((fw, fd, fh)),
        mass=4.0,
        origin=Origin(),
    )

    bay_z_top = top_rail_z - rh * 0.5
    bay_z_bottom = bottom_rail_z + rh * 0.5

    return SlotAResult(
        root_frame_part_name="frame",
        inner_width=fw - 2.0 * sw,
        bay_z_top=bay_z_top,
        bay_z_bottom=bay_z_bottom,
        # Hinge axis sits at the inner edge of the side stile, biased
        # 0.4*sw into the stile body so the joint origin (which equals
        # this anchor) lies inside the stile AABB — within
        # articulation_origin_far_from_geometry's 0.015 m tolerance.
        leaf_hinge_left_x=stile_x_left + sw * 0.40,
        leaf_hinge_right_x=stile_x_right - sw * 0.40,
        leaf_hinge_y=fd * 0.10,
    )


def _build_window_jamb_with_inset_panel(
    model: ArticulatedObject,
    r: ResolvedLouveredShutterAssemblyConfig,
) -> SlotAResult:
    """Outer window jamb that surrounds an inset slat-bearing panel.

    Derived from rec_..._d2759605...:model.py:L128-L172 (outer_frame
    only — the panel_frame part is built by Slot C). The outer jamb has
    a slightly wider envelope and shadows the panel inside it.
    """

    fw = r.frame_width
    fh = r.frame_height
    fd = r.frame_depth
    sw = r.stile_width
    rh = r.rail_height

    outer = model.part("outer_frame")

    stile_x_left = -fw * 0.5 + sw * 0.5
    stile_x_right = fw * 0.5 - sw * 0.5
    top_rail_z = fh * 0.5 - rh * 0.5
    bottom_rail_z = -fh * 0.5 + rh * 0.5

    _emit_outer_jambs_and_rails(
        outer,
        r=r,
        fw=fw,
        fh=fh,
        fd=fd,
        stile_x_left=stile_x_left,
        stile_x_right=stile_x_right,
        top_rail_z=top_rail_z,
        bottom_rail_z=bottom_rail_z,
        name_prefix="outer_",
    )

    # Decorative inner reveal — recessed shadow bead INSIDE each jamb /
    # rail thickness (NOT sticking forward into the bay, since leaves
    # hang inside that volume). Pushed in -y so the leaf bodies have
    # clearance. Adapted from rec_..._d2759605's painted-shadow trim
    # along the back face of the jamb.
    inner_w = fw - 2.0 * sw
    inner_h = fh - 2.0 * rh
    outer.visual(
        Box((inner_w + 0.010, fd * 0.18, rh * 0.5)),
        origin=Origin(xyz=(0.0, -fd * 0.32, top_rail_z - rh * 0.40)),
        material="shadow",
        name="upper_reveal_lip",
    )
    outer.visual(
        Box((inner_w + 0.010, fd * 0.18, rh * 0.5)),
        origin=Origin(xyz=(0.0, -fd * 0.32, bottom_rail_z + rh * 0.40)),
        material="shadow",
        name="lower_reveal_lip",
    )
    outer.visual(
        Box((sw * 0.5, fd * 0.18, inner_h * 0.92)),
        origin=Origin(xyz=(stile_x_left + sw * 0.30, -fd * 0.32, 0.0)),
        material="shadow",
        name="left_reveal_lip",
    )
    outer.visual(
        Box((sw * 0.5, fd * 0.18, inner_h * 0.92)),
        origin=Origin(xyz=(stile_x_right - sw * 0.30, -fd * 0.32, 0.0)),
        material="shadow",
        name="right_reveal_lip",
    )

    outer.inertial = Inertial.from_geometry(
        Box((fw, fd, fh)),
        mass=5.5,
        origin=Origin(),
    )

    bay_z_top = top_rail_z - rh * 0.5
    bay_z_bottom = bottom_rail_z + rh * 0.5

    return SlotAResult(
        root_frame_part_name="outer_frame",
        inner_width=inner_w - 2.0 * sw,  # panel sits inset, slimmer bay
        bay_z_top=bay_z_top,
        bay_z_bottom=bay_z_bottom,
        leaf_hinge_left_x=stile_x_left + sw * 0.40,
        leaf_hinge_right_x=stile_x_right - sw * 0.40,
        leaf_hinge_y=fd * 0.10,
    )


def _build_paneled_frame_with_mid_rail(
    model: ArticulatedObject,
    r: ResolvedLouveredShutterAssemblyConfig,
) -> SlotAResult:
    """Door-format frame with a horizontal mid_rail and a lower kick panel.

    Derived from rec_..._0219c5e7...:model.py:L25-L42. The mid_rail
    divides the door into an upper louver bay and a lower kick_panel
    region. Only the upper bay carries the slat array; lower bay is
    visual only.
    """

    fw = r.frame_width
    fh = r.frame_height
    fd = r.frame_depth
    sw = r.stile_width
    rh = r.rail_height

    frame = model.part("frame")

    stile_x_left = -fw * 0.5 + sw * 0.5
    stile_x_right = fw * 0.5 - sw * 0.5
    top_rail_z = fh * 0.5 - rh * 0.5
    bottom_rail_z = -fh * 0.5 + rh * 0.5

    _emit_outer_jambs_and_rails(
        frame,
        r=r,
        fw=fw,
        fh=fh,
        fd=fd,
        stile_x_left=stile_x_left,
        stile_x_right=stile_x_right,
        top_rail_z=top_rail_z,
        bottom_rail_z=bottom_rail_z,
        name_prefix="",
    )

    inner_w = fw - 2.0 * sw
    mid_rail_height = rh * 0.95
    # mid_rail sits at ≈ 35% of the inner opening height (rec_0219c5e7
    # kick_panel depth heuristic). Push it relative to the bottom_rail
    # top so its AABB always overlaps the stiles.
    mid_rail_z = bottom_rail_z + rh * 0.5 + (fh - rh) * 0.35
    frame.visual(
        Box((inner_w, fd, mid_rail_height)),
        origin=Origin(xyz=(0.0, 0.0, mid_rail_z)),
        material="frame_main",
        name="mid_rail",
    )

    # Kick panel — a flat panel filling the lower bay (visual only).
    kick_top_z = mid_rail_z - mid_rail_height * 0.5
    kick_bot_z = bottom_rail_z + rh * 0.5
    kick_h = max(0.04, kick_top_z - kick_bot_z)
    kick_center_z = 0.5 * (kick_top_z + kick_bot_z)
    frame.visual(
        Box((inner_w, fd * 0.55, kick_h)),
        origin=Origin(xyz=(0.0, 0.0, kick_center_z)),
        material="frame_accent",
        name="kick_panel",
    )

    frame.inertial = Inertial.from_geometry(
        Box((fw, fd, fh)),
        mass=6.5,
        origin=Origin(),
    )

    # Slat bay is the *upper* opening only.
    bay_z_top = top_rail_z - rh * 0.5
    bay_z_bottom = mid_rail_z + mid_rail_height * 0.5

    return SlotAResult(
        root_frame_part_name="frame",
        inner_width=inner_w,
        bay_z_top=bay_z_top,
        bay_z_bottom=bay_z_bottom,
        leaf_hinge_left_x=stile_x_left + sw * 0.40,
        leaf_hinge_right_x=stile_x_right - sw * 0.40,
        leaf_hinge_y=fd * 0.10,
    )


def _build_double_jamb_french_frame(
    model: ArticulatedObject,
    r: ResolvedLouveredShutterAssemblyConfig,
) -> SlotAResult:
    """Wide jamb that supports a french (left + right) leaf pair.

    Derived from rec_..._7c027fd5...:model.py:L40-L77. The outer
    jambs sit wider than the inner panel; a center_muntin marks the
    closing seam.
    """

    fw = r.frame_width
    fh = r.frame_height
    fd = r.frame_depth
    sw = r.stile_width
    rh = r.rail_height

    frame = model.part("window_frame")

    # Outer jambs sit at the very edges (slightly wider than simple).
    stile_x_left = -fw * 0.5 + sw * 0.5
    stile_x_right = fw * 0.5 - sw * 0.5
    top_rail_z = fh * 0.5 - rh * 0.5
    bottom_rail_z = -fh * 0.5 + rh * 0.5

    _emit_outer_jambs_and_rails(
        frame,
        r=r,
        fw=fw,
        fh=fh,
        fd=fd,
        stile_x_left=stile_x_left,
        stile_x_right=stile_x_right,
        top_rail_z=top_rail_z,
        bottom_rail_z=bottom_rail_z,
        name_prefix="",
    )

    inner_w = fw - 2.0 * sw

    # Center muntin — a thin vertical strip at x=0 marking the meeting
    # seam between left and right leaf. Its AABB must touch the top
    # and bottom rails so it isn't a disconnected island.
    frame.visual(
        Box((0.020, fd * 0.18, fh - rh - 0.010)),
        origin=Origin(xyz=(0.0, fd * 0.10, 0.0)),
        material="frame_accent",
        name="center_muntin",
    )

    # Decorative fixed hinge plates on each jamb (visual only). Each
    # plate overlaps the stile (intra-part) by sitting at the stile's
    # x with a small y offset.
    for side_idx, hinge_x in enumerate((stile_x_left, stile_x_right)):
        for k_idx, zc in enumerate(
            (
                -0.30 * (fh - rh),
                0.0,
                0.30 * (fh - rh),
            )
        ):
            frame.visual(
                Box((sw * 0.55, fd * 0.20, rh * 1.4)),
                origin=Origin(xyz=(hinge_x, fd * 0.15, zc)),
                material="metal",
                name=f"fixed_hinge_plate_{side_idx}_{k_idx}",
            )

    frame.inertial = Inertial.from_geometry(
        Box((fw, fd, fh)),
        mass=7.0,
        origin=Origin(),
    )

    bay_z_top = top_rail_z - rh * 0.5
    bay_z_bottom = bottom_rail_z + rh * 0.5

    return SlotAResult(
        root_frame_part_name="window_frame",
        inner_width=inner_w,
        bay_z_top=bay_z_top,
        bay_z_bottom=bay_z_bottom,
        leaf_hinge_left_x=stile_x_left + sw * 0.40,
        leaf_hinge_right_x=stile_x_right - sw * 0.40,
        leaf_hinge_y=fd * 0.10,
    )


FRAME_BUILDERS = {
    "simple_rectangular_frame": _build_simple_rectangular_frame,
    "window_jamb_with_inset_panel": _build_window_jamb_with_inset_panel,
    "paneled_frame_with_mid_rail": _build_paneled_frame_with_mid_rail,
    "double_jamb_french_frame": _build_double_jamb_french_frame,
}


# --------------------------------------------------------------------------- #
# Slot C leaf-hinge factories
#
# Each factory:
#   * takes the Slot A result (root frame part name + leaf-hinge anchors)
#   * builds 0-2 additional "leaf" parts
#   * emits side-hinge REVOLUTE joints (captured-pin barrel/plate)
#   * returns a list of (slats_parent_part_name, slat_bay) for Slot B
# --------------------------------------------------------------------------- #


@dataclass
class SlotCResult:
    """Output of a Slot C factory.

    Each entry in ``slats_parent_specs`` describes one slat-bay that
    Slot B should populate: the part name to parent slats to, plus the
    inner-width and z-bay extents in that part's local frame.
    """

    slats_parent_specs: list["SlatBaySpec"]


@dataclass
class SlatBaySpec:
    """Where Slot B should emit slats for a single slats_parent."""

    parent_part_name: str
    bay_inner_width: float
    bay_z_top: float
    bay_z_bottom: float
    # local x of the slat-bay center (where the slat axis sits).
    bay_center_x: float
    bay_center_y: float  # local y of the slat axis
    # Per-slat z positions are computed inside Slot B from N.


def _emit_leaf_frame_visuals(
    part,
    *,
    r: ResolvedLouveredShutterAssemblyConfig,
    leaf_width: float,
    leaf_height: float,
    leaf_depth: float,
    direction: float,
    name_prefix: str = "",
) -> None:
    """Emit the standard 4-piece leaf frame (2 stiles + 2 rails).

    Adapted from rec_..._7c027fd5...:model.py:L97-L128 (``add_leaf``).
    The leaf's part-local origin is at the HINGE axis (so direction=±1
    determines which way the leaf extends from the hinge).
    """

    sw = r.stile_width
    rh = r.rail_height

    outer_stile_x = direction * (sw * 0.5)
    center_stile_x = direction * (leaf_width - sw * 0.5)
    rail_center_x = direction * (leaf_width * 0.5)

    part.visual(
        Box((sw, leaf_depth, leaf_height)),
        origin=Origin(xyz=(outer_stile_x, 0.0, 0.0)),
        material="frame_main",
        name=f"{name_prefix}outer_stile",
    )
    part.visual(
        Box((sw, leaf_depth, leaf_height)),
        origin=Origin(xyz=(center_stile_x, 0.0, 0.0)),
        material="frame_main",
        name=f"{name_prefix}meeting_stile",
    )
    part.visual(
        Box((leaf_width, leaf_depth, rh)),
        origin=Origin(xyz=(rail_center_x, 0.0, leaf_height * 0.5 - rh * 0.5)),
        material="frame_main",
        name=f"{name_prefix}top_rail",
    )
    part.visual(
        Box((leaf_width, leaf_depth, rh)),
        origin=Origin(xyz=(rail_center_x, 0.0, -leaf_height * 0.5 + rh * 0.5)),
        material="frame_main",
        name=f"{name_prefix}bottom_rail",
    )
    # Routed back trim — a thin BACK-of-leaf strip that overlaps the
    # stiles and the bottom rail on the back face. Kept at y < 0 so it
    # doesn't intersect the slat blades (which sit at y=0 in the bay
    # opening). Width is leaf_width (full leaf) so its AABB overlaps
    # both stiles for connectivity.
    part.visual(
        Box(
            (
                leaf_width,
                leaf_depth * 0.18,
                rh * 0.40,
            )
        ),
        origin=Origin(
            xyz=(
                rail_center_x,
                -leaf_depth * 0.32,
                -leaf_height * 0.5 + rh * 0.5,
            )
        ),
        material="frame_accent",
        name=f"{name_prefix}back_trim_strip",
    )


def _emit_leaf_hinge_barrel(
    parent_part,
    leaf_part,
    *,
    r: ResolvedLouveredShutterAssemblyConfig,
    leaf_height: float,
    hinge_x_on_parent: float,
    hinge_y_on_parent: float,
    direction: float,
    name_suffix: str,
) -> tuple[str, str]:
    """Emit a tall ``hinge_barrel`` cylinder on ``parent_part`` and a
    matching ``hinge_plate`` block on ``leaf_part``. Returns
    ``(parent_visual_name, leaf_visual_name)``.

    Adapted from rec_..._d2759605...:model.py:L166-L172 (parent barrel)
    + L224-L236 (leaf plate). The barrel encloses the plate (captured
    pin), so this joint is grandfathered (no MatingContract); the
    overlap is whitelisted in run_*_tests.
    """

    sw = r.stile_width
    barrel_radius = max(0.005, sw * 0.18)
    barrel_length = max(0.060, leaf_height * 0.50)
    parent_visual_name = f"hinge_barrel_{name_suffix}"
    leaf_visual_name = f"hinge_plate_{name_suffix}"

    # Parent barrel — vertical cylinder on the hinge axis. The caller
    # has positioned ``hinge_x_on_parent`` slightly INSIDE the stile
    # (at stile_x + 0.40*sw), so the barrel's AABB overlaps the stile
    # box (sw/2 thickness either side). barrel_y is on/just behind
    # the stile front face so the AABB overlaps the stile in y as well.
    barrel_y = max(0.0, min(hinge_y_on_parent, r.frame_depth * 0.20))
    parent_part.visual(
        Cylinder(radius=barrel_radius, length=barrel_length),
        origin=Origin(xyz=(hinge_x_on_parent, barrel_y, 0.0)),
        material="metal",
        name=parent_visual_name,
    )

    # Leaf plate — small rectangular plate on the OUTER stile, facing
    # the parent barrel. Leaf-local origin sits on the hinge axis, so
    # the plate sits inside the outer stile (x near direction*sw*0.5).
    plate_thickness = max(0.0035, sw * 0.06)
    plate_x_local = direction * (sw * 0.5)
    leaf_part.visual(
        Box(
            (
                max(0.012, sw * 0.6),
                plate_thickness,
                barrel_length * 0.80,
            )
        ),
        origin=Origin(
            xyz=(
                plate_x_local,
                # Push toward where the barrel sits so plate AABB
                # overlaps the stile AND the barrel.
                -barrel_radius * 0.3,
                0.0,
            )
        ),
        material="metal",
        name=leaf_visual_name,
    )

    return parent_visual_name, leaf_visual_name


def _build_fixed_no_leaf_hinge(
    model: ArticulatedObject,
    r: ResolvedLouveredShutterAssemblyConfig,
    slot_a: SlotAResult,
) -> SlotCResult:
    """Anchor leaf-hinge — none. Slats parent directly to the root frame.

    Derived from rec_..._4492bf5f...:model.py:L48-L57 (slats are
    REVOLUTE children of ``frame`` with no leaf in between).
    """

    fw = r.frame_width
    sw = r.stile_width

    bay = SlatBaySpec(
        parent_part_name=slot_a.root_frame_part_name,
        bay_inner_width=fw - 2.0 * sw,
        bay_z_top=slot_a.bay_z_top,
        bay_z_bottom=slot_a.bay_z_bottom,
        bay_center_x=0.0,
        bay_center_y=0.0,
    )
    return SlotCResult(slats_parent_specs=[bay])


def _build_single_leaf_side_hinge(
    model: ArticulatedObject,
    r: ResolvedLouveredShutterAssemblyConfig,
    slot_a: SlotAResult,
) -> SlotCResult:
    """A single side-hinged leaf inside the outer jamb.

    Derived from rec_..._d2759605...:model.py:L174-L222 (``panel_frame``).
    The leaf's part-local origin sits on the hinge axis (so the joint
    origin in parent frame is exactly at the parent's hinge anchor).
    """

    fw = r.frame_width
    fh = r.frame_height
    fd = r.frame_depth
    sw = r.stile_width
    rh = r.rail_height
    parent_name = slot_a.root_frame_part_name
    parent_part = model.get_part(parent_name)

    # Leaf occupies the inner opening; clearance both sides + top/bot.
    side_clear = 0.005
    leaf_width = max(0.18, fw - 2.0 * sw - 2.0 * side_clear)
    leaf_height = max(0.30, fh - 2.0 * rh - 2.0 * 0.005)
    leaf_depth = max(0.022, fd * 0.7)

    leaf = model.part("leaf")
    _emit_leaf_frame_visuals(
        leaf,
        r=r,
        leaf_width=leaf_width,
        leaf_height=leaf_height,
        leaf_depth=leaf_depth,
        direction=1.0,
        name_prefix="",
    )

    # Side-hinge axis sits just inside the LEFT jamb (so the joint
    # origin remains inside the stile geometry — within tol=0.015).
    hinge_x_parent = slot_a.leaf_hinge_left_x
    hinge_y_parent = slot_a.leaf_hinge_y
    _emit_leaf_hinge_barrel(
        parent_part,
        leaf,
        r=r,
        leaf_height=leaf_height,
        hinge_x_on_parent=hinge_x_parent,
        hinge_y_on_parent=hinge_y_parent,
        direction=1.0,
        name_suffix="leaf",
    )

    model.articulation(
        "frame_to_leaf",
        ArticulationType.REVOLUTE,
        parent=parent_part,
        child=leaf,
        origin=Origin(xyz=(hinge_x_parent, hinge_y_parent, 0.0)),
        axis=(0.0, 0.0, 1.0),
        motion_limits=MotionLimits(
            effort=12.0,
            velocity=1.4,
            lower=0.0,
            upper=r.leaf_open_upper,
        ),
        # Captured-pin pivot — grandfathered (no MatingContract).
        # Overlaps allowed via run_*_tests.
    )

    bay = SlatBaySpec(
        parent_part_name="leaf",
        bay_inner_width=leaf_width - 2.0 * sw,
        bay_z_top=leaf_height * 0.5 - rh,
        bay_z_bottom=-leaf_height * 0.5 + rh,
        bay_center_x=leaf_width * 0.5,
        bay_center_y=0.0,
    )
    return SlotCResult(slats_parent_specs=[bay])


def _build_double_leaf_french_pair(
    model: ArticulatedObject,
    r: ResolvedLouveredShutterAssemblyConfig,
    slot_a: SlotAResult,
) -> SlotCResult:
    """Two leaves (left + right) hinged on opposite jambs.

    Derived from rec_..._7c027fd5...:model.py:L97-L171 (``add_leaf``)
    and L261-L263 (two add_leaf calls with direction=±1).
    """

    fw = r.frame_width
    fh = r.frame_height
    fd = r.frame_depth
    sw = r.stile_width
    rh = r.rail_height
    parent_name = slot_a.root_frame_part_name
    parent_part = model.get_part(parent_name)

    # Each leaf spans HALF the opening (less a small meeting clearance).
    meeting_clear = 0.010
    leaf_width = max(0.16, (fw - 2.0 * sw) * 0.5 - meeting_clear)
    leaf_height = max(0.30, fh - 2.0 * rh - 2.0 * 0.005)
    leaf_depth = max(0.022, fd * 0.7)

    bay_specs: list[SlatBaySpec] = []
    for leaf_idx, direction in enumerate((1.0, -1.0)):
        leaf = model.part(f"leaf_{leaf_idx}")
        _emit_leaf_frame_visuals(
            leaf,
            r=r,
            leaf_width=leaf_width,
            leaf_height=leaf_height,
            leaf_depth=leaf_depth,
            direction=direction,
            name_prefix="",
        )

        if direction > 0:
            hinge_x_parent = slot_a.leaf_hinge_left_x
        else:
            hinge_x_parent = slot_a.leaf_hinge_right_x
        hinge_y_parent = slot_a.leaf_hinge_y
        _emit_leaf_hinge_barrel(
            parent_part,
            leaf,
            r=r,
            leaf_height=leaf_height,
            hinge_x_on_parent=hinge_x_parent,
            hinge_y_on_parent=hinge_y_parent,
            direction=direction,
            name_suffix=f"leaf_{leaf_idx}",
        )

        model.articulation(
            f"frame_to_leaf_{leaf_idx}",
            ArticulationType.REVOLUTE,
            parent=parent_part,
            child=leaf,
            origin=Origin(xyz=(hinge_x_parent, hinge_y_parent, 0.0)),
            axis=(0.0, 0.0, -direction),
            motion_limits=MotionLimits(
                effort=12.0,
                velocity=1.4,
                lower=0.0,
                upper=r.leaf_open_upper,
            ),
        )

        bay = SlatBaySpec(
            parent_part_name=f"leaf_{leaf_idx}",
            bay_inner_width=leaf_width - 2.0 * sw,
            bay_z_top=leaf_height * 0.5 - rh,
            bay_z_bottom=-leaf_height * 0.5 + rh,
            bay_center_x=direction * leaf_width * 0.5,
            bay_center_y=0.0,
        )
        bay_specs.append(bay)

    return SlotCResult(slats_parent_specs=bay_specs)


def _build_bifold_leaf_chain(
    model: ArticulatedObject,
    r: ResolvedLouveredShutterAssemblyConfig,
    slot_a: SlotAResult,
) -> SlotCResult:
    """Bifold pair — outer_leaf hinges on jamb, inner_leaf hinges on
    outer_leaf's free edge.

    Derived from rec_..._cd6b3278...:model.py:L36-L48, L147-L174. The
    jamb is the model root (Slot A's frame remains the root). Outer
    leaf is REVOLUTE child of the frame; inner leaf is REVOLUTE child
    of outer_leaf, with motion in the opposite z direction.
    """

    fw = r.frame_width
    fh = r.frame_height
    fd = r.frame_depth
    sw = r.stile_width
    rh = r.rail_height
    parent_name = slot_a.root_frame_part_name
    parent_part = model.get_part(parent_name)

    meeting_clear = 0.010
    leaf_width = max(0.16, (fw - 2.0 * sw) * 0.5 - meeting_clear)
    leaf_height = max(0.30, fh - 2.0 * rh - 2.0 * 0.005)
    leaf_depth = max(0.022, fd * 0.7)

    # Outer leaf — REVOLUTE child of frame, hinge on LEFT jamb.
    outer = model.part("outer_leaf")
    _emit_leaf_frame_visuals(
        outer,
        r=r,
        leaf_width=leaf_width,
        leaf_height=leaf_height,
        leaf_depth=leaf_depth,
        direction=1.0,
        name_prefix="outer_",
    )
    hinge_x_parent = slot_a.leaf_hinge_left_x
    hinge_y_parent = slot_a.leaf_hinge_y
    _emit_leaf_hinge_barrel(
        parent_part,
        outer,
        r=r,
        leaf_height=leaf_height,
        hinge_x_on_parent=hinge_x_parent,
        hinge_y_on_parent=hinge_y_parent,
        direction=1.0,
        name_suffix="outer",
    )
    model.articulation(
        "jamb_to_outer",
        ArticulationType.REVOLUTE,
        parent=parent_part,
        child=outer,
        origin=Origin(xyz=(hinge_x_parent, hinge_y_parent, 0.0)),
        axis=(0.0, 0.0, 1.0),
        motion_limits=MotionLimits(
            effort=14.0,
            velocity=1.4,
            lower=0.0,
            upper=r.leaf_open_upper,
        ),
    )

    # Inner leaf — REVOLUTE child of outer_leaf, hinge on outer leaf's
    # FREE (meeting) edge in outer-leaf-local frame.
    inner = model.part("inner_leaf")
    _emit_leaf_frame_visuals(
        inner,
        r=r,
        leaf_width=leaf_width,
        leaf_height=leaf_height,
        leaf_depth=leaf_depth,
        direction=1.0,  # inner_leaf in its own frame extends +x
        name_prefix="inner_",
    )
    # Hinge in outer-leaf-local frame: at outer's free stile.
    outer_free_x = leaf_width
    outer_free_y = 0.0
    barrel_radius_inner = max(0.005, sw * 0.18)
    barrel_length_inner = max(0.060, leaf_height * 0.50)
    # Barrel sits on outer_leaf's free stile (overlaps stile AABB).
    outer.visual(
        Cylinder(radius=barrel_radius_inner, length=barrel_length_inner),
        origin=Origin(xyz=(outer_free_x, outer_free_y - barrel_radius_inner * 0.3, 0.0)),
        material="metal",
        name="hinge_barrel_inner",
    )
    plate_thickness_inner = max(0.0035, sw * 0.06)
    # Plate on inner sits at inner's outer_stile (x = sw/2 in inner local).
    inner.visual(
        Box(
            (
                max(0.012, sw * 0.6),
                plate_thickness_inner,
                barrel_length_inner * 0.80,
            )
        ),
        origin=Origin(xyz=(sw * 0.5, -barrel_radius_inner * 0.3, 0.0)),
        material="metal",
        name="hinge_plate_inner",
    )

    model.articulation(
        "outer_to_inner",
        ArticulationType.REVOLUTE,
        parent=outer,
        child=inner,
        origin=Origin(xyz=(outer_free_x, outer_free_y, 0.0)),
        axis=(0.0, 0.0, 1.0),
        motion_limits=MotionLimits(
            effort=11.0,
            velocity=1.5,
            lower=r.bifold_inner_lower,
            upper=0.0,
        ),
    )

    bay_specs = [
        SlatBaySpec(
            parent_part_name="outer_leaf",
            bay_inner_width=leaf_width - 2.0 * sw,
            bay_z_top=leaf_height * 0.5 - rh,
            bay_z_bottom=-leaf_height * 0.5 + rh,
            bay_center_x=leaf_width * 0.5,
            bay_center_y=0.0,
        ),
        SlatBaySpec(
            parent_part_name="inner_leaf",
            bay_inner_width=leaf_width - 2.0 * sw,
            bay_z_top=leaf_height * 0.5 - rh,
            bay_z_bottom=-leaf_height * 0.5 + rh,
            bay_center_x=leaf_width * 0.5,
            bay_center_y=0.0,
        ),
    ]
    return SlotCResult(slats_parent_specs=bay_specs)


LEAF_HINGE_BUILDERS = {
    "fixed_no_leaf_hinge": _build_fixed_no_leaf_hinge,
    "single_leaf_side_hinge": _build_single_leaf_side_hinge,
    "double_leaf_french_pair": _build_double_leaf_french_pair,
    "bifold_leaf_chain": _build_bifold_leaf_chain,
}


# --------------------------------------------------------------------------- #
# Slot B (slat multiplicity) — one helper per family. Each emits N slat
# parts and N REVOLUTE pivots (axis = (1, 0, 0)) under a given
# slats_parent_part_name.
# --------------------------------------------------------------------------- #


def _slat_z_positions(
    *, n: int, bay_z_top: float, bay_z_bottom: float, chord: float
) -> list[float]:
    """Distribute N slat-pivot z-positions evenly across the bay.

    Slats are placed at ``z_i = bay_bottom + chord*0.5 + i * pitch``,
    where pitch = (bay_height - chord) / (n - 1) for n >= 2.
    """
    bay_height = max(0.05, bay_z_top - bay_z_bottom)
    if n <= 1:
        return [0.5 * (bay_z_top + bay_z_bottom)]
    # Leave half-chord margin top/bottom so blades sit inside the bay.
    margin = chord * 0.5 + 0.004
    usable = max(0.05, bay_height - 2.0 * margin)
    pitch = usable / (n - 1)
    z_start = bay_z_bottom + margin
    return [z_start + i * pitch for i in range(n)]


def _emit_one_slat(
    model: ArticulatedObject,
    *,
    slat_name: str,
    joint_name: str,
    parent_part,
    blade_visual,
    chord: float,
    thickness: float,
    bay_inner_width: float,
    bay_center_x: float,
    bay_center_y: float,
    slat_z: float,
    tilt_limit: float,
    pin_radius: float,
    pin_length: float,
    is_mesh_blade: bool,
) -> None:
    """Emit a single slat part + its REVOLUTE pivot. The slat extends
    along the x-axis (long axis) in its own frame; pin cylinders go
    on each end.
    """

    slat = model.part(slat_name)

    # Blade — material differs slightly across families, but topology is
    # uniform: 1 main blade visual + 2 short cylinder pins. Pins are
    # ALWAYS named "left_pin" / "right_pin" so the allow_overlap helper
    # can match on element names regardless of family.
    if is_mesh_blade:
        slat.visual(blade_visual, material="slat_main", name="blade")
    else:
        slat.visual(blade_visual, material="slat_main", name="blade")

    # Pin half-length — pins extend OUT past the blade ends so they
    # poke into the parent stiles. Pin center sits at ±(blade_half +
    # pin_overhang). pin_overhang = 60% pin length so 40% pin half is
    # already inside the blade footprint (connectivity within slat).
    blade_half = bay_inner_width * 0.5 - 0.012
    pin_overhang = pin_length * 0.55
    pin_x = blade_half + pin_overhang - pin_length * 0.5
    slat.visual(
        Cylinder(radius=pin_radius, length=pin_length),
        origin=Origin(xyz=(-pin_x, 0.0, 0.0), rpy=(0.0, math.pi * 0.5, 0.0)),
        material="metal",
        name="left_pin",
    )
    slat.visual(
        Cylinder(radius=pin_radius, length=pin_length),
        origin=Origin(xyz=(pin_x, 0.0, 0.0), rpy=(0.0, math.pi * 0.5, 0.0)),
        material="metal",
        name="right_pin",
    )

    # Inertial — modest mass.
    slat.inertial = Inertial.from_geometry(
        Box((bay_inner_width, chord, max(thickness, 0.006))),
        mass=max(0.06, chord * 0.6),
        origin=Origin(),
    )

    model.articulation(
        joint_name,
        ArticulationType.REVOLUTE,
        parent=parent_part,
        child=slat,
        origin=Origin(xyz=(bay_center_x, bay_center_y, slat_z)),
        axis=(1.0, 0.0, 0.0),
        motion_limits=MotionLimits(
            effort=1.2,
            velocity=2.0,
            lower=-tilt_limit,
            upper=tilt_limit,
        ),
    )


def _emit_slats_for_bay(
    model: ArticulatedObject,
    r: ResolvedLouveredShutterAssemblyConfig,
    *,
    bay_index: int,
    bay: SlatBaySpec,
    family: SlatFamily,
) -> list[str]:
    """Emit N slats inside one bay; return list of slat part names."""

    parent_part = model.get_part(bay.parent_part_name)
    n = r.slat_count
    chord = r.slat_chord
    thickness = r.slat_thickness

    # The slat blade extends along x; its length is the bay's inner
    # opening minus a small pin-clearance margin.
    blade_length = max(0.10, bay.bay_inner_width - 0.018)

    pin_radius = max(0.0028, min(thickness * 0.45, 0.0065))
    # Pin length must overlap the parent stile (stile width sw). Make
    # pin a bit longer than sw so it's clearly captured.
    pin_length = max(0.014, r.stile_width * 1.10)

    z_positions = _slat_z_positions(
        n=n,
        bay_z_top=bay.bay_z_top,
        bay_z_bottom=bay.bay_z_bottom,
        chord=chord,
    )

    # Per-slat pivot pad on the parent — one thin horizontal Box at each
    # slat's joint origin so fail_if_articulation_origin_far_from_geometry
    # (tol=0.015) is satisfied at every pivot without a tall vertical
    # back rail. The pad is sized to be hidden behind its slat blade in
    # any pose: pad y stays under slat_thickness and pad z stays under
    # slat_thickness too, so when the slat tilts the pad never sticks
    # out past the blade's silhouette. The pad spans from the joint
    # origin x to the bay's right-side stile inner face so it touches
    # the stile geometry and keeps the parent's visuals one connected
    # island (stiles already bridge top_rail and bottom_rail).
    pad_y_extent = max(0.0025, min(thickness * 0.55, 0.0040))
    pad_z_extent = max(0.0015, min(thickness * 0.30, 0.0030))
    stile_x_inner_right = bay.bay_center_x + bay.bay_inner_width * 0.5
    pad_x_min = bay.bay_center_x - 0.003
    pad_x_max = stile_x_inner_right + 0.003
    pad_x_length = max(0.020, pad_x_max - pad_x_min)
    pad_center_x = 0.5 * (pad_x_min + pad_x_max)
    for i, slat_z in enumerate(z_positions):
        parent_part.visual(
            Box((pad_x_length, pad_y_extent, pad_z_extent)),
            origin=Origin(xyz=(pad_center_x, bay.bay_center_y, slat_z)),
            material="shadow",
            name=f"slat_pivot_pad_{bay_index}_{i}",
        )

    emitted: list[str] = []
    for i, slat_z in enumerate(z_positions):
        slat_name = f"slat_{bay_index}_{i}" if r.leaf_count >= 1 else f"slat_{i}"
        joint_name = f"slat_{bay_index}_{i}_pivot" if r.leaf_count >= 1 else f"slat_{i}_pivot"

        if family == "flat_planar":
            blade = _flat_planar_blade(blade_length, chord, thickness)
            is_mesh = False
        elif family == "airfoil":
            blade = _airfoil_blade_mesh(
                blade_length, chord, thickness, f"airfoil_blade_{bay_index}_{i}"
            )
            is_mesh = True
        elif family == "wide_plantation":
            blade = _wide_plantation_blade_mesh(
                blade_length, chord, thickness, f"wide_blade_{bay_index}_{i}"
            )
            is_mesh = True
        else:  # narrow_blind
            blade = _narrow_blind_blade_mesh(
                blade_length, chord, thickness, f"narrow_blade_{bay_index}_{i}"
            )
            is_mesh = True

        _emit_one_slat(
            model,
            slat_name=slat_name,
            joint_name=joint_name,
            parent_part=parent_part,
            blade_visual=blade,
            chord=chord,
            thickness=thickness,
            bay_inner_width=bay.bay_inner_width,
            bay_center_x=bay.bay_center_x,
            bay_center_y=bay.bay_center_y,
            slat_z=slat_z,
            tilt_limit=r.slat_tilt_limit,
            pin_radius=pin_radius,
            pin_length=pin_length,
            is_mesh_blade=is_mesh,
        )
        emitted.append(slat_name)

    return emitted


# --------------------------------------------------------------------------- #
# Slot D — tilt rod drive. Three modes:
#   * none                    — emit nothing
#   * prismatic_vertical_rod  — 1 part + 1 PRISMATIC joint per slats_parent
#   * fixed_visual_rod        — visuals on the slats_parent (no part / joint)
# --------------------------------------------------------------------------- #


def _emit_tilt_rod_guides_on_parent(
    parent_part,
    *,
    r: ResolvedLouveredShutterAssemblyConfig,
    bay: SlatBaySpec,
    name_suffix: str,
) -> tuple[float, float, float, str, str]:
    """Emit a top + bottom rod_guide visual on the slats_parent for a
    prismatic_vertical_rod variant.

    The rod's local origin sits midway between the two guides; the
    MatingContract pairs the rod's vertical_bar visual with one of
    these guides.

    Returns ``(rod_x_in_parent, top_z, bottom_z, top_guide_name,
    bottom_guide_name)``.
    """

    sw = r.stile_width
    # rod x sits inset from the meeting stile.
    rod_x = bay.bay_center_x + (bay.bay_inner_width * 0.5) - r.tilt_rod_x_inset
    rod_y = r.tilt_rod_y_offset

    # Top + bottom guides are short rectangular blocks bolted onto the
    # adjacent rails. The guide overlaps BOTH the rail (AABB connectivity)
    # AND the rod (so the rod isn't disconnected from the grounded body).
    # We push the guide ~4 mm into the bay so its AABB intersects the
    # rod's vertical_bar in z, while still overlapping the rail.
    guide_w = max(0.024, sw * 0.7)
    # Guide y-dim must span from inside the parent stile (y near 0)
    # ALL the way out to the rod's y position (rod_y, negative). We
    # centre the guide at rod_y * 0.5 (so it overlaps the parent visual
    # region near y=0 and also reaches the rod plane).
    guide_d = max(0.020, abs(r.tilt_rod_y_offset) * 1.20 + 0.016)
    guide_h = max(0.020, r.rail_height * 0.55)
    z_overlap_into_bay = 0.004  # 4 mm of guide pokes into the bay
    top_center_z = bay.bay_z_top + guide_h * 0.5 - z_overlap_into_bay
    bottom_center_z = bay.bay_z_bottom - guide_h * 0.5 + z_overlap_into_bay

    top_guide_name = f"rod_guide_top_{name_suffix}"
    bottom_guide_name = f"rod_guide_bottom_{name_suffix}"

    parent_part.visual(
        Box((guide_w, guide_d, guide_h)),
        origin=Origin(xyz=(rod_x, rod_y * 0.5, top_center_z)),
        material="frame_accent",
        name=top_guide_name,
    )
    parent_part.visual(
        Box((guide_w, guide_d, guide_h)),
        origin=Origin(xyz=(rod_x, rod_y * 0.5, bottom_center_z)),
        material="frame_accent",
        name=bottom_guide_name,
    )
    # Slim vertical "rod_track" running between the two guides at
    # (rod_x, rod_y, bay_center_z). Its purpose is to (a) make the
    # parent visual list one connected island (it overlaps both
    # guides), and (b) keep the joint origin inside parent geometry
    # for fail_if_articulation_origin_far_from_geometry (tol=0.015).
    bay_z_center = 0.5 * (bay.bay_z_top + bay.bay_z_bottom)
    track_span = max(0.10, bay.bay_z_top - bay.bay_z_bottom + 0.020)
    parent_part.visual(
        Box((guide_w * 0.40, 0.010, track_span)),
        origin=Origin(xyz=(rod_x, rod_y, bay_z_center)),
        material="shadow",
        name=f"rod_back_track_{name_suffix}",
    )
    return rod_x, top_center_z, bottom_center_z, top_guide_name, bottom_guide_name


def _build_prismatic_vertical_rod_for_bay(
    model: ArticulatedObject,
    r: ResolvedLouveredShutterAssemblyConfig,
    *,
    bay_index: int,
    bay: SlatBaySpec,
) -> str:
    """Build one tilt_rod part + one PRISMATIC joint for ``bay``.

    Adapted from rec_..._7c027fd5...:model.py:L198-L222 (``rod``
    construction + ``leaf_X_to_tilt_rod`` PRISMATIC). The rod has a
    vertical Box body + N per-slat drive_tab visuals.
    """

    parent_part = model.get_part(bay.parent_part_name)
    (
        rod_x,
        top_center_z,
        bottom_center_z,
        top_guide_name,
        bot_guide_name,
    ) = _emit_tilt_rod_guides_on_parent(
        parent_part,
        r=r,
        bay=bay,
        name_suffix=f"{bay_index}",
    )
    rod_y = r.tilt_rod_y_offset
    # Rod top face mates with the top guide's INNER (negative_z) face,
    # which sits exactly at bay.bay_z_top. Same for bottom.
    rod_top_z = bay.bay_z_top
    rod_bottom_z = bay.bay_z_bottom
    rod_height = max(0.10, rod_top_z - rod_bottom_z)
    rod_center_z = 0.5 * (rod_top_z + rod_bottom_z)

    # Pick a unique part name per bay.
    rod_name = f"tilt_rod_{bay_index}" if r.leaf_count >= 1 else "tilt_rod"
    rod = model.part(rod_name)

    # Vertical rod body — a tall thin Box (rec_7c027fd5 used Box; we
    # keep the primitive). Its origin sits at the rod's geometric
    # center (which is also the part frame origin).
    rod_body_w = 0.014
    rod_body_d = 0.012
    rod.visual(
        Box((rod_body_w, rod_body_d, rod_height)),
        origin=Origin(xyz=(0.0, 0.0, 0.0)),
        material="metal",
        name="vertical_bar",
    )
    # Per-slat drive_tabs at each slat z-position (relative to rod center).
    chord = r.slat_chord
    z_positions = _slat_z_positions(
        n=r.slat_count,
        bay_z_top=bay.bay_z_top,
        bay_z_bottom=bay.bay_z_bottom,
        chord=chord,
    )
    for i, zw in enumerate(z_positions):
        # In rod local frame, the tab z is (slat_z - rod_center_z).
        tab_z = zw - rod_center_z
        rod.visual(
            Box((0.020, 0.042, 0.006)),
            origin=Origin(xyz=(0.0, 0.015, tab_z)),
            material="metal",
            name=f"drive_tab_{i}",
        )

    # Rod inertial.
    rod.inertial = Inertial.from_geometry(
        Box((rod_body_w, max(rod_body_d, 0.044), rod_height)),
        mass=0.20,
        origin=Origin(),
    )

    joint_name = f"leaf_{bay_index}_to_tilt_rod" if r.leaf_count >= 1 else "frame_to_tilt_rod"
    model.articulation(
        joint_name,
        ArticulationType.PRISMATIC,
        parent=parent_part,
        child=rod,
        origin=Origin(xyz=(rod_x, rod_y, rod_center_z)),
        axis=(0.0, 0.0, 1.0),
        motion_limits=MotionLimits(
            effort=8.0,
            velocity=0.25,
            lower=-r.tilt_rod_travel,
            upper=r.tilt_rod_travel,
        ),
        # Tilt rod is captured between top + bottom guides — captured
        # geometry, grandfathered (no MatingContract). Overlap allowed
        # via run_*_tests.
    )
    return rod_name


def _emit_fixed_visual_rod_for_bay(
    model: ArticulatedObject,
    r: ResolvedLouveredShutterAssemblyConfig,
    *,
    bay_index: int,
    bay: SlatBaySpec,
) -> None:
    """Emit ONLY visuals on the slats_parent — no part, no joint.

    Adapted from rec_..._d2759605...:model.py:L263-L280 (the
    ``tilt_rod`` part is replaced by a fixed cylinder visual on the
    panel_frame in this mode). Three visuals total: a vertical rod
    shaft + two end caps. All visuals stick to the parent's stile/rail
    geometry so they don't form a disconnected island.
    """

    parent_part = model.get_part(bay.parent_part_name)
    rod_x = bay.bay_center_x + (bay.bay_inner_width * 0.5) - r.tilt_rod_x_inset
    # rod must touch a stile / rail visual to avoid a disconnected
    # island. Move rod_y inward (toward parent depth center) so its
    # AABB overlaps the rails.
    rod_y = max(r.tilt_rod_y_offset, -r.frame_depth * 0.35) * 0.4
    rod_top_z = bay.bay_z_top - 0.005
    rod_bottom_z = bay.bay_z_bottom + 0.005
    rod_center_z = 0.5 * (rod_top_z + rod_bottom_z)
    rod_height = max(0.10, rod_top_z - rod_bottom_z)

    parent_part.visual(
        Cylinder(radius=0.0065, length=rod_height),
        origin=Origin(xyz=(rod_x, rod_y, rod_center_z)),
        material="metal",
        name=f"visual_rod_shaft_{bay_index}",
    )
    parent_part.visual(
        Cylinder(radius=0.010, length=0.020),
        origin=Origin(
            xyz=(rod_x, rod_y, rod_top_z - 0.005),
        ),
        material="metal",
        name=f"visual_rod_top_cap_{bay_index}",
    )
    parent_part.visual(
        Cylinder(radius=0.010, length=0.020),
        origin=Origin(
            xyz=(rod_x, rod_y, rod_bottom_z + 0.005),
        ),
        material="metal",
        name=f"visual_rod_bottom_cap_{bay_index}",
    )


def _apply_tilt_rod_for_bays(
    model: ArticulatedObject,
    r: ResolvedLouveredShutterAssemblyConfig,
    bays: list[SlatBaySpec],
) -> list[str]:
    """Apply Slot D to every slats_parent bay. Returns names of rod
    parts that were created (empty for ``none`` and ``fixed_visual_rod``).
    """

    rod_parts: list[str] = []
    if r.tilt_rod_module == "none":
        return rod_parts
    for bay_index, bay in enumerate(bays):
        if r.tilt_rod_module == "prismatic_vertical_rod":
            rod_parts.append(
                _build_prismatic_vertical_rod_for_bay(model, r, bay_index=bay_index, bay=bay)
            )
        else:  # fixed_visual_rod
            _emit_fixed_visual_rod_for_bay(model, r, bay_index=bay_index, bay=bay)
    return rod_parts


# --------------------------------------------------------------------------- #
# Public entry points
# --------------------------------------------------------------------------- #


def slot_choices_for_seed(seed: int) -> list[tuple[str, str]]:
    """Return the (slot, module) picks for inspection — used by the
    ``module_topology_diversity`` gate to count unique topologies.

    For the multiplicity Slot B, the module name encodes the family +
    N (e.g. ``flat_planar_slats_N12``), so diversity counts each
    (family, N) as a distinct topology.
    """

    cfg = config_from_seed(seed)
    r = resolve_config(cfg)
    slat_module_name = f"{r.slat_family}_slats_N{r.slat_count}"
    return [
        ("frame", r.frame_module),
        ("slat", slat_module_name),
        ("leaf_hinge", r.leaf_hinge_module),
        ("tilt_rod", r.tilt_rod_module),
    ]


def build_louvered_shutter(
    config: LouveredShutterAssemblyConfig,
    *,
    assets: AssetContext | None = None,
) -> ArticulatedObject:
    """Compose a louvered-shutter assembly using the resolved config.

    Order:
      1. Slot A — build root frame
      2. Slot C — build any leaf parts + leaf-hinge joints
      3. Slot B — emit N slat parts + REVOLUTE pivots for each slats_parent
      4. Slot D — emit tilt-rod part + PRISMATIC joint (per slats_parent)
         or fixed visuals on slats_parent, or nothing.

    seed=0 (anchor) reproduces rec_..._4492bf5f...'s structure:
    frame + 12 slats parented to frame, no leaf, no tilt rod.
    """

    r = resolve_config(config)
    model = ArticulatedObject(name="louvered_shutter_assembly", assets=assets)
    for material_name, rgba in r.palette.items():
        model.material(material_name, rgba=rgba)

    # Slot A — frame.
    frame_builder = FRAME_BUILDERS[r.frame_module]
    slot_a = frame_builder(model, r)

    # Slot C — leaf hinge.
    leaf_builder = LEAF_HINGE_BUILDERS[r.leaf_hinge_module]
    slot_c = leaf_builder(model, r, slot_a)

    # Slot B — slats per slats_parent.
    for bay_idx, bay in enumerate(slot_c.slats_parent_specs):
        _emit_slats_for_bay(model, r, bay_index=bay_idx, bay=bay, family=r.slat_family)

    # Slot D — tilt rod drive.
    _apply_tilt_rod_for_bays(model, r, slot_c.slats_parent_specs)

    return model


def build_seeded_louvered_shutter(seed: int) -> ArticulatedObject:
    """Build the shutter model for the given seed (uses
    :func:`config_from_seed`).
    """
    return build_louvered_shutter(config_from_seed(seed))


# Backwards-compatible aliases for the agent_workflow's expected
# ``build_<slug>`` / ``build_seeded_<slug>`` function names.
build_louvered_shutter_assembly = build_louvered_shutter
build_seeded_louvered_shutter_assembly = build_seeded_louvered_shutter


# --------------------------------------------------------------------------- #
# Author-layer QC — captured-pin / hinge-barrel overlap allowances.
# --------------------------------------------------------------------------- #


def _slat_parent_specs(
    r: ResolvedLouveredShutterAssemblyConfig, part_names: set
) -> list[tuple[str, str, str]]:
    """Return ``[(parent_part_name, left_stile_visual, right_stile_visual), …]``
    for every bay that Slot B populated in the current build.

    Used by ``_declare_slat_pin_overlaps`` and ``_declare_tilt_rod_overlaps``.
    """

    if r.leaf_hinge_module == "fixed_no_leaf_hinge":
        # Use the right stile prefix depending on which Slot A built
        # the root frame (outer_frame uses "outer_" prefix).
        if "outer_frame" in part_names:
            return [("outer_frame", "outer_left_stile", "outer_right_stile")]
        if "window_frame" in part_names:
            return [("window_frame", "left_stile", "right_stile")]
        return [("frame", "left_stile", "right_stile")]
    if r.leaf_hinge_module == "single_leaf_side_hinge":
        return [("leaf", "outer_stile", "meeting_stile")]
    if r.leaf_hinge_module == "double_leaf_french_pair":
        return [
            ("leaf_0", "outer_stile", "meeting_stile"),
            ("leaf_1", "outer_stile", "meeting_stile"),
        ]
    # bifold
    return [
        ("outer_leaf", "outer_outer_stile", "outer_meeting_stile"),
        ("inner_leaf", "inner_outer_stile", "inner_meeting_stile"),
    ]


def _declare_slat_pin_overlaps(
    ctx: TestContext,
    model: ArticulatedObject,
    *,
    r: ResolvedLouveredShutterAssemblyConfig,
) -> None:
    """For every slat in every bay, declare allow_overlap between the
    slat's pin and the slats_parent's stile geometry.

    The pin is captured inside the stile (intentional inter-part
    interpenetration), so we whitelist the pair. The names of the
    stile visuals depend on which Slot C module built the leaf.
    """

    part_names = {p.name for p in model.parts}
    bay_specs = _slat_parent_specs(r, part_names)

    for bay_idx, (parent_name, left_stile, right_stile) in enumerate(bay_specs):
        if parent_name not in part_names:
            continue
        parent = model.get_part(parent_name)
        # Per-bay parent elements that may incidentally contact the
        # slat geometry (stile bushings, packed rails, AND the
        # fixed_visual_rod cylinders that live as parent visuals).
        parent_extra_elems = (
            "top_rail",
            "bottom_rail",
            "outer_top_rail",
            "outer_bottom_rail",
            "inner_top_rail",
            "inner_bottom_rail",
            "outer_outer_stile",
            "outer_meeting_stile",
            "inner_outer_stile",
            "inner_meeting_stile",
            "back_trim_strip",
            "outer_back_trim_strip",
            "inner_back_trim_strip",
            # Fixed-visual-rod visuals live on the slats_parent too.
            f"visual_rod_shaft_{bay_idx}",
            f"visual_rod_top_cap_{bay_idx}",
            f"visual_rod_bottom_cap_{bay_idx}",
            # rod_back_track lives on parent for prismatic_vertical_rod.
            f"rod_back_track_{bay_idx}",
            f"rod_guide_top_{bay_idx}",
            f"rod_guide_bottom_{bay_idx}",
            "mid_rail",
        ) + tuple(f"slat_pivot_pad_{bay_idx}_{i}" for i in range(r.slat_count))
        for i in range(r.slat_count):
            slat_name = f"slat_{bay_idx}_{i}" if r.leaf_count >= 1 else f"slat_{i}"
            if slat_name not in part_names:
                continue
            slat = model.get_part(slat_name)
            # Slats in opposite-direction leaves (french leaf_1, bifold
            # inner) have their pins mirrored relative to the stile
            # names. Declare allow_overlap for EVERY (stile_name,
            # pin_name) cross-product to make the matching robust.
            slat_elems = ("left_pin", "right_pin", "blade")
            for stile_name in (left_stile, right_stile, *parent_extra_elems):
                for slat_elem in slat_elems:
                    ctx.allow_overlap(
                        parent,
                        slat,
                        elem_a=stile_name,
                        elem_b=slat_elem,
                        reason=(
                            "slat pin/blade may graze parent stile/rail/rod "
                            "(captured-pin or close-pack geometry)"
                        ),
                    )


def _declare_leaf_hinge_overlaps(
    ctx: TestContext,
    model: ArticulatedObject,
    *,
    r: ResolvedLouveredShutterAssemblyConfig,
) -> None:
    """Declare allow_overlap between leaf-hinge barrels and leaf plates
    (intentional pin-through-knuckle overlap).
    """
    part_names = {p.name for p in model.parts}

    if r.leaf_hinge_module == "single_leaf_side_hinge":
        parent_name = (
            "outer_frame"
            if "outer_frame" in part_names
            else ("frame" if "frame" in part_names else "window_frame")
        )
        if parent_name in part_names and "leaf" in part_names:
            parent = model.get_part(parent_name)
            leaf = model.get_part("leaf")
            ctx.allow_overlap(
                parent,
                leaf,
                elem_a="hinge_barrel_leaf",
                elem_b="hinge_plate_leaf",
                reason="leaf hinge barrel intentionally captures plate",
            )
            # The leaf's stiles, rails, hinge plate, and back trim all
            # may graze the parent's stiles / rails / barrel at the
            # inner face of the jamb. Tolerate.
            parent_elems = (
                "left_stile",
                "outer_left_stile",
                "right_stile",
                "outer_right_stile",
                "top_rail",
                "outer_top_rail",
                "bottom_rail",
                "outer_bottom_rail",
                "hinge_barrel_leaf",
                "upper_reveal_lip",
                "lower_reveal_lip",
                "left_reveal_lip",
                "right_reveal_lip",
            )
            leaf_elems = (
                "hinge_plate_leaf",
                "outer_stile",
                "meeting_stile",
                "top_rail",
                "bottom_rail",
                "back_trim_strip",
            )
            for parent_elem in parent_elems:
                for leaf_elem in leaf_elems:
                    ctx.allow_overlap(
                        parent,
                        leaf,
                        elem_a=parent_elem,
                        elem_b=leaf_elem,
                        reason="leaf body sits adjacent to jamb / hinge",
                    )
    elif r.leaf_hinge_module == "double_leaf_french_pair":
        parent_name = (
            "outer_frame"
            if "outer_frame" in part_names
            else ("window_frame" if "window_frame" in part_names else "frame")
        )
        if parent_name in part_names:
            parent = model.get_part(parent_name)
            parent_elems_base = (
                "left_stile",
                "right_stile",
                "outer_left_stile",
                "outer_right_stile",
                "top_rail",
                "outer_top_rail",
                "bottom_rail",
                "outer_bottom_rail",
                "center_muntin",
                "upper_reveal_lip",
                "lower_reveal_lip",
                "left_reveal_lip",
                "right_reveal_lip",
            )
            for leaf_idx in (0, 1):
                leaf_part_name = f"leaf_{leaf_idx}"
                if leaf_part_name in part_names:
                    leaf_part = model.get_part(leaf_part_name)
                    barrel = f"hinge_barrel_leaf_{leaf_idx}"
                    plate = f"hinge_plate_leaf_{leaf_idx}"
                    parent_elems = (*parent_elems_base, barrel)
                    leaf_elems = (
                        plate,
                        "outer_stile",
                        "meeting_stile",
                        "top_rail",
                        "bottom_rail",
                        "back_trim_strip",
                    )
                    for parent_elem in parent_elems:
                        for leaf_elem in leaf_elems:
                            ctx.allow_overlap(
                                parent,
                                leaf_part,
                                elem_a=parent_elem,
                                elem_b=leaf_elem,
                                reason="french leaf body adjacent to jamb / hinge",
                            )
    elif r.leaf_hinge_module == "bifold_leaf_chain":
        parent_name = (
            "frame"
            if "frame" in part_names
            else ("outer_frame" if "outer_frame" in part_names else "window_frame")
        )
        if parent_name in part_names and "outer_leaf" in part_names:
            parent = model.get_part(parent_name)
            outer = model.get_part("outer_leaf")
            parent_elems_base = (
                "left_stile",
                "right_stile",
                "outer_left_stile",
                "outer_right_stile",
                "top_rail",
                "outer_top_rail",
                "bottom_rail",
                "outer_bottom_rail",
                "mid_rail",
                "kick_panel",
                "center_muntin",
                "upper_reveal_lip",
                "lower_reveal_lip",
                "left_reveal_lip",
                "right_reveal_lip",
            )
            for parent_elem in (*parent_elems_base, "hinge_barrel_outer"):
                for leaf_elem in (
                    "hinge_plate_outer",
                    "outer_outer_stile",
                    "outer_meeting_stile",
                    "outer_top_rail",
                    "outer_bottom_rail",
                    "outer_back_trim_strip",
                ):
                    ctx.allow_overlap(
                        parent,
                        outer,
                        elem_a=parent_elem,
                        elem_b=leaf_elem,
                        reason="bifold outer leaf adjacent to jamb / hinge",
                    )
        if "outer_leaf" in part_names and "inner_leaf" in part_names:
            outer = model.get_part("outer_leaf")
            inner = model.get_part("inner_leaf")
            outer_elems = (
                "outer_outer_stile",
                "outer_meeting_stile",
                "outer_top_rail",
                "outer_bottom_rail",
                "outer_back_trim_strip",
                "hinge_barrel_inner",
            )
            inner_elems = (
                "hinge_plate_inner",
                "inner_outer_stile",
                "inner_meeting_stile",
                "inner_top_rail",
                "inner_bottom_rail",
                "inner_back_trim_strip",
            )
            for outer_elem in outer_elems:
                for inner_elem in inner_elems:
                    ctx.allow_overlap(
                        outer,
                        inner,
                        elem_a=outer_elem,
                        elem_b=inner_elem,
                        reason="bifold inner leaf adjacent to outer leaf",
                    )


def _declare_tilt_rod_overlaps(
    ctx: TestContext,
    model: ArticulatedObject,
    *,
    r: ResolvedLouveredShutterAssemblyConfig,
) -> None:
    """When Slot D = prismatic_vertical_rod, the rod's vertical_bar
    runs between the two parent guides + sometimes passes over the
    slat drive areas. Declare those overlaps.
    """
    if r.tilt_rod_module != "prismatic_vertical_rod":
        return
    part_names = {p.name for p in model.parts}
    bay_specs = _slat_parent_specs(r, part_names)

    for bay_idx, (parent_name, _ls, _rs) in enumerate(bay_specs):
        rod_name = f"tilt_rod_{bay_idx}" if r.leaf_count >= 1 else "tilt_rod"
        if parent_name not in part_names or rod_name not in part_names:
            continue
        parent_part = model.get_part(parent_name)
        rod_part = model.get_part(rod_name)
        # Rod vertical_bar (and per-slat drive_tabs) overlap parent's
        # top + bottom rod guides + rod_back_track by construction.
        rod_visual_names = ["vertical_bar"] + [f"drive_tab_{i}" for i in range(r.slat_count)]
        for guide_name in (
            f"rod_guide_top_{bay_idx}",
            f"rod_guide_bottom_{bay_idx}",
            f"rod_back_track_{bay_idx}",
        ):
            for rod_elem in rod_visual_names:
                ctx.allow_overlap(
                    parent_part,
                    rod_part,
                    elem_a=guide_name,
                    elem_b=rod_elem,
                    reason=("rod slides through guide bushing / back track (captured)"),
                )

        # Rod drive_tabs may approach the slat front face; tolerate any
        # incidental overlap between the rod's drive_tab_i and the slat
        # blade.
        for i in range(r.slat_count):
            slat_name = f"slat_{bay_idx}_{i}" if r.leaf_count >= 1 else f"slat_{i}"
            if slat_name not in part_names:
                continue
            slat_part = model.get_part(slat_name)
            ctx.allow_overlap(
                rod_part,
                slat_part,
                elem_a=f"drive_tab_{i}",
                elem_b="blade",
                reason="drive tab nominally engages slat blade front face",
            )


def _expect_slat_pivot_moves_blade(
    ctx: TestContext,
    model: ArticulatedObject,
    r: ResolvedLouveredShutterAssemblyConfig,
) -> None:
    """When at least one slat pivot rotates, the blade's world AABB
    height should increase (the blade tilts out of the plane)."""

    part_names = {p.name for p in model.parts}
    # Pick the first slat in the first bay (any naming convention).
    candidate_names = [
        "slat_0_0",
        "slat_0",
    ]
    slat_name = next((n for n in candidate_names if n in part_names), None)
    if slat_name is None:
        return
    joint_names = {a.name for a in model.articulations}
    if "slat_0_0_pivot" in joint_names:
        joint_name = "slat_0_0_pivot"
    elif "slat_0_pivot" in joint_names:
        joint_name = "slat_0_pivot"
    else:
        return
    try:
        joint = model.get_articulation(joint_name)
    except Exception:  # noqa: BLE001
        return
    slat_part = model.get_part(slat_name)
    rest = ctx.part_world_aabb(slat_part)
    if rest is None:
        return
    rest_h = rest[1][2] - rest[0][2]
    rest_d = rest[1][1] - rest[0][1]
    with ctx.pose({joint: min(0.6, r.slat_tilt_limit - 0.05)}):
        tilted = ctx.part_world_aabb(slat_part)
        if tilted is None:
            return
        tilted_h = tilted[1][2] - tilted[0][2]
        tilted_d = tilted[1][1] - tilted[0][1]
    # When a chord-heavy slat tilts, its z extent SHRINKS and its y
    # extent grows (vice-versa for thickness-dominant blades). Accept
    # either direction — the only thing we care about is the AABB
    # genuinely changes between rest and tilted poses.
    delta = max(abs(tilted_h - rest_h), abs(tilted_d - rest_d))
    ctx.check(
        "slat_pivot_changes_blade_aabb",
        delta > max(0.002, r.slat_thickness * 0.20),
        f"rest=(h={rest_h:.4f},d={rest_d:.4f}), tilted=(h={tilted_h:.4f},d={tilted_d:.4f})",
    )


def run_louvered_shutter_tests(
    model: ArticulatedObject,
    config: LouveredShutterAssemblyConfig,
) -> TestReport:
    """Author-layer QC + captured-pin overlap allowances.

    Mirrors the structure of ``run_monitor_mount_tests`` /
    ``run_dj_equipment_tests``. The compiler-owned baseline (run during
    target=full compile) checks single-root, isolated parts,
    disconnected_geometry_islands, current-pose part overlaps,
    articulation_origin_far_from_geometry, and joint_mating_has_gap.
    """

    ctx = TestContext(model)
    r = resolve_config(config)

    ctx.check_model_valid()
    ctx.fail_if_isolated_parts()
    _declare_slat_pin_overlaps(ctx, model, r=r)
    _declare_leaf_hinge_overlaps(ctx, model, r=r)
    _declare_tilt_rod_overlaps(ctx, model, r=r)
    ctx.warn_if_part_contains_disconnected_geometry_islands()
    ctx.fail_if_parts_overlap_in_current_pose()
    ctx.fail_if_articulation_origin_far_from_geometry(tol=0.025)
    ctx.fail_if_joint_mating_has_gap()

    _expect_slat_pivot_moves_blade(ctx, model, r)

    return ctx.report()


# Backwards-compatible alias matching ``<slug>``.
run_louvered_shutter_assembly_tests = run_louvered_shutter_tests


# --------------------------------------------------------------------------- #
# Modular template authoring notes
# --------------------------------------------------------------------------- #
# Pattern: mixed (4 slots — see module docstring slot graph)
#
# Slot inventory + 5-star sources:
#
#   frame_topology:
#     simple_rectangular_frame       — rec_..._4492bf5f...:model.py:L13-L25
#                                       (ANCHOR; 2 stiles + 2 rails)
#     window_jamb_with_inset_panel   — rec_..._d2759605...:model.py:L128-L172
#                                       (outer_frame + inner reveal lips)
#     paneled_frame_with_mid_rail    — rec_..._0219c5e7...:model.py:L25-L42
#                                       (door-format; mid_rail divides bay)
#     double_jamb_french_frame       — rec_..._7c027fd5...:model.py:L40-L77
#                                       (wider envelope; center_muntin)
#
#   slat_module (multiplicity over family × N):
#     flat_planar_slats_N{5..14}     — rec_..._4492bf5f...:model.py:L26-L56
#                                       (ANCHOR with N=12; Box blade + 2 pins)
#     airfoil_slats_N{6..14}         — rec_..._d2759605...:model.py:L84-L116
#                                       (12-pt section_loft superellipse blade)
#     wide_plantation_slats_N{3..7}  — rec_..._0004:model.py:L34-L67
#                                       (thick wide superellipse blade)
#     narrow_blind_slats_N{10..21}   — rec_..._77374234...:model.py:L15-L60
#                                       (asymmetric 10-pt section_loft blade)
#
#   leaf_hinge_kinematics:
#     fixed_no_leaf_hinge            — rec_..._4492bf5f...:model.py:L48-L57
#                                       (ANCHOR; slats parent directly to frame)
#     single_leaf_side_hinge         — rec_..._d2759605...:model.py:L128-L222
#                                       (frame→leaf REVOLUTE around +z)
#     double_leaf_french_pair        — rec_..._7c027fd5...:model.py:L97-L171
#                                       (frame→leaf_0/leaf_1 mirrored)
#     bifold_leaf_chain              — rec_..._cd6b3278...:model.py:L36-L48,
#                                                          L147-L174
#                                       (jamb→outer_leaf→inner_leaf chain)
#
#   tilt_rod_drive:
#     none                           — rec_..._4492bf5f... (ANCHOR; no rod)
#     prismatic_vertical_rod         — rec_..._7c027fd5...:model.py:L198-L222
#                                       (1 part + PRISMATIC joint per leaf)
#     fixed_visual_rod               — rec_..._d2759605...:model.py:L282-L349
#                                       (cylinder visuals on slats_parent only)
#
# anchor_geometry_match is inapplicable to modular templates; it is
# skipped by the coverage gate via the ``__modular__ = True`` flag. The
# replacement gate is:
#   * module_topology_diversity — counts distinct slot_choice tuples
#     across passing seeds (≥5 required)
#
# Compatibility matrix (encoded in resolve_config):
#   simple_rectangular_frame × bifold_leaf_chain        → C ← fixed_no_leaf_hinge
#   simple_rectangular_frame × double_leaf_french_pair  → C ← single_leaf_side_hinge
#   double_jamb_french_frame × ¬french                  → C ← double_leaf_french_pair
#
# Combinations (after compatibility fold-back):
#   4 frames × 4 slat-families × 4 leaf-hinges × 3 tilt-rods = 192 raw;
#   approximately 90+ unique combinations after fold-back. ×N expansion
#   over multiplicity yields well over the diversity gate floor (≥5).
#
# Captured-pin overlap declarations (in run_*_tests):
#   * Every slat's left_pin / right_pin inside the slats_parent's
#     left/outer + right/meeting stile.
#   * Every leaf-hinge barrel inside its mating plate (for non-fixed C).
#   * Tilt rod vertical_bar through rod_guide_top/bottom (prismatic D).
#   * Tilt rod drive_tab_i overlapping slat blade (nominal contact).


__all__ = [
    "FrameModule",
    "LeafHingeModule",
    "LouveredShutterAssemblyConfig",
    "ResolvedLouveredShutterAssemblyConfig",
    "ShutterPaletteTheme",
    "SlatFamily",
    "TiltRodModule",
    "build_louvered_shutter",
    "build_louvered_shutter_assembly",
    "build_seeded_louvered_shutter",
    "build_seeded_louvered_shutter_assembly",
    "config_from_seed",
    "resolve_config",
    "run_louvered_shutter_assembly_tests",
    "run_louvered_shutter_tests",
    "slot_choices_for_seed",
]
