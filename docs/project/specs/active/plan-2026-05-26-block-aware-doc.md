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
- A rollup of inline links (link text, URL, title, span) per block, section, and document.
- Link-aware sentences: sentence spans never bisect a link, code span, or inline HTML,
  and each link maps to the sentence that contains it.
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

### Guiding architecture: align TextDoc with the Markdown parse

The north star: **align `TextDoc`'s block/paragraph/sentence structure with the marko
parse so `TextDoc` exposes everything a Markdown parser does — block and inline
structure, links, headings — plus what a parser does not: sentences, exact spans, sizes,
and rollups by section.** Each block knows (or holds a reference to) its marko node, so
type, inline elements, and structure come straight from the parser while chopdiff adds
the analytics on top. A consumer then has a single object that is a superset of a
Markdown AST *and* a structure/stats engine.

The layers below are the incremental, low-risk path toward this. Spans and sections are
pure additions; the structural-block parse (Layer 3) is where `TextDoc`'s blocks become
aligned with marko's blocks (a list is one block with item children; a fenced code block
is one block regardless of internal blank lines). Alignment is introduced as an **overlay
first** — the blank-line `Paragraph` list stays the unit the diff/window/wordtok code
uses — so it can be validated against the existing model. Re-founding `TextDoc` on the
single parse (making the aligned blocks the canonical unit) is the one change with real
blast radius, because it shifts block boundaries for lists and code that diffs and
sliding windows see; it stays gated behind the Layer 3 spike and explicit sign-off.

### Layer 1 — Exact spans, with `original_text` computed from one retained source

Make the **offsets the single source of truth** and retain the document text once on
`TextDoc`. Then `original_text` is a *computed* slice rather than a stored per-unit copy:

- `TextDoc` keeps the original `source_text`; each `Paragraph`/`Sentence` carries an
  exact span (`offsets` + an end). `original_text` becomes a computed property
  (`source_text[start:end]`) — exact by construction, unable to drift — and the
  duplicated paragraph- and sentence-level string copies go away (a memory win on large
  docs). `Sentence` still stores its normalized, *editable* `text` (what
  wordtoks/diffs/reassemble use); only the verbatim `original_text` is computed.
- Spans: `Paragraph.span` / `Sentence.span` `-> (start, end)`, plus
  `TextDoc.block_at_offset(o)` / `sentence_at_offset(o)` over those spans.
- Exactness needs an exact **end** per unit. A paragraph's end is already exact; a
  sentence's end needs boundary-preserving splitting (Layer 4) — until then sentence
  spans are exact for verbatim prose and fall back for irregular internal whitespace
  (e.g. tables).
- Derived/synthetic docs: `sub_doc` / `filtered` keep a reference to the same
  `source_text` (their spans still point into it), so computed `original_text` keeps
  working. Docs built from synthetic content (`from_wordtoks`, `append_sent`) have no
  source backing, so there `source_text` is the reassembled working text (or
  `original_text` is reported unavailable).

Trade-off: this couples a unit to its document's `source_text` (a `Paragraph` is no
longer fully self-contained), which matches a "unit is a view into its document" model.
The alternative — keep `original_text` stored — is simpler but duplicates strings.
Optionally add a small frozen `Span(start, end)` type. Decide the stored-vs-computed
choice in Phase 1 (see Open Questions).

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

### Layer 4 — Inline elements (links) and link-aware sentences

The aligned marko parse already carries inline structure, so this is mostly exposure.
Reuse flowmark's **public** `flowmark_markdown()` parser (already a dependency): a text
block's inline AST exposes `inline.Link` (`dest` = URL, `title`, child `RawText` = link
text), `inline.Url` (bare/autolinks), and `inline.CodeSpan`.

- **Link rollup.** Collect a `Link(text, url, title, span)` for every link; expose
  `block.links`, `TextDoc.links()`, and — composing with Layer 2 — `section.links` (the
  union over the section's blocks). marko decides what *is* a link (handling reference
  links, autolinks, and `[x](y)` inside code spans correctly); the exact source span is
  recovered by locating the link in the block text, the same way blocks and sentences
  are located, so links keep chopdiff's exact-reference guarantee.
