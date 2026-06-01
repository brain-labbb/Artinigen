# Turnstile Gates Spec

## 元信息
| 项 | 值 |
|---|---|
| slug | `turnstile_gates` |
| template path | `agent/templates/turnstile_gates.py` |
| test path | `tests/agent/test_turnstile_gates_template.py` |
| stage | `SPEC_ONLY_DRAFT` |
| status | `pending` |
| __modular__ | `True` |
| pattern | `mixed` |

## 5 星样本阅读摘要
| 项 | 值 |
|---|---|
| five_star_total | 45 |
| read_count | 45 |
| read_scope | all 5-star samples in this category; each record's `record.json`, active `revision.json`, `prompt.txt`, and `model.py` were scanned |
| samples_adopted_as_module_sources | 9 |
| samples_read_but_not_adopted | 36 |
| source_index_policy | adopted sources focus on the requested three-arm continuous turnstile family; one flap-gate sample was read but not adopted because it crosses the target boundary |

- adopted as module sources: `rec_turnstile_gates_0002`, `rec_turnstile_gates_035abd599f5c4979a5695cc7afca544f`, `rec_turnstile_gates_1126e053b2af476cbb85ee99dfc03430`, `rec_turnstile_gates_263530aa5ac54fec861233a7d86aa8c4`, `rec_turnstile_gates_76346937a9f345e2b518432844044a83`, `rec_turnstile_gates_7b8754ba455e44da91b04ad418caad73`, `rec_turnstile_gates_902e394e23c9438488a401153b69fc58`, `rec_turnstile_gates_fc56b55c52b04c4dab2e4f8071f2ff6c`, `rec_turnstile_gates_54b33ad76c7348f0af88a0f63b8d5dd4`.
- read but not adopted: `rec_turnstile_gates_0003`, `rec_turnstile_gates_01e2b031af004cd08d9a49bae41c68d7`, `rec_turnstile_gates_09401e46307b448ab3ae744aa09b7118`, `rec_turnstile_gates_1061f54cc4b24ca2a01d5eee227376d6`, `rec_turnstile_gates_10afa97736ab476db5a20db1354fd82f`, `rec_turnstile_gates_1acc26d66dde4c54956a759a0ed17b4a`, `rec_turnstile_gates_1f5c02cbba894e4b8131626056e68695`, `rec_turnstile_gates_2b0e7d2215fc4f219a239b8f8750cc39`, `rec_turnstile_gates_2d3832741c194383b9f5ed76dd039add`, `rec_turnstile_gates_32c96252aa6946dd8fe4a0c944df1a70`, `rec_turnstile_gates_3f627cbeef9f4a1f92512e83c795a368`, `rec_turnstile_gates_3fda89345ab849f59252666ea905b17f`, `rec_turnstile_gates_44e43b9ad72f46edbe32b5aace9079b8`, `rec_turnstile_gates_47c45a6adb6d42d8b377182a7a191b1d`, `rec_turnstile_gates_49f4876911a64d60b1aed31462254d15`, `rec_turnstile_gates_4bcc89a110fa4852a3e8d8e12af6deac`, `rec_turnstile_gates_584e96536b8b455388aa07695a46d679`, `rec_turnstile_gates_614a74b613744d76b7acfa1f81db479d`, `rec_turnstile_gates_65eae41165ac4f3f85b95f530c421cd1`, `rec_turnstile_gates_749b84d34b8c49f3b80ab1e3ad969759`, `rec_turnstile_gates_78ab9692c3ca41dc93e4f3846a8f6460`, `rec_turnstile_gates_79d95676d3d041f8ae06873b4b74b64a`, `rec_turnstile_gates_7fa8afe3190a4e27af2d73bfbce16dec`, `rec_turnstile_gates_891da42cf7654b2cb31b0ab6a1840dc7`, `rec_turnstile_gates_8a6bb85c9d4e4734a38b139a2f006c84`, `rec_turnstile_gates_8eaceeb4c6df41858cafad676d36acd9`, `rec_turnstile_gates_aa782b236e144e61871fda790d4f2275`, `rec_turnstile_gates_b91e139d71c74551b39106d2bfd51e88`, `rec_turnstile_gates_bfc6ae04f466430c92cacacf2f5be3e7`, `rec_turnstile_gates_c0b3c5b88fbd45f8b7c5ef363aa6e069`, `rec_turnstile_gates_c7cd7175280c4721ba55689aa3c79cc3`, `rec_turnstile_gates_c9e6d3f834ed41ac95e83586298a6107`, `rec_turnstile_gates_cc017302abec41c38a35c3b5ee49c3c2`, `rec_turnstile_gates_e615c706540b431592c7295a69ffa83e`, `rec_turnstile_gates_f28bc11db82a404295d60a88bd7056c4`, `rec_turnstile_gates_fee20e79da5e43c1a601f2144a31b70d`; reason: redundant three-arm turnstile variants, or in `rec_turnstile_gates_e615...` a swing-flap gate that conflicts with the requested three-arm continuous target.

