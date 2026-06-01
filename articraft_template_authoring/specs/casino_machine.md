# Casino Machine Spec

## 元信息
| 项 | 值 |
|---|---|
| slug | `casino_machine` |
| template path | `agent/templates/casino_machine.py` |
| test path | `tests/agent/test_casino_machine_template.py` |
| stage | `SPEC_ONLY_DRAFT` |
| status | `pending` |
| __modular__ | `True` |
| pattern | `parallel_children` |

## 5 星样本阅读摘要
| 项 | 值 |
|---|---|
| five_star_total | 18 |
| read_count | 18 |
| read_scope | all 5-star samples in this category; each record's `record.json`, active `revision.json`, `prompt.txt`, and `model.py` were scanned |
| samples_adopted_as_module_sources | 11 |
| samples_read_but_not_adopted | 7 |
| source_index_policy | adopted sources cover upright, slant-top, bar-top, modern five-reel, high-top, curved-front cabinet plus reels, levers, buttons, knobs, doors, flaps, and trays |

- adopted as module sources: `rec_a-casino-slot-machine-with-a-tall-cabinet-a-fron_20260401_024859_195918_39764297`, `rec_casino_machine_cfba59645a80411f8bed2072f9a9bfcf`, `rec_casino_machine_3725c99749b74e059f1c1aa88d9f9673`, `rec_casino_machine_04dbcc128faa4a12a0cd9eda80de5f1f`, `rec_casino_machine_0dc07bf220f3445398c77007f2a4ade3`, `rec_casino_machine_4ef053f79a3b46809426c50d640c1434`, `rec_casino_machine_a49e8cdfbc5e4e7dbd3c1e3fa91e869c`, `rec_casino_machine_a5d926cbd53d4a309199969ad8856d21`, `rec_casino_machine_b7a9b3572cfb45ec8a7eb5ec3a7ed453`, `rec_casino_machine_da56e08515584864835133be685527c6`, `rec_casino_machine_e60bb68099834916986dbbf2af56a85d`.
- read but not adopted: `rec_a-casino-slot-machine-with-a-tall-cabinet-a-fron_20260401_030831_141551_df669af7`, `rec_casino_machine_4e5fed5b3e2b45be81f98f55fc6a713c`, `rec_casino_machine_8e8bf222530442a2ab6d616e811d60eb`, `rec_casino_machine_a046c86a3fe440ccb808c0ff8cf8e89d`, `rec_casino_machine_a70993399d1b41d890e8589c17466b88`, `rec_casino_machine_a9bbb5d31a3940a9811917618890f778`, `rec_casino_machine_bd2b0f12181344659d40db62cce54652`; reason: duplicate cabinet/control/door/reel structures represented by adopted sources.

## 核心身份

Casino machine is a slot/video-poker/gaming terminal cabinet with a display/reel area, control deck, payout/cash/tray area, and at least one articulated gaming or service mechanism. Common motions are parallel reel CONTINUOUS rotations behind a window, side pull lever REVOLUTE, spin/cashout button PRISMATIC, selector/volume knob CONTINUOUS, service/belly/cashbox door REVOLUTE, and payout/bill/tray flap REVOLUTE. The cabinet is the root parent for most parallel children.

边界：
- 不包括 arcade driving cabinets or vending machines; those have different interaction surfaces.
- 不混入 pure display kiosk; casino identity needs reel/display plus gambling controls/tray/acceptor semantics.

