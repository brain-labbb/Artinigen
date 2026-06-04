# Modular Template Maturity Method

本文件补充 `MODULAR_TEMPLATE_AUTHORING.md`。它不定义另一条 authoring 路线；它只说明如何把 modular spec 中的 5 星样本 module source 参数化到成熟模板水平。

核心目标：**先用 slot graph 控制拓扑，再用 module factory 改编 5 星源码，最后用 InterfaceSpec / MatingContract / sweep gate 保证装配和运动语义。**

## 1. 两阶段 modular 模板标准

Stage 1 初版模板至少满足：

- `__modular__ = True`。
- spec 中每个 slot candidate 都有真实 5 星样本 `model.py:Lx-Ly` 来源。
- 每个主要 module factory 都能追溯到对应 source，保留其 part tree、joint 语义、primitive 复杂度和接口关系。
- `config_from_seed(0)` 选择 spec 标注的 anchor module 组合。
- `slot_choices_for_seed(seed)` 稳定返回每个 seed 的 module 组合。
- `config_from_seed` 只采样已实现、已测试、可装配的 module 组合。Stage 1 允许有限 coverage / curated seed domain 来覆盖代表组合和高风险组合，先稳定 sweep 和 viewer 目检。
- `resolve_config` 是唯一合法化和派生入口，负责 enum 校验、范围夹紧、互斥组合降级、尺寸链、接口点位和 joint range 派生。
- Module factory 只消费 resolved config、assets、palette 和 `ctx.rng`；不重新决定高层 slot graph。
- 每个跨 module 连接都有真实 InterfaceSpec；每个 separate moving child 有 joint metadata 和 MatingContract。
- 不动的装饰、封条、螺丝、刻度和面板细节优先作为 parent visual。
- `module_topology_diversity` gate 通过，high-risk coverage seed domain 覆盖计划已记录，且 sweep-pipeline 返回 `verdict=pass`。

Stage 2 / final mature 模板额外满足：

- 主体 `seed>0` 逻辑迁移为 unbounded deterministic procedural sampling。
- 除 anchor、coverage 和 regression overrides 外，不再用有限 curated / modulo table 作为主 seed domain。
- 1000-seed topology distinct target 达标，或有类别合法拓扑空间确实较小的审核理由。

## 2. High-quality modular reference map

实现新模板时，优先从下表选择 1-3 个最接近当前 slot graph / 运动拓扑的 modular 模板深读。它们是模块化路线的主要工程参考；旧 11 个 gold-standard 模板只补充成熟约束和通用 SDK / validator 经验。

| 参考类型 | 优先参考模板 | 适合学习 |
|---|---|---|
| `_modular.py` 架构样板 | `twojoint_prismatic_chain`, `twojoint_revolute_chain`, `usb_drive_with_swivel_cover`, `wheelbarrow`, `threestage_telescoping_slide` | `SlotSpec` / `ModuleBuild` / `InterfaceSpec` / `MatingContract`、seed=0 anchor、`slot_choices_for_seed`、module source adaptation |
| 串联 revolute / 机械臂 | `twojoint_revolute_chain`, `robotic_arms`, `robotic_leg`, `articulated_task_lamp` | 多关节链、axis family、base/link/end-effector slot、joint range 派生 |
| 串联 prismatic / telescoping / slide | `twojoint_prismatic_chain`, `threestage_telescoping_slide` | nested overlap、rail/socket 接口、prismatic range、coaxial stage seed domain |
| 单铰链 / 翻盖 / 门 | `single_revolute_hinge`, `zippo_lighter`, `singleleaf_drawbridge`, `wheelie_bin_with_hinged_lid`, `paper_cutter_guillotine` | hinge line、pin/barrel、closed pose、gated second DOF、captured-pin overlap |
| 连续旋转 / rotor / wheel | `wind_turbine`, `traditional_windmill`, `overshot_waterwheel`, `turntable`, `single_rotor_helicopter` | hub/shaft axis、radial multiplicity、bearing topology、continuous joint 语义 |
| 支撑/载具/接地结构 | `wheelbarrow`, `parabolic_dish_on_azimuth_elevation_mount`, `globe` | ground contact plane、support spine、parallel children、yaw/elevation stack |
| 多 slot + 可选机构 | `lighthouse_with_rotating_beacon_assembly`, `metronome`, `bell_tower_with_swinging_bell`, `turnstile_gates`, `casino_machine` | 4-6 slot 宽拓扑、optional moving child、service/accessory gates、topology diversity 审计 |
| 复杂外形 / mesh / cadquery 保真 | `lighthouse_with_rotating_beacon_assembly`, `usb_drive_with_swivel_cover`, `single_rotor_helicopter`, `metronome` | mesh/lathe/cadquery 不降级、source primitive 保留、visual identity |