## 核心身份

Turnstile gates here are three-arm mechanical turnstiles: a fixed frame/post/cabinet/bearing support carries a rotor hub with three radial arms, and the hub rotates continuously around a vertical center axis. Optional service panels, inspection hatches, lockout pawls, guard rings, bearing modules, and support heads may be present. The default seed domain excludes two-flap swing gates even if a record exists in the broad category.

边界：
- 不包括 security flap gates with two swing leaves as default template topology.
- 不混入 revolving doors: turnstile has arms/bars, not full-height door wings in a drum.

## 采用源码索引（Adopted Source Index）
| source_id | sample_id | model.py 来源 | 采纳用途 |
|---|---|---|---|
| S1 | `rec_turnstile_gates_035abd599f5c4979a5695cc7afca544f` | `data/records/rec_turnstile_gates_035abd599f5c4979a5695cc7afca544f/revisions/rev_000001/model.py:L30-L144` | canonical frame, guard ring, three-arm rotor, continuous spin |
| S2 | `rec_turnstile_gates_0002` | `data/records/rec_turnstile_gates_0002/revisions/rev_000001/model.py:L92-L536` | rugged base frame, rotor assembly, service panel, inspection hatch |
| S3 | `rec_turnstile_gates_1126e053b2af476cbb85ee99dfc03430` | `data/records/rec_turnstile_gates_1126e053b2af476cbb85ee99dfc03430/revisions/rev_000001/model.py:L31-L202` | compact frame and fold/stow-friendly arm hinge pattern |
| S4 | `rec_turnstile_gates_263530aa5ac54fec861233a7d86aa8c4` | `data/records/rec_turnstile_gates_263530aa5ac54fec861233a7d86aa8c4/revisions/rev_000001/model.py:L47-L384` | field-service base, bearing core, wear rings, rotor |
| S5 | `rec_turnstile_gates_76346937a9f345e2b518432844044a83` | `data/records/rec_turnstile_gates_76346937a9f345e2b518432844044a83/revisions/rev_000001/model.py:L30-L249` | split base/bearing/frame/head modules |
| S6 | `rec_turnstile_gates_7b8754ba455e44da91b04ad418caad73` | `data/records/rec_turnstile_gates_7b8754ba455e44da91b04ad418caad73/revisions/rev_000001/model.py:L68-L409` | industrial guard and lockout pawl |
| S7 | `rec_turnstile_gates_902e394e23c9438488a401153b69fc58` | `data/records/rec_turnstile_gates_902e394e23c9438488a401153b69fc58/revisions/rev_000001/model.py:L94-L459` | detailed pedestal and rotor |
| S8 | `rec_turnstile_gates_fc56b55c52b04c4dab2e4f8071f2ff6c` | `data/records/rec_turnstile_gates_fc56b55c52b04c4dab2e4f8071f2ff6c/revisions/rev_000001/model.py:L42-L240` | pedestal -> bearing_core -> rotor chain |
| S9 | `rec_turnstile_gates_54b33ad76c7348f0af88a0f63b8d5dd4` | `data/records/rec_turnstile_gates_54b33ad76c7348f0af88a0f63b8d5dd4/revisions/rev_000001/model.py:L29-L158` | paired side supports around rotating stage |

