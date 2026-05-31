"""Serial elbow arm — modular procedural template.

Slot graph:
    base -> upper_link -> forearm

The default family is a vertical-pitch two-link arm: shoulder and elbow are
both revolute joints with parallel Y axes. A planar pick-place branch is
available through ``axis_family="planar_yaw"``; that branch switches both
primary joints to Z axes instead of mixing pitch and yaw semantics.
"""

from __future__ import annotations

import itertools
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
    Inertial,
    MatingContract,
    MotionLimits,
    MotionProperties,
    Origin,
    TestContext,
    TestReport,
)

__modular__ = True


AxisFamily = Literal["vertical_pitch", "planar_yaw"]
BaseModule = Literal["pedestal_yoke", "root_fork", "controller_yaw_base"]
UpperModule = Literal[
    "box_beam_yoke",
    "open_plate_yoke",
    "dual_parallel_yoke",
    "triple_segment_yoke",
    "quad_segment_yoke",
    "five_dof_yoke",
    "six_dof_yoke",
    "seven_dof_yoke",
]
ForearmModule = Literal["flange_forearm", "pad_plate_forearm", "suction_tool_forearm"]
JointLimitProfile = Literal["industrial_safe", "wide_range", "compact_service"]
PaletteTheme = Literal["industrial_gray", "painted_white", "safety_orange"]
JointHousingStyle = Literal["boxed_clevis", "round_bearing", "split_plate", "compact_ring"]
JointCapMotif = Literal[
    "auto",
    "horizontal_slot",
    "cross_slot",
    "vertical_slot",
    "twin_bolt",
    "center_pin",
]

BASE_MODULES: tuple[str, ...] = ("pedestal_yoke", "root_fork", "controller_yaw_base")
UPPER_MODULES: tuple[str, ...] = (
    "box_beam_yoke",
    "open_plate_yoke",
    "dual_parallel_yoke",
    "triple_segment_yoke",
    "quad_segment_yoke",
    "five_dof_yoke",
    "six_dof_yoke",
    "seven_dof_yoke",
)
FOREARM_MODULES: tuple[str, ...] = ("flange_forearm", "pad_plate_forearm", "suction_tool_forearm")
JOINT_HOUSING_STYLES: tuple[str, ...] = (
    "boxed_clevis",
    "round_bearing",
    "split_plate",
    "compact_ring",
)
CAP_MOTIFS: tuple[str, ...] = (
    "horizontal_slot",
    "cross_slot",
    "vertical_slot",
    "twin_bolt",
    "center_pin",
)
JOINT_CAP_MOTIFS: tuple[str, ...] = ("auto", *CAP_MOTIFS)
ANCHOR_CHOICES: tuple[tuple[str, str], ...] = (
    ("base", "pedestal_yoke"),
    ("upper_link", "box_beam_yoke"),
    ("forearm", "flange_forearm"),
)

SOURCE_IDS = {
    "S1": "data/records/rec_serial_elbow_arm_0003/revisions/rev_000001/model.py:L24-L103",
    "S2": "data/records/rec_serial_elbow_arm_0003/revisions/rev_000001/model.py:L106-L271",
    "S3": "data/records/rec_serial_elbow_arm_0003/revisions/rev_000001/model.py:L282-L491",
    "S4": "data/records/rec_serial_elbow_arm_c8111e5b8ef843138835f71ed1538cda/revisions/rev_000001/model.py:L24-L86",
    "S5": "data/records/rec_serial_elbow_arm_c8111e5b8ef843138835f71ed1538cda/revisions/rev_000001/model.py:L89-L283",
    "S6": "data/records/rec_serial_elbow_arm_c8111e5b8ef843138835f71ed1538cda/revisions/rev_000001/model.py:L286-L520",
    "S7": "data/records/rec_serial_elbow_arm_478aa122662d4b30b7125b7215d77d4b/revisions/rev_000001/model.py:L23-L67",
    "S8": "data/records/rec_serial_elbow_arm_478aa122662d4b30b7125b7215d77d4b/revisions/rev_000001/model.py:L69-L148",
    "S9": "data/records/rec_serial_elbow_arm_478aa122662d4b30b7125b7215d77d4b/revisions/rev_000001/model.py:L151-L261",
    "S10": "data/records/rec_serial_elbow_arm_958fc14d6dc5464d82adfcbf2530c2b8/revisions/rev_000001/model.py:L18-L50",
    "S11": "data/records/rec_serial_elbow_arm_958fc14d6dc5464d82adfcbf2530c2b8/revisions/rev_000001/model.py:L52-L138",
    "S12": "data/records/rec_serial_elbow_arm_958fc14d6dc5464d82adfcbf2530c2b8/revisions/rev_000001/model.py:L139-L156",
}

SOURCE_ADAPTATION_MAP = {
    "base.pedestal_yoke": ("S2", "S3"),
    "base.root_fork": ("S5", "S6"),
    "base.controller_yaw_base": ("S10", "S12"),
    "upper_link.box_beam_yoke": ("S2", "S3"),
    "upper_link.open_plate_yoke": ("S5", "S6"),
    "upper_link.dual_parallel_yoke": ("S8", "S9", "S11"),
    "upper_link.triple_segment_yoke": ("S3", "S6", "S9"),
    "upper_link.quad_segment_yoke": ("S3", "S6", "S9"),
    "upper_link.five_dof_yoke": ("S3", "S6", "S9"),
    "upper_link.six_dof_yoke": ("S3", "S6", "S9"),
    "upper_link.seven_dof_yoke": ("S3", "S6", "S9"),
    "forearm.flange_forearm": ("S2", "S3"),
    "forearm.pad_plate_forearm": ("S5", "S6"),
    "forearm.suction_tool_forearm": ("S10", "S11", "S12"),
    "primary_joints.vertical_pitch": ("S3", "S6", "S9"),
    "primary_joints.planar_yaw": ("S12",),
    "joint_housings.boxed_clevis": ("S3", "S6", "S9"),
    "joint_housings.round_bearing": ("S3", "S6", "S9"),
    "joint_housings.split_plate": ("S5", "S6", "S9"),
    "joint_housings.compact_ring": ("S8", "S9", "S11"),
}

PALETTE_PRESETS: dict[str, dict[str, tuple[float, float, float, float]]] = {
    "industrial_gray": {
        "base": (0.45, 0.47, 0.49, 1.0),
        "link": (0.60, 0.62, 0.63, 1.0),
        "cover": (0.22, 0.23, 0.24, 1.0),
        "bolt": (0.10, 0.10, 0.11, 1.0),
        "accent": (0.95, 0.70, 0.18, 1.0),
        "rubber": (0.02, 0.02, 0.02, 1.0),
    },
    "painted_white": {
        "base": (0.78, 0.78, 0.74, 1.0),
        "link": (0.88, 0.87, 0.82, 1.0),
        "cover": (0.33, 0.34, 0.35, 1.0),
        "bolt": (0.08, 0.08, 0.08, 1.0),
        "accent": (0.12, 0.30, 0.60, 1.0),
        "rubber": (0.03, 0.03, 0.03, 1.0),
    },
    "safety_orange": {
        "base": (0.22, 0.24, 0.25, 1.0),
        "link": (0.90, 0.40, 0.12, 1.0),
        "cover": (0.12, 0.13, 0.14, 1.0),
        "bolt": (0.05, 0.05, 0.05, 1.0),
        "accent": (0.95, 0.90, 0.22, 1.0),
        "rubber": (0.01, 0.01, 0.01, 1.0),
    },
}


@dataclass(frozen=True)
class SerialElbowArmConfig:
    base_module: BaseModule | None = None
    upper_module: UpperModule | None = None
    forearm_module: ForearmModule | None = None
    axis_family: AxisFamily = "vertical_pitch"
    palette_theme: PaletteTheme = "industrial_gray"
    total_reach: float = 0.620
    link_ratio: float = 0.520
    shoulder_z: float = 0.180
    joint_limit_profile: JointLimitProfile = "industrial_safe"
    joint_housing_style: JointHousingStyle = "boxed_clevis"
    joint_cap_motif: JointCapMotif = "auto"
    has_cable_tube: bool = True
    name: str = "reference_serial_elbow_arm"
    palette: dict[str, tuple[float, float, float, float]] = field(
        default_factory=lambda: dict(PALETTE_PRESETS["industrial_gray"])
    )


@dataclass(frozen=True)
class ResolvedSerialElbowArmConfig:
    base_module: BaseModule
    upper_module: UpperModule
    forearm_module: ForearmModule
    axis_family: AxisFamily
    palette_theme: PaletteTheme
    total_reach: float
    link_ratio: float
    upper_len: float
    forearm_len: float
    tool_offset: float
    shoulder_z: float
    upper_width: float
    forearm_width: float
    link_height: float
    cheek_thickness: float
    bearing_clearance: float
    shoulder_axis: tuple[float, float, float]
    elbow_axis: tuple[float, float, float]
    shoulder_limit: tuple[float, float]
    elbow_limit: tuple[float, float]
    joint_housing_style: JointHousingStyle
    joint_cap_motif: JointCapMotif
    has_cable_tube: bool
    name: str
    palette: dict[str, tuple[float, float, float, float]]


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(value)))


