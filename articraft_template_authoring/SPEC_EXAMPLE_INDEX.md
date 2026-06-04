# Spec Example Index

本文件定义 `articraft_template_authoring` 中 spec 示例的读取边界，避免 agent 把旧格式 spec 当成新模板格式来源。

## Canonical Modular V1 Examples

`specs_modular_v1/` 是新 spec 的唯一示例来源。新增类别 spec 必须以 `SPEC_TEMPLATE.md` 为准，并且只能从本目录学习 schema、章节顺序、slot/module/interface 写法和 Stage 1 / Stage 2 seed-domain 表达。

当前文件：

- `articulated_task_lamp.md`
- `bell_tower_with_swinging_bell.md`
- `candy_vending_machine.md`
- `casino_machine.md`
- `globe.md`
- `lighthouse_with_rotating_beacon_assembly.md`
- `metronome.md`
- `overshot_waterwheel.md`
- `paper_cutter_guillotine.md`
- `parabolic_dish_on_azimuth_elevation_mount.md`
- `playground_swing.md`
- `single_rotor_helicopter.md`
- `singleleaf_drawbridge.md`
- `traditional_windmill.md`
- `turnstile_gates.md`
- `turntable.md`

## Transitional Modular References

`specs_modular_transitional/` 中的文件有 slot/module 思路和有价值的结构分析，但不保证完全符合当前 `SPEC_TEMPLATE.md` 的强制字段。可以参考结构识别、slot graph、validator 和 source adaptation 思路；禁止作为新 spec 的 schema 来源。

当前文件：

- `robotic_arms.md`
- `robotic_leg.md`
- `single_revolute_hinge.md`
- `threestage_telescoping_slide.md`
- `twojoint_prismatic_chain.md`
- `twojoint_revolute_chain.md`
- `usb_drive_with_swivel_cover.md`
- `wheelbarrow.md`
- `wheelie_bin_with_hinged_lid.md`
- `wind_turbine.md`
- `zippo_lighter.md`

## Legacy Reference Only

`specs_legacy_reference_only/` 中的文件是旧 parts/joints spec、baseline style reference，或含 `primary_anchor` 的旧路线材料。它们只能用于理解历史类别边界、validator 风格或迁移需求；禁止作为 modular spec schema、source contract、seed-domain contract 或新模板 authoring 路线来源。

当前文件：

- `barrier_gate.md`
- `bicycle_crankset_and_pedal_assembly.md`
- `blender.md`
- `box_fan_with_control_knob.md`
- `camcorder_with_flipout_screen.md`
- `camera_flash.md`
- `camera_lens.md`
- `cannon.md`
- `cantilever_articulated_arm.md`
- `car_sunroof_cassette.md`
- `cctv_mast_with_pantilt_camera_head.md`
- `ceiling_fan.md`
- `ceiling_light_fixture.md`
- `chest_freezer_with_hinged_lid.md`
- `coaxial_rotary_stack.md`
- `crane_tower.md`
- `desk_with_drawer.md`
- `desktop_monitor_with_tilt_swivel_stand.md`
- `desktop_pc_tower.md`
- `display_freezer_with_sliding_glass_lids.md`
- `dj_equipment.md`
- `drone.md`
- `ferris_wheel.md`
- `graphics_card_with_cooling_fans.md`
- `louvered_shutter_assembly.md`
- `monitor_mount.md`
- `platform_cart.md`
- `refrigerator_with_hinged_doors.md`
- `retractable_utility_knife.md`
- `revolving_door.md`
- `rolling_toolbox_with_telescoping_handle.md`
- `screwcap_bottle.md`
- `screwin_light_bulb_with_socket.md`
- `serial_elbow_arm.md`
- `simple_aframe_step_ladder.md`
- `sliding_window.md`
- `stand_mixer.md`
- `standing_desk_with_synchronous_telescoping_legs_and_articulated_controls.md`
- `tackle_box_with_simple_hinged_lid.md`
- `telescoping_boom.md`

## Blocked / Insufficient Sources

`specs_blocked_insufficient_sources/` 中的文件保留了已调查但未满足 5 星 source contract 的草案。它们不能作为 canonical modular v1 示例，也不能进入模板实现；只有在补齐足够 5 星样本并重写 source table 后，才可迁回 `specs_modular_v1/`。

当前文件：

- `satellite_with_articulated_solar_panels.md`
