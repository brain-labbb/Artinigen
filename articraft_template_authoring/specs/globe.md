# Globe Spec

## 元信息
| 项 | 值 |
|---|---|
| slug | `globe` |
| template path | `agent/templates/globe.py` |
| test path | `tests/agent/test_globe_template.py` |
| stage | `SPEC_ONLY_DRAFT` |
| status | `pending` |
| __modular__ | `True` |
| pattern | `mixed` |

## 5 星样本阅读摘要
| 项 | 值 |
|---|---|
| five_star_total | 28 |
| read_count | 28 |
| read_scope | all 5-star samples in this category; each record's `record.json`, active `revision.json`, `prompt.txt`, and `model.py` were scanned |
| samples_adopted_as_module_sources | 11 |
| samples_read_but_not_adopted | 17 |
| source_index_policy | adopted sources cover desktop meridian, classroom full ring, marine gimbal, turntable base, wall mount, floor stand, date ring, and side knob families |

- adopted as module sources: `rec_globe_0002`, `rec_globe_0003`, `rec_globe_0fc4e0cefb164176b77a767cd54d8816`, `rec_globe_1c4dea866a4340d792eedfb836a2c683`, `rec_globe_25701789f8164dab9c233cdaac1ff96c`, `rec_globe_3017c4d45cf44d2994e72570bc98a56d`, `rec_globe_31962387b4024251a1fca6f51ba28089`, `rec_globe_bb728b5bb5b64df798b3ef95f629fb38`, `rec_globe_dd09f51da481436e8a10f6b573d84744`, `rec_globe_e594c561feb0480c8a74192b74e79049`, `rec_globe_ef9e5cd15f884bac90c4a531305bb379`.
- read but not adopted: `rec_a-realistic-detailed-model-of-an-articulated-glo_20260320_235017_379193_b1490588`, `rec_globe_35a4dc2d75144987ae667216dff6d05d`, `rec_globe_3ab2c8a318684db5ae621bd6d66f129a`, `rec_globe_3dfdcdb0007d48f59136d9212f155f76`, `rec_globe_4a40f06f158347f7aa1fb07f24b21518`, `rec_globe_52934fe9864e4661acf3ed6eb5606ee0`, `rec_globe_598876330e2a49e5ad7d88b187684fb7`, `rec_globe_5c7a01506aa9416e91faa443aa856cfc`, `rec_globe_87ccfb681f9a4dd5a892755a9be40e48`, `rec_globe_9d50471a420d47ca9f519510f6e9ea17`, `rec_globe_a3cbd0301f114683b86737414a4e925a`, `rec_globe_ad2a9540145a48efa23fcf234cc82ca0`, `rec_globe_bdb5ebc873254d27b7ee77da49a1e74f`, `rec_globe_c2046023b07e4f17a34209200b123906`, `rec_globe_d42aa0f2efa54990be87891f818aab21`, `rec_globe_e158796bcf8d49d5a96ee3bc59b5d710`, `rec_globe_e4280c31c61d4872a54824276a852921`; reason: redundant desktop/classroom/celestial/floor-stand variants represented by adopted sources.

## 核心身份

Globe 是带可旋转球体的教育/装饰地球仪或天球仪。核心由 base/stand、meridian/cradle/support、sphere 三层构成，sphere 必须绕极轴连续旋转；很多样本还有 meridian tilt、base turntable、marine gimbal、wall arm、date ring 或 side knobs。球面可以有 relief continents / map marks，但这些必须作为 globe part 的 visual/mesh，不应独立固定为漂浮装饰。

边界：
- 不包括普通球、行星仪或灯罩：必须有支架和 articulated spin axis。
- 不混入 `turntable`：turntable 是唱盘设备；globe 的主旋转对象是球体。

