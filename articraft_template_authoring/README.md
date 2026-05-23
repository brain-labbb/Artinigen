# Articraft Template Authoring

本目录用于把 Articraft-10K 的新类别批量转成可参数化模板。

核心边界：**旧模板 = 写法参考；新 spec = 部件来源。**

核心流程是两阶段：

1. **Spec 阶段**：给 agent N 个 Articraft 类别。agent 必须枚举并完整阅读每个类别的全部 5 星样本，但只写 N 个 `specs/<category_slug>.md`，写完停止等待人工审核。
2. **Template 阶段**：人工审核并修改 spec 后，agent 再基于审核后的 spec 和 spec 中被采纳的 5 星样本源码片段写 `agent/templates/<category_slug>.py` 和测试；已有 11 个模板代码只作为骨架、SDK 用法、palette、validator 和测试风格参考。

## 文件

- `AGENT_ENTRYPOINT.md`：启动 agent 后优先阅读的入口规则。
- `agent_workflow.md`：完整工作流、spec schema、代码实现规则、测试规则、已有模板写法参考表。
- `CATEGORY_BATCH_TEMPLATE.md`：批量类别输入模板。
- `SPEC_REVIEW_TEMPLATE.md`：人工审核 spec 的 checklist。
- `specs/*.md`：已有 11 个类别的 baseline spec，用来参考结构、参数、关节和 validator 写法。

## 放置位置

建议把本目录放在项目根目录，例如：

```text
<repo_root>/
├── articraft_template_authoring/
├── agent/templates/                 # 已有 11 个模板代码在这里
├── tests/agent/
├── cli/template.py
└── <Articraft-10K dataset root>/
```

## 审核闸门

- 默认进入 `SPEC_ONLY` 模式。
- `SPEC_ONLY` 模式下禁止创建或修改 `agent/templates/*.py`、`tests/agent/*.py`、registry。
- agent 只写 N 个 spec，然后停止。
- 只有在人工明确说“spec 已审核，通过，继续写模板”后，才能进入 `TEMPLATE_AFTER_REVIEW` 模式。

## 新增 spec 的 5 星样本阅读与源码索引

新增类别必须先枚举并读取该类别全部 5 星样本，不能抽样、不能只读部分样本。

但最终 spec **只保留被采纳为模板依据、适合复用的源码索引**：

```text
path/to/model.py:Lx-Ly
```

已阅读但未采用的 5 星样本，不写入 spec 的来源索引表，也不在 Parts / Joints / 参数表中引用。

## Template 阶段实现优先级

写新模板时不要从已有 11 个旧模板里决定部件。正确优先级是：

1. 审核后的新类别 spec。
2. spec 中被采纳并带有 `model.py:Lx-Ly` 索引的 5 星样本部件、关节、参数代码片段。
3. 已有 11 个模板的代码骨架、SDK 用法、`resolve_config` / `_build_*` 组织方式、palette、validator 和测试风格。

已有 11 个旧模板是写法与工程规范参考，不是新类别部件来源。
