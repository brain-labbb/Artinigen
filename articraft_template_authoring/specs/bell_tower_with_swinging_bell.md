# Bell Tower With Swinging Bell Spec

## 元信息
| 项 | 值 |
|---|---|
| slug | `bell_tower_with_swinging_bell` |
| template path | `agent/templates/bell_tower_with_swinging_bell.py` |
| test path | `tests/agent/test_bell_tower_with_swinging_bell_template.py` |
| stage | `SPEC_ONLY_DRAFT` |
| status | `pending` |
| __modular__ | `True` |
| pattern | `mixed` |

## 5 星样本阅读摘要
| 项 | 值 |
|---|---|
| five_star_total | 38 |
| read_count | 38 |
| read_scope | all 5-star samples in this category; each record's `record.json`, active `revision.json`, `prompt.txt`, and `model.py` were scanned |
| samples_adopted_as_module_sources | 12 |
| samples_read_but_not_adopted | 26 |
| source_index_policy | adopted sources cover tower/frame families, single/multi/fixed bell motion, clapper/striker/pulley accessories, and architectural enclosure variants |

- adopted as module sources: `rec_bell_tower_with_swinging_bell_0003`, `rec_bell_tower_with_swinging_bell_0004`, `rec_bell_tower_with_swinging_bell_1fda08dfcd5e44fea0c755131bc83310`, `rec_bell_tower_with_swinging_bell_2f0ad6cf7c17417ab1291268aa663643`, `rec_bell_tower_with_swinging_bell_33d7a0f121c04430a49cfe9fdf17acc8`, `rec_bell_tower_with_swinging_bell_65f83abb46784f14a516d52ad4095a57`, `rec_bell_tower_with_swinging_bell_b33800d7c651451ab5b2ad344ebf3419`, `rec_bell_tower_with_swinging_bell_d362039f24d341dd934698320851a0c0`, `rec_bell_tower_with_swinging_bell_fb472780904e418995343e34a5c124bb`, `rec_bell_tower_with_swinging_bell_8eb18e56412449d5b41919422638347e`, `rec_bell_tower_with_swinging_bell_a219a0bb16ca404b8ebca3544f623dd7`, `rec_bell_tower_with_swinging_bell_c1789095c94d40668a1371797fcdaf70`.
- read but not adopted: `rec_bell_tower_with_swinging_bell_0007`, `rec_bell_tower_with_swinging_bell_0008`, `rec_bell_tower_with_swinging_bell_2995b9878ed34cbf886e9363bf14fa5d`, `rec_bell_tower_with_swinging_bell_34fc728624424681868c97b32bd4a5e8`, `rec_bell_tower_with_swinging_bell_3b32c147f02942baa482c3472a2339e2`, `rec_bell_tower_with_swinging_bell_45412a4b8fac40a7961e4c9ce8305ef5`, `rec_bell_tower_with_swinging_bell_53eb980281484b5c90f51824d63843ee`, `rec_bell_tower_with_swinging_bell_5d0d7016be2d436784ba53e98cb93f56`, `rec_bell_tower_with_swinging_bell_5e38a2e76c2842839d6a91f90159978a`, `rec_bell_tower_with_swinging_bell_6735fc90733a44b3b0e6fabf5feb1732`, `rec_bell_tower_with_swinging_bell_6d7fce3f3e4343a9af9fd95002bd4e35`, `rec_bell_tower_with_swinging_bell_753c4c2b2de14b0882d1ad9070e85061`, `rec_bell_tower_with_swinging_bell_80aac230bfe74f47bf1eecb678386cdc`, `rec_bell_tower_with_swinging_bell_950a28f660cf4215a4002cd54b5a291f`, `rec_bell_tower_with_swinging_bell_982cf580e65141d381d0e46d647318c9`, `rec_bell_tower_with_swinging_bell_b57b3e50c3774a6eac32ff84c44f0d60`, `rec_bell_tower_with_swinging_bell_bef40ee88fa141e7b7a313c354a68b48`, `rec_bell_tower_with_swinging_bell_c2ebae809533486fba06f1158cfe13c2`, `rec_bell_tower_with_swinging_bell_cc03138d3ca24f09af486637cc12f03d`, `rec_bell_tower_with_swinging_bell_cdc1748d19064b5da5b3c958feabe628`, `rec_bell_tower_with_swinging_bell_d38d0bea180b44d79ab6b7364f82a708`, `rec_bell_tower_with_swinging_bell_daf5ee873d4a4aa7b699b3eae452b46d`, `rec_bell_tower_with_swinging_bell_db8d2b0570634f6bb661d50a0905986b`, `rec_bell_tower_with_swinging_bell_dcef06c540cf40e4b4999b17341dc30b`, `rec_bell_tower_with_swinging_bell_e58a1aded0ba4e9f83e6171cee79bbce`, `rec_bell_tower_with_swinging_bell_f77911d09b1f44b49e6af5bfb5592933`; reason: duplicate frame/bell/clapper/architectural variants represented by adopted sources.

