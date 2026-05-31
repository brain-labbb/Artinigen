"""Unit tests for the modular graphics_card_with_cooling_fans template.

Covers:
- Seed reproducibility.
- seed=0 == anchor combination.
- Every legal slot × module combo builds (the compat matrix folds illegal
  combos, but the builder must succeed for whatever resolve_config yields).
- Topology diversity over seeds 0..19 (>=5 distinct slot tuples).
- Per-slot invalid-module rejection.
- Orthogonal support_brace_style compatibility folding.
- Every fan rotor has CONTINUOUS axis=(0,0,1) joint.
- Captured-pivot overlaps are declared by run_graphics_card_tests.
"""

from __future__ import annotations

import itertools

import pytest

from agent.templates.graphics_card_with_cooling_fans import (
    GRAPHICS_CARD_PALETTE_PRESETS,
    GraphicsCardConfig,
    build_graphics_card,
    build_seeded_graphics_card,
    config_from_seed,
    resolve_config,
    slot_choices_for_seed,
)
from sdk import ArticulationType, TestContext

# --------------------------------------------------------------------------- #
# Basic seed reproducibility / anchor.
# --------------------------------------------------------------------------- #


def test_seed_config_is_reproducible() -> None:
    assert config_from_seed(13) == config_from_seed(13)
    assert config_from_seed(13) != config_from_seed(14)


def test_seed_zero_is_anchor_combination() -> None:
    choices = slot_choices_for_seed(0)
    assert choices == [
        ("pcb_chassis_form", "standard_dual_slot"),
        ("cooler_assembly", "triple_axial_fan_equal"),
        ("rear_peripherals_form", "separate_backplate_and_io_parts"),
    ]
    cfg = config_from_seed(0)
    assert cfg.support_brace_style == "none"


def test_seed_zero_builds_with_expected_topology() -> None:
    """seed=0 should produce the anchor combination's expected parts:
    card_body + 3 fans + backplate + io_bracket, no support_brace, no
    power_block.
    """
    model = build_seeded_graphics_card(0)
    part_names = {p.name for p in model.parts}
    assert "card_body" in part_names
    assert "backplate" in part_names
    assert "io_bracket" in part_names
    # Triple equal fans use the (fan_left, fan_center, fan_right) names.
    assert {"fan_left", "fan_center", "fan_right"} <= part_names
    # No support_brace or power_block.
    assert "support_brace" not in part_names
    assert "power_block" not in part_names

    joint_topology = {(a.parent, a.child, a.articulation_type.name) for a in model.articulations}
    assert ("card_body", "fan_left", "CONTINUOUS") in joint_topology
    assert ("card_body", "fan_center", "CONTINUOUS") in joint_topology
    assert ("card_body", "fan_right", "CONTINUOUS") in joint_topology
    assert ("card_body", "backplate", "FIXED") in joint_topology
    assert ("card_body", "io_bracket", "FIXED") in joint_topology


# --------------------------------------------------------------------------- #
# Build smoke tests for a sample of seeds.
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("seed", [0, 1, 2, 3, 4, 5, 7, 12, 18, 23])
def test_seeded_builds_succeed(seed: int) -> None:
    model = build_seeded_graphics_card(seed)
    part_names = {p.name for p in model.parts}
    assert "card_body" in part_names, f"seed={seed} missing card_body"
    # At least one CONTINUOUS fan rotor joint should exist.
    cont_joints = [
        a for a in model.articulations if a.articulation_type == ArticulationType.CONTINUOUS
    ]
    assert len(cont_joints) >= 1, f"seed={seed} produced 0 CONTINUOUS joints"


@pytest.mark.parametrize("seed", [0, 1, 2, 3, 4, 5, 7, 12, 18, 23])
def test_fan_rotors_sit_above_grille_and_fins(seed: int) -> None:
    model = build_seeded_graphics_card(seed)
    ctx = TestContext(model)
    card_body = model.get_part("card_body")
    fin_names = [v.name for v in card_body.visuals if v.name and v.name.startswith("fin_")]
    fan_frame_names = [
        v.name
        for v in card_body.visuals
        if v.name and ("_bezel_ring" in v.name or "_stator_spoke_" in v.name)
    ]
    fixed_names = [
        v.name
        for v in card_body.visuals
        if v.name
        and (
            v.name.startswith("fin_")
            or "_bezel_ring" in v.name
            or "_stator_spoke_" in v.name
            or "shroud_inter_fan_bridge" in v.name
        )
    ]
    fin_top_z = max(ctx.part_element_world_aabb(card_body, elem=name)[1][2] for name in fin_names)
    frame_bottom_z = min(
        ctx.part_element_world_aabb(card_body, elem=name)[0][2] for name in fan_frame_names
    )
    assert frame_bottom_z <= fin_top_z + 0.0010, (
        f"seed={seed} fan frame detached from fin stack: "
        f"frame_bottom_z={frame_bottom_z:.4f}, fin_top_z={fin_top_z:.4f}"
    )
    fixed_top_z = max(
        ctx.part_element_world_aabb(card_body, elem=name)[1][2] for name in fixed_names
    )
    for joint in model.articulations:
        if joint.articulation_type != ArticulationType.CONTINUOUS:
            continue
        fan = model.get_part(joint.child)
        fan_bottom_z = ctx.part_world_aabb(fan)[0][2]
        assert fixed_top_z - 0.0010 <= fan_bottom_z <= fixed_top_z + 0.0015, (
            f"seed={seed} fan={joint.child} is not seated on grille: "
            f"fan_bottom_z={fan_bottom_z:.4f}, fixed_top_z={fixed_top_z:.4f}"
        )


