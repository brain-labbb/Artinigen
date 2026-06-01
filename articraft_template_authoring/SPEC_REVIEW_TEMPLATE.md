# Modular Spec Review Template

用于人工审核 agent 写出的 `articraft_template_authoring/specs/<slug>.md`。
包括**槽位 / 候选模块 / 拓扑组合**的审核维度。

## Review Target

| 项 | 值 |
|---|---|
| category_slug | <category_slug> |
| spec path | articraft_template_authoring/specs/<category_slug>.md |
| reviewer status | pending / approved / rejected |
| pattern | <linear_chain / parallel_children / multiplicity / mixed> |

## 必查项

### 样本阅读完整性

- [ ] agent 是否声明已枚举并完整读取该类别**全部** 5 星样本的
      `model.py / revision.json / record.json / prompt`（不允许抽样）。
- [ ] 已读但未采纳为模块来源的样本，是否在阅读摘要里列出并写了未采纳理由。

### 槽位设计

- [ ] 槽位数是否落在 **2-4** 之间。
- [ ] 如果是 5 个或以上，是否有理由（一般要折叠为 multiplicity）。
- [ ] 槽位之间是否**物理可串/并**（chain 的相邻 mating face 在 5 星样本里
      真实存在；parallel children 的所有 child 都能 parent 到同一 chassis）。
- [ ] 每个槽位代表的是**独立的结构变化轴**，不是同一个 part 的装饰变化。

### 候选模块设计

- [ ] **每槽位至少 3 个候选模块**。如果不足 3 个，spec 必须给出明确理由
      （比如某类别 5 星样本只有 2 种结构家族），且降级到 2，不能 1。
- [ ] 每个候选模块都有 `model.py:Lx-Ly` 引用来自一个真实 5 星样本。
- [ ] 每个候选模块是**结构性差异**（不同 part 数 / 不同 joint 拓扑 /
      不同主 mesh），而不是参数微调换皮（颜色、比例、装饰位置）。
- [ ] 每槽位**恰好标了一个 seed=0 anchor**。
- [ ] anchor module 是从某个真实 5 星样本来的（不能是 agent 自己设计的
      合成结构）。

### 槽位图（pattern）

- [ ] `pattern` 字段对（linear_chain / parallel_children / multiplicity / mixed）。
- [ ] 如果是 `multiplicity`，是否明确写了可采样 `N_min..N_max` 或固定 N；
      范围是否合理、有来源或 reviewer-gated 外推说明（例如 fan blades 3-8、
      arm links 1-5），且不是只写抽象的 `N`。
- [ ] 如果是 `parallel_children`，spec 是否说清楚 chassis 模块怎么暴露
      共用 attachment surface。

### 拓扑多样性

- [ ] spec 的"拓扑多样性审计"算出来的总组合数 ≥ 8（最低吃饱
      `module_topology_diversity ≥ 5`）。
- [ ] 多样性源是**模块级**变化（结构性），不是参数级。

### Parts / Joints

- [ ] 每槽位的每个 module 都列出了它会 emit 的 part 列表。
- [ ] joint 表覆盖：chain joints（slot 间） + internal joints（slot 内部）。
- [ ] 关节 type / axis / origin / range 明确。
- [ ] 标出哪些 joint 准备 grandfather（no MatingContract）—— 一般是
      pin-through-sleeve / 多体 captured pivot 这种 MatingContract 建模不了
      的几何。



- [ ] 这个类别确实**值得用 modular**（5 星样本拓扑显著不同），不是
      结构性变化不足的类别。
- [ ] 跟已有 spec 没有重复（
      要说清两个 spec 的覆盖边界）。

### Validator / Reject

- [ ] Validator 列了 author_run_tests 该检查的关键点。
- [ ] Reject cases 覆盖了哪些样本应该被识别为不属于这个模板。

### 实现可行性提示

- [ ] 是否有"模板实现备注"说明哪些 helper 共享、哪些 inter-part 重叠
      预期、哪些 joint grandfather。

## 审核结论

```text
approved / rejected
```

把 spec frontmatter 的 `status` 改成相应值。

## 修改意见

```text
...
```

## 审核通过后的实现阶段提醒

审核通过后 agent 进入 TEMPLATE_AFTER_REVIEW 阶段。重点提醒：

- **3 个 reference 模板**（knife / monitor_mount /
  dj_equipment）是 modular 模板的骨架来源，**不**直接用旧 11 个
  gold-standard 模板的代码骨架。
- 实现阶段必须读 `MATURE_METHOD.md` 和根
  `MODULAR_TEMPLATE_AUTHORING.md`。
- 完工标准：sweep `verdict=pass`, pass_rate ≥ 0.85, diversity ≥ 5,
  10 seed batch viewer 自检干净。
- 单类别串行 + 自闭环修，最多 2-3 个同族模板一组推进。
