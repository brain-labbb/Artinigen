# Articraft 新类别模板生成工作流

本文件定义 agent 如何从 Articraft-10K 的新类别生成 spec、如何等待人工审核、以及审核后如何基于 spec、旧 11 个 gold-standard 模板方法和已有模板代码落地新模板。

核心原则：**先 spec，后模板；审核前不写代码；Spec 阶段必须枚举并完整阅读目标类别全部 5 星样本；最终 spec 只引用被采纳为模板依据的源码片段；写代码时以审核后的 spec 和其中被采纳的 5 星样本源码片段为主实现来源，`MATURE_TEMPLATE_METHOD.md` 决定如何达到旧 11 个 gold-standard 模板的成熟度，旧 11 个模板代码作为 gold-standard 骨架/SDK/测试风格参考，新造 20+ 模板作为二级经验参考。**

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
审核后的 spec + 被采纳的 5 星样本源码片段（主实现来源） + `MATURE_TEMPLATE_METHOD.md`（参数化成熟度方法） + 旧 11 个 gold-standard 模板代码（骨架/SDK/测试风格参考） + 新 20+ 模板（二级经验参考） -> 新 model.py 模板 + 测试 + registry
```

每个新模板必须同时参考：

1. 审核后的 `specs/<category_slug>.md`。
2. spec 中标注并被采纳的 5 星样本 `model.py:Lx-Ly` 代码片段。
3. `MATURE_TEMPLATE_METHOD.md`：用于判断是否拆分/收窄、如何把五星样本代码参数化、如何写 `config_from_seed` / `resolve_config` / 空间约束 / builder / joint metadata / QC / 自动调参闭环。
4. 旧 11 个 gold-standard 模板代码，仅用于文件骨架、SDK 写法、`resolve_config` / `_build_*` 组织方式、palette、joint metadata、validator 和测试风格对齐。
5. 新造 20+ 模板，可以作为二级参考，学习拆分经验、seed domain、已修 QC/预览问题、相近 helper 和测试断言。
6. 本文件的通用模板要求、编码约定、已有模板写法参考表、测试规约。

---

## 2. SPEC_ONLY 工作流

### 2.1 收集并完整阅读 5 星样本

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

### 2.2 选择“被采纳源码片段”

完整阅读全部 5 星样本后，只选择适合模板化复用的代码片段进入 spec。

优先采纳：

- 结构清晰、part 树稳定的实现。
- 关节定义正确，axis / origin / range 明确的实现。
- 参数化程度较高，容易改写成模板的实现。
- 与旧 11 个 gold-standard 模板 SDK 用法接近的实现。
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

### 2.3 提炼核心身份

写 1–2 句中文，说明该类别最小辨识特征。

```md
## 核心身份
<什么东西>，至少包含 <关键结构>，并具有 <关键活动方式>。
```

### 2.4 提取部件

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

### 2.5 提取关节

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

### 2.6 提取参数

```md
## 参数范围汇总
| 参数 | 类型 | 取值范围 / 候选值 | 默认值 | 派生关系 | 来源 |
|---|---|---|---|---|---|
| door_count | int | 1 / 2 / 3 / 4 | 2 | 由 door_layout 派生 | S3 / path/to/model.py:L80-L93 |
```

要求：

- 参数必须基于完整阅读全部 5 星样本后的结构变化判断。
- 参数表中的来源索引只引用被采纳、适合模板复用的 `model.py:Lx-Ly` 片段。
- 连续尺寸参数用于表达尺度、比例、厚度、角度、行程等连续变化。
- 定性形态参数用于表达连续尺寸无法表达的形状、轮廓、布局、风格差异。
- 不强制每个部件都有离散桶；但如果 5 星样本显示存在定性外形差异，必须显式加入 `*_shape / *_style / *_profile / *_variant / *_layout` 等参数。

### 2.7 部件多样性审计（Part Diversity Audit）

每个 spec 必须对核心部件逐个做多样性审计。这个审计不是数 enum 行，而是判断每个关键部件是否有足够的形态表达。

至少检查：

- 主体外壳：`body / housing / case / frame`
- 活动部件：`door / blade / drawer / arm / screen / pedal / crank / lens barrel`
- 支撑部件：`base / stand / bracket / mast / fork / legs`
- 操作部件：`handle / knob / switch / latch / grip`
- 连接部件：`hinge / joint cover / collar / hub`
- 类别识别部件：最能让人认出该类别的 1–3 个 part

写法：

```md
## 部件多样性审计（Part Diversity Audit）
| 部件类型 | observed_variation | 连续参数是否足够 | 是否需要离散参数 | 推荐参数 | 说明 |
|---|---|---|---|---|---|
| blade | 木纹长方板 / 弧形 / 翼形 | no | yes | blade_shape | 长宽厚和 pitch 不能表达轮廓差异 |
| hub | 圆柱 / 球形 / 分层壳体 | no | yes | hub_style | hub 是核心视觉部件 |
| downrod | none | yes | no | downrod_length | 全部 5 星样本中未观察到定性外形差异；只保留长度连续参数 |
| pull_chain | none | no | no | none | 若样本中没有该部件或不属于核心部件，可记录 none，不强行加入参数 |
```

判断规则：

- 如果差异只是长短、宽窄、厚薄、角度、行程：连续参数即可。
- 如果差异是轮廓、拓扑、布局、截面、开孔、框架形式、操作件形式：必须显式枚举。
- 连续参数不能替代定性外形差异。
- 如果某个核心部件在全部 5 星样本中没有观察到形态多样性，记录 `observed_variation = none`，不强行加 enum。
- 如果只观察到长短、宽窄、厚薄、角度、行程等连续变化，说明连续参数为什么足够。

### 2.8 写组合逻辑

说明父子链、装配顺序、数量约束、派生关系：

```md
## 组合逻辑（Composition Logic）
1. 先识别主约束基准：envelope / spine / rail / hinge line / axis / socket / contact plane / symmetry plane / linkage pivots。
2. 根据类别拓扑选择约束策略：盒体分舱 / 框架支撑 / 导轨滑移 / 铰链扫掠 / 嵌套伸缩 / 径向排布 / 折叠连杆 / 接地支撑 / 镜像配对。
3. 再根据该基准派生所有子件数量、尺寸、origin、orientation 和 clearance。
4. 活动件挂在对应父件上，并从同一约束链派生 joint origin / range。
5. 装饰件作为 visual 子件挂载。
```

### 2.9 写已有模板写法参考

从本文件的「已有模板写法参考表」选择 pattern 名。该字段只回答一个问题：**新模板写代码时，旧 11 个 gold-standard 模板和可用二级参考里哪些文件最适合参考写法**。

```md
## 已有模板写法参考
prismatic_slide / revolute_hinge / handle_grip
```

注意：这个字段不是部件来源表，不决定新模板应该包含哪些实体部件。真正写入新模板的部件、关节和关键参数，必须来自审核后 spec 的 `部件（Parts）`、`关节（Joints）`、`参数范围汇总`，并优先回溯 `采用源码索引（Adopted Source Index）` 中的 5 星样本 `model.py:Lx-Ly`。旧 11 个 gold-standard 模板教 agent 怎么组织代码、怎么调用 SDK、怎么写 `resolve_config` / `_build_*`、怎么写 joint metadata 和测试；新 20+ 模板可作为二级参考，帮助学习相近类别拆分、seed domain、已修问题和测试覆盖；`MATURE_TEMPLATE_METHOD.md` 教 agent 如何把五星样本代码参数化到旧 11 个模板成熟度。

### 2.10 写 Validator

Validator 表必须可直接映射到后续测试代码。

```md
## Validator
| 检查项 | 标准 |
|---|---|
| joint count | 至少 1 个 revolute |
| axis check | hinge axis 与 spec 一致 |
| no floating | 所有 part 连接到主树 |
| part diversity | Part Diversity Audit 中需要的 style/shape 参数均存在 |
```

### 2.11 写 Reject cases

写 5–8 条，描述会让样本变成 1–3 星的失败模式。

---

## 3. Spec Schema

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

## 参数范围汇总
| 参数 | 类型 | 取值范围 / 候选值 | 默认值 | 派生关系 | 来源 |
|---|---|---|---|---|---|

## 部件多样性审计（Part Diversity Audit）
| 部件类型 | observed_variation | 连续参数是否足够 | 是否需要离散参数 | 推荐参数 | 说明 |
|---|---|---|---|---|---|
| <part> | none / <observed variants> | yes / no | yes / no | <param or none> | <reason> |

## 组合逻辑（Composition Logic）
...

## 已有模板写法参考
...

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

## 4. TEMPLATE_AFTER_REVIEW 工作流

### 4.1 读取审核后的 spec

检查：

- `reviewer status = approved` 或用户明确说明已审核通过。
- Parts / Joints / 参数范围表都有被采纳片段的来源索引。
- `采用源码索引` 只包含被采纳为模板依据的片段。
- `部件多样性审计` 已覆盖核心部件。
- 审计中标为“需要离散参数”的部件，在 `参数范围汇总` 中确实有对应 `*_shape / *_style / *_profile / *_variant / *_layout` 参数。
- 已有模板写法参考字段只用于选择旧 11 个 gold-standard 模板骨架、相似写法和可用二级参考，不作为部件实现的优先来源。

### 4.2 读取成熟模板方法并决定拆分 / 收窄

读取 `MATURE_TEMPLATE_METHOD.md`，先判断审核后的 spec 是否过宽。

必须检查：

- 是否存在多个不兼容主运动 spine。
- root 坐标系、主承载件、joint chain 是否能共享。
- `Part Diversity Audit` 中的拓扑差异是否大到需要拆分 slug。
- `config_from_seed` 是否能只采样已实现且测试覆盖的稳定子域。
- `resolve_config` 是否能合法化和派生所有互斥组合，而不是把非法组合留给 builder。

如果需要拆分，先给出拆分建议和每个子模板的 seed domain；不要把互斥机构硬塞进一个大模板。

### 4.3 选择旧 11 个 gold-standard 模板骨架

从旧 11 个 gold-standard 模板代码中选 1–3 个最接近的新类别骨架。注意：旧模板的作用是提供代码组织、SDK 用法、`resolve_config` / `_build_*` 拆分方式、palette、validator 和测试风格；不是优先部件实现来源。新生成但尚未人工验收的模板不能作为成熟度参考。

### 4.3.1 选择新 20+ 模板二级参考

可再选择 0–2 个相近的新模板作为二级参考。

允许参考：

- 拆分 slug 的经验。
- `config_from_seed` 如何限制稳定 seed domain。
- `resolve_config` 如何处理宽 spec 的降级。
- 已修过的 QC / 预览问题。
- 相近 helper 的局部写法和测试断言。

禁止参考：

- 用新模板定义成熟度下限。
- 复制未验收的新模板粗糙结构。
- 用新模板替代 spec 中采纳的 5 星样本源码片段。
- 因为新模板能跑通而跳过当前模板的自动调参闭环。

### 4.4 回溯被采纳的 5 星样本源码片段

根据 spec 中 `采用源码索引`、Parts / Joints / 参数表标注的 `model.py:Lx-Ly` 读取被采纳代码片段。该步骤是模板实现的主来源。

该步骤必须产出源码改编映射：

- adopted source id -> 对应模板 helper。
- adopted source id -> 对应 required / optional part。
- adopted source id -> 对应 joint type / axis / origin / range。
- 五星样本中的几何常量 -> `Config` 参数或 `ResolvedConfig` 派生量。
- 五星样本中的父子关系 / closed pose -> 模板装配顺序和 origin 公式。
- 五星样本中的承载基准 / 导轨 / 铰链 / 轴线 / 接地点 / 对称关系 -> `resolve_config` 中采用的约束策略。

如果某个核心 part 或 joint 没有 source mapping，则不得进入 builder 实现。

### 4.5 编写 `agent/templates/<category_slug>.py`

要求：

- 整体文件结构、命名、SDK 用法与旧 11 个 gold-standard 模板一致。
- 关键几何部件、关节和参数逻辑优先从 spec 中被采纳的 5 星样本片段改编。
- 旧 11 个 gold-standard 模板只用于包装成统一代码结构、补齐 SDK 写法、validator 风格和相似 pattern 的组织方式，不得覆盖 spec 中已采纳的源码片段。
- 新 20+ 模板只作为二级经验参考；可吸收同类修复经验，但不得降低本模板的验收线。
- 模板文件必须 `>= 1000` 行。1000 行是最低保险线，不是上限；行数达标仍需满足源码改编、空间约束、joint 语义和 QC。
- 所有关键尺寸、计数、关节参数都以函数参数暴露，并有默认值。
- `config_from_seed` 只采样当前实现且测试覆盖的稳定子域。
- `resolve_config` 负责 enum 校验、范围夹紧、别名/legacy 兼容、互斥组合降级、所有尺寸耦合与派生关系。
- `resolve_config` 必须采用拓扑匹配的约束设计：先确定外壳 / frame / base / rail / hinge line / axis / socket / contact plane / symmetry plane 等主约束基准，再派生子件数量、尺寸、origin、orientation 和 joint range，避免悬空和穿模。抽屉柜 envelope-first 只是一个例子，不可机械套用到所有类别。
- 进入 `_build_*` 前必须建立语义约束图：核心 part / joint 需要明确 `source -> parent -> interface -> derived placement -> motion story -> invariant`。不能把五星样本中的 gasket、hinge、guide shoe、hub、socket、divider、control 等当成独立视觉件随机摆放。
- 接口件优先从父基准派生：滑轨类先 rail slot 再 gasket / guide shoe / lid origin；铰链类先 hinge line/barrel 再门板和 pivot；旋转类先 hub/shaft/opening 再 fan/platter/blades；伸缩类先 socket/overlap 再 stage range；支撑类先 contact plane 再脚/轮/支架。
- `_build_*` 只负责几何落地，不再随机关键尺寸。
- 每个活动件必须有 joint metadata。
- 每个真实 joint 必须有 motion story：父件、子件、closed pose、运动方向、语义约束，并用测试检查 type / axis / origin / range。
- 非可动装饰优先 `parent.visual(...)`。
- palette 必须命名，不允许裸 RGB 随机。
- 对 `Part Diversity Audit` 中标为需要离散参数的核心部件，必须实现对应 shape/style/profile/variant/layout 分支。
- 测试必须覆盖 seed domain、关键 joint、关键 visual、离散多样性分支和模板内 QC。

### 4.6 自动调参闭环

> **该节已由 [`TEMPLATE_AUTHORING_AGENT.md`](../TEMPLATE_AUTHORING_AGENT.md) 取代。** 新的强制循环是：
>
> ```bash
> uv run articraft template sweep-pipeline <slug>
> ```
>
> 这个 CLI 按 `0 → 0-4 → 0-19 → 0-49` 增量运行 full compile sweep，失败即停，并输出 `repair_summary`。每个 seed 仍跑同 record `target=full` 的 author `run_tests` + compiler baseline（包括 `fail_if_articulation_origin_far_from_geometry`），并在阶段 report 中聚合 `failure_clusters`、`coverage_gates`（line_floor / enum_coverage / adopted_source）、跨调用 `streak_count` 和 `escalation`。本节保留作为旧实现的参考，但**不得作为完成判据**：模板必须按 `TEMPLATE_AUTHORING_AGENT.md` §4 的停止条件验收。

> 手动 fallback 是：
>
> ```bash
> uv run articraft template compile-sweep <slug> --seeds 0
> uv run articraft template compile-sweep <slug> --seeds 0-4
> uv run articraft template compile-sweep <slug> --seeds 0-19
> uv run articraft template compile-sweep <slug> --seeds 0-49
> ```
>
> pipeline pass 后仍需单独推 viewer：
>
> ```bash
> uv run articraft template batch <slug> --seeds 0-9 --agent claude-code
> ```

#### 历史描述（仅供参考）

实现初稿后，agent 必须自动调到验收线，不得把调参默认交给用户。

每一轮闭环（旧版手动列表，请用 `sweep-pipeline` 替代）：

1. 运行 `uv run pytest tests/agent/test_<category_slug>_template.py`。
2. 运行 `test "$(wc -l < agent/templates/<category_slug>.py)" -ge 1000`。
3. 运行 `uv run python scripts/check_template_qc.py --slugs <category_slug> --seeds 0-2`。
4. 运行 `uv run python scripts/render_template_previews.py --slugs <category_slug> --seeds 0-2`。
5. 打开预览图，检查类别身份、比例、装配、closed pose、活动件、导轨/铰链/套筒是否可信。
6. 对照 spec 中采用的 5 星样本 `model.py:Lx-Ly`，确认关键部件和 joint 没有被旧模板写法替代。
7. 检查拓扑约束派生链：子件数量、尺寸、origin、orientation、joint range 是否由该类别的主约束基准约束，而不是独立随机。抽屉柜用 envelope-first；滑轨用 rail；铰链件用 hinge line；伸缩件用 socket/overlap；旋转件用 hub/axis；支撑件用 contact plane。
8. 检查语义约束图和预览是否一致：gasket 必须嵌在 slot，hinge 必须贴 hinge line，fan 必须嵌入 shroud/hub，divider 必须贴底且不压货物，control/handle/button 必须贴面板，不能有解释不清的悬空 visual。
9. 如果任一项失败，直接修改模板和测试后重复本闭环。

旧版完成条件（同上，已被 `TEMPLATE_AUTHORING_AGENT.md` §4 取代）：

- 单测通过。
- 模板文件 `>= 1000` 行。
- QC 通过，或存在已解释且安全的例外。
- 预览图由 agent 检查通过，且 seed 0-2 有结构差异。
- 核心 part / joint 有 adopted source mapping。
- 空间派生链可解释，且约束策略与类别拓扑匹配；活动件 closed pose 不悬空、不穿模。
- `config_from_seed` 不采样未实现分支。
- `resolve_config` 能校验、夹紧、降级非法或过宽组合。
- 没有留下 TODO、人工手调建议或"后续再调"的完成状态。

只有 spec 矛盾、必须用户决定拆分 slug、或需要用户在保真/覆盖之间取舍时，才允许暂停询问。

### 4.7 多类别模板实现节奏

如果用户一次给出多个类别：

- SPEC_ONLY 可以批量处理。
- TEMPLATE_AFTER_REVIEW 默认一次只实现 1 个模板。
- 只有同一大类拆分出的高度相似子模板，才允许 2-3 个一组实现。
- 每个模板必须先通过单测、QC、预览自检和必要自动修复，再进入下一个模板。
- 禁止一次性生成 20/30 个未验收模板，然后依赖用户逐个手调。

---

## 5. Hard Fail Rules

### 5.1 SPEC_ONLY 阶段

- 目标类别找不到 5 星样本。
- 目标类别 5 星样本少于 5 个，且没有人工确认可继续。
- 没有枚举该类别全部 5 星样本。
- 没有读取该类别每一个 5 星样本的 `model.py` / `revision.json` / `record.json`。
- 新增 spec 的 `部件（Parts）` / `关节（Joints）` / `参数范围汇总` 缺少被采纳 5 星样本片段的真实 `model.py:Lx-Ly` 来源索引。
- spec 把已阅读但未采用的 5 星样本路径、行号、源码索引写进最终来源索引。
- spec 缺少 `部件多样性审计（Part Diversity Audit）`。
- 5 星样本中存在关键部件的定性形态差异，但 spec 只用连续尺寸参数表示。
- 核心部件没有观察到形态多样性，但未记录 `observed_variation = none`。
- 核心部件只观察到连续变化，但未说明连续参数为什么足够。
- spec 中出现无法从 5 星样本支持的结构，但没有标记为 `inferred`。

### 5.2 TEMPLATE_AFTER_REVIEW 阶段

- spec 未经人工审核确认。
- 实现模板时没有读取审核后的 spec。
- 实现模板时没有读取 `MATURE_TEMPLATE_METHOD.md`。
- 实现模板时没有打开旧 11 个 gold-standard 模板代码作为风格和 SDK 用法参考。
- 实现模板时完全忽略可用的新 20+ 同类二级参考，导致重复踩已修过的 seed/QC/预览问题。
- 实现模板时没有回溯 spec 中被采纳的 5 星样本 `model.py:Lx-Ly` 片段。
- 实现模板时只是看过五星样本，没有把对应源码片段实际适配到 helper / part / joint。
- 模板文件低于 1000 行，且没有用户明确豁免。
- 实现模板时没有落实 `Part Diversity Audit` 中要求的离散参数。
- spec 明显过宽但没有拆分/收窄，也没有限制 `config_from_seed` 的稳定子域。
- 一次性生成大量模板，未逐个测试、QC、预览或人工确认。
- 测试/QC/预览发现问题后停止并要求用户手调，而不是自行修复。
- 子件尺寸、origin、orientation 或 joint range 独立随机，没有从类别主约束基准派生，或把抽屉柜 envelope 公式机械套到不匹配拓扑，导致悬空/穿模风险。
- `_build_*` 中随机关键尺寸或决定高层 layout。
- 活动件缺少 joint metadata：`type / axis / origin / range`。
- joint 没有基于部件语义确定 type、axis、origin、range，导致运动方向或铰链/滑轨位置错误。
- 生成结果出现漂浮件、严重穿模、关节轴错误、类别身份丢失。

---

## 6. 通用模板要求

| 项 | 要求 |
|---|---|
| seed | 给定 seed 后生成结果可复现 |
| line floor | `agent/templates/<slug>.py` 至少 1000 行；1000 是下限不是上限 |
| 五星源码改编 | 核心 helper / part / joint 必须能追溯到 adopted 5 星源码片段 |
| part naming | 零件命名稳定，不随随机采样混乱 |
| joint metadata | 每个活动件必须有 joint type / axis / origin / range |
| diversity | 不能只靠颜色变化，必须有结构级随机；关键部件若存在定性形态差异，必须显式表达 |
| 参数语义 | 连续参数表达尺度 / 比例 / 厚度 / 角度；离散参数表达形态 / 轮廓 / 布局 / 风格 |
| 空间约束 | 先识别类别拓扑和主约束基准，再选择对应约束策略派生数量、尺寸、origin、orientation 和 joint range；抽屉柜 envelope-first 只是其中一种 |
| joint 语义 | 先理解真实运动语义，再确定 type、axis、origin、range，并测试运动方向 |
| 拆分 / 收窄 | 主运动 spine 或 joint chain 不兼容时，优先拆分 slug；若暂不拆分，`config_from_seed` 必须只采样稳定子域 |
| config_from_seed | 只负责可复现采样，且只采样已实现、已测试的布局和参数组合 |
| resolve_config | 负责 enum 校验、范围夹紧、legacy alias、互斥组合降级、尺寸和 joint 派生 |
| builder | `_build_*` 只消费 resolved config 和 assets；不随机关键尺寸，不决定高层 layout |
| 自动调参 | agent 必须运行测试、QC、预览、自检、修复、重复；用户不是默认调参器 |
| gold-standard 参考语义 | 旧 11 个模板是成熟度和工程风格 anchor，不是可 import 的部件库，也不是新模板部件来源 |
| 二级参考语义 | 新 20+ 模板可参考拆分、seed domain、测试和已修问题，但不能定义成熟度或替代 5 星源码 |
| 非可动子件挂载 | 非可动装饰 / 嵌入件优先用 `parent.visual(...)`，不创建独立 part 或 FIXED articulation |
| 测试规约 | 单测只跑单样本结构、关节、几何自洽；数据集级覆盖率放 batch validator 或 reviewer 抽样 |

---

## 7. 已有模板写法参考表

下表用于帮助 agent 在旧 11 个 gold-standard 模板和可用二级参考里定位相似写法。它不是部件库，也不是可 import 的代码符号。

**边界必须清楚：旧 11 个 gold-standard 模板教 agent 怎么写成熟模板；新 20+ 模板可提供二级经验参考；审核后的新 spec 决定新模板写什么部件；`MATURE_TEMPLATE_METHOD.md` 决定如何达到旧 11 个模板成熟度。**

| 写法参考项 | 中文 | 适合参考的 gold-standard 模板 | 具体参考位置 |
|---|---|---|---|
| prismatic_slide | 直线滑轨写法 | Sliding Window / Refrigerator drawer / Rolling Toolbox | `agent/templates/sliding_window.py` `_build_sash` |
| revolute_hinge | 旋转铰链写法 | Tackle Box / Refrigerator / Step Ladder / Stand Mixer | `agent/templates/refrigerator_with_hinged_doors.py` `_build_door_visuals` |
| telescoping_tube | 嵌套伸缩套筒写法 | Telescoping Boom / Standing Desk / Rolling Toolbox | `agent/templates/telescoping_boom.py` `_build_rect_stage` |
| continuous_wheel | 定轴轮写法 | Platform Cart / Rolling Toolbox | `agent/templates/platform_cart.py` `_add_wheel_geometry` |
| caster_wheel | 万向轮写法 | Platform Cart / Rolling Toolbox | `agent/templates/rolling_toolbox_with_telescoping_handle.py` `_build_caster_yoke` |
| latch_lock | 锁扣翻片写法 | Tackle Box / Rolling Toolbox | `agent/templates/tackle_box_with_simple_hinged_lid.py` `_build_latch_visuals` |
| handle_grip | 把手 / 推手写法 | Sliding Window / Tackle Box / Platform Cart | `agent/templates/tackle_box_with_simple_hinged_lid.py` `_build_top_bar_handle` |
| rotary_post | 旋转中心柱写法 | Revolving Door / Ferris Wheel | `agent/templates/revolving_door.py` `_build_central_post` |
| radial_array | 径向阵列写法 | Revolving Door / Ferris Wheel | `agent/templates/revolving_door.py` `_add_wing` |
| folding_link_chain | A-frame 折叠连杆写法 | Simple Aframe Step Ladder | `agent/templates/simple_aframe_step_ladder.py` `build()` 顶部铰链 + spreader 段 |
| button_slider | 控制按钮 / 拨杆写法 | Standing Desk / Stand Mixer | `agent/templates/stand_mixer.py` speed_selector / knob 段 |
| continuous_rotor | 连续旋转工具写法 | Stand Mixer / Ferris Wheel | `agent/templates/stand_mixer.py` `_build_dough_hook_geometry` + tool_spin_joint |
| mimic_link | Mimic 同步关节写法 | Standing Desk / Ferris Wheel | `agent/templates/ferris_wheel.py` `_add_gondola` 内 Mimic 配置 |
| gasket_strip | 门 / 盖封条写法 | Refrigerator | `agent/templates/refrigerator_with_hinged_doors.py` `_build_door_visuals` 四边薄条段 |
| guide_shoe | 导靴 / 滑块写法 | Sliding Window / drawer-like structures | `agent/templates/sliding_window.py` `_build_sash` 内 slider_pad 段 |

使用约定：

1. 本表只作为旧 11 个 gold-standard 模板写法参考和新 20+ 模板二级经验参考，不替代 spec 中被采纳的 5 星样本源码片段。
2. 若 spec 已经提供某个部件 / 关节 / 参数的 `model.py:Lx-Ly` 来源，必须优先改编该源码片段。
3. 打开对应 gold-standard 模板代码时，只学习文件组织、SDK 调用方式、helper 拆分、joint metadata 写法、palette 与 validator 风格。
4. 只有当 spec 中的 5 星源码片段缺少某个通用工程写法时，才允许从旧 11 个模板借用相似 helper 的写法，并按新类别尺寸、轴向、palette 重新校准。

---

## 8. Spec 审核 checklist

- [ ] 已枚举并读取该类别全部 5 星样本。
- [ ] spec 中没有把已读但未采用的样本写入来源索引。
- [ ] 核心身份能区分该类别与相邻类别。
- [ ] 部件表包含被采纳 5 星样本片段的 `model.py:Lx-Ly` 来源索引。
- [ ] 关节表包含 type / axis / origin / range / 来源。
- [ ] 参数表包含类型、取值范围、默认值、派生关系，以及被采纳片段来源。
- [ ] 已有 `部件多样性审计（Part Diversity Audit）`。
- [ ] 审计覆盖主体、活动件、支撑件、操作件、连接件和类别识别部件中实际存在的核心 part。
- [ ] 若观察到定性外形差异，参数表中已加入对应 `*_shape / *_style / *_profile / *_variant / *_layout`。
- [ ] 若没有观察到部件多样性，审计中记录 `observed_variation = none`。
- [ ] 若只观察到尺寸 / 比例 / 厚度 / 角度 / 行程变化，审计中说明连续参数为什么足够。
- [ ] 已有模板写法参考字段只用于旧 11 个 gold-standard 模板写法参考和新 20+ 模板二级经验参考，不是部件来源。
- [ ] 审核状态仍为 pending，不得进入模板实现阶段。