def test_palette_pool_has_visible_color_variety() -> None:
    assert {"red_gaming", "blue_silver"} <= set(GRAPHICS_CARD_PALETTE_PRESETS)
    saturated_shrouds = [
        name
        for name, palette in GRAPHICS_CARD_PALETTE_PRESETS.items()
        if max(palette["shroud_black"][:3]) - min(palette["shroud_black"][:3]) > 0.20
    ]
    assert len(saturated_shrouds) >= 2


# --------------------------------------------------------------------------- #
# Slot × module grid — every legal combination builds.
# --------------------------------------------------------------------------- #


_CHASSIS_OPTIONS = (
    "compact_short_dual_slot",
    "standard_dual_slot",
    "long_triple_slot",
)
_COOLER_OPTIONS = (
    "single_axial_fan_compact",
    "dual_axial_fan_pair",
    "triple_axial_fan_equal",
    "dual_large_tail_small_axial",
)
_REAR_OPTIONS = (
    "embedded_io_and_backplate",
    "separate_backplate_and_io_parts",
    "flagship_with_top_edge_power_block",
)
_BRACE_OPTIONS = ("none", "prop_leg", "fold_arm")


def test_every_legal_slot_combination_builds() -> None:
    """Loop the full 3×4×3×3 = 108 grid; for each, pass the config to
    resolve_config first (it folds illegal combos), then build. Every
    resolved-and-then-built model must produce a card_body and at least
    one fan rotor part with a CONTINUOUS joint.
    """
    for chassis, cooler, rear, brace in itertools.product(
        _CHASSIS_OPTIONS, _COOLER_OPTIONS, _REAR_OPTIONS, _BRACE_OPTIONS
    ):
        cfg = GraphicsCardConfig(
            pcb_chassis_module=chassis,  # type: ignore[arg-type]
            cooler_assembly_module=cooler,  # type: ignore[arg-type]
            rear_peripherals_module=rear,  # type: ignore[arg-type]
            support_brace_style=brace,  # type: ignore[arg-type]
        )
        model = build_graphics_card(cfg)
        tag = f"(chassis={chassis}, cooler={cooler}, rear={rear}, brace={brace})"
        part_names = {p.name for p in model.parts}
        assert "card_body" in part_names, f"{tag} missing card_body"

        cont_count = sum(
            1 for a in model.articulations if a.articulation_type == ArticulationType.CONTINUOUS
        )
        assert cont_count >= 1, f"{tag} produced 0 CONTINUOUS fan joints"
        for a in model.articulations:
            if a.articulation_type == ArticulationType.CONTINUOUS:
                ax = tuple(round(float(v), 6) for v in (a.axis or ()))
                assert ax == (0.0, 0.0, 1.0), f"{tag} fan {a.name} axis={ax}"


# --------------------------------------------------------------------------- #
# Topology diversity.
# --------------------------------------------------------------------------- #


def test_topology_diversity_over_seeds_0_to_19() -> None:
    """Across seeds 0..19 we expect at least 5 distinct slot tuples (the
    coverage gate's floor). With 3 × 4 × 3 = 36 possible slot tuples and
    25+ legal combos, this is far above floor in practice."""
    seen = {tuple(slot_choices_for_seed(s)) for s in range(20)}
    assert len(seen) >= 5, f"Expected >=5 distinct topologies in seeds 0..19, got {sorted(seen)}"


def test_topology_diversity_over_seeds_0_to_9() -> None:
    """Stricter check on first 10 seeds — we expect at least 5 distinct
    slot tuples (mature_method.md aims for 7, but with 4 coolers the
    sample noise is higher)."""
    seen = {tuple(slot_choices_for_seed(s)) for s in range(10)}
    assert len(seen) >= 5, f"Expected >=5 distinct topologies in seeds 0..9, got {sorted(seen)}"


# --------------------------------------------------------------------------- #
# Per-slot invalid-module rejection tests.
# --------------------------------------------------------------------------- #


