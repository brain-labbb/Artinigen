# Louvered Shutter Assembly — Modular Spec

## 元信息
| 项 | 值 |
|---|---|
| slug | `louvered_shutter_assembly` |
| template path | `agent/templates/louvered_shutter_assembly.py` |
| test path | `tests/agent/test_louvered_shutter_assembly_template.py` |
| stage | `SPEC_ONLY_DRAFT` |
| status | `pending` |
| __modular__ | `True` |
| pattern | `mixed` (multiplicity over slats + parallel-child leaf hinge + parallel-child tilt rod；4 slots) |

`mixed` 解释：**4 个槽位**。Slot A `frame_topology` 是 root chassis；Slot B `slat_module` 是
multiplicity 槽（每片 slat 是一个 REVOLUTE child）；Slot C `leaf_hinge_kinematics` 决定整扇/
整对绕 jamb 的 leaf hinge 拓扑（fixed / single-leaf / french pair / bifold chain）；Slot D
`tilt_rod_drive` 决定是否有 tilt rod 同步驱动 slat（none / PRISMATIC 可动 rod / FIXED 视觉 rod）。
Slot C 和 Slot D 在 5 星样本里**完全独立**（grep 33 个样本：tilt-rod×leaf-hinge 4 个组合全有
样本支持），故拆为两个独立 slot 而非耦合候选。

## 5 星样本阅读摘要
| 项 | 值 |
|---|---|
| five_star_total | 33 |
| read_count | 33 |
| read_scope | all 5-star samples in this category |
| samples_deep_read | 12 (full file walk-throughs for module-source extraction) |
| samples_skim_classified | 21 (header constants + joint topology pattern only) |
| samples_adopted_as_module_sources | 10 |
| samples_read_but_not_adopted | 23 (used only for parameter-range and topology audit) |

### Sample inventory (33 total)

| record_id | depth | topology classification | adoption |
|---|---|---|---|
| rec_louvered_shutter_assembly_0001 | deep | single side-hinged plantation leaf + flat slats N=11 + tilt-rod-mimic | adopted (slot A.simple_rectangular_frame; slot B.flat_planar_slats anchor source) |
| rec_louvered_shutter_assembly_0003 | deep | fixed rectangular frame + airfoil slats N=12 (no leaf hinge) | adopted (slot B.airfoil_slats; slot C.fixed_no_leaf_hinge) |
| rec_louvered_shutter_assembly_0004 | deep | fixed frame + wide superellipse plantation slats N=8 | adopted (slot B.wide_plantation_slats anchor source) |
| rec_louvered_shutter_assembly_0219c5e7a67f4adb917422bff27a05f2 | deep | louvered DOOR with kick-panel + mid-rail + 21 narrow slats + side hinge | adopted (slot A.paneled_frame_with_mid_rail) |
| rec_louvered_shutter_assembly_0470c5472ccc4d908162c0b9680f9be5 | deep | exterior storm shutter single leaf + 6 wide slats + horizontal control bar | adopted (slot C.single_leaf_side_hinge alt) |
| rec_louvered_shutter_assembly_10126677d9d544658d7f0532547b482f | skim | single leaf + 9 slats + tilt rod | not adopted (overlaps with 7c027fd / 0001 candidate) |
| rec_louvered_shutter_assembly_1456a5556e3f4487a8354bc7e02b50f8 | skim | single leaf + 9 slats + tilt rod | not adopted (parameter overlap with adopted variants) |
| rec_louvered_shutter_assembly_1e0fd6a81fab445ca693a6892585c319 | skim | single plantation leaf | not adopted (no novel topology vs 0001) |
| rec_louvered_shutter_assembly_2050ff87ad7a40f3bea2b945b6a57da2 | skim | fixed frame + 8 superellipse slats | not adopted (similar to 0003/0004) |
| rec_louvered_shutter_assembly_2593913bec5a45b186fd5a89675e9daa | skim | single side-hinged leaf + wide timber slats N=8 | not adopted (similar to 0001) |
| rec_louvered_shutter_assembly_2f5f538466104d2591a1937e3b114b5c | skim | fixed frame + flat slats N=8 | not adopted (covered by 4492bf5f) |
| rec_louvered_shutter_assembly_3df192becff849e997a89c0b2e4936a2 | skim | double french pair + 8 slats/leaf | not adopted (covered by 7c027fd5) |
| rec_louvered_shutter_assembly_41536fbc1fcd4e9d877da125e295e783 | deep | double leaf with mid-rail divider + small upper bank N=4 | adopted (slot A.paneled_frame_with_mid_rail alt source) |
| rec_louvered_shutter_assembly_4492bf5f324e4691a5b50d1de1a2f7c5 | deep | minimal fixed frame + flat slats N=12 (canonical baseline) | adopted (slot A.simple_rectangular_frame anchor; slot C.fixed_no_leaf_hinge anchor) |
| rec_louvered_shutter_assembly_4cef3e6dcd834585848ee7cfd02dc740 | skim | single leaf + control rod | not adopted (covered by 7c027fd5 tilt-rod) |
| rec_louvered_shutter_assembly_54553517611c4467b1ced14026ea876f | deep | single side-hinged storm panel + 8 airfoil slats + stay support arm | adopted (slot C.single_leaf_side_hinge anchor source) |
| rec_louvered_shutter_assembly_66d56074a5e4498aa8adc75e68f0fea9 | deep | louvered closet DOOR (H=2.0) + kick-panel + mid-rail + 12 slats | not adopted as primary (paneled_frame_with_mid_rail already covered by 0219c5e7) |
| rec_louvered_shutter_assembly_6f07da844cb04e3f926b6821d2890686 | skim | fixed frame + 9 slats | not adopted (covered by 4492bf5f / 0003) |
| rec_louvered_shutter_assembly_7267f6d1189e486da335d3f732a1fd04 | skim | single leaf + 11 slats + mid-rail | not adopted (paneled_frame_with_mid_rail already covered) |
| rec_louvered_shutter_assembly_7424390f18194610b0dc17d8b253db86 | skim | double leaf french + lock-rail mid-banks + tilt rods | not adopted (covered by 7c027fd5) |
| rec_louvered_shutter_assembly_76a8d868b4844b629c0547c1a03e5246 | skim | single leaf + 8 slats + tilt rod | not adopted (tilt-rod pattern already covered) |
| rec_louvered_shutter_assembly_77374234b7d94a189b300e03975bee73 | skim | fixed frame + 18 narrow slats (max-N case) | not adopted as primary (informs N_max for flat_planar family) |
| rec_louvered_shutter_assembly_78e9420a6d104009806233de22e6deae | skim | single leaf + 7 slats | not adopted |
| rec_louvered_shutter_assembly_7c027fd83b684e1bb3d2b2f4c2656525 | deep | double french leaf pair + 6 slats/leaf + vertical PRISMATIC tilt rod per leaf | adopted (slot C.double_leaf_french anchor source; slot B.flat_planar_slats secondary reference) |
| rec_louvered_shutter_assembly_a04e2c00b72b418da67df2047e3d0cba | skim | cafe-shutter double leaf + wide slats N=6 | not adopted (covered by 7c027fd5) |
| rec_louvered_shutter_assembly_c1156eea94444e789a404249930997a7 | skim | small fixed frame | not adopted |
| rec_louvered_shutter_assembly_cc42194271cc4e79a2775e8e293f7fc2 | skim | double leaf + 14 slats/leaf + tilt rod | not adopted (covered by 7c027fd5) |
| rec_louvered_shutter_assembly_cd6b32786e5c4247a78b6d28fe29f505 | deep | jamb + bifold leaves (outer↔inner) + 7 slats/leaf + control rod | adopted (slot C.bifold_leaf_pair anchor source) |
| rec_louvered_shutter_assembly_ce525f7d88234687807b25b48f1edf64 | skim | storm shutter + mid-rail | not adopted (covered by 54553517) |
| rec_louvered_shutter_assembly_cf066cf8178b4d75a9b1e27fef609890 | skim | mid-rail panel + slats | not adopted (covered by 41536fbc) |
| rec_louvered_shutter_assembly_d2759605eb0f4d49bdb825400e4fb507 | deep | window outer-frame + single hinged panel + airfoil slats N=12 + FIXED visual tilt rod | adopted (slot B.airfoil_slats anchor source; slot D-equivalent visual-rod evidence) |
| rec_louvered_shutter_assembly_d2d83a900f454b2196a72035cdc28725 | skim | fixed frame + 13 slats + tilt rod (frame_to_tilt_rod) | not adopted (covered by 4492bf5f + d2759605) |
| rec_louvered_shutter_assembly_efc8dc2c210b4b718612b7b6b2a0a8e7 | skim | small fixed frame + 8 wide slats | not adopted |