## 槽位 + 候选模块表

### Slot A：fixed_support
| module_name | 5_star_source | model.py:Lx-Ly | seed=0 anchor | 结构特征 |
|---|---|---|---|---|
| `guard_ring_frame` | `rec_turnstile_gates_035abd599f5c4979a5695cc7afca544f` | L30-L83 | **yes** | central column, bearing housing, fixed guard hoop |
| `rugged_service_frame` | `rec_turnstile_gates_0002` | L92-L292 | | base frame with service panel/hatch locations |
| `split_bearing_frame` | `rec_turnstile_gates_76346937a9f345e2b518432844044a83` | L30-L164 | | base, bearing_module, fixed_frame, head modules |
| `paired_side_supports` | `rec_turnstile_gates_54b33ad76c7348f0af88a0f63b8d5dd4` | L29-L101 | | paired side supports framing rotor |

### Slot B：rotor_arms
| module_name | 5_star_source | model.py:Lx-Ly | seed=0 anchor | 结构特征 |
|---|---|---|---|---|
| `classic_three_arm_rotor` | `rec_turnstile_gates_035abd599f5c4979a5695cc7afca544f` | L84-L144 | **yes** | hub shell/capstan with three fixed radial arms |
| `rugged_rotor_assembly` | `rec_turnstile_gates_0002` | L293-L508 | | heavier rotor and continuous main_rotation |
| `folding_arm_rotor` | `rec_turnstile_gates_1126e053b2af476cbb85ee99dfc03430` | L96-L202 | | compact rotor with per-arm REVOLUTE fold hint |
| `bearing_core_rotor` | `rec_turnstile_gates_fc56b55c52b04c4dab2e4f8071f2ff6c` | L42-L240 | | rotor carried by explicit bearing_core |

### Slot C：guards_service
| module_name | 5_star_source | model.py:Lx-Ly | seed=0 anchor | 结构特征 |
|---|---|---|---|---|
| `guard_ring_only` | `rec_turnstile_gates_035abd599f5c4979a5695cc7afca544f` | L30-L83 | **yes** | fixed guard ring around arm sweep |
| `service_panel_and_hatch` | `rec_turnstile_gates_0002` | L437-L536 | | two REVOLUTE service panels on fixed frame |
| `lockout_pawl` | `rec_turnstile_gates_7b8754ba455e44da91b04ad418caad73` | L364-L409 | | REVOLUTE pawl engaging rotor |
| `wear_ring_stack` | `rec_turnstile_gates_263530aa5ac54fec861233a7d86aa8c4` | L197-L384 | | bearing core with fixed wear rings and rotor |
| `none` | `rec_turnstile_gates_902e394e23c9438488a401153b69fc58` | L94-L459 | | detailed pedestal/rotor without extra service child |

## 槽位图（slot graph）

pattern: `mixed`

```text
[Slot A fixed_support]
  -- rotor_spin CONTINUOUS, axis Z -->
[Slot B rotor_arms]

[Slot A fixed_support] -- optional REVOLUTE/FIXED --> [Slot C guards_service]
[Slot B rotor_arms] -- optional per-arm REVOLUTE --> foldable arm subparts
```

## 部件（Parts）
| part | slot | visual_count | 描述 | 来源 |
|---|---|---:|---|---|
| `frame` / `base_frame` / `pedestal` / `bearing_core` | A | ~6-30 | static support, guard ring, bearing housing | S1-S9 |
| `rotor` / `rotor_assembly` / `arm_hub` | B | ~3-14 | rotating hub with three arms as visuals or foldable children | S1-S8 |
| `service_panel` / `inspection_hatch` / `lockout_pawl` / `wear_ring` | C | ~1-6 | optional service or safety hardware | S2/S4/S6 |

