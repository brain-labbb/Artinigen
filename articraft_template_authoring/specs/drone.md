# Drone Spec

## 元信息
| 项 | 值 |
|---|---|
| slug | `drone` |
| template path | `agent/templates/drone.py` |
| test path | `tests/agent/test_drone_template.py` |
| stage | `SPEC_ONLY_DRAFT` |
| status | `pending` |
| __modular__ | `True` |
| pattern | `mixed` (parent airframe + multiplicity rotor arms + 2 parallel-child slots: landing gear + payload undermount) |

`mixed` 解释：本模板有 **4 个槽位**。Slot A (`airframe_body`) 是 root chassis；
Slot B (`rotor_arms`) 是 **multiplicity** 槽位（候选 module 各自决定臂数 N ∈ {4,6,8} 与 fold/fixed 语义，每个臂派生 1 propeller continuous joint，可选 1 fold revolute joint）；Slot C (`landing_gear`) 与 Slot D (`payload_undermount`) 都是 airframe_body 下的 **parallel child**——分别处理"机身下方的接地支撑"与"机身腹下/鼻部的任务挂载"两个独立结构轴（5 星样本中两轴可任意组合）。Slot B、C、D 三个 child slot 都直接挂到 Slot A 的 airframe_body part 上，**不形成 A→B→C→D 串行链**——这是 dj_equipment.py 的 parallel-child 模式（多个独立 child slot 共享 chassis）与 monitor_mount.py 的 multiplicity 模式的混合。

---

## 5 星样本阅读摘要

| 项 | 值 |
|---|---|
| five_star_total | 28 |
| read_count | 28 |
| read_scope | all 5-star samples in this category |
| samples_adopted_as_module_sources | 11 |
| samples_read_but_not_adopted | 17（用于拓扑分类与边界约束，但不被作为候选 module 的 line-range 源） |

注：相比 3-槽位版本，本 spec 把"landing gear"从 Slot D `payload_undermount` 拆出来独立成 Slot C `landing_gear`（grep 28 个 5 星样本显示 gear∈{yes,no}×gimbal∈{yes,no} 4 个组合都存在，是两个独立结构轴）。这导致原本只贡献 airframe 或 rotor_arms 的 3 个样本现在**也**成为 Slot C 的 landing_gear 来源：

下表标注每个 5 星样本的 airframe 家族 / 关键特征 / 在 spec 中的角色：

| record_id | model.py 行数 | airframe family | 关键特征 | spec 角色 |
|---|---|---|---|---|
| `rec_drone_456cea3ca6b74cfe9d77a06909bb21d2` | 520 | folding quad | 4 folding arms + 4 prop spin + no gimbal；body 是 rounded_rect extruded shell + hinge supports | adopted: Slot A `rounded_shell_body`、Slot B `folding_quad_4arm` |
| `rec_drone_098da8da96264548b77a178b65dc143c` | 522 | folding hex | 6 folding arms + hex carbon plate stack + wire-loop landing skids | adopted: Slot A `hex_plate_stack_body`、Slot B `folding_hex_6arm`、**Slot C `wire_loop_skids`** |
| `rec_drone_23234c7162134fad9a7485bd7c256c29` | 624 | racing H-frame quad | 4 fixed arms 板间夹合 + camera_plate REVOLUTE 倾角 + 双桥板架 | adopted: Slot A `racing_h_frame_body`、Slot D `camera_plate_tilt` |
| `rec_drone_5ae12ee0a7154e21baf462db7f024d39` | 577 | cinema quad with 3-axis gimbal | 4 folding arms + 双 landing gear loops + yaw/tilt/roll gimbal + camera | adopted: Slot D `three_axis_gimbal`、**Slot C `tube_legs_pair`** |
| `rec_drone_a48c8e94909f42d3977f58b9f4c01d60` | 472 | cinema folding quad with 3-axis gimbal | similar topology, fuselage + folding arms + pan/tilt/roll gimbal | adopted: Slot D alt source (cross-verifies `three_axis_gimbal`) |
| `rec_drone_3841c83833864d36a7f95384646cad21` | 207 | mini quad fixed-arm with yaw-tilt gimbal | body 固定 4 臂视觉 + yaw bracket + pitch camera (2-DOF gimbal) | adopted: Slot D `yaw_tilt_gimbal` |
| `rec_drone_c412ec996ccb453c8a16d90e5ece0397` | 400 | heavy-lift octo with fold-down landing legs | 8 fixed arms + 4 revolute landing legs（folding gear） | adopted: Slot B `fixed_octo_8arm`、**Slot C `folding_landing_legs`** |
| `rec_drone_f2583ebb6138456fb59b4d2078d6b708` | 346 | heavy octo | 8 propeller continuous + 8 gear_leg revolute | adopted: Slot B cross-verification for `fixed_octo_8arm` |
| `rec_drone_2000ae3805194e03b1fb7794e5ab770a` | 401 | micro indoor quad with battery door | LatheGeometry 圆形 frame + 4 fixed arms + battery_door REVOLUTE | adopted: Slot A `lathe_round_body` |
| `rec_drone_ec15deb1b1234159ad5a153be205291a` | 296 | folding delivery with payload skid | 4 folding arms + REVOLUTE payload_skid hanging from belly | adopted: Slot D `payload_skid` |
| `rec_drone_a0b2fe6ad7d14f75a1c417b5c11148ca` | 408 | prosumer quad with single yaw gimbal | fixed arms 视觉嵌入 airframe + yaw bracket + REVOLUTE camera | adopted: Slot D cross-verification for `yaw_tilt_gimbal` |

以下 17 个 5 星样本被完整阅读但 **未被采用作为某个 module 的 line-range source**，理由如下：

