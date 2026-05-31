# Graphics Card With Cooling Fans Spec

## 元信息
| 项 | 值 |
|---|---|
| slug | `graphics_card_with_cooling_fans` |
| template path | `agent/templates/graphics_card_with_cooling_fans.py` |
| test path | `tests/agent/test_graphics_card_with_cooling_fans_template.py` |
| stage | `SPEC_ONLY_DRAFT` |
| status | `pending` |
| __modular__ | `True` |
| pattern | `parallel_children` |

`parallel_children`: 一个 `card_body` (PCB + heatsink + io_bracket 嵌入式 visuals) 作为根
chassis；shroud cover / cooler assembly fans / rear_peripherals_form (backplate, io_bracket)
都以并联子件形式 parent 回 `card_body`。fan rotors 用 `CONTINUOUS` joints
（axis=(0,0,1), origin=fan_center），其它结构件用 `FIXED`。

可选 `support_brace`（来自正交特征 `support_brace_style`，**不**属于任何 slot）用
`REVOLUTE` 接到 `card_body`；与 3 个 slot 正交（不增加 slot 数量，但产生独立 part 与
articulated joint）。

3 个槽位（A pcb_chassis_form / B cooler_assembly / C rear_peripherals_form）。Slot C 已
从原"维度混合"版本（含 support brace）重构为沿"rear peripheral 打包风格"一条干净的轴。
support brace 因 5 星样本只有 2 个独立来源（rec_9d1b234 prop_leg, rec_f0bbba fold_arm），
不足以构成 ≥3 候选的独立 slot；故降级为顶层 enum 参数，由兼容矩阵决定能否启用。

## 5 星样本阅读摘要
| 项 | 值 |
|---|---|
| five_star_total | 12 |
| read_count | 12 |
| read_scope | all 5-star samples in this category |
| samples_adopted_as_module_sources | 12 |
| samples_read_but_not_adopted | 0 |

每个 5 星样本及其在 spec 中的作用：

| record_id | role | 关键拓扑特征 |
|---|---|---|
| `rec_graphics_card_with_cooling_fans_6b578a4bcb04462796ae053915388353` | adopted → Slot A.compact_short_dual_slot + Slot B.single_axial_fan_compact | mini-ITX 短卡 (0.170×0.105)，单个大轴流风扇 (R=0.039)，stator spoke + bearing pin |
| `rec_graphics_card_with_cooling_fans_f0bbba958ef2467c901571d8aecae30f` | adopted → Slot A.compact_short_dual_slot + 正交 `support_brace_style=fold_arm` | 短卡 (0.195×0.105) + 双轴流风扇 + 折叠支撑臂 (REVOLUTE axis (0,1,0)) |
| `rec_graphics_card_with_cooling_fans_42e0f851eb70466091e3e4b04ebf9ab1` | adopted → Slot A.standard_dual_slot + Slot B.dual_axial_fan_pair + Slot C.embedded_io_and_backplate | PCB 0.285×0.110 + 双等距风扇 + cadquery shroud + raised lip + io/backplate 内联 visuals |
| `rec_graphics_card_with_cooling_fans_48c10853ee634eb6a3a86e0d46be99cc` | adopted → Slot B.dual_axial_fan_pair (alt) | 双不对称风扇 (-0.042, 0.082) + ExtrudeWithHoles shroud + BezelGeometry fan frame |
| `rec_graphics_card_with_cooling_fans_e40d5752e2eb4bb898152f62c7db58e8` | adopted → Slot C.separate_backplate_and_io_parts (anchor) | 分件 PCB/heatsink/shroud/backplate/io_bracket，shroud 父风扇，体现 parallel_children 链路 + 独立 backplate/io_bracket parts |
| `rec_graphics_card_with_cooling_fans_0003` | adopted → Slot C.separate_backplate_and_io_parts (alt) | 多 part 分件 (pcb, heatsink, shroud, bracket, fans)，Y-up 坐标也证明 axis 取板法线 |
| `rec_graphics_card_with_cooling_fans_6b65bf4ce88544ce8089393fa18d2297` | adopted → Slot A.long_triple_slot + Slot B.triple_axial_fan_equal | 0.330×0.125 长卡 + 三等距轴流风扇 + cadquery 多边形 shroud |
| `rec_graphics_card_with_cooling_fans_0004` | adopted → Slot B.triple_axial_fan_equal (anchor) + Slot C.separate_backplate_and_io_parts (alt) | 三等距风扇 + 完整 parallel_children (card_core parents shroud, backplate, io_bracket, 3 fans) |
| `rec_graphics_card_with_cooling_fans_9012571abea94981a464e14fd868f4dc` | adopted → Slot C.flagship_with_top_edge_power_block (anchor) | 三等距风扇 + TorusGeometry bezel + 顶边 8-pin 电源插座 (power_socket + pin grid) |
| `rec_graphics_card_with_cooling_fans_21b89290f63a470e994dc098fbef2ab0` | adopted → Slot C.flagship_with_top_edge_power_block (alt) | 三风扇 + 独立 backplate + bracket parts + power_connector_block on top edge |
| `rec_graphics_card_with_cooling_fans_9d1b234ba6b24c50852792133b616225` | adopted → 正交 `support_brace_style=prop_leg` (anchor) | 三风扇 + REVOLUTE prop_leg (axis (0,0,-1)，hinge_lug + hinge_barrel captured pin) |
| `rec_graphics_card_with_cooling_fans_aa098aaa920e4e52ad8456937df5172e` | adopted → Slot B.dual_large_tail_small_axial | 两个大轴流风扇 (R=0.044) + 一个小尾风扇 (R=0.028)，非对称三风扇布局 |

## 核心身份

带散热风扇的显卡：长条 PCB / heatsink 一体化 chassis、底边 PCIe 金手指、单端 I/O bracket 带视频
输出口、+Z 面的 shroud cover、1-3 个独立轴流风扇 rotor 以 `CONTINUOUS` joints 绕板法线
(`axis=(0,0,1)`) 自由旋转，可选 backplate / 顶边电源插座 / 折叠支撑脚。fan rotor 的叶盘/
hub 必须坐在固定栅格、stator spokes、bezel ring 和 heatsink fin stack 的上方，读作"装在
风扇框上面"的可转动盘；固定栅格可以托住或穿过中心轴，但不能让叶盘整体嵌进散热栅/鳍片层。
fan 数量与
shroud 开口数量必须严格对应；金手指必须在 PCB 底边；I/O bracket 必须在 PCB 一端，**不能**当
成普通主板、独立 case fan 或 CPU 散热塔。

