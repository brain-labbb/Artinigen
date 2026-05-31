"""Screw-in light bulb with socket, implemented as a modular template.

Slot graph:
  socket -> motion -> bulb

The fixed socket slot owns the fixture shell, liner, internal thread, and
center contact. The motion slot adds the coaxial Z screw carrier: either a
threaded turn/lift pair or a compact simple-spin carrier. The bulb slot owns
the moving screw sleeve, external thread, bottom contact, glass envelope, and
emitter, so the visible bulb payload moves together.
"""

from __future__ import annotations

import math
import random
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
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
    LatheGeometry,
    MeshGeometry,
    MotionLimits,
    Origin,
    TestContext,
    TestReport,
    TorusGeometry,
    mesh_from_geometry,
    tube_from_spline_points,
)

__modular__ = True


SocketModule = Literal[
    "ceramic_socket",
    "field_service_box",
    "calibration_fixture",
    "guarded_fixture",
]
MotionModule = Literal["threaded_turn_lift", "simple_spin"]
BulbModule = Literal["a_bulb", "globe", "candle", "tubular", "frosted_led"]
ThreadStandard = Literal["E12", "E14", "E26", "E27"]
EmitterStyle = Literal["filament_coil", "led_column", "glowing_core"]
MaterialStyle = Literal["black_ceramic", "white_porcelain", "industrial_brass"]

SOCKET_MODULES: tuple[SocketModule, ...] = (
    "ceramic_socket",
    "field_service_box",
    "calibration_fixture",
    "guarded_fixture",
)
MOTION_MODULES: tuple[MotionModule, ...] = ("threaded_turn_lift", "simple_spin")
BULB_MODULES: tuple[BulbModule, ...] = (
    "a_bulb",
    "globe",
    "candle",
    "tubular",
    "frosted_led",
)

SOURCE_IDS = {
    "S1": "data/records/rec_screwin_light_bulb_with_socket_0001/revisions/rev_000001/model.py:L66-L138",
    "S2": "data/records/rec_screwin_light_bulb_with_socket_0001/revisions/rev_000001/model.py:L141-L201",
    "S3": "data/records/rec_screwin_light_bulb_with_socket_0001/revisions/rev_000001/model.py:L203-L345",
    "S4": "data/records/rec_screwin_light_bulb_with_socket_0001/revisions/rev_000001/model.py:L347-L374",
    "S5": "data/records/rec_screwin_light_bulb_with_socket_1dc69a231a07414994cd08d1fb1f1513/revisions/rev_000001/model.py:L22-L136",
    "S6": "data/records/rec_screwin_light_bulb_with_socket_1dc69a231a07414994cd08d1fb1f1513/revisions/rev_000001/model.py:L139-L246",
    "S7": "data/records/rec_screwin_light_bulb_with_socket_1dc69a231a07414994cd08d1fb1f1513/revisions/rev_000001/model.py:L247-L423",
    "S8": "data/records/rec_screwin_light_bulb_with_socket_df6bc323aa9243aeb314e9ea467118d6/revisions/rev_000001/model.py:L51-L155",
    "S9": "data/records/rec_screwin_light_bulb_with_socket_df6bc323aa9243aeb314e9ea467118d6/revisions/rev_000001/model.py:L156-L377",
    "S10": "data/records/rec_screwin_light_bulb_with_socket_df6bc323aa9243aeb314e9ea467118d6/revisions/rev_000001/model.py:L379-L469",
    "S11": "data/records/rec_screwin_light_bulb_with_socket_e81c7386027e4833bc5699a7e434716e/revisions/rev_000001/model.py:L20-L159",
    "S12": "data/records/rec_screwin_light_bulb_with_socket_e81c7386027e4833bc5699a7e434716e/revisions/rev_000001/model.py:L219-L352",
    "S13": "data/records/rec_screwin_light_bulb_with_socket_e81c7386027e4833bc5699a7e434716e/revisions/rev_000001/model.py:L354-L505",
}

SOURCE_ADAPTATION_MAP = {
    "socket.ceramic_socket": ("S2", "S6"),
    "socket.field_service_box": ("S8", "S9", "S10"),
    "socket.calibration_fixture": ("S11", "S12", "S13"),
    "socket.guarded_fixture": ("S8", "S9"),
    "motion.threaded_turn_lift": ("S5", "S7", "S13"),
    "motion.simple_spin": ("S4", "S10"),
    "bulb.a_bulb": ("S1", "S3", "S7"),
    "bulb.globe": ("S3", "S7", "S10"),
    "bulb.candle": ("S3", "S10"),
    "bulb.tubular": ("S7", "S10"),
    "bulb.frosted_led": ("S7", "S13"),
}

PALETTES: dict[MaterialStyle, dict[str, tuple[float, float, float, float]]] = {
    "black_ceramic": {
        "socket": (0.025, 0.026, 0.028, 1.0),
        "porcelain": (0.82, 0.80, 0.72, 1.0),
        "metal": (0.72, 0.70, 0.64, 1.0),
        "thread": (0.94, 0.72, 0.34, 1.0),
        "glass": (0.88, 0.96, 1.0, 0.40),
        "glass_edge": (0.72, 0.88, 1.0, 0.46),
        "emitter": (1.0, 0.58, 0.18, 1.0),
        "dark": (0.06, 0.06, 0.055, 1.0),
    },
    "white_porcelain": {
        "socket": (0.86, 0.84, 0.78, 1.0),
        "porcelain": (0.92, 0.90, 0.84, 1.0),
        "metal": (0.68, 0.67, 0.62, 1.0),
        "thread": (0.92, 0.70, 0.32, 1.0),
        "glass": (0.92, 0.98, 1.0, 0.36),
        "glass_edge": (0.78, 0.90, 1.0, 0.46),
        "emitter": (1.0, 0.70, 0.22, 1.0),
        "dark": (0.10, 0.10, 0.10, 1.0),
    },
    "industrial_brass": {
        "socket": (0.20, 0.18, 0.15, 1.0),
        "porcelain": (0.56, 0.52, 0.44, 1.0),
        "metal": (0.84, 0.60, 0.28, 1.0),
        "thread": (0.98, 0.76, 0.36, 1.0),
        "glass": (0.90, 0.94, 1.0, 0.36),
        "glass_edge": (0.72, 0.84, 0.94, 0.44),
        "emitter": (1.0, 0.52, 0.12, 1.0),
        "dark": (0.04, 0.04, 0.04, 1.0),
    },
}

