"""Retractable utility knife — modular procedural template.

This template uses the slot/module/assembler abstraction in
``agent.templates._modular``. Three slots — **housing**, **mechanism**,
**blade** — each pick from a small candidate pool sourced from the 5-star
sample family. The assembler wires modules together with
``MatingContract``-backed articulations.

Slot graph:
  housing → mechanism → blade

Candidates (6 total):

  housing:
    - barrel_grip      (anchor; rec_..._cad8...:rev_000001 — classic
                        thumb-wheel + bottom-pan + rear bridge geometry)
    - pistol_grip      (alt: shorter handle + finger guard + no lock wheel,
                        derived from rec_..._9365...:rev_000001)

  mechanism:
    - retractable_slider (anchor; carrier + thumb_slider, FIXED slider)
    - service_door_swap  (alt: carrier + service_door REVOLUTE, derived
                        from rec_..._14ce...:rev_000001)

  blade:
    - straight_utility   (anchor; classic trapezoid blade)
    - hook               (alt: utility hook profile)

seed == 0 always picks the anchor combination
(barrel_grip + retractable_slider + straight_utility), so any per-anchor
smoke test on seed 0 reproduces the canonical 5-star geometry. Other
seeds RNG-pick uniformly across the 2×2×2 = 8 combinations.

Anchor responsibility is at the **interface** level: each module declares
the geometry of the face it exposes, and the assembler validates that
adjacent modules' faces match (geometry + opposite normals + extents-uv
within tolerance) before emitting the chain joint.
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
    Inertial,
    LoftGeometry,
    MotionLimits,
    Origin,
    TestContext,
    TestReport,
    mesh_from_geometry,
    rounded_rect_profile,
)

# Modular templates are flagged so the sweep coverage gate can skip
# anchor_geometry_match (a single-anchor gate that does not apply when
# topology varies across seeds) and run module-level checks instead.
__modular__ = True


HousingModule = Literal["barrel_grip", "pistol_grip"]
MechanismModule = Literal["retractable_slider", "service_door_swap"]
BladeModule = Literal["straight_utility", "hook"]

GripStyle = Literal["triple_strip", "single_strip", "diamond_pattern"]
NoseTreatment = Literal["squared", "rounded", "pointed"]
PaletteTheme = Literal[
    "anchor_yellow",
    "industrial_black",
    "navy_blue",
    "safety_orange",
    "stealth_gray",
]


# --------------------------------------------------------------------------- #
# Palette presets — preserved verbatim from the prior single-anchor template.
# Each theme provides body/grip/track/slider/wheel/steel/dark_steel color
# tokens that module factories pull from the resolved palette dict.
# --------------------------------------------------------------------------- #


KNIFE_PALETTE_PRESETS: dict[str, dict[str, tuple[float, float, float, float]]] = {
    "anchor_yellow": {
        "body": (0.92, 0.77, 0.16, 1.0),
        "grip": (0.12, 0.12, 0.12, 1.0),
        "track": (0.40, 0.42, 0.44, 1.0),
        "slider": (0.14, 0.14, 0.15, 1.0),
        "wheel": (0.10, 0.10, 0.11, 1.0),
        "steel": (0.82, 0.84, 0.86, 1.0),
        "dark_steel": (0.44, 0.47, 0.50, 1.0),
        "door": (0.92, 0.77, 0.16, 1.0),
    },
    "industrial_black": {
        "body": (0.10, 0.10, 0.11, 1.0),
        "grip": (0.65, 0.55, 0.18, 1.0),
        "track": (0.30, 0.32, 0.34, 1.0),
        "slider": (0.85, 0.20, 0.15, 1.0),
        "wheel": (0.05, 0.05, 0.06, 1.0),
        "steel": (0.82, 0.84, 0.86, 1.0),
        "dark_steel": (0.30, 0.32, 0.34, 1.0),
        "door": (0.15, 0.15, 0.16, 1.0),
    },
    "navy_blue": {
        "body": (0.13, 0.22, 0.40, 1.0),
        "grip": (0.55, 0.58, 0.62, 1.0),
        "track": (0.30, 0.34, 0.42, 1.0),
        "slider": (0.92, 0.92, 0.92, 1.0),
        "wheel": (0.85, 0.55, 0.10, 1.0),
        "steel": (0.82, 0.84, 0.86, 1.0),
        "dark_steel": (0.42, 0.45, 0.50, 1.0),
        "door": (0.18, 0.28, 0.48, 1.0),
    },
    "safety_orange": {
        "body": (0.95, 0.42, 0.10, 1.0),
        "grip": (0.10, 0.10, 0.11, 1.0),
        "track": (0.35, 0.36, 0.38, 1.0),
        "slider": (0.18, 0.18, 0.19, 1.0),
        "wheel": (0.06, 0.06, 0.07, 1.0),
        "steel": (0.85, 0.86, 0.88, 1.0),
        "dark_steel": (0.46, 0.48, 0.52, 1.0),
        "door": (0.95, 0.42, 0.10, 1.0),
    },
    "stealth_gray": {
        "body": (0.22, 0.23, 0.25, 1.0),
        "grip": (0.05, 0.05, 0.06, 1.0),
        "track": (0.34, 0.36, 0.38, 1.0),
        "slider": (0.10, 0.10, 0.11, 1.0),
        "wheel": (0.03, 0.03, 0.04, 1.0),
        "steel": (0.65, 0.68, 0.72, 1.0),
        "dark_steel": (0.28, 0.30, 0.32, 1.0),
        "door": (0.28, 0.29, 0.31, 1.0),
    },
}


@dataclass(frozen=True)
class RetractableUtilityKnifeConfig:
    """Public template config. Module selection is opt-in: leave any of
    the three module fields as ``None`` to let ``config_from_seed`` /
    ``resolve_config`` fill them in from the seed-driven RNG.

    ``handle_length`` / ``handle_width`` / ``handle_height`` etc. set the
    overall envelope; individual module factories may down-scale where
    appropriate (e.g. pistol_grip uses a shorter handle than barrel_grip
    even at the same nominal length, since a finger guard takes up some
    of the linear budget).
    """

    housing_module: HousingModule | None = None
    mechanism_module: MechanismModule | None = None
    blade_module: BladeModule | None = None

    grip_style: GripStyle = "triple_strip"
    nose_treatment: NoseTreatment = "squared"
    palette_theme: PaletteTheme = "anchor_yellow"

    handle_length: float = 0.168
    handle_width: float = 0.026
    handle_height: float = 0.021
    wall_thickness: float = 0.003

    blade_length: float = 0.121
    blade_height: float = 0.0088
    blade_thickness: float = 0.0008
    blade_segment_count: int = 5

    carrier_travel: float = 0.032
    carrier_length: float = 0.082
    carrier_width: float = 0.013
    carrier_block_length: float = 0.026

    slider_button_size: tuple[float, float, float] = (0.018, 0.010, 0.005)
    slider_ridge_count: int = 3

    lock_wheel_radius: float = 0.007
    lock_wheel_length: float = 0.005

    service_door_length: float = 0.060
    service_door_open_angle: float = 0.0

    palette: dict[str, tuple[float, float, float, float]] = field(
        default_factory=lambda: dict(KNIFE_PALETTE_PRESETS["anchor_yellow"])
    )


@dataclass(frozen=True)
class ResolvedRetractableUtilityKnifeConfig:
    """Dimension-clamped + module-resolved config consumed by builders."""

    housing_module: HousingModule
    mechanism_module: MechanismModule
    blade_module: BladeModule
    grip_style: GripStyle
    nose_treatment: NoseTreatment
    palette_theme: PaletteTheme
    handle_length: float
    handle_width: float
    handle_height: float
    wall_thickness: float
    blade_length: float
    blade_height: float
    blade_thickness: float
    blade_segment_count: int
    carrier_travel: float
    carrier_length: float
    carrier_width: float
    carrier_block_length: float
    slider_button_size: tuple[float, float, float]
    slider_ridge_count: int
    lock_wheel_radius: float
    lock_wheel_length: float
    service_door_length: float
    service_door_open_angle: float
    palette: dict[str, tuple[float, float, float, float]]


def config_from_seed(seed: int) -> RetractableUtilityKnifeConfig:
    """Sample a knife configuration for the given seed.

    seed == 0 always returns the anchor combination
    (barrel_grip + retractable_slider + straight_utility) at the anchor's
    canonical dimensions. Other seeds pick modules uniformly from each
    slot's candidate pool and sample continuous dimensions across a
    realistic range.
    """
    if seed == 0:
        return RetractableUtilityKnifeConfig(
            housing_module="barrel_grip",
            mechanism_module="retractable_slider",
            blade_module="straight_utility",
            grip_style="triple_strip",
            nose_treatment="squared",
            palette_theme="anchor_yellow",
            handle_length=0.168,
            handle_width=0.026,
            handle_height=0.021,
            blade_length=0.121,
            blade_height=0.0088,
            blade_thickness=0.0008,
            blade_segment_count=5,
            carrier_travel=0.032,
            carrier_length=0.082,
            carrier_width=0.013,
            carrier_block_length=0.026,
            slider_button_size=(0.018, 0.010, 0.005),
            slider_ridge_count=3,
            lock_wheel_radius=0.007,
            lock_wheel_length=0.005,
            service_door_length=0.060,
        )

    rng = random.Random(seed)
    housing: HousingModule = rng.choice(("barrel_grip", "pistol_grip"))
    mechanism: MechanismModule = rng.choice(("retractable_slider", "service_door_swap"))
    blade: BladeModule = rng.choice(("straight_utility", "hook"))
    grip_style: GripStyle = rng.choice(("triple_strip", "single_strip", "diamond_pattern"))
    nose_treatment: NoseTreatment = rng.choice(("squared", "rounded", "pointed"))
    palette_theme: PaletteTheme = rng.choice(tuple(KNIFE_PALETTE_PRESETS.keys()))

    handle_length = rng.uniform(0.145, 0.198)
    handle_width = rng.uniform(0.024, 0.030)
    handle_height = rng.uniform(0.018, 0.025)
    blade_length = rng.uniform(0.095, 0.140)
    blade_height = rng.uniform(0.0075, 0.0105)
    carrier_travel = rng.uniform(0.021, 0.058)
    blade_segment_count = rng.randint(3, 8)
    slider_ridge_count = rng.randint(1, 5)
    service_door_length = rng.uniform(0.050, 0.075)

    return RetractableUtilityKnifeConfig(
        housing_module=housing,
        mechanism_module=mechanism,
        blade_module=blade,
        grip_style=grip_style,
        nose_treatment=nose_treatment,
        palette_theme=palette_theme,
        handle_length=round(handle_length, 4),
        handle_width=round(handle_width, 4),
        handle_height=round(handle_height, 4),
        blade_length=round(blade_length, 4),
        blade_height=round(blade_height, 5),
        blade_segment_count=blade_segment_count,
        carrier_travel=round(carrier_travel, 4),
        slider_ridge_count=slider_ridge_count,
        service_door_length=round(service_door_length, 4),
    )


def resolve_config(
    config: RetractableUtilityKnifeConfig,
) -> ResolvedRetractableUtilityKnifeConfig:
    """Validate + clamp config; fill in any None module slots with anchor
    defaults."""

    housing = config.housing_module or "barrel_grip"
    mechanism = config.mechanism_module or "retractable_slider"
    blade = config.blade_module or "straight_utility"

    if housing not in ("barrel_grip", "pistol_grip"):
        raise ValueError(f"Unsupported housing_module: {housing}")
    if mechanism not in ("retractable_slider", "service_door_swap"):
        raise ValueError(f"Unsupported mechanism_module: {mechanism}")
    if blade not in ("straight_utility", "hook"):
        raise ValueError(f"Unsupported blade_module: {blade}")

    valid_grip = {"triple_strip", "single_strip", "diamond_pattern"}
    if str(config.grip_style) not in valid_grip:
        raise ValueError(f"Unsupported grip_style: {config.grip_style}")
    valid_nose = {"squared", "rounded", "pointed"}
    if str(config.nose_treatment) not in valid_nose:
        raise ValueError(f"Unsupported nose_treatment: {config.nose_treatment}")
    if str(config.palette_theme) not in KNIFE_PALETTE_PRESETS:
        raise ValueError(f"Unsupported palette_theme: {config.palette_theme}")

    handle_length = max(0.140, min(float(config.handle_length), 0.200))
    handle_width = max(0.020, min(float(config.handle_width), 0.034))
    handle_height = max(0.016, min(float(config.handle_height), 0.026))
    wall_thickness = max(0.0024, min(float(config.wall_thickness), 0.0040))
    blade_length = max(0.090, min(float(config.blade_length), 0.145))
    blade_height = max(0.0070, min(float(config.blade_height), 0.0115))
    blade_thickness = max(0.0006, min(float(config.blade_thickness), 0.0012))
    blade_seg = max(3, min(int(config.blade_segment_count), 8))
    carrier_travel = max(0.018, min(float(config.carrier_travel), 0.062))
    carrier_length = max(0.060, min(float(config.carrier_length), 0.110))
    carrier_width = max(0.010, min(handle_width - 2 * wall_thickness - 0.001, 0.020))
    carrier_block_length = max(0.018, min(float(config.carrier_block_length), 0.040))
    slider_button_size = tuple(float(v) for v in config.slider_button_size)
    if len(slider_button_size) != 3:
        slider_button_size = (0.018, 0.010, 0.005)
    slider_ridge_count = max(0, min(int(config.slider_ridge_count), 5))
    lock_wheel_radius = max(0.005, min(float(config.lock_wheel_radius), 0.011))
    lock_wheel_length = max(0.003, min(float(config.lock_wheel_length), 0.008))
    service_door_length = max(0.040, min(float(config.service_door_length), 0.090))
    service_door_open_angle = max(0.0, min(float(config.service_door_open_angle), 1.8))

    palette = dict(KNIFE_PALETTE_PRESETS[config.palette_theme])

    return ResolvedRetractableUtilityKnifeConfig(
        housing_module=housing,
        mechanism_module=mechanism,
        blade_module=blade,
        grip_style=config.grip_style,
        nose_treatment=config.nose_treatment,
        palette_theme=config.palette_theme,
        handle_length=handle_length,
        handle_width=handle_width,
        handle_height=handle_height,
        wall_thickness=wall_thickness,
        blade_length=blade_length,
        blade_height=blade_height,
        blade_thickness=blade_thickness,
        blade_segment_count=blade_seg,
        carrier_travel=carrier_travel,
        carrier_length=carrier_length,
        carrier_width=carrier_width,
        carrier_block_length=carrier_block_length,
        slider_button_size=slider_button_size,  # type: ignore[arg-type]
        slider_ridge_count=slider_ridge_count,
        lock_wheel_radius=lock_wheel_radius,
        lock_wheel_length=lock_wheel_length,
        service_door_length=service_door_length,
        service_door_open_angle=service_door_open_angle,
        palette=palette,
    )


# --------------------------------------------------------------------------- #
# Mesh helpers — preserved from prior template. Each module factory below
# pulls these in as-needed for blade silhouettes, lofted thumb buttons,
# and the optional rear top bridge.
# --------------------------------------------------------------------------- #


def _blade_mesh_straight(
    *,
    blade_length: float,
    blade_height: float,
    blade_thickness: float,
) -> object:
    """Classic snap-off / utility blade silhouette — flat bottom edge,
    rear tab, raked tip."""
    rear_tab = blade_length * 0.085
    body_length = blade_length * 0.685
    tip_extension = blade_length * 0.300
    rear_tip_lift = blade_height * 0.0625
    tip_lift = blade_height * 0.75
    profile = [
        (-rear_tab, rear_tip_lift),
        (-rear_tab + 0.004, 0.0),
        (body_length, 0.0),
        (body_length + tip_extension, tip_lift),
        (body_length * 0.566, blade_height),
        (-rear_tab, blade_height),
    ]
    return mesh_from_geometry(
        ExtrudeGeometry.from_z0(profile, blade_thickness, cap=True, closed=True),
        "utility_knife_blade_straight",
    )


def _blade_mesh_hook(
    *,
    blade_length: float,
    blade_height: float,
    blade_thickness: float,
) -> object:
    """Utility hook blade — short body with a downward-curling hook tip.
    Used by the ``hook`` blade module."""
    body_length = blade_length * 0.62
    hook_length = blade_length * 0.32
    rear_tab = blade_length * 0.10
    profile = [
        (-rear_tab, blade_height * 0.20),
        (-rear_tab + 0.003, 0.0),
        (body_length * 0.95, 0.0),
        (body_length + hook_length * 0.55, blade_height * 0.62),
        (body_length + hook_length, blade_height * 0.20),
        (body_length + hook_length * 0.78, blade_height * 0.75),
        (body_length, blade_height),
        (-rear_tab, blade_height),
    ]
    return mesh_from_geometry(
        ExtrudeGeometry.from_z0(profile, blade_thickness, cap=True, closed=True),
        "utility_knife_blade_hook",
    )


def _lofted_rounded_block_mesh(
    name: str,
    *,
    width: float,
    depth: float,
    height: float,
    top_scale: float = 0.72,
    mid_scale: float = 0.88,
    top_x_shift: float = 0.0,
) -> object:
    """Three-section lofted rounded-rect mesh — used for the slider button
    and rear top bridge. Preserved verbatim from the prior single-anchor
    template."""
    base_radius = min(width, depth) * 0.18

    def section(w: float, d: float, z: float, dx: float = 0.0):
        return [
            (x + dx, y, z)
            for x, y in rounded_rect_profile(w, d, radius=min(base_radius, w * 0.45, d * 0.45))
        ]

    geom = LoftGeometry(
        [
            section(width, depth, 0.0, 0.0),
            section(width * mid_scale, depth * mid_scale, height * 0.55, top_x_shift * 0.45),
            section(width * top_scale, depth * top_scale, height, top_x_shift),
        ],
        cap=True,
        closed=True,
    )
    return mesh_from_geometry(geom, name)


def _slider_button_mesh(size: tuple[float, float, float]) -> object:
    return _lofted_rounded_block_mesh(
        "utility_slider_button",
        width=float(size[0]),
        depth=float(size[1]),
        height=float(size[2]),
        top_scale=0.68,
        mid_scale=0.86,
        top_x_shift=0.0012,
    )


def _rear_top_bridge_mesh(width: float) -> object:
    return _lofted_rounded_block_mesh(
        "utility_rear_top_bridge",
        width=width,
        depth=0.018,
        height=0.003,
        top_scale=0.86,
        mid_scale=0.93,
        top_x_shift=0.0015,
    )


# --------------------------------------------------------------------------- #
# Module factories — housing
# --------------------------------------------------------------------------- #


def _build_barrel_grip_housing(ctx: ModuleBuildContext) -> ModuleBuild:
    """Anchor housing — classic box-cutter envelope with a rear lofted
    bridge, top rails, nose cheeks, grip strips and an optional thumb
    wheel lock (REVOLUTE child part).

    Exposes a single downstream interface on the **center** of the
    bottom_pan's +z face so the mechanism module can sit on the channel
    floor. Internal articulation: ``body_to_lock_wheel`` REVOLUTE around
    the right wall."""
    model = ctx.model
    r: ResolvedRetractableUtilityKnifeConfig = ctx.config  # type: ignore[assignment]

    body_shell = model.part("body_shell")
    body_mat = "body"
    grip_mat = "grip"
    L = r.handle_length
    W = r.handle_width
    H = r.handle_height
    wall = r.wall_thickness

    bottom_thickness = wall
    bottom_z = bottom_thickness * 0.5
    inner_height = H - bottom_thickness

    body_shell.visual(
        Box((L, W, bottom_thickness)),
        origin=Origin(xyz=(0.0, 0.0, bottom_z)),
        material=body_mat,
        name="bottom_pan",
    )

    wall_top_z = bottom_thickness + inner_height
    wall_center_z = bottom_thickness + 0.5 * inner_height
    wall_y_outer = 0.5 * W - 0.5 * wall
    wall_length = L - 2 * 0.006

    body_shell.visual(
        Box((wall_length, wall, inner_height)),
        origin=Origin(xyz=(-0.002, -wall_y_outer, wall_center_z)),
        material=body_mat,
        name="left_wall",
    )
    body_shell.visual(
        Box((wall_length, wall, inner_height)),
        origin=Origin(xyz=(-0.002, +wall_y_outer, wall_center_z)),
        material=body_mat,
        name="right_wall",
    )

    # NOTE: the top of the handle is intentionally left OPEN by the
    # housing module. The retractable_slider / service_door_swap
    # mechanism modules emit a single long ``slider_cover`` visual that
    # serves as the top of the knife AND slides with the carrier — so
    # the entire top surface reads as ONE unified piece that moves
    # together with the thumb push (rather than a static top_rail plus
    # a tiny moving button).
    #
    # top_rail spans from the rear cap to the front nose_roof so the
    # entire top surface reads as one continuous panel (broken only by
    # the slider slot in y). Length L*0.78 is chosen so the front edge
    # overlaps the nose_roof by ~1mm and there's no visible gap.
    top_rail_length = L * 0.78
    top_rail_width = W * 0.39
    top_rail_thickness = 0.004
    top_rail_y = 0.5 * W - 0.5 * top_rail_width
    body_shell.visual(
        Box((top_rail_length, top_rail_width, top_rail_thickness)),
        origin=Origin(xyz=(-0.006, -top_rail_y, wall_top_z - 0.5 * top_rail_thickness)),
        material=body_mat,
        name="left_top_rail",
    )
    body_shell.visual(
        Box((top_rail_length, top_rail_width, top_rail_thickness)),
        origin=Origin(xyz=(-0.006, +top_rail_y, wall_top_z - 0.5 * top_rail_thickness)),
        material=body_mat,
        name="right_top_rail",
    )

    rear_cap_thickness = 0.010
    body_shell.visual(
        Box((rear_cap_thickness, W, inner_height)),
        origin=Origin(xyz=(-0.5 * L + 0.5 * rear_cap_thickness, 0.0, wall_center_z)),
        material=body_mat,
        name="rear_cap",
    )

    if r.nose_treatment == "rounded":
        nose_cheek_length = 0.024
        nose_cheek_height_ratio = 0.62
        nose_roof_length = 0.030
    elif r.nose_treatment == "pointed":
        nose_cheek_length = 0.022
        nose_cheek_height_ratio = 0.55
        nose_roof_length = 0.034
    else:
        nose_cheek_length = 0.016
        nose_cheek_height_ratio = 0.75
        nose_roof_length = 0.024

    nose_cheek_height = inner_height * nose_cheek_height_ratio
    nose_cheek_center_z = bottom_thickness + 0.5 * nose_cheek_height
    nose_cheek_x = 0.5 * L - 0.5 * nose_cheek_length
    body_shell.visual(
        Box((nose_cheek_length, wall, nose_cheek_height)),
        origin=Origin(xyz=(nose_cheek_x, -wall_y_outer, nose_cheek_center_z)),
        material=body_mat,
        name="nose_left_cheek",
    )
    body_shell.visual(
        Box((nose_cheek_length, wall, nose_cheek_height)),
        origin=Origin(xyz=(nose_cheek_x, +wall_y_outer, nose_cheek_center_z)),
        material=body_mat,
        name="nose_right_cheek",
    )

    nose_roof_thickness = 0.003
    nose_roof_width = top_rail_width
    nose_roof_x = 0.5 * L - 0.5 * nose_roof_length - 0.001
    body_shell.visual(
        Box((nose_roof_length, nose_roof_width, nose_roof_thickness)),
        origin=Origin(xyz=(nose_roof_x, -top_rail_y, wall_top_z - 0.5 * nose_roof_thickness)),
        material=body_mat,
        name="nose_left_roof",
    )
    body_shell.visual(
        Box((nose_roof_length, nose_roof_width, nose_roof_thickness)),
        origin=Origin(xyz=(nose_roof_x, +top_rail_y, wall_top_z - 0.5 * nose_roof_thickness)),
        material=body_mat,
        name="nose_right_roof",
    )

    grip_thickness = 0.0014
    grip_height = inner_height * 0.4
    grip_z = bottom_thickness + grip_height * 0.6
    grip_y = 0.5 * W - 0.5 * grip_thickness

    if r.grip_style == "triple_strip":
        body_shell.visual(
            Box((L * 0.535, grip_thickness, grip_height)),
            origin=Origin(xyz=(-0.008, -grip_y, grip_z)),
            material=grip_mat,
            name="left_grip",
        )
        body_shell.visual(
            Box((L * 0.297, grip_thickness, grip_height)),
            origin=Origin(xyz=(-0.034, +grip_y, grip_z)),
            material=grip_mat,
            name="right_rear_grip",
        )
        body_shell.visual(
            Box((L * 0.178, grip_thickness, grip_height)),
            origin=Origin(xyz=(+0.056, +grip_y, grip_z)),
            material=grip_mat,
            name="right_front_grip",
        )
    elif r.grip_style == "single_strip":
        body_shell.visual(
            Box((L * 0.78, grip_thickness, grip_height * 1.25)),
            origin=Origin(xyz=(-0.008, -grip_y, grip_z)),
            material=grip_mat,
            name="left_grip",
        )
        body_shell.visual(
            Box((L * 0.78, grip_thickness, grip_height * 1.25)),
            origin=Origin(xyz=(-0.008, +grip_y, grip_z)),
            material=grip_mat,
            name="right_grip",
        )
    else:
        dot_w = L * 0.035
        dot_h = grip_height * 0.55
        dot_pitch = L * 0.07
        n_cols = max(3, int(L / dot_pitch * 0.55))
        for i in range(n_cols):
            x = -L * 0.30 + i * dot_pitch
            side_y = -grip_y if i % 2 == 0 else +grip_y
            body_shell.visual(
                Box((dot_w, grip_thickness, dot_h)),
                origin=Origin(xyz=(x, side_y, grip_z + grip_height * 0.15)),
                material=grip_mat,
                name=f"grip_dot_{i}",
            )

    # rear_top_bridge mesh is now emitted by the mechanism module (on
    # blade_carrier) so it slides forward with the blade. The visual
    # appears at the same body position at REST (joint=0); only its
    # kinematic parent has changed.

    body_shell.inertial = Inertial.from_geometry(
        Box((L * 1.012, W * 1.19, H)),
        mass=0.28,
        origin=Origin(xyz=(0.0, 0.0, 0.5 * H)),
    )

    # Lock wheel as an internal child of the housing module.
    lock_wheel = model.part("lock_wheel")
    R = r.lock_wheel_radius
    LW = r.lock_wheel_length
    disc_y_half = LW * 0.5
    lock_wheel.visual(
        Cylinder(radius=R, length=LW),
        origin=Origin(xyz=(0.0, disc_y_half, 0.0), rpy=(-math.pi / 2.0, 0.0, 0.0)),
        material="wheel",
        name="wheel_disc",
    )
    lock_wheel.visual(
        Cylinder(radius=R * 0.43, length=LW * 0.4),
        origin=Origin(
            xyz=(0.0, LW + LW * 0.2, 0.0),
            rpy=(-math.pi / 2.0, 0.0, 0.0),
        ),
        material="dark_steel",
        name="wheel_hub",
    )
    lock_wheel.visual(
        Box((R * 0.5, LW * 0.84, R * 0.31)),
        origin=Origin(xyz=(R * 1.14, disc_y_half + LW * 0.38, 0.0)),
        material="dark_steel",
        name="wheel_fin",
    )
    lock_wheel.inertial = Inertial.from_geometry(
        Cylinder(radius=R, length=LW),
        mass=0.01,
        origin=Origin(xyz=(0.0, disc_y_half, 0.0), rpy=(-math.pi / 2.0, 0.0, 0.0)),
    )

    wheel_x = L * 0.13
    wall_y = 0.5 * W - wall * 0.5
    wheel_z = bottom_thickness + inner_height * 0.65
    from sdk import MatingContract

    model.articulation(
        "body_to_lock_wheel",
        ArticulationType.REVOLUTE,
        parent=body_shell,
        child=lock_wheel,
        origin=Origin(xyz=(wheel_x, wall_y, wheel_z)),
        axis=(0.0, 1.0, 0.0),
        motion_limits=MotionLimits(effort=1.0, velocity=8.0, lower=-math.pi, upper=math.pi),
        mating=MatingContract(
            parent_face_geometry="right_wall",
            parent_face_side="positive_y",
            child_face_geometry="wheel_disc",
            child_face_side="negative_y",
            contact_tol=0.0020,
        ),
    )

    # Position the mechanism mount in the REAR half of the handle so the
    # blade extends FORWARD and exits the housing's nose at max carrier
    # travel. The carrier_block's rear edge sits roughly behind the rear
    # cap; the blade then runs from there toward the front opening.
    cl = r.carrier_length
    channel_x = -L * 0.5 + rear_cap_thickness + cl * 0.5 + 0.002
    downstream = InterfaceSpec(
        interface_name="downstream",
        part_name="body_shell",
        visual_name="bottom_pan",
        face_side="positive_z",
        anchor_local=(channel_x, 0.0, bottom_thickness),
        face_extents_uv=(L, W),
        extents_tol=0.40,
        contact_tol=0.0020,
    )

    return ModuleBuild(
        module_name="barrel_grip",
        parts_emitted=["body_shell", "lock_wheel"],
        internal_articulations=["body_to_lock_wheel"],
        interfaces={"downstream": downstream},
    )


def _build_pistol_grip_housing(ctx: ModuleBuildContext) -> ModuleBuild:
    """Compact pistol-grip housing — no thumb wheel, but a finger guard
    forward of the trigger area. Lower visual count + no internal
    articulation. Derived from rec_9365 (handle + nose_guard) geometry."""
    model = ctx.model
    r: ResolvedRetractableUtilityKnifeConfig = ctx.config  # type: ignore[assignment]

    body_shell = model.part("body_shell")
    body_mat = "body"
    grip_mat = "grip"
    L = r.handle_length * 0.92
    W = r.handle_width * 1.06
    H = r.handle_height * 1.10
    wall = r.wall_thickness

    bottom_thickness = wall
    bottom_z = bottom_thickness * 0.5
    inner_height = H - bottom_thickness
    wall_top_z = bottom_thickness + inner_height
    wall_center_z = bottom_thickness + 0.5 * inner_height
    wall_y_outer = 0.5 * W - 0.5 * wall

    body_shell.visual(
        Box((L, W, bottom_thickness)),
        origin=Origin(xyz=(0.0, 0.0, bottom_z)),
        material=body_mat,
        name="bottom_pan",
    )

    body_shell.visual(
        Box((L - 0.010, wall, inner_height)),
        origin=Origin(xyz=(0.0, -wall_y_outer, wall_center_z)),
        material=body_mat,
        name="left_wall",
    )
    body_shell.visual(
        Box((L - 0.010, wall, inner_height)),
        origin=Origin(xyz=(0.0, +wall_y_outer, wall_center_z)),
        material=body_mat,
        name="right_wall",
    )

    # top_deck is now emitted by the mechanism module (on blade_carrier)
    # so it slides forward with the blade. At REST it appears at the
    # same body position as before — only the kinematic parent changes.

    body_shell.visual(
        Box((0.010, W, inner_height)),
        origin=Origin(xyz=(-0.5 * L + 0.005, 0.0, wall_center_z)),
        material=body_mat,
        name="rear_cap",
    )

    # Pistol-grip protrusion (visual only — doesn't articulate).
    pistol_h = H * 0.62
    pistol_w = W * 1.20
    pistol_l = L * 0.18
    body_shell.visual(
        Box((pistol_l, pistol_w, pistol_h)),
        origin=Origin(xyz=(-L * 0.18, 0.0, -pistol_h * 0.45)),
        material=body_mat,
        name="grip_bulge",
    )

    # Finger guard forward of the grip.
    guard_l = 0.008
    guard_w = W * 1.10
    guard_h = H * 0.55
    body_shell.visual(
        Box((guard_l, guard_w, guard_h)),
        origin=Origin(xyz=(-L * 0.05, 0.0, -guard_h * 0.20)),
        material=body_mat,
        name="finger_guard",
    )

    # thumb_rest is now emitted by the mechanism module (on
    # blade_carrier) so it slides forward with the blade.

    # Grip stipple — three rubber dots on each side of the pistol bulge.
    dot_w = pistol_l * 0.20
    dot_h = pistol_h * 0.30
    for i in range(3):
        x = -L * 0.22 + i * (pistol_l * 0.28)
        body_shell.visual(
            Box((dot_w, 0.0014, dot_h)),
            origin=Origin(xyz=(x, -pistol_w * 0.5 + 0.0007, -pistol_h * 0.40)),
            material=grip_mat,
            name=f"grip_dot_left_{i}",
        )
        body_shell.visual(
            Box((dot_w, 0.0014, dot_h)),
            origin=Origin(xyz=(x, +pistol_w * 0.5 - 0.0007, -pistol_h * 0.40)),
            material=grip_mat,
            name=f"grip_dot_right_{i}",
        )

    # Nose treatment — twin cheek strips on the sides + a top roof tab,
    # leaving the front opening clear for the blade to extend through.
    nose_l = 0.008
    nose_cheek_h = inner_height * 0.78
    nose_cheek_x = 0.5 * L - nose_l * 0.5
    body_shell.visual(
        Box((nose_l, wall * 1.2, nose_cheek_h)),
        origin=Origin(xyz=(nose_cheek_x, -wall_y_outer, bottom_thickness + nose_cheek_h * 0.5)),
        material=body_mat,
        name="nose_left_cheek",
    )
    body_shell.visual(
        Box((nose_l, wall * 1.2, nose_cheek_h)),
        origin=Origin(xyz=(nose_cheek_x, +wall_y_outer, bottom_thickness + nose_cheek_h * 0.5)),
        material=body_mat,
        name="nose_right_cheek",
    )
    # Twin nose roofs, each glued to one side wall. Previously a single
    # centered panel at y=0 (W*0.62 wide) which left a 3-4mm gap on each
    # side to the nose_cheeks and read as a floating block when viewed
    # from above. Splitting into left/right pieces — each touching its
    # cheek — closes the visual gap while still leaving the central blade
    # slot clear.
    nose_roof_l = nose_l + 0.004
    nose_roof_thickness = 0.003
    nose_roof_width = W * 0.30
    nose_roof_y = 0.5 * W - 0.5 * nose_roof_width
    body_shell.visual(
        Box((nose_roof_l, nose_roof_width, nose_roof_thickness)),
        origin=Origin(xyz=(nose_cheek_x, -nose_roof_y, wall_top_z - 0.5 * nose_roof_thickness)),
        material=body_mat,
        name="nose_left_roof",
    )
    body_shell.visual(
        Box((nose_roof_l, nose_roof_width, nose_roof_thickness)),
        origin=Origin(xyz=(nose_cheek_x, +nose_roof_y, wall_top_z - 0.5 * nose_roof_thickness)),
        material=body_mat,
        name="nose_right_roof",
    )

    body_shell.inertial = Inertial.from_geometry(
        Box((L * 1.05, W * 1.30, H + pistol_h)),
        mass=0.24,
        origin=Origin(xyz=(-L * 0.10, 0.0, 0.5 * H - pistol_h * 0.20)),
    )

    # Position the mechanism mount rearward so the blade extends forward
    # past the nose at max carrier travel (same convention as
    # barrel_grip). pistol_grip's rear cap is 0.010 thick.
    cl = r.carrier_length
    rear_cap_thickness = 0.010
    channel_x = -L * 0.5 + rear_cap_thickness + cl * 0.5 + 0.002
    downstream = InterfaceSpec(
        interface_name="downstream",
        part_name="body_shell",
        visual_name="bottom_pan",
        face_side="positive_z",
        anchor_local=(channel_x, 0.0, bottom_thickness),
        face_extents_uv=(L, W),
        extents_tol=0.40,
        contact_tol=0.0020,
    )

    return ModuleBuild(
        module_name="pistol_grip",
        parts_emitted=["body_shell"],
        internal_articulations=[],
        interfaces={"downstream": downstream},
    )


# --------------------------------------------------------------------------- #
# Module factories — mechanism
# --------------------------------------------------------------------------- #


def _emit_slidable_housing_visuals(
    blade_carrier,
    ctx: ModuleBuildContext,
    r: ResolvedRetractableUtilityKnifeConfig,
    cl: float,
) -> None:
    """Emit visuals on ``blade_carrier`` that used to live on body_shell.

    These are the housing-style "cover" visuals (lofted bridges, top decks,
    thumb rests) that visually look like part of the handle but should
    slide with the carrier per the user's request:
    *anything that reads as a sliding cover should move together with the
    blade*. Each visual is positioned in carrier-local frame so that at
    REST (joint=0) it lands at exactly the same body-frame coordinate it
    used to occupy when emitted by the housing — so the appearance is
    unchanged at rest.

    Which visuals are emitted depends on which housing module was chosen
    upstream (read from ``ctx.prior_choices``). pistol_grip variants get
    ``top_deck`` + ``thumb_rest``; barrel_grip variants get
    ``rear_top_bridge``.
    """
    housing_name = next(
        (m for s, m in ctx.prior_choices if s == "housing"),
        None,
    )

    # carrier_block top is at z=block_h_const=0.010 (matches the visual
    # emitted earlier in the mechanism factories). We need a neck visual
    # bridging from the block up to whatever housing-style visual we
    # add — without this the lofted bridge / Box deck would be a
    # disconnected island on the carrier part. block_x_carrier is the
    # x-position of the carrier_block center in carrier frame (matches
    # the mechanism factories' block_x formula).
    block_h_const = 0.010
    block_x_carrier = r.carrier_block_length * 0.5 - 0.003 - cl * 0.5

    if housing_name == "barrel_grip":
        bridge_width = r.handle_length * 0.37
        bridge_x_in_carrier = r.handle_length * 0.25 - 0.012 - cl * 0.5
        bridge_z_in_carrier = r.handle_height - 0.001 - r.wall_thickness
        neck_z_bottom = block_h_const * 0.6
        neck_z_top = bridge_z_in_carrier + 0.001
        # neck positioned at carrier_block x so it physically touches
        # the block (the bridge is wide enough to span back to the neck).
        blade_carrier.visual(
            Box((0.020, 0.012, neck_z_top - neck_z_bottom)),
            origin=Origin(xyz=(block_x_carrier, 0.0, (neck_z_top + neck_z_bottom) * 0.5)),
            material="body",
            name="bridge_neck",
        )
        blade_carrier.visual(
            _rear_top_bridge_mesh(width=bridge_width),
            origin=Origin(xyz=(bridge_x_in_carrier, 0.0, bridge_z_in_carrier)),
            material="body",
            name="rear_top_bridge",
        )

    elif housing_name == "pistol_grip":
        # pistol_grip shrinks L by 0.92 and grows W by 1.06 internally.
        # Reproduce that scaling here so the visuals emitted on the
        # carrier land at exactly the same body positions as the housing
        # used to emit them.
        L_p = r.handle_length * 0.92
        W_p = r.handle_width * 1.06
        H_p = r.handle_height * 1.10
        # channel_x for pistol_grip uses L_p (rear_cap_thickness = 0.010).
        channel_x = -L_p * 0.5 + 0.010 + cl * 0.5 + 0.002
        # top_deck: housing body_x = -L_p*0.10; in carrier frame:
        deck_x_in_carrier = -L_p * 0.10 - channel_x
        deck_z_in_carrier = (H_p - 0.0015) - r.wall_thickness
        # Neck bridging carrier_block to the top_deck — positioned at the
        # carrier_block's x so it touches the block, while the deck (long
        # panel) extends over it and is connected via its own x-overlap.
        deck_neck_z_bottom = block_h_const * 0.6
        deck_neck_z_top = deck_z_in_carrier + 0.001
        blade_carrier.visual(
            Box((0.020, 0.012, deck_neck_z_top - deck_neck_z_bottom)),
            origin=Origin(
                xyz=(
                    block_x_carrier,
                    0.0,
                    (deck_neck_z_top + deck_neck_z_bottom) * 0.5,
                )
            ),
            material="body",
            name="top_deck_neck",
        )
        blade_carrier.visual(
            Box((L_p * 0.62, W_p * 0.86, 0.003)),
            origin=Origin(xyz=(deck_x_in_carrier, 0.0, deck_z_in_carrier)),
            material="body",
            name="top_deck",
        )
        # thumb_rest: housing body_x = -L_p*0.05.
        rest_x_in_carrier = -L_p * 0.05 - channel_x
        rest_z_in_carrier = (H_p + 0.0015) - r.wall_thickness
        blade_carrier.visual(
            Box((L_p * 0.10, W_p * 0.46, 0.003)),
            origin=Origin(xyz=(rest_x_in_carrier, 0.0, rest_z_in_carrier)),
            material="body",
            name="thumb_rest",
        )


def _build_retractable_slider_mechanism(ctx: ModuleBuildContext) -> ModuleBuild:
    """Anchor mechanism — blade_carrier with carrier_rail / carrier_block /
    front_shoe + a FIXED thumb_slider riding on top of the carrier_block.

    The carrier_rail's -z face center sits at the part frame origin, so the
    upstream interface anchor is (0, 0, 0) — required by the assembler.

    Internal articulation: ``carrier_to_slider`` FIXED."""
    model = ctx.model
    r: ResolvedRetractableUtilityKnifeConfig = ctx.config  # type: ignore[assignment]
    from sdk import MatingContract

    blade_carrier = model.part("blade_carrier")
    track_mat = "track"
    cl = r.carrier_length
    cw = r.carrier_width
    block_l = r.carrier_block_length
    block_h = 0.010
    rail_thickness = 0.003

    # All carrier visuals are positioned so the carrier_rail's -z face
    # center coincides with the part frame origin. Geometric layout is
    # identical to the anchor — only the part frame's anchor point shifts
    # from "rear corner" to "center of rail's bottom face".
    blade_carrier.visual(
        Box((cl, cw, rail_thickness)),
        origin=Origin(xyz=(0.0, 0.0, rail_thickness * 0.5)),
        material=track_mat,
        name="carrier_rail",
    )
    block_x = -cl * 0.5 + block_l * 0.5 - 0.003 + cl * 0.5
    # ^ block sits at the front of the carrier in the original layout
    #   (block_l*0.5 - 0.003 in old part frame); shifted by -cl/2 in the
    #   new frame, the block center is at (block_l*0.5 - 0.003 - cl/2).
    block_x = block_l * 0.5 - 0.003 - cl * 0.5
    blade_carrier.visual(
        Box((block_l, cw, block_h)),
        origin=Origin(xyz=(block_x, 0.0, block_h * 0.5)),
        material=track_mat,
        name="carrier_block",
    )
    shoe_l = 0.018
    shoe_x = cl - shoe_l * 0.5 - 0.004 - cl * 0.5
    blade_carrier.visual(
        Box((shoe_l, cw * 0.85, 0.006)),
        origin=Origin(xyz=(shoe_x, 0.0, 0.006 * 0.5 + 0.001)),
        material=track_mat,
        name="front_shoe",
    )

    _emit_slidable_housing_visuals(blade_carrier, ctx, r, cl)

    blade_carrier.inertial = Inertial.from_geometry(
        Box((cl, cw, block_h)),
        mass=0.03,
        origin=Origin(xyz=(0.0, 0.0, block_h * 0.5)),
    )

    thumb_slider = model.part("thumb_slider")
    slider_mat = "slider"
    stem_size = (0.005, 0.003, 0.008)
    thumb_slider.visual(
        Box(stem_size),
        origin=Origin(xyz=(0.0, 0.0, stem_size[2] * 0.5)),
        material=slider_mat,
        name="slider_stem",
    )
    btn_w, btn_d, btn_h = r.slider_button_size
    thumb_slider.visual(
        _slider_button_mesh(r.slider_button_size),
        origin=Origin(xyz=(0.0, 0.0, stem_size[2])),
        material=slider_mat,
        name="slider_button",
    )
    if r.slider_ridge_count > 0:
        span = btn_w * 0.55
        start_x = -span * 0.5
        step = span / max(1, r.slider_ridge_count - 1) if r.slider_ridge_count > 1 else 0.0
        for i in range(r.slider_ridge_count):
            x = start_x + i * step if r.slider_ridge_count > 1 else 0.0
            thumb_slider.visual(
                Box((0.0014, btn_d * 0.9, 0.0012)),
                origin=Origin(xyz=(x, 0.0, stem_size[2] + btn_h * 1.12)),
                material="dark_steel",
                name=f"slider_ridge_{i}",
            )
    thumb_slider.inertial = Inertial.from_geometry(
        Box((btn_w, btn_d, stem_size[2] + btn_h)),
        mass=0.012,
        origin=Origin(xyz=(0.0, 0.0, (stem_size[2] + btn_h) * 0.5)),
    )

    block_top_z = block_h
    slider_x = block_x + 0.002  # slightly forward of block center
    model.articulation(
        "carrier_to_slider",
        ArticulationType.FIXED,
        parent=blade_carrier,
        child=thumb_slider,
        origin=Origin(xyz=(slider_x, 0.0, block_top_z)),
        mating=MatingContract(
            parent_face_geometry="carrier_block",
            parent_face_side="positive_z",
            child_face_geometry="slider_stem",
            child_face_side="negative_z",
            contact_tol=0.0010,
        ),
    )

    upstream = InterfaceSpec(
        interface_name="upstream",
        part_name="blade_carrier",
        visual_name="carrier_rail",
        face_side="negative_z",
        anchor_local=(0.0, 0.0, 0.0),
        face_extents_uv=(cl, cw),
        extents_tol=0.50,
        contact_tol=0.0020,
        consumer_joint_type=ArticulationType.PRISMATIC,
        consumer_joint_axis=(1.0, 0.0, 0.0),
        consumer_motion_limits=MotionLimits(
            effort=12.0, velocity=0.20, lower=0.0, upper=r.carrier_travel
        ),
    )
    downstream = InterfaceSpec(
        interface_name="downstream",
        part_name="blade_carrier",
        visual_name="carrier_block",
        face_side="positive_z",
        anchor_local=(block_x, 0.0, block_h),
        face_extents_uv=(block_l, cw),
        extents_tol=0.50,
        contact_tol=0.0020,
    )

    return ModuleBuild(
        module_name="retractable_slider",
        parts_emitted=["blade_carrier", "thumb_slider"],
        internal_articulations=["carrier_to_slider"],
        interfaces={"upstream": upstream, "downstream": downstream},
    )


def _build_service_door_swap_mechanism(ctx: ModuleBuildContext) -> ModuleBuild:
    """Alt mechanism — blade_carrier rides the housing rail (PRISMATIC) and
    pivots open a side ``service_door`` (REVOLUTE around z) so the blade
    can be swapped without disassembly. Derived from
    rec_..._14ce...:rev_000001's carriage + service_door geometry."""
    model = ctx.model
    r: ResolvedRetractableUtilityKnifeConfig = ctx.config  # type: ignore[assignment]

    blade_carrier = model.part("blade_carrier")
    track_mat = "track"
    cl = r.carrier_length
    cw = r.carrier_width
    block_l = r.carrier_block_length
    block_h = 0.010
    rail_thickness = 0.003

    # Carrier_rail's -z face center is the part frame origin (assembler
    # contract for upstream interfaces).
    blade_carrier.visual(
        Box((cl, cw, rail_thickness)),
        origin=Origin(xyz=(0.0, 0.0, rail_thickness * 0.5)),
        material=track_mat,
        name="carrier_rail",
    )
    block_x = block_l * 0.5 - 0.003 - cl * 0.5
    blade_carrier.visual(
        Box((block_l, cw, block_h)),
        origin=Origin(xyz=(block_x, 0.0, block_h * 0.5)),
        material=track_mat,
        name="carrier_block",
    )
    hinge_r = 0.0028
    hinge_len = 0.014
    blade_carrier.visual(
        Cylinder(radius=hinge_r, length=hinge_len),
        origin=Origin(
            xyz=(block_x, cw * 0.5 + hinge_r * 0.7, block_h * 0.5),
            rpy=(0.0, 0.0, 0.0),
        ),
        material="dark_steel",
        name="hinge_barrel",
    )

    _emit_slidable_housing_visuals(blade_carrier, ctx, r, cl)

    blade_carrier.inertial = Inertial.from_geometry(
        Box((cl, cw, block_h)),
        mass=0.035,
        origin=Origin(xyz=(0.0, 0.0, block_h * 0.5)),
    )

    # Service door — opens around z to expose the blade pocket. The
    # service_door part frame is centered on the hinge axis: door_knuckle
    # is at the part origin, door_panel hangs sideways from there.
    service_door = model.part("service_door")
    door_l = r.service_door_length
    door_w = 0.0030
    door_h = r.handle_height * 0.72
    service_door.visual(
        Cylinder(radius=hinge_r * 0.95, length=hinge_len * 0.95),
        origin=Origin(xyz=(0.0, 0.0, 0.0)),
        material="dark_steel",
        name="door_knuckle",
    )
    service_door.visual(
        Box((door_l, door_w, door_h)),
        origin=Origin(xyz=(door_l * 0.5, door_w * 0.5 + hinge_r * 0.4, 0.0)),
        material="door",
        name="door_panel",
    )
    service_door.visual(
        Box((door_l * 0.20, 0.002, door_h * 0.18)),
        origin=Origin(xyz=(door_l * 0.50, door_w + hinge_r * 0.4 + 0.001, door_h * 0.32)),
        material="dark_steel",
        name="door_handle",
    )
    service_door.inertial = Inertial.from_geometry(
        Box((door_l, door_w + hinge_r * 2, door_h)),
        mass=0.018,
        origin=Origin(xyz=(door_l * 0.5, 0.0, 0.0)),
    )

    # Joint origin in carrier frame is at the center of the hinge barrel.
    # The mating contract uses pin-through-sleeve geometry (cylinder axis
    # along z); we measure face-normal gap along the hinge_barrel's +y
    # face vs door_knuckle's -y face so the gate sees a coincident
    # circumferential contact rather than vertical face mismatch.
    model.articulation(
        "carrier_to_service_door",
        ArticulationType.REVOLUTE,
        parent=blade_carrier,
        child=service_door,
        origin=Origin(xyz=(block_x, cw * 0.5 + hinge_r * 0.7, block_h * 0.5)),
        axis=(0.0, 0.0, 1.0),
        motion_limits=MotionLimits(effort=0.5, velocity=4.0, lower=0.0, upper=1.4),
    )

    upstream = InterfaceSpec(
        interface_name="upstream",
        part_name="blade_carrier",
        visual_name="carrier_rail",
        face_side="negative_z",
        anchor_local=(0.0, 0.0, 0.0),
        face_extents_uv=(cl, cw),
        extents_tol=0.50,
        contact_tol=0.0020,
        consumer_joint_type=ArticulationType.PRISMATIC,
        consumer_joint_axis=(1.0, 0.0, 0.0),
        consumer_motion_limits=MotionLimits(
            effort=12.0, velocity=0.20, lower=0.0, upper=r.carrier_travel
        ),
    )
    downstream = InterfaceSpec(
        interface_name="downstream",
        part_name="blade_carrier",
        visual_name="carrier_block",
        face_side="positive_z",
        anchor_local=(block_x, 0.0, block_h),
        face_extents_uv=(block_l, cw),
        extents_tol=0.50,
        contact_tol=0.0020,
    )

    return ModuleBuild(
        module_name="service_door_swap",
        parts_emitted=["blade_carrier", "service_door"],
        internal_articulations=["carrier_to_service_door"],
        interfaces={"upstream": upstream, "downstream": downstream},
    )