边界：
- 不包括：裸 PCB / 主板 / CPU air cooler tower / standalone case fan / AIO 水冷头单元。
- 不混入：水冷管 + radiator 的整套 AIO 系统（hose 出板外是 GPU AIO hybrid，本模板暂不覆盖）。
- 不混入：blower / squirrel-cage 鼓风式风扇（轴沿板长方向，与本类别 dominant 轴流语义冲突；
  12 个 5 星样本里没有一个是 blower-style，故不纳入候选）。

## 槽位 + 候选模块表

3 个 slot。Slot 多样性来自：(A) chassis 长/槽数, (B) cooler 风扇数/布局, (C) 后端 rear panel /
support brace 形态。每 slot ≥3 候选，每候选源自一个**不同**的 5 星记录。

### Slot A：pcb_chassis_form

card_body 的整体尺寸 + slot 高度 + heatsink + heatpipe 主架。决定后续 fan 数量上限、
shroud 长度、I/O bracket 高度。

| module_name | 5_star_source | model.py:Lx-Ly | seed=0 anchor | 结构特征 |
|---|---|---|---|---|
| `compact_short_dual_slot` | `rec_graphics_card_with_cooling_fans_6b578a4bcb04462796ae053915388353` | `L37-L99` | | mini-ITX 短卡 (0.170×0.105×0.0020 PCB, single slot bracket H≈0.057)，heatsink 0.143×0.090×0.009 + 单 fin stack + 2 heatpipes (R=0.0032)，**只允许单个大风扇** |
| `standard_dual_slot` | `rec_graphics_card_with_cooling_fans_42e0f851eb70466091e3e4b04ebf9ab1` | `L23-L122` | **yes** | 标准 desktop 双槽 (0.285×0.110×0.0016 PCB)，aluminum heatsink 0.218×0.078×0.008 + 21 fins + 4 heatpipes，dual-slot bracket H≈0.044，**允许 1-2 风扇** |
| `long_triple_slot` | `rec_graphics_card_with_cooling_fans_6b65bf4ce88544ce8089393fa18d2297` | `L24-L115` | | 长卡 (0.330×0.125 PCB, 0.108 高 bracket = 2.5-slot)，背板 + heatsink_core 0.304×0.107×0.014 + 25 fins + 4 heatpipes，**允许 2-3 风扇**，背板可作为 visual on body |

seed=0 anchor = `standard_dual_slot`：最具代表性的中间项，撑得起 1 / 2 风扇变种，是最容易测的尺寸。

### Slot B：cooler_assembly

shroud 覆盖件 + 风扇数量 + fan rotor articulations。每个风扇是一个独立 part with `CONTINUOUS`
joint，axis=(0,0,1)，origin 在 fan center。fan rotor 用 `FanRotorGeometry` 或等效 blade mesh。
风扇固定层的 Z 顺序必须是：heatsink fins 接触/承托 stator spokes / bezel ring，rotor disk
紧贴在固定风扇框上方；rotor bottom 与 fixed grille top 应是贴合关系（约 0-1mm 间隙或
极浅接触），允许中心 bearing_pin 穿入 hub 作为 captured shaft。禁止两种极端：叶盘整体沉入
鳍片/栅格底部，或整套风扇盘悬空脱离散热栅。

| module_name | 5_star_source | model.py:Lx-Ly | seed=0 anchor | 结构特征 |
|---|---|---|---|---|
| `single_axial_fan_compact` | `rec_graphics_card_with_cooling_fans_6b578a4bcb04462796ae053915388353` | `L100-L193` | | 1 个大轴流风扇 (R=0.039, 9 blades, scimitar) on `BezelGeometry` shroud (opening 0.088 circle)，stator spoke + bearing_pin 形成 captured-pin 重叠；仅与 `compact_short_dual_slot` 兼容 |
| `dual_axial_fan_pair` | `rec_graphics_card_with_cooling_fans_42e0f851eb70466091e3e4b04ebf9ab1` | `L34-L82, L132-L239` | | 2 个等距轴流风扇 (R=0.034, 11 blades, scimitar)，cadquery shroud 带 raised lip，每风扇 stator spoke (x + y cross) + 中央 shaft；fan centers = (-0.050, 0.060) 沿 X 方向 |
| `triple_axial_fan_equal` | `rec_graphics_card_with_cooling_fans_0004` | `L23-L131, L298-L354` | **yes** | 3 个等距 (-0.104, 0.0, 0.104) 大轴流风扇 (R=0.039)，每个风扇是独立 part with hub + hub_cap + 9 blades，CONTINUOUS axis (0,0,1)，配 rail+bridge skeleton shroud；只允许 long_triple_slot 或 standard_dual_slot+long PCB |
| `dual_large_tail_small_axial` | `rec_graphics_card_with_cooling_fans_aa098aaa920e4e52ad8456937df5172e` | `L25-L545` | | 两个大轴流 (R=0.044) + 一个小 tail 轴流 (R=0.028)，centers=(-0.092, 0.020, 0.122)，fan_support_frame helper 提供 annulus + spindle + struts；体现 multiplicity 不强制等径 |

seed=0 anchor = `triple_axial_fan_equal`：最 iconic 的 GPU 形象（PRIMARY anchor 选择与 sample 0004
匹配，0004 是最完整 parallel_children 范本）。

注：fan 数量的多样性通过这 4 个候选的离散结构差异表达（1 / 2 等距 / 3 等距 / 3 不对称），而不是
通过自由整数 `fan_count` —— 与 `MODULAR_TEMPLATE_AUTHORING.md` 的离散 module 哲学一致。

### Slot C：rear_peripherals_form

