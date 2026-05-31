# Modular Template Authoring

This document is the authoritative guide for adding a procedural
template under `agent/templates/<slug>.py`. A modular template defines
**slots**, each populated by one of several **module** factories per seed,
producing topology-level diversity (different part trees, joint counts,
chain depths) rather than just parameter variation.

The hard rules in [`articraft_template_authoring/DESIGN_RULES.md`](articraft_template_authoring/DESIGN_RULES.md)
apply to every template.

Read this **before** writing any module factory.

---

## Slot design — sizing slots and candidates

Before writing any module factory, decide **how many slots** the template
has and **how many candidate modules** per slot. This is the single most
impactful design call.

### How to decide slot count

1. **List the independent variation axes in the 5-star samples** — read all
   5-star records in the category and identify dimensions where samples
   genuinely differ in *structure* (part trees, joint counts/types), not
   just in dimensions or color.
   - knife: housing shape varies (barrel vs pistol) × mechanism varies
     (slider vs service-door) × blade varies (straight vs hook) = 3 axes
   - monitor_mount: base type (wall vs desk-clamp) × arm structure (1-N
     links) × head (pan+tilt vs tilt-only) = 3 axes
   - dj_equipment: chassis (controller vs turntable) × deck layout (jog
     vs platter+tonearm) × controls (faders vs pad grid) = 3 axes

2. **An axis qualifies as a slot only if it has ≥2 candidate modules**
   sourced from genuinely different 5-star samples. If only one sample
   supports that axis, it's not yet a slot — fold it into an adjacent
   slot's module variation, or skip it.

