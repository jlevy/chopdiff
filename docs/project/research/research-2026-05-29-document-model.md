# Research: A Source-Grounded, Cross-Language Document Model

**Date:** 2026-05-29 (last updated 2026-05-29)

**Author:** Codex and Claude (consolidated)

**Status:** Complete (survey, with 2026-05-29 fact-check updates)

> This document subsumes and replaces two earlier overlapping surveys:
> `research-2026-05-29-grounded-document-model.md` (the broad survey, matrix, options,
> and JSON sketch) and `research-2026-05-29-document-model-layering.md` (the
> model/serialization/implementation separation, the model→views framing, and the
> stand-off / lossless-tree / CRDT / block-JSON / djot prior art). All content from both
> is carried forward here.

## Overview

This research surveys ways to represent a document as a comprehensive,
JSON-serializable structure that remains grounded in the original source while
supporting visual analysis, AI analysis, human annotation, structural navigation,
document manipulation, and normalized rewriting.

The motivating direction is to build on Chopdiff and Flowmark rather than replacing
them:

- `TextDoc` is already a useful linear model for source-referenced text analysis,
  sentence/paragraph units, tokenization, diffs, and transform stitching.
- Flowmark and Marko already provide parser-backed Markdown normalization and structural
  interpretation.
- `TextNode` already provides a grounded tree for explicit HTML `div` structures.

Three framing claims organize the conclusions:

1. **The deliverable is a data model**, which is a distinct concern from its
   **serialization format** (JSON) and its **implementation** (Python today, possibly
   TypeScript/Rust/WASM later). The public contract should be a language-neutral schema;
   JSON and Python are projections of it.

2. **The most durable architecture is not a single universal tree.** It is a
   source-grounded document graph with several derived views (Markdown block structure,
   section hierarchy, inline/link index, sentence/token `TextDoc` view, optional
   rendered-layout geometry) plus external annotations that target nodes or spans. A
   single tree cannot express all of these because they overlap and cross-cut; a node
   table with typed layers can.

3. **For Chopdiff, the near-term Python API should remain `TextDoc`-centered.** The
   active implementation plan extends `TextDoc` with spans, sections, blocks, and links.
   `DocGraph` is the better name for the future language-neutral serialized
   graph/contract derived from `TextDoc`, not a competing Python document model unless a
   later use case proves that extra runtime object is worth the public API surface.

A corollary of (2): the "zoomable UI" and "multiple structural views" use cases are not
separate requirements. They are the same requirement: one model projected to many views
at many granularities.

## Questions to Answer

1. What existing document models, parsers, editor frameworks, and annotation standards
   should influence Chopdiff's next document model?
2. Which approaches preserve source grounding well enough for precise analysis and
   manipulation?
3. Which approaches provide clean, cross-platform JSON serialization for client-side UI,
   annotations, and processing?
4. Which approaches help with normalized Markdown rewriting versus live rich-text
   editing?
5. Is "data model" a distinct deliverable from "JSON serialization" and "Python
   implementation," and what follows from treating them separately?
6. Are "visual/zoomable UI" and "multiple structural views" separate requirements or one?
7. What is the cleanest conceptual core for annotations that survive edits and reparses?
8. How should this fit with the current `TextDoc`, block-aware document, and
   parser-backed Markdown segmentation plans?

## Scope

Included:

- Markdown and Markdown-derived structures
- HTML DOM and Markdown-to-HTML DOM workflows
- Editor document models: ProseMirror, Tiptap, Slate, Lexical, Quill Delta, and the
  block-id-first models (Editor.js, BlockNote, Notion)
- Parser-level systems: Marko, mdast/unist, CommonMark/cmark-gfm, djot, Tree-sitter, and
  Lezer
- Cross-format ASTs: Pandoc
- Stable-identity systems: lossless/red-green syntax trees (Roslyn, rowan, libSyntax) and
  CRDT rich-text (Yjs, Automerge, Loro)
- Annotation targeting models: W3C Web Annotation and the NLP stand-off tradition (UIMA
  CAS, brat, GATE)
- Layout-aware document extraction for visual/page overlays (PDF.js, Docling,
  Unstructured)
- Semantic XML models (DocBook, JATS, TEI) as discipline references
- The data-model / serialization / implementation separation and what it implies

Excluded for now:

- Selecting a new dependency or adding implementation code.
- Full PDF/OCR benchmark research.
- Collaborative-editing protocol design beyond lessons drawn here.
- Perfect source-preserving Markdown surgery. Normalized rewriting is the better first
  target.

## Existing Project Context

### `TextDoc`

`TextDoc` currently parses source into blank-line-separated `Paragraph`s and
sentence-level units. It preserves source text references through fixed offsets and
supports reassembly, replacement, subdocuments, word-token mappings, token diffs, and
windowed transformations.

Relevant strengths:

- Fast, simple linear analysis
- Source-referenced paragraph and sentence offsets
- Existing `TextUnit` size machinery
- Word-token diffs and mappings useful for transform validation and stitching
- Coarse Markdown block classification through Marko/Flowmark

Relevant limitations:

- `Offsets` are start-only today.
- Paragraphs are blank-line blocks, not parser-backed Markdown blocks.
- Tight lists, loose lists, nested lists, and fenced code with blank lines cannot be
  modeled precisely by blank-line segmentation alone.
- Sentence spans can be best-effort when the splitter normalizes whitespace.
- Links, inline code spans, and inline HTML are not yet first-class source-grounded
  nodes.
- Current offsets are Python string character offsets into the source text, not byte
  offsets. The serialized cross-language contract must say this explicitly and provide
  conversion indexes for byte-oriented parsers and UTF-16-oriented browser/editor APIs.
- `TextDoc` has exact source references for stored blocks, but the editable
  `reassemble()` form is still normalized: leading/trailing whitespace outside stored
  blocks and runs of blank lines are not preserved as a byte-for-byte full-document
  round trip.
- This branch now locks Flowmark v0.7.1 through a maintainer-approved cool-off
  exception, so the public `flowmark.atomic_spans` and `flowmark.markdown_ast` APIs are
  available for the block-aware plan. Marko remains locked at v2.2.2; v2.2.3 is current
  on PyPI but has not been separately excepted.

### `TextNode`

`TextNode` already proves a useful pattern: a tree view can be grounded in the original
source by storing offsets and content boundaries, while still offering rollups, child
selection, and reassembly. It is intentionally limited to `div`-oriented structure, but
the shape is directly relevant to a broader document model.

### Active Specs

The current project specs already point in the right direction:

