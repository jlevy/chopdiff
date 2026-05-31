# TextDoc and DocGraph: Design Specification

**Status:** Definitive front-to-back design of chopdiff's document model: the `TextDoc`
Python core and the `DocGraph` serialized projection. The design is settled (decision
records DR-1..DR-6 in
[`plan-2026-05-29-unified-document-model.md`](project/specs/active/plan-2026-05-29-unified-document-model.md));
see §14 for what is implemented (v0.4.0) versus in progress. Dated plans under
`docs/project/specs/` describe the incremental work toward this design.

## 1. Purpose

The document model consolidates, in one source-anchored structure, what a document
analysis or editing task normally needs from separate tools, and anchors every piece back
to the source by exact character offset:

- **Markdown block structure:** headings, paragraphs, lists/list items, tables, code,
  blockquotes, HTML, footnotes, thematic breaks.
- **Markdown inline structure:** links, code spans, inline HTML.
- **Language structure:** paragraphs, sentences, words/wordtoks, and the spacing between
  them.
- **Document structure:** heading hierarchy and TOC.

A Markdown parser gives you a block/inline AST but no sentences, sizes, or section
rollups. An NLP toolkit gives sentences but no Markdown structure and no exact source
mapping. This model is both, anchored to one retained source string.

Two surfaces, one design:

- **`TextDoc`** is the **Python core:** the in-process object for parsing, analysis,
  rollups, transforms, and editable reassembly.
- **`DocGraph`** is the **serialized, language-neutral projection** of the same content:
  a JSON contract for frontends, cross-language clients, and annotations. It is derived
  from `TextDoc`, not a competing model (DR-2).

## 2. Goals

- **One consolidating structure.** Markdown block, inline, language, and document structure
  in one object, not four tools stitched together.
- **Exact source anchoring.** Every unit references the source by `[start, end)`; spans
  round-trip verbatim; no copies, no drift. Offsets are **Unicode code points**.
- **Normalized form, derived views.** One canonical form: a stable node table; section
  hierarchy, block-type slices, element rollups, and tallies are *calculated fields* over
  it, never stored. If a view is hard to derive, refine the form.
- **Simplicity with flexibility (mechanism over menu).** One general query primitive
  (`collect()`), composable serialization layers (`include`), not a fixed menu of blessed
  rollups or detail levels, so the model serves many downstream uses without per-need API
  changes (DR-4, DR-5).
- **Markdown-correspondent block types.** One-to-one with Markdown kinds (bullet vs.
  ordered lists distinct); each block has one top-level type; nesting is recursive and
  fully populated.
- **Two block views.** A recursive **structural block tree** (for nesting/slicing/queries)
  and a flat **sequential base-block list** (a complete, ordered, non-overlapping partition
  whose reassembly reproduces the document), so a pipeline can process or resequence a
  document block by block.
- **Density-invariant lists.** Tight and loose lists produce identical tallies.
- **Source-canonical references.** A span reference is durable for annotations across edits
  (`SpanRef`, DR-6): a text quote is the canonical anchor, offsets are recomputable hints.
- **Cross-language contract.** `DocGraph` is a boring, parser-agnostic JSON schema
  (Pydantic-authored, DR-3); Python and any future TypeScript/Rust client are
  implementations of one contract.
- **Dual use.** Analysis of a fixed document *and* an editable model: modify units,
  reassemble, serialize a clean normalized document.
- **LLM/agent-friendly, Python-first, Rust-portable.** Ergonomic from Python and from
  LLM/agent code; a tight spec and thorough tests make a Rust port feasible.
- **Minimal dependencies; additive.** Existing diff/window/wordtok behavior preserved.

## 3. The Normalized Form

Everything is aligned by span into a single retained `source_text`. The **canonical
structure is a node table**, a stable set of nodes addressable by id and span, from which
every other structure is a derived view (DR-1):

1. **Source:** `source_text` plus exact `[start, end)` spans (Unicode code points); each
   unit's `original_text` is a computed slice, exact by construction.
2. **Node table:** one node per block, inline element, and heading: `Node{id, kind,
   parent, children, source_span, attrs}`. Block containment is `parent`/`children`; this
   is taken from marko's parse and *referenced*, not duplicated.