STANDARD: dict[ThreadStandard, tuple[float, float]] = {
    "E12": (0.0060, 0.0024),
    "E14": (0.0070, 0.0028),
    "E26": (0.0130, 0.0036),
    "E27": (0.0135, 0.0038),
}


@dataclass(frozen=True)
class ScrewinLightBulbWithSocketConfig:
    socket_module: SocketModule | None = None
    motion_module: MotionModule | None = None
    bulb_module: BulbModule | None = None
    thread_standard: ThreadStandard = "E26"
    emitter_style: EmitterStyle = "filament_coil"
    material_style: MaterialStyle = "black_ceramic"
    screw_turns: float = 2.45
    thread_clearance: float = 0.0010
    contact_gap_closed: float = 0.0010
    name: str = "screwin_light_bulb_with_socket"
    palette: dict[str, tuple[float, float, float, float]] = field(
        default_factory=lambda: dict(PALETTES["black_ceramic"])
    )


@dataclass(frozen=True)
class ResolvedScrewinLightBulbWithSocketConfig:
    socket_module: SocketModule
    motion_module: MotionModule
    bulb_module: BulbModule
    thread_standard: ThreadStandard
    emitter_style: EmitterStyle
    material_style: MaterialStyle
    bulb_base_radius: float
    thread_pitch: float
    screw_turns: float
    insertion_depth: float
    thread_clearance: float
    contact_gap_closed: float
    socket_inner_radius: float
    socket_outer_radius: float
    socket_height: float
    insert_height: float
    bulb_base_height: float
    axis_height: float
    glass_radius: float
    glass_height: float
    name: str
    palette: dict[str, tuple[float, float, float, float]]


def config_from_seed(seed: int) -> ScrewinLightBulbWithSocketConfig:
    if seed == 0:
        return ScrewinLightBulbWithSocketConfig(
            socket_module="ceramic_socket",
            motion_module="threaded_turn_lift",
            bulb_module="a_bulb",
            thread_standard="E26",
            emitter_style="filament_coil",
            material_style="black_ceramic",
            screw_turns=2.45,
            thread_clearance=0.0010,
            contact_gap_closed=0.0010,
            name="screwin_light_bulb_with_socket_seed_0_anchor",
        )

    rng = random.Random(seed)
    bulb_module = rng.choice(BULB_MODULES)
    emitter = (
        "led_column"
        if bulb_module == "frosted_led"
        else rng.choice(("filament_coil", "led_column", "glowing_core"))
    )
    return ScrewinLightBulbWithSocketConfig(
        socket_module=rng.choice(SOCKET_MODULES),
        motion_module=rng.choice(MOTION_MODULES),
        bulb_module=bulb_module,
        thread_standard=rng.choice(tuple(STANDARD)),
        emitter_style=emitter,
        material_style=rng.choice(tuple(PALETTES)),
        screw_turns=round(rng.uniform(1.2, 2.85), 2),
        thread_clearance=round(rng.uniform(0.0007, 0.0022), 4),
        contact_gap_closed=round(rng.uniform(0.0004, 0.0020), 4),
        name=f"seeded_screwin_light_bulb_with_socket_{seed}",
    )


def resolve_config(
    config: ScrewinLightBulbWithSocketConfig,
) -> ResolvedScrewinLightBulbWithSocketConfig:
    socket_module = config.socket_module or "ceramic_socket"
    motion_module = config.motion_module or "threaded_turn_lift"
    bulb_module = config.bulb_module or "a_bulb"

    if socket_module not in SOCKET_MODULES:
        raise ValueError(f"Unsupported socket_module: {socket_module}")
    if motion_module not in MOTION_MODULES:
        raise ValueError(f"Unsupported motion_module: {motion_module}")
    if bulb_module not in BULB_MODULES:
        raise ValueError(f"Unsupported bulb_module: {bulb_module}")
    if config.thread_standard not in STANDARD:
        raise ValueError(f"Unsupported thread_standard: {config.thread_standard}")
    if config.emitter_style not in {"filament_coil", "led_column", "glowing_core"}:
        raise ValueError(f"Unsupported emitter_style: {config.emitter_style}")
    if config.material_style not in PALETTES:
        raise ValueError(f"Unsupported material_style: {config.material_style}")

    base_radius, pitch = STANDARD[config.thread_standard]
    screw_turns = _clamp(float(config.screw_turns), 1.0, 3.0)
    clearance = _clamp(float(config.thread_clearance), 0.0006, 0.0025)
    contact_gap = _clamp(float(config.contact_gap_closed), 0.0, 0.0030)
    insertion = pitch * screw_turns
    socket_inner = base_radius + clearance + 0.0012
    socket_outer = socket_inner + (0.009 if config.thread_standard in {"E26", "E27"} else 0.006)
    insert_height = max(0.026, insertion + 0.020)
    socket_height = insert_height + 0.014
    bulb_base_height = insert_height * 0.82
    axis_height = bulb_base_height + 0.032

    radius_scale = {
        "a_bulb": 2.25,
        "globe": 2.75,
        "candle": 1.45,
        "tubular": 1.35,
        "frosted_led": 2.05,
    }[bulb_module]
    height_scale = {
        "a_bulb": 2.90,
        "globe": 2.20,
        "candle": 3.60,
        "tubular": 3.25,
        "frosted_led": 1.85,
    }[bulb_module]
    glass_radius = base_radius * radius_scale
    glass_height = glass_radius * height_scale

    palette = dict(PALETTES[config.material_style])
    if config.palette:
        palette.update(config.palette)

    return ResolvedScrewinLightBulbWithSocketConfig(
        socket_module=socket_module,
        motion_module=motion_module,
        bulb_module=bulb_module,
        thread_standard=config.thread_standard,
        emitter_style=config.emitter_style,
        material_style=config.material_style,
        bulb_base_radius=base_radius,
        thread_pitch=pitch,
        screw_turns=screw_turns,
        insertion_depth=insertion,
        thread_clearance=clearance,
        contact_gap_closed=contact_gap,
        socket_inner_radius=socket_inner,
        socket_outer_radius=socket_outer,
        socket_height=socket_height,
        insert_height=insert_height,
        bulb_base_height=bulb_base_height,
        axis_height=axis_height,
        glass_radius=glass_radius,
        glass_height=glass_height,
        name=config.name,
        palette=palette,
    )


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(value, upper))


