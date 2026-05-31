from __future__ import annotations

import pytest

from agent.templates.louvered_shutter_assembly import (
    SLAT_FAMILY_N_BOUNDS,
    LouveredShutterAssemblyConfig,
    build_louvered_shutter,
    build_seeded_louvered_shutter,
    config_from_seed,
    resolve_config,
    slot_choices_for_seed,
)
from sdk import ArticulationType

# --------------------------------------------------------------------------- #
# Seed reproducibility + anchor combo.
# --------------------------------------------------------------------------- #


def test_seed_config_is_reproducible() -> None:
    assert config_from_seed(11) == config_from_seed(11)
    assert config_from_seed(11) != config_from_seed(12)


def test_seed_zero_is_anchor_combination() -> None:
    """seed=0 must reproduce the spec's anchor combo:
    (simple_rectangular_frame, flat_planar_slats_N12, fixed_no_leaf_hinge, none).
    """
    choices = slot_choices_for_seed(0)
    assert choices == [
        ("frame", "simple_rectangular_frame"),
        ("slat", "flat_planar_slats_N12"),
        ("leaf_hinge", "fixed_no_leaf_hinge"),
        ("tilt_rod", "none"),
    ]


def test_seed_zero_part_tree_matches_anchor() -> None:
    """seed=0 reproduces rec_..._4492bf5f...'s minimal part tree:
    frame + 12 slats parented directly to frame, no leaf / no rod parts.
    """
    model = build_seeded_louvered_shutter(0)
    part_names = {p.name for p in model.parts}
    assert "frame" in part_names
    for i in range(12):
        assert f"slat_{i}" in part_names, f"missing slat_{i}"
    # No leaf / rod parts at seed=0.
    for forbidden in ("leaf", "leaf_0", "leaf_1", "outer_leaf", "inner_leaf"):
        assert forbidden not in part_names
    for p in part_names:
        assert "tilt_rod" not in p, f"unexpected tilt_rod part at seed=0: {p}"

    # Joints: 12 slat pivots + nothing else.
    joint_names = {a.name for a in model.articulations}
    for i in range(12):
        assert f"slat_{i}_pivot" in joint_names


# --------------------------------------------------------------------------- #
# All-combinations build test — every legal (A, B_family, C, D) tuple must
# build successfully. This loops the whole grid via resolve_config which
# applies the compatibility fold-back.
# --------------------------------------------------------------------------- #


def _legal_grid():
    """Enumerate every legal (frame, family, leaf, tilt) tuple after
    compatibility fold-back (so combos that collapse to the same
    effective tuple are deduplicated).
    """
    seen: set[tuple[str, str, str, str]] = set()
    for frame in (
        "simple_rectangular_frame",
        "window_jamb_with_inset_panel",
        "paneled_frame_with_mid_rail",
        "double_jamb_french_frame",
    ):
        for family in ("flat_planar", "airfoil", "wide_plantation", "narrow_blind"):
            for leaf in (
                "fixed_no_leaf_hinge",
                "single_leaf_side_hinge",
                "double_leaf_french_pair",
                "bifold_leaf_chain",
            ):
                for tilt in ("none", "prismatic_vertical_rod", "fixed_visual_rod"):
                    cfg = LouveredShutterAssemblyConfig(
                        frame_module=frame,  # type: ignore[arg-type]
                        slat_family=family,  # type: ignore[arg-type]
                        leaf_hinge_module=leaf,  # type: ignore[arg-type]
                        tilt_rod_module=tilt,  # type: ignore[arg-type]
                    )
                    r = resolve_config(cfg)
                    key = (
                        r.frame_module,
                        r.slat_family,
                        r.leaf_hinge_module,
                        r.tilt_rod_module,
                    )
                    if key in seen:
                        continue
                    seen.add(key)
                    yield cfg, key