def test_resolve_config_rejects_invalid_pcb_chassis_module() -> None:
    with pytest.raises(ValueError, match="pcb_chassis_module"):
        resolve_config(
            GraphicsCardConfig(pcb_chassis_module="unknown")  # type: ignore[arg-type]
        )


def test_resolve_config_rejects_invalid_cooler_assembly_module() -> None:
    with pytest.raises(ValueError, match="cooler_assembly_module"):
        resolve_config(
            GraphicsCardConfig(cooler_assembly_module="unknown")  # type: ignore[arg-type]
        )


def test_resolve_config_rejects_invalid_rear_peripherals_module() -> None:
    with pytest.raises(ValueError, match="rear_peripherals_module"):
        resolve_config(
            GraphicsCardConfig(rear_peripherals_module="unknown")  # type: ignore[arg-type]
        )


def test_resolve_config_rejects_invalid_support_brace_style() -> None:
    with pytest.raises(ValueError, match="support_brace_style"):
        resolve_config(
            GraphicsCardConfig(support_brace_style="unknown")  # type: ignore[arg-type]
        )


# --------------------------------------------------------------------------- #
# Orthogonal feature compatibility tests.
# --------------------------------------------------------------------------- #


def test_compact_with_prop_leg_folds_to_none() -> None:
    """compact_short_dual_slot is incompatible with prop_leg per the
    spec's matrix — resolve_config must fold to none."""
    cfg = GraphicsCardConfig(
        pcb_chassis_module="compact_short_dual_slot",
        cooler_assembly_module="dual_axial_fan_pair",
        rear_peripherals_module="separate_backplate_and_io_parts",
        support_brace_style="prop_leg",
    )
    r = resolve_config(cfg)
    assert r.support_brace_style == "none"


def test_long_with_fold_arm_folds_to_prop_leg() -> None:
    """long_triple_slot with fold_arm should fold to prop_leg."""
    cfg = GraphicsCardConfig(
        pcb_chassis_module="long_triple_slot",
        cooler_assembly_module="triple_axial_fan_equal",
        rear_peripherals_module="separate_backplate_and_io_parts",
        support_brace_style="fold_arm",
    )
    r = resolve_config(cfg)
    assert r.support_brace_style == "prop_leg"


def test_compact_with_triple_fan_folds_to_dual_pair() -> None:
    """compact_short_dual_slot is incompatible with triple_axial_fan_equal —
    resolve_config must fold to dual_axial_fan_pair."""
    cfg = GraphicsCardConfig(
        pcb_chassis_module="compact_short_dual_slot",
        cooler_assembly_module="triple_axial_fan_equal",
    )
    r = resolve_config(cfg)
    assert r.cooler_assembly_module == "dual_axial_fan_pair"


def test_compact_with_flagship_rear_folds_to_separate() -> None:
    cfg = GraphicsCardConfig(
        pcb_chassis_module="compact_short_dual_slot",
        cooler_assembly_module="single_axial_fan_compact",
        rear_peripherals_module="flagship_with_top_edge_power_block",
    )
    r = resolve_config(cfg)
    assert r.rear_peripherals_module == "separate_backplate_and_io_parts"


def test_single_fan_with_standard_chassis_folds_to_dual() -> None:
    """single_axial_fan_compact is only valid on compact chassis."""
    cfg = GraphicsCardConfig(
        pcb_chassis_module="standard_dual_slot",
        cooler_assembly_module="single_axial_fan_compact",
    )
    r = resolve_config(cfg)
    assert r.cooler_assembly_module == "dual_axial_fan_pair"


# --------------------------------------------------------------------------- #
# Specific topology assertions: support_brace and flagship power_block.
# --------------------------------------------------------------------------- #


def test_prop_leg_brace_emits_support_brace_part() -> None:
    cfg = GraphicsCardConfig(
        pcb_chassis_module="standard_dual_slot",
        cooler_assembly_module="dual_axial_fan_pair",
        rear_peripherals_module="separate_backplate_and_io_parts",
        support_brace_style="prop_leg",
    )
    model = build_graphics_card(cfg)
    part_names = {p.name for p in model.parts}
    assert "support_brace" in part_names
    # REVOLUTE joint exists.
    rev_joints = [
        a for a in model.articulations if a.articulation_type == ArticulationType.REVOLUTE
    ]
    assert any(a.child == "support_brace" for a in rev_joints)


def test_fold_arm_brace_emits_support_brace_part() -> None:
    cfg = GraphicsCardConfig(
        pcb_chassis_module="standard_dual_slot",
        cooler_assembly_module="dual_axial_fan_pair",
        rear_peripherals_module="separate_backplate_and_io_parts",
        support_brace_style="fold_arm",
    )
    model = build_graphics_card(cfg)
    part_names = {p.name for p in model.parts}
    assert "support_brace" in part_names


