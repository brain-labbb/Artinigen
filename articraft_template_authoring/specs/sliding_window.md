# Sliding Window｜滑动窗 Spec

## 元信息
| 项 | 值 |
|---|---|
| slug | `sliding_window` |
| template path | `agent/templates/sliding_window.py` |
| test path | `tests/agent/test_sliding_window_template.py` |

## 核心身份
带外框、轨道、玻璃窗扇，其中至少一个窗扇沿轨道做直线滑动。

## 部件（Parts）

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

## 组合逻辑（Composition Logic）
- 以“部件（Parts）”中的树结构作为父子装配顺序。
- 先在 `resolve_config` 中确定全局 spine / envelope，再派生子件尺寸、数量、位置和 joint range。
- 活动件必须挂在对应父 part 上；非可动装饰 / 嵌入件优先作为 `parent.visual(...)` 子件挂载。
- 所有 required part 必须连到同一主树；optional part 必须受参数显式控制。

## 关节（Joints）

| joint | 类型 | 含义 |
|---|---|---|
| sliding_sash_i_joint | prismatic | 窗扇沿轨道滑动 |

## 已有模板写法参考
prismatic_slide / handle_grip / guide_shoe / gasket_strip

## 参数范围汇总

| 参数 | 取值建议 |
|---|---|
| window_orientation | horizontal / vertical |
| sash_count | 2 / 3 / 4 |
| sliding_sash_count | 1 / 2（auto-clamp：`sliding_sash_count = min(sliding_sash_count, sash_count)`，保证不超过 sash_count）|
| frame_aspect_ratio | wide / square / tall（离散桶 + 桶内连续值） |
| rail_style | single / double / recessed |
| handle_style | tab / bar / recessed |
| grid_muntin_count | 0 / 2 / 4 / 6；muntin > 0 时必须有实体几何 |
| glass_opacity | clear (alpha ≥ 0.30) / frosted (alpha 0.20–0.30) / tinted (色相偏移) |
| lock_style | none / small latch / central lock |
| material_style | aluminum / PVC / wood / black metal |
| sill_profile | flush / nose（控制窗台外侧是否带 drip cap） |

## 约束
- sliding_sash 必须在 window_frame 内部。
- prismatic axis 必须与轨道方向平行。
- 滑动距离不能超过轨道长度。
- handle 必须附着在滑动窗扇上。
- glass_panel 必须嵌在 sash_frame 内。
- 固定窗扇和滑动窗扇不能完全重合。
- guide_shoe（若存在）必须始终被 rail 通道捕获，滑出末端时不能脱离。

## Validator
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

## Reject cases
- 没有可滑动窗扇。
- 滑动方向和轨道不一致。
- 玻璃或把手漂浮。
- 变成普通固定窗。
- grid_muntin_count > 0 但样本中没有 muntin 几何。

---