- `plan-2026-05-26-block-aware-doc.md` proposes exact spans, sections, structural
  blocks, links, and link-aware sentences, all extending `TextDoc` in place. This should
  remain the implementation plan.
- `plan-2026-05-26-markdown-block-segmentation.md` (archived) proposed a parallel
  parser-backed `MarkdownDoc`/`MarkdownBlock` layer; the chosen direction extends
  `TextDoc` rather than adding a parallel model.

This research reinforces those specs and makes the "derived overlay" architecture
explicit: keep source text and `TextDoc` as core linear grounding, add specialized views
on top, and define `DocGraph` as the serialized graph/schema projection. That is
different from resurrecting the archived `MarkdownDoc` as a second Python-side model.

## Findings

### The Deliverable Is a Data Model, Not a Format and Not an Implementation

A document "model" conflates three layers that should be designed and versioned
independently:

- **Conceptual model:** the entities and relationships: a source, a stable node table,
  spans, typed layers (sections, blocks, links, sentences, divs), and external
  annotations. This is the contract.
- **Serialization:** how the model is written down for transport and storage. JSON is
  the target, but JSON is a projection, not the model. The model should also be
  expressible as Protobuf/FlatBuffers or an in-memory columnar form without changing the
  contract.
- **Implementation:** Python dataclasses today; possibly a TypeScript mirror for the
  client, or a Rust/WASM core later. None of these is the model either.

Why this matters concretely:

- The public JSON schema must be **boring and parser-agnostic**: no Marko class names, no
  Python type tags, no field that only makes sense in one runtime. A field like
  `marko_node_type` belongs in optional `metadata`, never in the stable record.
- The model should be specified in a language-neutral artifact (a JSON Schema plus a
  prose spec, or a single IDL) so a TypeScript client and a Python core are two
  implementations of one contract, not two models that drift. This is the discipline LSP
  uses: the protocol is the spec; editors and servers are implementations.
- IDs and spans are the cross-language lingua franca. As long as every node has a stable
  `id` and a `source_span` in well-defined units, any language can cooperate on the same
  document. **The offset unit must be pinned in the spec**: UTF-8 byte offsets vs UTF-16
  code units vs Unicode scalar values, because JS strings are UTF-16-indexed, Python
  strings are scalar-value-indexed, and PDF/OCR tools count differently. This one detail
  is where cross-language document models silently diverge.

### Coordinate Systems Are a First-Class Design Choice

The fact-check pass makes this stronger than a footnote:

- W3C Web Annotation distinguishes `TextPositionSelector` (character positions) from
  `DataPositionSelector` (byte positions), and its text quote model explicitly says text
  selection is in Unicode code points rather than code units.
- `unist`/`mdast` positions use line, column, and optional offset; the offset is a
  character in the source file.
- LSP has three negotiated position encodings: UTF-8 bytes, UTF-16 code units, and
  UTF-32 code units. UTF-16 is the default editor protocol behavior, while UTF-32 is the
  encoding-agnostic "Unicode code point" form.
- Tree-sitter exposes byte ranges and points. Lezer/CodeMirror exposes integer document
  positions in the editor string model. Source maps use generated/original line and
  column positions, and ECMA-426 specifies UTF-16 columns for JavaScript/CSS source maps.

Recommendation: the first `DocGraph` schema should make `source_span` use
`unicode_code_points`, matching Python `TextDoc` offsets and W3C text selectors. Where a
consumer needs byte offsets or browser/editor offsets, expose explicit derived fields or
conversion tables such as `byte_span`, `utf16_span`, and `line_column_span`. Do not
overload one `start`/`end` pair with multiple coordinate systems.

### Zoom and Views Are One Requirement, Not Two

"Visual/zoom UI" and "multiple structural views" collapse into one requirement: **a
single model that supports cheap projection to many views at many granularities.** "Zoom"
is just choosing which view and which level to render:

- Zoomed out: the section tree / TOC (a view)
- Mid zoom: the block list, or a section's blocks (a view)
- Zoomed in: sentences, links, tokens, inline structure (views)
- Visual overlay: geometry attached by node id (a view)

So the unified requirement is: *one stable node set, addressable by id, from which
section tree, block tree, linear token stream, link index, and layout overlay are all
O(n) derivable projections that share node ids.* If the model has that property, both
"zoomable rendering" and "different structural views" are free; if it privileges one
hierarchy (a single mutable tree), both are expensive. "Efficiently designed for all
these use cases" therefore means: stable ids, random access by id and by offset, and the
ability to hold **overlapping, non-nesting** layers (sections cross block containment;
links are inline ranges; annotations are arbitrary). A pure tree cannot do the last; a
node table + typed span layers can.

### Grounding Patterns

The strongest systems keep several identifiers for the same target:

- A structural node id
- A source span in original input coordinates
- A text-quote selector with prefix/suffix for robustness after edits
- Optional rendered-layout coordinates for visual UI
- Optional path selectors for DOM/XML/editor models

This matters because any single targeting scheme fails under some transformation:

- Source offsets are precise but brittle after edits.
- Quoted text can survive small edits but may be ambiguous.
- Node ids are stable only within one parse or one operation history.
- DOM paths are useful in browser UIs but can change after rendering or normalization.
- Visual boxes are essential for layout inspection but are not semantic source truth.

The W3C Web Annotation model is the best reference for targeting: its selectors include
text position, text quote, fragment, CSS, XPath, data position, and SVG. The lesson is
not to adopt JSON-LD wholesale, but to store multiple selectors per target. (The NLP
stand-off tradition (UIMA CAS, brat, GATE) is the deeper reference for layering many
annotations over one immutable source; see below.)

### Markdown ASTs

#### Marko

Marko is the best near-term parser fit: it is already in the dependency graph and
Flowmark uses it. It provides a Python AST and GFM support through extensions. The main
gap is source spans: Marko elements do not expose exact spans by default, but Marko's
`Source` object maintains a moving parse position and `Parser.parse_source()` is small
enough to wrap for span annotation. Local verification on the locked Marko 2.2.2 source
confirms this is still plausible; PyPI now lists Marko 2.2.3 (2026-05-28), which should
not be adopted until it clears the repository's cool-off policy. **Recommendation:** use
Marko first for parser-backed `TextDoc.blocks()` / `DocGraph` derivation,
matching the current Python stack and avoiding a new parser dependency.

#### mdast and unist

