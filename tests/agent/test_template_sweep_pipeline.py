from __future__ import annotations

import json
from pathlib import Path

from agent import template_sweep_pipeline
from agent.template_sweep import SeedOutcome
from agent.template_sweep_pipeline import run_sweep_pipeline


def _fake_template(repo_root: Path, *, lines: int = 1200) -> None:
    path = repo_root / "agent" / "templates" / "stub_slug.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("x = 1\n" * lines, encoding="utf-8")


def _outcome(seed: int, *, verdict: str = "pass") -> SeedOutcome:
    if verdict == "fail":
        return SeedOutcome(
            seed=seed,
            verdict="fail",
            config={"seed": seed},
            failure_type="fail_if_parts_overlap_in_current_pose()",
            failure_type_normalized="fail_if_parts_overlap_in_current_pose",
            failure_details=f"seed-{seed}-overlap",
            elapsed_s=0.01,
        )
    return SeedOutcome(
        seed=seed,
        verdict="pass",
        config={"seed": seed},
        failure_type=None,
        failure_type_normalized=None,
        failure_details=None,
        elapsed_s=0.01,
    )


def _stub_seed_runner(monkeypatch, *, failing_seeds: set[int] | None = None):
    calls: list[list[int]] = []
    failures = failing_seeds or set()

    def fake_run_seed_outcomes(**kwargs):
        seeds = list(kwargs["seeds"])
        calls.append(seeds)
        return [_outcome(seed, verdict="fail" if seed in failures else "pass") for seed in seeds]

    monkeypatch.setattr(template_sweep_pipeline, "run_seed_outcomes", fake_run_seed_outcomes)
    return calls


def test_pipeline_all_stages_pass_and_does_not_recompile_prior_seeds(monkeypatch, tmp_path: Path):
    _fake_template(tmp_path)
    calls = _stub_seed_runner(monkeypatch)

    report = run_sweep_pipeline(
        slug="stub_slug",
        stem="stub",
        repo_root=tmp_path,
        max_workers=1,
        state_dir=None,
        pass_threshold=1.0,
    )

    assert report.verdict == "pass"
    assert report.stopped_at is None
    assert [stage.status for stage in report.stages] == ["pass", "pass", "pass", "pass"]
    assert calls == [list(range(0, 1)), list(range(1, 5)), list(range(5, 20)), list(range(20, 50))]


def test_pipeline_seed0_fail_skips_remaining_stages(monkeypatch, tmp_path: Path):
    _fake_template(tmp_path)
    calls = _stub_seed_runner(monkeypatch, failing_seeds={0})

    report = run_sweep_pipeline(
        slug="stub_slug",
        stem="stub",
        repo_root=tmp_path,
        max_workers=1,
        state_dir=None,
        pass_threshold=1.0,
    )

    assert report.verdict == "fail"
    assert report.stopped_at == "seed0"
    assert [stage.status for stage in report.stages] == ["fail", "skipped", "skipped", "skipped"]
    assert calls == [[0]]
    assert report.repair_summary["failed_stage"] == "seed0"
    assert report.repair_summary["failed_seeds"] == [0]
    assert report.repair_summary["top_failure_clusters"]


def test_pipeline_fast_fail_skips_later_stages(monkeypatch, tmp_path: Path):
    _fake_template(tmp_path)
    calls = _stub_seed_runner(monkeypatch, failing_seeds={2})

    report = run_sweep_pipeline(
        slug="stub_slug",
        stem="stub",
        repo_root=tmp_path,
        max_workers=1,
        state_dir=None,
        pass_threshold=1.0,
    )

    assert report.verdict == "fail"
    assert report.stopped_at == "fast"
    assert [stage.status for stage in report.stages] == ["pass", "fail", "skipped", "skipped"]
    assert calls == [[0], [1, 2, 3, 4]]


def test_pipeline_medium_fail_skips_final(monkeypatch, tmp_path: Path):
    _fake_template(tmp_path)
    calls = _stub_seed_runner(monkeypatch, failing_seeds={12})

    report = run_sweep_pipeline(
        slug="stub_slug",
        stem="stub",
        repo_root=tmp_path,
        max_workers=1,
        state_dir=None,
        pass_threshold=1.0,
    )

    assert report.verdict == "fail"
    assert report.stopped_at == "medium"
    assert [stage.status for stage in report.stages] == ["pass", "pass", "fail", "skipped"]
    assert calls == [[0], [1, 2, 3, 4], list(range(5, 20))]


def test_pipeline_final_fail_returns_fail(monkeypatch, tmp_path: Path):
    _fake_template(tmp_path)
    calls = _stub_seed_runner(monkeypatch, failing_seeds={49})

    report = run_sweep_pipeline(
        slug="stub_slug",
        stem="stub",
        repo_root=tmp_path,
        max_workers=1,
        state_dir=None,
        pass_threshold=1.0,
    )

    assert report.verdict == "fail"
    assert report.stopped_at == "final"
    assert [stage.status for stage in report.stages] == ["pass", "pass", "pass", "fail"]
    assert calls == [[0], [1, 2, 3, 4], list(range(5, 20)), list(range(20, 50))]


def test_pipeline_repair_summary_includes_failing_coverage_gates(monkeypatch, tmp_path: Path):
    _fake_template(tmp_path, lines=3)
    _stub_seed_runner(monkeypatch)

    report = run_sweep_pipeline(
        slug="stub_slug",
        stem="stub",
        repo_root=tmp_path,
        max_workers=1,
        state_dir=None,
        line_floor=1000,
    )

    assert report.verdict == "fail"
    assert report.stopped_at == "seed0"
    assert "line_floor" in report.repair_summary["failing_coverage_gates"]
    assert report.repair_summary["next_action"].startswith("Fix the largest failure cluster")


def test_pipeline_state_tracking_updates_once_per_run(monkeypatch, tmp_path: Path):
    _fake_template(tmp_path)
    _stub_seed_runner(monkeypatch, failing_seeds={2})
    state_dir = tmp_path / "state"

    report = run_sweep_pipeline(
        slug="stub_slug",
        stem="stub",
        repo_root=tmp_path,
        max_workers=1,
        state_dir=state_dir,
    )

    assert report.stopped_at == "fast"
    state = json.loads((state_dir / "stub_slug.json").read_text(encoding="utf-8"))
    assert len(state["sweep_history"]) == 1
