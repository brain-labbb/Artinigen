from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from agent.template_sweep import SeedOutcome
from agent.template_sweep_coverage import (
    _extract_adopted_source_ids,
    _literal_fields,
    check_adopted_source,
    check_enum_coverage,
    check_line_floor,
    evaluate_gates,
)


def _outcome(
    seed: int,
    verdict: str,
    config: dict,
) -> SeedOutcome:
    return SeedOutcome(
        seed=seed,
        verdict=verdict,
        config=config,
        failure_type=None if verdict == "pass" else "fail_if_isolated_parts()",
        failure_type_normalized=None if verdict == "pass" else "fail_if_isolated_parts",
        failure_details=None if verdict == "pass" else "isolated antenna",
        elapsed_s=0.0,
    )


# --------------------------------------------------------------------------- #
# line_floor
# --------------------------------------------------------------------------- #


def test_check_line_floor_passes_when_above_threshold() -> None:
    gate = check_line_floor(1500, floor=1000)
    assert gate.status == "pass"
    assert gate.details["line_count"] == 1500


def test_check_line_floor_fails_when_below_threshold() -> None:
    gate = check_line_floor(400, floor=1000)
    assert gate.status == "fail"
    assert "below the 1000-line floor" in gate.reason


# --------------------------------------------------------------------------- #
# enum_coverage
# --------------------------------------------------------------------------- #


def test_literal_fields_extracts_literal_typed_annotations() -> None:
    @dataclass
    class Cfg:
        shape: Literal["a", "b", "c"]
        size: float
        layout: Literal["x", "y"]

    fields = _literal_fields(Cfg)
    assert sorted(fields.keys()) == ["layout", "shape"]
    assert fields["shape"] == ["a", "b", "c"]


def test_check_enum_coverage_passes_when_every_value_seen_in_pass(monkeypatch) -> None:
    @dataclass
    class FakeCfg:
        shape: Literal["a", "b", "c"]

    monkeypatch.setattr("agent.template_sweep_coverage._input_config_class", lambda slug: FakeCfg)

    outcomes = [
        _outcome(0, "pass", {"shape": "a"}),
        _outcome(1, "pass", {"shape": "b"}),
        _outcome(2, "pass", {"shape": "c"}),
    ]
    gate = check_enum_coverage("fake", outcomes)
    assert gate.status == "pass"
    assert gate.details["fields"]["shape"]["missing"] == []


def test_check_enum_coverage_fails_when_value_missing_or_only_in_failure(
    monkeypatch,
) -> None:
    @dataclass
    class FakeCfg:
        shape: Literal["a", "b", "c"]

    monkeypatch.setattr("agent.template_sweep_coverage._input_config_class", lambda slug: FakeCfg)

    outcomes = [
        _outcome(0, "pass", {"shape": "a"}),
        _outcome(1, "fail", {"shape": "b"}),  # b only seen in failure -> not exercised
        # c never sampled
    ]
    gate = check_enum_coverage("fake", outcomes)
    assert gate.status == "fail"
    missing_values = {(m["field"], m["value"]) for m in gate.details["missing"]}
    assert missing_values == {("shape", "b"), ("shape", "c")}


def test_check_enum_coverage_skips_when_no_enum_fields(monkeypatch) -> None:
    @dataclass
    class FakeCfg:
        size: float
        count: int

    monkeypatch.setattr("agent.template_sweep_coverage._input_config_class", lambda slug: FakeCfg)

    gate = check_enum_coverage("fake", [_outcome(0, "pass", {"size": 1.0, "count": 2})])
    assert gate.status == "skipped"
    assert "no Literal-typed enum fields" in gate.reason


def test_check_enum_coverage_skips_when_template_uninspectable(monkeypatch) -> None:
    monkeypatch.setattr("agent.template_sweep_coverage._input_config_class", lambda slug: None)
    gate = check_enum_coverage("nonexistent", [])
    assert gate.status == "skipped"


# --------------------------------------------------------------------------- #
# adopted_source
# --------------------------------------------------------------------------- #


def test_extract_adopted_source_ids_picks_S_ids_from_table() -> None:
    spec_text = (
        "## 采用源码索引（Adopted Source Index）\n"
        "| source_id | sample_id | model.py 来源 | 采纳用途 |\n"
        "|---|---|---|---|\n"
        "| S1 | rec_abc | `data/.../model.py:L1-L10` | desc1 |\n"
        "| S2 | rec_def | `data/.../model.py:L20-L30` | desc2 |\n"
        "\n## 部件（Parts）\n"
        "| S99 | should-not-be-picked |\n"  # outside section
    )
    assert _extract_adopted_source_ids(spec_text) == ["S1", "S2"]


