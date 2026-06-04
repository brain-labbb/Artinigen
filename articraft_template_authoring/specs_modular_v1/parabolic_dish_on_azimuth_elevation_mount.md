# Parabolic Dish On Azimuth Elevation Mount Spec

## 元信息
| 项 | 值 |
|---|---|
| slug | `parabolic_dish_on_azimuth_elevation_mount` |
| template path | `agent/templates/parabolic_dish_on_azimuth_elevation_mount.py` |
| test path | `tests/agent/test_parabolic_dish_on_azimuth_elevation_mount_template.py` |
| stage | `SPEC_ONLY_DRAFT` |
| status | `pending` |
| __modular__ | `True` |
| pattern | `linear_chain` |

## 5 星样本阅读摘要
| 项 | 值 |
|---|---|
| five_star_total | 38 |
| read_count | 38 |
| read_scope | all 5-star samples in this category: `model.py` / `revision.json` / `record.json` / `prompt.txt` were read |
| samples_adopted_as_module_sources | 6 |
| samples_read_but_not_adopted | 32 |
| source_index_policy | only adopted reusable snippets are indexed below |

全量阅读后的结构族分布：

| 结构族 | 样本数 | 说明 |
|---|---:|---|
| pedestal/base -> azimuth stage -> dish | 24 | base/pedestal/yoke/dish 三件链，azimuth Z joint + elevation horizontal joint |
| tripod or portable base | 4 | tripod_base/head/dish, both REVOLUTE or azimuth continuous |
| roof/wall/mast mount | 7 | roof_mount/wall_mount/mast root, clamp/fork head, dish frame |
| instrument box / rear cover / side crank auxiliary | 5 | optional hatch, rear electronics cover, side crank/lock knob |
| dish reflector construction variants | 38 | lathe/cadquery/mesh parabolic shell, feed boom, rear ribs/truss, rim ring |

被采纳样本逐条标注：
- `rec_parabolic_dish_on_azimuth_elevation_mount_0004` — adopted：canonical pedestal, azimuth_yoke, reflector, CONTINUOUS azimuth + REVOLUTE elevation。
- `rec_parabolic_dish_on_azimuth_elevation_mount_1a992a547a104469adb6a6b286f64e1d` — adopted：roof mount, azimuth fork, feed boom mesh, roof-mounted chain。
- `rec_parabolic_dish_on_azimuth_elevation_mount_3ebbc287998444179c7080d3a2807954` — adopted：tripod portable base, head, dish shell/ribs/feed arm。
- `rec_parabolic_dish_on_azimuth_elevation_mount_49566120c578436cb5061a6f0e715707` — adopted：pedestal yoke, dish assembly, instrument box + hatch。
- `rec_parabolic_dish_on_azimuth_elevation_mount_b46d320f8c5e484d8e911539ce34497d` — adopted：mast + azimuth fork, cadquery reflector shell, parabolic spokes。
- `rec_parabolic_dish_on_azimuth_elevation_mount_ff95ab246ac04d8d92e07ad4c874a686` — adopted：heavy base, yoke pedestal, rear electronics cover REVOLUTE。
- Remaining 32 samples — read but not adopted: repeat the same azimuth/elevation chain with axis sign/material/primitive/depth differences or auxiliary details already covered.

## 核心身份
`parabolic_dish_on_azimuth_elevation_mount` 是一个可跟踪方向的抛物面天线：静态 root base/mast/roof/wall/tripod 支撑一个绕竖直 Z 轴调整方位角的 azimuth stage，再通过水平 elevation hinge 支撑 parabolic reflector/dish assembly。dish 必须有凹面 reflector、rim/back frame/feed horn 或 feed boom 等 antenna identity。默认成熟域是 two-DOF azimuth/elevation chain；rear cover、instrument hatch、crank/lock knob 是可选辅助。

边界：
- 不包括固定不动的 satellite dish；必须有 azimuth + elevation articulation。
- 不混入 camera pan-tilt head：必须有 parabolic reflector/dish and feed support。
- 不混入 radar array/flat panel antenna：reflector must be concave/parabolic。
- 不混入 telescope mount：feed horn/boom and reflector back frame are expected antenna features。