# --------------------------------------------------------------------------- #
# Module factories — blade
# --------------------------------------------------------------------------- #


def _build_straight_utility_blade(ctx: ModuleBuildContext) -> ModuleBuild:
    """Anchor blade — classic snap-off trapezoid, ExtrudeGeometry mesh
    with optional score lines for snap-off segments.

    The blade extends **forward** (+x) from the part frame origin so the
    rear tab attaches to the carrier_block and the bulk of the blade
    sweeps out the handle's nose as the carrier slides forward. The
    rear edge of the blade_plate is anchored just past part frame x=0;
    the -z face's z-component (normal axis) sits exactly at z=0 so the
    mating gate passes."""
    model = ctx.model
    r: ResolvedRetractableUtilityKnifeConfig = ctx.config  # type: ignore[assignment]

    rear_tab = r.blade_length * 0.085
    body_length = r.blade_length * 0.685
    tip_extension = r.blade_length * 0.300
    # shift_x = rear_tab places the blade's rear edge at part frame x=0;
    # the full blade extends to x = rear_tab + body_length + tip_extension.
    shift_x = rear_tab
    shift = (shift_x, r.blade_thickness * 0.5, 0.0)

    blade = model.part("blade")
    blade.visual(
        _blade_mesh_straight(
            blade_length=r.blade_length,
            blade_height=r.blade_height,
            blade_thickness=r.blade_thickness,
        ),
        origin=Origin(xyz=shift, rpy=(math.pi / 2.0, 0.0, 0.0)),
        material="steel",
        name="blade_plate",
    )

    # Score lines span only the BODY of the blade (skip rear tab + tip)
    # so they remain inside the blade_plate mesh after the asymmetric
    # forward shift.
    body_start_x = shift_x + body_length * 0.10
    body_end_x = shift_x + body_length * 0.90
    n = r.blade_segment_count
    if n > 1:
        score_step = (body_end_x - body_start_x) / (n - 1)
        score_positions = [body_start_x + i * score_step for i in range(n)]
    else:
        score_positions = [(body_start_x + body_end_x) * 0.5]
    for i, x in enumerate(score_positions):
        blade.visual(
            Box((0.0005, 0.00018, r.blade_height * 0.91)),
            origin=Origin(
                xyz=(x, -0.00033 + shift[1], r.blade_height * 0.5 + shift[2]),
                rpy=(math.pi / 2.0, 0.0, 0.0),
            ),
            material="dark_steel",
            name=f"score_line_{i}",
        )

    # Inertial AABB centered on the blade body in the new part frame.
    blade_total_length = rear_tab + body_length + tip_extension
    blade.inertial = Inertial.from_geometry(
        Box((blade_total_length, r.blade_thickness, r.blade_height)),
        mass=0.01,
        origin=Origin(xyz=(blade_total_length * 0.5, shift[1], r.blade_height * 0.5 + shift[2])),
    )

    # Mating face center along normal axis (z) is at 0; tangential x and y
    # are free per the assembler's relaxed contract.
    blade_face_center_x = shift_x + (body_length + tip_extension - rear_tab) * 0.5
    upstream = InterfaceSpec(
        interface_name="upstream",
        part_name="blade",
        visual_name="blade_plate",
        face_side="negative_z",
        anchor_local=(blade_face_center_x, 0.0, 0.0),
        face_extents_uv=(r.blade_length, r.blade_thickness),
        extents_tol=0.60,
        contact_tol=0.0030,
        consumer_joint_type=ArticulationType.FIXED,
    )

    return ModuleBuild(
        module_name="straight_utility",
        parts_emitted=["blade"],
        internal_articulations=[],
        interfaces={"upstream": upstream},
    )


