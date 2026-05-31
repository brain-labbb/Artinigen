from __future__ import annotations

import pytest

from agent.templates.screwcap_bottle import (
    SOURCE_ADAPTATION_MAP,
    SOURCE_IDS,
    ScrewcapBottleConfig,
    build_screwcap_bottle,
    build_seeded_screwcap_bottle,
    config_from_seed,
    resolve_config,
    run_screwcap_bottle_tests,
    slot_choices_for_seed,
)
from sdk import TestContext as ArticraftTestContext

BODY_MODULES = ("compact_lathe", "segmented_body", "rugged_utility")
THREAD_MODULES = ("helical_thread", "banded_thread", "stacked_finish")
CAP_MODULES = ("ribbed_shell", "knurled_shell", "tethered_utility")


def _assert_basic_qc_passes(model) -> None:
    ctx = ArticraftTestContext(model)
    ctx.check_model_valid()
    ctx.fail_if_isolated_parts()
    report = ctx.report()
    assert report.passed, report.failures


def test_seed_config_is_reproducible() -> None:
    assert config_from_seed(7) == config_from_seed(7)
    assert config_from_seed(7) != config_from_seed(8)
    assert build_seeded_screwcap_bottle(7).name == "seeded_screwcap_bottle_7"


def test_seed_zero_is_anchor_combination() -> None:
    assert slot_choices_for_seed(0) == [
        ("body", "compact_lathe"),
        ("thread", "helical_thread"),
        ("cap", "ribbed_shell"),
    ]


def test_default_identity_and_validator() -> None:
    config = config_from_seed(0)
    model = build_screwcap_bottle(config)
    report = run_screwcap_bottle_tests(model, config)
    assert report.passed, report.failures
    assert model.get_articulation("cap_spin").axis == (0.0, 0.0, 1.0)
    assert model.get_articulation("cap_thread_lift").axis == (0.0, 0.0, 1.0)


def test_all_module_combinations_build_successfully() -> None:
    for body in BODY_MODULES:
        for thread in THREAD_MODULES:
            for cap in CAP_MODULES:
                config = ScrewcapBottleConfig(
                    body_module=body,
                    thread_module=thread,
                    cap_module=cap,
                    screw_motion_model="threaded_turn_lift",
                )
                model = build_screwcap_bottle(config)
                part_names = {part.name for part in model.parts}
                assert {"bottle_body", "cap_insert", "screw_cap"} <= part_names
                _assert_basic_qc_passes(model)


def test_topology_diversity_in_first_ten_seeds() -> None:
    seen = {tuple(slot_choices_for_seed(seed)) for seed in range(10)}
    assert len(seen) >= 7, f"Expected >=7 distinct topologies, got {sorted(seen)}"


def test_rejects_invalid_body_module() -> None:
    with pytest.raises(ValueError, match="body_module"):
        resolve_config(ScrewcapBottleConfig(body_module="paint_can"))  # type: ignore[arg-type]


def test_rejects_invalid_thread_module() -> None:
    with pytest.raises(ValueError, match="thread_module"):
        resolve_config(ScrewcapBottleConfig(thread_module="zipper"))  # type: ignore[arg-type]


def test_rejects_invalid_cap_module() -> None:
    with pytest.raises(ValueError, match="cap_module"):
        resolve_config(ScrewcapBottleConfig(cap_module="snap_lid"))  # type: ignore[arg-type]


def test_threaded_turn_lift_and_simple_spin_semantics() -> None:
    threaded = build_screwcap_bottle(ScrewcapBottleConfig(screw_motion_model="threaded_turn_lift"))
    assert threaded.get_articulation("cap_thread_lift").articulation_type.name == "PRISMATIC"
    assert threaded.get_articulation("cap_spin").articulation_type.name == "REVOLUTE"

    simple = build_screwcap_bottle(ScrewcapBottleConfig(screw_motion_model="simple_spin"))
    assert simple.get_articulation("cap_spin").articulation_type.name == "CONTINUOUS"
    assert simple.get_articulation("cap_to_insert").articulation_type.name == "FIXED"


def test_source_adaptation_map_covers_core_semantics() -> None:
    assert SOURCE_IDS
    assert SOURCE_ADAPTATION_MAP
    assert "motion.threaded_turn_lift" in SOURCE_ADAPTATION_MAP
    assert len(SOURCE_IDS) >= 11


def test_representative_seeded_models_pass_basic_qc() -> None:
    for seed in range(5):
        model = build_seeded_screwcap_bottle(seed)
        _assert_basic_qc_passes(model)