**沿单一轴**：PCB 后端的 IO bracket + backplate + 电源接口的**整体打包风格**。
原 spec 把这一槽混入了 support brace（一个独立的 articulated 特征），现已剥离
出去——支撑脚由顶层 `support_brace_style` 正交参数控制（见 §参数范围汇总），
不属于本槽。

| module_name | 5_star_source | model.py:Lx-Ly | seed=0 anchor | 结构特征 |
|---|---|---|---|---|
| `embedded_io_and_backplate` | `rec_graphics_card_with_cooling_fans_42e0f851eb70466091e3e4b04ebf9ab1` | `L23-L122` | | IO bracket + backplate（如有）+ 所有显示口 + 电源接口都作为 `card_body` part 的 visuals 内联绘制，**不**产生独立 part / FIXED joint。Compact / mid-tier 卡的最简形态。Power connector 用匿名 Box visual 表达，不强调位置 |
| `separate_backplate_and_io_parts` | `rec_graphics_card_with_cooling_fans_e40d5752e2eb4bb898152f62c7db58e8` | `L287-L370` | **yes** | 独立 `backplate` part（panel + 2 ribs）+ 独立 `io_bracket` part（rounded outline + bracket holes mesh），两者各自通过 FIXED joint 接到 card_body；顶边 power connector 仍作为 card_body visual。最典型的桌面 GPU 后端，所以选为 anchor |
| `flagship_with_top_edge_power_block` | `rec_graphics_card_with_cooling_fans_9012571abea94981a464e14fd868f4dc` | `L184-L233` | | 独立 backplate / io_bracket + **额外**在 PCB 顶边放显式 `power_socket` Box (0.035×0.018×0.018) + 2×4 `power_pin_*` grid + bracket_foot / bracket_tab / 4 display_ports / 2 bracket_holes 完整 brushed_metal io_bracket。Premium / flagship 卡专属 |

seed=0 anchor = `separate_backplate_and_io_parts`：最典型的桌面 GPU 后端，撑住
anchor 组合既包含独立 part（覆盖 e40d5752 / 0003 / 0004 类拓扑）又不引入
flagship 的额外 power block。

> 候选 3 个 ≥3，沿"rear peripheral 是否独立 part / 是否含独立 top-edge power block"单一轴展开。每候选源自不同 5 星记录。
> Sample 21b89290（alt to `flagship_with_top_edge_power_block`）和 sample 0003 / 0004（alt to `separate_backplate_and_io_parts`）作为 cross-verification source，line range 列在 §采用源码索引。

## 槽位图（slot graph）

```
pattern: parallel_children

card_body (root chassis; embeds pcb + heatsink + heatpipes + io_bracket visuals)
   │
   ├──[FIXED]── shroud_cover         (from Slot B; embedded into card_body as visuals
   │                                    in some modules; modeled as separate part only
   │                                    when sample needs it, e.g. e40d5752)
   │
   ├──[CONTINUOUS axis=(0,0,1)]── fan_rotor_0  (Slot B)
   ├──[CONTINUOUS axis=(0,0,1)]── fan_rotor_1  (Slot B, if dual/triple)
   ├──[CONTINUOUS axis=(0,0,1)]── fan_rotor_2  (Slot B, if triple)
   │
   ├──[FIXED]── backplate_part            (Slot C, only in `separate_backplate_and_io_parts`
   │                                       and `flagship_with_top_edge_power_block`;
   │                                       `embedded_io_and_backplate` inlines as visuals)
   ├──[FIXED]── io_bracket_part           (Slot C, same gating as backplate_part)
   │
   └──[REVOLUTE axis=(0,0,-1) or (0,1,0)]── support_brace
                                          (orthogonal feature `support_brace_style`,
                                           NOT a slot; only when style ∈ {prop_leg,
                                           fold_arm} and compatibility matrix allows)
```

所有 fans 是 `card_body` 的并联子件，spin axis 平行于 PCB 法线 +Z。
backplate / io_bracket 是 Slot C 的并联子件（仅 `separate_*` / `flagship_*` 两个候选发出
独立 part，`embedded_io_and_backplate` 候选不发独立 part）。
support_brace 由顶层 enum 参数控制，与 Slot C 候选选择正交：可与任意 Slot C 候选共存
（仅受 Slot A 兼容矩阵限制——见 §参数范围汇总）。

## 部件（Parts）

按 (slot, module) 列出每个候选会 emit 的 part 名 / visual 数量 / 关键 mesh。

### Slot A / `compact_short_dual_slot`
| part | visual_count | 描述 | 来源 |
|---|---|---|---|
| `card_body` | ~25 | PCB (0.170×0.105×0.0020), pcie_contacts (gold strip), io_bracket (single-slot H=0.057), display_port + hdmi_port + 4 bracket_vents, heatsink_base 0.143×0.090, 11 fins (Box), 2 heatpipes (Cylinder pi/2 rotated), shroud (BezelGeometry), 4 shroud_screws | `model.py:L37-L165` 6b578a |

### Slot A / `standard_dual_slot`
| part | visual_count | 描述 | 来源 |
|---|---|---|---|
| `card_body` | ~50 | PCB (0.285×0.110×0.0016), gpu_package (chip footprint), heatsink_base + 21 fins, top-side power_socket, 12 pcie_fingers, io_bracket (H≈0.044) + bracket_foot + screw_ear + 3 display_ports + 5 vent_slots, fan-frame helpers (BezelGeometry) | `model.py:L100-L220` 42e0f851 |

### Slot A / `long_triple_slot`
| part | visual_count | 描述 | 来源 |
|---|---|---|---|
| `card_body` | ~60 | PCB (0.330×0.125), backplate visual (0.307×0.119), heatsink_core 0.304×0.107×0.014, 25 fins, 4 heatpipes, faceted shroud (cadquery), io_bracket 0.010×0.132×0.108 (2.5-slot) + 6 ports, 3 fan motor posts + stator cross | `model.py:L24-L180` 6b65bf |

### Slot B / `single_axial_fan_compact`
| part | visual_count | 描述 | 来源 |
|---|---|---|---|
| `fan_rotor` | 1 mesh (FanRotorGeometry) | outer R=0.039, hub R=0.014, 9 blades scimitar, thickness 0.010 | `model.py:L166-L182` 6b578a |
| (shroud visuals emit ON card_body, not as separate part) | — | BezelGeometry (opening 0.088 circle, outer 0.150×0.100 rounded_rect), stator_spoke_x + spoke_y + stator_hub + bearing_pin + retainer_clip | `model.py:L103-L150` 6b578a |

