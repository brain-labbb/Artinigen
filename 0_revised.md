# Articraft 10 类模板 Spec

## 0. 通用模板要求

| 项 | 要求 |
|---|---|
| seed | 给定 seed 后生成结果可复现 |
| part naming | 零件命名稳定，不随随机采样混乱 |
| joint metadata | 每个活动件必须有 joint type / axis / origin / range |
| diversity | 不能只靠颜色变化，必须有结构级随机 |
| validation | 每类必须自带 validator |
| reject | 漂浮零件、关节轴错误、严重穿模、类别身份丢失，一律拒绝 |
| module 表语义 | 表中列的可复用 module 是“几何/articulation pattern 提示”，不要求 part 名一定叫这个；只要满足结构与关节约束即可 |
| 参数语义 | RANDOM PARAMETERS 是设计空间提示，必须有 ≥3 种不同取值组合在 ≥20 个样本中实际可视化体现，不允许全部硬编码同一形态 |
| multi-parent 处理 | 当一个零件在物理上同时被多个父件支撑（如桌面 vs 双腿），允许选择单一父链 + Mimic 同步关节；不再强制单一 `*_lift_assembly` 抽象 |
| 离散桶 + 连续范围 | 形如 `small / medium / large`、`low / medium / tall`、`compact / normal / landmark` 的离散桶参数必须实现为「class（`Literal[...]`） + 桶内连续值（`rng.uniform`，每 class 一组范围）」两个字段同时存在，参考 `ferris_wheel.py` 的 `scale_mode` + `rim_radius`。class 挂耦合约束（如 step_count 范围、shelf_count 下限），桶内连续值打破"同 class 复刻"。**适用清单**：Sliding Window `frame_aspect_ratio`；Standing Desk `desktop_size`；Rolling Toolbox `box_size` 与 `wheel_size`；Revolving Door `door_radius` 与 `door_height`；Stand Mixer `bowl_slide_range`；Telescoping Boom `length_ratio`（每段 0.6–0.9 区间）；Step Ladder `ladder_height_class`（已示范）。 |
| 几何自洽 | 单一物体的 envelope（整机 W×H×D / 桌面 L×W / 推车甲板 L×W / 套筒段长度 / 梯子立柱高度 等）是 spine，在 `resolve_config` 决定后，所有子件尺寸（门 / 抽屉 / 隔板 / 轮位 / 各级套筒 / 踏板间距 等）必须从 spine 与 layout 派生，不允许在 `_build_*` 里独立 `rng`。样式 / 材质 / 颜色 / 装饰开关等"非尺寸"参数可独立采样，`_build_*` 适配所有组合；遇到 part / joint 数量级的真实物理耦合（如 `door_count` 受 `door_layout` 决定）才在 `resolve_config` 里派生。 |
| 非可动子件挂载 | 非可动装饰 / 嵌入件（`locking_collar` / `gasket_strip` / `anti_slip_pad` / curbstone / decoration / 加强筋 / 装饰帽 等）用 `parent.visual(...)` 直接挂为父 part 的 visual 子件，不创建独立 part 也不创建 FIXED articulation。例外：外部脚本需要单独着色 / hide / 索引该子件时才独立为 part。参考 `ferris_wheel.py` 里 `front_curbstone` / `rail_post_i` 的写法。 |

---

## 1. Sliding Window｜滑动窗

### 核心身份
带外框、轨道、玻璃窗扇，其中至少一个窗扇沿轨道做直线滑动。

### 固定结构
```
window_frame（窗户外框）
 ├── top_rail（上轨道）
 ├── bottom_rail（下轨道）
 ├── side_jambs（左右边框）
 ├── fixed_sash（固定窗扇，可选）
 ├── sliding_sash_0（滑动窗扇）
 │    ├── sash_frame
 │    ├── glass_panel
 │    ├── handle
 │    └── guide_shoe / slider_pad（滑动滑块/导靴，紧贴 rail，可选）
 └── stops / locks / seals
      └── travel_stop / keeper_block / latch_mount（明确的限位与锁挡块）
```

### 必须关节
| joint | 类型 | 含义 |
|---|---|---|
| sliding_sash_i_joint | prismatic | 窗扇沿轨道滑动 |

### 可复用模块（建议）
prismatic_slide / frame_panel / glass_panel / handle_grip / stopper / guide_shoe