| record_id | airframe family | 未采纳原因 |
|---|---|---|
| `rec_drone_0005` | hex delivery (6 fixed arms + payload pod FIXED) | hex 拓扑由 `rec_drone_098da8da` 覆盖；payload FIXED 不动，被 Slot D `payload_skid` 的 REVOLUTE 变体取代 |
| `rec_drone_01214f7d336b457794817a3ce14c6bf5` | folding quad with 3-axis gimbal | 拓扑与 `rec_drone_a48c8e94` 完全同族；adopted source 选了 a48c 因为它的 gimbal pan/tilt/roll 写法更紧凑 |
| `rec_drone_03e1cb454f134e4a92c3968b9686b8ce` | folding quad (no gimbal) | 同 `rec_drone_456cea3c` folding quad 家族，且无 payload，结构信息不增量 |
| `rec_drone_0645c54490154ab2b0291d20e1f9c855` | fixed-arm delivery with revolute landing_gear | Slot C `folding_landing_legs` 已采用 `rec_drone_c412ec99`（4 条 leg + 标准 fold revolute joints，结构更干净）；本样本作为同族 cross-verification source 保留 |
| `rec_drone_33f6437189534eadbebdc3e782193795` | folding racing quad + camera_pod hinge | 与 `rec_drone_23234c71` racing H-frame + camera tilt 同族；后者更完整 |
| `rec_drone_4ac21bd4944a49fe8a91dfd19dd465f1` | micro indoor quad with battery door | 与 `rec_drone_2000ae38` 同族，且 lathe 圆 body 在 2000ae38 写得更干净 |
| `rec_drone_5889264cec8a4b45931e9ccedb5c4a50` | **tiltrotor VTOL** | 边界外（见 §核心身份）：nacelle tilt + 横轴 prop。不进入默认 seed domain。仅作为 reject-case 与未来 split 候选保留 |
| `rec_drone_621dba9c925d440f8a477ef5eedb603e` | racing H-frame fixed-arm with camera_plate | 与 `rec_drone_23234c71` 同族，结构稍弱 |
| `rec_drone_6f0ab275499c4d118553b0376bc35588` | folding hex | 同 `rec_drone_098da8da` 家族 |
| `rec_drone_7c009298ae884253944afae31040154b` | **fixed-wing VTOL** | 边界外：wing + tail + 横轴 nacelle tilt。不进入默认 seed domain |
| `rec_drone_7d9f445e2c9c4257a743ad06d13ac5f8` | folding quad with 3-axis gimbal | 同 `rec_drone_a48c8e94` 家族 |
| `rec_drone_80fe2589f0654c48beb775a662d4b194` | fixed-arm racing quad | 同 `rec_drone_2000ae38`/`rec_drone_23234c71` 家族 |
| `rec_drone_d180b0d71c9e41199c73fc532f19fbf6` | **fixed-wing VTOL** | 边界外，同 `rec_drone_7c0092`，仅保留为 reject-case |
| `rec_drone_d3916bd34bcd41b1855859ef941d5a58` | **fixed-wing pusher (mapping survey)** | 边界外：单 propeller pusher + 翼 + 尾，不是多旋翼 |
| `rec_drone_e29ba95c174642ac8ea9ad7f084fabba` | **underwater ROV with horizontal thrusters** | 边界外：thrust 轴是 (1,0,0)/(0,1,0) 而非 (0,0,1)，且没有空中飞行 propeller 语义。归类为 ROV 边界 |
| `rec_drone_edcd27bf41e8484184a3a1592e921162` | hex delivery (fixed arms, no fold) | 与 `rec_drone_0005` 同族，且无 payload；line range 不增量 |
| `rec_drone_f365559e6649464e92c7cdab53cb40ec` | agricultural sprayer hex + tank + spray_boom | 把 tank 和 spray_boom REVOLUTE 拼到 airframe 上的特化变体；可作为未来 payload module 候选，但目前 Slot D 已有 4 候选，暂不收录 |

---

## 核心身份

无人机模板的默认成熟域是**多旋翼空中无人机（multirotor aerial drone）**：
中央 airframe body + 从机身径向辐射的 N ∈ {4, 6, 8} 个固定或可折叠 rotor arm
（每个 arm 末端必带 1 个 continuous propeller spin joint），可选机身下方的
payload undermount（云台 / 起落架 / 货箱）。所有 propeller spin 轴 **竖直
(0,0,1)**，对应飞行 thrust 方向。

边界：
- **不包括** tiltrotor VTOL（nacelle 绕横轴 tilt 改变 thrust 方向，例如
  `rec_drone_5889264c`、`rec_drone_d180b0d7`、`rec_drone_7c009298`）—— 需要
  额外 nacelle tilt revolute joint 链，与 multirotor 拓扑不兼容。
- **不包括** fixed-wing / VTOL 混合机（带 wing + tail + 单 pusher propeller，
  例如 `rec_drone_d3916bd3`）—— spine 是 fuselage 而非中心 hub，对称是
  bilateral 而非 radial。
- **不包括** 水下/水面 ROV（thrust 轴非竖直，例如 `rec_drone_e29ba95c`）。
- 边界情况在 spec 中以 reject-case 形式列出；模板的 validator 必须能识别并
  拒绝这些拓扑被错误地塞进 multirotor 默认 seed。

---

## 槽位 + 候选模块表

**4 个槽位**。Slot A 是 root chassis，Slot B 是 multiplicity rotor 阵列，Slot C
是 airframe 下的 parallel-child **landing gear** module（接地支撑结构），Slot D
是 airframe 下的 parallel-child **payload undermount** module（机身腹下/鼻部
任务挂载）。Slot C 与 Slot D 是两个独立结构轴（5 星 grep 显示 gear×payload 4
个组合全有支持），不共享 parent-child 链。每槽位 ≥3 候选。

### Slot A：`airframe_body`

中央 chassis part。决定 root pose 和 rotor 安装基面的几何。

| module_name | 5_star_source | model.py:Lx-Ly | seed=0 anchor | 结构特征 |
|---|---|---|---|---|
| `rounded_shell_body` | `rec_drone_456cea3ca6b74cfe9d77a06909bb21d2` | `data/records/rec_drone_456cea3ca6b74cfe9d77a06909bb21d2/revisions/rev_000001/model.py:L129-L205` | **yes** | ExtrudeGeometry + rounded_rect_profile 顶视圆角矩形机壳；顶面 top_deck、底面 belly_pack、鼻部 nose_chin + forward_sensor_bar、四角 hinge_support + hinge_barrel 给折叠臂提供铰链接口。视觉部件 ~12 个 |
| `hex_plate_stack_body` | `rec_drone_098da8da96264548b77a178b65dc143c` | `data/records/rec_drone_098da8da96264548b77a178b65dc143c/revisions/rev_000001/model.py:L147-L191` | | 六边形 ExtrudeGeometry 上下 carbon_plate + 6 根 standoff 支柱（径向 60° 等分）+ avionics_pod + gps_puck。明显的"工程飞控"外观；视觉部件 ~10 个 |
| `racing_h_frame_body` | `rec_drone_23234c7162134fad9a7485bd7c256c29` | `data/records/rec_drone_23234c7162134fad9a7485bd7c256c29/revisions/rev_000001/model.py:L184-L262` | | 双侧 lower_left/right_rail + front/rear_bridge + center_tray + top_plate + 4 standoff + 4 clamp + flight_stack + camera_bracket + vtx_cap。骨架式 racing H 板，臂直接夹在板间。视觉部件 ~14 个 |
| `lathe_round_body` | `rec_drone_2000ae3805194e03b1fb7794e5ab770a` | `data/records/rec_drone_2000ae3805194e03b1fb7794e5ab770a/revisions/rev_000001/model.py:L34-L72` | | LatheGeometry shell profile 生成的圆形微型机壳 + top_button accent。"toy / consumer indoor" 美学，视觉部件 ~2-3 个（紧凑） |

> 候选 4 个 ≥3，覆盖 rounded extruded 壳 / hex 板叠 / H-frame 板骨 / lathe 圆壳 4 种结构家族。任何两个候选的 part tree 与 visual 数差 ≥3，结构性独立。

### Slot B：`rotor_arms`（multiplicity）

从 airframe 径向延伸的 rotor arms。每个候选 module 同时决定：
**N（rotor 数）** + **fold/fixed 语义** + **arm geometry**。每 1 个 arm 对应
1 个 propeller，每个 propeller 一个 continuous spin joint（轴 (0,0,1)）；
folding 家族额外为每 arm 加 1 revolute fold joint。

