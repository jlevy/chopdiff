# Feature: Document-Model Documentation and Design Refinements

**Date:** 2026-05-31 (last updated 2026-05-31)

**Author:** Joshua Levy

**Status:** Implemented

## Overview

The DocGraph node model shipped (PR #12) on top of the v0.4.0 block-aware `TextDoc`. A
design review of the merged result found the architecture sound but the *stated
principles* under-articulated, the spec drifted from the code in a few places, and two
verified correctness/performance defects.
This plan refines the design so it is grounded in an explicit, layered set of
principles, fixes the obvious documentation and code defects first, and then maps the
deeper work that brings the implementation into alignment with those principles.

The work is sequenced so the safe, high-value changes land first (principles and
documentation, then obvious code fixes), and the design-alignment changes that need more
thought come last, each traceable to the principle it serves.

## Goals

- **Make the principles explicit and grounded.** Restate the design as a small spine of
  foundational principles with the capability and pragmatic principles derived from
  them, so every later decision cites a principle.
- **Remove documentation drift.** Bring `docs/textdoc-spec.md` into exact agreement with
  the implemented API (method vs.
  free function, return types, caching claims, the true canonical substrate).
- **Fix the obvious defects.** The `base_blocks()` cover-invariant bug and the
  `blocks()`/per-section re-parse cost are clear correctness/performance issues with no
  design ambiguity.
- **Map the alignment work.** Specify the design changes (layer-aware `collect()`, views
  that project from the node table, `base_blocks` surface) that close the gap between
  the “node table is canonical” claim and the current multi-parse reality.

## Non-Goals

- No new layers (synthetic, annotation, layout, provenance) — those remain later phases
  of the unified-document-model plan.
- No change to the `DocGraph/v0.1` serialized schema shape beyond what a fixed defect
  requires.
- No new external dependencies.
- No reopening of settled decision records (DR-1..DR-6); this plan refines their
  *expression* and *implementation fidelity*, not the decisions.

## Background

Context for the review and its findings:

- The model spans `node.py`, `node_table.py`, `block_tree.py`, `base_blocks.py`,
  `collect.py`, `span_ref.py`, `doc_graph.py`, `render.py`, and the heavily extended
  `text_doc.py`, with `docs/textdoc-spec.md` as the design of record.
- The spec’s §2 Goals reads as a flat list.
  The review found a **spine** of five foundational principles (shared offset space;
  source-canonical projection; layered parsing with offset-containment; mechanism over
  menu; model ≠ format ≠ implementation) that the other ten capability/pragmatic goals
  are consequences of.
  Naming the spine is the “grounding” this plan adds.
- Two defects were reproduced directly:
  - `base_blocks()` drops content that follows a nested sublist inside a list item
    (verified: the trailing paragraph of a list item is absent from the partition),
    violating the complete-cover / reassembly invariant.
  - `TextDoc.blocks()` is documented “lazy, cached” but re-parses on every call
    (`blocks() is blocks()` is `False`); `Section.blocks()` and `Section.links()` each
    re-parse the whole document per section, making a TOC walk quadratic.
    Only `node_table()` is actually cached.
- One honesty gap: the spec says the node table is *the* canonical store with all views
  as O(n) projections sharing its ids, but in code the node table is *assembled from*
  several independent parses, and `blocks()`/`sections()`/`links()`/`base_blocks()` do
  not project from it.
  The true unifying substrate is the shared `source_text` + code- point offset space.
- One API gap: `collect()` has no `layer=` filter, so kind-filtered queries return
  cross-layer duplicates (a paragraph appears as both a `markdown` and a `textual` node;
  a heading line also appears as a `textual` paragraph).
  This undercuts the “clean derived views” and “mechanism over menu” principles.

## Design

### The principles (the deliverable of Phase 1)

A three-tier set, to be added to `docs/textdoc-spec.md` as a new “Principles” section
ahead of §2 and cross-referenced from the goals.

**Tier 1 — Foundational (the spine):**

- **P1. One immutable source, one shared offset space, is the canonical substrate.**
  Every structure aligns to `source_text` by exact `[start, end)` in Unicode code
  points.
- **P2. Source is canonical; every structural model is a derived, re-derivable
  projection.** Edits go through the source/editing view and re-derive (DR-1/DR-2).
- **P3. Layered parsing; cross-layer relationships are offset-containment queries, not
  stored edges.** Independent parse dimensions (textual / markdown / document /
  synthetic) tagged by `layer`; containment, not persisted edges.
- **P4. Mechanism over menu.** One query primitive (`collect()`), two composable
  serialization axes (`include` / `detail`); no blessed per-kind rollups (DR-4/DR-5).
- **P5. Model ≠ format ≠ implementation.** A language-neutral JSON contract (Pydantic-
  authored, DR-3); Python now, Rust/TS later, implement one contract.

**Tier 2 — Representation:**

- **P6. Exact ground-truth references** (`source_text[s:e] == original_text`).
- **P7. Faithful, complete Markdown structure** (all modern block + inline kinds; one
  top-level type per block; recursive fully-populated nesting; bullet vs.
  ordered distinct).
- **P8. Textual structure with clean round-trip** (paragraphs/sentences/wordtoks editing
  view; `reassemble()`).
- **P9. Document structure** (heading hierarchy / sections / TOC; section containment).
- **P10. Synthetic tag structure** (marker-tag whitelist as a first-class layer).
- **P11. Clean whole-tree round-trip editing** — Markdown-object-exact after arbitrary
  edits, byte-exact when Flowmark-normalized or reconstructed from retained offsets.

**Tier 3 — Pragmatics:**

- **P12. Single canonical form, derived views, no stored counts.**
- **P13. Complete base-block partition** (ordered, non-overlapping, full cover, depth-
  annotated).
- **P14. Serializable projections** (full parse or any slice to language-neutral JSON).
- **P15. Parse cost ≈ one Markdown parse; expensive views are lazy.**
- **P16. Approximation where cheap and sufficient** (regex sentence segmentation,
  heuristic token sizing); exactness reserved for offsets/spans.
- **P17. Graceful tolerance of malformed input** (never throw on bad Markdown).
- **P18. Additive evolution** (existing diff/window/wordtok behavior preserved).

### Pitfalls and decisions to record

To be captured as a short “Pitfalls and decisions” note in the spec:

- Tight vs. loose lists are structurally identical; density is `Block.tight` metadata
  only and never enters a tally.
- Base blocks decompose lists recursively to `item_partition_depth` (default 6);
  blockquotes are always atomic.
- Fast/approximate sentence segmentation is accepted (no Spacy dependency); offsets stay
  exact via the span-aware splitter.
- Fast/approximate token sizing is accepted (`estimate_tokens` heuristic; not provider-
  keyed).
- The shared offset space — not the node table — is the true canonical substrate.
- Cross-layer queries are offset-containment; the same logical paragraph appears as
  distinct nodes in distinct layers, so queries must be layer-aware.
- Reference links and other unlocatable identities carry `span=None` and are excluded
  from offset-scoped rollups.
- Offsets are Unicode code points; byte/UTF-16 are derived on demand, never canonical.
- Round-trip is Markdown-object-exact, not byte-exact, except via retained offsets or
  after Flowmark normalization (two distinct equivalence levels; state both).

### Components

| Area | Files |
| --- | --- |
| Spec / principles | `docs/textdoc-spec.md` |
| Base-block cover fix | `src/chopdiff/docs/base_blocks.py`, `tests/docs/test_base_blocks.py` |
| Caching / parse cost | `src/chopdiff/docs/text_doc.py` |
| Layer-aware `collect()` | `src/chopdiff/docs/collect.py`, `src/chopdiff/docs/text_doc.py`, tests |
| Node-table-as-projection | `src/chopdiff/docs/node_table.py`, `src/chopdiff/docs/text_doc.py` |

### API Changes

- **Additive:** `collect(..., layer: set[Layer] | None = None)` on both the free
  function and `TextDoc.collect()`; default `None` = all layers (see Resolved
  Decisions).
- **Additive:** `TextDoc.base_blocks(*, item_partition_depth=6) -> list[BaseBlock]` as a
  method wrapping the free function, so the ergonomic surface matches `blocks()` and the
  spec describes a real method.
- **Behavioral fix (not a surface change):** `base_blocks()` now covers all list-item
  content; callers relying on the (buggy) partial cover would see additional base
  blocks.
- **Performance fix (not a surface change):** `blocks()` and per-section structural
  slices become memoized; results are unchanged.

## Implementation Plan

### Phase 1: Principles and documentation (do first)

Documentation-only; no code behavior change.
Lands the grounded principles and removes every drift the review found.

- [x] Add a “Principles” section (Tier 1–3, P1–P18) to `docs/textdoc-spec.md` ahead of
  §2, and cross-reference the existing goals to the principle each derives from.
- [x] Add the “Pitfalls and decisions” note (list above) to the spec.
- [x] Correct §3 wording: state that the shared offset space is the canonical substrate
  and the node table is a (cached) projection that gathers layers into one id space —
  drop the claim that views currently project from it (or scope it to the target state,
  clearly labeled).
- [x] Correct §6: `base_blocks` is a free function returning `list[BaseBlock]` (Block +
  depth), not `TextDoc.base_blocks() -> list[Block]`; note the `base_blocks.py` /
  `block_tree.py` split.
- [x] Correct §6 caching language for `blocks()` to match Phase 2 (mark as the intended
  state and link to the bead).
- [x] Update `CHANGELOG.md` (Unreleased) to note the principles section and the fixes.

### Phase 2: Obvious code fixes

Unambiguous correctness and performance defects.

- [x] Fix `base_blocks()` so a list item with content after (or between) nested sublists
  is fully covered: emit the item’s interstitial and trailing content as base blocks at
  the item’s depth, preserving order and non-overlap.
- [x] Add a cover-invariant test to `tests/docs/test_base_blocks.py` that fails before
  the fix (trailing-paragraph-after-sublist case, plus content between two sublists),
  asserting the union of base-block spans covers all non-whitespace source.
- [x] Memoize the structural block tree on the immutable `source_text` (cache
  `blocks()`), and make `Section.blocks()` / `Section.links()` slice the cached
  whole-document parse instead of re-parsing per section.
- [x] Verify `make lint` and `make test` are clean.

### Phase 3: Principle-alignment improvements

Design changes that close the gap to P12/P3/P4. Each cites its principle.

- [x] **(P3/P4/P12)** Add `layer: set[Layer] | None = None` (default all layers) to
  `collect()` and `TextDoc.collect()`; document that the same logical unit appears per
  layer and that callers scope by layer.
  Add tests showing a paragraph query returns one node per requested layer (no
  cross-layer duplicates) and that default-all still returns every layer.
- [x] **(P5)** Add `TextDoc.base_blocks()` wrapping the free function so spec and code
  agree (per Resolved Decisions).
- [x] **(P1/P12)** Land the offset-space-canonical framing: §3 wording (Phase 1) plus
  `node_table()` deriving from the memoized parse (Phase 2). No view-from-node-table
  refactor (see Resolved Decisions); nothing left open here.
- [x] Minor: make `collect()` sort `None`-span nodes deterministically (not at offset
  0); remove or justify the dead first-pass image branch in `_build_inline_nodes`.

## Testing Strategy

- Phase 2 is test-first: the cover-invariant test must fail before the fix and pass
  after. A property-style check (union of base-block spans covers all non-whitespace
  source, spans non-overlapping and ordered) guards the invariant generally.
- Caching changes are behavior-preserving: assert identical results before/after and
  assert the cached object identity / single parse call (e.g. via a call counter or
  `is`).
- Phase 3 `collect(layer=)` gets tests asserting no cross-layer duplicates for shared
  kinds (`paragraph`) and correct single-layer results.
- `make lint` and `make test` clean after each phase.

## Rollout Plan

- All changes are additive or behavior-preserving except the `base_blocks()` cover fix,
  which corrects a defect; note it in the changelog under fixes.
- Land per phase; each phase is independently shippable.
  Beads sequence the phases with dependencies (Phase 2 and 3 code beads depend on the
  Phase 1 spec beads only where the spec must describe the intended state first).

## Resolved Decisions

Both prior open questions are resolved; the principle and the simplest/most-flexible
choice are recorded here.

- **`collect()` layer handling — `layer: set[Layer] | None = None`, default = all layers
  (unfiltered).** Principle: P4 (mechanism over menu) plus a safety rule — never
  silently drop. `layer` is just another orthogonal filter like `kinds`; defaulting to
  one layer would make `collect(kinds={section})` silently return `[]` (a
  correctness-class surprise), whereas default-all returns visible, filterable
  duplicates (a noise-class surprise).
  Including-too-much is debuggable; silently-excluding is a footgun.
  The cross-layer overlap is the layered model being honest (P3), not a bug; the fix is
  the `layer=` filter plus documentation, not a privileged default.
  Additive (P18).
- **Canonical substrate — the source text + offset space, not the node table.**
  Principle: P1 over the earlier DR-1 aspiration.
  Amend the spec to name the offset space as canonical and the node table as *one*
  projection (the id-addressed, layer-tagged, serialization-friendly one).
  Do **not** refactor `blocks()`/`sections()`/`links()` to literally project from the
  node-table id space — the node table is itself built from those parses, so inverting
  the dependency is over-coupling.
  Instead the simple model is “one memoized structural parse, many derived views sharing
  the offset space”; the single-canonical-form ideal (P12/P15) holds at the level of the
  parse + offset space.
  Concretely this is the §3 wording correction (Phase 1) plus making `node_table()`
  derive from the same memoized parse as `blocks()` (Phase 2), not a separate refactor.

## References

- Design of record: `docs/textdoc-spec.md`
- Unified document model plan: `plan-2026-05-29-unified-document-model.md`
- Research: `research-2026-05-29-document-model.md`,
  `research-2026-05-30-multilayer-parsing.md`, `research-2026-05-30-span-references.md`
- Document-structure epic: `chopdiff-d6js`

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