def _axis_ring(
    r: ResolvedScrewinLightBulbWithSocketConfig,
) -> tuple[float, float]:
    inner_radius = r.bulb_base_radius * 1.035
    tube = r.axis_height * 0.5
    return inner_radius + tube, tube


def _mesh(model: ArticulatedObject, geometry: object, name: str):
    assert model.assets is not None
    return mesh_from_geometry(geometry, model.assets.mesh_path(name))


def _helical_ridge(
    *,
    base_radius: float,
    peak_radius: float,
    z_start: float,
    z_end: float,
    pitch: float,
    band_width: float,
    segments_per_turn: int = 30,
) -> MeshGeometry:
    turns = (z_end - z_start) / pitch
    steps = max(8, int(abs(turns) * segments_per_turn))
    geom = MeshGeometry()
    rows: list[list[int]] = []
    for k in range(steps + 1):
        t = k / steps
        theta = math.tau * turns * t
        z = z_start + (z_end - z_start) * t
        row = []
        for radius, dz in (
            (base_radius, -band_width / 2.0),
            (peak_radius, -band_width / 2.0),
            (peak_radius, band_width / 2.0),
            (base_radius, band_width / 2.0),
        ):
            row.append(geom.add_vertex(radius * math.cos(theta), radius * math.sin(theta), z + dz))
        rows.append(row)
    for k in range(steps):
        for a, b, c, d in (
            (rows[k][0], rows[k + 1][0], rows[k + 1][1], rows[k][1]),
            (rows[k][1], rows[k + 1][1], rows[k + 1][2], rows[k][2]),
            (rows[k][2], rows[k + 1][2], rows[k + 1][3], rows[k][3]),
            (rows[k][3], rows[k + 1][3], rows[k + 1][0], rows[k][0]),
        ):
            geom.add_face(a, b, c)
            geom.add_face(a, c, d)
    return geom


def _socket_shell_profiles(
    r: ResolvedScrewinLightBulbWithSocketConfig,
    *,
    shoulder: float = 1.0,
) -> tuple[list[tuple[float, float]], list[tuple[float, float]]]:
    outer = [
        (r.socket_outer_radius * 0.92, -0.010),
        (r.socket_outer_radius * 1.04 * shoulder, -0.004),
        (r.socket_outer_radius * 0.96, r.socket_height * 0.30),
        (r.socket_outer_radius * 0.88, r.socket_height * 0.78),
        (r.socket_outer_radius * 1.00, r.socket_height),
    ]
    inner = [
        (r.socket_inner_radius * 0.52, -0.006),
        (r.socket_inner_radius * 0.88, 0.004),
        (r.socket_inner_radius, r.socket_height * 0.80),
        (r.socket_inner_radius * 1.04, r.socket_height),
    ]
    return outer, inner


def _emit_socket_core(
    part,
    ctx: ModuleBuildContext,
    r: ResolvedScrewinLightBulbWithSocketConfig,
    *,
    module_name: str,
    shoulder: float = 1.0,
) -> None:
    outer, inner = _socket_shell_profiles(r, shoulder=shoulder)
    part.visual(
        _mesh(
            ctx.model,
            LatheGeometry.from_shell_profiles(
                outer, inner, segments=96, start_cap="flat", end_cap="flat"
            ),
            f"{module_name}_socket_shell.obj",
        ),
        material=ctx.palette["socket"],
        name="socket_shell",
    )
    part.visual(
        _mesh(
            ctx.model,
            LatheGeometry.from_shell_profiles(
                [
                    (r.socket_inner_radius * 1.05, 0.0),
                    (r.socket_inner_radius * 1.05, r.insert_height),
                ],
                [
                    (r.socket_inner_radius * 0.985, 0.0),
                    (r.socket_inner_radius * 0.985, r.insert_height),
                ],
                segments=96,
                start_cap="flat",
                end_cap="flat",
            ),
            f"{module_name}_socket_liner.obj",
        ),
        material=ctx.palette["metal"],
        name="socket_liner",
    )
    part.visual(
        _mesh(
            ctx.model,
            _helical_ridge(
                base_radius=r.socket_inner_radius * 1.000,
                peak_radius=r.socket_inner_radius * 0.975,
                z_start=0.010,
                z_end=r.insert_height - 0.004,
                pitch=r.thread_pitch,
                band_width=0.0011,
            ),
            f"{module_name}_internal_thread.obj",
        ),
        material=ctx.palette["thread"],
        name="internal_thread",
    )
    part.visual(
        Cylinder(radius=r.socket_inner_radius * 0.99, length=0.0030),
        origin=Origin(xyz=(0.0, 0.0, 0.0020)),
        material=ctx.palette["dark"],
        name="contact_boss",
    )
    part.visual(
        Cylinder(radius=r.socket_inner_radius * 0.42, length=0.0024),
        origin=Origin(xyz=(0.0, 0.0, 0.0036)),
        material=ctx.palette["thread"],
        name="center_contact",
    )
    part.visual(
        Box((r.socket_inner_radius * 1.30, 0.0020, 0.0016)),
        origin=Origin(xyz=(r.socket_inner_radius * 0.22, 0.0, 0.0036)),
        material=ctx.palette["thread"],
        name="center_contact_bridge",
    )
    part.visual(
        Cylinder(radius=r.socket_outer_radius * 1.12, length=0.006),
        origin=Origin(xyz=(0.0, 0.0, -0.012)),
        material=ctx.palette["dark"],
        name="base_plinth",
    )


def _socket_downstream(r: ResolvedScrewinLightBulbWithSocketConfig) -> InterfaceSpec:
    return InterfaceSpec(
        interface_name="socket_thread_axis",
        part_name="socket_body",
        visual_name="socket_liner",
        face_side="positive_z",
        anchor_local=(0.0, 0.0, r.insert_height),
        face_extents_uv=(r.socket_inner_radius * 1.84, r.socket_inner_radius * 1.84),
        contact_tol=0.0015,
    )