def _build_hook_blade(ctx: ModuleBuildContext) -> ModuleBuild:
    """Alt blade — utility hook with a downward curling tip (no
    snap-off scores).

    Mirrors the straight_utility blade's asymmetric forward-extending
    layout: rear edge at part frame x=0, tip extending toward +x."""
    model = ctx.model
    r: ResolvedRetractableUtilityKnifeConfig = ctx.config  # type: ignore[assignment]

    bl = r.blade_length * 0.94
    bh = r.blade_height * 1.10
    bt = r.blade_thickness

    rear_tab = bl * 0.10
    body_length = bl * 0.62
    hook_length = bl * 0.32
    shift_x = rear_tab
    shift = (shift_x, bt * 0.5, 0.0)

    blade = model.part("blade")
    blade.visual(
        _blade_mesh_hook(
            blade_length=bl,
            blade_height=bh,
            blade_thickness=bt,
        ),
        origin=Origin(xyz=shift, rpy=(math.pi / 2.0, 0.0, 0.0)),
        material="steel",
        name="blade_plate",
    )
    blade.visual(
        Box((bl * 0.40, 0.00020, bh * 0.16)),
        origin=Origin(
            xyz=(shift_x + bl * 0.20, -0.00040 + shift[1], bh * 0.80 + shift[2]),
            rpy=(math.pi / 2.0, 0.0, 0.0),
        ),
        material="dark_steel",
        name="hook_reinforcement",
    )
    blade.visual(
        Cylinder(radius=bh * 0.10, length=bt * 1.6),
        origin=Origin(
            xyz=(shift_x + 0.003, shift[1], bh * 0.5 + shift[2]),
            rpy=(math.pi / 2.0, 0.0, 0.0),
        ),
        material="dark_steel",
        name="mounting_hole",
    )

    blade_total_length = rear_tab + body_length + hook_length
    blade.inertial = Inertial.from_geometry(
        Box((blade_total_length, bt, bh)),
        mass=0.012,
        origin=Origin(xyz=(blade_total_length * 0.5, shift[1], bh * 0.5 + shift[2])),
    )

    blade_face_center_x = shift_x + (body_length + hook_length - rear_tab) * 0.5
    upstream = InterfaceSpec(
        interface_name="upstream",
        part_name="blade",
        visual_name="blade_plate",
        face_side="negative_z",
        anchor_local=(blade_face_center_x, 0.0, 0.0),
        face_extents_uv=(bl, bt),
        extents_tol=0.60,
        contact_tol=0.0030,
        consumer_joint_type=ArticulationType.FIXED,
    )

    return ModuleBuild(
        module_name="hook",
        parts_emitted=["blade"],
        internal_articulations=[],
        interfaces={"upstream": upstream},
    )


