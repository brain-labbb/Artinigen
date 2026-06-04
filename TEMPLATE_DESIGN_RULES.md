# Template Design Rules

Hard rules every procedural template under `agent/templates/<slug>.py` must
follow. These are checked mechanically by `articraft template compile-sweep`'s
gates and by the compiler-owned baseline; a template that violates any of
them cannot reach `verdict=pass`.

Read this **before** writing the first line of a new template. For new
Articraft category templates, also read `MODULAR_TEMPLATE_AUTHORING.md`; its
per-module source contract replaces the legacy single-anchor contract below.

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

For modular templates, this is enforced through module source review,
`module_topology_diversity`, visual support checks, and MatingContract checks.
For legacy non-modular templates, the `anchor_geometry_match` gate also catches
part/joint topology drift from a single anchor.

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

## Rule 3: derive structure from declared 5-star sources

New category templates are modular. They derive structure from per-module
5-star sources declared in the modular spec, not from a single `primary_anchor`.
Set `__modular__ = True`, implement `slot_choices_for_seed`, and use
`module_topology_diversity` as the topology coverage gate. Each module factory
must preserve the source module's part tree, joint semantics, primitive
complexity, and interface/support relationship.

### Legacy non-modular path: single PRIMARY_ANCHOR

**A template's part tree, joint topology, per-part visual count, and per-part
primitive types must be derivable from a single nominated 5-star record (the
PRIMARY_ANCHOR). Agents may freely parameterize literal dimensions, enum
branches, and loop counts; they may not invent structural elements the
anchor doesn't have, and they may not downgrade sophisticated primitives
(LatheGeometry / mesh_from_geometry / cadquery output → `Mesh`) to crude
Box/Cylinder placeholders.**

### Why

Without an anchor, agents drift to "imagine what a category looks like"
mode — and the dominant failure mode (visible in dj_equipment,
graphics_card, retractable_utility_knife) is that the agent picks crude
boxes/cylinders where the 5-star sample has carefully sculpted lathe
profiles. We've also seen agents invent entire structural elements (extra
parts, extra joint chains) that no 5-star sample has.

### Enforcement — `anchor_geometry_match` gate

The spec must declare `primary_anchor` in its 元信息 table:

```markdown
## 元信息
| 项 | 值 |
|---|---|
| slug | `dj_equipment` |
| template path | `agent/templates/dj_equipment.py` |
| primary_anchor | `rec_dj_equipment_xxx:rev_000001` |
| ...
```

On every sweep, `articraft template compile-sweep` extracts the anchor's
geometry fingerprint (part names normalized with `_i` suffix for indexed
families; joint topology; per-part visual count + primitive histogram +
Mesh count; overall bbox aspect ratio) and compares it to the template's
fingerprint at `seed=0`. Six sub-checks must all pass:

| Sub-check | What it catches |
|---|---|
| `part_name_set` | Template introduces parts the anchor doesn't have, or is missing parts the anchor has |
| `joint_topology` | Template adds/drops (parent, child, type) joint triples |
| `visual_count_per_part` | Template collapses anchor's N visuals into <50% of N |
| `primitive_complexity_lower_bound` | Template's Mesh count for any part drops below the anchor's |
| `primitive_histogram_similarity` | Template swaps primitive types (Cylinder→Box, etc.) |
| `bbox_ratio` | Template's overall aspect ratio diverges from the anchor's by more than 30% on any axis |

### Authoring workflow under Rule 3

When writing a new template (or rewriting an existing one), the **first
action** must be:

1. Run `uv run articraft template anchor-fingerprint <PRIMARY_ANCHOR>` to
   inspect the structure you must inherit.
2. Read the anchor's `model.py` end-to-end. Identify each helper, each
   `part.visual(...)` call, each `model.articulation(...)`. Decide which
   literals to parameterize and which loops to make variable-count.
3. Sketch the template's part tree mirroring the anchor's part tree
   (collapsing indexed families like `blade_0..N` into a single `blade_i`
   in your mental model).
4. Implement helpers that adapt the anchor's geometry. Replace literal
   coordinates with `config.<field>` / `r.<field>`; keep primitive types
   (Box stays Box, Cylinder stays Cylinder, Mesh stays Mesh).
5. Add `MatingContract` to every joint that creates a separate child part
   (Rule 2).
6. Run `compile-sweep`. Iterate until `verdict=pass`.

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

Before declaring a new modular template done, all of the following must hold:

1. [ ] Spec declares `__modular__ = True` and per-module 5-star sources.
2. [ ] Every module factory was authored after reading its source snippet.
   Literal values were parameterized; primitive types and joint semantics were
   preserved.
3. [ ] No FIXED articulation exists unless the docstring justifies why
   visual fusing won't work (Rule 1).
4. [ ] Every non-FIXED articulation declares a `MatingContract` pointing
   to real visuals on both sides (Rule 2).
5. [ ] `compile-sweep` reports `verdict=pass` on `--seeds 0-49`:
   - `pass_rate >= 0.95` (baseline incl. mating-gap, articulation-origin,
     overlap, isolated-parts).
   - `coverage_gates.line_floor.status == "pass"`.
   - `coverage_gates.module_topology_diversity.status == "pass"`.
6. [ ] Preview-self-checked seeds 0, 1, 2 visually look like the category
   and the closed pose has no visible gaps.

For legacy non-modular templates, replace items 1, 2, and the topology gate
with the single `primary_anchor` / `anchor_geometry_match` contract. Do not use
that legacy route for new modular category templates.
