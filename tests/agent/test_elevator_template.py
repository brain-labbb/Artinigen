from __future__ import annotations

from agent.templates.elevator import (
    build_elevator,
    config_from_seed,
    run_elevator_tests,
    slot_choices_for_seed,
)
from sdk import ArticulationType


def test_seed_zero_has_modular_choices() -> None:
    choices = slot_choices_for_seed(0)
    assert any(slot == "shaft" for slot, _module in choices)
    assert any(slot == "cabin" for slot, _module in choices)
    assert any(slot == "door_system" for slot, _module in choices)
    assert any(slot == "drive" for slot, _module in choices)
    assert any(slot == "bank_multiplicity" for slot, _module in choices)


def test_seeded_elevator_templates_pass_author_checks() -> None:
    for seed in range(10):
        config = config_from_seed(seed)
        model = build_elevator(config)
        report = run_elevator_tests(model, config)
        assert report.passed, (seed, report.failures)


def test_car_vertical_travel_joint_contract() -> None:
    model = build_elevator(config_from_seed(3))
    joints = [
        joint
        for joint in model.joints
        if joint.name == "car_vertical_travel" or joint.name.endswith("_car_vertical_travel")
    ]
    assert joints
    for joint in joints:
        assert joint.articulation_type == ArticulationType.PRISMATIC
        assert joint.axis == (0.0, 0.0, 1.0)
        assert joint.motion_limits.lower == 0.0
        assert joint.motion_limits.upper > 1.0
