# Modular Template — Full Agent Workflow

本文件是 modular 模板的完整两阶段工作流（SPEC_ONLY → 人工审核 →
TEMPLATE_AFTER_REVIEW）。

读完 [`AGENT_ENTRYPOINT.md`](AGENT_ENTRYPOINT.md) 后读本文件。

---

## 0. 何时进入 modular 流程

- 用户明确说"模块化"、"slot/module"、"想覆盖多种拓扑"→ 直接进 modular。

---

## 1. SPEC_ONLY 阶段

目标：

```text
N 个类别 → N 个 articraft_template_authoring/specs/<slug>.md → 停等审核
```

### 1.1 阅读 5 星样本

对每个类别：

1. 列出该类别下**全部** 5 星样本的 record_id（不允许抽样）。
2. 对每个样本读：`model.py / revision.json / record.json / prompt`。
3. 记录每个样本的：
   - part 树（part 名 + visual 数量）
   - joint 拓扑（parent / child / type / axis / motion_limits）
   - bbox 大致尺寸
   - 独特结构特征（"这个有 service door，那个有 storage tray"）

### 1.2 拆出独立变化轴

对比所有样本，找出独立变化维度（**结构性差异**，不是尺寸 / 颜色微调）：

- knife 例：housing 形（barrel vs pistol）/ mechanism（slider vs door swap）
  / blade 形（直 vs hook）
- monitor_mount 例：base（壁挂 vs 桌夹）/ arm 数（1-N 节）/ head（pan+tilt
  vs tilt-only）
- ceiling_fan 例：mount（壁挂 vs 吊装）/ motor housing 形 / blade 片数（3-8）

每个轴必须满足：

- 至少 2 个 5 星样本能各自提供候选模块的几何参考（达不到的轴去掉）
- 物理上能跟相邻轴串起来（chain）或并联到同一上游（parallel children）
- 跨样本的差异是**结构性的**，不能只是涂装 / 比例

### 1.3 选择槽位策略

按下面三种 pattern 之一（也可以混合，但 spec 必须明说）：

1. **Linear chain**（knife / monitor_mount basic）：槽位 A → B → C 串成链。
2. **Parallel children**（dj_equipment）：所有槽位的 part 都 parent
   到同一个 chassis part。
3. **Multiplicity**（monitor_mount arms / fan blades）：一个槽位有
   `N_min..N_max` 种倍数候选（每种 N 是一个独立 module 名），适用于
   "同一种 part 重复 N 次"。spec 必须写清可采样范围或固定值，例如
   fan blades `3..8`、serial arm links `1..5`；不要只写抽象的 `N`。

### 1.4 写 spec

按 [`SPEC_TEMPLATE.md`](SPEC_TEMPLATE.md) 的字段，写
`specs/<category_slug>.md`。必填项：

- 元信息（slug / template path / test path / stage / 模板 pattern）
- 5 星样本阅读清单（全部样本 record_id + 是否被 spec 采用为候选源）
- 核心身份描述
- **槽位 + 候选模块表**（含 5 星来源带 `model.py:Lx-Ly`）
- **槽位图**（chain / parallel / multiplicity 标注）
- **seed=0 anchor 选择**（每槽位标一个 anchor module）
- 每槽位的 part 列表 + joint 拓扑
- 参数范围表
- Multiplicity / Copy Logic（每个 spec 必填；agent 自己判断；有就写具体
  复制规则和 `N_min..N_max` / 固定 N，没有就写无）
- 拓扑多样性审计（组合数 / 倍数范围 / 预计 diversity gate 是否能过）
- Validator / Reject cases / 与相邻类别的边界

### 1.5 SPEC_ONLY 停止条件

写完所有目标类别的 spec 后停下，等用户审核。**不要**进入实现阶段。

---

## 2. 人工审核

人工 reviewer 用 [`SPEC_REVIEW_TEMPLATE.md`](SPEC_REVIEW_TEMPLATE.md) 检查：

- 槽位数是否合理（3 是 sweet spot，2 是 fallback，≥5 一般要折叠为
  multiplicity）
