# Modular Spec Template

`articraft_template_authoring/specs/<category_slug>.md` 的字段规范。
SPEC_ONLY 阶段必须按本格式产出 spec。

---

## 强制字段

### 1. 元信息

```markdown
## 元信息
| 项 | 值 |
|---|---|
| slug | `<category_slug>` |
| template path | `agent/templates/<slug>.py` |
| test path (optional) | `tests/agent/test_<slug>_template.py` — 可选回归网，默认被 pytest 排除；验收以 compile-sweep 为准 |
| stage | `SPEC_ONLY_DRAFT` |
| status | `pending` |
| __modular__ | `True` |
| pattern | `linear_chain` / `parallel_children` / `multiplicity` / `mixed` |
```

`pattern` 字段说明这个模板的主要 slot 组装方式：
- `linear_chain`：A → B → C 串成链（knife / monitor_mount basic）
- `parallel_children`：所有槽位 part 都 parent 到同一个 chassis（dj_equipment）
- `multiplicity`：某槽位是"同部件 N 次"（fan blades / N-link arm）
- `mixed`：混合多种

### 2. 5 星样本阅读清单

```markdown
## 5 星样本阅读摘要
| 项 | 值 |
|---|---|
| five_star_total | N |
| read_count | N |
| read_scope | all 5-star samples in this category |
| samples_adopted_as_module_sources | M |
| samples_read_but_not_adopted | N - M |
```

后面紧跟全部样本的清单（含 record_id），每个标 "adopted as source for
slot X module Y" 或 "read but not adopted, reason: ..."。

### 3. 核心身份

类别的物理含义（保证跟相邻类别区分开）+ 主要功能 + 默认成熟域。

```markdown
## 核心身份

<一段散文>，约 100-200 字。

边界：
- 不包括 ...
- 不混入 ...（说明边界）
```

### 4. 槽位 + 候选模块表（核心）

这是 spec 最核心的字段。

```markdown
## 槽位 + 候选模块表

### Slot A：<slot_name_a>

| module_name | 5_star_source | model.py:Lx-Ly | seed=0 anchor | 结构特征 |
|---|---|---|---|---|
| <module_alpha> | rec_<slug>_xxx | L25-L120 | **yes** | 描述这个 module 的结构和外形 |
| <module_beta> | rec_<slug>_yyy | L40-L155 | | ... |
| <module_gamma> | rec_<slug>_zzz | L30-L170 | | ... |

### Slot B：<slot_name_b>

...（同样的结构）

### Slot C：<slot_name_c>

...（同样的结构）
```

**硬约束**：
- 每个槽位 **至少 3 个候选**（不够 3 个，给出理由并退到 2，**禁止 1**）
- 每个候选必须有 `model.py:Lx-Ly` 引用（来自 spec 已读的某个 5 星样本）
- 每个候选必须**结构上不同**（不同 part 树 / 不同 joint 数 / 不同 mesh），
  不能只换比例 / 颜色 / 装饰
- 每槽位标恰好一个 `seed=0 anchor`

### 5. 槽位图

```markdown
## 槽位图（slot graph）

pattern: <linear_chain / parallel_children / multiplicity / mixed>

<slot A> --[chain_joint_type axis]--> <slot B> --[chain_joint_type axis]--> <slot C>

或者：

<slot A: chassis> ↘ (parents)
                  ├── <slot B parts>  (parallel REVOLUTE)
                  └── <slot C parts>  (parallel PRISMATIC)

或者（multiplicity）：

<slot A> → [multiplicity slot B: N=N_min..N_max, candidates: <list>] → <slot C>
```

### 6. 每槽位的 Parts / Joints

```markdown
## 部件（Parts）

按槽位组织。每个 module 候选下列出它会 emit 的 part 名和 visual 概览。

### Slot A / module <name>
| part | visual_count | 描述 | 来源 |
| <part_x> | ~N | ... | model.py:Lx-Ly |

## 关节（Joints）

按 chain 顺序列出：

| 关节 | 类型 | parent_slot.part | child_slot.part | axis | range | 描述 |
| ... | REVOLUTE | A.x | B.y | (0,0,1) | [-π,π] | ... |
```

### 7. 参数范围汇总

```markdown
## 参数范围汇总
| 参数 | 类型 | 取值范围 | 默认 | 派生关系 | 来源 |
| ... | float | [0.x, 0.y] | 0.x | ... | model.py:... |
```

主要列：尺寸参数（含 multiplicity 槽位的 N_min / N_max）、palette、enum
选择（如果模块内部还有 sub-enum）。

### 8. 拓扑多样性审计

```markdown
## 拓扑多样性审计

总组合数：A × B × C = X
（如果有 multiplicity 槽位，把 N_max - N_min + 1 算进去）

预计 `module_topology_diversity` 门控（≥5 distinct）能否过：yes / no
理由：...

每槽位候选数：
| slot | candidate_count | 是否 ≥3 | 备注 |
| A | 4 | yes | |
| B | 3 | yes | |
| C | 2 | **no** | 理由：5 星样本只有 2 种结构家族 |
```

### 9. 验证器和拒绝条件

```markdown
## Validator（author_run_tests 必须覆盖的点）

- ...

## Reject cases（必须能识别并拒绝）

- ...
```

### 10. 与相邻类别的边界

```markdown
## 与相邻类别的边界

- 不该混入：<相邻类别 1>（理由）
- 不该混入：<相邻类别 2>（理由）
```

---

## 可选字段

### 11. 模板实现备注（给后续实现 agent 的提示）

```markdown
## 模板实现备注（可选）

- 哪些 module 共享 helper 函数
- 哪些 joint 要 grandfathered（no MatingContract）
- 哪些 inter-part 重叠预期需要 allow_overlap 声明
- 任何 spec → 代码翻译的非平凡映射
```

### 12. Adopted Source Index

```markdown
## 采用源码索引（Adopted Source Index）

| source_id | sample_id | model.py 来源 | 采纳用途 |
| S1 | rec_xxx | L25-L120 | slot A.module_alpha 的 part 树和 helper |
| S2 | rec_yyy | L40-L155 | slot A.module_beta 的 alternate part 树 |
| ... | ... | ... | ... |
```

（参考已有 spec 的） source index 表，让 review 和后续实现 agent
可以追溯每片代码的来源。

---

## 写完后

spec 自身的 `stage` 字段还在 `SPEC_ONLY_DRAFT`。停下，等 reviewer 看
[`SPEC_REVIEW_TEMPLATE.md`](SPEC_REVIEW_TEMPLATE.md) 检查、修改 `stage`
为 `approved` 或 `rejected + 修改意见`。审核通过前**不要**进入实现。
