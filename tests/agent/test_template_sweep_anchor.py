from __future__ import annotations

from agent.template_sweep_anchor import (
    GeometryFingerprint,
    JointFingerprint,
    PartFingerprint,
    _axis_to_principal,
    _bbox_ratio,
    _cosine_similarity,
    _geometry_type_label,
    _primitive_local_aabb,
    compare_fingerprints,
    normalize_indexed_name,
    parse_anchor_reference,
)

# --------------------------------------------------------------------------- #
# Name + axis normalisation
# --------------------------------------------------------------------------- #


def test_normalize_indexed_name_strips_trailing_index() -> None:
    assert normalize_indexed_name("blade_0") == "blade_i"
    assert normalize_indexed_name("blade_12") == "blade_i"
    assert normalize_indexed_name("housing") == "housing"
    assert normalize_indexed_name("") == ""
    assert normalize_indexed_name(None) == ""


def test_normalize_indexed_name_handles_nested_indices() -> None:
    assert normalize_indexed_name("fan_head_0_collar_0") == "fan_head_i_collar_i"


def test_axis_to_principal_picks_largest_component() -> None:
    assert _axis_to_principal((0.0, 0.0, 1.0)) == "z"
    assert _axis_to_principal((1.0, 0.0, 0.0)) == "x"
    assert _axis_to_principal((0.0, 1.0, 0.0)) == "y"
    assert _axis_to_principal((0.0, 0.0, -1.0)) == "z"  # sign-agnostic
    assert _axis_to_principal((0.7, 0.3, 0.0)) == "x"


def test_axis_to_principal_returns_none_for_zero_vector() -> None:
    assert _axis_to_principal((0.0, 0.0, 0.0)) == "none"
    assert _axis_to_principal(None) == "none"
    assert _axis_to_principal((1.0,)) == "none"  # malformed


# --------------------------------------------------------------------------- #
# Primitive label + local AABB
# --------------------------------------------------------------------------- #


def test_geometry_type_label_uses_class_name() -> None:
    from sdk import Box, Cylinder, Mesh, Sphere

    assert _geometry_type_label(Box((0.1, 0.1, 0.1))) == "Box"
    assert _geometry_type_label(Cylinder(radius=0.05, length=0.10)) == "Cylinder"
    assert _geometry_type_label(Sphere(radius=0.04)) == "Sphere"
    assert _geometry_type_label(Mesh(name="fake")) == "Mesh"


def test_primitive_local_aabb_for_box() -> None:
    from sdk import Box

    assert _primitive_local_aabb(Box((0.2, 0.4, 0.1)), None) == (0.2, 0.4, 0.1)


def test_primitive_local_aabb_for_cylinder_along_z() -> None:
    from sdk import Cylinder

    assert _primitive_local_aabb(Cylinder(radius=0.05, length=0.10), None) == (
        0.10,
        0.10,
        0.10,
    )


def test_primitive_local_aabb_returns_none_for_mesh() -> None:
    from sdk import Mesh

    assert _primitive_local_aabb(Mesh(name="x"), None) is None


def test_bbox_ratio_normalises_to_max() -> None:
    assert _bbox_ratio((1.0, 0.5, 0.25)) == (1.0, 0.5, 0.25)
    assert _bbox_ratio((4.0, 2.0, 1.0)) == (1.0, 0.5, 0.25)


def test_bbox_ratio_returns_none_for_zero_extent() -> None:
    assert _bbox_ratio((0.0, 0.0, 0.0)) is None


# --------------------------------------------------------------------------- #
# Cosine similarity
# --------------------------------------------------------------------------- #


def test_cosine_similarity_identical_histograms_equals_one() -> None:
    import math

    assert math.isclose(
        _cosine_similarity({"Cylinder": 3, "Box": 1}, {"Cylinder": 3, "Box": 1}),
        1.0,
        abs_tol=1e-9,
    )


def test_cosine_similarity_disjoint_histograms_equals_zero() -> None:
    assert _cosine_similarity({"Mesh": 2}, {"Box": 2}) == 0.0


def test_cosine_similarity_empty_inputs_equals_one() -> None:
    assert _cosine_similarity({}, {}) == 1.0


# --------------------------------------------------------------------------- #
# parse_anchor_reference
# --------------------------------------------------------------------------- #


def test_parse_anchor_reference_with_explicit_revision() -> None:
    assert parse_anchor_reference("rec_x:rev_002") == ("rec_x", "rev_002")