- 每槽位候选数是否 ≥3（不够时是否退到 2 + 给出理由）
- 候选模块的 5 星来源是否真的结构不同（防止候选退化为参数微调换皮）
- 槽位图是否物理可行（chain 的相邻 mating face 是否真存在）
- multiplicity 槽位的 N_min / N_max 是否合理
- 拓扑组合数能否撑过 `module_topology_diversity ≥ 5`

reviewer 在 spec 的 frontmatter / 表格里把 `stage` 改为 `approved` 或
`rejected + 修改意见`。

---

## 3. TEMPLATE_AFTER_REVIEW 阶段

spec `approved` 后进入实现阶段。

### 3.1 必读

1. 本文件 §3。
2. [`MATURE_METHOD.md`](MATURE_METHOD.md)（成熟度标准）。
3. 项目根 [`../MODULAR_TEMPLATE_AUTHORING.md`](../MODULAR_TEMPLATE_AUTHORING.md)
   （架构 + 设计契约 + 实现 pattern）。
4. 项目根 [`DESIGN_RULES.md`](DESIGN_RULES.md)
   （3 条硬规则）。
5. 三个 reference 模板里**最接近目标拓扑**的那个的源码：
   - 串行链 → [`monitor_mount.py`](../agent/templates/monitor_mount.py)
   - 并联子件 → [`dj_equipment.py`](../agent/templates/dj_equipment.py)
   - 简单 3 槽位 → [`retractable_utility_knife.py`](../agent/templates/retractable_utility_knife.py)

### 3.2 实现产出物

- `agent/templates/<slug>.py` — modular template，必须：
  - `__modular__ = True` 标志
  - `<Slug>Config` / `Resolved<Slug>Config` 数据类
  - `config_from_seed(seed)` — seed=0 返回 anchor 组合
  - `resolve_config(config)` — 校验 / clamp
  - `build_<slug>(config, *, assets=None)` 主入口
  - `build_seeded_<slug>(seed)`
  - `slot_choices_for_seed(seed) -> list[tuple[str, str]]`
  - `run_<slug>_tests(model, config) -> TestReport`

- `tests/agent/test_<slug>_template.py` **可选**（非验收必需）。验收只看
  compile-sweep；per-template 测试默认被 `template_asset` marker 排除（见
  `tests/agent/conftest.py`），批量造模板时不写。仅当模板定稿、要长期锁结构
  时才写，且只覆盖 sweep 抽样覆盖不到的两项：
  - 所有 module 组合 build 成功（loop 整个 slot×module 网格——sweep 只抽样，
    冷门组合可能永远抽不到）
  - seed=0 = anchor 组合（sweep 不验证这一条）

- 如果模板用了非显然的 pattern（mid_arm 倍数、parallel children），
  在 `<slug>.py` 文件头注释里写清。

### 3.3 自检循环（分两阶段，先快后全）

**为什么分两段**：compile-sweep 单轮 20 seed 要 5-10 分钟（每 seed 都要 build
完整 URDF + mesh export），修一个 bug 重跑一次代价很大。先用 5 seed 把头部
bug 修干净，再上 20 seed 验证 edge case，能省 30-50% 的总时间。

```bash
# 验收只靠 compile-sweep,无 pytest 步骤。若写了可选的 per-template 回归测试,
# 用 `uv run --group dev pytest -m template_asset tests/agent/test_<slug>_template.py -q`
# 单独跑,它默认不在 sweep 流程里。

# 2a. 快速 5 seed sweep — 用来打掉 anchor / 主流模块组合 / 基础 mating 的 bug
uv run articraft template compile-sweep <slug> --seeds 0-4 \
    --quality-profile final --quiet --out /tmp/sw_<slug>_fast.json

# 在这一步要求：
# - verdict == "pass"；若失败，先修 seeds 0-4 的 failure/quality cluster
# 注意：seeds 0-4 不足以让 module_topology_diversity 过线（≥5 distinct），
# 该 gate 在 2b 的 20 seed 才正式判定，**这里不算硬约束**。
# 若 2a 失败，先把 seeds 0-4 的 failure cluster 修干净再继续；不要直接跳到 2b。

# 2b. 中段 20 seed sweep — 验证 edge case + diversity gate
uv run articraft template compile-sweep <slug> --seeds 0-19 \
    --quality-profile final --quiet --out /tmp/sw_<slug>.json

# 必须：
# - verdict == "pass"
# - pass_rate == 1.0
# - quality_summary.failed_gates == {}
# - coverage_gates.module_topology_diversity.status == "pass"（≥5 distinct）

# 2c. 最终 50 seed sweep — 唯一验收门
uv run articraft template compile-sweep <slug> --seeds 0-49 \
    --quality-profile final --quiet --out /tmp/sw_<slug>_final.json

# 必须同样 verdict=pass、pass_rate==1.0、quality_summary.failed_gates=={}，
# 且 diversity gate pass。

# 3. 10 seed viewer 推送
uv run articraft template batch <slug> --seeds 0-9 --agent claude-code
```

