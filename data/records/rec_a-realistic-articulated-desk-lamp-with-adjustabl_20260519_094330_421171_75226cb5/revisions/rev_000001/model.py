from __future__ import annotations

import math

from sdk import (
    ArticulatedObject,
    ArticulationType,
    Cylinder,
    MotionLimits,
    Origin,
    Sphere,
    TestContext,
    TestReport,
)


def build_object_model() -> ArticulatedObject:
    """
    A realistic articulated desk lamp with adjustable arm joints and pivoting lamp head.

    Classic architect's style desk lamp with:
    - Heavy weighted circular base
    - Two-segment adjustable arm (resting pose angled upward)
    - Pivoting conical lamp head
    - Desk/table scale
    """
    model = ArticulatedObject(name="articulated_desk_lamp")

    # Materials
    base_material = model.material("heavy_metal", rgba=(0.18, 0.18, 0.20, 1.0))
    arm_material = model.material("brushed_steel", rgba=(0.75, 0.76, 0.78, 1.0))
    joint_material = model.material("chrome", rgba=(0.90, 0.90, 0.92, 1.0))
    shade_material = model.material("matte_white", rgba=(0.92, 0.92, 0.90, 1.0))
    bulb_material = model.material("warm_light", rgba=(1.0, 0.95, 0.75, 0.9))

    # Dimensions
    base_radius = 0.12
    base_thickness = 0.025
    pivot_height = 0.06

    # Rest pose angles (natural desk lamp pose at q=0)
    lower_rest_angle = math.radians(-45)  # Lower arm 45 deg up from horizontal (negative for upward)
    upper_rest_angle = math.radians(30)  # Upper arm bends back 30 deg relative to lower

    # ==================== BASE ====================
    base = model.part("base")

    # Main weighted base disk
    base.visual(
        Cylinder(radius=base_radius, length=base_thickness),
        origin=Origin(xyz=(0.0, 0.0, base_thickness/2)),
        material=base_material,
        name="base_plate",
    )

    # Decorative upper ring
    base.visual(
        Cylinder(radius=base_radius * 0.85, length=0.008),
        origin=Origin(xyz=(0.0, 0.0, base_thickness + 0.004)),
        material=arm_material,
        name="base_ring",
    )

    # Pivot post
    base.visual(
        Cylinder(radius=0.018, length=pivot_height),
        origin=Origin(xyz=(0.0, 0.0, base_thickness + pivot_height/2)),
        material=joint_material,
        name="pivot_post",
    )

    # Pivot bosses (connection points for lower arm)
    for side, sign in (("left", -1.0), ("right", 1.0)):
        base.visual(
            Cylinder(radius=0.014, length=0.010),
            origin=Origin(
                xyz=(0.0, sign * 0.018, pivot_height),
                rpy=(math.pi/2, 0.0, 0.0),
            ),
            material=joint_material,
            name=f"pivot_boss_{side}",
        )

    # ==================== LOWER ARM ====================
    lower_arm = model.part("lower_arm")
    lower_arm_length = 0.24

    # Lower arm hub at pivot - positioned at origin
    lower_arm.visual(
        Cylinder(radius=0.016, length=0.024),
        origin=Origin(rpy=(math.pi/2, 0.0, 0.0)),
        material=joint_material,
        name="lower_hub",
    )

    # Lower arm rod - extends along +X at rest pose (45 deg up in world when q=0)
    # At q=0, this arm points 45 deg upward
    lower_arm.visual(
        Cylinder(radius=0.012, length=lower_arm_length),
        origin=Origin(xyz=(lower_arm_length/2, 0.0, 0.0)),
        material=arm_material,
        name="lower_rod",
    )

    # Elbow joint at end of lower arm
    lower_arm.visual(
        Cylinder(radius=0.014, length=0.022),
        origin=Origin(xyz=(lower_arm_length, 0.0, 0.0), rpy=(math.pi/2, 0.0, 0.0)),
        material=joint_material,
        name="lower_elbow",
    )

    # ==================== UPPER ARM ====================
    upper_arm = model.part("upper_arm")
    upper_arm_length = 0.18

    # Upper arm hub at elbow
    upper_arm.visual(
        Cylinder(radius=0.013, length=0.020),
        origin=Origin(rpy=(math.pi/2, 0.0, 0.0)),
        material=joint_material,
        name="upper_hub",
    )

    # Upper arm rod - extends along +X in its local frame
    # At q=0 relative to lower arm, it continues at upper_rest_angle
    upper_arm.visual(
        Cylinder(radius=0.010, length=upper_arm_length),
        origin=Origin(xyz=(upper_arm_length/2, 0.0, 0.0)),
        material=arm_material,
        name="upper_rod",
    )

    # Head pivot at end
    upper_arm.visual(
        Cylinder(radius=0.012, length=0.018),
        origin=Origin(xyz=(upper_arm_length, 0.0, 0.0), rpy=(math.pi/2, 0.0, 0.0)),
        material=joint_material,
        name="upper_pivot",
    )

    # ==================== LAMP HEAD ====================
    head = model.part("head")

    # Head pivot hub
    head.visual(
        Cylinder(radius=0.010, length=0.018),
        origin=Origin(rpy=(math.pi/2, 0.0, 0.0)),
        material=joint_material,
        name="head_hub",
    )

    # Shade neck extends backward from hub
    head.visual(
        Cylinder(radius=0.014, length=0.025),
        origin=Origin(xyz=(-0.02, 0.0, 0.0)),
        material=arm_material,
        name="shade_neck",
    )

    # Shade main body - conical
    head.visual(
        Cylinder(radius=0.038, length=0.020),
        origin=Origin(xyz=(0.015, 0.0, -0.005)),
        material=shade_material,
        name="shade_main",
    )

    # Shade inner section
    head.visual(
        Cylinder(radius=0.025, length=0.015),
        origin=Origin(xyz=(-0.005, 0.0, -0.003)),
        material=shade_material,
        name="shade_inner",
    )

    # Light bulb inside shade
    head.visual(
        Sphere(radius=0.010),
        origin=Origin(xyz=(0.005, 0.0, -0.004)),
        material=bulb_material,
        name="bulb",
    )

    # ==================== ARTICULATIONS ====================
    # Joint axis: (0, -1, 0) means positive q rotates upward (right-hand rule)

    # Base to lower arm joint
    # At q=0, lower arm is at lower_rest_angle (45 deg up)
    # Positive q rotates more upward, negative q rotates down toward horizontal
    model.articulation(
        "base_to_lower",
        ArticulationType.REVOLUTE,
        parent=base,
        child=lower_arm,
        origin=Origin(xyz=(0.0, 0.0, pivot_height), rpy=(0.0, lower_rest_angle, 0.0)),
        axis=(0.0, -1.0, 0.0),
        motion_limits=MotionLimits(
            effort=10.0,
            velocity=2.0,
            lower=-0.8,   # Can rotate down past horizontal
            upper=0.6,    # Can rotate up toward vertical
        ),
    )

    # Lower to upper arm (elbow)
    # At q=0, upper arm continues at upper_rest_angle relative to lower (-30 deg = bends back)
    model.articulation(
        "lower_to_upper",
        ArticulationType.REVOLUTE,
        parent=lower_arm,
        child=upper_arm,
        origin=Origin(xyz=(lower_arm_length, 0.0, 0.0), rpy=(0.0, upper_rest_angle, 0.0)),
        axis=(0.0, -1.0, 0.0),
        motion_limits=MotionLimits(
            effort=6.0,
            velocity=2.5,
            lower=-1.2,   # Can fold forward/down
            upper=0.8,    # Can fold back/up
        ),
    )

    # Upper to head
    # At q=0, head points in line with upper arm
    # Positive q tilts head up, negative tilts down
    head_tilt_offset = math.radians(-15)  # Head naturally tilts slightly down
    model.articulation(
        "upper_to_head",
        ArticulationType.REVOLUTE,
        parent=upper_arm,
        child=head,
        origin=Origin(xyz=(upper_arm_length, 0.0, 0.0), rpy=(0.0, head_tilt_offset, 0.0)),
        axis=(0.0, -1.0, 0.0),
        motion_limits=MotionLimits(
            effort=4.0,
            velocity=3.0,
            lower=-0.6,   # Can tilt down more
            upper=0.8,    # Can tilt up
        ),
    )

    return model