def test_parse_anchor_reference_defaults_to_rev_000001() -> None:
    assert parse_anchor_reference("rec_x") == ("rec_x", "rev_000001")


def test_parse_anchor_reference_strips_whitespace() -> None:
    assert parse_anchor_reference("  rec_x  :  rev_002  ") == ("rec_x", "rev_002")


def test_parse_anchor_reference_empty_raises() -> None:
    import pytest

    with pytest.raises(ValueError):
        parse_anchor_reference("")


# --------------------------------------------------------------------------- #
# compare_fingerprints — synthetic fingerprints exercising each subcheck
# --------------------------------------------------------------------------- #


def _make_fp(
    *,
    source: str = "test",
    parts: dict[str, PartFingerprint] | None = None,
    joints: list[JointFingerprint] | None = None,
    bbox_ratio: tuple[float, float, float] | None = (1.0, 1.0, 0.3),
) -> GeometryFingerprint:
    parts = parts or {}
    joints = joints or []
    return GeometryFingerprint(
        source=source,
        part_count=len(parts),
        parts=parts,
        joints=joints,
        bbox_ratio=bbox_ratio,
    )


def test_compare_passes_when_fingerprints_match() -> None:
    fp = _make_fp(
        parts={
            "housing": PartFingerprint("housing", 4, {"Cylinder": 2, "Mesh": 2}, (0.3, 0.3, 1.0)),
            "rotor": PartFingerprint(
                "rotor", 5, {"Cylinder": 3, "Mesh": 1, "Box": 1}, (0.4, 0.4, 0.1)
            ),
            "blade_i": PartFingerprint("blade_i", 2, {"Mesh": 1, "Cylinder": 1}, (0.1, 0.1, 0.02)),
        },
        joints=[
            JointFingerprint("housing", "rotor", "CONTINUOUS", "z"),
            JointFingerprint("rotor", "blade_i", "REVOLUTE", "z"),
        ],
    )
    report = compare_fingerprints(fp, fp)
    assert report.overall_status == "pass"
    for sc in report.subchecks:
        assert sc.status == "pass", sc.to_dict()


def test_compare_fails_when_template_has_extra_part() -> None:
    anchor = _make_fp(
        parts={
            "housing": PartFingerprint("housing", 4, {"Cylinder": 2, "Mesh": 2}),
        },
        joints=[JointFingerprint("housing", "rotor", "CONTINUOUS", "z")],
    )
    template = _make_fp(
        parts={
            "housing": PartFingerprint("housing", 4, {"Cylinder": 2, "Mesh": 2}),
            "knob_hole": PartFingerprint("knob_hole", 1, {"Cylinder": 1}),  # extra
        },
        joints=[JointFingerprint("housing", "rotor", "CONTINUOUS", "z")],
    )
    report = compare_fingerprints(anchor, template)
    assert report.overall_status == "fail"
    pns = next(sc for sc in report.subchecks if sc.name == "part_name_set")
    assert pns.status == "fail"
    extra = next(d for d in pns.deviations if d["kind"] == "extra_parts")
    assert extra["names"] == ["knob_hole"]


def test_compare_fails_when_template_drops_mesh_visuals() -> None:
    anchor = _make_fp(
        parts={"rotor": PartFingerprint("rotor", 5, {"Cylinder": 3, "Mesh": 2})},
        joints=[],
    )
    template = _make_fp(
        # template kept count but downgraded Mesh → Box
        parts={"rotor": PartFingerprint("rotor", 5, {"Cylinder": 3, "Box": 2})},
        joints=[],
    )
    report = compare_fingerprints(anchor, template)
    pcl = next(sc for sc in report.subchecks if sc.name == "primitive_complexity_lower_bound")
    assert pcl.status == "fail"
    dev = pcl.deviations[0]
    assert dev["part"] == "rotor"
    assert dev["anchor_mesh_count"] == 2
    assert dev["template_mesh_count"] == 0


def test_compare_fails_when_template_collapses_visuals() -> None:
    anchor = _make_fp(
        parts={"rotor": PartFingerprint("rotor", 5, {"Cylinder": 3, "Mesh": 2})},
        joints=[],
    )
    template = _make_fp(
        parts={"rotor": PartFingerprint("rotor", 1, {"Box": 1})},  # 5 → 1
        joints=[],
    )
    report = compare_fingerprints(anchor, template)
    vcp = next(sc for sc in report.subchecks if sc.name == "visual_count_per_part")
    assert vcp.status == "fail"
    dev = vcp.deviations[0]
    assert dev["part"] == "rotor"
    assert dev["anchor_count"] == 5
    assert dev["template_count"] == 1


