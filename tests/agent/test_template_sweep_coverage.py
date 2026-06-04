from __future__ import annotations

from pathlib import Path

from agent.template_sweep import SeedOutcome
from agent.template_sweep_coverage import (
    CoverageGateResult,
    CoverageGates,
    _normalize_slot_choices,
    check_module_topology_diversity,
    evaluate_gates,
)


def _outcome(
    seed: int,
    verdict: str = "pass",
) -> SeedOutcome:
    return SeedOutcome(
        seed=seed,
        verdict=verdict,
        config={"seed": seed},
        failure_type=None if verdict == "pass" else "fail_if_isolated_parts()",
        failure_type_normalized=None if verdict == "pass" else "fail_if_isolated_parts",
        failure_details=None if verdict == "pass" else "isolated antenna",
        elapsed_s=0.0,
    )


def _patch_modular_choices(monkeypatch, choices_by_seed: dict[int, object]) -> None:
    monkeypatch.setattr("agent.template_sweep_coverage.is_modular_template", lambda slug: True)
    monkeypatch.setattr(
        "agent.template_sweep_coverage._slot_choices_for_seed",
        lambda slug, seed: choices_by_seed[seed],
    )


def test_normalize_slot_choices_accepts_mapping_and_pairs() -> None:
    assert _normalize_slot_choices({"base": "tripod", "head": "pan_tilt"}) == (
        ("base", "tripod"),
        ("head", "pan_tilt"),
    )
    assert _normalize_slot_choices([("base", "tripod")]) == (("base", "tripod"),)


def test_normalize_slot_choices_rejects_invalid_shape() -> None:
    try:
        _normalize_slot_choices(["base_only"])
    except ValueError as exc:
        assert "pairs" in str(exc)
    else:
        raise AssertionError("expected invalid slot choices to fail")


def test_module_topology_diversity_skips_before_min_sweep_size(monkeypatch) -> None:
    monkeypatch.setattr("agent.template_sweep_coverage.is_modular_template", lambda slug: False)
    gate = check_module_topology_diversity("demo", [_outcome(seed) for seed in range(5)])
    assert gate.status == "skipped"
    assert gate.details["min_sweep_size"] == 20


def test_module_topology_diversity_fails_when_template_not_modular(monkeypatch) -> None:
    monkeypatch.setattr("agent.template_sweep_coverage.is_modular_template", lambda slug: False)
    gate = check_module_topology_diversity("demo", [_outcome(seed) for seed in range(20)])
    assert gate.status == "fail"
    assert "__modular__ = True" in gate.reason


def test_module_topology_diversity_fails_when_slot_report_missing(monkeypatch) -> None:
    monkeypatch.setattr("agent.template_sweep_coverage.is_modular_template", lambda slug: True)

    def missing_slot_report(slug: str, seed: int):
        raise AttributeError("missing callable slot_choices_for_seed(seed)")

    monkeypatch.setattr("agent.template_sweep_coverage._slot_choices_for_seed", missing_slot_report)
    gate = check_module_topology_diversity("demo", [_outcome(seed) for seed in range(20)])
    assert gate.status == "fail"
    assert gate.details["errors"][0]["error_kind"] == "AttributeError"
    assert "slot_choices_for_seed" in gate.reason


def test_module_topology_diversity_passes_with_ten_distinct_passing_tuples(
    monkeypatch,
) -> None:
    choices = {
        seed: [("base", f"base_{seed % 10}"), ("head", f"head_{seed % 2}")] for seed in range(20)
    }
    _patch_modular_choices(monkeypatch, choices)

    gate = check_module_topology_diversity("demo", [_outcome(seed) for seed in range(20)])

    assert gate.status == "pass"
    assert gate.details["distinct_count"] >= 10
    assert gate.details["passing_seed_count"] == 20


def test_module_topology_diversity_fails_when_distinct_count_is_too_low(
    monkeypatch,
) -> None:
    choices = {seed: [("base", "same"), ("head", f"head_{seed % 2}")] for seed in range(20)}
    _patch_modular_choices(monkeypatch, choices)

    gate = check_module_topology_diversity("demo", [_outcome(seed) for seed in range(20)])

    assert gate.status == "fail"
    assert gate.details["distinct_count"] == 2
    assert "at least 10" in gate.reason


def test_module_topology_diversity_counts_only_passing_seeds(monkeypatch) -> None:
    choices = {seed: [("base", f"base_{seed}")] for seed in range(20)}
    _patch_modular_choices(monkeypatch, choices)
    outcomes = [_outcome(seed, "pass" if seed < 4 else "fail") for seed in range(20)]

    gate = check_module_topology_diversity("demo", outcomes)

    assert gate.status == "fail"
    assert gate.details["passing_seed_count"] == 4
    assert gate.details["distinct_count"] == 4


def test_module_topology_diversity_fails_on_invalid_slot_choices(monkeypatch) -> None:
    choices = {seed: [("base", f"base_{seed % 5}")] for seed in range(20)}
    choices[7] = ["bad"]
    _patch_modular_choices(monkeypatch, choices)

    gate = check_module_topology_diversity("demo", [_outcome(seed) for seed in range(20)])

    assert gate.status == "fail"
    assert gate.details["errors"][0]["seed"] == 7
    assert gate.details["errors"][0]["error_kind"] == "ValueError"


def test_evaluate_gates_returns_only_module_topology(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "agent.template_sweep_coverage.check_module_topology_diversity",
        lambda slug, outcomes: CoverageGateResult(
            name="module_topology_diversity",
            status="pass",
            details={"distinct_count": 10},
        ),
    )

    gates = evaluate_gates(
        slug="demo",
        line_count=100,
        outcomes=[_outcome(seed) for seed in range(20)],
        repo_root=tmp_path,
    )

    assert isinstance(gates, CoverageGates)
    assert gates.to_dict().keys() == {"module_topology_diversity"}
    assert gates.module_topology_diversity.status == "pass"
    assert gates.all_pass_or_skipped() is True
    assert gates.failing_gates() == []
