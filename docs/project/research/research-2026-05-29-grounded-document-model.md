# Research: Source-Grounded Structural Document Model

**Date:** 2026-05-29 (last updated 2026-05-29)

**Author:** Codex

**Status:** Complete (initial survey)

## Overview

This research surveys ways to represent a document as a comprehensive, JSON-serializable
structure that remains grounded in the original source while supporting visual analysis,
AI analysis, human annotation, structural navigation, document manipulation, and
normalized rewriting.

The motivating direction is to build on Chopdiff and Flowmark rather than replacing
them:

- `TextDoc` is already a useful linear model for source-referenced text analysis,
  sentence/paragraph units, tokenization, diffs, and transform stitching.
- Flowmark and Marko already provide parser-backed Markdown normalization and structural
  interpretation.
- `TextNode` already provides a grounded tree for explicit HTML `div` structures.

The main conclusion is that the most durable architecture is not a single universal
tree. It is a source-grounded document graph with several derived views: Markdown block
structure, section hierarchy, inline/link index, sentence/token `TextDoc` view, optional
rendered-layout geometry, and external annotations that target nodes or spans.

## Questions to Answer

1. What existing document models, parsers, editor frameworks, and annotation standards
   should influence Chopdiff's next document model?
2. Which approaches preserve source grounding well enough for precise analysis and
   manipulation?
3. Which approaches provide clean JSON serialization for client-side UI, annotations,
   and cross-platform processing?
4. Which approaches help with normalized Markdown rewriting versus live rich-text
   editing?
5. How should this fit with the current `TextDoc`, block-aware document, and
   parser-backed Markdown segmentation plans?

## Scope

Included:

- Markdown and Markdown-derived structures.
- HTML DOM and Markdown-to-HTML DOM workflows.
- Editor document models such as ProseMirror, Tiptap, Slate, Lexical, and Quill Delta.
- Parser-level systems such as Marko, mdast/unist, CommonMark, Tree-sitter, and Lezer.
- Cross-format document ASTs such as Pandoc.
- Annotation targeting models, especially W3C Web Annotation.
- Layout-aware document extraction tools for visual/page geometry overlays.

Excluded for now:

- Selecting a new dependency or adding implementation code.
- Full PDF/OCR benchmark research.
- Collaborative editing protocol design beyond lessons from existing editor models.
- Perfect source-preserving Markdown surgery. Normalized rewriting is the better first
  target.

## Existing Project Context

### `TextDoc`

`TextDoc` currently parses source into blank-line-separated `Paragraph`s and
sentence-level units. It preserves source text references through fixed offsets and
supports reassembly, replacement, subdocuments, word token mappings, token diffs, and
windowed transformations.

Relevant strengths:

- Fast, simple linear analysis.
- Source-referenced paragraph and sentence offsets.
- Existing `TextUnit` size machinery.
- Word-token diffs and mappings useful for transform validation and stitching.
- Coarse Markdown block classification through Marko/Flowmark.

Relevant limitations:

- `Offsets` are start-only today.
- Paragraphs are blank-line blocks, not parser-backed Markdown blocks.
- Tight lists, loose lists, nested lists, and fenced code with blank lines cannot be
  modeled precisely by blank-line segmentation alone.
- Sentence spans can be best-effort when the splitter normalizes whitespace.
- Links, inline code spans, and inline HTML are not yet first-class source-grounded
  nodes.

### `TextNode`

`TextNode` already proves a useful pattern: a tree view can be grounded in the original
source by storing offsets and content boundaries, while still offering rollups, child
selection, and reassembly. It is intentionally limited to `div`-oriented structure, but
the shape is directly relevant to a broader document model.

### Active Specs

The current project specs already point in the right direction:

- `plan-2026-05-26-block-aware-doc.md` proposes exact spans, sections, structural
  blocks, links, and link-aware sentences.
- `plan-2026-05-26-markdown-block-segmentation.md` proposes a parser-backed
  `MarkdownDoc`/`MarkdownBlock` layer with source spans, block categories, section
  rollups, and integration with `TextDoc`.

This research reinforces those specs but recommends making the "derived overlay"
architecture explicit: keep source text and `TextDoc` as core linear grounding, and add
specialized views rather than forcing every use case into one mutable tree.

## Findings

### Grounding Patterns

The strongest systems keep several identifiers for the same target:

