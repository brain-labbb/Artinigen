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
| pattern | `mixed` |

## 5 星样本阅读摘要
| 项 | 值 |
|---|---|
| five_star_total | 41 |
| read_count | 41 |
| read_scope | all 5-star samples in this category; each record's `record.json`, active `revision.json`, `prompt.txt`, and `model.py` were scanned |
| samples_adopted_as_module_sources | 15 |
| samples_read_but_not_adopted | 26 |
| source_index_policy | adopted sources cover pedestal/tripod/wall/mobile/foundation supports, azimuth/elevation stage types, reflector/feed structures, and parallel service accessories |

- adopted as module sources: `rec_parabolic_dish_on_azimuth_elevation_mount_0004`, `rec_parabolic_dish_on_azimuth_elevation_mount_0005`, `rec_parabolic_dish_on_azimuth_elevation_mount_0112ba3226e1487192d3e73272a2db3d`, `rec_parabolic_dish_on_azimuth_elevation_mount_1a992a547a104469adb6a6b286f64e1d`, `rec_parabolic_dish_on_azimuth_elevation_mount_2b902e3ce5fc4373a2baa152a81521f2`, `rec_parabolic_dish_on_azimuth_elevation_mount_2ffd03382a5d419495965dfc566cd328`, `rec_parabolic_dish_on_azimuth_elevation_mount_424fe9ce18ea459db2e8e308da1c0aa3`, `rec_parabolic_dish_on_azimuth_elevation_mount_49566120c578436cb5061a6f0e715707`, `rec_parabolic_dish_on_azimuth_elevation_mount_77d410b1f7eb461e8ced096380b9939b`, `rec_parabolic_dish_on_azimuth_elevation_mount_a10cd68df45446dea72f5ab62d12b71f`, `rec_parabolic_dish_on_azimuth_elevation_mount_f1a5c78bd7e14a5aa372d61ed97fce17`, `rec_parabolic_dish_on_azimuth_elevation_mount_f862b07ed3e543f998f3ad7cccae3942`, `rec_radar_dish_on_pedestal_0001`, `rec_radio_telescope_on_azimuthelevation_mount_0001`, `rec_satellite_dish_on_pedestal_0001`.
- read but not adopted: `rec_parabolic_dish_on_azimuth_elevation_mount_0d4863f732e4437cbb72d2143499d39a`, `rec_parabolic_dish_on_azimuth_elevation_mount_113598a9eab74e75807c3aaae00aa262`, `rec_parabolic_dish_on_azimuth_elevation_mount_11d08956138d4c589cb527b07caeb7b0`, `rec_parabolic_dish_on_azimuth_elevation_mount_121fa18bce2642609c5eec64bac0fc07`, `rec_parabolic_dish_on_azimuth_elevation_mount_179aacb4fc8f481390ae0d97bb292f5e`, `rec_parabolic_dish_on_azimuth_elevation_mount_18eff859d8854213a75f4d5e0743a692`, `rec_parabolic_dish_on_azimuth_elevation_mount_22ad7145310e4dd9a378796027aa50f1`, `rec_parabolic_dish_on_azimuth_elevation_mount_3915507c20f348648f2986027fc5b7d6`, `rec_parabolic_dish_on_azimuth_elevation_mount_3d21d27db6d24321a13496e6c6104cfa`, `rec_parabolic_dish_on_azimuth_elevation_mount_3ebbc287998444179c7080d3a2807954`, `rec_parabolic_dish_on_azimuth_elevation_mount_4c59ed2aab1e4d4aa702dda68c40054a`, `rec_parabolic_dish_on_azimuth_elevation_mount_5c50c36bb8e4477ba523592bb2aaaf79`, `rec_parabolic_dish_on_azimuth_elevation_mount_6cae286c2723453989eb2a05cdedb038`, `rec_parabolic_dish_on_azimuth_elevation_mount_7ba40683e2a848c0991bb9294e60f9e8`, `rec_parabolic_dish_on_azimuth_elevation_mount_7c38db97269e429bb14d2b04998c5167`, `rec_parabolic_dish_on_azimuth_elevation_mount_7c7f540f3bc54fa29b7d54bb85b26ce1`, `rec_parabolic_dish_on_azimuth_elevation_mount_7f8512f01f3c4faf96101c5b596b1cf0`, `rec_parabolic_dish_on_azimuth_elevation_mount_a591490345ea40fe9c2ee315910e1855`, `rec_parabolic_dish_on_azimuth_elevation_mount_aedd5aed8708470a8566356d353c2520`, `rec_parabolic_dish_on_azimuth_elevation_mount_b24c9d542fd240bc80621921efd1b24d`, `rec_parabolic_dish_on_azimuth_elevation_mount_b46d320f8c5e484d8e911539ce34497d`, `rec_parabolic_dish_on_azimuth_elevation_mount_c60113318280491da3f28e81389e17af`, `rec_parabolic_dish_on_azimuth_elevation_mount_d8ba65c1b7a74a15b9b6c5b2342312ee`, `rec_parabolic_dish_on_azimuth_elevation_mount_f10149fa181245c4b6d04588513feff4`, `rec_parabolic_dish_on_azimuth_elevation_mount_f7afffc3fbc14af38b62a74b9a4bb6d4`, `rec_parabolic_dish_on_azimuth_elevation_mount_ff95ab246ac04d8d92e07ad4c874a686`; reason: duplicate pedestal/yoke/reflector/accessory variants already covered.

