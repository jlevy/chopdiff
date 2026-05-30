# Feature: A flexible unified document model (DocGraph)

**Date:** 2026-05-29 (last updated 2026-05-30)

**Author:** chopdiff maintainers

**Status:** Draft — **all nine decisions settled (2026-05-29 / 2026-05-30).** Decision
records DR-1..DR-6 cover the architecture (node table; `DocGraph` projection; Pydantic
authoring; one `collect()` rollup primitive; composable `include` layers; the `SpanRef`
span-reference type), plus 6 (minimal phase-1 scope), 8 (lazy-cache), 9 (count list-item
wrapper paragraphs). The **layered-parsing lens (E9, 2026-05-30)** is folded in as a
consolidating frame: it validates DR-1..DR-6, adds four cheap Phase-1 hooks (node `layer`
field, offset-containment queries, per-layer nesting guarantee, `SpanRef`-anchored edits),
unifies the `Layer` vocabulary, and names later Phases 3–4 (synthetic layer; cross-layer
structural edits). Ready to break Phase 1 into implementation beads.

**Implementation status:** **None yet — design settled, ready to build.** All nine
decisions are recorded (DR-1..DR-6); the next step is to break Phase 1 into implementation
beads. It builds on the block-aware/normalized-form work shipped in v0.4.0 (exact spans,
structural `blocks()`, sections, links, top-level `block_type_counts()`); everything
proposed here — recursive/nested rollups, the `SpanRef` model, and the `DocGraph`
projection — is not yet built. Tracked by epic `chopdiff-8q8q`.

> **Inputs:** the surveys in
> [`research-2026-05-29-document-model.md`](../../research/research-2026-05-29-document-model.md)
> (read it first — this plan operationalizes its recommended direction),
> [`research-2026-05-30-span-references.md`](../../research/research-2026-05-30-span-references.md)
> (the `SpanRef` design), and
> [`research-2026-05-30-multilayer-parsing.md`](../../research/research-2026-05-30-multilayer-parsing.md)
> (the layered-parsing lens, E9), and the design of record
> [`docs/textdoc-spec.md`](../../../textdoc-spec.md). This plan **subsumes** the archived
> [`plan-2026-05-29-multilevel-block-tallies.md`](../archive/plan-2026-05-29-multilevel-block-tallies.md):
> multi-level tallies become one feature of the unified model (their decisions are folded
> in here).

## Overview

We want a single, source-grounded, JSON-serializable representation of a *fully processed*
document from which we can cheaply derive any view (the exact original structure, the
section tree, the block tree, inline items) and any **rollup** — of either **values** (the
items themselves) or **counts** — at any scope (document, section, or block), recursively,
including inline items and the relationships between blocks and inline items. The model
should serialize cleanly for frontend UIs and support a few **optional levels of detail**
so it need not always be large.

The research concludes — and this plan adopts — that the durable shape is **not a single
tree** but a **stable node set addressable by id, plus typed layers and derived views**.
Sections cross-cut block containment, links are inline ranges, annotations are arbitrary;
a single hierarchy cannot hold all of them, but a node table with span/id addressing makes
every tree, slice, and rollup a cheap projection. `TextDoc` remains the Python core;
**`DocGraph`** is the serialized, language-neutral projection.

## Goals

- One **unified JSON schema** (`DocGraph`) for the fully processed document,
  reusable and serializable into frontend UIs.
- Recover the **exact original document structure** (containment tree) *and* the **section
  tree** as derived views of the same node set.
- **Flexible rollups** with no precommitment: values *or* counts, scoped to document /
  section / block, recursive or shallow, over blocks *and* inline items.
- First-class **inline items** (links, code spans, images, …) and **block↔inline
  relationships** (which inline items live in which block / sentence / section).
- **Slice by section** for every view and rollup.
- **Optional levels of detail** so a caller can ask for a small structural overview or a
  full dump.
- Stay within the design-of-record principles: source canonical, derived views, **no
  stored counts**, additive to `TextDoc`.

## Non-Goals

- A parallel runtime Python document model competing with `TextDoc` (the research is
  explicit: extend `TextDoc`; `DocGraph` is a projection/contract).
- Live collaborative editing, CRDForms, or a rich-text editor model as canonical (client
  edge only; keep an opaque `anchor` slot open).
- Perfect byte-for-byte source-preserving Markdown surgery (normalized rewrite is the
  first writeback target).
- New parser/editor dependencies in this phase (Marko/flowmark only; djot is a documented
  fallback). Follow `SUPPLY-CHAIN-SECURITY.md`.
- Layout/PDF geometry, annotations, and operation/provenance layers as *built* features
  now — the schema reserves slots for them, but they are later phases.

## Background

Where we are after v0.4.0:

- `TextDoc` is source-referenced (paragraph/sentence spans), block-aware
  (`TextDoc.blocks()` structural tree via flowmark spans), section-aware
  (`sections()`/`toc()`), and link-aware (`links()` with recovered spans).
- Tallies exist but are **top-level only**: `block_type_counts()` does not descend into
  blockquotes/list-items, returns counts (not values or locations together), and
  `Section.blocks()` re-parses the whole document per section. (This is the gap
  `plan-2026-05-29-multilevel-block-tallies.md` opened; it is folded in here.)
- The structural tree is a pure function of the immutable `source_text`, so caching is
  safe; flowmark already exposes every nested block with a span, so the full recursive
  structure is one walk away.

What the research adds: model ≠ format ≠ implementation; pin coordinates (Unicode code
points) and ids; stand-off layering as the conceptual core; red-green (immutable nodes +
computed position, trivia first-class) as the structural-tree pattern; "zoom and views are
one requirement."

**Prerequisite — robustness hardening.** This plan builds on `TextDoc`'s offsets,
sub-document slicing, and transforms. Phase 1 of
[`plan-2026-05-26-robustness-hardening.md`](plan-2026-05-26-robustness-hardening.md)
should land first: `sub_doc`/`sub_paras` currently alias caller objects (the node
table/`SpanRef` model wants safe copies), `filtered_transform` can skip its filter, and
div chunking mis-slices. The doc-model's source-grounding assumptions (exact spans,
honest `from_text` normalization) are already satisfied in v0.4.0.

## Requirements (from the request)

1. Rollups at **any time** of **values or counts**, not overly constrained.
2. Scoped around **blocks** or the **whole document** — and **by section**.
3. **Recursively** collect blocks **and inline item values**, and the **relationships**
   between blocks and inline items.
4. The **full recursive structure** available when needed.
5. Ideally a **tree document** whose section structure can be broken into the **exact
   original structure** *or* **any rollup**.
6. Likely a **single unified JSON schema** for the fully processed document, reusable and
   **serializable to frontend UIs**.
7. **A few optional levels of detail** so it is not always large.
8. **A consistent reference/annotation model across source, parsed model, and rendered
   output.** It must be easy to reference a piece of the document — a line/span in the
   original source, a *parsed element* (a table, a link), or a region in *rendered*
   content — using one scheme. References made against parsed elements must resolve down
   to the original source; **persisted** references must be **source-grounded** (the saved
   form references the original document); **in-memory/editor** references may use the tree
   but must round-trip to source on save and re-resolve to nodes on load/reparse.

