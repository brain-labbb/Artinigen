from __future__ import annotations

from itertools import product

import pytest

from agent.templates.screwin_light_bulb_with_socket import (
    BULB_MODULES,
    MOTION_MODULES,
    SOCKET_MODULES,
    SOURCE_ADAPTATION_MAP,
    SOURCE_IDS,
    ScrewinLightBulbWithSocketConfig,
    build_screwin_light_bulb_with_socket,
    build_seeded_screwin_light_bulb_with_socket,
    config_from_seed,
    resolve_config,
    run_screwin_light_bulb_with_socket_tests,
    slot_choices_for_seed,
)
from sdk import TestContext as ArticraftTestContext


def _assert_basic_qc_passes(model) -> None:
    ctx = ArticraftTestContext(model)
    ctx.check_model_valid()
    ctx.fail_if_isolated_parts()
    report = ctx.report()
    assert report.passed, report.failures


def test_seed_config_is_reproducible() -> None:
    assert config_from_seed(7) == config_from_seed(7)
    assert config_from_seed(7) != config_from_seed(8)
    assert (
        build_seeded_screwin_light_bulb_with_socket(7).name
        == "seeded_screwin_light_bulb_with_socket_7"
    )


def test_seed_zero_uses_anchor_modules() -> None:
    assert slot_choices_for_seed(0) == [
        ("socket", "ceramic_socket"),
        ("motion", "threaded_turn_lift"),
        ("bulb", "a_bulb"),
    ]


def test_all_module_combinations_build() -> None:
    for socket_module, motion_module, bulb_module in product(
        SOCKET_MODULES,
        MOTION_MODULES,
        BULB_MODULES,
    ):
        model = build_screwin_light_bulb_with_socket(
            ScrewinLightBulbWithSocketConfig(
                socket_module=socket_module,
                motion_module=motion_module,
                bulb_module=bulb_module,
                name=f"combo_{socket_module}_{motion_module}_{bulb_module}",
            )
        )
        assert model.get_part("socket_body") is not None
        assert model.get_part("thread_axis") is not None
        assert model.get_part("bulb_assembly") is not None


def test_topology_diversity_in_first_ten_seeds() -> None:
    choices = {tuple(slot_choices_for_seed(seed)) for seed in range(10)}
    assert len(choices) >= 7


def test_invalid_module_rejection_per_slot() -> None:
    with pytest.raises(ValueError, match="socket_module"):
        resolve_config(
            ScrewinLightBulbWithSocketConfig(socket_module="loose_wire")  # type: ignore[arg-type]
        )
    with pytest.raises(ValueError, match="motion_module"):
        resolve_config(
            ScrewinLightBulbWithSocketConfig(motion_module="sideways_thread")  # type: ignore[arg-type]
        )
    with pytest.raises(ValueError, match="bulb_module"):
        resolve_config(
            ScrewinLightBulbWithSocketConfig(bulb_module="bare_led_chip")  # type: ignore[arg-type]
        )


def test_default_identity_and_validator() -> None:
    config = ScrewinLightBulbWithSocketConfig()
    model = build_screwin_light_bulb_with_socket(config)
    report = run_screwin_light_bulb_with_socket_tests(model, config)
    assert report.passed, report.failures
    assert [joint.name for joint in model.articulations] == ["socket_to_motion", "motion_to_bulb"]


def test_source_adaptation_map_covers_core_semantics() -> None:
    assert set(SOURCE_IDS) >= {f"S{index}" for index in range(1, 14)}
    assert SOURCE_ADAPTATION_MAP["motion.threaded_turn_lift"] == ("S5", "S7", "S13")
    assert "bulb.a_bulb" in SOURCE_ADAPTATION_MAP


def test_representative_seeded_models_pass_basic_qc() -> None:
    for seed in range(3):
        _assert_basic_qc_passes(build_seeded_screwin_light_bulb_with_socket(seed))
