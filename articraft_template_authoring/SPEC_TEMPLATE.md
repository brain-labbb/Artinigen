# Modular Spec Template

`articraft_template_authoring/specs_modular_v1/<category_slug>.md` 的唯一字段规范。SPEC_ONLY 阶段必须按本格式产出 spec。

Modular spec 不使用单一 `primary_anchor` 作为主来源。它使用 per-module source table、每 slot 的 `seed=0 anchor` module，以及 slot graph 来描述模板结构。

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

| module_name | 5_star_source | model.py:Lx-Ly | seed=0 anchor | 结构特征 |
|---|---|---|---|---|
| <module_alpha> | rec_<slug>_xxx | L25-L120 | yes | part tree / joint / primitive / interface 特征 |
| <module_beta> | rec_<slug>_yyy | L40-L155 | | ... |

### Slot B：<slot_name_b>

...
```

硬约束：

- 每个 slot 目标 3-6 个 candidate；样本池不足时可降到 2，但必须说明理由。
- 禁止只有 1 个 candidate 的 slot，除非该 slot 折入相邻 module 或改成 module-local fixed structure。
- 每个 candidate 必须有 `model.py:Lx-Ly` 来源。
- 每个 slot 恰好一个 `seed=0 anchor`。
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
| <slot_choice> | enum | <module names> | <seed0 module> | 由 seed 或 override 选择 | module table |
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

预计 `module_topology_diversity` 门控（≥5 distinct）能否过：yes / no
理由：...

seed_domain_stage：stage1_coverage / stage2_procedural / final
Stage 1 high-risk coverage seed plan：列出 seed 范围、覆盖的 slot/module/multiplicity 组合、风险类型、viewer 目检重点和预计 distinct 数。
Stage 2 procedural target：所有 Stage-1 模板完成后升级；目标为 unbounded deterministic sampling，1000-seed topology distinct 建议 >=100，低于 100 需说明类别/兼容约束原因。
若使用 curated / modulo coverage seeds：说明这是 Stage 1 临时稳定域，不是最终 dataset-scale seed domain。

| seed/range | covered combo | risk type | viewer / validator focus |
|---|---|---|---|
| 0 | anchor module combination | regression anchor | source identity / baseline joint |
| 1-N | <high-risk combo> | floating / collision / axis / max multiplicity / bulky module / optional child | <checks> |

| slot | candidate_count | 是否 ≥2 | 是否 ≥3 | 备注 |
|---|---:|---|---|---|
| A | 4 | yes | yes | |
```

要求：

- `module_topology_diversity` 的 `>=5 distinct` 只是最低机械门槛，不是最终 seed domain 的目标。
- Stage 1 允许 finite coverage seed domain：可以用 curated / gated / modulo coverage table 先覆盖关键合法组合，目标是模板质量、稳定装配和 viewer 可审查。
- Stage 1 spec 必须明确 coverage domain 覆盖哪些 module、哪些 multiplicity、哪些稀有组合，以及哪些组合暂不采样。
- Coverage seed plan 必须优先覆盖最容易坏的组合：悬空/漂浮风险、穿模/clearance 风险、joint 轴或 range 风险、closed pose 风险、max multiplicity、bulky module、可选 moving child、长链/多子件装配、互斥 gate 或 fallback 降级路径。
- Stage 1 的目的之一是先收敛这些高风险几何/接口/约束组合；Stage 2 再放开 seed domain 时应复用这些已验证的 InterfaceSpec、尺寸派生和 compatibility gates。
- Stage 2 / final 要求迁移为 unbounded deterministic procedural sampling；除 anchor / regression / coverage overrides 外，主体 `seed>0` 不得无限轮换小型固定表。

### 10. Validator 和 Reject cases

```markdown
## Validator

- seed=0 equals anchor module combination
- slot_choices_for_seed returns implemented module names
- module_topology_diversity expected to pass
- Stage 1 high-risk coverage seed domain is documented and covers representative modules plus failure-prone combos
- Stage 2 procedural seed migration target is documented
- final templates do not endlessly cycle a small curated table as the main seed domain
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
