# Modular Spec Template

`articraft_template_authoring/specs_modular_v1/<category_slug>.md` 的唯一字段规范。SPEC_ONLY 阶段必须按本格式产出 spec。

Modular spec 不使用单一 `primary_anchor` 作为主来源，也不要求 `seed=0` 复现固定 anchor 组合。它使用 per-module source table、slot graph、InterfaceSpec / MatingContract 计划和 procedural sampling contract 来描述模板结构。

## 强制字段

### 1. 元信息

```markdown
## 元信息
| 项 | 值 |
|---|---|
| slug | `<category_slug>` |
| template path | `agent/templates/<slug>.py` |
| test path (optional) | `tests/agent/test_<slug>_template.py` |
| stage | `SPEC_ONLY_DRAFT` |
| status | `pending` |
| __modular__ | `True` |
| pattern | `linear_chain` / `parallel_children` / `multiplicity` / `mixed` |
```

`pattern` 说明主要 slot 组装方式：

- `linear_chain`：slot 串成链。
- `parallel_children`：多个 slot 的 part 挂到共同 chassis / parent。
- `multiplicity`：某 slot 负责同构子件 N 次复制。
- `mixed`：混合多种。

### 2. 5 星样本阅读摘要

```markdown
## 5 星样本阅读摘要
| 项 | 值 |
|---|---|
| five_star_total | N |
| read_count | N |
| read_scope | all 5-star samples in this category |
| source_index_policy | only adopted module sources are indexed below |
```

### 3. 核心身份

```markdown
## 核心身份

<类别物理含义、主要功能、默认成熟域。说明不该混入的相邻类别。>
```

### 4. 槽位 + 候选模块表

每个 slot 表示一个可替换结构/功能层。每个 candidate module 必须结构不同，并有 5 星样本来源。

```markdown
## 槽位 + 候选模块表

### Slot A：<slot_name_a>

| module_name | 5_star_source | model.py:Lx-Ly | sampling eligibility | 结构特征 |
|---|---|---|---|---|
| <module_alpha> | rec_<slug>_xxx | L25-L120 | eligible if compatible | part tree / joint / primitive / interface 特征 |
| <module_beta> | rec_<slug>_yyy | L40-L155 | eligible if compatible | ... |

### Slot B：<slot_name_b>

...
```

硬约束：

- 每个 slot 目标 3-6 个 candidate；样本池不足时可降到 2，但必须说明理由。
- 禁止只有 1 个 candidate 的 slot，除非该 slot 折入相邻 module 或改成 module-local fixed structure。
- 每个 candidate 必须有 `model.py:Lx-Ly` 来源。
- `sampling eligibility` 说明 candidate 是否进入 deterministic procedural sampler；默认是 `eligible if compatible`。若暂不采样，必须说明阻塞原因和 reviewer 状态。
- Candidate 之间必须有结构差异；只换尺寸、颜色、材质或装饰不是新 candidate。

### 5. 槽位图（slot graph）

```markdown
## 槽位图（slot graph）

pattern: <linear_chain / parallel_children / multiplicity / mixed>

<slot A> --[joint_type axis + interface]--> <slot B> --[...]--> <slot C>
```

必须说明：

- slot 顺序或 parent 关系。
- 每条跨 slot 连接的接口点位：mating face、pivot、rail、socket、axis、contact plane 或 symmetry plane。
- 跨 slot joint type、axis、range 或 fixed support policy。
- 哪些 slot 是互斥、可选或由上游 module 派生。

### 6. 每槽位 Module Emits / Interfaces

```markdown
## 每槽位 Module Emits / Interfaces

### Slot A / module <name>
| emits | 描述 | 来源 |
|---|---|---|
| parts | <part names / visual groups> | S1 / model.py:Lx-Ly |
| internal joints | <joint names, type, axis, range> | S1 / model.py:Lx-Ly |
| upstream interface | <face / anchor / parent policy> | S1 / model.py:Lx-Ly |
| downstream interface | <face / anchor / consumer joint> | S1 / model.py:Lx-Ly |
```

要求：

- 活动件必须有 articulation 语义。
- 不动细节写成 parent visual，不作为独立 part。
- Interface 必须能映射到后续 `InterfaceSpec` 和 `MatingContract`。

### 7. 参数范围汇总

```markdown
## 参数范围汇总
| 参数 | 类型 | 取值范围 / 候选值 | 默认 | 派生关系 | 来源 |
|---|---|---|---|---|---|
| <slot_choice> | enum | <module names> | sampled | 由 deterministic procedural sampler 或显式 regression override 选择 | module table |
| <dimension> | float | [min, max] | value | 从接口或父基准派生 | Sx / model.py:Lx-Ly |
```

参数只表达语义选择、尺寸、行程、角度、multiplicity 数量、palette 或 module-local variant。不要把未实现拓扑放进 enum。

### 8. Multiplicity / Copy Logic

每个 spec 都必须写本节。若没有模板级复制数量逻辑，也要明确说明没有。

有复制数量逻辑时写：

- `count_param`
- `N_range`
- sampling domain
- copied object
- naming
- placement
- joint policy
- source/gating

