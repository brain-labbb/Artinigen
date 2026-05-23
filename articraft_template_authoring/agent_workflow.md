# Articraft 新类别模板生成工作流

本文件定义 agent 如何从 Articraft-10K 的新类别生成 spec、如何等待人工审核、以及审核后如何基于 spec 和已有模板代码落地新模板。

核心原则：**先 spec，后模板；审核前不写代码；Spec 阶段必须枚举并完整阅读目标类别全部 5 星样本；最终 spec 只引用被采纳为模板依据的源码片段；写代码时以审核后的 spec 和其中被采纳的 5 星样本源码片段为主实现来源，已有 11 个模板代码只作为骨架、SDK 用法、测试风格和相似 pattern 参考。**

---

## 1. 两阶段执行模式

### 1.1 SPEC_ONLY：默认模式

用户给出 N 个 Articraft 类别后，agent 默认进入 `SPEC_ONLY`。

该阶段目标：

```text
N 个类别 -> N 个 specs/<category_slug>.md -> 停止等待人工审核
```

该阶段只允许创建 / 修改：

```text
articraft_template_authoring/specs/<category_slug>.md
```

该阶段禁止创建 / 修改：

```text
agent/templates/*.py
tests/agent/*.py
cli/template.py
任何 registry
```

完成 N 个 spec 后必须停止，不得继续写模板。

### 1.2 TEMPLATE_AFTER_REVIEW：审核后模式

只有用户明确表示 spec 已审核通过，才进入 `TEMPLATE_AFTER_REVIEW`。

该阶段目标：

```text
审核后的 spec + 被采纳的 5 星样本源码片段（主实现来源） + 已有 11 个模板代码（骨架/SDK/测试风格参考） -> 新 model.py 模板 + 测试 + registry
```

每个新模板必须同时参考：

1. 审核后的 `specs/<category_slug>.md`。
2. spec 中标注并被采纳的 5 星样本 `model.py:Lx-Ly` 代码片段。
3. 已有 11 个模板代码：`agent/templates/*.py`，仅用于文件骨架、SDK 写法、`resolve_config` / `_build_*` 组织方式、palette、validator 和测试风格对齐。
4. 本文件的通用模板要求、编码约定、已有模板写法参考表、测试规约。

---

## 2. 文件组织约定

```text
articraft_template_authoring/
├── AGENT_ENTRYPOINT.md
├── agent_workflow.md
├── CATEGORY_BATCH_TEMPLATE.md
├── SPEC_REVIEW_TEMPLATE.md
└── specs/
    ├── sliding_window.md
    ├── tackle_box_with_simple_hinged_lid.md
    ├── telescoping_boom.md
    └── <new_category_slug>.md
```

已有 11 个 `specs/*.md` 是 baseline spec，用于学习结构、参数、关节、validator 写法。新增类别必须另建新的 spec 文件。

---

## 3. 输入与输出

### 3.1 输入

| 输入项 | 说明 |
|---|---|
| category_slug list | 用户给出的 N 个 Articraft 类别，建议 snake_case |
| Articraft-10K dataset root | 用于读取 retained 样本、评分、`model.py`、`revision.json`、`record.json` |
| existing template directory | 默认 `agent/templates/`，包含已有 11 个模板代码 |
| existing tests directory | 默认 `tests/agent/` |
| baseline specs | `articraft_template_authoring/specs/*.md` |

### 3.2 SPEC_ONLY 输出

| 输出项 | 说明 |
|---|---|
| `articraft_template_authoring/specs/<category_slug>.md` | 该类别 spec。必须包含阅读摘要、核心身份、被采纳源码索引、Parts、Joints、组合逻辑、参数范围、已有模板写法参考、约束、Validator、Reject cases。|

### 3.3 TEMPLATE_AFTER_REVIEW 输出

