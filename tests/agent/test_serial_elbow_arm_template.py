from __future__ import annotations

import itertools

import pytest

from agent.templates.serial_elbow_arm import (
    SOURCE_ADAPTATION_MAP,
    SOURCE_IDS,
    SerialElbowArmConfig,
    build_seeded_serial_elbow_arm,
    build_serial_elbow_arm,
    config_from_seed,
    resolve_config,
    run_serial_elbow_arm_tests,
    slot_choices_for_seed,
)
from sdk import ArticulationType
from sdk import TestContext as ArticraftTestContext

BASE_MODULES = ("pedestal_yoke", "root_fork", "controller_yaw_base")
UPPER_MODULES = (
    "box_beam_yoke",
    "open_plate_yoke",
    "dual_parallel_yoke",
    "triple_segment_yoke",
    "quad_segment_yoke",
    "five_dof_yoke",
    "six_dof_yoke",
    "seven_dof_yoke",
)
FOREARM_MODULES = ("flange_forearm", "pad_plate_forearm", "suction_tool_forearm")
EXPECTED_DOF_BY_UPPER = {
    "box_beam_yoke": 2,
    "open_plate_yoke": 2,
    "dual_parallel_yoke": 2,
    "triple_segment_yoke": 3,
    "quad_segment_yoke": 4,
    "five_dof_yoke": 5,
    "six_dof_yoke": 6,
    "seven_dof_yoke": 7,
}
JOINT_HOUSING_STYLES = ("boxed_clevis", "round_bearing", "split_plate", "compact_ring")


def _assert_basic_qc_passes(model) -> None:
    ctx = ArticraftTestContext(model)
    ctx.check_model_valid()
    ctx.fail_if_isolated_parts()
    report = ctx.report()
    assert report.passed, report.failures


def test_seed_config_is_reproducible() -> None:
    assert config_from_seed(7) == config_from_seed(7)
    assert config_from_seed(7) != config_from_seed(8)
    assert slot_choices_for_seed(7) == slot_choices_for_seed(7)
    assert build_seeded_serial_elbow_arm(7).name == "seeded_serial_elbow_arm_7"


def test_seed_zero_is_anchor_combination() -> None:
    assert slot_choices_for_seed(0) == [
        ("base", "pedestal_yoke"),
        ("upper_link", "box_beam_yoke"),
        ("forearm", "flange_forearm"),
    ]


def test_all_module_combinations_build() -> None:
    for base_module, upper_module, forearm_module in itertools.product(
        BASE_MODULES, UPPER_MODULES, FOREARM_MODULES
    ):
        config = SerialElbowArmConfig(
            base_module=base_module,  # type: ignore[arg-type]
            upper_module=upper_module,  # type: ignore[arg-type]
            forearm_module=forearm_module,  # type: ignore[arg-type]
        )
        model = build_serial_elbow_arm(config)
        report = run_serial_elbow_arm_tests(model, config)
        assert report.passed, (base_module, upper_module, forearm_module, report.failures)
        revolute_count = sum(
            1
            for joint in model.articulations
            if joint.articulation_type == ArticulationType.REVOLUTE
        )
        assert revolute_count == EXPECTED_DOF_BY_UPPER[upper_module]


def test_topology_diversity_in_first_ten_seeds() -> None:
    observed = {tuple(slot_choices_for_seed(seed)) for seed in range(10)}
    assert len(observed) >= 7


def test_upper_modules_cover_two_to_seven_degrees_of_freedom() -> None:
    observed = set()
    for upper_module in UPPER_MODULES:
        model = build_serial_elbow_arm(
            SerialElbowArmConfig(upper_module=upper_module)  # type: ignore[arg-type]
        )
        observed.add(
            sum(
                1
                for joint in model.articulations
                if joint.articulation_type == ArticulationType.REVOLUTE
            )
        )
    assert observed == {2, 3, 4, 5, 6, 7}


def test_joint_housing_styles_build() -> None:
    for joint_housing_style in JOINT_HOUSING_STYLES:
        model = build_serial_elbow_arm(
            SerialElbowArmConfig(
                upper_module="five_dof_yoke",
                joint_housing_style=joint_housing_style,  # type: ignore[arg-type]
            )
        )
        report = run_serial_elbow_arm_tests(
            model,
            SerialElbowArmConfig(
                upper_module="five_dof_yoke",
                joint_housing_style=joint_housing_style,  # type: ignore[arg-type]
            ),
        )
        assert report.passed, (joint_housing_style, report.failures)


def test_joint_cap_faces_have_non_slot_variants() -> None:
    round_model = build_serial_elbow_arm(
        SerialElbowArmConfig(joint_housing_style="round_bearing")  # type: ignore[arg-type]
    )
    round_visual_names = {visual.name for visual in round_model.get_part("upper_link").visuals}
    assert "shoulder_centered_pitch_hub_inner_pin" in round_visual_names
    assert "shoulder_centered_pitch_hub_front_upper_bolt" in round_visual_names

    split_model = build_serial_elbow_arm(
        SerialElbowArmConfig(joint_housing_style="split_plate")  # type: ignore[arg-type]
    )
    split_visual_names = {visual.name for visual in split_model.get_part("upper_link").visuals}
    assert "shoulder_centered_pitch_hub_front_upper_split_lug" in split_visual_names
    assert "shoulder_centered_pitch_hub_rear_lower_split_lug" in split_visual_names

    compact_model = build_serial_elbow_arm(
        SerialElbowArmConfig(joint_housing_style="compact_ring")  # type: ignore[arg-type]
    )
    compact_visual_names = {visual.name for visual in compact_model.get_part("upper_link").visuals}
    assert "shoulder_centered_pitch_hub_center_pin" in compact_visual_names


