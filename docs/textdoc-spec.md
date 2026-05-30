# TextDoc and DocOverview: Design Specification

**Status:** Definitive front-to-back design of chopdiff's document model: the `TextDoc`
Python core and the `DocOverview` serialized projection. The design is settled (decision
records DR-1..DR-6 in
[`plan-2026-05-29-unified-document-model.md`](project/specs/active/plan-2026-05-29-unified-document-model.md));
see §14 for what is implemented (v0.4.0) versus in progress. Dated plans under
`docs/project/specs/` describe the incremental work toward this design.

## 1. Purpose

The document model consolidates, in one source-anchored structure, what a document
analysis or editing task normally needs from separate tools — and anchors every piece back
to the source by exact character offset:

- **Markdown block structure** — headings, paragraphs, lists/list items, tables, code,
  blockquotes, HTML, footnotes, thematic breaks.
- **Markdown inline structure** — links, code spans, inline HTML.
- **Language structure** — paragraphs, sentences, words/wordtoks, and the spacing between
  them.
- **Document structure** — heading hierarchy and TOC.

A Markdown parser gives you a block/inline AST but no sentences, sizes, or section
rollups. An NLP toolkit gives sentences but no Markdown structure and no exact source
mapping. This model is both, anchored to one retained source string.

Two surfaces, one design:

- **`TextDoc`** is the **Python core** — the in-process object for parsing, analysis,
  rollups, transforms, and editable reassembly.
- **`DocOverview`** is the **serialized, language-neutral projection** of the same content
  — a JSON contract for frontends, cross-language clients, and annotations. It is derived
  from `TextDoc`, not a competing model (DR-2).

## 2. Goals

- **One consolidating structure.** Markdown block + inline + language + document structure
  in one object, not four tools stitched together.
- **Exact source anchoring.** Every unit references the source by `[start, end)`; spans
  round-trip verbatim; no copies, no drift. Offsets are **Unicode code points**.
- **Normalized form, derived views.** One canonical form — a stable node table; section
  hierarchy, block-type slices, element rollups, and tallies are *calculated fields* over
  it, never stored. If a view is hard to derive, refine the form.
- **Simplicity with flexibility (mechanism over menu).** One general query primitive
  (`collect()`), composable serialization layers (`include`) — not a fixed menu of blessed
  rollups or detail levels, so the model serves many downstream uses without per-need API
  changes (DR-4, DR-5).
- **Markdown-correspondent block types.** One-to-one with Markdown kinds (bullet vs.
  ordered lists distinct); each block has one top-level type; nesting is recursive and
  fully populated.
- **Density-invariant lists.** Tight and loose lists produce identical tallies.
- **Source-canonical references.** A span reference is durable for annotations across edits
  (`SpanRef`, DR-6): a text quote is the canonical anchor, offsets are recomputable hints.
- **Cross-language contract.** `DocOverview` is a boring, parser-agnostic JSON schema
  (Pydantic-authored, DR-3); Python and any future TypeScript/Rust client are
  implementations of one contract.
- **Dual use.** Analysis of a fixed document *and* an editable model: modify units,
  reassemble, serialize a clean normalized document.
- **LLM/agent-friendly, Python-first, Rust-portable.** Ergonomic from Python and from
  LLM/agent code; a tight spec and thorough tests make a Rust port feasible.
- **Minimal dependencies; additive.** Existing diff/window/wordtok behavior preserved.

## 3. The normalized form

Everything is aligned by span into a single retained `source_text`. The **canonical
structure is a node table** — a stable set of nodes addressable by id and span — from which
every other structure is a derived view (DR-1):

1. **Source** — `source_text` plus exact `[start, end)` spans (Unicode code points); each
   unit's `original_text` is a computed slice, exact by construction.
2. **Node table** — one node per block, inline element, and heading: `Node{id, kind,
   parent, children, source_span, attrs}`. Block containment is `parent`/`children`; this
   is taken from marko's parse and *referenced*, not duplicated.
3. **Language structure** — paragraphs, sentences, and the wordtok view, with spans and
   spacing tokens (the editing view).

Why a node table and not a single tree: a document has several hierarchies that overlap and
do not nest — a **section** spans sibling blocks and is not a subtree of the block tree;
**links** are inline ranges; **annotations** target arbitrary spans. A single canonical tree
privileges one hierarchy and forces the rest into bespoke overlays. A node table gives one
id space for blocks *and* inline items, so the containment tree, section tree, block list,
link index, and token stream are all O(n) projections that share ids, and the serialized
JSON still presents a `document` root with children as its top-level shape.

**Views over the form.** Several ways to walk the same `source_text`, none of them the
canonical store:

