from __future__ import annotations

import pytest

from agent.templates.dj_equipment import (
    DjEquipmentConfig,
    build_dj_equipment,
    build_seeded_dj_equipment,
    config_from_seed,
    resolve_config,
    slot_choices_for_seed,
)


def test_seed_config_is_reproducible() -> None:
    assert config_from_seed(17) == config_from_seed(17)
    assert config_from_seed(17) != config_from_seed(18)


@pytest.mark.parametrize("seed", [0, 1, 2, 3, 5, 7, 12, 22])
def test_seeded_builds_have_chassis_and_deck_parts(seed: int) -> None:
    model = build_seeded_dj_equipment(seed)
    part_names = {p.name for p in model.parts}
    # housing + carry_handle always exist regardless of module mix.
    assert "housing" in part_names
    assert "carry_handle" in part_names
    # deck_layout always produces left_platter + right_platter (the
    # right_platter slot is reused as a tonearm in the alt variant).
    assert "left_platter" in part_names
    assert "right_platter" in part_names
    # controls always produces a crossfader plus side faders (which may
    # be either fader caps or pad-style buttons).
    assert "crossfader" in part_names
    assert "left_volume_fader" in part_names
    assert "right_volume_fader" in part_names


def test_seed_zero_is_anchor_combination() -> None:
    """seed=0 must reproduce the PRIMARY_ANCHOR module combination so any
    smoke test on seed 0 lands on the canonical 7-part topology."""
    choices = slot_choices_for_seed(0)
    assert choices == [
        ("chassis", "controller_chassis"),
        ("deck_layout", "dual_jog_decks"),
        ("controls", "triple_fader_strip"),
    ]


def test_seed_zero_matches_primary_anchor_joint_topology() -> None:
    """seed=0 must produce the anchor's exact 6 joints (REVOLUTE platters,
    PRISMATIC faders, REVOLUTE carry_handle), all parented to housing."""
    model = build_seeded_dj_equipment(0)
    topology = {(a.parent, a.child, a.articulation_type.name) for a in model.articulations}
    expected = {
        ("housing", "left_platter", "REVOLUTE"),
        ("housing", "right_platter", "REVOLUTE"),
        ("housing", "crossfader", "PRISMATIC"),
        ("housing", "left_volume_fader", "PRISMATIC"),
        ("housing", "right_volume_fader", "PRISMATIC"),
        ("housing", "carry_handle", "REVOLUTE"),
    }
    assert topology == expected


def test_topology_diversity_over_seeds() -> None:
    """Across seeds 0..9 we expect at least 7 distinct topology
    combinations (out of 8 possible). RNG can occasionally repeat at
    small sample sizes so we leave a 1-combination margin."""
    seen = {tuple(slot_choices_for_seed(s)) for s in range(10)}
    assert len(seen) >= 7, f"Expected >=7 distinct topologies in seeds 0..9, got {sorted(seen)}"


def test_all_eight_combinations_build_successfully() -> None:
    """Every cell of the 2x2x2 module grid must produce a buildable
    model with the core parts present."""
    for chassis in ("controller_chassis", "turntable_plinth"):
        for deck in ("dual_jog_decks", "single_platter_with_tonearm"):
            for controls in ("triple_fader_strip", "pad_grid_plus_fader"):
                cfg = DjEquipmentConfig(
                    chassis_module=chassis,  # type: ignore[arg-type]
                    deck_layout_module=deck,  # type: ignore[arg-type]
                    controls_module=controls,  # type: ignore[arg-type]
                )
                model = build_dj_equipment(cfg)
                part_names = {p.name for p in model.parts}
                tag = f"({chassis},{deck},{controls})"
                assert "housing" in part_names, f"{tag} missing housing"
                assert "carry_handle" in part_names, f"{tag} missing carry_handle"
                assert "left_platter" in part_names, f"{tag} missing left_platter"
                assert "right_platter" in part_names, f"{tag} missing right_platter"
                assert "crossfader" in part_names, f"{tag} missing crossfader"

                joint_topology = {
                    (a.parent, a.child, a.articulation_type.name) for a in model.articulations
                }
                # carry_handle joint is always REVOLUTE around +x on housing.
                assert ("housing", "carry_handle", "REVOLUTE") in joint_topology, (
                    f"{tag} missing housing->carry_handle REVOLUTE"
                )
                # crossfader joint is always PRISMATIC.
                assert ("housing", "crossfader", "PRISMATIC") in joint_topology, (
                    f"{tag} missing housing->crossfader PRISMATIC"
                )
                # Both platter joints are always REVOLUTE.
                assert ("housing", "left_platter", "REVOLUTE") in joint_topology, (
                    f"{tag} missing housing->left_platter REVOLUTE"
                )
                assert ("housing", "right_platter", "REVOLUTE") in joint_topology, (
                    f"{tag} missing housing->right_platter REVOLUTE"
                )

                # pad_grid_plus_fader specifically should emit at least one
                # pad part.
                if controls == "pad_grid_plus_fader":
                    pad_count = sum(1 for name in part_names if name.startswith("pad_r"))
                    assert pad_count >= 4, (
                        f"{tag} pad_grid_plus_fader emitted only {pad_count} pads"
                    )


def test_housing_has_mesh_visuals() -> None:
    """The controller_chassis housing must retain the anchor's 3 Mesh
    visuals (wall_ring / bottom_panel / top_deck) — primitive_complexity
    intent preserved at the module level."""
    from sdk import Mesh

    model = build_seeded_dj_equipment(0)
    housing = model.get_part("housing")
    mesh_count = sum(1 for v in housing.visuals if isinstance(v.geometry, Mesh))
    assert mesh_count >= 3, (
        f"Expected >=3 Mesh visuals on controller_chassis housing, got {mesh_count}"
    )


def test_resolve_config_rejects_invalid_chassis_module() -> None:
    with pytest.raises(ValueError, match="chassis_module"):
        resolve_config(DjEquipmentConfig(chassis_module="unknown"))  # type: ignore[arg-type]


def test_resolve_config_rejects_invalid_deck_layout_module() -> None:
    with pytest.raises(ValueError, match="deck_layout_module"):
        resolve_config(DjEquipmentConfig(deck_layout_module="unknown"))  # type: ignore[arg-type]


def test_resolve_config_rejects_invalid_controls_module() -> None:
    with pytest.raises(ValueError, match="controls_module"):
        resolve_config(DjEquipmentConfig(controls_module="unknown"))  # type: ignore[arg-type]


def test_resolve_config_clamps_oversized_body() -> None:
    cfg = DjEquipmentConfig(body_width=1.50)
    r = resolve_config(cfg)
    assert r.body_width <= 0.80
