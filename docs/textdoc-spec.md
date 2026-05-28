# TextDoc: Design Specification

**Status:** Definitive design of the `TextDoc` data structure. This is the front-to-back
reference; dated plans under `docs/project/specs/` describe the incremental work toward it.

## 1. Purpose

`TextDoc` is a single in-memory data structure that consolidates, for one document, the
several structures people normally need separate tools for — and anchors every piece back
to the original text by exact character offset.

It holds, at once:

- **Markdown block structure** — headings, paragraphs, lists (and list items), tables,
  code, blockquotes, HTML blocks, footnotes, thematic breaks.
- **Markdown inline structure** — links (and other inline elements: code spans, inline
  HTML).
- **Language structure** — paragraphs, sentences, words/wordtoks, and the inline and
  paragraph **spacing** between them.
- **Document structure** — the section hierarchy implied by headings, and a TOC.

This combination is unusual. A Markdown parser gives a block/inline AST but no sentences,
sizes, or section rollups. An NLP toolkit gives sentences but no Markdown structure and no
exact source mapping. `TextDoc` is both at once, and because every unit is an
offset-anchored *view* into one retained source string rather than a copy, it stays
efficient on large documents.

## 2. Goals

- **One consolidating structure.** Markdown block + inline + language + document structure
  in a single object, not four tools stitched together.
- **Exact source anchoring.** Every unit references the original text by exact
  `[start, end)` offset; nothing is copied, nothing drifts; spans round-trip verbatim.
- **Normalized form, derived views.** The structure is one normalized form; section
  hierarchy, block-type slices, element rollups, and tallies are *calculated fields* over
  it — never stored state. If a view is hard to derive, refine the form, don't add a field.
- **Markdown-correspondent block types.** Block types map one-to-one to Markdown kinds
  (bullet vs. ordered lists distinct); each block has one top-level type; nesting matters
  mainly for rollups.
- **Density-invariant lists.** Tight vs. loose lists are the same list; they must produce
  identical tallies.
- **Section rollups.** A hierarchical document keyed by headings, sliceable by block type,
  with links/elements and sizes rolled up per section and per document.
- **Dual use.** Good for analysis of a fixed document *and* as an editable model: modify
  units in place, then reassemble/serialize a clean, normalized new document.
- **LLM/agent-friendly and Python-first, Rust-portable.** Ergonomic to drive from Python
  (and from LLM/agent code), with a clean, tight spec and thorough tests precise enough
  that a Rust port is straightforward — several underlying components (regex, diffing) are
  already Rust-backed.
- **Minimal dependencies; additive.** Stays lightweight; existing diff/window/wordtok
  behavior and APIs are preserved.

## 3. The normalized form

`TextDoc` is **one normalized form**; every other shape is a **derived view** — a
calculated field over the form, not separately stored state.

The form is everything aligned by span into a single retained `source_text`:

1. **Original structure** — the verbatim `source_text` plus exact `[start, end)` spans.
   Each unit's `original_text` is a computed slice, so it is exact by construction and
   cannot drift, and no per-unit string copies are kept.
2. **Markdown structure** — the structural block tree (each block's top-level `BlockType`,
   span, and children) and the inline elements it contains, taken from the marko parse and
   *referenced*, not duplicated.
3. **Language structure** — paragraphs, sentences, and the wordtok view, with spans,
   including the spacing tokens between units.
4. **Section structure** — the heading hierarchy over the blocks.

Derived from it: a **section-hierarchical document** (hierarchy = heading outline); the
same content **sliced by block type**; **links/elements rolled up** per block, section, and
document; and **tallies** as `len()` / `Counter` over the referenced items.

**Design principle.** The form must be clean enough that these views are obvious one- or
two-line derivations. If a view needs a lot of calculation or is not obvious, refine the
normalized form — do not add a bespoke stored field or a parallel structure. Counts are
never stored: the model references items; every count is derived.

**Two views, one form.** There are two ways to walk the content, both views of the same
form indexing the same `source_text`: the blank-line `Paragraph`/`Sentence` view is the
editing unit (what diff/window/wordtok operate on); the structural block tree is the
Markdown backbone for slicing, nesting, per-item access, and rollups. Because both are
views, the structural tree changes no block boundaries the diff/window code sees — there is
no forced migration of the editing unit.

## 4. Core types and offsets

- `TextDoc` — retains `source_text`; owns the `Paragraph` list and the derived views.
- `Paragraph` — a blank-line block: `sentences`, an `Offsets`, a `span`, a cached top-level
  `block_type`, computed `original_text`, and helpers (`heading_level()`,
  `heading_title()`, `links()`).
- `Sentence` — `text` (normalized, *editable* — what wordtoks/diffs/reassemble use), an
  `Offsets`, a `span`, and a verbatim `original_text` computed from the span.
- `Offsets(doc_offset, block_offset)` — `doc_offset` absolute; `block_offset` relative to
  the parent (document for a paragraph, paragraph for a sentence).
- Spans — `Paragraph.span` / `Sentence.span` → `(start, end)`; `TextDoc.block_at_offset(o)`
  and `sentence_at_offset(o)` invert them.

Invariant: `source_text[unit.span[0]:unit.span[1]] == unit.original_text` for every
source-backed unit. Synthetic docs (`from_wordtoks`, `append_sent`) have no original
source, so `source_text` is the reassembled working text.

Sentence spans are exact for *all* content: the default splitter is flowmark's
`split_sentences_with_spans` (v0.7.0), whose `SentenceSpan`s are verbatim and never bisect
a link, code span, autolink, or URL. `Sentence.text` stays whitespace-normalized; only
`original_text`/spans are verbatim.

## 5. Block-type model