def _build_socket_ceramic(ctx: ModuleBuildContext) -> ModuleBuild:
    r: ResolvedScrewinLightBulbWithSocketConfig = ctx.config  # type: ignore[assignment]
    socket = ctx.model.part("socket_body")
    _emit_socket_core(socket, ctx, r, module_name="ceramic_socket")
    socket.visual(
        Cylinder(radius=r.socket_outer_radius * 0.84, length=r.socket_height * 0.34),
        origin=Origin(xyz=(0.0, 0.0, r.socket_height * 0.34)),
        material=ctx.palette["porcelain"],
        name="rib_anchor_band",
    )
    for index, angle in enumerate((0.0, math.tau / 3.0, 2.0 * math.tau / 3.0)):
        socket.visual(
            Box((r.socket_outer_radius * 0.34, 0.006, r.socket_height * 0.35)),
            origin=Origin(
                xyz=(
                    r.socket_outer_radius * 0.96 * math.cos(angle),
                    r.socket_outer_radius * 0.96 * math.sin(angle),
                    r.socket_height * 0.34,
                ),
                rpy=(0.0, 0.0, angle),
            ),
            material=ctx.palette["porcelain"],
            name=f"socket_rib_{index}",
        )
    return ModuleBuild(
        module_name="ceramic_socket",
        parts_emitted=["socket_body"],
        interfaces={"downstream": _socket_downstream(r)},
    )


def _build_socket_field_service_box(ctx: ModuleBuildContext) -> ModuleBuild:
    r: ResolvedScrewinLightBulbWithSocketConfig = ctx.config  # type: ignore[assignment]
    socket = ctx.model.part("socket_body")
    _emit_socket_core(socket, ctx, r, module_name="field_service_box", shoulder=1.05)
    socket.visual(
        Box((r.socket_outer_radius * 3.2, r.socket_outer_radius * 1.8, 0.030)),
        origin=Origin(xyz=(0.0, -r.socket_outer_radius * 1.00, 0.018)),
        material=ctx.palette["socket"],
        name="field_service_box",
    )
    socket.visual(
        Box((r.socket_outer_radius * 2.7, 0.003, 0.020)),
        origin=Origin(xyz=(0.0, -r.socket_outer_radius * 1.90, 0.021)),
        material=ctx.palette["porcelain"],
        name="hinged_service_cover",
    )
    socket.visual(
        Cylinder(radius=r.socket_outer_radius * 0.17, length=r.socket_outer_radius * 0.70),
        origin=Origin(
            xyz=(r.socket_outer_radius * 1.48, -r.socket_outer_radius * 1.00, 0.018),
            rpy=(0.0, math.pi / 2.0, 0.0),
        ),
        material=ctx.palette["dark"],
        name="cable_gland",
    )
    for index, x in enumerate((-0.45, 0.45)):
        socket.visual(
            Box((r.socket_outer_radius * 0.34, 0.004, 0.006)),
            origin=Origin(xyz=(x * r.socket_outer_radius, -r.socket_outer_radius * 1.88, 0.012)),
            material=ctx.palette["thread"],
            name=f"terminal_contact_{index}",
        )
    return ModuleBuild(
        module_name="field_service_box",
        parts_emitted=["socket_body"],
        interfaces={"downstream": _socket_downstream(r)},
    )


def _build_socket_calibration_fixture(ctx: ModuleBuildContext) -> ModuleBuild:
    r: ResolvedScrewinLightBulbWithSocketConfig = ctx.config  # type: ignore[assignment]
    socket = ctx.model.part("socket_body")
    _emit_socket_core(socket, ctx, r, module_name="calibration_fixture", shoulder=1.10)
    socket.visual(
        _mesh(
            ctx.model,
            TorusGeometry(
                radius=r.socket_outer_radius * 1.24,
                tube=0.0015,
                radial_segments=96,
                tubular_segments=10,
            ),
            "calibration_index_ring.obj",
        ),
        origin=Origin(xyz=(0.0, 0.0, r.socket_height - 0.001)),
        material=ctx.palette["thread"],
        name="index_ring",
    )
    for index, angle in enumerate((0.0, math.pi / 2.0, math.pi, 3.0 * math.pi / 2.0)):
        span = r.socket_outer_radius * 0.48
        socket.visual(
            Box((span, 0.0020, 0.0020)),
            origin=Origin(
                xyz=(
                    r.socket_outer_radius * 1.02 * math.cos(angle),
                    r.socket_outer_radius * 1.02 * math.sin(angle),
                    r.socket_height - 0.001,
                ),
                rpy=(0.0, 0.0, angle),
            ),
            material=ctx.palette["thread"],
            name=f"index_ring_spoke_{index}",
        )
    for index, angle in enumerate((0.0, math.pi / 2.0)):
        socket.visual(
            Cylinder(radius=0.0022, length=r.socket_outer_radius * 1.20),
            origin=Origin(
                xyz=(
                    r.socket_outer_radius * math.cos(angle),
                    r.socket_outer_radius * math.sin(angle),
                    r.socket_height * 0.50,
                ),
                rpy=(0.0, math.pi / 2.0, angle),
            ),
            material=ctx.palette["metal"],
            name=f"adjustment_screw_{index}",
        )
    socket.visual(
        Box((r.socket_outer_radius * 2.75, r.socket_outer_radius * 2.75, 0.004)),
        origin=Origin(xyz=(0.0, 0.0, -0.016)),
        material=ctx.palette["dark"],
        name="calibration_base_plate",
    )
    return ModuleBuild(
        module_name="calibration_fixture",
        parts_emitted=["socket_body"],
        interfaces={"downstream": _socket_downstream(r)},
    )