无复制数量逻辑时写：

```markdown
## Multiplicity / Copy Logic

- 无复制数量逻辑：核心结构由固定 named slots 表达，不暴露 `*_count`，也不通过循环复制模板级 visual/part/joint。
```

### 9. 拓扑多样性审计

```markdown
## 拓扑多样性审计

总组合数：A × B × C = X
（如有 multiplicity，把 N 的采样数量算进去）

预计 `module_topology_diversity` 门控（≥10 distinct）能否过：yes / no
理由：...

seed_domain_policy：procedural_first
Procedural Sampling / Sweep Plan：说明 deterministic procedural sampling 如何选择 slot/module/multiplicity，compatibility matrix / gating 如何避免非法组合，是否存在少量 regression overrides，以及 random sweep / viewer 目检范围。
Topology target：1000-seed topology distinct 建议 >=100，低于 100 需说明类别/兼容约束原因。
若使用 regression overrides：说明具体 seed、失败回归或审核理由；不得用小型 curated / modulo 表作为主 seed domain。
Controlled local parameterization：列出初版模板应包含的关键连续 scale，例如 support_width_scale、station_spacing_scale、arm_reach_scale、hub_radius_scale、branch_thickness_scale、terminal_size_scale；说明取值范围、clamp / derived constraints，以及它们不会破坏 InterfaceSpec / MatingContract / multiplicity。

| item | policy | validator / viewer focus |
|---|---|---|
| sampler | <slot order, weighted choices, compatibility gates> | slot_choices_for_seed matches build choices |
| compatibility matrix | <legal / mutually exclusive / fallback policies> | no floating, collision, axis, max multiplicity, bulky module, optional child failures |
| controlled local variation | <safe continuous scale params + clamp policy> | proportions vary without breaking interfaces, clearance, support, joint origin, or category identity |
| regression overrides | none / <seed + reason> | previously failed or reviewer-selected cases only |
| random sweep | e.g. seeds 0-49 for initial pass, 0-999 for maturity audit | module_topology_diversity and contract failures |

| slot | candidate_count | 是否 ≥2 | 是否 ≥3 | 备注 |
|---|---:|---|---|---|
| A | 4 | yes | yes | |
```

要求：

- `module_topology_diversity` 的 `>=10 distinct` 只是最低机械门槛，不是最终 seed domain 的目标。
- 新模板首次实现时就应以 deterministic procedural sampling 作为主 seed domain；`seed=0` 不特殊。
- 新模板首次实现时应包含少量关键局部 scale，但主多样性仍必须来自 slot/module/layout/multiplicity。不要把每个小零件都做自由随机；所有连续参数必须在 `resolve_config` 中 clamp / 派生，并受接口、clearance、joint range 和类别 identity 约束。
- Compatibility matrix / gating 必须优先排除容易坏的组合：悬空/漂浮风险、穿模/clearance 风险、joint 轴或 range 风险、closed pose 风险、max multiplicity、bulky module、可选 moving child、长链/多子件装配、互斥 gate 或 fallback 降级路径。
- Regression overrides 只能用于已知失败回归或审核指定样本；主体 seed domain 不得无限轮换小型 fixed / curated / modulo 表。

### 10. Validator 和 Reject cases

```markdown
## Validator

- slot_choices_for_seed returns implemented module names
- config_from_seed uses deterministic procedural sampling for all ordinary seeds
- module_topology_diversity expected to pass
- compatibility matrix / gating prevents illegal module combinations
- optional regression overrides are sparse and justified
- final templates do not endlessly cycle a small curated table as the main seed domain
- controlled local scale params are clamped and cannot break interfaces, clearance, joint origin, or category multiplicity
- critical InterfaceSpec / MatingContract points exist
- key joints have expected type / axis / range
- copied objects follow naming and placement policy

## Reject cases

- <会让模板失败的 5-8 条模式>
```

### 11. 与相邻类别的边界

```markdown
## 与相邻类别的边界

- 不该混入：<相邻类别 1>（理由）
- 不该混入：<相邻类别 2>（理由）
```

### 12. 审核记录

```markdown
## 审核记录
| 项 | 结论 |
|---|---|
| reviewer status | pending / approved / rejected |
| reviewer notes | ... |
```

## 可选字段

### 13. 模板实现备注

```markdown
## 模板实现备注（可选）

- 哪些 module 共享 helper
- 哪些 InterfaceSpec / MatingContract 要特别注意
- 哪些 captured-pin overlap 需要 element-scoped allow_overlap
- 哪些 module 组合暂不进入 seed domain
```

### 14. Module Source Index

如果 slot table 太长，可以在这里汇总 source id。

```markdown
## Module Source Index

| source_id | slot | module | sample_id | model.py 来源 | 采纳用途 |
|---|---|---|---|---|---|
| S1 | Slot A | module_alpha | rec_xxx | L25-L120 | part tree + upstream interface |
```

## 写完后

spec 的 `stage` 保持 `SPEC_ONLY_DRAFT`，`reviewer status` 保持 `pending`。停下，等待人工审核。审核通过前不要进入模板实现。
