# Articraft Modular Template Workflow

本文件定义新类别模板的唯一 authoring 流程：先写 modular spec，人工审核后再写 modular template。核心设计对象是 **slot / candidate module / interface point / module factory / topology diversity**。

## 1. 执行模式

### 1.1 SPEC_ONLY：默认模式

用户给出 N 个 Articraft 类别后，agent 默认进入 `SPEC_ONLY`。

目标：

```text
N 个类别 -> N 个 specs_modular_v1/<category_slug>.md -> 停止等待人工审核
```

只允许创建或修改：

```text
articraft_template_authoring/specs_modular_v1/<category_slug>.md
```

禁止创建或修改模板代码、测试、registry、CLI。

### 1.2 TEMPLATE_AFTER_REVIEW：审核后模式

只有用户明确表示 spec 已审核通过，才进入 `TEMPLATE_AFTER_REVIEW`。

目标：

```text
审核后的 modular spec
+ 每个 module candidate 的 5 星样本源码片段
+ MODULAR_TEMPLATE_AUTHORING.md
+ MATURE_TEMPLATE_METHOD.md
+ TEMPLATE_AUTHORING_AGENT.md / TEMPLATE_DESIGN_RULES.md
-> agent/templates/<slug>.py
-> sweep-pipeline verdict=pass
-> preview / viewer 目检
```

## 2. SPEC_ONLY 工作流

### 2.1 完整读取 5 星样本

1. 用 storage API 或 CLI 列出目标类别全部 retained 样本。
2. 过滤评分为 5 星的样本。
3. 必须读取所有 5 星样本；不得抽样。
4. 5 星样本少于 5 个时停止并报告，等待人工确认是否继续。
5. 对每个 5 星样本读取 `model.py`、`revision.json`、`record.json`、prompt 和 category metadata。

spec 中只写汇总和被采纳 module source，不列出未采用样本清单。

### 2.2 识别结构变化轴

从全部 5 星样本中识别真正的拓扑变化：

- part tree 不同。
- joint count / type / parent-child topology 不同。
- chain depth 不同。
- 同一功能层有不同接口点位或承载方式。
- 同构子件数量可变或固定 N 个同构复制件形成结构差异。

只改变尺寸、比例、颜色、材质、装饰密度的差异不是独立 slot，也不是独立 candidate module。

### 2.3 设计 slots

每个 slot 表示一个可替换的结构/功能层。典型模板使用 2-4 个 slot，3 个最常见。

slot 成立条件：

- 至少有 2 个结构不同的 candidate module；目标是 3-6 个。
- 相邻 slot 能通过共同 parent、mating face、pivot、rail、socket、axis、contact plane 或 symmetry plane 装配。
- slot 的变化会影响 part tree、joint topology、chain depth、module-local copied objects 或核心 primitive。

如果一个变化没有足够来源，折入相邻 module，或作为 module-local variant；不要为了凑 slot 发明结构。

### 2.4 选择 candidate modules

每个 candidate module 必须来自被采纳的 5 星样本代码片段。

优先采纳：

- part tree 清楚、活动语义明确、joint origin/axis/range 可回溯的片段。
- primitive 或 mesh 复杂度能体现类别身份的片段。
- 与 slot graph 接口点位兼容的片段。
- 能代表真实结构家族的片段，而不是单个装饰变体。

不采纳：

- 只换色、换尺寸、换装饰的片段。
- 漂浮、穿模、joint 语义错误或 SDK 用法混乱的片段。
- 不能接入当前 slot graph 的孤立结构。

### 2.5 写 modular spec

新增 spec 必须按 `SPEC_TEMPLATE.md` 的字段和顺序写。关键字段：

- 元信息：`slug`、template path、可选 test path、`__modular__ = True`、pattern、stage/status。
- 5 星样本阅读摘要。
- 核心身份和相邻类别边界。
- 槽位 + 候选模块表：每个 module 有 source、`model.py:Lx-Ly`、seed=0 anchor 标记和结构特征。
- 槽位图：serial chain、parallel children、multiplicity 或 mixed。
- 每槽位 module emits：按 module 说明会 emit 的 part、visual、internal articulation 和 interface。
- 参数范围汇总：只包含公开语义参数、slot/module 选择、multiplicity 数量和必要尺寸。
- Multiplicity / Copy Logic。
- 拓扑多样性审计：必须写总合法组合数、`module_topology_diversity` 最低门槛是否可过、Stage-1 high-risk coverage seed plan 和 Stage-2 procedural seed migration target。
- Validator、Reject cases、审核记录。

不要使用单一 `primary_anchor` 作为 modular spec 的主来源。modular spec 用 per-module source table 和 seed=0 anchor module 组合表达来源。

### 2.6 完成 SPEC_ONLY

写完 N 个 spec 后停止，不得继续实现模板。

## 3. TEMPLATE_AFTER_REVIEW 工作流

### 3.1 读取审核后的 spec

检查：