def test_all_legal_combinations_build_successfully() -> None:
    """Every legal (A, B_family, C, D) cell of the module grid must
    produce a buildable model. We loop the whole grid and let
    resolve_config fold incompatible (A, C) pairs back."""

    for cfg, key in _legal_grid():
        model = build_louvered_shutter(cfg)
        part_names = {p.name for p in model.parts}
        joint_names = {a.name for a in model.articulations}
        tag = f"({key})"
        # Root frame variant present.
        root_candidates = {"frame", "outer_frame", "window_frame"}
        assert part_names & root_candidates, f"{tag} missing root frame: {part_names}"
        # At least one slat pivot.
        slat_pivots = [j for j in joint_names if "_pivot" in j and "slat" in j]
        assert slat_pivots, f"{tag} missing slat pivots"


# --------------------------------------------------------------------------- #
# Multiplicity coverage — over a handful of seeds we must see at least 2
# distinct N values (verifies the multiplicity dimension actually varies).
# --------------------------------------------------------------------------- #


def test_multiplicity_covers_multiple_N_values() -> None:
    n_values = set()
    for s in range(20):
        cfg = config_from_seed(s)
        r = resolve_config(cfg)
        n_values.add(r.slat_count)
    assert len(n_values) >= 2, f"only saw N values {sorted(n_values)}"


# --------------------------------------------------------------------------- #
# Topology diversity — seeds 0..19 must produce ≥5 distinct slot tuples
# (matches the module_topology_diversity gate threshold).
# --------------------------------------------------------------------------- #


def test_topology_diversity_over_seeds() -> None:
    seen = {tuple(slot_choices_for_seed(s)) for s in range(20)}
    assert len(seen) >= 5, f"expected ≥5 distinct topologies, saw {sorted(seen)}"


# --------------------------------------------------------------------------- #
# Per-slot invalid module rejection — resolve_config must raise ValueError.
# --------------------------------------------------------------------------- #


def test_resolve_config_rejects_invalid_frame_module() -> None:
    with pytest.raises(ValueError, match="frame_module"):
        resolve_config(
            LouveredShutterAssemblyConfig(frame_module="nope_bogus")  # type: ignore[arg-type]
        )


def test_resolve_config_rejects_invalid_slat_family() -> None:
    with pytest.raises(ValueError, match="slat_family"):
        resolve_config(
            LouveredShutterAssemblyConfig(slat_family="ultra_thin")  # type: ignore[arg-type]
        )


def test_resolve_config_rejects_invalid_leaf_hinge_module() -> None:
    with pytest.raises(ValueError, match="leaf_hinge_module"):
        resolve_config(
            LouveredShutterAssemblyConfig(leaf_hinge_module="bad_hinge")  # type: ignore[arg-type]
        )


def test_resolve_config_rejects_invalid_tilt_rod_module() -> None:
    with pytest.raises(ValueError, match="tilt_rod_module"):
        resolve_config(
            LouveredShutterAssemblyConfig(tilt_rod_module="electric")  # type: ignore[arg-type]
        )


def test_resolve_config_rejects_invalid_palette() -> None:
    with pytest.raises(ValueError, match="palette_theme"):
        resolve_config(
            LouveredShutterAssemblyConfig(palette_theme="neon_pink")  # type: ignore[arg-type]
        )


# --------------------------------------------------------------------------- #
# Compatibility matrix — incompatible (A, C) pairs fold back per the spec.
# --------------------------------------------------------------------------- #


def test_compatibility_simple_frame_blocks_bifold() -> None:
    r = resolve_config(
        LouveredShutterAssemblyConfig(
            frame_module="simple_rectangular_frame",
            leaf_hinge_module="bifold_leaf_chain",
        )
    )
    assert r.leaf_hinge_module == "fixed_no_leaf_hinge"


def test_compatibility_simple_frame_blocks_french() -> None:
    r = resolve_config(
        LouveredShutterAssemblyConfig(
            frame_module="simple_rectangular_frame",
            leaf_hinge_module="double_leaf_french_pair",
        )
    )
    assert r.leaf_hinge_module == "single_leaf_side_hinge"


def test_compatibility_french_frame_forces_french_pair() -> None:
    r = resolve_config(
        LouveredShutterAssemblyConfig(
            frame_module="double_jamb_french_frame",
            leaf_hinge_module="fixed_no_leaf_hinge",
        )
    )
    assert r.leaf_hinge_module == "double_leaf_french_pair"


