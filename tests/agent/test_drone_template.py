from __future__ import annotations

import pytest

from agent.templates.drone import (
    _GEAR_CANDIDATES,
    _PAYLOAD_CANDIDATES,
    _ROTOR_CANDIDATES,
    ROTOR_MODULE_N,
    DroneConfig,
    build_drone,
    build_seeded_drone,
    config_from_seed,
    resolve_config,
    run_drone_tests,
    slot_choices_for_seed,
)
from sdk import ArticulationType, Mesh


def test_seed_config_is_reproducible() -> None:
    assert config_from_seed(11) == config_from_seed(11)
    assert config_from_seed(11) != config_from_seed(12)


def test_seed_zero_is_anchor_combination() -> None:
    choices = slot_choices_for_seed(0)
    assert choices == [
        ("airframe_body", "rounded_shell_body"),
        ("rotor_arms", "folding_quad_4arm"),
        ("landing_gear", "tube_legs_pair"),
        ("payload_undermount", "three_axis_gimbal"),
    ]


def test_seed_zero_part_tree_matches_anchor() -> None:
    """seed=0 reproduces the anchor combo (rounded_shell_body +
    folding_quad_4arm + tube_legs_pair + three_axis_gimbal)."""
    model = build_seeded_drone(0)
    part_names = {p.name for p in model.parts}
    expected = {
        "body",
        "arm_0",
        "arm_1",
        "arm_2",
        "arm_3",
        "propeller_0",
        "propeller_1",
        "propeller_2",
        "propeller_3",
        "left_landing_gear",
        "right_landing_gear",
        "gimbal_yaw",
        "gimbal_tilt",
        "camera",
    }
    assert expected.issubset(part_names), f"missing: {expected - part_names}"


def test_seed_zero_joint_topology_matches_anchor() -> None:
    """seed=0 anchor: 4 fold + 4 spin + 2 FIXED gear + 3 gimbal revolutes."""
    model = build_seeded_drone(0)
    joint_names = {j.name for j in model.articulations}
    # Folding arms
    for i in range(4):
        assert f"body_to_arm_{i}" in joint_names
        assert f"arm_to_propeller_{i}" in joint_names
    # Tube legs
    assert "body_to_left_landing_gear" in joint_names
    assert "body_to_right_landing_gear" in joint_names
    # 3-axis gimbal
    for n in ("gimbal_yaw", "gimbal_tilt", "gimbal_roll"):
        assert n in joint_names


def test_seed_zero_passes_template_qc() -> None:
    cfg = config_from_seed(0)
    model = build_drone(cfg)
    report = run_drone_tests(model, cfg)
    assert report.passed, report.failures


@pytest.mark.parametrize("seed", [1, 2, 3, 5, 7, 11])
def test_seeded_builds_succeed(seed: int) -> None:
    model = build_seeded_drone(seed)
    part_names = {p.name for p in model.parts}
    assert "body" in part_names
    # At least one propeller present.
    assert any(n.startswith("propeller_") for n in part_names)


def test_rotor_count_matches_module() -> None:
    """For every rotor_arms module, the number of propeller parts and
    spin joints must equal the module's N. We use the hex_plate_stack
    airframe so the Slot A × Slot B compatibility fallback doesn't
    downgrade hex/octo to quad."""
    for rotor in _ROTOR_CANDIDATES:
        cfg = DroneConfig(
            airframe_body_module="hex_plate_stack_body",
            rotor_arms_module=rotor,
        )
        r = resolve_config(cfg)
        model = build_drone(cfg)
        propeller_parts = [p for p in model.parts if p.name.startswith("propeller_")]
        spin_joints = [
            j
            for j in model.articulations
            if j.name.startswith("arm_to_propeller_") or j.name.startswith("body_to_propeller_")
        ]
        assert len(propeller_parts) == ROTOR_MODULE_N[rotor], (
            f"{rotor}: {len(propeller_parts)} propellers != N={ROTOR_MODULE_N[rotor]}"
        )
        assert len(spin_joints) == ROTOR_MODULE_N[rotor], (
            f"{rotor}: {len(spin_joints)} spin joints != N={ROTOR_MODULE_N[rotor]}"
        )
        # Every spin joint must be CONTINUOUS with axis (0,0,1).
        for j in spin_joints:
            assert j.articulation_type == ArticulationType.CONTINUOUS, (
                f"{rotor}: {j.name} is not CONTINUOUS"
            )
            assert tuple(j.axis) == (0.0, 0.0, 1.0), f"{rotor}: {j.name} axis={tuple(j.axis)}"
        assert r.rotor_count == ROTOR_MODULE_N[rotor]