| module_name | 5_star_source | model.py:Lx-Ly | seed=0 anchor | 结构特征 |
|---|---|---|---|---|
| `folding_quad_4arm` | `rec_drone_456cea3ca6b74cfe9d77a06909bb21d2` | `data/records/rec_drone_456cea3ca6b74cfe9d77a06909bb21d2/revisions/rev_000001/model.py:L207-L317` | **yes** | N=4 折叠臂。每臂以 hinge_barrel 为铰链中心，REVOLUTE fold + CONTINUOUS prop spin；4 个 prop 部件 + 4 个 arm 部件 = 8 movable parts，加 4 fold + 4 spin = 8 joints |
| `folding_hex_6arm` | `rec_drone_098da8da96264548b77a178b65dc143c` | `data/records/rec_drone_098da8da96264548b77a178b65dc143c/revisions/rev_000001/model.py:L224-L338` | | N=6 折叠臂（6 个 fold + 6 个 spin = 12 joints）。每臂 60° 等分，铰链点在 hex plate 边缘 |
| `fixed_quad_4arm` | `rec_drone_2000ae3805194e03b1fb7794e5ab770a` | `data/records/rec_drone_2000ae3805194e03b1fb7794e5ab770a/revisions/rev_000001/model.py:L86-L252` | | N=4 固定臂（arms 是 airframe.visual，**不**作为 movable part）。仅 4 propeller continuous spin joint。最简拓扑，无 fold；适合 racing / micro 美学 |
| `fixed_octo_8arm` | `rec_drone_c412ec996ccb453c8a16d90e5ece0397` | `data/records/rec_drone_c412ec996ccb453c8a16d90e5ece0397/revisions/rev_000001/model.py:L145-L229` | | N=8 固定臂（arms 是 airframe.visual 上的 arm_mesh 实例 + arm_root_clamp + arm_tip_clamp + motor_pod + motor_cap）。仅 8 propeller continuous spin joint，重型多轴布局 |

> 候选 4 个 ≥3，覆盖 {fold, fixed} × {quad, hex, octo} 中的 4 个合法组合
> （fold-octo 在 5 星样本中未出现，**不**纳入候选）。Slot B 的每个候选
> 显式 fix N；模板不再额外在 module 内随机化 N。这样 multiplicity 体现在
> "选哪个 module" 而非"选完 module 再随机 N"，便于 sweep diversity gate 直接
> 统计 slot_choice。

### Slot C：`landing_gear`（parallel child of airframe）

挂在 airframe 下方的接地支撑 module。对 airframe 是 parallel child，**不**插在
rotor arm 链上。固定式（FIXED）或折叠式（REVOLUTE）。`none` 候选不发任何 part。

| module_name | 5_star_source | model.py:Lx-Ly | seed=0 anchor | 结构特征 |
|---|---|---|---|---|
| `wire_loop_skids` | `rec_drone_098da8da96264548b77a178b65dc143c` | `data/records/rec_drone_098da8da96264548b77a178b65dc143c/revisions/rev_000001/model.py:L193-L222` | | 两根 wire_from_points 弯曲管材作 left/right skid，作为 airframe (center_frame) 的 FIXED visual（不是独立 movable part）。轻量、carbon 美学，适配 hex / racing 家族 |
| `tube_legs_pair` | `rec_drone_5ae12ee0a7154e21baf462db7f024d39` | `data/records/rec_drone_5ae12ee0a7154e21baf462db7f024d39/revisions/rev_000001/model.py:L91-L184` | **yes** | 两个独立的 `left_landing_gear` / `right_landing_gear` part，每个含 carbon 弯管 loop visual；FIXED 到 body，承担机身落地。Cinema/prosumer 经典布局，2 part / 2 FIXED joint |
| `folding_landing_legs` | `rec_drone_c412ec996ccb453c8a16d90e5ece0397` | `data/records/rec_drone_c412ec996ccb453c8a16d90e5ece0397/revisions/rev_000001/model.py:L186-L290` | | N=4（默认 4，可派生 N=8 octo 变体）个 `landing_leg_{index:02d}` part，每个 leg 通过 REVOLUTE `gear_fold_{index}` joint 折叠收起（gear-up 状态）；adapted for heavy-lift / VTOL 美学。每 leg ~5 visual，4 part + 4 REVOLUTE joints |
| `none` | — | — | | 不挂任何 landing gear。airframe 的 body 视觉自身已包含足够接地承载（racing H-frame body 视觉常自带 standoff 充当 mini-foot）。Slot D `payload_skid` 也可代偿接地（payload skid 的 runner 接触 ground plane） |

> 候选 4 个 ≥3。三种结构家族（fixed wire 视觉 / fixed tube part / folding revolute 4-leg），加显式 `none`。

### Slot D：`payload_undermount`（parallel child of airframe）

挂在 airframe 下方 / 鼻部的 payload module。对 airframe 是 parallel child，
**不**插在 rotor arm 链上。每个候选自带自己的 part tree + joint 链。

| module_name | 5_star_source | model.py:Lx-Ly | seed=0 anchor | 结构特征 |
|---|---|---|---|---|
| `three_axis_gimbal` | `rec_drone_5ae12ee0a7154e21baf462db7f024d39` | `data/records/rec_drone_5ae12ee0a7154e21baf462db7f024d39/revisions/rev_000001/model.py:L254-L428` | **yes** | gimbal_yaw → gimbal_tilt → camera 三段链，加 yaw / tilt / roll 三个 revolute joint。4 part（含 camera），3 revolute（payload 内部）+ 1 attach joint 到 airframe。云台是行业代表特征 |
| `yaw_tilt_gimbal` | `rec_drone_3841c83833864d36a7f95384646cad21` | `data/records/rec_drone_3841c83833864d36a7f95384646cad21/revisions/rev_000001/model.py:L129-L183` | | gimbal_yaw bracket + camera 两段链，1 yaw REVOLUTE + 1 pitch REVOLUTE = 2 part / 2 joint。轻量 2-DOF 云台（mini drone 常见） |
| `camera_plate_tilt` | `rec_drone_23234c7162134fad9a7485bd7c256c29` | `data/records/rec_drone_23234c7162134fad9a7485bd7c256c29/revisions/rev_000001/model.py:L351-L405` | | 单 camera_plate REVOLUTE 倾角（racing FPV camera mount）。1 part / 1 joint。固定相机 + 单 tilt 调整角度 |
| `payload_skid` | `rec_drone_ec15deb1b1234159ad5a153be205291a` | `data/records/rec_drone_ec15deb1b1234159ad5a153be205291a/revisions/rev_000001/model.py:L183-L224` | | 单 payload_skid hinged drop runner（送货 / 起落架双用途）。1 part（含 hinge_tube + 双 strut + 双 runner + 前后 crossbar）/ 1 REVOLUTE joint 轴 (0,-1,0) |
| `none` | — | — | | 不挂任何 payload。airframe 直接服务 rotor arms 而已。提供"机器人裸架"美学，并避免与某些 Slot A × Slot B 组合下相机/起落架穿模 |

> 候选 5 个 ≥3。`none` 显式提供"无挂载"语义，覆盖 hex delivery / racing 等本来就没有 payload 的家族。

---

## 槽位图（slot graph）

pattern: `mixed`（parallel children + multiplicity）

```
                            airframe_body            ← Slot A (root chassis)
                         ╱       │        │       ╲
        (radial, N×)    ╱        │        │        ╲ (parallel child)
                       ╱         │        │         ╲
                      ╱   (parallel child)  (parallel child)
                     ╱           │        │           ╲
        rotor_arm_0..N-1   landing_gear  payload_undermount
                              (Slot C)        (Slot D)
        Slot B (multiplicity, N from chosen module)
        each arm:                              fold (REVOLUTE) and/or spin (CONTINUOUS)
            ├── (optional) REVOLUTE fold joint at body rim
            └── propeller_i with CONTINUOUS spin joint, axis (0,0,1)

        Slot C landing_gear:
            FIXED (wire_loop_skids: visual only on airframe / tube_legs_pair: 2 fixed parts)
            or REVOLUTE × N (folding_landing_legs: N=4 fold joints with axis perpendicular
            to body radial direction)
            or skipped (`none`)

        Slot D payload_undermount:
            attached by 1 joint (FIXED or REVOLUTE depending on module).
            The payload's INTERNAL chain (e.g. yaw → tilt → roll → camera) is embedded
            inside the module's own part list.
            Skipped if `none`.
```