| 输出项 | 说明 |
|---|---|
| `agent/templates/<category_slug>.py` | 新类别可参数化模板 |
| `tests/agent/test_<category_slug>_template.py` | 模板 validator 测试 |
| registry update | 在 `cli/template.py` 或项目实际 registry 注册 slug |

---

## 4. Hard Fail Rules

以下情况必须停止，不得继续。

### 4.1 SPEC_ONLY 阶段

- 目标类别找不到 5 星样本。
- 目标类别 5 星样本少于 5 个，且没有人工确认可继续。
- 没有枚举该类别全部 5 星样本。
- 没有读取该类别每一个 5 星样本的 `model.py` / `revision.json` / `record.json`。
- 新增 spec 的 `部件（Parts）` / `关节（Joints）` / `参数范围汇总` 缺少被采纳 5 星样本片段的真实 `model.py:Lx-Ly` 来源索引。
- spec 把已阅读但未采用的 5 星样本路径、行号、源码索引写进最终来源索引。
- spec 中出现无法从 5 星样本支持的结构，但没有标记为 `inferred`。
- spec 只总结外观颜色，没有提炼结构级参数。

### 4.2 TEMPLATE_AFTER_REVIEW 阶段

- spec 未经人工审核确认。
- 实现模板时没有读取审核后的 spec。
- 实现模板时没有打开现有 11 个模板代码作为风格和 SDK 用法参考。
- 实现模板时没有回溯 spec 中被采纳的 5 星样本 `model.py:Lx-Ly` 片段。
- 新增 pattern 不在已有模板写法参考表，且没有登记来源与参考实现。
- `resolve_config` 后仍在 `_build_*` 中随机采样关键尺寸。
- 活动件缺少 joint metadata：`type / axis / origin / range`。
- 生成结果出现漂浮件、严重穿模、关节轴错误、类别身份丢失。

---

## 5. SPEC_ONLY 工作流

对用户给出的每个类别依次执行。

### 5.1 收集并完整阅读 5 星样本

1. 用 storage API 或 `uv run articraft dataset ...` 列出该类别全部 retained 样本。
2. 过滤评分为 5 星的样本，得到完整 5 星样本清单。
3. 必须读取清单中的全部 5 星样本；不得抽样、不得只读前几个、不得只读代表样本。
4. 5 星样本少于 5 个时停止并报告，等待人工确认是否继续。
5. 对每个 5 星样本都必须读取：
   - `model.py`
   - `revision.json`
   - `record.json`
   - prompt
   - category metadata

最终 spec 中只写阅读摘要，不列出全部样本路径，不为未采用样本建立来源索引。

建议写法：

```md
## 5 星样本阅读摘要
| 项 | 值 |
|---|---|
| five_star_total | <N> |
| read_count | <N> |
| read_scope | all 5-star samples in this category |
| source_index_policy | only adopted reusable snippets are indexed below |
```

### 5.2 选择“被采纳源码片段”

完整阅读全部 5 星样本后，只选择适合模板化复用的代码片段进入 spec。

优先采纳：

- 结构清晰、part 树稳定的实现。
- 关节定义正确，axis / origin / range 明确的实现。
- 参数化程度较高，容易改写成模板的实现。
- 与已有 11 个模板 SDK 用法接近的实现。
- 能代表类别核心身份，而不是单样本装饰变体的实现。

不采纳：

- 只体现装饰、颜色、局部风格的片段。
- 单样本偶然结构，无法泛化成模板参数。
- 关节轴错误、穿模、漂浮、SDK 用法混乱的片段。
- 与类别核心身份无关的附属物。

在 spec 中写：

```md
## 采用源码索引（Adopted Source Index）
| source_id | sample_id | model.py 来源 | 采纳用途 |
|---|---|---|---|
| S1 | <sample_id> | path/to/model.py:L12-L48 | body spine + primary part layout |
| S2 | <sample_id> | path/to/model.py:L51-L69 | hinge joint definition |
```

注意：本表只列被采纳的片段；已阅读但未采用的 5 星样本不要写进来。

