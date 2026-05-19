from __future__ import annotations

import cadquery as cq
from sdk import (
    ArticulatedObject,
    ArticulationType,
    Box,
    Cylinder,
    Material,
    MotionLimits,
    Origin,
    TestContext,
    TestReport,
    mesh_from_cadquery,
    place_on_face_uv,
)


def build_object_model() -> ArticulatedObject:
    """
    A realistic articulated 2x3 chest of drawers.

    6 pull-out drawers arranged in 2 columns by 3 rows.
    Each drawer slides on concealed drawer slides.
    Natural wood finish with metal handles.
    Bedroom furniture scale.
    """
    model = ArticulatedObject(name="chest_of_drawers_2x3")

    # Materials
    wood_material = model.material("wood", rgba=(0.75, 0.60, 0.45, 1.0))
    dark_wood = model.material("dark_wood", rgba=(0.55, 0.42, 0.30, 1.0))
    metal_handle = model.material("metal", rgba=(0.72, 0.72, 0.75, 1.0))

    # Main cabinet dimensions
    cabinet_width = 0.80      # 80cm wide
    cabinet_depth = 0.45      # 45cm deep
    cabinet_height = 1.05     # 105cm tall
    wall_thickness = 0.025    # 2.5cm wall thickness
    leg_height = 0.08         # 8cm legs

    # Interior cabinet space (accounting for top/bottom panels and leg height)
    interior_height = cabinet_height - leg_height - 2 * wall_thickness
    interior_width = cabinet_width - 2 * wall_thickness
    interior_depth = cabinet_depth - wall_thickness  # Back panel only

    # Drawer dimensions (calculated to fit inside cabinet interior)
    # 2 columns with center divider: 3 wall_thickness gaps (left wall, center, right wall)
    drawer_width = (interior_width - wall_thickness) / 2 - 0.005  # Small clearance
    # 3 rows with 2 horizontal dividers: 3 gaps between top and bottom panels
    drawer_height = (interior_height - 2 * wall_thickness) / 3 - 0.005  # Small clearance
    drawer_depth = interior_depth - 0.02  # Slightly less than interior depth for slides

    # ==================== CABINET FRAME ====================
    cabinet = model.part("cabinet")

    # Top panel
    cabinet.visual(
        Box((cabinet_width, cabinet_depth, wall_thickness)),
        origin=Origin(xyz=(0.0, 0.0, cabinet_height - wall_thickness/2)),
        material=wood_material,
        name="top_panel",
    )

    # Bottom panel (sits on legs)
    cabinet.visual(
        Box((cabinet_width, cabinet_depth, wall_thickness)),
        origin=Origin(xyz=(0.0, 0.0, leg_height + wall_thickness/2)),
        material=wood_material,
        name="bottom_panel",
    )

    # Left side panel
    cabinet.visual(
        Box((wall_thickness, cabinet_depth, cabinet_height - leg_height)),
        origin=Origin(xyz=(-cabinet_width/2 + wall_thickness/2, 0.0, (cabinet_height + leg_height)/2)),
        material=wood_material,
        name="left_side",
    )

    # Right side panel
    cabinet.visual(
        Box((wall_thickness, cabinet_depth, cabinet_height - leg_height)),
        origin=Origin(xyz=(cabinet_width/2 - wall_thickness/2, 0.0, (cabinet_height + leg_height)/2)),
        material=wood_material,
        name="right_side",
    )

    # Back panel
    cabinet.visual(
        Box((cabinet_width - 2*wall_thickness, wall_thickness, cabinet_height - leg_height - 2*wall_thickness)),
        origin=Origin(xyz=(0.0, -cabinet_depth/2 + wall_thickness/2, (cabinet_height + leg_height)/2)),
        material=wood_material,
        name="back_panel",
    )

    # Center divider (vertical separator between drawer columns)
    cabinet.visual(
        Box((wall_thickness, cabinet_depth - wall_thickness, cabinet_height - leg_height - 2*wall_thickness)),
        origin=Origin(xyz=(0.0, wall_thickness/2, (cabinet_height + leg_height)/2)),
        material=wood_material,
        name="center_divider",
    )

    # Horizontal dividers (between drawer rows)
    # Position: starting from bottom panel, evenly spaced
    for i in range(2):  # 2 dividers for 3 rows
        # Calculate position: bottom + spacing for (i+1) drawers + (i+1) gaps
        spacing_per_row = interior_height / 3
        z_pos = leg_height + wall_thickness + (i + 1) * spacing_per_row
        cabinet.visual(
            Box((interior_width, interior_depth, wall_thickness)),
            origin=Origin(xyz=(0.0, wall_thickness/2, z_pos)),
            material=wood_material,
            name=f"horizontal_divider_{i}",
        )

    # Four legs
    leg_size = 0.04
    leg_positions = [
        (-cabinet_width/2 + leg_size, -cabinet_depth/2 + leg_size),
        (cabinet_width/2 - leg_size, -cabinet_depth/2 + leg_size),
        (-cabinet_width/2 + leg_size, cabinet_depth/2 - leg_size),
        (cabinet_width/2 - leg_size, cabinet_depth/2 - leg_size),
    ]
    for i, (lx, ly) in enumerate(leg_positions):
        cabinet.visual(
            Box((leg_size, leg_size, leg_height)),
            origin=Origin(xyz=(lx, ly, leg_height/2)),
            material=dark_wood,
            name=f"leg_{i}",
        )

    # ==================== DRAWERS ====================
    # Create 6 drawers: 2 columns (left/right) x 3 rows (top/middle/bottom)
    drawer_names = [
        ["drawer_left_top", "drawer_right_top"],
        ["drawer_left_middle", "drawer_right_middle"],
        ["drawer_left_bottom", "drawer_right_bottom"],
    ]

    # Calculate drawer positions
    spacing_per_row = interior_height / 3
    for row in range(3):
        for col in range(2):
            drawer_name = drawer_names[row][col]

            # X position: left column is negative, right column is positive
            # Position in center of each half (with center divider in middle)
            if col == 0:
                x_offset = -wall_thickness/2 - drawer_width/2 - 0.0025  # Slight offset for clearance
            else:
                x_offset = wall_thickness/2 + drawer_width/2 + 0.0025

            # Z position: center of each row space (evenly distributed)
            # Row 0 (bottom): leg_height + wall_thickness + spacing_per_row/2
            # Row 1 (middle): + 1 full spacing
            # Row 2 (top): + 2 full spacing
            z_offset = leg_height + wall_thickness + (row + 0.5) * spacing_per_row

            # Y position: slightly forward from back panel for drawer slides
            y_offset = -cabinet_depth/2 + wall_thickness + drawer_depth/2 + 0.015

            drawer = model.part(drawer_name)

            # Drawer front face (visible when closed)
            # Positioned to be flush or slightly proud of cabinet front
            front_thickness = 0.018
            cabinet_front_y = cabinet_depth/2  # Front of cabinet
            # The drawer part origin is at y_offset, so local y needs to reach cabinet front
            # y_offset + local_y = cabinet_front_y + proudness
            proudness = 0.012  # 12mm proud of cabinet front (front face thickness + small gap)
            front_face_local_y = cabinet_front_y - y_offset + proudness
            drawer.visual(
                Box((drawer_width, front_thickness, drawer_height)),
                origin=Origin(xyz=(0.0, front_face_local_y, 0.0)),
                material=wood_material,
                name="front_face",
            )

            # Drawer bottom panel
            bottom_thickness = 0.012
            drawer.visual(
                Box((drawer_width - 0.01, drawer_depth, bottom_thickness)),
                origin=Origin(xyz=(0.0, 0.0, -drawer_height/2 + bottom_thickness/2)),
                material=wood_material,
                name="bottom_panel",
            )

            # Drawer left side panel
            side_thickness = 0.012
            drawer.visual(
                Box((side_thickness, drawer_depth, drawer_height - bottom_thickness)),
                origin=Origin(xyz=(-drawer_width/2 + side_thickness/2 + 0.005, 0.0, bottom_thickness/2)),
                material=wood_material,
                name="left_side",
            )

            # Drawer right side panel
            drawer.visual(
                Box((side_thickness, drawer_depth, drawer_height - bottom_thickness)),
                origin=Origin(xyz=(drawer_width/2 - side_thickness/2 - 0.005, 0.0, bottom_thickness/2)),
                material=wood_material,
                name="right_side",
            )

            # Drawer back panel
            back_thickness = 0.012
            drawer.visual(
                Box((drawer_width - 2*side_thickness - 0.01, back_thickness, drawer_height - bottom_thickness)),
                origin=Origin(xyz=(0.0, -drawer_depth/2 + back_thickness/2, bottom_thickness/2)),
                material=wood_material,
                name="back_panel",
            )

            # Metal handle
            handle_width = 0.12
            handle_height = 0.025
            handle_depth = 0.015
            handle_stem_height = 0.012

            # Handle base plate - positioned on front face
            handle_base_y = front_face_local_y + front_thickness/2 + handle_depth/2
            drawer.visual(
                Box((handle_width, handle_depth, handle_height)),
                origin=Origin(xyz=(0.0, handle_base_y, 0.0)),
                material=metal_handle,
                name="handle_base",
            )

            # Handle grip (curved metal bar using CadQuery)
            handle_cq = (
                cq.Workplane("XY")
                .moveTo(-handle_width/2 + 0.015, 0)
                .lineTo(-handle_width/2 + 0.015, handle_stem_height)
                .lineTo(handle_width/2 - 0.015, handle_stem_height)
                .lineTo(handle_width/2 - 0.015, 0)
                .close()
                .extrude(0.008)
            )

            drawer.visual(
                mesh_from_cadquery(handle_cq, f"{drawer_name}_handle_grip"),
                origin=Origin(
                    xyz=(0.0, handle_base_y, handle_height/2 - handle_stem_height/2)
                ),
                material=metal_handle,
                name="handle_grip",
            )

            # Articulation: prismatic joint for drawer slide
            # Drawer slides out along +Y axis
            model.articulation(
                f"{drawer_name}_slide",
                ArticulationType.PRISMATIC,
                parent=cabinet,
                child=drawer,
                origin=Origin(xyz=(x_offset, y_offset, z_offset)),
                axis=(0.0, 1.0, 0.0),  # Slide forward along +Y
                motion_limits=MotionLimits(
                    effort=30.0,
                    velocity=0.3,
                    lower=0.0,  # Closed position
                    upper=drawer_depth * 0.75,  # Open position (75% of drawer depth)
                ),
            )

    return model


