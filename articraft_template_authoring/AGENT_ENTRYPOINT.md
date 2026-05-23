# Agent Entrypoint

你是 Articraft 新类别模板生成 agent。启动后必须先读本文件，再读 `agent_workflow.md`。

## 核心边界

旧模板教 agent 怎么写模板；审核后的新 spec 决定新模板写什么部件。写模板时，实体部件、关节和关键参数必须优先来自新 spec 中被采纳且有 `model.py:Lx-Ly` 的 5 星样本源码片段。

## 默认模式：SPEC_ONLY

当用户给出 N 个 Articraft 类别时，默认只执行 Spec 阶段。

### SPEC_ONLY 允许做

- 读取 `agent_workflow.md`。
- 读取 `specs/*.md` 中已有 11 个 baseline spec，学习 spec 写法。
- 枚举并读取 Articraft-10K 中目标类别的全部 5 星样本；不得抽样、不得只读部分样本。
- 对每个 5 星样本都必须读取：
  - `model.py`
  - `revision.json`
  - `record.json`
  - prompt / category metadata
- 为每个目标类别写一个 `specs/<category_slug>.md`。
- 每个新增 spec 必须包含真实 `model.py:Lx-Ly` 来源索引；索引只引用被采纳为模板依据的 5 星样本代码片段。
- 每个新增 spec 必须包含 `部件多样性审计（Part Diversity Audit）`。

### SPEC_ONLY 禁止做

- 禁止写 `agent/templates/<category_slug>.py`。
- 禁止写 `tests/agent/test_<category_slug>_template.py`。
- 禁止修改 `cli/template.py` 或任何 registry。
- 禁止根据 spec 直接开始实现模板。
- 禁止把未审核 spec 当成最终 spec。
- 禁止把“已阅读但未采用”的 5 星样本路径、行号、源码索引写进最终 spec。
- 禁止用连续尺寸参数掩盖关键部件的定性外形差异。

### SPEC_ONLY 完成条件

为用户给出的 N 个类别全部写完 spec 后，必须停止，并输出：

```text
已完成 N 个 spec，等待人工审核。未进入模板实现阶段。
```

---

## 审核后模式：TEMPLATE_AFTER_REVIEW

只有当用户明确说“spec 已审核，通过，继续写模板”或同等意思时，才进入本模式。

### TEMPLATE_AFTER_REVIEW 必须参考

写每个新模板时必须同时参考四类材料，但优先级不同：

1. 已审核的 `specs/<category_slug>.md`。
2. **主实现来源**：spec 中标注并被采纳的 5 星样本 `model.py:Lx-Ly` 代码片段。关键部件、关节、参数优先从这里改编。
3. **风格与骨架参考**：现有 11 个模板代码 `agent/templates/*.py`，只用于对齐文件结构、SDK 用法、`resolve_config` / `_build_*` 组织方式、palette、joint metadata、validator 和测试风格。
4. `agent_workflow.md` 的已有模板写法参考表、编码约定、validator 规则。参考表只用于定位旧模板里的相似写法，不替代 spec 中已采纳的 5 星样本源码片段。

### TEMPLATE_AFTER_REVIEW 工作顺序

对每个类别依次执行：

1. 读取审核后的 spec。
2. 回溯 spec 中被采纳的 5 星样本 `model.py:Lx-Ly` 片段，确定关键部件、关节、参数的主实现来源。
3. 根据 `部件多样性审计` 确认哪些参数需要离散外形枚举，哪些只需要连续尺寸；如果未观察到部件多样性，按 `observed_variation = none` 处理，不强行加 enum。
4. 从已有 11 个模板中选择 1–3 个最近代码骨架，只学习文件结构、SDK 用法、`resolve_config`、`_build_*`、palette、validator。
5. 将被采纳的 5 星样本部件代码改编为新的 `agent/templates/<category_slug>.py`，并用已有模板风格包装。
6. 写 `tests/agent/test_<category_slug>_template.py`。
7. 更新 registry。
8. 至少运行：

```bash
uv run articraft template <category_slug> --seed 0
uv run articraft template <category_slug> --seed 1
uv run articraft template <category_slug> --seed 2
uv run pytest tests/agent/test_<category_slug>_template.py
```

### TEMPLATE_AFTER_REVIEW 禁止做

- 禁止忽略审核后的 spec。
- 禁止只靠 5 星样本代码直接拼模板。
- 禁止用已有 11 个旧模板的代码片段替代 spec 中已采纳、有来源索引的 5 星样本部件代码。
- 已有 11 个旧模板只作为代码骨架、SDK 用法、测试风格和相似写法参考。
- 禁止只实现固定形态；关键尺寸、计数、关节参数必须暴露为函数参数并有默认值。
- 禁止在 `_build_*` 中随机关键尺寸；关键尺寸必须在 `resolve_config` 中确定。
- 禁止忽略 `Part Diversity Audit` 中要求的 `*_shape / *_style / *_profile / *_variant / *_layout` 参数；也禁止在没有观察到多样性时编造 enum。

---

## 推荐用户指令

### 第一阶段：只写 spec

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
- 只生成 articraft_template_authoring/specs/<category_slug>.md。
- spec 中只保留被采纳为模板依据的 model.py:Lx-Ly 来源索引。
- 已阅读但未采用的样本不要写入来源索引。
- 必须为每个 spec 写 Part Diversity Audit。
- 写完 spec 后停止，等待我审核，不要写任何模板代码。
```

### 第二阶段：审核后写模板

```text
我已经审核并修改完这些 spec。
请进入 TEMPLATE_AFTER_REVIEW 模式。

要求：
- 基于审核后的 specs/<category_slug>.md 和 spec 中被采纳的 5 星样本 model.py 来源片段继续写 agent/templates/<category_slug>.py 和测试。
- 真正写入模板的部件、关节、参数，必须来自 spec 中被采纳的 5 星样本 model.py:Lx-Ly 片段。
- 现有 11 个模板代码只作为代码骨架、SDK 用法、resolve_config / _build_* 组织方式、palette、joint metadata、validator 和测试风格参考。
- 不要从旧 11 个模板里决定新类别的部件来源。
- 必须按照 Part Diversity Audit 实现部件级多样性。
```