def _module_combo_for_seed(seed: int) -> tuple[str, str, str]:
    if seed == 0:
        return ("pedestal_yoke", "box_beam_yoke", "flange_forearm")
    combos = list(itertools.product(BASE_MODULES, UPPER_MODULES, FOREARM_MODULES))
    return combos[(seed * 7) % len(combos)]


def _upper_segment_count(upper_module: str) -> int:
    if upper_module == "triple_segment_yoke":
        return 2
    if upper_module == "quad_segment_yoke":
        return 3
    if upper_module == "five_dof_yoke":
        return 4
    if upper_module == "six_dof_yoke":
        return 5
    if upper_module == "seven_dof_yoke":
        return 6
    return 1


def _upper_terminal_part_name(r: ResolvedSerialElbowArmConfig) -> str:
    segment_count = _upper_segment_count(r.upper_module)
    if segment_count == 1:
        return "upper_link"
    return f"serial_mid_link_{segment_count - 1}"


def _upper_terminal_anchor_x(r: ResolvedSerialElbowArmConfig) -> float:
    return r.upper_len / _upper_segment_count(r.upper_module)


def _joint_style_for_index(r: ResolvedSerialElbowArmConfig, joint_index: int) -> str:
    base_index = JOINT_HOUSING_STYLES.index(r.joint_housing_style)
    if _upper_segment_count(r.upper_module) == 1:
        offset = joint_index % 2
    else:
        offset = joint_index
    return JOINT_HOUSING_STYLES[(base_index + offset) % len(JOINT_HOUSING_STYLES)]


def _cap_motif_for_index(r: ResolvedSerialElbowArmConfig, joint_index: int) -> str:
    if r.joint_cap_motif != "auto":
        return r.joint_cap_motif
    style_index = JOINT_HOUSING_STYLES.index(r.joint_housing_style)
    return CAP_MOTIFS[(style_index + joint_index) % len(CAP_MOTIFS)]


def config_from_seed(seed: int) -> SerialElbowArmConfig:
    if seed == 0:
        return SerialElbowArmConfig()

    rng = random.Random(seed)
    base_module, upper_module, forearm_module = _module_combo_for_seed(seed)
    axis_family: AxisFamily = "planar_yaw" if rng.random() < 0.20 else "vertical_pitch"
    return SerialElbowArmConfig(
        base_module=base_module,  # type: ignore[arg-type]
        upper_module=upper_module,  # type: ignore[arg-type]
        forearm_module=forearm_module,  # type: ignore[arg-type]
        axis_family=axis_family,
        palette_theme=rng.choice(("industrial_gray", "painted_white", "safety_orange")),
        total_reach=round(rng.uniform(0.46, 1.30), 3),
        link_ratio=round(rng.uniform(0.46, 0.57), 3),
        shoulder_z=round(rng.uniform(0.13, 0.36), 3),
        joint_limit_profile=rng.choice(("industrial_safe", "wide_range", "compact_service")),
        joint_housing_style=rng.choice(JOINT_HOUSING_STYLES),  # type: ignore[arg-type]
        has_cable_tube=rng.random() < 0.70,
        name=f"seeded_serial_elbow_arm_{seed}",
    )


def _validate_choice(
    field_name: str, value: str | None, choices: tuple[str, ...], default: str
) -> str:
    if value is None:
        return default
    if value not in choices:
        raise ValueError(f"{field_name} must be one of {choices!r}; got {value!r}")
    return value


def resolve_config(config: SerialElbowArmConfig | None = None) -> ResolvedSerialElbowArmConfig:
    config = config or SerialElbowArmConfig()
    base_module = _validate_choice("base_module", config.base_module, BASE_MODULES, "pedestal_yoke")
    upper_module = _validate_choice(
        "upper_module", config.upper_module, UPPER_MODULES, "box_beam_yoke"
    )
    forearm_module = _validate_choice(
        "forearm_module", config.forearm_module, FOREARM_MODULES, "flange_forearm"
    )
    if config.axis_family not in {"vertical_pitch", "planar_yaw"}:
        raise ValueError(
            f"axis_family must be 'vertical_pitch' or 'planar_yaw'; got {config.axis_family!r}"
        )
    if config.palette_theme not in PALETTE_PRESETS:
        raise ValueError(f"palette_theme must be one of {tuple(PALETTE_PRESETS)!r}")
    if config.joint_limit_profile not in {"industrial_safe", "wide_range", "compact_service"}:
        raise ValueError(
            "joint_limit_profile must be industrial_safe, wide_range, or compact_service"
        )
    if config.joint_housing_style not in JOINT_HOUSING_STYLES:
        raise ValueError(f"joint_housing_style must be one of {JOINT_HOUSING_STYLES!r}")
    if config.joint_cap_motif not in JOINT_CAP_MOTIFS:
        raise ValueError(f"joint_cap_motif must be one of {JOINT_CAP_MOTIFS!r}")

    total_reach = _clamp(config.total_reach, 0.42, 1.40)
    link_ratio = _clamp(config.link_ratio, 0.45, 0.58)
    shoulder_z = _clamp(config.shoulder_z, 0.10, 0.45)
    tool_offset = 0.085 if forearm_module == "suction_tool_forearm" else 0.052
    upper_len = max(0.16, 0.14 * _upper_segment_count(upper_module), total_reach * link_ratio)
    forearm_len = max(0.14, total_reach - upper_len - tool_offset)
    upper_width = _clamp(total_reach * 0.074, 0.045, 0.095)
    forearm_width = _clamp(upper_width * 0.78, 0.036, 0.078)
    link_height = _clamp(total_reach * 0.082, 0.040, 0.105)
    cheek_thickness = _clamp(upper_width * 0.22, 0.010, 0.020)
    bearing_clearance = _clamp(upper_width * 0.08, 0.004, 0.009)

    if config.joint_limit_profile == "wide_range":
        shoulder_limit, elbow_limit = (-1.55, 1.35), (-2.25, 1.20)
    elif config.joint_limit_profile == "compact_service":
        shoulder_limit, elbow_limit = (-0.75, 1.05), (-1.35, 0.90)
    else:
        shoulder_limit, elbow_limit = (-1.20, 1.15), (-1.80, 1.25)

    axis = (0.0, 0.0, 1.0) if config.axis_family == "planar_yaw" else (0.0, 1.0, 0.0)
    palette = dict(PALETTE_PRESETS[config.palette_theme])
    palette.update(config.palette)

    return ResolvedSerialElbowArmConfig(
        base_module=base_module,  # type: ignore[arg-type]
        upper_module=upper_module,  # type: ignore[arg-type]
        forearm_module=forearm_module,  # type: ignore[arg-type]
        axis_family=config.axis_family,
        palette_theme=config.palette_theme,
        total_reach=total_reach,
        link_ratio=link_ratio,
        upper_len=upper_len,
        forearm_len=forearm_len,
        tool_offset=tool_offset,
        shoulder_z=shoulder_z,
        upper_width=upper_width,
        forearm_width=forearm_width,
        link_height=link_height,
        cheek_thickness=cheek_thickness,
        bearing_clearance=bearing_clearance,
        shoulder_axis=axis,
        elbow_axis=axis,
        shoulder_limit=shoulder_limit,
        elbow_limit=elbow_limit,
        joint_housing_style=config.joint_housing_style,
        joint_cap_motif=config.joint_cap_motif,
        has_cable_tube=config.has_cable_tube,
        name=config.name,
        palette=palette,
    )


def _mat(ctx: ModuleBuildContext, key: str) -> str:
    return f"serial_arm_{key}"


def _box(part, size, xyz, material: str, name: str) -> None:
    part.visual(Box(size), origin=Origin(xyz=xyz), material=material, name=name)


def _cylinder(
    part, radius: float, length: float, xyz, material: str, name: str, rpy=(0.0, 0.0, 0.0)
) -> None:
    part.visual(
        Cylinder(radius=radius, length=length),
        origin=Origin(xyz=xyz, rpy=rpy),
        material=material,
        name=name,
    )


def _emit_pitch_mating_pad(
    part,
    r: ResolvedSerialElbowArmConfig,
    ctx: ModuleBuildContext,
    *,
    x: float,
    z: float,
    face_side: Literal["positive_y", "negative_y"],
    name: str,
    pad_height_scale: float,
) -> None:
    pad_t = max(0.0025, min(r.cheek_thickness * 0.42, r.bearing_clearance * 0.90))
    y = -pad_t * 0.5 if face_side == "positive_y" else pad_t * 0.5
    _box(
        part,
        (r.link_height * 0.96, pad_t, r.link_height * pad_height_scale),
        (x, y, z),
        _mat(ctx, "cover"),
        name,
    )


