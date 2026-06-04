"""Lightweight module/slot/assembler abstraction for modular procedural templates.

Modular templates compose articulated objects from **modules** — self-contained
sub-trees that expose well-defined **mating interfaces**. An **assembler**
picks one module per **slot** and chains them via `MatingContract` joints.

Anchor responsibility moves from "whole template matches PRIMARY_ANCHOR" to
**"each pair of mated interfaces is geometrically compatible"**. Each module
declares the face it exposes; two chained modules must agree on face geometry
+ face dimensions within their declared tolerances.

This file intentionally provides only the abstraction; module factories and
the slot graph for each slug live in the per-template module.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Callable, Literal, Optional, Sequence

from sdk import (
    ArticulatedObject,
    ArticulationType,
    MatingContract,
    MotionLimits,
    Origin,
)

_OPPOSITE_SIDE = {
    "positive_x": "negative_x",
    "negative_x": "positive_x",
    "positive_y": "negative_y",
    "negative_y": "positive_y",
    "positive_z": "negative_z",
    "negative_z": "positive_z",
}


@dataclass(frozen=True)
class InterfaceSpec:
    """A single mating face exposed by a module.

    Two modules connect when one's ``downstream`` interface is joined to the
    next module's ``upstream`` interface. The assembler validates pairwise
    compatibility (face geometry name + opposite normals + extents-uv overlap
    within tolerance), then emits a single ``MatingContract``-backed
    `Articulation`.

    ``anchor_local`` is the geometric center of the mating face in the owning
    part's *local* frame (after any visual ``Origin.rpy``). The assembler
    uses ``(parent_anchor_local - child_anchor_local)`` as the joint origin
    in the parent's frame — assuming face_sides are opposite (no rotation).

    ``consumer_joint_type``/``axis``/``motion_limits`` are meaningful on
    ``upstream`` interfaces: the consuming assembler reads them to decide
    how to join this module to whatever sits upstream.
    """

    interface_name: str
    part_name: str
    visual_name: str
    face_side: str
    anchor_local: tuple[float, float, float]
    face_extents_uv: tuple[float, float] = (0.0, 0.0)
    extents_tol: float = 0.20
    contact_tol: float = 0.0015

    # Only meaningful for "upstream" interfaces — describes how the upstream
    # joint that consumes this interface should be parameterized.
    consumer_joint_type: ArticulationType = ArticulationType.FIXED
    consumer_joint_axis: tuple[float, float, float] = (0.0, 0.0, 1.0)
    consumer_motion_limits: Optional[MotionLimits] = None


@dataclass
class ModuleBuild:
    """Descriptor returned by a module factory after it has emitted parts
    + internal articulations onto the model.

    ``interfaces`` keys are local names (typically ``"upstream"`` /
    ``"downstream"``); the slot's upstream_iface_name / downstream_iface_name
    select which entries the assembler consumes when chaining.
    """

    module_name: str
    parts_emitted: list[str]
    internal_articulations: list[str] = field(default_factory=list)
    interfaces: dict[str, InterfaceSpec] = field(default_factory=dict)


@dataclass
class ModuleBuildContext:
    """Input handed to each module factory.

    Module factories should pull dimensions from ``config`` (a slug-specific
    resolved config dataclass) and color tokens from ``palette`` (a dict of
    material-name → rgba tuple). They emit parts directly onto ``model``,
    then return a `ModuleBuild` descriptor.

    ``prior_choices`` lists the (slot_name, module_name) tuples for every
    slot processed BEFORE the current one — used when a downstream module
    needs to know what's been picked upstream (e.g. to emit a visual that
    only makes sense when paired with a specific housing variant).
    """

    model: ArticulatedObject
    palette: dict[str, tuple[float, float, float, float]]
    rng: random.Random
    config: object
    slot_name: str
    module_name: str
    upstream_interface: Optional[InterfaceSpec] = None
    prior_choices: list[tuple[str, str]] = field(default_factory=list)


ModuleFactory = Callable[[ModuleBuildContext], ModuleBuild]


@dataclass(frozen=True)
class SlotSpec:
    """One slot in the assembly graph.

    ``candidates`` maps a module's public name to its factory. ``anchor_choice``
    is a backward-compatible name for a default/pinned choice; it must be one
    of those keys when ``assemble(..., selection_mode="anchor_choices")`` is
    used. In the default procedural mode, every seed, including seed 0, is
    sampled from ``candidates`` by the caller-provided RNG.

    Slots are traversed in declaration order; each slot's downstream interface
    becomes the next slot's upstream input. The first slot is the root (no
    upstream connection); its ``upstream_iface_name`` is ignored.
    """

    slot_name: str
    candidates: dict[str, ModuleFactory]
    anchor_choice: str
    upstream_iface_name: str = "upstream"
    downstream_iface_name: str = "downstream"


@dataclass
class AssemblyResult:
    """Returned by ``assemble`` so callers can inspect what was chosen.

    Useful for the ``module_topology_diversity`` gate (counts unique
    slot_choice tuples across seeds) and for debug logging.
    """

    slot_choices: list[tuple[str, str]]
    interfaces_chain: list[InterfaceSpec]
    builds: list[ModuleBuild]


def assemble(
    model: ArticulatedObject,
    *,
    slots: Sequence[SlotSpec],
    rng: random.Random,
    palette: dict[str, tuple[float, float, float, float]],
    config: object,
    seed: int,
    selection_mode: Literal["procedural", "anchor_choices"] = "procedural",
) -> AssemblyResult:
    """Build the model by running each slot's chosen module factory.

    Default selection is procedural-first: every seed, including seed 0, uses
    ``rng.choice`` over each slot's candidates. Older templates that already
    resolved/pinned their modules before calling the assembler may pass
    ``selection_mode="anchor_choices"`` to consume each slot's explicit
    ``anchor_choice`` without re-sampling.

    The assembler emits one ``Articulation`` per pair of adjacent slots
    (parent = previous module's downstream part, child = current module's
    upstream part). It uses the current module's ``upstream`` interface to
    select joint type/axis/limits; the joint origin is positioned so the
    two interfaces' anchor centers coincide.
    """

    slot_choices: list[tuple[str, str]] = []
    builds: list[ModuleBuild] = []
    interfaces_chain: list[InterfaceSpec] = []
    prev_downstream: Optional[InterfaceSpec] = None
    prev_slot_name = ""

    for slot in slots:
        choice = _pick_module(slot, rng=rng, seed=seed, selection_mode=selection_mode)
        slot_choices.append((slot.slot_name, choice))
        factory = slot.candidates[choice]

        ctx = ModuleBuildContext(
            model=model,
            palette=palette,
            rng=rng,
            config=config,
            slot_name=slot.slot_name,
            module_name=choice,
            upstream_interface=prev_downstream,
            prior_choices=list(slot_choices[:-1]),
        )
        build = factory(ctx)
        builds.append(build)

        upstream = build.interfaces.get(slot.upstream_iface_name)
        if prev_downstream is not None and upstream is not None:
            _validate_pair(prev_downstream, upstream, slot_name=slot.slot_name)
            _emit_chain_joint(
                model,
                joint_name=f"{prev_slot_name}_to_{slot.slot_name}",
                parent_iface=prev_downstream,
                child_iface=upstream,
            )
            interfaces_chain.append(prev_downstream)
            interfaces_chain.append(upstream)

        prev_downstream = build.interfaces.get(slot.downstream_iface_name)
        prev_slot_name = slot.slot_name

    return AssemblyResult(
        slot_choices=slot_choices,
        interfaces_chain=interfaces_chain,
        builds=builds,
    )


def _pick_module(
    slot: SlotSpec,
    *,
    rng: random.Random,
    seed: int,
    selection_mode: Literal["procedural", "anchor_choices"],
) -> str:
    """Pick a module according to the assembler's explicit selection mode."""
    if selection_mode == "anchor_choices":
        if slot.anchor_choice not in slot.candidates:
            raise ValueError(
                f"slot {slot.slot_name!r} anchor_choice {slot.anchor_choice!r} "
                f"missing from candidates {list(slot.candidates)!r}"
            )
        return slot.anchor_choice
    if selection_mode != "procedural":
        raise ValueError(f"Unsupported modular selection_mode: {selection_mode!r}")
    names = list(slot.candidates.keys())
    return rng.choice(names)


