# Mature Template Method

本文件总结原始 11 个手调成熟模板的共同方法。它用于补强 `TEMPLATE_AFTER_REVIEW` 阶段：spec 仍决定“写什么部件”，本文件决定“如何把五星样本代码参数化到旧 11 个模板的成熟度”。

核心目标：**不要把五星样本代码机械拼成一个大模板；要先收窄/拆分到稳定机构族，再把样本中的几何常量、关节关系和外形差异提升为受约束参数。**

## 0. Gold Standard 边界

本文件的成熟度锚点是原始 11 个旧模板：

- `ferris_wheel`
- `platform_cart`
- `refrigerator_with_hinged_doors`
- `revolving_door`
- `rolling_toolbox_with_telescoping_handle`
- `simple_aframe_step_ladder`
- `sliding_window`
- `stand_mixer`
- `standing_desk_with_synchronous_telescoping_legs_and_articulated_controls`
- `tackle_box_with_simple_hinged_lid`
- `telescoping_boom`

新生成的 20+ 模板可以参考，但只能作为 **secondary reference（二级参考）**：

- 可以参考它们的拆分经验、seed domain 限制、`resolve_config` 降级方式、已修过的 QC/预览问题、相近类别 helper、测试断言和 registry/stem 写法。
- 不可以用它们定义成熟度下限；成熟度下限仍由旧 11 个 gold-standard 模板定义。
- 不可以用它们替代 spec 中被采纳的 5 星样本源码片段。
- 不可以因为某个新模板能跑通，就放宽测试、QC、预览或自动调参闭环。

参考优先级：

1. 审核后的 spec 和其中被采纳的 5 星样本 `model.py:Lx-Ly`。
2. 旧 11 个 gold-standard 模板，定义成熟度、代码组织和验收线。
3. 已经人工调过或已通过 seed domain / QC / 预览自检的新 20+ 模板，作为同类经验和局部写法参考。
4. 未验收的新模板只能作为反例或 cautionary reference，用来避免重复踩坑。

模板阶段默认按 **单类别串行 + 自动调参闭环** 执行。若用户一次给 20 或 30 个新类别，允许批量写 spec，但模板实现必须逐个或最多 2-3 个一组推进；每个模板由 agent 自己完成测试、QC、预览检查和修复后再进入下一个。禁止一口气生成大量模板后再让用户手动救火。

## 1. 成熟模板的判定标准

一个模板达到当前成熟度，至少满足：

- `agent/templates/<slug>.py` 不能少于 1000 行。1000 行是最低保险线，不是上限，也不是目标行数；只要类别复杂，模板应自然超过 1000 行。低于 1000 行默认不合格，除非用户明确豁免。
- 行数只是保险线，不是充分条件。模板必须同时满足五星源码改编、参数化约束、QC、预览和自动调参闭环。
- `Config` 暴露语义参数：`*_layout`、`*_profile`、`*_style`、`*_shape`、`*_variant`、数量、行程、角度、主尺寸、材质和 `name`。
- `config_from_seed(seed)` 可复现，并且只随机到已实现、几何稳定、测试覆盖过的子域。
- `resolve_config(config)` 是唯一的合法化和派生入口：校验 enum、夹紧连续范围、处理别名/遗留值、派生尺寸、派生 joint 原点/行程相关量、必要时把过宽 spec 降级到稳定子族。
- `_build_*` 只消费 resolved config 和 assets；不再随机关键尺寸，不决定高层布局。
- 非活动装饰、封条、螺丝、刻度、按钮面板等优先作为 `parent.visual(...)`，不要为静态小装饰创建独立 part。
- 每个真实活动件都有 articulation，并带 `type / axis / origin / range` metadata；必要时保留 `source_id` 追踪来自哪个五星片段。
- 结构级多样性来自部件外形/布局/关节集合变化，不靠颜色充数。
- 单测覆盖 invalid config、seed 可复现、seed 随机域、关键 joint、关键 visual 名称、多样性分支、模板内 QC。

## 2. 先决定是否拆分类别

很多大类 spec 会覆盖多个不兼容机构。旧 11 个 gold 模板的共同点不是“覆盖越多越好”，而是主机构 spine 稳定、参数域受控、测试能锁住行为。新模板也应先拆成几何稳定的子模板，或者在 `config_from_seed` 中只采样稳定子族。