## 核心身份

百叶窗 / 百叶门组件是一个安装在墙 / 窗洞上的矩形外框（或多叶外框），框内承载一排平行的、可绕水平长轴翻转的 louver slats。articulated 行为的核心是：每片 slat 围绕同方向的 pivot 轴 tilt（典型范围 [-π/2, π/2]），可选地由一根竖直 tilt rod 同步驱动；整组装置可选地通过侧边 vertical hinge 像 casement 一样开合，或者拆成 bifold 两叶折叠。框 + slat array + per-slat pivot 是身份必需，leaf hinge / tilt rod 是可变拓扑。

边界：
- 不包括 rolling shutter（卷帘门 — slat 是连续卷曲条带，不是离散刚体 + per-slat pivot）。
- 不包括 venetian blinds（百叶帘 — slat 由 cord/ladder 悬挂，没有刚性框架 + side stile 捕获 pin）。
- 不包括纯粹 window frame（无 louver slat array）。
- 不包括 raised-panel / louvered closet door 但**没有可动 slat** 的情况（必须有 louver pivot 关节）。
- 不包括 sliding shutter / barn-door style（这些是沿轨道平移，不是 hinge / 框 + tilt）。

## 槽位 + 候选模块表

### Slot A：frame_topology

外部承载框，决定 slat array 的容器形状和 leaf hinge 锚点。

| module_name | 5_star_source | model.py:Lx-Ly | seed=0 anchor | 结构特征 |
|---|---|---|---|---|
| `simple_rectangular_frame` | `rec_louvered_shutter_assembly_4492bf5f324e4691a5b50d1de1a2f7c5` | `model.py:L13-L25` | **yes** | 两根 vertical stile + 两根 horizontal rail，纯矩形 single-bank 框；只有 4 个外框 visual，slat bank 直接占满 inner opening |
| `window_jamb_with_inset_panel` | `rec_louvered_shutter_assembly_d2759605eb0f4d49bdb825400e4fb507` | `model.py:L128-L172` | | 外层 `outer_frame`（jamb + head + sill）+ 内层独立 `panel_frame`（stile + top_rail + bottom_rail），两层框分离 part，panel_frame 是 leaf hinge 子件，slat bank 装在 panel_frame 内 |
| `paneled_frame_with_mid_rail` | `rec_louvered_shutter_assembly_0219c5e7a67f4adb917422bff27a05f2` | `model.py:L25-L42` | | 矩形框 + 中央水平 mid_rail（+ 可选 kick_panel） 把 slat bank 切成 upper / lower 两个独立 louver 区，每区有独立 N，slat pivot 轴方向相同但 z 分布按 bank 切分 |
| `double_jamb_french_frame` | `rec_louvered_shutter_assembly_7c027fd83b684e1bb3d2b2f4c2656525` | `model.py:L40-L77` | | 加宽外框带 head_jamb / sill / center_muntin，左右各留 hinge 位给两片对开 leaf；frame 本体 visual 包括两侧 jamb + head + sill + glass plane + center muntin |

### Slot B：slat_module（MULTIPLICITY slot）

slat bank 的形状家族 + 多个 slat 的 revolute pivot 群。N = louver count is the multiplicity dimension within each family.

| module_name | 5_star_source | model.py:Lx-Ly | seed=0 anchor | 结构特征 / N 范围 |
|---|---|---|---|---|
| `flat_planar_slats_N{N_min..N_max}` | `rec_louvered_shutter_assembly_4492bf5f324e4691a5b50d1de1a2f7c5` | `model.py:L26-L56` | **yes** (N=12) | 长方扁平 Box blade + 两端短 Cylinder pin；每片 slat = REVOLUTE child of frame，axis=(1,0,0) 沿 slat 长轴。N_min=5, N_max=14 |
| `airfoil_slats_N{N_min..N_max}` | `rec_louvered_shutter_assembly_d2759605eb0f4d49bdb825400e4fb507` | `model.py:L84-L116, L282-L332` | | 椭圆 / superellipse 截面通过 `mesh_from_geometry(section_loft(...))` 生成的弧面 louver；blade + 两端 pin + connector_tab；slat 长度 ≈ panel opening width 减去 pin_length；N_min=6, N_max=14 |
| `wide_plantation_slats_N{N_min..N_max}` | `rec_louvered_shutter_assembly_0004` | `model.py:L34-L67, L143-L210` | | 厚而宽的 plantation blade（chord ≈ 0.105，thickness ≈ 0.022）；少数大叶片；两端 pivot + 可选 ring；N_min=3, N_max=7 |
| `narrow_blind_slats_N{N_min..N_max}` | `rec_louvered_shutter_assembly_77374234b7d94a189b300e03975bee73` | `model.py:L15-L60` | | 薄而密的细 slat（chord ≈ 0.05，thickness ≤ 0.008），数量明显更多；适用于 floor-to-ceiling 或 closet-door layout；N_min=10, N_max=21 |

