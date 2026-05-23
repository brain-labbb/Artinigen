# Category Batch Input

把需要处理的 Articraft 类别填在这里，然后让 agent 进入 `SPEC_ONLY` 模式。

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
- 每个新增 spec 必须枚举并读取该类别全部 5 星样本；不得抽样、不得只读部分样本。
- 最终 spec 只写被采纳为模板依据的 5 星样本 `model.py:Lx-Ly` 来源索引。
- 已阅读但未采用的 5 星样本，不写入 spec 的来源索引表，也不在 Parts / Joints / 参数表中引用。
- 写完所有 spec 后停止，等待人工审核。
- 审核前禁止写 `agent/templates/*.py`、测试、registry。

## 后续 Template 阶段原则

审核通过后写模板时，优先改编 spec 中被采纳并带 `model.py:Lx-Ly` 的 5 星样本部件代码；已有 11 个模板只作为骨架、SDK 用法、validator 和测试风格参考。
