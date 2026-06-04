# Agent Entrypoint

你是 Articraft 新类别 **模块化参数化模板** 生成 agent。本目录只维护一条路线：

```text
5 星样本 -> modular spec(slot/module/point/interface) -> 人工审核 -> modular template
```

不要走非模块化部件清单 schema。新类别模板必须围绕 slot、candidate module、接口点位、module factory、seed=0 anchor module 和 `module_topology_diversity` 设计。

启动后必须先读本文件，再读 `agent_workflow.md` 和 `SPEC_TEMPLATE.md`。进入模板实现阶段前还必须读仓库根目录的 `MODULAR_TEMPLATE_AUTHORING.md`、`TEMPLATE_AUTHORING_AGENT.md`、`TEMPLATE_DESIGN_RULES.md`，以及本目录的 `MATURE_TEMPLATE_METHOD.md`。

## 核心边界

- `SPEC_TEMPLATE.md` 是唯一 spec schema。
- `SPEC_EXAMPLE_INDEX.md` 定义 spec 示例读取边界：新 spec 只能参考 `specs_modular_v1/` 的 schema；`specs_modular_transitional/` 只可参考结构思想；`specs_legacy_reference_only/` 和 `specs_blocked_insufficient_sources/` 禁止作为 schema 来源。
- `MODULAR_TEMPLATE_AUTHORING.md` 是模板实现的主协议。
- 5 星样本决定每个 slot 的 candidate module 来源、seed=0 anchor module、点位/接口、part tree、joint 拓扑和 primitive 复杂度。
- 旧 11 个 gold-standard 模板和已通过 sweep 的新模板只能作为 SDK 写法、约束设计、seed domain、sweep 修复经验参考，不能替代 spec 中的 module source。
- 模块化模板设置 `__modular__ = True`，用 `module_topology_diversity` 验收真实 slot/module 拓扑多样性。
- Seed domain 分两阶段管理。Stage 1 当前目标是先做出高质量模板，允许有限 `coverage_seed_domain` / curated seeds 覆盖关键组合并稳定 sweep；但 spec 必须明确它不是最终资产生成域。Stage 2 在所有 Stage-1 模板完成后，再统一升级为 unbounded deterministic procedural sampling；最终态不得用小型 curated / modulo 组合表无限轮换来冒充随机多样性。
- Stage 1 coverage seeds 必须优先覆盖最容易出错的组合：接口复杂、bulky module、max multiplicity、可选 moving child、互斥/降级 gate、长链/多子件装配，以及容易出现悬空、穿模、joint 轴错、closed pose 不合理或支撑路径断裂的组合。先收敛这些风险，Stage 2 扩展到更大 seed domain 时成功率才不会太低。

## 默认模式：SPEC_ONLY

当用户给出 N 个 Articraft 类别时，默认只执行 Spec 阶段。

### SPEC_ONLY 允许做

- 读取 `agent_workflow.md`、`SPEC_TEMPLATE.md`、`SPEC_EXAMPLE_INDEX.md`，以及 `specs_modular_v1/*.md` 中的 modular spec 示例。
- 枚举并读取 Articraft-10K 中目标类别的全部 5 星样本；不得抽样、不得只读部分样本。
- 对每个 5 星样本都读取 `model.py`、`revision.json`、`record.json`、prompt 和 category metadata。
- 为每个目标类别写一个 `articraft_template_authoring/specs_modular_v1/<category_slug>.md`。
- 每个新增 spec 必须包含 slot graph、slot/module candidate table、per-module `model.py:Lx-Ly` 来源、seed=0 anchor module、接口点位说明、Multiplicity / Copy Logic、拓扑多样性审计和 validator。

### SPEC_ONLY 禁止做

- 禁止写 `agent/templates/<category_slug>.py`。
- 禁止写 `tests/agent/test_<category_slug>_template.py`。
- 禁止修改 registry 或 CLI。
- 禁止根据未审核 spec 直接开始实现模板。
- 禁止把已阅读但未采用的 5 星样本塞进 module source 表。
- 禁止用连续尺寸参数代替真实拓扑差异；有结构差异时必须表现为不同 module、slot-level multiplicity 或明确的 module-local variant。

### SPEC_ONLY 完成条件

为用户给出的 N 个类别全部写完 modular spec 后，必须停止，并输出：

```text
已完成 N 个 modular spec，等待人工审核。未进入模板实现阶段。
```

## 审核后模式：TEMPLATE_AFTER_REVIEW

只有当用户明确说“spec 已审核，通过，继续写模板”或同等意思时，才进入本模式。

### TEMPLATE_AFTER_REVIEW 必须参考

按优先级读取：

1. 审核后的 `specs_modular_v1/<category_slug>.md`。
2. spec 中每个 module candidate 的 5 星样本 `model.py:Lx-Ly` 来源。
3. `MODULAR_TEMPLATE_AUTHORING.md`，用于 slot/module/InterfaceSpec/ModuleBuild/assemble/`__modular__`/`module_topology_diversity`。
4. `MATURE_TEMPLATE_METHOD.md`，用于 modular 成熟度、空间约束、joint 语义、seed domain、`resolve_config` 和自动调参。
5. `TEMPLATE_AUTHORING_AGENT.md` 和 `TEMPLATE_DESIGN_RULES.md`，用于 sweep loop、物理支撑、MatingContract 和停止条件。
6. 旧 11 个 gold-standard 模板和已通过 sweep 的 modular 模板都可参考，但分工不同：优先从 `MATURE_TEMPLATE_METHOD.md` 的 high-quality modular reference map 选择 1-3 个相近 modular 模板深读；旧 11 个主要作为成熟约束、SDK 写法、validator 和 sweep 修复经验参考。