### Slot C：leaf_hinge_kinematics

整体装置的 leaf hinge 拓扑（让整扇 / 整对绕 jamb 打开）。**已剥离 tilt rod**——tilt rod 由独立的 Slot D 控制（5 星样本里 leaf hinge 和 tilt rod 是两个完全独立的轴）。

| module_name | 5_star_source | model.py:Lx-Ly | seed=0 anchor | 结构特征 |
|---|---|---|---|---|
| `fixed_no_leaf_hinge` | `rec_louvered_shutter_assembly_4492bf5f324e4691a5b50d1de1a2f7c5` | `model.py:L48-L57` | **yes** | 无 leaf hinge；frame 是 root，slats 直接 REVOLUTE child of frame；最简形态。**不**含 tilt rod 描述 |
| `single_leaf_side_hinge` | `rec_louvered_shutter_assembly_d2759605eb0f4d49bdb825400e4fb507` | `model.py:L128-L222` | | frame (outer_frame) → leaf (panel_frame) REVOLUTE 围绕 jamb 竖轴（轴=(0,0,±1)），axis offset 在 jamb 内侧；slats parent = leaf。本身**不**绑定 tilt rod；rod 由 Slot D 决定 |
| `double_leaf_french_pair` | `rec_louvered_shutter_assembly_7c027fd83b684e1bb3d2b2f4c2656525` | `model.py:L97-L263` | | 同一 frame 上两个 leaf：`frame_to_leaf_0` 绕 left jamb，`frame_to_leaf_1` 绕 right jamb（轴符号相反），两 leaf 在中央 meeting stile 处闭合；每个 leaf 内部独立 slat bank。tilt rod（如 Slot D 启用）每 leaf 一根 |
| `bifold_leaf_chain` | `rec_louvered_shutter_assembly_cd6b32786e5c4247a78b6d28fe29f505` | `model.py:L36-L48, L147-L174` | | jamb → outer_leaf REVOLUTE 绕 jamb 竖轴 + outer_leaf → inner_leaf REVOLUTE 绕共享侧边竖轴；两叶链折叠；slats 分布在两 leaf 各自内 |

### Slot D：tilt_rod_drive

竖直 tilt rod 的拓扑选择。与 Slot C 完全正交（grep 33 样本：tilt rod 出现在
fixed 框 / single leaf / double leaf / bifold 4 种 Slot C 拓扑下都有出现）。**当多 leaf
时（french / bifold），rod 按 leaf 数复制**（每 leaf 一根独立 rod）。

| module_name | 5_star_source | model.py:Lx-Ly | seed=0 anchor | 结构特征 |
|---|---|---|---|---|
| `none` | `rec_louvered_shutter_assembly_4492bf5f324e4691a5b50d1de1a2f7c5` | `model.py:L13-L101` | **yes** | 不发任何 tilt rod part / 视觉。最简形态，占 33 个 5 星样本中 21 个（无 tilt 关键字）。anchor 选择此候选 |
| `prismatic_vertical_rod` | `rec_louvered_shutter_assembly_7c027fd83b684e1bb3d2b2f4c2656525` | `model.py:L198-L222` | | 每 leaf（或 frame）发 1 个 `tilt_rod` part：vertical Box + N 个 `drive_tab`；leaf 或 frame → tilt_rod PRISMATIC 沿 (0,0,1)，rod_travel ≈ 0.025-0.05；slat tilt 可 mimic 到 rod 位移 |
| `fixed_visual_rod` | `rec_louvered_shutter_assembly_d2759605eb0f4d49bdb825400e4fb507` | `model.py:L282-L349` | | 视觉 rod：在 slats parent（frame 或 leaf）的 visual 列表里画一根竖向 Cylinder + 末端 ring 装饰；**无独立 part / 无 joint**。代表 plantation shutter 风格里"看起来有 rod，实际靠暗销同步"的家族 |

每槽位均 ≥3 候选，每候选源自不同 5 星 record_id（cross-sample diversity 满足）。anchor 三槽位都落在
`rec_..._4492bf5f...`（canonical 最简形态），保证 seed=0 复现真实样本。

## 槽位图（slot graph）

```
pattern: mixed (4 slots)

(seed=0 anchor: simple_rectangular_frame + flat_planar_slats_N12 +
                fixed_no_leaf_hinge + tilt_rod_drive.none)

  Slot A: frame_topology  ──→ root chassis
        │
        ├──── Slot C: leaf_hinge_kinematics（决定 slats_parent_part 是 frame 还是 leaf）
        │       │
        │       ├── fixed_no_leaf_hinge    → slats_parent = frame
        │       ├── single_leaf_side_hinge → jamb/frame ──REVOLUTE axis=(0,0,±1)──→ leaf；slats_parent = leaf
        │       ├── double_leaf_french_pair → frame ──REVOLUTE──→ {leaf_0, leaf_1}；slats_parent = [leaf_0, leaf_1]
        │       └── bifold_leaf_chain      → jamb ──REVOLUTE──→ outer_leaf ──REVOLUTE──→ inner_leaf；slats_parent = [outer_leaf, inner_leaf]
        │
        ├──── Slot B: slat_module (multiplicity N=N_min..N_max)
        │       └── 对每个 slats_parent，发 N 个 `slat_i` REVOLUTE child（axis=(1,0,0)）
        │
        └──── Slot D: tilt_rod_drive（与 Slot C 正交；按 slats_parent 数复制）
                │
                ├── none                   → 不发任何 rod
                ├── prismatic_vertical_rod → 对每个 slats_parent 发 1 `tilt_rod_*` part + 1 PRISMATIC axis=(0,0,1)
                └── fixed_visual_rod       → 对每个 slats_parent 发 1 竖向 Cylinder visual on parent（无 part / 无 joint）
```

四个 slot 之间的关系：
- Slot A 始终是 root。
- Slot C 决定 **slats_parent_part**：一个或多个 leaf part（取决于 C 候选）。
- Slot B 对每个 slats_parent_part 发 N 个 slat（multiplicity）。
- Slot D 对每个 slats_parent_part 复制一份 rod（french 双 leaf → 2 rod，bifold 双 leaf → 2 rod）。