## 核心身份

This category is a parabolic reflector carried by an azimuth-elevation pointing mount: a grounded, roof, wall, shipboard, tripod, or observatory base rotates around vertical azimuth; a yoke/cradle/side bracket tilts the reflector around a horizontal elevation axis. The reflector assembly includes dish shell, rear support/back frame, and feed horn/boom/truss. Optional controls include side crank, lock knob, transport leg, electronics cover, or rear hatch.

边界：
- 不包括 satellite bus with solar panels; this is ground/vehicle infrastructure, not spacecraft.
- 不混入 CCTV pan-tilt head: this must have a parabolic dish/reflector and feed structure.

## 采用源码索引（Adopted Source Index）
| source_id | sample_id | model.py 来源 | 采纳用途 |
|---|---|---|---|
| S1 | `rec_parabolic_dish_on_azimuth_elevation_mount_0004` | `data/records/rec_parabolic_dish_on_azimuth_elevation_mount_0004/revisions/rev_000001/model.py:L148-L342` | pedestal + azimuth yoke + reflector, continuous yaw and revolute elevation |
| S2 | `rec_parabolic_dish_on_azimuth_elevation_mount_0005` | `data/records/rec_parabolic_dish_on_azimuth_elevation_mount_0005/revisions/rev_000001/model.py:L187-L371` | deep reflector and rear truss support |
| S3 | `rec_parabolic_dish_on_azimuth_elevation_mount_0112ba3226e1487192d3e73272a2db3d` | `data/records/rec_parabolic_dish_on_azimuth_elevation_mount_0112ba3226e1487192d3e73272a2db3d/revisions/rev_000001/model.py:L198-L463` | bounded azimuth REVOLUTE, yoke mount, reflector assembly |
| S4 | `rec_parabolic_dish_on_azimuth_elevation_mount_1a992a547a104469adb6a6b286f64e1d` | `data/records/rec_parabolic_dish_on_azimuth_elevation_mount_1a992a547a104469adb6a6b286f64e1d/revisions/rev_000001/model.py:L146-L358` | rooftop mesh reflector and side feed boom |
| S5 | `rec_parabolic_dish_on_azimuth_elevation_mount_2b902e3ce5fc4373a2baa152a81521f2` | `data/records/rec_parabolic_dish_on_azimuth_elevation_mount_2b902e3ce5fc4373a2baa152a81521f2/revisions/rev_000001/model.py:L31-L220` | wall bracket, clamp head, side elevation plate |
| S6 | `rec_parabolic_dish_on_azimuth_elevation_mount_2ffd03382a5d419495965dfc566cd328` | `data/records/rec_parabolic_dish_on_azimuth_elevation_mount_2ffd03382a5d419495965dfc566cd328/revisions/rev_000001/model.py:L149-L377` | roof tripod, compact azimuth head, VSAT dish frame |
| S7 | `rec_parabolic_dish_on_azimuth_elevation_mount_424fe9ce18ea459db2e8e308da1c0aa3` | `data/records/rec_parabolic_dish_on_azimuth_elevation_mount_424fe9ce18ea459db2e8e308da1c0aa3/revisions/rev_000001/model.py:L105-L382` | mobile base and fold-down transport leg |
| S8 | `rec_parabolic_dish_on_azimuth_elevation_mount_49566120c578436cb5061a6f0e715707` | `data/records/rec_parabolic_dish_on_azimuth_elevation_mount_49566120c578436cb5061a6f0e715707/revisions/rev_000001/model.py:L177-L453` | large dish, instrument box, rear hatch |
| S9 | `rec_parabolic_dish_on_azimuth_elevation_mount_77d410b1f7eb461e8ced096380b9939b` | `data/records/rec_parabolic_dish_on_azimuth_elevation_mount_77d410b1f7eb461e8ced096380b9939b/revisions/rev_000001/model.py:L104-L366` | observatory foundation and azimuth carriage |
| S10 | `rec_parabolic_dish_on_azimuth_elevation_mount_a10cd68df45446dea72f5ab62d12b71f` | `data/records/rec_parabolic_dish_on_azimuth_elevation_mount_a10cd68df45446dea72f5ab62d12b71f/revisions/rev_000001/model.py:L91-L385` | rear electronics cover on dish assembly |
| S11 | `rec_parabolic_dish_on_azimuth_elevation_mount_f1a5c78bd7e14a5aa372d61ed97fce17` | `data/records/rec_parabolic_dish_on_azimuth_elevation_mount_f1a5c78bd7e14a5aa372d61ed97fce17/revisions/rev_000001/model.py:L100-L327` | twin feed supports and lock knob |
| S12 | `rec_parabolic_dish_on_azimuth_elevation_mount_f862b07ed3e543f998f3ad7cccae3942` | `data/records/rec_parabolic_dish_on_azimuth_elevation_mount_f862b07ed3e543f998f3ad7cccae3942/revisions/rev_000001/model.py:L118-L284` | shipboard gimbal-like pedestal |
| S13 | `rec_radar_dish_on_pedestal_0001` | `data/records/rec_radar_dish_on_pedestal_0001/revisions/rev_000001/model.py:L64-L182` | radar dish/pedestal compact reference |
| S14 | `rec_radio_telescope_on_azimuthelevation_mount_0001` | `data/records/rec_radio_telescope_on_azimuthelevation_mount_0001/revisions/rev_000001/model.py:L192-L427` | large radio telescope scale/reference |
| S15 | `rec_satellite_dish_on_pedestal_0001` | `data/records/rec_satellite_dish_on_pedestal_0001/revisions/rev_000001/model.py:L160-L254` | satellite-dish pedestal canonical chain |