## 核心身份

Bell tower with swinging bell is an architectural or freestanding support that carries one or more bells on horizontal pivots. The core is a tower/frame/cupola/pavilion with a bell/yoke assembly that swings on a REVOLUTE joint about a horizontal axis. Optional secondary motion includes clapper swing, rope-guide pulley, or striker log. Some sources include fixed bell with moving clapper; that is a reviewed variation, not the seed-0 default.

边界：
- 不包括 purely decorative bell with no swing/clapper articulation.
- 不混入 clock tower; clock faces are not defining, swinging bell is.

## 采用源码索引（Adopted Source Index）
| source_id | sample_id | model.py 来源 | 采纳用途 |
|---|---|---|---|
| S1 | `rec_bell_tower_with_swinging_bell_0003` | `data/records/rec_bell_tower_with_swinging_bell_0003/revisions/rev_000001/model.py:L162-L412` | four-post welded steel frame and single swinging bell |
| S2 | `rec_bell_tower_with_swinging_bell_0004` | `data/records/rec_bell_tower_with_swinging_bell_0004/revisions/rev_000001/model.py:L201-L422` | octagonal cupola, roof plate, bell and fixed clapper |
| S3 | `rec_bell_tower_with_swinging_bell_1fda08dfcd5e44fea0c755131bc83310` | `data/records/rec_bell_tower_with_swinging_bell_1fda08dfcd5e44fea0c755131bc83310/revisions/rev_000001/model.py:L87-L268` | garden post, swinging bell, swinging clapper |
| S4 | `rec_bell_tower_with_swinging_bell_2f0ad6cf7c17417ab1291268aa663643` | `data/records/rec_bell_tower_with_swinging_bell_2f0ad6cf7c17417ab1291268aa663643/revisions/rev_000001/model.py:L111-L283` | raked timber frame, bell, clapper |
| S5 | `rec_bell_tower_with_swinging_bell_33d7a0f121c04430a49cfe9fdf17acc8` | `data/records/rec_bell_tower_with_swinging_bell_33d7a0f121c04430a49cfe9fdf17acc8/revisions/rev_000001/model.py:L77-L291` | carillon multi-bell tower |
| S6 | `rec_bell_tower_with_swinging_bell_65f83abb46784f14a516d52ad4095a57` | `data/records/rec_bell_tower_with_swinging_bell_65f83abb46784f14a516d52ad4095a57/revisions/rev_000001/model.py:L112-L333` | masonry tower and base guide pulley |
| S7 | `rec_bell_tower_with_swinging_bell_b33800d7c651451ab5b2ad344ebf3419` | `data/records/rec_bell_tower_with_swinging_bell_b33800d7c651451ab5b2ad344ebf3419/revisions/rev_000001/model.py:L43-L279` | fixed bell body with moving clapper only |
| S8 | `rec_bell_tower_with_swinging_bell_d362039f24d341dd934698320851a0c0` | `data/records/rec_bell_tower_with_swinging_bell_d362039f24d341dd934698320851a0c0/revisions/rev_000001/model.py:L66-L269` | Japanese frame, bell, swinging striker log |
| S9 | `rec_bell_tower_with_swinging_bell_fb472780904e418995343e34a5c124bb` | `data/records/rec_bell_tower_with_swinging_bell_fb472780904e418995343e34a5c124bb/revisions/rev_000001/model.py:L99-L356` | temple pavilion, bell, striker |
| S10 | `rec_bell_tower_with_swinging_bell_8eb18e56412449d5b41919422638347e` | `data/records/rec_bell_tower_with_swinging_bell_8eb18e56412449d5b41919422638347e/revisions/rev_000001/model.py:L115-L505` | parish stone tower, belfry frame, bell |
| S11 | `rec_bell_tower_with_swinging_bell_a219a0bb16ca404b8ebca3544f623dd7` | `data/records/rec_bell_tower_with_swinging_bell_a219a0bb16ca404b8ebca3544f623dd7/revisions/rev_000001/model.py:L87-L490` | Nordic stave tower, bell assembly, clapper |
| S12 | `rec_bell_tower_with_swinging_bell_c1789095c94d40668a1371797fcdaf70` | `data/records/rec_bell_tower_with_swinging_bell_c1789095c94d40668a1371797fcdaf70/revisions/rev_000001/model.py:L156-L499` | brick campanile, bell assembly, clapper |