def run_tests() -> TestReport:
    ctx = TestContext(object_model)

    cabinet = object_model.get_part("cabinet")

    # Verify all 6 drawers exist
    drawer_names = [
        "drawer_left_top", "drawer_right_top",
        "drawer_left_middle", "drawer_right_middle",
        "drawer_left_bottom", "drawer_right_bottom",
    ]

    for drawer_name in drawer_names:
        drawer = object_model.get_part(drawer_name)
        slide_joint = object_model.get_articulation(f"{drawer_name}_slide")

        # Verify drawer is a child of cabinet
        ctx.expect_overlap(cabinet, drawer, axes="xy", min_overlap=0.01)

        # Verify drawer can slide out (positive motion extends along +Y)
        rest_pos = ctx.part_world_position(drawer)
        with ctx.pose({slide_joint: slide_joint.motion_limits.upper}):
            extended_pos = ctx.part_world_position(drawer)
            ctx.check(
                f"{drawer_name}_extends_forward",
                extended_pos is not None and rest_pos is not None and extended_pos[1] > rest_pos[1] + 0.05,
                details=f"rest={rest_pos}, extended={extended_pos}",
            )

        # Verify drawer retains insertion when fully extended
        with ctx.pose({slide_joint: slide_joint.motion_limits.upper}):
            ctx.expect_overlap(
                drawer, cabinet,
                axes="y",
                min_overlap=0.08,
                name=f"{drawer_name}_retains_insertion_when_open",
            )

        # Verify drawer is properly contained within cabinet at rest
        with ctx.pose({slide_joint: 0.0}):
            ctx.expect_within(
                drawer, cabinet,
                axes="xz",
                margin=0.02,
                name=f"{drawer_name}_contained_in_cabinet",
            )

        # Verify front face is proud of cabinet when closed
        with ctx.pose({slide_joint: 0.0}):
            ctx.expect_gap(
                drawer, cabinet,
                axis="y",
                min_gap=-0.005,  # Slight proudness allowed
                max_gap=0.025,   # Not too far out
                positive_elem="front_face",
                name=f"{drawer_name}_front_face_position",
            )

    # Verify cabinet has single root structure
    ctx.check(
        "cabinet_is_root",
        len(object_model.root_parts()) == 1 and object_model.root_parts()[0].name == "cabinet",
        details=f"roots={[p.name for p in object_model.root_parts()]}",
    )

    # Verify cabinet has reasonable overall dimensions
    cabinet_aabb = ctx.part_world_aabb(cabinet)
    if cabinet_aabb:
        min_pt, max_pt = cabinet_aabb
        width = max_pt[0] - min_pt[0]
        depth = max_pt[1] - min_pt[1]
        height = max_pt[2] - min_pt[2]

        ctx.check(
            "cabinet_dimensions_reasonable",
            0.6 < width < 1.0 and 0.3 < depth < 0.6 and 0.8 < height < 1.3,
            details=f"width={width:.3f}, depth={depth:.3f}, height={height:.3f}",
        )

    return ctx.report()


object_model = build_object_model()