关键性质：
- Slot B、C、D 三个 child slot 都 parent 到 airframe_body，互相 **不串联**。
- Slot B 的 multiplicity 由所选 module 内置 N（4/6/8）；不在 module 之外再做
  multiplicity 采样，避免 sweep 难统计 diversity。
- Slot C 候选 `none` 与 Slot D 候选 `none` 互相独立——可以同时 `none`（裸架
  racing topology），也可以一个 `none` 一个非 none。
- Slot C `tube_legs_pair` / `folding_landing_legs` 与 Slot D `payload_skid` 共存时
  存在物理穿插风险（hinge 重叠），由 `resolve_config` 的兼容矩阵 fallback 处理。

参考实现 pattern：`agent/templates/dj_equipment.py` 的 parallel-child
"do not declare upstream interface, parent directly to chassis" 习惯 +
`agent/templates/monitor_mount.py` 的 multiplicity module（per-N 一个 module 名）混合。

---

## 部件（Parts）

按槽位组织。每个 module 候选下列出它会 emit 的 part 名和 visual 概览。

### Slot A / module `rounded_shell_body`
| part | visual_count | 描述 | 来源 |
|---|---|---|---|
| `body` | ~12 | rounded-rect extruded shell + top_deck + belly_pack + nose_chin + forward_sensor_bar + rear_vent + 4 pod boxes + 4 hinge_support + 4 hinge_barrel | `rec_drone_456cea3c...:model.py:L129-L205` |

### Slot A / module `hex_plate_stack_body`
| part | visual_count | 描述 | 来源 |
|---|---|---|---|
| `body` | ~10 | hex lower_plate + hex upper_plate + 6 standoff + avionics_pod + gps_puck（folding-arm 兼容版可继承 skid wire-loops） | `rec_drone_098da8da...:model.py:L147-L191` |

### Slot A / module `racing_h_frame_body`
| part | visual_count | 描述 | 来源 |
|---|---|---|---|
| `body` | ~14 | lower_left/right_rail + front/rear_bridge + center_tray + top_plate + 4 standoff cyl + 4 clamp + flight_stack + camera_bracket + vtx_cap | `rec_drone_23234c71...:model.py:L184-L262` |

### Slot A / module `lathe_round_body`
| part | visual_count | 描述 | 来源 |
|---|---|---|---|
| `body` | ~2-3 | LatheGeometry frame_shell + top_button accent | `rec_drone_2000ae38...:model.py:L34-L72` |

### Slot B / module `folding_quad_4arm`
| part | visual_count | 描述 | 来源 |
|---|---|---|---|
| `arm_i` × 4 | ~5 each | hinge_barrel + arm_tube + motor_pod + motor_cap + optional nav_light | `rec_drone_456cea3c...:model.py:L207-L317` |
| `propeller_i` × 4 | ~3 each | hub + 2 or 3 blade meshes | 同上 |

### Slot B / module `folding_hex_6arm`
| part | visual_count | 描述 | 来源 |
|---|---|---|---|
| `arm_i` × 6 | ~5 each | 60°-spaced arm booms with hinge fitting + motor pod | `rec_drone_098da8da...:model.py:L224-L338` |
| `propeller_i` × 6 | ~3 each | hub + blades | 同上 |

### Slot B / module `fixed_quad_4arm`
| part | visual_count | 描述 | 来源 |
|---|---|---|---|
| `propeller_i` × 4 | ~3 each | hub + blades；arm 视觉是 airframe.visual，不作 movable part | `rec_drone_2000ae38...:model.py:L86-L252` |

### Slot B / module `fixed_octo_8arm`
| part | visual_count | 描述 | 来源 |
|---|---|---|---|
| `propeller_i` × 8 | ~3 each | 8 个 prop，每 45° 一个；arm 视觉作 airframe.visual 的 arm_mesh + clamps + motor_pod + motor_cap 实例 | `rec_drone_c412ec99...:model.py:L145-L229` |

### Slot C / module `wire_loop_skids`
| part | visual_count | 描述 | 来源 |
|---|---|---|---|
| (none — visuals attached to airframe `body` directly) | 2 | `left_skid` + `right_skid` 两个 wire-loop visual 通过 `.visual(name="left_skid"/"right_skid")` 加到 airframe body part 上，不创建独立 movable part | `rec_drone_098da8da...:model.py:L193-L222` |

### Slot C / module `tube_legs_pair`
| part | visual_count | 描述 | 来源 |
|---|---|---|---|
| `left_landing_gear` | ~2 | 单个 carbon 弯管 loop visual + optional fairing | `rec_drone_5ae12ee0...:model.py:L162-L173` |
| `right_landing_gear` | ~2 | 同上，右侧 mirror | `rec_drone_5ae12ee0...:model.py:L176-L185` |

### Slot C / module `folding_landing_legs`
| part | visual_count | 描述 | 来源 |
|---|---|---|---|
| `landing_leg_i` × 4 | ~5 each | gear_mount + gear_brace + leg_strut + foot_pad + ankle_collar | `rec_drone_c412ec99...:model.py:L186-L270` |

### Slot C / module `none`
| part | visual_count | 描述 | 来源 |
|---|---|---|---|
| (none) | 0 | Slot C 跳过，无 part / joint | — |

### Slot D / module `three_axis_gimbal`
| part | visual_count | 描述 | 来源 |
|---|---|---|---|
| `gimbal_yaw` | ~2 | yaw_motor + yaw_hanger | `rec_drone_5ae12ee0...:model.py:L254-L271` |
| `gimbal_tilt` | ~5 | tilt_bridge + 2× hanger + 2× tilt_motor cyl | `rec_drone_5ae12ee0...:model.py:L273-L295` |
| `camera` | ~5 | camera_body + top_plate + roll_crossbar + lens + bezel | `rec_drone_5ae12ee0...:model.py:L297-L332` |

### Slot D / module `yaw_tilt_gimbal`
| part | visual_count | 描述 | 来源 |
|---|---|---|---|
| `gimbal_yaw` | ~3 | yaw bracket cyl + 2 side arm | `rec_drone_3841c838...:model.py:L129-L138` |
| `camera` | ~3 | camera body + lens barrel + lens accent | `rec_drone_3841c838...:model.py:L150-L174` |

### Slot D / module `camera_plate_tilt`
| part | visual_count | 描述 | 来源 |
|---|---|---|---|
| `camera_plate` | ~5 | hinge_tab + mount_spine + plate_panel + camera_body + lens | `rec_drone_23234c71...:model.py:L351-L400` |

### Slot D / module `payload_skid`
| part | visual_count | 描述 | 来源 |
|---|---|---|---|
| `payload_skid` | ~6 | hinge_tube + 2 drop_strut + 2 runner + front_crossbar + rear_crossbar | `rec_drone_ec15deb1...:model.py:L183-L214` |

### Slot D / module `none`
| part | visual_count | 描述 | 来源 |
|---|---|---|---|
| (none) | 0 | 不 emit 任何 part；assembler 跳过 Slot D 的 attach joint | — |