拆分/收窄信号：

- 同一类别下存在完全不同的主运动 spine：例如抬杆、滑门、升降柱、翻板。
- root 坐标系、主承载件、joint chain 难以共享。
- `resolve_config` 需要大量互斥分支才能避免无效组合。
- seed 随机后经常产生穿模、漂浮、类别身份混乱。
- spec 的 `Part Diversity Audit` 显示拓扑差异大于连续尺寸差异。

当前新模板调优中已经证明有效的做法：

- `barrier_gate` 被拆成 `barrier_gate_boom` 与 `barrier_gate_leaf_gate`。
- `blender` 被拆成 `blender_countertop` 与 `immersion_blender`。
- `desk_with_drawer` 对 `card_catalog` 做独立子模板。
- 某些宽 spec 保留兼容 enum，但 `config_from_seed` 不采样未成熟分支，`resolve_config` 会降级到稳定子族，测试会锁住 seed domain。

写新模板时，如果发现一个 spec 太宽，应先向用户说明建议拆分；如果继续实现单模板，必须明确“本轮实现的稳定子域”和“不采样/降级的子域”。

## 3. 五星样本代码的参数化步骤

从 spec 回溯被采纳的 `model.py:Lx-Ly` 后，必须真正理解并改编代码。不能只是“看一下”五星样本，也不能只从旧模板搬骨架。核心部件、关节、尺寸关系和运动语义必须来自被采纳的五星样本源码片段，并在新模板中适配成参数化 helper。

每个模板必须建立实际的源码改编关系：

- `SOURCE_IDS` 记录被采纳五星片段。
- 每个 required part、核心 optional part、真实活动 joint 都能追到一个或多个 `SOURCE_IDS`。
- 每个主要 `_build_*` helper 都应对应 spec 中某个 adopted source 的结构、尺寸关系、part tree 或 joint 语义。
- 每个主要空间约束策略都应能追到 adopted source 中的承载基准、导轨、铰链、轴线、接地点、套筒重叠、对称关系或 linkage 关系。
- 如果只借用了旧模板 helper 的工程写法，必须按当前类别的五星源码重新校准尺寸、轴向、origin、range 和 part 命名。
- 若五星样本源码中的某段不可直接复用，需要写明是“按语义重写”，但仍要保留对应 source id 和被保留的结构关系。

改写顺序：

1. 找主 spine：固定承载件、活动件、joint chain、closed pose 的空间关系。
2. 标注常量来源：把样本里的尺寸、位置、角度、数量、颜色、运动范围分成语义常量。
3. 常量升参：把会影响类别身份或多样性的常量提升为 `Config` 字段；把只为装配自洽服务的中间量留给 `ResolvedConfig`。
4. 形态升 enum：连续尺寸无法表达的轮廓、布局、截面、开孔、连接硬件、操作件样式，必须升成 `*_style / *_profile / *_shape / *_variant / *_layout`。
5. 关系进 `resolve_config`：尺寸耦合、互斥布局、数量派生、行程上限、joint origin 都在 `resolve_config` 里确定。
6. 几何进 `_build_*`：把五星样本的 part/visual 代码拆成 `_build_body`、`_build_moving_member`、`_build_controls`、`_build_hardware` 等 helper。
7. 装饰降级为 visual：非活动小件不创建 articulation；贴到最近父 part，避免孤立 part。
8. 写测试锁行为：每个参数化分支至少有一个结构断言或 QC 样本。

不要做：

- 不要把所有样本片段直接堆进一个 builder。
- 不要只读样本后用旧模板凭空重写；五星样本对应部分必须在新模板 helper 中留下结构、尺寸关系或 joint 语义的实际改编痕迹。
- 不要每个 numeric literal 都暴露成 public config；public 参数必须有语义。
- 不要在 `_build_*` 中重新 `random`。
- 不要用一个超宽 enum 表示还没真正实现的拓扑，然后让 seed 抽到它。
- 不要用视觉装饰替代必须活动的 part/joint。

## 3.1 语义约束图：先理解接口，再写几何

新模板失败最常见的原因不是 SDK 不会写，而是把五星样本里的零件当成“独立视觉件”堆出来，没有先理解它们为什么存在、依附谁、由什么约束派生。成熟模板必须在写 `_build_*` 前先建立 **semantic constraint graph（语义约束图）**。

