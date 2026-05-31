from __future__ import annotations

import pytest

from agent.templates.monitor_mount import (
    MonitorMountConfig,
    build_monitor_mount,
    build_seeded_monitor_mount,
    config_from_seed,
    resolve_config,
    slot_choices_for_seed,
)


def test_seed_config_is_reproducible() -> None:
    assert config_from_seed(11) == config_from_seed(11)
    assert config_from_seed(11) != config_from_seed(12)


@pytest.mark.parametrize("seed", [0, 1, 2, 5, 12])
def test_seeded_builds_succeed(seed: int) -> None:
    model = build_seeded_monitor_mount(seed)
    part_names = {p.name for p in model.parts}
    # Every build always has a pan_carriage (emitted by both base modules)
    # and a tilt_head (emitted by both head modules).
    assert "pan_carriage" in part_names, f"seed={seed} missing pan_carriage"
    assert "tilt_head" in part_names, f"seed={seed} missing tilt_head"

    # The chain joints are always present, regardless of module choice.
    joint_names = {a.name for a in model.articulations}
    assert "base_to_arm" in joint_names, f"seed={seed} missing base_to_arm"
    assert "arm_to_head" in joint_names, f"seed={seed} missing arm_to_head"


def test_seed_zero_is_anchor_combination() -> None:
    choices = slot_choices_for_seed(0)
    assert choices == [
        ("base", "wall_bracket"),
        ("arm", "dual_link_arm"),
        ("head", "pan_tilt_head"),
    ]


def test_seed_zero_part_tree_matches_anchor() -> None:
    """seed=0 reproduces the canonical 5-star sample's part tree:
    wall_bracket + pan_carriage + primary_arm + secondary_arm +
    head_knuckle + tilt_head."""
    model = build_seeded_monitor_mount(0)
    part_names = {p.name for p in model.parts}
    expected = {
        "wall_bracket",
        "pan_carriage",
        "primary_arm",
        "secondary_arm",
        "head_knuckle",
        "tilt_head",
    }
    assert expected.issubset(part_names), f"Missing parts: {expected - part_names}"


def test_joint_topology_matches_anchor_when_dual_link_arm() -> None:
    """seed=0 (anchor) reproduces the canonical 5-star sample's joint
    topology (5 joints: pan_pivot, base_to_arm, elbow_fold, arm_to_head,
    head_tilt). For other arm modules the chain length varies, so we
    only assert the exact topology when the seed picked the anchor
    arm_module."""
    model = build_seeded_monitor_mount(0)
    cfg = config_from_seed(0)
    assert cfg.arm_module == "dual_link_arm"
    topology = {(a.parent, a.child, a.articulation_type.name) for a in model.articulations}
    expected = {
        ("wall_bracket", "pan_carriage", "CONTINUOUS"),
        ("pan_carriage", "primary_arm", "REVOLUTE"),
        ("primary_arm", "secondary_arm", "REVOLUTE"),
        ("secondary_arm", "head_knuckle", "REVOLUTE"),
        ("head_knuckle", "tilt_head", "REVOLUTE"),
    }
    assert topology == expected


def test_topology_diversity_over_seeds() -> None:
    """Across seeds 0..31 we expect at least 16 distinct topology
    combinations (out of 2*8*2 = 32 possible). RNG can occasionally
    repeat at small sample sizes, so a wide sweep keeps the margin."""
    seen = {tuple(slot_choices_for_seed(s)) for s in range(32)}
    assert len(seen) >= 16, f"Expected >=16 distinct topologies in seeds 0..31, got {sorted(seen)}"


# Mapping from N-link arm module to (n_parts_in_arm, n_internal_joints).
# Used by the per-arm-module parametrized build test below to assert the
# expected mid_arm_i parts and elbow_fold_i joints are emitted.
_ARM_LINK_COUNTS = {
    "single_link_arm": (1, 0),
    "dual_link_arm": (2, 1),
    "triple_link_arm": (3, 2),
    "quad_link_arm": (4, 3),
    "quint_link_arm": (5, 4),
    "hex_link_arm": (6, 5),
    "hept_link_arm": (7, 6),
    "oct_link_arm": (8, 7),
}