In `fixed_no_leaf_hinge` mode the graph collapses to pure multiplicity（frame is root；N revolute slat children of frame）。In the other Slot C modes the slat-multiplicity sub-tree is replicated under each leaf。Slot D 与 Slot C 完全独立：例如 `single_leaf_side_hinge + none` 是 9 个 5 星样本的拓扑，`fixed_no_leaf_hinge + prismatic_vertical_rod` 是另一个独立组合。

## 部件（Parts）

### Slot A / `simple_rectangular_frame`
| part | visual_count | 描述 | 来源 |
|---|---|---|---|
| `frame` | 4 (2 stile + 2 rail) | 平坦矩形外框，包络整个 louver bay | `rec_..._4492bf5f...:model.py:L13-L25` |

### Slot A / `window_jamb_with_inset_panel`
| part | visual_count | 描述 | 来源 |
|---|---|---|---|
| `outer_frame` | 4-6 (jamb 左右 + head + sill + 可选 glass plane / muntin) | 外层 jamb 框，是 leaf hinge 的 fixed parent | `rec_..._d2759605...:model.py:L128-L172` |
| `panel_frame` | 4 (stile 左右 + top_rail + bottom_rail) | 内层 leaf 框，承载 slat bank；REVOLUTE child of `outer_frame` | `rec_..._d2759605...:model.py:L174-L222` |

### Slot A / `paneled_frame_with_mid_rail`
| part | visual_count | 描述 | 来源 |
|---|---|---|---|
| `frame` | 5-7 (stile 左右 + top_rail + mid_rail + bottom_rail + 可选 kick_panel) | 矩形框含 mid_rail，划出 upper / lower 两个 louver bank；mid_rail 也作为 slat pivot 上下边界 | `rec_..._0219c5e7...:model.py:L25-L42`；`rec_..._41536fbc...:model.py:L36-L57` |

### Slot A / `double_jamb_french_frame`
| part | visual_count | 描述 | 来源 |
|---|---|---|---|
| `window_frame` | 5-7 (jamb 左右 + head + sill + center_muntin + 可选 glass plane + fixed hinge plates) | 加宽矩形外框，左右各设一组 fixed hinge knuckles，预留两片 leaf 的 hinge mount | `rec_..._7c027fd5...:model.py:L40-L95` |

### Slot B / `flat_planar_slats_N`
| part | visual_count | 描述 | 来源 |
|---|---|---|---|
| `slat_i`（i in 0..N-1） | 3 (Box blade + 2 短 Cylinder pin) | 平板 slat，pin 两端嵌入 stile（captured-pin，需要 `allow_overlap`） | `rec_..._4492bf5f...:model.py:L30-L46` |

### Slot B / `airfoil_slats_N`
| part | visual_count | 描述 | 来源 |
|---|---|---|---|
| `slat_i` | 3-4 (loft mesh blade + 2 pin + 可选 connector_tab) | section_loft 曲面 blade，pivot pin 嵌入 stile；可选驱动 tab 朝 tilt rod | `rec_..._d2759605...:model.py:L84-L116, L282-L332` |

### Slot B / `wide_plantation_slats_N`
| part | visual_count | 描述 | 来源 |
|---|---|---|---|
| `slat_i` | 3-4 (厚 chord 较大的 Box / superellipse blade + 2 pin) | 少而宽，间距大；典型 chord ≥ 0.10，N 偏低 | `rec_..._0004:model.py:L34-L67, L143-L210` |

### Slot B / `narrow_blind_slats_N`
| part | visual_count | 描述 | 来源 |
|---|---|---|---|
| `slat_i` | 3 | 薄而密 slat，N 偏高；适配 paneled_frame / louvered-door 高度 | `rec_..._77374234...:model.py:L15-L60` |

### Slot C / `fixed_no_leaf_hinge`
零额外 part；Slot A 的 frame 就是 root，`slats_parent_part = frame`，slats 直接 parent 到 frame。

### Slot C / `single_leaf_side_hinge`
| part | visual_count | 描述 | 来源 |
|---|---|---|---|
| `leaf` | （= Slot A panel_frame 的 part） | slat 的 parent 改为 leaf；leaf 与 outer frame/jamb 之间是 REVOLUTE。**不**含 tilt rod | `rec_..._d2759605...:model.py:L128-L222`；alt `rec_..._7c027fd5...:model.py:L97-L171` |

### Slot C / `double_leaf_french_pair`
| part | visual_count | 描述 | 来源 |
|---|---|---|---|
| `leaf_0`, `leaf_1` | 每个同 single-leaf | 两个 leaf 各自 REVOLUTE child of frame；`slats_parent_part = [leaf_0, leaf_1]`；**不**绑定 tilt rod（由 Slot D 决定是否每 leaf 一根） | `rec_..._7c027fd5...:model.py:L97-L171, L261-L263` |

### Slot C / `bifold_leaf_chain`
| part | visual_count | 描述 | 来源 |
|---|---|---|---|
| `jamb` | 1-2 (standing_jamb + 可选 reveal) | 静止 root，承担 jamb_hinge_hardware | `rec_..._cd6b3278...:model.py:L36-L48` |
| `outer_leaf` | 同 Slot A panel_frame 加 hinge knuckles | REVOLUTE child of jamb（轴=(0,0,1)） | `rec_..._cd6b3278...:model.py:L147-L165` |
| `inner_leaf` | 同 outer_leaf | REVOLUTE child of outer_leaf 围绕共享侧边竖轴；`slats_parent_part = [outer_leaf, inner_leaf]` | `rec_..._cd6b3278...:model.py:L153-L174` |

### Slot D / `none`
零额外 part / joint / visual。

### Slot D / `prismatic_vertical_rod`
| part | visual_count | 描述 | 来源 |
|---|---|---|---|
| `tilt_rod` (per slats_parent) | 1 + N (vertical bar + per-slat drive_tab) | 沿 z 轴 PRISMATIC，rod_travel ≈ 0.03-0.05；可选 mimic 关联 slats。french / bifold 时每 leaf 一根（`tilt_rod_0`, `tilt_rod_1`） | `rec_..._7c027fd5...:model.py:L198-L222` |

### Slot D / `fixed_visual_rod`
| part | visual_count | 描述 | 来源 |
|---|---|---|---|
| (visuals on slats_parent，无独立 part) | 1-2 visuals per slats_parent | 竖向 Cylinder rod_shaft + 可选 末端 ring 装饰；**作为 frame / leaf 的 visual**，不创建独立 part，不引入 joint | `rec_..._d2759605...:model.py:L282-L349` |

## 关节（Joints）

