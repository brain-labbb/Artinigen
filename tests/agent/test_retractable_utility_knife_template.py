from __future__ import annotations

import pytest

from agent.templates.retractable_utility_knife import (
    RetractableUtilityKnifeConfig,
    build_retractable_utility_knife,
    build_seeded_retractable_utility_knife,
    config_from_seed,
    resolve_config,
    slot_choices_for_seed,
)


def test_seed_config_is_reproducible() -> None:
    assert config_from_seed(7) == config_from_seed(7)
    assert config_from_seed(7) != config_from_seed(8)


@pytest.mark.parametrize("seed", [0, 1, 2, 5, 12])
def test_seeded_builds_succeed(seed: int) -> None:
    model = build_seeded_retractable_utility_knife(seed)
    part_names = {p.name for p in model.parts}
    assert "body_shell" in part_names
    assert "blade_carrier" in part_names
    assert "blade" in part_names

    joint_topology = {(a.parent, a.child, a.articulation_type.name) for a in model.articulations}
    # The housing_to_mechanism joint is always PRISMATIC along x.
    assert any(
        parent == "body_shell" and child == "blade_carrier" and kind == "PRISMATIC"
        for parent, child, kind in joint_topology
    )
    # Blade is always FIXED to blade_carrier.
    assert ("blade_carrier", "blade", "FIXED") in joint_topology


def test_seed_zero_is_anchor_combination() -> None:
    choices = slot_choices_for_seed(0)
    assert choices == [
        ("housing", "barrel_grip"),
        ("mechanism", "retractable_slider"),
        ("blade", "straight_utility"),
    ]


def test_topology_diversity_over_seeds() -> None:
    """Across seeds 0..9 we expect at least 7 distinct topology
    combinations (out of 8 possible). RNG can occasionally repeat at
    small sample sizes so we leave a 1-combination margin."""
    seen = {tuple(slot_choices_for_seed(s)) for s in range(10)}
    assert len(seen) >= 7, f"Expected >=7 distinct topologies in seeds 0..9, got {sorted(seen)}"


def test_all_eight_combinations_build_successfully() -> None:
    """Every cell of the 2x2x2 module grid must produce a buildable
    model."""
    for h in ("barrel_grip", "pistol_grip"):
        for m in ("retractable_slider", "service_door_swap"):
            for b in ("straight_utility", "hook"):
                cfg = RetractableUtilityKnifeConfig(
                    housing_module=h,
                    mechanism_module=m,
                    blade_module=b,
                )
                model = build_retractable_utility_knife(cfg)
                part_names = {p.name for p in model.parts}
                assert "body_shell" in part_names, f"({h},{m},{b}) missing body_shell"
                assert "blade_carrier" in part_names, f"({h},{m},{b}) missing blade_carrier"
                assert "blade" in part_names, f"({h},{m},{b}) missing blade"
                if h == "barrel_grip":
                    assert "lock_wheel" in part_names, f"({h},{m},{b}) missing lock_wheel"
                if m == "service_door_swap":
                    assert "service_door" in part_names, f"({h},{m},{b}) missing service_door"
                else:
                    assert "thumb_slider" in part_names, f"({h},{m},{b}) missing thumb_slider"


def test_resolve_config_clamps_oversized_handle() -> None:
    cfg = RetractableUtilityKnifeConfig(handle_length=0.50)
    r = resolve_config(cfg)
    assert r.handle_length <= 0.200


def test_resolve_config_rejects_invalid_housing_module() -> None:
    with pytest.raises(ValueError, match="housing_module"):
        resolve_config(RetractableUtilityKnifeConfig(housing_module="unknown"))  # type: ignore[arg-type]


def test_resolve_config_rejects_invalid_mechanism_module() -> None:
    with pytest.raises(ValueError, match="mechanism_module"):
        resolve_config(RetractableUtilityKnifeConfig(mechanism_module="unknown"))  # type: ignore[arg-type]


def test_resolve_config_rejects_invalid_blade_module() -> None:
    with pytest.raises(ValueError, match="blade_module"):
        resolve_config(RetractableUtilityKnifeConfig(blade_module="unknown"))  # type: ignore[arg-type]
