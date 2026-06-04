# Articraft Modular Template Authoring

本目录用于把 Articraft-10K 新类别转成 **模块化参数化模板**。唯一路线是：

```text
完整读取目标类别 5 星样本
-> 写 modular spec(slot / module / point / interface)
-> 人工审核
-> 实现 __modular__ 模板
-> sweep-pipeline + viewer 目检
```

本目录不维护非模块化 authoring 路线。新类别模板不要使用单一部件清单作为主设计；必须用 slot graph、candidate module、InterfaceSpec、MatingContract、seed=0 anchor module 和 `module_topology_diversity` 表达结构级变化。

## 文件

- `AGENT_ENTRYPOINT.md`：agent 启动后优先阅读的入口规则。
- `agent_workflow.md`：两阶段 modular 工作流。
- `SPEC_TEMPLATE.md`：唯一 spec schema；定义 slot/module/source/slot graph/Multiplicity/拓扑多样性字段。
- `MATURE_TEMPLATE_METHOD.md`：模块化模板成熟度补充，聚焦空间约束、joint 语义、seed domain、`resolve_config`、sweep 修复。
- `SPEC_REVIEW_TEMPLATE.md`：人工审核 modular spec 的 checklist。
- `CATEGORY_BATCH_TEMPLATE.md`：批量类别输入模板。
- `DESIGN_RULES.md`：兼容入口，指向仓库根目录的 design / sweep 协议。
- `SPEC_EXAMPLE_INDEX.md`：spec 示例分层清单；定义哪些文件可作为 schema 来源。
- `specs_modular_v1/*.md`：当前 canonical modular v1 spec 示例；新 spec 只能从这里和 `SPEC_TEMPLATE.md` 学格式。
- `specs_modular_transitional/*.md`：过渡 modular 示例；只参考结构思想，不作为 schema 来源。
- `specs_legacy_reference_only/*.md`：旧格式 / baseline 示例；禁止作为新 spec 格式来源。
- `specs_blocked_insufficient_sources/*.md`：因 5 星样本不足而阻塞的 spec 草案；禁止作为 schema 或 module source 来源。

## 两阶段流程

1. **SPEC_ONLY**：给 agent N 个类别。agent 枚举并完整读取每个类别的全部 5 星样本，只生成 N 个 modular spec，写完停止等待人工审核。
2. **TEMPLATE_AFTER_REVIEW**：人工审核 spec 后，agent 基于 spec 中每个 module candidate 的 5 星样本源码实现 `agent/templates/<slug>.py`，并按 `MODULAR_TEMPLATE_AUTHORING.md` 和 `TEMPLATE_AUTHORING_AGENT.md` 运行 sweep 闭环。

## Modular Spec 关键规则

- 每个 slot 表示一个可替换的结构/功能层，必须能与相邻 slot 通过点位或共同 parent 装配。
- 每个 candidate module 必须来自真实 5 星样本 `model.py:Lx-Ly`，并且结构上不同；只换尺寸、颜色或装饰不是新 module。
- 每个 slot 必须标出 `seed=0 anchor` module；`config_from_seed(0)` 后续要复现这个 anchor 组合。
- spec 必须包含 slot graph、每 module 的 source、接口点位、内部/跨 slot joint 语义、Multiplicity / Copy Logic、拓扑多样性审计、Validator 和 Reject cases。
- 拓扑多样性审计必须区分 Stage 1 和 Stage 2：Stage 1 允许有限 coverage seed domain 先把模板质量做稳；coverage seeds 应优先覆盖最容易出现悬空、穿模、joint 轴错、closed pose 不合理、max multiplicity 或 bulky module 接口失败的组合。Stage 2 / final 才迁移到 unbounded deterministic procedural seed domain。
- 已阅读但未采用的 5 星样本不要写入 module source 表。

## 模板阶段关键规则

- 模板必须设置 `__modular__ = True`。
- 必须实现 `slot_choices_for_seed(seed)`，供 `module_topology_diversity` gate 使用。
- 新 modular 模板不使用单一 `primary_anchor`；per-module source table 是来源 contract。
- Module factory 必须改编 spec 中对应的 5 星样本片段，不能凭空发明结构。
- InterfaceSpec 的 `anchor_local`、MatingContract、visible support path 必须能支撑真实装配，不能用隐藏小件或浮空点位糊弄。
- `config_from_seed` 只采样已实现、已测试、可通过 sweep 的 module 组合。
- 当前 Stage 1 允许 `config_from_seed(seed>0)` 使用有限 coverage / curated domain 来覆盖代表组合、高风险组合、稳定 sweep 和 viewer 目检；必须标注为临时覆盖域。
- Stage 2 / final 要求主体 seed 逻辑升级为 unbounded deterministic procedural sampling；到最终态时，不得无限轮换少数 curated / modulo 组合表来冒充随机 seed domain。
- 唯一机械初步完成规则：`uv run articraft template sweep-pipeline <slug>` 返回 `verdict=pass`。
- 机械通过后仍要按根协议 preview / viewer 目检，确认类别身份、比例、闭合姿态和运动语义。