## 采用源码索引（Adopted Source Index）
| source_id | sample_id | model.py 来源 | 采纳用途 |
|---|---|---|---|
| S1 | `rec_parabolic_dish_on_azimuth_elevation_mount_0004` | `data/records/rec_parabolic_dish_on_azimuth_elevation_mount_0004/revisions/rev_000001/model.py:L30-L335` | canonical pedestal + azimuth yoke + reflector, CONTINUOUS azimuth and REVOLUTE elevation |
| S2 | `rec_parabolic_dish_on_azimuth_elevation_mount_1a992a547a104469adb6a6b286f64e1d` | `data/records/rec_parabolic_dish_on_azimuth_elevation_mount_1a992a547a104469adb6a6b286f64e1d/revisions/rev_000001/model.py:L24-L128,L146-L351` | roof mount, azimuth fork, reflector mesh, feed boom, two-joint chain |
| S3 | `rec_parabolic_dish_on_azimuth_elevation_mount_3ebbc287998444179c7080d3a2807954` | `data/records/rec_parabolic_dish_on_azimuth_elevation_mount_3ebbc287998444179c7080d3a2807954/revisions/rev_000001/model.py:L21-L106,L115-L269` | tripod base, head, dish shell/ribs/feed arm, portable REVOLUTE chain |
| S4 | `rec_parabolic_dish_on_azimuth_elevation_mount_49566120c578436cb5061a6f0e715707` | `data/records/rec_parabolic_dish_on_azimuth_elevation_mount_49566120c578436cb5061a6f0e715707/revisions/rev_000001/model.py:L27-L38,L177-L446` | instrument-box dish assembly, hatch REVOLUTE, yoke arms and rear braces |
| S5 | `rec_parabolic_dish_on_azimuth_elevation_mount_b46d320f8c5e484d8e911539ce34497d` | `data/records/rec_parabolic_dish_on_azimuth_elevation_mount_b46d320f8c5e484d8e911539ce34497d/revisions/rev_000001/model.py:L22-L120,L129-L342` | mast/fork head, cadquery annular support, parabolic reflector and spokes |
| S6 | `rec_parabolic_dish_on_azimuth_elevation_mount_ff95ab246ac04d8d92e07ad4c874a686` | `data/records/rec_parabolic_dish_on_azimuth_elevation_mount_ff95ab246ac04d8d92e07ad4c874a686/revisions/rev_000001/model.py:L21-L82,L93-L201` | heavy base/yoke, rear frame/feed support, rear cover REVOLUTE |

## 槽位 + 候选模块表

### Slot A：root_support
| module_name | 5_star_source | model.py:Lx-Ly | seed=0 anchor | 结构特征 |
|---|---|---|---|---|
| `pedestal_base` | S1 | `model.py:L148-L173` | **yes** | cylindrical base/pedestal with bearing rings |
| `roof_mount` | S2 | `model.py:L146-L193` | | roof plate / low mount, compact installation |
| `tripod_base` | S3 | `model.py:L115-L158` | | three legs and spreaders, portable support |
| `mast_mount` | S5 | `model.py:L129-L148` | | vertical mast carrying azimuth fork |
| `heavy_service_base` | S6 | `model.py:L93-L130` | | slab base, yoke towers, rear cable box |

### Slot B：azimuth_stage
| module_name | 5_star_source | model.py:Lx-Ly | seed=0 anchor | 结构特征 |
|---|---|---|---|---|
| `dual_yoke_stage` | S1 | `model.py:L185-L228,L320-L326` | **yes** | left/right yoke cheeks on azimuth turntable |
| `compact_roof_fork` | S2 | `model.py:L205-L251,L336-L342` | | short azimuth fork and bearing ring |
| `tripod_head` | S3 | `model.py:L158-L171,L254-L260` | | compact portable head, REVOLUTE yaw |
| `mast_azimuth_fork` | S5 | `model.py:L170-L183,L327-L333` | | mast-top fork with annular collar |
| `instrument_yoke` | S4 | `model.py:L232-L279,L410-L416` | | yoke arms, rear braces, instrument support |

### Slot C：dish_reflector_assembly
| module_name | 5_star_source | model.py:Lx-Ly | seed=0 anchor | 结构特征 |
|---|---|---|---|---|
| `lathe_reflector_with_feed` | S1 | `model.py:L240-L308,L329-L335` | **yes** | lathe reflector, rim, feed boom/horn, rear supports |
| `roof_feed_boom_dish` | S2 | `model.py:L64-L104,L266-L324` | | mesh reflector, feed boom, ribs, support struts |
| `portable_ribbed_dish` | S3 | `model.py:L55-L91,L191-L247` | | dish shell, ribs, feed arm for tripod |
| `instrumented_dish_with_box` | S4 | `model.py:L291-L398,L419-L446` | | dish assembly plus fixed instrument box and hinged hatch |
| `cadquery_spoked_reflector` | S5 | `model.py:L27-L104,L209-L320` | | cadquery dish shell, parabolic spokes, fork-side axis |

