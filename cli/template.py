from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from agent.runner import create_workbench_draft_record
from agent.template_sweep import (
    DEFAULT_COMPILE_TIMEOUT_S,
    DEFAULT_PASS_THRESHOLD,
    DEFAULT_SEED_COUNT,
    parse_seed_spec,
    report_to_json,
    run_sweep,
    stderr_progress_reporter,
    write_report,
)
from agent.template_sweep_pipeline import (
    PipelineStageResult,
    pipeline_report_to_json,
    run_sweep_pipeline,
    write_pipeline_report,
)
from cli.common import add_data_root_argument, warn_if_post_commit_hook_missing
from cli.external import _compile_record, _refresh_external_record, _validate_external_record
from storage.collections import CollectionStore
from storage.dataset_workflow import promote_record_workflow
from storage.datasets import DatasetStore
from storage.queries import StorageQueries
from storage.repo import StorageRepo
from storage.revisions import active_model_path
from storage.search import SearchIndex

ALLOWED_EXTERNAL_AGENTS = ("codex", "claude-code")
DEFAULT_PROVIDER_BY_AGENT = {
    "codex": "openai",
    "claude-code": "anthropic",
}

# Registry of procedural templates available for batch generation.
# Maps the template slug (module name under agent/templates/) to the function stem used
# inside that module: the template MUST export `build_<stem>`, `config_from_seed`, and
# `run_<stem>_tests`.
TEMPLATE_REGISTRY: dict[str, str] = {
    "barrier_gate_boom": "barrier_gate",
    "barrier_gate_leaf_gate": "barrier_gate",
    "bicycle_crankset_and_pedal_assembly": "bicycle_crankset",
    "blender_countertop": "blender",
    "immersion_blender": "blender",
    "box_fan_with_control_knob": "box_fan",
    "camcorder_with_flipout_screen": "camcorder",
    "camera_flash": "camera_flash",
    "camera_lens": "camera_lens",
    "cannon": "cannon",
    "cantilever_articulated_arm": "cantilever_arm",
    "cctv_mast_with_pantilt_camera_head": "cctv_mast_camera",
    "ceiling_fan": "ceiling_fan",
    "ceiling_light_fixture_adjustable": "ceiling_light",
    "chest_freezer_with_hinged_lid": "chest_freezer",
    "coaxial_rotary_stack": "coaxial_rotary_stack",
    "crane_tower": "crane_tower",
    "desk_with_drawer": "desk_with_drawer",
    "desk_with_drawer_card_catalog": "desk_with_drawer",
    "desktop_monitor_with_tilt_swivel_stand": "desktop_monitor",
    "monitor_mount": "monitor_mount",
    "paper_cutter_guillotine": "paper_cutter_guillotine",
    "desktop_pc_tower": "desktop_pc_tower",
    "display_freezer_with_sliding_glass_lids": "display_freezer",
    "dj_equipment": "dj_equipment",
    "drone": "drone",
    "graphics_card_with_cooling_fans": "graphics_card",
    "louvered_shutter_assembly": "louvered_shutter",
    "retractable_utility_knife": "retractable_utility_knife",
    "screwcap_bottle": "screwcap_bottle",
    "screwin_light_bulb_with_socket": "screwin_light_bulb_with_socket",
    "serial_elbow_arm": "serial_elbow_arm",
    "ferris_wheel": "ferris_wheel",
    "sliding_window": "sliding_window",
    "tackle_box_with_simple_hinged_lid": "tackle_box",
    "telescoping_boom": "telescoping_boom",
    "turntable": "turntable",
    "wind_turbine": "wind_turbine",
    "standing_desk_with_synchronous_telescoping_legs_and_articulated_controls": "standing_desk",
    "platform_cart": "platform_cart",
    "rolling_toolbox_with_telescoping_handle": "rolling_toolbox",
    "refrigerator_with_hinged_doors": "refrigerator",
    "revolving_door": "revolving_door",
    "simple_aframe_step_ladder": "simple_aframe_step_ladder",
    "stand_mixer": "stand_mixer",
}

