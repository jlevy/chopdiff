# Feature: Exact spans, sections, and structural blocks for TextDoc

**Date:** 2026-05-26

**Author:** chopdiff maintainers

**Status:** Draft

## Overview

`TextDoc` is now block-aware (as of v0.3.0): it classifies each block by Markdown kind,
filters/iterates by type, and records exact start offsets into the unmodified source.
This feature builds on that to add the three capabilities still missing for full
document-structure navigation:

1. **Exact spans** — a start *and* end for every block and sentence, so any unit's
   source text can be sliced exactly and any character offset can be mapped to the
   block/sentence containing it (and back).
2. **Sections** — a heading/section hierarchy and table of contents, derived from the
   heading blocks already classified today.
3. **Structural blocks** — an opt-in, whole-document parse that resolves what blank-line
   splitting cannot: individual list items, list nesting, and code/list blocks whose
   boundaries don't align to blank lines.

All of this extends `TextDoc` in place. We are explicitly **not** introducing a parallel
`BlockDoc`/`SectionDoc`/`FlexDoc`; the incremental v0.3.0 approach is the model.

## Goals

- Every `Paragraph` and `Sentence` exposes an exact `[start, end)` span (document- and
  parent-relative), with `block_at_offset` / `sentence_at_offset` lookups, round-tripping
  against the original text.
- A derived section hierarchy and TOC over heading blocks, correct for ATX and setext
  headings and never tripped by `#` inside fenced code.
- Rolled-up size stats per section (chars, words, sentences, tokens, …) in tree form,
  reusing the existing `size` machinery rather than new rollup logic.
- An opt-in structural block tree (`list_item` + nesting; code/table/blockquote as whole
  blocks) for callers that need per-item granularity.
- Strictly additive: `TextDoc`, `Paragraph`, `Sentence`, and the diff/window/wordtok
  machinery keep their current behavior and APIs.

## Non-Goals

- Replacing `TextDoc` or changing how diffs, sliding windows, or wordtoks work.
- CommonMark/GFM rendering or reformatting (flowmark already covers normalization).
- Replacing `TextNode` (the HTML-`<div>` view in `chopdiff.divs`).
- Exact, provider-keyed token counts (tracked separately).
- A concurrency/thread-safety layer.

## Background — current state (v0.3.0)

`TextDoc.from_text` splits the document on blank lines (two or more newlines, including
whitespace-only lines) into `Paragraph`s, each split into `Sentence`s. Relevant current
surface:

- `Paragraph`: `original_text` (the exact block text), `sentences`, `offsets:
  Offsets`, and a cached `block_type: BlockType` (heading, paragraph, list, table, code,
  blockquote, html, footnote), classified by parsing the block with flowmark's marko.
- `Sentence`: `text`, `offsets: Offsets`.
- `Offsets(doc_offset, block_offset)`: **start only.** `doc_offset` is absolute in the
  document; `block_offset` is relative to the parent (the document for a paragraph, the
  paragraph for a sentence). Offsets are exact references into the unmodified input.
- `TextDoc.iter_blocks(include=, exclude=)` and `filtered(...)` select blocks by type.

Limitations this feature addresses:

- Offsets are start-only — no end, so you cannot slice a unit's source text by span or
  map an arbitrary offset to its unit.
- A *tight* list is one `list` block (no per-item access); a fenced code block
  containing a blank line is split; loose nested lists flatten.