---

## 关节（Joints）

按 slot 分组，列出每个 module 候选会注入的 joints。

### Slot B 注入的关节（每个 rotor_arm 都有）

| 关节 | 类型 | parent | child | axis | range | 描述 |
|---|---|---|---|---|---|---|
| `body_to_arm_i`（folding 家族） | REVOLUTE | `body` | `arm_i` | (0,0,1) 沿垂直铰链销 | `[0, fold_angle_limit]`，典型 `[0, 1.45]` rad | 折叠臂从飞行展开位绕铰链销转到机身侧 |
| `arm_to_propeller_i`（folding 家族） | CONTINUOUS | `arm_i` | `propeller_i` | (0,0,1) 沿电机轴 | 无界 | propeller 绕电机轴自旋 |
| `body_to_propeller_i`（fixed 家族） | CONTINUOUS | `body` | `propeller_i` | (0,0,1) | 无界 | fixed-arm 家族跳过 arm part；propeller 直接 parent 到 body |

### Slot C 注入的关节

| module | 关节 | 类型 | parent | child | axis | range | 来源 |
|---|---|---|---|---|---|---|---|
| `wire_loop_skids` | （无 joint，仅 visual） | — | — | — | — | — | `rec_drone_098da8da...:model.py:L221-L222` |
| `tube_legs_pair` | `body_to_left_landing_gear` | FIXED | `body` | `left_landing_gear` | n/a | n/a | `rec_drone_5ae12ee0...:model.py:L335-L341` |
| `tube_legs_pair` | `body_to_right_landing_gear` | FIXED | `body` | `right_landing_gear` | n/a | n/a | `rec_drone_5ae12ee0...:model.py:L342-L348` |
| `folding_landing_legs` | `gear_fold_i` × 4 | REVOLUTE | `body` | `landing_leg_i` | 沿 leg 根铰链销，垂直 leg 长轴 | `[0, ~1.4]` rad (gear-up / gear-down) | `rec_drone_c412ec99...:model.py:L277+` |
| `none` | — | — | — | — | — | — | — |

### Slot D 注入的关节

| module | 关节链 | 类型 | 来源 |
|---|---|---|---|
| `three_axis_gimbal` | `body → gimbal_yaw` (REVOLUTE, axis (0,0,1)) → `gimbal_tilt` (REVOLUTE, axis (0,-1,0)) → `camera` (REVOLUTE, axis (1,0,0))；3 个 internal revolute | revolute × 3 | `rec_drone_5ae12ee0...:model.py:L349-L428` |
| `yaw_tilt_gimbal` | `body → gimbal_yaw` (REVOLUTE, (0,0,1)) → `camera` (REVOLUTE, (0,1,0))；2 revolute | revolute × 2 | `rec_drone_3841c838...:model.py:L140-L183` |
| `camera_plate_tilt` | `body → camera_plate` (REVOLUTE, (0,1,0)，范围 `[-0.4, 0.4]` rad)；1 revolute | revolute × 1 | `rec_drone_23234c71...:model.py:L386-L405` |
| `payload_skid` | `body → payload_skid` (REVOLUTE, axis (0,-1,0)，范围 `[0, 0.55]` rad)；1 revolute（货箱可下放） | revolute × 1 | `rec_drone_ec15deb1...:model.py:L216-L224` |
| `none` | — | — | — |

**所有 propeller spin axis 必须 (0,0,1)**（与 multirotor thrust 方向一致）。
gimbal yaw 用 (0,0,1)；gimbal tilt 用 ±(0,1,0)；gimbal roll 用 ±(1,0,0)。
偏离这些约定要被 validator 拒绝。

---

## 参数范围汇总

| 参数 | 类型 | 取值范围 / 候选值 | 默认值 (seed=0) | 派生关系 | 来源 |
|---|---|---|---|---|---|
| `airframe_body_module` | enum | `rounded_shell_body` / `hex_plate_stack_body` / `racing_h_frame_body` / `lathe_round_body` | `rounded_shell_body` | Slot A choice | 见 Slot A 表 |
| `rotor_arms_module` | enum | `folding_quad_4arm` / `folding_hex_6arm` / `fixed_quad_4arm` / `fixed_octo_8arm` | `folding_quad_4arm` | Slot B choice；fix N、fix fold semantics | 见 Slot B 表 |
| `landing_gear_module` | enum | `wire_loop_skids` / `tube_legs_pair` / `folding_landing_legs` / `none` | `tube_legs_pair` | Slot C choice；`none` 跳过 Slot C | 见 Slot C 表 |
| `payload_undermount_module` | enum | `three_axis_gimbal` / `yaw_tilt_gimbal` / `camera_plate_tilt` / `payload_skid` / `none` | `three_axis_gimbal` | Slot D choice | 见 Slot D 表 |
| `landing_gear_attach_z_offset` | float | [-0.18, -0.03] | -0.06 | Slot C 接地件相对 body 底面的 z；`folding_landing_legs` 取较小（远）值；`tube_legs_pair` 取中等值；`wire_loop_skids` 直接画在 body 视觉上 | `rec_drone_098da8da...:L193-L222`；`rec_drone_5ae12ee0...:L91-L184`；`rec_drone_c412ec99...:L186-L270` |
| `gear_fold_angle` | float | [0.0, 1.55] rad | 0.0 (gear-down) | `folding_landing_legs` 的 fold REVOLUTE 当前 pose；seed=0 anchor 起飞配置 = 0 | `rec_drone_c412ec99...:L277+` |
| `rotor_count` | derived int | 4 / 6 / 8 | 4 | derived from `rotor_arms_module`；不可独立设置 | — |
| `folding_enabled` | derived bool | true (folding_* modules) / false (fixed_* modules) | true | derived from `rotor_arms_module` | — |
| `body_length` | float | [0.10, 0.55] | 0.36 | airframe 主轴长度；lathe_round 取较小值 | `rec_drone_456cea3c...:model.py:L132`；`rec_drone_2000ae38...:model.py:L41-L61`；`rec_drone_c412ec99...:model.py:L122` |
| `body_width` | float | [0.08, 0.45] | 0.20 | airframe 横向宽度 | 同上 |
| `body_height` | float | [0.025, 0.16] | 0.05 | airframe 垂直高度（顶板到底板） | 同上 |
| `rotor_ring_radius` | float | [0.08, 0.55] | 0.21 | motor center 到 body center 的距离；约束 `arm_length = rotor_ring_radius - hinge_radius - pod_radius` | `rec_drone_456cea3c...:L207-L317`、`rec_drone_098da8da...:L224-L338`、`rec_drone_c412ec99...:L147` |
| `propeller_radius` | float | [0.04, 0.27] | 0.115 | `<= 0.45 * nearest_motor_spacing - clearance`（防 prop-prop / prop-body 穿插） | `rec_drone_456cea3c...:L207-L317`；`rec_drone_c412ec99...:L208-L229` |
| `propeller_blade_count` | int | 2 / 3 | 2 | 决定 prop mesh blade 数 | `rec_drone_456cea3c...:L28-L47`；`rec_drone_098da8da...:L40-L96` |
| `fold_angle_limit` | float | [0.7, 2.3] rad | 1.45 | folding 家族 fold REVOLUTE 上限；clamped by body radius + 相邻臂间距 | `rec_drone_456cea3c...:L300-L317`；`rec_drone_098da8da...:L300-L338` |
| `gimbal_attach_z_offset` | float | [-0.16, -0.02] | -0.05 | Slot D 挂载点相对 body 底面的 z；payload_skid 取较低值 | `rec_drone_5ae12ee0...:L256-L266`；`rec_drone_ec15deb1...:L218-L222` |
| `palette_theme` | enum | `carbon_black` / `racing_red` / `cinema_white` / `industrial_gray` / `safety_orange` | `carbon_black` | 配色主题 | 沿用本类模板惯例（参考 monitor_mount palette） |