def _build_socket_guarded_fixture(ctx: ModuleBuildContext) -> ModuleBuild:
    r: ResolvedScrewinLightBulbWithSocketConfig = ctx.config  # type: ignore[assignment]
    socket = ctx.model.part("socket_body")
    _emit_socket_core(socket, ctx, r, module_name="guarded_fixture", shoulder=1.08)
    ring_z = r.socket_height + r.glass_height * 0.38
    socket.visual(
        _mesh(
            ctx.model,
            TorusGeometry(
                radius=r.glass_radius * 1.18,
                tube=0.0013,
                radial_segments=112,
                tubular_segments=8,
            ),
            "guard_top_ring.obj",
        ),
        origin=Origin(xyz=(0.0, 0.0, ring_z)),
        material=ctx.palette["metal"],
        name="guard_top_ring",
    )
    socket.visual(
        _mesh(
            ctx.model,
            TorusGeometry(
                radius=r.glass_radius * 1.06,
                tube=0.0014,
                radial_segments=112,
                tubular_segments=8,
            ),
            "guard_lower_ring.obj",
        ),
        origin=Origin(xyz=(0.0, 0.0, r.socket_height - 0.001)),
        material=ctx.palette["metal"],
        name="guard_lower_ring",
    )
    for index, angle in enumerate((0.0, math.pi / 2.0, math.pi, 3.0 * math.pi / 2.0)):
        span = max(0.004, r.glass_radius * 1.06 - r.socket_outer_radius * 0.92)
        socket.visual(
            Box((span, 0.0020, 0.0020)),
            origin=Origin(
                xyz=(
                    (r.socket_outer_radius * 0.92 + span * 0.5) * math.cos(angle),
                    (r.socket_outer_radius * 0.92 + span * 0.5) * math.sin(angle),
                    r.socket_height - 0.001,
                ),
                rpy=(0.0, 0.0, angle),
            ),
            material=ctx.palette["metal"],
            name=f"guard_lower_spoke_{index}",
        )
    for index, angle in enumerate((0.0, math.pi / 2.0, math.pi, 3.0 * math.pi / 2.0)):
        radius = r.glass_radius * 1.12
        socket.visual(
            Box((0.0020, 0.0020, ring_z - r.socket_height + 0.004)),
            origin=Origin(
                xyz=(
                    radius * math.cos(angle),
                    radius * math.sin(angle),
                    (ring_z + r.socket_height) * 0.5 - 0.001,
                )
            ),
            material=ctx.palette["metal"],
            name=f"guard_wire_{index}",
        )
    return ModuleBuild(
        module_name="guarded_fixture",
        parts_emitted=["socket_body"],
        interfaces={"downstream": _socket_downstream(r)},
    )


def _motion_interfaces(
    r: ResolvedScrewinLightBulbWithSocketConfig,
    *,
    joint_type: ArticulationType,
    limits: MotionLimits | None,
) -> dict[str, InterfaceSpec]:
    return {
        "upstream": InterfaceSpec(
            interface_name="motion_socket_face",
            part_name="thread_axis",
            visual_name="axis_socket_pad",
            face_side="negative_z",
            anchor_local=(0.0, 0.0, 0.0),
            face_extents_uv=(r.bulb_base_radius * 0.50, r.bulb_base_radius * 0.50),
            consumer_joint_type=joint_type,
            consumer_joint_axis=(0.0, 0.0, 1.0),
            consumer_motion_limits=limits,
            contact_tol=0.0015,
        ),
        "downstream": InterfaceSpec(
            interface_name="motion_bulb_face",
            part_name="thread_axis",
            visual_name="bulb_drive_pad",
            face_side="positive_z",
            anchor_local=(0.0, 0.0, r.axis_height),
            face_extents_uv=(r.bulb_base_radius * 0.50, r.bulb_base_radius * 0.50),
            contact_tol=0.0015,
        ),
    }


def _build_motion_threaded_turn_lift(ctx: ModuleBuildContext) -> ModuleBuild:
    r: ResolvedScrewinLightBulbWithSocketConfig = ctx.config  # type: ignore[assignment]
    axis = ctx.model.part("thread_axis")
    axis.visual(
        Cylinder(radius=r.socket_inner_radius * 0.46, length=0.0040),
        origin=Origin(xyz=(0.0, 0.0, 0.0020)),
        material=ctx.palette["thread"],
        name="axis_socket_pad",
    )
    axis.visual(
        Cylinder(radius=max(0.00055, r.socket_inner_radius * 0.07), length=r.axis_height),
        origin=Origin(xyz=(0.0, 0.0, r.axis_height * 0.5)),
        material=ctx.palette["thread"],
        name="axis_spine",
    )
    axis.visual(
        Box((r.socket_inner_radius * 1.70, 0.0010, 0.0030)),
        origin=Origin(xyz=(r.socket_inner_radius * 0.45, 0.0, 0.0015)),
        material=ctx.palette["thread"],
        name="axis_socket_key",
    )
    axis.visual(
        Cylinder(radius=r.bulb_base_radius * 0.38, length=0.0040),
        origin=Origin(xyz=(0.0, 0.0, r.axis_height - 0.0020)),
        material=ctx.palette["thread"],
        name="bulb_drive_pad",
    )
    axis.visual(
        Box((r.bulb_base_radius * 1.05, 0.0010, 0.0030)),
        origin=Origin(xyz=(r.bulb_base_radius * 0.28, 0.0, r.axis_height - 0.0015)),
        material=ctx.palette["thread"],
        name="bulb_drive_key",
    )
    limits = MotionLimits(
        lower=0.0,
        upper=r.screw_turns * math.tau,
        effort=1.2,
        velocity=1.0,
    )
    return ModuleBuild(
        module_name="threaded_turn_lift",
        parts_emitted=["thread_axis"],
        interfaces=_motion_interfaces(r, joint_type=ArticulationType.REVOLUTE, limits=limits),
    )