每个被采纳的五星样本片段至少要抽取这些关系：

- `parent / child`：该部件贴在哪个父件上，是否嵌入、悬挂、夹持、套接、支撑或围绕父件运动。
- `interface`：真实接口是什么，例如 rail slot、hinge line、socket overlap、hub bore、panel face、contact plane、symmetry plane、pivot pair。
- `derived quantities`：数量、尺寸、origin、orientation、clearance、joint range 从哪个父基准派生。
- `motion story`：若是活动件，closed pose 在哪里，沿什么轴/绕什么轴运动，真实限位来自哪里。
- `material semantics`：材质是否表达功能，例如 glass 必须透明，rubber gasket 必须在槽里，metal rail 必须承载或限位，product/load 不应被结构板压住。
- `anti-floating invariant`：该部件至少有一个面、轴、边、中心或接地点和父基准重合/相切/嵌入；不能只靠世界坐标摆放。

写模板前，agent 必须能把主要部件写成这种映射：

```text
part_name:
  source: S3 model.py:L120-L166
  parent: cabinet_body
  interface: front rail slot top surface
  placement: y = rail_y - rail_width * 0.18, z = contact_z + groove_h / 2
  dimensions: length = rail_len, width = rail_width * 0.50, height = groove_h
  semantic: recessed rubber gasket inside rail channel
  joint_relation: sliding lid shoe sits above same contact_z; prismatic origin uses same rail/contact basis
  invariant: gasket bbox must lie inside or flush with rail bbox, not float above it
```

这个映射可以写在实现注释、测试命名、`SOURCE_IDS` 附近或开发笔记里；不要求每个小螺丝都写，但所有核心 part、活动件、关节、导轨/铰链/套筒/轴/支撑接口必须有这种关系。

通用装配链必须是：

1. **父 envelope / spine / interface**：先采样并派生主承载件、内腔、框架、轨道、铰链边、轴线、接地点、对称中心线等。
2. **接口件**：再从父基准派生 slot、gasket、hinge barrel、bearing, socket lip、guide shoe、hub collar、mount bracket、stop block 等接口件。
3. **活动件 closed pose**：活动件的 closed pose 必须贴在接口件上或嵌入接口中。
4. **joint origin / axis / range**：从同一接口基准派生，不得和可见支撑件脱节。
5. **装饰和标识**：最后才添加品牌牌、刻度、螺丝、颜色条等，不得用装饰掩盖结构问题。

不同拓扑的“接口优先”例子：

| 类别 / 拓扑 | 错误堆件方式 | 正确语义约束 |
|---|---|---|
| 滑轨/滑盖 | 把黑色条独立放在轨道附近 | 先定 rail slot，再让 gasket bbox 嵌入 slot，lid shoe 和 joint origin 使用同一 contact basis |
| 门/翻盖 | 先放门板再猜 hinge joint | 先定开口边和 hinge barrel，门板 closed pose 与开口贴合，pivot offset 由 barrel 半径和门厚派生 |
| 抽屉/滑箱 | 抽屉宽高深独立随机 | 先定柜体内腔、frame thickness、gap、drawer count，再均分单体尺寸和 slide range |
| 风扇/转盘 | 圆盘/叶片漂在外壳上方 | 先定 hub/shaft 和 shroud opening，fan disk 嵌入开孔，axis 穿过 hub center |
| 百叶窗/栅格 | 叶片逐个随机角度/位置 | 先定左右框和 pivot line，slat pitch 等距派生，所有叶片共享 tilt 语义或同步关系 |
| 伸缩件 | 内外段只是相邻长方体 | 先定套筒轴线、外段内径、内段外径和最小 overlap，range 由段长和 overlap 派生 |
| 支撑/轮/脚 | 支撑件在底部附近随机摆放 | 先定 base footprint 和 ground contact plane，脚/轮底部共面，轮轴穿过 fork/yoke |

Display freezer 的修复教训要作为通用反例记住：

- 黑色密封条不是装饰条；它是 `gasket in rail channel`，必须从 rail slot 派生并贴合。
- 灰色“板”如果语义是固定玻璃，必须使用透明 glass 材质，并受盖板/轨道/开口约束；如果语义是内部隔板，必须贴底、低矮，并由 cell height / product height / liner depth 派生。
- 为了通过 joint-origin 检查而额外加一根可见悬空 spine 是错误做法；正确做法是把 joint origin 移到真实接触几何附近，或者补真实接口件。
- 如果一个 visual 的语义解释不清楚，不能把它留在模板里；要么删掉，要么重写成有 parent/interface/invariant 的部件。