### Slot D：auxiliary_mechanism
| module_name | 5_star_source | model.py:Lx-Ly | seed=0 anchor | 结构特征 |
|---|---|---|---|---|
| `none` | S1 | `model.py:L320-L335` | **yes** | only azimuth + elevation |
| `instrument_hatch` | S4 | `model.py:L368-L446` | | fixed instrument_box plus REVOLUTE hatch |
| `rear_cover` | S6 | `model.py:L171-L201` | | dish-mounted rear cover hinged on electronics frame |
| `side_crank_or_lock_knob` | S4 | `model.py:L232-L279` | | visual/mechanical side crank or lock knob on azimuth/elevation head |

## 槽位图（slot graph）
pattern = `linear_chain`

```
[Slot A root_support]
      -- CONTINUOUS/REVOLUTE azimuth, axis (0,0,1) -->
[Slot B azimuth_stage]
      -- REVOLUTE elevation, horizontal axis -->
[Slot C dish_reflector_assembly]
      -- optional FIXED/REVOLUTE -->
[Slot D instrument_hatch / rear_cover]
```

主约束基准是 azimuth vertical axis 和 elevation hinge line。dish center, yoke cheeks, feed boom, rear frame, auxiliary hatch origin must derive from this chain.

## 部件（Parts）

### Slot A / root_support
| part | visual_count | 描述 | 来源 |
|---|---:|---|---|
| `pedestal` / `base` / `roof_mount` / `tripod` / `mast` | ~4-20 | ground/roof/wall/tripod/mast static root | S1 / S2 / S3 / S5 / S6 |

### Slot B / azimuth_stage
| part | visual_count | 描述 | 来源 |
|---|---:|---|---|
| `azimuth_yoke` / `azimuth_fork` / `head` / `pedestal` | ~4-18 | yaw stage with fork/yoke cheeks and elevation bearings | S1 / S2 / S3 / S4 / S5 |

### Slot C / dish_reflector_assembly
| part | visual_count | 描述 | 来源 |
|---|---:|---|---|
| `reflector` / `dish_assembly` / `dish` | ~8-30 | concave parabolic reflector, rim, back frame, ribs, feed horn/boom | S1-S6 |

### Slot D / auxiliary_mechanism
| part | visual_count | 描述 | 来源 |
|---|---:|---|---|
| `instrument_box` | ~2 | fixed electronics/instrument box mounted on dish | S4 |
| `instrument_hatch` / `rear_cover` | ~3-5 | hinged cover/hatch on rear/instrument box | S4 / S6 |
| `side_crank` / `lock_knob` | ~2-4 | optional rotary visual/control on yoke/head | S4 |

## 关节（Joints）
| 关节 | 类型 | parent_slot.part | child_slot.part | axis | range | 描述 | 来源 |
|---|---|---|---|---|---|---|---|
| `azimuth_spin` / `azimuth_yaw` | CONTINUOUS or REVOLUTE | A.root_support | B.azimuth_stage | `(0,0,1)` | unlimited or `[-pi, pi]` | 方位角旋转，竖直轴 | S1 / S2 / S3 / S4 / S5 / S6 |
| `elevation_tilt` | REVOLUTE | B.azimuth_stage | C.dish | `(1,0,0)` or `(0,±1,0)` horizontal | `[-0.25, 1.25]` reviewer-gated | 抛物面俯仰，axis 穿过 yoke cheek / dish side bearings | S1-S6 |
| `instrument_box_fixed` | FIXED | C.dish | D.instrument_box | n/a | n/a | instrument box 固定在 dish rear frame | S4 |
| `instrument_hatch_hinge` | REVOLUTE | D.instrument_box | D.instrument_hatch | local vertical/cover edge `(0,0,-1)` | `[0, 1.2]` | instrument hatch 开合 | S4 |
| `rear_cover_hinge` | REVOLUTE | C.dish | D.rear_cover | local cover hinge `(0,0,1)` | `[0, 1.1]` | rear electronics cover 开合 | S6 |
| `crank_spin` | CONTINUOUS | B.azimuth_stage | D.side_crank | horizontal | unlimited | optional crank/lock knob rotation | S4 |

## 每槽位 Module Emits / Interfaces