def _build_motion_simple_spin(ctx: ModuleBuildContext) -> ModuleBuild:
    r: ResolvedScrewinLightBulbWithSocketConfig = ctx.config  # type: ignore[assignment]
    axis = ctx.model.part("thread_axis")
    axis.visual(
        Cylinder(radius=r.socket_inner_radius * 0.44, length=0.0040),
        origin=Origin(xyz=(0.0, 0.0, 0.0020)),
        material=ctx.palette["thread"],
        name="axis_socket_pad",
    )
    axis.visual(
        Cylinder(radius=max(0.00055, r.socket_inner_radius * 0.07), length=r.axis_height),
        origin=Origin(xyz=(0.0, 0.0, r.axis_height * 0.5)),
        material=ctx.palette["thread"],
        name="axis_spine",
    )
    axis.visual(
        Box((r.socket_inner_radius * 1.70, 0.0010, 0.0030)),
        origin=Origin(xyz=(r.socket_inner_radius * 0.45, 0.0, 0.0015)),
        material=ctx.palette["thread"],
        name="axis_socket_key",
    )
    axis.visual(
        Cylinder(radius=r.bulb_base_radius * 0.36, length=0.0040),
        origin=Origin(xyz=(0.0, 0.0, r.axis_height - 0.0020)),
        material=ctx.palette["thread"],
        name="bulb_drive_pad",
    )
    axis.visual(
        Box((r.bulb_base_radius * 1.00, 0.0010, 0.0030)),
        origin=Origin(xyz=(r.bulb_base_radius * 0.26, 0.0, r.axis_height - 0.0015)),
        material=ctx.palette["thread"],
        name="bulb_drive_key",
    )
    limits = MotionLimits(effort=1.0, velocity=1.0)
    return ModuleBuild(
        module_name="simple_spin",
        parts_emitted=["thread_axis"],
        interfaces=_motion_interfaces(r, joint_type=ArticulationType.CONTINUOUS, limits=limits),
    )


def _glass_profiles(
    r: ResolvedScrewinLightBulbWithSocketConfig,
    module_name: BulbModule,
) -> tuple[list[tuple[float, float]], list[tuple[float, float]]]:
    if module_name == "globe":
        outer = [
            (r.bulb_base_radius * 0.86, 0.001),
            (r.glass_radius * 0.70, r.glass_height * 0.16),
            (r.glass_radius, r.glass_height * 0.48),
            (r.glass_radius * 0.70, r.glass_height * 0.82),
            (0.002, r.glass_height),
        ]
    elif module_name == "candle":
        outer = [
            (r.bulb_base_radius * 0.78, 0.001),
            (r.glass_radius, r.glass_height * 0.18),
            (r.glass_radius * 0.82, r.glass_height * 0.70),
            (0.003, r.glass_height),
        ]
    elif module_name == "tubular":
        outer = [
            (r.bulb_base_radius * 0.82, 0.001),
            (r.glass_radius, r.glass_height * 0.12),
            (r.glass_radius, r.glass_height * 0.86),
            (0.003, r.glass_height),
        ]
    elif module_name == "frosted_led":
        outer = [
            (r.bulb_base_radius * 0.92, 0.001),
            (r.glass_radius * 0.95, r.glass_height * 0.16),
            (r.glass_radius, r.glass_height * 0.52),
            (r.glass_radius * 0.52, r.glass_height * 0.88),
            (0.003, r.glass_height),
        ]
    else:
        outer = [
            (r.bulb_base_radius * 0.86, 0.001),
            (r.glass_radius * 0.60, r.glass_height * 0.18),
            (r.glass_radius, r.glass_height * 0.48),
            (r.glass_radius * 0.76, r.glass_height * 0.76),
            (0.003, r.glass_height),
        ]
    inner = [(max(0.001, radius - 0.0011), z + 0.0005) for radius, z in outer]
    return outer, inner


def _emit_bulb_base(
    part,
    ctx: ModuleBuildContext,
    r: ResolvedScrewinLightBulbWithSocketConfig,
    module_name: BulbModule,
) -> None:
    major_radius, tube_radius = _axis_ring(r)
    part.visual(
        _mesh(
            ctx.model,
            TorusGeometry(
                radius=major_radius,
                tube=tube_radius,
                radial_segments=96,
                tubular_segments=8,
            ),
            f"{module_name}_bulb_drive_face.obj",
        ),
        origin=Origin(xyz=(0.0, 0.0, tube_radius)),
        material=ctx.palette["thread"],
        name="bulb_drive_face",
    )
    part.visual(
        Cylinder(radius=r.bulb_base_radius, length=r.bulb_base_height),
        origin=Origin(xyz=(0.0, 0.0, -r.bulb_base_height * 0.5 + 0.0005)),
        material=ctx.palette["metal"],
        name="screw_sleeve",
    )
    part.visual(
        _mesh(
            ctx.model,
            _helical_ridge(
                base_radius=r.bulb_base_radius * 0.98,
                peak_radius=r.bulb_base_radius * 1.06,
                z_start=-r.bulb_base_height + 0.004,
                z_end=-0.004,
                pitch=r.thread_pitch,
                band_width=0.0013,
                segments_per_turn=32,
            ),
            f"{module_name}_external_thread.obj",
        ),
        material=ctx.palette["thread"],
        name="external_thread",
    )
    part.visual(
        Cylinder(radius=r.bulb_base_radius * 0.48, length=0.0030),
        origin=Origin(xyz=(0.0, 0.0, -r.bulb_base_height - 0.0008)),
        material=ctx.palette["dark"],
        name="contact_insulator",
    )
    part.visual(
        Cylinder(radius=r.bulb_base_radius * 0.36, length=0.0024),
        origin=Origin(xyz=(0.0, 0.0, -r.bulb_base_height - r.contact_gap_closed - 0.0012)),
        material=ctx.palette["thread"],
        name="base_contact",
    )
    part.visual(
        _mesh(
            ctx.model,
            TorusGeometry(
                radius=r.bulb_base_radius * 1.03,
                tube=0.0008,
                radial_segments=80,
                tubular_segments=8,
            ),
            f"{module_name}_glass_crimp.obj",
        ),
        origin=Origin(xyz=(0.0, 0.0, 0.002)),
        material=ctx.palette["thread"],
        name="crimp_seam",
    )