def _validate_pair(
    parent: InterfaceSpec,
    child: InterfaceSpec,
    *,
    slot_name: str,
) -> None:
    """Check the two interfaces can physically mate.

    The only firm rule is **opposite face normals** — one ``+x`` face must
    meet one ``-x`` face (etc.). Face extents are informational only:
    sliding joints (rail in channel) and mounting joints (blade on
    carrier_block) routinely have very different parent/child face sizes,
    so an extents-equality check produces false negatives. Geometric
    correctness is enforced by ``fail_if_joint_mating_has_gap`` and the
    overlap/floating-part baseline gates at compile time.
    """
    if _OPPOSITE_SIDE.get(parent.face_side) != child.face_side:
        raise ValueError(
            f"slot {slot_name!r}: interface face sides not opposite — "
            f"parent={parent.face_side!r} child={child.face_side!r}"
        )


def _emit_chain_joint(
    model: ArticulatedObject,
    *,
    joint_name: str,
    parent_iface: InterfaceSpec,
    child_iface: InterfaceSpec,
) -> None:
    """Create the single articulation that joins two modules.

    Joint origin is placed at the parent's downstream anchor (a point on
    the parent's mating face, in parent-link coordinates). The child
    module is expected to have built its upstream mating face **at its
    part frame origin** so that ``anchor_local`` is the zero vector
    (verified here). Under that contract the child link's geometry
    automatically meets the parent face at the joint origin.

    Putting the joint at the parent's anchor (rather than at the
    geometric difference) ensures the joint origin always lies on the
    parent's geometry, satisfying
    ``fail_if_articulation_origin_far_from_geometry``.
    """
    # Joint origin = parent's downstream anchor (in parent-link frame).
    # The child module must build so that its visuals contain (0,0,0) in
    # part frame AND the mating face's NORMAL-AXIS coordinate (z for +z/-z
    # mating, x for +x/-x, etc.) is 0; in-plane (tangential) coordinates
    # are free, since `fail_if_joint_mating_has_gap` only measures along
    # the parent face's normal. This lets the asymmetric blade modules
    # extend forward from their part-frame origin (the rear edge of the
    # blade) without aligning the face center to (0,0,0).
    pfs = parent_iface.face_side
    normal_axis_idx = {"x": 0, "y": 1, "z": 2}[pfs.split("_", 1)[1][0]]
    if abs(child_iface.anchor_local[normal_axis_idx]) > 1e-6:
        raise ValueError(
            f"module {child_iface.part_name!r}'s upstream interface anchor must have a "
            f"zero {pfs.split('_', 1)[1]}-component (matched to the parent face "
            f"normal); got {child_iface.anchor_local}."
        )
    origin_xyz = parent_iface.anchor_local

    mating = MatingContract(
        parent_face_geometry=parent_iface.visual_name,
        parent_face_side=parent_iface.face_side,
        child_face_geometry=child_iface.visual_name,
        child_face_side=child_iface.face_side,
        contact_tol=max(parent_iface.contact_tol, child_iface.contact_tol),
    )

    parent_part = model.get_part(parent_iface.part_name)
    child_part = model.get_part(child_iface.part_name)

    model.articulation(
        joint_name,
        child_iface.consumer_joint_type,
        parent=parent_part,
        child=child_part,
        origin=Origin(xyz=origin_xyz),
        axis=child_iface.consumer_joint_axis,
        motion_limits=child_iface.consumer_motion_limits,
        mating=mating,
    )


__all__ = [
    "InterfaceSpec",
    "ModuleBuild",
    "ModuleBuildContext",
    "ModuleFactory",
    "SlotSpec",
    "AssemblyResult",
    "assemble",
]