### 随机参数
| 参数 | 取值建议 |
|---|---|
| window_orientation | horizontal / vertical |
| sash_count | 2 / 3 / 4 |
| sliding_sash_count | 1 / 2（auto-clamp：`sliding_sash_count = min(sliding_sash_count, sash_count)`，保证不超过 sash_count）|
| frame_aspect_ratio | wide / square / tall |
| rail_style | single / double / recessed |
| handle_style | tab / bar / recessed |
| grid_muntin_count | 0 / 2 / 4 / 6；muntin > 0 时必须有实体几何 |
| glass_opacity | clear (alpha ≥ 0.30) / frosted (alpha 0.20–0.30) / tinted (色相偏移) |
| lock_style | none / small latch / central lock |
| material_style | aluminum / PVC / wood / black metal |

### 约束
- sliding_sash 必须在 window_frame 内部。
- prismatic axis 必须与轨道方向平行。
- 滑动距离不能超过轨道长度。
- handle 必须附着在滑动窗扇上。
- glass_panel 必须嵌在 sash_frame 内。
- 固定窗扇和滑动窗扇不能完全重合。
- guide_shoe（若存在）必须始终被 rail 通道捕获，滑出末端时不能脱离。

### Validator
| 检查项 | 标准 |
|---|---|
| joint count | 至少 1 个 prismatic joint |
| axis check | joint axis 与 rail 方向一致 |
| containment | sash 和 glass 都在 frame 内 |
| range check | 滑动范围不超过轨道 |
| no floating | handle / lock / seal 不漂浮 |
| identity | 必须仍然像滑动窗 |
| sash_count coverage（**数据集级**，不写进 `run_<name>_tests`） | sash_count ∈ {3, 4} 与 sliding_sash_count = 2 至少各出现 ≥3 次 |
| muntin geometry | grid_muntin_count > 0 时，muntin part 数与参数一致 |

### Reject cases
- 没有可滑动窗扇。
- 滑动方向和轨道不一致。
- 玻璃或把手漂浮。
- 变成普通固定窗。
- grid_muntin_count > 0 但样本中没有 muntin 几何。

---

## 2. Tackle Box With Simple Hinged Lid｜带简单铰链盖的钓具箱 / 工具箱

### 核心身份
一个箱体，带后侧铰链盖，通常带前侧锁扣、提手，可有内部托盘和分隔格。

### 固定结构

**必需**
```
box_body
 ├── lid
 │    └── lid_handle（可选）
 └── rear_hinge
```

**可选**
```
 ├── front_latches（建议 60% 以上样本包含）
 ├── carry_handle（建议 50% 以上样本包含）
 ├── inner_tray
 └── feet / corner_guards / ribs
```

### 必须关节
| joint | 类型 | 含义 |
|---|---|---|
| lid_joint | revolute | 盖子绕后侧铰链打开 |
| latch_joint_i | revolute / fixed（可缺省，若 latch_count = 0） | 锁扣翻转 |
| handle_joint | revolute / fixed（可缺省） | 提手翻转 |

### 可复用模块
revolute_hinge / latch_lock / handle_grip / box_shell / tray_insert

### 随机参数
| 参数 | 取值建议 |
|---|---|
| box_aspect_ratio | long / compact / deep |
| lid_style | flat / raised / ribbed / recessed |
| latch_count | 0 / 1 / 2 / 3 |
| latch_style | flip tab / clamp / hook |
| handle_style | top bar / folding / molded / none |
| tray_count | 0 / 1 / 2 |
| compartment_count | 2–12 |
| corner_guard | none / small / reinforced |
| feet_count | 0 / 4 |
| material_style | plastic / metal / rugged polymer |

### 约束
- lid_joint 必须在箱体后侧。
- 若存在 latch，必须在前侧或前侧附近。
- inner_tray 必须在箱体内部。
- 若存在 carry_handle，必须连接在盖子或箱体上方。
- 盖子打开范围建议 60–120°（0.0–2.1 rad）。
- 锁扣（若存在）不能漂浮在箱体前方。

### Validator
| 检查项 | 标准 |
|---|---|
| lid joint | 必须有 revolute lid joint |
| hinge position | hinge 在后侧边缘 |
| latch position | 若 latch_count > 0，必须在前侧 |
| lid sweep | 盖子打开不严重穿过 body |
| tray containment | tray 在 box 内 |
| no floating | 已有零件全部连接 |
| identity | 必须像钓具箱 / 工具箱 |

