# Feature: A flexible unified document model (DocumentOverview)

**Date:** 2026-05-29 (last updated 2026-05-29)

**Author:** chopdiff maintainers

**Status:** Draft — exploratory. This document first walks through approaches and
trade-offs ("Exploration"), then proposes a clean design ("Proposed design"). The pivotal
choices are listed in "Open decisions" and are **not yet settled**.

> **Inputs:** the survey in
> [`research-2026-05-29-document-model.md`](../../research/research-2026-05-29-document-model.md)
> (read it first — this plan operationalizes its recommended direction) and the design of
> record [`docs/textdoc-spec.md`](../../../textdoc-spec.md). This plan **subsumes**
> [`plan-2026-05-29-multilevel-block-tallies.md`](plan-2026-05-29-multilevel-block-tallies.md):
> multi-level tallies become one feature of the unified model.

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
**`DocumentOverview`** is the serialized, language-neutral projection.

## Goals

- One **unified JSON schema** (`DocumentOverview`) for the fully processed document,
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
  explicit: extend `TextDoc`; `DocumentOverview` is a projection/contract).
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

---

# Exploration

Each subsection states the question, the realistic options, pros/cons, and a leaning. None
is final until "Open decisions" is settled.

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

- **Option 2a — `DocumentOverview` is purely a serialized projection** built on demand
  from `TextDoc` (+ its block tree, sections, links). No new long-lived runtime object;
  `TextDoc` stays the core.
  - *Pros:* matches the research ("extend TextDoc; DocumentOverview is the contract"); no
    parallel model to keep in sync; reuses spans/sections/links already built.
  - *Cons:* the projection logic lives somewhere (a builder); repeated builds cost unless
    cached.
- **Option 2b — a first-class `DocumentOverview` runtime object** that owns the node table
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

**Leaning: 5c.** A small `Detail` ladder (`OUTLINE`, `BLOCKS`, `INLINE`, `FULL`) backed by
explicit include-flags. `OUTLINE` = section tree + counts only (tiny); `FULL` = everything
including text and (later) annotations.

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

---

# Proposed design

This is the recommended synthesis (1b + 2a + 3c + 4a + 5c + lazy cache), to be confirmed
in "Open decisions."

## D1. The `DocumentOverview` schema

A single JSON object, boring and parser-agnostic (no Marko/Python class names in stable
fields — those go in `metadata`). Shape (abbreviated; see the research JSON sketch):