对应测试要求：

- 对每个关键接口件写 bbox / origin 断言：例如 gasket 在 rail bbox 内、hinge origin 落在 hinge barrel 上、fan axis 穿过 hub center、divider bottom 等于 liner floor。
- 对材质语义写断言：例如 fixed glass alpha < 0.7，rubber gasket 使用 rubber material，不透明金属板不能替代玻璃。
- 对 joint 语义写断言：joint origin 接近真实几何，axis 平行 rail/hinge/shaft，range 小于可见导轨或扫掠约束。
- 对已修过的视觉问题写负断言：禁止 floating pad、裸露装饰条、重复隔板、悬空 spine、离开父接口面的 control/button/handle。

## 4. 推荐文件骨架

成熟模板通常按这个顺序组织：

```python
from __future__ import annotations

import math
import random
import tempfile
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Literal

from sdk import ...

Layout = Literal[...]
BodyStyle = Literal[...]
MovingPartProfile = Literal[...]
MaterialStyle = Literal[...]

SOURCE_IDS = {...}  # 推荐：新模板保留被采纳样本片段索引
PALETTES = {...}


@dataclass(frozen=True)
class CategoryConfig:
    ...


@dataclass(frozen=True)
class ResolvedCategoryConfig:
    ...


def config_from_seed(seed: int) -> CategoryConfig:
    ...


def resolve_config(config: CategoryConfig) -> ResolvedCategoryConfig:
    ...


def _joint_meta(...):
    ...


def _build_body(...):
    ...


def _build_moving_member(...):
    ...


def build_category(config: CategoryConfig | None = None, *, assets: AssetContext | None = None) -> ArticulatedObject:
    ...


def build_seeded_category(seed: int, *, assets: AssetContext | None = None) -> ArticulatedObject:
    ...


def with_overrides(config: CategoryConfig, **kwargs: object) -> CategoryConfig:
    return replace(config, **kwargs)


def run_category_tests(object_model: ArticulatedObject, config: CategoryConfig) -> TestReport:
    ...
```

`SOURCE_IDS` 不是老模板的硬要求，但新模板推荐保留，尤其是从五星样本直接改编的部件、joint、特殊几何 helper。

## 5. `config_from_seed` 规则

- 只采样当前实现并测试过的布局，不采样“未来想做”的 enum。
- 相关参数一起采样，避免非法组合。例如 layout 决定 support style、joint set、part count。
- 尺寸采样要留几何余量：关节行程不得超过轨道/壳体可用长度，活动件 closed pose 不应初始重叠。
- seed domain 要有测试：用 12、40 或 50 个 seed 检查采样集合是否正好落在预期子域。
- 如果原 spec 太宽，`config_from_seed` 应只随机稳定子族；其他值只能作为显式 override 进入 `resolve_config`，并被校验、降级或拒绝。

## 6. `resolve_config` 规则

`resolve_config` 是模板成熟度的核心。它应该：

- 校验所有 enum 和 bool/int/float 范围。
- 对兼容旧值使用 alias 映射；对不成熟组合使用明确降级，而不是在 builder 里默默失败。
- 根据主 layout 派生合法的 support style、part count、joint set、尺寸比例和装配间隙。
- 把所有公共尺寸夹紧到安全范围。
- 派生 `ResolvedConfig` 中的内部尺寸和约束量：壁厚、间隙、开口、行程、半径、柱距、抽屉行列数、panel 宽度、rail usable length、hinge pivot offset、socket overlap、hub radius、ground contact height、symmetry half-span、linkage pivot spacing 等。
- 保证后续 `_build_*` 不需要再判断非法组合。

如果一个参数被降级，测试应覆盖降级行为，像当前成熟模板里对过宽 legacy layout 的处理一样。

## 7. 空间约束和防悬空 / 防穿模设计