### Slot B / `dual_axial_fan_pair`
| part | visual_count | 描述 | 来源 |
|---|---|---|---|
| `fan_0`, `fan_1` | 1 rotor mesh each | FanRotorGeometry R=0.034, 11 blades, scimitar, thickness 0.008, spinner hub | `model.py:L69-L86, L223-L239` 42e0f851 |
| (shroud + fan frames as card_body visuals) | — | cadquery shroud (`_shroud_shell`) outer 0.235×0.094×0.012, two cuts at FAN_HOLE_R=0.0395, raised_lip 0.047/0.0395 extrude 0.006 | `model.py:L41-L66, L132-L138` 42e0f851 |

### Slot B / `triple_axial_fan_equal`
| part | visual_count | 描述 | 来源 |
|---|---|---|---|
| `fan_left`, `fan_center`, `fan_right` | 1 hub + 1 hub_cap + 9 blade Box visuals each | hub R=0.013×0.006, hub_cap R=0.016×0.002, blades 0.040×0.009×0.002 at radius 0.022 with yaw + pitch | `model.py:L37-L49, L298-L317` 0004 |
| shroud visuals on `card_body` | ~14 | top_plate + rear_top_rail (rails), 2 bridges + 2 end_frames + 2 bevels + 2 skirts + 2 caps + 12 opening_braces helper | `model.py:L52-L229` 0004 |

### Slot B / `dual_large_tail_small_axial`
| part | visual_count | 描述 | 来源 |
|---|---|---|---|
| `left_front_fan_rotor`, `center_front_fan_rotor` | rotor mesh (`fan_rotor_geometry` annulus + cap + 9 blade Box loop) | outer R=0.044, hub R=0.011, bore 0.0047, thickness 0.0092 | `model.py:L128-L168, L458-L494` aa098 |
| `tail_fan_rotor` | rotor mesh | outer R=0.028, hub R=0.008, bore 0.0037, 7 blades, thickness 0.0076 | `model.py:L496-L513` aa098 |
| shroud visuals on `card_body` | ~25 | gpu_shroud_fascia (faceted ExtrudeWithHoles, 3 holes at varying radii), top/bottom rail + nose/middle/rear bridges + tail upper/lower bar + tail_end_upper/lower frame + per-fan annulus frames + spindles + struts + rear_clips | `model.py:L171-L437` aa098 |

### Slot C / `embedded_io_and_backplate`
| part | visual_count | 描述 | 来源 |
|---|---|---|---|
| (visuals on `card_body`, no separate parts) | 10+ | io_bracket visuals + 显示口 + retention tab + （如有）backplate visuals 全部内联在 card_body 上；不发独立 part；anonymous Box visual 可表达 power connector 大致位置但不命名 | `model.py:L23-L122` 42e0f851 |

### Slot C / `separate_backplate_and_io_parts`
| part | visual_count | 描述 | 来源 |
|---|---|---|---|
| `backplate` | 3 visuals | backplate_panel (board-sized rounded rect) + backplate_rib_top + backplate_rib_bottom; FIXED to PCB at z<0 | `model.py:L287-L310` e40d5752 |
| `io_bracket` | 2 visuals | bracket_plate (ExtrudeWithHoles, 4 small rect cutouts + 1 large) + retention_tab; FIXED at -X end of PCB | `model.py:L312-L329` e40d5752 |

### Slot C / `flagship_with_top_edge_power_block`
| part | visual_count | 描述 | 来源 |
|---|---|---|---|
| `backplate` | 3+ visuals | 同 `separate_backplate_and_io_parts`：独立 backplate part | `model.py:L168-L232` 9012571（visuals on body 风格）或 `L216-L296` 21b89（separate part 风格） |
| `io_bracket` | 6 visuals | 独立 io_bracket part：bracket_plate 0.006×0.136×0.082 brushed_metal + bracket_foot + bracket_tab + 4 display_ports + 2 bracket_holes | `model.py:L168-L232` 9012571 / `L216-L296` 21b89 |
| `power_block` | 9 visuals | 顶边 `power_socket` Box 0.035×0.018×0.018 + 2×4 `power_pin_*` grid (8 pins)；可 FIXED 为独立 part 或作为 card_body 顶边 visual cluster；spec 推荐独立 part 便于 module-level testing | `model.py:L184-L233` 9012571 |

### 正交特征 `support_brace_style`（非 slot；与 Slot C 正交）

当 `support_brace_style ∈ {prop_leg, fold_arm}` 时，模板额外发一个 part 与 1 个 REVOLUTE joint。
当 `support_brace_style == none`（默认，10/12 样本）时跳过整段。Spec 把它列为顶层参数而非 slot，
理由：5 星样本只有 2 个独立 brace style 来源（9d1b234 prop_leg, f0bbba fold_arm），不足以构成 ≥3 候选的 slot（`none` 当 slot 第 3 候选会让 slot 等价于 enum bool，丧失 slot 的结构语义）。

| style | part | visual_count | 描述 | 来源 |
|---|---|---|---|---|
| `prop_leg` | `prop_leg` | 4 visuals | hinge_knuckle Cylinder + hinge_pin Cylinder + leg_beam Box (0.122×0.010×0.008) + foot_pad Box (0.020×0.020×0.007 rubber) | `model.py:L223-L251` 9d1b234 |
| `prop_leg` (hinge attach on card_body) | (visuals on `card_body`) | 4 | hinge_side_bridge + hinge_lug_0 + hinge_lug_1 + hinge_barrel_0 + hinge_barrel_1（captured-pin overlaps declared via `allow_overlap`） | `model.py:L176-L195` 9d1b234 |
| `fold_arm` | `support_brace` | 3 visuals | hinge_knuckle (Cylinder rpy=(pi/2,0,0)) + brace_arm Box (0.185×0.006×0.006, pitched at brace_angle) + brace_foot Box (rubber) | `model.py:L197-L230` f0bbba |
| `fold_arm` (hinge attach on card_body) | (visuals on `card_body`) | 2 | hinge_block (bracket_metal) + hinge_pin (dark_grey, rpy=(pi/2,0,0)) | `model.py:L149-L160` f0bbba |
| `none` | — | 0 | 不发任何 brace part / joint | — |