### TEMPLATE_AFTER_REVIEW 工作顺序

对每个类别依次执行：

1. 读取审核后的 modular spec，确认 `reviewer status = approved` 或用户明确确认通过。
2. 回溯每个 slot candidate 的 `model.py:Lx-Ly`，建立 `slot.module -> source -> module factory / interface / internal joints` 的映射。
3. 确认 slot count、candidate count、slot graph、Multiplicity、seed=0 anchor module 组合、Stage-1 high-risk coverage seed 计划和 Stage-2 procedural seed 扩展计划足以表达目标类别。
4. 判断是否需要拆分 slug 或收窄 seed domain；若主运动 spine、接口点位或 slot graph 不兼容，不要硬塞进一个模板。
5. 从 high-quality modular reference map 中选 1-3 个最接近当前 slot graph / 运动拓扑的模板深读，只学习 modular 组织、InterfaceSpec、MatingContract、seed domain 和 sweep 修复经验。
6. 按 `MODULAR_TEMPLATE_AUTHORING.md` 实现 `__modular__ = True`、`slot_choices_for_seed`、module factories、InterfaceSpec、MatingContract 和 `run_<slug>_tests`。
7. `config_from_seed(0)` 必须选择每个 slot 的 anchor module。Stage 1 允许 `seed>0` 使用有限 coverage / curated domain 来覆盖已实现、已测试、可装配的关键 module 组合，尤其是高风险装配组合；必须在 spec 和代码注释中标注为 coverage seed domain，不得宣称是最终无限生成逻辑。Stage 2 再把主体 seed 逻辑迁移为 slot 独立/条件独立随机。
8. 运行并重复修复：

```bash
uv run articraft template sweep-pipeline <category_slug>
```

唯一机械初步完成规则：

```text
sweep-pipeline verdict=pass
```

达到机械通过后，按根协议进行 preview / viewer 目检；如果发现类别身份、比例、闭合姿态或运动语义问题，继续修改并重新 sweep。

### TEMPLATE_AFTER_REVIEW 禁止做

- 禁止忽略审核后的 modular spec。
- 禁止用单一 `primary_anchor` 替代 per-module source table。
- 禁止实现非模块化模板作为新类别默认路线。
- 禁止只写连续 enum/尺寸变化而没有真实 module 拓扑变化。
- 禁止 module factory 脱离其 5 星来源，凭空发明 part tree、joint 拓扑或 primitive。
- 禁止没有 InterfaceSpec / MatingContract 的悬空点位。
- 禁止让 `config_from_seed` 采样尚未实现或未测试的 module 组合。
- 禁止把 Stage-1 `coverage_seed_domain` 当成最终 dataset-scale seed domain。若使用 curated / modulo 表，必须标注为 Stage 1 临时稳定域，并写明 Stage 2 扩展计划。
- 禁止 sweep 失败后把调参负担交给用户。

## 推荐用户指令

### 第一阶段：只写 modular spec

```text
请先阅读 articraft_template_authoring/AGENT_ENTRYPOINT.md，并严格进入 SPEC_ONLY 模式。

本次处理的 Articraft 类别如下：
1. <category_a>
2. <category_b>

Articraft-10K 数据集路径是：
<dataset_root>

要求：
- 必须枚举并完整阅读每个类别的全部 5 星样本。
- 每个 5 星样本都要读 model.py / revision.json / record.json。
- 只生成 articraft_template_authoring/specs_modular_v1/<category_slug>.md。
- spec 必须按 SPEC_TEMPLATE.md 的 modular slot/module schema 写。
- 每个 slot candidate 必须有真实 5 星样本 model.py:Lx-Ly 来源。
- 每个 slot 标出 seed=0 anchor module。
- 必须写 slot graph、Multiplicity / Copy Logic、接口点位、拓扑多样性审计、Stage-1 high-risk coverage seed 计划和 Stage-2 procedural seed 扩展计划。
- 写完 spec 后停止，等待我审核，不要写任何模板代码。
```

### 第二阶段：审核后写 modular template

```text
我已经审核并修改完这些 spec。
请进入 TEMPLATE_AFTER_REVIEW 模式。

要求：
- 基于审核后的 modular spec 和每个 slot/module 的 5 星样本 model.py 来源片段实现模板。
- 必须先读 MODULAR_TEMPLATE_AUTHORING.md、TEMPLATE_AUTHORING_AGENT.md、TEMPLATE_DESIGN_RULES.md 和 MATURE_TEMPLATE_METHOD.md。
- 模板必须设置 __modular__ = True，并实现 slot_choices_for_seed(seed)。
- seed=0 必须选择 spec 标注的 anchor module 组合。
- 当前阶段允许 seed>0 先使用有限 coverage seed domain 来稳定关键组合；必须标注为 Stage 1，不得当作最终无限生成逻辑。
- 必须实现 InterfaceSpec / MatingContract / module factories / run_<slug>_tests。
- 必须执行 sweep-pipeline 闭环直到 verdict=pass。
- 通过后按根协议做 preview / viewer 目检；若发现问题，继续修并重新 sweep。
```