## 槽位 + 候选模块表

### Slot A：tower_frame
| module_name | 5_star_source | model.py:Lx-Ly | seed=0 anchor | 结构特征 |
|---|---|---|---|---|
| `steel_four_post_frame` | `rec_bell_tower_with_swinging_bell_0003` | L162-L347 | **yes** | welded four-post frame with X-bracing and top beam |
| `octagonal_cupola` | `rec_bell_tower_with_swinging_bell_0004` | L201-L327 | | roof plate and louvered cupola enclosure |
| `garden_crossarm_post` | `rec_bell_tower_with_swinging_bell_1fda08dfcd5e44fea0c755131bc83310` | L87-L160 | | slim post with horizontal cross-arm |
| `masonry_belfry_tower` | `rec_bell_tower_with_swinging_bell_8eb18e56412449d5b41919422638347e` | L115-L491 | | stone tower plus separate belfry frame |
| `temple_pavilion_frame` | `rec_bell_tower_with_swinging_bell_fb472780904e418995343e34a5c124bb` | L99-L242 | | open timber pavilion support |

### Slot B：bell_motion
| module_name | 5_star_source | model.py:Lx-Ly | seed=0 anchor | 结构特征 |
|---|---|---|---|---|
| `single_swinging_bell` | `rec_bell_tower_with_swinging_bell_0003` | L348-L412 | **yes** | bell assembly REVOLUTE to frame |
| `bell_with_clapper_chain` | `rec_bell_tower_with_swinging_bell_1fda08dfcd5e44fea0c755131bc83310` | L161-L268 | | bell swings, clapper also REVOLUTE inside bell |
| `multi_bell_carillon` | `rec_bell_tower_with_swinging_bell_33d7a0f121c04430a49cfe9fdf17acc8` | L77-L291 | | multiple independent bells across belfry |
| `fixed_bell_moving_clapper` | `rec_bell_tower_with_swinging_bell_b33800d7c651451ab5b2ad344ebf3419` | L43-L279 | | yoke/bell fixed, only clapper swings |

### Slot C：secondary_actuator
| module_name | 5_star_source | model.py:Lx-Ly | seed=0 anchor | 结构特征 |
|---|---|---|---|---|
| `none` | `rec_bell_tower_with_swinging_bell_0003` | L348-L412 | **yes** | bell swing only |
| `internal_clapper` | `rec_bell_tower_with_swinging_bell_2f0ad6cf7c17417ab1291268aa663643` | L165-L283 | | clapper suspended inside bell on second revolute |
| `rope_guide_pulley` | `rec_bell_tower_with_swinging_bell_65f83abb46784f14a516d52ad4095a57` | L309-L333 | | base-level continuous guide wheel |
| `swinging_striker_log` | `rec_bell_tower_with_swinging_bell_d362039f24d341dd934698320851a0c0` | L211-L269 | | external striker log swinging from frame |

### Slot D：architectural_shell
| module_name | 5_star_source | model.py:Lx-Ly | seed=0 anchor | 结构特征 |
|---|---|---|---|---|
| `open_frame` | `rec_bell_tower_with_swinging_bell_0003` | L162-L347 | **yes** | exposed tower frame, no roof shell |
| `cupola_roof` | `rec_bell_tower_with_swinging_bell_0004` | L201-L401 | | octagonal roof/cupola shell fixed to roof plate |
| `stave_or_campanile_roof` | `rec_bell_tower_with_swinging_bell_a219a0bb16ca404b8ebca3544f623dd7` | L87-L333 | | pitched/wooden tower shell |
| `brick_campanile` | `rec_bell_tower_with_swinging_bell_c1789095c94d40668a1371797fcdaf70` | L156-L326 | | masonry campanile with open belfry |

## 槽位图（slot graph）

pattern: `mixed`

```text
[Slot A tower_frame + Slot D architectural_shell]
  -- bell_swing REVOLUTE, horizontal axis --> [Slot B bell_motion]
       └── optional clapper REVOLUTE --> [Slot C internal_clapper]
[Slot A tower_frame] -- optional continuous/revolute --> [Slot C pulley/striker]
```

## 部件（Parts）
| part | slot | visual_count | 描述 | 来源 |
|---|---|---:|---|---|
| `tower` / `frame` / `cupola` / `pavilion` | A/D | ~7-25 | architectural support and belfry frame | S1-S12 |
| `bell` / `bell_assembly` / `bell_yoke` | B | ~4-17 | bronze/iron bell, headstock/yoke | S1-S5/S11/S12 |
| `clapper` / `pulley` / `striker` | C | ~1-7 | secondary moving sound/rope element | S3/S6-S9 |