## 槽位 + 候选模块表

### Slot A：base_mount
| module_name | 5_star_source | model.py:Lx-Ly | seed=0 anchor | 结构特征 |
|---|---|---|---|---|
| `pedestal_base` | `rec_parabolic_dish_on_azimuth_elevation_mount_0004` | L148-L184 | **yes** | short pedestal with azimuth bearing seat |
| `tripod_roof_base` | `rec_parabolic_dish_on_azimuth_elevation_mount_2ffd03382a5d419495965dfc566cd328` | L149-L190 | | roof tripod with compact head |
| `wall_bracket_mast` | `rec_parabolic_dish_on_azimuth_elevation_mount_2b902e3ce5fc4373a2baa152a81521f2` | L31-L138 | | wall plate, pipe mast, clamp head |
| `mobile_base_frame` | `rec_parabolic_dish_on_azimuth_elevation_mount_424fe9ce18ea459db2e8e308da1c0aa3` | L105-L172 | | transportable base frame and pedestal |
| `observatory_foundation` | `rec_parabolic_dish_on_azimuth_elevation_mount_77d410b1f7eb461e8ced096380b9939b` | L104-L198 | | large foundation and azimuth carriage seat |

### Slot B：az_el_stage
| module_name | 5_star_source | model.py:Lx-Ly | seed=0 anchor | 结构特征 |
|---|---|---|---|---|
| `continuous_yoke` | `rec_parabolic_dish_on_azimuth_elevation_mount_0004` | L185-L342 | **yes** | azimuth CONTINUOUS + elevation REVOLUTE yoke |
| `bounded_yoke` | `rec_parabolic_dish_on_azimuth_elevation_mount_0112ba3226e1487192d3e73272a2db3d` | L235-L463 | | both azimuth and elevation as bounded REVOLUTE |
| `compact_top_plate_bracket` | `rec_parabolic_dish_on_azimuth_elevation_mount_2ffd03382a5d419495965dfc566cd328` | L191-L377 | | compact azimuth head with side elevation pivots |
| `shipboard_gimbal` | `rec_parabolic_dish_on_azimuth_elevation_mount_f862b07ed3e543f998f3ad7cccae3942` | L143-L284 | | compact maritime turntable and elevation head |