- A structural node id.
- A source span in original input coordinates.
- A text quote selector with prefix/suffix for robustness after edits.
- Optional rendered layout coordinates for visual UI.
- Optional path selectors for DOM/XML/editor models.

This matters because any single targeting scheme fails under some transformation:

- Source offsets are precise but brittle after edits.
- Quoted text can survive small edits but may be ambiguous.
- Node ids are stable only within one parse or one operation history.
- DOM paths are useful in browser UIs but can change after rendering or normalization.
- Visual boxes are essential for layout inspection but are not semantic source truth.

The W3C Web Annotation model is the best reference here. Its selectors include text
position, text quote, fragment, CSS, XPath, data position, SVG, and state concepts. The
important lesson is not to adopt JSON-LD wholesale immediately, but to store multiple
selectors per annotation target.

### Markdown ASTs

#### Marko

Marko is the best near-term parser fit because it is already in the dependency graph and
Flowmark uses it. It provides a Python AST and GFM support through extensions. The main
gap is source spans: Marko elements do not expose exact spans by default, but the active
spec notes that the parser's source cursor can likely be subclassed or wrapped to attach
spans.

Recommendation: use Marko first for parser-backed `MarkdownDoc` because it matches the
current Python stack and avoids a new parser dependency.

#### mdast and unist

The unified ecosystem's `mdast` and `unist` are the strongest JSON-first Markdown AST
reference. `unist` standardizes `type`, `children`, `value`, and positional information.
`mdast` defines Markdown-specific nodes such as heading, paragraph, list, list item,
link, image, code, table, and footnotes.

The tradeoff is that the ecosystem is JavaScript-first. It is valuable as a schema and
interoperability reference, but adopting it directly would duplicate the current
Python/Marko path.

Recommendation: borrow the shape, not necessarily the implementation.

#### CommonMark and cmark-gfm

CommonMark implementations are strong references for spec compliance and source
positions. `commonmark.js` exposes node `sourcepos`, and cmark/cmark-gfm can render
source positions in HTML/XML output. This is useful prior art for the exact-span
strategy.

The tradeoff is integration cost. A cmark-gfm dependency would improve spec alignment
but adds a second Markdown parser path and complicates Flowmark alignment.

Recommendation: treat CommonMark/cmark as validation and fallback research, not the
first implementation path.

### Cross-Format ASTs

#### Pandoc AST

Pandoc is the strongest cross-format AST and transformation model. It parses many input
formats into an intermediate AST, exposes JSON filters, and writes many output formats.
It is excellent for normalized conversion and broad document transformations.

The gap is source grounding. Pandoc's AST is designed as a normalized intermediate
representation, not as an exact source map back to Markdown byte offsets. It is also an
external executable/runtime concern.

Recommendation: use Pandoc as an optional export/import bridge or validation tool, not
as the canonical source-grounded model.

### DOM-Based Approaches

#### Browser DOM

The browser DOM is excellent for interactive UI, link discovery, rendered selection,
accessibility, and inspection. `DOMParser` can parse HTML into a document tree, and DOM
Range APIs support UI selections.

The gap is that DOM is post-parse and post-repair. It does not naturally preserve the
original Markdown source spans, Markdown constructs, or normalization choices.

Recommendation: use DOM as a client-side rendering and interaction view, with
`data-node-id` or `data-sourcepos` attributes emitted from the source-grounded model.

#### Markdown to HTML DOM

Rendering Markdown to HTML and then parsing/manipulating the DOM is convenient and works
well for many UI tasks. It can support a zoomable visual overview if generated elements
carry source or node identifiers.

The gap is semantic mismatch. Markdown list items, reference links, footnotes, tables,
raw HTML, and normalized whitespace may not map cleanly back to source.

Recommendation: generated HTML should be a view over the source-grounded model, not the
source of truth.

### Editor Document Models

#### ProseMirror and Tiptap

ProseMirror is the most relevant client-side editor model. It uses a schema-constrained
tree, JSON serialization, immutable document states, transactions, and position maps.
Tiptap builds a friendlier editor framework on top and recommends ProseMirror JSON for
storage.

This is highly relevant to document manipulation and UI editing. Its transaction model
is the strongest reference for move-section, insert-node, replace-range, and normalize
operations.

The gap is Markdown source grounding. Once content is in ProseMirror JSON, it becomes an
editor document model rather than the original Markdown source.

