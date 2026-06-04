# Template Authoring Agent Protocol

This document is the **authoritative iteration loop** for an external agent
(claude-code, codex, or any tool-using agent) authoring or improving a
procedural template under `agent/templates/<slug>.py`.

It replaces the manual ad-hoc loop in
[`articraft_template_authoring/agent_workflow.md`](articraft_template_authoring/agent_workflow.md)
section 4.6 with a CLI-structured one. The spec workflow (sections 2 and 3 of
`agent_workflow.md`) is unchanged; this doc only governs **TEMPLATE_AFTER_REVIEW**.

**Before writing the first line of code, read [`TEMPLATE_DESIGN_RULES.md`](TEMPLATE_DESIGN_RULES.md).**
For new Articraft category templates, also read
[`MODULAR_TEMPLATE_AUTHORING.md`](MODULAR_TEMPLATE_AUTHORING.md). New category
templates are modular by default: they set `__modular__ = True`, use per-module
5-star sources, and pass `module_topology_diversity`.

The single source of truth for whether a template is done is:

```bash
uv run articraft template sweep-pipeline <slug>
```

You may not declare a template complete on the strength of `pytest`,
`scripts/check_template_qc.py`, or eyeballing previews alone. The pipeline
runs incremental full sweeps (`0`, `0-4`, `0-19`, `0-49`) and stops at the
first failing stage with a repair summary. Each seed runs the same full
compile pipeline records go through. Specifically, the
compiler-owned baseline now runs:

- `check_model_valid` / `check_single_root_part` / `check_mesh_assets_ready`
  (model validity)
- `fail_if_isolated_parts` (geometric connectivity)
- `fail_if_parts_overlap_in_current_pose` (closed-pose overlap)
- `fail_if_articulation_origin_far_from_geometry(tol=0.015)` (joint origin
  not in air)
- `fail_if_joint_mating_has_gap` (every joint with a declared
  `MatingContract` has its parent/child mating faces within `contact_tol` in
  world coordinates — catches the dj_knob "decoration floats above panel"
  pattern Rule 2 forbids)

…plus the modular coverage gate listed in §3.

---

## 1. Required loop

For each iteration of authoring:

1. Make your edit to `agent/templates/<slug>.py` (and the corresponding test
   file under `tests/agent/test_<slug>_template.py` when appropriate).
2. Run:
   ```bash
   uv run articraft template sweep-pipeline <slug>
   ```
3. Parse the JSON. Decide your next action from the structured signals
   (`repair_summary`, stage reports, `failure_clusters`, `coverage_gates`,
   `escalation`) per the rules below.
4. Repeat. Do not declare done until `verdict=pass`.

The pipeline persists per-slug state under
`<repo_root>/.articraft/template_sweep_state/<slug>.json`. Each successive
invocation increments `streak_count` for failure clusters that survive the
edit, and updates `pass_rate_trend`. This is what lets the loop detect "I
am bouncing on the same root cause."

If the pipeline CLI is unavailable, use the manual fallback sequence below.
This fallback intentionally repeats cumulative seeds; the pipeline itself only
compiles newly added seeds within one run.

```bash
uv run articraft template compile-sweep <slug> --seeds 0
uv run articraft template compile-sweep <slug> --seeds 0-4
uv run articraft template compile-sweep <slug> --seeds 0-19
uv run articraft template compile-sweep <slug> --seeds 0-49
```

---

## 2. JSON contract