### Slot C：reflector_feed
| module_name | 5_star_source | model.py:Lx-Ly | seed=0 anchor | 结构特征 |
|---|---|---|---|---|
| `parabolic_reflector_feed_arm` | `rec_parabolic_dish_on_azimuth_elevation_mount_0004` | L240-L342 | **yes** | reflector with rear frame and feed arm |
| `deep_truss_reflector` | `rec_parabolic_dish_on_azimuth_elevation_mount_0005` | L258-L371 | | deep reflector and rear truss-like support |
| `mesh_rooftop_reflector` | `rec_parabolic_dish_on_azimuth_elevation_mount_1a992a547a104469adb6a6b286f64e1d` | L266-L358 | | mesh reflector with side feed boom |
| `instrumented_large_dish` | `rec_parabolic_dish_on_azimuth_elevation_mount_49566120c578436cb5061a6f0e715707` | L291-L453 | | large dish plus instrument box/hatch |

### Slot D：service_accessory
| module_name | 5_star_source | model.py:Lx-Ly | seed=0 anchor | 结构特征 |
|---|---|---|---|---|
| `none` | `rec_parabolic_dish_on_azimuth_elevation_mount_0004` | L148-L342 | **yes** | canonical mount with no extra moving accessory |
| `side_crank` | `rec_parabolic_dish_on_azimuth_elevation_mount_f1a5c78bd7e14a5aa372d61ed97fce17` | L268-L327 | | continuous side lock/crank knob |
| `transport_leg` | `rec_parabolic_dish_on_azimuth_elevation_mount_424fe9ce18ea459db2e8e308da1c0aa3` | L315-L382 | | fold-down REVOLUTE leg on base frame |
| `rear_cover` | `rec_parabolic_dish_on_azimuth_elevation_mount_a10cd68df45446dea72f5ab62d12b71f` | L312-L385 | | hinged electronics cover on dish back frame |
| `instrument_hatch` | `rec_parabolic_dish_on_azimuth_elevation_mount_49566120c578436cb5061a6f0e715707` | L368-L453 | | instrument box fixed to dish plus hatch REVOLUTE |

## 槽位图（slot graph）

pattern: `mixed`

```text
[Slot A base_mount]
  -- azimuth: CONTINUOUS/REVOLUTE, axis Z -->
[Slot B az_el_stage]
  -- elevation: REVOLUTE, horizontal axis -->
[Slot C reflector_feed]

[Slot A/B/C] -- optional parallel CONTINUOUS/REVOLUTE/FIXED --> [Slot D service_accessory]
```

## 部件（Parts）
| part | slot | visual_count | 描述 | 来源 |
|---|---|---:|---|---|
| `pedestal` / `tripod_base` / `wall_mount` / `foundation` | A | ~3-10 | grounded/roof/wall/ship/mobile support | S1/S5-S9/S12 |
| `azimuth_yoke` / `azimuth_stage` / `clamp_head` | B | ~5-12 | yawing head and elevation support | S1-S6/S12 |
| `dish_assembly` / `reflector` / `antenna_head` | C | ~8-22 | parabolic shell, back frame, feed, truss | S1-S4/S8 |
| `side_crank` / `transport_leg` / `rear_cover` / `instrument_hatch` | D | ~3-5 | optional articulated accessory | S7/S8/S10/S11 |