GENERIC_MODEL_TEMPLATE = """from __future__ import annotations

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


def _write_template_model(model_path: Path, *, slug: str, stem: str, seed: int) -> None:
    model_path.parent.mkdir(parents=True, exist_ok=True)
    body = GENERIC_MODEL_TEMPLATE.format(slug=slug, stem=stem, seed=seed)
    model_path.write_text(body, encoding="utf-8")


def batch_template(
    repo_root: Path,
    *,
    slug: str,
    stem: str,
    seeds: list[int],
    agent: str,
    category_slug: str | None,
    dry_run: bool,
) -> int:
    if dry_run:
        for seed in seeds:
            prompt = f"seeded {slug} {seed}"
            print(f"[seed={seed}] dry-run: would create record for prompt={prompt!r}")
        print(f"batch dry-run completed for {len(seeds)} seed(s)")
        return 0

    repo = StorageRepo(repo_root)
    repo.ensure_layout()
    provider = DEFAULT_PROVIDER_BY_AGENT[agent]
    failures: list[str] = []

    for seed in seeds:
        prompt = f"seeded {slug} {seed}"
        print(f"[seed={seed}] starting")
        try:
            record_dir = create_workbench_draft_record(
                repo_root=repo_root,
                prompt_text=prompt,
                provider=provider,
                model_id=None,
                thinking_level=None,
                sdk_package="sdk",
                label=f"{stem}_seed_{seed}",
                tags=["template_batch", slug],
                record_id=None,
                external_agent=agent,
            )
        except ValueError as exc:
            failures.append(f"seed={seed}: init failed: {exc}")
            continue

        record_id = record_dir.name
        model_path = active_model_path(repo, record_id)
        _write_template_model(model_path, slug=slug, stem=stem, seed=seed)

        status = _compile_record(repo_root, record_dir, target="visual", validate=True)
        if status != 0:
            failures.append(f"seed={seed}: compile/check failed for {record_id}")
            continue

        errors = _validate_external_record(repo, record_id)
        if errors:
            failures.append(f"seed={seed}: validation failed for {record_id}: {'; '.join(errors)}")
            continue

        if category_slug:
            _refresh_external_record(
                repo,
                record_id,
                final_status="external_finalized",
            )
            try:
                entry, category, _, _stats = promote_record_workflow(
                    repo,
                    DatasetStore(repo),
                    StorageQueries(repo),
                    record_id=record_id,
                    category_title=None,
                    category_slug=category_slug,
                    dataset_id=None,
                    promoted_at=datetime.now(timezone.utc)
                    .replace(microsecond=0)
                    .isoformat()
                    .replace("+00:00", "Z"),
                )
            except ValueError as exc:
                failures.append(f"seed={seed}: promote failed for {record_id}: {exc}")
                continue
            CollectionStore(repo).ensure_workbench()
            print(
                f"[seed={seed}] finalized into category={category.get('slug') or category_slug}: "
                f"{record_id} dataset_id={entry.get('dataset_id')}"
            )
        else:
            _refresh_external_record(repo, record_id, final_status="external_ready")
            print(f"[seed={seed}] ready: {record_id}")

    stats = SearchIndex(repo).rebuild()
    print(
        f"search_index={stats.path} records={stats.record_count} "
        f"categories={stats.category_count} workbench_entries={stats.workbench_entry_count}"
    )

    if failures:
        print("batch completed with failures:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print(f"batch completed successfully for {len(seeds)} seed(s)")
    return 0


def batch_ferris_wheel(
    repo_root: Path,
    *,
    seeds: list[int],
    agent: str,
    category_slug: str | None,
    dry_run: bool,
) -> int:
    return batch_template(
        repo_root,
        slug="ferris_wheel",
        stem=TEMPLATE_REGISTRY["ferris_wheel"],
        seeds=seeds,
        agent=agent,
        category_slug=category_slug,
        dry_run=dry_run,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="articraft template")
    add_data_root_argument(parser)
    subparsers = parser.add_subparsers(dest="command", required=True)

    batch = subparsers.add_parser(
        "batch", help="Batch-generate records from a procedural template."
    )
    batch_sub = batch.add_subparsers(dest="template_name", required=True)

    for slug in TEMPLATE_REGISTRY:
        sp = batch_sub.add_parser(slug, help=f"Batch-generate seeded {slug} records.")
        sp.add_argument(
            "--seeds",
            required=True,
            help="Seed list/ranges, e.g. '1-20' or '1,3,5-8'.",
        )
        sp.add_argument("--agent", default="codex", choices=ALLOWED_EXTERNAL_AGENTS)
        sp.add_argument(
            "--category-slug",
            default=None,
            help="Optional dataset category slug. When set, records are finalized and promoted.",
        )
        sp.add_argument(
            "--dry-run",
            action="store_true",
            help="Print the planned batch without creating records.",
        )

    fp = subparsers.add_parser(
        "anchor-fingerprint",
        help=(
            "Extract the geometry fingerprint of a 5-star anchor record so it can be "
            "diffed against a template's seed=0 fingerprint."
        ),
    )
    fp.add_argument(
        "anchor",
        help="Anchor reference, e.g. 'rec_ceiling_fan_xxx' or 'rec_ceiling_fan_xxx:rev_000001'.",
    )
    fp.add_argument(
        "--indent", type=int, default=2, help="JSON indentation (default 2; 0 for compact)."
    )

    sweep = subparsers.add_parser(
        "compile-sweep",
        help="Run multi-seed full-baseline compile sweep for a procedural template.",
    )
    sweep.add_argument("slug", choices=sorted(TEMPLATE_REGISTRY.keys()))
    sweep.add_argument(
        "--seeds",
        default=f"0-{DEFAULT_SEED_COUNT - 1}",
        help=(f"Seed list/ranges; defaults to '0-{DEFAULT_SEED_COUNT - 1}' (DEFAULT_SEED_COUNT)."),
    )
    sweep.add_argument(
        "--pass-threshold",
        type=float,
        default=DEFAULT_PASS_THRESHOLD,
        help=(f"Minimum pass_rate required for verdict=pass (default {DEFAULT_PASS_THRESHOLD})."),
    )
    sweep.add_argument(
        "--max-workers",
        type=int,
        default=None,
        help=(
            "ProcessPoolExecutor worker count. Defaults to min(len(seeds), 4); "
            "use 1 to run sequentially in the current process."
        ),
    )
    sweep.add_argument(
        "--sdk-package", default="sdk", help="SDK package to load (defaults to 'sdk')."
    )
    sweep.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Optional file path to write the JSON report to (in addition to stdout).",
    )
    sweep.add_argument(
        "--state-dir",
        type=Path,
        default=None,
        help=(
            "Directory to persist per-slug streak state across sweeps. "
            "Defaults to <repo_root>/.articraft/template_sweep_state when omitted. "
            "Pass an empty string to disable streak tracking."
        ),
    )
    sweep.add_argument(
        "--line-floor",
        type=int,
        default=1000,
        help="Minimum line count for the line_floor gate (default 1000).",
    )
    sweep.add_argument(
        "--compile-timeout",
        type=float,
        default=DEFAULT_COMPILE_TIMEOUT_S,
        help=(
            "Per-seed wall-time budget in seconds. Each seed compile runs in a "
            "fresh subprocess that is SIGKILL'd on timeout; the seed is marked "
            "compile_timeout in the JSON. Set to 0 to disable timeouts (legacy "
            f"in-process ProcessPool path). Default {DEFAULT_COMPILE_TIMEOUT_S:.0f}s."
        ),
    )
    sweep.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress per-seed stderr progress lines.",
    )

    pipeline = subparsers.add_parser(
        "sweep-pipeline",
        help="Run incremental seed0/fast/medium/final compile sweep pipeline.",
    )
    pipeline.add_argument("slug", choices=sorted(TEMPLATE_REGISTRY.keys()))
    pipeline.add_argument(
        "--pass-threshold",
        type=float,
        default=DEFAULT_PASS_THRESHOLD,
        help=(
            f"Minimum pass_rate required for each stage verdict=pass (default {DEFAULT_PASS_THRESHOLD})."
        ),
    )
    pipeline.add_argument(
        "--max-workers",
        type=int,
        default=None,
        help=(
            "ProcessPoolExecutor worker count. Defaults to min(len(stage seeds), 4); "
            "use 1 to run sequentially in the current process."
        ),
    )
    pipeline.add_argument(
        "--sdk-package", default="sdk", help="SDK package to load (defaults to 'sdk')."
    )
    pipeline.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Optional file path to write the JSON report to (in addition to stdout).",
    )
    pipeline.add_argument(
        "--state-dir",
        type=Path,
        default=None,
        help=(
            "Directory to persist per-slug streak state across pipeline runs. "
            "Defaults to <repo_root>/.articraft/template_sweep_state when omitted. "
            "Pass an empty string to disable streak tracking."
        ),
    )
    pipeline.add_argument(
        "--line-floor",
        type=int,
        default=1000,
        help="Minimum line count for the line_floor gate (default 1000).",
    )
    pipeline.add_argument(
        "--compile-timeout",
        type=float,
        default=DEFAULT_COMPILE_TIMEOUT_S,
        help=(
            "Per-seed wall-time budget in seconds. Each seed compile runs in a "
            "fresh subprocess that is SIGKILL'd on timeout; the seed is marked "
            "compile_timeout in the JSON. Set to 0 to disable timeouts (legacy "
            f"in-process ProcessPool path). Default {DEFAULT_COMPILE_TIMEOUT_S:.0f}s."
        ),
    )
    pipeline.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress per-seed and per-stage progress lines.",
    )

    return parser


def _resolve_state_dir(repo_root: Path, override: Path | None) -> Path | None:
    """Resolve the per-slug streak-state directory.

    Passing an empty string on the CLI maps to override=Path('') which we treat
    as 'disable streak tracking' (returns None). Otherwise default to
    `<repo_root>/.articraft/template_sweep_state`.
    """
    if override is None:
        return Path(repo_root) / ".articraft" / "template_sweep_state"
    text = str(override).strip()
    if not text or text == ".":
        return None
    return Path(text)


def compile_sweep(
    *,
    slug: str,
    stem: str,
    seeds: list[int],
    pass_threshold: float,
    max_workers: int | None,
    sdk_package: str,
    out_path: Path | None,
    state_dir: Path | None,
    line_floor: int,
    compile_timeout_s: float,
    quiet: bool,
) -> int:
    progress = None if quiet else stderr_progress_reporter(total=len(seeds))
    try:
        report = run_sweep(
            slug=slug,
            stem=stem,
            seeds=seeds,
            sdk_package=sdk_package,
            pass_threshold=pass_threshold,
            max_workers=max_workers,
            progress=progress,
            state_dir=state_dir,
            line_floor=line_floor,
            compile_timeout_s=compile_timeout_s,
        )
    except (FileNotFoundError, AttributeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    payload = report_to_json(report)
    print(payload)
    if out_path is not None:
        write_report(report, out_path=out_path)
    return 0 if report.verdict == "pass" else 1


def _pipeline_stage_progress(event: str, stage: PipelineStageResult) -> None:
    if event == "start":
        print(
            f"[stage={stage.name}] starting added={stage.added_seeds} "
            f"cumulative={stage.cumulative_seeds[0]}-{stage.cumulative_seeds[-1]}",
            file=sys.stderr,
            flush=True,
        )
        return
    if stage.status == "skipped":
        print(f"[stage={stage.name}] skipped", file=sys.stderr, flush=True)
        return
    report = stage.report
    elapsed = "" if report is None else f" ({report.elapsed_s:.2f}s)"
    print(
        f"[stage={stage.name}] {stage.status.upper()}{elapsed}",
        file=sys.stderr,
        flush=True,
    )


def sweep_pipeline(
    *,
    slug: str,
    stem: str,
    pass_threshold: float,
    max_workers: int | None,
    sdk_package: str,
    out_path: Path | None,
    state_dir: Path | None,
    line_floor: int,
    compile_timeout_s: float,
    quiet: bool,
) -> int:
    progress = None if quiet else stderr_progress_reporter(total=DEFAULT_SEED_COUNT)
    stage_progress = None if quiet else _pipeline_stage_progress
    try:
        report = run_sweep_pipeline(
            slug=slug,
            stem=stem,
            sdk_package=sdk_package,
            pass_threshold=pass_threshold,
            max_workers=max_workers,
            progress=progress,
            stage_progress=stage_progress,
            state_dir=state_dir,
            line_floor=line_floor,
            compile_timeout_s=compile_timeout_s,
        )
    except (FileNotFoundError, AttributeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    payload = pipeline_report_to_json(report)
    print(payload)
    if out_path is not None:
        write_pipeline_report(report, out_path=out_path)
    print(
        f"sweep-pipeline {slug} {report.verdict.upper()} "
        f"stages={len(report.stages)} seeds={DEFAULT_SEED_COUNT} elapsed={report.elapsed_s:.2f}s",
        file=sys.stderr,
        flush=True,
    )
    return 0 if report.verdict == "pass" else 1


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "anchor-fingerprint":
        import json as _json

        from agent.template_sweep_anchor import extract_fingerprint_from_anchor

        try:
            fp = extract_fingerprint_from_anchor(args.anchor, repo_root=args.repo_root)
        except (FileNotFoundError, ValueError) as exc:
            print(str(exc), file=sys.stderr)
            return 2
        indent = None if int(args.indent) <= 0 else int(args.indent)
        print(_json.dumps(fp.to_dict(), indent=indent))
        return 0

    if args.command == "compile-sweep":
        try:
            seeds = parse_seed_spec(args.seeds)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        state_dir = _resolve_state_dir(args.repo_root, args.state_dir)
        return compile_sweep(
            slug=args.slug,
            stem=TEMPLATE_REGISTRY[args.slug],
            seeds=seeds,
            pass_threshold=float(args.pass_threshold),
            max_workers=(None if args.max_workers is None else int(args.max_workers)),
            sdk_package=str(args.sdk_package),
            out_path=args.out,
            state_dir=state_dir,
            line_floor=int(args.line_floor),
            compile_timeout_s=float(args.compile_timeout),
            quiet=bool(args.quiet),
        )

    if args.command == "sweep-pipeline":
        state_dir = _resolve_state_dir(args.repo_root, args.state_dir)
        return sweep_pipeline(
            slug=args.slug,
            stem=TEMPLATE_REGISTRY[args.slug],
            pass_threshold=float(args.pass_threshold),
            max_workers=(None if args.max_workers is None else int(args.max_workers)),
            sdk_package=str(args.sdk_package),
            out_path=args.out,
            state_dir=state_dir,
            line_floor=int(args.line_floor),
            compile_timeout_s=float(args.compile_timeout),
            quiet=bool(args.quiet),
        )

    if args.command != "batch" or args.template_name not in TEMPLATE_REGISTRY:
        parser.error("Unsupported template command")

    try:
        seeds = parse_seed_spec(args.seeds)
    except ValueError as exc:
        print(str(exc))
        return 1

    if not args.dry_run:
        warn_if_post_commit_hook_missing(args.repo_root)

    return batch_template(
        args.repo_root,
        slug=args.template_name,
        stem=TEMPLATE_REGISTRY[args.template_name],
        seeds=seeds,
        agent=args.agent,
        category_slug=str(args.category_slug or "").strip() or None,
        dry_run=bool(args.dry_run),
    )