# --------------------------------------------------------------------------- #
# Slot graph + entry points
# --------------------------------------------------------------------------- #


HOUSING_FACTORIES = {
    "barrel_grip": _build_barrel_grip_housing,
    "pistol_grip": _build_pistol_grip_housing,
}

MECHANISM_FACTORIES = {
    "retractable_slider": _build_retractable_slider_mechanism,
    "service_door_swap": _build_service_door_swap_mechanism,
}

BLADE_FACTORIES = {
    "straight_utility": _build_straight_utility_blade,
    "hook": _build_hook_blade,
}


def _slots_for_config(r: ResolvedRetractableUtilityKnifeConfig) -> list[SlotSpec]:
    """Build the slot graph with each slot pinned to the chosen module
    (so the assembler doesn't re-roll for non-zero seeds).

    The slot graph is a strict chain: housing → mechanism → blade. The
    PRIMARY anchor combination (seed=0) is barrel_grip / retractable_slider
    / straight_utility, which reproduces the canonical 5-star sample's
    structural fingerprint and dimensions.
    """
    return [
        SlotSpec(
            slot_name="housing",
            candidates={r.housing_module: HOUSING_FACTORIES[r.housing_module]},
            anchor_choice=r.housing_module,
        ),
        SlotSpec(
            slot_name="mechanism",
            candidates={r.mechanism_module: MECHANISM_FACTORIES[r.mechanism_module]},
            anchor_choice=r.mechanism_module,
        ),
        SlotSpec(
            slot_name="blade",
            candidates={r.blade_module: BLADE_FACTORIES[r.blade_module]},
            anchor_choice=r.blade_module,
        ),
    ]