def test_compare_fails_when_template_introduces_extra_joint_topology() -> None:
    anchor = _make_fp(
        parts={"housing": PartFingerprint("housing", 1, {"Cylinder": 1})},
        joints=[JointFingerprint("housing", "rotor", "CONTINUOUS", "z")],
    )
    template = _make_fp(
        parts={"housing": PartFingerprint("housing", 1, {"Cylinder": 1})},
        joints=[
            JointFingerprint("housing", "rotor", "CONTINUOUS", "z"),
            JointFingerprint("rotor", "knob_hole", "FIXED", "none"),  # extra
        ],
    )
    report = compare_fingerprints(anchor, template)
    jt = next(sc for sc in report.subchecks if sc.name == "joint_topology")
    assert jt.status == "fail"
    extra = next(d for d in jt.deviations if d["kind"] == "extra_joints")
    assert ["rotor", "knob_hole", "FIXED"] in extra["joints"]


def test_compare_fails_when_bbox_ratio_diverges_significantly() -> None:
    anchor = _make_fp(parts={}, joints=[], bbox_ratio=(1.0, 1.0, 0.2))  # flat fan
    template = _make_fp(parts={}, joints=[], bbox_ratio=(0.2, 0.2, 1.0))  # elongated stick
    report = compare_fingerprints(anchor, template)
    bb = next(sc for sc in report.subchecks if sc.name == "bbox_ratio")
    assert bb.status == "fail"


def test_compare_bbox_subcheck_skips_when_missing() -> None:
    anchor = _make_fp(parts={}, joints=[], bbox_ratio=None)
    template = _make_fp(parts={}, joints=[], bbox_ratio=(1.0, 0.5, 0.25))
    report = compare_fingerprints(anchor, template)
    bb = next(sc for sc in report.subchecks if sc.name == "bbox_ratio")
    assert bb.status == "pass"
    assert "skipped_reason" in bb.details


def test_compare_primitive_histogram_similarity_catches_primitive_swap() -> None:
    # Same total visual count, but completely different primitive distribution.
    anchor = _make_fp(parts={"x": PartFingerprint("x", 4, {"Cylinder": 4})}, joints=[])
    template = _make_fp(parts={"x": PartFingerprint("x", 4, {"Box": 4})}, joints=[])
    report = compare_fingerprints(anchor, template)
    ph = next(sc for sc in report.subchecks if sc.name == "primitive_histogram_similarity")
    assert ph.status == "fail"


# --------------------------------------------------------------------------- #
# spec parser
# --------------------------------------------------------------------------- #


def test_parse_spec_primary_anchor_reads_value(tmp_path) -> None:
    from agent.template_sweep_coverage import parse_spec_primary_anchor

    spec_dir = tmp_path / "articraft_template_authoring" / "specs"
    spec_dir.mkdir(parents=True)
    (spec_dir / "demo_slug.md").write_text(
        "## 元信息\n"
        "| 项 | 值 |\n|---|---|\n"
        "| slug | `demo_slug` |\n"
        "| primary_anchor | `rec_demo_xyz:rev_000002` |\n",
        encoding="utf-8",
    )
    result = parse_spec_primary_anchor("demo_slug", repo_root=tmp_path)
    assert result == "rec_demo_xyz:rev_000002"


def test_parse_spec_primary_anchor_returns_none_when_missing(tmp_path) -> None:
    from agent.template_sweep_coverage import parse_spec_primary_anchor

    spec_dir = tmp_path / "articraft_template_authoring" / "specs"
    spec_dir.mkdir(parents=True)
    (spec_dir / "demo.md").write_text("## 元信息\n| slug | demo |\n", encoding="utf-8")
    assert parse_spec_primary_anchor("demo", repo_root=tmp_path) is None


def test_parse_spec_primary_anchor_returns_none_for_placeholder(tmp_path) -> None:
    from agent.template_sweep_coverage import parse_spec_primary_anchor

    spec_dir = tmp_path / "articraft_template_authoring" / "specs"
    spec_dir.mkdir(parents=True)
    (spec_dir / "demo.md").write_text("## 元信息\n| primary_anchor | TBD |\n", encoding="utf-8")
    assert parse_spec_primary_anchor("demo", repo_root=tmp_path) is None