- the blank-line `Paragraph`/`Sentence` **editing view** (used by diff/window/wordtok);
- the **structural block tree** (the Markdown backbone — slicing, nesting, per-item access);
- the **section tree** (heading hierarchy);
- the **inline/link index**.

The editing view's block boundaries are unchanged by the structural tree, so there is no
forced migration of the editing unit.

## 4. Core types, nodes, and offsets

- `TextDoc` — retains `source_text`; owns the `Paragraph` list (editing view) and the
  derived, lazily-cached node table and views.
- `Node` — `id` (stable within a parse), `kind` (a `BlockType` or an inline kind),
  `parent`, `children`, `source_span`, `attrs` (e.g. heading level, `List.ordered`/`tight`,
  link url/title). Parser-internal details live in `attrs`/`metadata`, never in stable
  public fields.
- `Paragraph` — a blank-line block: `sentences`, `Offsets`, `span`, cached top-level
  `block_type`, computed `original_text`, helpers (`heading_level()`, `heading_title()`,
  `links()`).
- `Sentence` — `text` (normalized, editable; what wordtoks/diffs/reassemble use), `Offsets`,
  `span`, verbatim `original_text` computed from the span.
- `Offsets(doc_offset, block_offset)` — `doc_offset` absolute; `block_offset` relative to
  the parent. **Offset unit is Unicode code points** (Python-native); `DocOverview` may
  expose derived `byte_span`/`utf16_span` for byte- or browser-oriented consumers, but the
  canonical `source_span` is code points (the cross-language footgun the W3C position
  selector left unresolved).
- `TextDoc.block_at_offset(o)` / `sentence_at_offset(o)` invert spans.

Invariant: `source_text[unit.span[0]:unit.span[1]] == unit.original_text` for every
source-backed unit. Synthetic docs (`from_wordtoks`, `append_sent`) have no source, so
`source_text` is the reassembled working text.

Sentence spans are exact for all content via flowmark's `split_sentences_with_spans`:
`SentenceSpan`s are verbatim and never bisect a link, code span, autolink, or URL.
`Sentence.text` stays whitespace-normalized; `original_text`/spans are verbatim.

## 5. Block-type model

`BlockType` corresponds one-to-one to Markdown block kinds: `heading`, `paragraph`, `list`
(bullet/unordered), `ordered_list`, `list_item`, `table`, `code`, `blockquote`, `html`,
`footnote`, `thematic_break`.

- **Bullet vs. ordered lists are distinct types.** marko's `List` carries `ordered`; `list`
  is the bullet list, `ordered_list` is enumerated, `list_item` is shared.
- **One top-level type per block,** from its **outer** element — a blockquote wrapping a
  table classifies as `blockquote` at the top level. This is what the top-level views and
  default rollups key on.
- **Nesting is recursive and fully populated.** Every container (blockquote, list item) has
  its block children in the node table, so a table nested inside a blockquote *is* a node
  and is found by a recursive `collect()`. The inner table keeps its own `table` kind;
  default (shallow) rollups attribute it to its enclosing top-level block, recursive rollups
  count it directly.

**List density must not change tallies.** A dense list and the same list written sparsely
are the same list. In the structural tree a list **always decomposes into `list_item`
children regardless of density** — a loose list is *one* list block with
blank-line-separated items, not N lists — so `len(list.children)` and any tally are
density-invariant. Density is metadata, not structure: a `tight: bool` on the list
(CommonMark semantics); the flag never enters a tally.

## 6. Structural block tree

`TextDoc.blocks() -> list[Block]` is the block-tree view over the node table (lazy,
cached):