本 spec 是 modular v1 早期写法；每个 slot/module 的 emitted parts、internal joints、upstream/downstream interface 已在「槽位 + 候选模块表」「槽位图」「部件（Parts）」「关节（Joints）」和 adopted source index 中给出。模板实现阶段必须把这些信息逐 module 显式落成 `ModuleBuild`、`InterfaceSpec` 和 `MatingContract`，不能只按全局部件清单拼装。

| emits | 描述 | 来源 |
|---|---|---|
| parts / visuals | 以各 slot candidate 的结构特征和「部件（Parts）」表为准；不动装饰优先作为 parent visual | adopted source index + slot table |
| internal joints | 以「关节（Joints）」表和 slot graph 中的 joint type / axis / range 为准 | adopted source index + joints table |
| upstream interface | 来自 slot graph 中的 parent face、hinge line、socket、rail、axis、contact plane 或 support policy | slot graph + source snippets |
| downstream interface | 消费相邻 slot 的 mating point / axis / face；必须在实现中转成真实 `InterfaceSpec` | slot graph + source snippets |
| mating contracts | 每个 separate moving child 和跨 slot 连接必须有可见支撑路径；captured pin / shaft / bearing overlap 需要局部 allow-overlap 理由 | validator + reject cases |

## 参数范围汇总
| 参数 | 类型 | 取值范围 / 候选值 | 默认值 | 派生关系 | 来源 |
|---|---|---|---|---|---|
| `root_style` | enum | `pedestal`, `roof_mount`, `tripod`, `mast`, `heavy_service_base` | `pedestal` | Slot A module | S1-S6 |
| `azimuth_stage_style` | enum | `dual_yoke`, `compact_fork`, `tripod_head`, `mast_fork`, `instrument_yoke` | `dual_yoke` | Slot B module, gated by root_style | S1-S5 |
| `reflector_style` | enum | `lathe_feed`, `roof_feed_boom`, `portable_ribbed`, `instrumented_box`, `cadquery_spoked` | `lathe_feed` | Slot C module | S1-S5 |
| `auxiliary_mechanism` | enum | `none`, `instrument_hatch`, `rear_cover`, `side_crank` | `none` | Slot D module | S4 / S6 |
| `dish_radius` | float | `[0.35, 1.05]` | `0.62` | yoke span and feed distance derive from radius | S1 / S2 / S6 |
| `dish_depth` | float | `[0.10, 0.42]` | `0.22` | parabolic shell depth, feed offset derived | S2 / S5 / S6 |
| `azimuth_height` | float | `[0.35, 1.35]` | `0.72` | support height to elevation hinge | S1 / S4 |
| `feed_style` | enum | `single_boom`, `dual_strut`, `tripod_feed`, `horn_only`, `none_minimal` | `single_boom` | reflector module substyle | S1 / S2 / S3 |
| `back_frame_style` | enum | `simple_spine`, `ribbed`, `truss`, `instrument_box`, `covered` | `simple_spine` | rear supports and auxiliary gating | S2 / S3 / S4 / S6 |
| `azimuth_joint_type` | enum | `continuous`, `revolute_limited` | `continuous` | samples include both; seed=0 continuous | S1 / S3 |

## Multiplicity / Copy Logic

- 无模板级可变复制数量逻辑：核心是 one root support, one azimuth stage, one dish assembly, optional one auxiliary cover/crank.
- Module-local repeated ribs, feed struts, tripod legs, yoke cheeks, bolts, and rim ticks are fixed helper loops; they do not expose independent `rib_count` or `leg_count` in this spec. Tripod legs are fixed 3 visual/support structure, not a sampled template-level N.

## 拓扑多样性审计

总组合数：5 root modules x 5 azimuth modules x 5 reflector modules x 4 auxiliary modules = 500 before gating.

预计 `module_topology_diversity` 门控（>=5 distinct）能否过：yes。理由：root support, auxiliary hatch/rear cover, azimuth joint type, reflector construction and fixed instrument box add distinct topologies.

| slot | candidate_count | 是否 >=3 | 备注 |
|---|---:|---|---|
| root_support | 5 | yes | pedestal/roof/tripod/mast/heavy base |
| azimuth_stage | 5 | yes | yoke/fork/head/mast/instrument variants |
| dish_reflector_assembly | 5 | yes | reflector/feed/back-frame variants |
| auxiliary_mechanism | 4 | yes | none/hatch/cover/crank |

