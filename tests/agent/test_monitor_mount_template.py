from __future__ import annotations

from pathlib import Path

import pytest

from agent.templates.monitor_mount import (
    SOURCE_ADAPTATION_MAP,
    SOURCE_IDS,
    MonitorMountConfig,
    build_monitor_mount,
    build_seeded_monitor_mount,
    config_from_seed,
    resolve_config,
    run_monitor_mount_tests,
)
from sdk import ArticulationType
from sdk import TestContext as ArticraftTestContext


def _assert_basic_qc_passes(model) -> None:
    ctx = ArticraftTestContext(model)
    ctx.check_model_valid()
    ctx.fail_if_isolated_parts()
    report = ctx.report()
    assert report.passed, report.failures


def test_seed_config_is_reproducible() -> None:
    assert config_from_seed(26) == config_from_seed(26)
    assert config_from_seed(26) != config_from_seed(27)
    assert build_seeded_monitor_mount(26).name == "seeded_monitor_mount_26"


def test_invalid_config_rejections() -> None:
    with pytest.raises(ValueError, match="Unsupported mount_base_style"):
        resolve_config(MonitorMountConfig(mount_base_style="ceiling_hook"))  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="total_reach"):
        resolve_config(MonitorMountConfig(total_reach=0.20))
    with pytest.raises(ValueError, match="tilt_range"):
        resolve_config(MonitorMountConfig(tilt_range=(0.5, -0.2)))


def test_default_monitor_mount_identity_and_validator() -> None:
    config = MonitorMountConfig()
    model = build_monitor_mount(config)
    report = run_monitor_mount_tests(model, config)

    assert report.passed, report.failures
    assert model.get_articulation("base_yaw").articulation_type == ArticulationType.CONTINUOUS
    assert model.get_articulation("shoulder_yaw").axis == (0.0, 0.0, 1.0)
    assert model.get_articulation("elbow_fold").origin.xyz[0] == pytest.approx(
        resolve_config(config).primary_len
    )
    assert "desk_top_clamp_plate" in {v.name for v in model.get_part("base_mount").visuals}
    assert "vesa_plate" in {v.name for v in model.get_part("vesa_plate").visuals}


def test_wall_plate_uses_wall_pan_and_wall_geometry() -> None:
    config = MonitorMountConfig(mount_base_style="wall_plate", arm_topology="simple_two_link")
    resolved = resolve_config(config)
    model = build_monitor_mount(config)

    assert resolved.arm_topology == "wall_planar_two_link"
    assert "wall_pan" in {joint.name for joint in model.articulations}
    assert "wall_back_plate" in {v.name for v in model.get_part("base_mount").visuals}
    assert model.get_articulation("shoulder_yaw").axis == (0.0, 0.0, 1.0)


def test_counterbalanced_branch_changes_axis_and_adds_strut() -> None:
    config = MonitorMountConfig(
        arm_topology="counterbalanced_lift_pitch",
        mount_base_style="desk_clamp",
        monitor_mass_class="heavy",
        link_style="spring_tube",
    )
    model = build_monitor_mount(config)
    resolved = resolve_config(config)

    assert resolved.arm_plane == "hybrid_counterbalanced"
    assert model.get_articulation("shoulder_lift").axis == (0.0, -1.0, 0.0)
    assert "counterbalance_outer_tube" in {v.name for v in model.get_part("primary_link").visuals}
    assert run_monitor_mount_tests(model, config).passed


def test_vesa_and_roll_branches_are_observable() -> None:
    config = MonitorMountConfig(vesa_size="dual_75_100", head_dof="pan_tilt_roll")
    model = build_monitor_mount(config)
    vesa_visuals = {v.name for v in model.get_part("vesa_plate").visuals}

    assert any(name.startswith("vesa_75_insert") for name in vesa_visuals)
    assert any(name.startswith("vesa_100_insert") for name in vesa_visuals)
    assert "display_roll" in {joint.name for joint in model.articulations}


def test_source_adaptation_map_covers_required_parts_and_joints() -> None:
    for key in (
        "base_mount",
        "primary_link",
        "secondary_link",
        "head_yoke",
        "vesa_plate",
        "base_yaw_joint",
        "elbow_joint",
        "head_tilt_joint",
    ):
        assert key in SOURCE_ADAPTATION_MAP
        assert SOURCE_ADAPTATION_MAP[key]
    assert set(SOURCE_IDS) >= {"S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9"}


def test_line_count_floor() -> None:
    path = Path("agent/templates/monitor_mount.py")
    assert len(path.read_text().splitlines()) >= 1000


def test_seed_domain_uses_implemented_branches() -> None:
    configs = [config_from_seed(seed) for seed in range(48)]
    assert {cfg.mount_base_style for cfg in configs} <= {
        "desk_clamp",
        "wall_plate",
        "pole_clamp",
        "freestanding_base",
    }
    assert {cfg.arm_topology for cfg in configs} <= {
        "simple_two_link",
        "wall_planar_two_link",
        "counterbalanced_lift_pitch",
    }
    assert {cfg.head_dof for cfg in configs} <= {"tilt_only", "pan_tilt", "pan_tilt_roll"}


def test_representative_seeded_models_pass_basic_qc() -> None:
    for seed in range(4):
        _assert_basic_qc_passes(build_seeded_monitor_mount(seed))