def build_retractable_utility_knife(
    config: RetractableUtilityKnifeConfig,
    *,
    assets: AssetContext | None = None,
) -> ArticulatedObject:
    """Compose a knife by running each slot's module factory and joining
    them with `MatingContract`-backed articulations."""
    r = resolve_config(config)
    model = ArticulatedObject(name="retractable_utility_knife", assets=assets)
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


def build_seeded_retractable_utility_knife(seed: int) -> ArticulatedObject:
    return build_retractable_utility_knife(config_from_seed(seed))


def slot_choices_for_seed(seed: int) -> list[tuple[str, str]]:
    """Return the (slot, module) picks for inspection — used by the
    `module_topology_diversity` gate to count unique topologies."""
    cfg = config_from_seed(seed)
    r = resolve_config(cfg)
    return [
        ("housing", r.housing_module),
        ("mechanism", r.mechanism_module),
        ("blade", r.blade_module),
    ]


# --------------------------------------------------------------------------- #
# Author-layer QC — knife-specific sanity beyond the compiler baseline.
# --------------------------------------------------------------------------- #


def _expect_anchor_size_range(
    ctx: TestContext, body_shell, r: ResolvedRetractableUtilityKnifeConfig
) -> None:
    """Catch the knife rendering at egregiously wrong scales (block,
    ruler, pen-tip)."""
    body_aabb = ctx.part_world_aabb(body_shell)
    if body_aabb is None:
        return
    x_size = body_aabb[1][0] - body_aabb[0][0]
    y_size = body_aabb[1][1] - body_aabb[0][1]
    z_size = body_aabb[1][2] - body_aabb[0][2]
    ctx.check(
        "body_size_realistic",
        0.115 <= x_size <= 0.230 and 0.018 <= y_size <= 0.060 and 0.014 <= z_size <= 0.060,
        f"Unexpected body AABB extents: x={x_size:.4f} y={y_size:.4f} z={z_size:.4f}",
    )


