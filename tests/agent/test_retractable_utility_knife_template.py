from __future__ import annotations

from pathlib import Path

import pytest

from agent.templates.retractable_utility_knife import (
    SOURCE_ADAPTATION_MAP,
    SOURCE_IDS,
    RetractableUtilityKnifeConfig,
    build_retractable_utility_knife,
    build_seeded_retractable_utility_knife,
    config_from_seed,
    resolve_config,
    run_retractable_utility_knife_tests,
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
    assert config_from_seed(7) == config_from_seed(7)
    assert config_from_seed(7) != config_from_seed(8)
    assert build_seeded_retractable_utility_knife(7).name == "seeded_retractable_utility_knife_7"


def test_invalid_config_rejections() -> None:
    with pytest.raises(ValueError):
        resolve_config(RetractableUtilityKnifeConfig(knife_body_style="folding_knife"))  # type: ignore[arg-type]


def test_default_identity_and_validator() -> None:
    config = RetractableUtilityKnifeConfig()
    model = build_retractable_utility_knife(config)
    report = run_retractable_utility_knife_tests(model, config)
    assert report.passed, report.failures
    assert model.get_articulation("blade_slide").articulation_type == ArticulationType.PRISMATIC
    assert model.get_articulation("blade_slide").axis == (1.0, 0.0, 0.0)


def test_source_adaptation_map_covers_core_semantics() -> None:
    assert SOURCE_IDS
    assert SOURCE_ADAPTATION_MAP
    assert len(SOURCE_IDS) >= 10


def test_line_count_floor() -> None:
    path = Path("agent/templates/retractable_utility_knife.py")
    assert len(path.read_text().splitlines()) >= 1000


def test_representative_seeded_models_pass_basic_qc() -> None:
    for seed in range(3):
        _assert_basic_qc_passes(build_seeded_retractable_utility_knife(seed))