### Reject cases
- 没有可动盖子。
- 铰链在箱体中间。
- 锁扣漂浮（若有）。
- 内部托盘在箱外。
- 变成普通 storage bin。

---

## 3. Telescoping Boom｜伸缩臂

### 核心身份
多级嵌套伸缩臂，每一级沿同一轴线线性伸缩。

### 固定结构
```
base_bracket（底座支架）
 └── outer_stage
      └── middle_stage（可选）
           └── inner_stage
                └── end_effector（可选）
```

### 必须关节
| joint | 类型 | 含义 |
|---|---|---|
| stage_i_joint 或 parent_to_child 命名 | prismatic | 第 i 级伸缩段沿主轴滑动 |

关节命名允许两种风格：`stage_i_to_stage_i+1` 或 `outer_to_middle / middle_to_inner_*`。校验只检查 axis 共线性和数量，不强制命名。

### 可复用模块
telescoping_tube / prismatic_slide / locking_collar / base_bracket / end_effector

### 随机参数
| 参数 | 取值建议 |
|---|---|
| stage_count | 2 / 3 / 4 |
| tube_cross_section | rectangular（`Box`） / round（`Cylinder`） / hex（6 个 ±30° 旋转的 `Box` 拼接，或自定义 mesh） |
| boom_orientation | horizontal / angled / vertical |
| length_ratio | 逐级递减 |
| overlap_ratio | 0.15–0.4 |
| base_style | plate / wall bracket / pedestal / clamp |
| end_effector | none / hook / light / camera / plate / clamp；若非 none，必须用 FIXED articulation 接在最内层末端 |
| collar_count | stage_count − 1 |
| decoration | warning stripe / bolts / fake cylinder；装饰仅是 visual mesh，不创建独立 part 或 joint |
| material_style | metal / black polymer / safety yellow |

### 约束
- 内层套筒尺寸必须小于外层。
- 所有 prismatic joint 的 axis 必须共线。
- 每一级伸出后仍要保留 overlap（min_overlap ≥ 0.6 × stage_length 推荐值）。
- end_effector 必须连接在最内层末端。
- locking_collar 位于两级套筒交界处。
- base_bracket 必须支撑 outer_stage。
- base part 命名建议包含 `base` / `support` / `bracket`，便于自动化校验。

### Validator
| 检查项 | 标准 |
|---|---|
| joint count | stage_count − 1 |
| joint type | 全部为 prismatic |
| axis collinearity | 所有伸缩轴共线 |
| nesting | 内层 bbox 小于外层 bbox |
| overlap | 每级有最小嵌套长度 |
| endpoint | end_effector 在最内层末端（若有） |
| no floating | collars / bolts / bracket 全连接 |

### Reject cases
- 多级管不嵌套。
- 各级伸缩方向不一致。
- prismatic axis 错误。
- 末端工具漂浮。
- 看起来像普通杆子，没有伸缩结构。

---

## 4. Standing Desk With Synchronous Telescoping Legs And Articulated Controls｜同步伸缩腿升降桌

### 核心身份
办公升降桌，带桌面、双腿或多腿同步伸缩柱、横梁、控制面板和独立按钮。

### 推荐树结构（两种模式皆允许）

**模式 A（单 lift 抽象）**
```
base_frame
 ├── outer_legs / feet
 └── upper_lift_assembly
      ├── desktop
      ├── inner_stages
      ├── crossbar
      └── control_panel → button_i
```

**模式 B（多腿 Mimic）**
```
base_frame
 ├── leg_0_outer / leg_1_outer (...)
 ├── leg_0_inner_stage（prismatic）
 ├── leg_1_inner_stage（prismatic, Mimic to leg_0）
 ├── desktop（fixed 到主腿，由 Mimic 保证同步）
 ├── crossbar（可融合在 desktop 的 apron / beam 中）
 └── control_panel（fixed 到 desktop 或主腿） → button_i
```

多腿 Mimic 必须使用 `Mimic` 关节，multiplier = 1.0，offset = 0，保证 max(Δz) − min(Δz) < 1 mm。

### 必须关节
| joint | 类型 | 含义 |
|---|---|---|
| desk_lift_joint 或 leg_i_lift_joint（带 Mimic） | prismatic | 桌面/腿组件上下滑动 |
| button_joint_i | prismatic / revolute | 控制按钮按压或拨动 |

