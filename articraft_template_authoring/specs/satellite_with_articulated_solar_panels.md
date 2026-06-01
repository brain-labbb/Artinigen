# Satellite With Articulated Solar Panels Spec

## 元信息
| 项 | 值 |
|---|---|
| slug | `satellite_with_articulated_solar_panels` |
| template path | `agent/templates/satellite_with_articulated_solar_panels.py` |
| test path | `tests/agent/test_satellite_with_articulated_solar_panels_template.py` |
| stage | `SOURCE_BLOCKED` |
| status | `needs_5_star_sources` |
| __modular__ | `True` |
| pattern | `mixed` |

## 5 星样本阅读摘要
| 项 | 值 |
|---|---|
| five_star_total | 0 |
| read_count | 0 |
| read_scope | all records in this category were enumerated; there are no rating-5 records available |
| samples_adopted_as_module_sources | 0 |
| samples_read_but_not_adopted | 0 |
| blocking_reason | SPEC_ONLY requires real 5-star module sources; this category currently has only one rating-4 dataset record |

Non-5-star reference found but **not adopted as 5-star source**: `rec_a-realistic-model-of-a-satellite_20260402_161121_286240_c5af0a24` (rating 4), with `model.py` at `data/records/rec_a-realistic-model-of-a-satellite_20260402_161121_286240_c5af0a24/revisions/rev_000001/model.py`. It contains `bus`, `left_solar_wing`, `right_solar_wing`, and `high_gain_antenna`; solar wings are REVOLUTE on bus, antenna is FIXED. Because it is not 5-star and there is only one structural family, it cannot satisfy the normal SPEC_ONLY module-source contract.

## 核心身份

Target identity, pending source approval: a spacecraft bus with articulated solar-array wings. The main bus carries avionics/radiators/antenna hardware; one or more solar panels deploy from hinges on bus sides; optional high-gain antenna, sensor mast, engine/nozzle, or secondary booms are attached to the bus. The core motion is solar panel deployment/retraction around bus-mounted hinges; optional antenna articulation may be added only when supported by future 5-star sources.

边界：
- 不包括 ground parabolic dish mounts; those belong to `parabolic_dish_on_azimuth_elevation_mount`.
- 不混入 drone/aircraft: this is an orbital spacecraft bus, not an aerodynamic vehicle.

## Provisional Non-Adopted Source Index
| source_id | sample_id | rating | model.py 来源 | observed structure |
|---|---|---:|---|---|
| R4-1 | `rec_a-realistic-model-of-a-satellite_20260402_161121_286240_c5af0a24` | 4 | `data/records/rec_a-realistic-model-of-a-satellite_20260402_161121_286240_c5af0a24/revisions/rev_000001/model.py:L86-L360` | `bus` with two `solar_wing` parts, two REVOLUTE deployment hinges, and fixed high-gain antenna |

## 槽位 + 候选模块表

Normal candidate tables are intentionally **not filled** because every candidate must cite a real 5-star source. A future approved spec should target at least:

| intended slot | minimum candidate families needed | notes |
|---|---|---|
| `bus_body` | 3 | boxy communications bus, cylindrical/hexagonal bus, truss bus |
| `solar_array` | 3 | single-panel wing, multi-panel foldout, bilateral long wing |
| `antenna_or_payload` | 3 | fixed high-gain dish, articulated antenna boom, sensor mast/payload module |
| `deployment_topology` | 2-3 | bilateral hinges, four-wing cross, nested fold panel chain |

## 槽位图（slot graph）

pattern target: `mixed`

```text
[bus_body]
  ├── REVOLUTE deploy hinge(s) --> [solar_array_i]
  ├── optional REVOLUTE/CONTINUOUS --> [antenna_or_payload]
  └── fixed visuals: radiators, decks, engine nozzle, star tracker
```

## 参数范围汇总
| 参数 | 类型 | intended range | 默认 | 来源状态 |
|---|---|---|---|---|
| `bus_style` | enum | pending 5-star sources | pending | blocked |
| `solar_wing_count` | int | 2 / 4 / maybe 1 | 2 | blocked |
| `panel_segments_per_wing` | int | 1-4 | 2 | blocked |
| `antenna_style` | enum | none / fixed / articulated | pending | blocked |

## Multiplicity / Copy Logic

Blocked/provisional only; do not implement from the current source set.

- Future `solar_wing_count` would control how many solar-array wings are attached to the bus. The current non-adopted rating-4 reference shows bilateral `N=2`; `N=1` or `N=4` needs 5-star backing before it becomes a normal sampling option.
- Future `panel_segments_per_wing` would control repeated panel segments within each wing. A single-panel wing uses one REVOLUTE bus hinge; a segmented foldout wing would be a serial chain of `wing_i_segment_j` parts/joints only if future sources support that topology.
- Naming should distinguish wing-level and segment-level multiplicity, for example `solar_wing_i`, `solar_wing_i_deploy`, `solar_wing_i_segment_j`, and `solar_wing_i_segment_j_fold`.
- Placement must keep solar wings attached to visible bus-side hinge barrels or yokes. Bilateral wings should mirror across the bus; four-wing topology should distribute roots on supported bus faces.
- Because this spec has zero 5-star sources, every count range above remains blocked and cannot satisfy `module_topology_diversity`.

## 拓扑多样性审计

正常 SPEC_ONLY 组合数：not applicable. Current 5-star source count is 0, so expected `module_topology_diversity` cannot be justified. The single rating-4 reference would yield at most one bus family and one solar-wing family, below the module-source contract.

| slot | candidate_count | 是否 >=3 | 备注 |
|---|---:|---|---|
| bus_body | 0 | no | no 5-star sources |
| solar_array | 0 | no | no 5-star sources |
| antenna_or_payload | 0 | no | no 5-star sources |

## Validator（future approved spec should cover）
- Bus must be the root spacecraft body and carry all non-moving radiators/decks/nozzles as visuals.
- Solar arrays must be separate articulated parts with visible hinge barrels/clevises on the bus.
- Deployment hinge axes must align with the panel root and keep panels clear of the bus.
- Optional antenna/payload must not be mistaken for ground dish infrastructure.

## Reject cases（必须能识别并拒绝）
- No articulated solar panels.
- Solar panels as floating slabs with no hinge/root yoke.
- Ground pedestal dish or drone/aircraft silhouette.
- A one-source template claiming module diversity without 5-star backing.

## 与相邻类别的边界
- `parabolic_dish_on_azimuth_elevation_mount`：ground/roof/wall az-el mount, not spacecraft bus.
- `drone` / `single_rotor_helicopter`：aerodynamic vehicles with rotors/landing gear, not orbital bus/solar arrays.

## 审核记录
| 项 | 结论 |
|---|---|
| reviewer status | source-blocked |
| reviewer notes | Need at least several rating-5 records before converting this to `SPEC_ONLY_DRAFT`; do not implement a template from the single rating-4 source alone. |
