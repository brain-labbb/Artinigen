# Template Design Rules

Hard rules every procedural template under `agent/templates/<slug>.py` must
follow. These are checked mechanically by `articraft template compile-sweep`'s
gates and by the compiler-owned baseline; a template that violates any of
them cannot reach `verdict=pass`.

Read this **before** writing the first line of a new template, and again
whenever a sweep surfaces a rule-3 cluster.

---

## Rule 1: 不动就不是 part ("if it doesn't move, it isn't a part")

**Decorative sub-elements that don't articulate (no revolute / prismatic /
continuous joint) MUST be attached as `parent.visual(...)`, NOT as separate
parts joined to the parent by a FIXED articulation.**

### Why

The 5-star records authored by the LLM record-generation harness consistently
fuse decorative geometry into the same `Part`. The 1-3 star records — and
many existing parametric templates — instead introduce a separate `Part` for
each decoration and connect it via a `FIXED` joint, often anchored to a tiny
"interface" disk on the parent. The interface disk is geometrically present
(so `fail_if_isolated_parts` / `fail_if_parts_overlap` pass at 1µm tol) but
visually invisible — leading to the dj_knob / gpu_bracket / knife_slider
"floating decoration" failure mode the user has shown is the dominant
remaining bug after baseline.

### Enforcement

Each candidate module's structure (parts, joints, per-part visual count)
must be derivable from its 5-star source record cited in the spec's module
table. The reviewer checks during spec review that the module table cites
real `model.py:Lx-Ly` ranges (see [`SPEC_REVIEW_TEMPLATE.md`](SPEC_REVIEW_TEMPLATE.md)).
At compile time two baseline checks guard this rule:

- `fail_if_unsupported_visual_islands` is the final hard gate. Every
  non-degenerate visible element must have a contact, slight embed, supported
  neighbor, or passing `MatingContract` path to the grounded body. This applies
  inside one part and between parts. A bare articulation is not support.
- `warn_if_part_contains_disconnected_geometry_islands` surfaces *every*
  part-internal island (any non-touching rigid piece) as a non-blocking
  warning. A single part being several separated pieces is often legitimate
  (comb teeth, fin stacks, bead arrays), so this does not fail the compile.
- `warn_if_floating_geometry_islands` remains a migration diagnostic for old
  part-internal float patterns, but final acceptance is decided by the visible
  support graph.

Exception: a part that is genuinely separated rigid pieces (comb teeth, a
grille, a fin stack) where connective geometry would invent material the real
object lacks may declare `ctx.allow_disconnected_islands(part, reason="...")`.
This silences the warning only; it does **not** exempt the part from the final
visual support graph. `allow_floating=True` is rejected by final profile. Fix
unsupported visible geometry with real contact, a visible support, or a passing
`MatingContract`; never mask an accidental seed-driven split.

### Examples

**Bad — `dj_equipment` knob, pre-rewrite:**
```python
body.visual(Cylinder(r=0.015, L=0.003),    # tiny "knob_hole" disk
            origin=Origin(xyz=(x, y, panel_z + 0.003)))
knob = model.part(f"knob_{i}")              # independent decorative part
_build_knob_part(knob, ...)
model.articulation(
    f"knob_turn_{i}",
    REVOLUTE,                                # this one IS articulated — OK
    parent=body, child=knob,
    origin=Origin(xyz=(x, y, panel_z + 0.004)),
    axis=(0, 0, 1),
)
```

If the knob actually rotates (REVOLUTE), this is fine — but the body must
have a *real* anchoring visual (see Rule 2), not the 3mm disk.

**Bad — purely decorative pad as separate part:**
```python
pad = model.part(f"pad_{i}")                # pad doesn't articulate
pad.visual(Box((0.030, 0.030, 0.003)), ...)
model.articulation(
    f"pad_fixed_{i}",
    FIXED,                                   # ⛔ Rule 1 violation
    parent=body, child=pad,
    origin=Origin(xyz=(x, y, panel_z + 0.0015)),
)
```