# --------------------------------------------------------------------------- #
# Slat axis sanity — every slat REVOLUTE has axis ≈ (1, 0, 0).
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("seed", [0, 3, 5, 7, 11, 13])
def test_slat_axis_is_x(seed: int) -> None:
    model = build_seeded_louvered_shutter(seed)
    for j in model.articulations:
        if "slat" in j.name and "pivot" in j.name:
            assert j.articulation_type == ArticulationType.REVOLUTE
            ax = tuple(j.axis)
            assert ax == (1.0, 0.0, 0.0), f"seed={seed} {j.name} axis={ax}"


# --------------------------------------------------------------------------- #
# Slot D semantics — when tilt_rod=none there are no tilt_rod parts; when
# prismatic_vertical_rod, rod count == leaf_count (or 1 if fixed frame).
# --------------------------------------------------------------------------- #


def test_tilt_rod_none_emits_no_rod_parts() -> None:
    cfg = LouveredShutterAssemblyConfig(
        frame_module="simple_rectangular_frame",
        slat_family="flat_planar",
        leaf_hinge_module="fixed_no_leaf_hinge",
        tilt_rod_module="none",
    )
    model = build_louvered_shutter(cfg)
    part_names = {p.name for p in model.parts}
    for n in part_names:
        assert not n.startswith("tilt_rod"), f"unexpected tilt_rod part: {n}"
    joint_names = {a.name for a in model.articulations}
    for j in joint_names:
        assert "rod" not in j, f"unexpected rod joint: {j}"


def test_tilt_rod_prismatic_emits_one_rod_per_leaf() -> None:
    # fixed_no_leaf_hinge with prismatic rod: 1 rod.
    cfg_fixed = LouveredShutterAssemblyConfig(
        frame_module="simple_rectangular_frame",
        slat_family="flat_planar",
        leaf_hinge_module="fixed_no_leaf_hinge",
        tilt_rod_module="prismatic_vertical_rod",
    )
    model_fixed = build_louvered_shutter(cfg_fixed)
    fixed_rods = [p for p in model_fixed.parts if p.name.startswith("tilt_rod")]
    assert len(fixed_rods) == 1

    # double_leaf_french_pair with prismatic rod: 2 rods.
    cfg_french = LouveredShutterAssemblyConfig(
        frame_module="double_jamb_french_frame",
        slat_family="flat_planar",
        leaf_hinge_module="double_leaf_french_pair",
        tilt_rod_module="prismatic_vertical_rod",
    )
    model_french = build_louvered_shutter(cfg_french)
    french_rods = [p for p in model_french.parts if p.name.startswith("tilt_rod")]
    assert len(french_rods) == 2


def test_tilt_rod_prismatic_axis_is_vertical_z() -> None:
    cfg = LouveredShutterAssemblyConfig(
        frame_module="simple_rectangular_frame",
        slat_family="flat_planar",
        leaf_hinge_module="fixed_no_leaf_hinge",
        tilt_rod_module="prismatic_vertical_rod",
    )
    model = build_louvered_shutter(cfg)
    rod_joints = [
        j
        for j in model.articulations
        if j.articulation_type == ArticulationType.PRISMATIC and "rod" in j.name
    ]
    assert rod_joints
    for j in rod_joints:
        assert tuple(j.axis) == (0.0, 0.0, 1.0)


def test_fixed_visual_rod_has_no_rod_part_or_joint() -> None:
    cfg = LouveredShutterAssemblyConfig(
        frame_module="simple_rectangular_frame",
        slat_family="flat_planar",
        leaf_hinge_module="fixed_no_leaf_hinge",
        tilt_rod_module="fixed_visual_rod",
    )
    model = build_louvered_shutter(cfg)
    for p in model.parts:
        assert "tilt_rod" not in p.name, f"unexpected rod part: {p.name}"
    for j in model.articulations:
        assert "rod_slide" not in j.name and "to_tilt_rod" not in j.name


