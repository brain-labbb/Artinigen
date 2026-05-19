from __future__ import annotations

import math

from sdk import (
    ArticulatedObject,
    ArticulationType,
    Box,
    Cylinder,
    MotionLimits,
    Origin,
    Sphere,
    TestContext,
    TestReport,
)


def _arm_bar(part, name: str, *, length: float, y: float, z: float, material: object) -> None:
    part.visual(
        Box((length, 0.008, 0.010)),
        origin=Origin(xyz=(length / 2.0, y, z)),
        material=material,
        name=name,
    )


def _cross_tie(part, name: str, *, x: float, material: object) -> None:
    part.visual(
        Box((0.014, 0.052, 0.010)),
        origin=Origin(xyz=(x, 0.0, 0.0)),
        material=material,
        name=name,
    )


def _end_spring(part, name: str, *, x0: float, x1: float, y: float, material: object) -> None:
    """A slim visible tension spring that touches both cross ties."""
    part.visual(
        Box((x1 - x0, 0.004, 0.004)),
        origin=Origin(xyz=((x0 + x1) / 2.0, y, 0.004)),
        material=material,
        name=name,
    )


def build_object_model() -> ArticulatedObject:
    model = ArticulatedObject(name="architect_desk_lamp")

    base_mat = model.material("weighted_black_base", rgba=(0.08, 0.085, 0.09, 1.0))
    arm_mat = model.material("brushed_aluminum_arm", rgba=(0.72, 0.73, 0.72, 1.0))
    joint_mat = model.material("polished_joint_hardware", rgba=(0.86, 0.86, 0.84, 1.0))
    spring_mat = model.material("spring_steel", rgba=(0.45, 0.46, 0.47, 1.0))
    shade_mat = model.material("warm_white_enamel", rgba=(0.92, 0.89, 0.82, 1.0))
    bulb_mat = model.material("warm_bulb", rgba=(1.0, 0.88, 0.55, 0.85))

    base = model.part("base")
    base.visual(
        Cylinder(radius=0.115, length=0.025),
        origin=Origin(xyz=(0.0, 0.0, 0.0125)),
        material=base_mat,
        name="base_disk",
    )
    base.visual(
        Cylinder(radius=0.080, length=0.010),
        origin=Origin(xyz=(0.0, 0.0, 0.030)),
        material=base_mat,
        name="base_cap",
    )
    base.visual(
        Cylinder(radius=0.015, length=0.060),
        origin=Origin(xyz=(0.0, 0.0, 0.065)),
        material=joint_mat,
        name="shoulder_post",
    )
    for label, y in (("rear", -0.024), ("front", 0.024)):
        base.visual(
            Cylinder(radius=0.016, length=0.010),
            origin=Origin(xyz=(0.0, y, 0.095), rpy=(math.pi / 2.0, 0.0, 0.0)),
            material=joint_mat,
            name=f"shoulder_boss_{label}",
        )
        base.visual(
            Box((0.012, 0.018, 0.036)),
            origin=Origin(xyz=(0.0, y * 0.82, 0.077)),
            material=joint_mat,
            name=f"shoulder_web_{label}",
        )

    lower_arm = model.part("lower_arm")
    lower_len = 0.255
    lower_arm.visual(
        Cylinder(radius=0.014, length=0.050),
        origin=Origin(rpy=(math.pi / 2.0, 0.0, 0.0)),
        material=joint_mat,
        name="shoulder_hub",
    )
    for label, y in (("rear", -0.018), ("front", 0.018)):
        _arm_bar(lower_arm, f"lower_rail_{label}", length=lower_len, y=y, z=0.000, material=arm_mat)
    _cross_tie(lower_arm, "lower_near_tie", x=0.045, material=arm_mat)
    _cross_tie(lower_arm, "lower_far_tie", x=lower_len - 0.040, material=arm_mat)
    lower_arm.visual(
        Cylinder(radius=0.015, length=0.052),
        origin=Origin(xyz=(lower_len, 0.0, 0.0), rpy=(math.pi / 2.0, 0.0, 0.0)),
        material=joint_mat,
        name="elbow_hub",
    )
    for label, y in (("rear", -0.026), ("front", 0.026)):
        _end_spring(
            lower_arm,
            f"lower_spring_{label}",
            x0=0.045,
            x1=lower_len - 0.040,
            y=y,
            material=spring_mat,
        )

    upper_arm = model.part("upper_arm")
    upper_len = 0.225
    upper_arm.visual(
        Cylinder(radius=0.014, length=0.050),
        origin=Origin(rpy=(math.pi / 2.0, 0.0, 0.0)),
        material=joint_mat,
        name="elbow_socket",
    )
    for label, y in (("rear", -0.018), ("front", 0.018)):
        _arm_bar(upper_arm, f"upper_rail_{label}", length=upper_len, y=y, z=0.000, material=arm_mat)
    _cross_tie(upper_arm, "upper_near_tie", x=0.040, material=arm_mat)
    _cross_tie(upper_arm, "upper_far_tie", x=upper_len - 0.035, material=arm_mat)
    upper_arm.visual(
        Cylinder(radius=0.013, length=0.048),
        origin=Origin(xyz=(upper_len, 0.0, 0.0), rpy=(math.pi / 2.0, 0.0, 0.0)),
        material=joint_mat,
        name="head_yoke",
    )
    for label, y in (("rear", -0.026), ("front", 0.026)):
        _end_spring(
            upper_arm,
            f"upper_spring_{label}",
            x0=0.040,
            x1=upper_len - 0.035,
            y=y,
            material=spring_mat,
        )

    head = model.part("head")
    head.visual(
        Cylinder(radius=0.011, length=0.046),
        origin=Origin(rpy=(math.pi / 2.0, 0.0, 0.0)),
        material=joint_mat,
        name="tilt_pin",
    )
    head.visual(
        Box((0.036, 0.020, 0.018)),
        origin=Origin(xyz=(0.020, 0.0, -0.006)),
        material=joint_mat,
        name="neck_block",
    )
    head.visual(
        Cylinder(radius=0.032, length=0.035),
        origin=Origin(xyz=(0.055, 0.0, -0.020), rpy=(0.0, math.pi / 2.0, 0.0)),
        material=shade_mat,
        name="shade_throat",
    )
    head.visual(
        Cylinder(radius=0.056, length=0.028),
        origin=Origin(xyz=(0.087, 0.0, -0.033), rpy=(0.0, math.pi / 2.0, 0.0)),
        material=shade_mat,
        name="shade_rim",
    )
    head.visual(
        Sphere(radius=0.017),
        origin=Origin(xyz=(0.078, 0.0, -0.032)),
        material=bulb_mat,
        name="bulb",
    )

    # These rest offsets put the lamp in a natural architect-lamp pose at q=0.
    shoulder_rest = math.radians(-55.0)
    elbow_rest = math.radians(35.0)
    head_rest = math.radians(-45.0)

    model.articulation(
        "shoulder_pitch",
        ArticulationType.REVOLUTE,
        parent=base,
        child=lower_arm,
        origin=Origin(xyz=(0.0, 0.0, 0.095), rpy=(0.0, shoulder_rest, 0.0)),
        axis=(0.0, -1.0, 0.0),
        motion_limits=MotionLimits(effort=12.0, velocity=2.0, lower=-0.65, upper=0.75),
    )
    model.articulation(
        "elbow_pitch",
        ArticulationType.REVOLUTE,
        parent=lower_arm,
        child=upper_arm,
        origin=Origin(xyz=(lower_len, 0.0, 0.0), rpy=(0.0, elbow_rest, 0.0)),
        axis=(0.0, -1.0, 0.0),
        motion_limits=MotionLimits(effort=8.0, velocity=2.5, lower=-1.0, upper=1.0),
    )
    model.articulation(
        "head_tilt",
        ArticulationType.REVOLUTE,
        parent=upper_arm,
        child=head,
        origin=Origin(xyz=(upper_len, 0.0, 0.0), rpy=(0.0, head_rest, 0.0)),
        axis=(0.0, -1.0, 0.0),
        motion_limits=MotionLimits(effort=4.0, velocity=3.0, lower=-0.7, upper=0.9),
    )
    return model