def _emit_centered_pitch_hub(
    part,
    r: ResolvedSerialElbowArmConfig,
    ctx: ModuleBuildContext,
    *,
    x: float,
    z: float,
    y_span: float,
    name: str,
    radius_scale: float = 0.48,
    style: str = "boxed_clevis",
    motif: str = "horizontal_slot",
) -> None:
    radius = r.link_height * radius_scale
    if style == "round_bearing":
        radius *= 1.12
    elif style == "compact_ring":
        radius *= 0.92
    web_y_span = y_span * 0.18
    web_material = _mat(ctx, "link")
    _cylinder(
        part,
        radius,
        max(0.010, y_span),
        (x, 0.0, z),
        _mat(ctx, "cover"),
        name,
        rpy=(math.pi / 2.0, 0.0, 0.0),
    )
    web_len = r.link_height * (
        0.80 if style == "split_plate" else 0.64 if style == "compact_ring" else 0.74
    )
    web_height = r.link_height * (0.26 if style == "compact_ring" else 0.34)
    _box(
        part,
        (web_len, web_y_span, web_height),
        (x, 0.0, z),
        web_material,
        f"{name}_web",
    )
    _emit_cap_motif(
        part,
        r,
        ctx,
        x=x,
        z=z,
        y_span=y_span,
        radius=radius,
        name=name,
        motif=motif,
    )
    if style == "round_bearing":
        _cylinder(
            part,
            radius * 0.68,
            max(0.004, y_span * 1.10),
            (x, 0.0, z),
            _mat(ctx, "bolt"),
            f"{name}_inner_pin",
            rpy=(math.pi / 2.0, 0.0, 0.0),
        )
        for side, y_sign in (("front", -1.0), ("rear", 1.0)):
            _cylinder(
                part,
                radius * 0.16,
                0.003,
                (x, y_sign * (y_span * 0.53), z + radius * 0.42),
                _mat(ctx, "bolt"),
                f"{name}_{side}_upper_bolt",
                rpy=(math.pi / 2.0, 0.0, 0.0),
            )
            _cylinder(
                part,
                radius * 0.16,
                0.003,
                (x, y_sign * (y_span * 0.53), z - radius * 0.42),
                _mat(ctx, "bolt"),
                f"{name}_{side}_lower_bolt",
                rpy=(math.pi / 2.0, 0.0, 0.0),
            )
    elif style == "split_plate":
        for label, z_sign in (("upper", 1.0), ("lower", -1.0)):
            _box(
                part,
                (r.link_height * 0.58, y_span * 0.12, r.link_height * 0.12),
                (x, -y_span * 0.50, z + z_sign * r.link_height * 0.30),
                _mat(ctx, "cover"),
                f"{name}_front_{label}_split_lug",
            )
            _box(
                part,
                (r.link_height * 0.58, y_span * 0.12, r.link_height * 0.12),
                (x, y_span * 0.50, z + z_sign * r.link_height * 0.30),
                _mat(ctx, "cover"),
                f"{name}_rear_{label}_split_lug",
            )
    elif style == "compact_ring":
        _cylinder(
            part,
            radius * 0.42,
            max(0.004, y_span * 1.08),
            (x, 0.0, z),
            _mat(ctx, "bolt"),
            f"{name}_center_pin",
            rpy=(math.pi / 2.0, 0.0, 0.0),
        )
        _cylinder(
            part,
            radius * 1.16,
            max(0.004, y_span * 0.18),
            (x, -y_span * 0.43, z),
            _mat(ctx, "accent"),
            f"{name}_outer_ring_left",
            rpy=(math.pi / 2.0, 0.0, 0.0),
        )
        _cylinder(
            part,
            radius * 1.16,
            max(0.004, y_span * 0.18),
            (x, y_span * 0.43, z),
            _mat(ctx, "accent"),
            f"{name}_outer_ring_right",
            rpy=(math.pi / 2.0, 0.0, 0.0),
        )


def _emit_cap_motif(
    part,
    r: ResolvedSerialElbowArmConfig,
    ctx: ModuleBuildContext,
    *,
    x: float,
    z: float,
    y_span: float,
    radius: float,
    name: str,
    motif: str,
) -> None:
    face_y = max(0.006, y_span * 0.515)
    motif_t = max(0.0025, min(0.004, y_span * 0.08))

    def emit_box(label: str, size: tuple[float, float, float], z_offset: float = 0.0) -> None:
        for side, sign in (("front", -1.0), ("rear", 1.0)):
            _box(
                part,
                size,
                (x, sign * face_y, z + z_offset),
                _mat(ctx, "accent"),
                f"{name}_{side}_{label}",
            )

    def emit_bolt(label: str, z_offset: float) -> None:
        for side, sign in (("front", -1.0), ("rear", 1.0)):
            _cylinder(
                part,
                radius * 0.17,
                motif_t,
                (x, sign * face_y, z + z_offset),
                _mat(ctx, "bolt"),
                f"{name}_{side}_{label}",
                rpy=(math.pi / 2.0, 0.0, 0.0),
            )

    if motif == "cross_slot":
        emit_box("horizontal_slot", (radius * 1.45, motif_t, radius * 0.22))
        emit_box("vertical_slot", (radius * 0.22, motif_t, radius * 1.45))
    elif motif == "vertical_slot":
        emit_box("vertical_slot", (radius * 0.24, motif_t, radius * 1.52))
    elif motif == "twin_bolt":
        emit_bolt("upper_bolt", radius * 0.46)
        emit_bolt("lower_bolt", -radius * 0.46)
    elif motif == "center_pin":
        emit_bolt("center_pin", 0.0)
    else:
        emit_box("horizontal_slot", (radius * 1.55, motif_t, radius * 0.22))


def _emit_pitch_cheek(
    part,
    r: ResolvedSerialElbowArmConfig,
    ctx: ModuleBuildContext,
    *,
    x: float,
    y: float,
    z: float,
    prefix: str,
    side: str,
    style: str,
    width_scale: float,
    height_scale: float,
) -> None:
    if style == "round_bearing":
        _box(
            part,
            (r.link_height * 0.48, r.cheek_thickness, r.link_height * 0.44),
            (x, y, z),
            _mat(ctx, "link"),
            f"{prefix}_{side}_round_ear_neck",
        )
        _cylinder(
            part,
            r.link_height * 0.62,
            r.cheek_thickness * 1.12,
            (x, y, z),
            _mat(ctx, "cover"),
            f"{prefix}_{side}_round_ear_plate",
            rpy=(math.pi / 2.0, 0.0, 0.0),
        )
        return
    if style == "split_plate":
        _box(
            part,
            (r.link_height * 0.20, r.cheek_thickness, r.link_height * 1.10),
            (x, y, z),
            _mat(ctx, "link"),
            f"{prefix}_{side}_split_spine",
        )
        for label, z_sign in (("upper", 1.0), ("lower", -1.0)):
            _box(
                part,
                (r.link_height * 0.70, r.cheek_thickness, r.link_height * 0.28),
                (x, y, z + z_sign * r.link_height * 0.36),
                _mat(ctx, "link"),
                f"{prefix}_{side}_{label}_split_ear",
            )
        return
    if style == "compact_ring":
        _box(
            part,
            (r.link_height * 0.36, r.cheek_thickness, r.link_height * 0.34),
            (x, y, z),
            _mat(ctx, "link"),
            f"{prefix}_{side}_compact_neck",
        )
        _cylinder(
            part,
            r.link_height * 0.46,
            r.cheek_thickness * 1.08,
            (x, y, z),
            _mat(ctx, "cover"),
            f"{prefix}_{side}_compact_round_plate",
            rpy=(math.pi / 2.0, 0.0, 0.0),
        )
        return
    _box(
        part,
        (r.link_height * width_scale, r.cheek_thickness, r.link_height * height_scale),
        (x, y, z),
        _mat(ctx, "link"),
        f"{prefix}_{side}_cheek",
    )


def _motion_limits(limits: tuple[float, float], *, effort: float, velocity: float) -> MotionLimits:
    return MotionLimits(effort=effort, velocity=velocity, lower=limits[0], upper=limits[1])


def _base_downstream_interface(r: ResolvedSerialElbowArmConfig, visual_name: str) -> InterfaceSpec:
    if r.axis_family == "planar_yaw":
        return InterfaceSpec(
            "shoulder_yaw_mount",
            "base",
            visual_name,
            "positive_z",
            (0.0, 0.0, r.shoulder_z),
            consumer_joint_type=ArticulationType.REVOLUTE,
            consumer_joint_axis=r.shoulder_axis,
            consumer_motion_limits=_motion_limits(r.shoulder_limit, effort=90.0, velocity=1.4),
        )
    return InterfaceSpec(
        "shoulder_pitch_mount",
        "base",
        visual_name,
        "positive_y",
        (0.0, 0.0, r.shoulder_z),
        consumer_joint_type=ArticulationType.REVOLUTE,
        consumer_joint_axis=r.shoulder_axis,
        consumer_motion_limits=_motion_limits(r.shoulder_limit, effort=90.0, velocity=1.4),
    )