# --------------------------------------------------------------------------- #
# Slat-count consistency — total slat parts == slat_count × leaf_count
# (or × 1 for fixed_no_leaf_hinge).
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "frame,leaf,bay_count",
    [
        ("simple_rectangular_frame", "fixed_no_leaf_hinge", 1),
        ("simple_rectangular_frame", "single_leaf_side_hinge", 1),
        ("double_jamb_french_frame", "double_leaf_french_pair", 2),
        ("window_jamb_with_inset_panel", "bifold_leaf_chain", 2),
    ],
)
def test_slat_count_matches_bay_count(frame: str, leaf: str, bay_count: int) -> None:
    cfg = LouveredShutterAssemblyConfig(
        frame_module=frame,  # type: ignore[arg-type]
        slat_family="flat_planar",
        leaf_hinge_module=leaf,  # type: ignore[arg-type]
        tilt_rod_module="none",
    )
    model = build_louvered_shutter(cfg)
    r = resolve_config(cfg)
    slat_parts = [p for p in model.parts if p.name.startswith("slat_")]
    assert len(slat_parts) == r.slat_count * bay_count


# --------------------------------------------------------------------------- #
# Leaf-hinge axis sanity — when Slot C != fixed, the leaf-hinge joint
# axes are vertical (±z).
# --------------------------------------------------------------------------- #


def test_single_leaf_hinge_axis_is_vertical() -> None:
    cfg = LouveredShutterAssemblyConfig(
        frame_module="window_jamb_with_inset_panel",
        slat_family="flat_planar",
        leaf_hinge_module="single_leaf_side_hinge",
        tilt_rod_module="none",
    )
    model = build_louvered_shutter(cfg)
    hinge = model.get_articulation("frame_to_leaf")
    assert hinge.articulation_type == ArticulationType.REVOLUTE
    ax = tuple(hinge.axis)
    assert ax in {(0.0, 0.0, 1.0), (0.0, 0.0, -1.0)}, ax


def test_bifold_chain_has_outer_to_inner() -> None:
    cfg = LouveredShutterAssemblyConfig(
        frame_module="window_jamb_with_inset_panel",
        slat_family="flat_planar",
        leaf_hinge_module="bifold_leaf_chain",
        tilt_rod_module="none",
    )
    model = build_louvered_shutter(cfg)
    joint_names = {j.name for j in model.articulations}
    assert "jamb_to_outer" in joint_names
    assert "outer_to_inner" in joint_names


# --------------------------------------------------------------------------- #
# Slat range — every slat pivot's motion limit spans ≥ π/4 (so slats
# genuinely articulate, not a degenerate joint).
# --------------------------------------------------------------------------- #


def test_slat_pivots_have_meaningful_range() -> None:
    cfg = LouveredShutterAssemblyConfig(
        frame_module="simple_rectangular_frame",
        slat_family="flat_planar",
        leaf_hinge_module="fixed_no_leaf_hinge",
        tilt_rod_module="none",
    )
    model = build_louvered_shutter(cfg)
    import math as _math

    for j in model.articulations:
        if "slat" in j.name and "pivot" in j.name:
            lim = j.motion_limits
            assert lim is not None
            assert lim.lower is not None and lim.upper is not None
            assert lim.upper - lim.lower >= _math.pi / 4.0


# --------------------------------------------------------------------------- #
# Build runs successfully for a representative seed sweep.
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("seed", [0, 1, 2, 4, 7, 13])
def test_seeded_builds_succeed(seed: int) -> None:
    model = build_seeded_louvered_shutter(seed)
    # Has at least one slat and one slat pivot.
    slat_parts = [p for p in model.parts if p.name.startswith("slat_")]
    assert slat_parts, f"seed={seed} no slats"
    slat_pivots = [j for j in model.articulations if "slat" in j.name and "pivot" in j.name]
    assert slat_pivots, f"seed={seed} no slat pivots"


def test_slat_family_n_bounds_are_consistent() -> None:
    """Sanity — SLAT_FAMILY_N_BOUNDS values are positive and well-ordered."""
    for fam, (lo, hi) in SLAT_FAMILY_N_BOUNDS.items():
        assert 0 < lo <= hi, f"{fam}: bad N bounds {(lo, hi)}"
