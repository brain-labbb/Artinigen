# Category Batch Input

把需要处理的 Articraft 类别填在这里，然后让 agent 进入 `SPEC_ONLY` 模式。SPEC_ONLY 只写 modular spec，不写模板代码。

## Mode

SPEC_ONLY

## Categories

| index | category_slug | notes |
|---:|---|---|
| 1 | <category_a> |  |
| 2 | <category_b> |  |
| 3 | <category_c> |  |

## Required Agent Behavior

- 只写 `articraft_template_authoring/specs/<category_slug>.md`。
- 每个新增 spec 必须按 `SPEC_TEMPLATE.md` 的 modular slot/module schema 写。
- 必须枚举并读取该类别全部 5 星样本；不得抽样、不得只读部分样本。
- 每个 slot candidate 必须有真实 5 星样本 `model.py:Lx-Ly` 来源。
- 每个 slot 必须标出恰好一个 `seed=0 anchor` module。
- 必须写 slot graph、接口点位、Multiplicity / Copy Logic、拓扑多样性审计、Validator 和 Reject cases。
- 已阅读但未采用的 5 星样本，不写入 module source 表。
- 写完所有 spec 后停止，等待人工审核。
- 审核前禁止写 `agent/templates/*.py`、测试、registry。

## Template 阶段原则

审核通过后写模板时，必须走 modular route：读 `MODULAR_TEMPLATE_AUTHORING.md`、`MATURE_TEMPLATE_METHOD.md`、`TEMPLATE_AUTHORING_AGENT.md` 和 `TEMPLATE_DESIGN_RULES.md`；实现 `__modular__ = True`、`slot_choices_for_seed`、module factories、InterfaceSpec、MatingContract、seed=0 anchor module 组合和模板内 tests；运行 `uv run articraft template sweep-pipeline <slug>` 直到 `verdict=pass`。通过后做 preview / viewer 目检；发现类别身份、比例、闭合姿态或运动语义问题时继续修复并重新 sweep。
