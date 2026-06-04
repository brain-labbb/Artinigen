"""Playground swing modular template.

Reviewed spec:
``articraft_template_authoring/specs/playground_swing.md``.

The category-level multiplicity is a wide playground frame carrying
``station_count`` independent swing stations. Each station samples a recipe
derived from the 5-star sample families: belt/plank, toddler bucket, tire,
lap-bar seat, platform, bench rocker, face-to-face glider, disc footrest, or
nest basket. Recipes may repeat or mix under one frame.
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
    Mimic,
    MotionLimits,
    Origin,
    Sphere,
    TestContext,
    TestReport,
    TireCarcass,
    TireGeometry,
    TireGroove,
    TireShoulder,
    TireSidewall,
    TireTread,
    TorusGeometry,
    mesh_from_geometry,
)

__modular__ = True


SupportFrameModule = Literal[
    "compact_a_frame_crossbeam",
    "multi_station_wide_frame",
]
StationRecipe = Literal[
    "simple_belt_station",
    "bucket_station",
    "tire_station",
    "lap_bar_station",
    "platform_station",
    "bench_station",
    "glider_station",
    "swivel_disc_station",
    "nest_station",
]
PaletteTheme = Literal["park_green", "safety_red", "galvanized_blue", "mixed_bright"]


STATION_RECIPES: tuple[StationRecipe, ...] = (
    "simple_belt_station",
    "bucket_station",
    "tire_station",
    "lap_bar_station",
    "platform_station",
    "bench_station",
    "glider_station",
    "swivel_disc_station",
    "nest_station",
)

PALETTES: dict[PaletteTheme, dict[str, tuple[float, float, float, float]]] = {
    "park_green": {
        "frame": (0.20, 0.36, 0.23, 1.0),
        "frame_dark": (0.10, 0.16, 0.12, 1.0),
        "steel": (0.62, 0.65, 0.66, 1.0),
        "dark": (0.08, 0.085, 0.09, 1.0),
        "rubber": (0.035, 0.035, 0.035, 1.0),
        "seat": (0.10, 0.10, 0.11, 1.0),
        "accent": (0.85, 0.10, 0.07, 1.0),
        "wood": (0.58, 0.39, 0.20, 1.0),
        "rope": (0.78, 0.62, 0.38, 1.0),
        "blue": (0.05, 0.25, 0.74, 1.0),
    },
    "safety_red": {
        "frame": (0.76, 0.08, 0.04, 1.0),
        "frame_dark": (0.32, 0.05, 0.03, 1.0),
        "steel": (0.70, 0.72, 0.73, 1.0),
        "dark": (0.09, 0.09, 0.10, 1.0),
        "rubber": (0.025, 0.025, 0.025, 1.0),
        "seat": (0.04, 0.18, 0.60, 1.0),
        "accent": (0.96, 0.70, 0.06, 1.0),
        "wood": (0.62, 0.42, 0.22, 1.0),
        "rope": (0.82, 0.66, 0.42, 1.0),
        "blue": (0.08, 0.30, 0.82, 1.0),
    },
    "galvanized_blue": {
        "frame": (0.08, 0.28, 0.68, 1.0),
        "frame_dark": (0.03, 0.08, 0.18, 1.0),
        "steel": (0.64, 0.67, 0.68, 1.0),
        "dark": (0.10, 0.11, 0.12, 1.0),
        "rubber": (0.030, 0.030, 0.030, 1.0),
        "seat": (0.11, 0.11, 0.12, 1.0),
        "accent": (0.96, 0.68, 0.08, 1.0),
        "wood": (0.55, 0.38, 0.20, 1.0),
        "rope": (0.76, 0.61, 0.39, 1.0),
        "blue": (0.03, 0.22, 0.78, 1.0),
    },
    "mixed_bright": {
        "frame": (0.92, 0.55, 0.08, 1.0),
        "frame_dark": (0.34, 0.22, 0.04, 1.0),
        "steel": (0.63, 0.65, 0.66, 1.0),
        "dark": (0.09, 0.09, 0.10, 1.0),
        "rubber": (0.030, 0.030, 0.030, 1.0),
        "seat": (0.04, 0.38, 0.44, 1.0),
        "accent": (0.82, 0.08, 0.04, 1.0),
        "wood": (0.60, 0.40, 0.18, 1.0),
        "rope": (0.82, 0.66, 0.42, 1.0),
        "blue": (0.05, 0.24, 0.78, 1.0),
    },
}

RECIPE_FOOTPRINTS: dict[StationRecipe, float] = {
    "simple_belt_station": 0.62,
    "bucket_station": 0.68,
    "tire_station": 0.92,
    "lap_bar_station": 0.72,
    "platform_station": 1.00,
    "bench_station": 1.38,
    "glider_station": 1.46,
    "swivel_disc_station": 0.58,
    "nest_station": 1.24,
}


@dataclass(frozen=True)
class PlaygroundSwingConfig:
    support_frame_module: SupportFrameModule = "compact_a_frame_crossbeam"
    station_count: int = 1
    station_recipes: tuple[StationRecipe, ...] | None = None
    palette_theme: PaletteTheme = "park_green"
    top_z: float = 2.20
    station_spacing: float = 0.18
    end_clearance: float = 0.32
    swing_limit: float = 0.62
    name: str = "playground_swing"
    palette: dict[str, tuple[float, float, float, float]] = field(
        default_factory=lambda: dict(PALETTES["park_green"])
    )


@dataclass(frozen=True)
class ResolvedPlaygroundSwingConfig:
    support_frame_module: SupportFrameModule
    station_count: int
    station_recipes: tuple[StationRecipe, ...]
    palette_theme: PaletteTheme
    top_z: float
    beam_length: float
    station_centers: tuple[float, ...]
    swing_limit: float
    name: str
    palette: dict[str, tuple[float, float, float, float]]


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, float(value)))


def _validate_recipe(name: str) -> StationRecipe:
    if name not in STATION_RECIPES:
        raise ValueError(f"Unknown playground swing station recipe: {name!r}")
    return name  # type: ignore[return-value]


def _recipe_sequence_for_seed(seed: int) -> tuple[StationRecipe, ...]:
    if seed == 0:
        return ("simple_belt_station",)
    rng = random.Random(seed)
    station_count = rng.randint(1, 5)
    recipes: list[StationRecipe] = []
    for index in range(station_count):
        if index == 0 and station_count >= 4:
            # Force at least one compact bay when the beam is very crowded.
            pool: tuple[StationRecipe, ...] = (
                "simple_belt_station",
                "bucket_station",
                "swivel_disc_station",
            )
        else:
            pool = STATION_RECIPES
        recipes.append(rng.choice(pool))
    return tuple(recipes)


def config_from_seed(seed: int) -> PlaygroundSwingConfig:
    if seed == 0:
        return PlaygroundSwingConfig(
            support_frame_module="compact_a_frame_crossbeam",
            station_count=1,
            station_recipes=("simple_belt_station",),
            palette_theme="park_green",
            name="playground_swing_anchor_seed_0",
        )
    recipes = _recipe_sequence_for_seed(seed)
    rng = random.Random(seed * 7919 + 17)
    palette_theme = rng.choice(tuple(PALETTES.keys()))
    return PlaygroundSwingConfig(
        support_frame_module="multi_station_wide_frame",
        station_count=len(recipes),
        station_recipes=recipes,
        palette_theme=palette_theme,
        swing_limit=rng.uniform(0.48, 0.72),
        name=f"seeded_playground_swing_{seed}",
    )


def resolve_config(config: PlaygroundSwingConfig) -> ResolvedPlaygroundSwingConfig:
    station_count = max(1, min(5, int(config.station_count)))
    if config.station_recipes:
        recipes = tuple(_validate_recipe(str(recipe)) for recipe in config.station_recipes)
        if len(recipes) != station_count:
            station_count = len(recipes)
    else:
        recipes = ("simple_belt_station",) * station_count

    if config.support_frame_module not in ("compact_a_frame_crossbeam", "multi_station_wide_frame"):
        support_frame_module: SupportFrameModule = "multi_station_wide_frame"
    else:
        support_frame_module = config.support_frame_module
    if support_frame_module == "compact_a_frame_crossbeam":
        station_count = 1
        recipes = recipes[:1] or ("simple_belt_station",)

    top_z = _clamp(config.top_z, 1.85, 2.45)
    spacing = _clamp(config.station_spacing, 0.12, 0.32)
    end_clearance = _clamp(config.end_clearance, 0.22, 0.55)
    footprints = [RECIPE_FOOTPRINTS[recipe] for recipe in recipes]
    beam_length = max(
        1.40, sum(footprints) + spacing * max(0, station_count - 1) + end_clearance * 2.0
    )

    centers: list[float] = []
    cursor = -beam_length / 2.0 + end_clearance
    for footprint in footprints:
        center = cursor + footprint / 2.0
        centers.append(center)
        cursor += footprint + spacing

    palette_theme = config.palette_theme if config.palette_theme in PALETTES else "park_green"
    palette = dict(PALETTES[palette_theme])
    palette.update(config.palette or {})

    return ResolvedPlaygroundSwingConfig(
        support_frame_module=support_frame_module,
        station_count=station_count,
        station_recipes=recipes,
        palette_theme=palette_theme,
        top_z=top_z,
        beam_length=beam_length,
        station_centers=tuple(centers),
        swing_limit=_clamp(config.swing_limit, 0.35, 0.85),
        name=config.name,
        palette=palette,
    )


def _segment_pose(
    start: tuple[float, float, float],
    end: tuple[float, float, float],
) -> tuple[Origin, float]:
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    dz = end[2] - start[2]
    length = math.sqrt(dx * dx + dy * dy + dz * dz)
    if length <= 1e-9:
        return Origin(xyz=start), 0.0
    yaw = math.atan2(dy, dx)
    pitch = math.acos(max(-1.0, min(1.0, dz / length)))
    return (
        Origin(
            xyz=((start[0] + end[0]) * 0.5, (start[1] + end[1]) * 0.5, (start[2] + end[2]) * 0.5),
            rpy=(0.0, pitch, yaw),
        ),
        length,
    )


def _add_tube(part, name: str, start, end, radius: float, material) -> None:
    origin, length = _segment_pose(start, end)
    part.visual(Cylinder(radius=radius, length=length), origin=origin, material=material, name=name)


def _mat(model: ArticulatedObject, key: str, rgba: tuple[float, float, float, float]):
    return model.material(key, rgba=rgba)


def _build_frame(model: ArticulatedObject, r: ResolvedPlaygroundSwingConfig) -> None:
    frame_mat = _mat(model, "frame_powder_coat", r.palette["frame"])
    frame_dark = _mat(model, "frame_dark_brace", r.palette["frame_dark"])
    steel = _mat(model, "galvanized_pivot_steel", r.palette["steel"])

    frame = model.part("frame")
    frame.inertial = Inertial.from_geometry(
        Box((r.beam_length, 1.65, r.top_z + 0.12)),
        mass=75.0 + 18.0 * r.station_count,
        origin=Origin(xyz=(0.0, 0.0, (r.top_z + 0.12) * 0.5)),
    )

    _add_tube(
        frame,
        "top_beam",
        (-r.beam_length / 2.0, 0.0, r.top_z),
        (r.beam_length / 2.0, 0.0, r.top_z),
        0.055,
        frame_mat,
    )

    support_xs = [-r.beam_length / 2.0 + 0.18, r.beam_length / 2.0 - 0.18]
    if r.station_count >= 4:
        gap_index = max(1, r.station_count // 2)
        center_support_x = (r.station_centers[gap_index - 1] + r.station_centers[gap_index]) * 0.5
        support_xs.insert(1, center_support_x)
    elif r.station_count == 3:
        frame.visual(
            Box((r.beam_length - 0.40, 0.050, 0.045)),
            origin=Origin(xyz=(0.0, -0.07, r.top_z - 0.20)),
            material=frame_dark,
            name="long_front_upper_brace",
        )
        frame.visual(
            Box((r.beam_length - 0.40, 0.050, 0.045)),
            origin=Origin(xyz=(0.0, 0.07, r.top_z - 0.20)),
            material=frame_dark,
            name="long_rear_upper_brace",
        )

    for idx, x in enumerate(support_xs):
        top = (x, 0.0, r.top_z - 0.01)
        front_foot = (x, 0.76, 0.06)
        rear_foot = (x, -0.76, 0.06)
        _add_tube(frame, f"support_{idx}_front_leg", top, front_foot, 0.040, frame_mat)
        _add_tube(frame, f"support_{idx}_rear_leg", top, rear_foot, 0.040, frame_mat)
        _add_tube(
            frame, f"support_{idx}_foot_bar", (x, -0.84, 0.055), (x, 0.84, 0.055), 0.030, frame_dark
        )
        _add_tube(
            frame, f"support_{idx}_mid_brace", (x, -0.54, 1.12), (x, 0.54, 1.12), 0.024, frame_dark
        )

    for index, x in enumerate(r.station_centers):
        # Visible bay hardware adapted from the dual-bay 5-star frame: two
        # cheek plates and a pin below the top beam for every station.
        frame.visual(
            Box((0.090, 0.036, 0.135)),
            origin=Origin(xyz=(x, -0.075, r.top_z - 0.105)),
            material=frame_mat,
            name=f"station_{index}_front_clevis_cheek",
        )
        frame.visual(
            Box((0.090, 0.036, 0.135)),
            origin=Origin(xyz=(x, 0.075, r.top_z - 0.105)),
            material=frame_mat,
            name=f"station_{index}_rear_clevis_cheek",
        )
        _add_tube(
            frame,
            f"station_{index}_pivot_pin",
            (x - 0.18, 0.0, r.top_z - 0.125),
            (x + 0.18, 0.0, r.top_z - 0.125),
            0.018,
            steel,
        )
        frame.visual(
            Box((0.12, 0.16, 0.040)),
            origin=Origin(xyz=(x, 0.0, r.top_z - 0.055)),
            material=frame_dark,
            name=f"station_{index}_hanger_block",
        )
        frame.visual(
            Box((0.13, 0.12, 0.075)),
            origin=Origin(xyz=(x, 0.0, r.top_z - 0.118)),
            material=frame_dark,
            name=f"station_{index}_pivot_saddle",
        )


def _motion(r: ResolvedPlaygroundSwingConfig, effort: float = 90.0) -> MotionLimits:
    return MotionLimits(effort=effort, velocity=1.8, lower=-r.swing_limit, upper=r.swing_limit)


def _add_top_hub(part, prefix: str, material, *, length: float = 0.42) -> None:
    part.visual(
        Cylinder(radius=0.030, length=length),
        origin=Origin(rpy=(0.0, math.pi / 2.0, 0.0)),
        material=material,
        name=f"{prefix}_upper_hub",
    )
    part.visual(
        Box((length + 0.10, 0.070, 0.055)),
        origin=Origin(xyz=(0.0, 0.0, -0.034)),
        material=material,
        name=f"{prefix}_upper_yoke_web",
    )


def _add_belt_station(
    model: ArticulatedObject, r: ResolvedPlaygroundSwingConfig, index: int, x: float
) -> None:
    steel = _mat(model, f"station_{index}_steel", r.palette["steel"])
    dark = _mat(model, f"station_{index}_dark", r.palette["dark"])
    seat_mat = _mat(model, f"station_{index}_seat", r.palette["seat"])
    swing = model.part(f"station_{index}_swing")
    _add_top_hub(swing, f"station_{index}", steel)
    drop = 1.42
    for side, sx in (("left", -0.20), ("right", 0.20)):
        _add_tube(
            swing,
            f"{side}_front_chain",
            (sx, 0.025, -0.030),
            (sx * 0.72, 0.10, -drop + 0.03),
            0.009,
            steel,
        )
        _add_tube(
            swing,
            f"{side}_rear_chain",
            (sx, -0.025, -0.030),
            (sx * 0.72, -0.10, -drop + 0.03),
            0.009,
            steel,
        )
        swing.visual(
            Box((0.060, 0.22, 0.070)),
            origin=Origin(xyz=(sx * 0.72, 0.0, -drop)),
            material=dark,
            name=f"{side}_seat_bracket",
        )
    swing.visual(
        Box((0.54, 0.24, 0.040)),
        origin=Origin(xyz=(0.0, 0.0, -drop - 0.03)),
        material=seat_mat,
        name="belt_seat",
    )
    swing.visual(
        Box((0.46, 0.20, 0.015)),
        origin=Origin(xyz=(0.0, 0.0, -drop - 0.005)),
        material=dark,
        name="seat_pad",
    )
    model.articulation(
        f"station_{index}_frame_to_swing",
        ArticulationType.REVOLUTE,
        parent="frame",
        child=swing,
        origin=Origin(xyz=(x, 0.0, r.top_z - 0.125)),
        axis=(1.0, 0.0, 0.0),
        motion_limits=_motion(r),
    )


def _add_bucket_station(
    model: ArticulatedObject, r: ResolvedPlaygroundSwingConfig, index: int, x: float
) -> None:
    steel = _mat(model, f"station_{index}_steel", r.palette["steel"])
    shell_mat = _mat(model, f"station_{index}_bucket_shell", r.palette["accent"])
    strap_mat = _mat(model, f"station_{index}_strap", r.palette["dark"])
    dark = _mat(model, f"station_{index}_bucket_shadow", r.palette["dark"])
    swing = model.part(f"station_{index}_bucket")
    _add_top_hub(swing, f"station_{index}", steel)
    drop = 1.28
    for sx in (-0.22, 0.22):
        _add_tube(
            swing,
            f"side_strap_{sx:+.1f}",
            (sx, 0.0, -0.02),
            (sx * 0.88, 0.0, -drop + 0.18),
            0.015,
            strap_mat,
        )
        swing.visual(
            Sphere(radius=0.038),
            origin=Origin(xyz=(sx * 0.88, 0.0, -drop + 0.16)),
            material=steel,
            name=f"side_bolt_{sx:+.1f}",
        )
    swing.visual(
        Box((0.54, 0.44, 0.34)),
        origin=Origin(xyz=(0.0, 0.0, -drop)),
        material=shell_mat,
        name="bucket_shell",
    )
    swing.visual(
        Box((0.22, 0.05, 0.13)),
        origin=Origin(xyz=(-0.12, 0.24, -drop - 0.02)),
        material=dark,
        name="left_leg_opening_shadow",
    )
    swing.visual(
        Box((0.22, 0.05, 0.13)),
        origin=Origin(xyz=(0.12, 0.24, -drop - 0.02)),
        material=dark,
        name="right_leg_opening_shadow",
    )
    swing.visual(
        Box((0.58, 0.055, 0.060)),
        origin=Origin(xyz=(0.0, 0.245, -drop + 0.10)),
        material=steel,
        name="front_rim",
    )
    swing.visual(
        Box((0.58, 0.055, 0.060)),
        origin=Origin(xyz=(0.0, -0.245, -drop + 0.10)),
        material=steel,
        name="rear_rim",
    )
    model.articulation(
        f"station_{index}_frame_to_bucket",
        ArticulationType.REVOLUTE,
        parent="frame",
        child=swing,
        origin=Origin(xyz=(x, 0.0, r.top_z - 0.125)),
        axis=(1.0, 0.0, 0.0),
        motion_limits=_motion(r, effort=110.0),
    )


def _add_tire_station(
    model: ArticulatedObject, r: ResolvedPlaygroundSwingConfig, index: int, x: float
) -> None:
    steel = _mat(model, f"station_{index}_steel", r.palette["steel"])
    rubber = _mat(model, f"station_{index}_rubber", r.palette["rubber"])
    accent = _mat(model, f"station_{index}_accent", r.palette["accent"])
    swing = model.part(f"station_{index}_tire")
    _add_top_hub(swing, f"station_{index}", steel, length=0.56)
    tire = TireGeometry(
        0.36,
        0.14,
        inner_radius=0.20,
        carcass=TireCarcass(belt_width_ratio=0.72, sidewall_bulge=0.08),
        tread=TireTread(style="block", depth=0.010, count=24, land_ratio=0.55),
        grooves=(TireGroove(center_offset=0.0, width=0.018, depth=0.004),),
        sidewall=TireSidewall(style="rounded", bulge=0.06),
        shoulder=TireShoulder(width=0.016, radius=0.005),
    )
    swing.visual(
        mesh_from_geometry(tire, f"station_{index}_tire_mesh"),
        origin=Origin(xyz=(0.0, 0.0, -1.22), rpy=(0.0, -math.pi / 2.0, 0.0)),
        material=rubber,
        name="tire_shell",
    )
    swing.visual(
        Box((0.64, 0.64, 0.070)),
        origin=Origin(xyz=(0.0, 0.0, -1.10)),
        material=steel,
        name="tire_anchor_spider_plate",
    )
    for name, top, bottom in (
        ("left", (-0.26, 0.0, -0.055), (-0.24, -0.17, -1.10)),
        ("center", (0.0, 0.0, -0.055), (0.0, 0.29, -1.10)),
        ("right", (0.26, 0.0, -0.055), (0.24, -0.17, -1.10)),
    ):
        _add_tube(swing, f"{name}_hanger", top, bottom, 0.016, steel)
        swing.visual(
            Sphere(radius=0.040),
            origin=Origin(xyz=bottom),
            material=accent,
            name=f"{name}_tire_clamp",
        )
        _add_tube(
            swing,
            f"{name}_tire_anchor_pin",
            bottom,
            (bottom[0], bottom[1], -1.245),
            0.020,
            steel,
        )
    model.articulation(
        f"station_{index}_frame_to_tire",
        ArticulationType.REVOLUTE,
        parent="frame",
        child=swing,
        origin=Origin(xyz=(x, 0.0, r.top_z - 0.125)),
        axis=(1.0, 0.0, 0.0),
        motion_limits=_motion(r, effort=130.0),
    )


def _add_lap_bar_station(
    model: ArticulatedObject, r: ResolvedPlaygroundSwingConfig, index: int, x: float
) -> None:
    steel = _mat(model, f"station_{index}_steel", r.palette["steel"])
    wood = _mat(model, f"station_{index}_wood", r.palette["wood"])
    red = _mat(model, f"station_{index}_red", r.palette["accent"])
    seat = model.part(f"station_{index}_slatted_seat")
    _add_top_hub(seat, f"station_{index}", steel)
    drop = 1.06
    for sx in (-0.24, 0.24):
        _add_tube(
            seat, f"hanger_{sx:+.1f}", (sx, 0.0, -0.02), (sx, 0.0, -drop + 0.01), 0.014, steel
        )
    seat.visual(
        Box((0.56, 0.35, 0.065)),
        origin=Origin(xyz=(0.0, 0.0, -drop)),
        material=steel,
        name="seat_frame",
    )
    for j, yy in enumerate((-0.13, -0.04, 0.05, 0.14)):
        seat.visual(
            Box((0.50, 0.055, 0.030)),
            origin=Origin(xyz=(0.0, yy, -drop + 0.035)),
            material=wood,
            name=f"seat_slat_{j}",
        )
    seat.visual(
        Box((0.48, 0.080, 0.130)),
        origin=Origin(xyz=(0.0, 0.18, -drop + 0.035)),
        material=steel,
        name="lap_hinge_socket",
    )
    model.articulation(
        f"station_{index}_frame_to_slatted_seat",
        ArticulationType.REVOLUTE,
        parent="frame",
        child=seat,
        origin=Origin(xyz=(x, 0.0, r.top_z - 0.125)),
        axis=(1.0, 0.0, 0.0),
        motion_limits=_motion(r),
    )
    lap = model.part(f"station_{index}_lap_bar")
    lap.visual(
        Cylinder(radius=0.018, length=0.50),
        origin=Origin(rpy=(0.0, math.pi / 2.0, 0.0)),
        material=red,
        name="lap_bar_hinge",
    )
    _add_tube(lap, "left_bar_arm", (-0.20, 0.0, 0.0), (-0.20, 0.18, 0.14), 0.012, red)
    _add_tube(lap, "right_bar_arm", (0.20, 0.0, 0.0), (0.20, 0.18, 0.14), 0.012, red)
    lap.visual(
        Cylinder(radius=0.014, length=0.44),
        origin=Origin(xyz=(0.0, 0.18, 0.14), rpy=(0.0, math.pi / 2.0, 0.0)),
        material=red,
        name="front_guard",
    )
    model.articulation(
        f"station_{index}_seat_to_lap_bar",
        ArticulationType.REVOLUTE,
        parent=seat,
        child=lap,
        origin=Origin(xyz=(0.0, 0.20, -drop + 0.11)),
        axis=(1.0, 0.0, 0.0),
        motion_limits=MotionLimits(effort=10.0, velocity=1.5, lower=0.0, upper=1.15),
    )


def _add_platform_station(
    model: ArticulatedObject, r: ResolvedPlaygroundSwingConfig, index: int, x: float
) -> None:
    steel = _mat(model, f"station_{index}_steel", r.palette["steel"])
    dark = _mat(model, f"station_{index}_dark", r.palette["dark"])
    red = _mat(model, f"station_{index}_red", r.palette["accent"])
    links = model.part(f"station_{index}_platform_links")
    _add_top_hub(links, f"station_{index}", steel, length=0.70)
    drop = 1.18
    for sx in (-0.32, 0.32):
        _add_tube(links, f"side_link_{sx:+.1f}", (sx, 0.0, -0.02), (sx, 0.0, -drop), 0.018, steel)
        links.visual(
            Cylinder(radius=0.040, length=0.075),
            origin=Origin(xyz=(sx, 0.0, -drop), rpy=(0.0, math.pi / 2.0, 0.0)),
            material=steel,
            name=f"lower_eye_{sx:+.1f}",
        )
    links.visual(
        Cylinder(radius=0.020, length=0.72),
        origin=Origin(xyz=(0.0, 0.0, -drop), rpy=(0.0, math.pi / 2.0, 0.0)),
        material=steel,
        name="lower_pivot_crossbar",
    )
    model.articulation(
        f"station_{index}_frame_to_platform_links",
        ArticulationType.REVOLUTE,
        parent="frame",
        child=links,
        origin=Origin(xyz=(x, 0.0, r.top_z - 0.125)),
        axis=(1.0, 0.0, 0.0),
        motion_limits=MotionLimits(effort=180.0, velocity=1.2, lower=-0.45, upper=0.45),
    )
    platform = model.part(f"station_{index}_platform")
    platform.visual(
        Cylinder(radius=0.026, length=0.72),
        origin=Origin(rpy=(0.0, math.pi / 2.0, 0.0)),
        material=red,
        name="platform_pivot_bar",
    )
    platform.visual(
        Box((0.70, 0.11, 0.080)),
        origin=Origin(xyz=(0.0, 0.0, -0.035)),
        material=red,
        name="pivot_to_deck_web",
    )
    platform.visual(
        Box((0.82, 0.70, 0.040)),
        origin=Origin(xyz=(0.0, 0.0, -0.08)),
        material=dark,
        name="tread_deck",
    )
    platform.visual(
        Box((0.86, 0.055, 0.070)),
        origin=Origin(xyz=(0.0, -0.36, -0.06)),
        material=red,
        name="side_rail_front",
    )
    platform.visual(
        Box((0.86, 0.055, 0.070)),
        origin=Origin(xyz=(0.0, 0.36, -0.06)),
        material=red,
        name="side_rail_rear",
    )
    _add_tube(platform, "hand_post_front", (0.30, -0.24, -0.06), (0.30, -0.24, 0.26), 0.018, red)
    _add_tube(platform, "hand_post_rear", (0.30, 0.24, -0.06), (0.30, 0.24, 0.26), 0.018, red)
    platform.visual(
        Cylinder(radius=0.020, length=0.54),
        origin=Origin(xyz=(0.30, 0.0, 0.26), rpy=(math.pi / 2.0, 0.0, 0.0)),
        material=red,
        name="hand_bar",
    )
    model.articulation(
        f"station_{index}_links_to_platform",
        ArticulationType.REVOLUTE,
        parent=links,
        child=platform,
        origin=Origin(xyz=(0.0, 0.0, -drop)),
        axis=(1.0, 0.0, 0.0),
        motion_limits=MotionLimits(effort=110.0, velocity=1.2, lower=-0.45, upper=0.45),
        mimic=Mimic(joint=f"station_{index}_frame_to_platform_links", multiplier=-1.0),
    )


def _add_bench_station(
    model: ArticulatedObject,
    r: ResolvedPlaygroundSwingConfig,
    index: int,
    x: float,
    *,
    glider: bool = False,
) -> None:
    steel = _mat(model, f"station_{index}_steel", r.palette["steel"])
    frame_mat = _mat(model, f"station_{index}_bench_frame", r.palette["frame_dark"])
    wood = _mat(model, f"station_{index}_wood", r.palette["wood"])
    dark = _mat(model, f"station_{index}_bench_dark", r.palette["dark"])
    yoke = model.part(f"station_{index}_glider_links" if glider else f"station_{index}_bench_yoke")
    _add_top_hub(yoke, f"station_{index}", steel, length=0.95 if glider else 0.78)
    drop = 1.14
    for sx in (-0.42, 0.42):
        _add_tube(yoke, f"side_arm_{sx:+.1f}", (sx, 0.0, -0.02), (sx, -0.05, -drop), 0.019, steel)
        yoke.visual(
            Cylinder(radius=0.032, length=0.09),
            origin=Origin(xyz=(sx, -0.05, -drop), rpy=(0.0, math.pi / 2.0, 0.0)),
            material=steel,
            name=f"lower_bushing_{sx:+.1f}",
        )
    yoke.visual(
        Cylinder(radius=0.020, length=0.88),
        origin=Origin(xyz=(0.0, -0.05, -drop), rpy=(0.0, math.pi / 2.0, 0.0)),
        material=steel,
        name="lower_pivot_crossbar",
    )
    joint_name = (
        f"station_{index}_frame_to_glider_links"
        if glider
        else f"station_{index}_frame_to_bench_yoke"
    )
    model.articulation(
        joint_name,
        ArticulationType.REVOLUTE,
        parent="frame",
        child=yoke,
        origin=Origin(xyz=(x, 0.0, r.top_z - 0.125)),
        axis=(1.0, 0.0, 0.0),
        motion_limits=MotionLimits(effort=150.0, velocity=1.2, lower=-0.46, upper=0.46),
    )
    bench = model.part(
        f"station_{index}_face_to_face_bench" if glider else f"station_{index}_bench"
    )
    bench.visual(
        Cylinder(radius=0.025, length=0.90),
        origin=Origin(rpy=(0.0, math.pi / 2.0, 0.0)),
        material=frame_mat,
        name="bench_pivot_bar",
    )
    bench.visual(
        Box((0.88, 0.12, 0.140)),
        origin=Origin(xyz=(0.0, 0.0, -0.055)),
        material=frame_mat,
        name="pivot_to_bench_frame_web",
    )
    bench.visual(
        Box((1.06, 0.48, 0.055)),
        origin=Origin(xyz=(0.0, 0.0, -0.12)),
        material=frame_mat,
        name="bench_frame",
    )
    if glider:
        bench.visual(
            Box((1.02, 0.24, 0.050)),
            origin=Origin(xyz=(0.0, -0.23, -0.08)),
            material=wood,
            name="seat_pan_front",
        )
        bench.visual(
            Box((1.02, 0.24, 0.050)),
            origin=Origin(xyz=(0.0, 0.23, -0.08)),
            material=wood,
            name="seat_pan_rear",
        )
        bench.visual(
            Box((1.00, 0.22, 0.140)),
            origin=Origin(xyz=(0.0, -0.34, -0.04)),
            material=frame_mat,
            name="front_seat_to_back_web",
        )
        bench.visual(
            Box((1.00, 0.22, 0.140)),
            origin=Origin(xyz=(0.0, 0.34, -0.04)),
            material=frame_mat,
            name="rear_seat_to_back_web",
        )
        bench.visual(
            Box((1.02, 0.055, 0.30)),
            origin=Origin(xyz=(0.0, -0.43, 0.12)),
            material=wood,
            name="back_panel_front",
        )
        bench.visual(
            Box((1.02, 0.055, 0.30)),
            origin=Origin(xyz=(0.0, 0.43, 0.12)),
            material=wood,
            name="back_panel_rear",
        )
        bench.visual(
            Box((0.86, 0.18, 0.050)),
            origin=Origin(xyz=(0.0, 0.0, -0.16)),
            material=dark,
            name="center_footwell",
        )
    else:
        for j, yy in enumerate((-0.17, -0.06, 0.05, 0.16)):
            bench.visual(
                Box((1.04, 0.080, 0.025)),
                origin=Origin(xyz=(0.0, yy, -0.10)),
                material=wood,
                name=f"seat_slat_{j}",
            )
        for sx in (-0.44, 0.44):
            bench.visual(
                Box((0.060, 0.090, 0.420)),
                origin=Origin(xyz=(sx, -0.25, 0.05)),
                material=frame_mat,
                name=f"back_post_{sx:+.1f}",
            )
        for j, zz in enumerate((0.02, 0.12, 0.22)):
            bench.visual(
                Box((1.04, 0.035, 0.075)),
                origin=Origin(xyz=(0.0, -0.28, zz)),
                material=wood,
                name=f"back_slat_{j}",
            )
    model.articulation(
        f"station_{index}_links_to_bench",
        ArticulationType.REVOLUTE,
        parent=yoke,
        child=bench,
        origin=Origin(xyz=(0.0, -0.05, -drop)),
        axis=(1.0, 0.0, 0.0),
        motion_limits=MotionLimits(effort=80.0, velocity=1.2, lower=-0.30, upper=0.30),
        mimic=Mimic(joint=joint_name, multiplier=-1.0 if glider else 0.35),
    )


def _add_disc_station(
    model: ArticulatedObject, r: ResolvedPlaygroundSwingConfig, index: int, x: float
) -> None:
    steel = _mat(model, f"station_{index}_steel", r.palette["steel"])
    dark = _mat(model, f"station_{index}_dark", r.palette["dark"])
    seat = model.part(f"station_{index}_disc_seat")
    _add_top_hub(seat, f"station_{index}", steel, length=0.24)
    _add_tube(seat, "single_strap", (0.0, 0.0, -0.02), (0.0, 0.0, -0.55), 0.018, dark)
    seat.visual(
        Cylinder(radius=0.20, length=0.040),
        origin=Origin(xyz=(0.0, 0.0, -0.62)),
        material=dark,
        name="seat_disk",
    )
    seat.visual(
        Sphere(radius=0.055), origin=Origin(xyz=(0.0, 0.0, -0.57)), material=steel, name="seat_hub"
    )
    model.articulation(
        f"station_{index}_frame_to_disc",
        ArticulationType.REVOLUTE,
        parent="frame",
        child=seat,
        origin=Origin(xyz=(x, 0.0, r.top_z - 0.125)),
        axis=(1.0, 0.0, 0.0),
        motion_limits=MotionLimits(effort=35.0, velocity=1.7, lower=-0.65, upper=0.65),
    )
    foot = model.part(f"station_{index}_footrest_ring")
    foot.visual(
        mesh_from_geometry(
            TorusGeometry(radius=0.15, tube=0.010, radial_segments=16, tubular_segments=48),
            f"station_{index}_footrest_ring_mesh",
        ),
        origin=Origin(xyz=(-0.11, 0.0, -0.10)),
        material=steel,
        name="footrest_loop",
    )
    foot.visual(Box((0.04, 0.03, 0.035)), origin=Origin(), material=steel, name="footrest_hinge")
    _add_tube(foot, "footrest_hinge_strut", (0.0, 0.0, 0.0), (0.04, 0.0, -0.10), 0.012, steel)
    model.articulation(
        f"station_{index}_disc_to_footrest",
        ArticulationType.REVOLUTE,
        parent=seat,
        child=foot,
        origin=Origin(xyz=(0.09, 0.0, -0.64)),
        axis=(0.0, 1.0, 0.0),
        motion_limits=MotionLimits(effort=4.0, velocity=1.5, lower=0.0, upper=0.60),
    )


def _add_nest_station(
    model: ArticulatedObject, r: ResolvedPlaygroundSwingConfig, index: int, x: float
) -> None:
    steel = _mat(model, f"station_{index}_steel", r.palette["steel"])
    rope = _mat(model, f"station_{index}_rope", r.palette["rope"])
    blue = _mat(model, f"station_{index}_blue", r.palette["blue"])
    hanger = model.part(f"station_{index}_nest_hanger")
    _add_top_hub(hanger, f"station_{index}", steel, length=0.82)
    drop = 1.18
    for sx in (-0.34, 0.34):
        _add_tube(
            hanger,
            f"paired_link_{sx:+.1f}_a",
            (sx, -0.02, -0.02),
            (sx * 0.72, -0.36, -drop),
            0.016,
            steel,
        )
        _add_tube(
            hanger,
            f"paired_link_{sx:+.1f}_b",
            (sx, 0.02, -0.02),
            (sx * 0.72, 0.36, -drop),
            0.016,
            steel,
        )
    hanger.visual(
        Cylinder(radius=0.022, length=0.78),
        origin=Origin(xyz=(0.0, 0.0, -drop), rpy=(0.0, math.pi / 2.0, 0.0)),
        material=steel,
        name="lower_basket_pivot_bar",
    )
    _add_tube(
        hanger, "lower_front_spreader", (-0.25, -0.36, -drop), (0.25, -0.36, -drop), 0.014, steel
    )
    _add_tube(
        hanger, "lower_rear_spreader", (-0.25, 0.36, -drop), (0.25, 0.36, -drop), 0.014, steel
    )
    _add_tube(
        hanger, "lower_center_web_front", (0.0, 0.0, -drop), (0.0, -0.36, -drop), 0.012, steel
    )
    _add_tube(hanger, "lower_center_web_rear", (0.0, 0.0, -drop), (0.0, 0.36, -drop), 0.012, steel)
    model.articulation(
        f"station_{index}_frame_to_nest_hanger",
        ArticulationType.REVOLUTE,
        parent="frame",
        child=hanger,
        origin=Origin(xyz=(x, 0.0, r.top_z - 0.125)),
        axis=(1.0, 0.0, 0.0),
        motion_limits=MotionLimits(effort=100.0, velocity=1.5, lower=-0.55, upper=0.55),
    )
    basket = model.part(f"station_{index}_nest_basket")
    basket.visual(
        Cylinder(radius=0.026, length=0.76),
        origin=Origin(rpy=(0.0, math.pi / 2.0, 0.0)),
        material=blue,
        name="basket_pivot_bar",
    )
    basket.visual(
        mesh_from_geometry(
            TorusGeometry(radius=0.48, tube=0.045, radial_segments=24, tubular_segments=72),
            f"station_{index}_nest_ring_mesh",
        ),
        material=blue,
        name="padded_ring",
    )
    basket.visual(
        mesh_from_geometry(
            TorusGeometry(radius=0.27, tube=0.010, radial_segments=12, tubular_segments=48),
            f"station_{index}_inner_rope_ring_mesh",
        ),
        origin=Origin(xyz=(0.0, 0.0, -0.025)),
        material=rope,
        name="inner_rope_ring",
    )
    for j, yy in enumerate((-0.30, -0.15, 0.0, 0.15, 0.30)):
        half = math.sqrt(max(0.0, 0.45 * 0.45 - yy * yy))
        _add_tube(basket, f"weave_x_{j}", (-half, yy, -0.035), (half, yy, -0.035), 0.006, rope)
    for j, xx in enumerate((-0.30, -0.15, 0.0, 0.15, 0.30)):
        half = math.sqrt(max(0.0, 0.45 * 0.45 - xx * xx))
        _add_tube(basket, f"weave_y_{j}", (xx, -half, -0.043), (xx, half, -0.043), 0.006, rope)
    model.articulation(
        f"station_{index}_hanger_to_nest",
        ArticulationType.REVOLUTE,
        parent=hanger,
        child=basket,
        origin=Origin(xyz=(0.0, 0.0, -drop)),
        axis=(1.0, 0.0, 0.0),
        motion_limits=MotionLimits(effort=22.0, velocity=1.0, lower=-0.18, upper=0.18),
    )


def _build_station(
    model: ArticulatedObject,
    r: ResolvedPlaygroundSwingConfig,
    index: int,
    recipe: StationRecipe,
    x: float,
) -> None:
    if recipe == "simple_belt_station":
        _add_belt_station(model, r, index, x)
    elif recipe == "bucket_station":
        _add_bucket_station(model, r, index, x)
    elif recipe == "tire_station":
        _add_tire_station(model, r, index, x)
    elif recipe == "lap_bar_station":
        _add_lap_bar_station(model, r, index, x)
    elif recipe == "platform_station":
        _add_platform_station(model, r, index, x)
    elif recipe == "bench_station":
        _add_bench_station(model, r, index, x, glider=False)
    elif recipe == "glider_station":
        _add_bench_station(model, r, index, x, glider=True)
    elif recipe == "swivel_disc_station":
        _add_disc_station(model, r, index, x)
    elif recipe == "nest_station":
        _add_nest_station(model, r, index, x)
    else:  # pragma: no cover - resolve_config validates.
        raise ValueError(f"Unhandled station recipe {recipe!r}")


def build_playground_swing(
    config: PlaygroundSwingConfig | None = None,
    *,
    assets: AssetContext | None = None,
) -> ArticulatedObject:
    r = resolve_config(config or PlaygroundSwingConfig())
    model = ArticulatedObject(name=r.name, assets=assets)
    _build_frame(model, r)
    for index, (recipe, x) in enumerate(zip(r.station_recipes, r.station_centers)):
        _build_station(model, r, index, recipe, x)
    model.meta["template_slug"] = "playground_swing"
    model.meta["station_recipes"] = list(r.station_recipes)
    return model


def build_seeded_playground_swing(
    seed: int, *, assets: AssetContext | None = None
) -> ArticulatedObject:
    return build_playground_swing(config_from_seed(seed), assets=assets)


def slot_choices_for_seed(seed: int) -> list[tuple[str, str]]:
    config = resolve_config(config_from_seed(seed))
    choices: list[tuple[str, str]] = [("support_frame", config.support_frame_module)]
    choices.append(("station_count", f"{config.station_count}_stations"))
    for index, recipe in enumerate(config.station_recipes):
        choices.append((f"station_{index}", recipe))
    return choices


def _main_station_part_name(recipe: StationRecipe, index: int) -> str:
    return {
        "simple_belt_station": f"station_{index}_swing",
        "bucket_station": f"station_{index}_bucket",
        "tire_station": f"station_{index}_tire",
        "lap_bar_station": f"station_{index}_slatted_seat",
        "platform_station": f"station_{index}_platform_links",
        "bench_station": f"station_{index}_bench_yoke",
        "glider_station": f"station_{index}_glider_links",
        "swivel_disc_station": f"station_{index}_disc_seat",
        "nest_station": f"station_{index}_nest_hanger",
    }[recipe]


def run_playground_swing_tests(
    object_model: ArticulatedObject,
    config: PlaygroundSwingConfig,
) -> TestReport:
    r = resolve_config(config)
    ctx = TestContext(object_model)
    frame = object_model.get_part("frame")
    part_by_name = {part.name: part for part in object_model.parts}

    for index, recipe in enumerate(r.station_recipes):
        main_name = _main_station_part_name(recipe, index)
        main = part_by_name.get(main_name)
        if main is not None:
            ctx.allow_overlap(
                frame,
                main,
                reason="The station top hub is captured inside the frame clevis/saddle around the shared pivot axis.",
            )
            ctx.allow_overlap(
                frame,
                main,
                elem_a=f"station_{index}_pivot_pin",
                elem_b=f"station_{index}_upper_hub",
                reason="The swing station upper hub is intentionally captured on the frame pivot pin.",
            )
            ctx.allow_overlap(
                frame,
                main,
                elem_a=f"station_{index}_pivot_saddle",
                elem_b=f"station_{index}_upper_hub",
                reason="The saddle visibly supports the captured hub around the same top pivot.",
            )
        for child_name in (
            f"station_{index}_lap_bar",
            f"station_{index}_platform",
            f"station_{index}_bench",
            f"station_{index}_face_to_face_bench",
            f"station_{index}_footrest_ring",
            f"station_{index}_nest_basket",
        ):
            child = part_by_name.get(child_name)
            if child is not None and main is not None:
                ctx.allow_overlap(
                    main,
                    child,
                    reason="Station-local hinge hardware intentionally captures the child part at its pivot.",
                )

    ctx.check_model_valid()
    parts = {part.name for part in object_model.parts}
    joints = {joint.name: joint for joint in object_model.articulations}
    ctx.check("frame_present", "frame" in parts)
    ctx.check("station_count_matches_config", len(r.station_recipes) == r.station_count)
    for index, recipe in enumerate(r.station_recipes):
        main_name = _main_station_part_name(recipe, index)
        ctx.check(f"station_{index}_main_part_present", main_name in parts, details=recipe)
        station_joints = [name for name in joints if name.startswith(f"station_{index}_")]
        ctx.check(
            f"station_{index}_has_articulation", bool(station_joints), details=str(station_joints)
        )
    return ctx.report()


__all__ = [
    "PlaygroundSwingConfig",
    "ResolvedPlaygroundSwingConfig",
    "build_playground_swing",
    "build_seeded_playground_swing",
    "config_from_seed",
    "resolve_config",
    "run_playground_swing_tests",
    "slot_choices_for_seed",
    "__modular__",
]
