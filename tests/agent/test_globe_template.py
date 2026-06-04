from __future__ import annotations

from agent.templates.globe import (
    build_globe,
    config_from_seed,
    run_globe_tests,
    slot_choices_for_seed,
)


def test_seed_zero_anchor_combination() -> None:
    assert slot_choices_for_seed(0) == [
        ("support_base", "classic_desktop"),
        ("meridian_or_cradle", "full_tilting"),
        ("globe_surface", "continent_patch"),
        ("auxiliary_rotary", "none"),
        ("graticule_density", "medium"),
        ("land_patch_style", "simple_continents"),
    ]


def test_seed_zero_globe_template_passes_author_checks() -> None:
    config = config_from_seed(0)
    model = build_globe(config)
    report = run_globe_tests(model, config)
    assert report.passed, report.failures
