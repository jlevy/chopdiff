# Research: A Cross-Language Document Data Model — Layering, Prior Art, and Annotation

**Date:** 2026-05-29 (last updated 2026-05-29)

**Author:** Claude

**Status:** Complete (initial survey)

## Overview

This brief complements
[research-2026-05-29-grounded-document-model.md](research-2026-05-29-grounded-document-model.md),
which surveyed source-grounded structural document models and recommended a
source-grounded graph with derived views (Option F). This doc does two things that
survey did not:

1. Sharpens the central architectural claim: the deliverable is a **data model**, which
   is a separate concern from its **serialization format** (JSON) and its
   **implementation** (Python today, possibly TypeScript/Rust/WASM later). Several of
   the motivating use cases that looked distinct — "zoomable UI" and "different
   structural views" — are not separate features. They are the *same* requirement: one
   clean, multi-use model that can be projected into many views cheaply.

2. Adds the prior art the first survey missed, which turns out to be the strongest
   reference material for the hardest requirements: stand-off annotation (NLP and web),
   lossless / full-fidelity syntax trees (the red-green tree), CRDT rich-text models,
   block-JSON editors, and djot.

The motivating direction is unchanged: build on Chopdiff (`TextDoc`, `TextNode`,
wordtok diffs, windowed transforms) and Flowmark/Marko, with Markdown source remaining
canonical.

## Questions to Answer

1. Is "data model" a distinct deliverable from "JSON serialization" and "Python
   implementation," and what falls out of treating them separately?
2. Are "visual/zoomable UI" and "multiple structural views" really separate
   requirements, or one?
3. What prior art did the first survey miss, and which requirements does it best serve?
4. What is the cleanest conceptual core for annotations that survive edits and reparses?
5. How should the model be specified so it is genuinely cross-language?

## Scope

Included:

- The model/serialization/implementation separation and what it implies for API design.
- Prior art not covered in the first survey: stand-off annotation (UIMA CAS, GATE,
  brat, W3C Web Annotation), lossless syntax trees (Roslyn red-green, rowan, libSyntax),
  CRDT rich-text (Yjs, Automerge, Loro), block-JSON editors (Editor.js, BlockNote,
  Notion), and djot.
- How these refine the recommended Option F architecture.

Excluded:

- Re-deriving the first survey's matrix (Marko, mdast, Pandoc, ProseMirror, DOM,
  Tree-sitter/Lezer, PDF.js, Docling). See that doc.
- Choosing dependencies or writing implementation code.
- Collaborative-editing protocol design beyond the lessons drawn here.

## Findings

### The deliverable is a data model, not a format and not a class

A document "model" conflates three layers that should be designed and versioned
independently:

- **Conceptual model** — the entities and relationships: a source, a stable node table,
  spans, typed layers (sections, blocks, links, sentences, divs), and external
  annotations. This is the contract.
- **Serialization** — how the model is written down for transport and storage. JSON is
  the target, but JSON is a projection, not the model. The model should also be
  expressible as Protobuf/FlatBuffers, or even an in-memory columnar form, without
  changing the contract.
- **Implementation** — Python dataclasses today; possibly a TypeScript mirror for the
  client, or a Rust/WASM core later. None of these is the model either.

Why this matters concretely:

- The public JSON schema must be **boring and parser-agnostic** (the first survey's
  insight): no Marko class names, no Python type tags, no field that only makes sense in
  one runtime. A field like `marko_node_type` belongs in optional `metadata`, never in
  the stable record.
- The model should be specified in a language-neutral artifact — a JSON Schema plus a
  prose spec, or a single schema IDL — so a TypeScript client and a Python core are two
  implementations of one contract, not two models that drift. This is the same
  discipline LSP uses: the protocol is the spec; VS Code and pyright are
  implementations.
- IDs and spans are the cross-language lingua franca. As long as every node has a stable
  `id` and a `source_span` in well-defined units (UTF-8 byte offsets vs. UTF-16 code
  units vs. Unicode scalar values — **this must be pinned in the spec**, because
  JS strings are UTF-16 and Python strings are scalar-value indexed, and PDF/OCR tools
  count differently), any language can cooperate on the same document.

Recommendation: treat the JSON Schema (or equivalent IDL) as the source of truth and
generate or hand-mirror language bindings from it. Pin the offset unit explicitly.

### "Zoomable UI" and "multiple views" are one requirement, not two

The first survey listed visual/zoom UI (F) and multi-view (G) as separate axes. They
collapse into one: **a single model that supports cheap projection to many views at
many granularities.** "Zoom" is just choosing which view and which level to render:

- Zoomed out: the section tree / TOC (a view).
- Mid zoom: the block list, or a section's blocks (a view).
- Zoomed in: sentences, links, tokens, inline structure (views).
- Visual overlay: geometry attached by node id (a view).

