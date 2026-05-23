# Bicycle Fork And Handlebar Assembly Spec

## 元信息
| 项 | 值 |
|---|---|
| slug | `bicycle_fork_and_handlebar_assembly` |
| template path | `agent/templates/bicycle_fork_and_handlebar_assembly.py` |
| test path | `tests/agent/test_bicycle_fork_and_handlebar_assembly_template.py` |
| stage | `SPEC_ONLY_DRAFT` |
| status | `SPEC_ONLY_DRAFT` |

## 5 星样本阅读摘要
| 项 | 值 |
|---|---|
| five_star_total | 37 |
| read_count | 37 |
| read_scope | all 5-star samples in this category |
| source_index_policy | only adopted reusable snippets are indexed below |

## 核心身份
自行车前端转向组件，由 head tube/headset 固定结构、可转向的 fork/steerer、stem 和 handlebar 组成；可选 suspension lower legs、quill height adjustment、handlebar angle adjustment、front rack 和 brake hardware。

## 采用源码索引（Adopted Source Index）
| source_id | sample_id | model.py 来源 | 采纳用途 |
|---|---|---|---|
| S1 | rec_bicycle_fork_and_handlebar_assembly_0005 | `data/records/rec_bicycle_fork_and_handlebar_assembly_0005/revisions/rev_000001/model.py:L137-L397` | road fork baseline: head tube, rigid fork blades, threadless stem, drop bar, steering joint |
| S2 | rec_bicycle_fork_and_handlebar_assembly_276e99adfa7d485bad00a29bd2bc2fa1 | `data/records/rec_bicycle_fork_and_handlebar_assembly_276e99adfa7d485bad00a29bd2bc2fa1/revisions/rev_000001/model.py:L104-L340` | suspension fork: crown, upper sleeves, lower legs, prismatic compression, stem/bar joints |
| S3 | rec_bicycle_fork_and_handlebar_assembly_054d0e4b729646468a58c8afb1e39170 | `data/records/rec_bicycle_fork_and_handlebar_assembly_054d0e4b729646468a58c8afb1e39170/revisions/rev_000001/model.py:L55-L253` | quill stem: fork shell, drop bars, prismatic stem height and revolute bar angle |
| S4 | rec_bicycle_fork_and_handlebar_assembly_f35bef096f6447ada25fd46bd0a7893a | `data/records/rec_bicycle_fork_and_handlebar_assembly_f35bef096f6447ada25fd46bd0a7893a/revisions/rev_000001/model.py:L113-L308` | cargo/commuter fork: unicrown curved blades, riser stem, flat bar and front rack |
| S5 | rec_bicycle_fork_and_handlebar_assembly_4963f76fb70a4a7faa9b4cdc5e0e0e1d | `data/records/rec_bicycle_fork_and_handlebar_assembly_4963f76fb70a4a7faa9b4cdc5e0e0e1d/revisions/rev_000001/model.py:L83-L403` | aero integrated cockpit: fixed steerer/stem and continuous/revolute handlebar clamp rotation |