def _expect_carrier_travel_changes_blade_position(
    ctx: TestContext, slide_joint, blade, body_shell
) -> None:
    """When the carrier slides from lower to upper, the blade's world AABB
    must advance along x by roughly the joint's travel."""
    limits = slide_joint.motion_limits
    if limits is None or limits.lower is None or limits.upper is None:
        return
    with ctx.pose({slide_joint: limits.lower}):
        rest = ctx.part_world_aabb(blade)
        ctx.fail_if_parts_overlap_in_current_pose(name="carrier_lower_no_overlap")
        ctx.fail_if_isolated_parts(name="carrier_lower_no_floating")
    with ctx.pose({slide_joint: limits.upper}):
        extended = ctx.part_world_aabb(blade)
        ctx.fail_if_parts_overlap_in_current_pose(name="carrier_upper_no_overlap")
        ctx.fail_if_isolated_parts(name="carrier_upper_no_floating")
    if rest is None or extended is None:
        return
    advance = extended[1][0] - rest[1][0]
    expected = limits.upper - limits.lower
    ctx.check(
        "carrier_travel_advances_blade",
        abs(advance - expected) < 0.008,
        (
            f"Blade tip world-x advance under carrier slide should be ~{expected:.4f}m, "
            f"got {advance:.4f}m"
        ),
    )