def test_folding_arm_axes_and_count() -> None:
    """For folding rotor modules, the body_to_arm_i joints must be
    REVOLUTE with vertical axis. Use hex_plate_stack airframe so the
    Slot A × Slot B compatibility fallback doesn't downgrade hex to quad."""
    for rotor in ("folding_quad_4arm", "folding_hex_6arm"):
        cfg = DroneConfig(
            airframe_body_module="hex_plate_stack_body",
            rotor_arms_module=rotor,
        )
        model = build_drone(cfg)
        fold_joints = [j for j in model.articulations if j.name.startswith("body_to_arm_")]
        assert len(fold_joints) == ROTOR_MODULE_N[rotor]
        for j in fold_joints:
            assert j.articulation_type == ArticulationType.REVOLUTE


def test_hex_plate_stack_body_uses_hex_mesh_plates() -> None:
    cfg = DroneConfig(
        airframe_body_module="hex_plate_stack_body",
        rotor_arms_module="folding_hex_6arm",
        landing_gear_module="none",
        payload_undermount_module="none",
    )
    body = build_drone(cfg).get_part("body")

    lower_plate = body.get_visual("lower_plate")
    upper_plate = body.get_visual("upper_plate")

    assert isinstance(lower_plate.geometry, Mesh)
    assert isinstance(upper_plate.geometry, Mesh)
    assert lower_plate.geometry.name == "drone_hex_lower_plate"
    assert upper_plate.geometry.name == "drone_hex_upper_plate"


def test_three_axis_gimbal_axes() -> None:
    cfg = DroneConfig(payload_undermount_module="three_axis_gimbal")
    model = build_drone(cfg)
    yaw = model.get_articulation("gimbal_yaw")
    tilt = model.get_articulation("gimbal_tilt")
    roll = model.get_articulation("gimbal_roll")
    assert tuple(yaw.axis) == (0.0, 0.0, 1.0)
    assert tuple(tilt.axis) in {(0.0, 1.0, 0.0), (0.0, -1.0, 0.0)}
    assert tuple(roll.axis) in {(1.0, 0.0, 0.0), (-1.0, 0.0, 0.0)}


def test_yaw_tilt_gimbal_chain() -> None:
    cfg = DroneConfig(payload_undermount_module="yaw_tilt_gimbal")
    model = build_drone(cfg)
    joint_names = {j.name for j in model.articulations}
    assert "gimbal_yaw" in joint_names
    assert "gimbal_tilt" in joint_names
    # No roll for 2-DOF.
    assert "gimbal_roll" not in joint_names


def test_camera_plate_tilt_axis() -> None:
    cfg = DroneConfig(payload_undermount_module="camera_plate_tilt")
    model = build_drone(cfg)
    j = model.get_articulation("camera_plate_tilt")
    assert j.articulation_type == ArticulationType.REVOLUTE
    assert tuple(j.axis) in {(0.0, 1.0, 0.0), (0.0, -1.0, 0.0)}


def test_payload_skid_hinge_axis() -> None:
    cfg = DroneConfig(
        rotor_arms_module="folding_quad_4arm",
        landing_gear_module="tube_legs_pair",
        payload_undermount_module="payload_skid",
    )
    model = build_drone(cfg)
    j = model.get_articulation("payload_skid_hinge")
    assert j.articulation_type == ArticulationType.REVOLUTE
    assert tuple(j.axis) in {(0.0, 1.0, 0.0), (0.0, -1.0, 0.0)}