若 `stage_count = N`（每条腿嵌套 N 段），每条腿需要 `N − 1` 个 prismatic 关节（outer→middle、middle→inner、…），同腿后续 prismatic 全部 Mimic 到该腿第一段；多腿情况下，每条腿第一段再 Mimic 到主腿第一段。

### 可复用模块
telescoping_tube / prismatic_slide / button_slider / crossbar_frame / base_foot

### 随机参数
| 参数 | 取值建议 |
|---|---|
| leg_count | 2 / 3 |
| stage_count per leg | 2 / 3 |
| desktop_shape | rectangle / rounded / L-shape |
| desktop_size | small / medium / large |
| leg_cross_section | rectangular / round / oval |
| crossbar_style | front / rear / double / integrated_into_desktop_apron |
| foot_style | T-foot / rectangular / wide |
| control_panel_position | left / right / center / front_underside |
| button_count | 2 / 4 / 6 |
| material_style | wood+metal / black / white |

### 约束
- 升降 axis 必须竖直 `(0, 0, 1)`。
- 左右内升降段必须与对应外桌腿轴线对齐。
- 桌面必须保持水平。
- 内层升降段必须嵌套在外层桌腿中。
- 桌脚必须接近地面。
- 控制面板必须在桌面下方或桌面前侧下沿。
- 按钮必须附着在控制面板上。
- 若使用模式 B，每条腿的 lift 关节必须有 Mimic 链接到主腿，且 axes 平行。

### Validator
| 检查项 | 标准 |
|---|---|
| lift joint | ≥ 1 个 prismatic lift joint |
| axis check | 升降轴竖直 |
| desktop level | 桌面水平 |
| leg alignment | 左右内外腿对齐 |
| nesting | inner stage 在 outer leg 内 |
| button attachment | buttons 在 control panel 上 |
| stability | feet 宽度足够支撑桌面 |
| sync check | 多腿场景 max(Δz) − min(Δz) < 1 mm |
| identity | 必须像升降桌 |

### Reject cases
- 没有升降关节。
- 桌面倾斜严重。
- 桌腿不嵌套。
- 控制按钮漂浮。
- 看起来像普通桌子。

---

## 5. Platform Cart｜平台推车

### 核心身份
平板运输车，带平台 deck、底部轮子，可选折叠推手、万向轮、栏杆和防滑垫。

### 固定结构
```
deck
 ├── 4 wheels (front_left/right, rear_left/right)
 ├── folding_handle（可选）
 ├── caster_forks（可选）
 ├── anti_slip_pad（推荐必有，2–6 mm 厚 rubber/mat）
 └── bumpers / rails（可选）
```

### 必须关节
| joint | 类型 | 含义 |
|---|---|---|
| wheel_i_joint | continuous | 轮子绕轮轴旋转 |
| caster_i_joint | continuous / revolute | 万向轮绕竖直轴转向 |
| handle_joint | revolute | 推手折叠 |
| steering_joint | revolute（绕 Z，可选） | 用于 wagon 风格的前桥/转向桥 |

### 可复用模块
continuous_wheel / caster_wheel / revolute_hinge / handle_grip / deck_panel

### 随机参数
| 参数 | 取值建议 |
|---|---|
| deck_shape | rectangle / rounded / ribbed |
| wheel_count | 4 / 6 |
| wheel_type | all_caster / mixed_steering（前转向桥 + 后定轮） / all_fixed |
| handle_style | U-handle / twin bar / single bar / none |
| handle_fold_angle | 0 至 π/2 rad |
| side_rail | none / low（0.03–0.08 m） / full（> 0.2 m） |
| bumper_style | none / corner / full |
| anti_slip_pattern | none / stripes / dots / grid |
| deck_aspect_ratio | compact / long / wide |
| material_style | steel / plastic / aluminum |

### 约束
- 所有轮子必须在平台下方。
- 轮子左右分布要基本对称。
- 轮子旋转轴必须与轮面方向一致。
- 万向轮转向轴必须接近竖直。
- 折叠推手的铰链应在平台后侧附近：`y ∈ [0.2 L, 0.5 L]`。
- 推手折叠时不能严重穿过平台。
- 轮子必须接近地面（z gap ≤ 0.055 m）。

### Validator
| 检查项 | 标准 |
|---|---|
| wheel count | ≥ 4 |
| wheel joint | continuous |
| caster axis | 竖直转向 |
| ground contact | wheels 接近地面 |
| handle axis | handle hinge 轴水平 |
| no floating | wheel fork / handle / bumper 不漂浮 |
| identity | 必须像平台推车 |