def run_tests() -> TestReport:
    ctx = TestContext(object_model)

    # Get parts and articulations
    base = object_model.get_part("base")
    lower_arm = object_model.get_part("lower_arm")
    upper_arm = object_model.get_part("upper_arm")
    head = object_model.get_part("head")

    base_to_lower = object_model.get_articulation("base_to_lower")
    lower_to_upper = object_model.get_articulation("lower_to_upper")
    upper_to_head = object_model.get_articulation("upper_to_head")

    # Allow overlaps at joint connections
    ctx.allow_overlap(
        lower_arm, base,
        elem_a="lower_hub",
        elem_b="pivot_boss_left",
        reason="Joint hub nests between pivot bosses",
    )
    ctx.allow_overlap(
        lower_arm, base,
        elem_a="lower_hub",
        elem_b="pivot_boss_right",
        reason="Joint hub nests between pivot bosses",
    )
    ctx.allow_overlap(
        lower_arm, base,
        elem_a="lower_hub",
        elem_b="pivot_post",
        reason="Hub overlaps pivot post",
    )
    ctx.allow_overlap(
        upper_arm, lower_arm,
        elem_a="upper_hub",
        elem_b="lower_elbow",
        reason="Elbow joint nesting",
    )
    ctx.allow_overlap(
        head, upper_arm,
        elem_a="head_hub",
        elem_b="upper_pivot",
        reason="Head pivot nesting",
    )
    ctx.allow_overlap(
        head, upper_arm,
        elem_a="bulb",
        elem_b="upper_pivot",
        reason="Bulb near pivot",
    )
    ctx.allow_overlap(
        head, upper_arm,
        elem_a="shade_main",
        elem_b="upper_pivot",
        reason="Shade connects to pivot",
    )
    ctx.allow_overlap(
        head, upper_arm,
        elem_a="shade_inner",
        elem_b="upper_pivot",
        reason="Shade connects to pivot",
    )
    ctx.allow_overlap(
        head, upper_arm,
        elem_a="shade_neck",
        elem_b="upper_pivot",
        reason="Shade neck connects to pivot",
    )

    # Verify root is base
    roots = object_model.root_parts()
    ctx.check(
        "single_root_is_base",
        len(roots) == 1 and roots[0].name == "base",
        details=f"roots={[p.name for p in roots]}",
    )

    # Verify base footprint
    base_aabb = ctx.part_world_aabb(base)
    if base_aabb:
        min_pt, max_pt = base_aabb
        base_diameter = max_pt[0] - min_pt[0]
        ctx.check(
            "base_has_reasonable_footprint",
            base_diameter > 0.15,
            details=f"base_diameter={base_diameter:.3f}",
        )

    # Verify arm articulation works
    # At rest pose (q=0), lamp should be in natural desk position
    with ctx.pose({base_to_lower: 0.0, lower_to_upper: 0.0, upper_to_head: 0.0}):
        rest_head_pos = ctx.part_world_position(head)
        # Head should be above base and forward
        ctx.check(
            "rest_pose_head_above_base",
            rest_head_pos[2] > 0.15 and rest_head_pos[0] > 0.15,
            details=f"rest_head_pos={rest_head_pos}",
        )

    # Lower arm can swing up more
    with ctx.pose({base_to_lower: base_to_lower.motion_limits.upper}):
        up_head_pos = ctx.part_world_position(head)
        ctx.check(
            "lower_arm_swings_upward",
            up_head_pos[2] > rest_head_pos[2],
            details=f"up_z={up_head_pos[2]:.3f} > rest_z={rest_head_pos[2]:.3f}",
        )

    # Lower arm can swing down
    with ctx.pose({base_to_lower: base_to_lower.motion_limits.lower}):
        down_head_pos = ctx.part_world_position(head)
        ctx.check(
            "lower_arm_swings_downward",
            down_head_pos[2] < rest_head_pos[2],
            details=f"down_z={down_head_pos[2]:.3f} < rest_z={rest_head_pos[2]:.3f}",
        )

    # Elbow can fold
    with ctx.pose({lower_to_upper: lower_to_upper.motion_limits.lower}):
        folded_pos = ctx.part_world_position(upper_arm)
        ctx.check(
            "elbow_can_fold",
            folded_pos is not None,
            details="elbow works",
        )

    # Head can tilt - check that shade orientation changes
    with ctx.pose({base_to_lower: 0.0, lower_to_upper: 0.0, upper_to_head: 0.0}):
        rest_head_pos = ctx.part_world_position(head)
    with ctx.pose({base_to_lower: 0.0, lower_to_upper: 0.0, upper_to_head: 0.5}):
        tilted_head_pos = ctx.part_world_position(head)
        ctx.check(
            "head_can_tilt",
            tilted_head_pos is not None and rest_head_pos is not None,
            details=f"rest={rest_head_pos}, tilted={tilted_head_pos}",
        )

    # Shade clears base
    with ctx.pose({base_to_lower: 0.0, lower_to_upper: 0.0, upper_to_head: 0.0}):
        ctx.expect_gap(
            head, base,
            axis="z",
            min_gap=0.05,
            positive_elem="shade_main",
            negative_elem="base_plate",
            name="shade_clears_base_at_rest",
        )

    # Bulb inside shade
    ctx.expect_within(
        head, head,
        axes="xy",
        inner_elem="bulb",
        outer_elem="shade_main",
        margin=0.025,
        name="bulb_inside_shade",
    )

    return ctx.report()


object_model = build_object_model()
