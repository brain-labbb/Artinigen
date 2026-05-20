from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from agent.runner import create_workbench_draft_record
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

FERRIS_WHEEL_MODEL_TEMPLATE = """from __future__ import annotations

from agent.templates.ferris_wheel import (
    build_ferris_wheel,
    config_from_seed,
    run_ferris_wheel_tests,
)
from sdk import AssetContext

SEED = {seed}
CONFIG = config_from_seed(SEED)
ASSETS = AssetContext.from_script(__file__)


def build_object_model():
    return build_ferris_wheel(CONFIG, assets=ASSETS)


def run_tests():
    return run_ferris_wheel_tests(object_model, CONFIG)


object_model = build_object_model()
"""


def parse_seed_spec(spec: str) -> list[int]:
    seeds: list[int] = []
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
            seeds.extend(range(start, end + 1))
        else:
            seeds.append(int(part))
    if not seeds:
        raise ValueError("At least one seed is required")
    return seeds


def _write_ferris_wheel_model(model_path: Path, *, seed: int) -> None:
    model_path.parent.mkdir(parents=True, exist_ok=True)
    model_path.write_text(FERRIS_WHEEL_MODEL_TEMPLATE.format(seed=seed), encoding="utf-8")


def batch_ferris_wheel(
    repo_root: Path,
    *,
    seeds: list[int],
    agent: str,
    category_slug: str | None,
    dry_run: bool,
) -> int:
    if dry_run:
        for seed in seeds:
            prompt = f"seeded ferris wheel {seed}"
            print(f"[seed={seed}] dry-run: would create record for prompt={prompt!r}")
        print(f"batch dry-run completed for {len(seeds)} seed(s)")
        return 0

    repo = StorageRepo(repo_root)
    repo.ensure_layout()
    provider = DEFAULT_PROVIDER_BY_AGENT[agent]
    failures: list[str] = []

    for seed in seeds:
        prompt = f"seeded ferris wheel {seed}"
        print(f"[seed={seed}] starting")
        try:
            record_dir = create_workbench_draft_record(
                repo_root=repo_root,
                prompt_text=prompt,
                provider=provider,
                model_id=None,
                thinking_level=None,
                sdk_package="sdk",
                label=f"ferris_seed_{seed}",
                tags=["template_batch", "ferris_wheel"],
                record_id=None,
                external_agent=agent,
            )
        except ValueError as exc:
            failures.append(f"seed={seed}: init failed: {exc}")
            continue

        record_id = record_dir.name
        model_path = active_model_path(record_dir)
        _write_ferris_wheel_model(model_path, seed=seed)

        status = _compile_record(repo_root, record_dir, target="full", validate=True)
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


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="articraft template")
    add_data_root_argument(parser)
    subparsers = parser.add_subparsers(dest="command", required=True)

    batch = subparsers.add_parser(
        "batch", help="Batch-generate records from a procedural template."
    )
    batch_sub = batch.add_subparsers(dest="template_name", required=True)

    ferris = batch_sub.add_parser("ferris_wheel", help="Batch-generate seeded ferris wheels.")
    ferris.add_argument(
        "--seeds",
        required=True,
        help="Seed list/ranges, e.g. '1-20' or '1,3,5-8'.",
    )
    ferris.add_argument("--agent", default="codex", choices=ALLOWED_EXTERNAL_AGENTS)
    ferris.add_argument(
        "--category-slug",
        default=None,
        help="Optional dataset category slug. When set, records are finalized and promoted.",
    )
    ferris.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the planned batch without creating records.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command != "batch" or args.template_name != "ferris_wheel":
        parser.error("Unsupported template command")

    try:
        seeds = parse_seed_spec(args.seeds)
    except ValueError as exc:
        print(str(exc))
        return 1

    if not args.dry_run:
        warn_if_post_commit_hook_missing(args.repo_root)

    return batch_ferris_wheel(
        args.repo_root,
        seeds=seeds,
        agent=args.agent,
        category_slug=str(args.category_slug or "").strip() or None,
        dry_run=bool(args.dry_run),
    )
