# Modular Spec Review Template

用于人工审核 `articraft_template_authoring/specs_modular_v1/<category_slug>.md`。

## Review Target

| 项 | 值 |
|---|---|
| category_slug | <category_slug> |
| spec path | articraft_template_authoring/specs_modular_v1/<category_slug>.md |
| reviewer status | pending / approved / rejected |

## 必查项

- [ ] agent 声明已枚举并完整读取该类别全部 5 星样本的 `model.py / revision.json / record.json`。
- [ ] spec 使用 `SPEC_TEMPLATE.md` 的 modular schema，且 `__modular__ = True`。
- [ ] 核心身份清楚，能区分相邻类别。
- [ ] slot count 合理：每个 slot 都代表真实结构/功能层，且能通过接口点位与相邻 slot 装配。
- [ ] 每个 slot 至少 2 个结构不同的 candidate module；若少于目标 3 个，有基于 5 星样本池的理由。
- [ ] 每个 candidate module 都有真实 5 星样本 `model.py:Lx-Ly` 来源。
- [ ] Candidate module 之间的差异是 part tree、joint topology、chain depth、primitive 或复制逻辑差异，不只是尺寸、颜色或装饰差异。
- [ ] Slot graph 清楚说明 serial / parallel / multiplicity / mixed 装配关系。
- [ ] 接口点位明确：共同 parent、mating face、pivot、rail、socket、axis、contact plane 或 symmetry plane。
- [ ] 跨 module joint 的 type / axis / range / parent-child 语义明确。
- [ ] Multiplicity / Copy Logic 说明 N_range、sampling domain、copied object、naming、placement、joint policy 和 source/gating。
- [ ] 参数表只暴露语义参数、slot/module 选择、必要尺寸和 multiplicity 数量；没有把未实现拓扑塞进 enum。
- [ ] 拓扑多样性审计说明组合数，以及 `module_topology_diversity` 是否预计可过。
- [ ] Procedural Sampling / Sweep Plan 说明 deterministic procedural sampling 如何选择 slot/module。
- [ ] Compatibility matrix / gating 清楚说明哪些 module 组合合法、互斥、降级或拒绝。
- [ ] Controlled local parameterization 已写明关键连续 scale、范围、clamp / derived constraints，以及不会破坏接口、clearance、joint origin 或类别 multiplicity。
- [ ] 局部尺寸扰动只是辅助比例/细节多样性；spec 没有用连续尺寸随机替代真实 slot/module/multiplicity 拓扑差异。
- [ ] 可选 regression overrides 有明确失败回归或审核理由；没有把小型 curated / modulo 表作为主 seed domain。
- [ ] Random sweep seed 范围和 viewer 目检重点已写明，并覆盖 `module_topology_diversity` 预期。
- [ ] Validator 能转成模板内 `run_<slug>_tests` 或 sweep 可检查项。
- [ ] Reject cases 覆盖漂浮、穿模、接口错位、joint 方向错误、类别身份丢失、module 组合非法等失败模式。
- [ ] spec 没有使用单一 `primary_anchor` 替代 per-module source table。
- [ ] spec 没有把已读但未采用的样本写入 module source 表。

## 审核结论

```text
approved / rejected
```

## 修改意见

```text
...
```

## Template 阶段提醒

审核通过后，agent 必须进入 modular template 实现：读取 `MODULAR_TEMPLATE_AUTHORING.md`、`MATURE_TEMPLATE_METHOD.md`、`TEMPLATE_AUTHORING_AGENT.md` 和 `TEMPLATE_DESIGN_RULES.md`；实现 `__modular__ = True`、`slot_choices_for_seed`、procedural `config_from_seed`、module factories、InterfaceSpec、MatingContract 和 `run_<slug>_tests`；运行 `uv run articraft template sweep-pipeline <slug>` 直到 `verdict=pass`，再做 preview / viewer 目检。