The unified ecosystem's `mdast`/`unist` are the strongest JSON-first Markdown AST
reference. `unist` standardizes `type`, `children`, `value`, and positional information;
`mdast` defines heading, paragraph, list, list item, link, image, code, table, and
footnote nodes. The tradeoff: it is JavaScript-first and would duplicate the Python/Marko
path. **Recommendation:** borrow the JSON shape and positional conventions, not the
implementation.

#### CommonMark and cmark-gfm

CommonMark implementations are strong references for spec compliance and source
positions. `commonmark.js` exposes node `sourcepos`, and cmark/cmark-gfm can render
source positions. Useful prior art for the exact-span strategy, but a second Markdown
parser path complicates Flowmark alignment. **Recommendation:** treat as
validation/fallback research, not the first implementation.

#### djot

**djot** (by John MacFarlane, author of Pandoc and a CommonMark lead) is a Markdown
successor designed for unambiguous parsing, and it carries **native source positions**.
If attaching exact spans to Marko proves painful (the block-aware plan's main open risk),
djot is the cleanest Markdown-family AST-with-sourcepos to evaluate as a fallback parser.
The official JavaScript parser exposes `sourcePositions: true` and event spans; djot is
also still described as not completely stable. **Recommendation:** keep Marko as the
first path; hold djot as the fallback.

### Cross-Format ASTs

#### Pandoc AST

Pandoc is the strongest cross-format AST and transformation model: it parses many input
formats into an intermediate AST, exposes JSON filters, and writes many output formats.
Excellent for normalized conversion and broad transformations. The gap is source
grounding: Pandoc's AST is a normalized intermediate representation, not an exact source
map back to Markdown byte offsets, and it is an external runtime concern.
**Recommendation:** use Pandoc as an optional export/import bridge or validation tool,
not the canonical source-grounded model.

### DOM-Based Approaches

#### Browser DOM

Excellent for interactive UI, link discovery, rendered selection, accessibility, and
inspection (`DOMParser`, DOM Range APIs). The gap: DOM is post-parse and post-repair and
does not preserve original Markdown source spans, constructs, or normalization choices.
**Recommendation:** use DOM as a client-side rendering/interaction view, with
`data-node-id` or `data-sourcepos` attributes emitted from the source-grounded model.

#### Markdown to HTML DOM

Rendering Markdown to HTML then parsing/manipulating the DOM is convenient and supports a
zoomable visual overview if generated elements carry source/node identifiers. The gap is
semantic mismatch: list items, reference links, footnotes, tables, raw HTML, and
normalized whitespace may not map cleanly back to source. **Recommendation:** generated
HTML should be a view over the source-grounded model, not the source of truth.

### Editor Document Models

#### ProseMirror and Tiptap

ProseMirror is the most relevant client-side editor model: a schema-constrained tree,
JSON serialization, immutable document states, transactions, and position maps. Tiptap
builds a friendlier framework on top and recommends ProseMirror JSON for storage. Its
transaction model is the strongest reference for move-section, insert-node,
replace-range, and normalize operations. The gap: once content is in ProseMirror JSON it
becomes an editor model rather than the original Markdown source. **Recommendation:**
learn from its schema, transactions, and position maps, and consider a client adapter;
do not make ProseMirror JSON canonical unless the product becomes primarily an editor.

#### Slate and Lexical

Flexible JSON editor models, useful references for custom editors, normalization, and
plugin-driven behavior, but less aligned with Markdown source rewriting and semantic
analytics. **Recommendation:** secondary references only.

#### Quill Delta

A clean JSON format that represents both documents and changes; excellent for
operational-transform-style rich text. The gap is structural expressiveness: less
natural for section trees, nested block semantics, and source spans.
**Recommendation:** borrow the "document plus operations" idea, not the linear Delta
format as the main model.

#### Block-JSON Editors: Editor.js, BlockNote, Notion

The block-id-first models are closer to the stated use cases ("annotate nodes," "move
sections") than the position-map or nested-node editors:

- **Editor.js:** dead-simple `{blocks: [{id, type, data}]}` JSON; trivial to consume
  cross-language; weak inline/source grounding.
- **BlockNote:** a block model with stable block ids built on ProseMirror/Tiptap,
  providing block-level identity (good for move/annotate) with ProseMirror editing underneath.
- **Notion block model:** every block has an id and a parent; the whole document is a
  block tree addressed by id, the canonical example of "blocks as the unit of
  addressing, annotation, and reorganization."

These validate that a **block-id-addressed JSON** is the ergonomic shape for client UIs
that move, annotate, and reorder. **Recommendation:** borrow the block-id-addressed JSON
ergonomics for the client projection; keep source spans (which these lack) as Chopdiff's
differentiator.

### Incremental Parser Systems

#### Tree-sitter

Excellent at concrete syntax trees with byte ranges and incremental parsing; nodes expose
byte ranges and descendant lookup by byte/point. Strong fit for editor-grade source
mapping. The gap is semantic modeling: it produces a syntax tree, not a document model
with sections, prose semantics, links, annotations, and normalized writing.
**Recommendation:** useful later if client-side incremental Markdown parsing becomes a
priority; not needed for the first Python-backed model.

#### Lezer and CodeMirror

Lezer is CodeMirror's parser system: compact syntax trees with from/to positions,
incremental parsing, and Markdown support. Same gap as Tree-sitter: a syntax/editor
layer, not the full semantic overview. **Recommendation:** a possible client-side editor
and live syntax view, fed by or synchronized with the canonical source-grounded JSON.

### Stable Identity: Lossless Trees and CRDTs

Two well-developed traditions solve "stable node identity," each for a different regime.

#### Lossless / Red-Green Syntax Trees (Identity under Reparse)

The strongest prior art for "exact source grounding with stable structural identity" is
the lossless syntax tree used by modern compilers and IDEs:

- **Roslyn red-green trees** (C#): immutable "green" nodes store kind, width, and trivia
  (whitespace/comments) but *not* absolute position; a lazily-created "red" facade
  computes absolute positions on demand. Because trivia is in the tree, the tree
  reproduces the source byte-for-byte and node identity is independent of position.
- **rowan / rust-analyzer** and **Swift libSyntax/SwiftSyntax:** the same pattern,
  full-fidelity, lossless, position-on-demand.

Two lessons map directly onto Chopdiff: (1) `TextNode` already reaches for this with
character offsets and exact reassembly; the red-green split is the principled version
(separate immutable structural identity from computed position), and it answers the
block-aware plan's open question about node identity surviving edits. (2) "Trivia" is the
compiler word for exactly Chopdiff's promise to preserve whitespace and reassemble
verbatim; the model should keep trivia first-class rather than reconstruct separators
heuristically on reassemble.

#### CRDT Rich-Text (Identity under Live Edits)

CRDTs have largely superseded operational transforms for local-first and collaborative
documents:

- **Yjs, Automerge, Loro:** every character/element carries a stable unique id, so a
  range pinned to ids survives arbitrary concurrent edits with no reattachment
  heuristics. All three have clean JSON/binary export.

The hardest annotation problem, reattaching after edits, is *solved* by id-per-element
when the document is being actively edited. Span+quote selectors are right for the
read-mostly, reparse-from-source path; CRDT ids are right for a live collaborative
editor. **Recommendation:** defer CRDTs to the client edge (do not make a CRDT canonical
since it makes Markdown secondary, the same failure mode as making ProseMirror canonical);
keep the option open by allowing annotation targets to carry an opaque `anchor` id
alongside span/quote.

### Stand-off Annotation

The strongest prior art for "annotate nodes, keep references to the original, support
many independent layers" is the stand-off markup tradition:

- **UIMA CAS** (Common Analysis Structure): an immutable text ("Sofa") plus *all* analysis
  as external typed annotations carrying offset ranges, with multiple "views" over one
  Sofa. Almost exactly the proposed architecture, with a mature type system and decades
  of NLP tooling.
- **GATE, brat, WebAnno:** practical stand-off annotation stores and UIs; brat's
  offset-range model and visualization are a good concrete reference.
- **W3C Web Annotation:** the web-native targeting model with multiple selectors.

The unifying insight: **sections, links, AI summaries, and human notes are all the same
kind of thing: a typed layer of offset-grounded (or node-grounded) annotations over an
immutable source.** This is stronger than a "views + separate annotations" split: if the
model treats every derived structure as a layer, then "give me an AI summary of section
3" and "give me the TOC" use one mechanism. Parsing produces the base layers; AI and
humans add more. **Recommendation:** make stand-off layering the conceptual core; borrow
W3C selectors so a layer can reattach after a reparse or edit (store node id *and* source
span *and* text-quote).

### Dual Addressing: Source-Canonical References, Tree-Convenient Handles

A reference to "a piece of the document" must work in four contexts: reading the source,
editing the parsed tree (possibly via a bridged editor), saving, and interacting with
rendered output, and those contexts disagree about what is stable:

- The **source** is canonical and is what persists; a saved reference must be
  source-grounded (span + quote), because node ids are meaningful only within one parse.
- The **parsed tree** is the convenient handle while editing ("annotate this table"), but
  its node ids are per-parse / transient.
- **Rendered output** needs to map a selection back to an element and thence to source.

The resolution is asymmetric. **Model → source is total**: every node carries a
`source_span`, so attaching at the model level (a table, a link) is automatically grounded
in the original document. **Source → model is re-resolution**: after a (re)parse, match by
span, then by text-quote, then by a structural path. That yields one rule set: edit
against tree handles, **persist source-grounded**, re-resolve to nodes on load, and emit
`data-node-id` / `data-source-span` in rendered HTML so UI selections round-trip. An
editor-bridge path (ProseMirror/block-JSON in memory) then serializes annotations *through*
the model to *original document + source-grounded targets*, so the saved artifact never
depends on a transient editor or parse identity. This is W3C multi-selector targeting plus
persistence discipline: name which selector is *canonical* (source span), which is
*convenient* (node id), and which is *robust* (quote / structural path).

### Source Maps and Transform Provenance

Source maps are not a document model, but they are a useful pattern for normalized
rewriting. ECMA-426 standardizes a JSON source map format for bidirectional mapping from
generated code back to original sources; its core idea is a compact table of
generated-position to original-position mappings, not a semantic tree.

For Chopdiff this suggests a separate **provenance layer**:

- `source_span` answers "where did this node come from in the canonical source?"
- `generated_span` answers "where did this node land in normalized/rendered output?"
- `mapping_kind` distinguishes exact, normalized, inferred, inserted, and deleted
  mappings.
- Operation records (`move_section`, `replace_block`, `normalize`) should emit mapping
  tables when they produce a new source string.

Do not make source maps the canonical model. Use their generated↔original mapping
discipline for normalized Markdown rewrite validation, diff review, and UI highlights.

### Layout-Aware Document Extraction

#### PDF.js

Exposes page text content, viewport transforms, and page structure trees when available.
Highly relevant for visual overlays, page coordinates, text selection, and PDF
inspection. The gap: PDF text extraction normalizes and reorders text and does not map
cleanly to Markdown source. **Recommendation:** treat PDF.js geometry as a layout overlay
when the source is a PDF, not as the canonical model for Markdown.

#### Docling and Unstructured

The modern "document AI extraction" direction: parse PDFs, DOCX, PPTX, images, and other
formats into structured elements with coordinates, tables, reading order, and JSON
export. Highly relevant for visual analysis and imported documents; less relevant for
exact Markdown rewrite when Markdown is the original source. **Recommendation:** support
an optional `layout`/`imported_elements` layer attaching page and bounding-box
information to source-grounded nodes where alignment is possible.

### Semantic XML Models

DocBook, JATS, and TEI show mature semantic document modeling: rich element vocabularies,
validation, and long-term publishing workflows. The tradeoff is complexity: too
heavyweight for a Markdown-first, AI-assisted workflow. **Recommendation:** borrow the
discipline of explicit semantic roles and schemas, but keep the Chopdiff model lighter
and JSON-native. (TEI also has its own stand-off tradition, reinforcing the layering
direction.)

## Key Insights

- **Markdown source should remain canonical.** The parsed overview is derived, cached,
  serialized, annotated, and transformed; edits should ultimately produce new source text
  and then reparse. This avoids the hardest class of bugs: a rich document model drifting
  away from the actual Markdown file.
- **`TextDoc` is the implementation core; `DocGraph` is the contract.** The
  active plan should keep extending `TextDoc` in place while the schema layer defines a
  cross-language graph projection. Avoid a parallel Python document model until a real
  runtime boundary requires it.
- **Model ≠ format ≠ implementation.** The contract is a language-neutral schema; JSON
  and Python are projections. Pin the offset unit in the spec; the first version should
  use Unicode code points for `source_span`, with explicit byte/UTF-16 conversion fields
  when needed.
- **A graph is more honest than one tree.** Markdown blocks form one hierarchy; sections
  form a heading-derived hierarchy that crosses block containment; sentences/tokens form
  a linear sequence; links are inline ranges; layout groups by page/column/line;
  annotations are external claims. The practical model is a node graph with derived
  indexes and named views.
- **Zoom and views are the same requirement:** stable ids + random access + overlapping
  layers makes every view and zoom level a cheap projection.
- **One mechanism for all structure.** Stand-off layering (UIMA/W3C) unifies parsed
  structure (sections, blocks, links) and added structure (AI summaries, human notes) as
  typed layers over immutable source.
- **JSON should be stable and boring:** explicit discriminated records, no
  parser-internal class names; parser specifics live in `metadata`.
- **Annotations should be separate from the parse:** portable across reparses, many
  independent layers over the same model.
- **References are dual-addressed, source-canonical.** Reference parsed elements by node id
  in memory, but persist source-grounded (span + quote): model→source resolution is total
  (every node has a span), source→model is robust re-resolution, and rendered output carries
  node id + source span so selections round-trip. Save keeps the original document plus
  source-grounded annotations; the tree is the editing convenience, not the durable anchor.
- **Visual analysis is an overlay:** visual geometry is not document structure; for
  Markdown, source structure drives the model and geometry attaches to nodes separately.
  For PDFs/OCR, geometry may be the only reliable initial grounding.
- **Stable identity is a solved problem, twice:** red-green trees give identity under
  reparse (compiler world); CRDT ids give it under live edits (collaborative world). Use
  the first for the canonical pipeline; reserve the second for the edit edge.
- **Generated output needs provenance, not a second truth.** Source-map-style
  generated↔original mappings are the right layer for normalized Markdown output,
  rendered HTML, and rewrite validation.
- **Chopdiff's moat is grounding.** Editors (ProseMirror, Editor.js, BlockNote) and CRDTs
  all make the original source secondary; Chopdiff keeps source canonical with exact
  source references and should move toward exact span slicing / verbatim block
  reassembly rather than trading grounding away.

## Comparison Matrix

Scored on the requirement axes: **A** source grounding, **B** structure richness, **C**
clean cross-platform JSON, **D** edit/writeback fit, **E** annotation targeting +
reattachment after edits, **F+G** unified model→views (one model projected to many
views/zoom levels). ✅ strong / ◐ partial / ✘ weak.

| Approach | A Ground | B Struct | C JSON | D Write | E Annot/reattach | F+G model→views | Role for chopdiff |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Current `TextDoc` | ◐ start-only spans | ◐ blocks | ◐ if serialized | ✅ text transforms | ◐ | ◐ | Core linear layer (keep) |
| `TextNode` div tree | ✅ div spans | ◐ HTML chunks | ◐ if serialized | ◐ | ◐ | ◐ | Named-structure layer (keep) |
| Marko AST | ◐ no spans by default | ✅ blocks/inlines | needs wrapper | ✅ w/ Flowmark | ✘ | ◐ | **First parser-backed path** |
| mdast/unist | ✅ position | ✅ | ✅✅ | ✅ (JS) | ◐ | ◐ | Borrow JSON shape |
| CommonMark/cmark-gfm | ✅ sourcepos | ✅ | ◐ | ✅ renderer | ◐ | ◐ | Validation/fallback ref |
| djot AST | ✅ native sourcepos | ✅ | ✅ | ✅ | ◐ | ◐ | Fallback parser to Marko |
| Pandoc AST | ✘ original spans | ✅✅ cross-fmt | ✅✅ | ✅✅ normalized | ✘ | ◐ | Optional bridge, not canonical |
| Browser DOM | ✘ for MD source | ✅ rendered | ◐ | ✘ MD source | ◐ | ◐ | UI view only |
| MD→HTML DOM (`data-node-id`) | ◐ if emitted | ◐ to ✅ | ◐ | ◐ | ◐ | ✅ | Derived render view |
| ProseMirror/Tiptap | ✘ MD source | ✅ | ✅✅ | ✅✅ transactions | ◐ pos-map | ✅ | Client adapter + design ref |
| Slate/Lexical | ✘ MD source | ✅ custom | ✅ | ✅ editors | ◐ | ✅ | Secondary editor refs |
| Quill Delta | ✘ MD source | ◐ | ✅✅ | ✅✅ deltas | ◐ | ◐ | Borrow operation ideas |
| Editor.js/BlockNote/Notion (block-JSON) | ✘ MD source | ✅ blocks+ids | ✅✅ | ✅ | ✅ block ids | ◐ | Client JSON ergonomics |
| Tree-sitter | ✅✅ byte ranges | syntax-rich | ◐ | ◐ source editors | ◐ | ◐ | Later incremental parser |
| Lezer/CodeMirror | ✅✅ editor positions | syntax-rich | ◐ | ◐ browser editors | ◐ | ✅ | Later client live parser |
| Source maps / ECMA-426 | ✅ generated↔original positions | ✘ semantic | ✅ | ✅ provenance | ◐ | ◐ | Provenance layer for normalized output |
| Roslyn red-green / rowan / libSyntax | ✅✅ full-fidelity + trivia | ✅ | n/a | ✅ | ✅ stable ids on reparse | ◐ (one tree) | **Pattern for structural tree** |
| CRDT (Yjs/Automerge/Loro) | ✘ for MD source | ◐ | ✅ | ✅✅ | ✅✅ survives edits | ◐ | Edit-edge identity (defer) |
| W3C Web Annotation | targeting only | ✘ | ✅✅ | n/a | ✅✅ multi-selector | n/a | Annotation selector ref |
| UIMA CAS / brat / GATE (stand-off) | ✅ offsets | typed layers | ◐ to ✅ | n/a | ✅✅ typed layers | ✅ many views/Sofa | **Conceptual core for layers** |
| PDF.js | ✅ page/text geometry | ◐ visual | ◐ | ✘ for MD | ◐ | ✅✅ | Layout overlay |
| Docling/Unstructured | ✅ imported layout | ✅ extracted | ✅ | ◐ imported | ◐ | ✅✅ | Optional import/layout layer |
| DocBook/JATS/TEI | ✅ XML structure | ✅✅ | ◐ XML not JSON | ✅ publishing | ◐ (TEI standoff) | ◐ | Semantic-model inspiration |

## Options Considered

There are two distinct decision axes: the **architecture** of the model (Options A–F) and
how the model is **specified** as a contract (Options G–I).

### Architecture

#### Option A: Extend `TextDoc` into one comprehensive model

Add spans, sections, links, parser-backed blocks, visual layout, and annotations directly
onto `TextDoc`.

**Pros:** simple public story (one object); maximum reuse of size/token/diff/transform
APIs; incremental from current code.
**Cons:** risks making `TextDoc` responsible for unrelated views; parser-backed block
boundaries conflict with current paragraph/window assumptions; visual layout and
annotations don't naturally belong in a linear text model.
**Assessment:** useful for spans and simple convenience APIs, too constraining as the
full architecture.

#### Option B: Add a parser-backed `DocGraph` projection

Keep `TextDoc` as the linear text model; add a serialized graph projection that owns
source metadata, parser-backed nodes, sections, links, annotations, provenance, and
indexes back into `TextDoc`.

**Pros:** preserves existing `TextDoc` behavior; exact Markdown structure where
blank-line paragraphs are insufficient; natural JSON model for UI and annotations; can
evolve without breaking diff/window code; aligns with the active plan by making
`DocGraph` a contract/projection rather than a competing Python API.
**Cons:** requires careful mapping between parser spans and `TextDoc` spans; adds a
schema/projection layer that must be versioned and tested.
**Assessment:** Recommended.

#### Option C: Adopt mdast/unist as the canonical JSON schema

**Pros:** mature JSON shape; broad ecosystem; strong positional convention.
**Cons:** JavaScript-first; lacks Chopdiff sentence/token/diff/section/annotation needs
without extensions; duplicates the Python/Marko stack.
**Assessment:** good schema inspiration, not the canonical implementation.

#### Option D: Use Pandoc AST as the canonical model

**Pros:** excellent cross-format model and normalized writing; mature filters; many
formats.
**Cons:** source grounding to original Markdown is not the design center; external
runtime; less aligned with `TextDoc` spans/tokens/diffs.
**Assessment:** useful optional bridge, not canonical.

#### Option E: Use ProseMirror/Tiptap JSON as the canonical model

**Pros:** excellent client-side editing, schema, transactions, UI behavior.
**Cons:** original Markdown source becomes secondary; lossy/opinionated roundtrip;
Python-side analytics depend on an editor-specific model.
**Assessment:** strong client adapter and design reference, not canonical.

#### Option F: Source-grounded document graph with multiple views

Store canonical source plus stable JSON nodes, spans, indexes, views, annotations, and
optional layout overlays.

**Pros:** handles all major use cases without forcing incompatible structures into one
tree; keeps source grounding explicit; lets UI, AI, annotations, transforms, and layout
share node ids; serializes cleanly and stays parser-agnostic at the public boundary.
**Cons:** more conceptual surface than a single AST; requires disciplined schema design
and validation.
**Assessment:** Recommended architectural north star.

### Model Specification

#### Option G: Specify the model as a language-neutral schema (recommended)

Author a JSON Schema (or IDL) + prose spec as the source of truth (source record, stable
node table, typed span layers, annotations), with Python and any future TypeScript/Rust
bindings as implementations; offset unit pinned explicitly.

**Pros:** prevents Python/JS model drift; enables a true cross-language client; JSON stays
boring by construction; versionable contract independent of any runtime.
**Cons:** up-front schema discipline; a second artifact to maintain; risk of
over-specifying before use cases are proven.
**Assessment:** Recommended, but start minimal (source + nodes + one or two layers) and
grow around real use cases.

#### Option H: Python dataclasses are the model; JSON is incidental

**Pros:** fastest to build; matches current Chopdiff style.
**Cons:** the model becomes whatever Python emits; cross-language clients
reverse-engineer it; parser/runtime details leak into JSON; offset-unit ambiguity goes
unaddressed.
**Assessment:** fine for a prototype, wrong as the long-term contract given the
cross-language goal.

#### Option I: Adopt an existing block-JSON or editor model as canonical

Use Editor.js/BlockNote/ProseMirror/CRDT JSON as the canonical model.

**Pros:** mature client tooling and JSON shapes.
**Cons:** all make original Markdown source secondary; lossy/opinionated roundtrip; gives
up Chopdiff's grounding moat.
**Assessment:** client-projection and ergonomics references only, not canonical.

### Eliminated Early

- **Pandoc as canonical (Option D):** source grounding is not its design center; external
  runtime. Kept only as a bridge.
- **ProseMirror/CRDT as canonical (Options E, I):** make Markdown secondary; reserved for
  the client/edit edge.

## Recommended Direction

Build a source-grounded `DocGraph` projection (Option B + F), specified as a
language-neutral contract (Option G), with these components:

1. **Source record:** original text or external reference; content hash; source format
   and parser metadata. Pin `source_span` to Unicode code points here, and expose
   explicit derived byte/UTF-16 coordinates when needed.
2. **Stable node table:** `id`, `kind`, `role`, `parent`, `children`, `source_span`,
   optional `analysis_span`, and `attrs`; parser-specific details hidden behind stable
   public fields (in `metadata`).
3. **Views** (all derived projections sharing node ids): `blocks` (parser-backed block
   order), `sections` (heading tree + TOC), `links` (inline link/image/reference index),
   `sentences` (`TextDoc` index), `tokens` (word-token index on request), `divs`
   (explicit HTML/div structure), `layout` (optional rendered/imported geometry).
4. **Annotations:** stored separately, as typed stand-off layers targeting nodes or
   ranges with multiple selectors: node id; source span; text quote with prefix/suffix;
   optional opaque anchor (for future CRDT); optional DOM path; optional visual bbox.
5. **Operations and provenance:** high-level records for manipulations: move section;
   replace block; insert after node; rewrite span; normalize document. Apply to source
   (or to a normalized Markdown AST), emit new Markdown, attach generated↔original
   mapping records, then reparse and validate.
6. **Normalized output:** Flowmark remains the likely Markdown normalizer; Pandoc an
   optional cross-format bridge.

Borrow the **red-green pattern** (immutable nodes + computed positions, trivia
first-class) for the eventual structural tree, and the **stand-off layering** model
(UIMA/W3C) for views + annotations as one mechanism.

## Proposed JSON Sketch

```json
{
  "schema": "chopdiff.doc_graph.v1",
  "source": {
    "format": "markdown",
    "offset_unit": "unicode_code_points",
    "sha256": "...",
    "text": "optional"
  },
  "nodes": [
    {
      "id": "n_root",
      "kind": "document",
      "role": "root",
      "children": ["n_0001"]
    },
    {
      "id": "n_0001",
      "kind": "heading",
      "role": "section_title",
      "source_span": {"start": 0, "end": 12},
      "byte_span": {"start": 0, "end": 12},
      "analysis_span": {"start": 2, "end": 12},
      "parent": "n_root",
      "children": [],
      "attrs": {"level": 1, "text": "Overview"}
    }
  ],
  "views": {
    "toc": ["n_0001"],
    "blocks": ["n_0001"],
    "links": [],
    "sentences": []
  },
  "annotations": [
    {
      "id": "a_0001",
      "kind": "summary",
      "target": {
        "node_id": "n_0001",
        "source_span": {"start": 0, "end": 12},
        "text_quote": {"exact": "Overview", "prefix": "# ", "suffix": "\n\n"}
      },
      "body": {"text": "Top-level section heading."}
    }
  ],
  "layout": [],
  "provenance": []
}
```

Parser-specific source can be recorded in metadata but must not leak into the stable
public schema. `offset_unit` is explicit so every consumer agrees on coordinates; byte
and UTF-16 spans are optional derived coordinates, not substitutes for the canonical
`source_span`.

## Use Case Mapping

### Dynamic Zoomable UI

Section tree for top-level navigation; block list for medium zoom; sentence/link/token
views for detail zoom; optional layout overlay for rendered positioning; DOM rendering
with `data-node-id` for browser interaction. (All are projections of the one node table;
see "zoom and views are one requirement.")

### AI and Human Annotations

External annotation records as typed stand-off layers; W3C-inspired target selectors;
node ids for fast lookup; source spans and text quotes for reattachment after edits;
layers for summaries, claims, TODOs, rewrite suggestions, citations, visual comments, and
human review.

### Link Identification and Reference

Parser-backed inline nodes from Marko; link records with text, URL, title, source span,
containing block, containing sentence, and containing section; separate treatment of
inline links, reference links, autolinks, images, and raw HTML anchors.

### Section Moves and Semantic Reorganization

Section view for selecting move targets; source spans for exact extraction when safe;
parser-backed normalized rewrite when exact extraction is unsafe; operation records to
describe the move before emitting new Markdown; reparse and diff to validate.

### Normalized Markdown Rewriting

Parser-backed Markdown blocks for structure; Flowmark for normalization; `TextDoc` token
diffs for validating how much changed; optional Pandoc bridge if the output format is not
Markdown.

### Visual Document Analysis

Browser-rendered HTML layout for Markdown; PDF.js layout for PDF views;
Docling/Unstructured-style imported element coordinates for non-Markdown sources; layout
overlay keyed by node ids when alignment is possible.

## Implementation Implications

### Near-Term Additions

- Add computed `[start, end)` spans to `Paragraph` and `Sentence`, using Unicode code
  point offsets to match current `TextDoc` indexing
- Add `block_at_offset` and `sentence_at_offset`
- Add a clear source-text retention/accessor strategy for exact span slicing
- Add parser-backed structural blocks as a `TextDoc` overlay/projection, not a parallel
  Python document model
- Add heading-derived sections and TOC
- Add link extraction with spans

### Medium-Term Additions

- Add a JSON Schema (language-neutral) plus Pydantic/dataclass serialization for
  `DocGraph`; pin the offset unit and add conversion helpers for UTF-8 bytes and
  UTF-16 code units
- Add annotation target records (stand-off layers)
- Add operation records for structural transforms
- Add provenance records for normalized/generated output, source-map style
- Add a layout overlay type
- Add browser rendering helpers that emit `data-node-id`
- Define the model→views projection contract and confirm each view is O(n) from the node
  table

### Later Additions

- Add a ProseMirror/Tiptap or block-JSON adapter if live rich-text editing becomes
  important
- Add a Lezer/CodeMirror adapter if client-side incremental Markdown parsing becomes
  important
- Add a CRDT anchor option on annotation targets if collaborative editing becomes
  important
- Add a Pandoc bridge for cross-format conversion
- Add PDF.js/Docling import alignment for visual documents

## Risks

- **Parser drift:** if `TextDoc`, Marko, Flowmark, and any client parser disagree, source
  spans and UI selections diverge.
- **Offset-unit ambiguity:** unspecified byte-vs-UTF-16-vs-code-point coordinates
  silently break cross-language clients. Pin canonical `source_span` to Unicode code
  points and require named derived coordinates for bytes or UTF-16.
- **Over-modeling:** a universal graph can become too abstract. Keep the first schema
  small and expand around real use cases.
- **Annotation reattachment:** no selector is sufficient alone. Store multiple selectors
  from the start; allow an opaque anchor for the CRDT path.
- **Mutation semantics:** mutable parsed nodes create ambiguity. Prefer immutable parsed
  snapshots plus explicit operations (red-green identity).
- **Dependency creep:** avoid adding new parser/editor dependencies until a concrete phase
  requires them. Follow `SUPPLY-CHAIN-SECURITY.md` before adding or upgrading any
  dependency.

## Recommendations

1. Keep `TextDoc` as the canonical Python linear analysis layer.
2. Extend `TextDoc` with parser-backed structural overlays in the near term; define
   `DocGraph` as the language-neutral serialized graph projection. Do not add a
   parallel `MarkdownDoc` runtime API unless a concrete boundary justifies it.
3. Specify the model as a **language-neutral contract** (JSON Schema + prose), with Python
   (and later TypeScript) as implementations; pin `source_span` to Unicode code points
   and expose byte/UTF-16 conversions explicitly.
4. Adopt **stand-off layering** (UIMA/W3C) as the conceptual core: source + stable node
   table + typed span layers; parsed structure and AI/human annotations are all layers.
5. Treat **zoom and views as one requirement:** validate the model against stable ids +
   random access + overlapping layers.
6. Use **Marko** first (aligned with Flowmark and the Python stack); hold **djot** as the
   fallback parser if Marko span attachment is too costly.
7. Borrow **mdast/unist** JSON conventions, **ProseMirror** transaction/position-map ideas
   for operations, **block-JSON** ergonomics for the client projection, and **W3C Web
   Annotation** selectors for targets.
8. Adopt the **red-green pattern** (immutable nodes + computed positions, trivia
   first-class) for the eventual structural tree; reserve **CRDT** ids for the edit edge.
9. Treat browser DOM, PDF.js, Docling, and Unstructured as view/import/layout layers.
10. Make normalized Markdown rewriting the first writeback target; defer perfect
    source-preserving edits.
11. Design public JSON around stable node records, not parser-internal AST objects.
12. Add source-map-style provenance for normalized/generated output.
13. Validate every manipulation by reparsing and comparing source spans, node structure,
    provenance mappings, and token diffs.
14. Preserve Chopdiff's differentiator: source canonical, exact source references, and
    progressive movement toward exact span slicing / verbatim block reassembly.

## Next Steps

- [ ] Use `DocGraph` for the serialized graph/schema projection; keep `TextDoc`
      as the near-term Python implementation surface unless a later boundary requires a
      separate runtime object.
- [ ] Add exact span accessors and offset-lookup APIs to `TextDoc`
      (`block_at_offset`/`sentence_at_offset`).
- [ ] Prototype Marko span attachment for full-document Markdown blocks; evaluate djot
      sourcepos as a fallback on the block-type corpus.
- [ ] Define a minimal language-neutral JSON Schema for source, nodes, views,
      annotations, provenance, and layout, with the offset unit pinned to Unicode code
      points; validate round-trip from `TextDoc`.
- [ ] Add section and link indexes on top of parser-backed blocks.
- [ ] Define the model→views projection contract and confirm O(n) derivation per view.
- [ ] Decide the annotation target shape: node id + source span + text-quote (+ optional
      structural path; + optional opaque anchor for future CRDT). Make `source_span` the
      persisted canonical (drop transient `node_id` on save); specify model→source (total)
      and source→model (re-resolution) rules. See
      `plan-2026-05-29-unified-document-model.md` (E8/D5).
- [ ] Build one small UI fixture that renders HTML with `data-node-id` and a zoomable
      section/block/link outline.
- [ ] Define operation records for move-section and replace-block transforms.
- [ ] Define generated↔original provenance records for normalized Markdown output.

## Methodology

Local review of `src/chopdiff/docs/text_doc.py`, `src/chopdiff/divs/text_node.py`, the
active block-aware plan, the active robustness plan, the archived block-segmentation
plan, and tbd issue notes. External review prioritized official documentation and primary
project references for Marko, mdast/unist, CommonMark/cmark, djot, Pandoc, DOM APIs,
ProseMirror/Tiptap, Slate/Lexical/Quill, Editor.js/BlockNote/Notion,
Tree-sitter/Lezer, Roslyn/rowan/libSyntax, Yjs/Automerge/Loro, W3C Web Annotation,
UIMA CAS/brat/GATE, PDF.js, Docling/Unstructured, DocBook/JATS/TEI, LSP coordinate
encodings, and ECMA-426 source maps. PyPI was checked on 2026-05-29 for current
Flowmark and Marko release status; Flowmark v0.7.1 was then adopted through the
repository's documented maintainer-approved exception path. No new benchmarks were run;
claims about specific tools reflect their documented designs.

## References

Local:

- [TextDoc](../../../src/chopdiff/docs/text_doc.py)
- [TextNode](../../../src/chopdiff/divs/text_node.py)
- [Block-aware doc plan](../specs/archive/plan-2026-05-26-block-aware-doc.md)
- [Markdown block segmentation plan (archived)](../specs/archive/plan-2026-05-26-markdown-block-segmentation.md)
- [Supply-chain security](../../../SUPPLY-CHAIN-SECURITY.md)

External, Markdown and cross-format ASTs:

- [Marko API Reference](https://marko-py.readthedocs.io/en/latest/api.html)
- [Marko Built-in Extensions](https://marko-py.readthedocs.io/en/latest/extensions.html)
- [Marko on PyPI](https://pypi.org/project/marko/)
- [Flowmark on PyPI](https://pypi.org/project/flowmark/)
- [mdast](https://github.com/syntax-tree/mdast)
- [unist](https://github.com/syntax-tree/unist)
- [commonmark.js](https://github.com/commonmark/commonmark.js)
- [cmark-gfm](https://github.com/github/cmark-gfm)
- [djot syntax and AST](https://djot.net/)
- [@djot/djot package API](https://www.npmjs.com/package/@djot/djot)
- [Pandoc filters](https://pandoc.org/filters.html)
- [Pandoc Lua filters](https://pandoc.org/lua-filters.html)

External, DOM and editors:

- [DOMParser](https://developer.mozilla.org/en-US/docs/Web/API/DOMParser/parseFromString)
- [Document Object Model](https://developer.mozilla.org/docs/Web/API/Document_Object_Model)
- [Language Server Protocol specification](https://microsoft.github.io/language-server-protocol/specifications/lsp/3.18/specification/)
- [ECMA-426 Source Map Format](https://tc39.es/ecma426/)
- [ProseMirror guide](https://prosemirror.net/docs/guide/)
- [ProseMirror reference](https://prosemirror.net/docs/ref/)
- [Tiptap core concepts](https://tiptap.dev/docs/editor/core-concepts/introduction)
- [Slate serializing](https://docs.slatejs.org/concepts/10-serializing)
- [Quill Delta](https://v2.quilljs.com/docs/delta)
- [Editor.js output data](https://editorjs.io/base-concepts/#editor-js-output-data)
- [BlockNote document structure](https://www.blocknotejs.org/docs/foundations/document-structure)

External, incremental parsers, lossless trees, and CRDTs:

- [Tree-sitter Python node API](https://tree-sitter.github.io/py-tree-sitter/classes/tree_sitter.Node.html)
- [Lezer reference](https://lezer.codemirror.net/docs/ref/)
- [Roslyn syntax trees (red-green), Eric Lippert](https://ericlippert.com/2012/06/08/red-green-trees/)
- [Roslyn syntax tree docs](https://learn.microsoft.com/en-us/dotnet/csharp/roslyn-sdk/work-with-syntax)
- [rowan (rust-analyzer syntax trees)](https://github.com/rust-analyzer/rowan)
- [SwiftSyntax](https://github.com/swiftlang/swift-syntax)
- [Yjs](https://docs.yjs.dev/)
- [Automerge](https://automerge.org/docs/documents/)
- [Loro](https://loro.dev/docs)

External, annotation, layout, and semantic XML:

- [W3C Web Annotation Data Model](https://www.w3.org/TR/annotation-model/)
- [UIMA CAS reference](https://uima.apache.org/d/uimaj-current/references.html)
- [brat standoff format](https://brat.nlplab.org/standoff.html)
- [GATE annotation model](https://gate.ac.uk/sale/tao/splitch5.html)
- [PDF.js PDFPageProxy API](https://mozilla.github.io/pdf.js/api/draft/module-pdfjsLib-PDFPageProxy.html)
- [Docling documentation](https://docling-project.github.io/docling/)
- [Unstructured document elements](https://docs.unstructured.io/platform-api/partition-api/document-elements)
- [JATS](https://jats.nlm.nih.gov/)
- [DocBook schemas](https://docbook.org/schemas/docbook/)
- [TEI Guidelines](https://guidelines.tei-c.de/en/html/index.html)
