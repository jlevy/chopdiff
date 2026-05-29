# Feature: Multi-level block-type tallies and locations (Phase 7)

**Date:** 2026-05-29

**Author:** chopdiff maintainers

**Status:** Superseded / archived — folded into
[`plan-2026-05-29-unified-document-model.md`](../active/plan-2026-05-29-unified-document-model.md).
Multi-level tallies are the "flexible rollups" feature of that unified-model plan (Phase
1), and this note's four design decisions are folded into that plan's "Open decisions".
Kept in `archive/` for the detailed nested-block (axis A) and caching (axis B) trade-off
analysis; the unified-model spec is the authoritative planning surface.

**Implementation status:** none — design-stage; not the active planning surface.

> **Design of record:** [`docs/textdoc-spec.md`](../../../textdoc-spec.md) §9 (Derived
> views and rollups). This plan extends that section; it does not change the normalized
> form.

## Problem

We want, at **every scope** — document, section (own content), section subtree, and any
container block — a tally of **how many of each `BlockType`** there are *and* **where each
one is** (its span). This must include blocks **nested inside containers** (a table inside
a blockquote, a code block inside a list item).

Today this is only partly available:

- `TextDoc.block_type_counts()` and `Section.block_type_counts()` count **top-level blocks
  only**. A document with three tables (one top-level, one in a blockquote, one in a list
  item) reports **one** table — blockquotes are leaves and list items recurse only into
  nested lists, so the other two tables are not in the tree at all.
- Counts carry no locations; "where" needs a separate manual pass over `blocks()`.
- `Section.blocks()` re-parses the whole document on every call (and once *per section*),
  so per-section analysis is quadratic in document size.

## What the data already gives us

Two facts (both verified against flowmark 0.7.1) shape the design:

1. **The full structure is one walk away.** `flowmark_markdown().parse(text)` already
   produces a *fully recursive* tree in which **every** block element at **every** nesting
   level carries an authoritative `element.span` — e.g. a `Table (15, 51)` inside a
   `Quote (0, 51)` has its own offsets. chopdiff currently *discards* this nesting
   (blockquote → leaf). Surfacing it is a tree walk over an already-parsed structure, not
   a new computation. There is nothing expensive to precompute and no auxiliary index
   needed for correctness — counts and locations are `len()` and `.span` over the walk.

2. **The tree is a pure function of immutable input.** The structural tree derives only
   from `TextDoc.source_text`, which is fixed at parse time and is *not* changed by
   sentence edits (those touch the editing view, `reassemble()`). So any caching of the
   tree or its tallies is safe without invalidation logic, as long as `source_text` is not
   reassigned after parsing (already the contract).

A third fact removes a worry: tight and loose list items **both** wrap their content in a
`Paragraph` in marko's AST (the `tight` flag is a rendering concern), so recursive
structural tallies are **density-invariant** — the same content yields the same counts
regardless of blank-line spacing. (A genuine continuation paragraph adds a real paragraph,
as it should.)

## Requirements

- Counts by `BlockType` at: document, section (own), section (subtree), and any block's
  descendants.
- Locations (spans), not just counts.
- Cover nested blocks (blockquote / list-item contents).
- No stored counts in the data model — everything a derived view (memoization is fine).
- Density-invariant for structural blocks.
- Additive; minimize breakage.

## Design axis A — how nested blocks are exposed

**A1. Keep `blocks()` top-level (status quo) + add a separate recursive walk.**
`blocks()` stays top-level with list nesting; add `walk_blocks()` for deep traversal;
tallies take a `recursive` flag.
- *Pros:* zero change to `blocks()`; preserves the "classify by outer type" top-level view;
  top-level density-invariance untouched.
- *Cons:* two notions of "the tree"; blockquote/list-item children stay empty in
  `blocks()`, so the deep walk needs its own descent into the marko tree — duplicating
  traversal logic.

**A2. Make `blocks()` fully recursive.** Every container populates its block children.
- *Pros:* one canonical tree; recursion is natural; matches "normalized form is canonical."
- *Cons:* changes `.children` of `blockquote` (empty → populated) and `list_item`
  (lists-only → all block children); deep-recursion semantics shift; loses the
  structural-level "outer type only" simplification (still recoverable at top level).