- **Link-aware sentences.** Today `split_sentences_regex` normalizes whitespace and is
  not atomic-aware, so a sentence can bisect link text or be confused by URL
  punctuation. Add an offset-preserving, atomic-aware splitter that treats links, code
  spans, inline HTML, and bare URLs as unbreakable tokens, applies the existing
  end-of-sentence heuristic only between tokens, and keeps source offsets. This makes
  sentence spans exact *and* guarantees they never split a link; link↔sentence
  association then falls out of the spans (a link belongs to the sentence whose span
  contains it). It also resolves the best-effort sentence-span limitation from Layer 1.

**Reuse boundary.** Only flowmark's public `flowmark_markdown()` is safe to import.
`atomic_patterns` (the link/code-span/URL/tag regexes) and the inline-traversal helpers
are flowmark *internals* (not in `__all__`); either export them from flowmark upstream
(first-party, clean) or keep a small local copy of those regexes in chopdiff. Do not
import flowmark internals directly.

### API Changes

All additive:

- `TextDoc` retains `source_text`; `Paragraph.original_text` / `Sentence.original_text`
  become computed slices of it (offsets are the source of truth). `Sentence.text`
  (normalized, editable) stays stored.
- `Paragraph`/`Sentence`: computed `span`/end accessors; optional `Span` type.
- `TextDoc`: `block_at_offset`, `sentence_at_offset`, `sections`, `toc`, `links`, and
  (Layer 3) `blocks`.
- `Section` and `Block` dataclasses; `Link` record; `BlockType.list_item` /
  `BlockType.thematic_break`; an atomic-aware sentence `Splitter`.

## Implementation Plan

### Phase 1 — Spans and mapping

- [ ] Retain `TextDoc.source_text`; make `Paragraph`/`Sentence` `original_text` computed
      slices (offsets as source of truth); keep `Sentence.text` editable.
- [ ] Computed `span`/end accessors; `block_at_offset` / `sentence_at_offset` + round-trip tests.
- [ ] Exact for verbatim sentences now; full exactness lands with the Layer 4 splitter.
- [ ] Define `original_text` behavior for derived/synthetic docs (`sub_doc`/`filtered`/
      `from_wordtoks`/`append_sent`).

### Phase 2 — Sections and TOC

- [ ] `Section` type; `TextDoc.sections()` / `toc()` over heading blocks.
- [ ] Port a `read_time` util and an `analyze_doc`-style example onto this.

### Phase 3 — Structural block tree (opt-in)

- [ ] Spike marko source-mapping vs a block scanner for sub-paragraph exact offsets.
- [ ] `Block` tree with `list_item` + nesting; `TextDoc.blocks()`; golden tests.
- [ ] Align blocks with the marko parse as an overlay (each block references its node).

### Phase 4 — Inline links and link-aware sentences

- [ ] `Link(text, url, title, span)` rollup via `flowmark_markdown()` + span location;
      `block.links` / `section.links` / `TextDoc.links()`.
- [ ] Atomic-aware, offset-preserving sentence splitter (links/code/HTML/URLs atomic);
      exact, link-safe sentence spans; link↔sentence association.
- [ ] Decide flowmark atomic-pattern reuse (export upstream vs local copy).

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
- `original_text` stored per unit vs computed from a retained `TextDoc.source_text`
  (recommended: computed — exact and memory-efficient, at the cost of coupling units to
  their document and needing a fallback policy for synthetic docs)?
- Alignment: keep the marko-aligned blocks as an overlay indefinitely, or eventually
  re-found `TextDoc`'s canonical unit on the single parse (changing list/code block
  boundaries that diffs and sliding windows see)?
- Reuse flowmark's `atomic_patterns` by exporting them from flowmark (first-party) or by
  keeping a small local copy in chopdiff? Should the atomic-aware splitter become the
  default `Splitter` or stay opt-in (the splitter is already pluggable)?