So the real, unified requirement is: *one stable node set, addressable by id, from which
section tree, block tree, linear token stream, link index, and layout overlay are all
O(n) derivable projections that share node ids.* If the model has that property, both
"zoomable rendering" and "different structural views" are free. If it lacks it (e.g. a
single mutable tree that privileges one hierarchy), both are expensive.

This reframing also clarifies what "efficiently designed for all these use cases" means:
the model needs (a) stable ids, (b) random access by id and by offset, and (c) the
ability to hold *overlapping, non-nesting* layers (sections cross block containment;
links are inline ranges; annotations are arbitrary). A pure tree cannot do (c); a
node table + typed span layers can.

### Stand-off annotation: the canonical core for layers and annotations

The strongest prior art for "annotate nodes, keep references to the original, support
many independent layers" is the stand-off markup tradition, which the first survey only
touched via W3C Web Annotation.

- **UIMA CAS** (Common Analysis Structure): an immutable text ("Sofa") plus *all*
  analysis as external typed annotations carrying offset ranges. Multiple "views" over
  one Sofa. This is almost exactly the proposed architecture, with a mature type system
  and 20 years of NLP tooling behind it.
- **GATE, brat, WebAnno**: practical stand-off annotation stores and UIs; brat's
  offset-range model and visualization are a good concrete reference for span layers.
- **W3C Web Annotation** (already in the first survey): the web-native targeting model
  with multiple selectors (TextPosition, TextQuote+prefix/suffix, CSS, XPath, Fragment).

The unifying insight these supply: **sections, links, AI summaries, and human notes are
all the same kind of thing — a typed layer of offset-grounded (or node-grounded)
annotations over an immutable source.** This is stronger than the first survey's
"views + separate annotations" split. If the model treats *every* derived structure as
a layer, then "give me an AI summary of section 3" and "give me the TOC" use one
mechanism. Parsing produces the base layers; AI and humans add more.

Recommendation: make stand-off layering the conceptual core. Borrow W3C selectors for
robustness (store node id *and* source span *and* text-quote so a layer can reattach
after a reparse or edit).

### Lossless / full-fidelity syntax trees: the core for source grounding + stable ids

The strongest prior art for "exact source grounding with stable structural identity" is
the lossless syntax tree, used by modern compilers and IDEs:

- **Roslyn red-green trees** (C#): immutable "green" nodes store kind, width, and trivia
  (whitespace/comments) but *not* absolute position; a lazily-created "red" facade
  computes absolute positions on demand. Because trivia is in the tree, the tree
  reproduces the source byte-for-byte, and node identity is independent of position.
- **rowan / rust-analyzer**, **Swift libSyntax/SwiftSyntax**: the same pattern —
  full-fidelity, lossless, position-on-demand.

Two lessons map directly onto Chopdiff:

1. `TextNode` already reaches for this with character offsets and exact reassembly. The
   red-green split is the principled version: separate immutable structural identity
   (the node and its width) from position (computed). This is the design to adopt if
   `TextDoc` is ever re-founded on a single parse (Layer 3 in the block-aware plan), and
   it answers that plan's open question about node identity surviving edits — green
   nodes have stable identity; only positions recompute.
2. "Trivia" is the compiler word for exactly Chopdiff's promise to preserve whitespace
   and reassemble verbatim. The model should name and keep trivia explicitly rather than
   reconstructing separators heuristically on reassemble.

Recommendation: adopt the red-green concept (immutable nodes + computed positions) for
the structural tree; keep trivia as first-class so verbatim round-trip is structural,
not best-effort.

### CRDT rich-text: the answer to "annotations that survive edits"

The first survey covered Quill Delta / operational transforms but not CRDTs, which have
largely superseded OT for local-first and collaborative documents:

- **Yjs, Automerge, Loro**: every character/element carries a stable unique id, so a
  range pinned to ids survives arbitrary concurrent edits with no reattachment
  heuristics. All three have clean JSON/binary export.

Relevance: the hardest annotation problem the first survey flagged — reattaching after
edits — is *solved* by id-per-element when the document is being actively edited.
Span+quote selectors are the right choice for the read-mostly, reparse-from-source path;
CRDT ids are the right choice if/when the client becomes a live collaborative editor.
These are complementary, not competing: source+spans for the canonical Markdown pipeline,
CRDT ids at the editing edge.

Recommendation: defer CRDTs to the client edge; do not make a CRDT the canonical model
(it makes Markdown secondary, same failure mode as making ProseMirror canonical). Keep
the option open by ensuring annotation targets can carry an opaque `anchor` id alongside
span/quote.

### Block-JSON editors: closest off-the-shelf to "clean JSON for the client"

The first survey covered ProseMirror/Slate/Lexical (position-map or nested-node models)
but not the block-id-first JSON shape, which is closer to the stated use cases ("annotate
nodes," "move sections"):

- **Editor.js**: dead-simple `{blocks: [{id, type, data}]}` JSON. Trivial to consume
  cross-language; weak inline/source grounding.
- **BlockNote**: a block model with stable block ids built on ProseMirror/Tiptap —
  block-level identity (good for move/annotate) with ProseMirror's editing underneath.
- **Notion block model**: every block has an id and a parent; the whole document is a
  block tree addressed by id. The canonical example of "blocks as the unit of
  addressing, annotation, and reorganization."

Relevance: these validate that a **block-id-addressed JSON** is the ergonomic shape for
client UIs that move, annotate, and reorder. The lesson for Chopdiff's serialization is
to expose block-level ids prominently, even though Chopdiff's grounding (source spans)
is stronger than any of these provide.

Recommendation: borrow the block-id-addressed JSON ergonomics for the client projection;
keep source spans (which these lack) as Chopdiff's differentiator.

### djot: a cleaner Markdown-family AST with native source positions

**djot** (by John MacFarlane, author of Pandoc and a CommonMark lead) is a Markdown
successor designed for unambiguous parsing and carries **native source positions**. If
attaching exact spans to Marko proves painful (the block-aware plan's main open risk),
djot is the cleanest Markdown-family AST-with-sourcepos to evaluate as a fallback parser.

Recommendation: keep Marko as the first path (already aligned with Flowmark); hold djot
as the fallback if Marko span attachment is too costly.

## Key Insights

- **Model ≠ format ≠ implementation.** The contract is a language-neutral schema; JSON
  and Python are projections of it. Pin the offset unit (bytes vs UTF-16 vs scalar) in
  the spec, because that one detail is where cross-language models silently diverge.
- **Zoom and views are the same requirement.** A model with stable ids + random access +
  overlapping span layers makes every view and every zoom level a cheap projection. This
  is the real meaning of "efficiently designed for all these use cases."
- **One mechanism for all structure.** Stand-off layering (UIMA/W3C) unifies parsed
  structure (sections, blocks, links) and added structure (AI summaries, human notes) as
  typed layers over immutable source. Fewer concepts, more reuse.
- **Stable identity is a solved problem, twice.** Red-green trees give stable identity
  under reparse (compiler world); CRDT ids give it under live edits (collaborative
  world). Use the first for the canonical pipeline, reserve the second for the edit edge.
- **Chopdiff's moat is grounding.** Editors (ProseMirror, Editor.js, BlockNote) and
  CRDTs all make the original source secondary. Chopdiff keeps source canonical with
  exact spans plus verbatim reassembly — the thing none of them offer. Don't trade that
  away.

## Comparison Matrix

Approaches added by this brief, scored on the requirement axes from the first survey
(A grounding, B structure, C clean JSON, D writeback, E annotation/reattach, F+G unified
model→views). ✅ strong / ◐ partial / ✘ weak.

| Approach | A Ground | B Struct | C JSON | D Write | E Annot/reattach | F+G model→views | Role for chopdiff |
| --- | --- | --- | --- | --- | --- | --- | --- |
| UIMA CAS / brat / GATE (stand-off) | ✅ offsets | typed layers | ◐/✅ | n/a | ✅✅ typed layers | ✅ many views/Sofa | **Conceptual core for layers + annotations** |
| W3C Web Annotation | targeting only | ✘ | ✅✅ | n/a | ✅✅ multi-selector | n/a | Annotation selector reference |
| Roslyn red-green / rowan / libSyntax | ✅✅ full-fidelity | ✅ | n/a | ✅ | ✅ stable ids on reparse | ◐ (one tree) | **Pattern for structural tree + trivia** |
| CRDT (Yjs / Automerge / Loro) | ✘ for MD source | ◐ | ✅ | ✅✅ | ✅✅ survives edits | ◐ | Edit-edge identity (defer) |
| Editor.js / BlockNote / Notion (block-JSON) | ✘ for MD source | ✅ blocks+ids | ✅✅ | ✅ | ✅ block ids | ◐ | Client JSON ergonomics |
| djot AST | ✅ native sourcepos | ✅ | ✅ | ✅ | ◐ | ◐ | Fallback parser to Marko |

## Options Considered

### Option A: Specify the model as a language-neutral schema (recommended)

**Description:** Author a JSON Schema (or IDL) + prose spec as the source of truth:
source record, stable node table, typed span layers, annotations. Python and any future
TypeScript/Rust bindings are implementations of it. Offset unit pinned explicitly.

**Pros:**
- Prevents Python/JS model drift; enables a true cross-language client.
- JSON stays boring and parser-agnostic by construction.
- Versionable contract independent of any runtime.

**Cons:**
- Up-front schema discipline; a second artifact to maintain alongside the dataclasses.
- Risk of over-specifying before use cases are proven.

**Assessment:** Recommended, but start minimal (source + nodes + one or two layers) and
grow around real use cases.

### Option B: Python dataclasses are the model; JSON is incidental

**Description:** Define everything as Python dataclasses and serialize ad hoc.

**Pros:**
- Fastest to build; matches current Chopdiff style.

**Cons:**
- The model becomes whatever Python emits; cross-language clients reverse-engineer it.
- Parser/runtime details leak into JSON; offset-unit ambiguity goes unaddressed.

**Assessment:** Fine for a prototype, wrong as the long-term contract given the stated
cross-language goal.

### Option C: Adopt an existing block-JSON or editor model as canonical

**Description:** Use Editor.js/BlockNote/ProseMirror/CRDT JSON as the canonical model.

**Pros:**
- Mature client tooling and JSON shapes.

**Cons:**
- All make original Markdown source secondary; lossy/opinionated roundtrip; gives up
  Chopdiff's grounding moat.

**Assessment:** Use as client-projection and ergonomics references only, not canonical.
(Consistent with the first survey's conclusion.)

## Recommendations

1. Treat the **data model as a language-neutral contract**, specified as JSON Schema +
   prose, with Python (and later TypeScript) as implementations. Pin the offset unit.
2. Adopt **stand-off layering** (UIMA/W3C) as the conceptual core: source + stable node
   table + typed span layers; parsed structure and AI/human annotations are all layers.
3. Collapse the first survey's F and G axes into one requirement — **stable ids + random
   access + overlapping layers** — and validate the model against it directly.
4. Adopt the **red-green pattern** (immutable nodes + computed positions, trivia
   first-class) for the eventual structural tree; it answers the block-aware plan's node-
   identity-under-edits question.
5. Keep **CRDT** as an edit-edge option (carry an opaque anchor id on annotation targets)
   and **djot** as a fallback parser; neither is canonical.
6. Preserve Chopdiff's differentiator: **source canonical, exact spans, verbatim
   reassembly** — the property the editor/CRDT/block models all lack.

## Next Steps

- [ ] Fold these five approaches and the model/format/impl framing into (or cross-link
      from) the first survey so there is one coherent reference.
- [ ] Draft a minimal language-neutral schema (source, node table, one section layer,
      one annotation layer) with the offset unit pinned; validate round-trip from
      `TextDoc`.
- [ ] Define the "model→views" projection contract (section tree, block list, token
      stream, link index) and confirm each is O(n) from the node table.
- [ ] Decide annotation target shape: node id + source span + text-quote (+ optional
      opaque anchor for future CRDT).
- [ ] Evaluate Marko span attachment vs djot sourcepos on the existing block-type corpus.
- [ ] Track as a bead under the block-aware document work (`chopdiff-jh56`).

## Methodology

Local review of `src/chopdiff/docs/text_doc.py`, `src/chopdiff/divs/text_node.py`, the
active block-aware plan, and the first grounded-document-model survey. External review
prioritized primary references for the prior art the first survey did not cover
(stand-off annotation, lossless syntax trees, CRDTs, block-JSON editors, djot). No new
benchmarks were run; claims about specific tools reflect their documented designs.

## References

Local:

- [Grounded document model survey](research-2026-05-29-grounded-document-model.md)
- [Block-aware doc plan](../specs/active/plan-2026-05-26-block-aware-doc.md)
- [TextDoc](../../../src/chopdiff/docs/text_doc.py)
- [TextNode](../../../src/chopdiff/divs/text_node.py)

External:

- [UIMA CAS reference](https://uima.apache.org/d/uimaj-current/references.html)
- [brat standoff format](https://brat.nlplab.org/standoff.html)
- [GATE annotation model](https://gate.ac.uk/sale/tao/splitch5.html)
- [W3C Web Annotation Data Model](https://www.w3.org/TR/annotation-model/)
- [Roslyn syntax trees (red-green) — Eric Lippert](https://ericlippert.com/2012/06/08/red-green-trees/)
- [Roslyn syntax tree docs](https://learn.microsoft.com/en-us/dotnet/csharp/roslyn-sdk/work-with-syntax)
- [rowan (rust-analyzer syntax trees)](https://github.com/rust-analyzer/rowan)
- [SwiftSyntax](https://github.com/swiftlang/swift-syntax)
- [Yjs](https://docs.yjs.dev/)
- [Automerge](https://automerge.org/docs/documents/)
- [Loro](https://loro.dev/docs)
- [Editor.js output data](https://editorjs.io/base-concepts/#editor-js-output-data)
- [BlockNote document structure](https://www.blocknotejs.org/docs/foundations/document-structure)
- [djot syntax and AST](https://djot.net/)