### 5.3 提炼核心身份

写 1–2 句中文，说明该类别最小辨识特征。

格式：

```md
## 核心身份
<什么东西>，至少包含 <关键结构>，并具有 <关键活动方式>。
```

这句话决定 reject cases。任何不满足核心身份的结构都不应进入模板。

### 5.4 提取部件

从被采纳源码片段中抽取可复用、可参数化部件。

```md
## 部件（Parts）
| 部件 | 描述 | 参数 | 来源 |
|---|---|---|---|
| body | 主体承载件 | width: float, height: float, depth: float | S1 / path/to/model.py:L12-L48 |
```

要求：

- 来源必须是被采纳 5 星样本中的真实 `model.py:Lx-Ly`。
- required part 只能来自多个 5 星样本的稳定交集或核心身份约束。
- 不稳定出现的部件标为 optional。
- 样本中没有但逻辑上需要的部件必须标为 `inferred`，不得混入 required part。
- 非可动装饰件默认用 `parent.visual(...)`，不创建独立 part。

### 5.5 提取关节

```md
## 关节（Joints）
| 关节 | 类型 | axis | origin | range | 描述 | 来源 |
|---|---|---|---|---|---|---|
| lid_joint | revolute | (0, 1, 0) | rear hinge edge | [0, 2.1] | 盖子绕后侧铰链打开 | S2 / path/to/model.py:L51-L69 |
```

要求：

- 每个活动件必须有 joint。
- joint 必须记录 `type / axis / origin / range`。
- axis 统一使用世界系 `(x, y, z)`。
- prismatic 关节必须说明滑动方向与最大行程。
- Mimic 关节必须说明源关节、multiplier、offset。

### 5.6 提取参数

```md
## 参数范围汇总
| 参数 | 类型 | 取值范围 / 候选值 | 默认值 | 派生关系 | 来源 |
|---|---|---|---|---|---|
| door_count | int | 1 / 2 / 3 / 4 | 2 | 由 door_layout 派生 | S3 / path/to/model.py:L80-L93 |
```

要求：

- 参数必须基于完整阅读全部 5 星样本后的结构变化判断。
- 参数表中的来源索引只引用被采纳、适合模板复用的 `model.py:Lx-Ly` 片段。
- “small / medium / large”“low / medium / tall”必须拆成：`*_class` + 桶内连续值。
- 所有关键尺寸必须在 `resolve_config` 中确定。
- 参数必须能在样本中产生结构级差异，不允许只换颜色。

### 5.7 写组合逻辑

说明父子链、装配顺序、数量约束、派生关系：

```md
## 组合逻辑（Composition Logic）
1. 先生成 spine/envelope。
2. 再根据 spine 派生所有子件尺寸。
3. 活动件挂在对应父件上。
4. 装饰件作为 visual 子件挂载。
```

### 5.8 写已有模板写法参考

从本文件的「已有模板写法参考表」选择 pattern 名。该字段只回答一个问题：**新模板写代码时，旧 11 个模板里哪些文件最适合参考写法**。

```md
## 已有模板写法参考
prismatic_slide / revolute_hinge / handle_grip
```

注意：这个字段不是部件来源表，不决定新模板应该包含哪些实体部件。真正写入新模板的部件、关节和关键参数，必须来自审核后 spec 的 `部件（Parts）`、`关节（Joints）`、`参数范围汇总`，并优先回溯 `采用源码索引（Adopted Source Index）` 中的 5 星样本 `model.py:Lx-Ly`。旧 11 个模板只教 agent 怎么组织代码、怎么调用 SDK、怎么写 `resolve_config` / `_build_*`、怎么写 joint metadata 和测试。

### 5.9 写 Validator

Validator 表必须可直接映射到后续测试代码。

```md
## Validator
| 检查项 | 标准 |
|---|---|
| joint count | 至少 1 个 revolute |
| axis check | hinge axis 与 spec 一致 |
| no floating | 所有 part 连接到主树 |
```

