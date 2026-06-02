# Agent Entrypoint

你是 Articraft **模块化（modular）模板**生成 agent。Articraft 的所有
新模板都通过这套流程产出：先读 5 星样本写 spec，人工审核后用
slot/module/assembler 架构实现一个能覆盖多种拓扑的模板。

本文件既是 agent 的启动入口，也是人类浏览本目录的索引。

## 两阶段流程

1. **SPEC_ONLY**：给 agent N 个 Articraft 类别。agent 枚举并完整阅读
   每个类别的全部 5 星样本，写 `specs/<category_slug>.md`（含模块表 +
   槽位图 + 拓扑多样性审计），停下等人工审核。
2. **TEMPLATE_AFTER_REVIEW**：人工审核 spec 后，agent 按 spec 写
   `agent/templates/<category_slug>.py` + 测试，自检
   `compile-sweep --quality-profile final --seeds 0-49` + 10 seed batch 推 viewer。

## 启动后依序读

1. 本文件
2. [`agent_workflow.md`](agent_workflow.md) — 完整两阶段工作流（含批量类别输入格式）
3. 进入 SPEC 阶段前：[`SPEC_TEMPLATE.md`](SPEC_TEMPLATE.md) — spec 字段规范
4. 进入实现阶段前还要读：
   - [`MATURE_METHOD.md`](MATURE_METHOD.md) — 实现成熟度标准
   - [`DESIGN_RULES.md`](DESIGN_RULES.md) — 3 条硬规则
   - 项目根 [`../MODULAR_TEMPLATE_AUTHORING.md`](../MODULAR_TEMPLATE_AUTHORING.md)
     — 架构 + 设计契约 + 实现 pattern

人工 reviewer 还会用 [`SPEC_REVIEW_TEMPLATE.md`](SPEC_REVIEW_TEMPLATE.md)
来检查 agent 产出的 spec。

## 3 个 reference 模板（实现阶段骨架来源）

实现阶段挑最接近目标拓扑的那个作骨架来源：

- [`../agent/templates/retractable_utility_knife.py`](../agent/templates/retractable_utility_knife.py)
  — linear chain，3 槽位 × 2 候选 = 8 拓扑
- [`../agent/templates/monitor_mount.py`](../agent/templates/monitor_mount.py)
  — chain + multiplicity（1-8 节臂），2 × 8 × 2 = 32 拓扑
- [`../agent/templates/dj_equipment.py`](../agent/templates/dj_equipment.py)
  — parallel children（deck / controls 并联 parent 到 chassis），8 拓扑

它们是**结构骨架、helper 写法、interface 约束、allow_overlap 风格、测试
断言**的来源。新 spec 决定"写什么槽位 / 选什么候选模块 / 每个候选源自
哪个 5 星样本"。[`MATURE_METHOD.md`](MATURE_METHOD.md) 决定"如何把
模块化结构做到 reference 模板的成熟度（含 disconnected_islands、mating
contract、captured-pin 重叠声明等关键质量标准）"。

## 默认模式：SPEC_ONLY

用户给出 N 个类别时，默认只跑 Spec 阶段。

### SPEC_ONLY 允许做

- 读取 `agent_workflow.md`、`SPEC_TEMPLATE.md`、`SPEC_REVIEW_TEMPLATE.md`
- 读取 `specs/*.md` 中已有 spec，学习写法
- 枚举并读取目标类别全部 5 星样本（**不得抽样**）。每个样本必须读
  `model.py / revision.json / record.json / prompt`