不通过时**自闭环修**，常见失败和应对见
`MATURE_METHOD.md` §"常见失败模式"和 root
[`MODULAR_TEMPLATE_AUTHORING.md`](../MODULAR_TEMPLATE_AUTHORING.md)
"Common pitfalls"。

**经验法则**：如果 2a 跑出 pass_rate < 0.4，多半是 anchor 或核心 helper 有
结构问题——先停下来检查 `config_from_seed(0)` 的 build_<slug> 输出，再迭代；
盲目跑 2b 只会浪费更多 sweep 时间。

### 3.4 完工标准

- final sweep verdict=pass, pass_rate == 1.0, failed_gates == {}, diversity ≥ 5
  （**唯一验收门**，不要求 pytest）
- 10 seed batch 全部 compile 成功
- 自检过一遍 viewer 的 10 个 seed，**没有明显几何错误**（关节悬空、
  部件穿模、视觉断片）
- 把每 seed 的 `slot_choices_for_seed(seed)` 选了什么 module 简短报告给用户

不满足任何一条都不能宣布完工。

---

## 4. 单类别串行执行

**每次最多 2-3 个同族模板一组推进**。禁止一口气
跑 N 个 modular 模板，因为：

- 模块化代码量大（每模板 1500-2500 行）
- 失败模式更隐蔽（disconnected_islands / mating gap / 倍数 N 边缘情况
  各自要单独修）
- 一旦 sub-agent 把 sweep 失败的模板堆给用户，调试成本爆炸

每个模板自闭环到 sweep pass + viewer 看完为止，再开下一个。

---

## 5. 数据交付到用户

完工后简短汇报：

```text
- slug: <category_slug>
- spec: articraft_template_authoring/specs/<slug>.md
- template: agent/templates/<slug>.py (NNNN lines)
- sweep: verdict=pass, pass_rate=1.00, failed_gates={}, distinct_topologies=K
- batch: 10/10 seeds compiled to viewer (record IDs ...)
- per-seed picks: <seed 0..9 的 slot_choices_for_seed 一行一个>
```

让用户在 viewer 自己看效果决定下一步。

---

## 附录：批量类别输入格式

用户给 agent 多个类别时，按以下格式填表：

```markdown
## Mode
SPEC_ONLY

## Categories

| index | category_slug | notes |
|---:|---|---|
| 1 | <category_a> |  |
| 2 | <category_b> |  |
| 3 | <category_c> |  |
```

agent 收到这个表后按 §1（SPEC_ONLY）的规则一个一个写 spec，写完所有
`specs/<slug>.md` 停下等审核。每个 spec 必须：

- 枚举并读取该类别**全部** 5 星样本（不允许抽样）
- 每槽位 ≥3 候选模块（不够 3 个退到 2），每个候选带 `model.py:Lx-Ly` 引用
- 每槽位标恰好一个 `seed=0 anchor`
- 显式声明 pattern：`linear_chain` / `parallel_children` / `multiplicity` / `mixed`
- 拓扑多样性审计：组合数 ≥8，能撑过 `module_topology_diversity ≥ 5`

具体 spec 字段规范见 [`SPEC_TEMPLATE.md`](SPEC_TEMPLATE.md)。