def test_extract_adopted_source_ids_empty_when_section_missing() -> None:
    spec_text = "## 核心身份\nsome text\n"
    assert _extract_adopted_source_ids(spec_text) == []


def test_check_adopted_source_passes_when_all_ids_referenced(tmp_path: Path) -> None:
    spec = tmp_path / "articraft_template_authoring" / "specs" / "demo.md"
    spec.parent.mkdir(parents=True)
    spec.write_text(
        "## 采用源码索引（Adopted Source Index）\n"
        "| source_id | sample_id |\n|---|---|\n| S1 | x |\n| S2 | y |\n"
        "\n## next\n",
        encoding="utf-8",
    )
    template = tmp_path / "agent" / "templates" / "demo.py"
    template.parent.mkdir(parents=True)
    template.write_text(
        "from x import y\n# adopted: S1 from data/abc/model.py:L1-L10\n"
        "# adopted: S2 from data/def/model.py:L20-L30\n",
        encoding="utf-8",
    )
    gate = check_adopted_source("demo", repo_root=tmp_path)
    assert gate.status == "pass"
    assert gate.details["missing"] == []


def test_check_adopted_source_fails_when_template_missing_markers(tmp_path: Path) -> None:
    spec = tmp_path / "articraft_template_authoring" / "specs" / "demo.md"
    spec.parent.mkdir(parents=True)
    spec.write_text(
        "## 采用源码索引（Adopted Source Index）\n"
        "| source_id | sample_id |\n|---|---|\n| S1 | x |\n| S2 | y |\n"
        "\n## next\n",
        encoding="utf-8",
    )
    template = tmp_path / "agent" / "templates" / "demo.py"
    template.parent.mkdir(parents=True)
    template.write_text("# adopted: S1\n# no S2 marker here\n", encoding="utf-8")

    gate = check_adopted_source("demo", repo_root=tmp_path)
    assert gate.status == "fail"
    assert gate.details["missing"] == ["S2"]


def test_check_adopted_source_skips_when_spec_missing(tmp_path: Path) -> None:
    gate = check_adopted_source("no_spec_here", repo_root=tmp_path)
    assert gate.status == "skipped"
    assert "spec markdown not found" in gate.reason


def test_check_adopted_source_skips_when_spec_has_no_section(tmp_path: Path) -> None:
    spec = tmp_path / "articraft_template_authoring" / "specs" / "demo.md"
    spec.parent.mkdir(parents=True)
    spec.write_text("## 核心身份\nA description\n", encoding="utf-8")
    gate = check_adopted_source("demo", repo_root=tmp_path)
    assert gate.status == "skipped"
    assert "no Adopted Source Index entries" in gate.reason


# --------------------------------------------------------------------------- #
# aggregate
# --------------------------------------------------------------------------- #


def test_evaluate_gates_aggregates(monkeypatch, tmp_path: Path) -> None:
    @dataclass
    class FakeCfg:
        shape: Literal["a", "b"]

    monkeypatch.setattr("agent.template_sweep_coverage._input_config_class", lambda slug: FakeCfg)

    gates = evaluate_gates(
        slug="demo",
        line_count=1200,
        outcomes=[_outcome(0, "pass", {"shape": "a"}), _outcome(1, "pass", {"shape": "b"})],
        repo_root=tmp_path,  # no spec -> adopted_source skipped
        line_floor=1000,
    )
    assert gates.line_floor.status == "pass"
    assert gates.enum_coverage.status == "pass"
    assert gates.adopted_source.status == "skipped"
    assert gates.all_pass_or_skipped() is True
    assert gates.failing_gates() == []


def test_evaluate_gates_reports_failures(monkeypatch, tmp_path: Path) -> None:
    @dataclass
    class FakeCfg:
        shape: Literal["a", "b"]

    monkeypatch.setattr("agent.template_sweep_coverage._input_config_class", lambda slug: FakeCfg)

    gates = evaluate_gates(
        slug="demo",
        line_count=400,  # below floor
        outcomes=[_outcome(0, "pass", {"shape": "a"})],  # b missing
        repo_root=tmp_path,
        line_floor=1000,
    )
    failing = gates.failing_gates()
    assert "line_floor" in failing
    assert "enum_coverage" in failing
    assert gates.all_pass_or_skipped() is False