悬空和穿模通常不是渲染问题，而是参数化顺序错了。抽屉/柜体的 envelope-first 公式只是其中一种约束方法，不能被机械套用到所有类别。成熟模板必须先理解类别的结构拓扑和五星样本中的装配语义，再选择合适的 **主约束基准**：可能是外壳 envelope、框架 spine、导轨中心线、铰链边、嵌套套筒、轮轴、旋转中心、接地点、对称中心线或多杆 linkage，而不一定是 `cabinet_width/depth/height`。

通用顺序：

1. 先确定该类别的主约束基准：外壳、frame、base、spine、rail、hinge line、axis、socket、ground contact plane、symmetry plane 等。
2. 再选择对应的约束策略：盒体分舱、框架支撑、导轨滑移、铰链扫掠、嵌套伸缩、径向排布、折叠连杆、接地支撑、镜像配对等。
3. 再采样受约束的数量和布局：count、row/column、spoke count、leg count、segment count、panel count、link count。
4. 再派生单体尺寸和 clearance：由可用空间、中心线间距、厚度、套接余量、扫掠半径、接地高度、机械止挡计算，不独立随机。
5. 再派生 part origin / orientation：每个子件 origin 由父基准、index、axis、gap、angle、clearance 或 contact plane 算出。
6. 最后派生 joint origin / range：行程或角度不得超过导轨、壳体开口、套筒重叠、铰链 clearance、连杆几何或可见机械止挡。

约束策略库示例：

| 拓扑 / 语义 | 主约束基准 | 派生逻辑 | 典型 joint 约束 |
|---|---|---|---|
| 柜体 / 抽屉 / 货架 | 外壳 envelope + frame thickness | 先定外壳，再按 margin/gap 分舱，单元尺寸由剩余空间均分或按比例分配 | prismatic range 小于抽屉深度 / 导轨长度 |
| 门 / 翻盖 / 折页面板 | 铰链边 / hinge barrel | 子件 closed pose 贴合开口，厚度和铰链半径决定 pivot offset 与扫掠间隙 | revolute origin 在 hinge line，range 受相邻面板和止挡限制 |
| 滑窗 / 滑轨 / 滑块 | rail centerline / slot envelope | 先定轨道长度和槽宽，再派生滑块尺寸、闭合位置、端部止挡 | prismatic axis 平行 rail，range 小于 rail usable length |
| 伸缩杆 / telescoping boom | 嵌套套筒轴线 | 外段内径约束内段外径，最小插入重叠约束最大伸长 | prismatic range = 段长 - overlap - stop |
| 轮子 / 风扇 / 转盘 / 卷轴 | 旋转轴 / hub center | 先定 hub radius 和轴线，再按角度均布 spokes/blades/rim | continuous 或 revolute axis 穿过 hub center |
| 梯子 / 支架 / 折叠架 | ground contact plane + hinge spread | 先定脚点、展开角、横档间距，再派生腿长、横档 origin、铰链高度 | revolute range 受腿长、地面接触和交叉杆约束 |
| 推车 / 底座 / 桌椅 | base footprint + support spine | 先定接地点和承载框，再派生腿/轮/支撑件位置，保证底部共面或合理接触 | wheel continuous axis 对齐车轴；caster swivel 与 fork 语义一致 |
| 对称夹具 / 把手 / 双臂机构 | symmetry plane / centerline | 先定中心线和半距，再镜像派生左右件，避免一侧独立漂移 | paired joints 轴向/范围镜像或同步 |
| 多段连杆 / 剪式 / 同步机构 | linkage pivots | 先解 pivot 间距和杆长，再派生中间铰点，保证闭合姿态可达 | revolute origins 必须落在真实 pivot，mimic 关系稳定 |

典型抽屉/柜体逻辑只是一个例子：

```python
usable_h = cabinet_height - top_margin - bottom_margin
max_drawers = max(1, int((usable_h + gap) / (min_drawer_h + gap)))
n_drawers = clamp(requested_or_sampled_count, 1, max_drawers)
drawer_height = (usable_h - (n_drawers - 1) * gap) / n_drawers
drawer_width = cabinet_width - 2.0 * frame_thickness - 2.0 * side_clearance
drawer_depth = cabinet_depth - back_gap - front_clearance
drawer_travel = min(requested_travel, drawer_depth - rear_stop - front_stop)
```

硬规则：