| 关节名 | 类型 | parent.slot | child.slot | axis | origin | range | 描述 |
|---|---|---|---|---|---|---|---|
| `slat_i_pivot` (i in 0..N-1) | REVOLUTE | A.frame 或 C.leaf | B.slat_i | `(1, 0, 0)`（slat 长轴方向） | slat 在 stile 内的两 pin 中线 z=z_i | `[-1.0, 1.0]` rad (典型 ±π/2) | 每片 louver 绕长轴 tilt；N 个独立 joint，是 multiplicity 的核心 |
| `frame_to_leaf` / `frame_to_leaf_0` | REVOLUTE | A.frame（或 outer_frame / window_frame） | C.leaf / leaf_0 | `(0, 0, ±1)` 竖向 | leaf hinge edge 上的 jamb 内侧 | `[0, 1.55]` rad | 单 leaf / french 第一片 side hinge |
| `frame_to_leaf_1` | REVOLUTE | A.window_frame | C.leaf_1 | `(0, 0, ∓1)` 反向竖向 | 对称 jamb 内侧 | `[0, 1.55]` rad | french pair 的第二片，开向相反 |
| `jamb_to_outer` | REVOLUTE | A.jamb（bifold 特化） | C.outer_leaf | `(0, 0, 1)` | jamb 内侧上的竖向 hinge 轴 | `[0, 1.65]` rad | bifold 第一段 |
| `outer_to_inner` | REVOLUTE | C.outer_leaf | C.inner_leaf | `(0, 0, 1)` | outer_leaf 自由侧的共享竖向 hinge | `[-2.75, 0.0]` rad | bifold 第二段（折叠方向相反） |
| `leaf_to_tilt_rod` / `*_rod_slide` (Slot D = `prismatic_vertical_rod`) | PRISMATIC | A.frame 或 C.leaf（== slats_parent） | D.tilt_rod | `(0, 0, 1)` 竖向 | tilt rod guide 中线 | `[-0.04, 0.04]` m | 同步 slat 的 vertical 操作杆。每个 slats_parent 一根 rod |
| `slat_i_mimic` (optional, when Slot D = `prismatic_vertical_rod` 且启用 mimic) | REVOLUTE (mimic) | A/C.leaf | B.slat_i | 同 `slat_i_pivot` | 同上 | source=`slat_0_pivot` 或 `*_rod_slide`，multiplier 派生 | 让 rod 平移 / master slat 同步剩余 slat tilt |
| （无 joint，仅 visual）(Slot D = `fixed_visual_rod`) | — | — | — | — | — | — | 视觉 rod 不引入 joint |

**Grandfathered joints (no MatingContract)**：所有 `slat_i_pivot` — slat 的 pin 是被 stile 的 hole 捕获的 pin-through-bushing，几何上 pin 与 stile 必然重叠（captured-pin），不适合 MatingContract 的 face-meet 模型，由 `ctx.allow_overlap(...)` 显式声明（参见 `rec_..._4492bf5f...:model.py:L68-L77` 测试段落）。Leaf-hinge `frame_to_leaf*` 和 tilt rod `*_rod_slide` 可以挂 MatingContract（lug / barrel / guide-block face-to-face）。

## 参数范围汇总

| 参数 | 类型 | 取值范围 | 默认 | 派生关系 | 来源 |
|---|---|---|---|---|---|
| `frame_width` | float | `0.40 - 1.80` m | `0.66` | window-format vs door-format；door 默认 ≥ 0.70 | S(d2759605):L22; S(0219c5e7):L25-L31 |
| `frame_height` | float | `0.65 - 2.10` m | `1.20` | door-format 用 ≥ 1.80；window-format 0.65-1.50 | S(d2759605):L23; S(0219c5e7):L31; S(66d56074):L19 |
| `frame_depth` | float | `0.030 - 0.090` m | `0.045` | stile / rail Box 的 y-thickness | S(0004):L29 |
| `stile_width` | float | `0.040 - 0.080` m | `0.060` | 占 frame_width 的 8-12% | S(0004):L30; S(d2759605):L33 |
| `rail_height` | float | `0.045 - 0.110` m | `0.075` | top/bottom rail z-thickness | S(0004):L31; S(7c027fd):L34 |
| `panel_layout` (Slot A) | enum | `simple_rectangular_frame` / `window_jamb_with_inset_panel` / `paneled_frame_with_mid_rail` / `double_jamb_french_frame` | `simple_rectangular_frame` (anchor) | 决定 Slot A 子结构 | 各 Slot A 候选 |
| `slat_family` (Slot B) | enum | `flat_planar` / `airfoil` / `wide_plantation` / `narrow_blind` | `flat_planar` (anchor) | 决定 slat blade mesh / 默认厚度 | 各 Slot B 候选 |
| `N_slats` | int (multiplicity) | family-specific | family-specific | clamp by `(frame_inner_height - 2 * rail_h) / slat_pitch` | 见下表 |
| `slat_pitch` | float | `0.045 - 0.18` m | derived | `(opening_height) / N_slats`；wide 家族 0.13+，narrow 家族 0.045-0.065 | S(0004):L40 (0.092); S(77374234):L? |
| `slat_thickness` | float | `0.005 - 0.022` m | family-specific | flat=0.008, airfoil=0.011, wide=0.018-0.022, narrow=0.006 | S(各 B 候选) |
| `slat_blade_chord` | float | `0.045 - 0.115` m | family-specific | wide ≥ 0.10, narrow ≤ 0.060 | S(各 B 候选) |
| `slat_tilt_lower` / `slat_tilt_upper` | float | `[-π/2, +π/2]` | `[-1.0, 1.0]` | symmetric range；可被 `slat_angle_closed` 偏置 | S(4492bf5f):L55 |
| `leaf_hinge_module` (Slot C) | enum | `fixed_no_leaf_hinge` / `single_leaf_side_hinge` / `double_leaf_french_pair` / `bifold_leaf_chain` | `fixed_no_leaf_hinge` (anchor) | 决定 leaf joints 拓扑（**不**再决定 tilt rod） | 各 Slot C 候选 |
| `tilt_rod_module` (Slot D) | enum | `none` / `prismatic_vertical_rod` / `fixed_visual_rod` | `none` (anchor) | 决定 tilt rod 是否出现、是否 articulate；与 Slot C 正交，但 rod 复制次数 = `leaf_count`（由 Slot C 决定） | 各 Slot D 候选 |
| `leaf_count` | derived int | 1 / 2 | derived from Slot C | fixed→0, single→1, french→2, bifold→2 | 各 Slot C 候选 |
| `leaf_hinge_lower` / `_upper` | float | `[0, 1.65]` rad | `[0, 1.55]` | 单 leaf 90° + 余量；bifold inner `[-2.75, 0]` | S(7c027fd):L169; S(cd6b3278):L165, L173 |
| `tilt_rod_travel` | float | `0.025 - 0.050` m | `0.035` | rod top/bottom guides 间隔的一小部分；仅 `prismatic_vertical_rod` 有效 | S(7c027fd):L40, L220; S(cd6b3278):L198 |
| `tilt_rod_x_offset` / `_y_offset` | float | `0.05 - 0.15` m / `-0.10 - -0.05` m | family-specific | rod 必在 leaf 前面或后面，y 向偏置到 stile 前 / 后；适用 `prismatic_vertical_rod` 和 `fixed_visual_rod` | S(7c027fd):L37, L38 |
| `palette` | enum | `painted_white` / `warm_painted_wood` / `dark_stained` / `industrial_metal` / `cafe_cream` / `storm_blue` | `painted_white` | 仅影响 material rgba，不影响 topology | 跨样本（S(7c027fd) / S(54553517) / S(0470c5)） |