## 部件（Parts）
| 部件 | 描述 | 参数 | 来源 |
|---|---|---|---|
| head_tube | 固定头管/车架前端 stub，含 upper/lower headset cups | head_tube_style: enum, head_tube_length: float, head_angle: float | S1 / `data/records/rec_bicycle_fork_and_handlebar_assembly_0005/revisions/rev_000001/model.py:L137-L175`; S5 / `data/records/rec_bicycle_fork_and_handlebar_assembly_4963f76fb70a4a7faa9b4cdc5e0e0e1d/revisions/rev_000001/model.py:L83-L154` |
| fork | 可转向前叉主体，含 steerer、crown、左右 blade、dropouts | fork_style: enum, blade_profile: enum, blade_length: float, dropout_style: enum | S1 / `data/records/rec_bicycle_fork_and_handlebar_assembly_0005/revisions/rev_000001/model.py:L176-L245`; S3 / `data/records/rec_bicycle_fork_and_handlebar_assembly_054d0e4b729646468a58c8afb1e39170/revisions/rev_000001/model.py:L55-L110`; S4 / `data/records/rec_bicycle_fork_and_handlebar_assembly_f35bef096f6447ada25fd46bd0a7893a/revisions/rev_000001/model.py:L120-L192` |
| suspension_lower_left / suspension_lower_right | 可选避震下腿，沿左右 upper sleeve/stanchion 做 prismatic compression | suspension_enabled: bool, suspension_travel: float, lower_leg_style: enum | S2 / `data/records/rec_bicycle_fork_and_handlebar_assembly_276e99adfa7d485bad00a29bd2bc2fa1/revisions/rev_000001/model.py:L104-L219` |
| stem | stem 或 quill stem；连接 steerer 与 handlebar clamp | stem_style: enum, stem_length: float, stem_rise: float, quill_height_adjust: bool | S1 / `data/records/rec_bicycle_fork_and_handlebar_assembly_0005/revisions/rev_000001/model.py:L247-L283`; S2 / `data/records/rec_bicycle_fork_and_handlebar_assembly_276e99adfa7d485bad00a29bd2bc2fa1/revisions/rev_000001/model.py:L221-L257`; S3 / `data/records/rec_bicycle_fork_and_handlebar_assembly_054d0e4b729646468a58c8afb1e39170/revisions/rev_000001/model.py:L111-L176`; S5 / `data/records/rec_bicycle_fork_and_handlebar_assembly_4963f76fb70a4a7faa9b4cdc5e0e0e1d/revisions/rev_000001/model.py:L232-L319` |
| faceplate | 可选 stem faceplate/clamp plate，通常 fixed 到 stem | faceplate_enabled: bool, bolt_count: int | S1 / `data/records/rec_bicycle_fork_and_handlebar_assembly_0005/revisions/rev_000001/model.py:L284-L303`; S5 / `data/records/rec_bicycle_fork_and_handlebar_assembly_4963f76fb70a4a7faa9b4cdc5e0e0e1d/revisions/rev_000001/model.py:L269-L303` |
| handlebar | drop/flat/riser/swept/bullhorn/aero handlebar，含 grips/tape/hoods | handlebar_style: enum, bar_width: float, bar_sweep: float, bar_drop: float | S1 / `data/records/rec_bicycle_fork_and_handlebar_assembly_0005/revisions/rev_000001/model.py:L305-L373`; S2 / `data/records/rec_bicycle_fork_and_handlebar_assembly_276e99adfa7d485bad00a29bd2bc2fa1/revisions/rev_000001/model.py:L258-L287`; S5 / `data/records/rec_bicycle_fork_and_handlebar_assembly_4963f76fb70a4a7faa9b4cdc5e0e0e1d/revisions/rev_000001/model.py:L320-L391` |
| front_rack | 货架/commuter 变体的可选前置平台，fixed 到 fork low-rider mounts | rack_enabled: bool, rack_style: enum | S4 / `data/records/rec_bicycle_fork_and_handlebar_assembly_f35bef096f6447ada25fd46bd0a7893a/revisions/rev_000001/model.py:L262-L308` |
| brake_levers | 可选 compact brake-lever hardware，样本中少量出现；作为 handlebar child 或 fixed part | brake_lever_style: enum, brake_lever_enabled: bool | S1 / `data/records/rec_bicycle_fork_and_handlebar_assembly_0005/revisions/rev_000001/model.py:L361-L373` |

## 关节（Joints）
| 关节 | 类型 | axis | origin | range | 描述 | 来源 |
|---|---|---|---|---|---|---|
| steering_axis | revolute or continuous | `(0, 0, 1)` after world normalization | head tube/steerer centerline | `[-0.6, 0.6]` to `[-1.2, 1.2]`; continuous only for full-spin variants | fork/steerer relative to head tube steering | S1 / `data/records/rec_bicycle_fork_and_handlebar_assembly_0005/revisions/rev_000001/model.py:L374-L382`; S4 / `data/records/rec_bicycle_fork_and_handlebar_assembly_f35bef096f6447ada25fd46bd0a7893a/revisions/rev_000001/model.py:L295-L304` |
| fork_to_stem | fixed | follows steerer axis | steerer top / clamp center | fixed | threadless stem fixed to fork/steerer | S1 / `data/records/rec_bicycle_fork_and_handlebar_assembly_0005/revisions/rev_000001/model.py:L383-L390`; S4 / `data/records/rec_bicycle_fork_and_handlebar_assembly_f35bef096f6447ada25fd46bd0a7893a/revisions/rev_000001/model.py:L306-L308`; S5 / `data/records/rec_bicycle_fork_and_handlebar_assembly_4963f76fb70a4a7faa9b4cdc5e0e0e1d/revisions/rev_000001/model.py:L224-L319` |
| stem_to_handlebar | fixed or revolute/continuous | handlebar clamp roll axis `(1, 0, 0)` or local clamp axis | stem face clamp center | fixed, `[-0.45, 0.35]`, or continuous for aero angle adjustment | handlebar clamped or angle-adjustable in stem | S1 / `data/records/rec_bicycle_fork_and_handlebar_assembly_0005/revisions/rev_000001/model.py:L391-L397`; S3 / `data/records/rec_bicycle_fork_and_handlebar_assembly_054d0e4b729646468a58c8afb1e39170/revisions/rev_000001/model.py:L244-L253`; S5 / `data/records/rec_bicycle_fork_and_handlebar_assembly_4963f76fb70a4a7faa9b4cdc5e0e0e1d/revisions/rev_000001/model.py:L392-L403` |
| suspension_left_slide / suspension_right_slide | prismatic | `(0, 0, 1)` or `(0, 0, -1)` depending child frame | each stanchion/lower-leg axis | `[0, 0.085]` to `[0, 0.14]` | suspension compression along both fork legs | S2 / `data/records/rec_bicycle_fork_and_handlebar_assembly_276e99adfa7d485bad00a29bd2bc2fa1/revisions/rev_000001/model.py:L288-L315` |
| quill_height | prismatic | `(0, 0, 1)` | quill insertion axis inside steerer | `[0, 0.055]` to `[0, 0.075]` | quill stem vertical height adjustment | S3 / `data/records/rec_bicycle_fork_and_handlebar_assembly_054d0e4b729646468a58c8afb1e39170/revisions/rev_000001/model.py:L235-L243` |
| rack_mount | fixed | none | fork low-rider mount frame | fixed | front rack fixed to fork | S4 / `data/records/rec_bicycle_fork_and_handlebar_assembly_f35bef096f6447ada25fd46bd0a7893a/revisions/rev_000001/model.py:L306-L308` |

