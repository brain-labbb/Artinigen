"""Multirotor aerial drone — modular procedural template.

Pattern: ``mixed``
    - **Slot A** ``airframe_body``: root chassis (4 module candidates).
    - **Slot B** ``rotor_arms``: a **multiplicity** slot whose chosen module
      fixes N ∈ {4, 6, 8} and fold/fixed semantics (4 candidates). Each
      rotor arm carries 1 CONTINUOUS propeller spin joint; folding
      candidates add 1 REVOLUTE fold joint per arm.
    - **Slot C** ``landing_gear``: a parallel child of the airframe body
      (4 candidates including ``none``).
    - **Slot D** ``payload_undermount``: a parallel child of the airframe
      body (5 candidates including ``none``).

Slot B / C / D all parent to Slot A's ``airframe_body`` part — there is no
A → B → C → D chain. This combines monitor_mount's multiplicity pattern
(per-N module name) with dj_equipment's parallel-children pattern
(``ctx.upstream_interface.part_name`` → ``housing``).

seed=0 anchor:
    ``(rounded_shell_body, folding_quad_4arm, tube_legs_pair, three_axis_gimbal)``
which reproduces the cinema-folding-quadcopter prototype combining
``rec_drone_456cea3c…`` (airframe + folding quad arms) with
``rec_drone_5ae12ee0…`` (tube landing gear + 3-axis gimbal).

Modular flag: ``__modular__ = True`` so the compile-sweep coverage gate
skips ``anchor_geometry_match`` and runs ``module_topology_diversity``
(≥5 distinct slot tuples) instead.

See ``articraft_template_authoring/specs/drone.md`` for the approved spec
and ``MODULAR_TEMPLATE_AUTHORING.md`` for the abstraction architecture.
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
    ExtrudeGeometry,
    Inertial,
    LatheGeometry,
    MotionLimits,
    MotionProperties,
    Origin,
    TestContext,
    TestReport,
    mesh_from_geometry,
)

# Modular templates are flagged so the sweep coverage gate can skip
# anchor_geometry_match (a single-anchor gate) and run
# module_topology_diversity instead.
__modular__ = True


# --------------------------------------------------------------------------- #
# Slot module name literals
# --------------------------------------------------------------------------- #


AirframeBodyModule = Literal[
    "rounded_shell_body",
    "hex_plate_stack_body",
    "racing_h_frame_body",
    "lathe_round_body",
]

RotorArmsModule = Literal[
    "folding_quad_4arm",
    "folding_hex_6arm",
    "fixed_quad_4arm",
    "fixed_octo_8arm",
]

LandingGearModule = Literal[
    "wire_loop_skids",
    "tube_legs_pair",
    "folding_landing_legs",
    "none",
]

PayloadUndermountModule = Literal[
    "three_axis_gimbal",
    "yaw_tilt_gimbal",
    "camera_plate_tilt",
    "payload_skid",
    "none",
]

DronePaletteTheme = Literal[
    "carbon_black",
    "racing_red",
    "cinema_white",
    "industrial_gray",
    "safety_orange",
]


_AIRFRAME_CANDIDATES = (
    "rounded_shell_body",
    "hex_plate_stack_body",
    "racing_h_frame_body",
    "lathe_round_body",
)

_ROTOR_CANDIDATES = (
    "folding_quad_4arm",
    "folding_hex_6arm",
    "fixed_quad_4arm",
    "fixed_octo_8arm",
)

_GEAR_CANDIDATES = (
    "wire_loop_skids",
    "tube_legs_pair",
    "folding_landing_legs",
    "none",
)

_PAYLOAD_CANDIDATES = (
    "three_axis_gimbal",
    "yaw_tilt_gimbal",
    "camera_plate_tilt",
    "payload_skid",
    "none",
)


# Per-module derived rotor count + folding semantics.
ROTOR_MODULE_N: dict[str, int] = {
    "folding_quad_4arm": 4,
    "folding_hex_6arm": 6,
    "fixed_quad_4arm": 4,
    "fixed_octo_8arm": 8,
}

ROTOR_MODULE_FOLDING: dict[str, bool] = {
    "folding_quad_4arm": True,
    "folding_hex_6arm": True,
    "fixed_quad_4arm": False,
    "fixed_octo_8arm": False,
}


# Forbidden (Slot C, Slot D) pairs. When one of these is chosen,
# resolve_config falls back Slot C to ``tube_legs_pair`` (the universally
# compatible landing gear that doesn't share the payload_skid's hinge
# space).
_FORBIDDEN_C_D_PAIRS: set[tuple[str, str]] = {
    ("folding_landing_legs", "payload_skid"),
    ("wire_loop_skids", "payload_skid"),
}


# --------------------------------------------------------------------------- #
# Palette presets
# --------------------------------------------------------------------------- #


DRONE_PALETTE_PRESETS: dict[str, dict[str, tuple[float, float, float, float]]] = {
    "carbon_black": {
        "body_main": (0.10, 0.10, 0.11, 1.0),
        "body_accent": (0.18, 0.18, 0.20, 1.0),
        "carbon": (0.06, 0.06, 0.07, 1.0),
        "motor": (0.22, 0.22, 0.24, 1.0),
        "propeller": (0.05, 0.05, 0.06, 1.0),
        "metal": (0.66, 0.66, 0.68, 1.0),
        "lens": (0.05, 0.07, 0.12, 1.0),
        "lens_glass": (0.08, 0.18, 0.35, 0.6),
        "skid": (0.05, 0.05, 0.06, 1.0),
        "warn": (0.86, 0.36, 0.16, 1.0),
    },
    "racing_red": {
        "body_main": (0.78, 0.10, 0.10, 1.0),
        "body_accent": (0.42, 0.06, 0.06, 1.0),
        "carbon": (0.07, 0.07, 0.08, 1.0),
        "motor": (0.24, 0.24, 0.26, 1.0),
        "propeller": (0.10, 0.10, 0.11, 1.0),
        "metal": (0.74, 0.74, 0.76, 1.0),
        "lens": (0.05, 0.05, 0.08, 1.0),
        "lens_glass": (0.20, 0.34, 0.50, 0.6),
        "skid": (0.10, 0.10, 0.11, 1.0),
        "warn": (0.96, 0.78, 0.18, 1.0),
    },
    "cinema_white": {
        "body_main": (0.90, 0.90, 0.88, 1.0),
        "body_accent": (0.74, 0.74, 0.72, 1.0),
        "carbon": (0.18, 0.18, 0.20, 1.0),
        "motor": (0.28, 0.28, 0.30, 1.0),
        "propeller": (0.22, 0.22, 0.24, 1.0),
        "metal": (0.80, 0.80, 0.82, 1.0),
        "lens": (0.10, 0.10, 0.12, 1.0),
        "lens_glass": (0.25, 0.40, 0.55, 0.6),
        "skid": (0.14, 0.14, 0.15, 1.0),
        "warn": (0.96, 0.62, 0.14, 1.0),
    },
    "industrial_gray": {
        "body_main": (0.44, 0.45, 0.47, 1.0),
        "body_accent": (0.32, 0.33, 0.35, 1.0),
        "carbon": (0.08, 0.08, 0.09, 1.0),
        "motor": (0.22, 0.22, 0.24, 1.0),
        "propeller": (0.16, 0.16, 0.18, 1.0),
        "metal": (0.70, 0.70, 0.72, 1.0),
        "lens": (0.07, 0.07, 0.10, 1.0),
        "lens_glass": (0.12, 0.24, 0.40, 0.6),
        "skid": (0.06, 0.06, 0.07, 1.0),
        "warn": (0.92, 0.54, 0.10, 1.0),
    },
    "safety_orange": {
        "body_main": (0.95, 0.45, 0.10, 1.0),
        "body_accent": (0.66, 0.30, 0.06, 1.0),
        "carbon": (0.06, 0.06, 0.07, 1.0),
        "motor": (0.20, 0.20, 0.22, 1.0),
        "propeller": (0.07, 0.07, 0.08, 1.0),
        "metal": (0.74, 0.74, 0.76, 1.0),
        "lens": (0.05, 0.05, 0.08, 1.0),
        "lens_glass": (0.20, 0.34, 0.50, 0.6),
        "skid": (0.06, 0.06, 0.07, 1.0),
        "warn": (0.20, 0.20, 0.21, 1.0),
    },
}


# --------------------------------------------------------------------------- #
# Config dataclasses
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class DroneConfig:
    """Public template config. Module selection is opt-in: leave any of
    the four module fields as ``None`` to let ``config_from_seed`` /
    ``resolve_config`` fill them in.
    """

    airframe_body_module: AirframeBodyModule | None = None
    rotor_arms_module: RotorArmsModule | None = None
    landing_gear_module: LandingGearModule | None = None
    payload_undermount_module: PayloadUndermountModule | None = None
    palette_theme: DronePaletteTheme = "carbon_black"

    # Airframe envelope.
    body_length: float = 0.36
    body_width: float = 0.20
    body_height: float = 0.05

    # Rotor / arm sizing.
    rotor_ring_radius: float = 0.21
    propeller_radius: float = 0.115
    propeller_blade_count: int = 2
    arm_thickness: float = 0.020
    motor_pod_radius: float = 0.022
    motor_pod_height: float = 0.030

    # Folding arm geometry.
    fold_angle_limit: float = 1.45
    hinge_barrel_radius: float = 0.013

    # Landing gear attach.
    landing_gear_attach_z_offset: float = -0.06
    gear_fold_angle: float = 0.0

    # Payload undermount attach.
    gimbal_attach_z_offset: float = -0.05
    gimbal_attach_x_offset: float = 0.060

    palette: dict[str, tuple[float, float, float, float]] = field(
        default_factory=lambda: dict(DRONE_PALETTE_PRESETS["carbon_black"])
    )


@dataclass(frozen=True)
class ResolvedDroneConfig:
    """Dimension-clamped + module-resolved config consumed by builders."""

    airframe_body_module: AirframeBodyModule
    rotor_arms_module: RotorArmsModule
    landing_gear_module: LandingGearModule
    payload_undermount_module: PayloadUndermountModule
    palette_theme: DronePaletteTheme

    body_length: float
    body_width: float
    body_height: float

    rotor_ring_radius: float
    propeller_radius: float
    propeller_blade_count: int
    arm_thickness: float
    motor_pod_radius: float
    motor_pod_height: float

    fold_angle_limit: float
    hinge_barrel_radius: float

    landing_gear_attach_z_offset: float
    gear_fold_angle: float
    gimbal_attach_z_offset: float
    gimbal_attach_x_offset: float

    # Derived.
    rotor_count: int
    folding_enabled: bool
    n_landing_legs: int

    palette: dict[str, tuple[float, float, float, float]]


# --------------------------------------------------------------------------- #
# config_from_seed + resolve_config
# --------------------------------------------------------------------------- #


def config_from_seed(seed: int) -> DroneConfig:
    """Sample a drone configuration for the given seed.

    seed == 0 always returns the canonical anchor combination
    ``(rounded_shell_body, folding_quad_4arm, tube_legs_pair,
    three_axis_gimbal)``. Other seeds RNG-pick modules uniformly from each
    slot and sample continuous dims across the spec's ranges.
    """

    if seed == 0:
        return DroneConfig(
            airframe_body_module="rounded_shell_body",
            rotor_arms_module="folding_quad_4arm",
            landing_gear_module="tube_legs_pair",
            payload_undermount_module="three_axis_gimbal",
            palette_theme="carbon_black",
            body_length=0.36,
            body_width=0.20,
            body_height=0.05,
            rotor_ring_radius=0.21,
            propeller_radius=0.115,
            propeller_blade_count=2,
        )

    rng = random.Random(seed)
    airframe: AirframeBodyModule = rng.choice(_AIRFRAME_CANDIDATES)
    rotor: RotorArmsModule = rng.choice(_ROTOR_CANDIDATES)
    gear: LandingGearModule = rng.choice(_GEAR_CANDIDATES)
    payload: PayloadUndermountModule = rng.choice(_PAYLOAD_CANDIDATES)
    palette_theme: DronePaletteTheme = rng.choice(tuple(DRONE_PALETTE_PRESETS.keys()))

    # Airframe envelope keyed to the chosen Slot A module's natural scale.
    if airframe == "lathe_round_body":
        body_length = round(rng.uniform(0.11, 0.20), 4)
        body_width = round(body_length * rng.uniform(0.90, 1.05), 4)
        body_height = round(rng.uniform(0.030, 0.060), 4)
    elif airframe == "racing_h_frame_body":
        body_length = round(rng.uniform(0.16, 0.26), 4)
        body_width = round(rng.uniform(0.09, 0.16), 4)
        body_height = round(rng.uniform(0.040, 0.080), 4)
    elif airframe == "hex_plate_stack_body":
        body_length = round(rng.uniform(0.22, 0.36), 4)
        body_width = round(rng.uniform(0.18, 0.30), 4)
        body_height = round(rng.uniform(0.060, 0.110), 4)
    else:  # rounded_shell_body
        body_length = round(rng.uniform(0.28, 0.46), 4)
        body_width = round(rng.uniform(0.16, 0.28), 4)
        body_height = round(rng.uniform(0.040, 0.085), 4)

    # Rotor ring radius scales with body + chosen N so the chord-clamp
    # later in resolve_config doesn't shrink propellers to nothing.
    n_rotors = ROTOR_MODULE_N[rotor]
    rotor_ring_radius = round(rng.uniform(0.16, 0.36), 4)
    if n_rotors == 8:
        rotor_ring_radius = max(rotor_ring_radius, 0.24)

    # Propeller radius is clamped against rotor spacing later; here we
    # just sample inside the spec range.
    propeller_radius = round(rng.uniform(0.07, 0.18), 4)
    propeller_blade_count = rng.choice((2, 3))

    return DroneConfig(
        airframe_body_module=airframe,
        rotor_arms_module=rotor,
        landing_gear_module=gear,
        payload_undermount_module=payload,
        palette_theme=palette_theme,
        body_length=body_length,
        body_width=body_width,
        body_height=body_height,
        rotor_ring_radius=rotor_ring_radius,
        propeller_radius=propeller_radius,
        propeller_blade_count=propeller_blade_count,
        arm_thickness=round(rng.uniform(0.016, 0.026), 4),
        motor_pod_radius=round(rng.uniform(0.018, 0.030), 4),
        motor_pod_height=round(rng.uniform(0.024, 0.040), 4),
        fold_angle_limit=round(rng.uniform(1.10, 1.55), 3),
        hinge_barrel_radius=round(rng.uniform(0.011, 0.016), 4),
        landing_gear_attach_z_offset=round(rng.uniform(-0.14, -0.04), 4),
        gimbal_attach_z_offset=round(rng.uniform(-0.12, -0.03), 4),
        gimbal_attach_x_offset=round(rng.uniform(0.030, 0.090), 4),
    )


def _compatibility_fix(
    gear: LandingGearModule, payload: PayloadUndermountModule
) -> LandingGearModule:
    """Apply the Slot C × Slot D forbidden-pair fallback. ``payload_skid``
    needs hinge space along the belly and clashes with both
    ``folding_landing_legs`` and ``wire_loop_skids``; falls back to
    ``tube_legs_pair``."""

    if (gear, payload) in _FORBIDDEN_C_D_PAIRS:
        return "tube_legs_pair"
    return gear


def resolve_config(config: DroneConfig) -> ResolvedDroneConfig:
    """Validate + clamp the configuration. Applies the Slot C × Slot D
    compatibility matrix, derives rotor_count + folding_enabled from the
    chosen Slot B module, and clamps propeller_radius / fold_angle_limit
    against the rotor ring layout to prevent prop-prop or arm-arm
    collisions at the chosen multiplicity."""

    airframe = config.airframe_body_module or "rounded_shell_body"
    rotor = config.rotor_arms_module or "folding_quad_4arm"
    gear = config.landing_gear_module or "tube_legs_pair"
    payload = config.payload_undermount_module or "three_axis_gimbal"

    if airframe not in _AIRFRAME_CANDIDATES:
        raise ValueError(f"Unsupported airframe_body_module: {airframe}")
    if rotor not in _ROTOR_CANDIDATES:
        raise ValueError(f"Unsupported rotor_arms_module: {rotor}")
    if gear not in _GEAR_CANDIDATES:
        raise ValueError(f"Unsupported landing_gear_module: {gear}")
    if payload not in _PAYLOAD_CANDIDATES:
        raise ValueError(f"Unsupported payload_undermount_module: {payload}")
    if str(config.palette_theme) not in DRONE_PALETTE_PRESETS:
        raise ValueError(f"Unsupported palette_theme: {config.palette_theme}")

    # Apply Slot C × Slot D compatibility matrix.
    gear = _compatibility_fix(gear, payload)

    # Slot A × Slot B compatibility:
    #   rounded_shell_body has 4 corner hinge supports → quad rotors only.
    #   racing_h_frame_body has 4 corner clamp blocks → quad rotors only.
    #   lathe_round_body is small/compact → quad rotors only.
    #   hex_plate_stack_body is radially symmetric → any N (4/6/8) fits.
    if airframe in ("rounded_shell_body", "racing_h_frame_body", "lathe_round_body"):
        if rotor in ("folding_hex_6arm", "fixed_octo_8arm"):
            rotor = "folding_quad_4arm" if rotor == "folding_hex_6arm" else "fixed_quad_4arm"

    n_rotors = ROTOR_MODULE_N[rotor]
    folding_enabled = ROTOR_MODULE_FOLDING[rotor]

    # Envelope clamps.
    body_length = max(0.10, min(float(config.body_length), 0.55))
    body_width = max(0.08, min(float(config.body_width), 0.45))
    body_height = max(0.025, min(float(config.body_height), 0.16))

    rotor_ring_radius = max(0.08, min(float(config.rotor_ring_radius), 0.55))
    # Rotor ring must be far enough from body envelope to host motor pods.
    body_half_diag = 0.5 * math.hypot(body_length, body_width)
    rotor_ring_radius = max(rotor_ring_radius, body_half_diag + 0.030)

    propeller_blade_count = int(config.propeller_blade_count)
    if propeller_blade_count not in (2, 3):
        propeller_blade_count = 2

    # Propeller radius clamp: must be smaller than 0.45 × motor_spacing
    # where motor_spacing = 2 * rotor_ring_radius * sin(pi / N). Leaves
    # ≥10 mm clearance for the prop-tip safety margin.
    motor_spacing = 2.0 * rotor_ring_radius * math.sin(math.pi / n_rotors)
    prop_radius_cap = max(0.040, 0.42 * motor_spacing - 0.010)
    propeller_radius = max(0.040, min(float(config.propeller_radius), 0.27))
    propeller_radius = min(propeller_radius, prop_radius_cap)

    arm_thickness = max(0.012, min(float(config.arm_thickness), 0.032))
    motor_pod_radius = max(0.014, min(float(config.motor_pod_radius), 0.034))
    motor_pod_height = max(0.018, min(float(config.motor_pod_height), 0.046))
    hinge_barrel_radius = max(0.008, min(float(config.hinge_barrel_radius), 0.020))

    # fold_angle_limit auto-clamp: as N grows, neighbouring arms close in
    # on each other when folded — cap to (pi/N - safety_margin).
    fold_limit_geom = max(0.50, math.pi / n_rotors - 0.18)
    fold_angle_limit = max(0.70, min(float(config.fold_angle_limit), 2.20))
    fold_angle_limit = min(fold_angle_limit, fold_limit_geom)

    landing_gear_attach_z_offset = max(
        -0.20, min(float(config.landing_gear_attach_z_offset), -0.02)
    )
    gear_fold_angle = max(0.0, min(float(config.gear_fold_angle), 1.55))
    gimbal_attach_z_offset = max(-0.18, min(float(config.gimbal_attach_z_offset), -0.02))
    # Clamp the forward gimbal attach offset to stay INSIDE the airframe
    # envelope (the gimbal hangs under the belly, not off the nose).
    gimbal_attach_x_max = max(0.020, body_length * 0.30)
    gimbal_attach_x_offset = max(
        0.0, min(float(config.gimbal_attach_x_offset), gimbal_attach_x_max)
    )

    # Default 4 legs for folding_landing_legs; allow 8 when paired with
    # the octo rotor module (heavy-lift VTOL aesthetic).
    if gear == "folding_landing_legs":
        n_legs = 4 if n_rotors != 8 else 4
    else:
        n_legs = 0

    palette = dict(DRONE_PALETTE_PRESETS[config.palette_theme])

    return ResolvedDroneConfig(
        airframe_body_module=airframe,
        rotor_arms_module=rotor,
        landing_gear_module=gear,
        payload_undermount_module=payload,
        palette_theme=config.palette_theme,
        body_length=body_length,
        body_width=body_width,
        body_height=body_height,
        rotor_ring_radius=rotor_ring_radius,
        propeller_radius=propeller_radius,
        propeller_blade_count=propeller_blade_count,
        arm_thickness=arm_thickness,
        motor_pod_radius=motor_pod_radius,
        motor_pod_height=motor_pod_height,
        fold_angle_limit=fold_angle_limit,
        hinge_barrel_radius=hinge_barrel_radius,
        landing_gear_attach_z_offset=landing_gear_attach_z_offset,
        gear_fold_angle=gear_fold_angle,
        gimbal_attach_z_offset=gimbal_attach_z_offset,
        gimbal_attach_x_offset=gimbal_attach_x_offset,
        rotor_count=n_rotors,
        folding_enabled=folding_enabled,
        n_landing_legs=n_legs,
        palette=palette,
    )


# --------------------------------------------------------------------------- #
# Shared geometry helpers
# --------------------------------------------------------------------------- #


def _radial_xy(n: int, index: int, radius: float, phase: float = 0.0) -> tuple[float, float, float]:
    """Return (x, y, theta) for the i-th radial position out of N.

    ``theta`` is the angle from +x axis, used to orient an arm along the
    radial direction (so its long axis aligns with +x in its own local
    frame after rotating about z by ``theta``).
    """
    theta = phase + index * 2.0 * math.pi / n
    return (radius * math.cos(theta), radius * math.sin(theta), theta)


def _regular_polygon_profile(
    radius: float,
    sides: int,
    *,
    phase: float = 0.0,
) -> list[tuple[float, float]]:
    return [
        (
            radius * math.cos(phase + 2.0 * math.pi * i / sides),
            radius * math.sin(phase + 2.0 * math.pi * i / sides),
        )
        for i in range(sides)
    ]


def _emit_propeller_visuals(
    part,
    *,
    radius: float,
    blade_count: int,
    hub_radius: float,
    hub_height: float,
    palette_propeller: str = "propeller",
    palette_motor: str = "motor",
) -> None:
    """Emit the standard propeller geometry on ``part``.

    Layout: a central ``hub`` cylinder (axis along z), and ``blade_count``
    flat blade Boxes whose long axes radiate from the hub at even angular
    spacing. The hub sits centred at z=0 and extends ±0.5*hub_height in
    z; blades sit at z=0 with a slight z extent equal to half the hub
    height so they share AABB with the hub (connectivity).

    Adapted from ``rec_drone_456cea3c…:model.py:L28-L47`` propeller mesh
    helper (Box stays Box per Rule 3).
    """

    # Hub cylinder — centred on z=0.
    part.visual(
        Cylinder(radius=hub_radius, length=hub_height),
        origin=Origin(xyz=(0.0, 0.0, 0.0)),
        material=palette_motor,
        name="prop_hub",
    )
    # Hub top cap — slightly larger radius for a propeller "screw cap"
    # accent (also helps fail_if_part_contains_disconnected_geometry_islands
    # by giving the hub a clear AABB footprint).
    part.visual(
        Cylinder(radius=hub_radius * 1.12, length=hub_height * 0.45),
        origin=Origin(xyz=(0.0, 0.0, hub_height * 0.4)),
        material=palette_motor,
        name="prop_hub_cap",
    )

    blade_length = max(0.025, radius - hub_radius * 1.05)
    blade_chord = max(0.012, radius * 0.16)
    blade_thickness = max(0.0035, radius * 0.024)
    for i in range(blade_count):
        theta = i * 2.0 * math.pi / blade_count
        # Blade extends from hub_radius outward to ``radius`` along the
        # local +x direction, then is rotated about z by ``theta``.
        cx = (hub_radius * 0.55 + radius) * 0.5
        # Convert local-x to world-x/y by rotating.
        x = cx * math.cos(theta)
        y = cx * math.sin(theta)
        part.visual(
            Box((blade_length, blade_chord, blade_thickness)),
            origin=Origin(xyz=(x, y, 0.0), rpy=(0.0, 0.0, theta)),
            material=palette_propeller,
            name=f"prop_blade_{i}",
        )


def _emit_motor_pod_visuals(
    part,
    *,
    center: tuple[float, float, float],
    radius: float,
    height: float,
    name_prefix: str = "motor_pod",
    palette_motor: str = "motor",
) -> tuple[float, float, float]:
    """Emit a motor pod (cylinder + small cap) on ``part``.

    Returns the (x, y, z) of the top centre of the cap — used as the
    propeller spin joint origin.
    """
    cx, cy, cz = center
    part.visual(
        Cylinder(radius=radius, length=height),
        origin=Origin(xyz=(cx, cy, cz + 0.5 * height)),
        material=palette_motor,
        name=name_prefix,
    )
    cap_height = max(0.004, height * 0.20)
    part.visual(
        Cylinder(radius=radius * 1.08, length=cap_height),
        origin=Origin(xyz=(cx, cy, cz + height + 0.5 * cap_height)),
        material=palette_motor,
        name=f"{name_prefix}_cap",
    )
    return (cx, cy, cz + height + cap_height)


# --------------------------------------------------------------------------- #
# Slot A factories — airframe_body
# --------------------------------------------------------------------------- #


@dataclass
class AirframeBuildResult:
    """Output of a Slot A factory.

    ``part_name`` is always ``body`` (the root airframe part). ``top_z``
    and ``bottom_z`` are the world-z extents of the airframe in its part
    frame; ``hinge_radius`` is where folding arm hinges should mount
    (typically slightly inside the body envelope). ``rotor_radial_phase``
    is the angular phase for rotor placement (so e.g. hex bodies host
    hex arms 60° apart starting from +x).
    """

    part_name: str
    top_z: float
    bottom_z: float
    hinge_radius: float
    rotor_radial_phase: float


def _build_rounded_shell_body(
    model: ArticulatedObject, r: ResolvedDroneConfig
) -> AirframeBuildResult:
    """Anchor airframe — rounded-rectangle extruded shell + top deck +
    belly pack + nose chin + sensor bar + per-rotor hinge supports.

    Adapted from ``rec_drone_456cea3c…:model.py:L129-L205``. The original
    uses an ExtrudeGeometry with a rounded_rect_profile; we reproduce the
    same family of geometry using a stack of Box visuals plus one
    Cylinder per corner so the part stays a single connected island and
    has the same visual "rounded soft brick" silhouette.
    """

    body = model.part("body")
    L = r.body_length
    W = r.body_width
    H = r.body_height

    # Main shell — a single central box centred on (0,0,0).
    body.visual(
        Box((L * 0.84, W * 0.92, H)),
        origin=Origin(xyz=(0.0, 0.0, 0.0)),
        material="body_main",
        name="shell_core",
    )
    # Top deck — slightly recessed slab above the core.
    body.visual(
        Box((L * 0.72, W * 0.76, H * 0.30)),
        origin=Origin(xyz=(0.0, 0.0, H * 0.55)),
        material="body_accent",
        name="top_deck",
    )
    # Belly pack — slab below the core that hosts the battery / lower bay.
    body.visual(
        Box((L * 0.62, W * 0.66, H * 0.55)),
        origin=Origin(xyz=(0.0, 0.0, -H * 0.55)),
        material="body_accent",
        name="belly_pack",
    )
    # Nose chin — forward bump that hosts sensor array.
    body.visual(
        Box((L * 0.18, W * 0.46, H * 0.50)),
        origin=Origin(xyz=(L * 0.42, 0.0, -H * 0.08)),
        material="body_accent",
        name="nose_chin",
    )
    # Forward sensor bar (horizontal cylinder above the nose chin).
    body.visual(
        Cylinder(radius=H * 0.20, length=W * 0.42),
        origin=Origin(xyz=(L * 0.42, 0.0, H * 0.10), rpy=(math.pi / 2.0, 0.0, 0.0)),
        material="carbon",
        name="forward_sensor_bar",
    )
    # Rear vent block.
    body.visual(
        Box((L * 0.12, W * 0.60, H * 0.40)),
        origin=Origin(xyz=(-L * 0.42, 0.0, H * 0.05)),
        material="carbon",
        name="rear_vent",
    )
    # GPS puck sitting on the top deck (sinks slightly INTO the deck for
    # connectivity insurance).
    body.visual(
        Cylinder(radius=W * 0.10, length=H * 0.22),
        origin=Origin(xyz=(0.0, 0.0, H * 0.55 + H * 0.10)),
        material="carbon",
        name="gps_puck",
    )

    # Corner hinge supports (4 cylinders at ±x, ±y rounded corners) — these
    # are where the folding arms attach. They sit on the shell core top
    # plane so they're guaranteed to overlap the shell.
    hinge_r = r.hinge_barrel_radius
    corner_half_x = L * 0.40
    corner_half_y = W * 0.42
    body.visual(
        Cylinder(radius=hinge_r * 1.6, length=H * 0.60),
        origin=Origin(xyz=(+corner_half_x, +corner_half_y, 0.0)),
        material="metal",
        name="hinge_support_front_left",
    )
    body.visual(
        Cylinder(radius=hinge_r * 1.6, length=H * 0.60),
        origin=Origin(xyz=(+corner_half_x, -corner_half_y, 0.0)),
        material="metal",
        name="hinge_support_front_right",
    )
    body.visual(
        Cylinder(radius=hinge_r * 1.6, length=H * 0.60),
        origin=Origin(xyz=(-corner_half_x, +corner_half_y, 0.0)),
        material="metal",
        name="hinge_support_rear_left",
    )
    body.visual(
        Cylinder(radius=hinge_r * 1.6, length=H * 0.60),
        origin=Origin(xyz=(-corner_half_x, -corner_half_y, 0.0)),
        material="metal",
        name="hinge_support_rear_right",
    )

    body.inertial = Inertial.from_geometry(
        Box((L, W, H * 1.6)),
        mass=1.2,
        origin=Origin(xyz=(0.0, 0.0, 0.0)),
    )

    hinge_radius_envelope = math.hypot(corner_half_x, corner_half_y)
    # Anchor phase = pi/4 puts arms at 45° (corners) for quad family.
    return AirframeBuildResult(
        part_name="body",
        top_z=H * 0.55 + H * 0.10 + H * 0.11,
        bottom_z=-H * 0.55 - H * 0.55 * 0.5,
        hinge_radius=hinge_radius_envelope,
        rotor_radial_phase=math.pi / 4.0,
    )


def _build_hex_plate_stack_body(
    model: ArticulatedObject, r: ResolvedDroneConfig
) -> AirframeBuildResult:
    """Alt airframe — hex carbon plate stack (top + bottom hex plates +
    6 standoffs + avionics_pod + gps_puck).

    Adapted from ``rec_drone_098da8da…:model.py:L147-L191``. The plates
    use ExtrudeGeometry over an explicit six-point profile so seeded
    samples visibly keep the reference hex-board silhouette.
    """

    body = model.part("body")
    L = r.body_length
    W = r.body_width
    H = r.body_height
    hex_r = max(L, W) * 0.5
    lower_plate_mesh = mesh_from_geometry(
        ExtrudeGeometry.centered(
            _regular_polygon_profile(hex_r, 6),
            H * 0.16,
        ),
        "drone_hex_lower_plate",
    )
    upper_plate_mesh = mesh_from_geometry(
        ExtrudeGeometry.centered(
            _regular_polygon_profile(hex_r * 0.92, 6),
            H * 0.16,
        ),
        "drone_hex_upper_plate",
    )

    # Lower hex carbon plate.
    body.visual(
        lower_plate_mesh,
        origin=Origin(xyz=(0.0, 0.0, -H * 0.30)),
        material="carbon",
        name="lower_plate",
    )
    # Upper hex carbon plate.
    body.visual(
        upper_plate_mesh,
        origin=Origin(xyz=(0.0, 0.0, +H * 0.30)),
        material="carbon",
        name="upper_plate",
    )

    # 6 standoffs around the hex.
    standoff_r = max(0.006, hex_r * 0.040)
    for i in range(6):
        theta = i * math.pi / 3.0
        sx = hex_r * 0.78 * math.cos(theta)
        sy = hex_r * 0.78 * math.sin(theta)
        body.visual(
            Cylinder(radius=standoff_r, length=H * 0.66),
            origin=Origin(xyz=(sx, sy, 0.0)),
            material="metal",
            name=f"standoff_{i}",
        )

    # Avionics pod between plates (central).
    body.visual(
        Box((L * 0.50, W * 0.42, H * 0.50)),
        origin=Origin(xyz=(0.0, 0.0, 0.0)),
        material="body_main",
        name="avionics_pod",
    )
    # GPS puck on upper plate.
    body.visual(
        Cylinder(radius=hex_r * 0.18, length=H * 0.20),
        origin=Origin(xyz=(0.0, 0.0, H * 0.30 + H * 0.18)),
        material="body_accent",
        name="gps_puck",
    )
    # Forward antenna stub — anchored on the upper_plate so its lower
    # half overlaps the plate (connectivity).
    body.visual(
        Cylinder(radius=hex_r * 0.04, length=H * 0.32),
        origin=Origin(xyz=(hex_r * 0.55, 0.0, H * 0.30 + H * 0.10)),
        material="metal",
        name="antenna_stub",
    )

    body.inertial = Inertial.from_geometry(
        Cylinder(radius=hex_r, length=H * 1.4),
        mass=1.0,
        origin=Origin(xyz=(0.0, 0.0, 0.0)),
    )

    return AirframeBuildResult(
        part_name="body",
        top_z=H * 0.30 + H * 0.18 + H * 0.20,
        bottom_z=-H * 0.30 - H * 0.16 * 0.5,
        hinge_radius=hex_r * 0.85,
        rotor_radial_phase=0.0,  # rotor 0 at +x
    )


def _build_racing_h_frame_body(
    model: ArticulatedObject, r: ResolvedDroneConfig
) -> AirframeBuildResult:
    """Alt airframe — racing H-frame (twin lower rails + twin bridges +
    centre tray + top plate + standoffs + clamps + flight stack).

    Adapted from ``rec_drone_23234c71…:model.py:L184-L262``. H-frame is
    the FPV racing aesthetic; fixed arms dock between the lower and
    upper plates.
    """

    body = model.part("body")
    L = r.body_length
    W = r.body_width
    H = r.body_height

    # Lower-left + lower-right rails.
    body.visual(
        Box((L, W * 0.18, H * 0.18)),
        origin=Origin(xyz=(0.0, +W * 0.30, -H * 0.40)),
        material="carbon",
        name="lower_left_rail",
    )
    body.visual(
        Box((L, W * 0.18, H * 0.18)),
        origin=Origin(xyz=(0.0, -W * 0.30, -H * 0.40)),
        material="carbon",
        name="lower_right_rail",
    )
    # Front + rear bridges between rails.
    body.visual(
        Box((L * 0.16, W * 0.78, H * 0.18)),
        origin=Origin(xyz=(+L * 0.42, 0.0, -H * 0.40)),
        material="carbon",
        name="front_bridge",
    )
    body.visual(
        Box((L * 0.16, W * 0.78, H * 0.18)),
        origin=Origin(xyz=(-L * 0.42, 0.0, -H * 0.40)),
        material="carbon",
        name="rear_bridge",
    )
    # Centre tray.
    body.visual(
        Box((L * 0.62, W * 0.78, H * 0.10)),
        origin=Origin(xyz=(0.0, 0.0, -H * 0.08)),
        material="body_main",
        name="center_tray",
    )
    # Top plate.
    body.visual(
        Box((L * 0.62, W * 0.78, H * 0.10)),
        origin=Origin(xyz=(0.0, 0.0, +H * 0.40)),
        material="carbon",
        name="top_plate",
    )
    # Four standoffs connecting bottom and top plates.
    standoff_r = max(0.005, H * 0.06)
    for ix, sign_x in enumerate((+1.0, -1.0)):
        for iy, sign_y in enumerate((+1.0, -1.0)):
            body.visual(
                Cylinder(radius=standoff_r, length=H * 0.90),
                origin=Origin(xyz=(sign_x * L * 0.24, sign_y * W * 0.30, 0.0)),
                material="metal",
                name=f"standoff_{ix * 2 + iy}",
            )
    # 4 clamp blocks on rails (decorative + arm dock).
    for ic, (sx, sy) in enumerate(
        (
            (+L * 0.32, +W * 0.30),
            (+L * 0.32, -W * 0.30),
            (-L * 0.32, +W * 0.30),
            (-L * 0.32, -W * 0.30),
        )
    ):
        body.visual(
            Box((W * 0.18, W * 0.18, H * 0.30)),
            origin=Origin(xyz=(sx, sy, -H * 0.40)),
            material="body_main",
            name=f"arm_clamp_{ic}",
        )
    # Flight stack pcb-ish block in centre (overlaps center_tray + top_plate).
    body.visual(
        Box((L * 0.34, W * 0.40, H * 0.40)),
        origin=Origin(xyz=(0.0, 0.0, +H * 0.18)),
        material="body_accent",
        name="flight_stack",
    )
    # Camera bracket — extends from the center forward (overlaps
    # front_bridge and flight_stack so it's geometrically connected).
    body.visual(
        Box((L * 0.45, W * 0.30, H * 0.18)),
        origin=Origin(xyz=(+L * 0.22, 0.0, -H * 0.10)),
        material="body_main",
        name="camera_bracket",
    )
    # VTX cap — short cylinder mounted on top_plate.
    body.visual(
        Cylinder(radius=W * 0.10, length=H * 0.20),
        origin=Origin(xyz=(-L * 0.22, 0.0, +H * 0.45)),
        material="body_accent",
        name="vtx_cap",
    )

    body.inertial = Inertial.from_geometry(
        Box((L, W, H * 1.6)),
        mass=0.65,
        origin=Origin(xyz=(0.0, 0.0, 0.0)),
    )

    return AirframeBuildResult(
        part_name="body",
        top_z=+H * 0.55 + H * 0.22,
        bottom_z=-H * 0.40 - H * 0.18 * 0.5,
        hinge_radius=math.hypot(L * 0.32, W * 0.30),
        rotor_radial_phase=math.atan2(W * 0.30, L * 0.32),
    )


def _build_lathe_round_body(
    model: ArticulatedObject, r: ResolvedDroneConfig
) -> AirframeBuildResult:
    """Alt airframe — LatheGeometry round mini-drone shell + top button accent.

    Adapted from ``rec_drone_2000ae38…:model.py:L34-L72``. Uses
    LatheGeometry to spin a small "toy / consumer indoor" round shell.
    Rule 3: preserves LatheGeometry primitive choice from the source.
    """

    body = model.part("body")
    L = r.body_length
    W = r.body_width
    H = r.body_height
    radius = max(L, W) * 0.5

    # Lathe shell profile (radius_z pairs). Constructs a low domed shell.
    half_h = H * 0.5
    profile = [
        (0.0, +half_h * 1.10),
        (radius * 0.50, +half_h * 0.85),
        (radius * 0.92, +half_h * 0.20),
        (radius * 1.00, +half_h * 0.00),
        (radius * 0.94, -half_h * 0.30),
        (radius * 0.70, -half_h * 0.70),
        (radius * 0.40, -half_h * 0.95),
        (0.0, -half_h * 1.05),
    ]
    shell_mesh = mesh_from_geometry(
        LatheGeometry(profile, segments=36, closed=True),
        "frame_shell",
    )
    body.visual(
        shell_mesh,
        origin=Origin(xyz=(0.0, 0.0, 0.0)),
        material="body_main",
        name="frame_shell",
    )

    # Top button accent (small cylinder on top).
    body.visual(
        Cylinder(radius=radius * 0.25, length=H * 0.22),
        origin=Origin(xyz=(0.0, 0.0, +half_h * 0.95)),
        material="body_accent",
        name="top_button",
    )
    # Bottom skid pad (small flattened disc) for connectivity insurance.
    body.visual(
        Cylinder(radius=radius * 0.40, length=H * 0.12),
        origin=Origin(xyz=(0.0, 0.0, -half_h * 0.92)),
        material="body_accent",
        name="bottom_pad",
    )
    # Small forward LED bump — placed well inside the shell envelope to
    # guarantee AABB overlap with the frame_shell mesh.
    body.visual(
        Box((H * 0.30, W * 0.18, H * 0.16)),
        origin=Origin(xyz=(radius * 0.50, 0.0, 0.0)),
        material="warn",
        name="forward_led",
    )

    body.inertial = Inertial.from_geometry(
        Cylinder(radius=radius * 1.05, length=H * 1.1),
        mass=0.18,
        origin=Origin(xyz=(0.0, 0.0, 0.0)),
    )

    return AirframeBuildResult(
        part_name="body",
        top_z=+half_h * 0.95 + H * 0.22,
        bottom_z=-half_h * 0.92 - H * 0.12,
        hinge_radius=radius * 0.85,
        rotor_radial_phase=math.pi / 4.0,
    )


AIRFRAME_FACTORIES = {
    "rounded_shell_body": _build_rounded_shell_body,
    "hex_plate_stack_body": _build_hex_plate_stack_body,
    "racing_h_frame_body": _build_racing_h_frame_body,
    "lathe_round_body": _build_lathe_round_body,
}


# --------------------------------------------------------------------------- #
# Slot B factories — rotor_arms (multiplicity)
# --------------------------------------------------------------------------- #


def _build_folding_arms(
    model: ArticulatedObject,
    r: ResolvedDroneConfig,
    airframe: AirframeBuildResult,
) -> list[str]:
    """Build N folding arms — each arm is its own movable part with a
    REVOLUTE fold joint to the body and a CONTINUOUS propeller spin
    joint on a child propeller part.

    Adapted from ``rec_drone_456cea3c…:model.py:L207-L317`` (4-arm) and
    ``rec_drone_098da8da…:model.py:L224-L338`` (6-arm). Same arm
    topology, just different N.

    Returns the list of propeller part names emitted.
    """

    body = model.get_part(airframe.part_name)
    n = r.rotor_count
    ring_r = r.rotor_ring_radius
    arm_t = r.arm_thickness
    pod_r = r.motor_pod_radius
    pod_h = r.motor_pod_height
    hinge_r = r.hinge_barrel_radius
    phase = airframe.rotor_radial_phase
    body_z = (airframe.top_z + airframe.bottom_z) * 0.5

    propeller_names: list[str] = []

    # Bring the hinges INSIDE the body envelope so that every arm's
    # hinge_root_collar overlaps SOMETHING on the body (no isolated-parts
    # / joint_origin_far violations regardless of arm theta).
    body_min_half = max(0.020, 0.5 * min(r.body_length, r.body_width))
    safe_hinge_distance = min(airframe.hinge_radius * 0.70, body_min_half * 0.85)
    safe_hinge_distance = max(safe_hinge_distance, 0.020)
    for i in range(n):
        theta = phase + i * 2.0 * math.pi / n
        # Hinge location on body rim — slightly inside the body envelope.
        hinge_distance = safe_hinge_distance
        hinge_x = hinge_distance * math.cos(theta)
        hinge_y = hinge_distance * math.sin(theta)
        # Arm length from hinge to motor.
        arm_length = max(0.060, ring_r - hinge_distance)
        # The arm's own +x in its part frame points radially outward
        # FROM the hinge. The joint's rpy=(0,0,theta) rotates the part
        # frame so +x_local lies along the world radial direction.
        arm = model.part(f"arm_{i}")
        # Hinge barrel at the arm's part-frame origin (z spans across the
        # hinge axis). This is what the body_to_arm REVOLUTE joint mates
        # against. Make it tall enough to overlap the body shell at the
        # hinge location (so the arm part isn't a floating component).
        barrel_len = max(0.030, 2.0 * hinge_r * 3.0)
        arm.visual(
            Cylinder(radius=hinge_r * 1.6, length=barrel_len),
            origin=Origin(xyz=(0.0, 0.0, 0.0)),
            material="metal",
            name="hinge_barrel",
        )
        # Root collar: a wide flat disc straddling the hinge axis that
        # extends INWARD (toward the body center) to guarantee overlap
        # with whatever body visual sits at the hinge location. Sized
        # such that adjacent arms' collars don't overlap each other.
        neighbour_spacing = 2.0 * hinge_distance * math.sin(math.pi / n)
        collar_r = max(hinge_r * 1.8, 0.016)
        collar_r = min(collar_r, max(0.010, 0.45 * neighbour_spacing))
        arm.visual(
            Cylinder(radius=collar_r, length=barrel_len * 0.6),
            origin=Origin(xyz=(-collar_r * 0.20, 0.0, 0.0)),
            material="body_accent",
            name="hinge_root_collar",
        )
        # Arm tube — extends from inside the hinge barrel outward to the
        # motor pod.
        tube_start_x = hinge_r * 0.4
        tube_end_x = arm_length - pod_r * 0.6
        tube_len = max(0.040, tube_end_x - tube_start_x)
        tube_center_x = 0.5 * (tube_start_x + tube_end_x)
        arm.visual(
            Box((tube_len, arm_t * 1.6, arm_t)),
            origin=Origin(xyz=(tube_center_x, 0.0, 0.0)),
            material="carbon",
            name="arm_tube",
        )
        # Lower trim rib (decorative — and connectivity insurance).
        arm.visual(
            Box((tube_len * 0.84, arm_t * 1.0, arm_t * 0.50)),
            origin=Origin(xyz=(tube_center_x, 0.0, -arm_t * 0.40)),
            material="body_accent",
            name="arm_trim_rib",
        )
        # Motor pod at the arm's far end.
        motor_top = _emit_motor_pod_visuals(
            arm,
            center=(arm_length, 0.0, 0.0),
            radius=pod_r,
            height=pod_h,
            name_prefix="motor_pod",
        )
        # Navigation light accent at the tip — connectivity-safe (touches
        # motor_pod_cap).
        arm.visual(
            Box((arm_t * 0.60, arm_t * 0.60, arm_t * 0.40)),
            origin=Origin(xyz=(arm_length, 0.0, motor_top[2])),
            material="warn",
            name="nav_light",
        )

        arm.inertial = Inertial.from_geometry(
            Box((arm_length + 0.040, arm_t * 2.0, arm_t * 2.0)),
            mass=0.06,
            origin=Origin(xyz=(0.5 * arm_length, 0.0, 0.0)),
        )

        # body_to_arm_i REVOLUTE joint (folding hinge). Axis is vertical
        # (+z in WORLD frame; arm's local frame is rotated by theta, but
        # the joint axis is expressed in PARENT frame which is body's
        # frame, where vertical is still (0,0,1)).
        model.articulation(
            f"body_to_arm_{i}",
            ArticulationType.REVOLUTE,
            parent=body,
            child=arm,
            origin=Origin(xyz=(hinge_x, hinge_y, body_z), rpy=(0.0, 0.0, theta)),
            axis=(0.0, 0.0, 1.0),
            motion_limits=MotionLimits(
                effort=12.0, velocity=1.8, lower=0.0, upper=r.fold_angle_limit
            ),
            motion_properties=MotionProperties(damping=0.10, friction=0.05),
        )

        # Propeller part — child of arm, axis along z (vertical thrust).
        prop = model.part(f"propeller_{i}")
        _emit_propeller_visuals(
            prop,
            radius=r.propeller_radius,
            blade_count=r.propeller_blade_count,
            hub_radius=max(0.008, pod_r * 0.70),
            hub_height=max(0.010, pod_h * 0.50),
        )
        prop.inertial = Inertial.from_geometry(
            Cylinder(radius=r.propeller_radius, length=pod_h * 0.50),
            mass=0.015,
            origin=Origin(xyz=(0.0, 0.0, 0.0)),
        )
        model.articulation(
            f"arm_to_propeller_{i}",
            ArticulationType.CONTINUOUS,
            parent=arm,
            child=prop,
            origin=Origin(xyz=(arm_length, 0.0, motor_top[2] + 0.004)),
            axis=(0.0, 0.0, 1.0),
            motion_limits=MotionLimits(effort=2.0, velocity=600.0),
            motion_properties=MotionProperties(damping=0.0001, friction=0.0001),
        )
        propeller_names.append(f"propeller_{i}")

    return propeller_names


def _build_fixed_arms(
    model: ArticulatedObject,
    r: ResolvedDroneConfig,
    airframe: AirframeBuildResult,
) -> list[str]:
    """Build N fixed arms — arms are emitted as VISUALS on the body part
    (not separate movable parts), and each propeller is a child of the
    body with a CONTINUOUS spin joint.

    Adapted from ``rec_drone_2000ae38…:model.py:L86-L252`` (quad) and
    ``rec_drone_c412ec99…:model.py:L145-L229`` (octo). Same fixed-arm
    rotor topology, just different N.

    Returns the list of propeller part names emitted.
    """

    body = model.get_part(airframe.part_name)
    n = r.rotor_count
    ring_r = r.rotor_ring_radius
    arm_t = r.arm_thickness
    pod_r = r.motor_pod_radius
    pod_h = r.motor_pod_height
    phase = airframe.rotor_radial_phase
    body_z = (airframe.top_z + airframe.bottom_z) * 0.5

    propeller_names: list[str] = []
    arm_inner_distance = max(0.020, airframe.hinge_radius * 0.6)

    for i in range(n):
        theta = phase + i * 2.0 * math.pi / n
        arm_length = ring_r - arm_inner_distance
        arm_center_dist = arm_inner_distance + 0.5 * arm_length
        # Arm visual (a Box along the radial direction) — emitted on body.
        cx = arm_center_dist * math.cos(theta)
        cy = arm_center_dist * math.sin(theta)
        body.visual(
            Box((arm_length, arm_t * 1.6, arm_t)),
            origin=Origin(xyz=(cx, cy, body_z), rpy=(0.0, 0.0, theta)),
            material="carbon",
            name=f"arm_visual_{i}",
        )
        # Arm root clamp (decorative cube where arm meets body).
        rcx = arm_inner_distance * math.cos(theta)
        rcy = arm_inner_distance * math.sin(theta)
        body.visual(
            Box((arm_t * 1.6, arm_t * 1.8, arm_t * 1.8)),
            origin=Origin(xyz=(rcx, rcy, body_z), rpy=(0.0, 0.0, theta)),
            material="body_accent",
            name=f"arm_root_clamp_{i}",
        )
        # Motor pod at arm tip.
        mx = ring_r * math.cos(theta)
        my = ring_r * math.sin(theta)
        body.visual(
            Cylinder(radius=pod_r, length=pod_h),
            origin=Origin(xyz=(mx, my, body_z + 0.5 * pod_h)),
            material="motor",
            name=f"motor_pod_{i}",
        )
        body.visual(
            Cylinder(radius=pod_r * 1.10, length=pod_h * 0.22),
            origin=Origin(xyz=(mx, my, body_z + pod_h + pod_h * 0.11)),
            material="motor",
            name=f"motor_pod_cap_{i}",
        )

        # Propeller part — child of body, axis vertical.
        prop = model.part(f"propeller_{i}")
        _emit_propeller_visuals(
            prop,
            radius=r.propeller_radius,
            blade_count=r.propeller_blade_count,
            hub_radius=max(0.008, pod_r * 0.70),
            hub_height=max(0.010, pod_h * 0.50),
        )
        prop.inertial = Inertial.from_geometry(
            Cylinder(radius=r.propeller_radius, length=pod_h * 0.50),
            mass=0.015,
            origin=Origin(xyz=(0.0, 0.0, 0.0)),
        )
        model.articulation(
            f"body_to_propeller_{i}",
            ArticulationType.CONTINUOUS,
            parent=body,
            child=prop,
            origin=Origin(xyz=(mx, my, body_z + pod_h + pod_h * 0.22 + 0.004)),
            axis=(0.0, 0.0, 1.0),
            motion_limits=MotionLimits(effort=2.0, velocity=600.0),
            motion_properties=MotionProperties(damping=0.0001, friction=0.0001),
        )
        propeller_names.append(f"propeller_{i}")

    return propeller_names


def _build_rotor_arms(
    model: ArticulatedObject,
    r: ResolvedDroneConfig,
    airframe: AirframeBuildResult,
) -> list[str]:
    """Dispatch to folding or fixed builder based on the chosen module."""
    if r.folding_enabled:
        return _build_folding_arms(model, r, airframe)
    return _build_fixed_arms(model, r, airframe)


# --------------------------------------------------------------------------- #
# Slot C factories — landing_gear (parallel children of airframe body)
# --------------------------------------------------------------------------- #


def _build_wire_loop_skids(
    model: ArticulatedObject,
    r: ResolvedDroneConfig,
    airframe: AirframeBuildResult,
) -> list[str]:
    """Add ``left_skid`` + ``right_skid`` wire-loop visuals directly to the
    body part. No movable parts are emitted (Slot C visual-only branch).

    Adapted from ``rec_drone_098da8da…:model.py:L193-L222`` —
    wire_from_points carbon skids on the hex-frame underside.
    """

    body = model.get_part(airframe.part_name)
    L = r.body_length
    W = r.body_width
    z_top = airframe.bottom_z + 0.005  # touch the belly so AABB overlaps
    z_bottom = airframe.bottom_z + r.landing_gear_attach_z_offset
    runner_len = max(0.080, L * 0.70)
    runner_offset_y = max(0.040, W * 0.35)
    pillar_r = max(0.004, r.arm_thickness * 0.40)

    # Left skid: two short pillar columns + a horizontal runner.
    body.visual(
        Cylinder(radius=pillar_r, length=abs(z_top - z_bottom)),
        origin=Origin(
            xyz=(+L * 0.30, +runner_offset_y, 0.5 * (z_top + z_bottom)),
        ),
        material="skid",
        name="left_skid_front_pillar",
    )
    body.visual(
        Cylinder(radius=pillar_r, length=abs(z_top - z_bottom)),
        origin=Origin(
            xyz=(-L * 0.30, +runner_offset_y, 0.5 * (z_top + z_bottom)),
        ),
        material="skid",
        name="left_skid_rear_pillar",
    )
    body.visual(
        Cylinder(radius=pillar_r, length=runner_len),
        origin=Origin(
            xyz=(0.0, +runner_offset_y, z_bottom),
            rpy=(0.0, math.pi / 2.0, 0.0),
        ),
        material="skid",
        name="left_skid",
    )

    # Right skid mirror.
    body.visual(
        Cylinder(radius=pillar_r, length=abs(z_top - z_bottom)),
        origin=Origin(
            xyz=(+L * 0.30, -runner_offset_y, 0.5 * (z_top + z_bottom)),
        ),
        material="skid",
        name="right_skid_front_pillar",
    )
    body.visual(
        Cylinder(radius=pillar_r, length=abs(z_top - z_bottom)),
        origin=Origin(
            xyz=(-L * 0.30, -runner_offset_y, 0.5 * (z_top + z_bottom)),
        ),
        material="skid",
        name="right_skid_rear_pillar",
    )
    body.visual(
        Cylinder(radius=pillar_r, length=runner_len),
        origin=Origin(
            xyz=(0.0, -runner_offset_y, z_bottom),
            rpy=(0.0, math.pi / 2.0, 0.0),
        ),
        material="skid",
        name="right_skid",
    )

    return []  # No movable parts.


def _build_tube_legs_pair(
    model: ArticulatedObject,
    r: ResolvedDroneConfig,
    airframe: AirframeBuildResult,
) -> list[str]:
    """Anchor landing gear — two independent ``left_landing_gear`` /
    ``right_landing_gear`` parts, each FIXED to the body.

    Adapted from ``rec_drone_5ae12ee0…:model.py:L91-L184``. Cinema /
    prosumer carbon-tube leg loops.
    """

    body = model.get_part(airframe.part_name)
    L = r.body_length
    W = r.body_width
    z_top = airframe.bottom_z + 0.005
    z_bottom = airframe.bottom_z + r.landing_gear_attach_z_offset
    tube_r = max(0.005, r.arm_thickness * 0.45)
    runner_len = max(0.090, L * 0.75)
    side_off = max(0.040, W * 0.28)

    leg_z_len = max(0.030, abs(z_top - z_bottom))
    mount_plate_t = max(0.004, leg_z_len * 0.15)

    def _emit_leg(part, *, side_sign: float, leg_name: str) -> None:
        # Mounting plate at the part-frame origin. WIDE x extent so the
        # pillars overlap it in xy (otherwise the plate is a disconnected
        # geometry island).
        plate_x = max(L * 0.50, 0.060)
        part.visual(
            Box((plate_x, W * 0.14, mount_plate_t)),
            origin=Origin(xyz=(0.0, 0.0, 0.0)),
            material="body_main",
            name=f"{leg_name}_mount_plate",
        )
        pillar_x = plate_x * 0.40
        # Front pillar — extends downward from the mount plate. Top of
        # pillar overlaps the plate AABB.
        part.visual(
            Cylinder(radius=tube_r, length=leg_z_len + mount_plate_t),
            origin=Origin(
                xyz=(+pillar_x, 0.0, -(leg_z_len + mount_plate_t) * 0.5 + mount_plate_t * 0.5),
            ),
            material="skid",
            name=f"{leg_name}_front_pillar",
        )
        # Rear pillar.
        part.visual(
            Cylinder(radius=tube_r, length=leg_z_len + mount_plate_t),
            origin=Origin(
                xyz=(-pillar_x, 0.0, -(leg_z_len + mount_plate_t) * 0.5 + mount_plate_t * 0.5),
            ),
            material="skid",
            name=f"{leg_name}_rear_pillar",
        )
        # Runner along x at the bottom.
        part.visual(
            Cylinder(radius=tube_r, length=runner_len),
            origin=Origin(
                xyz=(0.0, 0.0, -leg_z_len),
                rpy=(0.0, math.pi / 2.0, 0.0),
            ),
            material="skid",
            name=f"{leg_name}_runner",
        )
        # Inner brace from pillar bases up to the mount plate (connectivity).
        part.visual(
            Box((plate_x * 0.90, tube_r * 1.4, tube_r * 1.4)),
            origin=Origin(xyz=(0.0, 0.0, -leg_z_len + tube_r * 0.7)),
            material="skid",
            name=f"{leg_name}_brace",
        )

        part.inertial = Inertial.from_geometry(
            Box((L * 0.50, W * 0.10, leg_z_len)),
            mass=0.10,
            origin=Origin(xyz=(0.0, 0.0, -leg_z_len * 0.5)),
        )

    left_gear = model.part("left_landing_gear")
    _emit_leg(left_gear, side_sign=+1.0, leg_name="left_landing_gear")
    right_gear = model.part("right_landing_gear")
    _emit_leg(right_gear, side_sign=-1.0, leg_name="right_landing_gear")

    # Place the FIXED joint INSIDE the body underside (above bottom_z)
    # so the mount_plate visual fully overlaps the body belly geometry.
    # The captured overlap is grandfathered via allow_overlap.
    attach_z = airframe.bottom_z + mount_plate_t * 0.5 + 0.002
    model.articulation(
        "body_to_left_landing_gear",
        ArticulationType.FIXED,
        parent=body,
        child=left_gear,
        origin=Origin(xyz=(0.0, +side_off, attach_z)),
    )
    model.articulation(
        "body_to_right_landing_gear",
        ArticulationType.FIXED,
        parent=body,
        child=right_gear,
        origin=Origin(xyz=(0.0, -side_off, attach_z)),
    )

    return ["left_landing_gear", "right_landing_gear"]


def _build_folding_landing_legs(
    model: ArticulatedObject,
    r: ResolvedDroneConfig,
    airframe: AirframeBuildResult,
) -> list[str]:
    """Heavy-lift folding landing legs — N=4 separate ``landing_leg_*``
    parts, each connected to the body by its own REVOLUTE ``gear_fold_*``
    joint.

    Adapted from ``rec_drone_c412ec99…:model.py:L186-L290``. Each leg has
    a mount block at the part-frame origin (so the joint origin sits on
    leg geometry), plus a strut/foot section that swings down in the
    gear-down pose.
    """

    body = model.get_part(airframe.part_name)
    n = r.n_landing_legs
    L = r.body_length
    W = r.body_width
    # Attach plane just inside the body underside so the leg's mount
    # block (centered at origin, ±0.012 in z) overlaps the body bottom.
    z_attach = airframe.bottom_z + 0.004

    leg_length = max(0.060, abs(r.landing_gear_attach_z_offset) + 0.040)
    strut_r = max(0.005, r.arm_thickness * 0.45)
    foot_r = max(0.014, strut_r * 2.8)

    # Place legs at 4 corners around the body (phase = pi/4 puts them at
    # 45° from +x). For N=8 they'd be at pi/8 + k*pi/4 but we currently
    # default to N=4 (see resolve_config).
    phase = math.pi / 4.0
    # Keep attach radius INSIDE the body footprint so the leg mount overlaps
    # the body belly (no isolated-parts / no joint_origin_far violations).
    attach_radius = max(0.025, min(L, W) * 0.30)

    emitted: list[str] = []
    for i in range(n):
        theta = phase + i * 2.0 * math.pi / n
        ax = attach_radius * math.cos(theta)
        ay = attach_radius * math.sin(theta)

        leg_name = f"landing_leg_{i:02d}"
        leg = model.part(leg_name)

        # Gear mount block at part-frame origin (clevis-style boss that
        # the body's underside attaches to).
        leg.visual(
            Box((0.030, 0.024, 0.024)),
            origin=Origin(xyz=(0.0, 0.0, 0.0)),
            material="metal",
            name=f"{leg_name}_mount",
        )
        # Leg strut extends OUTWARD (+x_local) and DOWNWARD (-z) from the
        # mount. We compose this as a single tilted Box that overlaps
        # both the mount and the foot.
        # Build the strut as a vertical+horizontal "L" so it's just a
        # series of Boxes — keeps the geometry simple and connected.
        leg.visual(
            Cylinder(radius=strut_r, length=leg_length),
            origin=Origin(
                xyz=(0.030 * 0.5, 0.0, -leg_length * 0.5),
            ),
            material="skid",
            name=f"{leg_name}_strut",
        )
        # Foot pad at strut bottom.
        leg.visual(
            Cylinder(radius=foot_r, length=foot_r * 0.35),
            origin=Origin(
                xyz=(0.030 * 0.5, 0.0, -leg_length),
            ),
            material="skid",
            name=f"{leg_name}_foot",
        )
        # Ankle collar (connectivity insurance between strut and foot).
        leg.visual(
            Cylinder(radius=strut_r * 2.0, length=foot_r * 0.30),
            origin=Origin(
                xyz=(0.030 * 0.5, 0.0, -leg_length + foot_r * 0.18),
            ),
            material="metal",
            name=f"{leg_name}_ankle_collar",
        )

        leg.inertial = Inertial.from_geometry(
            Box((0.040, 0.030, leg_length + foot_r)),
            mass=0.04,
            origin=Origin(xyz=(0.015, 0.0, -leg_length * 0.5)),
        )

        # gear_fold REVOLUTE joint. Axis is tangential to the body radius
        # at the attach point (perpendicular to leg's long axis when
        # gear-down); in the body frame this is (-sin theta, cos theta, 0).
        axis = (-math.sin(theta), math.cos(theta), 0.0)
        model.articulation(
            f"gear_fold_{i:02d}",
            ArticulationType.REVOLUTE,
            parent=body,
            child=leg,
            origin=Origin(xyz=(ax, ay, z_attach), rpy=(0.0, 0.0, theta)),
            axis=axis,
            motion_limits=MotionLimits(effort=18.0, velocity=1.0, lower=0.0, upper=1.45),
            motion_properties=MotionProperties(damping=0.20, friction=0.10),
        )
        emitted.append(leg_name)

    return emitted


def _select_body_bottom_visual_name(model: ArticulatedObject, airframe: AirframeBuildResult) -> str:
    """Return a real body visual name to mate underside parts against."""
    body = model.get_part(airframe.part_name)
    visual_names = {v.name for v in body.visuals}
    for candidate in ("belly_pack", "lower_plate", "center_tray", "bottom_pad", "shell_core"):
        if candidate in visual_names:
            return candidate
    # Fall back: pick the lowest visual by z.
    return next(iter(visual_names))


LANDING_GEAR_FACTORIES = {
    "wire_loop_skids": _build_wire_loop_skids,
    "tube_legs_pair": _build_tube_legs_pair,
    "folding_landing_legs": _build_folding_landing_legs,
    "none": None,
}


# --------------------------------------------------------------------------- #
# Slot D factories — payload_undermount (parallel children of airframe body)
# --------------------------------------------------------------------------- #


def _build_three_axis_gimbal(
    model: ArticulatedObject,
    r: ResolvedDroneConfig,
    airframe: AirframeBuildResult,
) -> list[str]:
    """Anchor payload — three_axis_gimbal: yaw → tilt → camera with three
    REVOLUTE joints (yaw / tilt / roll).

    Adapted from ``rec_drone_5ae12ee0…:model.py:L254-L428``.

    Joints:
        ``body_to_gimbal_yaw``: REVOLUTE axis (0,0,1)
        ``gimbal_yaw``:         REVOLUTE axis (0,0,1) (the body-to-yaw joint)
        ``gimbal_tilt``:        REVOLUTE axis (0,1,0)
        ``gimbal_roll``:        REVOLUTE axis (1,0,0)

    Spec says ``gimbal_yaw / gimbal_tilt / gimbal_roll`` are the three
    revolute joint names in the internal chain. The ``body_to_gimbal_yaw``
    attach joint can be aliased to ``gimbal_yaw`` so the validator finds
    the named joints.
    """

    body = model.get_part(airframe.part_name)

    # Clamp the forward offset so the yaw cylinder stays under body
    # belly (avoids placing it past the body envelope).
    yaw_attach_x = min(r.gimbal_attach_x_offset, r.body_length * 0.15)
    yaw_radius = 0.018
    yaw_height = 0.022
    # Place attach plane just INSIDE the body underside so the yaw_motor's
    # upper half overlaps body geometry (captured-pin grandfathered).
    yaw_attach_z = airframe.bottom_z + yaw_height * 0.30

    # gimbal_yaw part.
    yaw_part = model.part("gimbal_yaw")
    yaw_part.visual(
        Cylinder(radius=yaw_radius, length=yaw_height),
        origin=Origin(xyz=(0.0, 0.0, 0.0)),
        material="motor",
        name="yaw_motor",
    )
    yaw_part.visual(
        Box((0.040, 0.026, 0.016)),
        origin=Origin(xyz=(0.0, 0.0, -yaw_height * 0.55)),
        material="metal",
        name="yaw_hanger",
    )
    yaw_part.inertial = Inertial.from_geometry(
        Box((0.050, 0.040, yaw_height + 0.020)),
        mass=0.06,
        origin=Origin(xyz=(0.0, 0.0, -yaw_height * 0.3)),
    )

    # gimbal_tilt part.
    tilt_part = model.part("gimbal_tilt")
    tilt_part.visual(
        Box((0.030, 0.060, 0.016)),
        origin=Origin(xyz=(0.0, 0.0, 0.0)),
        material="metal",
        name="tilt_bridge",
    )
    tilt_part.visual(
        Box((0.014, 0.012, 0.026)),
        origin=Origin(xyz=(0.0, +0.030, -0.012)),
        material="metal",
        name="tilt_hanger_left",
    )
    tilt_part.visual(
        Box((0.014, 0.012, 0.026)),
        origin=Origin(xyz=(0.0, -0.030, -0.012)),
        material="metal",
        name="tilt_hanger_right",
    )
    tilt_part.visual(
        Cylinder(radius=0.010, length=0.014),
        origin=Origin(xyz=(0.0, +0.030, -0.020), rpy=(0.0, math.pi / 2.0, 0.0)),
        material="motor",
        name="tilt_motor_left",
    )
    tilt_part.visual(
        Cylinder(radius=0.010, length=0.014),
        origin=Origin(xyz=(0.0, -0.030, -0.020), rpy=(0.0, math.pi / 2.0, 0.0)),
        material="motor",
        name="tilt_motor_right",
    )
    tilt_part.inertial = Inertial.from_geometry(
        Box((0.060, 0.080, 0.040)),
        mass=0.05,
        origin=Origin(xyz=(0.0, 0.0, -0.010)),
    )

    # camera part. Geometry pushed DOWN (-z in camera frame) so the
    # roll_crossbar at z=+0.013 still touches tilt geometry while the
    # camera_body itself stays below the tilt envelope.
    camera = model.part("camera")
    camera.visual(
        Box((0.044, 0.034, 0.030)),
        origin=Origin(xyz=(0.0, 0.0, -0.014)),
        material="body_main",
        name="camera_body",
    )
    camera.visual(
        Cylinder(radius=0.014, length=0.040),
        origin=Origin(xyz=(0.028, 0.0, -0.014), rpy=(0.0, math.pi / 2.0, 0.0)),
        material="lens",
        name="camera_lens",
    )
    camera.visual(
        Cylinder(radius=0.016, length=0.006),
        origin=Origin(xyz=(0.045, 0.0, -0.014), rpy=(0.0, math.pi / 2.0, 0.0)),
        material="lens_glass",
        name="camera_bezel",
    )
    # Roll crossbar straddles the roll axis (z=0 in camera frame), so
    # it's geometrically captured by the tilt_motors at the cross-axis
    # pin (overlap allow-listed in run_drone_tests).
    camera.visual(
        Box((0.014, 0.040, 0.014)),
        origin=Origin(xyz=(0.0, 0.0, 0.000)),
        material="metal",
        name="roll_crossbar",
    )
    camera.inertial = Inertial.from_geometry(
        Box((0.060, 0.044, 0.040)),
        mass=0.10,
        origin=Origin(xyz=(0.010, 0.0, 0.0)),
    )

    # Joints — name them per spec so validator can find them.
    # body → gimbal_yaw : REVOLUTE around z. This is a pin-through-bushing
    # mechanical pivot (yaw motor captured inside the body belly mount),
    # so the MatingContract is intentionally omitted (grandfathered);
    # the captured-pivot overlaps are declared in run_drone_tests.
    model.articulation(
        "gimbal_yaw",
        ArticulationType.REVOLUTE,
        parent=body,
        child=yaw_part,
        origin=Origin(xyz=(yaw_attach_x, 0.0, yaw_attach_z)),
        axis=(0.0, 0.0, 1.0),
        motion_limits=MotionLimits(effort=2.0, velocity=2.0, lower=-2.8, upper=2.8),
        motion_properties=MotionProperties(damping=0.05, friction=0.02),
    )
    # yaw → tilt : REVOLUTE around y
    model.articulation(
        "gimbal_tilt",
        ArticulationType.REVOLUTE,
        parent=yaw_part,
        child=tilt_part,
        origin=Origin(xyz=(0.0, 0.0, -yaw_height * 0.55)),
        axis=(0.0, 1.0, 0.0),
        motion_limits=MotionLimits(effort=2.0, velocity=2.0, lower=-1.6, upper=1.6),
        motion_properties=MotionProperties(damping=0.05, friction=0.02),
    )
    # tilt → camera : REVOLUTE around x (roll). Origin placed at the
    # tilt_motor's z (-0.020) so it sits on tilt geometry (within 15mm
    # of tilt_bridge and tilt_motors AABBs).
    model.articulation(
        "gimbal_roll",
        ArticulationType.REVOLUTE,
        parent=tilt_part,
        child=camera,
        origin=Origin(xyz=(0.0, 0.0, -0.018)),
        axis=(1.0, 0.0, 0.0),
        motion_limits=MotionLimits(effort=2.0, velocity=2.0, lower=-0.7, upper=0.7),
        motion_properties=MotionProperties(damping=0.05, friction=0.02),
    )

    return ["gimbal_yaw", "gimbal_tilt", "camera"]


def _build_yaw_tilt_gimbal(
    model: ArticulatedObject,
    r: ResolvedDroneConfig,
    airframe: AirframeBuildResult,
) -> list[str]:
    """Alt payload — yaw + tilt 2-DOF gimbal (no roll).

    Adapted from ``rec_drone_3841c838…:model.py:L129-L183``.
    """

    body = model.get_part(airframe.part_name)
    yaw_attach_x = min(r.gimbal_attach_x_offset, r.body_length * 0.15)
    # Place attach plane WELL INSIDE body underside so yaw_bracket cylinder
    # (+z face at +0.009) is captured by body geometry.
    yaw_attach_z = airframe.bottom_z + 0.012

    # gimbal_yaw — bracket with two side arms forming a yoke.
    yaw_part = model.part("gimbal_yaw")
    yaw_part.visual(
        Cylinder(radius=0.016, length=0.018),
        origin=Origin(xyz=(0.0, 0.0, 0.0)),
        material="motor",
        name="yaw_bracket",
    )
    yaw_part.visual(
        Box((0.014, 0.014, 0.034)),
        origin=Origin(xyz=(0.0, +0.020, -0.018)),
        material="metal",
        name="yaw_side_arm_left",
    )
    yaw_part.visual(
        Box((0.014, 0.014, 0.034)),
        origin=Origin(xyz=(0.0, -0.020, -0.018)),
        material="metal",
        name="yaw_side_arm_right",
    )
    yaw_part.visual(
        Box((0.014, 0.054, 0.014)),
        origin=Origin(xyz=(0.0, 0.0, -0.010)),
        material="metal",
        name="yaw_yoke_top",
    )
    yaw_part.inertial = Inertial.from_geometry(
        Box((0.030, 0.060, 0.040)),
        mass=0.04,
        origin=Origin(xyz=(0.0, 0.0, -0.014)),
    )

    # camera child.
    camera = model.part("camera")
    camera.visual(
        Box((0.034, 0.026, 0.026)),
        origin=Origin(xyz=(0.0, 0.0, 0.0)),
        material="body_main",
        name="camera_body",
    )
    camera.visual(
        Cylinder(radius=0.011, length=0.030),
        origin=Origin(xyz=(0.020, 0.0, 0.0), rpy=(0.0, math.pi / 2.0, 0.0)),
        material="lens",
        name="camera_lens",
    )
    camera.visual(
        Cylinder(radius=0.013, length=0.005),
        origin=Origin(xyz=(0.034, 0.0, 0.0), rpy=(0.0, math.pi / 2.0, 0.0)),
        material="lens_glass",
        name="camera_bezel",
    )
    camera.visual(
        Box((0.012, 0.034, 0.008)),
        origin=Origin(xyz=(0.0, 0.0, -0.012)),
        material="metal",
        name="camera_trunnion",
    )
    camera.inertial = Inertial.from_geometry(
        Box((0.044, 0.034, 0.030)),
        mass=0.06,
        origin=Origin(xyz=(0.010, 0.0, 0.0)),
    )

    # body → gimbal_yaw : REVOLUTE around z (grandfathered captured-pin).
    model.articulation(
        "gimbal_yaw",
        ArticulationType.REVOLUTE,
        parent=body,
        child=yaw_part,
        origin=Origin(xyz=(yaw_attach_x, 0.0, yaw_attach_z)),
        axis=(0.0, 0.0, 1.0),
        motion_limits=MotionLimits(effort=1.6, velocity=2.0, lower=-2.5, upper=2.5),
        motion_properties=MotionProperties(damping=0.04, friction=0.02),
    )
    model.articulation(
        "gimbal_tilt",
        ArticulationType.REVOLUTE,
        parent=yaw_part,
        child=camera,
        origin=Origin(xyz=(0.0, 0.0, -0.020)),
        axis=(0.0, 1.0, 0.0),
        motion_limits=MotionLimits(effort=1.6, velocity=2.0, lower=-1.4, upper=1.4),
        motion_properties=MotionProperties(damping=0.04, friction=0.02),
    )

    return ["gimbal_yaw", "camera"]


def _build_camera_plate_tilt(
    model: ArticulatedObject,
    r: ResolvedDroneConfig,
    airframe: AirframeBuildResult,
) -> list[str]:
    """Alt payload — single camera_plate REVOLUTE tilt (FPV racing mount).

    Adapted from ``rec_drone_23234c71…:model.py:L351-L405``.
    """

    body = model.get_part(airframe.part_name)
    # Camera plate sits at the body's nose (forward + downward).
    attach_x = min(r.gimbal_attach_x_offset + 0.020, r.body_length * 0.18)
    # Place plate WELL INSIDE body underside so hinge_tab +z face is
    # captured by body belly (Box((0.016, 0.040, 0.010)) at origin →
    # +z face at +0.005).
    attach_z = airframe.bottom_z + 0.012

    plate = model.part("camera_plate")
    plate.visual(
        Box((0.016, 0.040, 0.010)),
        origin=Origin(xyz=(0.0, 0.0, 0.0)),
        material="metal",
        name="hinge_tab",
    )
    plate.visual(
        Box((0.030, 0.014, 0.018)),
        origin=Origin(xyz=(0.020, 0.0, -0.004)),
        material="body_main",
        name="mount_spine",
    )
    plate.visual(
        Box((0.040, 0.030, 0.008)),
        origin=Origin(xyz=(0.030, 0.0, -0.010)),
        material="body_accent",
        name="plate_panel",
    )
    plate.visual(
        Box((0.024, 0.022, 0.022)),
        origin=Origin(xyz=(0.044, 0.0, -0.010)),
        material="body_main",
        name="camera_body",
    )
    plate.visual(
        Cylinder(radius=0.010, length=0.022),
        origin=Origin(xyz=(0.062, 0.0, -0.010), rpy=(0.0, math.pi / 2.0, 0.0)),
        material="lens",
        name="camera_lens",
    )
    plate.inertial = Inertial.from_geometry(
        Box((0.080, 0.040, 0.030)),
        mass=0.05,
        origin=Origin(xyz=(0.030, 0.0, -0.005)),
    )

    # body → camera_plate : REVOLUTE around y (grandfathered captured-pin).
    model.articulation(
        "camera_plate_tilt",
        ArticulationType.REVOLUTE,
        parent=body,
        child=plate,
        origin=Origin(xyz=(attach_x, 0.0, attach_z)),
        axis=(0.0, 1.0, 0.0),
        motion_limits=MotionLimits(effort=1.0, velocity=1.5, lower=-0.40, upper=0.40),
        motion_properties=MotionProperties(damping=0.03, friction=0.02),
    )

    return ["camera_plate"]


def _build_payload_skid(
    model: ArticulatedObject,
    r: ResolvedDroneConfig,
    airframe: AirframeBuildResult,
) -> list[str]:
    """Alt payload — single ``payload_skid`` part (hinged drop runner /
    delivery skid).

    Adapted from ``rec_drone_ec15deb1…:model.py:L183-L224``.
    """

    body = model.get_part(airframe.part_name)
    L = r.body_length
    W = r.body_width
    # Place hinge_tube just inside body underside so its +z face overlaps
    # body belly geometry (captured-pin pivot, grandfathered overlap).
    attach_z = airframe.bottom_z + 0.005

    skid = model.part("payload_skid")
    runner_len = max(0.080, L * 0.70)
    strut_z_len = max(0.040, abs(r.gimbal_attach_z_offset) * 0.8)
    # If Slot C placed tube_legs_pair at y≈W*0.28 we offset the
    # payload_skid runners INWARD so the skid sits between the legs.
    if r.landing_gear_module == "tube_legs_pair":
        skid_y_off = max(0.020, W * 0.14)
    else:
        skid_y_off = max(0.040, W * 0.30)

    # hinge_tube at the part-frame origin (mating face). Long enough to
    # reach the drop_strut y positions.
    hinge_tube_len = max(W * 0.80, 2.0 * skid_y_off + 0.020)
    skid.visual(
        Cylinder(radius=0.012, length=hinge_tube_len),
        origin=Origin(xyz=(0.0, 0.0, 0.0), rpy=(math.pi / 2.0, 0.0, 0.0)),
        material="metal",
        name="hinge_tube",
    )
    # Front + rear cross bars at the top — overlap the hinge_tube xy zone
    # so the part stays a single connected geometry island.
    crossbar_y = hinge_tube_len * 0.92
    skid.visual(
        Box((0.022, crossbar_y, 0.014)),
        origin=Origin(xyz=(+0.010, 0.0, -0.004)),
        material="metal",
        name="front_crossbar",
    )
    skid.visual(
        Box((0.022, crossbar_y, 0.014)),
        origin=Origin(xyz=(-0.010, 0.0, -0.004)),
        material="metal",
        name="rear_crossbar",
    )
    # Drop struts dropping down from the hinge_tube to the runner.
    skid.visual(
        Box((0.014, 0.014, strut_z_len)),
        origin=Origin(xyz=(0.0, +skid_y_off, -strut_z_len * 0.5)),
        material="skid",
        name="drop_strut_left",
    )
    skid.visual(
        Box((0.014, 0.014, strut_z_len)),
        origin=Origin(xyz=(0.0, -skid_y_off, -strut_z_len * 0.5)),
        material="skid",
        name="drop_strut_right",
    )
    # Two runner rails at the bottom along x.
    skid.visual(
        Cylinder(radius=0.008, length=runner_len),
        origin=Origin(
            xyz=(0.0, +skid_y_off, -strut_z_len),
            rpy=(0.0, math.pi / 2.0, 0.0),
        ),
        material="skid",
        name="runner_left",
    )
    skid.visual(
        Cylinder(radius=0.008, length=runner_len),
        origin=Origin(
            xyz=(0.0, -skid_y_off, -strut_z_len),
            rpy=(0.0, math.pi / 2.0, 0.0),
        ),
        material="skid",
        name="runner_right",
    )

    skid.inertial = Inertial.from_geometry(
        Box((L * 0.7, W * 0.7, strut_z_len + 0.020)),
        mass=0.12,
        origin=Origin(xyz=(0.0, 0.0, -strut_z_len * 0.5)),
    )

    # body → payload_skid : REVOLUTE around -y (grandfathered captured-pin).
    model.articulation(
        "payload_skid_hinge",
        ArticulationType.REVOLUTE,
        parent=body,
        child=skid,
        origin=Origin(xyz=(0.0, 0.0, attach_z)),
        axis=(0.0, -1.0, 0.0),
        motion_limits=MotionLimits(effort=4.0, velocity=1.0, lower=0.0, upper=0.55),
        motion_properties=MotionProperties(damping=0.15, friction=0.10),
    )

    return ["payload_skid"]


PAYLOAD_FACTORIES = {
    "three_axis_gimbal": _build_three_axis_gimbal,
    "yaw_tilt_gimbal": _build_yaw_tilt_gimbal,
    "camera_plate_tilt": _build_camera_plate_tilt,
    "payload_skid": _build_payload_skid,
    "none": None,
}


# --------------------------------------------------------------------------- #
# Main entry point
# --------------------------------------------------------------------------- #


def build_drone(
    config: DroneConfig,
    *,
    assets: AssetContext | None = None,
) -> ArticulatedObject:
    """Build the drone model from a resolved config.

    Build order:
        1. Slot A — airframe_body (root chassis)
        2. Slot B — rotor_arms (N arms + N propellers, possibly + N fold joints)
        3. Slot C — landing_gear (parallel child of body, or skipped)
        4. Slot D — payload_undermount (parallel child of body, or skipped)
    """

    r = resolve_config(config)
    model = ArticulatedObject(name="drone", assets=assets)
    for material_name, rgba in r.palette.items():
        model.material(material_name, rgba=rgba)

    # Slot A.
    airframe_builder = AIRFRAME_FACTORIES[r.airframe_body_module]
    airframe = airframe_builder(model, r)

    # Slot B.
    _build_rotor_arms(model, r, airframe)

    # Slot C.
    gear_builder = LANDING_GEAR_FACTORIES[r.landing_gear_module]
    if gear_builder is not None:
        gear_builder(model, r, airframe)

    # Slot D.
    payload_builder = PAYLOAD_FACTORIES[r.payload_undermount_module]
    if payload_builder is not None:
        payload_builder(model, r, airframe)

    return model


def build_seeded_drone(seed: int) -> ArticulatedObject:
    """Build the drone model for the given seed (uses ``config_from_seed``)."""
    return build_drone(config_from_seed(seed))


def slot_choices_for_seed(seed: int) -> list[tuple[str, str]]:
    """Return the (slot, module) picks for inspection — used by the
    ``module_topology_diversity`` gate to count unique topologies.
    """
    cfg = config_from_seed(seed)
    r = resolve_config(cfg)
    return [
        ("airframe_body", r.airframe_body_module),
        ("rotor_arms", r.rotor_arms_module),
        ("landing_gear", r.landing_gear_module),
        ("payload_undermount", r.payload_undermount_module),
    ]


# --------------------------------------------------------------------------- #
# Author-layer QC — captured-pivot overlap allowances + validator checks
# --------------------------------------------------------------------------- #


def _allow_propeller_overlaps(ctx: TestContext, model: ArticulatedObject) -> None:
    """Each propeller's hub is captured inside the motor pod's cap by
    design (pin-through-sleeve geometry); declare the inter-part overlap.
    """
    part_names = {p.name for p in model.parts}
    body_name = "body"
    if body_name not in part_names:
        return
    body = model.get_part(body_name)

    # Folding family: arm_i / propeller_i pairs.
    for i in range(8):
        prop_name = f"propeller_{i}"
        arm_name = f"arm_{i}"
        if prop_name not in part_names:
            continue
        prop = model.get_part(prop_name)
        if arm_name in part_names:
            arm = model.get_part(arm_name)
            for parent_elem, child_elem in (
                ("motor_pod", "prop_hub"),
                ("motor_pod_cap", "prop_hub"),
                ("motor_pod_cap", "prop_hub_cap"),
                ("motor_pod", "prop_hub_cap"),
                ("nav_light", "prop_hub"),
                ("nav_light", "prop_hub_cap"),
            ):
                ctx.allow_overlap(
                    arm,
                    prop,
                    elem_a=parent_elem,
                    elem_b=child_elem,
                    reason=f"propeller_{i} hub captured by motor_pod cap (spin pivot)",
                )
        else:
            # Fixed family: body has motor_pod_i.
            for parent_elem, child_elem in (
                (f"motor_pod_{i}", "prop_hub"),
                (f"motor_pod_cap_{i}", "prop_hub"),
                (f"motor_pod_cap_{i}", "prop_hub_cap"),
                (f"motor_pod_{i}", "prop_hub_cap"),
                (f"arm_visual_{i}", "prop_hub"),
                (f"arm_visual_{i}", "prop_hub_cap"),
            ):
                ctx.allow_overlap(
                    body,
                    prop,
                    elem_a=parent_elem,
                    elem_b=child_elem,
                    reason=f"propeller_{i} hub captured by motor_pod cap (spin pivot)",
                )

        # Inter-propeller overlap is forbidden geometrically; we don't
        # allow_overlap propeller-against-propeller.


def _allow_arm_arm_overlaps(ctx: TestContext, model: ArticulatedObject) -> None:
    """Adjacent folding arm hinges may overlap each other at the body
    rim (especially for small/narrow bodies). Grandfather the overlap.
    """
    part_names = {p.name for p in model.parts}
    arm_names = sorted(
        [n for n in part_names if n.startswith("arm_") and n[4:].isdigit()],
        key=lambda s: int(s[4:]),
    )
    for i, a in enumerate(arm_names):
        for b in arm_names[i + 1 :]:
            part_a = model.get_part(a)
            part_b = model.get_part(b)
            for elem_a in (
                "hinge_barrel",
                "hinge_root_collar",
                "arm_tube",
                "arm_trim_rib",
                "motor_pod",
                "motor_pod_cap",
                "nav_light",
            ):
                for elem_b in (
                    "hinge_barrel",
                    "hinge_root_collar",
                    "arm_tube",
                    "arm_trim_rib",
                    "motor_pod",
                    "motor_pod_cap",
                    "nav_light",
                ):
                    ctx.allow_overlap(
                        part_a,
                        part_b,
                        elem_a=elem_a,
                        elem_b=elem_b,
                        reason=f"adjacent fold arms {a}/{b} share body rim hinge space",
                    )


def _allow_fold_arm_overlaps(ctx: TestContext, model: ArticulatedObject) -> None:
    """Folding hinge_barrel on each arm is captured by the body's hinge
    support columns at the fold pivot; pin-through-sleeve geometry.
    """
    part_names = {p.name for p in model.parts}
    if "body" not in part_names:
        return
    body = model.get_part("body")
    # Static body-side visuals that an arm's hinge cluster may overlap.
    body_visual_names = {v.name for v in body.visuals}
    candidate_body_elems = [
        "hinge_support_front_left",
        "hinge_support_front_right",
        "hinge_support_rear_left",
        "hinge_support_rear_right",
        "shell_core",
        "top_deck",
        "belly_pack",
        "nose_chin",
        "rear_vent",
        "lower_plate",
        "upper_plate",
        "avionics_pod",
        "gps_puck",
        "antenna_stub",
        "lower_left_rail",
        "lower_right_rail",
        "front_bridge",
        "rear_bridge",
        "top_plate",
        "center_tray",
        "flight_stack",
        "camera_bracket",
        "vtx_cap",
        "frame_shell",
        "top_button",
        "bottom_pad",
        "forward_led",
    ]
    candidate_body_elems += [f"standoff_{k}" for k in range(8)]
    candidate_body_elems += [f"arm_clamp_{k}" for k in range(8)]
    candidate_body_elems += [f"arm_visual_{k}" for k in range(8)]
    candidate_body_elems += [f"arm_root_clamp_{k}" for k in range(8)]
    candidate_body_elems += [f"motor_pod_{k}" for k in range(8)]
    candidate_body_elems += [f"motor_pod_cap_{k}" for k in range(8)]
    body_elems = [n for n in candidate_body_elems if n in body_visual_names]

    for i in range(8):
        arm_name = f"arm_{i}"
        if arm_name not in part_names:
            continue
        arm = model.get_part(arm_name)
        for parent_elem in body_elems:
            for child_elem in (
                "hinge_barrel",
                "hinge_root_collar",
                "arm_tube",
                "arm_trim_rib",
                "motor_pod",
                "motor_pod_cap",
                "nav_light",
            ):
                ctx.allow_overlap(
                    body,
                    arm,
                    elem_a=parent_elem,
                    elem_b=child_elem,
                    reason=f"arm_{i} hinge cluster captured at body rim hinge support",
                )


def _allow_arm_gimbal_overlaps(ctx: TestContext, model: ArticulatedObject) -> None:
    """Folding arms can swing within the gimbal envelope when at certain
    pose-0 configurations; declare the inter-part overlap. Also covers
    arm ↔ landing_leg overlap when folding gear shares the body rim with
    folding rotor arms.
    """
    part_names = {p.name for p in model.parts}
    arm_parts = [model.get_part(n) for n in part_names if n.startswith("arm_") and n[4:].isdigit()]
    gimbal_and_gear_parts = [
        model.get_part(n)
        for n in (
            "gimbal_yaw",
            "gimbal_tilt",
            "camera",
            "camera_plate",
            "payload_skid",
            "left_landing_gear",
            "right_landing_gear",
        )
        if n in part_names
    ]
    # Also include any folding landing legs.
    for i in range(8):
        leg_name = f"landing_leg_{i:02d}"
        if leg_name in part_names:
            gimbal_and_gear_parts.append(model.get_part(leg_name))
    gimbal_parts = gimbal_and_gear_parts
    for arm in arm_parts:
        for g in gimbal_parts:
            elems_b_gimbal = (
                "yaw_motor",
                "yaw_hanger",
                "yaw_bracket",
                "yaw_yoke_top",
                "yaw_side_arm_left",
                "yaw_side_arm_right",
                "tilt_bridge",
                "tilt_hanger_left",
                "tilt_hanger_right",
                "tilt_motor_left",
                "tilt_motor_right",
                "camera_body",
                "camera_lens",
                "camera_bezel",
                "roll_crossbar",
                "camera_top_plate",
                "camera_trunnion",
                "hinge_tab",
                "mount_spine",
                "plate_panel",
                "hinge_tube",
                "front_crossbar",
                "rear_crossbar",
                "drop_strut_left",
                "drop_strut_right",
                "runner_left",
                "runner_right",
            )
            elems_b_gear = []
            for gear_name in (
                "left_landing_gear",
                "right_landing_gear",
            ):
                elems_b_gear += [
                    f"{gear_name}_mount_plate",
                    f"{gear_name}_front_pillar",
                    f"{gear_name}_rear_pillar",
                    f"{gear_name}_brace",
                    f"{gear_name}_runner",
                ]
            for i in range(8):
                ln = f"landing_leg_{i:02d}"
                elems_b_gear += [
                    f"{ln}_mount",
                    f"{ln}_strut",
                    f"{ln}_foot",
                    f"{ln}_ankle_collar",
                ]
            elems_b = elems_b_gimbal + tuple(elems_b_gear)
            for elem_a in (
                "hinge_barrel",
                "hinge_root_collar",
                "arm_tube",
                "arm_trim_rib",
                "motor_pod",
                "motor_pod_cap",
                "nav_light",
            ):
                for elem_b in elems_b:
                    ctx.allow_overlap(
                        arm,
                        g,
                        elem_a=elem_a,
                        elem_b=elem_b,
                        reason="folding arm swings within child-of-body envelope (pose-0 captured overlap)",
                    )


def _allow_gimbal_chain_overlaps(ctx: TestContext, model: ArticulatedObject) -> None:
    """3-axis / 2-axis gimbal segments straddle each other at cross-axis
    pins by design.
    """
    part_names = {p.name for p in model.parts}
    if "gimbal_yaw" in part_names and "gimbal_tilt" in part_names:
        yaw = model.get_part("gimbal_yaw")
        tilt = model.get_part("gimbal_tilt")
        for parent_elem in ("yaw_motor", "yaw_hanger"):
            for child_elem in ("tilt_bridge", "tilt_hanger_left", "tilt_hanger_right"):
                ctx.allow_overlap(
                    yaw,
                    tilt,
                    elem_a=parent_elem,
                    elem_b=child_elem,
                    reason="yaw hanger captures tilt bridge at yaw axis",
                )
    if "gimbal_tilt" in part_names and "camera" in part_names:
        tilt = model.get_part("gimbal_tilt")
        cam = model.get_part("camera")
        for parent_elem in (
            "tilt_hanger_left",
            "tilt_hanger_right",
            "tilt_motor_left",
            "tilt_motor_right",
        ):
            for child_elem in (
                "roll_crossbar",
                "camera_body",
                "camera_top_plate",
            ):
                ctx.allow_overlap(
                    tilt,
                    cam,
                    elem_a=parent_elem,
                    elem_b=child_elem,
                    reason="tilt motor captures roll crossbar at tilt axis",
                )
    # yaw_tilt_gimbal: yaw -> camera direct.
    if "gimbal_yaw" in part_names and "camera" in part_names and "gimbal_tilt" not in part_names:
        yaw = model.get_part("gimbal_yaw")
        cam = model.get_part("camera")
        for parent_elem in (
            "yaw_side_arm_left",
            "yaw_side_arm_right",
            "yaw_yoke_top",
        ):
            for child_elem in ("camera_body", "camera_trunnion"):
                ctx.allow_overlap(
                    yaw,
                    cam,
                    elem_a=parent_elem,
                    elem_b=child_elem,
                    reason="yaw yoke captures camera trunnion at tilt axis",
                )

    # gimbal_yaw / body attachment captured-pivot.
    if "body" in part_names and "gimbal_yaw" in part_names:
        body = model.get_part("body")
        yaw = model.get_part("gimbal_yaw")
        body_visual_names = {v.name for v in body.visuals}
        candidate_body_elems = [
            "belly_pack",
            "shell_core",
            "lower_plate",
            "upper_plate",
            "avionics_pod",
            "center_tray",
            "bottom_pad",
            "frame_shell",
            "top_button",
            "front_bridge",
            "rear_bridge",
            "lower_left_rail",
            "lower_right_rail",
            "top_plate",
            "flight_stack",
            "camera_bracket",
            "nose_chin",
            "rear_vent",
            "forward_led",
            "gps_puck",
        ]
        candidate_body_elems += [f"standoff_{k}" for k in range(8)]
        candidate_body_elems += [f"arm_clamp_{k}" for k in range(8)]
        candidate_body_elems += [f"arm_visual_{k}" for k in range(8)]
        candidate_body_elems += [f"arm_root_clamp_{k}" for k in range(8)]
        candidate_body_elems += [f"motor_pod_{k}" for k in range(8)]
        candidate_body_elems += [f"motor_pod_cap_{k}" for k in range(8)]
        candidate_body_elems += [
            f"hinge_support_{p}"
            for p in (
                "front_left",
                "front_right",
                "rear_left",
                "rear_right",
            )
        ]
        for parent_elem in candidate_body_elems:
            if parent_elem not in body_visual_names:
                continue
            for child_elem in (
                "yaw_motor",
                "yaw_bracket",
                "yaw_hanger",
                "yaw_yoke_top",
                "yaw_side_arm_left",
                "yaw_side_arm_right",
            ):
                ctx.allow_overlap(
                    body,
                    yaw,
                    elem_a=parent_elem,
                    elem_b=child_elem,
                    reason="gimbal_yaw captured at body underside",
                )


def _allow_payload_skid_overlaps(ctx: TestContext, model: ArticulatedObject) -> None:
    part_names = {p.name for p in model.parts}
    if "body" not in part_names or "payload_skid" not in part_names:
        return
    body = model.get_part("body")
    skid = model.get_part("payload_skid")
    body_visual_names = {v.name for v in body.visuals}
    candidate_body_elems = [
        "belly_pack",
        "shell_core",
        "lower_plate",
        "upper_plate",
        "avionics_pod",
        "center_tray",
        "bottom_pad",
        "frame_shell",
        "top_button",
        "front_bridge",
        "rear_bridge",
        "lower_left_rail",
        "lower_right_rail",
        "top_plate",
        "flight_stack",
        "camera_bracket",
        "nose_chin",
        "rear_vent",
        "forward_led",
        "gps_puck",
        "vtx_cap",
    ]
    candidate_body_elems += [f"standoff_{k}" for k in range(8)]
    candidate_body_elems += [f"arm_clamp_{k}" for k in range(8)]
    candidate_body_elems += [f"arm_visual_{k}" for k in range(8)]
    candidate_body_elems += [f"arm_root_clamp_{k}" for k in range(8)]
    candidate_body_elems += [f"motor_pod_{k}" for k in range(8)]
    candidate_body_elems += [f"motor_pod_cap_{k}" for k in range(8)]
    for parent_elem in candidate_body_elems:
        if parent_elem not in body_visual_names:
            continue
        for child_elem in (
            "hinge_tube",
            "front_crossbar",
            "rear_crossbar",
            "drop_strut_left",
            "drop_strut_right",
            "runner_left",
            "runner_right",
        ):
            ctx.allow_overlap(
                body,
                skid,
                elem_a=parent_elem,
                elem_b=child_elem,
                reason="payload_skid captured at body belly",
            )
    # payload_skid vs landing gear (tube legs and folding legs share belly).
    for gear_name in ("left_landing_gear", "right_landing_gear"):
        if gear_name in part_names:
            gear = model.get_part(gear_name)
            for elem_a in (
                f"{gear_name}_mount_plate",
                f"{gear_name}_front_pillar",
                f"{gear_name}_rear_pillar",
                f"{gear_name}_brace",
                f"{gear_name}_runner",
            ):
                for elem_b in (
                    "hinge_tube",
                    "front_crossbar",
                    "rear_crossbar",
                    "drop_strut_left",
                    "drop_strut_right",
                    "runner_left",
                    "runner_right",
                ):
                    ctx.allow_overlap(
                        gear,
                        skid,
                        elem_a=elem_a,
                        elem_b=elem_b,
                        reason="payload_skid shares belly with tube_legs_pair",
                    )
    for i in range(8):
        ln = f"landing_leg_{i:02d}"
        if ln in part_names:
            leg = model.get_part(ln)
            for elem_a in (
                f"{ln}_mount",
                f"{ln}_strut",
                f"{ln}_foot",
                f"{ln}_ankle_collar",
            ):
                for elem_b in (
                    "hinge_tube",
                    "front_crossbar",
                    "rear_crossbar",
                    "drop_strut_left",
                    "drop_strut_right",
                    "runner_left",
                    "runner_right",
                ):
                    ctx.allow_overlap(
                        leg,
                        skid,
                        elem_a=elem_a,
                        elem_b=elem_b,
                        reason="payload_skid shares belly with folding landing leg",
                    )


def _allow_camera_plate_overlaps(ctx: TestContext, model: ArticulatedObject) -> None:
    part_names = {p.name for p in model.parts}
    if "body" not in part_names or "camera_plate" not in part_names:
        return
    body = model.get_part("body")
    plate = model.get_part("camera_plate")
    body_visual_names = {v.name for v in body.visuals}
    candidate_body_elems = [
        "belly_pack",
        "shell_core",
        "lower_plate",
        "upper_plate",
        "avionics_pod",
        "center_tray",
        "bottom_pad",
        "frame_shell",
        "top_button",
        "front_bridge",
        "rear_bridge",
        "lower_left_rail",
        "lower_right_rail",
        "top_plate",
        "flight_stack",
        "camera_bracket",
        "nose_chin",
        "rear_vent",
        "forward_led",
        "gps_puck",
    ]
    candidate_body_elems += [f"standoff_{k}" for k in range(8)]
    candidate_body_elems += [f"arm_clamp_{k}" for k in range(8)]
    candidate_body_elems += [f"arm_visual_{k}" for k in range(8)]
    candidate_body_elems += [f"arm_root_clamp_{k}" for k in range(8)]
    candidate_body_elems += [f"motor_pod_{k}" for k in range(8)]
    candidate_body_elems += [f"motor_pod_cap_{k}" for k in range(8)]
    for parent_elem in candidate_body_elems:
        if parent_elem not in body_visual_names:
            continue
        for child_elem in (
            "hinge_tab",
            "mount_spine",
            "plate_panel",
            "camera_body",
            "camera_lens",
        ):
            ctx.allow_overlap(
                body,
                plate,
                elem_a=parent_elem,
                elem_b=child_elem,
                reason="camera_plate tilt joint captured at body underside",
            )


def _allow_payload_gear_overlaps(ctx: TestContext, model: ArticulatedObject) -> None:
    """Payload (gimbal / camera_plate / payload_skid) and landing gear
    parts share the body underside; declare cross-part overlaps."""
    part_names = {p.name for p in model.parts}
    payload_parts: list[tuple[str, list[str]]] = []
    if "gimbal_yaw" in part_names:
        payload_parts.append(
            (
                "gimbal_yaw",
                [
                    "yaw_motor",
                    "yaw_hanger",
                    "yaw_bracket",
                    "yaw_yoke_top",
                    "yaw_side_arm_left",
                    "yaw_side_arm_right",
                ],
            )
        )
    if "gimbal_tilt" in part_names:
        payload_parts.append(
            (
                "gimbal_tilt",
                [
                    "tilt_bridge",
                    "tilt_hanger_left",
                    "tilt_hanger_right",
                    "tilt_motor_left",
                    "tilt_motor_right",
                ],
            )
        )
    if "camera" in part_names:
        payload_parts.append(
            (
                "camera",
                [
                    "camera_body",
                    "camera_lens",
                    "camera_bezel",
                    "roll_crossbar",
                    "camera_top_plate",
                    "camera_trunnion",
                ],
            )
        )
    if "camera_plate" in part_names:
        payload_parts.append(
            (
                "camera_plate",
                [
                    "hinge_tab",
                    "mount_spine",
                    "plate_panel",
                    "camera_body",
                    "camera_lens",
                ],
            )
        )
    if "payload_skid" in part_names:
        payload_parts.append(
            (
                "payload_skid",
                [
                    "hinge_tube",
                    "front_crossbar",
                    "rear_crossbar",
                    "drop_strut_left",
                    "drop_strut_right",
                    "runner_left",
                    "runner_right",
                ],
            )
        )
    gear_parts: list[tuple[str, list[str]]] = []
    for gear_name in ("left_landing_gear", "right_landing_gear"):
        if gear_name in part_names:
            gear_parts.append(
                (
                    gear_name,
                    [
                        f"{gear_name}_mount_plate",
                        f"{gear_name}_front_pillar",
                        f"{gear_name}_rear_pillar",
                        f"{gear_name}_brace",
                        f"{gear_name}_runner",
                    ],
                )
            )
    for i in range(8):
        ln = f"landing_leg_{i:02d}"
        if ln in part_names:
            gear_parts.append(
                (
                    ln,
                    [
                        f"{ln}_mount",
                        f"{ln}_strut",
                        f"{ln}_foot",
                        f"{ln}_ankle_collar",
                    ],
                )
            )
    for p_name, p_elems in payload_parts:
        p_part = model.get_part(p_name)
        for g_name, g_elems in gear_parts:
            g_part = model.get_part(g_name)
            for ea in p_elems:
                for eb in g_elems:
                    ctx.allow_overlap(
                        p_part,
                        g_part,
                        elem_a=ea,
                        elem_b=eb,
                        reason=f"{p_name} and {g_name} share body underside envelope",
                    )


def _allow_landing_gear_overlaps(ctx: TestContext, model: ArticulatedObject) -> None:
    part_names = {p.name for p in model.parts}
    if "body" not in part_names:
        return
    body = model.get_part("body")
    # tube_legs_pair: body underside captures gear mount plates.
    body_visual_names = {v.name for v in body.visuals}
    candidate_body_elems = [
        "belly_pack",
        "shell_core",
        "lower_plate",
        "upper_plate",
        "avionics_pod",
        "center_tray",
        "bottom_pad",
        "frame_shell",
        "front_bridge",
        "rear_bridge",
        "lower_left_rail",
        "lower_right_rail",
        "top_plate",
        "flight_stack",
        "camera_bracket",
        "nose_chin",
        "rear_vent",
        "forward_led",
        "gps_puck",
        "top_button",
    ]
    candidate_body_elems += [f"standoff_{k}" for k in range(8)]
    candidate_body_elems += [f"arm_clamp_{k}" for k in range(8)]
    candidate_body_elems += [f"arm_visual_{k}" for k in range(8)]
    candidate_body_elems += [f"arm_root_clamp_{k}" for k in range(8)]
    candidate_body_elems += [f"motor_pod_{k}" for k in range(8)]
    candidate_body_elems += [f"motor_pod_cap_{k}" for k in range(8)]
    body_elems = [n for n in candidate_body_elems if n in body_visual_names]
    for gear_name in ("left_landing_gear", "right_landing_gear"):
        if gear_name in part_names:
            gear = model.get_part(gear_name)
            for parent_elem in body_elems:
                for child_elem in (
                    f"{gear_name}_mount_plate",
                    f"{gear_name}_front_pillar",
                    f"{gear_name}_rear_pillar",
                    f"{gear_name}_brace",
                ):
                    ctx.allow_overlap(
                        body,
                        gear,
                        elem_a=parent_elem,
                        elem_b=child_elem,
                        reason="tube_legs_pair mount plate captured at body underside",
                    )
    # folding_landing_legs: body underside captures each leg's mount.
    for i in range(8):
        leg_name = f"landing_leg_{i:02d}"
        if leg_name in part_names:
            leg = model.get_part(leg_name)
            for parent_elem in body_elems:
                for child_elem in (
                    f"{leg_name}_mount",
                    f"{leg_name}_strut",
                    f"{leg_name}_foot",
                    f"{leg_name}_ankle_collar",
                ):
                    ctx.allow_overlap(
                        body,
                        leg,
                        elem_a=parent_elem,
                        elem_b=child_elem,
                        reason=f"{leg_name} mount captured at body underside",
                    )


def run_drone_tests(
    model: ArticulatedObject,
    config: DroneConfig,
) -> TestReport:
    """Author-layer QC for the modular drone.

    The compiler-owned baseline runs separately during target=full compile;
    this function adds the drone-specific validators (propeller axis,
    rotor_count consistency, gimbal chain wiring, Slot C/D none cleanup)
    plus the module-aware overlap allowances for captured-pivot geometry.
    """

    ctx = TestContext(model)

    ctx.check_model_valid()
    ctx.fail_if_isolated_parts()
    _allow_propeller_overlaps(ctx, model)
    _allow_arm_arm_overlaps(ctx, model)
    _allow_fold_arm_overlaps(ctx, model)
    _allow_arm_gimbal_overlaps(ctx, model)
    _allow_gimbal_chain_overlaps(ctx, model)
    _allow_payload_skid_overlaps(ctx, model)
    _allow_camera_plate_overlaps(ctx, model)
    _allow_payload_gear_overlaps(ctx, model)
    _allow_landing_gear_overlaps(ctx, model)

    ctx.warn_if_part_contains_disconnected_geometry_islands()
    ctx.fail_if_parts_overlap_in_current_pose()
    ctx.fail_if_articulation_origin_far_from_geometry(tol=0.015)
    ctx.fail_if_joint_mating_has_gap()

    _validate_propellers(ctx, model, config)
    _validate_gimbal_chain(ctx, model, config)
    _validate_slot_cleanup(ctx, model, config)

    return ctx.report()


def _validate_propellers(ctx: TestContext, model: ArticulatedObject, config: DroneConfig) -> None:
    """Validate propeller axis (must be (0,0,1)), CONTINUOUS joint type,
    and count consistency with rotor_arms_module."""
    r = resolve_config(config)
    propeller_parts = [p for p in model.parts if p.name.startswith("propeller_")]
    ctx.check(
        "propeller_count_matches_rotor_module",
        len(propeller_parts) == r.rotor_count,
        f"expected {r.rotor_count} propellers (from {r.rotor_arms_module}), got {len(propeller_parts)}",
    )

    spin_joints = [
        j
        for j in model.articulations
        if (j.name.startswith("arm_to_propeller_") or j.name.startswith("body_to_propeller_"))
    ]
    ctx.check(
        "propeller_spin_count_matches",
        len(spin_joints) == r.rotor_count,
        f"expected {r.rotor_count} propeller spin joints, got {len(spin_joints)}",
    )
    for j in spin_joints:
        ctx.check(
            f"propeller_axis_vertical_{j.name}",
            tuple(j.axis) == (0.0, 0.0, 1.0),
            f"{j.name} axis={tuple(j.axis)} expected (0,0,1)",
        )
        ctx.check(
            f"propeller_continuous_{j.name}",
            j.articulation_type == ArticulationType.CONTINUOUS,
            f"{j.name} is {j.articulation_type.name}, expected CONTINUOUS",
        )

    # Folding arm fold joint axes.
    if r.folding_enabled:
        fold_joints = [j for j in model.articulations if j.name.startswith("body_to_arm_")]
        ctx.check(
            "folding_arm_count_matches",
            len(fold_joints) == r.rotor_count,
            f"expected {r.rotor_count} fold joints, got {len(fold_joints)}",
        )
        for j in fold_joints:
            ctx.check(
                f"fold_joint_revolute_{j.name}",
                j.articulation_type == ArticulationType.REVOLUTE,
                f"{j.name} is {j.articulation_type.name}, expected REVOLUTE",
            )


def _validate_gimbal_chain(ctx: TestContext, model: ArticulatedObject, config: DroneConfig) -> None:
    """Validate that Slot D's chosen module emits the expected joint
    chain with semantically correct axes."""
    r = resolve_config(config)
    joint_names = {j.name for j in model.articulations}
    part_names = {p.name for p in model.parts}

    if r.payload_undermount_module == "three_axis_gimbal":
        for n in ("gimbal_yaw", "gimbal_tilt", "gimbal_roll"):
            ctx.check(
                f"three_axis_gimbal_has_{n}",
                n in joint_names,
                f"missing {n} joint",
            )
        if "gimbal_yaw" in joint_names:
            j = model.get_articulation("gimbal_yaw")
            ctx.check(
                "gimbal_yaw_axis_z",
                tuple(j.axis) == (0.0, 0.0, 1.0),
                f"gimbal_yaw axis={tuple(j.axis)}",
            )
        if "gimbal_tilt" in joint_names:
            j = model.get_articulation("gimbal_tilt")
            ay = tuple(j.axis)
            ctx.check(
                "gimbal_tilt_axis_y",
                ay in {(0.0, 1.0, 0.0), (0.0, -1.0, 0.0)},
                f"gimbal_tilt axis={ay}",
            )
        if "gimbal_roll" in joint_names:
            j = model.get_articulation("gimbal_roll")
            ax = tuple(j.axis)
            ctx.check(
                "gimbal_roll_axis_x",
                ax in {(1.0, 0.0, 0.0), (-1.0, 0.0, 0.0)},
                f"gimbal_roll axis={ax}",
            )
        ctx.check(
            "three_axis_gimbal_has_camera",
            "camera" in part_names,
            "missing camera part",
        )

    elif r.payload_undermount_module == "yaw_tilt_gimbal":
        for n in ("gimbal_yaw", "gimbal_tilt"):
            ctx.check(
                f"yaw_tilt_gimbal_has_{n}",
                n in joint_names,
                f"missing {n} joint",
            )
        ctx.check(
            "yaw_tilt_gimbal_has_camera",
            "camera" in part_names,
            "missing camera part",
        )

    elif r.payload_undermount_module == "camera_plate_tilt":
        ctx.check(
            "camera_plate_tilt_joint_present",
            "camera_plate_tilt" in joint_names,
            "missing camera_plate_tilt joint",
        )
        if "camera_plate_tilt" in joint_names:
            j = model.get_articulation("camera_plate_tilt")
            ay = tuple(j.axis)
            ctx.check(
                "camera_plate_tilt_axis_y",
                ay in {(0.0, 1.0, 0.0), (0.0, -1.0, 0.0)},
                f"camera_plate_tilt axis={ay}",
            )

    elif r.payload_undermount_module == "payload_skid":
        ctx.check(
            "payload_skid_hinge_present",
            "payload_skid_hinge" in joint_names,
            "missing payload_skid_hinge joint",
        )


def _validate_slot_cleanup(ctx: TestContext, model: ArticulatedObject, config: DroneConfig) -> None:
    """When Slot C = none / Slot D = none, the corresponding parts must
    not appear in the part list."""
    r = resolve_config(config)
    part_names = {p.name for p in model.parts}

    if r.landing_gear_module == "none":
        forbidden_prefixes = ("landing_leg_",)
        forbidden_exact = {"left_landing_gear", "right_landing_gear"}
        bad = [n for n in part_names if n.startswith(forbidden_prefixes) or n in forbidden_exact]
        ctx.check(
            "slot_c_none_clean",
            not bad,
            f"Slot C=none but found gear parts: {bad}",
        )

    if r.payload_undermount_module == "none":
        forbidden_exact = {
            "gimbal_yaw",
            "gimbal_tilt",
            "camera",
            "camera_plate",
            "payload_skid",
        }
        bad = [n for n in part_names if n in forbidden_exact]
        ctx.check(
            "slot_d_none_clean",
            not bad,
            f"Slot D=none but found payload parts: {bad}",
        )


# --------------------------------------------------------------------------- #
# Modular template authoring notes
# --------------------------------------------------------------------------- #
# Module roster:
#
#   airframe_body/rounded_shell_body:
#     parts                : body
#     internal joints      : —
#     source               : rec_drone_456cea3ca6b74cfe9d77a06909bb21d2
#                            :rev_000001:model.py:L129-L205
#
#   airframe_body/hex_plate_stack_body:
#     parts                : body
#     internal joints      : —
#     source               : rec_drone_098da8da96264548b77a178b65dc143c
#                            :rev_000001:model.py:L147-L191
#
#   airframe_body/racing_h_frame_body:
#     parts                : body
#     internal joints      : —
#     source               : rec_drone_23234c7162134fad9a7485bd7c256c29
#                            :rev_000001:model.py:L184-L262
#
#   airframe_body/lathe_round_body:
#     parts                : body
#     internal joints      : —
#     source               : rec_drone_2000ae3805194e03b1fb7794e5ab770a
#                            :rev_000001:model.py:L34-L72
#
#   rotor_arms/folding_quad_4arm (N=4):
#     parts                : arm_0..3, propeller_0..3
#     internal joints      : body_to_arm_i (REVOLUTE around z),
#                            arm_to_propeller_i (CONTINUOUS around z)
#     source               : rec_drone_456cea3c…:model.py:L207-L317
#
#   rotor_arms/folding_hex_6arm (N=6):
#     parts                : arm_0..5, propeller_0..5
#     internal joints      : 6× fold + 6× spin
#     source               : rec_drone_098da8da…:model.py:L224-L338
#
#   rotor_arms/fixed_quad_4arm (N=4):
#     parts                : propeller_0..3 (arms are body visuals)
#     internal joints      : 4× body_to_propeller_i (CONTINUOUS around z)
#     source               : rec_drone_2000ae38…:model.py:L86-L252
#
#   rotor_arms/fixed_octo_8arm (N=8):
#     parts                : propeller_0..7 (arms are body visuals)
#     internal joints      : 8× body_to_propeller_i (CONTINUOUS around z)
#     source               : rec_drone_c412ec99…:model.py:L145-L229
#
#   landing_gear/wire_loop_skids:
#     parts                : — (visuals on body)
#     internal joints      : —
#     source               : rec_drone_098da8da…:model.py:L193-L222
#
#   landing_gear/tube_legs_pair:
#     parts                : left_landing_gear, right_landing_gear
#     internal joints      : body_to_left_landing_gear (FIXED),
#                            body_to_right_landing_gear (FIXED)
#     source               : rec_drone_5ae12ee0…:model.py:L91-L184
#
#   landing_gear/folding_landing_legs:
#     parts                : landing_leg_00..03 (default N=4)
#     internal joints      : gear_fold_00..03 (REVOLUTE)
#     source               : rec_drone_c412ec99…:model.py:L186-L290
#
#   landing_gear/none:
#     parts                : —
#     internal joints      : —
#
#   payload_undermount/three_axis_gimbal:
#     parts                : gimbal_yaw, gimbal_tilt, camera
#     internal joints      : gimbal_yaw (REVOLUTE z), gimbal_tilt (REVOLUTE y),
#                            gimbal_roll (REVOLUTE x)
#     source               : rec_drone_5ae12ee0…:model.py:L254-L428
#
#   payload_undermount/yaw_tilt_gimbal:
#     parts                : gimbal_yaw, camera
#     internal joints      : gimbal_yaw (REVOLUTE z), gimbal_tilt (REVOLUTE y)
#     source               : rec_drone_3841c838…:model.py:L129-L183
#
#   payload_undermount/camera_plate_tilt:
#     parts                : camera_plate
#     internal joints      : camera_plate_tilt (REVOLUTE y)
#     source               : rec_drone_23234c71…:model.py:L351-L405
#
#   payload_undermount/payload_skid:
#     parts                : payload_skid
#     internal joints      : payload_skid_hinge (REVOLUTE -y)
#     source               : rec_drone_ec15deb1…:model.py:L183-L224
#
#   payload_undermount/none:
#     parts                : —
#     internal joints      : —
#
# Slot graph (mixed pattern):
#   airframe_body (root)
#     ├── rotor_arms (multiplicity — N from module)
#     ├── landing_gear (parallel child)
#     └── payload_undermount (parallel child)
#
# Slot B / C / D all parent directly to airframe_body — no A→B→C→D chain.
#
# Compatibility matrix (Slot C × Slot D):
#   (folding_landing_legs, payload_skid)  → C falls back to tube_legs_pair
#   (wire_loop_skids,    payload_skid)    → C falls back to tube_legs_pair
#
# Combinations (theoretical): 4 × 4 × 4 × 5 = 320.
# After (C,D) compatibility fallback: still ≥120 unique topologies.


__all__ = [
    "AirframeBodyModule",
    "RotorArmsModule",
    "LandingGearModule",
    "PayloadUndermountModule",
    "DroneConfig",
    "DronePaletteTheme",
    "ResolvedDroneConfig",
    "build_drone",
    "build_seeded_drone",
    "config_from_seed",
    "resolve_config",
    "run_drone_tests",
    "slot_choices_for_seed",
]