3. **Language structure:** paragraphs, sentences, and the wordtok view, with spans and
   spacing tokens (the editing view).

Why a node table and not a single tree: a document has several hierarchies that overlap and
do not nest: a **section** spans sibling blocks and is not a subtree of the block tree;
**links** are inline ranges; **annotations** target arbitrary spans. A single canonical tree
privileges one hierarchy and forces the rest into bespoke overlays. A node table gives one
id space for blocks *and* inline items, so the containment tree, section tree, block list,
link index, and token stream are all O(n) projections that share ids, and the serialized
JSON still presents a `document` root with children as its top-level shape.

**Views over the form.** Several ways to walk the same `source_text`, none of them the
canonical store:

- the blank-line `Paragraph`/`Sentence` **editing view** (used by diff/window/wordtok);
- the **structural block tree** (the recursive Markdown backbone: slicing, nesting,
  per-item access);
- the **sequential block list** (the flat, non-recursive *base-block* partition, §6);
- the **section tree** (heading hierarchy);
- the **inline/link index**.

The editing view's block boundaries are unchanged by the structural tree, so there is no
forced migration of the editing unit.

**Parse layers.** Those views are not ad-hoc; each is one **parse layer** over the shared
offset space. chopdiff parses the same `source_text` along several independent dimensions,
each contributing nodes tagged with their `layer`:

| Layer | Produces | Depends on | Nesting guarantee |
| --- | --- | --- | --- |
| **textual** | paragraphs, sentences, word tokens | — | ordered list |
| **markdown** | block elements (recursive) and inline (links, code, emphasis) | — | tree |
| **document** | section / heading hierarchy and TOC | markdown (headings) | tree |
| **synthetic** | regions marked by a small defined set of marker tags (today `<div>`/`<span>`), chunk groupings (later phase) | — | tree |

Two consequences define how layers interact:

- **Cross-layer relationships are offset-containment queries, not stored edges.** Within a
  layer, navigate `parent`/`children`; *across* layers, use interval containment/overlap
  ("which markdown blocks are inside this `<div>`", "which section contains this link").
  This is what lets layers overlap and cross-cut without contradiction (a section is not a
  subtree of the block tree; a `<div>` may open mid-block).
- **Each layer declares a nesting guarantee:** well-nested layers project to a tree view,
  ordered-only layers to a sequential list view (the §6 tree-vs-partition distinction,
  generalized). The `SpanRef`-targeted annotation layer (§11) is the out-of-band layer,
  anchored to the same offset space.

The **synthetic layer is a general mechanism, not a `<div>` special case:** synthetic
structure is introduced by a small, defined vocabulary of marker tags that delimit regions
for chunking, grouping, and in-band metadata. The vocabulary is a fixed, known whitelist and
can take any of these forms:

- standard HTML containers, today `<div>`/`<span>` via `TextNode`;
- custom semantic XML tags such as `<chunk>`;
- comment-delimited (Markdoc-style) directives such as `<!-- chunk id="foo" -->`, which carry
  structure in Markdown without rendering.

The layer carries each region as a node with its tag name and attributes in `attrs`, so a new
marker tag is configuration (an entry in the whitelist), not a new code path.

Layers are **enabled à la carte** (a configuration, not a fork): today's `TextNode` tag
subsystem is "the synthetic layer alone," and the full analysis path enables several. See
[`research-2026-05-30-multilayer-parsing.md`](project/research/research-2026-05-30-multilayer-parsing.md)
for the framing and prior art.

## 4. Core Types, Nodes, and Offsets

- `TextDoc`: retains `source_text`; owns the `Paragraph` list (editing view) and the
  derived, lazily-cached node table and views.
- `Node`: `id` (stable within a parse), `kind` (a `BlockType` or an inline kind), `layer`
  (the parse dimension it belongs to, textual / markdown / document / synthetic; §3),
  `parent`, `children`, `source_span`, `attrs` (e.g. heading level, `List.ordered`/`tight`,
  link url/title). `parent`/`children` are within-layer edges; cross-layer relationships are
  offset-containment queries (§3). Parser-internal details live in `attrs`/`metadata`, never
  in stable public fields.