Recommendation: learn from ProseMirror's schema, transactions, and position maps, and
consider a client adapter. Do not make ProseMirror JSON the canonical model for
Chopdiff unless the product becomes primarily a rich-text editor.

#### Slate and Lexical

Slate and Lexical are flexible JSON editor models. They are useful references for
custom editors, normalization, and plugin-driven behavior.

The gap is that they are less directly aligned with Markdown source rewriting and
semantic document analytics.

Recommendation: use them as secondary references only.

#### Quill Delta

Quill Delta is a clean JSON format that can represent both documents and changes. It is
excellent for operational-transform-style rich text.

The gap is structural expressiveness. It is less natural for section trees, nested block
semantics, Markdown-specific source spans, and source-grounded annotations.

Recommendation: borrow the "document plus operations" idea, but not the linear Delta
format as the main model.

### Incremental Parser Systems

#### Tree-sitter

Tree-sitter is excellent at concrete syntax trees with byte ranges and incremental
parsing. Its nodes expose byte ranges and descendant lookup by byte or point range. This
is a strong fit for editor-grade source mapping.

The gap is semantic modeling. Tree-sitter produces a syntax tree, not a ready document
analysis model with sections, prose semantics, links, annotations, and normalized
writing.

Recommendation: useful later if client-side incremental Markdown parsing becomes a
priority. Not needed for the first Python-backed model.

#### Lezer and CodeMirror

Lezer is CodeMirror's parser system and is strongly relevant to a browser-based
Markdown editor. It provides compact syntax trees with from/to positions, incremental
parsing, and Markdown support.

The gap is similar to Tree-sitter: it is a syntax/editor layer, not the full semantic
document overview.

Recommendation: use Lezer/CodeMirror as a possible client-side editor and live syntax
view, fed by or synchronized with the canonical source-grounded JSON model.

### Layout-Aware Document Extraction

#### PDF.js

PDF.js exposes page text content, viewport transforms, and page structure trees when
available. It is highly relevant for visual overlays, page coordinates, text
selection, and PDF inspection.

The gap is that PDF text extraction normalizes and reorders text in ways that do not
map cleanly to Markdown source. PDF is a visual/page format, not a semantic authoring
source.

Recommendation: treat PDF.js geometry as a layout overlay when the source is a PDF or
rendered PDF, not as the canonical document model for Markdown.

#### Docling and Unstructured

Docling and Unstructured represent the modern "document AI extraction" direction:
parse PDFs, DOCX, PPTX, images, and other formats into structured elements with
coordinates, tables, reading order, and JSON export.

These are highly relevant for visual analysis and imported documents. They are less
relevant for exact Markdown rewrite when Markdown is the original source.

Recommendation: support an optional `layout` or `imported_elements` layer that can
attach page and bounding-box information to source-grounded nodes where alignment is
possible.

### Semantic XML Models

DocBook, JATS, and TEI show what mature semantic document modeling looks like. They have
rich element vocabularies, validation, and long-term publishing workflows.

The tradeoff is complexity. They are too heavyweight for a Markdown-first, AI-assisted
editing and analysis workflow.

Recommendation: borrow the discipline of explicit semantic roles and schemas, but keep
the Chopdiff model lighter and JSON-native.

## Key Insights

### The Canonical Artifact Should Remain Source Text

For Chopdiff and Flowmark, Markdown source should remain canonical. The parsed document
overview should be derived, cached, serialized, annotated, and transformed, but edits
should ultimately produce new source text and then reparse.

This avoids the hardest class of bugs: a rich document model drifting away from the
actual Markdown file.

### A Graph Is More Honest Than One Tree

A single tree cannot naturally express all useful views:

- Markdown blocks form one hierarchy.
- Sections form a heading-derived hierarchy that crosses ordinary block containment.
- Sentences and tokens form a linear sequence.
- Links are inline ranges that may cross child text nodes in some ASTs.
- Visual layout may group text by page, column, line, or bounding box.
- Human and AI annotations are external claims about nodes or ranges.

The practical model is a node graph with derived indexes and named views.

### JSON Should Be Stable And Boring

The serialization should avoid Python-specific objects and parser-internal class names.
Use explicit discriminated records:

```json
{
  "id": "n_0123",
  "kind": "heading",
  "source_span": {"start": 120, "end": 146},
  "analysis_span": {"start": 122, "end": 146},
  "parent": "n_root",
  "children": ["n_0124"],
  "attrs": {"level": 2, "text": "Background"}
}
```