单样本结构检查写进 `run_<slug>_tests`；数据集级覆盖率检查只写进 batch validator 或 reviewer checklist。

### 5.10 写 Reject cases

写 5–8 条，描述会让样本变成 1–3 星的失败模式：

```md
## Reject cases
- 关键活动件缺失。
- 关节轴方向错误。
- 部件漂浮。
- 严重穿模。
- 类别身份丢失。
```

---

## 6. Spec Schema

每个新增 `specs/<category_slug>.md` 必须使用以下字段，字段顺序不要变。

```md
# <类别名> Spec

## 元信息
| 项 | 值 |
|---|---|
| slug | <category_slug> |
| template path | agent/templates/<category_slug>.py |
| test path | tests/agent/test_<category_slug>_template.py |
| stage | SPEC_ONLY_DRAFT / REVIEWED |

## 5 星样本阅读摘要
| 项 | 值 |
|---|---|
| five_star_total | <N> |
| read_count | <N> |
| read_scope | all 5-star samples in this category |
| source_index_policy | only adopted reusable snippets are indexed below |

## 核心身份
...

## 采用源码索引（Adopted Source Index）
| source_id | sample_id | model.py 来源 | 采纳用途 |
|---|---|---|---|

## 部件（Parts）
| 部件 | 描述 | 参数 | 来源 |
|---|---|---|---|

## 关节（Joints）
| 关节 | 类型 | axis | origin | range | 描述 | 来源 |
|---|---|---|---|---|---|---|

## 组合逻辑（Composition Logic）
...

## 已有模板写法参考
...

## 参数范围汇总
| 参数 | 类型 | 取值范围 / 候选值 | 默认值 | 派生关系 | 来源 |
|---|---|---|---|---|---|

## 约束
- ...

## Validator
| 检查项 | 标准 |
|---|---|

## Reject cases
- ...

## 审核记录
| 项 | 结论 |
|---|---|
| reviewer status | pending / approved / rejected |
| reviewer notes | ... |
```

---

## 7. TEMPLATE_AFTER_REVIEW 工作流

对每个审核通过的类别依次执行。

### 7.1 读取审核后的 spec

必须先读取：

```text
articraft_template_authoring/specs/<category_slug>.md
```

检查：

- `reviewer status = approved` 或用户明确说明已审核通过。
- Parts / Joints / 参数范围表都有被采纳片段的来源索引。
- `采用源码索引` 只包含被采纳为模板依据的片段。
- 已有模板写法参考字段可映射到 参考表；该字段只用于选择已有模板骨架和相似写法，不作为部件实现的优先来源。

### 7.2 选择已有模板骨架

从已有 11 个模板代码中选 1–3 个最接近的新类别骨架。注意：已有模板的作用是提供代码组织、SDK 用法、`resolve_config` / `_build_*` 拆分方式、palette、validator 和测试风格；不是优先部件实现来源。关键部件、关节和参数实现必须优先改编 spec 中被采纳的 5 星样本源码片段。

优先级：

1. 关节类型一致。
2. part 树相似。
3. 参数模式相似。
4. validator 逻辑相似。
5. SDK 用法最接近。

示例：

| 新类别结构 | 优先参考模板 |
|---|---|
| 直线滑动 / 抽屉 / 导轨 | `sliding_window.py` / `refrigerator_with_hinged_doors.py` |
| 铰链盖 / 翻盖 / 门 | `tackle_box_with_simple_hinged_lid.py` / `refrigerator_with_hinged_doors.py` |
| 多级伸缩 | `telescoping_boom.py` / `standing_desk_with_synchronous_telescoping_legs_and_articulated_controls.py` |
| 轮子 / 推车 / 万向轮 | `platform_cart.py` / `rolling_toolbox_with_telescoping_handle.py` |
| 径向阵列 / 中心旋转 | `revolving_door.py` / `ferris_wheel.py` |
| 折叠框架 | `simple_aframe_step_ladder.py` |
| 竖直旋转工具 / 控件 | `stand_mixer.py` |

