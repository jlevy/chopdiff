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
  sentence's exact end now comes from `flowmark.atomic.split_sentences_with_spans`
  (flowmark #47), which chopdiff adopts as its splitter — so sentence spans are exact for
  *all* content (verbatim prose is already exact even with the current splitter).
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

flowmark PR #47 (upcoming release) publishes the inline API this layer needs, so this is
mostly *adoption*, not new code (see the Addendum for the exact surface):

- **Link rollup.** `flowmark.ast.extract_links(doc)` returns `Link(text, url, title)` in
  document order with correct identity (reference links resolved, escapes honored,
  autolinks/images handled). It deliberately carries **no span** — marko has no inline
  offsets — so chopdiff recovers each link's exact `[start, end)` against its own source,
  the same source-mapping role it plays for blocks and sentences. This is genuinely
  nontrivial (duplicate link text, reference links with no inline span, code-embedded
  `[x](y)`), so chopdiff owns a reconciliation step aligning the ordered `extract_links`
  identities with located link spans (the `MARKDOWN_LINK` / `AUTOLINK` / `BARE_URL`
  patterns via `flowmark.atomic.iter_atomic_spans`). Expose `block.links`,
  `section.links` (union over the section's blocks, composing with Layer 2), and
  `TextDoc.links()` — each a `(Link, span)` once chopdiff attaches the span.
- **Link-aware sentences.** Adopt `flowmark.atomic.split_sentences_with_spans(text) ->
  list[SentenceSpan]` (where `SentenceSpan.text == source[start:end]` verbatim, and a
  boundary never bisects a link, code span, autolink, or URL) as chopdiff's splitter.
  This makes `Sentence` spans exact for *all* content — folding the previously-deferred
  "full exactness" into Layer 1 — and link↔sentence association falls out of the spans.
  chopdiff's pluggable `Splitter` becomes span-aware: the verbatim `SentenceSpan` feeds
  `Sentence.original_text`/offsets, and the normalized working `text` is derived as today.

**Reuse boundary (resolved by flowmark #47).** flowmark now publishes `flowmark.atomic`
(patterns + `iter_atomic_spans` + `split_sentences_with_spans`) and `flowmark.ast`
(`walk_elements`, `extract_links`, `Link`) as a stable, intentional surface, so chopdiff
imports those directly — no local regex copy and no internal imports. Requires bumping the
flowmark dependency to the release containing #47 (under the cool-off policy).

### API Changes

All additive:

- `TextDoc` retains `source_text`; `Paragraph.original_text` / `Sentence.original_text`
  become computed slices of it (offsets are the source of truth). `Sentence.text`
  (normalized, editable) stays stored.
- `Paragraph`/`Sentence`: computed `span`/end accessors; optional `Span` type.
- `TextDoc`: `block_at_offset`, `sentence_at_offset`, `sections`, `toc`, `links`, and
  (Layer 3) `blocks`.
- `Section` and `Block` dataclasses; a `(Link, span)` rollup type; `BlockType.list_item`
  / `BlockType.thematic_break`.
- Adopt `flowmark.atomic` / `flowmark.ast` (flowmark #47): span-aware sentence splitting
  (`split_sentences_with_spans`), `extract_links`, atomic patterns. Bump the flowmark
  dependency to the release containing #47.

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

- [ ] Bump the flowmark dependency to the release containing #47 (under the cool-off).
- [ ] Adopt `flowmark.atomic.split_sentences_with_spans` for exact, link-safe sentence
      spans (folds into Layer 1); decide default-vs-opt-in `Splitter`.
- [ ] Link rollup: reconcile `flowmark.ast.extract_links` identity with located link
      spans (`flowmark.atomic` patterns) → `block.links` / `section.links` /
      `TextDoc.links()`; link↔sentence association via spans.

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
- flowmark reuse: RESOLVED — flowmark #47 publishes `flowmark.atomic` and `flowmark.ast`;
  chopdiff imports them (no local copy). Remaining: should
  `flowmark.atomic.split_sentences_with_spans` become chopdiff's *default* `Splitter`, or
  stay opt-in (the splitter is already pluggable)? Adopting it by default makes spans
  exact everywhere but changes `Sentence.text` from normalized to verbatim unless
  chopdiff re-normalizes.

## References

- v0.3.0 (PRs #7, #9, #10): shipped `BlockType`, `iter_blocks`/`filtered`, `Offsets`,
  exact paragraph offsets, blank-line splitting, `estimate_tokens`.
- PR #1 `feature/extend-chopdiff-section-iteration` (`SectionDoc`/`FlexDoc`): prior art,
  reviewed and not merged.
- `src/chopdiff/docs/text_doc.py`: current `TextDoc` / `Paragraph` / `Sentence` /
  `Offsets` / `BlockType`.
- flowmark PR #47 — public inline API: `flowmark.atomic` (`ATOMIC_PATTERNS`,
  `iter_atomic_spans`, `SentenceSpan`, `split_sentences_with_spans`) and `flowmark.ast`
  (`walk_elements`, `extract_links`, `Link`), plus `flowmark_markdown()`. chopdiff adopts
  these for Layer 4.

## Addendum: flowmark inline API (implemented in flowmark PR #47)

The upstream changes this plan needed were proposed against flowmark and are implemented
in flowmark **PR #47** (a new public, versioned surface). chopdiff adopts it directly;
the proposals below are now realized as:

1. **`flowmark.atomic`** — public atomic-construct patterns and offset-preserving
   tokenizers: `AtomicPattern`, `ATOMIC_PATTERNS`, `ATOMIC_CONSTRUCT_PATTERN`,
   `MARKDOWN_INLINE_PATTERNS` (Markdown-only prose subset), the named patterns
   (`MARKDOWN_LINK`, `INLINE_CODE_SPAN`, `AUTOLINK`, `BARE_URL`, HTML/Jinja), and
   `AtomicSpan` / `AtomicWord` / `iter_atomic_spans` / `iter_atomic_words`. These give
   chopdiff exact link/code spans and atomic-aware tokenization with no local copy.

2. **`flowmark.atomic.split_sentences_with_spans(text) -> list[SentenceSpan]`** — the
   offset-preserving, atomic-aware sentence splitter. `SentenceSpan(text, start, end)` is
   verbatim (`text == source[start:end]`) and never bisects a link/code span/URL. This is
   exactly what chopdiff's `Sentence` spans need for full exactness (Layer 1 + Layer 4).

3. **`flowmark.ast`** — `walk_elements(element)` (generic read-only marko walk) and
   `extract_links(doc) -> list[Link]`, `Link(text, url, title)`. Correct link *identity*
   (reference links, escapes, autolinks, images).

**Deliberate boundary chopdiff inherits.** flowmark documents that `extract_links` /
`Link` carry **no span** by design (marko has no inline offsets), and that the
`MARKDOWN_LINK` regex is a *heuristic* for "what must not be broken," **not** a link
enumerator. So the one piece chopdiff still owns is *reconciling* link identity
(`extract_links`) with located link spans (`iter_atomic_spans` on the link patterns) to
produce `(Link, span)`. flowmark deliberately leaves this consumer-side; chopdiff names
the same boundary in Layer 4.

**Minor ergonomics note (raised on flowmark #47, non-blocking):** `AtomicSpan` exposes
`is_atomic` but not the matched pattern *name*, so a consumer reconciling links must
re-match the link patterns to tell a link span from a code span. An optional `name` (or a
`patterns=` filter that tags matches) on `iter_atomic_spans` would make consumer-side
link-span reconciliation cheaper, without crossing the identity-vs-span boundary.

chopdiff therefore depends on the flowmark release containing #47 (added under the
cool-off policy when Layer 4 is implemented).
