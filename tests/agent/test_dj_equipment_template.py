from __future__ import annotations

from pathlib import Path

import pytest

from agent.templates.dj_equipment import (
    DJEquipmentConfig,
    build_dj_equipment,
    build_seeded_dj_equipment,
    config_from_seed,
    resolve_config,
    run_dj_equipment_tests,
)
from sdk import ArticulationType
from sdk._core.v0.testing import TestContext as SDKTestContext


def _assert_template_qc_passes(config: DJEquipmentConfig) -> None:
    model = build_dj_equipment(config)
    report = run_dj_equipment_tests(model, config)
    assert report.passed, report.failures


def test_template_line_floor() -> None:
    template_path = Path("agent/templates/dj_equipment.py")
    assert len(template_path.read_text().splitlines()) >= 1000


def test_seed_reproducibility() -> None:
    assert config_from_seed(3) == config_from_seed(3)
    assert config_from_seed(3) != config_from_seed(4)
    assert build_seeded_dj_equipment(3).name == "seeded_dj_equipment_3"


def test_default_seed_domain_excludes_review_gated_families() -> None:
    families = {config_from_seed(seed).equipment_family for seed in range(40)}
    assert families <= {"all_in_one_controller", "dj_mixer", "turntable_deck"}


def test_all_in_one_controller_has_dual_jog_and_pad_grid() -> None:
    config = DJEquipmentConfig(equipment_family="all_in_one_controller")
    resolved = resolve_config(config)
    model = build_dj_equipment(config)
    platter_joints = [
        joint for joint in model.articulations if joint.name.startswith("platter_spin_")
    ]
    pad_joints = [joint for joint in model.articulations if joint.name.startswith("pad_press_")]

    assert resolved.platter_count == 2
    assert len(platter_joints) == 2
    assert len(pad_joints) == resolved.pad_count
    assert resolved.pad_count >= 8


def test_mixer_faders_and_knobs_use_panel_axes() -> None:
    config = DJEquipmentConfig(equipment_family="dj_mixer", channel_count=4)
    resolved = resolve_config(config)
    model = build_dj_equipment(config)
    fader_joints = [
        joint
        for joint in model.articulations
        if "fader" in joint.name and joint.name.endswith("_slide")
    ]
    knob_joints = [joint for joint in model.articulations if joint.name.startswith("knob_turn_")]

    assert len(fader_joints) == resolved.fader_count
    assert len(knob_joints) == resolved.knob_count
    assert all(joint.articulation_type == ArticulationType.PRISMATIC for joint in fader_joints)
    assert {tuple(joint.axis) for joint in fader_joints} <= {(1.0, 0.0, 0.0), (0.0, 1.0, 0.0)}
    assert all(tuple(joint.axis) == (0.0, 0.0, 1.0) for joint in knob_joints)


def test_turntable_tonearm_pivot_stays_outside_platter_center() -> None:
    config = DJEquipmentConfig(equipment_family="turntable_deck")
    resolved = resolve_config(config)
    model = build_dj_equipment(config)
    tonearm = model.get_articulation("tonearm_swing")
    platter = model.get_articulation("platter_spin_0")

    assert tonearm.articulation_type == ArticulationType.REVOLUTE
    assert tuple(tonearm.axis) == (0.0, 0.0, 1.0)
    dx = tonearm.origin.xyz[0] - platter.origin.xyz[0]
    dy = tonearm.origin.xyz[1] - platter.origin.xyz[1]
    assert (dx * dx + dy * dy) ** 0.5 > resolved.platter_radius


def test_review_gated_family_downgrades_in_default_domain() -> None:
    resolved = resolve_config(
        DJEquipmentConfig(
            equipment_family="pad_sampler",
            seed_domain="controller_mixer_turntable_core",
        )
    )
    assert resolved.equipment_family == "all_in_one_controller"


@pytest.mark.parametrize("seed", range(12))
def test_seeded_configs_pass_template_qc(seed: int) -> None:
    _assert_template_qc_passes(config_from_seed(seed))


def test_strict_current_pose_overlap_seed_zero() -> None:
    model = build_dj_equipment(config_from_seed(0))
    ctx = SDKTestContext(model)
    ctx.fail_if_parts_overlap_in_current_pose(overlap_tol=0.003, overlap_volume_tol=1e-7)
    assert ctx.report().passed