def test_joint_cap_center_motifs_include_cross_and_bolts() -> None:
    cross_model = build_serial_elbow_arm(
        SerialElbowArmConfig(joint_housing_style="round_bearing")  # type: ignore[arg-type]
    )
    cross_visual_names = {visual.name for visual in cross_model.get_part("upper_link").visuals}
    assert "shoulder_centered_pitch_hub_front_horizontal_slot" in cross_visual_names
    assert "shoulder_centered_pitch_hub_front_vertical_slot" in cross_visual_names

    bolt_model = build_serial_elbow_arm(
        SerialElbowArmConfig(joint_housing_style="compact_ring")  # type: ignore[arg-type]
    )
    bolt_visual_names = {visual.name for visual in bolt_model.get_part("upper_link").visuals}
    assert "shoulder_centered_pitch_hub_front_upper_bolt" in bolt_visual_names
    assert "elbow_centered_pitch_socket_front_center_pin" in bolt_visual_names


def test_joint_cap_motif_can_be_overridden() -> None:
    model = build_serial_elbow_arm(SerialElbowArmConfig(joint_cap_motif="cross_slot"))
    visual_names = {visual.name for visual in model.get_part("upper_link").visuals}
    assert "shoulder_centered_pitch_hub_front_horizontal_slot" in visual_names
    assert "shoulder_centered_pitch_hub_front_vertical_slot" in visual_names
    assert "elbow_centered_pitch_socket_front_horizontal_slot" in visual_names
    assert "elbow_centered_pitch_socket_front_vertical_slot" in visual_names


def test_joint_support_plates_have_non_box_variants() -> None:
    round_model = build_serial_elbow_arm(
        SerialElbowArmConfig(joint_housing_style="boxed_clevis")  # type: ignore[arg-type]
    )
    round_visual_names = {visual.name for visual in round_model.get_part("upper_link").visuals}
    assert "elbow_left_round_ear_plate" in round_visual_names

    split_model = build_serial_elbow_arm(
        SerialElbowArmConfig(joint_housing_style="round_bearing")  # type: ignore[arg-type]
    )
    split_visual_names = {visual.name for visual in split_model.get_part("upper_link").visuals}
    assert "elbow_left_upper_split_ear" in split_visual_names

    compact_model = build_serial_elbow_arm(
        SerialElbowArmConfig(joint_housing_style="split_plate")  # type: ignore[arg-type]
    )
    compact_visual_names = {visual.name for visual in compact_model.get_part("upper_link").visuals}
    assert "elbow_left_compact_round_plate" in compact_visual_names


def test_invalid_module_rejection_per_slot() -> None:
    with pytest.raises(ValueError, match="base_module"):
        resolve_config(SerialElbowArmConfig(base_module="bad_base"))  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="upper_module"):
        resolve_config(SerialElbowArmConfig(upper_module="bad_upper"))  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="forearm_module"):
        resolve_config(SerialElbowArmConfig(forearm_module="bad_forearm"))  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="joint_housing_style"):
        resolve_config(SerialElbowArmConfig(joint_housing_style="bad_joint"))  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="joint_cap_motif"):
        resolve_config(SerialElbowArmConfig(joint_cap_motif="bad_motif"))  # type: ignore[arg-type]


def test_default_identity_axes_and_validator() -> None:
    config = SerialElbowArmConfig()
    model = build_serial_elbow_arm(config)
    report = run_serial_elbow_arm_tests(model, config)
    assert report.passed, report.failures
    assert model.get_articulation("shoulder_pitch").axis == (0.0, 1.0, 0.0)
    assert model.get_articulation("elbow_pitch").axis == (0.0, 1.0, 0.0)


def test_planar_yaw_branch_uses_z_axes() -> None:
    config = SerialElbowArmConfig(axis_family="planar_yaw")
    model = build_serial_elbow_arm(config)
    report = run_serial_elbow_arm_tests(model, config)
    assert report.passed, report.failures
    assert model.get_articulation("shoulder_yaw").axis == (0.0, 0.0, 1.0)
    assert model.get_articulation("elbow_yaw").axis == (0.0, 0.0, 1.0)


def test_seed_nine_pitch_hubs_are_centered_in_yoke_gap() -> None:
    model = build_seeded_serial_elbow_arm(9)
    upper_link = model.get_part("upper_link")
    elbow = model.get_articulation("elbow_pitch")
    terminal_link = model.get_part(elbow.parent)
    forearm = model.get_part("forearm")

    assert upper_link.get_visual("shoulder_centered_pitch_hub").origin.xyz[1] == pytest.approx(0.0)
    assert terminal_link.get_visual("elbow_centered_pitch_socket").origin.xyz[1] == pytest.approx(
        0.0
    )
    assert forearm.get_visual("forearm_centered_pitch_hub").origin.xyz[1] == pytest.approx(0.0)


def test_source_adaptation_map_covers_core_semantics() -> None:
    assert SOURCE_IDS
    assert SOURCE_ADAPTATION_MAP
    assert "primary_joints.vertical_pitch" in SOURCE_ADAPTATION_MAP
    assert "primary_joints.planar_yaw" in SOURCE_ADAPTATION_MAP


def test_representative_seeded_models_pass_basic_qc() -> None:
    for seed in range(4):
        model = build_seeded_serial_elbow_arm(seed)
        _assert_basic_qc_passes(model)
        revolute_joints = [
            joint
            for joint in model.articulations
            if joint.articulation_type == ArticulationType.REVOLUTE
        ]
        upper_module = dict(slot_choices_for_seed(seed))["upper_link"]
        assert len(revolute_joints) == EXPECTED_DOF_BY_UPPER[upper_module]