- `Paragraph`: a blank-line block: `sentences`, `Offsets`, `span`, cached top-level
  `block_type`, computed `original_text`, helpers (`heading_level()`, `heading_title()`,
  `links()`).
- `Sentence`: `text` (normalized, editable; what wordtoks/diffs/reassemble use), `Offsets`,
  `span`, verbatim `original_text` computed from the span.
- `Offsets(doc_offset, block_offset)`: `doc_offset` absolute; `block_offset` relative to
  the parent. **Offset unit is Unicode code points** (Python-native); `DocGraph` may
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

## 5. Block-Type Model

`BlockType` corresponds one-to-one to Markdown block kinds: `heading`, `paragraph`, `list`
(bullet/unordered), `ordered_list`, `list_item`, `table`, `code`, `blockquote`, `html`,
`footnote`, `thematic_break`.

- **Bullet vs. ordered lists are distinct types.** marko's `List` carries `ordered`; `list`
  is the bullet list, `ordered_list` is enumerated, `list_item` is shared.
- **One top-level type per block,** from its **outer** element: a blockquote wrapping a
  table classifies as `blockquote` at the top level. This is what the top-level views and
  default rollups key on.
- **Nesting is recursive and fully populated.** Every container (blockquote, list item) has
  its block children in the node table, so a table nested inside a blockquote *is* a node
  and is found by a recursive `collect()`. The inner table keeps its own `table` kind;
  default (shallow) rollups attribute it to its enclosing top-level block, recursive rollups
  count it directly.

**List density must not change tallies.** A dense list and the same list written sparsely
are the same list. In the structural tree a list **always decomposes into `list_item`
children regardless of density**: a loose list is *one* list block with
blank-line-separated items, not N lists, so `len(list.children)` and any tally are
density-invariant. Density is metadata, not structure: a `tight: bool` on the list
(CommonMark semantics); the flag never enters a tally.

## 6. Block Views: Structural Tree and Sequential Base-Block List

**Terminology.** To avoid overloading "block":

- **block element** / **inline element:** the Markdown element *class* (CommonMark/mdast
  sense): block-level (heading, paragraph, blockquote, list, list item, table, code, …) vs
  inline (link, code span, emphasis, …).
- **block node:** a node with a block kind in the recursive **structural block tree**
  (`blocks()`); containers (blockquote, list, list item) contain child block nodes.
- **base block:** a unit of the flat **sequential block list** (`base_blocks()`): a
  complete, ordered, non-overlapping partition of the document into the units a pipeline
  processes or a UI resequences.

These are two views of the same node table, for two different jobs (and they must not be
conflated; see §9: the tree supports *queries* that may overlap; the base-block list is a
*partition* with a cover invariant).

### Structural block tree: `TextDoc.blocks() -> list[Block]`

The recursive view (lazy, cached):