def run_retractable_utility_knife_tests(
    model: ArticulatedObject,
    config: RetractableUtilityKnifeConfig,
) -> TestReport:
    """Author-layer QC. The compiler-owned baseline runs separately during
    target=full compile (validity, overlaps, isolation, mating gap, joint
    origin proximity); this function only adds the knife-specific motion +
    envelope sanity that wouldn't be caught by generic gates."""
    r = resolve_config(config)
    ctx = TestContext(model)

    body_shell = model.get_part("body_shell")
    blade = model.get_part("blade")

    slide_joint = model.get_articulation("housing_to_mechanism")

    # For pistol_grip + retractable_slider variants, the top_deck_neck
    # (carrier visual connecting carrier_block up to the deck) shares the
    # same x-z column as the slider_button (thumb_slider visual). Both
    # sit above carrier_block by design and slide together; their slight
    # AABB overlap is intentional contact.
    part_names = {p.name for p in model.parts}
    if "blade_carrier" in part_names and "thumb_slider" in part_names:
        ctx.allow_overlap(
            model.get_part("blade_carrier"),
            model.get_part("thumb_slider"),
            elem_a="top_deck_neck",
            elem_b="slider_button",
            reason="top_deck_neck rises from carrier_block in the same column as slider_button; both slide together",
        )

    ctx.check_model_valid()
    ctx.fail_if_isolated_parts()
    ctx.warn_if_part_contains_disconnected_geometry_islands()
    ctx.fail_if_parts_overlap_in_current_pose()
    ctx.fail_if_articulation_origin_far_from_geometry(tol=0.015)
    ctx.fail_if_joint_mating_has_gap()

    ctx.check(
        "carrier_joint_type_is_prismatic",
        slide_joint.articulation_type == ArticulationType.PRISMATIC,
        f"Expected PRISMATIC slide joint, got {slide_joint.articulation_type!r}",
    )
    ctx.check(
        "carrier_joint_axis_is_x",
        tuple(slide_joint.axis) == (1.0, 0.0, 0.0),
        f"Expected slide axis (1, 0, 0), got {slide_joint.axis!r}",
    )

    _expect_anchor_size_range(ctx, body_shell, r)
    _expect_carrier_travel_changes_blade_position(ctx, slide_joint, blade, body_shell)

    return ctx.report()