The parser-specific source can be recorded in metadata, but should not leak into the
stable public schema.

### Annotations Should Be Separate From The Parse

AI summaries, human comments, rewrite suggestions, visual marks, and review notes should
not be embedded directly into parsed nodes. They should be separate records targeting
nodes and spans with multiple selectors.

This makes annotations portable across reparses and lets the same document model support
many independent annotation layers.

### Visual Analysis Is An Overlay

Zoomable UI needs visual geometry, but visual layout is not the same as document
structure. For Markdown, source structure should drive the model. Browser/PDF/layout
geometry should attach to nodes as a separate overlay:

```json
{
  "node_id": "n_0123",
  "surface": "html",
  "page": null,
  "bbox": [24, 160, 740, 192]
}
```

For PDFs and OCR imports, geometry may be the only reliable initial grounding. For
Markdown, geometry should remain derived.

## Comparison Matrix

| Approach | Source grounding | Structure richness | JSON portability | Edit/writeback fit | Visual UI fit | Fit for Chopdiff direction |
| --- | --- | --- | --- | --- | --- | --- |
| Current `TextDoc` | Good for paragraphs/sentences; needs end spans | Low to medium | Good if serialized explicitly | Good for text transforms | Low | Keep as core linear layer |
| `TextNode` div tree | Good for explicit div spans | Medium for HTML chunks | Good if serialized | Medium | Medium | Keep as named-structure layer |
| Marko AST | Medium now; can improve with span attachment | High for Markdown blocks/inlines | Needs wrapper schema | Good for normalized Markdown with Flowmark | Medium | Best first parser-backed path |
| mdast/unist | Strong positional model | High | Excellent | Good in JS ecosystem | Medium | Schema inspiration, not first implementation |
| CommonMark/cmark-gfm | Strong sourcepos precedent | High for CommonMark/GFM | Medium | Good renderer support | Medium | Validation/fallback reference |
| Pandoc AST | Weak to medium for original spans | Very high cross-format | Excellent | Excellent normalized conversion | Low | Optional bridge, not canonical |
| Browser DOM | Weak for Markdown source | High for rendered HTML | Medium | Poor for Markdown source edits | Excellent | UI view only |
| Markdown to HTML DOM | Medium if `data-sourcepos` emitted | Medium to high | Medium | Medium for generated HTML, weak for source | Excellent | Derived view |
| ProseMirror/Tiptap | Internal position model, weak original source grounding | High | Excellent | Excellent transactions | Excellent | Client adapter and design reference |
| Slate/Lexical | Weak source grounding | High customizability | Good | Good for editors | Excellent | Secondary editor references |
| Quill Delta | Weak source grounding | Medium | Excellent | Excellent for rich-text deltas | Good | Borrow operation ideas only |
| Tree-sitter | Excellent byte ranges | Syntax-rich, semantic-light | Medium | Good for source editors | Good | Later incremental parser option |
| Lezer/CodeMirror | Excellent editor positions | Syntax-rich, semantic-light | Medium | Good for browser editors | Excellent | Later client-side live parser |
| W3C Web Annotation | Target grounding only | Not a document parser | Excellent | Annotation-specific | Good | Best annotation selector reference |
| PDF.js | Strong page/text geometry | Medium visual structure | Medium | Poor for Markdown | Excellent | Layout overlay |
| Docling/Unstructured | Strong imported layout elements | High for extracted docs | Good | Medium for imported docs | Excellent | Optional import/layout layer |
| DocBook/JATS/TEI | Strong XML structure | Very high | Good XML, not JSON-native | Good in publishing toolchains | Low | Semantic-model inspiration only |

## Options Considered

### Option A: Extend `TextDoc` Into One Comprehensive Model

**Description:** Add spans, sections, links, parser-backed blocks, visual layout, and
annotations directly onto `TextDoc`.

**Pros:**

- Simple public story: one object.
- Maximum reuse of existing size, token, diff, and transform APIs.
- Incremental from the current code.

**Cons:**

- Risks making `TextDoc` responsible for unrelated views.
- Parser-backed block boundaries conflict with current paragraph/window assumptions.
- Visual layout and annotations do not naturally belong inside the linear text model.

**Assessment:** Useful for spans and simple convenience APIs, but too constraining as
the full architecture.