注：`rotor_count` 和 `folding_enabled` 是**派生**自 `rotor_arms_module`，**不**是独立参数。这是 multiplicity 槽位的核心约束。

---

## 拓扑多样性审计

**总组合数**：A × B × C × D = 4 × 4 × 4 × 5 = **320**（理论上界）。

减去兼容矩阵 fallback 的非法组合（典型：`wire_loop_skids` + `payload_skid` 物理穿插，`folding_landing_legs` + `payload_skid` 共享挂载点，`lathe_round_body` + `fixed_octo_8arm` 几何不允许等），合法组合数 **≥120**。

预计 `module_topology_diversity` 门控（≥5 distinct slot_choice combos in passing seeds）：**yes，远超 5**。

| slot | candidate_count | 是否 ≥3 | 备注 |
|---|---:|---|---|
| A `airframe_body` | 4 | yes | 4 种结构家族（rounded extruded / hex plate stack / H-frame rails / lathe round），part tree 与 visual 数差 ≥3 |
| B `rotor_arms` | 4 | yes | 4 种 rotor 拓扑（fold-4 / fold-6 / fixed-4 / fixed-8），N + fold 语义 + part tree 都不同 |
| C `landing_gear` | 4 | yes | 4 种 gear 拓扑（wire-loop visual / tube legs 2-part fixed / folding 4-leg revolute / none），joint 数 0→0→4→0 |
| D `payload_undermount` | 5 | yes | 5 种 payload（3-axis gimbal / 2-axis gimbal / single tilt plate / payload skid / none），joint chain 长度从 0 到 3 |

20 seed sweep 期望覆盖 ~15-20 个 distinct (A,B,C,D) 组合，pass_rate ≥ 0.85 应有富余（4 slots 的 distinct slot_choice 集本身就比 3 slots 更细，更容易撞到 ≥5）。

seed=0 anchor：`(rounded_shell_body, folding_quad_4arm, tube_legs_pair, three_axis_gimbal)` —— 这是 5 星样本中的"原型经典 cinema folding quadcopter"，把 `rec_drone_456cea3c` 的 airframe + arms、`rec_drone_5ae12ee0` 的 tube landing gear 与 3-axis gimbal 合成。

---

## Validator（author_run_tests 必须覆盖的点）

- `identity`: airframe_body + ≥4 propeller continuous joints 存在；至少 1 个 part 是 multirotor-style propeller。
- `rotor_count_consistency`: `len(propellers) == rotor_count == N_from_rotor_arms_module`；folding 家族另需 `len(arms) == rotor_count`。
- `propeller_axis_vertical`: 每个 `propeller_*` spin joint 的 axis 必须是 `(0, 0, 1)`（允许浮点 ≤1e-6 误差）。
- `propeller_continuous`: 每个 propeller spin joint 是 `ArticulationType.CONTINUOUS`。
- `folding_arm_axis`（folding 家族）: 每个 `body_to_arm_*` 是 REVOLUTE，axis 沿铰链销（取候选 module 约定的固定轴向），range 在 `[0, fold_angle_limit]`。
- `rotor_ring_radius_consistency`: motor 中心到 body 中心的水平距离 ≈ `rotor_ring_radius`（±5% 容差）。
- `propeller_clearance`: 任意两个 propeller disk 不穿插；propeller 也不穿插 body envelope。
- `gimbal_chain`（Slot D ∈ {`three_axis_gimbal`, `yaw_tilt_gimbal`}）：yaw → tilt → (roll →) camera 的 parent chain 存在；yaw axis (0,0,1)；tilt axis ±(0,1,0)；roll axis ±(1,0,0)。
- `camera_plate_tilt_axis`（Slot D = `camera_plate_tilt`）：唯一 revolute 的 axis ±(0,1,0)。
- `payload_skid_attach`（Slot D = `payload_skid`）：attach joint axis ±(0,1,0)；range upper > 0；skid 的 hinge_tube 与 body 底面接触。
- `landing_gear_consistency`（Slot C ∈ {`tube_legs_pair`, `folding_landing_legs`}）：每个 landing gear part 都通过 FIXED 或 REVOLUTE 关节连到 `body`；不存在浮空 gear part。
- `folding_landing_legs_count`（Slot C = `folding_landing_legs`）：part 数 = fold REVOLUTE joint 数 = 4（或 N 自适应于 rotor_count，但不少于 3）。
- `wire_loop_skids_visual_only`（Slot C = `wire_loop_skids`）：left_skid / right_skid 是 airframe `body` 的 visual，**不**作为独立 part 出现在 `model.parts()` 列表中。
- `landing_gear_ground_contact`（Slot C ∈ {`tube_legs_pair`, `folding_landing_legs`} 且 `gear_fold_angle == 0`）：所有 landing gear 的 lowest visual z 应低于 airframe `body` 的 lowest z，且彼此差 ≥ `body_height * 0.5`（确保机身离地）。
- `slot_c_d_compatibility`：（Slot C, Slot D）∉ `forbidden_pairs`。`forbidden_pairs` 至少包含 `(folding_landing_legs, payload_skid)` 与 `(wire_loop_skids, payload_skid)`（runner 与 skid 共享空间会穿插）。
- `module_topology_diversity`: 在 seeds 0-19 内出现 ≥5 个 distinct (A,B,C,D) slot_choice 组合。
- `seed_0_anchor`: seed=0 必须产出 `(rounded_shell_body, folding_quad_4arm, tube_legs_pair, three_axis_gimbal)`。
- `no_floating`: 所有 part 都有 parent / joint 链通到 root airframe_body；空 Slot C (`none`) / 空 Slot D (`none`) 情况下没有孤立 payload / gear part。
- `slot_c_none_clean`: Slot C = `none` 时不存在 `landing_gear_*` / `landing_leg_*` / `*_skid` 任何 part 名（除非来自 Slot D `payload_skid`）。
- `slot_d_none_clean`: Slot D = `none` 时不存在 `gimbal_*` / `camera*` / `payload_skid` 任何 part 名。

---

## Reject cases（必须能识别并拒绝）

- 没有任何 propeller 或 propeller 不是 continuous joint（变成"固定风扇装饰"）。
- propeller 数与 `rotor_arms_module` 隐含的 N 不一致。
- propeller spin axis 偏离 (0,0,1)（例如水平 thrust 的 ROV、横轴 tiltrotor nacelle 误塞进来）。
- folding 家族 fold revolute axis 不沿铰链销（例如错成水平），导致折叠时穿过机身。
- propeller disk 大幅切入 body 或相邻 propeller（`propeller_radius` 超过 `0.45 * motor_spacing`）。
- Slot D = `three_axis_gimbal` 但缺少 roll 段，或 gimbal_tilt parent 不是 gimbal_yaw（链断）。
- Slot D = `none` 但 part 列表中出现 `camera*` / `gimbal_*`（清理不彻底）。
- Slot C = `folding_landing_legs` 但 `gear_fold_*` joint 非 REVOLUTE，或 leg part 与 fold joint 数不一致。
- Slot C 与 Slot D 选了被 `forbidden_pairs` 禁止的组合，但模板没有 fallback 到合法组合。
- Slot C = `tube_legs_pair` / `folding_landing_legs` 配置下，gear 离地距离 ≤ 0（gear 顶端高于 body 底面，相当于穿过 body）。
- 试图把 wing / tail / nacelle tilt yoke / horizontal-axis thruster 塞进 multirotor airframe（边界外类别误入）。
- airframe_body 是 fuselage 形（长轴 >> 横轴 + 翼根接口），明显是 fixed-wing 域。
- multiplicity Slot B 选了 fold_octo（在 5 星样本中不存在；模板拒绝该非法组合）。

