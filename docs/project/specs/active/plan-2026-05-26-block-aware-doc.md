# Feature: Block-aware document model for chopdiff

**Date:** 2026-05-26 (last updated 2026-05-26, revised after the v0.3.0 release)

**Author:** chopdiff maintainers

**Status:** Draft (revised)

## Overview

Give chopdiff a Markdown-block-aware document model with exact source spans for every
structural unit (block and sentence), a heading/section hierarchy, and per-list-item
granularity.

**This spec was substantially delivered, in pieces, by the v0.3.0 release.** The
original "lightweight first step" (`BlockType`, `iter_blocks`/`filtered`) plus the exact
offsets and the `Offsets` record all shipped on the existing `TextDoc` rather than a new
class. This revision records what shipped, narrows the spec to the genuine remaining
gaps, and — informed by how well the incremental approach worked — **recommends
evolving `TextDoc` rather than building a parallel `BlockDoc` with adapters.**

## What shipped in v0.3.0

These were goals of the original spec and are now on `main`:

- **Block classification** (`BlockType`: heading, paragraph, list, table, code,
  blockquote, html, footnote) via `Paragraph.block_type`, determined by parsing each
  block with flowmark's marko parser (not a regex heuristic). Correctly ignores `#`
  inside fenced code and recognizes setext headings, GFM tables, and footnote defs.
- **Filtered iteration / aggregation**: `TextDoc.iter_blocks(include=, exclude=)` and
  `TextDoc.filtered(...)`, so callers can process only paragraphs and list items (or
  skip headings/tables) and count sentences/words over a subset.
- **Exact offsets**: `from_text` no longer strips the document; `Offsets(doc_offset,
  block_offset)` on `Paragraph` and `Sentence` round-trips into the unmodified input
  (`doc_offset` absolute, `block_offset` relative to the parent).
- **Robust paragraph splitting**: blank line = two or more newlines, including
  whitespace-only blank lines; runs collapse to one break.
- **Token estimation**: `estimate_tokens` / `TextUnit.tokens` (no tokenizer, no
  network); `tiktoken` removed.

As a result, the core downstream needs (track paragraphs and sentences, see block
structure, iterate/skip by block type, aggregate counts) are **already met** for the
common cases.

## Remaining gaps (the actual scope now)

1. **Exact block/sentence spans.** `Offsets` carries only a start (`doc_offset`); there
   is no `end`. Extracting "the exact source text of this block/sentence" or doing
   bidirectional offset↔block↔sentence mapping needs a span `[start, end)`.
2. **Per-list-item granularity and nesting.** A tight list is still a single `list`
   block; loose lists yield one block per item but flatten nesting. There is no
   first-class list item or nesting depth.
3. **Exact block boundaries for code/loose lists.** Blank-line splitting still splits a
   fenced code block that contains a blank line, and cannot see structure that does not
   align to blank lines.
4. **Heading/section hierarchy + TOC.** No tree over heading blocks (the PR #1
   `SectionDoc` was not merged).
5. **Exact sentence spans.** Sentence offsets are best-effort: the sentence splitter
   normalizes whitespace, so a sentence inside a table is not a verbatim slice and its
   offset falls back to a cursor position.

## Non-Goals

- Replacing `TextDoc` or its sentence/wordtok/diff/sliding-window machinery.
- Full CommonMark/GFM rendering or reformatting (flowmark covers that).
- Replacing the HTML-div parser (`chopdiff.divs` / `TextNode`).
- A concurrency/thread-safety layer.

## Design (revised)

**Recommendation: evolve `TextDoc` incrementally; do not introduce a parallel `BlockDoc`
class with `to_text_doc()` adapters.** The v0.3.0 work showed that adding block-awareness
directly to `TextDoc` is low-risk, additive, and avoids a second overlapping
abstraction (the very problem the original spec set out to remove). The remaining gaps
are best addressed as additive layers, smallest-first.

### Step 1 — spans (small, high value)

Extend the shipped `Offsets` from a start-only record to a span. Either add `end` to
`Offsets` or introduce a `Span(start, end)` with both a `doc`-relative and
`block`-relative form, keeping backward-compatible accessors where practical. With end
offsets:

- `block.text` / `sentence.text` can be sliced exactly from the source.
- Implement bidirectional mapping: `TextDoc.block_at_offset(o)` /
  `sentence_at_offset(o)`.
- Make sentence spans exact where the sentence is a verbatim slice; keep a documented
  best-effort fallback for splitter-normalized content (e.g. tables).

This is additive and unblocks the "track sentence spans within a document" use case
fully.

### Step 2 — heading/section hierarchy (cheap, derived)

Add a derived view that groups the existing `block_type == heading` paragraphs into a
tree (`TextDoc.sections()` / `toc()`), with each section spanning from its heading to
the next heading of equal-or-higher level. This reuses the already-correct,
code-fence-safe heading classification and needs **no** re-parse — superseding the
intent of PR #1's `SectionDoc` without its fragile hand-rolled offsets.

### Step 3 — true block structure (the genuinely new, harder part)

For per-list-item granularity, nesting, and exact code/list boundaries, parse the
**whole document once** into a structural block tree (list → items → nested lists; code
as one block regardless of internal blank lines). Offer this as an **opt-in richer
structure** (e.g. `TextDoc.blocks()` returning typed `Block`s with spans and children)
rather than replacing the blank-line `Paragraph` model that diff/windowing depend on.

Offsets remain the hard part. With spans from Step 1 in place, evaluate:

- **marko line-numbers + a source-mapping pass** over the single parse, or
- **a small line-oriented block scanner** (fenced code, ATX/setext headings, list
  items, blockquotes, tables, thematic breaks, paragraphs), cross-checked against marko.

A spike is still warranted, but it is now lower-stakes: paragraph-level exact offsets
already work, so this only needs to be correct for sub-paragraph structure.

### `BlockType` additions

When Step 3 lands, extend `BlockType` with `list_item` (and `thematic_break` if needed).
This is additive to the shipped enum.

## Open questions — resolved or narrowed

- **`from_text` strip / exact offsets** — RESOLVED: strip removed in v0.3.0; paragraph
  offsets are exact.
- **Replace vs wrap `TextDoc`** — RESOLVED: do neither; evolve `TextDoc` in place.
- **marko vs scanner for offsets** — NARROWED: only needed for sub-paragraph structure
  (Step 3); spike before committing.
- **List nesting / multi-paragraph items** — still open; decide representation in Step 3
  (e.g. items hold child blocks).
- **`FlexDoc` / `TextNode`** — keep `TextNode` (HTML-div view) separate; do not build
  `FlexDoc`.

## Implementation Plan

### Phase 1: Spans

- [ ] Add end offsets (span) to `Offsets`; exact `block.text` / `sentence.text`.
- [ ] Make sentence spans exact for verbatim sentences; documented fallback otherwise.
- [ ] `block_at_offset` / `sentence_at_offset` bidirectional mapping + round-trip tests.

### Phase 2: Sections

- [ ] Derived `sections()` / `toc()` over heading blocks (setext + code-fence safe).
- [ ] Port the `read_time` util and an `analyze_doc`-style example onto this.

### Phase 3: True block structure (opt-in)

- [ ] Spike marko source-mapping vs a block scanner for sub-paragraph exact offsets.
- [ ] `TextDoc.blocks()` structural tree with `list_item` + nesting; golden tests.

## Testing Strategy

- Golden / corpus tests over diverse Markdown (reuse the rich corpus added in
  `tests/docs/test_block_types.py`): block list with types and spans snapshotted.
- Invariants: `original_text[block.start:block.end] == block.text`;
  `original_text[s.start:s.end] == s.text` for verbatim sentences; blocks non-overlapping.
- Heading hierarchy: ATX + setext levels; `#` in fenced code never a heading.
- Cross-check structural parse against marko on the corpus.

## References

- v0.3.0 release — shipped `BlockType`, `Offsets`, exact offsets, `iter_blocks`/
  `filtered`, blank-line splitting, `estimate_tokens` (PRs #7, #9, #10).
- PR #1: `feature/extend-chopdiff-section-iteration` (`SectionDoc`/`FlexDoc`) — prior art
  and review findings; not merged.
- `src/chopdiff/docs/text_doc.py` — current `TextDoc` / `Paragraph` / `Sentence` /
  `Offsets` / `BlockType`.
