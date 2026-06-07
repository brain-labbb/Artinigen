"""Multi-seed compile sweep for procedural templates.

This is the core engine behind `articraft template compile-sweep`. For each
seed in the requested range, it:

1. Calls `<template_module>.config_from_seed(seed)` to materialize the config.
2. Writes a synthetic `model.py` under a temp directory using the same
   `GENERIC_MODEL_TEMPLATE` shape that `articraft template batch` uses.
3. Invokes `agent.compiler.compile_urdf_report(target="full")`, which runs
   both the author-defined `run_tests()` and the compiler-owned baseline
   (single-root, mesh assets, isolated parts, overlap, articulation-origin
   distance). Template sweep also promotes compiler disconnected-geometry
   warnings to seed failures so part-internal floating visual islands do not
   pass as acceptable template variants.
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
import subprocess
import sys
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
DEFAULT_COMPILE_TIMEOUT_S = 60.0
_DISCONNECTED_GEOMETRY_WARNING = "Disconnected geometry islands detected"
_DISCONNECTED_GEOMETRY_FAILURE_TYPE = (
    "fail_if_part_contains_disconnected_geometry_islands(tol=1e-06)"
)

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


def _disconnected_geometry_warning_details(warnings: Iterable[str]) -> str | None:
    for warning in warnings:
        text = str(warning)
        if _DISCONNECTED_GEOMETRY_WARNING in text:
            return (
                "Template sweep treats compiler disconnected-geometry warnings as failures. "
                "Fix floating visuals inside the named part by embedding them into the "
                "supporting surface, adding a real bridge/cantilever, or splitting them "
                "into separate fixed parts.\n"
                f"{text[:2000]}"
            )
    return None


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
            compile_report = compile_urdf_report(
                script_path,
                sdk_package=sdk_package,
                run_checks=True,
                target="full",
                rewrite_visual_glb=False,
            )
            disconnected_details = _disconnected_geometry_warning_details(compile_report.warnings)
            if disconnected_details is not None:
                return SeedOutcome(
                    seed=seed,
                    verdict="fail",
                    config=config_dict,
                    failure_type=_DISCONNECTED_GEOMETRY_FAILURE_TYPE,
                    failure_type_normalized=_normalize_failure_type(
                        _DISCONNECTED_GEOMETRY_FAILURE_TYPE
                    ),
                    failure_details=disconnected_details,
                    elapsed_s=time.monotonic() - start,
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


_SUBPROCESS_WORKER_SOURCE = """
import json
import sys
import traceback
from agent.template_sweep import _compile_one
try:
    outcome = _compile_one({slug!r}, {stem!r}, {seed}, {sdk_package!r})
    sys.stdout.write(json.dumps(outcome.to_dict()))
except BaseException as exc:
    sys.stderr.write(traceback.format_exc())
    raise