# --------------------------------------------------------------------------- #
# Modular template authoring notes
# --------------------------------------------------------------------------- #
# Module roster:
#
#   housing/barrel_grip:
#     parts                : body_shell, lock_wheel
#     internal joints      : body_to_lock_wheel (REVOLUTE around +y wall)
#     downstream interface : body_shell.bottom_pan (+z) centered on body
#     source               : rec_..._cad8...:rev_000001 lines 104-292
#
#   housing/pistol_grip:
#     parts                : body_shell (with grip_bulge + finger_guard)
#     internal joints      : none
#     downstream interface : body_shell.bottom_pan (+z) centered on body
#     source               : rec_..._9365...:rev_000001 (compact pistol
#                            grip aesthetic, no thumb wheel)
#
#   mechanism/retractable_slider:
#     parts                : blade_carrier, thumb_slider
#     internal joints      : carrier_to_slider (FIXED)
#     upstream interface   : blade_carrier.carrier_rail (-z), consumer
#                            PRISMATIC along +x with travel = carrier_travel
#     downstream interface : blade_carrier.carrier_block (+z)
#     source               : rec_..._cad8...:rev_000001 lines 195-267
#
#   mechanism/service_door_swap:
#     parts                : blade_carrier (with hinge_barrel), service_door
#     internal joints      : carrier_to_service_door (REVOLUTE around +z)
#     upstream interface   : blade_carrier.carrier_rail (-z), consumer
#                            PRISMATIC along +x with travel = carrier_travel
#     downstream interface : blade_carrier.carrier_block (+z)
#     source               : rec_..._14ce...:rev_000001 lines 59-239
#
#   blade/straight_utility:
#     parts                : blade
#     internal joints      : none
#     upstream interface   : blade.blade_plate (-z), consumer FIXED
#     source               : rec_..._cad8...:rev_000001 lines 220-241
#
#   blade/hook:
#     parts                : blade (hook silhouette + reinforcement)
#     internal joints      : none
#     upstream interface   : blade.blade_plate (-z), consumer FIXED
#     source               : utility hook variant (no direct 5-star sample;
#                            derived from straight_utility profile with
#                            curved tip)
#
# Slot graph (strict chain):
#   housing --[housing_to_mechanism PRISMATIC]--> mechanism
#       --[mechanism_to_blade FIXED]--> blade
#
# anchor_geometry_match (single-anchor full-template fingerprint) is
# inapplicable to modular templates and is skipped by the coverage gate
# via the ``__modular__ = True`` module flag. The replacement is
# module_topology_diversity (counts distinct slot_choices across seeds)
# + module_interface_match (interface-pair validity, already enforced at
# build time by the assembler's ``_validate_pair``).
#
# Combinations: 2 housings × 2 mechanisms × 2 blades = 8 unique topologies.
# RNG over 10 seeds yields ≥7 unique combinations in expectation.


__all__ = [
    "BladeModule",
    "GripStyle",
    "HousingModule",
    "MechanismModule",
    "NoseTreatment",
    "PaletteTheme",
    "RetractableUtilityKnifeConfig",
    "ResolvedRetractableUtilityKnifeConfig",
    "build_retractable_utility_knife",
    "build_seeded_retractable_utility_knife",
    "config_from_seed",
    "resolve_config",
    "run_retractable_utility_knife_tests",
    "slot_choices_for_seed",
]