## 关节（Joints）

按 chain 顺序列出。base chassis = `card_body`，所有移动子件 parent 都是 `card_body`。

| 关节 | 类型 | parent_slot.part | child_slot.part | axis | range | 描述 | 来源 |
|---|---|---|---|---|---|---|---|
| `fan_spin_0` / `fan_left_spin` | CONTINUOUS | A.card_body | B.fan_left / fan_rotor | `(0, 0, 1)` | unbounded | 第一颗 fan 绕 PCB 法线旋转，origin 在 fan_center | sample 0004 L341-L354; 42e0f851 L223-L239; 9012571 L254-L277 |
| `fan_spin_1` / `fan_center_spin` | CONTINUOUS | A.card_body | B.fan_center / fan_1 | `(0, 0, 1)` | unbounded | 第二颗 fan (dual / triple 配置才有) | sample 0004 L341-L354; aa098 L525-L532 |
| `fan_spin_2` / `fan_right_spin` | CONTINUOUS | A.card_body | B.fan_right / fan_2 / tail_fan_rotor | `(0, 0, 1)` | unbounded | 第三颗 fan (triple 配置才有；asymmetric variant 时半径不同) | 0004 L341-L354; 9012571 L268-L277; aa098 L534-L542 |
| `body_to_backplate` | FIXED | A.card_body | C.backplate | n/a | n/a | backplate 平贴 PCB 反面 (z<0)，仅在 `separate_backplate_and_io_parts` 与 `flagship_with_top_edge_power_block` 候选出现 | e40d5752 L358-L364; 0003 L399-L405 |
| `body_to_io_bracket` | FIXED | A.card_body | C.io_bracket | n/a | n/a | io_bracket 贴 PCB 的 -X 端，仅在分件 Slot C 候选出现（不在 `embedded_io_and_backplate`） | e40d5752 L365-L371; 0004 L333-L339 |
| `body_to_power_block` | FIXED | A.card_body | C.power_block | n/a | n/a | power_socket + pin grid 作为独立 part，仅 `flagship_with_top_edge_power_block` 出现 | 9012571 L184-L233; 21b89 L216-L296 |
| `body_to_support_brace` | REVOLUTE | A.card_body | （正交）prop_leg | `(0, 0, -1)` | `[0.0, 1.35]` | 正交特征 `support_brace_style=prop_leg`：prop_leg 折叠 / 展开，origin 在 card_body 后下角 hinge cluster | 9d1b234 L288-L297 |
| `body_to_support_brace` | REVOLUTE | A.card_body | （正交）support_brace | `(0, 1, 0)` | `[0.0, 0.85]` | 正交特征 `support_brace_style=fold_arm`：fold_arm 较小，绕 +Y 翻下，origin 在 hinge_block 中心 | f0bbba L231-L239 |

约束：
- fan 数量 = `len(fan_spin_*) == len(fan_rotor_parts)`，并与所选 Slot B 模块的 N (1/2/3) 完全一致。
- fan axis **必须** 是 (0,0,1)，origin 严格等于 fan_center；不允许沿 X 或 Y 方向。
- fan rotor disk 必须高于固定 grille / stator spokes / bezel ring / fin stack：fan part 的
  rest-pose z-min 应 ≥ fixed grille top z - 0.00075；只有 bearing_pin ↔ hub 的 captured
  shaft overlap 可以例外。
- prop_leg / brace 的 captured-pin 重叠（hinge_pin ↔ hinge_barrel）必须用 `ctx.allow_overlap` 声明。
- support_brace 是**与 Slot C 正交的特征**，是否出现取决于顶层 `support_brace_style` 参数 + 兼容矩阵，不取决于 Slot C 候选。

## 参数范围汇总

| 参数 | 类型 | 取值范围 | 默认 | 派生关系 | 来源 |
|---|---|---|---|---|---|
| `card_length` | float | by chassis module: compact 0.170-0.200, standard 0.270-0.295, long 0.310-0.335 | derived from chassis | drives shroud length, fan center spacing | A 模块 6b578a / 42e0f851 / 6b65bf |
| `card_height` | float | by chassis module: compact 0.100-0.118, standard 0.108-0.120, long 0.120-0.132 | derived | clamps fan_radius | A 模块 |
| `pcb_thickness` | float | `0.0016-0.004` | `0.002` | 装饰参数，不影响拓扑 | 全 12 样本 |
| `slot_bracket_height` | float | by chassis: compact 0.040-0.060, standard 0.040-0.050, long 0.080-0.110 | derived | controls io_bracket Z extent，决定 single/dual/2.5-slot 外观 | A 模块 |
| `fan_radius_primary` | float | by cooler module: single 0.034-0.041, dual 0.030-0.039, triple_equal 0.034-0.041, dual_large_tail 0.040-0.046 | derived from cooler module | `<= min(card_height/2 - margin, fan_pitch/2 - margin)` | B 模块 |
| `fan_radius_tail` | float | `0.024-0.032` (only in `dual_large_tail_small_axial`) | `0.028` | 只在该模块下生效 | aa098 `model.py:L496-L513` |
| `fan_blade_count` | int | `7-11` | `9` | 由 cooler module 决定主流值 | 各 B 模块 |
| `fan_centers_x` | derived | 1: single→`[0]`, 2: dual→`[-L/4, +L/4]`, 3: triple_equal→`[-L/3, 0, +L/3]`, 3: tail→`[-L/3, 0, +L/3*1.0]` with tail smaller | derived | 由 cooler module + card_length 派生 | B 模块 |
| `slot_c_module` | enum | `embedded_io_and_backplate` / `separate_backplate_and_io_parts` / `flagship_with_top_edge_power_block` | `separate_backplate_and_io_parts` | Slot C 选择；决定是否发 backplate / io_bracket / power_block 独立 part | 见 Slot C 表 |
| `power_block_present` | bool | derived from `slot_c_module` | derived | true iff `slot_c_module == flagship_with_top_edge_power_block` | 9012571 / 21b89 |
| `backplate_as_separate_part` | bool | derived from `slot_c_module` | derived | true iff `slot_c_module ∈ {separate_backplate_and_io_parts, flagship_with_top_edge_power_block}` | e40d5752 / 0003 / 9012571 / 21b89 |
| `support_brace_style` | enum (**正交**，非 slot) | `none` / `prop_leg` / `fold_arm` | `none` | 与 3 个 slot 正交的 articulated feature flag；启用时生成 1 个独立 brace part + 1 REVOLUTE joint | 9d1b234 / f0bbba |
| `support_brace_range` | tuple | prop_leg=`[0.0, 1.35]`, fold_arm=`[0.0, 0.85]` | per style | REVOLUTE joint limits, derived from `support_brace_style` | 9d1b234 / f0bbba |
| `palette` | enum | `anchor_black` / `pcb_green_default` / `gunmetal` / `white_studio` / `red_gaming` / `blue_silver` | `red_gaming` for seed=0, otherwise sampled | trim 装饰，不影响拓扑；必须避免全灰单调，至少有 PCB green/gold contacts/copper heatpipes 或红/蓝/白 shroud 之一形成对比 | 全样本 material 集合 + reviewer 色彩要求 |