def test_forbidden_slot_c_d_pair_falls_back() -> None:
    """(folding_landing_legs, payload_skid) must fall back Slot C to
    tube_legs_pair so the build is legal."""
    cfg = DroneConfig(
        landing_gear_module="folding_landing_legs",
        payload_undermount_module="payload_skid",
    )
    r = resolve_config(cfg)
    assert r.landing_gear_module == "tube_legs_pair"


def test_forbidden_wire_loop_skids_payload_skid_falls_back() -> None:
    cfg = DroneConfig(
        landing_gear_module="wire_loop_skids",
        payload_undermount_module="payload_skid",
    )
    r = resolve_config(cfg)
    assert r.landing_gear_module == "tube_legs_pair"


def test_slot_c_none_skips_landing_gear_parts() -> None:
    cfg = DroneConfig(
        landing_gear_module="none",
        payload_undermount_module="none",
    )
    model = build_drone(cfg)
    part_names = {p.name for p in model.parts}
    assert "left_landing_gear" not in part_names
    assert "right_landing_gear" not in part_names
    assert not any(n.startswith("landing_leg_") for n in part_names)


def test_slot_d_none_skips_payload_parts() -> None:
    cfg = DroneConfig(
        landing_gear_module="tube_legs_pair",
        payload_undermount_module="none",
    )
    model = build_drone(cfg)
    part_names = {p.name for p in model.parts}
    assert "gimbal_yaw" not in part_names
    assert "gimbal_tilt" not in part_names
    assert "camera" not in part_names
    assert "camera_plate" not in part_names
    assert "payload_skid" not in part_names


def test_topology_diversity_over_seeds() -> None:
    """Across seeds 0..19 we expect ≥5 distinct (A,B,C,D) tuples (the
    module_topology_diversity gate threshold)."""
    seen = {tuple(slot_choices_for_seed(s)) for s in range(20)}
    assert len(seen) >= 5, f"only {len(seen)} distinct: {sorted(seen)}"


def test_legal_combinations_build() -> None:
    """Every legal (A,B,C,D) combination must build without raising.
    Forbidden (C,D) pairs are detected by resolve_config and remapped.
    We sample one (A,B) pair per axis to keep the matrix small enough."""
    sampled_airframes = ("rounded_shell_body", "hex_plate_stack_body", "lathe_round_body")
    sampled_rotors = ("folding_quad_4arm", "fixed_quad_4arm", "fixed_octo_8arm")
    for airframe in sampled_airframes:
        for rotor in sampled_rotors:
            for gear in _GEAR_CANDIDATES:
                for payload in _PAYLOAD_CANDIDATES:
                    cfg = DroneConfig(
                        airframe_body_module=airframe,
                        rotor_arms_module=rotor,
                        landing_gear_module=gear,
                        payload_undermount_module=payload,
                    )
                    # resolve_config applies fallback; build must succeed.
                    model = build_drone(cfg)
                    assert model is not None


def test_resolve_config_rejects_invalid_airframe() -> None:
    with pytest.raises(ValueError, match="airframe_body_module"):
        resolve_config(DroneConfig(airframe_body_module="unknown"))  # type: ignore[arg-type]


def test_resolve_config_rejects_invalid_rotor() -> None:
    with pytest.raises(ValueError, match="rotor_arms_module"):
        resolve_config(DroneConfig(rotor_arms_module="fold_octo_8arm"))  # type: ignore[arg-type]


def test_resolve_config_rejects_invalid_landing_gear() -> None:
    with pytest.raises(ValueError, match="landing_gear_module"):
        resolve_config(DroneConfig(landing_gear_module="hovercraft"))  # type: ignore[arg-type]


def test_resolve_config_rejects_invalid_payload() -> None:
    with pytest.raises(ValueError, match="payload_undermount_module"):
        resolve_config(DroneConfig(payload_undermount_module="laser_turret"))  # type: ignore[arg-type]


@pytest.mark.parametrize("seed", range(10))
def test_seeded_drone_passes_template_qc(seed: int) -> None:
    cfg = config_from_seed(seed)
    model = build_drone(cfg)
    report = run_drone_tests(model, cfg)
    assert report.passed, f"seed={seed}: {report.failures}"