- `Block(type, span, children, tight)`: `span` is trimmed so `source[start:end]` is the
  exact text; `children` holds nested blocks. A `list`/`ordered_list` block's children are
  its `list_item`s; **containers fully populate their block children** (a blockquote's or
  list item's nested blocks are present). `tight` carries CommonMark list density on list
  blocks (`None` elsewhere).
- Resolves what blank-line splitting cannot: a fenced code block stays whole even with
  internal blank lines; a list decomposes into items with nested sublists; a table inside a
  blockquote is reachable.

Block boundaries and spans come straight from flowmark's parser: every block element
carries an authoritative `element.span = (start, end)` read from marko's own source
positions (`flowmark.markdown_ast.block_span`), so chopdiff runs no block-detection regex of
its own and makes no block-boundary decisions. The structure is cross-checked against marko
in tests.

### Sequential block list: `TextDoc.base_blocks() -> list[Block]`

A **base block is a block node** (the same `Block`/node type), but the **base-block list**
is a *partition* of the document: the ordered sequence of base blocks, each carrying a
`depth`. It is the view for block-by-block pipelines and outline UIs that move/resequence
blocks (e.g. Notion-style drag-and-drop, where every item is a draggable unit). chopdiff
does not implement such UIs, but the model supports addressing and reordering at this
granularity. Document manipulation and processing happen base block by base block.

**Frontier.** Leaf and atomic blocks (heading, paragraph, table, code, thematic break,
HTML, and a whole **blockquote**) are each one base block. **Lists decompose:** each **list
item, at every nesting level, is its own base block** with increasing `depth`
(flat-with-depth). An item holding a nested list contributes its own content at depth *d*
and its nested items follow at *d+1*, which keeps the partition non-overlapping.

How deep lists decompose is one numeric parameter, `base_blocks(item_partition_depth=6)`:

- `item_partition_depth = N` (default **6**, deep enough for normal nested lists): split list items
  down to *N* nesting levels; list content nested deeper than *N* stays whole inside its
  depth-*N* base block (avoids pathological fan-out on very deep lists).
- `item_partition_depth = -1`: unlimited; split at every nesting level.
- `item_partition_depth = 0`: lists are not split; each list is a single base block (coarse mode,
  i.e. the top-level blocks).

Blockquotes are always one base block regardless of `item_partition_depth`.

**Invariants** (validated and documented): the base-block list is **ordered** by position,
**non-overlapping** by span, and a **complete cover**. Reassembling the base blocks in order
reproduces the document **exactly except for normalized paragraph-break whitespace** (runs
of blank lines between blocks); every base block also retains its exact `source_span`, so a
byte-for-byte reconstruction is available from offsets when needed. A pipeline may process,
edit, or **resequence** base blocks and reassemble; `depth` is mutable metadata, so promoting
a depth-2 item to depth-1 on a move just changes its rendered nesting, not a violation.

## 7. Sections and TOC

A derived hierarchy over heading nodes, no re-parse:

- `Section`: heading, `level`, the content it owns (up to the next heading of level ≤
  this), child `Section`s. Content/span/sizes are computed; `Section.blocks()` is the block
  tree scoped to the section.
- `TextDoc.sections()` → tree; `toc()` → flat `(level, title, span)`.
- Sizes reuse `TextDoc.size`: `Section.size(unit, subtree=True|False)`, `size_summary()`,
  `TextDoc.section_size_tree(units=…)`. Every `TextUnit` rolls up uniformly.

## 8. Inline Elements and Links

Inline elements (links, code spans, images, …) are **first-class nodes** whose `parent` is
their containing block, with computed `section`/`sentence` associations, so block↔inline
relationships are node edges, and "links in section 3" is a scoped `collect(kinds={link})`.

- `Link(text, url, title, span)`: identity from `flowmark.markdown_ast.extract_links`
  (reference links resolved, escapes honored, autolinks/images handled), which carries no
  span by design. chopdiff recovers each exact `[start, end)` by reconciling the ordered
  identities with the name-tagged atomic spans from `flowmark.atomic_spans.iter_atomic_spans`
  (`markdown_link` / `autolink` / `bare_url`); reference links keep identity but no exact
  span.
- `link → sentence` via `sentence_at_offset(link.span[0])`.

## 9. Derived Views and Rollups

All calculated over the node table; nothing stores counts. The surface is **one general
query primitive, no blessed per-kind rollups** (DR-4):

```python
collect(*, kinds=None, where=None, recursive=False, inline=False) -> list[Node]
```

at document / section / block scope (`dg`, `dg.section(id)`, `dg.node(id)`). `kinds=`
selects by node kind (the typed common case); `where=` is a `Node -> bool` predicate escape
hatch; `recursive` descends into children; `inline` includes inline nodes. It returns
**nodes** (each with `span`, `attrs`, edges). **Counts, values, and groupings are standard
Python** over the result, documented with worked examples, not separate methods:

```python
dg.collect(kinds={NodeKind.table}, recursive=True)        # the tables (values + spans)
len(dg.collect(kinds={NodeKind.table}, recursive=True))   # how many
Counter(n.kind for n in dg.collect(recursive=True))       # tally by kind
dg.section(s3).collect(kinds={NodeKind.link}, recursive=True)   # links in section 3
```

Slice-by-block-type, per-section rollups, and element rollups are all expressions of this
one primitive; relationships are node edges. There are no `tables()`/`code_blocks()`
shortcuts to maintain. (The v0.4.0 `block_type_counts()` convenience accessors are
superseded by `collect()`; see §14.)

**Query vs. partition; do not conflate.** `collect()` is a *query*: it gathers matching
nodes and the results may **overlap** their containers (a table nested in a blockquote is
returned by `collect(kinds={table}, recursive=True)` alongside the blockquote). That is
correct for counting/gathering. The base-block list (§6) is a *partition*: a complete,
ordered, **non-overlapping** cover for linear processing. Use `collect()` to ask "how many
/ which"; use `base_blocks()` to iterate the document's content units.

## 10. DocGraph: The Serialized Projection

`DocGraph` is the JSON contract derived from `TextDoc` (DR-1, DR-2), authored as Pydantic
models that emit a JSON Schema (DR-3). Boring and parser-agnostic: no marko/Python class
names in stable fields. Shape (abbreviated):

```
DocGraph = {
  schema: "DocGraph/v0.1",
  source:  { format, offset_unit: "unicode_code_points", sha256, text? },
  nodes:   [ Node, ... ],                       # the canonical node table
  views:   { toc, blocks, links, sentences },   # arrays of node ids (projections)
  annotations: [],  layout: [],  provenance: [] # reserved layers (later phases)
}
```

`TextDoc.graph(*, include=..., detail=...)` builds/serializes it. **What is built and
serialized is controlled by two composable axes**, not a fixed ladder (DR-5):

```python
graph()                                                  # default layers, structural core
graph(include={Layer.markdown, Layer.document})          # blocks + sections
graph(include={Layer.markdown}, detail={Detail.text, Detail.inline})  # + node text + inline
```

- **`include` is a set of `Layer`s:** the parse dimensions of §3: `textual`, `markdown`,
  `document`, `synthetic`, later `annotations`/`layout`. Enabling a layer builds and
  serializes its nodes/views; enabling `document` auto-enables its dependency `markdown`.
- **`detail` is a small set of payload sub-options:** `text` (per-node source text),
  `inline` (inline nodes), `tokens`, derived coords, controlling richness *within* enabled
  layers.

The structural core (node table, `layer`, and spans) is always present. Presets are
caller-defined `frozenset`s, documented as examples. A new parse dimension is one additive
`Layer`; a new payload category is one additive `Detail`, never a refactor. (One vocabulary:
the earlier mixed `Layer` enum was split into `Layer` and `Detail` per E9; see the plan's DR-5.)

## 11. SpanRef and Annotations

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
- **Chrome URL Text Fragment convertible:** the quote maps to
  `#:~:text=[prefix-,]exact[,-suffix]` (a lossy projection: prose, word-boundary,
  case-insensitive), generated on demand, never stored.
- **Deferred:** an XPath/DOM `structural_path` and a CRDT `anchor` slot, added only on a
  concrete need.

Annotations are a **stand-off layer**: parsed structure (sections, blocks, links) and added
structure (summaries, notes, suggestions) are the same kind of thing: typed layers of
`SpanRef`-targeted records over immutable source. **The annotation layer is a later phase**
and is expected to be revisited and refined once v1 is in use; v1 fixes the `SpanRef`
contract (at least as expressive as the Chrome-style `exact`+`prefix`/`suffix` floor) so the
node model, schema, and editor bridge are designed around it.

Background, syntaxes, and the syntactic-vs-quoted trade-offs are surveyed (with citations)
in
[`research-2026-05-30-span-references.md`](project/research/research-2026-05-30-span-references.md).

## 12. Editing and Serialization

`Sentence.text` is the editable content: edits change what `reassemble()` produces while
the fixed source references (`original_text`, `offsets`, cached `block_type`) keep
describing the original. So `TextDoc` doubles as an editable model: modify units, then
`reassemble()` to serialize a new document (optionally normalized by flowmark). The
diff/sliding-window/wordtok machinery operates on this editing view unchanged.

The structural node table is a pure function of the immutable `source_text` (sentence edits
touch the editing view, not `source_text`), so it and its derived views are lazily cached;
the operative contract is "do not reassign `source_text` after parse." Edit by editing the
`TextDoc`/source and re-deriving `DocGraph`; an editor bridge resolves annotations through
`SpanRef`. Render helpers emit `data-node-id` / `data-source-span` so a rendered selection
resolves to a node and thence to source.

## 13. Invariants and Non-Goals

Invariants: offset-anchored (code points); node ids stable within a parse; one canonical
form (node table) with derived views (no duplicated content, no stored counts); references
are quote-canonical; additive (existing behavior preserved).

Non-goals: a parallel runtime `BlockDoc`/`SectionDoc`/`FlexDoc` Python model (DocGraph is
a projection, not a competing editable model); blessed per-kind rollups or fixed detail
levels; DOM/XPath/CSS selectors in `SpanRef` (plain-text-first); CommonMark/GFM rendering
(flowmark covers normalization); stored cross-layer edges (cross-layer relationships are
offset-containment queries, §3); exact provider-keyed token counts (`estimate_tokens` is a
heuristic); a thread-safety layer.

**Later phases, not non-goals (E9).** The **synthetic layer**, re-expressing today's
`TextNode` tag chunking (a small defined set of marker tags, today `<div>`/`<span>`) as a layer
keyed into the node table, and **cross-layer structural edits** (move/wrap/splice anchored on
`SpanRef`, generalizing `div_insert_wrapped`) are deferred phases, not excluded. `TextNode`
stays as-is meanwhile.
The annotation, operation, provenance, and layout layers are likewise schema-reserved and
built later. The Phase-1 hooks (the `layer` field, offset-containment `collect()`,
`SpanRef`-anchored edits) keep these a small lift rather than a redesign.

## 14. Implementation Status

- **Shipped in v0.4.0:** exact spans; the opt-in structural block tree `blocks()` (boundaries
  and spans from flowmark, no regex scanner); sections/TOC/size rollups; inline-link rollups
  and link-aware sentences; `ordered_list`/density-invariant lists; per-section blocks; and
  **top-level** `block_type_counts()`.
- **Implemented (post-v0.4.0):** the recursive node table (containers fully populate
  children, including blockquote and list-item block children); `base_blocks()` sequential
  partition with its non-overlapping cover invariant; the single `collect()` primitive
  (superseding `block_type_counts()`; migration:
  `Counter(n.kind for n in doc.graph().collect(...))`); composable `include` layers and
  `detail` payload options; the `DocGraph` Pydantic schema ("DocGraph/v0.1"); and the
  `SpanRef` contract with exact resolution (fuzzy re-anchor wired behind it).
- **In progress:** annotation layer, synthetic layer (re-expressing `TextNode` tag chunking
  as a layer), cross-layer structural edits, and operation/provenance/layout layers.
  Tracked by epic `chopdiff-8q8q`; sequenced in
  [`plan-2026-05-29-unified-document-model.md`](project/specs/active/plan-2026-05-29-unified-document-model.md).

## 15. References

- Unified document model plan (decision records, phases):
  [`plan-2026-05-29-unified-document-model.md`](project/specs/active/plan-2026-05-29-unified-document-model.md).
- Research: the cross-language document-model survey
  [`research-2026-05-29-document-model.md`](project/research/research-2026-05-29-document-model.md),
  the span-references survey
  [`research-2026-05-30-span-references.md`](project/research/research-2026-05-30-span-references.md),
  and the layered-parsing brief
  [`research-2026-05-30-multilayer-parsing.md`](project/research/research-2026-05-30-multilayer-parsing.md).
- Completed block-aware plan (v0.4.0):
  [`plan-2026-05-26-block-aware-doc.md`](project/specs/archive/plan-2026-05-26-block-aware-doc.md).
- flowmark v0.7.1 API: `flowmark.atomic_spans` (`iter_atomic_spans`,
  `split_sentences_with_spans`, named `AtomicSpan`s) and `flowmark.markdown_ast`
  (`block_span`, `walk_elements`, `extract_links`, `Link`).
- Source: `src/chopdiff/docs/text_doc.py`, `block_tree.py`, `block_types.py`.

* * *

*This document follows the tbd [writing style guidelines](https://github.com/jlevy/tbd).*
