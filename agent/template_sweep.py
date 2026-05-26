"""Multi-seed compile sweep for procedural templates.

This is the core engine behind `articraft template compile-sweep`. For each
seed in the requested range, it:

1. Calls `<template_module>.config_from_seed(seed)` to materialize the config.
2. Writes a synthetic `model.py` under a temp directory using the same
   `GENERIC_MODEL_TEMPLATE` shape that `articraft template batch` uses.
3. Invokes `agent.compiler.compile_urdf_report(target="full")`, which runs
   both the author-defined `run_tests()` and the compiler-owned baseline
   (single-root, mesh assets, isolated parts, overlap, articulation-origin
   distance).
4. Records the verdict, primary failure type, and failure details.

Subsequent phases (in this same module) layer on failure clustering, streak
state, and coverage gates. This first cut only emits raw per-seed results
plus a top-level pass-rate verdict.
"""

from __future__ import annotations

import concurrent.futures
import dataclasses
import importlib
import json
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable

from agent.compiler import compile_urdf_report
from agent.feedback import compile_signal_bundle_from_exception
from agent.models import CompileSignal

DEFAULT_PASS_THRESHOLD = 0.95
DEFAULT_SEED_COUNT = 50

# Same shape as cli.template.GENERIC_MODEL_TEMPLATE; duplicated here to avoid a
# circular import between cli.template and agent.template_sweep. If the canonical
# template under cli.template ever changes, mirror it here too.
_GENERIC_MODEL_TEMPLATE = """from __future__ import annotations

from agent.templates.{slug} import (
    build_{stem},
    config_from_seed,
    run_{stem}_tests,
)
from sdk import AssetContext

SEED = {seed}
CONFIG = config_from_seed(SEED)
ASSETS = AssetContext.from_script(__file__)


def build_object_model():
    return build_{stem}(CONFIG, assets=ASSETS)


def run_tests():
    return run_{stem}_tests(object_model, CONFIG)


object_model = build_object_model()
"""


@dataclass(slots=True, frozen=True)
class SeedOutcome:
    """Per-seed compile result."""

    seed: int
    verdict: str  # "pass" | "fail"
    config: dict[str, Any]
    failure_type: str | None
    failure_type_normalized: str | None
    failure_details: str | None
    elapsed_s: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "seed": self.seed,
            "verdict": self.verdict,
            "config": self.config,
            "failure_type": self.failure_type,
            "failure_type_normalized": self.failure_type_normalized,
            "failure_details": self.failure_details,
            "elapsed_s": self.elapsed_s,
        }


@dataclass(slots=True)
class SweepReport:
    """Aggregate report for a sweep."""

    slug: str
    stem: str
    total_seeds: int
    seeds_requested: list[int]
    passed_seeds: list[int]
    failed_outcomes: list[SeedOutcome]
    line_count: int
    pass_rate: float
    pass_threshold: float
    verdict: str
    elapsed_s: float
    failure_clusters: list[Any] = field(default_factory=list)
    cluster_streaks: dict[str, int] = field(default_factory=dict)
    escalation: dict[str, Any] | None = None
    coverage_gates: dict[str, Any] | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def _cluster_dict(self, cluster: Any) -> dict[str, Any]:
        d = cluster.to_dict()
        d["streak_count"] = int(self.cluster_streaks.get(d.get("cluster_signature", ""), 1))
        return d

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "slug": self.slug,
            "stem": self.stem,
            "total_seeds": self.total_seeds,
            "seeds_requested": self.seeds_requested,
            "passed_seeds": self.passed_seeds,
            "failed_seeds": [outcome.to_dict() for outcome in self.failed_outcomes],
            "failure_clusters": [self._cluster_dict(c) for c in self.failure_clusters],
            "line_count": self.line_count,
            "pass_rate": self.pass_rate,
            "pass_threshold": self.pass_threshold,
            "verdict": self.verdict,
            "elapsed_s": self.elapsed_s,
        }
        if self.escalation is not None:
            payload["escalation"] = self.escalation
        if self.coverage_gates is not None:
            payload["coverage_gates"] = self.coverage_gates
        payload.update({k: v for k, v in self.extra.items() if k not in payload})
        return payload


def parse_seed_spec(spec: str) -> list[int]:
    """Parse a seed spec like '0-49' or '1,3,5-8' into an ordered list of ints."""
    seeds: list[int] = []
    seen: set[int] = set()
    for chunk in spec.split(","):
        part = chunk.strip()
        if not part:
            continue
        if "-" in part:
            start_text, end_text = part.split("-", 1)
            start = int(start_text.strip())
            end = int(end_text.strip())
            if end < start:
                raise ValueError(f"Invalid seed range: {part}")
            for seed in range(start, end + 1):
                if seed not in seen:
                    seen.add(seed)
                    seeds.append(seed)
        else:
            seed = int(part)
            if seed not in seen:
                seen.add(seed)
                seeds.append(seed)
    if not seeds:
        raise ValueError("At least one seed is required")
    return seeds