### Option B: Add A Parser-Backed `MarkdownDoc` Overlay

**Description:** Keep `TextDoc` as the linear text model and add a `MarkdownDoc` or
`DocumentOverview` object that owns source text, parser-backed nodes, sections, links,
and indexes back into `TextDoc`.

**Pros:**

- Preserves existing `TextDoc` behavior.
- Gives exact Markdown structure where blank-line paragraphs are insufficient.
- Provides a natural JSON model for UI and annotations.
- Can evolve independently without breaking diff/window code.

**Cons:**

- Requires careful mapping between parser spans and `TextDoc` spans.
- Adds a second public model that must be documented clearly.

**Assessment:** Recommended.

### Option C: Adopt mdast/unist As The Canonical JSON Schema

**Description:** Use the unified ecosystem's Markdown AST shape as the serialized model.

**Pros:**

- Mature JSON shape.
- Broad ecosystem.
- Strong positional convention.

**Cons:**

- JavaScript-first implementation path.
- Does not include Chopdiff-specific sentence, token, diff, section rollup, and
  annotation needs without extensions.
- Would duplicate the current Python/Marko stack.

**Assessment:** Good schema inspiration, but not the canonical implementation choice.

### Option D: Use Pandoc AST As The Canonical Model

**Description:** Parse Markdown to Pandoc JSON and use Pandoc filters/writers for all
structural manipulation.

**Pros:**

- Excellent cross-format model and normalized writing.
- Mature filter ecosystem.
- Handles many formats beyond Markdown.

**Cons:**

- Source grounding to original Markdown is not the design center.
- External runtime dependency.
- Less aligned with `TextDoc` spans, tokens, and diff filtering.

**Assessment:** Useful optional bridge, not canonical.

### Option E: Use ProseMirror/Tiptap JSON As The Canonical Model

**Description:** Treat the document as a rich-text editor state and serialize it as
ProseMirror/Tiptap JSON.

**Pros:**

- Excellent client-side editing, schema, transactions, and UI behavior.
- Natural for interactive manipulation.

**Cons:**

- Original Markdown source becomes secondary.
- Markdown roundtrip can be lossy or opinionated.
- Python-side document analytics would depend on an editor-specific model.

**Assessment:** Strong client adapter and design reference, but not canonical for
Markdown-source-grounded Chopdiff.

### Option F: Source-Grounded Document Graph With Multiple Views

**Description:** Store canonical source plus stable JSON nodes, spans, indexes, views,
annotations, and optional layout overlays.

**Pros:**

- Handles all major use cases without forcing incompatible structures into one tree.
- Keeps source grounding explicit.
- Allows UI, AI, annotations, transforms, and visual layout to share node ids.
- Can serialize cleanly and remain parser-agnostic at the public API boundary.

**Cons:**

- More conceptual surface than a single AST.
- Requires disciplined schema design and validation.

**Assessment:** Recommended architectural north star.

## Recommended Direction

Build a source-grounded `DocumentOverview`/`MarkdownDoc` layer with these components:

1. **Source record**
   - Original text or external reference.
   - Content hash.
   - Source format and parser metadata.

2. **Stable node table**
   - `id`, `kind`, `role`, `parent`, `children`, `source_span`, optional
     `analysis_span`, and `attrs`.
   - Parser-specific details hidden behind stable public fields.

3. **Views**
   - `blocks`: parser-backed Markdown block order.
   - `sections`: heading-derived tree and TOC.
   - `links`: inline link/image/reference index.
   - `sentences`: `TextDoc` sentence index.
   - `tokens`: word-token index when requested.
   - `divs`: explicit HTML/div structure when present.
   - `layout`: optional rendered or imported geometry.

4. **Annotations**
   - Stored separately from nodes.
   - Target nodes or ranges with multiple selectors:
     - node id;
     - source span;
     - text quote with prefix/suffix;
     - optional DOM path;
     - optional visual bbox.

5. **Operations**
   - Represent manipulations as high-level operations:
     - move section;
     - replace block;
     - insert after node;
     - rewrite span;
     - normalize document.
   - Apply operations to source or to a normalized Markdown AST, emit new Markdown,
     then reparse.

6. **Normalized output**
   - Flowmark remains the likely Markdown normalizer.
   - Pandoc can be an optional cross-format bridge.

## Proposed JSON Sketch

