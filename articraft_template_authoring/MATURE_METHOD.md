# Mature Modular Method

本文件总结 3 个 reference modular 模板（knife / monitor_mount / dj_equipment）
共同的成熟度方法。TEMPLATE_AFTER_REVIEW 阶段必读。

核心目标：**不要把 5 星样本代码硬塞成一个大文件；先按 spec 的槽位 / 候选
模块拆，把每个候选模块写成结构清晰的 factory，再用 `_modular.py` 的
assembler 把它们组装起来，最后过两道质量关：sweep + viewer 自检。**

---

## 0. Gold Standard 边界

本流程的成熟度锚点是 **3 个 modular reference 模板**：

- [`agent/templates/retractable_utility_knife.py`](../agent/templates/retractable_utility_knife.py)
  — linear chain, 3 槽位 × 2 候选 = 8 拓扑
- [`agent/templates/monitor_mount.py`](../agent/templates/monitor_mount.py)
  — chain + multiplicity, 2 × 8 × 2 = 32 拓扑
- [`agent/templates/dj_equipment.py`](../agent/templates/dj_equipment.py)
  — parallel children, 2 × 2 × 2 = 8 拓扑（每槽位多家族）

这 3 个模板代表 3 种典型 pattern，新模板基本能映射到其中之一。**不要**
直接复用旧 11 个 gold-standard 模板的代码骨架
跟 modular 抽象不兼容）。

参考优先级：

1. 审核后的 modular spec 和其中的候选模块 5 星来源（`model.py:Lx-Ly`）
2. 3 个 reference modular 模板的对应 pattern
3. 项目根 [`../MODULAR_TEMPLATE_AUTHORING.md`](../MODULAR_TEMPLATE_AUTHORING.md)
   的架构 / 设计契约 / Common pitfalls
4. 已通过 sweep 的其他 modular 模板（如果有）

---

## 1. 模板文件结构

按 reference 模板的固定顺序排：

```
1. module docstring（pattern 说明 + 槽位图）
2. imports
3. __modular__ = True
4. Module 名 / Palette 枚举 + 默认色板字典
5. <Slug>Config 数据类（frozen）
6. Resolved<Slug>Config 数据类
7. config_from_seed(seed) — seed=0 锁 anchor
8. resolve_config(config) — clamp / validate
9. Mesh / 形状 helpers
10. 各槽位的 module factory（顺序按槽位声明顺序）
    - <Slot A>：3 个候选 factory
    - <Slot B>：3 个候选 factory
    - <Slot C>：3 个候选 factory
11. ARM_FACTORIES / 各槽位的 _FACTORIES dict
12. _slots_for_config(r) 构造 SlotSpec 列表
13. build_<slug>(config) 主入口（调 assemble）
14. build_seeded_<slug>(seed)
15. slot_choices_for_seed(seed)
16. run_<slug>_tests(model, config) — author 测试 + allow_overlap 声明
17. 注释块：模块化设计说明 + adoption table
18. __all__
```

---

## 2. Config / ResolvedConfig 写法

 `Config` 一致，但多了**模块选择字段**：

```python
SlotAModule = Literal["module_alpha", "module_beta", "module_gamma"]
SlotBModule = Literal[...]
SlotCModule = Literal[...]

@dataclass(frozen=True)
class <Slug>Config:
    slot_a_module: SlotAModule | None = None
    slot_b_module: SlotBModule | None = None
    slot_c_module: SlotCModule | None = None
    # ...其他尺寸 / 颜色 / palette 字段...
```

`config_from_seed` 要求：

- `seed == 0`：返回 anchor 组合 + spec 标定的 anchor 尺寸
- 其他 seed：每个槽位 `rng.choice` 候选 module；尺寸用 rng.uniform 在
  spec 给定的范围内采样

`resolve_config` 要求：

- 校验每个 module 字段是 enum 合法值，否则 `raise ValueError`
- clamp 所有 float 字段到 spec 范围内
- 填充任何 None 模块字段为 anchor 默认值

---

## 3. Module Factory 写法

每个 module factory 签名：