def _upper_upstream_interface(
    r: ResolvedSerialElbowArmConfig, visual_name: str, *, part_name: str = "upper_link"
) -> InterfaceSpec:
    if r.axis_family == "planar_yaw":
        return InterfaceSpec(
            "shoulder_yaw_hub",
            part_name,
            visual_name,
            "negative_z",
            (0.0, 0.0, 0.0),
            consumer_joint_type=ArticulationType.REVOLUTE,
            consumer_joint_axis=r.shoulder_axis,
            consumer_motion_limits=_motion_limits(r.shoulder_limit, effort=90.0, velocity=1.4),
        )
    return InterfaceSpec(
        "shoulder_pitch_hub",
        part_name,
        visual_name,
        "negative_y",
        (0.0, 0.0, 0.0),
        consumer_joint_type=ArticulationType.REVOLUTE,
        consumer_joint_axis=r.shoulder_axis,
        consumer_motion_limits=_motion_limits(r.shoulder_limit, effort=90.0, velocity=1.4),
    )


def _upper_downstream_interface(
    r: ResolvedSerialElbowArmConfig,
    visual_name: str,
    *,
    part_name: str = "upper_link",
    anchor_x: float | None = None,
) -> InterfaceSpec:
    anchor_x = r.upper_len if anchor_x is None else anchor_x
    if r.axis_family == "planar_yaw":
        return InterfaceSpec(
            "elbow_yaw_socket",
            part_name,
            visual_name,
            "positive_z",
            (anchor_x, 0.0, 0.0),
            consumer_joint_type=ArticulationType.REVOLUTE,
            consumer_joint_axis=r.elbow_axis,
            consumer_motion_limits=_motion_limits(r.elbow_limit, effort=55.0, velocity=1.8),
        )
    return InterfaceSpec(
        "elbow_pitch_socket",
        part_name,
        visual_name,
        "positive_y",
        (anchor_x, 0.0, 0.0),
        consumer_joint_type=ArticulationType.REVOLUTE,
        consumer_joint_axis=r.elbow_axis,
        consumer_motion_limits=_motion_limits(r.elbow_limit, effort=55.0, velocity=1.8),
    )


def _forearm_upstream_interface(r: ResolvedSerialElbowArmConfig, visual_name: str) -> InterfaceSpec:
    if r.axis_family == "planar_yaw":
        return InterfaceSpec(
            "elbow_yaw_hub",
            "forearm",
            visual_name,
            "negative_z",
            (0.0, 0.0, 0.0),
            consumer_joint_type=ArticulationType.REVOLUTE,
            consumer_joint_axis=r.elbow_axis,
            consumer_motion_limits=_motion_limits(r.elbow_limit, effort=55.0, velocity=1.8),
        )
    return InterfaceSpec(
        "elbow_pitch_hub",
        "forearm",
        visual_name,
        "negative_y",
        (0.0, 0.0, 0.0),
        consumer_joint_type=ArticulationType.REVOLUTE,
        consumer_joint_axis=r.elbow_axis,
        consumer_motion_limits=_motion_limits(r.elbow_limit, effort=55.0, velocity=1.8),
    )


def _emit_base_common(
    part, r: ResolvedSerialElbowArmConfig, ctx: ModuleBuildContext, *, plate_scale: float
) -> None:
    plate_x = max(0.20, r.total_reach * 0.34 * plate_scale)
    plate_y = max(0.16, r.upper_width * 3.2 * plate_scale)
    _box(
        part, (plate_x, plate_y, 0.024), (0.0, 0.0, 0.012), _mat(ctx, "base"), "ground_mount_plate"
    )
    for i, (sx, sy) in enumerate(((-1.0, -1.0), (-1.0, 1.0), (1.0, -1.0), (1.0, 1.0))):
        _cylinder(
            part,
            0.005,
            0.006,
            (sx * plate_x * 0.36, sy * plate_y * 0.32, 0.027),
            _mat(ctx, "bolt"),
            f"mount_bolt_{i}",
        )


def _emit_pitch_yoke(
    part,
    r: ResolvedSerialElbowArmConfig,
    ctx: ModuleBuildContext,
    *,
    visual_name: str,
    style: str,
) -> None:
    gap = r.upper_width + 2.0 * r.bearing_clearance
    cheek_y = gap * 0.5 + r.cheek_thickness * 0.5
    column_h = max(0.04, r.shoulder_z - r.link_height * 0.32)
    _box(
        part,
        (r.upper_width * 1.5, gap + 2.0 * r.cheek_thickness + 0.016, column_h),
        (0.0, 0.0, column_h * 0.5),
        _mat(ctx, "base"),
        "pedestal_column",
    )
    for side, sign in (("left", -1.0), ("right", 1.0)):
        _emit_pitch_cheek(
            part,
            r,
            ctx,
            x=0.0,
            y=sign * cheek_y,
            z=r.shoulder_z,
            prefix="shoulder",
            side=side,
            style=style,
            width_scale=1.32,
            height_scale=1.85,
        )
    _box(
        part,
        (r.upper_width * 1.18, max(0.0025, r.bearing_clearance * 0.90), r.link_height * 1.08),
        (0.0, -max(0.0025, r.bearing_clearance * 0.90) * 0.5, r.shoulder_z),
        _mat(ctx, "cover"),
        visual_name,
    )
    for side, sign in (("left", -1.0), ("right", 1.0)):
        cover_radius = r.link_height * (
            0.50 if style == "round_bearing" else 0.34 if style == "compact_ring" else 0.42
        )
        _cylinder(
            part,
            cover_radius,
            0.006,
            (0.0, sign * (cheek_y + r.cheek_thickness * 0.54), r.shoulder_z),
            _mat(ctx, "cover"),
            f"shoulder_{side}_bearing_cover",
            rpy=(math.pi / 2.0, 0.0, 0.0),
        )
    if style == "split_plate":
        _box(
            part,
            (r.upper_width * 1.12, gap + r.cheek_thickness, r.link_height * 0.12),
            (0.0, 0.0, r.shoulder_z + r.link_height * 0.54),
            _mat(ctx, "accent"),
            "shoulder_upper_tie_bar",
        )


def _emit_yaw_base(
    part, r: ResolvedSerialElbowArmConfig, ctx: ModuleBuildContext, *, visual_name: str
) -> None:
    post_h = max(0.060, r.shoulder_z - 0.018)
    _cylinder(
        part,
        r.upper_width * 0.86,
        post_h,
        (0.0, 0.0, post_h * 0.5),
        _mat(ctx, "base"),
        "yaw_pedestal_column",
    )
    _box(
        part,
        (r.upper_width * 2.25, r.upper_width * 2.25, 0.018),
        (0.0, 0.0, r.shoulder_z - 0.009),
        _mat(ctx, "cover"),
        visual_name,
    )


def _build_base_pedestal_yoke(ctx: ModuleBuildContext) -> ModuleBuild:
    r: ResolvedSerialElbowArmConfig = ctx.config  # type: ignore[assignment]
    part = ctx.model.part("base")
    _emit_base_common(part, r, ctx, plate_scale=1.0)
    socket_name = (
        "shoulder_yaw_socket" if r.axis_family == "planar_yaw" else "shoulder_pitch_socket"
    )
    if r.axis_family == "planar_yaw":
        _emit_yaw_base(part, r, ctx, visual_name=socket_name)
    else:
        _emit_pitch_yoke(part, r, ctx, visual_name=socket_name, style=_joint_style_for_index(r, 0))
    part.inertial = Inertial.from_geometry(
        Box((0.24, 0.20, max(r.shoulder_z, 0.12))),
        mass=8.5,
        origin=Origin(xyz=(0.0, 0.0, r.shoulder_z * 0.5)),
    )
    return ModuleBuild(
        "pedestal_yoke",
        ["base"],
        interfaces={"downstream": _base_downstream_interface(r, socket_name)},
    )


def _build_base_root_fork(ctx: ModuleBuildContext) -> ModuleBuild:
    r: ResolvedSerialElbowArmConfig = ctx.config  # type: ignore[assignment]
    part = ctx.model.part("base")
    _emit_base_common(part, r, ctx, plate_scale=0.82)
    socket_name = (
        "shoulder_yaw_socket" if r.axis_family == "planar_yaw" else "shoulder_pitch_socket"
    )
    if r.axis_family == "planar_yaw":
        _emit_yaw_base(part, r, ctx, visual_name=socket_name)
    else:
        _box(
            part,
            (r.upper_width * 0.82, r.upper_width * 0.82, r.shoulder_z),
            (0.0, 0.0, r.shoulder_z * 0.5),
            _mat(ctx, "base"),
            "compact_root_post",
        )
        _emit_pitch_yoke(part, r, ctx, visual_name=socket_name, style=_joint_style_for_index(r, 0))
        _box(
            part,
            (r.upper_width * 1.8, r.cheek_thickness, r.link_height * 0.45),
            (-r.upper_width * 0.28, 0.0, r.shoulder_z - r.link_height * 0.74),
            _mat(ctx, "accent"),
            "fork_cross_stop",
        )
    part.inertial = Inertial.from_geometry(
        Box((0.22, 0.18, max(r.shoulder_z, 0.12))),
        mass=7.8,
        origin=Origin(xyz=(0.0, 0.0, r.shoulder_z * 0.5)),
    )
    return ModuleBuild(
        "root_fork",
        ["base"],
        interfaces={"downstream": _base_downstream_interface(r, socket_name)},
    )