## 关节（Joints）
| 关节 | 类型 | parent_slot.part | child_slot.part | axis | range | 描述 |
|---|---|---|---|---|---|---|
| `rotor_spin` | CONTINUOUS | A.frame/bearing | B.rotor | `(0,0,1)` | unbounded | main three-arm rotation |
| `arm_fold_i` | REVOLUTE | B.rotor | B.arm_i | horizontal/local | bounded | optional compact/folding arms |
| `service_panel_hinge` | REVOLUTE | A.frame | C.service_panel | vertical | open/close | optional access panel |
| `inspection_hatch_hinge` | REVOLUTE | A.frame | C.inspection_hatch | horizontal | open/close | optional hatch |
| `lockout_pawl` | REVOLUTE | A.frame | C.lockout_pawl | horizontal | engage/release | optional safety pawl |

## 参数范围汇总
| 参数 | 类型 | 取值范围 | 默认 | 派生关系 | 来源 |
|---|---|---|---|---|---|
| `support_style` | enum | `guard_ring_frame` / `rugged_service_frame` / `split_bearing_frame` / `paired_side_supports` | `guard_ring_frame` | Slot A | S1/S2/S5/S9 |
| `rotor_style` | enum | `classic_three_arm_rotor` / `rugged_rotor_assembly` / `folding_arm_rotor` / `bearing_core_rotor` | `classic_three_arm_rotor` | Slot B | S1-S3/S8 |
| `service_style` | enum | `guard_ring_only` / `service_panel_and_hatch` / `lockout_pawl` / `wear_ring_stack` / `none` | `guard_ring_only` | Slot C | S1/S2/S4/S6 |
| `arm_count` | int | 3 only in default domain | 3 | fixed three-arm clone count; do not random-sample other counts unless reviewer approves | all adopted |
| `spin_axis` | enum | vertical Z | Z | fixed category invariant | all adopted |

## Multiplicity / Copy Logic

- `arm_count` is a fixed category invariant for this spec: `N=3`. It is not a random multiplicity parameter.
- For `classic_three_arm_rotor`, `rugged_rotor_assembly`, and `bearing_core_rotor`, the copied objects are arm visuals baked into the single Slot B rotor part. They share the one `rotor_spin` CONTINUOUS joint.
- For `folding_arm_rotor`, the copied objects may be part+joint pairs: `arm_i` plus `arm_fold_i`, still with exactly three arms.
- Placement is radial around the vertical hub at phases `0°`, `120°`, and `240°`. Each arm root must visibly intersect or socket into the hub.
- Reviewer-gated non-3 arm counts must stay out of the default seed domain because the requested category note and adopted source set target three-arm continuous turnstiles.

## 拓扑多样性审计

总组合数：`4 support × 4 rotor × 5 service = 80`。预计 `module_topology_diversity` 门控（>=5 distinct）能过：yes; split bearing, foldable arms, service panels, lockout pawl, and wear ring stack alter graph.

| slot | candidate_count | 是否 >=3 | 备注 |
|---|---:|---|---|
| fixed_support | 4 | yes | |
| rotor_arms | 4 | yes | |
| guards_service | 5 | yes | includes `none` |

## Validator（author_run_tests 必须覆盖的点）
- Rotor must have exactly three arms by default and spin continuously around vertical axis.
- Arms must be connected to hub and evenly spaced 120 degrees.
- Fixed guard/support must overlap or surround the rotor appropriately without collision in sampled spin poses.
- Service panels/lockout pawl must be anchored to fixed support.
- Flap-gate two-leaf topology is rejected from default domain.

## Reject cases（必须能识别并拒绝）
- No continuous rotor or rotor axis not vertical.
- Arm count not 3 in default seed domain.
- Arms as separate fixed children without real connection or Rule-1 justification.
- Two swing-leaf security gate instead of rotary arm turnstile.
- Rotor floating above bearing housing.

## 与相邻类别的边界
- `revolving_door`：door wings in drum, not three radial bars.
- `barrier_gate`：single boom arm, not central three-arm rotor.
- `access_control_flap_gate`：two swing leaves/cabinets, not default here.

## 审核记录
| 项 | 结论 |
|---|---|
| reviewer status | pending |
| reviewer notes | SPEC_ONLY_DRAFT；等待人工审核 |