```python
def _build_<slot>_<module>(ctx: ModuleBuildContext) -> ModuleBuild:
    model = ctx.model
    r: Resolved<Slug>Config = ctx.config  # type: ignore[assignment]
    # ...
    return ModuleBuild(
        module_name="<module_name>",
        parts_emitted=[...],
        internal_articulations=[...],
        interfaces={"upstream": ..., "downstream": ...},
    )
```

**硬约束**：

1. **upstream interface 的 anchor_local 沿 mating-normal 轴必须为 0**
   （切向 x / y 自由）。否则 assembler 会 raise ValueError。

2. **part 内 visual 必须全部连通**（AABB 实际相交，1e-6 tol）。
   常见漏点：lofted bridge 浮在 carrier 上、lower_lug 浮在 pivot 下、
   bracket 浮在 deck 上。解决：加 neck/riser/post connector Box 桥接。

3. **joint origin 必须落在 parent 和 child 的几何 AABB 内**（tol 0.015）。
   做法：child 模块 emit 时让 (0,0,0) 落在主 hub 的 AABB 内。

4. **机械捕获式 pivot 用 grandfather**（joint 没有 `mating=` 字段），
   并在 `run_*_tests` 里 `ctx.allow_overlap` 声明 inter-part 重叠。

5. **每个 module 用 `ctx.rng` 拿随机源**（不要自己 `random.Random`），
   `ctx.config` 拿尺寸，`ctx.palette` 拿色板，`ctx.prior_choices` 看
   上游选了谁（如果模块行为跟上游耦合）。

---

## 4. Slot 设计的成熟度

跟 spec 一致，但加几条实现侧约束：

- **3 个槽位是 sweet spot**。简单类别 2 个也行；超过 4 个一般要折叠
  为 multiplicity。
- **每槽位 3-6 个候选模块**。2 个是最低线（要有理由）。
- 同槽位的候选模块**结构性不同**，不是参数微调换皮。
- 多样性测试期望：`seeds 0-9` 内见到 ≥7 个 distinct picks。

---

## 5. assemble 调用

```python
def build_<slug>(config, *, assets=None):
    r = resolve_config(config)
    model = ArticulatedObject(name="<slug>", assets=assets)
    for material_name, rgba in r.palette.items():
        model.material(material_name, rgba=rgba)

    rng = random.Random(0)  # assemble 内部不再依赖 rng（seed=0 路径）
    assemble(
        model,
        slots=_slots_for_config(r),
        rng=rng,
        palette=r.palette,
        config=r,
        seed=0,  # seed=0 是确定性 path；具体 seed 用 build_seeded_<slug>(seed)
    )
    return model
```

注意：`build_seeded_<slug>(seed)` 真正用了 seed 抽 module；`build_<slug>`
是给定 config 的确定路径（不抽签）。

---

## 6. run_<slug>_tests 的 allow_overlap

模块化模板通常会引入大量**预期的 inter-part 重叠**：

- 串行链的 hub 穿过 clevis lugs（hub_top ↔ top_lug）
- captured pivot pin 穿过 bushing（cylinder_a ↔ cylinder_b）
- multiplicity 倍数槽位的 N 个子件之间相互靠近
- 加 connector neck 后引发的新重叠

`run_<slug>_tests(model, config)` 函数里**集中声明**所有 allow_overlap，
按 reference 模板风格组织：

```python
def _allow_internal_pivot_overlaps(ctx: TestContext, model: ArticulatedObject):
    part_names = {p.name for p in model.parts}
    if "<parent_part>" in part_names and "<child_part>" in part_names:
        parent = model.get_part("<parent_part>")
        child = model.get_part("<child_part>")
        for parent_elem, child_elem in (
            ("parent_visual_1", "child_visual_1"),
            ...
        ):
            ctx.allow_overlap(parent, child, elem_a=..., elem_b=...,
                              reason="...")
```

monitor_mount 是这块写得最系统的范例，直接抄它的结构。

---

## 7. 测试覆盖

**权威验收信号是 `compile-sweep`，不是 pytest**（见根 `CLAUDE.md`）。模板是否合格
完全由 `compile-sweep <slug> --seeds 0-49` 的三道门（baseline 质量门 +
`module_topology_diversity` ≥5）判定。