### 色彩多样性约束

- 不允许整卡只由接近同一灰度的材料组成；灰/银可用于 bracket、heatsink、backplate，但必须有
  PCB green、gold contacts、copper heatpipes、黑色/白色/红色/蓝色 shroud 或 fan contrast。
- seed=0 可使用 `red_gaming` 作为更易审核的默认配色：红色 shroud + 黑色 fan + 绿色 PCB +
  金色触点 + 铜色热管，避免 viewport 中读成一整块灰。
- palette 只改变材质，不改变 part tree、joint count 或 slot tuple；拓扑多样性审计不把 palette
  计入 slot diversity。

## 拓扑多样性审计

Slot 组合数：A (3) × B (4) × C (3) = **36 distinct slot tuples**。
Orthogonal feature `support_brace_style` ∈ {none, prop_leg, fold_arm} → 36 × 3 = **108 完整拓扑**。
并非所有组合都合法（见下面兼容矩阵），但 `resolve_config` 会把 illegal 组合 fold 到最近合法组合。

| slot | candidate_count | 是否 ≥3 | 备注 |
|---|---|---|---|
| A pcb_chassis_form | 3 | yes | compact / standard / long |
| B cooler_assembly | 4 | yes | single / dual / triple_equal / dual_large_tail_small |
| C rear_peripherals_form | 3 | yes | embedded / separate / flagship_top_edge_power（沿单一轴："rear peripheral 是否独立 part / 是否含独立 top-edge power block"） |
| 正交 support_brace_style | 3 | n/a (非 slot) | none / prop_leg / fold_arm；diversity gate **不统计**正交特征，只统计 slot tuple |

兼容矩阵（resolve_config 必须执行的硬约束）：

- `compact_short_dual_slot` ⇔ Slot B 只能 `single_axial_fan_compact` 或 `dual_axial_fan_pair`
  （compact 短卡放不下 3 风扇）。
- `single_axial_fan_compact` ⇔ Slot A 必须 `compact_short_dual_slot`。
- `triple_axial_fan_equal` / `dual_large_tail_small_axial` ⇔ Slot A 必须
  `standard_dual_slot` 或 `long_triple_slot`。
- `compact_short_dual_slot` ⇔ Slot C 只能 `embedded_io_and_backplate` 或
  `separate_backplate_and_io_parts`；`flagship_with_top_edge_power_block` 默认 fold
  到 `separate_backplate_and_io_parts`（compact 卡通常不需独立 power block，电源走小型 6-pin
  可由 anonymous visual 表达）。
- `compact_short_dual_slot` ⇔ `support_brace_style` 只能 `none` 或 `fold_arm`
  （compact 卡不下沉，`prop_leg` fallback 到 `none`）。
- `long_triple_slot` ⇔ `support_brace_style` 倾向 `none` 或 `prop_leg`
  （`fold_arm` 太小撑不住长卡，fallback 到 `prop_leg`）。
- standard_dual_slot 允许全部 3 个 brace style。

合法 slot tuple 估算：
- compact × {single, dual} × {embedded, separate} = 4
- standard × {single?, dual, triple, dual_large_tail} × {embedded, separate, flagship} = ~12
- long × {dual, triple, dual_large_tail} × {embedded, separate, flagship} = 9

**合法 slot tuple ≥ 25**；再乘 orthogonal brace style，**合法完整拓扑 ≥ 60**。
`module_topology_diversity ≥ 5` 门控：**yes，远超**。

预计 `module_topology_diversity` 门控（≥5 distinct slot tuples）：**yes**。
理由：3 个 chassis × 4 个 cooler × 3 个 rear 候选都基于不同 5 星样本，
part 树 / joint count / fan count 均不同；只要 20 seed 各 RNG 一遍即可
轻松覆盖 ≥5 distinct (slot_a, slot_b, slot_c) 三元组。

## Validator（author_run_tests 必须覆盖的点）

- **identity**: card_body 存在；PCB visual / heatsink visual / io_bracket visual 三件齐全；
  PCIe gold finger visual 在 PCB 底边 (y=-card_height/2 附近)。
- **fan count consistency**: `len(continuous_fan_joints) == len(fan_rotor_parts) == cooler_module.fan_count`。
- **fan axis**: 每个 continuous joint 的 `axis == (0,0,1)`（tol 1e-6）。
- **fan origin**: 每个 joint origin 的 z 等于 cooler_module 的 fan_plane_z；x 在
  `fan_centers_x` 列表里；y == 0 (除非 sample 0003 风格 Y-up coord 显式声明)。
- **rotor within frame**: 每个 fan rotor 的 xy AABB 包含在它对应的 shroud opening / bezel
  内部 (`ctx.expect_within` margin 0.001-0.005)。