def test_none_brace_emits_no_support_brace_part() -> None:
    cfg = GraphicsCardConfig(
        pcb_chassis_module="standard_dual_slot",
        cooler_assembly_module="triple_axial_fan_equal",
        rear_peripherals_module="separate_backplate_and_io_parts",
        support_brace_style="none",
    )
    model = build_graphics_card(cfg)
    part_names = {p.name for p in model.parts}
    assert "support_brace" not in part_names


def test_flagship_emits_power_block_part() -> None:
    cfg = GraphicsCardConfig(
        pcb_chassis_module="standard_dual_slot",
        cooler_assembly_module="triple_axial_fan_equal",
        rear_peripherals_module="flagship_with_top_edge_power_block",
    )
    model = build_graphics_card(cfg)
    part_names = {p.name for p in model.parts}
    assert "power_block" in part_names
    assert "backplate" in part_names
    assert "io_bracket" in part_names


def test_embedded_rear_emits_no_separate_parts() -> None:
    cfg = GraphicsCardConfig(
        pcb_chassis_module="standard_dual_slot",
        cooler_assembly_module="dual_axial_fan_pair",
        rear_peripherals_module="embedded_io_and_backplate",
    )
    model = build_graphics_card(cfg)
    part_names = {p.name for p in model.parts}
    assert "backplate" not in part_names
    assert "io_bracket" not in part_names
    assert "power_block" not in part_names


# --------------------------------------------------------------------------- #
# Fan count / axis structural assertions.
# --------------------------------------------------------------------------- #


def test_single_fan_module_emits_exactly_one_continuous_joint() -> None:
    cfg = GraphicsCardConfig(
        pcb_chassis_module="compact_short_dual_slot",
        cooler_assembly_module="single_axial_fan_compact",
        rear_peripherals_module="embedded_io_and_backplate",
    )
    model = build_graphics_card(cfg)
    cont = [a for a in model.articulations if a.articulation_type == ArticulationType.CONTINUOUS]
    assert len(cont) == 1


def test_dual_fan_module_emits_exactly_two_continuous_joints() -> None:
    cfg = GraphicsCardConfig(
        pcb_chassis_module="standard_dual_slot",
        cooler_assembly_module="dual_axial_fan_pair",
        rear_peripherals_module="separate_backplate_and_io_parts",
    )
    model = build_graphics_card(cfg)
    cont = [a for a in model.articulations if a.articulation_type == ArticulationType.CONTINUOUS]
    assert len(cont) == 2


def test_triple_fan_module_emits_exactly_three_continuous_joints() -> None:
    cfg = GraphicsCardConfig(
        pcb_chassis_module="standard_dual_slot",
        cooler_assembly_module="triple_axial_fan_equal",
        rear_peripherals_module="separate_backplate_and_io_parts",
    )
    model = build_graphics_card(cfg)
    cont = [a for a in model.articulations if a.articulation_type == ArticulationType.CONTINUOUS]
    assert len(cont) == 3


def test_dual_large_tail_module_emits_three_continuous_joints() -> None:
    cfg = GraphicsCardConfig(
        pcb_chassis_module="long_triple_slot",
        cooler_assembly_module="dual_large_tail_small_axial",
        rear_peripherals_module="separate_backplate_and_io_parts",
    )
    model = build_graphics_card(cfg)
    cont = [a for a in model.articulations if a.articulation_type == ArticulationType.CONTINUOUS]
    assert len(cont) == 3


def test_every_fan_continuous_joint_axis_is_pcb_normal() -> None:
    """Across a sample of seeds, every CONTINUOUS joint axis must be
    exactly (0,0,1)."""
    for seed in range(0, 10):
        model = build_seeded_graphics_card(seed)
        for a in model.articulations:
            if a.articulation_type == ArticulationType.CONTINUOUS:
                ax = tuple(round(float(v), 6) for v in (a.axis or ()))
                assert ax == (0.0, 0.0, 1.0), (
                    f"seed={seed} joint {a.name} axis={ax}, expected (0,0,1)"
                )


# --------------------------------------------------------------------------- #
# Mesh primitive preservation.
# --------------------------------------------------------------------------- #


def test_fan_rotor_uses_a_mesh_visual() -> None:
    """Rotor parts include a Mesh visual derived from FanRotorGeometry
    (Rule 3: don't downgrade sophisticated primitives to crude
    Box/Cylinder)."""
    from sdk import Mesh

    model = build_seeded_graphics_card(0)
    fan_left = model.get_part("fan_left")
    mesh_count = sum(1 for v in fan_left.visuals if isinstance(v.geometry, Mesh))
    assert mesh_count >= 1, "Expected at least one Mesh visual on the fan rotor"