### Reject cases
- 没有平台。
- 轮子漂浮。
- 轮轴方向错误。
- 推手位置错误。
- 变成滑板或桌子。

---

## 6. Rolling Toolbox With Telescoping Handle｜带伸缩拉杆的轮式工具箱

### 核心身份
可移动工具箱，带箱体、箱盖、锁扣、后轮、前支撑、伸缩拉杆。

### 固定结构
```
toolbox_body
 ├── lid
 ├── front_latches
 ├── rear_wheels
 ├── front_feet / front_casters
 ├── telescoping_handle（双轨/双杆结构）
 │    ├── handle_outer_sleeve_l / r（固定在箱体上的两根导套）
 │    └── handle_inner（U 型把手，整体作为一个 prismatic 部件滑入滑出）
 ├── carry_handle
 ├── drawer（可选，前抽屉，prismatic）
 └── side_ribs / corner_guards
```

### 必须关节
| joint | 类型 | 含义 |
|---|---|---|
| wheel_joint_i | continuous | 后轮旋转 |
| handle_stage_joint | prismatic | 拉杆伸缩 |
| handle_stage_2_joint | prismatic（可选，stage_count ≥ 2 时使用） | 二级嵌套伸缩段 |
| lid_joint | revolute / fixed | 箱盖开合 |
| latch_joint_i | revolute | 锁扣翻转 |
| drawer_joint | prismatic（可选） | 前抽屉抽出 |

### 可复用模块
telescoping_tube / continuous_wheel / revolute_hinge / latch_lock / handle_grip / box_shell

### 随机参数
| 参数 | 取值建议 |
|---|---|
| box_size | compact / standard / jobsite large |
| wheel_size | small / medium / rugged large |
| wheel_tread | smooth / ribbed / chunky |
| handle_stage_count | 1 / 2 / 3 |
| handle_shape | U-shape / twin rod / suitcase-style |
| latch_count | 1 / 2 / 3 |
| lid_style | flat / raised / split |
| front_support | feet / small casters |
| corner_guard | none / reinforced |
| material_style | yellow-black / red-black / gray |

### 约束
- 后轮必须靠近箱体后下方。
- 拉杆必须从后侧或顶部后方伸出。
- 拉杆伸缩 axis 应接近竖直或后倾 ≤ 15°。
- 内外拉杆/导套必须保持嵌套，伸出末端导杆不脱离导套。
- 轮子必须接近地面。
- 锁扣必须在箱体前侧。
- 箱盖必须在箱体上方。

### Validator
| 检查项 | 标准 |
|---|---|
| wheel joint | 后轮为 continuous |
| handle joint | 拉杆为 prismatic |
| nesting | 拉杆杆体始终在导套内 |
| wheel contact | wheels 接近地面 |
| latch position | latch 在前侧 |
| lid position | lid 在上方 |
| no floating | handle / wheel / latch 全连接 |

### Reject cases
- 没有轮子。
- 拉杆不是伸缩结构。
- 后轮位置错误。
- 拉杆漂浮。
- 看起来不像工具箱。

---

## 7. Refrigerator With Hinged Doors｜带铰链门冰箱

### 核心身份
冰箱主体，带一扇或多扇铰链门、门把手、内部隔板、抽屉、门封条。

### 固定结构
```
fridge_body
 ├── doors（upper / lower / left / right / freezer）
 │    ├── handle
 │    ├── gasket_strip（required visual：沿门四边的薄条，厚度 8–12 mm）
 │    ├── door_shelf（可选）
 │    └── service_flap / hatch_panel（可选，subdoor，最多 1 个/门）
 ├── interior_shelves（必须有可见几何，不允许仅有空腔阴影）
 ├── drawers（可选）
 └── control_panel / dispenser（可选）
```

### 必须关节
| joint | 类型 | 含义 |
|---|---|---|
| door_i_joint | revolute | 门绕侧边打开 |
| drawer_i_joint | prismatic（可选） | 抽屉前后滑动 |
| subdoor_joint | revolute（可选） | 门面子门/服务窗 |
| dispenser_flap_joint | revolute（可选，`dispenser ∈ {water, ice}` 时建议有） | 取水/制冰口翻盖 |
| ice_bin_joint | prismatic（可选） | 门内制冰抽屉 |

### 可复用模块
revolute_hinge / drawer_box / shelf_rack / handle_grip / gasket_strip