### Multiplicity ranges per slat family

| slat_family | N_min | N_max | typical | rationale |
|---|---|---|---|---|
| `flat_planar` | 5 | 14 | 8-12 | 4492bf5f 用 12；2f5f5384 用 8；77374234 偶有 18 但归属 narrow_blind |
| `airfoil` | 6 | 14 | 8-12 | d2759605 用 12；多数 0003/2050ff87 在 8-12 |
| `wide_plantation` | 3 | 7 | 4-6 | 0004 用 8 (上限)；41536fbc 用 4；2593913b 用 8 |
| `narrow_blind` | 10 | 21 | 12-18 | 77374234 用 18；0219c5e7 用 21；66d56074 用 12 |

## 拓扑多样性审计

| 维度 | 数量 | 备注 |
|---|---|---|
| Slot A candidates | 4 | simple, jamb_with_inset_panel, paneled_with_mid_rail, double_jamb_french |
| Slot B candidates | 4 | flat_planar, airfoil, wide_plantation, narrow_blind |
| Slot C candidates (leaf hinge) | 4 | fixed_no_leaf_hinge, single_leaf_side_hinge, double_leaf_french_pair, bifold_leaf_chain |
| Slot D candidates (tilt rod) | 3 | none, prismatic_vertical_rod, fixed_visual_rod |
| 候选组合 (A × B × C × D) | 4 × 4 × 4 × 3 = **192** | discrete-only, 不含 N |
| 乘上 N multiplicity (median 9 distinct N per family: flat 10 / airfoil 9 / wide 5 / narrow 12) | 192 × 9 ≈ **1728** | N 是 multiplicity 槽位的扩展；diversity gate 不展开 N，1728 只是直觉性的"形态空间大小" |

**约束**：某些 (A, C) 组合是非法或需要折叠（`compatibility matrix`）：
- `simple_rectangular_frame` 与 `bifold_leaf_chain` 不兼容（bifold 要求显式 jamb part）→ 在该组合下自动折回 `fixed_no_leaf_hinge`。
- `simple_rectangular_frame` 与 `double_leaf_french_pair` 不兼容（french 需要 double-jamb 几何）→ 折回 `single_leaf_side_hinge`。
- `paneled_frame_with_mid_rail` 兼容所有 C；mid_rail 将 slat bank split 为 upper/lower 两个 sub-bank（实现时是同一 family，N 拆成 N_upper + N_lower）。
- `double_jamb_french_frame` 强制 `double_leaf_french_pair`（如选其他 C 则折回到 french pair）。

**Slot D 与 Slot C 完全兼容**（grep 33 样本：tilt rod 出现在所有 4 种 Slot C 拓扑下都有样本支持）：
- (`fixed_no_leaf_hinge`, `prismatic_vertical_rod`) — 例 rec_d2d83a90（fixed + tilt rod, 9 个 5 星样本）
- (`fixed_no_leaf_hinge`, `none`) — 例 rec_4492bf5f（18 个 5 星样本）
- (`single_leaf_side_hinge`, `prismatic_vertical_rod`) — 例 rec_7c027fd5
- (`single_leaf_side_hinge`, `none`) — 例 rec_0001 / rec_41536fbc（3 个 5 星样本）
- (`double_leaf_french_pair`, `prismatic_vertical_rod`) — 例 rec_7c027fd5（双 rod）
- (`double_leaf_french_pair`, `none`) — 例 rec_3df192be / rec_a04e2c00（少数 5 星）
- (`bifold_leaf_chain`, `prismatic_vertical_rod`) — 例 rec_cd6b3278（双 leaf 各一根 control_rod）
- (`bifold_leaf_chain`, `none`) — 视为合法（未直接观测但拓扑允许）
- 配 `fixed_visual_rod` 时所有 Slot C 都合法（rod 是 visual，无 joint 约束）

合法组合数（discrete only）≥ 32 × 3 = **96**，远超 `module_topology_diversity ≥ 5` 门控。

| slot | candidate_count | 是否 ≥3 | 备注 |
|---|---|---|---|
| A (frame_topology) | 4 | yes | 每候选来自不同 record |
| B (slat_module multiplicity) | 4 family × (3-12 N) | yes | 4 个家族 + N 范围 |
| C (leaf_hinge_kinematics) | 4 | yes | 每候选来自不同 record |
| D (tilt_rod_drive) | 3 | yes | 每候选来自不同 record（none 候选 anchor 自 4492bf5f 与多数样本） |

预计 `module_topology_diversity` 门控 (≥5 distinct slot picks across passing seeds)：**comfortably pass**。即使应用所有兼容矩阵的 fold-back，仍有 ≥90 个合法组合。

seed=0 anchor: `(simple_rectangular_frame, flat_planar_slats_N12, fixed_no_leaf_hinge, tilt_rod_drive.none)` —— 全部来自 `rec_..._4492bf5f...`，canonical 最简形态。

## Validator（author_run_tests 必须覆盖的点）

