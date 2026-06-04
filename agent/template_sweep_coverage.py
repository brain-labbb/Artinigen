"""Modular coverage gate for `articraft template compile-sweep`.

The template authoring route is now modular-only. A sweep passes coverage when
the template declares `__modular__ = True`, exposes `slot_choices_for_seed`, and
the passing seeds produce enough distinct slot/module choice tuples.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

from agent.template_sweep import SeedOutcome

MODULE_TOPOLOGY_MIN_DISTINCT = 5
MODULE_TOPOLOGY_MIN_SWEEP_SIZE = 20


@dataclass(slots=True)
class CoverageGateResult:
    name: str
    status: str  # "pass" | "fail" | "skipped"
    details: dict[str, Any] = field(default_factory=dict)
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "details": self.details,
            "reason": self.reason,
        }


@dataclass(slots=True)
class CoverageGates:
    module_topology_diversity: CoverageGateResult

    def _iter_gates(self):
        return (self.module_topology_diversity,)

    def to_dict(self) -> dict[str, Any]:
        return {
            "module_topology_diversity": self.module_topology_diversity.to_dict(),
        }

    def all_pass_or_skipped(self) -> bool:
        return all(gate.status in {"pass", "skipped"} for gate in self._iter_gates())

    def failing_gates(self) -> list[str]:
        return [gate.name for gate in self._iter_gates() if gate.status == "fail"]


def _template_module(slug: str):
    try:
        return importlib.import_module(f"agent.templates.{slug}")
    except ImportError:
        return None


def is_modular_template(slug: str) -> bool:
    module = _template_module(slug)
    return bool(getattr(module, "__modular__", False)) if module is not None else False


def _slot_choices_for_seed(slug: str, seed: int) -> Any:
    module = _template_module(slug)
    if module is None:
        raise ImportError(f"agent.templates.{slug} could not be imported")
    fn = getattr(module, "slot_choices_for_seed", None)
    if not callable(fn):
        raise AttributeError(
            f"agent.templates.{slug} is missing callable slot_choices_for_seed(seed)"
        )
    return fn(seed)


def _normalize_slot_choices(raw: Any) -> tuple[tuple[str, str], ...]:
    if isinstance(raw, Mapping):
        items = list(raw.items())
    elif isinstance(raw, Sequence) and not isinstance(raw, (str, bytes, bytearray)):
        items = list(raw)
    else:
        raise ValueError("slot_choices_for_seed must return a mapping or sequence of pairs")

    normalized: list[tuple[str, str]] = []
    for index, item in enumerate(items):
        if not (
            isinstance(item, Sequence)
            and not isinstance(item, (str, bytes, bytearray))
            and len(item) == 2
        ):
            raise ValueError(
                "slot_choices_for_seed entries must be (slot_name, module_name) pairs; "
                f"entry {index} was {item!r}"
            )
        slot_name, module_name = item
        if not isinstance(slot_name, str) or not isinstance(module_name, str):
            raise ValueError(
                "slot_choices_for_seed entries must contain string slot/module names; "
                f"entry {index} was {item!r}"
            )
        normalized.append((slot_name, module_name))

    if not normalized:
        raise ValueError("slot_choices_for_seed returned no slot choices")
    return tuple(normalized)


def check_module_topology_diversity(
    slug: str,
    outcomes: Sequence[SeedOutcome],
    *,
    min_distinct: int = MODULE_TOPOLOGY_MIN_DISTINCT,
    min_sweep_size: int = MODULE_TOPOLOGY_MIN_SWEEP_SIZE,
) -> CoverageGateResult:
    if len(outcomes) < min_sweep_size:
        return CoverageGateResult(
            name="module_topology_diversity",
            status="skipped",
            details={
                "total_outcomes": len(outcomes),
                "min_sweep_size": min_sweep_size,
                "min_distinct": min_distinct,
            },
            reason=(
                "module_topology_diversity is enforced once the cumulative sweep "
                f"has at least {min_sweep_size} seeds."
            ),
        )

    if not is_modular_template(slug):
        return CoverageGateResult(
            name="module_topology_diversity",
            status="fail",
            details={"slug": slug, "__modular__": False, "min_distinct": min_distinct},
            reason=(
                "template is not marked `__modular__ = True`; new parameterized "
                "templates must use the modular slot/module route."
            ),
        )

    passing = [outcome for outcome in outcomes if outcome.verdict == "pass"]
    distinct: dict[tuple[tuple[str, str], ...], list[int]] = {}
    errors: list[dict[str, Any]] = []
    for outcome in passing:
        try:
            choices = _normalize_slot_choices(_slot_choices_for_seed(slug, outcome.seed))
        except Exception as exc:  # noqa: BLE001 - report malformed seed choices as gate data
            errors.append(
                {
                    "seed": outcome.seed,
                    "error_kind": type(exc).__name__,
                    "error": str(exc),
                }
            )
            continue
        distinct.setdefault(choices, []).append(outcome.seed)

    details: dict[str, Any] = {
        "total_outcomes": len(outcomes),
        "passing_seed_count": len(passing),
        "min_distinct": min_distinct,
        "distinct_count": len(distinct),
        "distinct_choices": [
            {
                "slot_choices": list(choices),
                "example_seed": seeds[0],
                "seed_count": len(seeds),
            }
            for choices, seeds in distinct.items()
        ],
        "errors": errors,
    }

    if errors:
        return CoverageGateResult(
            name="module_topology_diversity",
            status="fail",
            details=details,
            reason=(
                "one or more passing seeds could not be mapped through "
                "slot_choices_for_seed(seed); fix the modular reporting function."
            ),
        )

    if len(distinct) >= min_distinct:
        return CoverageGateResult(
            name="module_topology_diversity",
            status="pass",
            details=details,
        )

    return CoverageGateResult(
        name="module_topology_diversity",
        status="fail",
        details=details,
        reason=(
            f"only {len(distinct)} distinct passing slot-choice tuple(s) were found; "
            f"at least {min_distinct} are required. Add real module candidates, "
            "repair failing module combinations, or narrow invalid seed domains."
        ),
    )


def evaluate_gates(
    *,
    slug: str,
    outcomes: Sequence[SeedOutcome],
    repo_root: Path,
    line_count: int | None = None,
) -> CoverageGates:
    _ = repo_root, line_count
    return CoverageGates(
        module_topology_diversity=check_module_topology_diversity(slug, outcomes),
    )
