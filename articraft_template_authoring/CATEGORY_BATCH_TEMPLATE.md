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
- 每个 spec 必须包含 `部件多样性审计（Part Diversity Audit）`。
- 对每个关键部件判断：是否观察到多样性；若没有，记录 `observed_variation = none`；若连续参数不够，必须加入 `*_shape / *_style / *_profile / *_variant / *_layout`。
- 写完所有 spec 后停止，等待人工审核。
- 审核前禁止写 `agent/templates/*.py`、测试、registry。

## 后续 Template 阶段原则

审核通过后写模板时，优先改编 spec 中被采纳并带 `model.py:Lx-Ly` 的 5 星样本部件代码；旧 11 个 gold-standard 模板作为骨架、SDK 用法、validator 和测试风格参考，新 20+ 模板可作为拆分、seed domain、QC/预览修复和测试断言的二级参考；并必须按 `MATURE_TEMPLATE_METHOD.md` 做拆分/收窄、参数化、拓扑匹配的空间约束、joint 语义、seed domain、`resolve_config`、QC 和自动调参闭环。抽屉柜 envelope-first 只是一个约束例子，不是通用公式；滑轨、铰链、伸缩、旋转、支撑、对称和 linkage 结构都要用对应约束链。模板文件至少 1000 行，且 1000 是下限不是上限。模板实现必须逐个或最多 2-3 个同族模板一组推进，不能一次性生成大量未验收模板，也不能把测试、QC、预览后的明显问题交给用户手调。