- **identity**：frame 部件存在；至少 1 个 slat_* 部件存在；至少 1 个 REVOLUTE slat pivot joint 存在。
- **slat count consistency**：`len([j for j in joints if j.name matches "slat_*_pivot" or "*_to_slat_*"]) == N_slats * leaf_count`。
- **slat axis sanity**：每个 slat pivot 的 axis 必须 ≈ (1, 0, 0)（或全部统一为某个固定方向）；不能出现 (0, 0, 1) 这种竖向 slat。
- **slat range**：每个 slat pivot motion_limits 跨越 ≥ π/4（防止退化成不能动的固定 slat）。
- **slat containment**：所有 slat 在 closed pose 时，其 blade AABB.z 必在 frame inner opening 之内（top_rail 下边 ≤ slat_z ≤ bottom_rail 上边）；slat 两端 pin 落在 stile 之内（captured，含 `allow_overlap`）。
- **leaf hinge sanity** (when Slot C ≠ `fixed_no_leaf_hinge`)：leaf hinge axis ≈ (0, 0, ±1)；origin 在 jamb/side-edge 上，不在 frame 中心；leaf 在打开 pose 下 AABB 中心明显移出 frame opening。
- **tilt rod sanity** (when Slot D = `prismatic_vertical_rod`)：rod PRISMATIC axis ≈ (0, 0, 1)；rod 在 leaf 前/后面，不与 slat 主体几何重叠；rod_travel ≤ guide 间距；rod 数 == `leaf_count`（fixed→0, single→1, french→2, bifold→2）。
- **fixed_visual_rod sanity** (when Slot D = `fixed_visual_rod`)：rod 竖向 visual 出现在 slats_parent 的 visual 列表里；**不**存在独立 `tilt_rod*` part；**不**存在 `*_rod_slide` joint。
- **slot_c_d_independence**：所有 (Slot C, Slot D) 组合都必须能合法 build（除非 Slot A 兼容矩阵强制 Slot C fallback 后导致 Slot D 也需要适配）。
- **bifold chain validity** (when Slot C = `bifold_leaf_chain`)：`outer_to_inner` joint origin 必在 outer_leaf 自由侧（非 jamb 侧）。
- **multiplicity coverage**：sweep 内出现 ≥2 个不同的 N_slats 值（验证 multiplicity 起作用）。
- **module diversity**：seeds 0-19 内出现 ≥5 个 distinct (A, B_family, C, D) 组合（满足 `module_topology_diversity`）。
- **seed_0_anchor**：seed=0 必须产出 `(simple_rectangular_frame, flat_planar_slats_N12, fixed_no_leaf_hinge, none)`。

## Reject cases（必须能识别并拒绝）

- 只有窗框 / 一块平板，没有可识别 slat array（→ identity 拒绝）。
- slat 是固定 visual（无 REVOLUTE joint，或 joint range = 0）。
- slat pivot axis 错成竖向 (0, 0, 1) → 看起来像 mini-door 而非 louver。
- slat pin 长度 / origin 错配，pin 完全在 stile 外（漂浮）或穿透 stile（无 allow_overlap 声明）。
- tilt rod 漂浮（PRISMATIC parent 不是 leaf / frame，或 rod 不在任何 guide 范围内）。
- leaf hinge axis 不在 jamb / leaf side edge（而是在 frame 中心），leaf 转动时穿过整个 frame。
- french pair 两片 leaf hinge 在同一侧（应该对称分布在左右 jamb）。
- bifold 链中 `outer_to_inner` 轴方向错（与 jamb hinge 同向 → 折叠不出来）。
- 简单矩形 frame 配 bifold leaf chain 而未触发 fold-back（违反 compatibility matrix）。
- mid_rail 模式没有真正的 mid_rail visual（mid_rail 是参数但 part 树没有对应 box）。
- Slot D = `prismatic_vertical_rod` 但 rod 数与 `leaf_count` 不一致（french / bifold 双 leaf 但只画一根 rod）。
- Slot D = `fixed_visual_rod` 但实际创建了独立 `tilt_rod*` part 或 `*_rod_slide` PRISMATIC（应只是 visual）。
- Slot D = `none` 但 part 树中出现 `tilt_rod*` 残留（清理不彻底）。

## 与相邻类别的边界

- **`sliding_window`**：sliding window 的 sash 是 PRISMATIC 平移、轴沿水平 X；louvered shutter 的 articulation 是 slat REVOLUTE tilt 和 / 或 leaf REVOLUTE side hinge。如果 model 没有 louver pivot bank 就不属于本类。
- **`rolling_shutter` / curtain coil**：rolling shutter 的 slats 是连续柔性条带卷绕到 cassette；本模板的 slat 是 N 个独立 REVOLUTE rigid body，且不卷绕。
- **`venetian_blinds`**：venetian 用 cord/ladder 悬挂 slats，没有 stile 内嵌 pin；其 tilt 是绳传动而非每 slat 单独 REVOLUTE。
- **`louvered_closet_door` (无可动 slat)**：closet door 看起来像 louvered，但 slat 是固定 visual，没有 REVOLUTE joint → 不属于本模板。本模板要求 slat pivot 是真正可动 joint。
- **`barn_door_shutter` (sliding on rail)**：barn-style shutters 沿 rail PRISMATIC 滑动，没有 leaf hinge → 不属于本模板。
- **`plantation_shutter`** 是本模板的 subset / alias（同 `wide_plantation_slats` 或 `airfoil_slats` + side-hinge / fixed-frame 的组合），不单独成类。

## 模板实现备注（可选）

- **共享 helper**：所有 4 个 slat family 应共用一个 `_emit_louver_slat(part, mesh_or_box, length, pin_radius, pin_length, ...)` 工厂，差异只在 mesh 生成（Box vs section_loft vs ExtrudeGeometry）和 pin 尺寸。每个 family 一个 `_build_slat_mesh_<family>(chord, thickness)`。
- **multiplicity sub-loop**：每个 Slot B family 的 `_build_slats(parent_part, N, ...)` 在 caller（assemble）里一致循环：根据 `N_slats` 和 `slat_pitch` 计算 N 个 z-position，对每个 emit slat part + REVOLUTE joint to parent，axis 固定 (1, 0, 0)。
- **Slot C 的 parent_for_slats**：Slot C 必须暴露 `slats_parent_parts: list[Part]` 接口给 assembler — fixed mode 返回 `[frame]`；single/window-jamb 返回 `[leaf]`；french 返回 `[leaf_0, leaf_1]`；bifold 返回 `[outer_leaf, inner_leaf]`。
- **Slot D 按 leaf 复制**：Slot D 的 build helper 对每个 `slats_parent_parts` 元素**独立**调一次：`prismatic_vertical_rod` → emit 1 `tilt_rod_<i>` part + 1 PRISMATIC joint to parent；`fixed_visual_rod` → emit visual on parent；`none` → 跳过。
- **allow_overlap 模板**：在 author tests 中对每个 `(frame_or_leaf, slat_i)` 对声明 `ctx.allow_overlap(..., elem_a="stile_*", elem_b="*_pin", reason="captured pin in stile bushing")`，并 `expect_overlap` 显式断言 pin-into-stile 接触。
- **mating contracts**：leaf hinge 用 lug-on-jamb / barrel-on-leaf MatingContract（face-to-face hinge knuckle）；Slot D `prismatic_vertical_rod` 的 PRISMATIC 用 guide-block / rod-end face MatingContract；slat pivots 一律 grandfathered（no MatingContract，由 allow_overlap 兜底）；`fixed_visual_rod` 无 joint 无需 MatingContract。
- **paneled_frame_with_mid_rail 实现**：把 single bank 拆成 two banks，slat assembler 跑两遍（不同 z-range，可以不同 N_upper / N_lower），mid_rail 是 frame 的额外 visual + slat z-clamp 边界。
- **double_leaf_french_pair / bifold_leaf_chain 的对称写法**：定义 `_build_leaf(direction_sign, hinge_x, ...)` helper，french 调用两次 `direction_sign=±1`，bifold 调用两次但第二次 parent=outer_leaf 而非 frame。
- **`__modular__ = True`** 标志放文件头，作为 `agent.templates._modular` 抽象的 opt-in。