---

## 与相邻类别的边界

- **不该混入 `helicopter`**：helicopter 是单 main rotor + tail rotor（不同 axis），不是径向阵列。模板 Slot B 候选都是 ≥4 旋翼。
- **不该混入 fixed-wing aircraft / `mapping_survey_drone` 类**：spine 是 fuselage 而非中心 hub；翼 + 尾的 bilateral 对称与 radial multirotor 不兼容（参见 `rec_drone_d3916bd3` 边界）。
- **不该混入 tiltrotor VTOL**：nacelle tilt 改变 thrust 方向（横轴 revolute），与本模板的固定 vertical-axis spin 假设冲突（参见 `rec_drone_5889264c`、`rec_drone_d180b0d7`）。可作未来 `drone_tiltrotor` 子模板。
- **不该混入 underwater ROV / 水面无人艇**：thrust 轴非竖直，且通常无 propeller 在空中飞行的 thrust kinematics（参见 `rec_drone_e29ba95c`）。
- **不该混入 `ceiling_fan`**：虽然都是 continuous rotor，但 ceiling_fan 是单 hub + ≥3 blade 视觉部件（blade 不是独立 movable part），轴是从天花板向下；本模板 propellers 是独立 movable parts。
- **不该混入 `model_rocket`**：模型火箭无 propeller、无 thrust 旋转 joint。
- **不该混入 `cantilever_articulated_arm` / `serial_elbow_arm`**：那些是 serial arm，本模板是 radial 阵列 + parallel payload。

---

## 模板实现备注（给后续实现 agent 的提示）

实现阶段挑 reference 模板时，**同时**抄两个：
- `agent/templates/monitor_mount.py` 的 multiplicity 写法（每个 N 一个 module 名 + assembler 不在 module 外部叠 N）。
- `agent/templates/dj_equipment.py` 的 parallel-child 写法（Slot B / C 都不声明 `upstream` interface，而是 `parent=model.get_part(airframe_body_part_name)` 直接 attach）。

共享 helper 建议：
- `_build_propeller_mesh(blade_count, radius, palette)` 用于所有 Slot B 候选 emit propeller visual（fold + fixed 共用）。
- `_build_motor_pod_visual(part, *, radius, length, palette)` 用于把 motor_pod cylinder + cap 加到 fold 家族的 `arm_i` 或 fixed 家族的 `body`。
- `_radial_xy(n, index, radius, phase=0)` 返回第 i 个臂的 (x, y, angle)。fold/fixed 家族共用，Slot C `folding_landing_legs` 也可用（N=4 legs 按 π/4 + i·π/2 等分）。
- `_attach_gimbal_to_airframe(model, airframe_body, xy=(nose_offset, 0), z=gimbal_attach_z_offset)` 用于所有 Slot D gimbal 系列在同一接口挂载。
- `_attach_landing_gear_to_airframe(model, airframe_body, *, gear_module, z=landing_gear_attach_z_offset)` 统一 Slot C 与 airframe 的 mating 入口；不同 module 内部决定 FIXED / REVOLUTE。
- `_compute_ground_clearance(airframe_body, gear_module)` 计算机身离地距离（用于 validator `landing_gear_ground_contact`）。

`allow_overlap` 预期场景：
- propeller hub 与 motor_pod cap 的 captured-pin 重叠（每个 spin joint 都会触发）。
- folding 家族 hinge_barrel 与 arm 根部 sleeve 的 captured-pivot 重叠。
- payload_skid 的 hinge_tube 与 body 底面 hinge mount 的 captured-pivot 重叠。
- 3-axis gimbal 各段 hanger 与下游 part 的 cross-axis pin 重叠（参考 `rec_drone_5ae12ee0` 的 expect_overlap 写法）。
- `folding_landing_legs` 的 gear_mount / gear_brace 与 airframe body 底面的 leg mounting boss 重叠（captured-pivot，每条 leg 触发一次）。
- `tube_legs_pair` 的 carbon loop top 与 body 下沿 mount 接触的 captured-pivot 重叠。

不要 grandfather 的 joint（需要 MatingContract）：
- airframe_body 与 payload_undermount 的 attach joint（cylindrical hinge mount，可用 MatingContract）。
- folding 家族 `body_to_arm_*`（hinge_barrel 与 body hinge_support 形成 boss/socket，可用 MatingContract）。
- `tube_legs_pair` 的 FIXED `body_to_*_landing_gear`（圆管端帽对 body 平面 mount，可用 MatingContract）。
- `folding_landing_legs` 的 REVOLUTE `gear_fold_*`（gear_mount boss/socket，可用 MatingContract）。

要 grandfather 的 joint（pin-through-bushing，无 MatingContract）：
- propeller spin（hub 嵌在 motor_pod cap 内）。
- 3-axis gimbal 各 revolute（each motor 嵌套捕获式）。
- `wire_loop_skids` 没有 joint（视觉直挂 body），无需 grandfather。

multiplicity-N 边缘情况：
- N=8 时，`fold_angle_limit` 需自动 clamp 到 `min(1.45, π/N - safety)` 避免相邻臂折叠时穿插。spec 让模板按 `nearest_motor_spacing` 自动派生。
- `propeller_radius` 必须 `< 0.45 * (2*rotor_ring_radius*sin(π/N)) - clearance`。模板需在 `resolve_config` 中强制 clamp。
- `folding_landing_legs` 默认 4 legs，但若 rotor_arms_module 是 octo（N=8），可派生 8 legs；leg 角度用 `_radial_xy(n=N_legs, phase=π/N_legs)` 错开 rotor 投影点。

Slot C = `none` 时，跳过整个 Slot C build；不要 emit empty part。
Slot D = `none` 时，跳过整个 Slot D build；不要 emit empty part。

`resolve_config` 的 Slot C × Slot D 兼容矩阵（compatibility matrix）：
- `(folding_landing_legs, payload_skid)` 与 `(wire_loop_skids, payload_skid)` 禁止；遇到时把 Slot C fallback 到 `tube_legs_pair`（payload_skid 的 hinge 与 tube legs 不冲突，runner 在 legs 之间下放）。
- `(none, none)` 合法（racing 裸架 + 无挂载，对应 rec_drone_2000ae38 / rec_drone_23234c71 等 5 星）。

---

## 采用源码索引（Adopted Source Index）

为后续实现 agent 提供精确的 line-range 切片指引。每条记录都已在上面槽位表中引用，本表是扁平索引。