### 7.3 回溯被采纳的 5 星样本源码片段

根据 spec 中 `采用源码索引`、Parts / Joints / 参数表标注的 `model.py:Lx-Ly` 读取被采纳代码片段。该步骤是模板实现的主来源。

用途：

- 抽取关键几何部件写法。
- 抽取 joint 定义写法。
- 抽取参数范围和默认值。
- 抽取材质 / palette 习惯。

模板代码中的注释必须标明关键复用来源，例如：

```python
# Adapted from Articraft-10K sample: samples/<id>/model.py:L51-L69
```

### 7.4 编写 `agent/templates/<category_slug>.py`

要求：

- 整体文件结构、命名、SDK 用法与已有 11 个模板一致。
- 关键几何部件、关节和参数逻辑优先从 spec 中被采纳的 5 星样本片段改编。
- 已有 11 个模板只用于包装成统一代码结构、补齐 SDK 写法、validator 风格和相似 pattern 的组织方式，不得覆盖 spec 中已采纳的源码片段。
- 所有关键尺寸、计数、关节参数都以函数参数暴露，并有默认值。
- `resolve_config` 负责所有尺寸耦合与派生关系。
- `_build_*` 只负责几何落地，不再随机关键尺寸。
- 每个活动件必须有 joint metadata。
- 非可动装饰优先 `parent.visual(...)`。
- palette 必须命名，不允许裸 RGB 随机。

### 7.5 写测试

测试路径：

```text
tests/agent/test_<category_slug>_template.py
```

测试覆盖：

- part 数量
- joint 数量
- joint 类型
- axis
- range
- parent-child connectivity
- bbox containment
- no floating
- no severe penetration
- identity check

### 7.6 注册并运行

根据项目实际 registry 位置注册 slug，例如：

```text
cli/template.py
```

至少运行：

```bash
uv run articraft template <category_slug> --seed 0
uv run articraft template <category_slug> --seed 1
uv run articraft template <category_slug> --seed 2
uv run pytest tests/agent/test_<category_slug>_template.py
```

失败时优先修复：

1. URDF / SDK API 错误。
2. joint metadata 缺失。
3. bbox / connectivity 错误。
4. 明显穿模 / 漂浮。
5. 类别身份不清。
6. 参数随机性不足。

---

## 8. 通用模板要求

所有新增类别都必须遵守下表。

| 项 | 要求 |
|---|---|
| seed | 给定 seed 后生成结果可复现 |
| part naming | 零件命名稳定，不随随机采样混乱 |
| joint metadata | 每个活动件必须有 joint type / axis / origin / range |
| diversity | 不能只靠颜色变化，必须有结构级随机 |
| validation | 每类必须自带 validator |
| reject | 漂浮零件、关节轴错误、严重穿模、类别身份丢失，一律拒绝 |
| 已有模板写法参考表语义 | 该表是「已有模板写法参考 + 工程风格 anchor」，不是可 import 的库，也不是新模板部件来源 |
| 参数语义 | RANDOM PARAMETERS 是设计空间提示，必须有结构级差异，不允许全部硬编码同一形态 |
| multi-parent 处理 | 物理上多父支撑的零件允许选择单一父链 + Mimic 同步关节 |
| 离散桶 + 连续范围 | `small / medium / large`、`low / medium / tall`、`compact / normal / landmark` 等必须实现为 class 字段 + 桶内连续值 |
| 几何自洽 | 单一物体的 envelope 是 spine，所有关键子件尺寸从 spine 和 layout 派生 |
| 非可动子件挂载 | 非可动装饰 / 嵌入件优先用 `parent.visual(...)`，不创建独立 part 或 FIXED articulation |
| 测试规约 | 单测只跑单样本结构、关节、几何自洽；数据集级覆盖率放 batch validator 或 reviewer 抽样 |

---