### 随机参数
| 参数 | 取值建议 |
|---|---|
| door_layout | single / top_freezer / bottom_freezer / side_by_side / t_type_1up_2down / three_door_stacked / french_3door / french_4door / four_door_stacked |
| door_count | 由 `door_layout` 派生：single→1，top_freezer / bottom_freezer / side_by_side→2，t_type_1up_2down / three_door_stacked / french_3door→3，french_4door / four_door_stacked→4 |
| freezer_ratio | 0.25–0.5（仅在 layout 含冷冻区时生效；`single` 时被 build 代码忽略） |
| handle_style | vertical / horizontal / recessed |
| shelf_count | 2–6（独立采样；`_build_*` 按冰箱内高 / 隔板厚度自适应均匀分布，放不下时由 build 代码自然截断） |
| drawer_count | 0–3 |
| door_shelf_count | 0–4 |
| dispenser | none / water / ice |
| gasket_style | thin / thick / dark |
| material_style | white / stainless / black / retro |

### 约束
- 每扇门的 hinge axis 必须竖直 `(0, 0, ±1)`。
- 门的旋转轴必须在门边缘。
- 门打开范围建议 60–120°。
- shelves 必须在冰箱主体内部，且必须是显式 part。
- drawers 必须在主体内部并沿前后方向滑动。
- handles 必须附着在门上。
- gasket 必须跟随 door 移动（作为 door 的子件）。
- subdoor 必须 fixed 在主门 face 上，旋转 Z 轴，extent < 0.3 m。

### Validator
| 检查项 | 标准 |
|---|---|
| door joint | 每扇门有 revolute joint |
| hinge position | hinge 在门侧边 |
| shelf geometry | shelves 必须有可见 box/mesh part |
| shelf count by layout | top-bottom ≥ 3，French/side-by-side ≥ 4 |
| drawer axis | drawer 沿前后方向 prismatic |
| open sweep | 门打开不严重穿主体 |
| handle attachment | handle 附着在 door |
| gasket presence | door 必须有 gasket_strip 几何 |
| identity | 必须像 refrigerator |

### Reject cases
- 门不能打开。
- 门铰链在中间。
- 隔板或抽屉漂浮，或隔板只有空腔阴影没有实体几何。
- 冰箱变成普通柜子。
- 门布局和 hinge 方向不一致。

---

## 8. Revolving Door｜旋转门

### 核心身份
中心柱带 2、3 或 4 个径向门翼，在圆筒形或半圆形外壳中绕竖直轴连续旋转。单台旋转门 = 一个中心柱 + 一组门翼；多台 airlock 复合属于多个独立 instance，不属于本类别。

### 固定结构
```
outer_drum（可选）
 ├── top_cap
 ├── bottom_ring
 └── side_glass_panels

central_post
 ├── wing_0
 ├── wing_1
 ├── wing_2
 └── wing_3（可选）
```

### 必须关节
| joint | 类型 | 含义 |
|---|---|---|
| central_rotation_joint（命名风格 `*_spin` / `*_rotation`） | continuous | 中心门翼组件绕竖直轴旋转 |
| bypass_sliding_joint | prismatic（可选，仅 2-wing bypass 配置时；parent = `outer_drum` / 静态外壳（**非** `central_post`），axis 沿门洞宽度方向） | 2-翼旁通门的辅助滑动 |

### 可复用模块
rotary_post / radial_array / glass_panel / handle_grip / cylindrical_frame

### 随机参数
| 参数 | 取值建议 |
|---|---|
| wing_count |  3 / 4 / 5 /6|
| drum_type | full cylinder / partial / open frame |
| door_radius | small / medium / large |
| door_height | low / standard / tall |
| wing_material | glass / metal frame / wood panel |
| push_bar_style | straight / curved / none |
| top_cap_style | flat / thick / decorative |
| bottom_ring | none / low / full |
| sensor_module | none / small blocks |
| material_style | glass / dark metal / aluminum |

### 约束
- 门翼必须等角度分布。
- 中心旋转轴必须竖直 `(0, 0, 1)`。
- 门翼外缘不能超出外壳半径太多。
- 门翼必须连接到中心柱。
- 一个 record 内必须只有一组 wings；多台 airlock 必须拆分为多个 record。
- central_post + wings 作为整体旋转。
- 不能让每个 wing 独立乱转。