---

# Exploration

Each subsection states the question, the realistic options, pros/cons, and a leaning;
the settled choices are recorded under "Decisions" and the Decision Record.

## E1. One tree, or a node set with derived trees?

The request asks for a "tree document … broken down into the exact original structure or
any rollup." The instinct is a single tree. The research argues against a single canonical
tree.

- **Option 1a — one canonical tree (blocks), sections as an overlay.** The block
  containment tree is canonical; sections are computed from heading levels and reference
  block ids.
  - *Pros:* matches intuition; the "exact original structure" is literally the tree;
    simple mental model.
  - *Cons:* sections cross-cut block containment (a section spans many sibling blocks and
    stops mid-stream at the next heading), so the section tree is *not* a subtree of the
    block tree — it must be an overlay anyway. Inline items and annotations are ranges, not
    tree nodes. So "one tree" silently becomes "one tree plus overlays."
- **Option 1b — a stable node set (table) addressable by id + span, with every tree and
  slice as a derived view (research's recommendation).** Nodes carry `parent`/`children`
  for the containment tree; the section tree, block list, inline index, and rollups are
  projections sharing node ids.
  - *Pros:* the exact containment tree *and* the section tree *and* any rollup are all
    cheap projections of one set; overlapping/cross-cutting layers (sections, links,
    annotations) are natural; "zoom = pick a view + level" falls out; serializes to one
    JSON.
  - *Cons:* one more indirection than a bare tree; need discipline on ids and span units.

**Leaning: 1b, presented so the tree intuition is preserved as a view.** The user's "tree
that breaks down into exact structure or any rollup" is exactly 1b's containment-tree
projection plus rollup projections — we get the tree *and* the flexibility, instead of
choosing. The JSON still *looks* tree-shaped at the top (a `document` root with children),
so consumers that just want the tree ignore the extra indexes.

## E2. Canonical store: extend `TextDoc`, or a standalone object?

- **Option 2a — `DocGraph` is purely a serialized projection** built on demand
  from `TextDoc` (+ its block tree, sections, links). No new long-lived runtime object;
  `TextDoc` stays the core.
  - *Pros:* matches the research ("extend TextDoc; DocGraph is the contract"); no
    parallel model to keep in sync; reuses spans/sections/links already built.
  - *Cons:* the projection logic lives somewhere (a builder); repeated builds cost unless
    cached.
- **Option 2b — a first-class `DocGraph` runtime object** that owns the node table
  and is the primary API.
  - *Pros:* one object to pass around; natural home for query methods.
  - *Cons:* a second document model competing with `TextDoc`; the research explicitly
    warns against this until a runtime boundary requires it.

**Leaning: 2a, with a thin builder + lazy cache.** Build the node table once from
`TextDoc` (lazily, keyed to the immutable `source_text`), expose query/rollup methods over
it, and serialize to the JSON schema. No competing model.

## E3. Rollups: derived queries vs materialized indexes; values vs counts

The requirement is "values *or* counts, any scope, recursive, blocks + inline." The
unifying primitive is a **scoped, typed collection of nodes**; counts are `len`, values
are the nodes (each with span, text, attrs).

- **Option 3a — pure derived queries** (`collect(scope, kinds, recursive)` walks the node
  set each call).
  - *Pros:* maximally flexible and uncommitted (the request's "don't overly constrain");
    no stored counts; always current.
  - *Cons:* repeated walks; per-section re-walk cost (mitigated once the tree is cached).
- **Option 3b — materialized per-scope indexes** (precompute `dict[kind, list[node]]` per
  section/block).
  - *Pros:* O(1) repeated lookups.
  - *Cons:* stored derived state to invalidate; violates "no stored counts" in spirit;
    over-commits to particular rollups.
- **Option 3c — lazy-cached node table + on-demand queries (hybrid).** Cache the *node
  set* (expensive part: parse+walk) once; rollups are cheap queries/`Counter`s over it,
  optionally memoized.
  - *Pros:* flexible like 3a, fast like 3b, no premature commitment; "no stored counts"
    holds (counts are derived from the cached node set, not stored).
  - *Cons:* must document the source-text-immutability contract.

**Leaning: 3c.** A single query primitive returns nodes; counts/values/locations are all
read off the result. Example shape:

```
overview.collect(scope=Scope.section(s_id), kinds={NodeKind.table, NodeKind.link},
                 recursive=True) -> list[Node]        # values (each has .span/.text/.attrs)
overview.counts(scope=..., recursive=True) -> Counter[NodeKind]   # = Counter(n.kind for n in collect)
```

## E4. Inline items and block↔inline relationships

Inline items (links, code spans, images, emphasis…) are ranges inside a block, not
block-tree children. Two ways to relate them:

- **Option 4a — inline items are nodes in the same table**, with `parent` = containing
  block and a derived `section`/`sentence` association; block↔inline relationship is just
  parent/ancestor lookup and span containment.
  - *Pros:* one addressing scheme; "links in section 3" = scoped collect; relationships
    are graph edges already present (parent/ancestor, span-contains).
  - *Cons:* inline nodes may lack exact spans for some cases (reference links) — store
    `span=None` with identity, as `links()` already does.
- **Option 4b — inline items live only in a separate `links`/`inline` view**, related by
  storing block id on each.
  - *Pros:* keeps the block tree purely block-level.
  - *Cons:* a second addressing scheme; relationship queries become bespoke.

**Leaning: 4a.** Inline items are nodes (`kind` in an `inline` family) with `parent` block
and computed containing-sentence/section; this makes "recursively collect blocks **and**
inline item values, and the relationships between them" a single mechanism.

## E5. Levels of detail

A caller should choose how much to materialize/serialize. Options for the axis:

- **Option 5a — cumulative levels** (`STRUCTURE ⊂ INLINE ⊂ TEXT ⊂ ANALYSIS ⊂ FULL`): each
  level adds fields/layers.
  - *Pros:* simple to explain ("give me level 2"); predictable size growth.
  - *Cons:* coarse; a caller wanting only links must take everything up to that level.
- **Option 5b — feature flags** (include `text`, `inline`, `sentences`, `tokens`,
  `annotations`, `layout` independently).
  - *Pros:* precise; minimal payloads.
  - *Cons:* more combinations to test/document.
- **Option 5c — both:** named levels as presets over the underlying flags.
  - *Pros:* easy default ladder + precise control when needed.
  - *Cons:* slight surface duplication.

**Leaning: composable `include` layers (the flags of 5c, without a named ladder)** — same
mechanism-over-menu reasoning as the rollup surface (E3). Settled in DR-5.

## E6. Computation and caching

Carried from the tallies analysis and E2/E3: the node table derives from immutable
`source_text`.

- **Eager at parse:** rejected (pays even when unused; `blocks()` is opt-in).
- **Recompute each call:** simple but quadratic for per-section work.
- **Lazy-cached (leaning):** build the node table once on first structural access; views
  and rollups are cheap; `Section` work slices the cached tree instead of re-parsing.
  Safe because `source_text` is fixed; memoization is not a "stored count."

## E7. Coordinates, ids, stability (from research, low-controversy)

- **Coordinates:** canonical `source_span` in **Unicode code points** (matches Python
  `TextDoc`); optional derived `byte_span`/`utf16_span`/`line_column_span` for
  byte/browser consumers. Pin `offset_unit` in the schema.
- **Ids:** stable within a parse (`n_0001`…); the schema reserves an opaque `anchor` slot
  on annotation targets for a future CRDT/edit-edge id. Borrow the **red-green** idea
  (immutable node identity, position computed) conceptually; we do not need a full
  red-green implementation now.
- **Stability:** annotations (later) target node id **and** source span **and** text-quote,
  per W3C, so they survive a reparse.

## E8. Span references and annotation targeting (dual addressing)

One scheme must let a caller reference the document while **reading** (a source line/span),
while **editing in memory** (a parsed element — a table, a link — possibly via a bridged
editor model), while **saving** (source-grounded, since the original document is what
persists), and in **rendered output** (click a region → element → source). The pivotal
question is *what anchors a reference*, and which anchor is canonical for persistence.

- **Option 8a — source-span only.** A reference is just a `source_span` (+ maybe a quote).
  - *Pros:* trivially persistent and source-canonical; no per-parse identity to track;
    survives model rebuilds.
  - *Cons:* awkward to *create* against "the table node" or "this link" while editing the
    tree; brittle as a live handle under in-memory edits (offsets shift); rendered-UI
    selections must be span-mapped by hand.
- **Option 8b — node-id only.** A reference is a node `id` in the current model.
  - *Pros:* ergonomic in memory and in an editor bridge; O(1) lookup; natural for "annotate
    this table."
  - *Cons:* node ids are **per-parse / per-session transient** — not stable across reparse
    or reopen, so they **cannot** be the persisted canonical; a saved id is meaningless to
    the next parse.
- **Option 8c — multi-selector reference, source-canonical (recommended).** A reference
  carries coordinated selectors: a transient `node_id` (in-memory handle), the canonical
  `source_span`, a `text_quote` (prefix/exact/suffix for robustness), an optional
  reparse-stable structural path, and a reserved opaque `anchor` (future CRDT/editor edge).
  Resolution is asymmetric and total in the useful direction:
  - **model → source is total:** every node has a `source_span`, so attaching at the model
    level (table/link) *automatically* yields a source-grounded reference. This is exactly
    the request: "attach at the document-model level … allows us to also attach at the
    grounded original level."
  - **source → model is re-resolution:** after a (re)parse, find the node whose span
    matches/contains the reference; if the source moved, fall back to `text_quote` then the
    structural path. Robust, not guaranteed — which is why the *persisted* form keeps the
    source-grounded selectors, not the transient id.
  - *Pros:* one scheme for all four contexts; source stays canonical for save; tree stays
    ergonomic for edit; degrades gracefully after edits/reparses.
  - *Cons:* a small selector record to define and test; resolution rules to specify.

**Leaning: 8c.** It is the research's W3C multi-selector targeting made concrete, plus the
explicit **save = source-grounded / edit = tree-handle** split the request calls for.

Two consequences to design in:

- **Persistence rule.** On **save**, a reference is normalized to its source-grounded
  selectors (drop the transient `node_id`); the saved artifact is *original document +
  source-grounded annotations*. Future on-disk formats store annotations this way.
- **Editor-bridge round-trip.** When editing in memory (optionally bridged to a ProseMirror
  /block-JSON editor model), annotations attach to model nodes; on serialize they resolve
  to source spans and ride out through `DocGraph` to *original document + annotations
  that reference original-document structures*; on reopen, a reparse re-resolves them to
  nodes. Rendered HTML carries `data-node-id` / `data-source-span` so a UI selection maps
  back to a node and thence to source.

## E9. The layered-parsing lens (consolidating frame, 2026-05-30)

After the background research (see
[`research-2026-05-30-multilayer-parsing.md`](../../research/research-2026-05-30-multilayer-parsing.md)),
one framing makes the whole design cohere and shows how to extend it cleanly: the derived
views are not ad-hoc — each is **one parse layer** over the shared offset space. chopdiff
already parses the same `source_text` along several independent dimensions:

| Layer | Produces | Depends on |
| --- | --- | --- |
| **textual** | paragraphs, sentences, word tokens | — |
| **markdown** | block elements (recursive) + inline (links, code, emphasis) | — |
| **document** | section / heading hierarchy + TOC | markdown (headings) |
| **synthetic** | explicit `<div>`/`<span>` regions, chunk groupings (today's `TextNode`) | — |

This is **not a redesign** — it validates DR-1..DR-6 (a node table, not one tree, is exactly
what coexisting layers need) and reframes the settled views as layers. The key realizations:

- **A reference is a layer, not a pointer.** The `SpanRef`-targeted annotation layer (E8/D5)
  is the out-of-band layer; it anchors to the same offset space as the parsed layers.
- **Cross-layer relationships are offset-containment queries, not stored edges.** Within a
  layer, `parent`/`children`; across layers, interval containment/overlap ("which blocks are
  inside this `<div>`", "which section contains this link"). This is what makes overlap
  representable and future cross-layer edits tractable.
- **Each layer declares a nesting guarantee** — well-nested → a tree view (`blocks()`, the
  section tree); ordered-only → a sequential list view (`base_blocks()`, a flat annotation
  layer). This generalizes the §6 tree-vs-partition distinction to every layer.
- **Enablement is a configuration, not a fork.** Today's `TextNode`-as-separable-subsystem is
  simply "the synthetic layer enabled alone." The same model serves the cheap structural-only
  path and the full multi-layer analysis path; we never maintain two architectures.

**Four cheap "design-in-now" hooks** make the synthetic layer and future structural edits a
small lift later instead of a refactor; they are the entire delta this lens adds:

1. **A `layer` field on `Node`** (`Node{id, kind, layer, parent, children, source_span,
   attrs}`). Almost free in Phase 1; it is what lets the synthetic layer's nodes coexist by
   span rather than by fitting one tree.
2. **Offset-containment as a `collect()` mode** — interval containment/overlap so cross-layer
   queries work without re-parsing.
3. **A per-layer nesting guarantee** (tree vs ordered list), recorded on each layer.
4. **`SpanRef` as the anchor for edits too,** not just annotations — so the later structural
   operations attach to `SpanRef`s and survive reparse.

**Unified `Layer` vocabulary (settled 2026-05-30).** "Layer" now means a **parse dimension**
you can *enable* (build) and *include* (serialize): `textual`, `markdown`, `document`,
`synthetic`, and later `annotations`/`layout`. The earlier DR-5 enum members (`text`,
`inline`, `tokens`, derived coords) become **detail sub-options** of a layer (payload
richness), not top-level layers — one vocabulary instead of two. Enabling `document`
auto-enables `markdown` (its only dependency). This refines DR-5's *membership*, not its
mechanism (composable, no fixed ladder); see DR-5.

**Later by design, not now.** The **synthetic layer** (re-expressing `TextNode`/div parsing
as a layer keyed into the node table) and **cross-layer structural-edit operations**
(move/wrap/splice anchored on `SpanRef`, generalizing today's `div_insert_wrapped`) are named
later phases (Phases 3–4). The four hooks above ensure they drop in without reworking the
core — which is the whole point of getting the layered shape right now.

---

# Proposed design

This is the recommended synthesis (1b + 2a + 3c + 4a + 5c + lazy cache), to be confirmed
under "Decisions."

## D1. The `DocGraph` schema

A single JSON object, boring and parser-agnostic (no Marko/Python class names in stable
fields — those go in `metadata`). Shape (abbreviated; see the research JSON sketch):

```
DocGraph = {
  schema: "chopdiff.doc_graph.v1",
  source:  { format, offset_unit: "unicode_code_points", sha256, text? },
  nodes:   [ Node, ... ],            # the stable node set (block + inline families)
  views:   { toc, blocks, links, sentences, ... },   # arrays of node ids (projections)
  annotations: [],  layout: [],  provenance: []      # reserved typed layers (later)
}

Node = {
  id, kind, layer, role?, parent?, children: [id...],   # `layer` = parse dimension (E9)
  source_span: {start,end}?,         # code points; None for unlocatable inline (ref links)
  byte_span?, utf16_span?,           # optional derived coords
  attrs: { ... },                    # e.g. heading level, list ordered/tight, link url/title
  text?,                             # included only at TEXT/FULL detail
  metadata?: { ... }                 # parser specifics live here, never in stable fields
}
```

- The **containment tree** is `nodes` via `parent`/`children` from the `document` root —
  this is the "exact original structure" tree.
- The **section tree** is the `toc` view (heading nodes + nesting) — an overlay, since it
  cross-cuts block containment.
- **Inline items** are nodes whose `parent` is their block; `links` view indexes them.
- Every view is an array of ids → O(n) derivable, sharing identity.

## D2. Python projection and query API (over `TextDoc`)

A builder turns a `TextDoc` (+ its cached recursive block tree, sections, links) into the
node table, lazily and cached on the immutable source. Public surface (additive), kept
deliberately minimal — **one general query primitive, no blessed per-kind rollups** (DR-4):

- `TextDoc.graph(*, include=...) -> DocGraph` — build/serialize; `include` is a set of
  optional layers, default = structural core only (DR-5).
- **One query primitive**, at document / section / block scope:
  ```python
  collect(*, kinds=None, where=None, recursive=False, inline=False) -> list[Node]
  ```
  `kinds=` selects by node kind (typed, common case); `where=` is a `Node -> bool`
  predicate escape hatch for anything else; `recursive` descends into children; `inline`
  includes inline nodes. It returns **nodes** — each carrying `span`, `attrs`, and edges.
- **Values, counts, and groupings are standard Python over the result**, documented with
  clear examples, not separate methods:
  ```python
  dg.collect(kinds={NodeKind.table}, recursive=True)            # the tables (values + spans)
  len(dg.collect(kinds={NodeKind.table}, recursive=True))       # how many
  Counter(n.kind for n in dg.collect(recursive=True))           # tally by kind
  {k: list(g) for k, g in groupby(... )}                        # group as needed
  ```
- Scope handles: `dg` (document), `dg.section(id)`, `dg.node(id)`; each exposes `collect`,
  so rollups are uniform across scopes.
- Relationships are node edges, not a separate rollup: `node.parent`, `node.ancestors`,
  `node.section`, `node.sentence` (for inline). "links in section 3" =
  `dg.section(s3).collect(kinds={NodeKind.link}, recursive=True)`; pair with their block
  via `[(n, n.parent) for n in ...]`.

This makes the structural block tree fully recursive (containers populate children),
fixing the tallies gap: a table inside a blockquote or list item is a node and is found.
The existing v0.4.0 convenience accessors (`TextDoc.block_type_counts()`,
`Section.block_type_counts()`) are **superseded by `collect()`** and are removed when the
unified model lands (migration: `Counter(n.kind for n in dg.collect(...))`); this is a
semi-breaking change for the next minor.

## D3. Detail / payload control

`graph(*, include=..., detail=...)` controls what is built and serialized. **`include` is a
set of `Layer`s** — parse dimensions: `textual`, `markdown`, `document`, `synthetic`, later
`annotations`/`layout` (E9). The structural core (node table: ids, kinds, `layer`,
parent/children, `source_span`) is always present; each enabled layer adds its nodes/views.
There is **no fixed level ladder** (DR-5) — a caller composes exactly the layers they need;
enabling `document` auto-enables its dependency `markdown`:

```python
graph()                                       # default layers, structural core (small)
graph(include={Layer.markdown, Layer.document})           # blocks + sections
graph(include={Layer.markdown}, detail={Detail.text, Detail.inline})  # + node text + inline
```

**Payload richness within a layer is a small set of `detail` sub-options** (`text`,
`inline`, `tokens`, derived coords) — the former DR-5 enum members, now detail flags rather
than top-level layers (E9 unified vocabulary). Each layer/detail maps to a cleanly separable
part of the Pydantic model. Common compositions are shown in docs as *examples*, not blessed
presets; a downstream user who wants a preset defines their own `frozenset`. New parse
dimensions are one more `Layer`; new payload categories are one more `detail` — additive, no
refactor.

## D4. How the requirements are met

| Requirement | Mechanism |
| --- | --- |
| Rollups of values or counts, any time | one `collect()` over the node set; counts via `len`/`Counter` |
| Around blocks or whole document, by section | scope handles: document / `section(id)` / `node(id)` |
| Recursively collect blocks + inline + relationships | recursive `collect(inline=True)`; parent/section/sentence edges |
| Full recursive structure | fully-populated containment tree in `nodes` |
| Tree → exact structure or any rollup | containment tree view + rollup projections of one node set |
| Single serializable JSON for UIs | `DocGraph` schema, id-addressed, parser-agnostic |
| Optional levels of detail | composable `include` layers (no fixed ladder); default = core |
| Reference anything (source / element / rendered) | one `SpanRef` with coordinated selectors (D5) |
| Persist source-grounded; edit by tree | save normalizes to source selectors; in-memory uses `node_id` |

## D5. Span references (`SpanRef`), annotations, and persistence

A single small **`SpanRef`** type underlies all addressing (E8, 8c). Its design follows the
prior art surveyed in
[`research-2026-05-30-span-references.md`](../../research/research-2026-05-30-span-references.md)
(Chrome URL Text Fragments, W3C Web Annotation selectors, Hypothesis fuzzy anchoring,
RFC 5147) — see that brief for syntaxes, links, and full trade-offs.

```
SpanRef = {
  # Quoted span — CANONICAL, durable anchor (survives edits; Chrome-Text-Fragment shaped)
  exact: str,
  prefix?: str,        # ~32-128 chars of enclosing context, for uniqueness
  suffix?: str,
  # Syntactic span — exact within the current source; a recomputable HINT (code points)
  start?: int,
  end?: int,
  # node_id: in-memory handle only, NEVER persisted
}
Annotation = { id, kind, target: SpanRef, body, metadata? }
```

**Canonical = the quote; offset = a hint.** This is the key lesson from the research: every
mature system (W3C `oa:Choice`, Hypothesis) treats the **text quote (`exact`+`prefix`/
`suffix`) as the durable anchor** and **character offsets as accelerators**, because the
quote survives restructuring and is fuzzy-matchable while offsets shift on any earlier
edit. Within one parse the offset is exact (chopdiff retains `source_text`), so it is the
fast path; across edits the quote is what recovers the target.

### Syntactic (offset) vs quoted (prefix/suffix) matching — trade-offs

| | Syntactic offset span (`start`/`end`) | Quoted span (`exact`+`prefix`/`suffix`) |
| --- | --- | --- |
| Robust to edits elsewhere | ✘ shifts | ✅ survives |
| Disambiguation of repeats | ✅ exact position | ✅ via prefix/suffix (✘ exact-only) |
| Cost / compactness | ✅ two ints | proportional to quote + context |
| Browser/Text-Fragment shaped | ✘ (no offsets in `#:~:text=`) | ✅ maps directly |
| Sub-word / code targets | ✅ | ✘ (Text Fragments are word-boundary, case-insensitive) |

So we keep **both**: offsets for exact, cheap, in-parse addressing; the quote for durable,
portable, edit-surviving references. (Compare RFC 5147 `#char=`/`#line=` with `;md5=`
integrity — offset + change-detection but no recovery — vs the quote's fuzzy recovery.)

### Rules

- **model → source is total.** Building a `SpanRef` from any node fills both the offset
  (the node's `source_span`) and the quote (sliced from source + context), so attaching at
  the model level (table, link) is automatically grounded in the original source.
- **source → model is re-resolution.** Fast path: if the text at `start:end` still equals
  `exact`, accept. Else fuzzy re-anchor via `exact`+`prefix`/`suffix` (offset as a search
  hint, then full document), and update `start`/`end`. (Mirrors Hypothesis' strategy.)
- **Persistence is quote-canonical and source-grounded.** Saving keeps the quote (durable)
  and drops the transient `node_id`; offsets persist only as hints. The saved artifact is
  the **original document plus source-grounded annotations**.
- **Chrome Text Fragment** export is a lossy projection of the quote
  (`#:~:text=[prefix-,]exact[,-suffix]`): prose only, word-boundary, case-insensitive;
  truncate context for URL length. The directive is generated on demand, never stored.
- **Rendered output references back.** HTML/render helpers emit `data-node-id` and
  `data-source-span` so a click/selection resolves to a node and thence to source.
- **Offset unit is Unicode code points** (Python-native); provide a UTF-16 conversion for
  JS interop (the W3C position-selector unit ambiguity is a known cross-language footgun).
- **Deferred (not in v1):** an XPath/DOM `structural_path` (environment-specific) and an
  opaque CRDT `anchor` slot — added only if a concrete need appears.

Annotations are a **stand-off layer** (the research's conceptual core): parsed structure
(sections, blocks, links) and added structure (summaries, notes, rewrite suggestions) are
the same kind of thing — typed layers of `SpanRef`-targeted records. **Building the
annotation layer is a later phase**, and we expect to **revisit and refine it** (and
possibly `SpanRef` itself) once v1 is in use; this plan only fixes the `SpanRef` contract
and resolution rules now so the node model, schema, and editor bridge are designed around
it. v1 is at least as expressive as a Chrome-style `exact`+`prefix`/`suffix` selector,
which is the agreed floor.

Worked use case (read → edit → save): open a Markdown doc; build the in-memory model
(optionally bridged to an editor); a user/AI annotates the parsed table and a link (model
nodes); on save, the `SpanRef`s persist quote-canonical and serialize as *original Markdown
+ source-grounded annotations*; reopening reparses and re-resolves them to nodes (fast path
when unchanged, fuzzy re-anchor when edited).

## Decisions (all settled)

Summary index; rationale and consequences are in the Decision Record below.

1. **Node set vs single tree (E1).** ✅ **SETTLED (2026-05-29): node-table-with-views
   (1b).** A stable node table (id + span) is canonical; the containment tree, section
   tree, block list, and inline index are derived views, and the JSON presents a
   `document` root with children as its top-level shape. Container children are fully
   populated (a table inside a blockquote/list item is a node), with top-level `blocks()`
   shape preserved and a `recursive` opt-in for traversal/rollups. See the Decision Record
   and the archived [tallies note](../archive/plan-2026-05-29-multilevel-block-tallies.md)
   axis A.
2. **Projection vs runtime object (E2).** ✅ **SETTLED (2026-05-29): projection (2a).**
   `DocGraph` is a derived projection/contract built from `TextDoc` (the Python core),
   not a competing editable runtime model. It may be a rich value with query methods, but
   source text / `TextDoc` stays canonical; edits go through `TextDoc`/source and
   re-derive. See the Decision Record.
3. **Rollup surface (E3/E4).** ✅ **SETTLED (2026-05-29): Option B — one general query
   primitive, no blessed shortcuts.** A single `collect(*, kinds=, where=, recursive=,
   inline=)` over the node set, at doc/section/block scope; counts/values/groupings are
   standard Python (`len`/`Counter`/comprehensions) documented with clear examples. Inline
   items are nodes (4a); relationships are node edges. No per-kind rollup methods, to keep
   the embeddable library's surface small. See DR-4.
4. **Detail axis (E5).** ✅ **SETTLED (2026-05-29; vocabulary unified 2026-05-30): Option B
   — composable layers, no fixed ladder.** `include` selects which `Layer`s (parse
   dimensions: `textual`/`markdown`/`document`/`synthetic`/…) to build and serialize;
   `detail` sub-options (`text`/`inline`/`tokens`/coords) control payload richness. Default
   = structural core; presets are caller-defined, not blessed. Same simplicity+flexibility
   principle as DR-4. See DR-5 and E9.
5. **Schema versioning home.** ✅ **SETTLED (2026-05-29): Pydantic as the authoring layer.**
   The `DocGraph` schema is authored as Pydantic models (single source of truth), which
   emit a JSON Schema; a standalone language-neutral artifact (JSON Schema, or a
   TypeScript/Zod mirror) is formalized later once the shape stabilizes. See DR-3.
6. **Scope of phase 1.** ✅ **SETTLED (2026-05-29): minimal slice.** Phase 1 is the
   recursive node model + `collect()` + `SpanRef` contract; annotations, operations,
   provenance, and layout are schema-reserved and built in later phases.
7. **Span-reference selector set (`SpanRef`) (E8/D5).** ✅ **SETTLED (2026-05-30): `SpanRef`
   carries a quoted span (`exact`+`prefix`/`suffix`, the canonical durable anchor) and an
   offset span (`start`/`end`, code points, a recomputable hint); quote-canonical
   persistence; Chrome-Text-Fragment convertible; `node_id` never persisted; `structural_path`
   and CRDT `anchor` deferred.** Informed by
   [`research-2026-05-30-span-references.md`](../../research/research-2026-05-30-span-references.md).
   See DR-6.
8. **Computation/caching (E6).** ✅ **SETTLED (2026-05-29): lazy-cache** the node table off
   the immutable `source_text` (also fixes the quadratic per-section `Section.blocks()`
   re-parse). Memoization of a derived view is not a "stored count"; the contract is "do
   not reassign `source_text` after parse." Already de-risked by the robustness Phase-1
   `sub_doc`/`sub_paras` copy fix.
9. **List-item paragraph counting.** ✅ **SETTLED (2026-05-29): count it.** The wrapper
   `Paragraph` inside each list item is counted as a `paragraph`; it is density-invariant
   (tight and loose items both wrap), and excluding it would be a special case.

## Decision record

### DR-1 — Canonical structure: node table with derived views (settles Open decision 1)

**Decision (2026-05-29):** Store the document structure as a **stable node table**
(`Node{id, kind, parent, children, source_span, attrs}`) covering blocks, inline items,
and headings. The block containment tree, section tree, block list, link index, and token
stream are **derived views** (arrays of node ids / filters), not the canonical store. The
serialized JSON presents a `document` root with `children` as its top-level shape, so the
tree remains a first-class view.

**Why:** chopdiff has several hierarchies that overlap and do not nest — a section spans
sibling blocks and is not a subtree of the block tree; links are inline ranges;
annotations target arbitrary spans. A single canonical tree privileges one hierarchy and
forces every other structure to be a bespoke overlay with its own addressing. A node table
gives one id space for blocks *and* inline items, makes overlapping layers and "zoom =
pick a view + level" cheap O(n) projections, and serializes to the flat, id-addressed JSON
frontends want. (A single tree would have sufficed for analysis-only counts/slices, but
not for annotations, the dual source/tree `SpanRef` model, or UI serialization.)

**Consequences:** a node-table builder to write and test; discipline on id stability and
span units (Unicode code points, decision 7/E7); container children become populated
(additive to `Block.children`, noted in the changelog). Over-modeling is bounded by the
minimal Phase-1 scope (decision 6).

### DR-2 — `DocGraph` is a projection of `TextDoc`, not a runtime model (settles Open decision 2)

**Decision (2026-05-29):** `DocGraph` is a **derived projection / serialized contract**
built from `TextDoc` (the Python core). It may be returned as a rich value with
a `collect()` query method, but it is **read-mostly and not canonical**: source
text / `TextDoc` is the source of truth, and edits go through `TextDoc`/source and
re-derive. No competing editable runtime document model.

**Why:** keeping source canonical avoids the central failure mode — a rich in-memory model
drifting away from the actual Markdown (the ProseMirror/CRDT trap, where Markdown becomes
secondary). It minimizes new public surface, reuses `TextDoc`'s spans/sections/links/size
machinery, and keeps `DocGraph` honest as a cross-language contract (Python and a future
TS client are both implementations of one schema). A first-class runtime object is
reserved for the day a genuine runtime boundary (e.g. live collaborative editing) requires
it.

**Consequences:** query/rollup methods live on the small derived object `graph()`
returns (not bloating `TextDoc`); the projection is lazily cached off the immutable
`source_text` (decision 8), so the operative contract is "do not reassign `source_text`
after parse." Editing is "edit `TextDoc`/source, then re-derive," with the editor edge
bridging through the `SpanRef` model (E8/D5).

### DR-3 — Schema authoring layer: Pydantic now, formal schema later (settles Open decision 5)

**Decision (2026-05-29):** Author the `DocGraph` schema as **Pydantic models** — the
single source of truth in Python — which also emit a JSON Schema. A standalone
language-neutral artifact (formal JSON Schema, or a TypeScript/Zod mirror for clients) is
derived and frozen later, once the shape stabilizes against real use cases.

**Why:** fastest to build and validate against `TextDoc`; Pydantic gives validation plus
JSON-Schema export for free; avoids prematurely freezing a hand-written schema before use
cases prove the shape. The model ≠ format separation (research) holds: the Pydantic models
*are* the authored contract; JSON Schema and Zod are projections of it.

**Consequences:** keep parser-internal fields out of the stable models (in `metadata`);
pin `offset_unit` (Unicode code points); when the shape stabilizes, publish the emitted
JSON Schema as the cross-language artifact and consider a Zod mirror for TS clients.

### DR-4 — Rollup surface: one general query primitive, no blessed shortcuts (settles Open decision 3)

**Decision (2026-05-29):** Provide a **single general query primitive** —
`collect(*, kinds=, where=, recursive=, inline=)` over the node set at doc/section/block
scope — and **no per-kind rollup methods**. Values are the returned nodes; counts and
groupings are standard Python (`len`, `Counter`, comprehensions), documented with clear
worked examples. Relationships are node edges (`parent`/`section`/`sentence`), not a
separate API.

**Why:** chopdiff is a low-level library embedded in other programs. A fixed menu of
"blessed" rollups (`tables()`, `code_blocks()`, …) is combinatorial (kind × scope ×
recursive × values/counts × inline), can't cover ad-hoc queries, and grows the surface to
design, version, and maintain. One primitive with a `kinds=` selector plus a `where=`
predicate escape hatch is maximally flexible, has a tiny stable surface, and keeps "no
stored counts" by construction. The maintenance cost of shortcuts of uncertain value is
not worth embedding in a low-level dependency.

**Consequences:** discoverability rests on clear docs and worked examples (the
`examples/normalized_form.py` pattern) rather than autocomplete; the v0.4.0
`block_type_counts()` accessors are superseded by `collect()` and removed in the next minor
(migration documented). Add named conveniences later only if docs/usage prove a specific
one is broadly needed.

### DR-5 — Detail/payload control: composable `include` layers, no fixed ladder (settles Open decision 4)

**Decision (2026-05-29; vocabulary unified 2026-05-30, E9):** Control what is built and
serialized with two composable axes: **`include` = a set of `Layer`s** (parse dimensions:
`textual`, `markdown`, `document`, `synthetic`, later `annotations`/`layout`) and **`detail`
= payload sub-options** (`text`, `inline`, `tokens`, derived coords). The structural core
(node table + `layer` + spans) is always present; everything else is opt-in. **No fixed
`OUTLINE/BLOCKS/INLINE/FULL` ladder.** Presets are caller-defined `frozenset`, documented as
examples, not blessed constants. (Originally the `Layer` enum mixed parse dimensions and
payload detail; E9 split them into `Layer` + `detail` for one consistent vocabulary — a
membership refinement, not a mechanism change.)

**Why:** same simplicity+flexibility principle as DR-4, applied to the payload axis. A
fixed cumulative ladder is coarse (can't ask for "blocks + links but no text") and a new
downstream combination forces inserting a level — a breaking, refactor-inducing change.
Orthogonal flags give any combination with a small, stable surface; new data categories are
one additive `Layer`. This is a document model meant to serve many situations without being
updated each time.

**Consequences:** keep the default small and useful (core only); each `Layer` maps to a
cleanly separable part of the Pydantic models so "include or not" is a clean per-layer
toggle; testing is linear (per layer), not combinatorial; document common compositions as
examples.

### DR-6 — Span references: `SpanRef` (quote canonical + offset hint) (settles Open decision 7)

**Decision (2026-05-30):** A small **`SpanRef`** type carries two coordinated span kinds:
a **quoted span** (`exact` + optional `prefix`/`suffix`)
that is the **canonical durable anchor**, and an **offset span** (`start`/`end` in Unicode
code points) that is a **recomputable hint**. Persistence is quote-canonical and
source-grounded; `node_id` is an in-memory handle only and is never persisted. The quote is
shaped to be **convertible to/from a Chrome URL Text Fragment** (lossy: prose,
word-boundary, case-insensitive). A reparse-stable `structural_path` and a CRDT `anchor`
slot are **deferred** until a concrete need appears. Full shape, rules, and the
syntactic-vs-quoted trade-off table are in D5.

**Why:** the surveyed prior art (see
[`research-2026-05-30-span-references.md`](../../research/research-2026-05-30-span-references.md):
Chrome Text Fragments, W3C Web Annotation `TextQuoteSelector`/`TextPositionSelector` +
`oa:Choice`, Hypothesis fuzzy anchoring, RFC 5147) converges on storing the **text quote as
the durable anchor with positions as accelerators** — quotes survive edits and re-anchor
fuzzily; offsets shift. Carrying both gives exact cheap in-parse addressing *and*
edit-surviving, browser-portable references, with one source-canonical form.

**Consequences:** Phase 1 ships the `SpanRef` contract + exact (fast-path) resolution; the
fuzzy re-anchor and the Chrome Text Fragment export are wired behind it (fuzzy path may be
stubbed first). The **annotation layer is a later phase and is expected to be revisited and
refined** once v1 is in use — `SpanRef` v1 is deliberately scoped to the Chrome-style
`exact`+`prefix`/`suffix` floor, accepting later enhancement.

## Implementation plan

All decisions are settled, so we **update the design of record first** (Phase 0) and then
implement against it, keeping `docs/textdoc-spec.md` the single current, comprehensive,
concise design doc for the document model.

### Phase 0: make `docs/textdoc-spec.md` current (do first)

Fold the settled DocGraph design into the design of record before writing code, so the
implementation is built against current docs. The DocGraph/`collect`/`SpanRef` edits are
applied; the E9 layer-concept edits are the remaining Phase-0 work (see "Design-of-record
updates" below for the per-section detail):

- [x] §3 normalized form: canonical normalized form is the **node table**; `TextDoc` is the
      Python core/editing view, `DocGraph` the derived projection/contract (DR-1, DR-2).
- [x] §6 structural tree: containers fully populate children (recursive); the block tree is
      a derived view; density-invariant.
- [x] §8 inline: inline items are nodes; links via `collect(kinds={link})`.
- [x] §9 derived views: the single `collect()` primitive (DR-4) replaces
      `block_type_counts()`; composable `include` layers (DR-5); drop "top-level only".
- [x] New section: **DocGraph** node model + JSON schema (Pydantic authoring, views,
      layers, coordinates = Unicode code points), and **`SpanRef`** + the (later) annotation
      stand-off layer (DR-3, DR-6).
- [x] §11 invariants: node-id stability within a parse; quote-canonical references; no
      blessed rollups/levels. §12: add the span-references research brief.
- [x] **E9 layer concept:** §3/§4 introduce the four parse **layers** + the `layer` field on
      `Node` + the dependency DAG; cross-layer relationships are **offset-containment**
      queries; each layer has a **nesting guarantee** (tree vs ordered list). §10 unify the
      `Layer` vocabulary (parse dimensions) + `detail` sub-options. §13 note the synthetic
      layer / cross-layer edits are later phases (not "replace `TextNode`"). §15 add the
      multilayer brief.

### Phase 1: recursive node model + flexible rollups (Python)

- [ ] Make the structural block tree fully recursive (containers populate block children);
      keep top-level `blocks()` shape, add deep traversal. Density-invariant preserved.
- [ ] Add `base_blocks(*, item_partition_depth=6)` — the flat, depth-annotated **sequential block
      list** (partition). `item_partition_depth` controls list decomposition (default 6; `-1`
      unlimited; `0` lists unsplit); blockquotes always atomic. Invariant: ordered,
      non-overlapping, complete cover whose reassembly reproduces the document (exact except
      normalized paragraph-break whitespace; exact via offsets). A base block is a block
      node; the base-block *list* is the partition. (textdoc-spec §6.)
- [ ] Model inline items as nodes with `parent` block and computed `section`/`sentence`.
- [ ] **Tag every node with its `layer`** (textual / markdown / document) and record each
      layer's **nesting guarantee** (tree vs ordered list). Reserve the `synthetic` layer
      (not built in Phase 1). (E9 hooks 1 and 3 — cheap now, enables Phases 3–4.)
- [ ] Lazy-cache the node table on the immutable `source_text`; make `Section.blocks()`
      slice the cached tree (remove per-section reparse).
- [ ] Add the single `collect(*, kinds=, where=, recursive=, inline=)` query primitive
      with document / section / block scope handles, **including an offset-containment mode
      for cross-layer queries** (E9 hook 2). No per-kind rollup methods (DR-4).
- [ ] Define the `SpanRef` type and resolution: `SpanRef.from_node(node)` (total
      model→source), `resolve(span_ref, doc)` (source→model: exact fast path, then quote fuzzy re-anchor),
      and `to_persisted()` (drop transient `node_id`). `SpanRef` is the anchor for edits too,
      not just annotations (E9 hook 4). No annotation *storage* yet — just the targeting
      contract the rest of the model is designed around.
- [ ] Tests: nested tables/code in blockquotes and list items are counted and locatable;
      per-section value+count rollups; density invariance; section slicing; `SpanRef`
      round-trips (node → source-grounded → re-resolved node) and survives a reparse.

### Phase 2: `DocGraph` serialization + detail levels

- [ ] Pydantic/dataclass models for the schema (nodes, views, source, reserved
      `annotations` layer with the `SpanRef` target shape); `offset_unit` pinned to
      Unicode code points; optional derived coords.
- [ ] `TextDoc.graph(*, include=…)` builder + `Layer` set (no ladder); render helpers emit
      `data-node-id` / `data-source-span` so rendered selections resolve back to source.
- [ ] Round-trip + golden tests; a tiny UI fixture is out of scope here (later phase).
- [ ] Author the standalone language-neutral JSON Schema once the shape is confirmed
      (decision 5).

### Phase 3 (later): the synthetic layer

Re-express the existing `<div>`/`<span>` structural parsing (`TextNode`, `parse_divs`,
chunking) as the **synthetic layer** keyed into the shared node table — reconciling the two
structural models the codebase has today (marko block model vs the `TextNode` div parser).
Deferred by design (E9): not needed to ship the core, and the Phase-1 hooks (`layer` field,
offset-containment `collect()`) make it additive rather than a rewrite.

- [ ] Map `parse_divs`/`TextNode` output into `Node`s tagged `layer=synthetic`, keeping
      exact offsets; the existing parser can back it (no new dependency).
- [ ] Synthetic nodes coexist with markdown/textual nodes by span; cross-layer queries
      ("which markdown blocks are inside this `<div class="chunk">`") via offset-containment.
- [ ] In-band metadata (`<span data-timestamp>`) becomes a synthetic-layer node that can
      emit a `SpanRef` for free — unifying in-band and out-of-band (annotation-layer) metadata.

### Phase 4 (later): cross-layer structural edits + stand-off layers

The eventual payoff: **structural-edit operations anchored on `SpanRef` that work uniformly
across layers**, generalizing today's synthetic-structure edits (`div_insert_wrapped`,
wrap/splice). Plus the built-out `annotations` (stand-off), `operation`/`provenance`, and
`layout` layers the schema reserves.

- [ ] Operation records (move section, wrap region, replace block, splice) that resolve
      targets via `SpanRef`, apply to source, re-derive, and validate (reparse + token diff).
- [ ] The `annotations` stand-off layer (built on the Phase-1 `SpanRef` contract); revisit
      and refine `SpanRef`/annotations once v1 is in use, as DR-6 anticipates.
- [ ] `provenance` (source-map-style generated↔original) and `layout` overlays as needed.

## Design-of-record updates (`docs/textdoc-spec.md`)

Phase 0 makes `docs/textdoc-spec.md` the single current, comprehensive, concise design doc.
Per-section edits (the design doc carries the prose; this maps what changes):

- **§1 Purpose / §2 Goals** — add that the serialized normalized-form contract is
  `DocGraph` (language-neutral, frontend-serializable); `TextDoc` is the Python core.
  Goals add: cross-language JSON contract, source-canonical references, simplicity +
  flexibility (one query primitive, composable layers — no blessed menus).
- **§3 The normalized form** — the **node table is canonical**; the block tree, section
  tree, inline index, and token stream are derived views; `DocGraph` is the projection
  of `TextDoc` (DR-1, DR-2). **Introduce the four parse layers** (textual / markdown /
  document / synthetic) — the views *are* layer views — with the dependency DAG (document →
  markdown) and **offset-containment as the cross-layer relationship** (E9).
- **§4 Core types and offsets** — define `Node{id, kind, layer, parent, children,
  source_span, attrs}` (the `layer` field, E9); node ids stable within a parse; each layer
  carries a **nesting guarantee** (tree vs ordered list); **pin the offset unit to Unicode
  code points** with byte/UTF-16 conversions as derived coords.
- **§5 Block-type model** — note containers (blockquote, list item) fully populate block
  children; `ordered_list` already present.
- **§6 Block views** — terminology (*block element*/*inline* vs *block node* vs *base
  block*); the recursive structural tree (containers fully populate children;
  density-invariant) **and** the flat `base_blocks()` sequential partition (ordered,
  non-overlapping, complete cover; depth-annotated; reassembly reproduces the document); the
  query-vs-partition distinction.
- **§7 Sections and TOC** — section is a view; `Section`-scoped `collect()` for per-section
  slices/rollups.
- **§8 Inline elements and links** — inline items are first-class nodes; links are
  `collect(kinds={link})`; block↔inline relationships are node edges.
- **§9 Derived views and rollups** — replace the "top-level only / planned" status with the
  settled single `collect(*, kinds=, where=, recursive=, inline=)` primitive (DR-4);
  counts/values via standard Python; **remove `block_type_counts()`** (superseded; migration
  note); payload via composable `include` layers (DR-5).
- **New section — DocGraph schema** — node table + views + reserved layers; Pydantic
  authoring (DR-3); **unified `Layer` vocabulary** (parse dimensions) + `detail` sub-options
  (E9); coordinates.
- **§13 invariants/non-goals** — refine "replacing `TextNode`" non-goal: `TextNode` stays;
  **expressing it as the synthetic layer (Phase 3) and cross-layer structural edits (Phase
  4) are later phases**, not non-goals. Cross-layer relations are offset-containment, never
  stored cross-layer edges.
- **New section — `SpanRef` and annotations** — the span-reference type (quote canonical +
  offset hint; Chrome-Text-Fragment convertible; DR-6); the stand-off annotation layer as a
  later phase expected to be refined.
- **§10 Editing and serialization** — `DocGraph` serialization with `include` layers;
  edit `TextDoc`/source then re-derive; rendered `data-node-id`/`data-source-span`.
- **§11 Invariants and non-goals** — node-id stability within a parse; quote-canonical
  references; no blessed rollups/levels; offset unit pinned. Non-goals: no parallel runtime
  model, no DOM/XPath selectors, annotations/operations/provenance/layout are later.
- **§12 References** — add `research-2026-05-30-span-references.md`,
  `research-2026-05-30-multilayer-parsing.md`, the document-model survey, and this plan.

When Phase 0 lands, the `block_type_counts()` removal is the one semi-breaking changelog
item (migration: `Counter(n.kind for n in doc.graph().collect(...))`).

## Testing Strategy

- Recursive tallies: a document with tables/code nested in blockquotes and list items
  yields correct counts *and* locations at document, section, and block scope.
- Density invariance: tight vs loose lists give identical structural rollups.
- Section slicing: every view/rollup scoped to a section matches a whole-document filter
  restricted to that section's span; spans stay within `section.span`.
- Serialization: `DocGraph` round-trips; ids are stable within a parse; stable
  fields contain no parser-internal names; `include` layers compose (including a layer adds
  only its part; the structural core is always present).
- Coordinates: `source_span` round-trips against `source_text`; derived byte/UTF-16 spans
  agree on ASCII and a multi-byte sample.
- Span references: a `SpanRef` built from a node carries the node's `source_span`; persisting
  drops `node_id`; after a no-op reparse it re-resolves to the same node; after an edit
  that shifts offsets, `text_quote` still re-resolves it. An annotation created against a
  parsed table/link serializes with a source-grounded target.

## Relationship to other specs

- **Subsumes** the archived
  [`plan-2026-05-29-multilevel-block-tallies.md`](../archive/plan-2026-05-29-multilevel-block-tallies.md)
  (multi-level tallies = the rollup feature of phase 1; kept in `archive/` for its detailed
  nested-block/caching axis analysis).
- **Updates `docs/textdoc-spec.md`** (the design of record) **first**, in Phase 0 — see
  "Design-of-record updates" — so implementation is built against current docs.
- Independent of `plan-2026-05-26-robustness-hardening.md`.

* * *

*This document follows the tbd [writing style guidelines](https://github.com/jlevy/tbd).*