3. **Slots must be chainable** physically — adjacent slots have to share
   a mating face (serial chain like arm links) or a common parent (parallel
   children like dj's deck/controls). If two "axes" can't share a mating
   surface, they probably belong to the same slot as alternative modules,
   not separate slots.

4. **Typical slot counts and trade-offs**:

   | Slot count | Trade-off |
   |---|---|
   | 1 | No topology variation — single slot collapses to a fixed structure (use a different decomposition) |
   | 2 | Combo count = a × b; struggles to hit `module_topology_diversity` ≥ 5 unless each slot has ≥3 candidates |
   | **3** | Sweet spot — a × b × c easily exceeds the diversity floor, each module has tractable scope |
   | 4 | Each module has narrower responsibility, more inter-part mating seams, allow_overlap declarations multiply |
   | ≥5 | Code size explodes; one or more "slots" usually folds cleanly into **slot-level multiplicity** instead |

   Most templates land at 3. Simpler categories may use 2 (hammer = head
   + handle); complex categories that look like 5+ slots typically have
   axes that should be expressed as slot-level multiplicity (e.g.,
   office_chair's armrests are a multiplicity feature of the seat slot,
   not a separate slot).

### How to decide candidate count per slot

**Recommended: 3-6 candidates per slot. Degrade to 2 only if the 5-star
sample pool doesn't yield enough structurally distinct sources.**

| Candidates | Effect |
|---|---|
| 2 (last-resort fallback) | Minimum viable; combo count `2×2×2=8` works if all slots have ≥2 and the `module_topology_diversity` gate threshold (5) is barely met |
| **3-6 (target)** | Each slot's RNG genuinely samples a wide structural space; combo count `4×4×4 = 64` is comfortable |
| 7+ | Marginal returns; module factory code volume balloons; 5-star sample pool usually can't sustain that many *distinct* candidates without re-skinning the same structure |

**Each candidate must be structurally distinct, not a re-skin**:
- ✅ Two housing candidates from two different 5-star records that have
  different part counts or different joint placements
- ✅ Two blade candidates with materially different profiles (snap-off
  trapezoid vs utility hook) and different sub-feature counts
- ❌ Two "candidates" that are the same part tree with different palette
  colors → that's a palette parameter, not a module distinction
- ❌ Two candidates differing only in linear dimensions → that's a
  parameter sample, not a module

### Choosing between "more candidates", "slot-level multiplicity", and "extra slot"

When a new structural variation appears in your spec, ask:

1. Is it a **different way of doing the same functional job** at the
   same attachment point? → **add as a new candidate** in an existing
   slot (e.g., a new blade profile → new module in the `blade` slot).

2. Is it the **same part repeated N times** with regular spacing or
   pattern? → use **slot-level multiplicity** (one module per N, named
   `tri_blade`, `quad_blade`, …). The number itself becomes the
   topology variation. See the "variable-multiplicity radial" and
   "variable-multiplicity chain" patterns below.

3. Is it a **physically separate functional layer** that didn't exist in
   the original slot graph? → **add as a new slot**, but only if there
   are ≥2 candidate modules for it. Otherwise fold it as an optional
   feature of an existing module.

Rule of thumb: **prefer "more candidates" over "more slots"**. Each new
slot adds inter-module mating geometry to reason about; each new
candidate is self-contained.

---

## Reference implementations

| Template | Slot graph | Highlights |
|---|---|---|
| [`agent/templates/retractable_utility_knife.py`](agent/templates/retractable_utility_knife.py) | housing → mechanism → blade | Linear chain, 2 candidates/slot, 8 topology combos |
| [`agent/templates/monitor_mount.py`](agent/templates/monitor_mount.py) | base → arm → head | Variable arm chain (1-8 links), 32 topology combos |
| [`agent/templates/dj_equipment.py`](agent/templates/dj_equipment.py) | chassis → deck_layout → controls | Parallel children pattern (deck/controls parent directly to housing) |

Read the slug closest to your target structure before writing.

---

## Architecture

The abstraction lives in [`agent/templates/_modular.py`](agent/templates/_modular.py).
Four core dataclasses:

### `InterfaceSpec`
A face exposed by a module that can mate with another module's opposite
face. Defines:
- `part_name`, `visual_name`, `face_side` — which part / which visual / which
  axis face the assembler will reference for the MatingContract
- `anchor_local` — center of that face in the owning part's local frame
- `consumer_joint_type`, `consumer_joint_axis`, `consumer_motion_limits` —
  meaningful on `upstream` interfaces only; tells the assembler what kind
  of joint to emit when chaining to this module

### `Module` / `ModuleBuild`
A module factory emits parts + internal articulations onto a model and
returns a `ModuleBuild` descriptor listing what it emitted and the
interfaces it exposes (typically `"upstream"` and `"downstream"`).

### `SlotSpec`
One slot in the assembly graph. Owns `candidates: dict[name, factory]`
and an `anchor_choice` (the module name picked for `seed == 0`, which
should reproduce a canonical 5-star sample).

### `assemble(...)`
The driver. For each slot in order: pick a module (seed=0 → anchor, else
uniform random), run its factory, emit a chain joint between the previous
module's downstream interface and this module's upstream interface.

---

## Design contract — read carefully

### Contract 1 — Module chain wiring

For each module factory `def _build_<name>(ctx: ModuleBuildContext) -> ModuleBuild`:

- Pull resolved config from `ctx.config` (slug-specific `Resolved<Slug>Config`).
- Pull palette via `ctx.palette` (already registered as `model.material(...)`).
- Use `ctx.rng` for any per-module randomness (don't make a new `random.Random`).
- Inspect `ctx.prior_choices` (list of `(slot_name, module_name)` for upstream
  slots) when the module's geometry depends on the upstream choice — e.g.,
  when housing+mechanism share a slidable cover that gets re-anchored.
- Read `ctx.upstream_interface.part_name` when the module needs to parent
  joints directly to an upstream part (non-chain parallel pattern, see
  dj_equipment's deck/controls modules).

### Contract 2 — Upstream interface anchor

The assembler positions the joint at `parent_anchor_local` in the parent's
frame. For the **child** module's `upstream` interface, the `anchor_local`'s
**normal-axis component must be 0** — the other two components (tangential)
are free. Why: the child link's frame is placed at the joint origin; the
mating face's normal-axis position must coincide with the parent's mating
face for `fail_if_joint_mating_has_gap` to pass.

Example: if the upstream `face_side` is `negative_z`, the child's
`anchor_local` must look like `(any_x, any_y, 0.0)`. The mating face will
sit at z=0 in the child's local frame; tangential x/y of the face center
is free.

`_modular.py`'s `_emit_chain_joint` enforces this; violating it raises
ValueError at assembly time.

### Contract 3 — Visual connectivity within a part

`fail_if_part_contains_disconnected_geometry_islands` is a **FAIL-level**
baseline check (since 2026-05). Every visual on a part must overlap (AABB)
with at least one other visual on the same part, transitively forming
one connected island.

Common fix: add a "neck" or "riser" Box that bridges between two visuals
that would otherwise be geometric islands (e.g. a lofted bridge that
floats above a carrier_block, a lower_lug below a clevis pivot).

The connectivity check uses a strict 1e-6 tolerance — visuals must
actually overlap, not just touch boundaries. If two parts touch by a
boundary face, push them into each other by 1-2 mm so the check passes.

Escape hatch (use sparingly): for a part that is *genuinely* a set of
separated rigid pieces — a comb, grille, or fin stack where adding a
bridge would invent material the real object does not have — declare
`ctx.allow_disconnected_islands(part, reason="...")` in `run_<slug>_tests`.
This downgrades the strict check to a warning for that part only. Do NOT
use it to paper over an accidental seed-driven split; those should be
fixed in geometry. Prefer a real bridging connector whenever the pieces
are meant to be one solid body.

### Contract 4 — seed=0 is the anchor

`config_from_seed(0)` must return the canonical 5-star sample's
configuration (anchor module per slot + anchor's nominal dimensions).
Other seeds RNG-pick uniformly from each slot's candidates.

The `slot_choices_for_seed(seed) -> list[tuple[str, str]]` function
exports the per-seed module picks; it's consumed by the
`module_topology_diversity` coverage gate.

### Contract 5 — `__modular__ = True`

Set `__modular__ = True` at module scope. The sweep coverage gate uses
this flag to:
- Skip the legacy `anchor_geometry_match` gate (replaced by per-module sources in the spec's module table)
- Run `module_topology_diversity` instead (counts distinct slot_choice
  tuples across passing seeds; needs ≥5)

---

## Required deliverables

When adding a new modular template `<slug>`, produce:

1. **`agent/templates/<slug>.py`** — the template module. Must export:
   - `<Slug>Config` (frozen dataclass, public API)
   - `Resolved<Slug>Config` (clamped, internal)
   - `config_from_seed(seed: int) -> <Slug>Config` — seed=0 = anchor
   - `resolve_config(config) -> Resolved<Slug>Config`
   - `build_<slug>(config, *, assets=None) -> ArticulatedObject`
   - `build_seeded_<slug>(seed) -> ArticulatedObject`
   - `slot_choices_for_seed(seed) -> list[tuple[str, str]]`
   - `run_<slug>_tests(model, config) -> TestReport`
   - `__modular__ = True`
2. **`tests/agent/test_<slug>_template.py`** — must include:
   - Seed reproducibility test
   - Seed=0 equals anchor combination test
   - All-combinations-build test (loop the entire slot×module grid)
   - Topology diversity test (≥7 distinct picks in first 10 seeds)
   - Invalid module rejection test per slot
3. **`articraft_template_authoring/specs/<slug>.md`** — spec doc.
   Replace the single `primary_anchor` field with a `topology_variants`
   table listing each module and its source record.

---

## Validation contract — must pass before declaring done

```bash
# 1. Unit tests
uv run --group dev pytest tests/agent/test_<slug>_template.py -q

# 2. Compile sweep (50 seeds across 4 parallel processes)
uv run articraft template compile-sweep <slug> --seeds 0-49 \
    --quiet --out /tmp/sw_<slug>.json
```

The sweep JSON must satisfy:
- `verdict == "pass"`
- `pass_rate >= 0.85` (default threshold; configurable via `--pass-threshold`)
- `coverage_gates.module_topology_diversity.status == "pass"` (≥5 distinct
  observed combinations)

Then visually verify:
```bash
uv run articraft template batch <slug> --seeds 0-9 --agent claude-code
just viewer
```
Walk through all 10 seeds in the viewer to catch issues the gates miss
(weird proportions, parts that look floating despite passing connectivity,
mechanism that doesn't slide as intended). Do not declare done if any
seed looks broken in the viewer.

---

## Common pitfalls (learned the hard way)

### Disconnected geometry islands
Most common. The strict 1e-6 connectivity check fails any visual that
doesn't AABB-overlap with the rest of its part. Symptoms:
- A lug or boss appears to "float" near a joint pivot
- A bridge mesh sits above a carrier_block with a gap
- A bracket sits above a top_deck without overlap

Fix: insert a **connector** visual (Box neck or vertical riser) that
overlaps both the floating visual and the rest of the part. The
connector typically has small width and tall z to span the gap.

When you place a visual at z=0 (e.g. above wall_top_z) "touching" another
at z=0, that's a boundary — push by 1mm so AABBs actually overlap.

If the part is *supposed* to be separated rigid pieces (comb teeth, a
grille, a fin stack) and a connector would invent fake material, declare
`ctx.allow_disconnected_islands(part, reason="...")` instead of bridging.
That is the only sanctioned way to keep genuine multi-piece parts; never
reach for it to hide an accidental split.

### Joint origin far from geometry
`fail_if_articulation_origin_far_from_geometry(tol=0.015)` requires the
joint origin (in parent's frame) to lie within tolerance of both parent
and child AABB. The baseline tol is **relative**: the effective tol per
joint is `max(0.015, 0.05 * max(parent, child) bbox diagonal)`, so the
15mm floor still applies to small parts while large parts get a
proportional allowance instead of a fixed 15mm that would be unfairly
tight. It only ever loosens, so no previously-passing template regresses.

For chain joints emitted by the assembler, this means the **child
module's visuals must contain (0,0,0) in part frame**, since the child
frame's origin is at the joint origin. Typical fix: emit the upstream
mating face's geometry so its AABB includes the origin (e.g., a hub
cylinder centered on z=0..length, x=0±radius, y=0±radius).

### Mating gap along normal axis
`fail_if_joint_mating_has_gap` measures distance **only along the
parent face's outward normal** (axis-aligned), not 3D Euclidean. So
sliding rails (long parent face, short child face) and asymmetric
mounts work fine if the normal-axis position matches. Tangential
offset is free.

Use this property: place the child's upstream face anchor at any
tangential x/y as long as the normal-axis component is 0.

### Captured-pin overlaps
Mechanical pivots — pin-through-sleeve, hub straddling clevis lugs,
spindle in bearing cup — have intentional inter-part overlap. The
compiler baseline's overlap check would flag them. Declare allowances
in `run_<slug>_tests`:

```python
ctx.allow_overlap(
    parent_part,
    child_part,
    elem_a="parent_visual",
    elem_b="child_visual",
    reason="<short rationale>",
)
```

See [`_allow_internal_pivot_overlaps`](agent/templates/monitor_mount.py)
in monitor_mount for a comprehensive example covering shoulder, elbow,
wrist clevises + their riser webs.

### MatingContract grandfathering
Joints whose geometry can't be modeled as two axis-aligned faces in
contact (pin through sleeve, captured trunnion, ball-in-socket) should
**omit** the `mating=...` field. These are "grandfathered" — the
`fail_if_joint_mating_has_gap` check is skipped for them. The
articulation still works; only the mating-contract verification is
opted out.

Use sparingly — prefer real MatingContracts where the geometry fits
(clevis: top_lug +z mating to child hub -z is a perfect fit).

### Inter-part overlap from extended connectors
When you add a connector neck/riser to fix disconnected islands, it
may now collide with adjacent parts at the joint. Declare
`allow_overlap` between the new connector and the adjacent parts'
hubs/collars/lugs. See monitor_mount's wrist_riser_web declarations.

### Pass threshold
Default is **0.85** (50 seeds → ≤7 failures tolerated). For wide-domain
modular templates this is appropriate. Set higher (`--pass-threshold 0.95`)
only if your template has a narrow parameter range and you want a
quality bar.

---

## Pattern: parallel-children slot

For DJ-equipment-style templates where multiple slot's parts all
parent to a single chassis (not a serial chain):

```python
def _build_deck_layout(ctx: ModuleBuildContext) -> ModuleBuild:
    model = ctx.model
    # Read upstream module's housing name (set by chassis slot).
    housing_name = ctx.upstream_interface.part_name  # "housing"
    housing = model.get_part(housing_name)

    # Emit child parts and joints with parent=housing.
    left_platter = model.part("left_platter")
    # ... build platter visuals ...
    model.articulation(
        "housing_to_left_platter",
        ArticulationType.REVOLUTE,
        parent=housing,
        child=left_platter,
        origin=...,
        axis=(0, 0, 1),
        mating=...,
    )

    # Crucially: do NOT define an "upstream" interface — that suppresses
    # the assembler's automatic chain joint.
    # Optionally re-export the housing's downstream face so subsequent
    # slots also parent to housing.
    return ModuleBuild(
        module_name="dual_jog_decks",
        parts_emitted=["left_platter", "right_platter"],
        internal_articulations=["housing_to_left_platter",
                                "housing_to_right_platter"],
        interfaces={"downstream": ctx.upstream_interface},
    )
```

---

## Pattern: variable-multiplicity radial (fan blades, propellers, gear teeth)

For templates where a slot's module emits **N identical sub-parts radially
attached to a common hub** (fan blades, propeller fins, gear teeth,
camera rig spokes), declare **one module per N** and emit N FIXED
children of the hub with even angular spacing:

```python
def _build_n_blade_rotor(ctx: ModuleBuildContext, *, n: int) -> ModuleBuild:
    model = ctx.model
    r: ResolvedConfig = ctx.config  # type: ignore[assignment]

    # The hub lives in the upstream module (motor/housing). Read its
    # name from the upstream interface.
    hub_name = ctx.upstream_interface.part_name
    hub = model.get_part(hub_name)

    for i in range(n):
        blade = model.part(f"blade_{i}")
        _emit_blade_visuals(blade, r)  # geometry identical per blade
        angle = i * 2.0 * math.pi / n
        # FIXED child of hub. All blades rotate together when the hub
        # rotates (the motor → hub joint is REVOLUTE upstream).
        # MatingContract on radial blade-root ↔ hub-cylinder geometry
        # doesn't fit cleanly, so grandfather and rely on allow_overlap.
        model.articulation(
            f"hub_to_blade_{i}",
            ArticulationType.FIXED,
            parent=hub,
            child=blade,
            origin=Origin(xyz=(0.0, 0.0, 0.0), rpy=(0.0, 0.0, angle)),
        )

    return ModuleBuild(
        module_name=f"{n}_blade_set",
        parts_emitted=[f"blade_{i}" for i in range(n)],
        internal_articulations=[f"hub_to_blade_{i}" for i in range(n)],
        # No "upstream" interface — that suppresses the assembler's
        # automatic chain joint. The motor → hub coupling lives in
        # the upstream module.
        interfaces={"downstream": ctx.upstream_interface},
    )

BLADE_FACTORIES = {
    f"{prefix}_blade_set": (lambda n=n: lambda ctx: _build_n_blade_rotor(ctx, n=n))()
    for n, prefix in [(3, "tri"), (4, "quad"), (5, "quint"),
                       (6, "hex"), (7, "hept"), (8, "oct")]
}
```

This is the **parallel-children pattern** (see dj_equipment) combined
with multiplicity in the module name. Key differences from the
serial-chain N-link arm:

| | Serial chain (N-link arm) | Parallel radial (N-blade rotor) |
|---|---|---|
| Topology | `link_0 → link_1 → ... → link_{N-1}` | `hub → blade_0`, `hub → blade_1`, … (all FIXED) |
| Joints | N-1 internal REVOLUTE | N FIXED, all to same hub |
| Each link parents to | Previous link | Same upstream hub |
| Module declares | upstream + downstream interface | downstream only; re-exports upstream |
| Real-world | Articulated arm, scissor lift, telescoping pole | Fan, propeller, gear, ferris wheel, sprocket |

**Important practical notes for radial multiplicity**:
- All N blades share **identical geometry** — emit via one shared helper
  to keep visual count and bbox proportional across the N variants
- Declare `ctx.allow_overlap(hub, blade_i, ...)` for every blade's root
  visual ↔ hub cylinder in `run_<slug>_tests`, since the radial blade-root
  contact isn't modeled by MatingContract
- `disconnected_geometry_islands` will pass per-blade trivially (each
  blade has few visuals all locally connected), but **don't forget to
  connect each blade's own internal visuals** — if a blade has a tip
  cap that doesn't touch the blade root, it's a per-part island
- Blade angular orientation in its OWN frame: the blade extends along
  +x (radial outward); the hub joint's rpy rotates each blade around z

---

## Pattern: variable-multiplicity chain (N-link arm)

For templates where a slot's module needs to expose a parameterized number
of repeated sub-parts (e.g., 1-8 arm links), declare **one module per
N** rather than threading multiplicity through a single module:

```python
ARM_FACTORIES = {
    f"{prefix}_link_arm": (lambda n=n: lambda ctx: _build_n_link_arm(ctx, n=n))()
    for n, prefix in [(1, "single"), (2, "dual"), (3, "triple"),
                       (4, "quad"), (5, "quint"), (6, "hex"),
                       (7, "hept"), (8, "oct")]
}
```

The module name encodes N (e.g. `quint_link_arm`), which is what the
`module_topology_diversity` gate counts as distinct combinations. This
gives the gate the granularity to verify all chain lengths are sampled.

The internal `_build_n_link_arm(ctx, *, n)` helper iterates: emit
primary_arm with shoulder_hub + elbow_clevis; emit N-2 mid_arm_i parts
via a shared `_emit_mid_arm_link` helper; emit secondary_arm with
elbow_hub + wrist_clevis; chain them with `elbow_fold_i` REVOLUTE
joints.

See monitor_mount's `_build_n_link_arm` for a working example.

---

## Reporting iteration progress

When iterating on a failing sweep, paste the relevant JSON fields:

```bash
python3 -c "
import json
d=json.load(open('/tmp/sw_<slug>.json'))
print('verdict:', d['verdict'], 'pass_rate:', d['pass_rate'])
print('diversity:', d['coverage_gates']['module_topology_diversity']['details']['observed_distinct'])
for c in d.get('failure_clusters', [])[:3]:
    print('FAIL count:', len(c.get('seeds', [])))
    print('  detail:', c.get('example_failure_details', '')[:300])
"
```

Don't claim done unless `verdict == "pass"`. A `pass_rate` of 0.84 with
8 failing seeds means there's still a systematic edge case to address,
not a "close enough".

---

## Where new strict gates come from

The compiler-owned baseline (in [`agent/compiler.py`](agent/compiler.py)
`_run_compiler_owned_baseline_tests`) runs on every compile. Adding a
new strict check there means ALL templates must satisfy it. The
disconnected_geometry_islands check was upgraded from warn-level to
fail-level in 2026-05; future strict additions should follow the same
pattern (audit existing templates first, fix any that would regress).