**A3. Hybrid (recommended candidate).** Populate **all** container children so the tree is
complete and lossless, but keep the *default* tally/index scope **top-level** with a
`recursive` opt-in.
- *Pros:* one complete tree (the nested table is always discoverable); top-level list and
  default counts are unchanged (back-compatible); "outer type at top level, inner via
  descent" satisfies both the existing contract and the new requirement.
- *Cons:* `.children` on `blockquote`/`list_item` gains entries (additive but a behavior
  change to document); one `recursive` parameter to thread through.

## Design axis B — computation strategy

**B1. Recompute on each call (status quo).**
- *Pros:* simplest; no staleness; literally "no stored counts."
- *Cons:* O(parse) per call; `Section.blocks()` re-parses the whole doc per section →
  quadratic; tallies re-walk every call. Poor for analysis workloads that probe many
  slices.

**B2. Lazy-cached, keyed on the immutable `source_text` (recommended candidate).** Parse
once and build the recursive tree once (a `@cached_property`/memoized derivation); tallies
and indexes are thin walks over the cached tree (cached if measured to matter).
`Section.blocks()` becomes a **slice of the cached document tree**, not a re-parse →
linear.
- *Pros:* cost is opt-in (paid only if the structural view is used — `blocks()` is
  documented as opt-in); fast on repeat; removes the quadratic per-section re-parse; safe
  because `source_text` is fixed. Memoization is an implementation detail, not a stored
  field in the normalized form, so it is consistent with "no stored counts" (the same way
  `Paragraph.block_type` is already a `cached_property`).
- *Cons:* must document "do not reassign `source_text` after parse" (already implied);
  holds the tree in memory; `cached_property` on the mutable `TextDoc` dataclass needs the
  usual care.

**B3. Eager precompute at construction.**
- *Pros:* predictable cost; always ready.
- *Cons:* pays even when `blocks()` is never used (the common diff/window path); violates
  the "opt-in structural view" contract; wasteful. Rejected.

## Design axis C — API surface

One traversal primitive, with derived views layered on top:

- `walk_blocks(*, recursive: bool = False) -> Iterator[Block]` — the traversal everything
  else is built on (optionally yielding `(block, depth)` or parent links).
- `block_index(*, recursive=False) -> dict[BlockType, list[Block]]` — the unifying
  "count + where" view: counts are `len(v)`, locations are `[b.span for b in v]`.
- `block_type_counts()` becomes a thin `{k: len(v) for k, v in block_index().items()}`
  (or stays a `Counter`), at document, section-own, section-subtree, and block scope.
- Section scope adds a `subtree: bool` to include child sections.

Open API question: whether the primary return is a `Counter` (counts) or the richer index
(`dict[BlockType, list[Block]]`) with counts derived from it. The index is strictly more
useful (it answers "where"), so it is the better primitive; `block_type_counts()` can
remain as a convenience.

## Recommendation (proposed, pending decisions)

**A3 + B2 + C:** a complete (recursive) but back-compatible tree, lazily cached off the
immutable `source_text`, with a `walk_blocks()` primitive and a `block_index()` view that
carries both counts and locations at every scope. This makes the full tally available,
fixes the quadratic per-section re-parse, and stays within the "derived views, no stored
counts" principle.

## Open decisions

1. **Tree shape / default scope.** Fully populate container children and default tallies to
   top-level with `recursive` opt-in (A3), or keep `blocks()` top-level and expose a
   separate deep walk (A1)? (A2 — recursive *by default everywhere* — is the third option,
   more breaking.)
2. **Computation strategy.** Lazy-cache the tree off `source_text` (B2), or keep pure
   recompute-on-call (B1)? B2 also fixes the quadratic `Section.blocks()`.
3. **Primary tally return.** Index (`dict[BlockType, list[Block]]`, counts via `len`) as the
   primitive with `block_type_counts()` as convenience, or keep `Counter` primary and add a
   separate locations accessor?
4. **Density / paragraph counting.** Confirm we count list-item wrapper paragraphs as
   paragraphs (they are density-invariant) or exclude them — affects only the `paragraph`
   tally, not `table`/`code`/`blockquote`/etc.

## Rollout

Additive minor release (target v0.5.0). If A2/A3 is chosen, note the `.children`
population on `blockquote`/`list_item` as a behavior change in the changelog. No change to
the normalized form or to `textdoc-spec.md` beyond expanding §9.

* * *

*This document follows the tbd [writing style guidelines](https://github.com/jlevy/tbd).*