```
DocumentOverview = {
  schema: "chopdiff.document_overview.v1",
  source:  { format, offset_unit: "unicode_code_points", sha256, text? },
  nodes:   [ Node, ... ],            # the stable node set (block + inline families)
  views:   { toc, blocks, links, sentences, ... },   # arrays of node ids (projections)
  annotations: [],  layout: [],  provenance: []      # reserved typed layers (later)
}

Node = {
  id, kind, role?, parent?, children: [id...],
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
node table, lazily and cached on the immutable source. Public surface (additive):

- `TextDoc.overview(detail=Detail.BLOCKS) -> DocumentOverview` — build/serialize.
- Query primitive (works at doc, section, or block scope):
  - `collect(*, kinds=None, recursive=False, inline=False) -> list[Node]` (values)
  - `counts(*, recursive=False, inline=False) -> Counter[NodeKind]` (counts)
  - `index(*, recursive=False) -> dict[NodeKind, list[Node]]` (values + locations + counts)
- Scope handles: `overview` (document), `overview.section(id)`, `overview.node(id)`; each
  exposes the same three methods, so rollups are uniform across scopes.
- Relationships: `node.parent`, `node.ancestors`, `node.section`, `node.sentence` (for
  inline), all by id; "links in section 3" = `overview.section(s3).collect(kinds={link},
  recursive=True)`.

This makes the structural block tree fully recursive (containers populate children),
fixing the tallies gap: a table inside a blockquote or list item is a node and is counted.

## D3. Detail levels

`Detail.OUTLINE` (sections + counts) ⊂ `BLOCKS` (+ block nodes/spans) ⊂ `INLINE` (+ inline
nodes) ⊂ `FULL` (+ `text`, sentences/tokens, and reserved layers). Backed by independent
include-flags (`text`, `sentences`, `tokens`, `annotations`, `layout`) for precise control.

## D4. How the requirements are met

| Requirement | Mechanism |
| --- | --- |
| Rollups of values or counts, any time | `collect` / `counts` / `index` over the node set |
| Around blocks or whole document, by section | scope handles: document / `section(id)` / `node(id)` |
| Recursively collect blocks + inline + relationships | recursive `collect(inline=True)`; parent/section/sentence edges |
| Full recursive structure | fully-populated containment tree in `nodes` |
| Tree → exact structure or any rollup | containment tree view + rollup projections of one node set |
| Single serializable JSON for UIs | `DocumentOverview` schema, id-addressed, parser-agnostic |
| Optional levels of detail | `Detail` ladder + include-flags |

## Open decisions

1. **Node set vs single tree (E1).** Adopt the node-table-with-views (1b) with the
   containment tree as the top-level JSON shape? (Recommended.)
2. **Projection vs runtime object (E2).** `DocumentOverview` as a built projection over
   `TextDoc` (2a), no competing runtime model? (Recommended.)
3. **Rollup surface (E3/E4).** One `collect/counts/index` primitive with scope handles, and
   inline items as nodes (4a)? Or keep block-only rollups + a separate link index?
4. **Detail axis (E5).** Cumulative `Detail` ladder backed by flags (5c)?
5. **Schema versioning home.** Do we author the language-neutral JSON Schema artifact now
   (research Option G) or start with Pydantic models that emit the schema and add the
   standalone JSON Schema once the shape stabilizes?
6. **Scope of phase 1.** Smallest useful slice (see plan) — confirm it excludes
   annotations/operations/provenance/layout (schema-reserved, built later).

## Implementation plan

Kept to two phases; phase 1 is the useful core, phase 2 is serialization polish. (No work
starts until "Open decisions" is settled.)

### Phase 1: recursive node model + flexible rollups (Python)

- [ ] Make the structural block tree fully recursive (containers populate block children);
      keep top-level `blocks()` shape, add deep traversal. Density-invariant preserved.
- [ ] Model inline items as nodes with `parent` block and computed `section`/`sentence`.
- [ ] Lazy-cache the node table on the immutable `source_text`; make `Section.blocks()`
      slice the cached tree (remove per-section reparse).
- [ ] Add the `collect` / `counts` / `index` query primitive with document / section /
      block scope handles; recursive and inline options.
- [ ] Tests: nested tables/code in blockquotes and list items are counted and locatable;
      per-section value+count rollups; density invariance; section slicing.

### Phase 2: `DocumentOverview` serialization + detail levels

- [ ] Pydantic/dataclass models for the schema (nodes, views, source, reserved layers);
      `offset_unit` pinned to Unicode code points; optional derived coords.
- [ ] `TextDoc.overview(detail=…)` builder + `Detail` ladder/flags.
- [ ] Round-trip + golden tests; a tiny UI fixture is out of scope here (later phase).
- [ ] Author the standalone language-neutral JSON Schema once the shape is confirmed
      (decision 5).

## Testing Strategy

- Recursive tallies: a document with tables/code nested in blockquotes and list items
  yields correct counts *and* locations at document, section, and block scope.
- Density invariance: tight vs loose lists give identical structural rollups.
- Section slicing: every view/rollup scoped to a section matches a whole-document filter
  restricted to that section's span; spans stay within `section.span`.
- Serialization: `DocumentOverview` round-trips; ids are stable within a parse; stable
  fields contain no parser-internal names; detail levels are subset-consistent
  (`OUTLINE ⊂ BLOCKS ⊂ INLINE ⊂ FULL`).
- Coordinates: `source_span` round-trips against `source_text`; derived byte/UTF-16 spans
  agree on ASCII and a multi-byte sample.

## Relationship to other specs

- **Subsumes** `plan-2026-05-29-multilevel-block-tallies.md` (multi-level tallies = the
  rollup feature of phase 1). That spec will be archived as folded-in once this is
  approved.
- **Extends** `docs/textdoc-spec.md` §6/§9 (structural tree + derived views); the design of
  record is updated when phase 1 lands.
- Independent of `plan-2026-05-26-robustness-hardening.md`.

* * *

*This document follows the tbd [writing style guidelines](https://github.com/jlevy/tbd).*