**Good — fold pad into the body:**
```python
body.visual(
    Box((0.030, 0.030, 0.003)),
    origin=Origin(xyz=(x, y, panel_z + 0.0015)),
    name=f"pad_{i}",                         # named visual, same part
)
```

### Allowed exceptions

The only legitimate reason to use FIXED articulations is when two parts
genuinely need independent reference frames (e.g., separate kinematic
sub-assemblies that you later compose). If you must, add a docstring above
the joint explaining *why* a fixed articulation is required instead of
visual fusing, and verify the parent has a real anchoring visual per Rule 2.

---

## Rule 2: parent must really anchor the child ("no phantom anchors")

**When a template DOES need a separate part attached via a joint, the parent
part's geometry at the joint location must visually anchor the child — not a
1-3mm "interface" disk that disappears in the rendering.**

Concretely:

- Every articulation that creates a separate child part must declare a
  `MatingContract` pinning the parent's mating face and the child's mating
  face to the specific visuals that touch.
- The parent's mating visual must be a *real* visual — large enough to
  visually justify the child's position — not a sub-millimetre cosmetic.

### Why

Even when `fail_if_articulation_origin_far_from_geometry` passes (joint
origin is within 15mm of both part geometries), the mating *surfaces* of
the two visuals may still be separated by several millimetres of air. Five
of the seven `verdict=pass` templates we saw exhibit this — a small parent
"hole" disk inside the body's flat panel anchors the knob geometrically but
not visually.

### Enforcement

The compiler-owned baseline runs `fail_if_joint_mating_has_gap` on every
compile. For each articulation that declares a MatingContract, the check
computes the world-frame position of the named parent face and the named
child face and fails if their distance exceeds `contact_tol` (default 1mm).
Joints without a MatingContract are grandfathered (skipped).

### Example

**Bad — knob anchored by a phantom 3mm disk:**
```python
body.visual(
    Cylinder(radius=0.015, length=0.003),    # 3mm thick disk
    origin=Origin(xyz=(x, y, panel_z + 0.003)),
    name=f"knob_socket_{i}",
)
knob = model.part(f"knob_{i}")
_build_knob_part(knob, ...)
model.articulation(
    f"knob_turn_{i}",
    ArticulationType.REVOLUTE,
    parent=body, child=knob,
    origin=Origin(xyz=(x, y, panel_z + 0.004)),
    # ⛔ No MatingContract — knob_bottom can sit at panel_z + 0.004
    # but the visible body panel top is at panel_z + 0.005, leaving
    # 4mm of air between the panel and the knob.
)
```

**Good — knob mating face explicitly pinned to a real body face:**
```python
body.visual(
    Box((panel_w, panel_d, panel_thickness)),
    origin=Origin(xyz=(0.0, 0.0, panel_z + 0.5 * panel_thickness)),
    name="control_panel",                    # the actual panel visual
)
knob = model.part(f"knob_{i}")
_build_knob_part(knob, ...)
model.articulation(
    f"knob_turn_{i}",
    ArticulationType.REVOLUTE,
    parent=body, child=knob,
    origin=Origin(xyz=(x, y, panel_z + panel_thickness)),
    axis=(0, 0, 1),
    mating=MatingContract(
        parent_face_geometry="control_panel",
        parent_face_side="positive_z",
        child_face_geometry="knob_body",
        child_face_side="negative_z",
        contact_tol=0.001,
    ),
)
```

Now if the knob's `_build_knob_part` puts `knob_body` extent so its bottom
isn't at `panel_z + panel_thickness`, the baseline fails with a clear
deviation report.

---

## Rule 3: derive each module from a real 5-star sample