def _config_to_dict(config: Any) -> dict[str, Any]:
    if dataclasses.is_dataclass(config):
        return dataclasses.asdict(config)
    if hasattr(config, "__dict__"):
        return {k: v for k, v in vars(config).items() if not k.startswith("_")}
    return {"_repr": repr(config)}


def _normalize_failure_type(failure_type: str | None) -> str | None:
    """Strip parameter parens from a check_name so clusters group across tol values."""
    if failure_type is None:
        return None
    base = failure_type.split("(")[0].strip()
    return base or failure_type


def _extract_failure(exc: BaseException) -> tuple[str, str]:
    """Pick the (failure_type, details) tuple from a compile exception.

    Prefers the first non-warning signal in the attached bundle; falls back to
    the exception class name + message.
    """
    bundle = compile_signal_bundle_from_exception(exc)
    failure_signals: list[CompileSignal] = [
        signal for signal in bundle.signals if signal.severity == "failure"
    ]
    if failure_signals:
        primary = failure_signals[0]
        check = primary.check_name or primary.code or primary.kind or "unknown_failure"
        details = primary.details or primary.summary or ""
        return check, details
    return type(exc).__name__, str(exc)


def _line_count(path: Path) -> int:
    try:
        with path.open("r", encoding="utf-8") as fp:
            return sum(1 for _ in fp)
    except OSError:
        return 0


def _template_module_path(slug: str, *, repo_root: Path) -> Path:
    return repo_root / "agent" / "templates" / f"{slug}.py"


def _resolve_config_from_seed(slug: str, seed: int) -> Any:
    module = importlib.import_module(f"agent.templates.{slug}")
    config_from_seed = getattr(module, "config_from_seed", None)
    if not callable(config_from_seed):
        raise AttributeError(
            f"agent.templates.{slug} is missing a callable config_from_seed(seed)."
        )
    return config_from_seed(seed)


def _compile_one(slug: str, stem: str, seed: int, sdk_package: str) -> SeedOutcome:
    """Run a single (slug, seed) compile and return its outcome.

    Designed to be safe in either main process or a subprocess.
    """
    start = time.monotonic()
    config = _resolve_config_from_seed(slug, seed)
    config_dict = _config_to_dict(config)
    with tempfile.TemporaryDirectory(prefix=f"sweep_{slug}_{seed}_") as tmp:
        script_path = Path(tmp) / "model.py"
        script_path.write_text(
            _GENERIC_MODEL_TEMPLATE.format(slug=slug, stem=stem, seed=seed),
            encoding="utf-8",
        )
        try:
            compile_urdf_report(
                script_path,
                sdk_package=sdk_package,
                run_checks=True,
                target="full",
                rewrite_visual_glb=False,
            )
        except Exception as exc:  # noqa: BLE001 — captured into structured outcome
            failure_type, details = _extract_failure(exc)
            return SeedOutcome(
                seed=seed,
                verdict="fail",
                config=config_dict,
                failure_type=failure_type,
                failure_type_normalized=_normalize_failure_type(failure_type),
                failure_details=details,
                elapsed_s=time.monotonic() - start,
            )
    return SeedOutcome(
        seed=seed,
        verdict="pass",
        config=config_dict,
        failure_type=None,
        failure_type_normalized=None,
        failure_details=None,
        elapsed_s=time.monotonic() - start,
    )


def _run_seeds_sequential(
    slug: str,
    stem: str,
    seeds: Iterable[int],
    sdk_package: str,
    progress: Callable[[SeedOutcome], None] | None = None,
) -> list[SeedOutcome]:
    outcomes: list[SeedOutcome] = []
    for seed in seeds:
        outcome = _compile_one(slug, stem, seed, sdk_package)
        outcomes.append(outcome)
        if progress is not None:
            progress(outcome)
    return outcomes


def _run_seeds_parallel(
    slug: str,
    stem: str,
    seeds: list[int],
    sdk_package: str,
    max_workers: int,
    progress: Callable[[SeedOutcome], None] | None = None,
) -> list[SeedOutcome]:
    outcomes: dict[int, SeedOutcome] = {}
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        future_map = {
            executor.submit(_compile_one, slug, stem, seed, sdk_package): seed for seed in seeds
        }
        for future in concurrent.futures.as_completed(future_map):
            seed = future_map[future]
            try:
                outcome = future.result()
            except Exception as exc:  # noqa: BLE001 — subprocess crash
                outcome = SeedOutcome(
                    seed=seed,
                    verdict="fail",
                    config={},
                    failure_type=f"subprocess_error:{type(exc).__name__}",
                    failure_type_normalized=f"subprocess_error:{type(exc).__name__}",
                    failure_details=str(exc),
                    elapsed_s=0.0,
                )
            outcomes[seed] = outcome
            if progress is not None:
                progress(outcome)
    return [outcomes[seed] for seed in seeds]