## 参数范围汇总
| 参数 | 类型 | 取值范围 / 候选值 | 默认值 | 派生关系 | 来源 |
|---|---|---|---|---|---|
| fork_style | enum | `rigid_road` / `unicrown_city` / `bmx_rigid` / `suspension_mtb` / `cargo_unicrown` / `aero_integrated` | `rigid_road` | determines fork/crown/blade/lower-leg parts | S1-S5 |
| handlebar_style | enum | `drop` / `flat` / `riser` / `swept_back` / `bullhorn` / `aero_drop` | `drop` | controls bar geometry and grip/hood placement | S1 / `data/records/rec_bicycle_fork_and_handlebar_assembly_0005/revisions/rev_000001/model.py:L305-L373`; S2 / `data/records/rec_bicycle_fork_and_handlebar_assembly_276e99adfa7d485bad00a29bd2bc2fa1/revisions/rev_000001/model.py:L258-L287`; S5 / `data/records/rec_bicycle_fork_and_handlebar_assembly_4963f76fb70a4a7faa9b4cdc5e0e0e1d/revisions/rev_000001/model.py:L320-L391` |
| stem_style | enum | `threadless_ahead` / `quill` / `integrated_aero` / `riser_stem` | `threadless_ahead` | quill enables `quill_height`; aero may fix steering and rotate bar clamp | S1 / `data/records/rec_bicycle_fork_and_handlebar_assembly_0005/revisions/rev_000001/model.py:L247-L303`; S3 / `data/records/rec_bicycle_fork_and_handlebar_assembly_054d0e4b729646468a58c8afb1e39170/revisions/rev_000001/model.py:L111-L253`; S5 / `data/records/rec_bicycle_fork_and_handlebar_assembly_4963f76fb70a4a7faa9b4cdc5e0e0e1d/revisions/rev_000001/model.py:L232-L403` |
| suspension_enabled | bool | `true / false` | `false` | true adds left/right prismatic lower legs | S2 / `data/records/rec_bicycle_fork_and_handlebar_assembly_276e99adfa7d485bad00a29bd2bc2fa1/revisions/rev_000001/model.py:L104-L315` |
| suspension_travel | float | `0.055-0.140` | `0.085` | prismatic range for both lower legs | S2 / `data/records/rec_bicycle_fork_and_handlebar_assembly_276e99adfa7d485bad00a29bd2bc2fa1/revisions/rev_000001/model.py:L288-L315` |
| steering_range | float | `0.6-1.25` | `0.85` | revolute lower/upper = `+-steering_range` | S1 / `data/records/rec_bicycle_fork_and_handlebar_assembly_0005/revisions/rev_000001/model.py:L374-L382`; S4 / `data/records/rec_bicycle_fork_and_handlebar_assembly_f35bef096f6447ada25fd46bd0a7893a/revisions/rev_000001/model.py:L295-L304` |
| bar_angle_adjust | enum | `fixed` / `limited_revolute` / `continuous_aero` | `fixed` | controls stem_to_handlebar joint type | S3 / `data/records/rec_bicycle_fork_and_handlebar_assembly_054d0e4b729646468a58c8afb1e39170/revisions/rev_000001/model.py:L244-L253`; S5 / `data/records/rec_bicycle_fork_and_handlebar_assembly_4963f76fb70a4a7faa9b4cdc5e0e0e1d/revisions/rev_000001/model.py:L392-L403` |
| rack_enabled | bool | `true / false` | `false` | true adds front_rack fixed to fork | S4 / `data/records/rec_bicycle_fork_and_handlebar_assembly_f35bef096f6447ada25fd46bd0a7893a/revisions/rev_000001/model.py:L262-L308` |
| brake_lever_enabled | bool | `true / false` | `false` | drop bar variants may attach hoods/levers | S1 / `data/records/rec_bicycle_fork_and_handlebar_assembly_0005/revisions/rev_000001/model.py:L361-L373` |
| blade_profile | enum | `straight_round` / `curved_blade` / `bladed_carbon` / `oversized_fat` / `suspension_stanchion` | `bladed_carbon` | constrained by `fork_style` | S1 / `data/records/rec_bicycle_fork_and_handlebar_assembly_0005/revisions/rev_000001/model.py:L200-L245`; S2 / `data/records/rec_bicycle_fork_and_handlebar_assembly_276e99adfa7d485bad00a29bd2bc2fa1/revisions/rev_000001/model.py:L153-L219`; S4 / `data/records/rec_bicycle_fork_and_handlebar_assembly_f35bef096f6447ada25fd46bd0a7893a/revisions/rev_000001/model.py:L139-L192` |