- **rotor seated on grille**: 每个 fan part 的 rest-pose z-min 必须贴近 fixed grille/stator/bezel
  的 z-max（允许约 -0.001 到 +0.0015 m），同时 fixed bezel/stator 的 z-min 必须接触/轻微进入
  fin stack top（gap 不超过 0.001 m）；禁止风扇叶盘嵌进散热鳍片底部，也禁止风扇总成悬空。
- **spin invariance**: pose 设到 π/2 后 `part_world_position(fan)` 与 rest 一致 (tol 1e-6)。
- **PCIe fingers on bottom edge**: pcie 金手指 visual 的 y 在 PCB 下半边。
- **io_bracket on one end**: io_bracket / bracket_plate visual 的 x 等于 PCB 的 ±max_x。
- **bracket height matches slot module**: slot_bracket_height 与 `slot_bracket_height` 参数
  在 5% 容差内一致。
- **backplate flush** (only when `backplate_as_separate_part == True`):
  `expect_gap(card_body, backplate, axis='z', max_gap=0.001, max_penetration=0.0)`。
- **brace hinge captured** (orthogonal feature, when `support_brace_style ≠ 'none'`)：声明
  `ctx.allow_overlap(card_body, brace, elem_a='hinge_barrel_*', elem_b='hinge_pin', reason=...)`，
  并 `expect_overlap(... axes='z', min_overlap=0.007)`。
- **brace deployed-pose translates foot down** (orthogonal feature)：pose=upper limit 时 foot AABB 的 y 比 stowed 低至少 0.025–0.090 m。
- **brace compatibility** (orthogonal feature)：`(slot_a_module, support_brace_style)` ∉ `forbidden_brace_pairs`（详见 §拓扑多样性审计的兼容矩阵）。
- **power_block top edge** (only when `slot_c_module == flagship_with_top_edge_power_block`):
  power_socket visual 的 y > +card_height/2 - 0.020；power_pin grid 紧邻 socket。
- **no floating parts**: `ctx.fail_if_isolated_parts()` 通过。
- **no rest-pose overlap** (except declared captured-pins): `ctx.fail_if_parts_overlap_in_current_pose()` 通过。

## Reject cases（必须能识别并拒绝）

- 风扇是 visual 而非独立 part / 没有 CONTINUOUS joint。
- fan axis 沿 X 或 Y 方向（轮子语义，非轴流风扇）。
- fan rotor 的叶盘/圆盘沉入 fixed grille、stator spokes、bezel ring 或 heatsink fins 底部；
  中心 bearing pin 捕获 hub 可以 overlap，但叶盘整体必须贴在栅上面。
- fan bezel/stator/rotor 总成与 heatsink fin stack 明显脱离，形成可见悬空层。
- 全模型材质接近同一灰度，缺少 PCB/金手指/热管/彩色 shroud 或 fan contrast。
- fan rotor 数量与 cooler module 声明的 fan count 不一致。
- 多个 fan rotor 半径相同但 X 位置重叠（fan disks 互相穿模）。
- 短 PCB (compact_short_dual_slot) 强行放 3 个等距大风扇。
- triple_axial_fan_equal 风扇沿 Y 方向排布（应沿 X 沿 card length）。
- PCIe fingers 不在 PCB 底边（被放在 shroud 顶面或 io_bracket 上）。
- io_bracket 不在 PCB 一端，或两端都有 bracket。
- support_brace 漂浮（hinge_pin 不与 hinge_barrel/hinge_block overlap）。
- support_brace_prop_leg / fold_arm 的 REVOLUTE range 跨越 PCB 平面（leg 应当向板面外侧或下方
  展开，不应穿过 PCB）。
- backplate 浮在 PCB 上方而非贴在 -Z 面。
- 没有任何 PCIe 金手指 visual（GPU 身份失败）。
- 没有 io_bracket（GPU 身份失败）。
- 没有 shroud 或 fan frame visuals（只是一块板加圆盘）。
- 任何 fan rotor 的 xy AABB 超出对应 shroud opening。

## 与相邻类别的边界

- 不该混入：**bare PCB / motherboard / circuit_board_module**。区分点：本类别必须有 +Z 面
  的 cooler shroud 和至少 1 个 fan rotor 的 CONTINUOUS joint。motherboard 没有 cooler，
  没有 PCIe edge fingers（motherboard 是 PCIe slots 接收端）。
- 不该混入：**CPU air cooler tower** （独立 heatsink+fan 立方体）。CPU cooler 没有 PCB
  作为底板，没有 PCIe fingers，没有 io_bracket。
- 不该混入：**standalone case fan**（80mm/120mm 单 fan 单元）。case fan 是孤立 fan，没有
  PCB / shroud / io_bracket。
- 不该混入：**AIO water cooler pump + radiator** 系统。AIO 有水管走出本体并连接 radiator；
  GPU AIO hybrid 在本模板中不覆盖（reviewer-gated future variant）。
- 不该混入：**blower-style GPU**（squirrel-cage / 鼓风，轴向板长方向）。12 个 5 星样本里
  没有 blower，本模板只覆盖轴流 (axial Z-spin) 拓扑。

## 模板实现备注（可选）

- **共享 helper**：所有 axial fan 候选共享一个 `_make_axial_fan_rotor(radius, hub_radius, blade_count, thickness)`
  helper（FanRotorGeometry 与 hand-built blade box 两种实现都允许；为 stability 优先 FanRotorGeometry）。
- **shroud builder**：每个 Slot B 模块各有自己的 shroud builder（不可共享，因为 outline 不同），
  但都按相同 contract：emit visuals on `card_body` part, 并在 `fan_centers_x` 处留圆孔。
- **fan_centers_x 派生**：必须由 cooler module 内部决定（不要让 user 自由采样 X 列表），
  保证 fan 之间不穿模。
- **captured-pin overlaps**：所有 fan 模块必须为 (fan_rotor.hub ↔ card_body.fan_axle/motor_post/
  bearing_pin) 用 `ctx.allow_overlap(reason="rotor hub captures fixed shaft as bearing")`
  声明；prop_leg/fold_arm 必须为 (brace.hinge_pin/knuckle ↔ card_body.hinge_barrel/hinge_block)
  声明。