- reviewer status 为 approved，或用户明确说已审核通过。
- 每个 slot candidate 都有真实 5 星样本 `model.py:Lx-Ly`。
- 每个 slot 恰好一个 seed=0 anchor module。
- slot graph 能清楚描述 module 之间如何装配。
- Multiplicity / Copy Logic 明确说明 N 的范围、采样域、复制对象、命名、placement 和 joint policy。
- 拓扑多样性审计说明 `module_topology_diversity` 是否可过，并说明 Stage-1 high-risk coverage seed domain 覆盖计划和 Stage-2 procedural seed 扩展计划。

### 3.2 回溯 module sources

根据 spec 打开每个 candidate module 的源码片段，建立映射：

- `slot.module -> module factory`。
- `slot.module -> emitted parts / visuals / internal joints`。
- `slot.module -> upstream/downstream InterfaceSpec`。
- `slot.module -> primitive choices and mesh helpers`。
- `slot.module -> source dimensions promoted to Config / ResolvedConfig`。
- `slot.module -> MatingContract / support invariant`。

核心 module 没有 source mapping 时，不得实现对应 factory。

### 3.3 决定拆分或收窄

如果一个 spec 覆盖多个不兼容主运动 spine、root coordinate、slot graph 或接口点位，优先拆分 slug。若暂不拆分，`config_from_seed` 只能采样已实现且测试覆盖的稳定子域。

### 3.4 实现 modular template

必须遵循 `MODULAR_TEMPLATE_AUTHORING.md`：

- 设置 `__modular__ = True`。
- 定义 Config / ResolvedConfig。
- `config_from_seed(0)` 返回 seed=0 anchor module 组合。
- Stage 1 的 `config_from_seed(seed>0)` 可以使用有限 coverage / curated domain 覆盖关键合法组合，尤其是容易悬空、穿模、轴错、closed pose 失真、max multiplicity、bulky module、optional moving child 和 gate/fallback 的高风险组合；必须标注为临时稳定域，且不得采样未实现或未测试组合。
- Stage 2 / final 再迁移到 slot 独立或条件独立的 unbounded procedural sampling。
- `slot_choices_for_seed(seed)` 返回稳定的 `(slot_name, module_name)` 列表。
- 每个 module factory 只消费 resolved config、palette、assets 和 `ctx.rng`。
- 每个跨 module 连接用 InterfaceSpec 和 MatingContract 表达真实接触。
- 活动件必须有真实 articulation；不动的装饰作为 parent visual。
- `run_<slug>_tests` 覆盖关键 module、接口点位、joint 语义、allow_overlap 的局部声明和 seed domain。

实现前先从 `MATURE_TEMPLATE_METHOD.md` 的 high-quality modular reference map 中选 1-3 个相近模板深读。选择依据是 slot graph、运动拓扑、接口类型和 multiplicity，而不是类别名称相似。不要一次性读全部 modular 模板；不相关参考会污染当前 spec。

### 3.5 自动调参闭环

每轮实现或修复后运行：

```bash
uv run articraft template sweep-pipeline <category_slug>
```

解析 JSON 中的 `repair_summary`、`failure_clusters`、`coverage_gates`、`escalation`。优先修最大 failure cluster；不要逐 seed 打补丁。

机械初步完成条件：

```text
sweep-pipeline verdict=pass
```

通过后按根协议渲染 preview / viewer 目检；若类别身份、比例、闭合姿态或运动语义有问题，继续修改并重新 sweep。

## 4. Hard Fail Rules

### SPEC_ONLY

- 没有读取目标类别全部 5 星样本。
- spec 没有使用 `SPEC_TEMPLATE.md` 的 modular schema。
- slot candidate 缺少真实 `model.py:Lx-Ly` 来源。
- slot 只有 1 个 candidate 且没有明确降级理由。
- seed=0 anchor module 未标注或每 slot 多于一个。
- slot graph 无法解释 module 如何装配。
- Multiplicity 存在但未写 N_range、sampling domain、copied object、placement、joint policy。
- 拓扑多样性审计缺失。
- 把未采用样本写进 module source 表。

### TEMPLATE_AFTER_REVIEW

- spec 未审核通过。
- 没有读取 `MODULAR_TEMPLATE_AUTHORING.md`。
- 模板没有设置 `__modular__ = True`。
- 没有实现 `slot_choices_for_seed`。
- module factory 没有改编对应 5 星源码片段。
- `config_from_seed` 采样未实现或未测试的 module 组合。
- InterfaceSpec / MatingContract 与可见几何脱节。
- sweep 失败后停止并要求用户手调。
- 一次性生成大量模板而没有逐个达到 `verdict=pass`。

## 5. 多类别节奏

- SPEC_ONLY 可以批量处理多个类别。
- TEMPLATE_AFTER_REVIEW 默认一次只实现 1 个模板。
- 只有同一大类拆分出的高度相似模板，才允许 2-3 个一组推进。
- 每个模板必须先达到 `sweep-pipeline verdict=pass` 并完成目检，再进入下一个。