## 采用源码索引（Adopted Source Index）
| source_id | sample_id | model.py 来源 | 采纳用途 |
|---|---|---|---|
| S1 | `rec_globe_0002` | `data/records/rec_globe_0002/revisions/rev_000001/model.py:L187-L398` | desktop yoke, meridian tilt, globe spin, relief continents |
| S2 | `rec_globe_0003` | `data/records/rec_globe_0003/revisions/rev_000001/model.py:L71-L366` | classroom full circular meridian and forked pedestal |
| S3 | `rec_globe_0fc4e0cefb164176b77a767cd54d8816` | `data/records/rec_globe_0fc4e0cefb164176b77a767cd54d8816/revisions/rev_000001/model.py:L152-L298` | marine outer cradle, inner ring, globe spin |
| S4 | `rec_globe_1c4dea866a4340d792eedfb836a2c683` | `data/records/rec_globe_1c4dea866a4340d792eedfb836a2c683/revisions/rev_000001/model.py:L241-L423` | equatorial date ring as second continuous child |
| S5 | `rec_globe_25701789f8164dab9c233cdaac1ff96c` | `data/records/rec_globe_25701789f8164dab9c233cdaac1ff96c/revisions/rev_000001/model.py:L69-L246` | celestial open two-post cradle on turntable base |
| S6 | `rec_globe_3017c4d45cf44d2994e72570bc98a56d` | `data/records/rec_globe_3017c4d45cf44d2994e72570bc98a56d/revisions/rev_000001/model.py:L45-L286` | side adjustment knobs as continuous children |
| S7 | `rec_globe_31962387b4024251a1fca6f51ba28089` | `data/records/rec_globe_31962387b4024251a1fca6f51ba28089/revisions/rev_000001/model.py:L56-L269` | floor stand with pedestal turntable |
| S8 | `rec_globe_bb728b5bb5b64df798b3ef95f629fb38` | `data/records/rec_globe_bb728b5bb5b64df798b3ef95f629fb38/revisions/rev_000001/model.py:L106-L244` | minimalist single-sided canted support |
| S9 | `rec_globe_dd09f51da481436e8a10f6b573d84744` | `data/records/rec_globe_dd09f51da481436e8a10f6b573d84744/revisions/rev_000001/model.py:L113-L326` | wall-mounted support arm and partial meridian |
| S10 | `rec_globe_e594c561feb0480c8a74192b74e79049` | `data/records/rec_globe_e594c561feb0480c8a74192b74e79049/revisions/rev_000001/model.py:L65-L328` | executive floor tripod/shelf stand |
| S11 | `rec_globe_ef9e5cd15f884bac90c4a531305bb379` | `data/records/rec_globe_ef9e5cd15f884bac90c4a531305bb379/revisions/rev_000001/model.py:L86-L286` | antique desk globe with horizon ring |

## 槽位 + 候选模块表

### Slot A：base_support
| module_name | 5_star_source | model.py:Lx-Ly | seed=0 anchor | 结构特征 |
|---|---|---|---|---|
| `desktop_yoke_base` | `rec_globe_0002` | L187-L278 | **yes** | round base, column, fork/yoke support |
| `classroom_pedestal` | `rec_globe_0003` | L71-L150 | | broad pedestal and full-ring support fork |
| `floor_turntable_stand` | `rec_globe_31962387b4024251a1fca6f51ba28089` | L56-L198 | | floor stand with base swivel/turntable |
| `wall_arm_mount` | `rec_globe_dd09f51da481436e8a10f6b573d84744` | L113-L158 | | wall bracket and projecting arm |
| `minimal_single_arm` | `rec_globe_bb728b5bb5b64df798b3ef95f629fb38` | L106-L198 | | ring base with canted one-sided support |

### Slot B：meridian_cradle
| module_name | 5_star_source | model.py:Lx-Ly | seed=0 anchor | 结构特征 |
|---|---|---|---|---|
| `tilting_meridian_ring` | `rec_globe_0002` | L279-L345, L373-L398 | **yes** | meridian ring REVOLUTE to base, globe CONTINUOUS inside |
| `full_classroom_meridian` | `rec_globe_0003` | L151-L192, L341-L366 | | full circular ring between trunnions |
| `marine_gimbal_inner_ring` | `rec_globe_0fc4e0cefb164176b77a767cd54d8816` | L152-L298 | | outer cradle + inner ring REVOLUTE + globe spin |
| `open_two_post_cradle` | `rec_globe_25701789f8164dab9c233cdaac1ff96c` | L88-L246 | | two-post celestial cradle on continuous turntable |
| `partial_wall_meridian` | `rec_globe_dd09f51da481436e8a10f6b573d84744` | L159-L326 | | wall-arm partial ring on side trunnion |

### Slot C：sphere_map
| module_name | 5_star_source | model.py:Lx-Ly | seed=0 anchor | 结构特征 |
|---|---|---|---|---|
| `relief_world_sphere` | `rec_globe_0002` | L346-L398 | **yes** | globe sphere with relief/continent visuals and polar caps |
| `classroom_marked_sphere` | `rec_globe_0003` | L193-L366 | | sphere with latitude/longitude and map markings |
| `celestial_sphere` | `rec_globe_25701789f8164dab9c233cdaac1ff96c` | L196-L246 | | celestial globe with simple polar pivots |
| `antique_horizon_sphere` | `rec_globe_ef9e5cd15f884bac90c4a531305bb379` | L213-L286 | | antique globe with horizon/meridian context |

### Slot D：secondary_motion
| module_name | 5_star_source | model.py:Lx-Ly | seed=0 anchor | 结构特征 |
|---|---|---|---|---|
| `meridian_tilt_only` | `rec_globe_0002` | L373-L398 | **yes** | two joints: meridian tilt and globe spin |
| `base_turntable` | `rec_globe_25701789f8164dab9c233cdaac1ff96c` | L229-L246 | | base->cradle continuous plus globe spin |
| `equatorial_date_ring` | `rec_globe_1c4dea866a4340d792eedfb836a2c683` | L391-L423 | | date ring continuous around stand |
| `side_adjustment_knobs` | `rec_globe_3017c4d45cf44d2994e72570bc98a56d` | L236-L286 | | two side knobs continuous on pedestal |

## 槽位图（slot graph）

pattern: `mixed`

