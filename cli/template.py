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

# Registry of procedural templates available for batch generation.
# Maps the template slug (module name under agent/templates/) to the function stem used
# inside that module: the template MUST export `build_<stem>`, `config_from_seed`, and
# `run_<stem>_tests`.
TEMPLATE_REGISTRY: dict[str, str] = {
    "ferris_wheel": "ferris_wheel",
    "sliding_window": "sliding_window",
    "tackle_box_with_simple_hinged_lid": "tackle_box",
    "telescoping_boom": "telescoping_boom",
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

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

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