`tests/agent/test_<slug>_template.py` 是**可选**的结构回归网，不是验收门。它默认
被 pytest 排除（自动打 `template_asset` marker，见 `tests/agent/conftest.py`），
不会进 `just test-all` / CI 的默认集；要跑用 `pytest -m template_asset`。

什么时候值得写它：某个模板**定稿、要长期锁住不被改坏**时。即便写，也**只建议覆盖
compile-sweep 抽样覆盖不到的两项**——其余 sweep 已经管了：

- **所有 module 组合 build 成功**（穷举 slot×module 笛卡尔积；sweep 是抽样，可能
  永远抽不到某个冷门组合）
- **seed=0 = anchor 组合**（`slot_choices_for_seed(0) == [(slotA, anchor_a), ...]`；
  sweep 不验证 seed0 是锚点）

可复现 / 拓扑多样性 / 基础 QC 都与 sweep 重复，不必在 test 里重写。

---

## 8. 完工自检循环

跟 `agent_workflow.md §3.3` 一致：**两段式 sweep**——先 `--seeds 0-4`
打掉头部 bug（anchor / 主流模块组合 / 基础 mating），再 `--seeds 0-19`
验证 edge case + diversity gate。盲跑 20 seed 修一轮 5-10 分钟，迭代代价大。

再强调几条死规：

- **disconnected_geometry_islands 是 FAIL 级**（不是 warn）。任何浮空
  visual 都会让 sweep verdict=fail。真·多块刚性件（梳齿/栅格/鳍片堆）若加桥
  会凭空造材料，用 `ctx.allow_disconnected_islands(part, reason="...")` 降为
  warning；仅限真多块件，不可掩盖意外断裂的 seed。
- **pass_threshold 默认 0.85**。20 seed 允许 ≤3 个失败。5 seed 阶段
  允许 ≤1 个失败（pass_rate ≥ 0.8）。
- **`module_topology_diversity` 不在 5 seed 阶段判定**（≥5 distinct 凑不齐）。
  只在 20 seed 阶段是硬约束。
- **必须自己跑 viewer 看一遍 10 个 seed**。sweep verdict=pass 不代表外观
  没问题（盒子比例怪、机构语义不对、关节运动方向反），这些必须 viewer
  自查。

不通过任何一条不能宣布完工。把失败 cluster + 修复方案写下来给用户看，
不要把脏数据丢给用户救火。

---

## 9. 常见失败模式

跟 root [`../MODULAR_TEMPLATE_AUTHORING.md`](../MODULAR_TEMPLATE_AUTHORING.md)
"Common pitfalls" 章节一致。简明：

| 失败 | 原因 | 修复 |
|---|---|---|
| disconnected_geometry_islands | visual 间不 AABB 相交 | 加 connector neck/riser；真·多块件用 allow_disconnected_islands |
| joint_origin_far_from_geometry | child 模块的 (0,0,0) 不在它自己 visual AABB 内（tol=max(0.015, 0.05×bbox 对角线)，大件按比例放宽） | 调 hub 位置或加 anchor visual |
| joint_mating_has_gap | 沿 normal 轴的 face center 不重合 | 调 anchor_local 的 normal-axis 分量 |
| inter-part overlap | 加 connector 后引发新重叠 | 在 _allow_internal_pivot_overlaps 加声明 |
| pass_rate < 0.85 | 某些 module 组合 + 某些尺寸触发边缘 case | sweep 报告里看失败 cluster，修改有问题的 module 或 clamp 范围 |
| diversity < 5 | 候选模块过少 / RNG 太集中 | 加候选模块 OR 改 rng.choice 权重 |
| seed=0 ≠ anchor 拓扑 | config_from_seed(0) 不返回 anchor 组合 | 修 config_from_seed 的 seed==0 分支 |

---

## 10. 批量推进规则

**每次最多 2-3 个同族模板一组推进**。
- spec 阶段可以批量写（10 个 spec 一起写没问题）。
- 实现阶段必须单类别串行 + 自闭环修。
- 一旦某模板 sweep 长时间过不去（≥3 轮失败 cluster），停下来报告给
  用户，不要堆给下一个模板。
