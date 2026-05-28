# Feature: A normalized document form for TextDoc — spans, sections, structural blocks, and derived views

**Date:** 2026-05-26 (revised 2026-05-27 to add the normalized-form view model)

**Author:** chopdiff maintainers

**Status:** Approved (verified against flowmark v0.7.0); revised with the normalized-form
direction (Phases 1–4 implemented on PR #12)

> **Design of record:** the definitive front-to-back design of the `TextDoc` data
> structure lives in [`docs/textdoc-spec.md`](../../../textdoc-spec.md). This document is
> the *implementation plan* (phases, beads, file-level steps) that builds toward it.

## Overview

`TextDoc` is block-aware as of v0.3.0 (it classifies each block by Markdown kind,
filters/iterates by type, and records exact start offsets), and PR #12 added exact spans,
a section hierarchy, an opt-in structural block tree, and inline-link rollups. This spec
consolidates those into one end-to-end design and makes explicit the model they are
converging on: a single **normalized form** of the document from which every other shape
is a **derived view**.

The normalized form is one representation — everything aligned by span into the retained
`source_text` — that captures the document's four structures at once:

1. **Original structure** — the verbatim `source_text` and exact `[start, end)` spans;
   every unit is a *view into it* (nothing is copied).
2. **Markdown structure** — the block tree (each block's top-level type, nesting, list
   items) and the inline elements (links, code spans, …) it contains, taken from the
   marko parse and *referenced*, not duplicated.
3. **Language structure** — paragraphs, sentences, words/wordtoks, and the inline and
   paragraph spacing between them, all with spans.
4. **Section structure** — the heading hierarchy and table of contents over the blocks.

From this one form, the shapes a caller wants are **calculated fields**, not stored state:

- a hierarchical document whose hierarchy *is* the section outline (governed by headings);
- that same content sliced by block type;
- all links (and other inline/block elements) rolled up per block, per section, and per
  document;
- tallies of any of the above — counts are `len()`/`Counter` over the *referenced items*,
  never a stored field.

**Design principle.** The normalized form must be clean and flexible enough that these
views are obvious one- or two-line derivations. If a view needs a lot of calculation or
is not obvious, that is the signal to refine the normalized form — *not* to add a bespoke
stored field or a parallel structure.

**Why this matters (the broader goal of `TextDoc`).** Consolidating Markdown block
structure, Markdown inline structure (links and other inline elements), language structure
(paragraphs, sentences, words, and the spacing between them), and document structure
(section headings, TOC) in *one* data structure — each piece a reference into the original
text by exact offset — is unusual: parsers give you an AST but not sentences, spans, or
rollups; NLP tools give you sentences but not Markdown structure or exact source mapping.
`TextDoc` is both at once, and because every unit is an offset-anchored view rather than a
copy, it is efficient on large documents. This makes it good for **textual analysis of a
fixed document** (spans, sizes, sections, link/element rollups, density-invariant tallies)
*and* as an **editable model**: edit units in place, then reassemble/serialize a clean,
normalized new document. Analysis and edit-then-serialize are two uses of the same form.

All of this extends `TextDoc` in place. We are explicitly **not** introducing a parallel
`BlockDoc`/`SectionDoc`/`FlexDoc`; the normalized form lives on `TextDoc`.

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
- **Markdown-correspondent block types:** `BlockType` maps one-to-one to Markdown block
  kinds, including **separate types for bullet (itemized) and ordered (enumerated)
  lists**.
- **A single top-level block type per block:** every blank-line/structural block has
  exactly one top-level classification (its outer element). Nesting is a secondary
  nuance that matters mainly for rollups, where a nested element is attributed to its
  enclosing top-level block by default (e.g. a table inside a blockquote counts as a
  blockquote, not a table). Descending into nested types is opt-in.
- **Derived views, not stored state:** the section-hierarchical document, block-type
  slices, and inline/block element rollups are all calculated fields over the normalized
  form; no view stores counts or duplicates content.
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

### The normalized form and derived views (central design)

The north star: **one normalized form on `TextDoc` that aligns the original, Markdown,
textual, and section structures by span, so `TextDoc` exposes everything a Markdown
parser does — block and inline structure, links, headings — plus what a parser does not:
sentences, exact spans, sizes, and rollups by section.** A consumer then has a single
object that is a superset of a Markdown AST *and* a structure/stats engine, where every
other shape is a derivation.

**What the normalized form holds (all aligned by span into one `source_text`):**

- the **structural block tree** (marko-aligned): each block's top-level `BlockType`,
  its span, and its children (list → `list_item`s; an item may hold nested blocks); a
  block references its inline elements (links, code spans) rather than copying them;
- the **paragraph/sentence** breakdown with spans (the textual structure);
- the retained `source_text` so any `original_text` is a computed slice.

The block tree and the paragraph/sentence breakdown are **two views of the same form**,
both indexing the same `source_text`. They are not competing canonical models: the
blank-line `Paragraph`/`Sentence` view remains what the diff/window/wordtok code edits,
while the structural block tree is the Markdown-structure backbone for slicing and
rollups. Because both are views, no diff/window boundaries have to change — this resolves
the earlier "overlay vs. re-found" tension (see Open Questions): keep both as views; do
**not** force a re-founding of `TextDoc`'s editing unit on the structural parse.

**Views derived from the form (calculated, never stored):**

- **Section-hierarchical document** — group blocks by the heading hierarchy (Layer 2).
  `Section` references its blocks; its content, span, and sizes are computed.
- **Slice by block type** — filter blocks/sections by top-level `BlockType`
  (`iter_blocks`/`filtered`, and the same predicate over `blocks()` / a section's blocks).
- **Element rollups** — links (and, in general, any inline or block element) gathered per
  block, per section (union over the section's blocks), and per document, by referencing
  the same located elements; `link → sentence` falls out of overlapping spans.
- **Tallies** — `len(...)` / `Counter(b.block_type for b in …)` over whichever referenced
  collection (a section's blocks, the whole-doc block tree, a block's links). Counts are
  always derived; the data model stores items, not totals.

This is the bar for "easy to drive": each of the above is a one- or two-line derivation.
Where it is not (e.g. structural items were only reachable for the whole document, not a
section), that is a normalized-form gap to close, not a place for a stored count.

### Block-type model

`BlockType` corresponds one-to-one to Markdown block kinds, so a `TextDoc` classification
reads like the Markdown structure it came from.

- **Bullet vs. ordered lists are distinct types.** marko's `List` carries `ordered`, so
  an itemized list and an enumerated list classify differently. Chosen, additive shape:
  keep `list` meaning the **bullet/unordered** list (its current value) and add
  `ordered_list` for the enumerated list; `list_item` is shared by both (an item's
  ordered-ness is a property of its parent list). This is a behavior change for callers
  who matched `BlockType.list` expecting *both* kinds — called out as a minor-version
  note. (Symmetric rename to `bullet_list`/`ordered_list` is the alternative but breaks
  the shipped `list` name; not chosen.)
- **One top-level type per block.** Each blank-line/structural block has exactly one
  top-level `BlockType`, taken from its **outer** element — already how `classify_block`
  works (a blockquote wrapping a table classifies as `blockquote`). This single
  classification is what `iter_blocks`/`filtered`/section slicing and the default rollups
  key on.
- **Nesting is a secondary nuance, for rollups.** Inside the structural tree a block keeps
  its own type (the table inside the blockquote is still a `table` `Block` in the tree),
  but a *tally or element rollup* attributes nested content to its enclosing top-level
  block **by default** — a table inside a blockquote counts as a blockquote. Descending
  into nested types (counting that inner table, or its links, separately) is an explicit,
  opt-in traversal of `children`, not the default. This keeps the common case (counts by
  top-level kind) trivial while leaving the rare nested case reachable.

Enum (Markdown-correspondent): `heading`, `paragraph`, `list` (bullet), `ordered_list`,
`list_item`, `table`, `code`, `blockquote`, `html`, `footnote`, `thematic_break`.

**List density (tight vs. loose) must not change tallies.** A list written densely (no
blank lines between items) and the same list written sparsely (blank lines between items)
are semantically the same list; counts of lists and items must be identical either way.
Today they are not: blank-line splitting makes a tight list one `list` block with no
per-item access, while a loose list becomes several single-item `list` blocks. The
normalized form removes this difference:

- In the structural tree, a list **always decomposes into `list_item` children
  regardless of density** — a loose list is *one* `list`/`ordered_list` block whose items
  happen to be blank-line-separated, not N separate lists. So `len(list.children)` and
  any block-type tally are density-invariant. (This supersedes the current "loose list
  splits / nesting flattens" limitation, which lived in the blank-line view.)
- Density is recorded as metadata, not structure. Chosen approach: a `tight: bool` flag
  (CommonMark's notion — a list is loose if any of its items are blank-line-separated or
  contain multiple block children). The per-item variant the requirement suggests —
  flagging each `list_item` as dense/loose relative to its siblings — is the same
  information at finer grain; we carry it on the **list** by default (simpler,
  CommonMark-aligned) and can expose a derived `list_item.tight` if a mixed-density list
  ever needs exact round-tripping. Either way the flag never enters a tally.

Note this lives in the **structural tree** (the normalized Markdown view). The blank-line
`Paragraph` editing view still sees loose-list items as separate paragraphs — that is the
editing unit, not the tally unit — which is why density-invariant counting belongs to the
block tree, not to `paragraphs`.

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
  sentence's exact end now comes from `flowmark.atomic_spans.split_sentences_with_spans`
  (flowmark v0.7.0), which chopdiff adopts as its splitter — so sentence spans are exact for
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
- `BlockType` gains `list_item`, `thematic_break`, and `ordered_list` (see Block-type
  model); a `list` block holds `list_item` children, and ordered-ness is the parent
  list's type.

Exact sub-paragraph offsets are the open technical risk. Spike two approaches on a
corpus before committing:

- marko line-numbers plus a source-mapping pass over a single parse, or
- a small line-oriented block scanner (fenced code, ATX/setext headings, list items,
  blockquotes, tables, thematic breaks, paragraphs), cross-checked against marko.

Document-level paragraph offsets are already exact, so this only needs to be correct for
structure *within* and *across* blank-line boundaries.

### Layer 4 — Inline elements (links) and link-aware sentences

flowmark v0.7.0 publishes the inline API this layer needs, so this is
mostly *adoption*, not new code (see the Addendum for the exact surface):

- **Link rollup.** `flowmark.markdown_ast.extract_links(doc)` returns `Link(text, url, title)` in
  document order with correct identity (reference links resolved, escapes honored,
  autolinks/images handled). It deliberately carries **no span** — marko has no inline
  offsets — so chopdiff recovers each link's exact `[start, end)` against its own source,
  the same source-mapping role it plays for blocks and sentences. This is genuinely
  nontrivial (duplicate link text, reference links with no inline span, code-embedded
  `[x](y)`), so chopdiff owns a reconciliation step aligning the ordered `extract_links`
  identities with located link spans (the `MARKDOWN_LINK` / `AUTOLINK` / `BARE_URL`
  patterns via `flowmark.atomic_spans.iter_atomic_spans`). Expose `block.links`,
  `section.links` (union over the section's blocks, composing with Layer 2), and
  `TextDoc.links()` — each a `(Link, span)` once chopdiff attaches the span.
- **Link-aware sentences.** Adopt `flowmark.atomic_spans.split_sentences_with_spans(text) ->
  list[SentenceSpan]` (where `SentenceSpan.text == source[start:end]` verbatim, and a
  boundary never bisects a link, code span, autolink, or URL) as chopdiff's splitter.
  This makes `Sentence` spans exact for *all* content — folding the previously-deferred
  "full exactness" into Layer 1 — and link↔sentence association falls out of the spans.
  chopdiff's pluggable `Splitter` becomes span-aware: the verbatim `SentenceSpan` feeds
  `Sentence.original_text`/offsets, and the normalized working `text` is derived as today.

**Reuse boundary (resolved by flowmark v0.7.0).** flowmark now publishes `flowmark.atomic_spans`
(patterns + `iter_atomic_spans` + `split_sentences_with_spans`) and `flowmark.markdown_ast`
(`walk_elements`, `extract_links`, `Link`) as a stable, intentional surface, so chopdiff
imports those directly — no local regex copy and no internal imports. Requires bumping the
flowmark dependency to flowmark v0.7.0 (under the cool-off policy).

### API Changes

All additive:

- `TextDoc` retains `source_text`; `Paragraph.original_text` / `Sentence.original_text`
  become computed slices of it (offsets are the source of truth). `Sentence.text`
  (normalized, editable) stays stored.
- `Paragraph`/`Sentence`: computed `span`/end accessors; optional `Span` type.
- `TextDoc`: `block_at_offset`, `sentence_at_offset`, `sections`, `toc`, `links`, and
  (Layer 3) `blocks`.
- `Section` and `Block` dataclasses; a `(Link, span)` rollup type; `BlockType.list_item`
  / `BlockType.thematic_break` / `BlockType.ordered_list`.
- Derived-view helpers (all computed, no stored counts): per-section structural blocks so
  block-type slices and element rollups scope to a section; `Counter`-style tallies over
  referenced items at block/section/document level.
- Adopt `flowmark.atomic_spans` / `flowmark.markdown_ast` (flowmark v0.7.0): span-aware sentence splitting
  (`split_sentences_with_spans`), `extract_links`, atomic patterns. Bump the flowmark
  dependency to flowmark v0.7.0.

## Implementation Plan

Each phase is independently shippable and additive. Phases 1–2 need no new dependency;
Phase 4 (and the splitter adoption) needs the flowmark v0.7.0 bump (see Addendum).

**Status:** Phases 1–4 are implemented on PR #12 (exact spans, sections/TOC/size rollups,
the opt-in structural block tree with `list_item`/`thematic_break`, and inline-link
rollups with link-aware sentence spans). Phase 5 below is the new normalized-form
consolidation work (Markdown-correspondent block types, density-invariant lists, and the
derived element/tally views).

### Phase 1 — Exact spans + offset mapping  (bead `chopdiff-0tgl`)

Files: `src/chopdiff/docs/text_doc.py`, `sizes.py`; tests in `tests/docs/test_offsets.py`.

- [ ] Add `TextDoc.source_text: str` set in `from_text`. Define the derived/synthetic
      policy: `sub_doc`/`filtered` carry the **same** `source_text` (their offsets index
      it); `from_wordtoks`/`append_sent` set `source_text` to the reassembled text.
- [ ] Make `Paragraph.original_text` a computed property `source_text[start:end]`
      (recommended) — or keep stored; decide here (Open Questions). Keep `Sentence.text`
      stored/editable; compute `Sentence.original_text` from the span.
- [ ] Add end offsets: `Paragraph.span`/`end_offset`, `Sentence.span` (doc- and
      block-relative). Optional frozen `Span(start, end)`.
- [ ] Add `TextDoc.block_at_offset(o) -> Paragraph | None` and `sentence_at_offset(o) ->
      SentIndex | None` (search over spans).
- [ ] Tests: round-trip `source_text[p.span] == p.original_text`; mapping consistency;
      derived/synthetic-doc behavior. (Sentence spans exact for verbatim prose now; full
      exactness arrives with the Phase 4 splitter.)

### Phase 2 — Sections, TOC, and rolled-up stats  (bead `chopdiff-08uq`)

- [ ] `Section` dataclass: heading `Paragraph`, `level`, the blocks it owns (from this
      heading to the next heading of level ≤ this), child `Section`s, and a span.
- [ ] `TextDoc.sections() -> list[Section]` (tree, single pass over `iter_blocks`
      maintaining a heading-level stack) and `toc()` (flattened title/level/span).
- [ ] `Section.size(unit, subtree=True)` = `TextDoc(section_blocks).size(unit)` (reuse,
      no new rollup logic); `Section.size_summary()`; `TextDoc.section_size_tree(units=)`
      renderer (mirrors `TextNode.structure_summary`).
- [ ] Port the `read_time` util + an `analyze_doc`-style example onto sections.
- [ ] Tests: ATX/setext hierarchy, `#`-in-code excluded; rolled-up size == sum over
      subtree blocks; root section size == whole-doc size.

### Phase 3 — Structural block tree, opt-in  (bead `chopdiff-ck9i`)

- [ ] Spike marko line-numbers + source-mapping vs a line-oriented block scanner for
      sub-paragraph exact offsets; cross-check structure against marko on the corpus.
- [ ] `Block` dataclass: `type`, span, `level`, `children`; `BlockType.list_item` +
      `BlockType.thematic_break`. `TextDoc.blocks()` (lazy, cached).
- [ ] Align each block to its marko node as an **overlay** (the blank-line `Paragraph`
      list stays the diff/window/wordtok unit; canonical switch is gated, see Design).
- [ ] Golden tests: block tree types/spans/nesting; tight-list items; code-with-internal-
      blank-line is one block.

### Phase 4 — Inline links + link-aware sentences  (bead `chopdiff-43ji`)

- [ ] Dependency: require `flowmark>=0.7.0`; advance `[tool.uv] exclude-newer` to
      ≥ 2026-06-10 (14 days after the 2026-05-27 release) or add a reviewed
      `exclude-newer-package` exception; re-lock (`pathspec` joins the tree); record in
      `SUPPLY-CHAIN-SECURITY.md`.
- [ ] Adopt `flowmark.atomic_spans.split_sentences_with_spans` as the sentence splitter
      (default vs opt-in — Open Questions): populate `Sentence` spans + `original_text`
      exactly; derive normalized `text`. This makes Phase 1's sentence spans exact for all
      content.
- [ ] Link rollup `Link(text, url, title, span)`: `flowmark.markdown_ast.extract_links`
      for identity, reconciled in document order with `iter_atomic_spans` link spans
      (filter `name in {markdown_link, autolink, bare_url}`); reference links get identity
      but no exact span. Expose `block.links`, `section.links`, `TextDoc.links()`.
- [ ] Link↔sentence association via spans. Tests: identity+span rollup; sentence spans
      never bisect a link; reconciliation on reference links and code-embedded brackets.

### Phase 5 — Normalized form: block-type model + derived views

Folds the structural block tree and the section/element rollups into one normalized form,
closing the gaps that made the views non-trivial.

- [ ] Block types correspond to Markdown kinds: add `BlockType.ordered_list`; `list`
      becomes bullet-only. Carry ordered-ness from marko's `List.ordered`. Minor-version
      note for callers matching `BlockType.list` for both kinds.
- [ ] Density-invariant lists in the structural tree: a list always decomposes into
      `list_item` children regardless of blank-line spacing (loose list = one list block,
      not N); record `tight: bool` on the list (CommonMark semantics). Tallies of lists
      and items become identical for dense vs. sparse input. Tests: dense and loose
      variants of the same list produce identical block/item counts.
- [ ] Per-section structural blocks: scope `blocks()` to a section (e.g.
      `Section.blocks()`) so block-type slices and element rollups work per section, not
      only whole-document.
- [ ] Derived rollups/tallies (no stored counts): a helper that gathers any block-type
      slice or inline-element set at block/section/document level, and counts as
      `len()`/`Counter` over the referenced items. Default rollups attribute nested
      content to the enclosing top-level block; descending into `children` is opt-in.
- [ ] End-to-end example exercising every view over one document: section tree,
      slice-by-block-type, links/elements per section, and density-invariant tallies.

## Testing Strategy

- Span invariants: `original_text[p.span] == p.original_text`; verbatim
  `original_text[s.span] == s.text`; non-overlapping, ordered spans.
- Mapping: `block_at_offset`/`sentence_at_offset` agree with the spans across the doc.
- Sections: ATX + setext levels; `#` inside fenced code never starts a section; nesting.
- Structural parse: cross-checked against marko on the corpus in
  `tests/docs/test_block_types.py`; list-item and nesting cases.

## Rollout Plan

- Phases 1–4 shipped together on PR #12 (additive; `BlockType` gained `list_item` /
  `thematic_break`).
- Phase 5 ships as a minor release. Adding `BlockType.ordered_list` and making `list`
  bullet-only is the one semi-breaking note (callers matching `BlockType.list` for *both*
  list kinds now miss ordered lists); everything else — density-invariant lists, per-
  section blocks, derived rollups — is additive.

## Open Questions

Most of the original questions are now decided (implemented on PR #12 or resolved by the
normalized-form direction):

- Spans: RESOLVED — computed accessors; `original_text` is a computed slice of the
  retained `source_text` (exact and memory-efficient). Synthetic docs fall back to the
  reassembled text.
- Sections: RESOLVED — both a nested tree (`sections()`) and a flat list (`toc()`).
- Counts / tallies: RESOLVED — never stored. The data model references items; every count
  is a derived `len()`/`Counter`. A view that is hard to derive signals a normalized-form
  gap to close, not a stored field to add.
- Block types: RESOLVED — Markdown-correspondent, with `ordered_list` distinct from `list`
  (bullet); one top-level type per block; nested content rolls up under its enclosing
  top-level block by default.
- Alignment (overlay vs. canonical): RESOLVED — the structural block tree and the
  blank-line `Paragraph`/`Sentence` breakdown are **both views** of one normalized form.
  The `Paragraph`/`Sentence` view stays the diff/window/wordtok editing unit, so no block
  boundaries change and there is no forced re-founding/blast-radius event.
- flowmark reuse: RESOLVED — chopdiff imports `flowmark.atomic_spans` /
  `flowmark.markdown_ast` (flowmark v0.7.0). `split_sentences_with_spans` is the default
  splitter; `Sentence.text` stays normalized while `original_text`/spans are verbatim.

Still open:

- List density: confirm `tight` belongs on the **list** (default, CommonMark-aligned) vs.
  a per-`list_item` dense flag for exact round-tripping of mixed-density lists.
- Multi-paragraph / loose list items: how to represent an item that contains several
  block children (the item's `children` are blocks; spans cover the whole item).
- Rollup ergonomics: a single generic element-rollup helper vs. typed accessors
  (`links()`, future `tables()`, …) layered over it.

## References

- v0.3.0 (PRs #7, #9, #10): shipped `BlockType`, `iter_blocks`/`filtered`, `Offsets`,
  exact paragraph offsets, blank-line splitting, `estimate_tokens`.
- PR #1 `feature/extend-chopdiff-section-iteration` (`SectionDoc`/`FlexDoc`): prior art,
  reviewed and not merged.
- `src/chopdiff/docs/text_doc.py`: current `TextDoc` / `Paragraph` / `Sentence` /
  `Offsets` / `BlockType`.
- flowmark v0.7.0 — public inline API: `flowmark.atomic_spans` (`ATOMIC_PATTERNS`,
  `iter_atomic_spans`, `SentenceSpan`, `split_sentences_with_spans`) and `flowmark.markdown_ast`
  (`walk_elements`, `extract_links`, `Link`), plus `flowmark_markdown()`. chopdiff adopts
  these for Layer 4.

## Addendum: flowmark inline API (released in flowmark v0.7.0)

The upstream changes this plan needed shipped in flowmark **v0.7.0** (2026-05-27) as a
public, versioned surface. chopdiff adopts it directly. Verified against the v0.7.0 tag
(see Validation below); note the module names differ from the original PR #47 branch:

1. **`flowmark.atomic_spans`** — atomic-construct patterns and offset-preserving
   tokenizers: `AtomicPattern`, `ATOMIC_PATTERNS`, `ATOMIC_CONSTRUCT_PATTERN`,
   `MARKDOWN_INLINE_PATTERNS`, named patterns (`MARKDOWN_LINK`, `INLINE_CODE_SPAN`,
   `AUTOLINK`, `BARE_URL`, HTML/Jinja), and `AtomicSpan` / `AtomicWord` /
   `iter_atomic_spans` / `iter_atomic_words`. `AtomicSpan` is
   `(text, start, end, is_atomic, name)` — it **carries the matched pattern `name`**
   (e.g. `"markdown_link"`, `"inline_code_span"`, `"autolink"`, `"bare_url"`), so a
   consumer filters atomic spans to links by name with no re-matching.

2. **`flowmark.atomic_spans.split_sentences_with_spans(text) -> list[SentenceSpan]`** —
   the offset-preserving, atomic-aware sentence splitter. `SentenceSpan(text, start, end)`
   is verbatim (`text == source[start:end]`) and never bisects a link/code span/URL —
   exactly what chopdiff's `Sentence` spans need for full exactness (Layer 1 + Layer 4).

3. **`flowmark.markdown_ast`** — `walk_elements(element)` (generic read-only marko walk),
   `extract_links(doc) -> list[Link]`, `Link(text, url, title)`. Correct link *identity*
   (reference links, escapes, autolinks, images).

**Deliberate boundary chopdiff inherits.** flowmark documents that `extract_links` /
`Link` carry **no span** by design (marko has no inline offsets), and that the
`MARKDOWN_LINK` regex is a *heuristic*, **not** a link enumerator. So the one piece
chopdiff owns is *reconciling* link identity (`extract_links`) with located link spans
(`iter_atomic_spans` filtered by `name`) to produce `(Link, span)`. The `AtomicSpan.name`
field (added in v0.7.0) makes this cheap; chopdiff still aligns the ordered identity list
with the located spans (reference links have no inline span, so they get no exact span).

**Dependency impact.** Requires `flowmark>=0.7.0`, which pulls in `pathspec` transitively
(marko/regex/strif are already chopdiff deps). flowmark 0.7.0 was released 2026-05-27,
**newer than chopdiff's cool-off cutoff (2026-05-11)**, so adding it requires advancing
`[tool.uv] exclude-newer` to ≥ 2026-06-10 (14 days after release) or a reviewed
`exclude-newer-package` exception for flowmark, per `SUPPLY-CHAIN-SECURITY.md`. This gates
Layer 4 implementation, not Layers 1–2 (which do not need the new API beyond the splitter;
the splitter adoption can wait for the dependency bump).

## Validation (flowmark v0.7.0 tested)

Exercised the released v0.7.0 API (imported the v0.7.0 source against chopdiff's
environment, which already has marko) on a Markdown sample with a titled link, inline
code, a bare URL, and multiple sentences. Confirmed:

- `flowmark.atomic_spans.split_sentences_with_spans` returns verbatim `SentenceSpan`s that
  round-trip (`source[start:end] == text`) and do **not** bisect a link or code span — so
  it can back chopdiff's exact `Sentence` spans directly.
- `iter_atomic_spans` yields atomic spans tagged with `name`
  (`markdown_link` / `inline_code_span` / `autolink` / `bare_url` / `html_open_tag` /
  `html_close_tag`), giving exact, typed link/code spans.
- `flowmark.markdown_ast.extract_links` returns correct `Link(text, url, title)` identity
  (including bare-URL autolinks), with no span — matching the documented boundary.
- Field shapes: `SentenceSpan(text, start, end)`, `AtomicSpan(text, start, end, is_atomic,
  name)`, `Link(text, url, title)`.

Conclusion: the plan is aligned with the shipped API; the only consumer-side work is
the link identity↔span reconciliation (Phase 4), which `AtomicSpan.name` makes
straightforward.