`BlockType` corresponds one-to-one to Markdown block kinds: `heading`, `paragraph`, `list`
(bullet/unordered), `ordered_list`, `list_item`, `table`, `code`, `blockquote`, `html`,
`footnote`, `thematic_break`.

- **Bullet vs. ordered lists are distinct types.** marko's `List` carries `ordered`;
  `list` is the bullet list (current value, kept), `ordered_list` the enumerated list,
  `list_item` shared. (Callers matching `BlockType.list` for *both* kinds get a
  minor-version note.)
- **One top-level type per block**, from its **outer** element — a blockquote wrapping a
  table classifies as `blockquote`. This is what `iter_blocks`/`filtered`, section slicing,
  and default rollups key on.
- **Nesting is secondary, for rollups.** In the tree a block keeps its own type (that inner
  table is still a `table` `Block`), but a tally/rollup attributes nested content to its
  enclosing top-level block **by default**; descending into `children` is opt-in.

**List density must not change tallies.** A dense list (no blank lines between items) and
the same list written sparsely are the same list. In the structural tree a list **always
decomposes into `list_item` children regardless of density** — a loose list is *one* list
block with blank-line-separated items, not N lists — so `len(list.children)` and any tally
are density-invariant. Density is metadata, not structure: a `tight: bool` on the list
(CommonMark semantics); a finer per-item flag is the same info and may be exposed as a
derived convenience. The flag never enters a tally. (The blank-line `Paragraph` editing
view still sees loose items as separate paragraphs — the editing unit, not the tally unit.)

## 6. Structural block tree

`TextDoc.blocks() -> list[Block]` parses the whole document once (lazy, cached),
independent of blank-line splitting:

- `Block`: `type: BlockType`, `span` (trimmed, so `source[start:end]` is the exact text),
  `children` (a `list` block's children are its `list_item`s; an item may hold nested
  blocks).
- Resolves what blank-line splitting cannot: a fenced code block stays whole even with
  internal blank lines; a tight list decomposes into items with nested sublists.

Offsets come from a line scanner (marko exposes no source positions); the top-level
structure is cross-checked against marko in tests.

## 7. Sections and TOC

A derived hierarchy over heading blocks, no re-parse:

- `Section`: a heading `Paragraph`, its `level`, the blocks it owns (to the next heading of
  level ≤ this), child `Section`s. References its blocks; content/span/sizes computed.
- `TextDoc.sections()` → tree; `toc()` → flat `(level, title, span)`.
- Sizes reuse `TextDoc.size`: `Section.size(unit, subtree=True|False)`, `size_summary()`,
  and `TextDoc.section_size_tree(units=…)` for the readable rolled-up tree. Every
  `TextUnit` (chars, words, sentences, tokens, …) rolls up uniformly.

## 8. Inline elements and links

- `Link(text, url, title, span)` — identity from `flowmark.markdown_ast.extract_links`
  (reference links resolved, escapes honored, autolinks/images handled), which carries no
  span by design. chopdiff recovers each exact `[start, end)` by reconciling the ordered
  identities with the name-tagged atomic spans from
  `flowmark.atomic_spans.iter_atomic_spans` (`markdown_link` / `autolink` / `bare_url`);
  reference links keep identity but no exact span.
- Rollups: `Paragraph.links()`, `Section.links()` (union over the section's blocks),
  `TextDoc.links()`; `link → sentence` via `sentence_at_offset(link.span[0])`.

Links are the first inline element exposed; the same identity-plus-located-span pattern
generalizes to other inline elements.

## 9. Derived views and rollups

All calculated over the form; none store counts:

- **Slice by block type** — filter blocks/sections by top-level `BlockType` (`iter_blocks`
  / `filtered`, or the same predicate over `blocks()` / a section's blocks).
- **Per-section structural blocks** — the block tree scoped to a section, so slices and
  rollups work per section, not only whole-document.
- **Element rollups** — links (and future elements) gathered per block, section, document.
- **Tallies** — `len(...)` / `Counter(b.block_type for b in …)` over the referenced
  collection; nested content rolls up under its top-level block by default.

## 10. Editing and serialization

`Sentence.text` is the editable content: edits change what `reassemble()` produces while
the fixed source references (`original_text`, `offsets`, cached `block_type`) keep
describing the original. So `TextDoc` doubles as an editable model — modify units, then
`reassemble()` to serialize a new document, optionally normalized further by flowmark. The
diff/sliding-window/wordtok machinery operates on this editing view unchanged.

## 11. Invariants and non-goals

Invariants: offset-anchored (every unit maps to exact offsets; spans round-trip); additive
(existing `TextDoc`/`Paragraph`/`Sentence` and diff/window/wordtok behavior preserved); one
form with derived views (no duplicated content, no stored counts).

Non-goals: a parallel `BlockDoc`/`SectionDoc`/`FlexDoc`; CommonMark/GFM rendering
(flowmark covers normalization); replacing `TextNode` (the HTML-`<div>` chunking view);
exact provider-keyed token counts (`estimate_tokens` is a heuristic); a thread-safety
layer.

## 12. References

- Implementation plan / phases: `docs/project/specs/active/plan-2026-05-26-block-aware-doc.md`.
  Phases 1–4 (exact spans, sections/TOC/size rollups, opt-in structural block tree,
  inline-link rollups + link-aware sentences) are implemented on PR #12; Phase 5
  (`ordered_list`, density-invariant lists, per-section blocks, derived rollups)
  consolidates toward this design.
- flowmark v0.7.0 inline API: `flowmark.atomic_spans` (`iter_atomic_spans`,
  `split_sentences_with_spans`, named `AtomicSpan`s) and `flowmark.markdown_ast`
  (`walk_elements`, `extract_links`, `Link`).
- Source: `src/chopdiff/docs/text_doc.py`, `block_tree.py`, `block_types.py`.
