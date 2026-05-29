# TextDoc: Design Specification

**Status:** Definitive front-to-back design of the `TextDoc` data structure. Dated plans
under `docs/project/specs/` describe incremental work toward it.

## 1. Purpose

`TextDoc` consolidates, in one data structure, what a document analysis or editing task
normally needs from separate tools — and anchors every piece back to the source by exact
character offset:

- **Markdown block structure** — headings, paragraphs, lists/list items, tables, code,
  blockquotes, HTML, footnotes, thematic breaks.
- **Markdown inline structure** — links, code spans, inline HTML.
- **Language structure** — paragraphs, sentences, words/wordtoks, and the spacing
  between them.
- **Document structure** — heading hierarchy and TOC.

A Markdown parser gives you a block/inline AST but no sentences, sizes, or section
rollups. An NLP toolkit gives sentences but no Markdown structure and no exact source
mapping. `TextDoc` is both, and because every unit is an offset-anchored view into one
retained source string, it stays efficient on large documents.

## 2. Goals

- **One consolidating structure.** Markdown block + inline + language + document
  structure in one object, not four tools stitched together.
- **Exact source anchoring.** Every unit references the source by `[start, end)`; spans
  round-trip verbatim; no copies, no drift.
- **Normalized form, derived views.** One form; section hierarchy, block-type slices,
  element rollups, and tallies are *calculated fields* over it — never stored. If a view
  is hard to derive, refine the form.
- **Markdown-correspondent block types.** One-to-one with Markdown kinds (bullet vs.
  ordered lists distinct); each block has one top-level type; nesting is for rollups.
- **Density-invariant lists.** Tight and loose lists produce identical tallies.
- **Section rollups.** A hierarchical document keyed by headings, sliceable by block
  type, with links/elements and sizes rolled up per section and per document.
- **Dual use.** Analysis of a fixed document *and* an editable model: modify units,
  reassemble, serialize a clean normalized document.
- **LLM/agent-friendly, Python-first, Rust-portable.** Ergonomic from Python and from
  LLM/agent code; a tight spec and thorough tests make a Rust port feasible (regex and
  diff are already Rust-backed).
- **Minimal dependencies; additive.** Existing diff/window/wordtok behavior and APIs
  preserved.

## 3. The normalized form

Everything aligned by span into a single retained `source_text`:

1. **Original structure** — `source_text` plus exact `[start, end)` spans; each unit's
   `original_text` is a computed slice, exact by construction.
2. **Markdown structure** — the structural block tree (top-level `BlockType`, span,
   children) and inline elements, taken from marko and *referenced*, not duplicated.
3. **Language structure** — paragraphs, sentences, and the wordtok view, with spans and
   spacing tokens.
4. **Section structure** — the heading hierarchy over the blocks.

Derived from it: a **section-hierarchical document**; the same content **sliced by block
type**; **links/elements rolled up** per block, section, document; **tallies** as
`len()` / `Counter` over the referenced items.

**Two views, one form.** Two ways to walk the content, both indexing the same
`source_text`: the blank-line `Paragraph`/`Sentence` view is the editing unit (used by
diff/window/wordtok); the structural block tree is the Markdown backbone (for slicing,
nesting, per-item access, rollups). The tree changes no block boundaries the editing view
sees, so there is no forced migration of the editing unit.

## 4. Core types and offsets

- `TextDoc` — retains `source_text`; owns the `Paragraph` list and derived views.
- `Paragraph` — a blank-line block: `sentences`, `Offsets`, `span`, cached top-level
  `block_type`, computed `original_text`, helpers (`heading_level()`,
  `heading_title()`, `links()`).
- `Sentence` — `text` (normalized, editable; what wordtoks/diffs/reassemble use),
  `Offsets`, `span`, verbatim `original_text` computed from the span.
- `Offsets(doc_offset, block_offset)` — `doc_offset` absolute; `block_offset` relative to
  the parent (document for a paragraph, paragraph for a sentence).
- `TextDoc.block_at_offset(o)` / `sentence_at_offset(o)` invert spans.

Invariant: `source_text[unit.span[0]:unit.span[1]] == unit.original_text` for every
source-backed unit. Synthetic docs (`from_wordtoks`, `append_sent`) have no source, so
`source_text` is the reassembled working text.

Sentence spans are exact for all content via flowmark's `split_sentences_with_spans`
(v0.7.0): `SentenceSpan`s are verbatim and never bisect a link, code span, autolink, or
URL. `Sentence.text` stays whitespace-normalized; `original_text`/spans are verbatim.

## 5. Block-type model

`BlockType` corresponds one-to-one to Markdown block kinds: `heading`, `paragraph`,
`list` (bullet/unordered), `ordered_list`, `list_item`, `table`, `code`, `blockquote`,
`html`, `footnote`, `thematic_break`.

- **Bullet vs. ordered lists are distinct types.** marko's `List` carries `ordered`;
  `list` is the bullet list (current value, kept), `ordered_list` is enumerated, and
  `list_item` is shared. (Callers matching `BlockType.list` for *both* kinds get a
  minor-version note.)