| source_id | sample_id | model.py 来源 | 采纳用途 |
|---|---|---|---|
| S1 | `rec_drone_456cea3ca6b74cfe9d77a06909bb21d2` | `data/records/rec_drone_456cea3ca6b74cfe9d77a06909bb21d2/revisions/rev_000001/model.py:L28-L47` | Slot B propeller blade mesh helper |
| S2 | `rec_drone_456cea3ca6b74cfe9d77a06909bb21d2` | `data/records/rec_drone_456cea3ca6b74cfe9d77a06909bb21d2/revisions/rev_000001/model.py:L129-L205` | Slot A `rounded_shell_body` part tree（含 hinge_support / hinge_barrel pod 接口） |
| S3 | `rec_drone_456cea3ca6b74cfe9d77a06909bb21d2` | `data/records/rec_drone_456cea3ca6b74cfe9d77a06909bb21d2/revisions/rev_000001/model.py:L207-L317` | Slot B `folding_quad_4arm` arm + propeller + fold / spin joints |
| S4 | `rec_drone_098da8da96264548b77a178b65dc143c` | `data/records/rec_drone_098da8da96264548b77a178b65dc143c/revisions/rev_000001/model.py:L40-L96` | Slot B hex / fold 共享的 arm boom + propeller blades mesh helper |
| S5 | `rec_drone_098da8da96264548b77a178b65dc143c` | `data/records/rec_drone_098da8da96264548b77a178b65dc143c/revisions/rev_000001/model.py:L147-L191` | Slot A `hex_plate_stack_body` part tree |
| S6 | `rec_drone_098da8da96264548b77a178b65dc143c` | `data/records/rec_drone_098da8da96264548b77a178b65dc143c/revisions/rev_000001/model.py:L224-L338` | Slot B `folding_hex_6arm` arm + propeller + fold / spin joints |
| S7 | `rec_drone_23234c7162134fad9a7485bd7c256c29` | `data/records/rec_drone_23234c7162134fad9a7485bd7c256c29/revisions/rev_000001/model.py:L184-L262` | Slot A `racing_h_frame_body` part tree |
| S8 | `rec_drone_23234c7162134fad9a7485bd7c256c29` | `data/records/rec_drone_23234c7162134fad9a7485bd7c256c29/revisions/rev_000001/model.py:L351-L405` | Slot D `camera_plate_tilt` part + single tilt joint |
| S9 | `rec_drone_2000ae3805194e03b1fb7794e5ab770a` | `data/records/rec_drone_2000ae3805194e03b1fb7794e5ab770a/revisions/rev_000001/model.py:L34-L72` | Slot A `lathe_round_body` LatheGeometry frame shell |
| S10 | `rec_drone_2000ae3805194e03b1fb7794e5ab770a` | `data/records/rec_drone_2000ae3805194e03b1fb7794e5ab770a/revisions/rev_000001/model.py:L86-L252` | Slot B `fixed_quad_4arm` arms as airframe visuals + 4 propeller continuous joints |
| S11 | `rec_drone_c412ec996ccb453c8a16d90e5ece0397` | `data/records/rec_drone_c412ec996ccb453c8a16d90e5ece0397/revisions/rev_000001/model.py:L100-L143` | Slot A alt heavy-octo airframe（与 hex_plate 类似，但矩形板，可启发 N=8 时 hex_plate 适配） |
| S12 | `rec_drone_c412ec996ccb453c8a16d90e5ece0397` | `data/records/rec_drone_c412ec996ccb453c8a16d90e5ece0397/revisions/rev_000001/model.py:L145-L229` | Slot B `fixed_octo_8arm` 8 arm/clamp/motor_pod visuals + 8 propeller continuous joints |
| S13 | `rec_drone_5ae12ee0a7154e21baf462db7f024d39` | `data/records/rec_drone_5ae12ee0a7154e21baf462db7f024d39/revisions/rev_000001/model.py:L254-L332` | Slot D `three_axis_gimbal` gimbal_yaw / tilt / camera part tree |
| S14 | `rec_drone_5ae12ee0a7154e21baf462db7f024d39` | `data/records/rec_drone_5ae12ee0a7154e21baf462db7f024d39/revisions/rev_000001/model.py:L349-L428` | Slot D `three_axis_gimbal` yaw + tilt + roll revolute joints |
| S15 | `rec_drone_a48c8e94909f42d3977f58b9f4c01d60` | `data/records/rec_drone_a48c8e94909f42d3977f58b9f4c01d60/revisions/rev_000001/model.py:L244-L338` | Slot D `three_axis_gimbal` 第二参考（更紧凑的 pan/tilt/roll 写法，可交叉验证 axis 约定） |
| S16 | `rec_drone_3841c83833864d36a7f95384646cad21` | `data/records/rec_drone_3841c83833864d36a7f95384646cad21/revisions/rev_000001/model.py:L129-L183` | Slot D `yaw_tilt_gimbal` 2-DOF 云台 part + 2 revolute |
| S17 | `rec_drone_ec15deb1b1234159ad5a153be205291a` | `data/records/rec_drone_ec15deb1b1234159ad5a153be205291a/revisions/rev_000001/model.py:L183-L224` | Slot D `payload_skid` payload_skid part + 1 attach revolute |
| S18 | `rec_drone_098da8da96264548b77a178b65dc143c` | `data/records/rec_drone_098da8da96264548b77a178b65dc143c/revisions/rev_000001/model.py:L193-L222` | Slot C `wire_loop_skids` wire_from_points skid visuals attached to airframe body |
| S19 | `rec_drone_5ae12ee0a7154e21baf462db7f024d39` | `data/records/rec_drone_5ae12ee0a7154e21baf462db7f024d39/revisions/rev_000001/model.py:L91-L184` | Slot C `tube_legs_pair` left/right_landing_gear part + carbon loop visual |
| S20 | `rec_drone_5ae12ee0a7154e21baf462db7f024d39` | `data/records/rec_drone_5ae12ee0a7154e21baf462db7f024d39/revisions/rev_000001/model.py:L335-L348` | Slot C `tube_legs_pair` FIXED body→landing_gear attach joints + contact tests |
| S21 | `rec_drone_c412ec996ccb453c8a16d90e5ece0397` | `data/records/rec_drone_c412ec996ccb453c8a16d90e5ece0397/revisions/rev_000001/model.py:L86-L100` | Slot C `folding_landing_legs` landing_leg_strut mesh helper |
| S22 | `rec_drone_c412ec996ccb453c8a16d90e5ece0397` | `data/records/rec_drone_c412ec996ccb453c8a16d90e5ece0397/revisions/rev_000001/model.py:L186-L290` | Slot C `folding_landing_legs` N×leg parts + gear_fold REVOLUTE joints |

---

## 审核记录

| 项 | 结论 |
|---|---|
| reviewer status | pending |
| reviewer notes | SPEC_ONLY_DRAFT；等待人工审核。模板 scope 收窄为 multirotor aerial drone (4/6/8 rotors, optional fold)；tiltrotor / fixed-wing VTOL / ROV / fixed-wing pusher 显式排除并在 Reject cases 中列出。**本版相比上一版把 landing_gear 从 Slot D payload_undermount 拆出成独立 Slot C**（5 星 grep 验证 gear 和 gimbal 是两个独立轴，4 个组合都有样本支持），4 槽位拓扑数 4×4×4×5=320（合法 ≥120）。如果 reviewer 想要更激进的 multiplicity（在 Slot B 内部再让 N 浮动），可改为 `multiplicity` pattern + 模板里再加 N_min/N_max；当前定为每个 Slot B module 固定 N，便于 sweep diversity gate 直接 distinct 计数。 |