- 子件尺寸不能脱离主约束基准独立随机。盒体类从外壳剩余空间派生；杆件类从 pivot/axis/contact 派生；旋转类从 hub/radius/angle 派生；伸缩类从套筒内外径、段长和 overlap 派生。
- 子件 origin 不能靠目测常量，应从父基准、index、axis、angle、gap、clearance、contact plane 或 linkage 解派生。
- 活动件 closed pose 必须落在它真实的机械容纳关系里：导轨内、铰链边上、套筒内、框架内、轮叉内、插槽内、接地点上或对称配对位置上。
- prismatic range 必须小于可见导轨、套筒、滑槽、抽屉深度或容纳空间的有效长度。
- revolute 活动件的扫掠必须检查 closed pose 和主要 open pose，不得与父件严重穿模；铰链 origin 必须贴合真实 hinge/pivot。
- continuous 旋转件的轴必须穿过 hub/shaft，附属 blade/spoke/rim 必须围绕该轴按角度派生，不能自由漂浮。
- 支撑类物体必须有明确接地点或承载面：脚、轮、底座、支架底端应共面或符合真实高低关系。
- 镜像/成对结构必须从同一个 symmetry plane / centerline 派生，不能左右各自随机导致错位。
- linkage 或同步机构必须先确定 pivot 几何，再放杆件和 joint；不要先画杆再猜 joint。
- 若 layout 改变拓扑，必须为该 layout 单独选择约束策略和尺寸链，不能复用不匹配的 envelope 公式。

## 8. Builder 规则

- Builder 的输入是 `ResolvedConfig`、materials、assets；不读取随机数。
- 按“承载件 -> 活动件 -> joint -> controls/hardware -> decoration”的顺序组装。
- 活动件独立 part；非活动细节作为 visual。
- visual 名称要稳定，因为测试会用 visual 名称检查分支是否真实落地。
- 重复结构用 helper 循环生成，命名要稳定：`drawer_0`、`rail_pad_1`、`slat_3_tilt`。
- 复杂几何可以用 `ExtrudeGeometry`、`LatheGeometry`、`cadquery` 或 mesh helper，但必须由参数驱动并可复现。
- palette 使用命名材质，不要在 builder 里随机裸 RGB。

## 9. Joint 规则

- spec 里的活动关系必须变成 articulation，不要只画成静态开口状态。
- 关节不能只按几何猜轴，必须先理解部件语义：它是抽屉滑轨、门铰链、翻盖、伸缩杆、旋钮、轮子、同步连杆还是风扇/刀片连续旋转。
- 每个 joint 必须写清楚 motion story：父件是谁、子件是谁、closed pose 是什么、open/extended pose 朝哪里运动、真实机械约束是什么。
- joint origin 要来自 resolved dimensions，不能靠目测常量。
- prismatic axis 必须平行可见导轨/套筒/滑槽。
- revolute axis 必须穿过可见 hinge/pin/barrel/yoke。
- continuous joint 用于轮、风扇、转盘、叶片、卷轴等无角度上限机构。
- mimic/synchronized 机构必须命名稳定，并在 metadata 或测试里体现源 joint 关系。
- 非 fixed joint 的 metadata 至少包含 `type`、`axis`、`origin`、`range`。
- 测试必须检查关键 joint 的 type、axis、origin 所在边/导轨，以及 range 是否与语义一致。
- 若预览或 URDF 中运动方向看起来反了，优先修语义和坐标系，不要用装饰遮掩。

## 10. 测试成熟度

每个新模板至少要有：

- invalid config rejection：非法 enum、非法 count、非法 range。
- seed reproducibility：同 seed 相等，不同 seed 有差异。
- seed domain restriction：如果做过拆分/收窄，测试 seed 不会跑到退休大类或未实现分支。
- line count floor：`agent/templates/<slug>.py` 行数必须 `>= 1000`。
- source adaptation map：核心 helper / required part / joint 能追溯到 `SOURCE_IDS` 或 adopted source。
- identity test：关键 part、visual、joint 存在。
- joint metadata test：非 fixed joint 有 spec metadata。
- spatial constraint test：数量、尺寸、origin 和 joint range 由该类别的主约束基准派生；drawer/panel/slat/leg/wheel/hinge/segment 等不悬空、不超出父容纳结构、不脱离真实轴线或接地点。
- diversity branch test：`*_style / *_profile / *_layout` 改变真实 visual/joint，不只是改字段。
- `run_*_tests` pass。
- 2-3 个 seed 的 `TestContext.check_model_valid()`、`fail_if_isolated_parts()`、`fail_if_parts_overlap_in_current_pose(...)`。

