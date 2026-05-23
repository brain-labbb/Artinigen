# Articraft Template Authoring

本目录用于把 Articraft-10K 的新类别批量转成可参数化模板。

核心边界：**旧 11 个模板 = 写法参考；新 spec = 部件来源。**

## 两阶段流程

1. **SPEC_ONLY**：给 agent N 个 Articraft 类别。agent 必须枚举并完整阅读每个类别的全部 5 星样本，只生成 N 个 `specs/<category_slug>.md`，写完停止等待人工审核。
2. **TEMPLATE_AFTER_REVIEW**：人工审核并修改 spec 后，agent 再基于审核后的 spec 和 spec 中被采纳的 5 星样本源码片段写 `agent/templates/<category_slug>.py` 和测试。旧 11 个模板只作为代码骨架、SDK 用法、`resolve_config` / `_build_*` 组织方式、palette、joint metadata、validator 和测试风格参考。

## 文件

- `AGENT_ENTRYPOINT.md`：启动 agent 后优先阅读的入口规则。
- `agent_workflow.md`：完整工作流、spec schema、代码实现规则、测试规则、已有模板写法参考表。
- `CATEGORY_BATCH_TEMPLATE.md`：批量类别输入模板。
- `SPEC_REVIEW_TEMPLATE.md`：人工审核 spec 的 checklist。
- `specs/*.md`：已有 11 个类别的 baseline spec，用来参考 spec 写法，不作为新类别部件来源。

## 放置位置

```text
<repo_root>/
├── articraft_template_authoring/
├── agent/templates/                 # 你已有的 11 个模板代码在这里
├── tests/agent/
├── cli/template.py
└── <Articraft-10K dataset root>/
```

## 新增 spec 的关键规则

- 必须完整读取该类别全部 5 星样本。
- 最终 spec 只保留被采纳为模板依据、适合复用的源码索引：`path/to/model.py:Lx-Ly`。
- 已阅读但未采用的 5 星样本，不写入 `Adopted Source Index`，也不在 Parts / Joints / 参数表中引用。
- 每个 spec 必须做 **部件级多样性审计（Part Diversity Audit）**。
- 不强制每个部件都有离散桶；如果某个关键部件没有观察到形态多样性，记录 `observed_variation = none`；如果存在连续尺寸参数无法表达的定性外形差异，必须显式加入 `*_shape / *_style / *_profile / *_variant / *_layout` 等参数。