def _emit_glass_and_emitter(
    part,
    ctx: ModuleBuildContext,
    r: ResolvedScrewinLightBulbWithSocketConfig,
    module_name: BulbModule,
) -> None:
    outer, inner = _glass_profiles(r, module_name)
    part.visual(
        Cylinder(radius=r.bulb_base_radius * 0.90, length=0.008),
        origin=Origin(xyz=(0.0, 0.0, 0.004)),
        material=ctx.palette["glass_edge"],
        name="glass_neck_collar",
    )
    part.visual(
        _mesh(
            ctx.model,
            LatheGeometry.from_shell_profiles(
                outer, inner, segments=112, start_cap="flat", end_cap="flat"
            ),
            f"{module_name}_glass_envelope.obj",
        ),
        origin=Origin(xyz=(0.0, 0.0, 0.0)),
        material=ctx.palette["glass"],
        name="glass_envelope",
    )
    part.visual(
        Cylinder(radius=max(0.0016, r.bulb_base_radius * 0.13), length=r.glass_height * 0.92),
        origin=Origin(xyz=(0.0, 0.0, r.glass_height * 0.46)),
        material=ctx.palette["glass_edge"],
        name="glass_stem_bridge",
    )
    part.visual(
        Cylinder(radius=max(0.00065, r.glass_radius * 0.035), length=r.glass_height * 0.40),
        origin=Origin(xyz=(0.0, 0.0, r.glass_height * 0.20)),
        material=ctx.palette["emitter"],
        name="emitter_stem",
    )
    emitter_style = "led_column" if module_name == "frosted_led" else r.emitter_style
    if emitter_style == "filament_coil":
        supports = [
            (-r.glass_radius * 0.16, 0.0, 0.006),
            (-r.glass_radius * 0.20, 0.0, r.glass_height * 0.36),
            (r.glass_radius * 0.20, 0.0, r.glass_height * 0.36),
            (r.glass_radius * 0.16, 0.0, 0.006),
        ]
        part.visual(
            _mesh(
                ctx.model,
                tube_from_spline_points(
                    supports,
                    radius=0.00055,
                    samples_per_segment=10,
                    radial_segments=10,
                    cap_ends=True,
                ),
                f"{module_name}_filament_supports.obj",
            ),
            material=ctx.palette["emitter"],
            name="filament_supports",
        )
        points = [
            (
                -r.glass_radius * 0.18 + r.glass_radius * 0.36 * i / 72,
                0.00065 * math.cos(math.tau * 7.0 * i / 72),
                r.glass_height * 0.36 + 0.00065 * math.sin(math.tau * 7.0 * i / 72),
            )
            for i in range(73)
        ]
        part.visual(
            _mesh(
                ctx.model,
                tube_from_spline_points(
                    points,
                    radius=0.00032,
                    samples_per_segment=1,
                    radial_segments=8,
                    cap_ends=True,
                ),
                f"{module_name}_filament_coil.obj",
            ),
            material=ctx.palette["emitter"],
            name="filament_coil",
        )
    elif emitter_style == "led_column":
        part.visual(
            Cylinder(radius=r.glass_radius * 0.12, length=r.glass_height * 0.34),
            origin=Origin(xyz=(0.0, 0.0, r.glass_height * 0.22)),
            material=ctx.palette["emitter"],
            name="led_emitter_column",
        )
        part.visual(
            Cylinder(radius=r.glass_radius * 0.26, length=0.002),
            origin=Origin(xyz=(0.0, 0.0, r.glass_height * 0.40)),
            material=ctx.palette["glass_edge"],
            name="led_diffuser_cap",
        )
    else:
        part.visual(
            Cylinder(radius=r.glass_radius * 0.18, length=r.glass_height * 0.16),
            origin=Origin(xyz=(0.0, 0.0, r.glass_height * 0.28)),
            material=ctx.palette["emitter"],
            name="glowing_core",
        )


def _build_bulb_module(ctx: ModuleBuildContext, module_name: BulbModule) -> ModuleBuild:
    r: ResolvedScrewinLightBulbWithSocketConfig = ctx.config  # type: ignore[assignment]
    bulb = ctx.model.part("bulb_assembly")
    _emit_bulb_base(bulb, ctx, r, module_name)
    _emit_glass_and_emitter(bulb, ctx, r, module_name)
    prior = dict(ctx.prior_choices)
    threaded = prior.get("motion") == "threaded_turn_lift"
    upstream = InterfaceSpec(
        interface_name="bulb_drive_face",
        part_name="bulb_assembly",
        visual_name="bulb_drive_face",
        face_side="negative_z",
        anchor_local=(0.0, 0.0, 0.0),
        face_extents_uv=(r.bulb_base_radius * 1.44, r.bulb_base_radius * 1.44),
        consumer_joint_type=ArticulationType.PRISMATIC if threaded else ArticulationType.FIXED,
        consumer_joint_axis=(0.0, 0.0, 1.0),
        consumer_motion_limits=MotionLimits(
            lower=0.0,
            upper=r.insertion_depth,
            effort=18.0,
            velocity=0.015,
        )
        if threaded
        else None,
        contact_tol=0.0015,
    )
    return ModuleBuild(
        module_name=module_name,
        parts_emitted=["bulb_assembly"],
        interfaces={"upstream": upstream},
    )


def _build_bulb_a_bulb(ctx: ModuleBuildContext) -> ModuleBuild:
    return _build_bulb_module(ctx, "a_bulb")


def _build_bulb_globe(ctx: ModuleBuildContext) -> ModuleBuild:
    return _build_bulb_module(ctx, "globe")


def _build_bulb_candle(ctx: ModuleBuildContext) -> ModuleBuild:
    return _build_bulb_module(ctx, "candle")


def _build_bulb_tubular(ctx: ModuleBuildContext) -> ModuleBuild:
    return _build_bulb_module(ctx, "tubular")


def _build_bulb_frosted_led(ctx: ModuleBuildContext) -> ModuleBuild:
    return _build_bulb_module(ctx, "frosted_led")


SOCKET_FACTORIES = {
    "ceramic_socket": _build_socket_ceramic,
    "field_service_box": _build_socket_field_service_box,
    "calibration_fixture": _build_socket_calibration_fixture,
    "guarded_fixture": _build_socket_guarded_fixture,
}
MOTION_FACTORIES = {
    "threaded_turn_lift": _build_motion_threaded_turn_lift,
    "simple_spin": _build_motion_simple_spin,
}
BULB_FACTORIES = {
    "a_bulb": _build_bulb_a_bulb,
    "globe": _build_bulb_globe,
    "candle": _build_bulb_candle,
    "tubular": _build_bulb_tubular,
    "frosted_led": _build_bulb_frosted_led,
}


def _slots_for_config(r: ResolvedScrewinLightBulbWithSocketConfig) -> list[SlotSpec]:
    return [
        SlotSpec(
            slot_name="socket",
            candidates={r.socket_module: SOCKET_FACTORIES[r.socket_module]},
            anchor_choice=r.socket_module,
        ),
        SlotSpec(
            slot_name="motion",
            candidates={r.motion_module: MOTION_FACTORIES[r.motion_module]},
            anchor_choice=r.motion_module,
        ),
        SlotSpec(
            slot_name="bulb",
            candidates={r.bulb_module: BULB_FACTORIES[r.bulb_module]},
            anchor_choice=r.bulb_module,
        ),
    ]