```jsonc
{
  "slug": "ceiling_fan",
  "stem": "ceiling_fan",
  "total_seeds": 50,
  "passed_seeds": [0, 2, 3, ...],
  "failed_seeds": [
    {
      "seed": 1,
      "config": { "fan_layout": "rod_canopy", "blade_count": 4, ... },
      "failure_type": "fail_if_articulation_origin_far_from_geometry(tol=0.015)",
      "failure_type_normalized": "fail_if_articulation_origin_far_from_geometry",
      "failure_details": "joint='mount_to_motor' dist_parent=0.075 ...",
      "elapsed_s": 0.10
    }
  ],
  "failure_clusters": [
    {
      "cluster_id": 1,
      "cluster_signature": "2774f2e29b65",
      "shared_failure_type": "fail_if_articulation_origin_far_from_geometry",
      "shared_config_axes": { "hub_style": "spherical" },
      "seeds": [1, 7, 14, 23, 41],
      "example_failure_details": "joint='mount_to_motor' dist_parent=0.075 ...",
      "diagnosis_hint": "Joint origin (in parent frame) falls outside ...",
      "is_singleton": false,
      "streak_count": 2
    }
  ],
  "coverage_gates": {
    "module_topology_diversity":  { "status": "pass" | "fail" | "skipped", "details": {...}, "reason": "..." }
  },
  "escalation": {
    "required": false,
    "reasons": [],
    "cluster_streaks": { "2774f2e29b65": 2 },
    "pass_rate_trend": [0.0, 0.4, 0.6]
  },
  "line_count": 1247,
  "pass_rate": 0.94,
  "pass_threshold": 0.95,
  "verdict": "pass" | "fail",
  "elapsed_s": 18.4
}
```

`verdict=pass` requires **all** of:
- `pass_rate >= pass_threshold` (default 0.95 — 50 seeds, ≤2 failures allowed)
- every entry in `coverage_gates` has `status` of `pass` or `skipped`

If `verdict=fail`, the loop is not done.

---

## 3. Decision rules

### 3.1 Read `failure_clusters` before reading individual `failed_seeds`

Clusters are pre-aggregated by normalized failure_type and shared config
axes. The biggest cluster is the most likely root cause. Working at the
cluster level prevents the "fix seed 7, break seed 0" trap.

Fix order:
1. Largest cluster first (sorted by descending size).
2. If multiple clusters have the same failure_type but different
   `shared_config_axes`, treat the one with the more distinctive axis
   pattern as the structural bug; the others may be downstream noise.
3. Use `diagnosis_hint` as the first hypothesis; check
   `example_failure_details` to ground it in the actual joint/part names.

**Do not** make per-seed surgical edits when a cluster spans more than one seed.

### 3.2 Coverage gates

| Gate | What it checks | What to do on `fail` |
|---|---|---|
| `module_topology_diversity` | modular templates expose at least the required number of distinct passing `slot_choices_for_seed` tuples | Fix missing module factories, narrow invalid seed domains, or revise the modular spec if the sample pool cannot support enough distinct topology. |

`status: "skipped"` is fine during early pipeline stages; the topology gate is
enforced once the cumulative sweep reaches 20 seeds. Skipped does not block
`verdict=pass`.

### 3.3 Escalation

When `escalation.required = true`, **stop patching code** and instead:

| Reason | Required next action |
|---|---|
| `cluster signature X unchanged for >= 3 sweeps` | The same structural failure has survived 3 attempts. Either **narrow `config_from_seed`** to exclude the failing axis (e.g. drop `hub_style="spherical"` from the sample domain) OR **split the slug** into multiple templates with disjoint motion spines. Both are recorded in your handoff notes. |
| `pass_rate has not improved over the last 3 sweeps` | Your local edits are not converging. Re-read the spec; consider that the spec may need to be tightened or split. Do NOT keep trying random tweaks. |

After escalating, **do not** keep iterating in the same slug. Write a short
handoff note (in the PR description or chat reply) explaining what was tried
and what the recommended narrow/split is, and stop.

---

## 4. Stop conditions

Declare the template done iff **all** of the following hold on the most
recent sweep:

- `verdict == "pass"`
- `pass_rate >= 0.95`
- `coverage_gates.module_topology_diversity.status == "pass"` on the 0-49 stage
- You have visually inspected previews for at least seeds `0, 1, 2` using
  `uv run python scripts/render_template_previews.py --slugs <slug> --seeds 0-2`
  and confirmed they look like the category and have no obvious
  identity/proportion/closed-pose problems.