- `Block(type, span, children, tight)` — `span` is trimmed so `source[start:end]` is the
  exact text; `children` holds nested blocks. A `list`/`ordered_list` block's children are
  its `list_item`s; **containers fully populate their block children** (a blockquote's or
  list item's nested blocks are present). `tight` carries CommonMark list density on list
  blocks (`None` elsewhere).
- Resolves what blank-line splitting cannot: a fenced code block stays whole even with
  internal blank lines; a list decomposes into items with nested sublists; a table inside a
  blockquote is reachable.

Block boundaries and spans come straight from flowmark's parser — every block element
carries an authoritative `element.span = (start, end)` read from marko's own source
positions (`flowmark.markdown_ast.block_span`), so chopdiff runs no block-detection regex of
its own and makes no block-boundary decisions. The structure is cross-checked against marko
in tests.

## 7. Sections and TOC

A derived hierarchy over heading nodes, no re-parse:

- `Section` — heading, `level`, the content it owns (up to the next heading of level ≤
  this), child `Section`s. Content/span/sizes are computed; `Section.blocks()` is the block
  tree scoped to the section.
- `TextDoc.sections()` → tree; `toc()` → flat `(level, title, span)`.
- Sizes reuse `TextDoc.size`: `Section.size(unit, subtree=True|False)`, `size_summary()`,
  `TextDoc.section_size_tree(units=…)`. Every `TextUnit` rolls up uniformly.

## 8. Inline elements and links

Inline elements (links, code spans, images, …) are **first-class nodes** whose `parent` is
their containing block, with computed `section`/`sentence` associations — so block↔inline
relationships are node edges, and "links in section 3" is a scoped `collect(kinds={link})`.

- `Link(text, url, title, span)` — identity from `flowmark.markdown_ast.extract_links`
  (reference links resolved, escapes honored, autolinks/images handled), which carries no
  span by design. chopdiff recovers each exact `[start, end)` by reconciling the ordered
  identities with the name-tagged atomic spans from `flowmark.atomic_spans.iter_atomic_spans`
  (`markdown_link` / `autolink` / `bare_url`); reference links keep identity but no exact
  span.
- `link → sentence` via `sentence_at_offset(link.span[0])`.

## 9. Derived views and rollups

All calculated over the node table; nothing stores counts. The surface is **one general
query primitive, no blessed per-kind rollups** (DR-4):

```python
collect(*, kinds=None, where=None, recursive=False, inline=False) -> list[Node]
```

at document / section / block scope (`ov`, `ov.section(id)`, `ov.node(id)`). `kinds=`
selects by node kind (the typed common case); `where=` is a `Node -> bool` predicate escape
hatch; `recursive` descends into children; `inline` includes inline nodes. It returns
**nodes** (each with `span`, `attrs`, edges). **Counts, values, and groupings are standard
Python** over the result — documented with worked examples, not separate methods:

```python
ov.collect(kinds={NodeKind.table}, recursive=True)        # the tables (values + spans)
len(ov.collect(kinds={NodeKind.table}, recursive=True))   # how many
Counter(n.kind for n in ov.collect(recursive=True))       # tally by kind
ov.section(s3).collect(kinds={NodeKind.link}, recursive=True)   # links in section 3
```

Slice-by-block-type, per-section rollups, and element rollups are all expressions of this
one primitive; relationships are node edges. There are no `tables()`/`code_blocks()`
shortcuts to maintain. (The v0.4.0 `block_type_counts()` convenience accessors are
superseded by `collect()`; see §14.)

## 10. DocOverview: the serialized projection

`DocOverview` is the JSON contract derived from `TextDoc` (DR-1, DR-2), authored as Pydantic
models that emit a JSON Schema (DR-3). Boring and parser-agnostic — no marko/Python class
names in stable fields. Shape (abbreviated):

```
DocOverview = {
  schema: "chopdiff.doc_overview.v1",
  source:  { format, offset_unit: "unicode_code_points", sha256, text? },
  nodes:   [ Node, ... ],                       # the canonical node table
  views:   { toc, blocks, links, sentences },   # arrays of node ids (projections)
  annotations: [],  layout: [],  provenance: [] # reserved layers (later phases)
}
```

`TextDoc.overview(*, include=...)` builds/serializes it. **Payload size is controlled by a
composable set of optional layers** — not a fixed ladder (DR-5):

```python
overview()                                    # structural core only (small)
overview(include={Layer.text, Layer.inline})  # + node text and inline nodes
```

`Layer` is a small orthogonal enum (`text`, `inline`, `sentences`, `tokens`, derived coords,
later `annotations`/`layout`); the structural core (node table + spans) is always present.
Presets are caller-defined `frozenset[Layer]`, documented as examples. New data categories
are one additive `Layer`, never a refactor.

## 11. SpanRef and annotations

`SpanRef` is the one span-reference type used for addressing a piece of the document from
source, parsed model, and rendered output (DR-6). It carries two coordinated span kinds:

```
SpanRef = {
  exact: str, prefix?: str, suffix?: str,   # quoted span — CANONICAL durable anchor
  start?: int, end?: int,                   # offset span (code points) — recomputable HINT
}
```

- **Quote canonical, offset a hint.** Every mature annotation system (W3C `oa:Choice`,
  Hypothesis) treats the text quote as the durable anchor and offsets as accelerators,
  because the quote survives edits and re-anchors fuzzily while offsets shift. Within one
  parse the offset is exact (the fast path); across edits the quote recovers the target.
- **Resolution.** model→source is total (a node fills both span and quote); source→model is
  exact fast-path then quote fuzzy re-anchor, updating offsets.
- **Persistence** is quote-canonical and source-grounded; an in-memory `node_id` handle is
  never persisted.
- **Chrome URL Text Fragment convertible** — the quote maps to
  `#:~:text=[prefix-,]exact[,-suffix]` (a lossy projection: prose, word-boundary,
  case-insensitive), generated on demand, never stored.
- **Deferred:** an XPath/DOM `structural_path` and a CRDT `anchor` slot, added only on a
  concrete need.

Annotations are a **stand-off layer**: parsed structure (sections, blocks, links) and added
structure (summaries, notes, suggestions) are the same kind of thing — typed layers of
`SpanRef`-targeted records over immutable source. **The annotation layer is a later phase**
and is expected to be revisited and refined once v1 is in use; v1 fixes the `SpanRef`
contract (at least as expressive as the Chrome-style `exact`+`prefix`/`suffix` floor) so the
node model, schema, and editor bridge are designed around it.

Background, syntaxes, and the syntactic-vs-quoted trade-offs are surveyed (with citations)
in
[`research-2026-05-30-span-references.md`](project/research/research-2026-05-30-span-references.md).

## 12. Editing and serialization

`Sentence.text` is the editable content: edits change what `reassemble()` produces while
the fixed source references (`original_text`, `offsets`, cached `block_type`) keep
describing the original. So `TextDoc` doubles as an editable model — modify units, then
`reassemble()` to serialize a new document (optionally normalized by flowmark). The
diff/sliding-window/wordtok machinery operates on this editing view unchanged.

The structural node table is a pure function of the immutable `source_text` (sentence edits
touch the editing view, not `source_text`), so it and its derived views are lazily cached;
the operative contract is "do not reassign `source_text` after parse." Edit by editing the
`TextDoc`/source and re-deriving `DocOverview`; an editor bridge resolves annotations through
`SpanRef`. Render helpers emit `data-node-id` / `data-source-span` so a rendered selection
resolves to a node and thence to source.

## 13. Invariants and non-goals

Invariants: offset-anchored (code points); node ids stable within a parse; one canonical
form (node table) with derived views (no duplicated content, no stored counts); references
are quote-canonical; additive (existing behavior preserved).

Non-goals: a parallel runtime `BlockDoc`/`SectionDoc`/`FlexDoc` Python model (DocOverview is
a projection, not a competing editable model); blessed per-kind rollups or fixed detail
levels; DOM/XPath/CSS selectors in `SpanRef` (plain-text-first); CommonMark/GFM rendering
(flowmark covers normalization); replacing `TextNode` (HTML-`<div>` chunking); exact
provider-keyed token counts (`estimate_tokens` is a heuristic); a thread-safety layer. The
annotation, operation, provenance, and layout layers are schema-reserved but built later.

## 14. Implementation status

- **Shipped in v0.4.0:** exact spans; the opt-in structural block tree `blocks()` (boundaries
  and spans from flowmark, no regex scanner); sections/TOC/size rollups; inline-link rollups
  and link-aware sentences; `ordered_list`/density-invariant lists; per-section blocks; and
  **top-level** `block_type_counts()`. At v0.4.0 `blocks()` does not yet populate
  blockquote/list-item children, so top-level counts do not see a nested table.
- **In progress (this design):** the recursive node table (containers fully populate
  children); the single `collect()` primitive (superseding and removing `block_type_counts()`,
  the one semi-breaking change — migration: `Counter(n.kind for n in
  doc.overview().collect(...))`); composable `include` layers; the `DocOverview` Pydantic
  schema; and the `SpanRef` contract with exact resolution (fuzzy re-anchor wired behind it).
  Tracked by epic `chopdiff-8q8q`; sequenced in
  [`plan-2026-05-29-unified-document-model.md`](project/specs/active/plan-2026-05-29-unified-document-model.md).

## 15. References

- Unified document model plan (decision records, phases):
  [`plan-2026-05-29-unified-document-model.md`](project/specs/active/plan-2026-05-29-unified-document-model.md).
- Research: the cross-language document-model survey
  [`research-2026-05-29-document-model.md`](project/research/research-2026-05-29-document-model.md)
  and the span-references survey
  [`research-2026-05-30-span-references.md`](project/research/research-2026-05-30-span-references.md).
- Completed block-aware plan (v0.4.0):
  [`plan-2026-05-26-block-aware-doc.md`](project/specs/archive/plan-2026-05-26-block-aware-doc.md).
- flowmark v0.7.1 API: `flowmark.atomic_spans` (`iter_atomic_spans`,
  `split_sentences_with_spans`, named `AtomicSpan`s) and `flowmark.markdown_ast`
  (`block_span`, `walk_elements`, `extract_links`, `Link`).
- Source: `src/chopdiff/docs/text_doc.py`, `block_tree.py`, `block_types.py`.

* * *

*This document follows the tbd [writing style guidelines](https://github.com/jlevy/tbd).*