**Every candidate module's part tree, joint topology, per-part visual count,
and per-part primitive types must be derivable from a real 5-star sample
(declared as the module's `source_5_star_record` + `model.py:Lx-Ly` in the
spec's module table). Agents may freely parameterize literal dimensions,
enum branches, and loop counts; they may not invent structural elements no
5-star sample has, and they may not downgrade sophisticated primitives
(LatheGeometry / mesh_from_geometry / cadquery output → `Mesh`) to crude
Box/Cylinder placeholders.**

### Why

Without a real source per module, agents drift to "imagine what a category
looks like" mode — and the dominant failure mode is that agents pick crude
boxes/cylinders where the 5-star sample has carefully sculpted lathe
profiles, or invent entire structural elements (extra parts, extra joint
chains) that no 5-star sample has.

### How modular templates pin sources

The spec's module table lists, per slot, every candidate module's 5-star
source with `model.py:Lx-Ly` line references:

```markdown
## 槽位 + 候选模块表

### Slot housing

| module_name | 5_star_source | model.py:Lx-Ly | seed=0 anchor | 结构特征 |
|---|---|---|---|---|
| barrel_grip | rec_..._cad8... | L93-L193 | **yes** | classic box-cutter envelope |
| pistol_grip | rec_..._9365... | L40-L155 |  | pistol grip + finger guard |
```

The implementation must adapt those line ranges into the module factory:
copy structure, parameterize dimensions, keep primitive types.

### Authoring workflow under Rule 3

When writing each module factory, the **first action** must be:

1. Open the source 5-star record's `model.py` at the line range cited in
   the spec.
2. Read those lines end-to-end. Identify each helper, each `part.visual(...)`
   call, each `model.articulation(...)`. Decide which literals to
   parameterize and which loops to make variable-count.
3. Sketch the module's part tree mirroring the source's structure.
4. Implement the factory that adapts the source's geometry. Replace literal
   coordinates with `r.<field>`; keep primitive types (Box stays Box,
   Cylinder stays Cylinder, Mesh stays Mesh).
5. Add `MatingContract` to every joint that creates a separate child part
   (Rule 2). Use `allow_overlap` for captured-pin geometry (Rule 2's
   grandfather pattern).
6. Run `compile-sweep --quality-profile final`. Iterate until `verdict=pass`.

### What "adapting" means concretely

- ✓ Replace `Cylinder(radius=0.115, length=0.030)` with
  `Cylinder(radius=config.hub_radius, length=config.hub_height)`.
- ✓ Replace `for i in (0, 1, 2):` with `for i in range(config.blade_count):`.
- ✓ Add an `if r.blade_shape == "swept":` branch that calls a *different*
  `mesh_from_geometry(...)` profile — but you must still call
  `mesh_from_geometry`, not fall back to `Box(...)`.
- ⛔ Replace `LatheGeometry([(0.000, -0.056), (0.072, -0.050), ...])` with
  `Cylinder(radius=0.072, length=0.10)`. **Downgrading primitives is the
  thing this rule exists to prevent.**

If you genuinely can't adopt the anchor's primitive choices (e.g., the
anchor uses a cadquery mesh and your template's environment can't import
cadquery), open a discussion before authoring — don't silently substitute
crude primitives.

---

## Putting it together: a checklist for a new template

Before declaring a template done, all of the following must hold:

1. [ ] Spec's module table lists, per slot, each candidate module's
   `source_5_star_record` + `model.py:Lx-Ly` line range.
2. [ ] Every module factory was authored after reading the cited line
   range. Literal values were parameterized; primitive types were
   preserved.
3. [ ] No FIXED articulation exists unless the docstring justifies why
   visual fusing won't work (Rule 1).
4. [ ] Every chain joint declares a `MatingContract` pointing to real
   visuals on both sides (Rule 2); captured-pin geometry is grandfathered
   with `allow_overlap` declarations in `run_<slug>_tests`.
5. [ ] `compile-sweep --quality-profile final` reports `verdict=pass` on
   `--seeds 0-49`:
   - `pass_rate == 1.0`.
   - `quality_summary.failed_gates == {}`.
   - `coverage_gates.module_topology_diversity.status == "pass"`
     (≥5 distinct slot-choice combinations).
6. [ ] `template batch --seeds 0-9 --agent claude-code` produces 10/10
   compilable records, and the agent visually checks the viewer for
   floating parts / gross geometry errors.

If you reach step 5 with a persistent failure cluster, **do not patch
around it**. Either correct the affected module to match its 5-star
source, fix the connectivity / mating geometry per
[`MATURE_METHOD.md`](MATURE_METHOD.md) §"常见失败模式", or escalate to
the user.