## 采用源码索引（Adopted Source Index）
| source_id | sample_id | model.py 来源 | 采纳用途 |
|---|---|---|---|
| S1 | `rec_casino_machine_cfba59645a80411f8bed2072f9a9bfcf` | `data/records/rec_casino_machine_cfba59645a80411f8bed2072f9a9bfcf/revisions/rev_000001/model.py:L86-L389` | classic upright slot, reel set, side lever, payout tray flap |
| S2 | `rec_a-casino-slot-machine-with-a-tall-cabinet-a-fron_20260401_024859_195918_39764297` | `data/records/rec_a-casino-slot-machine-with-a-tall-cabinet-a-fron_20260401_024859_195918_39764297/revisions/rev_000001/model.py:L36-L359` | tall cabinet, reel_bank, coin tray, pull handle |
| S3 | `rec_casino_machine_3725c99749b74e059f1c1aa88d9f9673` | `data/records/rec_casino_machine_3725c99749b74e059f1c1aa88d9f9673/revisions/rev_000001/model.py:L66-L151` | slant-top body, belly door, spin button, volume knob |
| S4 | `rec_casino_machine_04dbcc128faa4a12a0cd9eda80de5f1f` | `data/records/rec_casino_machine_04dbcc128faa4a12a0cd9eda80de5f1f/revisions/rev_000001/model.py:L111-L189` | bar-top video poker and tray flap/button press |
| S5 | `rec_casino_machine_0dc07bf220f3445398c77007f2a4ade3` | `data/records/rec_casino_machine_0dc07bf220f3445398c77007f2a4ade3/revisions/rev_000001/model.py:L54-L430` | modern five-reel cabinet, spin button, maintenance panel |
| S6 | `rec_casino_machine_4ef053f79a3b46809426c50d640c1434` | `data/records/rec_casino_machine_4ef053f79a3b46809426c50d640c1434/revisions/rev_000001/model.py:L35-L354` | compact bar-mounted terminal, selector knob, tray flap, service panel |
| S7 | `rec_casino_machine_a49e8cdfbc5e4e7dbd3c1e3fa91e869c` | `data/records/rec_casino_machine_a49e8cdfbc5e4e7dbd3c1e3fa91e869c/revisions/rev_000001/model.py:L37-L400` | high-top slot, reel set, service door, pull lever |
| S8 | `rec_casino_machine_a5d926cbd53d4a309199969ad8856d21` | `data/records/rec_casino_machine_a5d926cbd53d4a309199969ad8856d21/revisions/rev_000001/model.py:L174-L450` | curved-front cabinet, three reels, buttons, cashbox door |
| S9 | `rec_casino_machine_b7a9b3572cfb45ec8a7eb5ec3a7ed453` | `data/records/rec_casino_machine_b7a9b3572cfb45ec8a7eb5ec3a7ed453/revisions/rev_000001/model.py:L132-L422` | upright rectangular cabinet, three reels, handle, coin tray door |
| S10 | `rec_casino_machine_da56e08515584864835133be685527c6` | `data/records/rec_casino_machine_da56e08515584864835133be685527c6/revisions/rev_000001/model.py:L33-L283` | video-poker cabinet, bill acceptor flap, payout tray flap, cashout button |
| S11 | `rec_casino_machine_e60bb68099834916986dbbf2af56a85d` | `data/records/rec_casino_machine_e60bb68099834916986dbbf2af56a85d/revisions/rev_000001/model.py:L143-L419` | slant-top detailed cabinet, belly door, spin button, volume knob |

## 槽位 + 候选模块表

### Slot A：cabinet_body
| module_name | 5_star_source | model.py:Lx-Ly | seed=0 anchor | 结构特征 |
|---|---|---|---|---|
| `classic_upright_cabinet` | `rec_casino_machine_cfba59645a80411f8bed2072f9a9bfcf` | L86-L261 | **yes** | tall classic cabinet with reel window and payout tray area |
| `slant_top_cabinet` | `rec_casino_machine_e60bb68099834916986dbbf2af56a85d` | L143-L287 | | angled screen/button deck and belly door opening |
| `bar_top_video_poker` | `rec_casino_machine_04dbcc128faa4a12a0cd9eda80de5f1f` | L111-L142 | | shallow bar-top cabinet with tray recess |
| `modern_five_reel_cabinet` | `rec_casino_machine_0dc07bf220f3445398c77007f2a4ade3` | L54-L359 | | broad display face, shallow control deck, rear panel |
| `curved_front_cabinet` | `rec_casino_machine_a5d926cbd53d4a309199969ad8856d21` | L174-L356 | | curved/rounded front with central reel window |

### Slot B：reel_or_display_mechanism
| module_name | 5_star_source | model.py:Lx-Ly | seed=0 anchor | 结构特征 |
|---|---|---|---|---|
| `three_reel_continuous` | `rec_casino_machine_cfba59645a80411f8bed2072f9a9bfcf` | L295-L303 | **yes** | three parallel continuous reels behind window |
| `five_reel_continuous` | `rec_casino_machine_0dc07bf220f3445398c77007f2a4ade3` | L350-L358 | | five parallel reel child parts |
| `fixed_reel_bank` | `rec_a-casino-slot-machine-with-a-tall-cabinet-a-fron_20260401_024859_195918_39764297` | L187-L338 | | reel_bank as supported/fixed subassembly |
| `video_screen_buttons` | `rec_casino_machine_04dbcc128faa4a12a0cd9eda80de5f1f` | L111-L189 | | no reels; video-poker screen with button row and tray flap |