def _build_base_controller_yaw(ctx: ModuleBuildContext) -> ModuleBuild:
    r: ResolvedSerialElbowArmConfig = ctx.config  # type: ignore[assignment]
    part = ctx.model.part("base")
    _emit_base_common(part, r, ctx, plate_scale=1.18)
    socket_name = (
        "shoulder_yaw_socket" if r.axis_family == "planar_yaw" else "shoulder_pitch_socket"
    )
    if r.axis_family == "planar_yaw":
        _emit_yaw_base(part, r, ctx, visual_name=socket_name)
    else:
        _emit_pitch_yoke(part, r, ctx, visual_name=socket_name, style=_joint_style_for_index(r, 0))
    _box(
        part,
        (r.upper_width * 1.6, r.upper_width * 1.05, r.shoulder_z * 0.46),
        (-r.upper_width * 2.2, -r.upper_width * 1.25, max(0.040, r.shoulder_z * 0.23)),
        _mat(ctx, "cover"),
        "controller_box",
    )
    _box(
        part,
        (r.upper_width * 0.75, 0.010, 0.010),
        (-r.upper_width * 2.2, -r.upper_width * 0.74, r.shoulder_z * 0.38),
        _mat(ctx, "accent"),
        "controller_status_strip",
    )
    part.inertial = Inertial.from_geometry(
        Box((0.30, 0.24, max(r.shoulder_z, 0.12))),
        mass=9.2,
        origin=Origin(xyz=(0.0, 0.0, r.shoulder_z * 0.5)),
    )
    return ModuleBuild(
        "controller_yaw_base",
        ["base"],
        interfaces={"downstream": _base_downstream_interface(r, socket_name)},
    )


def _emit_upper_upstream_hub(
    part,
    r: ResolvedSerialElbowArmConfig,
    ctx: ModuleBuildContext,
    *,
    name: str,
    centered_name: str,
    y_span: float | None = None,
    style: str = "boxed_clevis",
    motif: str = "horizontal_slot",
) -> None:
    if r.axis_family == "planar_yaw":
        _box(
            part,
            (r.link_height * 1.2, r.link_height * 1.2, r.link_height * 0.52),
            (0.0, 0.0, r.link_height * 0.26),
            _mat(ctx, "cover"),
            name,
        )
        return

    _emit_pitch_mating_pad(
        part,
        r,
        ctx,
        x=0.0,
        z=0.0,
        face_side="negative_y",
        name=name,
        pad_height_scale=1.08,
    )
    _emit_centered_pitch_hub(
        part,
        r,
        ctx,
        x=0.0,
        z=0.0,
        y_span=r.upper_width * 0.86 if y_span is None else y_span,
        name=centered_name,
        radius_scale=0.56,
        style=style,
        motif=motif,
    )


def _emit_upper_downstream_socket(
    part,
    r: ResolvedSerialElbowArmConfig,
    ctx: ModuleBuildContext,
    *,
    x: float,
    name: str,
    centered_name: str,
    style: str = "boxed_clevis",
    motif: str = "horizontal_slot",
) -> None:
    if r.axis_family == "planar_yaw":
        _box(
            part,
            (r.link_height * 1.05, r.link_height * 1.05, r.cheek_thickness),
            (x, 0.0, -r.cheek_thickness * 0.5),
            _mat(ctx, "cover"),
            name,
        )
        return

    _emit_pitch_mating_pad(
        part,
        r,
        ctx,
        x=x,
        z=0.0,
        face_side="positive_y",
        name=name,
        pad_height_scale=1.04,
    )
    _emit_centered_pitch_hub(
        part,
        r,
        ctx,
        x=x,
        z=0.0,
        y_span=r.forearm_width * 0.84,
        name=centered_name,
        radius_scale=0.48,
        style=style,
        motif=motif,
    )


def _emit_upper_interfaces(
    part, r: ResolvedSerialElbowArmConfig, ctx: ModuleBuildContext
) -> tuple[str, str]:
    upstream_name = "shoulder_yaw_hub" if r.axis_family == "planar_yaw" else "shoulder_pitch_hub"
    downstream_name = "elbow_yaw_socket" if r.axis_family == "planar_yaw" else "elbow_pitch_socket"
    _emit_upper_upstream_hub(
        part,
        r,
        ctx,
        name=upstream_name,
        centered_name="shoulder_centered_pitch_hub",
        style=_joint_style_for_index(r, 0),
        motif=_cap_motif_for_index(r, 0),
    )
    _emit_upper_downstream_socket(
        part,
        r,
        ctx,
        x=r.upper_len,
        name=downstream_name,
        centered_name="elbow_centered_pitch_socket",
        style=_joint_style_for_index(r, 1),
        motif=_cap_motif_for_index(r, 1),
    )
    return upstream_name, downstream_name


def _emit_elbow_yoke_details(
    part,
    r: ResolvedSerialElbowArmConfig,
    ctx: ModuleBuildContext,
    *,
    x: float | None = None,
    prefix: str = "elbow",
    style: str = "boxed_clevis",
) -> None:
    x = r.upper_len if x is None else x
    if r.axis_family == "planar_yaw":
        _cylinder(
            part,
            r.forearm_width * 0.58,
            0.014,
            (x, 0.0, 0.012),
            _mat(ctx, "bolt"),
            f"{prefix}_yaw_bearing",
        )
        return
    gap = r.forearm_width + 2.0 * r.bearing_clearance
    cheek_y = gap * 0.5 + r.cheek_thickness * 0.5
    _box(
        part,
        (
            r.link_height
            * (0.86 if style == "round_bearing" else 0.62 if style == "compact_ring" else 0.72),
            gap + 2.0 * r.cheek_thickness + 0.006,
            r.link_height * (0.12 if style == "split_plate" else 0.16),
        ),
        (x, 0.0, 0.0),
        _mat(ctx, "link"),
        f"{prefix}_cross_bridge",
    )
    for side, sign in (("left", -1.0), ("right", 1.0)):
        _emit_pitch_cheek(
            part,
            r,
            ctx,
            x=x,
            y=sign * cheek_y,
            z=0.0,
            prefix=prefix,
            side=side,
            style=style,
            width_scale=0.82,
            height_scale=1.32,
        )
        cover_radius = r.link_height * (
            0.48 if style == "round_bearing" else 0.30 if style == "compact_ring" else 0.38
        )
        _cylinder(
            part,
            cover_radius,
            r.cheek_thickness * 1.45,
            (x, sign * cheek_y, 0.0),
            _mat(ctx, "cover"),
            f"{prefix}_{side}_cover",
            rpy=(math.pi / 2.0, 0.0, 0.0),
        )
    if style == "split_plate":
        _box(
            part,
            (r.link_height * 0.70, gap + r.cheek_thickness, r.link_height * 0.10),
            (x, 0.0, r.link_height * 0.48),
            _mat(ctx, "accent"),
            f"{prefix}_upper_tie_plate",
        )
        _box(
            part,
            (r.link_height * 0.70, gap + r.cheek_thickness, r.link_height * 0.10),
            (x, 0.0, -r.link_height * 0.48),
            _mat(ctx, "accent"),
            f"{prefix}_lower_tie_plate",
        )
    elif style == "compact_ring":
        _cylinder(
            part,
            r.link_height * 0.42,
            gap + r.cheek_thickness * 1.3,
            (x, 0.0, 0.0),
            _mat(ctx, "accent"),
            f"{prefix}_compact_ring",
            rpy=(math.pi / 2.0, 0.0, 0.0),
        )


def _build_upper_box_beam_yoke(ctx: ModuleBuildContext) -> ModuleBuild:
    r: ResolvedSerialElbowArmConfig = ctx.config  # type: ignore[assignment]
    part = ctx.model.part("upper_link")
    upstream_name, downstream_name = _emit_upper_interfaces(part, r, ctx)
    _box(
        part,
        (r.upper_len + r.link_height * 0.55, r.upper_width * 0.66, r.link_height * 0.50),
        (r.upper_len * 0.5, 0.0, 0.0),
        _mat(ctx, "link"),
        "upper_box_beam",
    )
    _box(
        part,
        (r.upper_len * 0.70, r.upper_width * 0.72, r.link_height * 0.10),
        (r.upper_len * 0.52, 0.0, r.link_height * 0.30),
        _mat(ctx, "cover"),
        "upper_top_web",
    )
    _emit_elbow_yoke_details(part, r, ctx, style=_joint_style_for_index(r, 1))
    if r.has_cable_tube:
        _cylinder(
            part,
            r.link_height * 0.065,
            r.upper_len * 0.72,
            (r.upper_len * 0.52, -r.upper_width * 0.38, r.link_height * 0.35),
            _mat(ctx, "bolt"),
            "upper_cable_tube",
            rpy=(0.0, math.pi / 2.0, 0.0),
        )
    part.inertial = Inertial.from_geometry(
        Box((r.upper_len, r.upper_width, r.link_height)),
        mass=4.5,
        origin=Origin(xyz=(r.upper_len * 0.5, 0.0, 0.0)),
    )
    return ModuleBuild(
        "box_beam_yoke",
        ["upper_link"],
        interfaces={
            "upstream": _upper_upstream_interface(r, upstream_name),
            "downstream": _upper_downstream_interface(r, downstream_name),
        },
    )