## 部件多样性审计（Part Diversity Audit）
| 部件类型 | observed_variation | 连续参数是否足够 | 是否需要离散参数 | 推荐参数 | 说明 |
|---|---|---|---|---|---|
| root support | pedestal / roof mount / tripod / mast / heavy base | no | yes | `root_style` | contact plane and part tree differ |
| azimuth stage | dual yoke / compact fork / tripod head / mast fork / instrument yoke | no | yes | `azimuth_stage_style` | elevation hinge support geometry differs |
| reflector | lathe shell / ribbed mesh / cadquery spoked / instrumented back | no | yes | `reflector_style`, `back_frame_style` | concave dish construction and rear support differ |
| feed | single boom / dual strut / tripod feed / horn-only | no | yes | `feed_style` | antenna identity changes |
| auxiliary cover | none / instrument hatch / rear cover / crank | no | yes | `auxiliary_mechanism` | adds part/joint |
| dish radius/depth | continuous size/depth | yes | no | `dish_radius`, `dish_depth` | same topology with scale/depth changes |

## 组合逻辑（Composition Logic）
1. `root_style` establishes ground/roof/wall/contact plane and azimuth axis.
2. `azimuth_stage_style` places yoke/fork cheeks symmetrically around elevation hinge line.
3. `dish_radius/depth` derive reflector mesh, rim, back frame, feed boom length, and yoke clearance.
4. `elevation_tilt` origin lies on side bearing line through dish assembly, not at arbitrary center.
5. Auxiliary hatch/cover attaches to rear frame/instrument box and uses local hinge edge; side crank attaches to azimuth/elevation head.

## 已有模板写法参考
`cctv_mast_with_pantilt_camera_head` / `monitor_mount` / `rotary_post` / `revolute_hinge`（仅参考组织与 joint metadata）

## 约束
- 必须有 azimuth joint around vertical axis and elevation joint around horizontal axis。
- Dish reflector must be concave/parabolic with visible rim/feed/back-frame identity。
- Elevation hinge line must intersect yoke/fork bearings and dish side/back frame.
- Feed boom/horn must remain attached to dish and point toward reflector focus.
- Root support must touch ground/roof/wall plane according to style.

### Stage 1 / Stage 2 seed-domain plan

seed_domain_stage：stage1_coverage。当前 spec 的组合空间以「拓扑多样性审计」中的兼容 slot/module 组合为准；Stage 1 seed domain 应优先覆盖 seed=0 anchor、每个主要 slot candidate、最大 part/joint 数组合、bulky module、可选 moving child、captured-pin / bearing / hinge / rail 接口、以及最容易出现悬空、穿模、joint 轴错或 closed pose 不合理的组合。

Stage 1 high-risk coverage seed plan：

| seed/range | covered combo | risk type | viewer / validator focus |
|---|---|---|---|
| 0 | spec 标注的 seed=0 anchor module combination | regression anchor | 类别身份、baseline part tree、主 joint 语义 |
| 1-N | 覆盖各 slot 的非 anchor candidate 和 gated optional moving child | interface / axis / support | 悬空、穿模、joint origin、axis、range、closed pose |
| N+ | 覆盖最大 part count、bulky module、captured-pin / bearing / hinge / rail 组合 | clearance / mating contract | visible support path、allow-overlap 局部理由、viewer 比例 |

Stage 2 procedural target：所有 Stage-1 模板完成并通过 sweep/viewer 后，主体 `seed>0` 逻辑迁移为 unbounded deterministic procedural sampling；除 anchor、coverage 和 regression overrides 外，不得无限轮换少数 curated / modulo 组合表来冒充 dataset-scale seed domain。

## Validator
| 检查项 | 标准 |
|---|---|
| identity | concave dish + feed/back frame + mount present |
| azimuth joint | Z-axis CONTINUOUS or REVOLUTE from root to azimuth stage |
| elevation joint | horizontal REVOLUTE from azimuth stage to dish |
| chain order | root -> azimuth -> dish, no direct floating dish |
| hinge placement | elevation origin near yoke/dish bearing line |
| reflector geometry | dish has concave shell/rim and feed support |
| auxiliary | hatch/cover/crank parented to dish/head and not replacing main joints |
| diversity | root_style, azimuth_stage_style, reflector_style branches covered |

## Reject cases
- 静态 dish 没有 azimuth/elevation 两级运动。
- 变成 camera/telescope pan-tilt，没有 parabolic reflector。
- Elevation axis vertical or azimuth axis horizontal。
- Dish floats away from yoke/fork or feed horn detached。
- Rear cover/hatch placed on front reflector surface blocking dish identity。
- Tripod/roof/wall support does not contact its intended plane。

## 审核记录
| 项 | 结论 |
|---|---|
| reviewer status | pending |
| reviewer notes | 等待人工审核；未进入模板实现阶段 |