- No section hierarchy (PR #1's `SectionDoc` was reviewed and not merged).
- Sentence offsets are best-effort: the sentence splitter normalizes whitespace, so a
  sentence inside e.g. a table is not a verbatim slice of the block.

## Design

Three additive layers, smallest and most valuable first. Layers 1 and 2 are cheap and
reuse what already exists; Layer 3 is the only part needing real parsing work.

### Layer 1 — Exact spans (compute, don't store)

A paragraph's `original_text` is already an exact slice of the source, so its end is
simply `doc_offset + len(original_text)` — **no new stored state is needed.** Add
computed accessors rather than new fields:

- `Paragraph.span -> (start, end)` and `Paragraph.end_offset` (= `doc_offset +
  len(original_text)`).
- `Sentence` spans, both block-relative and absolute, from `offsets` + `len(text)`. For
  verbatim sentences these round-trip exactly; for splitter-normalized sentences (e.g.
  tables) the span is best-effort and documented as such.
- `TextDoc.block_at_offset(o) -> Paragraph | None` and `sentence_at_offset(o) ->
  SentIndex | None`, implemented by binary/linear search over the paragraph spans.

Optionally introduce a small frozen `Span(start, end)` value type if it reads better
than tuples, but keep `Offsets` as-is to avoid churn.

### Layer 2 — Sections and TOC (derived, no reparse)

Add a derived hierarchy over the existing heading blocks:

- `Section`: a heading `Paragraph`, its level, the contiguous blocks it owns (up to the
  next heading of equal-or-higher level), and child `Section`s.
- `TextDoc.sections() -> list[Section]` (tree) and `toc()` (flattened title/level/span).

This reuses the already-correct, code-fence-safe, setext-aware heading classification and
the Layer 1 spans; it needs **no** re-parse and supersedes the intent of `SectionDoc`
without its fragile hand-rolled offsets.

**Rolled-up stats (the key reuse).** A `Section`'s size is just the sum of its blocks'
sizes, so instead of new rollup logic a `Section` produces a sub-document view of its
blocks and defers to the existing size machinery:

- `Section.size(unit, subtree=True)` — size including all subsections (default),
  computed by running `TextDoc.size` over the section's block subset, so separator and
  whitespace accounting matches whole-document sizes. `subtree=False` reports own
  content only (excluding child sections).
- `Section.size_summary()` per node and a `TextDoc.section_size_tree(units=...)` renderer
  for the readable rolled-up tree (mirroring `size_summary` and
  `TextNode.structure_summary`). Every `TextUnit` (chars, words, sentences, tokens, …)
  rolls up uniformly with no per-unit special-casing.

This makes "sizes by section, as a tree" a one-call operation, and follows the existing
precedent that `TextNode.size` sums its children.

### Layer 3 — Structural block tree (opt-in, the hard part)

For per-list-item granularity, nesting, and exact code/list boundaries, parse the whole
document once into a structural tree, offered as an opt-in API that does **not** replace
the blank-line `Paragraph` model:

- `Block`: `type: BlockType`, span, optional `level`, and `children` (a list holds
  `list_item`s; an item may hold nested blocks).
- `TextDoc.blocks() -> list[Block]` (or a standalone `parse_blocks(text)`), lazily
  computed and cached.
- `BlockType` gains `list_item` and `thematic_break` (additive to the shipped enum).

Exact sub-paragraph offsets are the open technical risk. Spike two approaches on a
corpus before committing:

- marko line-numbers plus a source-mapping pass over a single parse, or
- a small line-oriented block scanner (fenced code, ATX/setext headings, list items,
  blockquotes, tables, thematic breaks, paragraphs), cross-checked against marko.

Document-level paragraph offsets are already exact, so this only needs to be correct for
structure *within* and *across* blank-line boundaries.

### API Changes

All additive:

- `Paragraph`/`Sentence`: computed span/end accessors; optional `Span` type.
- `TextDoc`: `block_at_offset`, `sentence_at_offset`, `sections`, `toc`, and (Layer 3)
  `blocks`.
- `Section` and `Block` dataclasses; `BlockType.list_item` / `BlockType.thematic_break`.

## Implementation Plan

### Phase 1 — Spans and mapping

- [ ] Computed span/end accessors on `Paragraph` and `Sentence`.
- [ ] `block_at_offset` / `sentence_at_offset` with round-trip tests.
- [ ] Make sentence spans exact for verbatim sentences; documented fallback otherwise.

### Phase 2 — Sections and TOC

- [ ] `Section` type; `TextDoc.sections()` / `toc()` over heading blocks.
- [ ] Port a `read_time` util and an `analyze_doc`-style example onto this.

### Phase 3 — Structural block tree (opt-in)

- [ ] Spike marko source-mapping vs a block scanner for sub-paragraph exact offsets.
- [ ] `Block` tree with `list_item` + nesting; `TextDoc.blocks()`; golden tests.

## Testing Strategy

- Span invariants: `original_text[p.span] == p.original_text`; verbatim
  `original_text[s.span] == s.text`; non-overlapping, ordered spans.
- Mapping: `block_at_offset`/`sentence_at_offset` agree with the spans across the doc.
- Sections: ATX + setext levels; `#` inside fenced code never starts a section; nesting.
- Structural parse: cross-checked against marko on the corpus in
  `tests/docs/test_block_types.py`; list-item and nesting cases.

## Rollout Plan

- Phases 1 and 2 are additive and backward-compatible; ship together as a minor release.
- Phase 3 ships separately once the offset spike settles; `BlockType` additions are
  additive.

## Open Questions

- Spans: computed accessors (recommended) vs a stored `end` on `Offsets`?
- Sections: expose as a nested tree, a flat list with levels, or both?
- Layer 3: marko source-mapping vs a custom scanner; how to represent nested and
  multi-paragraph list items; should code blocks be reassembled across blank lines.
- Should `TextDoc` retain the full original source string to support slicing by an
  arbitrary external offset, or is per-unit `original_text` sufficient (it is for
  `block_at_offset`)?

## References

- v0.3.0 (PRs #7, #9, #10): shipped `BlockType`, `iter_blocks`/`filtered`, `Offsets`,
  exact paragraph offsets, blank-line splitting, `estimate_tokens`.
- PR #1 `feature/extend-chopdiff-section-iteration` (`SectionDoc`/`FlexDoc`): prior art,
  reviewed and not merged.
- `src/chopdiff/docs/text_doc.py`: current `TextDoc` / `Paragraph` / `Sentence` /
  `Offsets` / `BlockType`.
