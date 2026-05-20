from __future__ import annotations

from pathlib import Path

import pytest

from cli import template as template_cli


def test_parse_seed_spec_supports_ranges_and_lists() -> None:
    assert template_cli.parse_seed_spec("1-3") == [1, 2, 3]
    assert template_cli.parse_seed_spec("1,3,5-7") == [1, 3, 5, 6, 7]


def test_parse_seed_spec_rejects_empty_input() -> None:
    with pytest.raises(ValueError, match="At least one seed"):
        template_cli.parse_seed_spec("")


def test_batch_ferris_wheel_dry_run(tmp_path: Path) -> None:
    exit_code = template_cli.batch_ferris_wheel(
        tmp_path,
        seeds=[1, 2],
        agent="codex",
        category_slug=None,
        dry_run=True,
    )

    assert exit_code == 0
    assert not (tmp_path / "data" / "records").exists()
