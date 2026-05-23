# Platform Cart｜平台推车 Spec

## 元信息
| 项 | 值 |
|---|---|
| slug | `platform_cart` |
| template path | `agent/templates/platform_cart.py` |
| test path | `tests/agent/test_platform_cart_template.py` |

## 核心身份
平板运输车，带平台 deck、底部轮子，可选折叠推手、万向轮、栏杆和防滑垫。

## 部件（Parts）

```
deck                                  # 平台主 part
 ├── wheel_i / caster_i               # 4 或 6 个轮 part；caster 模式下还有 caster_swivel_i + caster_wheel_i 两层
 ├── steering_bridge（可选，wheel_type = mixed_steering 时）  # 前转向桥独立 part
 ├── handle_left / handle_right 或 single handle part（可选）  # 推手部件
 ├── tow_bar（可选，tow_attachment = tow_bar 时）              # revolute part
 ├── fold_lip（可选，side_rail = fold_down_lip 时）            # revolute part
 └── （visual 子件挂在 deck 上）anti_slip_pad / bumpers / side_rail / tow_loop / deck_top 纹理等
```

## 组合逻辑（Composition Logic）
- 以“部件（Parts）”中的树结构作为父子装配顺序。
- 先在 `resolve_config` 中确定全局 spine / envelope，再派生子件尺寸、数量、位置和 joint range。
- 活动件必须挂在对应父 part 上；非可动装饰 / 嵌入件优先作为 `parent.visual(...)` 子件挂载。
- 所有 required part 必须连到同一主树；optional part 必须受参数显式控制。

## 关节（Joints）

| joint | 类型 | 含义 |
|---|---|---|
| wheel_i_joint | continuous | 定轮绕轮轴旋转 |
| caster_i_swivel_joint | continuous | 万向轮绕竖直轴转向 |
| caster_i_spin_joint | continuous | 万向轮的轮子绕水平轴旋转（与 swivel 串联） |
| handle_joint 或 handle_left_joint / handle_right_joint | revolute | 推手折叠（twin 配置下左右各一个） |
| steering_joint | revolute（可选，wheel_type = mixed_steering） | wagon 风格的前桥转向 |
| tow_bar_joint | revolute（可选） | 拖杆折叠 |
| fold_lip_joint | revolute（可选） | 可翻折侧栏 |

## 已有模板写法参考
continuous_wheel / caster_wheel / revolute_hinge / handle_grip

## 参数范围汇总

| 参数 | 取值建议 |
|---|---|
| deck_shape | rectangle / rounded / ribbed / tray / framed / slatted / tapered / stepped |
| deck_aspect_ratio | compact / long / wide |
| deck_top_style | flat / ribbed / diamond_plate / 等（参考代码 DECK_TOP_STYLES） |
| wheel_count | 4 / 6 |
| wheel_type | all_caster / mixed_steering / all_fixed |
| wheel_style | rubber / hard / pneumatic 等（参考代码 WHEEL_STYLES） |
| handle_style | u_handle / twin_bar / single_bar / shopping_cart / pistol_grip / panel_handle / none |
| handle_layout | single / twin 等（参考代码 HANDLE_LAYOUTS） |
| handle_fold_angle | 0 至 π/2 rad |
| handle_hinge_y_ratio | 0.2–0.5（铰链在平台后段的相对位置） |
| pistol_facing | left / right（handle_style = pistol_grip 时） |
| tow_attachment | none / tow_loop / tow_bar |
| side_rail | none / low_lip / tall_rails / fold_down_lip |
| rail_height | 连续值（仅 side_rail ≠ none 时） |
| bumper_style | none / corner / full |
| anti_slip_pattern | none / stripes / dots / grid |
| material_style | steel / plastic / aluminum |

## 约束
- 所有轮子必须在平台下方。
- 轮子左右分布要基本对称。
- 轮子旋转轴必须与轮面方向一致。
- 万向轮转向轴必须接近竖直。
- 折叠推手的铰链应在平台后侧附近：`y ∈ [0.2 L, 0.5 L]`。
- 推手折叠时不能严重穿过平台。
- 轮子必须接近地面（z gap ≤ 0.055 m）。

## Validator
| 检查项 | 标准 |
|---|---|
| wheel count | ≥ 4 |
| wheel joint | continuous |
| caster axis | 竖直转向 |
| ground contact | wheels 接近地面 |
| handle axis | handle hinge 轴水平 |
| no floating | wheel fork / handle / bumper 不漂浮 |
| identity | 必须像平台推车 |

## Reject cases
- 没有平台。
- 轮子漂浮。
- 轮轴方向错误。
- 推手位置错误。
- 变成滑板或桌子。

---
