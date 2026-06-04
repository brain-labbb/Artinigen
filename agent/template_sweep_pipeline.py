"""Incremental multi-stage sweep pipeline for procedural templates."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from agent.template_sweep import (
    DEFAULT_PASS_THRESHOLD,
    SeedOutcome,
    SweepReport,
    build_sweep_report_from_outcomes,
    run_seed_outcomes,
)

PIPELINE_NEXT_ACTION = (
    "Fix the largest failure cluster first, rerun the pipeline from seed 0 after editing "
    "the template, and do not run viewer batch until the pipeline passes."
)


@dataclass(slots=True, frozen=True)
class PipelineStageSpec:
    name: str
    added_seeds: list[int]
    cumulative_seeds: list[int]


PIPELINE_STAGES: tuple[PipelineStageSpec, ...] = (
    PipelineStageSpec("seed0", [0], [0]),
    PipelineStageSpec("fast", list(range(1, 5)), list(range(0, 5))),
    PipelineStageSpec("medium", list(range(5, 20)), list(range(0, 20))),
    PipelineStageSpec("final", list(range(20, 50)), list(range(0, 50))),
)


@dataclass(slots=True)
class PipelineStageResult:
    name: str
    added_seeds: list[int]
    cumulative_seeds: list[int]
    status: str
    report: SweepReport | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "added_seeds": list(self.added_seeds),
            "cumulative_seeds": list(self.cumulative_seeds),
            "status": self.status,
            "report": None if self.report is None else self.report.to_dict(),
        }


@dataclass(slots=True)
class PipelineReport:
    slug: str
    stem: str
    verdict: str
    stopped_at: str | None
    pass_threshold: float
    stages: list[PipelineStageResult]
    repair_summary: dict[str, Any] = field(default_factory=dict)
    elapsed_s: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "slug": self.slug,
            "stem": self.stem,
            "verdict": self.verdict,
            "stopped_at": self.stopped_at,
            "pass_threshold": self.pass_threshold,
            "stages": [stage.to_dict() for stage in self.stages],
            "repair_summary": dict(self.repair_summary),
            "elapsed_s": self.elapsed_s,
        }


def pipeline_report_to_json(report: PipelineReport, *, indent: int | None = 2) -> str:
    return json.dumps(report.to_dict(), indent=indent, sort_keys=False, default=str)


def write_pipeline_report(report: PipelineReport, *, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(pipeline_report_to_json(report), encoding="utf-8")


def build_repair_summary(stage_name: str, report: SweepReport) -> dict[str, Any]:
    report_payload = report.to_dict()
    coverage_gates = report_payload.get("coverage_gates") or {}
    failing_gates = {
        name: gate
        for name, gate in coverage_gates.items()
        if isinstance(gate, dict) and gate.get("status") not in {"pass", "skipped"}
    }
    failed_seeds = [outcome.seed for outcome in report.failed_outcomes]
    return {
        "failed_stage": stage_name,
        "failed_seeds": failed_seeds,
        "failing_coverage_gates": failing_gates,
        "top_failure_clusters": report_payload.get("failure_clusters", [])[:3],
        "escalation": report_payload.get("escalation"),
        "next_action": PIPELINE_NEXT_ACTION,
    }


def run_sweep_pipeline(
    *,
    slug: str,
    stem: str,
    sdk_package: str = "sdk",
    pass_threshold: float = DEFAULT_PASS_THRESHOLD,
    max_workers: int | None = None,
    repo_root: Path | None = None,
    progress: Callable[[SeedOutcome], None] | None = None,
    stage_progress: Callable[[str, PipelineStageResult], None] | None = None,
    state_dir: Path | None = None,
    compile_timeout_s: float = 0.0,
) -> PipelineReport:
    repo_root = repo_root or Path(__file__).resolve().parents[1]
    started = time.monotonic()
    outcomes_by_seed: dict[int, SeedOutcome] = {}
    stages: list[PipelineStageResult] = []
    stopped_at: str | None = None
    repair_summary: dict[str, Any] = {}

    for index, spec in enumerate(PIPELINE_STAGES):
        if stage_progress is not None:
            stage_progress(
                "start",
                PipelineStageResult(
                    name=spec.name,
                    added_seeds=list(spec.added_seeds),
                    cumulative_seeds=list(spec.cumulative_seeds),
                    status="running",
                    report=None,
                ),
            )
        stage_started = time.monotonic()
        added_outcomes = run_seed_outcomes(
            slug=slug,
            stem=stem,
            seeds=spec.added_seeds,
            sdk_package=sdk_package,
            max_workers=max_workers,
            repo_root=repo_root,
            progress=progress,
            compile_timeout_s=compile_timeout_s,
        )
        outcomes_by_seed.update({outcome.seed: outcome for outcome in added_outcomes})
        cumulative_outcomes = [outcomes_by_seed[seed] for seed in spec.cumulative_seeds]
        is_final_stage = index == len(PIPELINE_STAGES) - 1
        report = build_sweep_report_from_outcomes(
            slug=slug,
            stem=stem,
            seeds=spec.cumulative_seeds,
            outcomes=cumulative_outcomes,
            pass_threshold=pass_threshold,
            repo_root=repo_root,
            state_dir=state_dir if is_final_stage else None,
            elapsed_s=time.monotonic() - stage_started,
        )
        if report.verdict == "fail" and not is_final_stage and state_dir is not None:
            report = build_sweep_report_from_outcomes(
                slug=slug,
                stem=stem,
                seeds=spec.cumulative_seeds,
                outcomes=cumulative_outcomes,
                pass_threshold=pass_threshold,
                repo_root=repo_root,
                state_dir=state_dir,
                elapsed_s=time.monotonic() - stage_started,
            )
        status = report.verdict
        stage_result = PipelineStageResult(
            name=spec.name,
            added_seeds=list(spec.added_seeds),
            cumulative_seeds=list(spec.cumulative_seeds),
            status=status,
            report=report,
        )
        stages.append(stage_result)
        if stage_progress is not None:
            stage_progress("end", stage_result)
        if status == "fail":
            stopped_at = spec.name
            repair_summary = build_repair_summary(spec.name, report)
            for skipped in PIPELINE_STAGES[index + 1 :]:
                skipped_result = PipelineStageResult(
                    name=skipped.name,
                    added_seeds=list(skipped.added_seeds),
                    cumulative_seeds=list(skipped.cumulative_seeds),
                    status="skipped",
                    report=None,
                )
                stages.append(skipped_result)
                if stage_progress is not None:
                    stage_progress("end", skipped_result)
            break

    verdict = "fail" if stopped_at is not None else "pass"
    return PipelineReport(
        slug=slug,
        stem=stem,
        verdict=verdict,
        stopped_at=stopped_at,
        pass_threshold=pass_threshold,
        stages=stages,
        repair_summary=repair_summary,
        elapsed_s=round(time.monotonic() - started, 3),
    )