def _build_upper_open_plate_yoke(ctx: ModuleBuildContext) -> ModuleBuild:
    r: ResolvedSerialElbowArmConfig = ctx.config  # type: ignore[assignment]
    part = ctx.model.part("upper_link")
    upstream_name, downstream_name = _emit_upper_interfaces(part, r, ctx)
    for side, sign in (("left", -1.0), ("right", 1.0)):
        _box(
            part,
            (r.upper_len + r.link_height * 0.42, r.upper_width * 0.18, r.link_height * 0.46),
            (r.upper_len * 0.5, sign * r.upper_width * 0.30, 0.0),
            _mat(ctx, "link"),
            f"upper_{side}_side_plate",
        )
    _box(
        part,
        (r.upper_len * 0.78, r.upper_width * 0.56, r.link_height * 0.22),
        (r.upper_len * 0.50, 0.0, r.link_height * 0.08),
        _mat(ctx, "cover"),
        "upper_window_top_bridge",
    )
    _box(
        part,
        (r.upper_len * 0.62, r.upper_width * 0.44, r.link_height * 0.18),
        (r.upper_len * 0.52, 0.0, -r.link_height * 0.06),
        _mat(ctx, "cover"),
        "upper_window_bottom_bridge",
    )
    _emit_elbow_yoke_details(part, r, ctx, style=_joint_style_for_index(r, 1))
    part.inertial = Inertial.from_geometry(
        Box((r.upper_len, r.upper_width, r.link_height)),
        mass=4.0,
        origin=Origin(xyz=(r.upper_len * 0.5, 0.0, 0.0)),
    )
    return ModuleBuild(
        "open_plate_yoke",
        ["upper_link"],
        interfaces={
            "upstream": _upper_upstream_interface(r, upstream_name),
            "downstream": _upper_downstream_interface(r, downstream_name),
        },
    )


def _build_upper_dual_parallel_yoke(ctx: ModuleBuildContext) -> ModuleBuild:
    r: ResolvedSerialElbowArmConfig = ctx.config  # type: ignore[assignment]
    part = ctx.model.part("upper_link")
    upstream_name, downstream_name = _emit_upper_interfaces(part, r, ctx)
    for side, sign in (("left", -1.0), ("right", 1.0)):
        _box(
            part,
            (r.upper_len + r.link_height * 0.38, r.upper_width * 0.22, r.link_height * 0.34),
            (r.upper_len * 0.5, sign * r.upper_width * 0.36, 0.0),
            _mat(ctx, "link"),
            f"upper_{side}_parallel_bar",
        )
    _box(
        part,
        (r.upper_len * 0.32, r.upper_width * 0.82, r.link_height * 0.20),
        (r.upper_len * 0.22, 0.0, r.link_height * 0.08),
        _mat(ctx, "accent"),
        "upper_proximal_tie_plate",
    )
    _box(
        part,
        (r.upper_len * 0.34, r.upper_width * 0.82, r.link_height * 0.20),
        (r.upper_len * 0.74, 0.0, r.link_height * 0.08),
        _mat(ctx, "accent"),
        "upper_distal_tie_plate",
    )
    _emit_elbow_yoke_details(part, r, ctx, style=_joint_style_for_index(r, 1))
    part.inertial = Inertial.from_geometry(
        Box((r.upper_len, r.upper_width, r.link_height)),
        mass=4.2,
        origin=Origin(xyz=(r.upper_len * 0.5, 0.0, 0.0)),
    )
    return ModuleBuild(
        "dual_parallel_yoke",
        ["upper_link"],
        interfaces={
            "upstream": _upper_upstream_interface(r, upstream_name),
            "downstream": _upper_downstream_interface(r, downstream_name),
        },
    )


def _emit_multi_segment_beam(
    part,
    r: ResolvedSerialElbowArmConfig,
    ctx: ModuleBuildContext,
    *,
    length: float,
    prefix: str,
    style: Literal["box", "open", "parallel"],
) -> None:
    if style == "parallel":
        for side, sign in (("left", -1.0), ("right", 1.0)):
            _box(
                part,
                (length + r.link_height * 0.28, r.upper_width * 0.18, r.link_height * 0.34),
                (length * 0.5, sign * r.upper_width * 0.34, 0.0),
                _mat(ctx, "link"),
                f"{prefix}_{side}_parallel_bar",
            )
    elif style == "open":
        for side, sign in (("left", -1.0), ("right", 1.0)):
            _box(
                part,
                (length + r.link_height * 0.30, r.upper_width * 0.16, r.link_height * 0.42),
                (length * 0.5, sign * r.upper_width * 0.28, 0.0),
                _mat(ctx, "link"),
                f"{prefix}_{side}_side_plate",
            )
        _box(
            part,
            (length * 0.70, r.upper_width * 0.50, r.link_height * 0.18),
            (length * 0.50, 0.0, r.link_height * 0.10),
            _mat(ctx, "cover"),
            f"{prefix}_top_bridge",
        )
    else:
        _box(
            part,
            (length + r.link_height * 0.36, r.upper_width * 0.58, r.link_height * 0.44),
            (length * 0.5, 0.0, 0.0),
            _mat(ctx, "link"),
            f"{prefix}_box_beam",
        )
        _box(
            part,
            (length * 0.66, r.upper_width * 0.66, r.link_height * 0.09),
            (length * 0.52, 0.0, r.link_height * 0.25),
            _mat(ctx, "cover"),
            f"{prefix}_top_web",
        )


def _build_multi_dof_upper_yoke(
    ctx: ModuleBuildContext,
    *,
    dof: int,
    module_name: str,
    style: Literal["box", "open", "parallel"],
) -> ModuleBuild:
    r: ResolvedSerialElbowArmConfig = ctx.config  # type: ignore[assignment]
    model = ctx.model
    segment_count = dof - 1
    segment_len = r.upper_len / segment_count
    parts = []
    part_names: list[str] = []

    for idx in range(segment_count):
        part_name = "upper_link" if idx == 0 else f"serial_mid_link_{idx}"
        part = model.part(part_name)
        part_names.append(part_name)
        parts.append(part)

        if idx == 0:
            upstream_name = (
                "shoulder_yaw_hub" if r.axis_family == "planar_yaw" else "shoulder_pitch_hub"
            )
            centered_upstream = "shoulder_centered_pitch_hub"
            hub_y_span = r.upper_width * 0.86
        else:
            upstream_name = (
                f"serial_internal_yaw_hub_{idx}"
                if r.axis_family == "planar_yaw"
                else f"serial_internal_pitch_hub_{idx}"
            )
            centered_upstream = f"serial_mid_{idx}_centered_pitch_hub"
            hub_y_span = r.forearm_width * 0.86
        _emit_upper_upstream_hub(
            part,
            r,
            ctx,
            name=upstream_name,
            centered_name=centered_upstream,
            y_span=hub_y_span,
            style=_joint_style_for_index(r, idx),
            motif=_cap_motif_for_index(r, idx),
        )

        is_terminal = idx == segment_count - 1
        downstream_name = (
            ("elbow_yaw_socket" if r.axis_family == "planar_yaw" else "elbow_pitch_socket")
            if is_terminal
            else (
                f"serial_internal_yaw_socket_{idx + 1}"
                if r.axis_family == "planar_yaw"
                else f"serial_internal_pitch_socket_{idx + 1}"
            )
        )
        centered_downstream = (
            "elbow_centered_pitch_socket"
            if is_terminal
            else f"serial_joint_{idx + 1}_centered_pitch_socket"
        )
        _emit_upper_downstream_socket(
            part,
            r,
            ctx,
            x=segment_len,
            name=downstream_name,
            centered_name=centered_downstream,
            style=_joint_style_for_index(r, idx + 1),
            motif=_cap_motif_for_index(r, idx + 1),
        )
        _emit_multi_segment_beam(
            part,
            r,
            ctx,
            length=segment_len,
            prefix="upper_link" if idx == 0 else f"serial_mid_{idx}",
            style=style,
        )
        _emit_elbow_yoke_details(
            part,
            r,
            ctx,
            x=segment_len,
            prefix="elbow" if is_terminal else f"serial_joint_{idx + 1}",
            style=_joint_style_for_index(r, idx + 1),
        )
        if r.has_cable_tube and idx == 0:
            _cylinder(
                part,
                r.link_height * 0.055,
                segment_len * 0.68,
                (segment_len * 0.52, -r.upper_width * 0.26, r.link_height * 0.22),
                _mat(ctx, "bolt"),
                "upper_cable_tube",
                rpy=(0.0, math.pi / 2.0, 0.0),
            )
        part.inertial = Inertial.from_geometry(
            Box((segment_len, r.upper_width, r.link_height)),
            mass=max(1.0, 4.3 / segment_count),
            origin=Origin(xyz=(segment_len * 0.5, 0.0, 0.0)),
        )

    internal_joints: list[str] = []
    face_axis = "z" if r.axis_family == "planar_yaw" else "y"
    for idx in range(segment_count - 1):
        parent = parts[idx]
        child = parts[idx + 1]
        joint_name = f"serial_mid_{'yaw' if r.axis_family == 'planar_yaw' else 'pitch'}_{idx + 1}"
        parent_socket = (
            f"serial_internal_{face_axis}aw_socket_{idx + 1}"
            if face_axis == "y"
            else f"serial_internal_yaw_socket_{idx + 1}"
        )
        child_hub = (
            f"serial_internal_{face_axis}aw_hub_{idx + 1}"
            if face_axis == "y"
            else f"serial_internal_yaw_hub_{idx + 1}"
        )
        if r.axis_family != "planar_yaw":
            parent_socket = f"serial_internal_pitch_socket_{idx + 1}"
            child_hub = f"serial_internal_pitch_hub_{idx + 1}"
        model.articulation(
            joint_name,
            ArticulationType.REVOLUTE,
            parent=parent,
            child=child,
            origin=Origin(xyz=(segment_len, 0.0, 0.0)),
            axis=r.elbow_axis,
            motion_limits=_motion_limits(r.elbow_limit, effort=48.0, velocity=1.6),
            motion_properties=MotionProperties(damping=0.28, friction=0.14),
            mating=MatingContract(
                parent_face_geometry=parent_socket,
                parent_face_side="positive_z" if r.axis_family == "planar_yaw" else "positive_y",
                child_face_geometry=child_hub,
                child_face_side="negative_z" if r.axis_family == "planar_yaw" else "negative_y",
                contact_tol=0.003,
            ),
        )
        internal_joints.append(joint_name)

    upstream_name = "shoulder_yaw_hub" if r.axis_family == "planar_yaw" else "shoulder_pitch_hub"
    downstream_name = "elbow_yaw_socket" if r.axis_family == "planar_yaw" else "elbow_pitch_socket"
    terminal_part = part_names[-1]
    return ModuleBuild(
        module_name,
        part_names,
        internal_articulations=internal_joints,
        interfaces={
            "upstream": _upper_upstream_interface(r, upstream_name),
            "downstream": _upper_downstream_interface(
                r,
                downstream_name,
                part_name=terminal_part,
                anchor_x=segment_len,
            ),
        },
    )


