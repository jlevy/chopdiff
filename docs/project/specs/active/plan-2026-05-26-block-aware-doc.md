# Feature: Block-aware document model for chopdiff

**Date:** 2026-05-26 (last updated 2026-05-26)

**Author:** chopdiff maintainers

**Status:** Draft

## Overview

Give chopdiff a single, Markdown-block-aware document model: parse a document once
into a flat list of typed blocks (heading, paragraph, list item, table, code,
blockquote, etc.), each with exact character offsets into the original text, with
sentence spans hanging off text blocks and a heading hierarchy derived from the
block list.

This is the foundation a downstream agent needs to: track paragraphs and sentence
spans, see the block-level structure of a document, iterate over only certain block
kinds (e.g. paragraphs and list items) while skipping others (e.g. headings and
tables), and aggregate counts (total sentences/words across all paragraphs).

The lightweight first step — `BlockType` + `Paragraph.block_type` + `iter_blocks` /
`filtered` on the existing `TextDoc` — ships separately (PR #7). This spec covers the
deeper model that fixes the limitations that step cannot.

## Goals

- Parse Markdown **once** into an ordered list of typed `Block`s.
- Each block carries **exact** `start_offset`/`end_offset` into the original
  (unmodified) text, such that `text[block.start_offset:block.end_offset]` round-trips.
- Classify blocks: heading, paragraph, list, list item, table, code, blockquote,
  thematic break, html block, footnote definition.
- Per-list-item granularity: a list exposes its individual items as blocks.
- Sentence spans: text blocks expose sentences with absolute offsets into the original
  text (not offsets into a stripped copy).
- Filtered iteration and aggregation by block type
  (`iter_blocks(include=/exclude=)`, `filtered(...).size(unit)`).
- Heading (section) hierarchy derived from the block list, correctly ignoring `#`
  inside code blocks and including setext (`===` / `---`) headings.
- Bidirectional offset mapping: original offset -> block -> sentence, and back.

## Non-Goals

- Full CommonMark/GFM rendering or round-trip reformatting (flowmark already covers
  Markdown normalization).
- Replacing the HTML-div parser (`chopdiff.divs` / `TextNode`) in this work.
- Changing the sentence splitter or the wordtok / diff / sliding-window transforms.
- A general concurrency/thread-safety layer.

## Background

chopdiff currently has three independent parsers and no unified block model:

1. `TextDoc` (`docs/text_doc.py`) splits on blank lines into `Paragraph`/`Sentence`.
   It is not Markdown-block-aware: a list becomes one block, a code block with an
   internal blank line is split, and there are no block-type labels. It also does
   `text.strip()` on input, so `char_offset`s are not true offsets into the original
   document — a problem for tracking sentence spans.
2. `TextNode` (`docs/../divs`) parses HTML `<div>` structure via selectolax.
3. PR #1 (`feature/extend-chopdiff-section-iteration`) adds `SectionDoc` (marko-based
   heading hierarchy) and a `FlexDoc` façade. Review found the heading offsets are
   hand-rolled and fragile (setext headings dropped, ATX-only line heuristics), the
   façade recomputes paragraph offsets instead of reusing them, swallows exceptions,
   uses untyped `dict` APIs, and adds premature locking. Its durable ideas are
   code-block-aware heading detection and the `read_time` / `analyze_doc` utilities.

The result is overlapping abstractions and no single source of truth for "what are the
blocks of this document, where are they, and what type is each." This spec defines that
single source of truth.

## Design

### Approach

Introduce `chopdiff.docs.block_doc` with a typed `Block` and a `BlockDoc` container,
built from a single Markdown block parse that yields **exact offsets**. Reuse the
existing sentence splitter for sentence spans within text blocks. Derive the heading
hierarchy from the block list (superseding `SectionDoc`).

The central technical decision is how to obtain exact offsets, because marko (2.2.x)
does not attach reliable character spans to all nodes:

- **Option A — marko + source mapping:** parse with marko for structure, then map each
  element back to offsets using line numbers plus a scan. This is what PR #1 attempts
  and where it is fragile.
- **Option B — dedicated block scanner (recommended):** Markdown's *block* grammar is
  small (fenced/indented code, ATX + setext headings, bullet/ordered list items,
  blockquotes, tables, thematic breaks, blank-line-separated paragraphs, html blocks,
  footnote defs). A focused line-oriented scanner can emit `(type, start, end)` with
  exact offsets directly, which is more robust for offsets than marko. Validate its
  block structure against marko in tests.

Recommendation: Option B for offset fidelity, cross-checked against marko in tests.
Spike both before committing (see Open Questions).

### Components