模板调试时优先运行：

```bash
uv run pytest tests/agent/test_<category_slug>_template.py
test "$(wc -l < agent/templates/<category_slug>.py)" -ge 1000
uv run python scripts/check_template_qc.py --slugs <category_slug> --seeds 0-2
uv run python scripts/render_template_previews.py --slugs <category_slug> --seeds 0-2
```

如果 `scripts/check_template_qc.py` 的默认 slug 列表和 registry 暂时不同，显式传 `--slugs <category_slug>`，不要依赖默认列表。

## 11. 自动调参闭环

模板阶段不是“写完代码 + 跑一次测试”就结束。agent 必须像人工手调一样自我迭代，直到达到旧 11 个 gold-standard 模板的成熟度。

每个模板必须执行以下闭环：

1. **实现初稿**：只实现当前模板稳定子域，不把未成熟分支放进 seed domain。
2. **结构测试**：运行单测和 `scripts/check_template_qc.py --slugs <slug> --seeds 0-2`。
3. **预览生成**：运行 `scripts/render_template_previews.py --slugs <slug> --seeds 0-2`。
4. **视觉自检**：打开 contact sheet 或单张预览，检查类别身份、比例、closed pose、活动件位置、导轨/铰链/套筒是否可信。
5. **源码回溯对照**：对照 spec 中采用的 5 星样本片段，检查关键部件和 joint 是否真正来自源码，而不是旧模板迁移痕迹。
6. **行数和来源检查**：检查模板行数 `>= 1000`，并确认核心 helper、required part、joint 有 source adaptation mapping。
7. **自动修复**：若测试/QC/预览/身份/行数/来源任一不合格，直接修改模板和测试；不要把问题转交给用户。
8. **重复闭环**：重新运行测试、QC、预览，直到通过验收。

完成前必须满足：

- 单测通过。
- 模板文件行数 `>= 1000`。
- 核心部件和 joint 已实际改编五星样本对应源码片段，而不是只在 spec 中引用。
- QC 通过，或存在已解释且安全的重叠例外。
- 预览图已由 agent 检查，且不像“普通相邻类别”或“只有装饰差异的旧模板”。
- seed 0-2 至少呈现结构差异，不只是颜色变化。
- `config_from_seed` 不采样未实现或不稳定分支。
- `resolve_config` 能处理显式 override 的非法/过宽组合。
- 没有留下 TODO、人工手调建议、未实现分支承诺。

只有以下情况才允许暂停询问用户：

- spec 与 5 星样本来源互相矛盾。
- 目标类别必须拆分，但拆分 slug 会影响用户的数据组织决策。
- 旧 11 个 gold-standard 模板和 5 星样本都没有可用工程参照，且继续实现会产生虚假结构。
- 需要用户选择保真优先还是覆盖更多变体优先。

除此之外，agent 必须自己完成调参，不得要求用户逐个手调。

## 12. 多类别实现节奏

批量写模板时，按这个节奏推进：

1. 先为所有类别完成 spec，人工审核并标出是否需要拆分。
2. 从中选 1 个最典型类别实现到 gold-standard 水平。
3. 跑单测、QC、预览，并根据失败/渲染图做手调。
4. 把这次手调经验回写到 spec 或本方法文档。
5. 再进入下一个类别。

最多允许 2-3 个高度相似类别并行实现，例如同一大类拆分出的子模板。禁止一次性写 20 个完整模板而不逐个验收。

## 13. Agent 自调时的决策顺序

当模板第一次生成后不够像五星样本，agent 按这个顺序自动调：

1. 先看类别身份：主 spine、承载件、活动件、joint 方向是否正确。
2. 再看装配：closed pose 是否在真实导轨/铰链/套筒内。
3. 再看多样性：enum 分支是否真的改变外形/布局/关节集合。
4. 再看尺寸范围：seed 是否过宽导致穿模或过窄导致无差异。
5. 最后看装饰：封条、螺丝、纹理、刻度、把手、警示条。

不要先堆装饰修像；如果 spine 和 joint 错了，装饰越多越难调。用户不应该成为默认调参器，agent 必须先自行完成这些修复。
