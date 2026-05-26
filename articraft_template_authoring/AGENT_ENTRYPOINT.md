# Agent Entrypoint

你是 Articraft 新类别模板生成 agent。启动后必须先读本文件，再读 `agent_workflow.md`；进入模板实现阶段前还必须读 `MATURE_TEMPLATE_METHOD.md`。

## 核心边界

旧 11 个 gold-standard 模板教 agent 怎么写成熟模板；新造 20+ 模板可作为二级经验参考；审核后的新 spec 决定新模板写什么部件；`MATURE_TEMPLATE_METHOD.md` 决定如何把五星样本代码参数化到旧 11 个模板的成熟度。写模板时，实体部件、关节和关键参数必须优先来自新 spec 中被采纳且有 `model.py:Lx-Ly` 的 5 星样本源码片段。

## 默认模式：SPEC_ONLY

当用户给出 N 个 Articraft 类别时，默认只执行 Spec 阶段。

### SPEC_ONLY 允许做

- 读取 `agent_workflow.md`。
- 读取 `specs/*.md` 中已有 baseline / reviewed spec，学习 spec 写法。
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

写每个新模板时必须同时参考六类材料，但优先级不同：

1. 已审核的 `specs/<category_slug>.md`。
2. **主实现来源**：spec 中标注并被采纳的 5 星样本 `model.py:Lx-Ly` 代码片段。关键部件、关节、参数优先从这里改编。
3. **成熟度方法**：`MATURE_TEMPLATE_METHOD.md`，用于决定如何拆分/收窄机构族、如何把五星样本常量提升为 `Config` / `ResolvedConfig` 参数、如何写 seed domain、空间约束、joint 语义、validator、QC 和自动调参闭环。
4. **风格与骨架参考**：旧 11 个 gold-standard 模板代码，只用于对齐文件结构、SDK 用法、`resolve_config` / `_build_*` 组织方式、palette、joint metadata、validator 和测试风格。
5. **二级经验参考**：新造的 20+ 模板可以参考其拆分经验、seed domain、已修 QC/预览问题、相近 helper 和测试断言，但不能定义成熟度下限，也不能替代 5 星样本源码来源。
6. `agent_workflow.md` 的已有模板写法参考表、编码约定、validator 规则。参考表只用于定位旧 11 个 gold-standard 模板和可用二级参考里的相似写法，不替代 spec 中已采纳的 5 星样本源码片段。

### TEMPLATE_AFTER_REVIEW 工作顺序

对每个类别依次执行：

1. 读取审核后的 spec。
2. 回溯 spec 中被采纳的 5 星样本 `model.py:Lx-Ly` 片段，确定关键部件、关节、参数的主实现来源，并建立 adopted source 到模板 helper / part / joint 的改编映射。
3. 根据 `部件多样性审计` 确认哪些参数需要离散外形枚举，哪些只需要连续尺寸；如果未观察到部件多样性，按 `observed_variation = none` 处理，不强行加 enum。
4. 读取 `MATURE_TEMPLATE_METHOD.md`，先判断是否需要拆分/收窄到稳定子族；如果需要拆分，先提出拆分 slug，不要把互斥机构硬塞进一个模板。
5. 从旧 11 个 gold-standard 模板中选择 1–3 个最近代码骨架，只学习文件结构、SDK 用法、`resolve_config`、`_build_*`、palette、validator。
6. 可再选择 0–2 个新造且已调过/已验收的相近模板作为二级参考，只学习拆分经验、seed domain、测试和已修问题。
7. 将被采纳的 5 星样本部件代码改编为新的 `agent/templates/<category_slug>.py`，并用 gold-standard 模板风格包装。
8. 写 `tests/agent/test_<category_slug>_template.py`。
9. 更新 registry。
10. 进入自动调参闭环：测试、QC、预览、视觉自检、修复，直到达到验收线。
11. 至少运行：

```bash
uv run pytest tests/agent/test_<category_slug>_template.py
test "$(wc -l < agent/templates/<category_slug>.py)" -ge 1000
uv run python scripts/check_template_qc.py --slugs <category_slug> --seeds 0-2
uv run python scripts/render_template_previews.py --slugs <category_slug> --seeds 0-2
```

如果需要生成 record，再运行：

```bash
uv run articraft template batch <category_slug> --seeds 0-2
```

### TEMPLATE_AFTER_REVIEW 执行节奏

- 默认一次只实现 1 个类别。
- 若用户给出 20/30 个类别，允许批量完成 spec，但模板实现必须串行推进。
- 只有高度相似、同一大类拆分出的子模板，才允许 2-3 个一组实现。
- 每个模板必须完成测试、QC、预览或人工确认后，才能进入下一个模板。
- 预览不只是生成文件，agent 必须自己检查图像并修复明显问题。
- 禁止一口气生成大量模板后把手调负担转给用户。

### TEMPLATE_AFTER_REVIEW 禁止做

- 禁止忽略审核后的 spec。
- 禁止只靠 5 星样本代码直接拼模板。
- 禁止只是“看过”五星样本却没有把对应源码片段实际改编到模板 helper / part / joint 中。
- 禁止用旧 11 个模板的代码片段替代 spec 中已采纳、有来源索引的 5 星样本部件代码。
- 旧 11 个模板只作为代码骨架、SDK 用法、测试风格和相似写法参考。
- 禁止把新 20+ 模板当成成熟度下限；它们只能作为二级经验参考。
- 禁止用新模板中的未验收实现掩盖当前模板的 QC、预览或类别身份问题。
- 禁止忽略 `MATURE_TEMPLATE_METHOD.md` 中的拆分/收窄、`config_from_seed`、`resolve_config`、builder 和 QC 规则。
- 禁止把失败的测试、QC、预览问题或 seed domain 问题留给用户手调。
- 禁止提交低于 1000 行的模板；1000 行是下限，不是上限。
- 禁止子件尺寸、origin、orientation 或 joint range 独立随机导致悬空 / 穿模；必须先识别类别拓扑和主约束基准，再选择匹配的约束策略派生几何与运动。抽屉柜 envelope-first 只是一个例子，不能机械套到所有类别。
- 禁止未理解部件语义就写 joint；必须基于真实运动语义确定 type、axis、origin、range。
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
- 必须先读 MATURE_TEMPLATE_METHOD.md，并按其中的拆分/收窄、参数化、resolve_config、builder、测试成熟度规则执行。
- 必须执行自动调参闭环：测试、QC、渲染预览、检查图像、修复、重复，不能把手调留给我。
- 必须真正改编 spec 中采用的 5 星样本源码片段，建立 source id 到模板 helper / part / joint 的对应关系。
- 模板文件必须至少 1000 行；1000 是最低保险线，不是上限。
- 必须用与类别拓扑匹配的参数化约束防悬空 / 穿模：抽屉柜用 envelope-first，滑轨用 rail，铰链件用 hinge line，伸缩件用 socket/overlap，旋转件用 hub/axis，支撑件用 contact plane；并用部件语义校准 joint 运动。
- 旧 11 个 gold-standard 模板代码只作为代码骨架、SDK 用法、resolve_config / _build_* 组织方式、palette、joint metadata、validator 和测试风格参考。
- 新造的 20+ 模板可以作为二级参考，用来学习相近类别拆分、seed domain、测试和已修问题，但不能降低旧 11 个模板定义的成熟度标准。
- 如果本次有多个类别，模板实现阶段必须逐个或最多 2-3 个同族模板一组推进，不能一次性生成 20/30 个模板。
- 不要从已有模板里决定新类别的部件来源。
- 必须按照 Part Diversity Audit 实现部件级多样性。
```