## 9. 命名与编码约定

| 项 | 约定 |
|---|---|
| slug 命名 | `snake_case`，与 prompt / category 一致。复合特征用 `_and_` 或 `_with_` 连接 |
| Part 命名 | 与 spec 的 part 树严格对应。计数派生件用 `_i` 后缀，i 从 0 起 |
| Joint 命名 | `<part>_joint` 或语义化 `<动作>_joint`。Mimic 派生关节命名并注释源关节 |
| Axis 写法 | 全部用世界系 `(x, y, z)` tuple；竖直默认 `(0, 0, 1)`，宽度方向默认 `(0, 1, 0)`，前后方向默认 `(1, 0, 0)` |
| 范围单位 | 距离 m，角度 rad，质量 kg |
| `resolve_config` | 所有尺寸耦合、派生 count、axis、range 都在此固定 |
| `_build_*` 函数 | 一段几何 = 一个 helper；helper 自描述自包含，不依赖外部全局状态 |
| Visual 子件 | 用 `parent.visual(...)`，不创建 part 也不创建 FIXED articulation |
| 颜色采样 | 调色板必须命名，不允许裸 `(r, g, b)` 随机 |

---

## 10. 已有模板写法参考表

下表用于帮助 agent 在已有 11 个旧模板里定位相似写法。它不是部件库，也不是可 import 的代码符号。

**边界必须清楚：旧模板教 agent 怎么写模板；审核后的新 spec 决定新模板写什么部件。**

实现优先级必须是：

1. 审核后的 spec。
2. spec 中被采纳并带有 `model.py:Lx-Ly` 索引的 5 星样本部件 / 关节 / 参数代码片段。
3. 已有 11 个旧模板的代码骨架、SDK 写法、`resolve_config` / `_build_*` 组织方式、palette、joint metadata、validator 和测试风格。

| 写法参考项 | 中文 | 适合参考的旧模板 | 具体参考位置 |
|---|---|---|---|
| prismatic_slide | 直线滑轨写法 | Sliding Window / Refrigerator drawer / Rolling Toolbox | `agent/templates/sliding_window.py` `_build_sash` |
| revolute_hinge | 旋转铰链写法 | Tackle Box / Refrigerator / Step Ladder / Stand Mixer | `agent/templates/refrigerator_with_hinged_doors.py` `_build_door_visuals` |
| telescoping_tube | 嵌套伸缩套筒写法 | Telescoping Boom / Standing Desk / Rolling Toolbox | `agent/templates/telescoping_boom.py` `_build_rect_stage` |
| continuous_wheel | 定轴轮写法 | Platform Cart / Rolling Toolbox | `agent/templates/platform_cart.py` `_add_wheel_geometry` |
| caster_wheel | 万向轮写法 | Platform Cart / Rolling Toolbox | `agent/templates/rolling_toolbox_with_telescoping_handle.py` `_build_caster_yoke` |
| latch_lock | 锁扣翻片写法 | Tackle Box / Rolling Toolbox | `agent/templates/tackle_box_with_simple_hinged_lid.py` `_build_latch_visuals` |
| handle_grip | 把手 / 推手写法 | Sliding Window / Tackle Box / Platform Cart | `agent/templates/tackle_box_with_simple_hinged_lid.py` `_build_top_bar_handle`；folding handle 见 `agent/templates/platform_cart.py` |
| rotary_post | 旋转中心柱写法 | Revolving Door / Ferris Wheel | `agent/templates/revolving_door.py` `_build_central_post` |
| radial_array | 径向阵列写法 | Revolving Door / Ferris Wheel | `agent/templates/revolving_door.py` `_add_wing` |
| folding_link_chain | A-frame 折叠连杆写法 | Simple Aframe Step Ladder | `agent/templates/simple_aframe_step_ladder.py` `build()` 顶部铰链 + spreader 段 |
| button_slider | 控制按钮 / 拨杆写法 | Standing Desk / Stand Mixer | `agent/templates/stand_mixer.py` speed_selector / knob 段 |
| continuous_rotor | 连续旋转工具写法 | Stand Mixer / Ferris Wheel | `agent/templates/stand_mixer.py` `_build_dough_hook_geometry` + tool_spin_joint |
| mimic_link | Mimic 同步关节写法 | Standing Desk / Ferris Wheel | `agent/templates/ferris_wheel.py` `_add_gondola` 内 Mimic 配置 |
| gasket_strip | 门 / 盖封条写法 | Refrigerator | `agent/templates/refrigerator_with_hinged_doors.py` `_build_door_visuals` 四边薄条段 |
| guide_shoe | 导靴 / 滑块写法 | Sliding Window / drawer-like structures | `agent/templates/sliding_window.py` `_build_sash` 内 slider_pad 段 |