### Slot C：user_controls
| module_name | 5_star_source | model.py:Lx-Ly | seed=0 anchor | 结构特征 |
|---|---|---|---|---|
| `side_pull_lever` | `rec_casino_machine_cfba59645a80411f8bed2072f9a9bfcf` | L305-L356 | **yes** | side lever REVOLUTE on cabinet flank |
| `spin_button_press` | `rec_casino_machine_da56e08515584864835133be685527c6` | L206-L237 | | PRISMATIC cashout/spin buttons on deck |
| `selector_knob` | `rec_casino_machine_4ef053f79a3b46809426c50d640c1434` | L255-L326 | | selector knob CONTINUOUS about side/shelf shaft |
| `volume_knob` | `rec_casino_machine_e60bb68099834916986dbbf2af56a85d` | L355-L419 | | slant-top volume knob continuous and spin button |

### Slot D：access_tray_doors
| module_name | 5_star_source | model.py:Lx-Ly | seed=0 anchor | 结构特征 |
|---|---|---|---|---|
| `payout_tray_flap` | `rec_casino_machine_cfba59645a80411f8bed2072f9a9bfcf` | L358-L389 | **yes** | front payout tray flap REVOLUTE |
| `belly_service_door` | `rec_casino_machine_e60bb68099834916986dbbf2af56a85d` | L288-L393 | | vertical side-hinged belly door |
| `rear_maintenance_panel` | `rec_casino_machine_0dc07bf220f3445398c77007f2a4ade3` | L399-L430 | | rear maintenance panel REVOLUTE |
| `bill_and_tray_flaps` | `rec_casino_machine_da56e08515584864835133be685527c6` | L239-L283 | | bill acceptor flap plus payout tray flap |
| `coin_tray_door` | `rec_casino_machine_b7a9b3572cfb45ec8a7eb5ec3a7ed453` | L337-L422 | | coin tray door and handle context |

## 槽位图（slot graph）

pattern: `parallel_children`

```text
[Slot A cabinet_body]
  ├── CONTINUOUS reel_i × N --> [Slot B reel_or_display_mechanism]
  ├── REVOLUTE/PRISMATIC/CONTINUOUS --> [Slot C user_controls]
  └── REVOLUTE --> [Slot D access_tray_doors]
```

## 部件（Parts）
| part | slot | visual_count | 描述 | 来源 |
|---|---|---:|---|---|
| `cabinet` / `machine_body` / `base_cabinet` | A | ~3-32 | tall/slant/bar-top/modern/curved cabinet | S1-S11 |
| `reel` / `reel_bank` / `reel_window` / `screen` | B | ~1-8 | rotating reels or video display mechanism | S1/S2/S4/S5 |
| `side_lever` / `spin_button` / `selector_knob` / `volume_knob` | C | ~1-5 | user controls with real joints | S1/S3/S6/S10/S11 |
| `tray_flap` / `service_door` / `rear_panel` / `bill_flap` | D | ~2-5 | access/tray/cashbox panels | S1/S5/S7/S9-S11 |

## 关节（Joints）
| 关节 | 类型 | parent_slot.part | child_slot.part | axis | range | 描述 |
|---|---|---|---|---|---|---|
| `reel_i_spin` | CONTINUOUS | A.cabinet | B.reel_i | horizontal `(1,0,0)` or `(0,1,0)` | unbounded | reel drums spin behind window |
| `lever_pull` | REVOLUTE | A.cabinet | C.side_lever | transverse horizontal | bounded pull | classic side handle |
| `button_press` | PRISMATIC | A.cabinet/deck | C.button | local vertical | short travel | spin/cashout button |
| `knob_turn` | CONTINUOUS | A.cabinet/deck | C.knob | local shaft | unbounded | selector/volume knob |
| `door_or_flap_hinge` | REVOLUTE | A.cabinet | D.panel | horizontal/vertical | open/close | service, tray, bill, cashbox panels |