- 为每个目标类别写一个 `specs/<category_slug>.md`（按 `SPEC_TEMPLATE.md`）
- 每个 spec 必须包含：
  - **模块表**：列出每个槽位的候选模块 + 各自的 5 星样本来源（带
    `model.py:Lx-Ly` 引用），**至少 3 个候选/槽位**（不够 3 个退到 2）
  - **槽位图**：chain / parallel / multiplicity / 混合
  - **anchor 标注**：每个槽位标 seed=0 该选哪个模块
  - **Multiplicity / Copy Logic**：每个 spec 必填；这里只指模板级复制数量逻辑。
    有同构 visual/part/joint 复制时必须写 `N_min..N_max`、离散集合或固定 N 个
    同构复制件；固定单件 named slot 不要写成 `*_count=fixed 1`
  - **拓扑多样性审计**：模块表算下来组合数是否 ≥8，是否能挤过
    `module_topology_diversity` 门控（≥5）

### SPEC_ONLY 禁止做

- 禁止写 `agent/templates/<category_slug>.py`
- 禁止写 `tests/agent/test_<category_slug>_template.py`
- 禁止改 `agent/templates/_modular.py`
- 禁止改 sweep / gate 代码
- 禁止改 root docs（`DESIGN_RULES.md` 等）

## TEMPLATE_AFTER_REVIEW（人工审核后）

人工 review 完 spec、状态改成 `approved` 后，agent 按 spec 进入实现阶段。

### 允许做

- 读取 `MATURE_METHOD.md` 和根 `MODULAR_TEMPLATE_AUTHORING.md`
- 创建 `agent/templates/<category_slug>.py`（modular 拓扑展开后自然 2000+ 行，无硬性下限）
- 在 `agent/templates/` registry 注册新模板（如果项目结构需要）
- 跑 `compile-sweep --quality-profile final --seeds 0-49`，必须
  `verdict=pass`、`pass_rate == 1.0`、`module_topology_diversity` ≥ 5，
  且 `quality_summary.failed_gates == {}`（**这是唯一验收门**，不靠 pytest）
- （可选）创建 `tests/agent/test_<category_slug>_template.py` 作为结构回归网；
  它默认被 pytest 排除（`template_asset` marker），非验收必需，仅在模板定稿
  需长期锁结构时写，且只覆盖 sweep 抽样覆盖不到的两项（穷举 build + anchor）
- 跑 `template batch --seeds 0-9 --agent claude-code`，把 10 个 seed 推到
  viewer 自检视觉
- 自闭环修 disconnected_islands、mating gap、overlap、单元测试错误

### 禁止做

- 禁止修改 spec（spec 在审核阶段已锁定；如要改回到 SPEC_ONLY 重新走）
- 禁止改 `_modular.py` 抽象层
- 禁止改 sweep / gate 代码
- 禁止改其他模板（除非用户明确授权）
- 禁止把"视觉看着没问题"当成完工标准；必须 sweep `verdict=pass` 且
  自己过一遍 10 seed viewer

## 完工标准

- pytest 全过
- `uv run articraft template compile-sweep <slug> --quality-profile final --seeds 0-49`
  输出 `verdict=pass`，`pass_rate == 1.0`，`quality_summary.failed_gates == {}`，
  `module_topology_diversity` ≥ 5 distinct
- `template batch --seeds 0-9 --agent claude-code` 10/10 compile 成功
- 自己 viewer 过一遍 10 个 seed，没有明显几何错误

## 一句话目标

让一个 agent 从"给定 N 个新类别"到"产出审核通过的 spec → 实现合格的
模板 → 50 seed final sweep pass + viewer 自检通过"全程自闭环，**无需人工救火
几何/连通/重叠问题**。

## 本目录文件

- `AGENT_ENTRYPOINT.md` — 本文件
- `agent_workflow.md` — 完整两阶段工作流（含批量类别输入格式）
- `SPEC_TEMPLATE.md` — spec 字段规范
- `SPEC_REVIEW_TEMPLATE.md` — 人工审核 checklist
- `MATURE_METHOD.md` — 实现成熟度标准
- `DESIGN_RULES.md` — 硬规则（compile-sweep 门控会强制）
- `specs/` — 已写好的 spec（审核状态写在 frontmatter）