def test_all_combinations_build_successfully() -> None:
    """Every cell of the 2x8x2 module grid must produce a buildable
    model with the expected mid_arm_i parts and elbow_fold_i joints."""
    for b in ("wall_bracket", "desk_clamp_post"):
        for a, (n_links, n_internal) in _ARM_LINK_COUNTS.items():
            for h in ("pan_tilt_head", "tilt_only_head"):
                cfg = MonitorMountConfig(
                    base_module=b,
                    arm_module=a,
                    head_module=h,
                )
                model = build_monitor_mount(cfg)
                part_names = {p.name for p in model.parts}
                joint_names = {j.name for j in model.articulations}
                assert "pan_carriage" in part_names, f"({b},{a},{h}) missing pan_carriage"
                assert "tilt_head" in part_names, f"({b},{a},{h}) missing tilt_head"
                if b == "wall_bracket":
                    assert "wall_bracket" in part_names, f"({b},{a},{h}) missing wall_bracket"
                else:
                    assert "desk_clamp" in part_names, f"({b},{a},{h}) missing desk_clamp"
                # primary_arm is always present.
                assert "primary_arm" in part_names, f"({b},{a},{h}) missing primary_arm"
                # secondary_arm is present for every arm except single_link.
                if a == "single_link_arm":
                    assert "secondary_arm" not in part_names, (
                        f"({b},{a},{h}) unexpected secondary_arm"
                    )
                else:
                    assert "secondary_arm" in part_names, f"({b},{a},{h}) missing secondary_arm"
                # Expected mid_arm_i parts: N-2 for N >= 2 (otherwise 0).
                mid_count = max(0, n_links - 2)
                for idx in range(1, mid_count + 1):
                    assert f"mid_arm_{idx}" in part_names, f"({b},{a},{h}) missing mid_arm_{idx}"
                # No spurious extra mid_arm_i parts beyond the expected count.
                assert f"mid_arm_{mid_count + 1}" not in part_names, (
                    f"({b},{a},{h}) unexpected mid_arm_{mid_count + 1}"
                )
                # Expected elbow_fold_i internal joints. dual_link_arm
                # uses 'elbow_fold' (no suffix); N>=3 use 'elbow_fold_i'.
                if a == "dual_link_arm":
                    assert "elbow_fold" in joint_names, f"({b},{a},{h}) missing elbow_fold"
                else:
                    for j in range(1, n_internal + 1):
                        assert f"elbow_fold_{j}" in joint_names, (
                            f"({b},{a},{h}) missing elbow_fold_{j}"
                        )
                    assert f"elbow_fold_{n_internal + 1}" not in joint_names, (
                        f"({b},{a},{h}) unexpected elbow_fold_{n_internal + 1}"
                    )
                if h == "pan_tilt_head":
                    assert "head_knuckle" in part_names, f"({b},{a},{h}) missing head_knuckle"


@pytest.mark.parametrize(
    "arm_module,expected_parts,expected_joints",
    [
        (
            "triple_link_arm",
            {"primary_arm", "mid_arm_1", "secondary_arm"},
            {"elbow_fold_1", "elbow_fold_2"},
        ),
        (
            "quad_link_arm",
            {"primary_arm", "mid_arm_1", "mid_arm_2", "secondary_arm"},
            {"elbow_fold_1", "elbow_fold_2", "elbow_fold_3"},
        ),
        (
            "quint_link_arm",
            {"primary_arm", "mid_arm_1", "mid_arm_2", "mid_arm_3", "secondary_arm"},
            {"elbow_fold_1", "elbow_fold_2", "elbow_fold_3", "elbow_fold_4"},
        ),
        (
            "hex_link_arm",
            {
                "primary_arm",
                "mid_arm_1",
                "mid_arm_2",
                "mid_arm_3",
                "mid_arm_4",
                "secondary_arm",
            },
            {
                "elbow_fold_1",
                "elbow_fold_2",
                "elbow_fold_3",
                "elbow_fold_4",
                "elbow_fold_5",
            },
        ),
        (
            "hept_link_arm",
            {
                "primary_arm",
                "mid_arm_1",
                "mid_arm_2",
                "mid_arm_3",
                "mid_arm_4",
                "mid_arm_5",
                "secondary_arm",
            },
            {
                "elbow_fold_1",
                "elbow_fold_2",
                "elbow_fold_3",
                "elbow_fold_4",
                "elbow_fold_5",
                "elbow_fold_6",
            },
        ),
        (
            "oct_link_arm",
            {
                "primary_arm",
                "mid_arm_1",
                "mid_arm_2",
                "mid_arm_3",
                "mid_arm_4",
                "mid_arm_5",
                "mid_arm_6",
                "secondary_arm",
            },
            {
                "elbow_fold_1",
                "elbow_fold_2",
                "elbow_fold_3",
                "elbow_fold_4",
                "elbow_fold_5",
                "elbow_fold_6",
                "elbow_fold_7",
            },
        ),
    ],
)
def test_n_link_arm_parts_and_joints(
    arm_module: str,
    expected_parts: set,
    expected_joints: set,
) -> None:
    """N-link arms (N=3..8) emit primary_arm + N-2 mid_arm_i parts +
    secondary_arm and N-1 internal elbow_fold_i joints."""
    cfg = MonitorMountConfig(arm_module=arm_module)  # type: ignore[arg-type]
    model = build_monitor_mount(cfg)
    part_names = {p.name for p in model.parts}
    assert expected_parts.issubset(part_names), (
        f"{arm_module} missing parts {expected_parts - part_names}"
    )
    joint_names = {a.name for a in model.articulations}
    assert expected_joints.issubset(joint_names), (
        f"{arm_module} missing joints {expected_joints - joint_names}"
    )


def test_resolve_config_rejects_invalid_base_module() -> None:
    with pytest.raises(ValueError, match="base_module"):
        resolve_config(MonitorMountConfig(base_module="unknown"))  # type: ignore[arg-type]


def test_resolve_config_rejects_invalid_arm_module() -> None:
    with pytest.raises(ValueError, match="arm_module"):
        resolve_config(MonitorMountConfig(arm_module="unknown"))  # type: ignore[arg-type]


def test_resolve_config_rejects_invalid_head_module() -> None:
    with pytest.raises(ValueError, match="head_module"):
        resolve_config(MonitorMountConfig(head_module="unknown"))  # type: ignore[arg-type]