```json
{
  "schema": "chopdiff.document_overview.v1",
  "source": {
    "format": "markdown",
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
        "text_quote": {
          "exact": "Overview",
          "prefix": "# ",
          "suffix": "\n\n"
        }
      },
      "body": {"text": "Top-level section heading."}
    }
  ],
  "layout": []
}
```

## Use Case Mapping

### Dynamic Zoomable UI

Use:

- Section tree for top-level navigation.
- Block list for medium zoom.
- Sentence/link/token views for detail zoom.
- Optional layout overlay for rendered positioning.
- DOM rendering with `data-node-id` attributes for browser interaction.

### AI And Human Annotations

Use:

- External annotation records.
- W3C-inspired target selectors.
- Node ids for fast lookup.
- Source spans and text quotes for reattachment after edits.
- Annotation layers for summaries, claims, TODOs, rewrite suggestions, citations,
  visual comments, and human review.

### Link Identification And Reference

Use:

- Parser-backed inline nodes from Marko.
- Link records with text, URL, title, source span, containing block, containing
  sentence, and containing section.
- Separate treatment of inline links, reference links, autolinks, images, and raw HTML
  anchors.

### Section Moves And Semantic Reorganization

Use:

- Section view for selecting move targets.
- Source spans for exact extraction when safe.
- Parser-backed normalized rewrite when exact extraction is unsafe.
- Operation records to describe the move before emitting new Markdown.
- Reparse and diff to validate the output.

### Normalized Markdown Rewriting

Use:

- Parser-backed Markdown blocks for structure.
- Flowmark for normalization.
- `TextDoc` token diffs for validating how much changed.
- Optional Pandoc bridge if output format is not Markdown.

### Visual Document Analysis

Use:

- Browser-rendered HTML layout for Markdown.
- PDF.js layout for PDF views.
- Docling/Unstructured-style imported element coordinates for non-Markdown sources.
- Layout overlay keyed by node ids when alignment is possible.

## Implementation Implications

### Near-Term Additions

- Add computed spans to `Paragraph` and `Sentence`.
- Add `block_at_offset` and `sentence_at_offset`.
- Add `source_text` retention or a clear source accessor strategy if arbitrary slicing
  becomes necessary.
- Add parser-backed `MarkdownDoc` with source spans.
- Add heading-derived sections and TOC.
- Add link extraction with spans.

### Medium-Term Additions

- Add JSON schema or Pydantic/dataclass serialization for `DocumentOverview`.
- Add annotation target records.
- Add operation records for structural transforms.
- Add layout overlay type.
- Add browser rendering helpers that emit `data-node-id`.

### Later Additions

- Add ProseMirror/Tiptap adapter if live rich-text editing becomes important.
- Add Lezer/CodeMirror adapter if client-side incremental Markdown parsing becomes
  important.
- Add Pandoc bridge for cross-format conversion.
- Add PDF.js/Docling import alignment for visual documents.

## Risks

- **Parser drift:** If `TextDoc`, Marko, Flowmark, and any client parser disagree,
  source spans and UI selections can diverge.
- **Over-modeling:** A universal document graph can become too abstract. Keep the first
  schema small and expand only around real use cases.
- **Annotation reattachment:** No selector is sufficient alone. Store multiple selectors
  from the start.
- **Mutation semantics:** Mutable parsed nodes will create ambiguity. Prefer immutable
  parsed snapshots plus explicit operations.
- **Dependency creep:** Avoid adding new parser/editor dependencies until a concrete
  phase requires them. Follow `SUPPLY-CHAIN-SECURITY.md` before adding or upgrading any
  dependency.

## Recommendations

1. Keep `TextDoc` as the canonical linear analysis layer.
2. Add a separate parser-backed `MarkdownDoc`/`DocumentOverview` overlay rather than
   forcing all structure into `TextDoc`.
3. Use Marko first because it is already aligned with Flowmark and the current Python
   stack.
4. Borrow `mdast`/`unist` conventions for JSON shape and positional fields.
5. Borrow ProseMirror's transaction and position-map ideas for structural operations.
6. Borrow W3C Web Annotation selectors for robust annotation targets.
7. Treat browser DOM, PDF.js, Docling, and Unstructured as view/import/layout layers.
8. Make normalized Markdown rewriting the first writeback target; defer perfect
   source-preserving edits.
9. Design public JSON around stable node records, not parser-internal AST objects.
10. Validate every manipulation by reparsing and comparing source spans, node structure,
    and token diffs.