### Validator
| 检查项 | 标准 |
|---|---|
| joint count | 至少 1 个 continuous |
| axis check | 旋转轴竖直 |
| radial distribution | wings 等角度（容差 < 1°） |
| radius check | wings 在 drum 内 |
| connectivity | wings 连接 central post |
| no floating | push bars / caps / panels 连接 |
| single unit | 每个 record 只允许一组 central_post + wings |
| identity | 必须像 revolving door |

### Reject cases
- 变成普通门。
- 门翼数量不对称。
- 中心轴不竖直。
- 门翼穿出外壳太多。
- 每个门翼独立乱转。
- 一个 record 中出现两组以上独立旋转的 rotor。

---

## 9. Simple Aframe Step Ladder｜简单 A 字折叠梯

### 核心身份
A 字形折叠梯，前侧为爬梯框，后侧为支撑框，通过顶部铰链开合，带踏板和脚垫。

### 固定结构
```
front_frame
 ├── front_left_rail / front_right_rail
 └── step_0 / step_1 / ... / step_i

rear_support_frame
 ├── rear_left_rail / rear_right_rail
 └── rear_crossbars

top_cap
 └── hinge_joint

spreaders（可选）
feet
```

### 必须关节
| joint | 类型 | 含义 |
|---|---|---|
| frame_fold_joint | revolute | 后支撑框相对前爬梯框折叠 |
| spreader_joint_i | revolute / fixed | 防张开连杆（可选） |

### 可复用模块
revolute_hinge / folding_link_chain / step_rung / rubber_foot / crossbar_frame

### 随机参数
| 参数 | 取值建议 |
|---|---|
| ladder_height_class | low / medium / tall（按 0. 通用约定的「离散桶 + 连续范围」实现，每 class 一组实际 `top_rail_z` 范围。该字段是 spine，`step_count` 派生自此） |
| step_count | 派生自 `ladder_height_class`：low → {2, 3}；medium → {3, 4, 5}；tall → {5, 6, 7} |
| frame_angle | 15–35° |
| step_style | flat / narrow rung / anti-slip；anti-slip 必须通过 grip 材质/凸起几何呈现 |
| rail_cross_section | rectangular / round |
| rear_support_style | simple / cross-braced |
| top_cap_style | narrow cap / tool tray / flat |
| spreader_type | none / side bar / folding link |
| foot_style | rubber pads / wide pads |
| material_style | aluminum / fiberglass / steel |

### 约束
- 踏板必须连接左右前立柱。
- 后支撑框必须通过顶部铰链接到前爬梯框。
- 前后脚都应接近地面。
- 展开后必须形成 A 字形。
- 折叠关节轴必须沿梯子宽度方向（世界坐标系下 Y 轴），不允许沿前后方向（X 轴）。
- 防张开连杆不能漂浮；若不存在，参数中必须显式声明 `spreader_type = none`。

### Validator
| 检查项 | 标准 |
|---|---|
| step count | 与参数一致 |
| hinge position | hinge 在顶部 |
| fold axis | 必须为宽度方向（Y 轴） |
| foot contact | 四个脚接近地面 |
| A shape | 前后框形成夹角 |
| step attachment | steps 连接左右 rail |
| collision | 折叠/打开时不严重穿模 |
| spreader consistency | spreader_type 与 spreader part 计数一致（0、2 或 4） |
| anti-slip evidence | step_style = anti-slip 时必须有 grip 几何或材质 |

### Reject cases
- 后支撑框没有铰链。
- 梯子不是 A 字形。
- 踏板漂浮。
- 脚不接地。
- fold joint axis 错为前后方向（X 轴）。

---

## 10. Stand Mixer｜厨师机 / 台式搅拌机

### 核心身份
台式厨师机，带底座、立柱、可抬起机头、搅拌碗、搅拌头、速度旋钮或控制件。

### 固定结构
```
mixer_base
 ├── bowl_carriage（可选）
 │    └── mixing_bowl
 ├── rear_column
 ├── mixer_head
 │    ├── motor_housing
 │    ├── attachment_socket
 │    └── tool_attachment
 │         └── dough_hook / whisk / flat_beater
 ├── speed_selector
 └── head_lock_control（可选）
```

### 必须关节
| joint | 类型 | 含义 |
|---|---|---|
| head_tilt_joint | revolute | 机头绕后侧铰链抬起 |
| tool_spin_joint | continuous | 搅拌工具绕竖直轴旋转 |
| bowl_lift_or_slide_joint | prismatic | 碗运动（前后滑动 X/Y 轴 或 升降 Z 轴，可选；fixed bowl 仅在 prompt 明确说明时允许） |
| speed_selector_joint | revolute / continuous（可选，无控件时省略） | 速度旋钮 |
| head_lock_joint | prismatic / revolute（可选） | 机头锁定按钮或拨杆 |