def _build_upper_triple_segment_yoke(ctx: ModuleBuildContext) -> ModuleBuild:
    return _build_multi_dof_upper_yoke(ctx, dof=3, module_name="triple_segment_yoke", style="box")


def _build_upper_quad_segment_yoke(ctx: ModuleBuildContext) -> ModuleBuild:
    return _build_multi_dof_upper_yoke(ctx, dof=4, module_name="quad_segment_yoke", style="open")


def _build_upper_five_dof_yoke(ctx: ModuleBuildContext) -> ModuleBuild:
    return _build_multi_dof_upper_yoke(ctx, dof=5, module_name="five_dof_yoke", style="parallel")


def _build_upper_six_dof_yoke(ctx: ModuleBuildContext) -> ModuleBuild:
    return _build_multi_dof_upper_yoke(ctx, dof=6, module_name="six_dof_yoke", style="box")


def _build_upper_seven_dof_yoke(ctx: ModuleBuildContext) -> ModuleBuild:
    return _build_multi_dof_upper_yoke(ctx, dof=7, module_name="seven_dof_yoke", style="open")


def _emit_forearm_upstream(
    part,
    r: ResolvedSerialElbowArmConfig,
    ctx: ModuleBuildContext,
    *,
    style: str,
    motif: str,
) -> str:
    if r.axis_family == "planar_yaw":
        name = "elbow_yaw_hub"
        _box(
            part,
            (r.link_height, r.link_height, r.link_height * 0.44),
            (0.0, 0.0, r.link_height * 0.22),
            _mat(ctx, "cover"),
            name,
        )
    else:
        name = "elbow_pitch_hub"
        _emit_pitch_mating_pad(
            part,
            r,
            ctx,
            x=0.0,
            z=0.0,
            face_side="negative_y",
            name=name,
            pad_height_scale=0.98,
        )
        _emit_centered_pitch_hub(
            part,
            r,
            ctx,
            x=0.0,
            z=0.0,
            y_span=r.forearm_width * 0.86,
            name="forearm_centered_pitch_hub",
            radius_scale=0.48,
            style=style,
            motif=motif,
        )
    return name


def _emit_forearm_beam(
    part, r: ResolvedSerialElbowArmConfig, ctx: ModuleBuildContext, *, plate_style: bool
) -> None:
    if plate_style:
        for side, sign in (("left", -1.0), ("right", 1.0)):
            _box(
                part,
                (
                    r.forearm_len + r.link_height * 0.35,
                    r.forearm_width * 0.20,
                    r.link_height * 0.42,
                ),
                (r.forearm_len * 0.5, sign * r.forearm_width * 0.30, 0.0),
                _mat(ctx, "link"),
                f"forearm_{side}_side_plate",
            )
        _box(
            part,
            (r.forearm_len * 0.68, r.forearm_width * 0.52, r.link_height * 0.22),
            (r.forearm_len * 0.54, 0.0, r.link_height * 0.08),
            _mat(ctx, "cover"),
            "forearm_top_bridge",
        )
    else:
        _box(
            part,
            (r.forearm_len + r.link_height * 0.42, r.forearm_width * 0.60, r.link_height * 0.44),
            (r.forearm_len * 0.5, 0.0, 0.0),
            _mat(ctx, "link"),
            "forearm_main_beam",
        )


def _emit_tool_flange(part, r: ResolvedSerialElbowArmConfig, ctx: ModuleBuildContext) -> None:
    _box(
        part,
        (0.020, r.forearm_width * 0.92, r.link_height * 0.86),
        (r.forearm_len, 0.0, 0.0),
        _mat(ctx, "cover"),
        "tool_mount_plate",
    )
    _cylinder(
        part,
        r.forearm_width * 0.42,
        0.016,
        (r.forearm_len + 0.018, 0.0, 0.0),
        _mat(ctx, "cover"),
        "round_tool_flange",
        rpy=(0.0, math.pi / 2.0, 0.0),
    )


def _build_forearm_flange(ctx: ModuleBuildContext) -> ModuleBuild:
    r: ResolvedSerialElbowArmConfig = ctx.config  # type: ignore[assignment]
    part = ctx.model.part("forearm")
    upstream_name = _emit_forearm_upstream(
        part,
        r,
        ctx,
        style=_joint_style_for_index(r, _upper_segment_count(r.upper_module)),
        motif=_cap_motif_for_index(r, _upper_segment_count(r.upper_module)),
    )
    _emit_forearm_beam(part, r, ctx, plate_style=False)
    _emit_tool_flange(part, r, ctx)
    part.inertial = Inertial.from_geometry(
        Box((r.forearm_len, r.forearm_width, r.link_height)),
        mass=2.8,
        origin=Origin(xyz=(r.forearm_len * 0.5, 0.0, 0.0)),
    )
    return ModuleBuild(
        "flange_forearm",
        ["forearm"],
        interfaces={"upstream": _forearm_upstream_interface(r, upstream_name)},
    )


def _build_forearm_pad_plate(ctx: ModuleBuildContext) -> ModuleBuild:
    r: ResolvedSerialElbowArmConfig = ctx.config  # type: ignore[assignment]
    part = ctx.model.part("forearm")
    upstream_name = _emit_forearm_upstream(
        part,
        r,
        ctx,
        style=_joint_style_for_index(r, _upper_segment_count(r.upper_module)),
        motif=_cap_motif_for_index(r, _upper_segment_count(r.upper_module)),
    )
    _emit_forearm_beam(part, r, ctx, plate_style=True)
    _box(
        part,
        (0.026, r.forearm_width * 1.18, r.link_height * 1.08),
        (r.forearm_len, 0.0, 0.0),
        _mat(ctx, "cover"),
        "rectangular_tool_pad",
    )
    for i, z in enumerate((-0.28, 0.28)):
        _cylinder(
            part,
            0.0045,
            0.006,
            (r.forearm_len + 0.016, 0.0, z * r.link_height),
            _mat(ctx, "bolt"),
            f"pad_bolt_{i}",
            rpy=(0.0, math.pi / 2.0, 0.0),
        )
    part.inertial = Inertial.from_geometry(
        Box((r.forearm_len, r.forearm_width, r.link_height)),
        mass=2.6,
        origin=Origin(xyz=(r.forearm_len * 0.5, 0.0, 0.0)),
    )
    return ModuleBuild(
        "pad_plate_forearm",
        ["forearm"],
        interfaces={"upstream": _forearm_upstream_interface(r, upstream_name)},
    )