使用约定：

1. 本表只作为旧模板写法参考，不替代 spec 中被采纳的 5 星样本源码片段。
2. 若 spec 已经提供某个部件 / 关节 / 参数的 `model.py:Lx-Ly` 来源，必须优先改编该源码片段。
3. 打开对应旧模板代码时，只学习文件组织、SDK 调用方式、helper 拆分、joint metadata 写法、palette 与 validator 风格。
4. 只有当 spec 中的 5 星源码片段缺少某个通用工程写法时，才允许从旧模板借用相似 helper 的写法，并按新类别尺寸、轴向、palette 重新校准。
5. 新类别引入本表没有的写法时，先在新 spec 的「已有模板写法参考」字段写新名字，再在本表末尾追加一行，包含参考位置。

## 11. Spec 审核 checklist

提交一份新类别 spec 前自查：

- [ ] 已枚举并读取该类别全部 5 星样本，且不少于 5 个；不足 5 个时已说明原因并等待人工确认。
- [ ] 读取内容包含每个 5 星样本的 `model.py` / `revision.json` / `record.json`。
- [ ] spec 中没有把已读但未采用的样本写入来源索引。
- [ ] 核心身份能区分该类别与相邻类别。
- [ ] 部件表包含被采纳 5 星样本片段的 `model.py:Lx-Ly` 来源索引。
- [ ] 关节表包含 type / axis / origin / range / 来源。
- [ ] 参数表包含类型、取值范围、默认值、派生关系，以及被采纳片段来源。
- [ ] required part 是全部 5 星样本的稳定交集或核心身份必需项，不是单样本零件清单。
- [ ] 所有“小/中/大”“低/中/高”语义字段都拆成 class + 桶内连续值。
- [ ] 约束、Validator、Reject cases 互相补完，不重复堆砌。
- [ ] 已有模板写法参考项都能在参考表中查到；新增 pattern 已登记。
- [ ] 审核状态仍为 pending，不得进入模板实现阶段。

---

## 12. Template 实现 checklist

实现新模板前自查：

- [ ] 用户明确批准进入 `TEMPLATE_AFTER_REVIEW`。
- [ ] 已读取审核后的 spec。
- [ ] 已读取 spec 中所有被采纳的关键 `model.py:Lx-Ly` 源码片段。
- [ ] 已打开 1–3 个最接近的已有模板代码作为骨架、SDK、测试风格参考。
- [ ] 已确认关键部件 / 关节 / 参数优先改编 spec 中被采纳的 5 星样本源码片段。
- [ ] 已确定哪些已有模板写法参考项仅作为风格与骨架参考使用。
- [ ] `resolve_config` 固定所有关键尺寸、数量、range。
- [ ] `_build_*` 不再随机关键尺寸。
- [ ] 每个活动件都有 joint metadata。
- [ ] 非可动装饰件用 visual 子件挂载。
- [ ] 已写测试并覆盖 spec 的 Validator 表。
- [ ] `uv run articraft template <slug> --seed 0..2` 能跑通。
- [ ] `uv run pytest tests/agent/test_<slug>_template.py` 能跑通。