"""


def _seed_outcome_from_dict(payload: dict) -> SeedOutcome:
    return SeedOutcome(
        seed=int(payload["seed"]),
        verdict=str(payload["verdict"]),
        config=dict(payload.get("config") or {}),
        failure_type=payload.get("failure_type"),
        failure_type_normalized=payload.get("failure_type_normalized"),
        failure_details=payload.get("failure_details"),
        elapsed_s=float(payload.get("elapsed_s") or 0.0),
    )


def _timeout_outcome(seed: int, timeout_s: float) -> SeedOutcome:
    return SeedOutcome(
        seed=seed,
        verdict="fail",
        config={},
        failure_type=f"compile_timeout({timeout_s:.0f}s)",
        failure_type_normalized="compile_timeout",
        failure_details=(
            f"per-seed compile exceeded the {timeout_s:.0f}s wall-time budget "
            "and the worker subprocess was SIGKILL'd. Likely cause: a geometry "
            "QC step (fcl distance / trimesh boolean) entered a non-terminating "
            "loop on degenerate geometry produced by this seed."
        ),
        elapsed_s=float(timeout_s),
    )


def _subprocess_crash_outcome(seed: int, returncode: int, stderr: str) -> SeedOutcome:
    return SeedOutcome(
        seed=seed,
        verdict="fail",
        config={},
        failure_type=f"subprocess_crash(rc={returncode})",
        failure_type_normalized="subprocess_crash",
        failure_details=stderr[:2000] if stderr else f"non-zero return code {returncode}",
        elapsed_s=0.0,
    )


def _compile_one_via_subprocess(
    slug: str,
    stem: str,
    seed: int,
    sdk_package: str,
    *,
    timeout_s: float,
    repo_root: Path,
) -> SeedOutcome:
    """Run a single (slug, seed) compile in a fresh Python subprocess with a hard
    wall-time timeout. On timeout, the subprocess is SIGKILL'd and a synthetic
    `compile_timeout` SeedOutcome is returned so the sweep can continue past
    templates that hang inside non-Python-interruptible QC code (e.g. fcl)."""
    code = _SUBPROCESS_WORKER_SOURCE.format(
        slug=slug, stem=stem, seed=seed, sdk_package=sdk_package
    )
    try:
        proc = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=timeout_s,
            cwd=str(repo_root),
        )
    except subprocess.TimeoutExpired:
        return _timeout_outcome(seed, timeout_s)
    if proc.returncode != 0:
        return _subprocess_crash_outcome(seed, proc.returncode, proc.stderr)
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        return _subprocess_crash_outcome(
            seed,
            0,
            f"could not decode worker JSON: {exc}\nstdout preview: {proc.stdout[:500]!r}",
        )
    return _seed_outcome_from_dict(payload)


def _run_seeds_sequential(
    slug: str,
    stem: str,
    seeds: Iterable[int],
    sdk_package: str,
    progress: Callable[[SeedOutcome], None] | None = None,
    *,
    compile_timeout_s: float = 0.0,
    repo_root: Path | None = None,
) -> list[SeedOutcome]:
    outcomes: list[SeedOutcome] = []
    for seed in seeds:
        if compile_timeout_s > 0.0:
            outcome = _compile_one_via_subprocess(
                slug,
                stem,
                seed,
                sdk_package,
                timeout_s=compile_timeout_s,
                repo_root=repo_root or Path(__file__).resolve().parents[1],
            )
        else:
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
    *,
    compile_timeout_s: float = 0.0,
    repo_root: Path | None = None,
) -> list[SeedOutcome]:
    """Parallel seed runner.

    When `compile_timeout_s > 0`, each seed compile happens inside a fresh
    subprocess invoked via `subprocess.run(..., timeout=...)`. The parent
    parallelizes those via a ThreadPoolExecutor (threads block on .run()'s
    pipe), and SIGKILLs the subprocess on timeout — bulletproof against
    non-interruptible C-level hangs in geometry QC.

    When `compile_timeout_s == 0`, the legacy ProcessPoolExecutor path is used
    (faster on healthy templates, but a single hung seed will block one worker
    indefinitely).
    """
    outcomes: dict[int, SeedOutcome] = {}

    if compile_timeout_s > 0.0:
        root = repo_root or Path(__file__).resolve().parents[1]
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_map = {
                executor.submit(
                    _compile_one_via_subprocess,
                    slug,
                    stem,
                    seed,
                    sdk_package,
                    timeout_s=compile_timeout_s,
                    repo_root=root,
                ): seed
                for seed in seeds
            }
            for future in concurrent.futures.as_completed(future_map):
                seed = future_map[future]
                try:
                    outcome = future.result()
                except Exception as exc:  # noqa: BLE001 — should not happen now, but be safe
                    outcome = SeedOutcome(
                        seed=seed,
                        verdict="fail",
                        config={},
                        failure_type=f"thread_error:{type(exc).__name__}",
                        failure_type_normalized="thread_error",
                        failure_details=str(exc),
                        elapsed_s=0.0,
                    )
                outcomes[seed] = outcome
                if progress is not None:
                    progress(outcome)
        return [outcomes[seed] for seed in seeds]

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


def run_seed_outcomes(
    *,
    slug: str,
    stem: str,
    seeds: list[int],
    sdk_package: str = "sdk",
    max_workers: int | None = None,
    repo_root: Path | None = None,
    progress: Callable[[SeedOutcome], None] | None = None,
    compile_timeout_s: float = 0.0,
) -> list[SeedOutcome]:
    """Compile the requested seeds and return raw per-seed outcomes.

    `max_workers=1` (or `None` when there is a single seed) runs sequentially in
    the current process. Anything else uses a ProcessPoolExecutor (in-process
    workers) by default, or a ThreadPool+subprocess scheme when
    `compile_timeout_s > 0` so each seed has a hard wall-time budget enforced
    via SIGKILL.
    """
    if not seeds:
        raise ValueError("seeds must contain at least one entry")
    repo_root = repo_root or Path(__file__).resolve().parents[1]
    template_path = _template_module_path(slug, repo_root=repo_root)
    if not template_path.exists():
        raise FileNotFoundError(f"agent/templates/{slug}.py not found (looked at {template_path})")

    workers = max_workers if max_workers is not None else min(len(seeds), 4)
    if workers <= 1 or len(seeds) == 1:
        return _run_seeds_sequential(
            slug,
            stem,
            seeds,
            sdk_package,
            progress,
            compile_timeout_s=compile_timeout_s,
            repo_root=repo_root,
        )
    return _run_seeds_parallel(
        slug,
        stem,
        seeds,
        sdk_package,
        workers,
        progress,
        compile_timeout_s=compile_timeout_s,
        repo_root=repo_root,
    )


def build_sweep_report_from_outcomes(
    *,
    slug: str,
    stem: str,
    seeds: list[int],
    outcomes: list[SeedOutcome],
    pass_threshold: float = DEFAULT_PASS_THRESHOLD,
    repo_root: Path | None = None,
    state_dir: Path | None = None,
    elapsed_s: float = 0.0,
) -> SweepReport:
    """Aggregate existing outcomes into the same report shape used by run_sweep."""
    if not seeds:
        raise ValueError("seeds must contain at least one entry")
    repo_root = repo_root or Path(__file__).resolve().parents[1]
    template_path = _template_module_path(slug, repo_root=repo_root)
    if not template_path.exists():
        raise FileNotFoundError(f"agent/templates/{slug}.py not found (looked at {template_path})")

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

    gates = evaluate_gates(
        slug=slug,
        outcomes=outcomes,
        repo_root=repo_root,
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
        pass_rate=round(pass_rate, 6),
        pass_threshold=pass_threshold,
        verdict=verdict,
        elapsed_s=round(elapsed_s, 3),
        failure_clusters=clusters,
        cluster_streaks=cluster_streaks,
        escalation=escalation_payload,
        coverage_gates=gates.to_dict(),
    )


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
    compile_timeout_s: float = 0.0,
) -> SweepReport:
    """Run a multi-seed compile sweep and return the structured report."""
    started = time.monotonic()
    outcomes = run_seed_outcomes(
        slug=slug,
        stem=stem,
        seeds=seeds,
        sdk_package=sdk_package,
        max_workers=max_workers,
        repo_root=repo_root,
        progress=progress,
        compile_timeout_s=compile_timeout_s,
    )
    elapsed = time.monotonic() - started
    return build_sweep_report_from_outcomes(
        slug=slug,
        stem=stem,
        seeds=seeds,
        outcomes=outcomes,
        pass_threshold=pass_threshold,
        repo_root=repo_root,
        state_dir=state_dir,
        elapsed_s=elapsed,
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