def run_sweep(
    *,
    slug: str,
    stem: str,
    seeds: list[int],
    sdk_package: str = "sdk",
    pass_threshold: float = DEFAULT_PASS_THRESHOLD,
    max_workers: int | None = None,
    repo_root: Path | None = None,
    progress: Callable[[SeedOutcome], None] | None = None,
    state_dir: Path | None = None,
    line_floor: int = 1000,
) -> SweepReport:
    """Run a multi-seed compile sweep and return the structured report.

    `max_workers=1` (or `None` when there is a single seed) runs sequentially in
    the current process. Anything else uses a ProcessPoolExecutor so the SDK's
    `runpy` execution lock doesn't serialize the sweep.
    """
    if not seeds:
        raise ValueError("seeds must contain at least one entry")
    repo_root = repo_root or Path(__file__).resolve().parents[1]
    template_path = _template_module_path(slug, repo_root=repo_root)
    if not template_path.exists():
        raise FileNotFoundError(f"agent/templates/{slug}.py not found (looked at {template_path})")

    started = time.monotonic()
    workers = max_workers if max_workers is not None else min(len(seeds), 4)
    if workers <= 1 or len(seeds) == 1:
        outcomes = _run_seeds_sequential(slug, stem, seeds, sdk_package, progress)
    else:
        outcomes = _run_seeds_parallel(slug, stem, seeds, sdk_package, workers, progress)
    elapsed = time.monotonic() - started

    passed_seeds = [o.seed for o in outcomes if o.verdict == "pass"]
    failed_outcomes = [o for o in outcomes if o.verdict == "fail"]
    pass_rate = len(passed_seeds) / len(seeds) if seeds else 0.0

    # Local imports to avoid top-level cycles.
    from agent.template_sweep_clusters import cluster_failures
    from agent.template_sweep_coverage import evaluate_gates
    from agent.template_sweep_state import (
        compute_escalation,
        load_state,
        save_state,
        update_streaks,
    )

    clusters = cluster_failures(failed_outcomes)
    cluster_signatures = [c.cluster_signature for c in clusters]
    line_count = _line_count(template_path)

    gates = evaluate_gates(
        slug=slug,
        line_count=line_count,
        outcomes=outcomes,
        repo_root=repo_root,
        line_floor=line_floor,
    )

    verdict = "pass" if pass_rate >= pass_threshold and gates.all_pass_or_skipped() else "fail"

    cluster_streaks: dict[str, int] = {sig: 1 for sig in cluster_signatures}
    escalation_payload: dict[str, Any] | None = None
    if state_dir is not None:
        previous = load_state(state_dir, slug)
        next_state = update_streaks(
            slug=slug,
            previous=previous,
            current_cluster_signatures=cluster_signatures,
            current_pass_rate=pass_rate,
            current_verdict=verdict,
        )
        save_state(state_dir, next_state)
        cluster_streaks = dict(next_state.cluster_streaks)
        decision = compute_escalation(next_state)
        escalation_payload = decision.to_dict()

    return SweepReport(
        slug=slug,
        stem=stem,
        total_seeds=len(seeds),
        seeds_requested=list(seeds),
        passed_seeds=passed_seeds,
        failed_outcomes=failed_outcomes,
        line_count=line_count,
        pass_rate=round(pass_rate, 6),
        pass_threshold=pass_threshold,
        verdict=verdict,
        elapsed_s=round(elapsed, 3),
        failure_clusters=clusters,
        cluster_streaks=cluster_streaks,
        escalation=escalation_payload,
        coverage_gates=gates.to_dict(),
    )


def report_to_json(report: SweepReport, *, indent: int | None = 2) -> str:
    """Serialize report to JSON string."""
    return json.dumps(report.to_dict(), indent=indent, sort_keys=False, default=str)


def write_report(report: SweepReport, *, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report_to_json(report), encoding="utf-8")


def _ascii_progress_line(outcome: SeedOutcome, *, total: int, done_count: int) -> str:
    state = "PASS" if outcome.verdict == "pass" else "FAIL"
    elapsed = f"{outcome.elapsed_s:.2f}s"
    if outcome.verdict == "fail":
        ft = outcome.failure_type_normalized or outcome.failure_type or "unknown"
        return f"[{done_count}/{total}] seed={outcome.seed} {state} ({elapsed}) {ft}"
    return f"[{done_count}/{total}] seed={outcome.seed} {state} ({elapsed})"


def stderr_progress_reporter(total: int) -> Callable[[SeedOutcome], None]:
    """Return a progress callback that writes one short line per seed to stderr."""
    import sys

    state = {"count": 0}

    def _report(outcome: SeedOutcome) -> None:
        state["count"] += 1
        line = _ascii_progress_line(outcome, total=total, done_count=state["count"])
        print(line, file=sys.stderr, flush=True)

    return _report