## Next Steps

- [ ] Decide naming: `MarkdownDoc`, `DocumentOverview`, or another name.
- [ ] Add exact span accessors and offset lookup APIs to `TextDoc`.
- [ ] Prototype Marko span attachment for full-document Markdown blocks.
- [ ] Define a minimal JSON schema for source, nodes, views, annotations, and layout.
- [ ] Add section and link indexes on top of parser-backed blocks.
- [ ] Build one small UI fixture that renders HTML with `data-node-id` attributes and a
      zoomable section/block/link outline.
- [ ] Define operation records for move-section and replace-block transforms.

## Methodology

The research combined local code/spec review with external source review. Local review
focused on:

- `src/chopdiff/docs/text_doc.py`
- `src/chopdiff/divs/text_node.py`
- `docs/project/specs/active/plan-2026-05-26-block-aware-doc.md`
- `docs/project/specs/active/plan-2026-05-26-markdown-block-segmentation.md`
- `docs/review/senior-engineering-review.md`

External review prioritized official documentation and primary project references for:

- Marko
- mdast/unist
- CommonMark/cmark
- Pandoc
- DOM APIs
- ProseMirror/Tiptap
- Slate/Lexical/Quill
- Tree-sitter/Lezer
- W3C Web Annotation
- PDF.js
- Docling/Unstructured
- DocBook/JATS/TEI

## References

Local:

- [TextDoc](../../../src/chopdiff/docs/text_doc.py)
- [TextNode](../../../src/chopdiff/divs/text_node.py)
- [Exact spans, sections, and structural blocks for TextDoc](../specs/active/plan-2026-05-26-block-aware-doc.md)
- [Parser-backed Markdown block segmentation](../specs/active/plan-2026-05-26-markdown-block-segmentation.md)
- [Senior engineering review](../../review/senior-engineering-review.md)
- [Supply-chain security](../../../SUPPLY-CHAIN-SECURITY.md)

External:

- [Marko API Reference](https://marko-py.readthedocs.io/en/latest/api.html)
- [Marko Built-in Extensions](https://marko-py.readthedocs.io/en/latest/extensions.html)
- [mdast](https://github.com/syntax-tree/mdast)
- [unist](https://github.com/syntax-tree/unist)
- [commonmark.js](https://github.com/commonmark/commonmark.js)
- [cmark-gfm](https://github.com/github/cmark-gfm)
- [Pandoc filters](https://pandoc.org/filters.html)
- [Pandoc Lua filters](https://pandoc.org/lua-filters.html)
- [DOMParser](https://developer.mozilla.org/en-US/docs/Web/API/DOMParser/parseFromString)
- [Document Object Model](https://developer.mozilla.org/docs/Web/API/Document_Object_Model)
- [ProseMirror guide](https://prosemirror.net/docs/guide/)
- [ProseMirror reference](https://prosemirror.net/docs/ref/)
- [Tiptap core concepts](https://tiptap.dev/docs/editor/core-concepts/introduction)
- [Slate serializing](https://docs.slatejs.org/concepts/10-serializing)
- [Slate editor API](https://docs.slatejs.org/api/nodes/editor)
- [Quill Delta](https://v2.quilljs.com/docs/delta)
- [Tree-sitter Python node API](https://tree-sitter.github.io/py-tree-sitter/classes/tree_sitter.Node.html)
- [Tree-sitter Python tree API](https://tree-sitter.github.io/py-tree-sitter/classes/tree_sitter.Tree.html)
- [Lezer reference](https://lezer.codemirror.net/docs/ref/)
- [Lezer guide](https://lezer.codemirror.net/docs/guide/)
- [W3C Web Annotation Data Model](https://www.w3.org/TR/annotation-model/)
- [PDF.js PDFPageProxy API](https://mozilla.github.io/pdf.js/api/draft/module-pdfjsLib-PDFPageProxy.html)
- [Docling documentation](https://docling-project.github.io/docling/)
- [Docling document reference](https://docling-project.github.io/docling/reference/docling_document/)
- [Unstructured document elements](https://docs.unstructured.io/platform-api/partition-api/document-elements)
- [JATS](https://jats.nlm.nih.gov/)
- [DocBook schemas](https://docbook.org/schemas/docbook/)
- [TEI Guidelines](https://guidelines.tei-c.de/en/html/index.html)