- `BlockType` (StrEnum): extends the enum shipped in PR #7 with `list_item`,
  `thematic_break`, and any needed additions; this becomes the canonical enum.
- `Block` (dataclass): `type`, `start_offset`, `end_offset`, `text` (a property
  slicing the original), optional `level` (headings / list nesting), optional
  `children` (list -> list items), and lazily computed `sentences` (with absolute
  offsets) for text blocks.
- `BlockDoc` (dataclass/container): holds `original_text` and `blocks`; provides
  `iter_blocks(include=, exclude=)`, `filtered(...)`, `size(unit, ...)`,
  `block_at_offset(offset)`, `sentence_at_offset(offset)`, and a derived
  `section_tree()` / `toc()` from heading blocks.
- Sentence spans: reuse `default_sentence_splitter`; record absolute
  `start_offset`/`end_offset` per sentence.
- Adapters: `BlockDoc.to_text_doc()` / construction from `BlockDoc` so existing
  wordtok/diff/sliding-window code keeps working unchanged.

### API Changes

- New module `chopdiff.docs.block_doc` (`Block`, `BlockDoc`); canonical `BlockType`.
- `chopdiff.docs.text_doc` keeps `TextDoc` for transforms; `BlockType` defined once and
  re-used (the PR #7 enum is the seed, moved/extended without breaking imports).
- Direction-setting (not necessarily in first cut): `SectionDoc`/`FlexDoc` from PR #1
  are superseded by `BlockDoc`; do not merge PR #1's versions. Port the `read_time`
  util and `analyze_doc` example onto `BlockDoc`.
- No top-level `__init__` re-export changes are required; keep submodule imports.

## Implementation Plan

### Phase 1: Block model with exact offsets

- [ ] Spike Option A vs Option B for exact offsets on a representative corpus; pick one.
- [ ] Implement the block parser producing typed `Block`s with round-trippable offsets.
- [ ] Implement `BlockDoc` with `iter_blocks`/`filtered`/`size` and offset lookups.
- [ ] Sentence spans with absolute offsets on text blocks.
- [ ] Heading hierarchy + TOC derived from heading blocks (setext + code-fence safe).
- [ ] Tests: offset round-trip, classification, filtered counts, sentence-span
      round-trip, heading hierarchy (incl. setext), `#`-in-code ignored, list items.

### Phase 2: Convergence and migration (if needed)

- [ ] `BlockDoc` <-> `TextDoc` adapters so transforms are unaffected.
- [ ] Port `read_time` util and `analyze_doc` / `insert_size_info` examples onto
      `BlockDoc`; supersede `SectionDoc`/`FlexDoc`.
- [ ] Migration notes for existing `TextDoc` callers; deprecate overlapping APIs.

## Testing Strategy

- Golden / corpus tests over diverse Markdown (reuse PR #1's `test_markdown.md` corpus):
  block list with types and offsets snapshotted.
- Invariant: for every block, `original_text[block.start:block.end] == block.text`;
  blocks are non-overlapping and cover the document (modulo inter-block whitespace).
- Sentence spans: `original_text[s.start:s.end] == s.text` for each sentence.
- Heading hierarchy: ATX + setext levels correct; `#` inside fenced code never a
  heading; nesting matches marko's structure.
- Filtering/aggregation: counts of sentences/words over paragraph-only subset match
  hand-computed values.
- Cross-check block structure against marko on the corpus (catches scanner gaps).

## Rollout Plan

- Land as a new additive module; no behavior change to `TextDoc` transforms.
- Keep PR #7's lightweight `block_type` API working (it is forward-compatible: same
  `BlockType` names); `BlockDoc` becomes the richer option when exact offsets or
  list-item granularity are needed.

## Open Questions

- Offsets: does marko 2.2.x expose enough position info to avoid a custom scanner, or
  is the scanner (Option B) required for fidelity?
- Does `BlockDoc` eventually **replace** `TextDoc` as the primary entry point, or wrap
  it? (Affects how aggressively we migrate transforms.)
- Nested lists and "loose" lists: how deep should `list_item` nesting go, and how are
  multi-paragraph list items represented?
- Should `TextDoc.from_text`'s `strip()` be changed to preserve absolute offsets, or is
  that only fixed in `BlockDoc`?
- Keep `FlexDoc`/`TextNode` HTML-div view, or fold div-awareness into `BlockDoc` later?

## References

- PR #1: `feature/extend-chopdiff-section-iteration` (SectionDoc/FlexDoc) — prior art
  and review findings.
- PR #7: `claude/textdoc-block-types` — the shipped lightweight `BlockType` step.
- `src/chopdiff/docs/text_doc.py` — current `TextDoc`/`Paragraph`/`Sentence` model.
