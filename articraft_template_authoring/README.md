# Articraft Template Authoring

本目录用于把 Articraft-10K 的新类别批量转成可参数化模板。

核心边界：**旧 11 个 gold-standard 模板 = 成熟度标准；新造 20+ 模板 = 二级经验参考；新 spec = 部件来源。**

## 两阶段流程

1. **SPEC_ONLY**：给 agent N 个 Articraft 类别。agent 必须枚举并完整阅读每个类别的全部 5 星样本，只生成 N 个 `specs/<category_slug>.md`，写完停止等待人工审核。
2. **TEMPLATE_AFTER_REVIEW**：人工审核并修改 spec 后，agent 再基于审核后的 spec 和 spec 中被采纳的 5 星样本源码片段写 `agent/templates/<category_slug>.py` 和测试。旧 11 个 gold-standard 模板作为代码骨架、SDK 用法、`resolve_config` / `_build_*` 组织方式、palette、joint metadata、validator 和测试风格参考；新造 20+ 模板可作为拆分、seed domain、QC/预览修复和测试断言的二级参考；`MATURE_TEMPLATE_METHOD.md` 约束如何拆分/收窄、如何把五星样本参数化到旧 11 个模板的成熟度。

## 文件

- `AGENT_ENTRYPOINT.md`：启动 agent 后优先阅读的入口规则。
- `agent_workflow.md`：完整工作流、spec schema、代码实现规则、测试规则、已有模板写法参考表。
- `MATURE_TEMPLATE_METHOD.md`：从旧 11 个 gold-standard 模板抽出的实现方法，重点约束拆分/收窄、`Config` / `ResolvedConfig`、`config_from_seed`、`resolve_config`、builder、joint metadata 和 QC。
- `CATEGORY_BATCH_TEMPLATE.md`：批量类别输入模板。
- `SPEC_REVIEW_TEMPLATE.md`：人工审核 spec 的 checklist。
- `specs/*.md`：已有 baseline / reviewed spec，用来参考 spec 写法，不作为新类别部件来源。

## 放置位置

```text
<repo_root>/
├── articraft_template_authoring/
├── agent/templates/                 # gold-standard 模板与新模板代码在这里
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

## 模板阶段的成熟度重点

- 先判断类别是否过宽：主运动 spine、root 坐标系、joint chain 不兼容时，应拆分 slug 或收窄 seed domain。
- 旧 11 个模板定义成熟度下限；新 20+ 模板可以参考，但只能作为二级经验来源。
- 模板文件必须至少 1000 行；1000 是最低保险线，不是上限，也不是充分条件。
- 五星样本源码不能只是阅读引用，关键 helper / part / joint 必须实际改编 adopted `model.py:Lx-Ly` 片段。
- 空间结构必须先识别类别拓扑和主约束基准，再选择约束策略派生数量、尺寸、origin、orientation 和 joint range；抽屉柜 envelope-first 只是一个例子，滑轨、铰链、伸缩、旋转、支撑、对称和 linkage 结构都要用各自的约束链，避免悬空 / 穿模。
- joint 必须按部件语义确定 type、axis、origin、range，并通过测试和预览检查运动方向。
- `config_from_seed` 只采样已实现且测试覆盖的稳定子域。
- `resolve_config` 负责 enum 校验、范围夹紧、legacy alias、互斥组合降级、尺寸和 joint 参数派生。
- `_build_*` 只落几何，不随机关键尺寸。
- 测试必须锁住 seed domain、关键 joint、关键 visual、离散多样性分支和 QC。
- agent 必须自动执行测试、QC、渲染预览、看图自检、修复、重复；用户不应成为默认手调器。
- 多类别模板实现必须串行或小批量推进；不要一次性生成 20/30 个未验收模板。