def run_tests() -> TestReport:
    ctx = TestContext(object_model)

    base = object_model.get_part("base")
    lower_arm = object_model.get_part("lower_arm")
    upper_arm = object_model.get_part("upper_arm")
    head = object_model.get_part("head")
    shoulder = object_model.get_articulation("shoulder_pitch")
    elbow = object_model.get_articulation("elbow_pitch")
    tilt = object_model.get_articulation("head_tilt")

    ctx.allow_overlap(
        lower_arm,
        base,
        elem_a="shoulder_hub",
        elem_b="shoulder_boss_rear",
        reason="The shoulder pin is captured between the base bosses.",
    )
    ctx.allow_overlap(
        lower_arm,
        base,
        elem_a="shoulder_hub",
        elem_b="shoulder_boss_front",
        reason="The shoulder pin is captured between the base bosses.",
    )
    ctx.allow_overlap(
        lower_arm,
        base,
        elem_a="shoulder_hub",
        elem_b="shoulder_post",
        reason="The shoulder hub surrounds the top of the support post.",
    )
    ctx.allow_overlap(
        lower_arm,
        base,
        elem_a="shoulder_hub",
        elem_b="shoulder_web_rear",
        reason="The rear shoulder web is welded into the hub support.",
    )
    ctx.allow_overlap(
        lower_arm,
        base,
        elem_a="shoulder_hub",
        elem_b="shoulder_web_front",
        reason="The front shoulder web is welded into the hub support.",
    )
    ctx.allow_overlap(
        upper_arm,
        lower_arm,
        elem_a="elbow_socket",
        elem_b="elbow_hub",
        reason="The elbow hinge barrel and socket are intentionally nested.",
    )
    ctx.allow_overlap(
        upper_arm,
        lower_arm,
        elem_a="upper_rail_rear",
        elem_b="elbow_hub",
        reason="The rear upper rail is welded into the elbow hinge barrel.",
    )
    ctx.allow_overlap(
        upper_arm,
        lower_arm,
        elem_a="upper_rail_front",
        elem_b="elbow_hub",
        reason="The front upper rail is welded into the elbow hinge barrel.",
    )
    ctx.allow_overlap(
        upper_arm,
        lower_arm,
        elem_a="elbow_socket",
        elem_b="lower_rail_rear",
        reason="The elbow socket is seated against the lower rear rail at the hinge.",
    )
    ctx.allow_overlap(
        upper_arm,
        lower_arm,
        elem_a="elbow_socket",
        elem_b="lower_rail_front",
        reason="The elbow socket is seated against the lower front rail at the hinge.",
    )
    ctx.allow_overlap(
        head,
        upper_arm,
        elem_a="tilt_pin",
        elem_b="head_yoke",
        reason="The head tilt pin is captured by the yoke.",
    )
    ctx.allow_overlap(
        head,
        upper_arm,
        elem_a="neck_block",
        elem_b="head_yoke",
        reason="The neck block seats against the head yoke.",
    )
    ctx.allow_overlap(
        head,
        upper_arm,
        elem_a="tilt_pin",
        elem_b="upper_rail_rear",
        reason="The tilt pin passes close to the rear yoke rail.",
    )
    ctx.allow_overlap(
        head,
        upper_arm,
        elem_a="tilt_pin",
        elem_b="upper_rail_front",
        reason="The tilt pin passes close to the front yoke rail.",
    )

    roots = object_model.root_parts()
    ctx.check("base_is_single_root", len(roots) == 1 and roots[0].name == "base")
    ctx.expect_gap(
        head,
        base,
        axis="z",
        min_gap=0.050,
        positive_elem="shade_rim",
        negative_elem="base_disk",
        name="rest_pose_shade_clears_base",
    )
    ctx.expect_gap(
        lower_arm,
        base,
        axis="z",
        min_gap=0.010,
        positive_elem="lower_near_tie",
        negative_elem="base_cap",
        name="lower_arm_above_base_cap",
    )
    ctx.expect_overlap(
        head,
        head,
        axes="yz",
        min_overlap=0.020,
        elem_a="bulb",
        elem_b="shade_rim",
        name="bulb_sits_inside_shade_opening",
    )

    with ctx.pose({shoulder: shoulder.motion_limits.upper, elbow: 0.0, tilt: 0.0}):
        raised_head = ctx.part_world_position(head)
    with ctx.pose({shoulder: shoulder.motion_limits.lower, elbow: 0.0, tilt: 0.0}):
        lowered_head = ctx.part_world_position(head)
    ctx.check(
        "shoulder_changes_lamp_height",
        raised_head is not None
        and lowered_head is not None
        and raised_head[2] > lowered_head[2] + 0.12,
        details=f"raised={raised_head}, lowered={lowered_head}",
    )

    with ctx.pose({shoulder: 0.0, elbow: elbow.motion_limits.upper, tilt: 0.0}):
        open_pos = ctx.part_world_position(head)
    with ctx.pose({shoulder: 0.0, elbow: elbow.motion_limits.lower, tilt: 0.0}):
        folded_pos = ctx.part_world_position(head)
    ctx.check(
        "elbow_folds_arm_span",
        open_pos is not None
        and folded_pos is not None
        and abs(open_pos[0] - folded_pos[0]) > 0.10,
        details=f"open={open_pos}, folded={folded_pos}",
    )

    with ctx.pose({shoulder: 0.0, elbow: 0.0, tilt: tilt.motion_limits.upper}):
        ctx.expect_gap(
            head,
            upper_arm,
            axis="z",
            min_gap=-0.020,
            positive_elem="shade_rim",
            negative_elem="upper_far_tie",
            name="tilted_head_stays_near_yoke",
        )

    return ctx.report()


object_model = build_object_model()