The first three are mechanical and surfaced in the JSON. The preview check still
requires your judgment because no compiler check answers "does this look
like a <category>." Always do it.

---

## 5. What you may NOT do

- **Do not** declare done because `pytest tests/agent/test_<slug>_template.py`
  passes. That suite covers a different (smaller) baseline than the sweep CLI.
- **Do not** lower `--pass-threshold` to make the verdict pass. The threshold
  is policy, not a tuning knob. If 0.95 looks unachievable, escalate.
- **Do not** disable streak tracking via `--state-dir ""` to escape
  escalation. The streak signal is what catches non-converging loops.
- **Do not** widen the sweep seed range (`--seeds 0-99`) to dilute a real
  failure cluster. The cluster signature is independent of seed count.
- **Do not** edit `_BASELINE_ARTICULATION_ORIGIN_TOL` in
  `agent/compiler.py` to make geometry checks pass. The tolerance is a
  cross-template floor.

---

## 6. Relation to existing docs and CLIs

| Document / Tool | What it covers | Who is in charge |
|---|---|---|
| `articraft_template_authoring/agent_workflow.md` | **SPEC_ONLY** modular spec workflow and reviewed-spec handoff | Applies before implementation |
| `articraft_template_authoring/SPEC_TEMPLATE.md` | Required modular slot/module spec schema | Applies to new category specs |
| `MODULAR_TEMPLATE_AUTHORING.md` | Slot/module implementation contract, `__modular__`, InterfaceSpec, `module_topology_diversity` | Applies to new category templates |
| `articraft_template_authoring/MATURE_TEMPLATE_METHOD.md` | Modular maturity notes for source adaptation, interfaces, seed domain, and sweep repair | Applies during implementation |
| `articraft template sweep-pipeline <slug>` | Per-iteration ground-truth signal | **You read this every iteration** |
| `articraft template compile-sweep <slug> --seeds X` | Manual fallback / targeted diagnosis | Use only when pipeline output asks for focused follow-up |
| `articraft template batch <slug> --seeds X` | Promote template into real records | Run only after this doc's stop conditions are met |
| `articraft external check <record>` | Record-level baseline + author tests | Same baseline as sweep; use it after batch to validate a specific record |

---

## 7. Frequently asked

**Q: What if all 50 seeds fail because of one trivial bug (e.g. typo)?**
Fix the trivial bug. After the next sweep most seeds will pass and you can
work cluster-by-cluster on the remainder.

**Q: A cluster's `shared_config_axes` shows axes that aren't really the
cause (e.g. `guard_style=none` is always the failure case because it's the
default).**
That's noise from too-few sample seeds. Use the full 50; the noise filters
out. If a cluster shrinks to one or two seeds with diverse configs, treat
it as a singleton.

**Q: How long should a sweep take?**
Target is <2 min per sweep at `--max-workers 4`. If a single seed
compile is taking >30s, the template's `_build_*` has accidental O(n²) or
the QC step is bogging down — fix it before iterating further.

---

## 8. End-to-end example

```bash
# 1. Edit agent/templates/cantilever_articulated_arm.py based on spec.
# 2. Run the incremental pipeline.
uv run articraft template sweep-pipeline cantilever_articulated_arm \
    --pass-threshold 0.95 \
    --max-workers 4 \
    --out reports/cantilever_arm_pipeline_1.json
# 3. Inspect:
#    - repair_summary.failed_stage
#    - repair_summary.top_failure_clusters[0]
#    - repair_summary.failing_coverage_gates
#    - repair_summary.escalation
# 4. Apply a targeted fix to the cluster's likely root cause.
# 5. Re-run the pipeline from seed 0. Watch streak_count on the cluster.
# 6. If streak hits 3, stop patching, write a handoff note recommending
#    config_from_seed narrowing or a slug split.
# 7. Otherwise, repeat until verdict=pass, then visually self-review
#    previews for seeds 0, 1, 2.
```