## 采用源码索引（Adopted Source Index）

| source_id | sample_id | model.py 来源 | 采纳用途 |
|---|---|---|---|
| S1 | `rec_louvered_shutter_assembly_4492bf5f324e4691a5b50d1de1a2f7c5` | `model.py:L13-L25` | Slot A.simple_rectangular_frame 部件树 |
| S2 | `rec_louvered_shutter_assembly_4492bf5f324e4691a5b50d1de1a2f7c5` | `model.py:L26-L56` | Slot B.flat_planar_slats anchor + 通用 slat-pivot 写法 |
| S3 | `rec_louvered_shutter_assembly_4492bf5f324e4691a5b50d1de1a2f7c5` | `model.py:L60-L101` | Slot C.fixed_no_leaf_hinge anchor (无额外 joint) + allow_overlap 写法 |
| S4 | `rec_louvered_shutter_assembly_7c027fd83b684e1bb3d2b2f4c2656525` | `model.py:L40-L77` | Slot A.double_jamb_french_frame + window_frame visual 写法 |
| S5 | `rec_louvered_shutter_assembly_7c027fd83b684e1bb3d2b2f4c2656525` | `model.py:L97-L171` | Slot C.single_leaf_side_hinge helper（leaf REVOLUTE hinge，**不**含 tilt rod） |
| S5b | `rec_louvered_shutter_assembly_7c027fd83b684e1bb3d2b2f4c2656525` | `model.py:L198-L222` | Slot D.prismatic_vertical_rod anchor source（vertical PRISMATIC tilt rod + per-slat drive_tab） |
| S6 | `rec_louvered_shutter_assembly_7c027fd83b684e1bb3d2b2f4c2656525` | `model.py:L261-L263` | Slot C.double_leaf_french_pair 对称 leaf 写法 |
| S7 | `rec_louvered_shutter_assembly_d2759605eb0f4d49bdb825400e4fb507` | `model.py:L84-L116` | Slot B.airfoil_slats anchor (section_loft mesh) |
| S8 | `rec_louvered_shutter_assembly_d2759605eb0f4d49bdb825400e4fb507` | `model.py:L128-L222` | Slot A.window_jamb_with_inset_panel (outer_frame + panel_frame 双层) + Slot C.single_leaf_side_hinge anchor source |
| S9 | `rec_louvered_shutter_assembly_d2759605eb0f4d49bdb825400e4fb507` | `model.py:L282-L349` | Slot D.fixed_visual_rod anchor source（视觉 rod, 无独立 part 无 joint）+ slat_pivot 写法参考 |
| S10 | `rec_louvered_shutter_assembly_cd6b32786e5c4247a78b6d28fe29f505` | `model.py:L36-L48, L147-L174` | Slot C.bifold_leaf_chain anchor (jamb → outer_leaf → inner_leaf) |
| S11 | `rec_louvered_shutter_assembly_cd6b32786e5c4247a78b6d28fe29f505` | `model.py:L176-L200` | bifold 模式下的 per-leaf control_rod 写法（Slot D.prismatic_vertical_rod 的 alt 源，验证 2-leaf 复制规则） |
| S12 | `rec_louvered_shutter_assembly_0001` | `model.py:L27-L57` | Slot A.simple_rectangular_frame alt + flat_planar_slats N=11 参考 |
| S13 | `rec_louvered_shutter_assembly_0003` | `model.py:L29-L93` | Slot B.airfoil_slats alt (Extrude + spline profile) |
| S14 | `rec_louvered_shutter_assembly_0004` | `model.py:L34-L67` | Slot B.wide_plantation_slats anchor (superellipse profile) |
| S15 | `rec_louvered_shutter_assembly_0219c5e7a67f4adb917422bff27a05f2` | `model.py:L25-L49` | Slot A.paneled_frame_with_mid_rail anchor (DOOR-format kick_panel + mid_rail) |
| S16 | `rec_louvered_shutter_assembly_41536fbc1fcd4e9d877da125e295e783` | `model.py:L23-L60` | Slot A.paneled_frame_with_mid_rail alt + 上下两 bank 的 N 拆分写法 |
| S17 | `rec_louvered_shutter_assembly_54553517611c4467b1ced14026ea876f` | `model.py:L48-L195` | Slot C.single_leaf_side_hinge alt（带 stay support arm 的 storm 变体，作为 future-gated reference，不进入默认 candidate） |
| S18 | `rec_louvered_shutter_assembly_0470c5472ccc4d908162c0b9680f9be5` | `model.py:L18-L93` | Slot C.single_leaf_side_hinge alt + horizontal control bar 变体 |
| S19 | `rec_louvered_shutter_assembly_77374234b7d94a189b300e03975bee73` | `model.py:L15-L60` | Slot B.narrow_blind_slats anchor (N=18) |

## 审核记录

| 项 | 结论 |
|---|---|
| reviewer status | pending |
| reviewer notes | SPEC_ONLY_DRAFT; awaiting human review per `articraft_template_authoring/SPEC_REVIEW_TEMPLATE.md`. Modular pattern is `mixed` (multiplicity over slats + parallel-child leaf hinge + parallel-child tilt rod). **本版相比上一版把 tilt rod 从 Slot C 的耦合候选拆出来独立成 Slot D**（grep 33 个样本验证 leaf-hinge 和 tilt-rod 是两个独立轴：tilt×leaf 4 个组合都有 5 星样本）。4 槽位拓扑数 4×4×4×3=192（合法 ≥96）。Slot C 候选由 4 个减少（`single_leaf_side_hinge_with_tilt_rod` 重命名为 `single_leaf_side_hinge`），但仍 4 个。Slot D 有 3 个候选（none / prismatic_vertical_rod / fixed_visual_rod），每候选源自不同 5 星样本。storm-shutter support-arm topology (54553517) 仍作为 future-gated variant 不进入默认候选。 |