## 关节（Joints）
| 关节 | 类型 | parent_slot.part | child_slot.part | axis | range | 描述 |
|---|---|---|---|---|---|---|
| `azimuth_rotation` | CONTINUOUS / REVOLUTE | A.base | B.azimuth_stage | `(0,0,1)` | unbounded or bounded | yaw around vertical |
| `elevation_rotation` | REVOLUTE | B.azimuth_stage | C.dish | horizontal `(0,1,0)` or `(1,0,0)` | bounded tilt | dish elevation |
| `crank_rotation` | CONTINUOUS | B.stage | D.side_crank | horizontal | unbounded | optional side crank |
| `transport_leg_hinge` | REVOLUTE | A.base_frame | D.transport_leg | horizontal | deploy/stow | optional mobile leg |
| `rear_cover_hinge` | REVOLUTE | C.dish/instrument_box | D.cover | local hinge | open/close | optional cover/hatch |

## 参数范围汇总
| 参数 | 类型 | 取值范围 | 默认 | 派生关系 | 来源 |
|---|---|---|---|---|---|
| `base_style` | enum | `pedestal_base` / `tripod_roof_base` / `wall_bracket_mast` / `mobile_base_frame` / `observatory_foundation` | `pedestal_base` | Slot A | S1/S5-S9 |
| `stage_style` | enum | `continuous_yoke` / `bounded_yoke` / `compact_top_plate_bracket` / `shipboard_gimbal` | `continuous_yoke` | Slot B | S1/S3/S6/S12 |
| `reflector_style` | enum | `parabolic_reflector_feed_arm` / `deep_truss_reflector` / `mesh_rooftop_reflector` / `instrumented_large_dish` | `parabolic_reflector_feed_arm` | Slot C | S1/S2/S4/S8 |
| `accessory_style` | enum | `none` / `side_crank` / `transport_leg` / `rear_cover` / `instrument_hatch` | `none` | Slot D | S7/S8/S10/S11 |
| `azimuth_type` | enum | `continuous` / `bounded_revolute` | `continuous` | derived from stage | S1/S3 |
| `dish_depth` | float | shallow/deep continuous range | sampled | tied to reflector style | S1/S2/S4 |

## Multiplicity / Copy Logic

- 无复制数量逻辑：本类别的 core articulation is one grounded base/mount, one azimuth stage, and one elevation dish/feed assembly. The template should not expose `dish_count`, `feed_arm_count`, or sampled `leg_count`.
- Tripod legs, truss ribs, mesh struts, bolts, and support braces inside selected modules are source-local fixed structure or baked visuals. They can vary by module style but should not become an independent count-sampling axis.
- Optional accessories such as crank, transport leg, rear cover, or instrument hatch are named Slot D modules, not cloned N times.

## 拓扑多样性审计

总组合数：`5 base × 4 stage × 4 reflector × 5 accessory = 400`。预计 `module_topology_diversity` 门控（>=5 distinct）能过：yes，base grounding mode, azimuth joint type, reflector part tree, and accessory joints all change topology.

| slot | candidate_count | 是否 >=3 | 备注 |
|---|---:|---|---|
| base_mount | 5 | yes | |
| az_el_stage | 4 | yes | |
| reflector_feed | 4 | yes | |
| service_accessory | 5 | yes | includes `none` |

## Validator（author_run_tests 必须覆盖的点）
- 必须有 azimuth joint around vertical and elevation joint around horizontal.
- reflector/dish must be visibly mounted in yoke/cradle; no floating dish.
- feed arm/horn must be attached to reflector/back frame and aimed toward dish center.
- wall/tripod/mobile/foundation supports must have appropriate ground/wall contact.
- optional cover/leg/crank/hatch must have real parent mating surfaces.

## Reject cases（必须能识别并拒绝）
- Dish without parabolic reflector or feed structure.
- Azimuth/elevation axes swapped or both vertical.
- Reflector intersects support through its bowl sweep without intended contact.
- Service accessories floating or represented by fixed child decorations.
- Spacecraft satellite bus with solar arrays; that belongs to satellite category.

## 与相邻类别的边界
- `satellite_with_articulated_solar_panels`：spacecraft bus and solar wings, no grounded az/el pedestal.
- `cctv_mast_with_pantilt_camera_head`：camera head rather than parabolic dish/feed.
- `radio_telescope` standalone: allowed as scale variant only when record category is this az/el dish class.

## 审核记录
| 项 | 结论 |
|---|---|
| reviewer status | pending |
| reviewer notes | SPEC_ONLY_DRAFT；等待人工审核 |