def build_screwin_light_bulb_with_socket(
    config: ScrewinLightBulbWithSocketConfig | None = None,
    *,
    assets: AssetContext | None = None,
) -> ArticulatedObject:
    config = config or ScrewinLightBulbWithSocketConfig()
    r = resolve_config(config)
    assets = assets or AssetContext(Path(tempfile.mkdtemp(prefix="articraft-screwin-bulb-assets-")))
    model = ArticulatedObject(name=r.name, assets=assets)
    material_names = {}
    for material_name, rgba in r.palette.items():
        registered_name = material_name
        model.material(registered_name, rgba=rgba)
        material_names[material_name] = registered_name

    assemble(
        model,
        slots=_slots_for_config(r),
        rng=random.Random(0),
        palette=material_names,  # type: ignore[arg-type]
        config=r,
        seed=0,
    )
    model.meta["slot_choices"] = slot_choices_for_config_from_resolved(r)
    model.meta["thread_pitch"] = r.thread_pitch
    model.meta["insertion_depth"] = r.insertion_depth
    return model


def build_seeded_screwin_light_bulb_with_socket(
    seed: int,
    *,
    assets: AssetContext | None = None,
) -> ArticulatedObject:
    return build_screwin_light_bulb_with_socket(config_from_seed(seed), assets=assets)


def slot_choices_for_config_from_resolved(
    r: ResolvedScrewinLightBulbWithSocketConfig,
) -> list[tuple[str, str]]:
    return [
        ("socket", r.socket_module),
        ("motion", r.motion_module),
        ("bulb", r.bulb_module),
    ]


def slot_choices_for_seed(seed: int) -> list[tuple[str, str]]:
    return slot_choices_for_config_from_resolved(resolve_config(config_from_seed(seed)))


def _allow_expected_thread_overlaps(ctx: TestContext) -> None:
    ctx.allow_overlap(
        "socket_body",
        "thread_axis",
        elem_a="socket_liner",
        elem_b="axis_socket_pad",
        reason="coaxial screw carrier is seated inside the threaded socket liner",
    )
    ctx.allow_overlap(
        "socket_body",
        "bulb_assembly",
        elem_a="socket_liner",
        elem_b="screw_sleeve",
        reason="bulb screw sleeve is intentionally engaged inside the socket liner",
    )
    ctx.allow_overlap(
        "socket_body",
        "bulb_assembly",
        elem_a="internal_thread",
        elem_b="external_thread",
        reason="male and female screw-thread ridges intermesh in the seated pose",
    )
    ctx.allow_overlap(
        "thread_axis",
        "bulb_assembly",
        elem_a="bulb_drive_pad",
        elem_b="bulb_drive_face",
        reason="motion carrier face is captured against the bulb drive face",
    )


def run_screwin_light_bulb_with_socket_tests(
    object_model: ArticulatedObject,
    config: ScrewinLightBulbWithSocketConfig,
) -> TestReport:
    r = resolve_config(config)
    ctx = TestContext(object_model)
    _allow_expected_thread_overlaps(ctx)
    ctx.check_model_valid()
    ctx.fail_if_isolated_parts()
    ctx.warn_if_part_contains_disconnected_geometry_islands()

    part_names = {part.name for part in object_model.parts}
    ctx.check(
        "identity_parts_present",
        {"socket_body", "thread_axis", "bulb_assembly"}.issubset(part_names),
        details=f"parts={sorted(part_names)}",
    )
    socket_to_motion = object_model.get_articulation("socket_to_motion")
    motion_to_bulb = object_model.get_articulation("motion_to_bulb")
    ctx.check(
        "socket_is_fixed_parent",
        socket_to_motion.parent == "socket_body",
        details=f"parent={socket_to_motion.parent}",
    )
    ctx.check(
        "coaxial_z_screw_axis",
        tuple(socket_to_motion.axis) == (0.0, 0.0, 1.0),
        details=str(socket_to_motion.axis),
    )
    ctx.check(
        "thread_fit_clearance",
        r.socket_inner_radius > r.bulb_base_radius + r.thread_clearance,
        details=f"inner={r.socket_inner_radius:.4f} base={r.bulb_base_radius:.4f}",
    )
    if r.motion_module == "threaded_turn_lift":
        ctx.check(
            "threaded_motion_types",
            socket_to_motion.articulation_type == ArticulationType.REVOLUTE
            and motion_to_bulb.articulation_type == ArticulationType.PRISMATIC,
            details=f"{socket_to_motion.articulation_type}, {motion_to_bulb.articulation_type}",
        )
        ctx.check(
            "thread_advance_axis",
            tuple(motion_to_bulb.axis) == (0.0, 0.0, 1.0),
            details=str(motion_to_bulb.axis),
        )
        limits = motion_to_bulb.motion_limits
        ctx.check(
            "pitch_consistency",
            limits is not None
            and abs((limits.upper or 0.0) - r.thread_pitch * r.screw_turns) < 1e-9,
            details=f"travel={None if limits is None else limits.upper} pitch={r.thread_pitch}",
        )
    else:
        ctx.check(
            "simple_spin_motion_types",
            socket_to_motion.articulation_type == ArticulationType.CONTINUOUS
            and motion_to_bulb.articulation_type == ArticulationType.FIXED,
            details=f"{socket_to_motion.articulation_type}, {motion_to_bulb.articulation_type}",
        )
    return ctx.report()


__all__ = [
    "__modular__",
    "ScrewinLightBulbWithSocketConfig",
    "ResolvedScrewinLightBulbWithSocketConfig",
    "SOURCE_IDS",
    "SOURCE_ADAPTATION_MAP",
    "SOCKET_MODULES",
    "MOTION_MODULES",
    "BULB_MODULES",
    "config_from_seed",
    "resolve_config",
    "build_screwin_light_bulb_with_socket",
    "build_seeded_screwin_light_bulb_with_socket",
    "slot_choices_for_seed",
    "run_screwin_light_bulb_with_socket_tests",
]