## 关节（Joints）
| 关节 | 类型 | parent_slot.part | child_slot.part | axis | range | 描述 |
|---|---|---|---|---|---|---|
| `bell_swing` | REVOLUTE | A.frame/tower | B.bell | horizontal `(1,0,0)` or `(0,1,0)` | bounded swing | main bell motion |
| `bell_to_clapper` | REVOLUTE / FIXED | B.bell | C.clapper | horizontal | bounded or fixed | internal clapper |
| `pulley_axle` | CONTINUOUS | A.tower | C.pulley | horizontal | unbounded | rope guide wheel |
| `striker_swing` | REVOLUTE | A.frame | C.striker | horizontal | bounded | external temple striker |
| `tower_to_frame` | FIXED | A.tower | A.belfry_frame | n/a | fixed | optional structural sub-frame |

## 参数范围汇总
| 参数 | 类型 | 取值范围 | 默认 | 派生关系 | 来源 |
|---|---|---|---|---|---|
| `tower_style` | enum | `steel_four_post_frame` / `octagonal_cupola` / `garden_crossarm_post` / `masonry_belfry_tower` / `temple_pavilion_frame` | `steel_four_post_frame` | Slot A | S1-S3/S9/S10 |
| `bell_motion_style` | enum | `single_swinging_bell` / `bell_with_clapper_chain` / `multi_bell_carillon` / `fixed_bell_moving_clapper` | `single_swinging_bell` | Slot B | S1/S3/S5/S7 |
| `secondary_actuator` | enum | `none` / `internal_clapper` / `rope_guide_pulley` / `swinging_striker_log` | `none` | Slot C | S4/S6/S8 |
| `architectural_shell` | enum | `open_frame` / `cupola_roof` / `stave_or_campanile_roof` / `brick_campanile` | `open_frame` | Slot D | S1/S2/S11/S12 |
| `bell_count` | int | `1-5` | 1 | multi_bell_carillon uses repeated independent bells | S5 |

## Multiplicity / Copy Logic

- `bell_count` applies only when `bell_motion_style=multi_bell_carillon`. All other bell-motion modules force `N=1`.
- The copied object is an independent bell/yoke assembly. Each copied bell gets its own part and its own horizontal REVOLUTE joint, named `bell_i` and `bell_swing_i`.
- Placement is side-by-side along the belfry beam or crossbar, with visible bearing ears/brackets for every copied pivot. Spacing must keep bells from intersecting in sampled swing poses.
- Optional clappers may be copied per bell only when the selected secondary-actuator/module source supports clapper chains; otherwise the multi-bell branch should keep bells as independent swinging bells without inventing unsupported extra clappers.
- `fixed_bell_moving_clapper` is a reviewed variation and does not use `bell_count > 1` in the default domain.

## 拓扑多样性审计

总组合数：`5 tower × 4 bell_motion × 4 secondary × 4 shell = 320`。预计 `module_topology_diversity` 门控（>=5 distinct）能过：yes; single vs clapper chain vs multi-bell vs fixed-bell changes joint graph and part multiplicity.

| slot | candidate_count | 是否 >=3 | 备注 |
|---|---:|---|---|
| tower_frame | 5 | yes | |
| bell_motion | 4 | yes | |
| secondary_actuator | 4 | yes | includes `none` |
| architectural_shell | 4 | yes | |

## Validator（author_run_tests 必须覆盖的点）
- Must include visible tower/frame/cupola/pavilion support.
- Main bell or clapper must articulate around horizontal axis.
- Bell/yoke pivots must be seated on visible beam/bracket ears.
- Multi-bell variant must place bells side-by-side with separate pivots.
- Clapper/striker/pulley, if present, must be mounted to bell/frame with clear support.

## Reject cases（必须能识别并拒绝）
- No moving bell/clapper/striker at all.
- Bell floating under roof or pivot outside visible supports.
- Bell swing axis vertical.
- Clock-tower facade without bell identity.
- Decorative louvers/braces as floating fixed parts.

## 与相邻类别的边界
- `clock_tower`：clock faces/gears are not enough; this category centers on bell swing.
- `doorbell` / `desk_bell`：small handheld/table bell lacks tower/frame.
- `turnstile_gates`：rotating barrier, not hanging bell.

## 审核记录
| 项 | 结论 |
|---|---|
| reviewer status | pending |
| reviewer notes | SPEC_ONLY_DRAFT；等待人工审核 |