```text
[Slot A base_support] -- optional tilt/turntable joint --> [Slot B meridian_cradle]
[Slot B meridian_cradle] -- globe_spin CONTINUOUS, polar axis --> [Slot C sphere_map]
[Slot A or B] -- optional parallel CONTINUOUS/REVOLUTE --> [Slot D secondary_motion]
```

## 部件（Parts）
| part | slot | visual_count | 描述 | 来源 |
|---|---|---:|---|---|
| `base` / `stand` / `wall_arm` | A | ~2-17 | tabletop/floor/wall base and support | S1/S2/S7-S11 |
| `meridian` / `cradle` / `inner_ring` | B | ~1-10 | ring/fork/cradle around globe | S1-S5/S9 |
| `globe` | C | ~2-13 | sphere and surface/map/relief visuals | S1-S6/S11 |
| `date_ring` / `side_knob_i` | D | ~1-2 | optional secondary rotating controls | S4/S6 |

## 关节（Joints）
| 关节 | 类型 | parent_slot.part | child_slot.part | axis | range | 描述 |
|---|---|---|---|---|---|---|
| `base_to_meridian` | REVOLUTE / CONTINUOUS / FIXED | A.base | B.meridian | usually horizontal for tilt, vertical for turntable | bounded or unbounded | support articulation |
| `meridian_to_globe` | CONTINUOUS | B.meridian | C.globe | polar axis | unbounded | sphere spin |
| `date_ring_axis` | CONTINUOUS | A.stand | D.date_ring | `(0,0,1)` | unbounded | optional equatorial ring |
| `knob_i_spin` | CONTINUOUS | A.pedestal | D.side_knob_i | horizontal | unbounded | optional side adjustment knobs |

## 参数范围汇总
| 参数 | 类型 | 取值范围 | 默认 | 派生关系 | 来源 |
|---|---|---|---|---|---|
| `support_style` | enum | `desktop_yoke_base` / `classroom_pedestal` / `floor_turntable_stand` / `wall_arm_mount` / `minimal_single_arm` | `desktop_yoke_base` | Slot A | S1/S2/S7-S9 |
| `cradle_style` | enum | `tilting_meridian_ring` / `full_classroom_meridian` / `marine_gimbal_inner_ring` / `open_two_post_cradle` / `partial_wall_meridian` | `tilting_meridian_ring` | Slot B | S1-S5/S9 |
| `sphere_style` | enum | `relief_world_sphere` / `classroom_marked_sphere` / `celestial_sphere` / `antique_horizon_sphere` | `relief_world_sphere` | Slot C | S1/S2/S5/S11 |
| `secondary_motion` | enum | `meridian_tilt_only` / `base_turntable` / `equatorial_date_ring` / `side_adjustment_knobs` / `none` | `meridian_tilt_only` | optional parallel child | S1/S4-S6 |
| `axial_tilt_deg` | float | `0-30` | 23.5 | globe polar axis relative to support | S1/S2 |

## Multiplicity / Copy Logic

- 无复制数量逻辑：本类别的核心结构是 one base/support, one cradle/meridian family, and one rotating globe. The template should not expose a `globe_count`, `ring_count`, or sampled `knob_count`.
- `side_knob_i` in the joint table is source-local optional control naming for the `side_adjustment_knobs` module. It is not a category-level random count loop and should remain a fixed small structure defined by that selected module.
- Map/relief/latitude-longitude markings are visual detail on the single `globe` part, not repeated independent parts or joints.

## 拓扑多样性审计

总组合数：`5 support × 5 cradle × 4 sphere × 5 secondary = 500`。预计 `module_topology_diversity` 门控（>=5 distinct）能过：yes，support/cradle/secondary slots change joint chain and part count substantially.

| slot | candidate_count | 是否 >=3 | 备注 |
|---|---:|---|---|
| base_support | 5 | yes | |
| meridian_cradle | 5 | yes | |
| sphere_map | 4 | yes | |
| secondary_motion | 5 | yes | includes `none` |

## Validator（author_run_tests 必须覆盖的点）
- 必须有 rotating `globe` part and continuous polar spin.
- globe must be seated between visible pivots/ring/fork; no floating sphere.
- meridian/cradle tilt axis, if present, must be supported by yoke/trunnions.
- surface relief/map visuals must belong to `globe`, not separate fixed parts.
- wall/floor/desktop variants must have stable support contacting ground or wall plane.

## Reject cases（必须能识别并拒绝）
- 只有球体，没有 stand/cradle and spin joint.
- globe spin axis not passing through sphere center.
- meridian ring intersects sphere heavily without intended trunnion contact.
- date ring / side knobs floating or created as unanchored decorative fixed parts.

## 与相邻类别的边界
- `turntable`：turntable platter is a flat disc with tonearm; globe has sphere and meridian/cradle.
- `planetarium` / `orrery`：multiple orbiting bodies are out of scope.
- `ceiling_light_fixture`：globe shade without map/cradle/spin is not this category.

## 审核记录
| 项 | 结论 |
|---|---|
| reviewer status | pending |
| reviewer notes | SPEC_ONLY_DRAFT；等待人工审核 |