## 部件多样性审计（Part Diversity Audit）
| 部件类型 | observed_variation | 连续参数是否足够 | 是否需要离散参数 | 推荐参数 | 说明 |
|---|---|---|---|---|---|
| fork/crown | rigid road, unicrown city/cargo, BMX/fat wide crown, suspension crown, aero integrated | no | yes | fork_style, blade_profile | crown/blade topology and suspension parts differ qualitatively |
| lower legs | none / paired telescoping suspension lower legs | no | yes | suspension_enabled, lower_leg_style | prismatic lower legs are separate parts only in suspension variants |
| handlebar | drop, flat, riser, swept-back, bullhorn, aero drop | no | yes | handlebar_style | bar shape cannot be represented by width/sweep only |
| stem | threadless ahead, quill, riser, integrated aero | no | yes | stem_style | insertion, clamp and joint semantics differ |
| front rack | none / low-rider cargo rack | no | yes | rack_enabled, rack_style | rack is optional category-visible equipment in cargo samples |
| headset/head tube | round/tapered/aero head tube | no | yes | head_tube_style | headset and head-angle treatment differ |
| brake/control hardware | none / hood-like brake blocks/levers | no | yes | brake_lever_enabled, brake_lever_style | only present in subset; optional but qualitative |

## 组合逻辑（Composition Logic）
1. Build fixed `head_tube` with headset cups and frame stubs.
2. Build steering child: rigid fork or suspension crown; normalize steering axis to world Z in template output.
3. If suspension is enabled, attach left/right lower legs as prismatic children of crown/upper sleeves and keep travel synchronized by equal range.
4. Attach stem according to `stem_style`: fixed threadless/integrated, prismatic quill height, or revolute stem angle when selected.
5. Attach handlebar to stem; choose fixed, limited roll, or continuous/aero angle joint according to `bar_angle_adjust`.
6. Optional rack and brake hardware are fixed children of fork/handlebar and must not create unrelated motion.

## 已有模板写法参考
revolute_hinge / prismatic_slide / telescoping_tube / guide_shoe / handle_grip

## 约束
- Main steering axis must be vertical in template world coordinates and pass through head tube/steerer center.
- Fork blades/dropouts must be symmetric around the steering plane.
- Stem must remain clamped around the steerer or inserted into it; quill height must retain insertion.
- Handlebar center clamp must sit inside/against the stem clamp.
- Suspension lower legs must remain coaxial with upper sleeves/stanchions and retain overlap at full extension.
- Rack, brake levers, grips and faceplate bolts must be attached to fork/stem/handlebar.

## Validator
| 检查项 | 标准 |
|---|---|
| steering joint | at least one steering revolute/continuous unless explicit aero fixed-steerer variant with handlebar rotation |
| axis check | steering axis near `(0, 0, 1)`; suspension axes parallel to fork leg axes |
| fork symmetry | left/right blade or lower-leg pair mirrored within tolerance |
| suspension consistency | if enabled, exactly two prismatic lower-leg joints with equal travel |
| stem attachment | stem surrounds/inserts into steerer and is connected |
| handlebar attachment | handlebar clamp section overlaps stem clamp |
| optional rack | if enabled, rack fixed to fork and not floating |
| part diversity | `fork_style`, `handlebar_style`, `stem_style`, `suspension_enabled` exist |
| identity | recognizable bicycle fork plus handlebar cockpit |

## Reject cases
- No fork blades or no handlebar.
- Steering axis not aligned with head tube.
- Suspension lower legs slide in different directions or detach.
- Handlebar floats in front of stem.
- Stem is missing clamp/insertion geometry.
- Drop/riser/swept/aero bars reduced to the same straight cylinder despite selected style.
- Rack or brake hardware appears without attachment.

## 审核记录
| 项 | 结论 |
|---|---|
| reviewer status | pending |
| reviewer notes | SPEC_ONLY_DRAFT; waiting for human review |