### 可复用模块
revolute_hinge / continuous_rotor / prismatic_slide / button_slider / rotary_knob / bowl_module / rounded_body_shell

### 随机参数
| 参数 | 取值建议 |
|---|---|
| head_shape | rounded / boxy / retro / industrial |
| base_shape | oval / rectangle / rounded |
| bowl_shape | deep bowl / wide bowl / tapered |
| tool_type | dough_hook / whisk / flat_beater |
| head_tilt_range | 25–60° |
| bowl_lift_type | none（fixed） / slide_horizontal（X 或 Y 前后滑动） / lever_lift（Z 轴升降） |
| bowl_slide_range | short / medium |
| speed_selector_style | knob / lever / dial / none |
| speed_selector_mount | base_fixed / head_mounted |
| control_count | 1 / 2 / 3 |
| material_style | pastel / stainless / black / retro |
| detail_level | minimal / normal / detailed |

### 约束
- mixer_head 必须连接到 rear_column。
- head_tilt_joint 必须位于机头后侧或立柱顶部，默认 axis = (0, -1, 0)，部分样本使用 (1, 0, 0) 作为侧倾铰链亦可接受。
- tool_attachment 必须位于机头下方，并对准搅拌碗中心附近。
- tool_spin_joint 的 axis 应近似竖直 `(0, 0, 1)`。
- mixing_bowl 必须位于机头下方，不可漂浮。
- bowl 运动 axis 可为前后（X/Y）或竖直（Z，升降臂式）。
- speed_selector 必须附着在底座或机头侧面。
- 不表达真实齿轮传动，只表达搅拌头连续旋转。

### Validator
| 检查项 | 标准 |
|---|---|
| head joint | 有 revolute head tilt joint |
| tool joint | 有 continuous tool spin joint |
| tool alignment | 搅拌工具位于 bowl 中心附近 |
| bowl placement | bowl 在 base 上，且在 head 下方 |
| head sweep | 机头抬起不严重穿过立柱或碗 |
| control attachment | knob / lever 附着在主体上 |
| bowl motion | bowl 若可动，必须有 prismatic joint；fixed bowl 必须在 prompt 中说明 |
| identity | 必须像 stand mixer |
| no floating | bowl / tool / controls 全连接 |

### Reject cases
- 没有搅拌碗。
- 没有可旋转搅拌工具。
- 机头和立柱断开。
- 搅拌头不在碗上方。
- 变成 blender 或普通碗。

---

## 第一批机制模块抽取

| 模块 | 中文 | 首次来源 | 后续复用 |
|---|---|---|---|
| prismatic_slide | 直线滑轨 | Sliding Window | Standing Desk / Telescoping Boom / Rolling Toolbox / Stand Mixer |
| revolute_hinge | 旋转铰链 | Tackle Box | Refrigerator / Step Ladder / Stand Mixer |
| telescoping_tube | 伸缩套筒 | Telescoping Boom | Standing Desk / Rolling Toolbox |
| continuous_wheel | 连续旋转轮 | Platform Cart | Rolling Toolbox |
| caster_wheel | 万向轮 | Platform Cart | 后续 cart / suitcase / chair |
| latch_lock | 锁扣 | Tackle Box | Rolling Toolbox / Refrigerator |
| handle_grip | 把手 | Sliding Window / Tackle Box | 几乎所有产品类 |
| rotary_post | 旋转中心柱 | Revolving Door | turntable / globe / fan |
| radial_array | 径向阵列 | Revolving Door | fan / Ferris wheel / clock |
| folding_link_chain | 折叠连杆 | Simple Aframe Step Ladder | folding chair / folding cart |
| button_slider | 按钮滑块 | Standing Desk | Stand Mixer / controls |
| continuous_rotor | 连续旋转器 | Stand Mixer | fan / blender / wheel modules |
| mimic_link | Mimic 同步关节 | Standing Desk | 任何对称同步驱动结构 |
| gasket_strip | 门封条 | Refrigerator | 任何带密封的盖/门 |
| guide_shoe | 导靴 / 滑块 | Sliding Window | Rolling Toolbox handle / drawer |
