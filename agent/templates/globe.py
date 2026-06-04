"""Globe procedural template.

Implements ``articraft_template_authoring/specs/globe.md``.

The template is organized around the reviewed mixed slot graph:

* Slot A ``support_base``: desktop base, cradle stand, pedestal, or wall arm.
* Slot B ``meridian_or_cradle``: tilting/fixed/nested/partial meridian carrier,
  or a no-ring support pedestal.
* Slot C ``globe_surface``: ocean sphere with visible continents, graticule
  bands, polar caps, and equator/latitude/longitude identity marks.
* Slot D ``auxiliary_rotary``: optional date ring or base support yaw.

Identity invariant: every seed has a supported globe sphere and a
``globe_spin`` CONTINUOUS joint whose origin is at the sphere center.

Geometry policy: parent supports include explicit pivot sockets or saddles.
The meridian and globe carry matching caps on the same axis so the articulated
chain reads as physically connected in both static and moving poses.

Adopted source mapping:
S1 rec_globe_0002:
   classic desktop base, yoke arms, tilting meridian ring, continent patches.
S2 rec_globe_0fc4e0cefb164176b77a767cd54d8816:
   outer cradle stand, nested inner ring, graticule helpers.
S3 rec_globe_1c4dea866a4340d792eedfb836a2c683:
   partial support ring and auxiliary date ring.
S4 rec_globe_35a4dc2d75144987ae667216dff6d05d:
   fixed meridian ring with denser map patching.
S5 rec_globe_bb728b5bb5b64df798b3ef95f629fb38:
   rotating support pedestal stage.
S6 rec_globe_dd09f51da481436e8a10f6b573d84744:
   wall bracket and partial meridian frame.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
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
    Part,
    Sphere,
    TestContext,
    TestReport,
    TorusGeometry,
    mesh_from_geometry,
)

__modular__ = True


SupportStyle = Literal[
    "classic_desktop",
    "outer_cradle",
    "partial_ring",
    "rotating_pedestal",
    "wall_arm",
]
MeridianStyle = Literal[
    "full_tilting",
    "nested_inner",
    "fixed_full",
    "none_pedestal",
    "partial_wall",
]
SurfaceStyle = Literal[
    "continent_patch",
    "graticule_patch",
    "dense_map",
    "minimal_ocean",
]
AuxiliaryRotary = Literal[
    "none",
    "date_ring",
    "support_yaw",
]
GraticuleDensity = Literal[
    "none",
    "low",
    "medium",
    "high",
]
LandPatchStyle = Literal[
    "simple_continents",
    "abstract_patches",
    "dense_patches",
]
PaletteTheme = Literal[
    "schoolhouse_blue",
    "antique_brass",
    "museum_dark",
    "wall_mount_slate",
    "modern_white",
]


SUPPORT_STYLES: tuple[SupportStyle, ...] = (
    "classic_desktop",
    "outer_cradle",
    "partial_ring",
    "rotating_pedestal",
    "wall_arm",
)
MERIDIAN_STYLES: tuple[MeridianStyle, ...] = (
    "full_tilting",
    "nested_inner",
    "fixed_full",
    "none_pedestal",
    "partial_wall",
)
SURFACE_STYLES: tuple[SurfaceStyle, ...] = (
    "continent_patch",
    "graticule_patch",
    "dense_map",
    "minimal_ocean",
)
AUXILIARY_ROTARY_STYLES: tuple[AuxiliaryRotary, ...] = (
    "none",
    "date_ring",
    "support_yaw",
)
GRATICULE_DENSITIES: tuple[GraticuleDensity, ...] = (
    "none",
    "low",
    "medium",
    "high",
)
LAND_PATCH_STYLES: tuple[LandPatchStyle, ...] = (
    "simple_continents",
    "abstract_patches",
    "dense_patches",
)
PALETTE_THEMES: tuple[PaletteTheme, ...] = (
    "schoolhouse_blue",
    "antique_brass",
    "museum_dark",
    "wall_mount_slate",
    "modern_white",
)


SOURCE_INDEX = {
    "S1": ("data/records/rec_globe_0002/revisions/rev_000001/model.py:L62-L94,L187-L393"),
    "S2": (
        "data/records/rec_globe_0fc4e0cefb164176b77a767cd54d8816/"
        "revisions/rev_000001/model.py:L27-L126,L152-L296"
    ),
    "S3": (
        "data/records/rec_globe_1c4dea866a4340d792eedfb836a2c683/"
        "revisions/rev_000001/model.py:L21-L178,L241-L421"
    ),
    "S4": (
        "data/records/rec_globe_35a4dc2d75144987ae667216dff6d05d/"
        "revisions/rev_000001/model.py:L36-L178,L191-L392"
    ),
    "S5": (
        "data/records/rec_globe_bb728b5bb5b64df798b3ef95f629fb38/"
        "revisions/rev_000001/model.py:L36-L88,L106-L242"
    ),
    "S6": (
        "data/records/rec_globe_dd09f51da481436e8a10f6b573d84744/"
        "revisions/rev_000001/model.py:L27-L103,L113-L324"
    ),
}


PALETTES: dict[PaletteTheme, dict[str, tuple[float, float, float, float]]] = {
    "schoolhouse_blue": {
        "ocean": (0.08, 0.38, 0.68, 1.0),
        "ocean_dark": (0.03, 0.16, 0.30, 1.0),
        "land": (0.30, 0.58, 0.27, 1.0),
        "land_light": (0.58, 0.72, 0.34, 1.0),
        "land_dark": (0.18, 0.42, 0.20, 1.0),
        "graticule": (0.88, 0.86, 0.70, 1.0),
        "metal": (0.78, 0.64, 0.30, 1.0),
        "metal_dark": (0.34, 0.24, 0.11, 1.0),
        "wood": (0.40, 0.22, 0.12, 1.0),
        "wood_dark": (0.20, 0.10, 0.055, 1.0),
        "wall": (0.52, 0.54, 0.56, 1.0),
    },
    "antique_brass": {
        "ocean": (0.12, 0.26, 0.38, 1.0),
        "ocean_dark": (0.04, 0.09, 0.13, 1.0),
        "land": (0.62, 0.45, 0.22, 1.0),
        "land_light": (0.78, 0.62, 0.34, 1.0),
        "land_dark": (0.42, 0.30, 0.16, 1.0),
        "graticule": (0.96, 0.82, 0.44, 1.0),
        "metal": (0.82, 0.62, 0.24, 1.0),
        "metal_dark": (0.34, 0.23, 0.09, 1.0),
        "wood": (0.34, 0.18, 0.08, 1.0),
        "wood_dark": (0.16, 0.08, 0.035, 1.0),
        "wall": (0.62, 0.58, 0.50, 1.0),
    },
    "museum_dark": {
        "ocean": (0.02, 0.08, 0.13, 1.0),
        "ocean_dark": (0.01, 0.03, 0.055, 1.0),
        "land": (0.34, 0.52, 0.36, 1.0),
        "land_light": (0.58, 0.66, 0.42, 1.0),
        "land_dark": (0.16, 0.30, 0.18, 1.0),
        "graticule": (0.78, 0.78, 0.72, 1.0),
        "metal": (0.62, 0.64, 0.66, 1.0),
        "metal_dark": (0.16, 0.17, 0.18, 1.0),
        "wood": (0.08, 0.075, 0.07, 1.0),
        "wood_dark": (0.025, 0.025, 0.025, 1.0),
        "wall": (0.28, 0.30, 0.32, 1.0),
    },
    "wall_mount_slate": {
        "ocean": (0.06, 0.22, 0.36, 1.0),
        "ocean_dark": (0.02, 0.08, 0.14, 1.0),
        "land": (0.44, 0.58, 0.34, 1.0),
        "land_light": (0.72, 0.75, 0.48, 1.0),
        "land_dark": (0.24, 0.38, 0.22, 1.0),
        "graticule": (0.84, 0.86, 0.82, 1.0),
        "metal": (0.54, 0.58, 0.60, 1.0),
        "metal_dark": (0.18, 0.20, 0.22, 1.0),
        "wood": (0.22, 0.24, 0.26, 1.0),
        "wood_dark": (0.08, 0.09, 0.10, 1.0),
        "wall": (0.42, 0.44, 0.46, 1.0),
    },
    "modern_white": {
        "ocean": (0.20, 0.50, 0.72, 1.0),
        "ocean_dark": (0.06, 0.22, 0.38, 1.0),
        "land": (0.46, 0.62, 0.40, 1.0),
        "land_light": (0.76, 0.82, 0.52, 1.0),
        "land_dark": (0.28, 0.44, 0.26, 1.0),
        "graticule": (0.96, 0.96, 0.90, 1.0),
        "metal": (0.82, 0.84, 0.84, 1.0),
        "metal_dark": (0.36, 0.38, 0.40, 1.0),
        "wood": (0.88, 0.86, 0.78, 1.0),
        "wood_dark": (0.54, 0.52, 0.48, 1.0),
        "wall": (0.78, 0.80, 0.82, 1.0),
    },
}


@dataclass(frozen=True)
class GlobeConfig:
    support_style: SupportStyle = "classic_desktop"
    meridian_style: MeridianStyle = "full_tilting"
    surface_style: SurfaceStyle = "continent_patch"
    auxiliary_rotary: AuxiliaryRotary = "none"
    palette_theme: PaletteTheme = "schoolhouse_blue"
    globe_radius: float = 0.50
    axial_tilt_degrees: float = 23.5
    ring_clearance: float = 0.045
    base_height: float = 0.28
    graticule_density: GraticuleDensity = "medium"
    land_patch_style: LandPatchStyle = "simple_continents"
    tilt_range: float = 0.55
    name: str = "reference_globe"
    palette: dict[str, tuple[float, float, float, float]] | None = None


@dataclass(frozen=True)
class ResolvedGlobeConfig:
    support_style: SupportStyle
    meridian_style: MeridianStyle
    surface_style: SurfaceStyle
    auxiliary_rotary: AuxiliaryRotary
    palette_theme: PaletteTheme
    globe_radius: float
    axial_tilt_degrees: float
    ring_clearance: float
    base_height: float
    graticule_density: GraticuleDensity
    land_patch_style: LandPatchStyle
    tilt_range: float
    ring_radius: float
    ring_tube: float
    globe_center_z: float
    pedestal_radius: float
    base_radius: float
    base_depth: float
    yoke_width: float
    yoke_post_height: float
    spin_axis: tuple[float, float, float]
    name: str
    palette: dict[str, tuple[float, float, float, float]]


@dataclass(frozen=True)
class SupportAnchors:
    root: Part
    carrier: Part
    globe_parent: Part
    globe_center_z: float
    ring_radius: float
    ring_tube: float
    pivot_x: float
    support_kind: str


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(value)))


def _require(value: str, allowed: tuple[str, ...], *, field_name: str) -> str:
    if value not in allowed:
        raise ValueError(f"{field_name} must be one of {allowed}, got {value!r}")
    return value


def _cyl_x() -> tuple[float, float, float]:
    return (0.0, math.pi / 2.0, 0.0)


def _cyl_y() -> tuple[float, float, float]:
    return (math.pi / 2.0, 0.0, 0.0)


def _cyl_z() -> tuple[float, float, float]:
    return (0.0, 0.0, 0.0)


def _torus_vertical() -> tuple[float, float, float]:
    return (math.pi / 2.0, 0.0, 0.0)


def _register_materials(
    model: ArticulatedObject, palette: dict[str, tuple[float, float, float, float]]
):
    return {name: model.material(f"globe_{name}", rgba=rgba) for name, rgba in palette.items()}


def _mesh_for_model(model: ArticulatedObject, geometry: object, name: str):
    if model.assets is not None:
        return mesh_from_geometry(geometry, model.assets.mesh_path(f"{name}.obj"))
    return mesh_from_geometry(geometry, name)


def _add_torus(
    model: ArticulatedObject,
    part: Part,
    *,
    name: str,
    radius: float,
    tube: float,
    material: object,
    origin: Origin | None = None,
    radial_segments: int = 18,
    tubular_segments: int = 72,
) -> None:
    part.visual(
        _mesh_for_model(
            model,
            TorusGeometry(
                radius=radius,
                tube=tube,
                radial_segments=radial_segments,
                tubular_segments=tubular_segments,
            ),
            name,
        ),
        origin=origin or Origin(),
        material=material,
        name=name,
    )


def _unit_from_lat_lon(lat_deg: float, lon_deg: float) -> tuple[float, float, float]:
    lat = math.radians(lat_deg)
    lon = math.radians(lon_deg)
    return (
        math.cos(lat) * math.cos(lon),
        math.cos(lat) * math.sin(lon),
        math.sin(lat),
    )


def _patch_origin(radius: float, lat_deg: float, lon_deg: float) -> Origin:
    x, y, z = _unit_from_lat_lon(lat_deg, lon_deg)
    yaw = math.atan2(y, x)
    pitch = -math.asin(z)
    return Origin(
        xyz=(x * radius, y * radius, z * radius),
        rpy=(0.0, pitch, yaw),
    )


def _patch_visual(
    globe: Part,
    *,
    radius: float,
    lat: float,
    lon: float,
    width: float,
    height: float,
    material: object,
    name: str,
) -> None:
    globe.visual(
        Box((width, radius * 0.018, height)),
        origin=_patch_origin(radius * 1.006, lat, lon),
        material=material,
        name=name,
    )


def _band_visual(
    globe: Part,
    *,
    radius: float,
    name: str,
    material: object,
    axis: str,
    scale: float = 1.0,
    tube_scale: float = 1.0,
    model: ArticulatedObject,
) -> None:
    tube = max(radius * 0.006 * tube_scale, 0.0025)
    band_radius = radius * scale
    if axis == "xy":
        rpy = (0.0, 0.0, 0.0)
    elif axis == "xz":
        rpy = _torus_vertical()
    elif axis == "yz":
        rpy = (0.0, math.pi / 2.0, 0.0)
    else:
        raise ValueError(f"unknown graticule axis {axis!r}")
    _add_torus(
        model,
        globe,
        name=name,
        radius=band_radius,
        tube=tube,
        material=material,
        origin=Origin(rpy=rpy),
        radial_segments=10,
        tubular_segments=64,
    )


def config_from_seed(seed: int) -> GlobeConfig:
    curated: dict[int, GlobeConfig] = {
        0: GlobeConfig(
            support_style="classic_desktop",
            meridian_style="full_tilting",
            surface_style="continent_patch",
            auxiliary_rotary="none",
            globe_radius=0.50,
            axial_tilt_degrees=23.5,
            ring_clearance=0.045,
            base_height=0.28,
            graticule_density="medium",
            land_patch_style="simple_continents",
            palette_theme="schoolhouse_blue",
            name="seeded_globe_0",
        ),
        1: GlobeConfig(
            support_style="classic_desktop",
            meridian_style="full_tilting",
            surface_style="graticule_patch",
            auxiliary_rotary="none",
            globe_radius=0.42,
            axial_tilt_degrees=21.0,
            ring_clearance=0.055,
            base_height=0.26,
            graticule_density="high",
            land_patch_style="abstract_patches",
            palette_theme="antique_brass",
            name="seeded_globe_1",
        ),
        2: GlobeConfig(
            support_style="classic_desktop",
            meridian_style="full_tilting",
            surface_style="minimal_ocean",
            auxiliary_rotary="none",
            globe_radius=0.46,
            axial_tilt_degrees=18.0,
            ring_clearance=0.04,
            base_height=0.30,
            graticule_density="low",
            land_patch_style="abstract_patches",
            palette_theme="modern_white",
            name="seeded_globe_2",
        ),
        3: GlobeConfig(
            support_style="classic_desktop",
            meridian_style="full_tilting",
            surface_style="dense_map",
            auxiliary_rotary="none",
            globe_radius=0.52,
            axial_tilt_degrees=27.0,
            ring_clearance=0.05,
            base_height=0.32,
            graticule_density="high",
            land_patch_style="dense_patches",
            palette_theme="museum_dark",
            name="seeded_globe_3",
        ),
        4: GlobeConfig(
            support_style="classic_desktop",
            meridian_style="full_tilting",
            surface_style="graticule_patch",
            auxiliary_rotary="none",
            globe_radius=0.44,
            axial_tilt_degrees=25.0,
            ring_clearance=0.06,
            base_height=0.30,
            graticule_density="medium",
            land_patch_style="abstract_patches",
            palette_theme="wall_mount_slate",
            name="seeded_globe_4",
        ),
        5: GlobeConfig(
            support_style="classic_desktop",
            meridian_style="full_tilting",
            surface_style="dense_map",
            auxiliary_rotary="none",
            globe_radius=0.58,
            axial_tilt_degrees=32.0,
            ring_clearance=0.065,
            base_height=0.38,
            graticule_density="medium",
            land_patch_style="dense_patches",
            palette_theme="museum_dark",
            name="seeded_globe_5",
        ),
        6: GlobeConfig(
            support_style="classic_desktop",
            meridian_style="full_tilting",
            surface_style="continent_patch",
            auxiliary_rotary="none",
            globe_radius=0.56,
            axial_tilt_degrees=17.0,
            ring_clearance=0.045,
            base_height=0.34,
            graticule_density="medium",
            land_patch_style="abstract_patches",
            palette_theme="wall_mount_slate",
            name="seeded_globe_6",
        ),
        7: GlobeConfig(
            support_style="classic_desktop",
            meridian_style="full_tilting",
            surface_style="continent_patch",
            auxiliary_rotary="none",
            globe_radius=0.60,
            axial_tilt_degrees=19.0,
            ring_clearance=0.06,
            base_height=0.42,
            graticule_density="low",
            land_patch_style="simple_continents",
            palette_theme="schoolhouse_blue",
            name="seeded_globe_7",
        ),
        8: GlobeConfig(
            support_style="classic_desktop",
            meridian_style="full_tilting",
            surface_style="minimal_ocean",
            auxiliary_rotary="none",
            globe_radius=0.40,
            axial_tilt_degrees=16.8,
            ring_clearance=0.04,
            base_height=0.24,
            graticule_density="low",
            land_patch_style="abstract_patches",
            palette_theme="antique_brass",
            name="seeded_globe_8",
        ),
        9: GlobeConfig(
            support_style="classic_desktop",
            meridian_style="full_tilting",
            surface_style="dense_map",
            auxiliary_rotary="none",
            globe_radius=0.38,
            axial_tilt_degrees=31.6,
            ring_clearance=0.035,
            base_height=0.25,
            graticule_density="none",
            land_patch_style="abstract_patches",
            palette_theme="modern_white",
            name="seeded_globe_9",
        ),
    }
    if seed in curated:
        return curated[seed]

    rng = random.Random(seed)
    support = rng.choice(SUPPORT_STYLES)
    if support == "rotating_pedestal":
        meridian: MeridianStyle = "none_pedestal"
        auxiliary: AuxiliaryRotary = "support_yaw"
    elif support == "wall_arm":
        meridian = "partial_wall"
        auxiliary = "none"
    elif support == "outer_cradle":
        meridian = "nested_inner"
        auxiliary = rng.choice(("none", "date_ring"))
    else:
        meridian = rng.choice(("full_tilting", "fixed_full"))
        auxiliary = rng.choice(AUXILIARY_ROTARY_STYLES)
        if auxiliary == "support_yaw":
            auxiliary = "none"

    return GlobeConfig(
        support_style=support,
        meridian_style=meridian,
        surface_style=rng.choice(SURFACE_STYLES),
        auxiliary_rotary=auxiliary,
        palette_theme=rng.choice(PALETTE_THEMES),
        globe_radius=round(rng.uniform(0.34, 0.64), 3),
        axial_tilt_degrees=round(rng.uniform(16.0, 34.0), 2),
        ring_clearance=round(rng.uniform(0.035, 0.075), 3),
        base_height=round(rng.uniform(0.18, 0.46), 3),
        graticule_density=rng.choice(GRATICULE_DENSITIES),
        land_patch_style=rng.choice(LAND_PATCH_STYLES),
        tilt_range=round(rng.uniform(0.38, 0.62), 3),
        name=f"seeded_globe_{seed}",
    )


def resolve_config(config: GlobeConfig) -> ResolvedGlobeConfig:
    support = _require(
        config.support_style,
        SUPPORT_STYLES,
        field_name="support_style",
    )
    meridian = _require(
        config.meridian_style,
        MERIDIAN_STYLES,
        field_name="meridian_style",
    )
    surface = _require(
        config.surface_style,
        SURFACE_STYLES,
        field_name="surface_style",
    )
    auxiliary = _require(
        config.auxiliary_rotary,
        AUXILIARY_ROTARY_STYLES,
        field_name="auxiliary_rotary",
    )
    density = _require(
        config.graticule_density,
        GRATICULE_DENSITIES,
        field_name="graticule_density",
    )
    patch_style = _require(
        config.land_patch_style,
        LAND_PATCH_STYLES,
        field_name="land_patch_style",
    )
    palette_theme = _require(
        config.palette_theme,
        PALETTE_THEMES,
        field_name="palette_theme",
    )

    if support == "rotating_pedestal":
        meridian = "none_pedestal"
        auxiliary = "support_yaw"
    elif support == "wall_arm":
        meridian = "partial_wall"
        auxiliary = "none"
    elif support == "outer_cradle":
        meridian = "nested_inner"
        if auxiliary == "support_yaw":
            auxiliary = "date_ring"
    elif meridian == "none_pedestal":
        support = "rotating_pedestal"
        auxiliary = "support_yaw"

    radius = _clamp(config.globe_radius, 0.32, 0.72)
    clearance = _clamp(config.ring_clearance, 0.025, 0.09)
    if meridian == "none_pedestal":
        clearance = max(clearance, 0.035)
    ring_radius = radius + clearance
    ring_tube = max(0.010, min(0.026, radius * 0.035))

    if support == "wall_arm":
        base_height = _clamp(config.base_height, 0.20, 0.48)
    elif support == "rotating_pedestal":
        base_height = _clamp(config.base_height, 0.26, 0.56)
    elif support == "outer_cradle":
        base_height = _clamp(config.base_height, 0.18, 0.34)
    else:
        base_height = _clamp(config.base_height, 0.20, 0.48)

    globe_center_z = base_height + ring_radius
    if support == "wall_arm":
        globe_center_z = max(globe_center_z, radius * 1.35)
    pedestal_radius = max(radius * 0.16, 0.075)
    base_radius = max(radius * 0.42, 0.20)
    base_depth = max(radius * 0.32, 0.16)
    yoke_width = ring_radius * 2.0
    yoke_post_height = globe_center_z

    palette = dict(PALETTES[palette_theme])  # type: ignore[index]
    if config.palette:
        palette.update(config.palette)

    return ResolvedGlobeConfig(
        support_style=support,  # type: ignore[arg-type]
        meridian_style=meridian,  # type: ignore[arg-type]
        surface_style=surface,  # type: ignore[arg-type]
        auxiliary_rotary=auxiliary,  # type: ignore[arg-type]
        palette_theme=palette_theme,  # type: ignore[arg-type]
        globe_radius=radius,
        axial_tilt_degrees=_clamp(config.axial_tilt_degrees, 15.0, 35.0),
        ring_clearance=clearance,
        base_height=base_height,
        graticule_density=density,  # type: ignore[arg-type]
        land_patch_style=patch_style,  # type: ignore[arg-type]
        tilt_range=_clamp(config.tilt_range, 0.25, 0.72),
        ring_radius=ring_radius,
        ring_tube=ring_tube,
        globe_center_z=globe_center_z,
        pedestal_radius=pedestal_radius,
        base_radius=base_radius,
        base_depth=base_depth,
        yoke_width=yoke_width,
        yoke_post_height=yoke_post_height,
        spin_axis=(0.0, 0.0, 1.0),
        name=config.name,
        palette=palette,
    )


def _build_classic_desktop_base(
    model: ArticulatedObject,
    r: ResolvedGlobeConfig,
    materials: dict[str, object],
) -> SupportAnchors:
    base = model.part("base")
    R = r.globe_radius
    base.visual(
        Cylinder(radius=r.base_radius * 1.06, length=R * 0.075),
        origin=Origin(xyz=(0.0, 0.0, R * 0.0375), rpy=_cyl_z()),
        material=materials["wood_dark"],
        name="round_stepped_foot",
    )
    base.visual(
        Cylinder(radius=r.base_radius * 0.82, length=R * 0.10),
        origin=Origin(xyz=(0.0, 0.0, R * 0.11), rpy=_cyl_z()),
        material=materials["wood"],
        name="polished_base_disk",
    )
    base.visual(
        Cylinder(radius=r.base_radius * 0.50, length=R * 0.075),
        origin=Origin(xyz=(0.0, 0.0, R * 0.19), rpy=_cyl_z()),
        material=materials["metal"],
        name="brass_base_collar",
    )
    pedestal_len = max(R * 0.12, r.base_height - R * 0.13)
    pedestal_z = R * 0.09 + pedestal_len * 0.5
    lower_socket_z = r.base_height - R * 0.050
    base.visual(
        Cylinder(radius=r.pedestal_radius, length=pedestal_len),
        origin=Origin(xyz=(0.0, 0.0, pedestal_z), rpy=_cyl_z()),
        material=materials["wood"],
        name="central_turned_pedestal",
    )
    base.visual(
        Cylinder(radius=r.pedestal_radius * 1.35, length=R * 0.050),
        origin=Origin(xyz=(0.0, 0.0, lower_socket_z), rpy=_cyl_z()),
        material=materials["metal"],
        name="yoke_lower_socket",
    )
    base.visual(
        Sphere(radius=r.ring_tube * 0.85),
        origin=Origin(xyz=(0.0, 0.0, r.globe_center_z)),
        material=materials["metal_dark"],
        name="central_tilt_axis_datum",
    )
    base.visual(
        Cylinder(radius=r.ring_tube * 0.42, length=r.ring_radius * 2.06),
        origin=Origin(xyz=(0.0, 0.0, r.globe_center_z), rpy=_cyl_x()),
        material=materials["metal_dark"],
        name="central_tilt_axis_rod",
    )

    post_r = max(R * 0.032, 0.012)
    post_y = -post_r * 4.0
    for side_name, x in (("left", -r.ring_radius), ("right", r.ring_radius)):
        base.visual(
            Cylinder(radius=post_r, length=r.yoke_post_height - r.base_height),
            origin=Origin(
                xyz=(x, post_y, (r.yoke_post_height + r.base_height) * 0.5),
                rpy=_cyl_z(),
            ),
            material=materials["metal"],
            name=f"{side_name}_yoke_upright",
        )
        base.visual(
            Cylinder(radius=post_r * 0.72, length=abs(post_y)),
            origin=Origin(
                xyz=(x, post_y * 0.5, r.globe_center_z),
                rpy=_cyl_y(),
            ),
            material=materials["metal"],
            name=f"{side_name}_yoke_top_bridge",
        )
        base.visual(
            Sphere(radius=post_r * 1.55),
            origin=Origin(xyz=(x, 0.0, r.globe_center_z)),
            material=materials["metal_dark"],
            name=f"{side_name}_yoke_pivot_socket",
        )
        base.visual(
            Box((post_r * 3.1, post_r * 1.8, post_r * 0.9)),
            origin=Origin(xyz=(x, post_y, r.base_height + R * 0.04)),
            material=materials["metal_dark"],
            name=f"{side_name}_yoke_foot_clamp",
        )
        base.visual(
            Cylinder(radius=post_r * 0.80, length=r.base_height - R * 0.18),
            origin=Origin(xyz=(x, post_y, (r.base_height + R * 0.18) * 0.5), rpy=_cyl_z()),
            material=materials["metal"],
            name=f"{side_name}_yoke_lower_extension",
        )
    base.visual(
        Box((r.ring_radius * 2.16, abs(post_y) + post_r * 2.6, post_r * 1.1)),
        origin=Origin(xyz=(0.0, post_y * 0.5, R * 0.18)),
        material=materials["metal_dark"],
        name="rear_yoke_floor_crossbrace",
    )

    meridian = _build_meridian_carrier(model, r, base, materials, parent_kind="desktop")
    return SupportAnchors(
        root=base,
        carrier=meridian,
        globe_parent=meridian,
        globe_center_z=r.globe_center_z,
        ring_radius=r.ring_radius,
        ring_tube=r.ring_tube,
        pivot_x=r.ring_radius,
        support_kind="classic_desktop",
    )


def _build_outer_cradle_base(
    model: ArticulatedObject,
    r: ResolvedGlobeConfig,
    materials: dict[str, object],
) -> SupportAnchors:
    cradle = model.part("outer_cradle")
    R = r.globe_radius
    cradle.visual(
        Box((r.ring_radius * 1.55, r.base_depth * 1.65, R * 0.090)),
        origin=Origin(xyz=(0.0, 0.0, R * 0.045)),
        material=materials["wood_dark"],
        name="rectangular_cradle_foot",
    )
    cradle.visual(
        Cylinder(radius=r.pedestal_radius * 1.15, length=r.base_height * 0.82),
        origin=Origin(xyz=(0.0, 0.0, r.base_height * 0.45), rpy=_cyl_z()),
        material=materials["wood"],
        name="center_cradle_column",
    )
    cradle.visual(
        Box((r.ring_radius * 1.30, r.base_depth * 0.24, R * 0.055)),
        origin=Origin(xyz=(0.0, -r.base_depth * 0.32, r.base_height)),
        material=materials["metal_dark"],
        name="front_cross_saddle",
    )
    cradle.visual(
        Box((r.ring_radius * 1.30, r.base_depth * 0.24, R * 0.055)),
        origin=Origin(xyz=(0.0, r.base_depth * 0.32, r.base_height)),
        material=materials["metal_dark"],
        name="rear_cross_saddle",
    )
    outer_radius = r.ring_radius + R * 0.085
    _add_torus(
        model,
        cradle,
        name="outer_cradle_ring",
        radius=outer_radius,
        tube=r.ring_tube * 0.92,
        material=materials["metal"],
        origin=Origin(xyz=(0.0, 0.0, r.globe_center_z), rpy=_torus_vertical()),
    )
    for x in (-r.ring_radius, r.ring_radius):
        cradle.visual(
            Sphere(radius=r.ring_tube * 1.75),
            origin=Origin(xyz=(x, 0.0, r.globe_center_z)),
            material=materials["metal_dark"],
            name=f"outer_cradle_pivot_socket_{'left' if x < 0 else 'right'}",
        )

    meridian = _build_meridian_carrier(model, r, cradle, materials, parent_kind="cradle")
    return SupportAnchors(
        root=cradle,
        carrier=meridian,
        globe_parent=meridian,
        globe_center_z=r.globe_center_z,
        ring_radius=r.ring_radius,
        ring_tube=r.ring_tube,
        pivot_x=r.ring_radius,
        support_kind="outer_cradle",
    )


def _build_partial_ring_base(
    model: ArticulatedObject,
    r: ResolvedGlobeConfig,
    materials: dict[str, object],
) -> SupportAnchors:
    stand = model.part("stand")
    R = r.globe_radius
    stand.visual(
        Cylinder(radius=r.base_radius, length=R * 0.085),
        origin=Origin(xyz=(0.0, 0.0, R * 0.0425), rpy=_cyl_z()),
        material=materials["wood_dark"],
        name="partial_ring_base_disk",
    )
    stand.visual(
        Cylinder(radius=r.pedestal_radius * 1.10, length=r.base_height),
        origin=Origin(xyz=(0.0, 0.0, r.base_height * 0.5), rpy=_cyl_z()),
        material=materials["metal"],
        name="partial_ring_center_post",
    )
    stand.visual(
        Box((r.ring_radius * 1.52, r.base_depth * 0.22, R * 0.060)),
        origin=Origin(xyz=(0.0, 0.0, r.base_height)),
        material=materials["metal_dark"],
        name="partial_ring_crosshead",
    )
    for x in (-r.ring_radius, r.ring_radius):
        stand.visual(
            Cylinder(radius=r.ring_tube * 0.90, length=r.globe_center_z - r.base_height),
            origin=Origin(xyz=(x, 0.0, (r.globe_center_z + r.base_height) * 0.5), rpy=_cyl_z()),
            material=materials["metal"],
            name=f"partial_ring_side_post_{'left' if x < 0 else 'right'}",
        )

    meridian = _build_meridian_carrier(model, r, stand, materials, parent_kind="partial")
    return SupportAnchors(
        root=stand,
        carrier=meridian,
        globe_parent=meridian,
        globe_center_z=r.globe_center_z,
        ring_radius=r.ring_radius,
        ring_tube=r.ring_tube,
        pivot_x=r.ring_radius,
        support_kind="partial_ring",
    )


def _build_rotating_pedestal_base(
    model: ArticulatedObject,
    r: ResolvedGlobeConfig,
    materials: dict[str, object],
) -> SupportAnchors:
    base = model.part("base_ring")
    support = model.part("support_pedestal")
    R = r.globe_radius
    base.visual(
        Cylinder(radius=r.base_radius * 1.08, length=R * 0.090),
        origin=Origin(xyz=(0.0, 0.0, R * 0.045), rpy=_cyl_z()),
        material=materials["wood_dark"],
        name="turning_base_outer_disk",
    )
    base.visual(
        Cylinder(radius=r.base_radius * 0.74, length=R * 0.070),
        origin=Origin(xyz=(0.0, 0.0, R * 0.125), rpy=_cyl_z()),
        material=materials["metal_dark"],
        name="turning_base_bearing_race",
    )
    support.visual(
        Cylinder(radius=r.pedestal_radius * 1.40, length=r.base_height * 0.42),
        origin=Origin(xyz=(0.0, 0.0, r.base_height * 0.21), rpy=_cyl_z()),
        material=materials["metal"],
        name="rotating_lower_pedestal",
    )
    support.visual(
        Cylinder(radius=r.pedestal_radius * 0.86, length=r.globe_center_z - R * 0.18),
        origin=Origin(xyz=(0.0, 0.0, (r.globe_center_z - R * 0.18) * 0.5), rpy=_cyl_z()),
        material=materials["wood"],
        name="rotating_tall_support",
    )
    support.visual(
        Cylinder(radius=r.pedestal_radius * 1.75, length=R * 0.070),
        origin=Origin(xyz=(0.0, 0.0, r.globe_center_z - R * 0.78), rpy=_cyl_z()),
        material=materials["metal"],
        name="globe_bottom_saddle",
    )
    support.visual(
        Sphere(radius=r.ring_tube * 2.2),
        origin=Origin(xyz=(0.0, 0.0, r.globe_center_z - R * 0.98)),
        material=materials["metal_dark"],
        name="lower_spin_saddle_ball",
    )
    model.articulation(
        "support_yaw",
        ArticulationType.CONTINUOUS,
        parent=base,
        child=support,
        origin=Origin(xyz=(0.0, 0.0, R * 0.14)),
        axis=(0.0, 0.0, 1.0),
        motion_limits=MotionLimits(effort=25.0, velocity=1.5),
    )
    return SupportAnchors(
        root=base,
        carrier=support,
        globe_parent=support,
        globe_center_z=r.globe_center_z,
        ring_radius=r.ring_radius,
        ring_tube=r.ring_tube,
        pivot_x=0.0,
        support_kind="rotating_pedestal",
    )


def _build_wall_arm_base(
    model: ArticulatedObject,
    r: ResolvedGlobeConfig,
    materials: dict[str, object],
) -> SupportAnchors:
    wall = model.part("wall_arm")
    R = r.globe_radius
    wall.visual(
        Box((R * 0.34, R * 0.070, R * 1.35)),
        origin=Origin(xyz=(-r.ring_radius - R * 0.30, R * 0.28, r.globe_center_z)),
        material=materials["wall"],
        name="flat_wall_backing_plate",
    )
    wall.visual(
        Box((R * 0.22, R * 0.12, R * 0.22)),
        origin=Origin(xyz=(-r.ring_radius - R * 0.30, R * 0.20, r.globe_center_z + R * 0.36)),
        material=materials["metal_dark"],
        name="upper_wall_mount_block",
    )
    wall.visual(
        Box((R * 0.22, R * 0.12, R * 0.22)),
        origin=Origin(xyz=(-r.ring_radius - R * 0.30, R * 0.20, r.globe_center_z - R * 0.36)),
        material=materials["metal_dark"],
        name="lower_wall_mount_block",
    )
    wall.visual(
        Box((r.ring_radius + R * 0.30, R * 0.060, R * 0.075)),
        origin=Origin(xyz=(-R * 0.18, R * 0.02, r.globe_center_z + R * 0.18)),
        material=materials["metal"],
        name="cantilever_upper_arm",
    )
    wall.visual(
        Box((r.ring_radius + R * 0.30, R * 0.060, R * 0.075)),
        origin=Origin(xyz=(-R * 0.18, R * 0.02, r.globe_center_z - R * 0.18)),
        material=materials["metal"],
        name="cantilever_lower_arm",
    )
    wall.visual(
        Cylinder(radius=r.ring_tube * 1.3, length=R * 0.20),
        origin=Origin(xyz=(-r.ring_radius, 0.0, r.globe_center_z), rpy=_cyl_y()),
        material=materials["metal_dark"],
        name="wall_arm_side_pivot_socket",
    )

    meridian = _build_meridian_carrier(model, r, wall, materials, parent_kind="wall")
    return SupportAnchors(
        root=wall,
        carrier=meridian,
        globe_parent=meridian,
        globe_center_z=r.globe_center_z,
        ring_radius=r.ring_radius,
        ring_tube=r.ring_tube,
        pivot_x=r.ring_radius,
        support_kind="wall_arm",
    )


def _build_meridian_carrier(
    model: ArticulatedObject,
    r: ResolvedGlobeConfig,
    parent: Part,
    materials: dict[str, object],
    *,
    parent_kind: str,
) -> Part:
    name = "inner_ring" if r.meridian_style == "nested_inner" else "meridian"
    if r.meridian_style == "partial_wall":
        name = "partial_meridian"
    meridian = model.part(name)

    if r.meridian_style == "partial_wall":
        _decorate_partial_wall_meridian(model, meridian, r, materials)
    elif r.support_style == "partial_ring":
        _decorate_partial_desktop_meridian(model, meridian, r, materials)
    else:
        _decorate_full_meridian(model, meridian, r, materials)

    joint_name = "meridian_fixed"
    joint_type = ArticulationType.FIXED
    motion_limits = None
    axis = (1.0, 0.0, 0.0)
    if r.meridian_style in ("full_tilting", "nested_inner", "partial_wall"):
        joint_name = "meridian_tilt"
        joint_type = ArticulationType.REVOLUTE
        motion_limits = MotionLimits(
            effort=80.0,
            velocity=0.8,
            lower=-r.tilt_range,
            upper=r.tilt_range,
        )
    if parent_kind == "wall":
        axis = (0.0, 1.0, 0.0)
    model.articulation(
        joint_name,
        joint_type,
        parent=parent,
        child=meridian,
        origin=Origin(xyz=(0.0, 0.0, r.globe_center_z)),
        axis=axis,
        motion_limits=motion_limits,
    )
    meridian.inertial = Inertial.from_geometry(
        Sphere(radius=r.ring_radius),
        mass=max(0.8, r.globe_radius * 2.2),
        origin=Origin(),
    )
    return meridian


def _decorate_full_meridian(
    model: ArticulatedObject,
    meridian: Part,
    r: ResolvedGlobeConfig,
    materials: dict[str, object],
) -> None:
    _add_torus(
        model,
        meridian,
        name="full_meridian_ring",
        radius=r.ring_radius,
        tube=r.ring_tube,
        material=materials["metal"],
        origin=Origin(rpy=_torus_vertical()),
    )
    for sign, side in ((-1.0, "left"), (1.0, "right")):
        meridian.visual(
            Cylinder(radius=r.ring_tube * 1.20, length=r.ring_tube * 5.0),
            origin=Origin(xyz=(sign * r.ring_radius, 0.0, 0.0), rpy=_cyl_x()),
            material=materials["metal_dark"],
            name=f"{side}_meridian_axis_boss",
        )
        meridian.visual(
            Sphere(radius=r.ring_tube * 1.45),
            origin=Origin(xyz=(sign * r.ring_radius, 0.0, 0.0)),
            material=materials["metal"],
            name=f"{side}_meridian_pivot_cap",
        )
    meridian.visual(
        Sphere(radius=r.ring_tube * 0.85),
        origin=Origin(),
        material=materials["metal_dark"],
        name="globe_spin_bearing_hub",
    )
    meridian.visual(
        Cylinder(radius=r.ring_tube * 0.42, length=r.ring_radius * 2.04),
        origin=Origin(rpy=_cyl_x()),
        material=materials["metal_dark"],
        name="globe_spin_axis_rod",
    )


def _decorate_partial_desktop_meridian(
    model: ArticulatedObject,
    meridian: Part,
    r: ResolvedGlobeConfig,
    materials: dict[str, object],
) -> None:
    _add_torus(
        model,
        meridian,
        name="partial_stand_meridian_ring",
        radius=r.ring_radius,
        tube=r.ring_tube,
        material=materials["metal"],
        origin=Origin(rpy=_torus_vertical()),
        tubular_segments=56,
    )
    meridian.visual(
        Box((r.ring_tube * 3.5, r.ring_tube * 2.0, r.ring_radius * 0.62)),
        origin=Origin(xyz=(0.0, 0.0, -r.ring_radius * 0.72)),
        material=materials["metal_dark"],
        name="partial_meridian_lower_spine",
    )
    for sign, side in ((-1.0, "left"), (1.0, "right")):
        meridian.visual(
            Sphere(radius=r.ring_tube * 1.45),
            origin=Origin(xyz=(sign * r.ring_radius, 0.0, 0.0)),
            material=materials["metal"],
            name=f"{side}_partial_axis_cap",
        )


def _decorate_partial_wall_meridian(
    model: ArticulatedObject,
    meridian: Part,
    r: ResolvedGlobeConfig,
    materials: dict[str, object],
) -> None:
    _add_torus(
        model,
        meridian,
        name="wall_partial_meridian_arc",
        radius=r.ring_radius,
        tube=r.ring_tube,
        material=materials["metal"],
        origin=Origin(rpy=_torus_vertical()),
        tubular_segments=56,
    )
    meridian.visual(
        Box((r.ring_radius * 0.42, r.ring_tube * 2.2, r.ring_tube * 1.6)),
        origin=Origin(xyz=(-r.ring_radius * 0.82, 0.0, r.ring_radius * 0.34)),
        material=materials["metal_dark"],
        name="wall_meridian_upper_mount_bridge",
    )
    meridian.visual(
        Box((r.ring_radius * 0.42, r.ring_tube * 2.2, r.ring_tube * 1.6)),
        origin=Origin(xyz=(-r.ring_radius * 0.82, 0.0, -r.ring_radius * 0.34)),
        material=materials["metal_dark"],
        name="wall_meridian_lower_mount_bridge",
    )
    meridian.visual(
        Cylinder(radius=r.ring_tube * 1.35, length=r.ring_tube * 5.0),
        origin=Origin(xyz=(-r.ring_radius, 0.0, 0.0), rpy=_cyl_y()),
        material=materials["metal_dark"],
        name="wall_meridian_side_hinge_pin",
    )
    meridian.visual(
        Sphere(radius=r.ring_tube * 1.35),
        origin=Origin(xyz=(r.ring_radius, 0.0, 0.0)),
        material=materials["metal"],
        name="wall_meridian_free_axis_cap",
    )


def _build_globe(
    model: ArticulatedObject,
    r: ResolvedGlobeConfig,
    parent: Part,
    materials: dict[str, object],
) -> Part:
    globe = model.part("globe")
    _decorate_globe_surface(model, globe, r, materials)
    origin = Origin()
    if parent.name in ("support_pedestal",):
        origin = Origin(xyz=(0.0, 0.0, r.globe_center_z))
    model.articulation(
        "globe_spin",
        ArticulationType.CONTINUOUS,
        parent=parent,
        child=globe,
        origin=origin,
        axis=r.spin_axis,
        motion_limits=MotionLimits(effort=20.0, velocity=2.8),
    )
    globe.inertial = Inertial.from_geometry(
        Sphere(radius=r.globe_radius),
        mass=max(1.0, 8.0 * r.globe_radius),
        origin=Origin(),
    )
    return globe


def _decorate_globe_surface(
    model: ArticulatedObject,
    globe: Part,
    r: ResolvedGlobeConfig,
    materials: dict[str, object],
) -> None:
    R = r.globe_radius
    globe.visual(
        Sphere(radius=R),
        origin=Origin(),
        material=materials["ocean"],
        name="ocean_sphere",
    )
    globe.visual(
        Sphere(radius=R * 0.996),
        origin=Origin(),
        material=materials["ocean_dark"],
        name="deep_ocean_shadow_core",
    )
    globe.visual(
        Cylinder(radius=R * 0.055, length=R * 0.10),
        origin=Origin(xyz=(0.0, 0.0, R * 1.01), rpy=_cyl_z()),
        material=materials["metal"],
        name="north_polar_axis_cap",
    )
    globe.visual(
        Cylinder(radius=R * 0.055, length=R * 0.10),
        origin=Origin(xyz=(0.0, 0.0, -R * 1.01), rpy=_cyl_z()),
        material=materials["metal"],
        name="south_polar_axis_cap",
    )
    _decorate_graticule(model, globe, r, materials)
    _decorate_land_patches(globe, r, materials)
    if r.surface_style in ("dense_map", "graticule_patch"):
        _decorate_map_labels(globe, r, materials)


def _decorate_graticule(
    model: ArticulatedObject,
    globe: Part,
    r: ResolvedGlobeConfig,
    materials: dict[str, object],
) -> None:
    R = r.globe_radius
    _band_visual(
        globe,
        radius=R,
        name="equator_band",
        material=materials["graticule"],
        axis="xy",
        model=model,
        tube_scale=1.25,
    )
    if r.graticule_density == "none":
        return
    _band_visual(
        globe,
        radius=R,
        name="prime_meridian_band",
        material=materials["graticule"],
        axis="xz",
        model=model,
    )
    _band_visual(
        globe,
        radius=R,
        name="secondary_meridian_band",
        material=materials["graticule"],
        axis="yz",
        model=model,
    )
    lat_scales = {
        "low": (0.72,),
        "medium": (0.52, 0.82),
        "high": (0.36, 0.62, 0.84),
    }.get(r.graticule_density, (0.52, 0.82))
    for i, scale in enumerate(lat_scales):
        z = R * math.sqrt(max(0.0, 1.0 - scale * scale))
        for sign, hemi in ((1.0, "north"), (-1.0, "south")):
            _add_torus(
                model,
                globe,
                name=f"{hemi}_latitude_band_{i}",
                radius=R * scale,
                tube=max(R * 0.004, 0.002),
                material=materials["graticule"],
                origin=Origin(xyz=(0.0, 0.0, sign * z)),
                radial_segments=8,
                tubular_segments=56,
            )


def _decorate_land_patches(
    globe: Part,
    r: ResolvedGlobeConfig,
    materials: dict[str, object],
) -> None:
    R = r.globe_radius
    if r.surface_style == "minimal_ocean":
        patch_specs = (
            (-4, -20, R * 0.34, R * 0.16, "land"),
            (22, 84, R * 0.24, R * 0.14, "land_light"),
            (-28, 122, R * 0.28, R * 0.12, "land_dark"),
        )
    elif r.land_patch_style == "dense_patches" or r.surface_style == "dense_map":
        patch_specs = (
            (35, -100, R * 0.30, R * 0.20, "land"),
            (5, -62, R * 0.23, R * 0.25, "land_dark"),
            (-18, -58, R * 0.20, R * 0.28, "land_light"),
            (48, 18, R * 0.25, R * 0.18, "land"),
            (4, 22, R * 0.22, R * 0.24, "land_dark"),
            (48, 90, R * 0.34, R * 0.20, "land_light"),
            (18, 74, R * 0.22, R * 0.16, "land"),
            (-25, 134, R * 0.25, R * 0.18, "land_dark"),
            (-72, 20, R * 0.32, R * 0.10, "land_light"),
        )
    elif r.land_patch_style == "abstract_patches" or r.surface_style == "graticule_patch":
        patch_specs = (
            (28, -92, R * 0.28, R * 0.16, "land"),
            (-12, -60, R * 0.22, R * 0.24, "land_light"),
            (42, 42, R * 0.32, R * 0.15, "land_dark"),
            (16, 102, R * 0.26, R * 0.17, "land"),
            (-30, 128, R * 0.22, R * 0.16, "land_light"),
        )
    else:
        patch_specs = (
            (42, -105, R * 0.28, R * 0.18, "land"),
            (8, -72, R * 0.20, R * 0.24, "land_dark"),
            (-22, -58, R * 0.18, R * 0.26, "land_light"),
            (50, 20, R * 0.25, R * 0.17, "land"),
            (8, 25, R * 0.18, R * 0.22, "land_dark"),
            (43, 90, R * 0.32, R * 0.17, "land_light"),
            (-25, 132, R * 0.24, R * 0.16, "land"),
        )
    for i, (lat, lon, width, height, material_key) in enumerate(patch_specs):
        _patch_visual(
            globe,
            radius=R,
            lat=lat,
            lon=lon,
            width=width,
            height=height,
            material=materials[material_key],
            name=f"continent_patch_{i}",
        )


def _decorate_map_labels(
    globe: Part,
    r: ResolvedGlobeConfig,
    materials: dict[str, object],
) -> None:
    R = r.globe_radius
    for i, lon in enumerate((-150, -60, 30, 120)):
        _patch_visual(
            globe,
            radius=R,
            lat=-4,
            lon=lon,
            width=R * 0.11,
            height=R * 0.025,
            material=materials["graticule"],
            name=f"small_map_label_dash_{i}",
        )


def _build_date_ring(
    model: ArticulatedObject,
    r: ResolvedGlobeConfig,
    root: Part,
    materials: dict[str, object],
) -> Part:
    date_ring = model.part("date_ring")
    ring_z = max(r.base_height * 0.80, r.globe_center_z - r.globe_radius * 1.16)
    _add_torus(
        model,
        date_ring,
        name="calendar_date_ring",
        radius=r.globe_radius * 0.70,
        tube=max(r.globe_radius * 0.014, 0.006),
        material=materials["metal_dark"],
        origin=Origin(),
        radial_segments=10,
        tubular_segments=64,
    )
    for i in range(12):
        angle = math.tau * i / 12.0
        date_ring.visual(
            Box((r.globe_radius * 0.035, r.globe_radius * 0.012, r.globe_radius * 0.010)),
            origin=Origin(
                xyz=(
                    math.cos(angle) * r.globe_radius * 0.70,
                    math.sin(angle) * r.globe_radius * 0.70,
                    0.0,
                ),
                rpy=(0.0, 0.0, angle),
            ),
            material=materials["graticule"],
            name=f"date_tick_{i}",
        )
    model.articulation(
        "date_ring_spin",
        ArticulationType.CONTINUOUS,
        parent=root,
        child=date_ring,
        origin=Origin(xyz=(0.0, 0.0, ring_z)),
        axis=(0.0, 0.0, 1.0),
        motion_limits=MotionLimits(effort=8.0, velocity=1.2),
    )
    date_ring.inertial = Inertial.from_geometry(
        Cylinder(radius=r.globe_radius * 0.70, length=r.globe_radius * 0.03),
        mass=0.3,
        origin=Origin(rpy=_cyl_z()),
    )
    return date_ring


def _build_support(
    model: ArticulatedObject,
    r: ResolvedGlobeConfig,
    materials: dict[str, object],
) -> SupportAnchors:
    if r.support_style == "outer_cradle":
        return _build_outer_cradle_base(model, r, materials)
    if r.support_style == "partial_ring":
        return _build_partial_ring_base(model, r, materials)
    if r.support_style == "rotating_pedestal":
        return _build_rotating_pedestal_base(model, r, materials)
    if r.support_style == "wall_arm":
        return _build_wall_arm_base(model, r, materials)
    return _build_classic_desktop_base(model, r, materials)


def build_globe(
    config: GlobeConfig | None = None,
    *,
    assets: AssetContext | None = None,
) -> ArticulatedObject:
    cfg = config or GlobeConfig()
    r = resolve_config(cfg)
    model = ArticulatedObject(name=r.name, assets=assets)
    materials = _register_materials(model, r.palette)
    support = _build_support(model, r, materials)
    _build_globe(model, r, support.globe_parent, materials)
    if r.auxiliary_rotary == "date_ring":
        _build_date_ring(model, r, support.root, materials)
    return model


def build_seeded_globe(
    seed: int,
    *,
    assets: AssetContext | None = None,
) -> ArticulatedObject:
    return build_globe(config_from_seed(seed), assets=assets)


def slot_choices_for_config(config: GlobeConfig) -> list[tuple[str, str]]:
    r = resolve_config(config)
    return [
        ("support_base", r.support_style),
        ("meridian_or_cradle", r.meridian_style),
        ("globe_surface", r.surface_style),
        ("auxiliary_rotary", r.auxiliary_rotary),
        ("graticule_density", r.graticule_density),
        ("land_patch_style", r.land_patch_style),
    ]


def slot_choices_for_seed(seed: int) -> list[tuple[str, str]]:
    return slot_choices_for_config(config_from_seed(seed))


def _allow_expected_overlaps(ctx: TestContext, model: ArticulatedObject) -> None:
    part_names = {part.name for part in model.parts}
    if "globe" in part_names:
        globe = model.get_part("globe")
        for support_name in ("meridian", "inner_ring", "partial_meridian", "support_pedestal"):
            if support_name not in part_names:
                continue
            support = model.get_part(support_name)
            for elem_a in (
                "full_meridian_ring",
                "partial_stand_meridian_ring",
                "wall_partial_meridian_arc",
                "left_meridian_axis_boss",
                "right_meridian_axis_boss",
                "globe_spin_bearing_hub",
                "globe_spin_axis_rod",
                "globe_bottom_saddle",
                "lower_spin_saddle_ball",
            ):
                for elem_b in (
                    "ocean_sphere",
                    "deep_ocean_shadow_core",
                    "north_polar_axis_cap",
                    "south_polar_axis_cap",
                    "equator_band",
                    "prime_meridian_band",
                    "secondary_meridian_band",
                    "north_latitude_band_0",
                    "north_latitude_band_1",
                    "north_latitude_band_2",
                    "south_latitude_band_0",
                    "south_latitude_band_1",
                    "south_latitude_band_2",
                ):
                    try:
                        ctx.allow_overlap(
                            support,
                            globe,
                            elem_a=elem_a,
                            elem_b=elem_b,
                            reason="globe is captured by meridian ring or pedestal spin saddle",
                        )
                    except Exception:
                        pass

    for support_name in ("base", "stand", "outer_cradle", "wall_arm"):
        if support_name not in part_names:
            continue
        support = model.get_part(support_name)
        for ring_name in ("meridian", "inner_ring", "partial_meridian"):
            if ring_name not in part_names:
                continue
            ring = model.get_part(ring_name)
            for elem_a in (
                "left_yoke_pivot_socket",
                "right_yoke_pivot_socket",
                "left_yoke_top_bridge",
                "right_yoke_top_bridge",
                "yoke_lower_socket",
                "central_tilt_axis_datum",
                "central_tilt_axis_rod",
                "outer_cradle_pivot_socket_left",
                "outer_cradle_pivot_socket_right",
                "wall_arm_side_pivot_socket",
                "partial_ring_side_post_left",
                "partial_ring_side_post_right",
            ):
                for elem_b in (
                    "full_meridian_ring",
                    "globe_spin_bearing_hub",
                    "globe_spin_axis_rod",
                    "left_meridian_axis_boss",
                    "right_meridian_axis_boss",
                    "left_meridian_pivot_cap",
                    "right_meridian_pivot_cap",
                    "left_partial_axis_cap",
                    "right_partial_axis_cap",
                    "wall_meridian_side_hinge_pin",
                    "wall_meridian_free_axis_cap",
                ):
                    try:
                        ctx.allow_overlap(
                            support,
                            ring,
                            elem_a=elem_a,
                            elem_b=elem_b,
                            reason="meridian pivot cap is seated in support socket",
                        )
                    except Exception:
                        pass

    if "base_ring" in part_names and "support_pedestal" in part_names:
        base = model.get_part("base_ring")
        pedestal = model.get_part("support_pedestal")
        for elem_a in ("turning_base_bearing_race",):
            for elem_b in ("rotating_lower_pedestal",):
                try:
                    ctx.allow_overlap(
                        base,
                        pedestal,
                        elem_a=elem_a,
                        elem_b=elem_b,
                        reason="rotating pedestal sits inside the base bearing race",
                    )
                except Exception:
                    pass

    if "base" in part_names and "globe" in part_names:
        base = model.get_part("base")
        globe = model.get_part("globe")
        for elem_a in ("central_tilt_axis_datum", "central_tilt_axis_rod"):
            for elem_b in (
                "ocean_sphere",
                "deep_ocean_shadow_core",
                "equator_band",
                "prime_meridian_band",
                "secondary_meridian_band",
            ):
                try:
                    ctx.allow_overlap(
                        base,
                        globe,
                        elem_a=elem_a,
                        elem_b=elem_b,
                        reason="central tilt datum sits inside the globe bearing axis",
                    )
                except Exception:
                    pass


def run_globe_tests(
    object_model: ArticulatedObject,
    config: GlobeConfig,
) -> TestReport:
    r = resolve_config(config)
    ctx = TestContext(object_model)
    _allow_expected_overlaps(ctx, object_model)
    ctx.check_model_valid()
    ctx.fail_if_isolated_parts()
    ctx.warn_if_part_contains_disconnected_geometry_islands()
    ctx.fail_if_parts_overlap_in_current_pose()

    part_names = {part.name for part in object_model.parts}
    joint_names = {joint.name for joint in object_model.joints}
    if "globe" not in part_names:
        ctx.fail("identity", "globe template must contain a globe part")
    if "globe_spin" not in joint_names:
        ctx.fail("main_joint", "globe template must expose globe_spin")
    if r.support_style == "rotating_pedestal" and "support_yaw" not in joint_names:
        ctx.fail("support_yaw", "rotating pedestal support must include support_yaw")
    if r.auxiliary_rotary == "date_ring" and "date_ring_spin" not in joint_names:
        ctx.fail("date_ring", "date_ring auxiliary must include date_ring_spin")
    if r.meridian_style != "none_pedestal" and not any(
        name in part_names for name in ("meridian", "inner_ring", "partial_meridian")
    ):
        ctx.fail("meridian", "non-pedestal globe must include a meridian or cradle ring")
    if r.ring_radius <= r.globe_radius:
        ctx.fail("clearance", "meridian radius must be larger than globe radius")

    spin_joint = None
    for joint in object_model.joints:
        if joint.name == "globe_spin":
            spin_joint = joint
            break
    if spin_joint is not None:
        if spin_joint.articulation_type != ArticulationType.CONTINUOUS:
            ctx.fail("globe_spin_type", "globe_spin must be continuous")
        ox, oy, oz = spin_joint.origin.xyz
        if spin_joint.parent == "support_pedestal":
            expected = (0.0, 0.0, r.globe_center_z)
        else:
            expected = (0.0, 0.0, 0.0)
        dist = math.sqrt(
            (ox - expected[0]) ** 2 + (oy - expected[1]) ** 2 + (oz - expected[2]) ** 2
        )
        if dist > 1e-6:
            ctx.fail("spin_origin", "globe_spin origin must be at the globe center")
    return ctx.report()