## References

- v0.3.0 (PRs #7, #9, #10): shipped `BlockType`, `iter_blocks`/`filtered`, `Offsets`,
  exact paragraph offsets, blank-line splitting, `estimate_tokens`.
- PR #1 `feature/extend-chopdiff-section-iteration` (`SectionDoc`/`FlexDoc`): prior art,
  reviewed and not merged.
- `src/chopdiff/docs/text_doc.py`: current `TextDoc` / `Paragraph` / `Sentence` /
  `Offsets` / `BlockType`.
- flowmark (public `flowmark_markdown()`), and its internal
  `linewrapping/atomic_patterns.py` (link/code-span/URL regexes) and
  `transforms/doc_transforms.py` (inline traversal) — prior art for inline handling.

## Addendum: Proposed upstream changes to flowmark

Layer 4 (and the marko alignment generally) wants to reuse flowmark rather than
re-implement Markdown inline handling. flowmark already has everything needed, but the
useful pieces live in internal modules not in its public `__all__`. Since flowmark and
chopdiff are both first-party, the cleanest path is a small, intentional public surface
in flowmark. Concrete proposals, cross-referenced to flowmark v0.6.5 source:

1. **Publish the atomic-construct patterns.** `src/flowmark/linewrapping/atomic_patterns.py`
   defines `AtomicPattern` plus `MARKDOWN_LINK`, `INLINE_CODE_SPAN`, HTML/Jinja tag and
   comment patterns, the ordered `ATOMIC_PATTERNS` tuple, and the combined
   `ATOMIC_CONSTRUCT_PATTERN` regex. These encode exactly "what must not be split
   mid-construct" — what chopdiff needs for link-safe sentence splitting and exact
   link/code spans. Re-export them from the package (e.g. a public `flowmark.atomic`
   submodule and `__all__` entries) so chopdiff uses one source of truth instead of a
   drifting local copy.

2. **Offer offset-preserving, atomic-aware sentence splitting.** The public
   `src/flowmark/linewrapping/sentence_split_regex.py:split_sentences_regex` does
   `text.split()` then `" ".join(...)`, so it loses whitespace and offsets and is not
   atomic-aware (it can split inside a link). flowmark already tokenizes atomically for
   wrapping. Propose a public, offset-preserving API:
   - `iter_atomic_tokens(text) -> Iterable[(text, start, end, is_atomic)]` over
     `ATOMIC_CONSTRUCT_PATTERN`, and/or
   - `split_sentences_with_spans(text) -> list[(text, start, end)]` that applies the
     existing end-of-sentence heuristic only between atomic tokens and never splits one.
   flowmark is the natural home (it owns both sentence splitting and the atomic patterns);
   chopdiff would consume these directly for exact, link-safe `Sentence` spans.

3. **Publish AST traversal + link extraction.** `src/flowmark/transforms/doc_transforms.py`
   has `transform_tree(element, transformer)` (a robust marko walk) and
   `_collect_inline_segments(...)`, and `src/flowmark/formats/flowmark_markdown.py`
   exposes the configured parser (GFM + footnote). Export a read-only inline iterator
   (e.g. `iter_inline(element)`) and a convenience `extract_links(doc) ->
   list[Link(text, url, title)]` built on the same traversal, so consumers don't
   re-implement AST walks that must track GFM/footnote element types.

4. **Commit to a stable, versioned public surface.** Because chopdiff will depend on the
   above, the exported names should be an intentional API (a `flowmark.atomic` /
   `flowmark.ast` submodule and `__all__`), not just de-underscored internals, so
   chopdiff is not coupled to flowmark's internal refactors.

Until these land, chopdiff keeps the Layer 4 fallback: use only the public
`flowmark_markdown()` and hold a small local copy of the link/code-span/URL regexes.
These proposals should be filed as flowmark issues (first-party) and, ideally, a small
flowmark PR exporting (1) and (3) — which unblock most of Layer 4 — with (2) as the
larger follow-up.
