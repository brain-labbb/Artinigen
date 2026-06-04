from __future__ import annotations

import random

from agent.templates._modular import ModuleBuild, SlotSpec, assemble
from sdk import ArticulatedObject


def _empty_module(name: str):
    def _factory(_ctx) -> ModuleBuild:
        return ModuleBuild(module_name=name, parts_emitted=[])

    return _factory


def test_assemble_seed_zero_uses_procedural_selection_by_default() -> None:
    slot = SlotSpec(
        slot_name="body",
        candidates={"anchor": _empty_module("anchor"), "sampled": _empty_module("sampled")},
        anchor_choice="anchor",
    )

    result = assemble(
        ArticulatedObject(name="procedural_default"),
        slots=[slot],
        rng=random.Random(0),
        palette={},
        config=object(),
        seed=0,
    )

    assert result.slot_choices == [("body", "sampled")]


def test_assemble_can_explicitly_consume_pinned_anchor_choices() -> None:
    slot = SlotSpec(
        slot_name="body",
        candidates={"anchor": _empty_module("anchor"), "sampled": _empty_module("sampled")},
        anchor_choice="anchor",
    )

    result = assemble(
        ArticulatedObject(name="pinned_choices"),
        slots=[slot],
        rng=random.Random(0),
        palette={},
        config=object(),
        seed=0,
        selection_mode="anchor_choices",
    )

    assert result.slot_choices == [("body", "anchor")]