- **One top-level type per block,** from its **outer** element — a blockquote wrapping a
  table classifies as `blockquote`. This is what `iter_blocks`/`filtered`, section
  slicing, and default rollups key on.
- **Nesting is secondary, for rollups.** In the tree a block keeps its own type (that
  inner table is still a `table` `Block`), but a tally/rollup attributes nested content
  to its enclosing top-level block by default; descending into `children` is opt-in.

**List density must not change tallies.** A dense list and the same list written
sparsely are the same list. In the structural tree a list **always decomposes into
`list_item` children regardless of density** — a loose list is *one* list block with
blank-line-separated items, not N lists — so `len(list.children)` and any tally are
density-invariant. Density is metadata, not structure: a `tight: bool` on the list
(CommonMark semantics); a per-item flag is the same information and can be derived. The
flag never enters a tally.

## 6. Structural block tree

`TextDoc.blocks() -> list[Block]` parses the whole document once (lazy, cached):

- `Block(type, span, children, tight)` — `span` is trimmed so `source[start:end]` is the
  exact text; `children` holds nested blocks (a `list`/`ordered_list` block's children are
  its `list_item`s). `tight` carries CommonMark list density on list blocks (`None`
  elsewhere).
- Resolves what blank-line splitting cannot: a fenced code block stays whole even with
  internal blank lines; a list decomposes into items with nested sublists.

Block boundaries and spans come straight from flowmark's parser — every block element
carries an authoritative `element.span = (start, end)` read from marko's own source
positions (`flowmark.markdown_ast.block_span`), so chopdiff runs no block-detection regex
of its own and makes no block-boundary decisions. The top-level structure is cross-checked
against marko in tests.

## 7. Sections and TOC

A derived hierarchy over heading blocks, no re-parse:

- `Section` — heading `Paragraph`, `level`, the blocks it owns (up to the next heading
  of level ≤ this), child `Section`s. References its blocks; content/span/sizes computed.
- `TextDoc.sections()` → tree; `toc()` → flat `(level, title, span)`.
- Sizes reuse `TextDoc.size`: `Section.size(unit, subtree=True|False)`, `size_summary()`,
  and `TextDoc.section_size_tree(units=…)`. Every `TextUnit` rolls up uniformly.

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

- **Slice by block type** — filter by top-level `BlockType` (`iter_blocks`/`filtered`, or
  the same predicate over `blocks()` or a section's blocks).
- **Per-section structural blocks** — the block tree scoped to a section, so slices and
  rollups work per section, not only whole-document.
- **Element rollups** — links (and future elements) gathered per block, section,
  document.
- **Tallies** — `len(...)` / `Counter(b.type for b in …)` over the referenced collection
  (e.g. `TextDoc.block_type_counts()`, `Section.block_type_counts()`); nested content
  rolls up under its top-level block by default, descending into `children` is opt-in.

**Status (v0.4.0):** the views above are built **top-level only** — `blocks()` does not
populate blockquote/list-item children, so `block_type_counts()` does not see a table
nested in a blockquote, and rollups carry counts but not locations together. Fully
recursive rollups (values *and* counts at any scope, over blocks and inline items), the
`Reference`/annotation model, and the serialized `DocOverview` projection are **planned,
not yet built** — see
[`plan-2026-05-29-unified-document-model.md`](project/specs/active/plan-2026-05-29-unified-document-model.md).

## 10. Editing and serialization

`Sentence.text` is the editable content: edits change what `reassemble()` produces while
the fixed source references (`original_text`, `offsets`, cached `block_type`) keep
describing the original. So `TextDoc` doubles as an editable model — modify units, then
`reassemble()` to serialize a new document (optionally normalized by flowmark). The
diff/sliding-window/wordtok machinery operates on this editing view unchanged.

## 11. Invariants and non-goals

Invariants: offset-anchored; additive (existing behavior preserved); one form with
derived views (no duplicated content, no stored counts).

Non-goals: a parallel `BlockDoc`/`SectionDoc`/`FlexDoc`; CommonMark/GFM rendering
(flowmark covers normalization); replacing `TextNode` (HTML-`<div>` chunking); exact
provider-keyed token counts (`estimate_tokens` is a heuristic); a thread-safety layer.

## 12. References

- Implementation plan (completed):
  `docs/project/specs/archive/plan-2026-05-26-block-aware-doc.md`. All phases are
  implemented and shipped in v0.4.0: exact spans, sections/TOC/size rollups, the opt-in
  structural block tree, inline-link rollups + link-aware sentences (Phases 1–4), flowmark
  block-span adoption that removed chopdiff's regex scanner (Phase 5), and the
  normalized-form view set — `ordered_list`, density-invariant lists, per-section blocks,
  derived rollups (Phase 6).
- flowmark v0.7.1 API: `flowmark.atomic_spans` (`iter_atomic_spans`,
  `split_sentences_with_spans`, named `AtomicSpan`s) and `flowmark.markdown_ast`
  (`block_span`, `walk_elements`, `extract_links`, `Link`).
- Source: `src/chopdiff/docs/text_doc.py`, `block_tree.py`, `block_types.py`.

* * *

*This document follows the tbd [writing style guidelines](https://github.com/jlevy/tbd).*