参考规则：

- 只学习 modular 组织和修复经验；不能用参考模板替代当前 spec 的 module source。
- 如果当前类别需要 `_modular.py` 的自动装配，优先读第一行架构样板。
- 如果当前类别是 domain-specific mixed graph，读对应拓扑行，再读 0-1 个旧 11 gold-standard 看成熟约束。
- 若参考模板自身与当前 spec 的接口策略冲突，以当前 spec 的 5 星 module source 为准。

## 3. 先判断是否拆分 slug

模块化不是把所有结构都硬塞进一个超宽 slot graph。出现以下情况应拆分或收窄 seed domain：

- 样本存在多个不兼容主运动 spine。
- root 坐标系、承载件、joint chain 或接口点位无法共享。
- 不同结构需要完全不同的 slot graph。
- 某些 module 组合无法通过 MatingContract 或 visible support graph 合法装配。
- `resolve_config` 需要大量互斥降级才能避免无效组合。

如果继续保留单 slug，必须明确当前实现的稳定子域，并让 `config_from_seed` 不采样未成熟组合。

## 4. Module source 改编步骤

对每个 `slot.module` 执行：

1. 读取 source `model.py:Lx-Ly`，标出 part、visual、internal articulation、parent-child 关系、primitive 和尺寸常量。
2. 抽取接口点位：upstream/downstream face、pivot、rail、socket、axis、contact plane 或 symmetry plane。
3. 把源码常量分成 public Config 参数和 ResolvedConfig 派生量。
4. 保留 source primitive 类型；不要把 mesh/lathe/cadquery 结构降级成粗糙 Box/Cylinder。
5. 写 module factory，返回 ModuleBuild 和 InterfaceSpec。
6. 对 separate moving part 写真实 joint metadata 和 MatingContract。
7. 对 non-moving detail 使用 parent visual。
8. 在 `run_<slug>_tests` 中覆盖核心 source adaptation、接口接触、joint 语义和允许 overlap 的局部理由。

## 5. 接口优先的空间约束

成熟 modular 模板先解接口，再落几何：

1. 确定 slot graph 的主约束基准：frame、base、rail、hinge line、axis、socket、contact plane、symmetry plane、linkage pivots。
2. 为每个 module 派生 upstream/downstream InterfaceSpec。
3. 从接口点位派生 module origin、visual 尺寸、clearance、overlap 和 joint origin。
4. 将活动件 closed pose 放在真实容纳关系里：导轨内、铰链边、套筒内、轴承内、支撑面上或对称配对位置。
5. 最后添加装饰和标识。

常见拓扑约束：

| 拓扑 | 主接口 | 关键约束 |
|---|---|---|
| serial chain | upstream/downstream mating faces | child upstream face normal component must match assembler contract |
| parallel children | shared parent panel / chassis face | 每个 child 都有真实 parent visual 和 MatingContract |
| rail / slide | rail slot / guide face | prismatic axis 平行 rail，range 小于 usable length |
| hinge / lid / door | hinge line / barrel | revolute origin 落在可见 hinge，closed pose 贴合开口 |
| telescoping | socket / overlap | range 由 stage length 和 minimum overlap 派生 |
| rotor / platter / wheel | hub / shaft axis | continuous axis 穿过 hub center |
| support / caster / leg | ground contact plane | 接地点共面，轮轴穿过 fork/yoke |
| linkage | pivot pairs | 先解 pivot 几何，再放杆件和 joint |