def _build_forearm_suction_tool(ctx: ModuleBuildContext) -> ModuleBuild:
    r: ResolvedSerialElbowArmConfig = ctx.config  # type: ignore[assignment]
    part = ctx.model.part("forearm")
    upstream_name = _emit_forearm_upstream(
        part,
        r,
        ctx,
        style=_joint_style_for_index(r, _upper_segment_count(r.upper_module)),
        motif=_cap_motif_for_index(r, _upper_segment_count(r.upper_module)),
    )
    _emit_forearm_beam(part, r, ctx, plate_style=False)
    _box(
        part,
        (0.018, r.forearm_width * 0.82, r.link_height * 0.72),
        (r.forearm_len, 0.0, 0.0),
        _mat(ctx, "cover"),
        "tool_mount_plate",
    )
    _cylinder(
        part,
        r.link_height * 0.08,
        r.tool_offset,
        (r.forearm_len + r.tool_offset * 0.5, 0.0, -r.link_height * 0.30),
        _mat(ctx, "bolt"),
        "vacuum_tube",
        rpy=(0.0, math.pi / 2.0, 0.0),
    )
    _cylinder(
        part,
        r.forearm_width * 0.30,
        0.024,
        (r.forearm_len + r.tool_offset, 0.0, -r.link_height * 0.30),
        _mat(ctx, "rubber"),
        "suction_cup",
        rpy=(0.0, math.pi / 2.0, 0.0),
    )
    part.inertial = Inertial.from_geometry(
        Box((r.forearm_len + r.tool_offset, r.forearm_width, r.link_height)),
        mass=2.7,
        origin=Origin(xyz=(r.forearm_len * 0.5, 0.0, 0.0)),
    )
    return ModuleBuild(
        "suction_tool_forearm",
        ["forearm"],
        interfaces={"upstream": _forearm_upstream_interface(r, upstream_name)},
    )


BASE_FACTORIES = {
    "pedestal_yoke": _build_base_pedestal_yoke,
    "root_fork": _build_base_root_fork,
    "controller_yaw_base": _build_base_controller_yaw,
}
UPPER_FACTORIES = {
    "box_beam_yoke": _build_upper_box_beam_yoke,
    "open_plate_yoke": _build_upper_open_plate_yoke,
    "dual_parallel_yoke": _build_upper_dual_parallel_yoke,
    "triple_segment_yoke": _build_upper_triple_segment_yoke,
    "quad_segment_yoke": _build_upper_quad_segment_yoke,
    "five_dof_yoke": _build_upper_five_dof_yoke,
    "six_dof_yoke": _build_upper_six_dof_yoke,
    "seven_dof_yoke": _build_upper_seven_dof_yoke,
}
FOREARM_FACTORIES = {
    "flange_forearm": _build_forearm_flange,
    "pad_plate_forearm": _build_forearm_pad_plate,
    "suction_tool_forearm": _build_forearm_suction_tool,
}


def _slots_for_config(r: ResolvedSerialElbowArmConfig) -> list[SlotSpec]:
    return [
        SlotSpec("base", BASE_FACTORIES, r.base_module),
        SlotSpec("upper_link", UPPER_FACTORIES, r.upper_module),
        SlotSpec("forearm", FOREARM_FACTORIES, r.forearm_module),
    ]


def _rename_assembled_joints(model: ArticulatedObject, r: ResolvedSerialElbowArmConfig) -> None:
    shoulder = model.get_articulation("base_to_upper_link")
    elbow = model.get_articulation("upper_link_to_forearm")
    shoulder_name = "shoulder_yaw" if r.axis_family == "planar_yaw" else "shoulder_pitch"
    elbow_name = "elbow_yaw" if r.axis_family == "planar_yaw" else "elbow_pitch"
    del model._articulation_index[shoulder.name]
    del model._articulation_index[elbow.name]
    shoulder.name = shoulder_name
    elbow.name = elbow_name
    shoulder.meta.update(
        {
            "source_id": "S12" if r.axis_family == "planar_yaw" else "S3/S6/S9",
            "upper_len": r.upper_len,
        }
    )
    elbow.meta.update(
        {
            "source_id": "S12" if r.axis_family == "planar_yaw" else "S3/S6/S9",
            "forearm_len": r.forearm_len,
        }
    )
    model._articulation_index[shoulder.name] = shoulder
    model._articulation_index[elbow.name] = elbow


def build_serial_elbow_arm(
    config: SerialElbowArmConfig | None = None, *, assets: AssetContext | None = None
) -> ArticulatedObject:
    r = resolve_config(config)
    model = ArticulatedObject(name=r.name, assets=assets)
    for name, rgba in r.palette.items():
        model.material(f"serial_arm_{name}", rgba=rgba)

    assemble(
        model,
        slots=_slots_for_config(r),
        rng=random.Random(0),
        palette=r.palette,
        config=r,
        seed=0,
    )
    _rename_assembled_joints(model, r)
    model.meta["slot_choices"] = slot_choices_for_config(r)
    return model


def build_seeded_serial_elbow_arm(
    seed: int, *, assets: AssetContext | None = None
) -> ArticulatedObject:
    return build_serial_elbow_arm(config_from_seed(seed), assets=assets)


def slot_choices_for_config(config: ResolvedSerialElbowArmConfig) -> list[tuple[str, str]]:
    return [
        ("base", config.base_module),
        ("upper_link", config.upper_module),
        ("forearm", config.forearm_module),
    ]


def slot_choices_for_seed(seed: int) -> list[tuple[str, str]]:
    return slot_choices_for_config(resolve_config(config_from_seed(seed)))


def run_serial_elbow_arm_tests(
    object_model: ArticulatedObject, config: SerialElbowArmConfig | None = None
) -> TestReport:
    r = resolve_config(config)
    ctx = TestContext(object_model)
    ctx.check_model_valid()
    ctx.fail_if_isolated_parts()

    base = object_model.get_part("base")
    upper_link = object_model.get_part("upper_link")
    forearm = object_model.get_part("forearm")
    ctx.allow_overlap(
        base,
        upper_link,
        reason="captured shoulder pivot hub sits inside the base yoke/bearing envelope",
    )

    segment_count = _upper_segment_count(r.upper_module)
    upper_chain = ["upper_link"] + [f"serial_mid_link_{idx}" for idx in range(1, segment_count)]
    for parent_name, child_name in zip(upper_chain, upper_chain[1:]):
        ctx.allow_overlap(
            object_model.get_part(parent_name),
            object_model.get_part(child_name),
            reason=f"captured serial pivot hub sits inside the {parent_name} yoke envelope",
        )
    ctx.allow_overlap(
        object_model.get_part(upper_chain[-1]),
        forearm,
        reason="captured elbow pivot hub sits inside the terminal upper-link yoke envelope",
    )

    part_names = {part.name for part in object_model.parts}
    ctx.check(
        "identity_parts",
        {"base", "upper_link", "forearm"}.issubset(part_names),
        details=str(sorted(part_names)),
    )

    shoulder_name = "shoulder_yaw" if r.axis_family == "planar_yaw" else "shoulder_pitch"
    elbow_name = "elbow_yaw" if r.axis_family == "planar_yaw" else "elbow_pitch"
    shoulder = object_model.get_articulation(shoulder_name)
    elbow = object_model.get_articulation(elbow_name)
    revolute_count = sum(
        1
        for joint in object_model.articulations
        if joint.articulation_type == ArticulationType.REVOLUTE
    )
    expected_revolute_count = _upper_segment_count(r.upper_module) + 1
    ctx.check(
        "expected_revolute_joint_count",
        revolute_count == expected_revolute_count,
        details=f"found {revolute_count}, expected {expected_revolute_count}",
    )
    ctx.check(
        "shoulder_parent_child",
        shoulder.parent == "base" and shoulder.child == "upper_link",
        details=f"{shoulder.parent}->{shoulder.child}",
    )
    ctx.check(
        "elbow_parent_child",
        elbow.parent == _upper_terminal_part_name(r) and elbow.child == "forearm",
        details=f"{elbow.parent}->{elbow.child}",
    )
    ctx.check("shoulder_axis", tuple(shoulder.axis) == r.shoulder_axis, details=str(shoulder.axis))
    ctx.check("elbow_axis", tuple(elbow.axis) == r.elbow_axis, details=str(elbow.axis))
    ctx.check(
        "axis_family_consistent",
        tuple(shoulder.axis) == tuple(elbow.axis),
        details=f"{shoulder.axis} {elbow.axis}",
    )
    ctx.check(
        "shoulder_origin",
        abs(shoulder.origin.xyz[2] - r.shoulder_z) < 1e-9,
        details=str(shoulder.origin.xyz),
    )
    ctx.check(
        "elbow_origin",
        abs(elbow.origin.xyz[0] - _upper_terminal_anchor_x(r)) < 1e-9,
        details=str(elbow.origin.xyz),
    )
    ctx.check(
        "link_lengths_positive",
        r.upper_len >= 0.16 and r.forearm_len >= 0.14,
        details=f"{r.upper_len} {r.forearm_len}",
    )
    return ctx.report()


__all__ = [
    "__modular__",
    "SerialElbowArmConfig",
    "ResolvedSerialElbowArmConfig",
    "SOURCE_IDS",
    "SOURCE_ADAPTATION_MAP",
    "config_from_seed",
    "resolve_config",
    "build_serial_elbow_arm",
    "build_seeded_serial_elbow_arm",
    "slot_choices_for_seed",
    "run_serial_elbow_arm_tests",
]