## 参数范围汇总
| 参数 | 类型 | 取值范围 | 默认 | 派生关系 | 来源 |
|---|---|---|---|---|---|
| `cabinet_style` | enum | `classic_upright_cabinet` / `slant_top_cabinet` / `bar_top_video_poker` / `modern_five_reel_cabinet` / `curved_front_cabinet` | `classic_upright_cabinet` | Slot A | S1/S4/S5/S8/S11 |
| `reel_display_style` | enum | `three_reel_continuous` / `five_reel_continuous` / `fixed_reel_bank` / `video_screen_buttons` | `three_reel_continuous` | Slot B | S1/S2/S4/S5 |
| `control_style` | enum | `side_pull_lever` / `spin_button_press` / `selector_knob` / `volume_knob` | `side_pull_lever` | Slot C | S1/S6/S10/S11 |
| `access_style` | enum | `payout_tray_flap` / `belly_service_door` / `rear_maintenance_panel` / `bill_and_tray_flaps` / `coin_tray_door` | `payout_tray_flap` | Slot D | S1/S5/S9-S11 |
| `reel_count` | int | `0 / 3 / 5` | 3 | derived from display style; strict slot-machine target samples 3 unless reviewer enables broad casino variants | S1/S4/S5 |

## Multiplicity / Copy Logic

- `reel_count` is derived from `reel_display_style`, not sampled independently: `three_reel_continuous -> 3`, `five_reel_continuous -> 5`, `video_screen_buttons -> 0`; `fixed_reel_bank` may show reel visuals but does not emit continuous reel joints.
- Continuous reel branches copy part+joint pairs. For `N` reels, emit `reel_i` as separate Slot B child parts and `reel_i_spin` as separate CONTINUOUS joints parented to the cabinet or reel frame.
- Placement is parallel across the display window: reels are evenly spaced left-to-right, share the same horizontal spin-axis direction, and remain behind the reel glass/window.
- Seed-0 and the requested narrow slot-machine domain use `N=3`. `N=5` and `N=0` are broader casino-machine variants and should be reviewer-gated if the template is meant to stay at "3x continuous reels".
- Reel multiplicity is independent from control/access multiplicity: lever, button, knob, door, and tray joints stay in Slot C/D and must not be cloned once per reel.

## 拓扑多样性审计

总组合数：`5 cabinet × 4 reel/display × 4 controls × 5 access = 400`。预计 `module_topology_diversity` 门控（>=5 distinct）能过：yes; reel multiplicity, lever/button/knob joint types, and door/flap variants alter graph.

| slot | candidate_count | 是否 >=3 | 备注 |
|---|---:|---|---|
| cabinet_body | 5 | yes | |
| reel_or_display_mechanism | 4 | yes | |
| user_controls | 4 | yes | |
| access_tray_doors | 5 | yes | |

## Validator（author_run_tests 必须覆盖的点）
- Must have casino cabinet identity: reel/display area, control deck, tray/acceptor/service area.
- Reel display style with reels must create `reel_count` continuous horizontal-axis reels.
- Lever/button/knob controls must be anchored to visible cabinet/deck sockets.
- Door/flap panels must sit in real recessed openings and hinge/slide along plausible axes.
- Video-poker variant may have no reels, but must keep screen, controls, and tray/access motion.

## Reject cases（必须能识别并拒绝）
- Arcade cabinet, vending machine, or kiosk with no casino controls/reel/tray semantics.
- Reels vertical-axis or not behind display window.
- Lever/button/knob floating on cabinet face without socket/deck.
- Cash/tray/service panels as painted visuals when slot requests articulated door/flap.
- All controls static when prompt/category requires articulated mechanisms.

## 与相邻类别的边界
- `arcade_machine`：driving/joystick cabinets lack slot reels, payout tray, bill/coin/lever semantics.
- `vending_machine`：dispenses goods; casino machine centers gambling controls and payout/cashbox.
- `dj_equipment` / `turntable`：audio controls/platter/tonearm, not gaming cabinet.

## 审核记录
| 项 | 结论 |
|---|---|
| reviewer status | pending |
| reviewer notes | SPEC_ONLY_DRAFT；等待人工审核 |