## 6. Seed domain 和拓扑多样性

- `config_from_seed(0)` 是 anchor 组合。
- Stage 1 其他 seeds 可以使用有限 coverage / curated domain，但只能采样已实现、已测试、可装配的组合，并必须覆盖主要 module、multiplicity、稀有合法组合和 viewer 目检需求。
- Stage 1 coverage seeds 应优先收敛 failure-prone 组合：悬空/漂浮风险、穿模/clearance 风险、joint 轴或 range 风险、closed pose 风险、max multiplicity、bulky module、可选 moving child、长链/多子件装配、互斥 gate 或 fallback 降级路径。
- Stage 1 收敛出的 InterfaceSpec、尺寸派生、compatibility gates 和 validator 应作为 Stage 2 扩展 seed domain 的基础，避免第二阶段放开组合后失败率过高。
- Stage 1 使用 `seed % len(table)` 或 curated table 时，必须明确标注为临时 coverage seed domain，不得宣称为最终 dataset-scale 生成逻辑。
- Stage 2 默认策略是 slot-independent 或 conditionally-independent sampling：先采样上游结构槽，再按显式 gate 采样兼容下游槽。只有少量 anchor / coverage / visual regression seed 可以保留 curated preset。
- 如果某些 module 组合互斥，`resolve_config` 必须显式降级或拒绝；不要让 builder 才失败。
- `slot_choices_for_seed` 必须和实际 build 使用的 choices 一致。
- `module_topology_diversity` 需要至少 5 个通过 seed 的 distinct slot choice tuple；这是 sweep 的最低机械门槛，不是成熟数据生成目标。
- Stage 2 / final 模板应在 1000 个 seed 下达到至少 100 个 topology distinct slot choice tuple。低于 100 时，必须记录原因：样本池确实小、slot 兼容约束强，或 reviewer 明确接受。

## 7. Builder 和 factory 规则

- 顶层 builder 只创建 model、materials、resolved config，并调用 modular assembler 或等价的 slot dispatch。
- Module factory 负责本 module 的 geometry、internal joints、interfaces 和 source adaptation。
- Factory 内可以用 `ctx.rng` 做 module-local 小扰动，但不能改变 slot choice 或高层 topology。
- Repeated objects 用稳定命名：`blade_i`、`link_i`、`rail_pad_i`。
- Mesh / lathe / cadquery helpers 必须参数化、可复现，并继承 source 的 primitive 语义。
- Palette 使用命名材质，不在 factory 里随机裸 RGB。

## 8. Joint 和 MatingContract 规则

- spec 中的活动关系必须变成 articulation，不要只画静态开口状态。
- joint type、axis、origin、range 来自 source 语义和接口基准。
- prismatic axis 平行 rail/slot/socket。
- revolute axis 穿过 hinge/pin/barrel/yoke。
- continuous axis 穿过 hub/shaft。
- 每个 separate child part 必须有可见支撑路径；joint 本身不是支撑。
- 捕获式 pin、shaft、bearing cup 的 intentional overlap 必须用 element-scoped `ctx.allow_overlap(..., elem_a=..., elem_b=..., reason=...)` 声明。

## 9. 自动调参闭环

每轮实现或修复后运行：

```bash
uv run articraft template sweep-pipeline <category_slug>
```

修复顺序：

1. 最大 failure cluster。
2. Interface / MatingContract / visible support 问题。
3. joint origin / axis / range。
4. module_topology_diversity / seed domain。
5. primitive downgrade 或 source adaptation 缺失。
6. 视觉身份和比例。

初步机械完成只有一条：

```text
sweep-pipeline verdict=pass
```

通过后仍要按根协议生成 preview 或 batch viewer 记录，检查 seeds 的类别身份、比例、闭合姿态和运动语义。