- **fan count 多样性策略**：通过 Slot B 的 4 个离散候选模块表达 fan_count ∈ {1, 2, 3}
  （single=1, dual=2, triple_equal=3, dual_large_tail=3），而 NOT 用自由整数
  `fan_count` 参数 —— 这是 MODULAR_TEMPLATE_AUTHORING.md 的离散 module 哲学要求。
  实现时 cooler module 自己持有 `fan_count` 常量。
- **Slot C 分件 vs 嵌入**：标准 backplate 模块用独立 `backplate` part + FIXED joint
  （来自 e40d5752, 0003），而 `backplate_with_top_edge_power_connector` 在 sample 9012571
  里全是 card_body 上的 visuals。实现时建议统一为：所有 Slot C 模块都以独立 part 输出
  （便于 module-level testing），并把 sample 9012571 的 visuals 重打包成 separate `io_assembly` part。
- **anchor 复现性**：seed=0 → A.standard_dual_slot + B.triple_axial_fan_equal +
  C.separate_backplate_and_io_parts + 正交 `support_brace_style=none`。这与 PRIMARY_ANCHOR
  候选 sample 0004 拓扑一致（0004 也是 standard-to-long 双槽 + 三等距风扇 + 标准独立
  backplate + io_bracket parts，无 brace 无 flagship power block）。
- **support brace 作为正交特征**：实现时不要把 `support_brace_*` 包进 Slot C 的某个 module 实现里；
  应该是 assembler 在所有 slot build 完成后，按 `support_brace_style` 参数额外调一次
  `_attach_support_brace_to_card_body(model, card_body, style)` helper。这样可以保证
  Slot C 与 support brace 的实现真正解耦，便于单元测试每个组合。
- **MatingContract**：fan_rotor 的 captured shaft 是 grandfathered overlap，不需要 mating
  contract；backplate↔PCB 用 `expect_gap` 配合 FIXED joint 表达。

## 采用源码索引（Adopted Source Index）

| source_id | sample_id | model.py 来源 | 采纳用途 |
|---|---|---|---|
| S1 | `rec_graphics_card_with_cooling_fans_6b578a4bcb04462796ae053915388353` | `L37-L99` | Slot A.compact_short_dual_slot chassis (mini-ITX) |
| S2 | `rec_graphics_card_with_cooling_fans_6b578a4bcb04462796ae053915388353` | `L100-L193` | Slot B.single_axial_fan_compact rotor + bezel shroud |
| S3 | `rec_graphics_card_with_cooling_fans_42e0f851eb70466091e3e4b04ebf9ab1` | `L23-L122` | Slot A.standard_dual_slot chassis（anchor）|
| S4 | `rec_graphics_card_with_cooling_fans_42e0f851eb70466091e3e4b04ebf9ab1` | `L41-L82, L132-L239` | Slot B.dual_axial_fan_pair shroud (cadquery) + rotor |
| S5 | `rec_graphics_card_with_cooling_fans_48c10853ee634eb6a3a86e0d46be99cc` | `L122-L226` | Slot B.dual_axial_fan_pair alt (BezelGeometry helper, ExtrudeWithHoles shroud) |
| S6 | `rec_graphics_card_with_cooling_fans_6b65bf4ce88544ce8089393fa18d2297` | `L24-L156` | Slot A.long_triple_slot chassis (full backplate + 25 fins + 4 heatpipes) |
| S7 | `rec_graphics_card_with_cooling_fans_0004` | `L23-L131, L298-L354` | Slot B.triple_axial_fan_equal (anchor) + parallel_children pattern reference |
| S8 | `rec_graphics_card_with_cooling_fans_0003` | `L194-L437` | Slot C.separate_backplate_and_io_parts (alt) — multi-part 分件参考 (separate pcb/heatsink/shroud/bracket parts) |
| S9 | `rec_graphics_card_with_cooling_fans_9012571abea94981a464e14fd868f4dc` | `L184-L233` | Slot C.flagship_with_top_edge_power_block (anchor for that candidate; 8-pin + pin grid + brushed io_bracket) |
| S10 | `rec_graphics_card_with_cooling_fans_21b89290f63a470e994dc098fbef2ab0` | `L216-L296` | Slot C.flagship_with_top_edge_power_block (alt) — separate backplate part + bracket + power_connector_block on body |
| S11 | `rec_graphics_card_with_cooling_fans_9d1b234ba6b24c50852792133b616225` | `L176-L297` | 正交 `support_brace_style=prop_leg`（REVOLUTE -Z, hinge_lug + hinge_barrel captured pin） |
| S12 | `rec_graphics_card_with_cooling_fans_aa098aaa920e4e52ad8456937df5172e` | `L25-L545` | Slot B.dual_large_tail_small_axial (asymmetric tail fan, helper geometry) |
| S13 | `rec_graphics_card_with_cooling_fans_e40d5752e2eb4bb898152f62c7db58e8` | `L167-L389` | Slot C.separate_backplate_and_io_parts (anchor) — separate backplate + io_bracket parts |
| S14 | `rec_graphics_card_with_cooling_fans_f0bbba958ef2467c901571d8aecae30f` | `L149-L239` | 正交 `support_brace_style=fold_arm`（REVOLUTE +Y, compact card brace） |

所有 12 个 5 星样本都至少为一个 slot/module 候选提供了几何来源；没有"读了但未采用"的样本。

## 审核记录

| 项 | 结论 |
|---|---|
| reviewer status | pending |
| reviewer notes | SPEC_ONLY_DRAFT; 待人工 reviewer 检查模块兼容矩阵、fan_centers_x 派生公式与 Slot B `single` × Slot A `compact` 的 anchor 退化逻辑。**本版相比上一版把 Slot C 从"维度混合"（backplate + power connector + support brace 3 个轴塞 4 个候选）重构为沿"rear peripheral 打包风格"单一轴的 3 候选**；support brace 因 5 星只有 2 个独立来源（不足 ≥3）从 slot 降为顶层正交 enum 参数 `support_brace_style`，由 (Slot A, brace_style) 兼容矩阵控制。Slot 数仍 3，slot tuple 数 36，加正交 brace style 完整拓扑 108（合法 ≥60）。未进入模板实现阶段。 |
