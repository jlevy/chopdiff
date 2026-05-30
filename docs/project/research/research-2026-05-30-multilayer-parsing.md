# Research: Multi-Layer, Multi-View Parsing over an Immutable Source

**Date:** 2026-05-30 (last updated 2026-05-30)

**Author:** Claude (with Joshua Levy)

**Status:** In Progress

> Companion to two prior briefs, which it builds on rather than repeats:
> [`research-2026-05-29-document-model.md`](research-2026-05-29-document-model.md)
> (the broad cross-language survey: stand-off markup, lossless trees, CRDTs, block-JSON,
> editor models, the model/format/implementation separation) and
> [`research-2026-05-30-span-references.md`](research-2026-05-30-span-references.md)
> (durable span references / Chrome Text Fragments / W3C selectors). This brief narrows to
> one question those two raised but did not fully develop: **what does it mean to treat a
> document as several coexisting, independently-enabled parses over one immutable source,
> and is that a coherent, novel, and useful framework?**

## Overview

Chopdiff already parses the same source text several different ways:

- `TextDoc` parses it into a linear sequence of paragraphs, sentences, and word tokens.
- The block-aware work (v0.4.0) parses it into flowmark/marko Markdown block structure and
  a heading-derived section/TOC hierarchy.
- `TextNode` parses it into a tree of explicit HTML `<div>` regions, *without* interpreting
  the Markdown inside them.

The insight motivating this brief: these are not three competing document models to be
unified into one tree. They are **four (or more) independent parses of one immutable
source string, each producing offset-keyed spans into that same string.** None is more
"true" than the others. They overlap and cross-cut: a heading-defined section can contain
several Markdown blocks; a `<div>` can open mid-block; a sentence can straddle two blocks;
a link is an inline range inside a block. Forcing them into a single hierarchy loses
information; keeping them as separate coordinate-aligned layers over one source loses
nothing.

The proposed framework, then, is a **flexible framework for layered parsing**: a backing
document (the immutable source plus a node table keyed to code-point offsets) over which
any number of *parse layers* can be turned on. Each layer contributes nodes/spans; each
layer exposes its own derived view (a tree or an ordered list); relationships *between*
layers are computed on demand by offset containment rather than stored as edges. Layers
have dependencies (sections need headings, which need block parsing) and a cost, so a
document is "parsed to" some configuration of enabled layers rather than parsed once and
for all.

This is the conceptual core behind both `DocGraph` (the serialized, language-neutral
projection of the layers) and `TextDoc` (the Python parsing/analysis API that builds and
queries them). The claim worth testing in this brief is that this layered framing is
**unusually general** — most prior systems commit to a single privileged hierarchy and
bolt the others on — and that getting the framework right is what buys flexibility for
downstream uses we have not yet imagined.

## Questions to Answer

1. Is "one immutable source, many coexisting independently-enabled parse layers" a
   coherent model, or does it collapse into either a single tree or an unmanageable graph?
2. What prior art exists for *multiple* coordinated structural layers over one text (as
   opposed to one tree + external annotations), and where does each fall short of a
   general framework?
3. How do Chopdiff's existing parses (`TextDoc`, block/section, `TextNode` divs) map onto
   layers, and which are genuinely independent vs dependent?
4. What is the right relationship primitive *across* layers — stored edges, or computed
   offset containment — and when does containment break (overlap, mid-block boundaries)?
5. How should layers be classified by *purpose* — comprehension/reading vs
   manipulation/rewriting vs both — and does that classification inform the API?
6. What are the three implementation strata (contract `DocGraph` / parsing API `TextDoc` /
   serialization) and which one carries the flexibility?
7. What is the hardest open problem (offset invalidation under edits) and how do related
   systems handle it?

## Scope

Included: the *layering* question specifically — coexisting parses, enablement and
dependencies, cross-layer relationships, layer purpose taxonomy, and how this reframes
the node-table-with-views architecture already recommended in the broad survey.

Excluded (covered elsewhere, cited not repeated): the full editor/parser/CRDT/PDF survey
and the comparison matrix (see `research-2026-05-29-document-model.md`); durable
span-reference selector design (see `research-2026-05-30-span-references.md`); choice of
Markdown parser (Marko vs djot); offset-unit choice (settled: Unicode code points). No new
dependency selection and no implementation code here.

## Findings

### Prior art: multiple coordinated layers over one source

> _Citations being verified by a research pass; this section will be filled in with
> primary sources. Placeholder structure below records the threads to cover._

#### Overlapping / concurrent markup

_To fill: GODDAG, LMNL (ranges), TexMECS, TAG/TAGML, XConcur, standoff properties — the
data models that abandon the single-tree assumption._

#### Stand-off and multi-tier annotation (NLP / linguistics)

_To fill: UIMA CAS Sofa + multiple views, NIF + RFC 5147 offsets, ELAN/Praat tiers — the
"many independent layers over immutable text" tradition._

#### Multi-grammar / layered parsing in tools

_To fill: Tree-sitter injection grammars (embedded languages over one buffer), language
servers / semantic tokens as a layer over syntax._

#### The OHCO thesis and its overlapping-hierarchy critique

_To fill: OHCO ("text is an Ordered Hierarchy of Content Objects") and the critique that
real documents have multiple overlapping hierarchies — the academic framing of exactly why
one tree is insufficient._

### The backing document: source + node table keyed to offsets

The substrate every layer shares is small and boring on purpose:

- **Immutable `source_text`.** Canonical, never mutated in place; edits produce a new
  source and a reparse (see the broad survey's "Markdown source should remain canonical").
- **Offset coordinate system.** Unicode code points (settled; matches Python `str`
  indexing and W3C text selectors; UTF-16/byte conversions are derived, not canonical).
- **A node table.** Each node has a stable id (within one parse), a `kind`, a
  `source_span` `[start, end)` in code points, and a `layer` it belongs to. The table is
  the meeting place: nodes from different layers coexist because they are all just spans
  into the same string.

Crucially, there is **no single parent pointer that spans layers.** Within a layer a node
may have a parent (block tree, section tree); across layers, "containment" is a *query*
over offsets, not a stored edge. This is what lets layers overlap without contradiction.

### Layers are independent parses, with a dependency DAG

The four dimensions the project has identified, restated as layers with their inputs:

| Layer | Produces | Reads | Depends on |
| --- | --- | --- | --- |
| **Textual** | paragraphs, sentences, word tokens | `source_text` | — |
| **Markdown structure** | block elements (recursive), inline (links, code, emphasis) | `source_text` | — |
| **Document structure** | section / heading hierarchy + TOC | headings | Markdown structure |
| **Synthetic structure** | explicit `<div>` / `<span>` regions, chunk groupings | `source_text` (tag scan only) | — |

Three properties follow:

1. **Most layers parse straight from the source.** Textual, Markdown, and synthetic
   layers each need only `source_text`. They can be enabled in any combination. Only the
   document-structure layer has a hard upstream dependency (sections are derived from
   Markdown headings). The dependency graph is shallow — a DAG, mostly flat.

2. **Enablement is a configuration, not an architecture fork.** A document can be held
   with only the synthetic layer on (the cheap div-chunking path: carve `<div>` regions,
   process chunks, reassemble — *no* Markdown or sentence parsing). Or textual+Markdown
   for analysis. Or all four. The `TextNode`-as-separable-subsystem design that exists
   today is, in this framing, simply "the synthetic layer with the others left off." That
   resolves the separable-vs-unified tension: it is the same model at different enablement
   levels, not two architectures.

3. **Cost tracks enablement.** Sentence splitting and full Markdown inline parsing are the
   expensive layers; a structural `<div>` scan is cheap. Pricing parsing by layer lets a
   caller pay only for what a use case needs.

### Cross-layer relationships are offset-containment queries

Because every node is a span in one coordinate system, the universal relationship operator
is interval containment/overlap, not tree navigation:

- "Which Markdown blocks fall inside this `<div class="chunk">`?" → blocks whose span ⊆ the
  div span.
- "Which section contains this link?" → the section whose span contains the link span.
- "Is this `<span data-timestamp>` inside a single sentence?" → sentence span ⊇ span span.

This is the payoff of the shared coordinate system: in-band metadata discovered during
parsing (a `data-timestamp` span from the synthetic layer) and an out-of-band annotation
attached externally (a SpanRef) become *the same kind of thing* — a span carrying a
payload — and relate to every other layer by the same containment query. The bridge
between in-band and out-of-band metadata is structural, not manual.

### Two view shapes per layer: well-nested tree vs ordered list

Offset containment reconstructs a clean tree *only* when a layer's spans are well-nested.
That holds for Markdown blocks and (usually) for `<div>` regions, but not in general:

- A SpanRef annotation can straddle two paragraphs.
- A `<div>` can legally open mid-block or cross a Markdown boundary.
- Sections nest cleanly among themselves but cross block containment.

So each layer should declare its **nesting guarantee**:

- **Well-nested** → its view is a tree (e.g. `blocks()`, the section tree).
- **Ordered only** → its view is a sequential list with overlap-tolerant queries (e.g.
  `base_blocks()`, a flat annotation layer).

This is exactly the `blocks()` (structural tree) vs `base_blocks()` (sequential
partition) distinction from the TextDoc spec, generalized: *every* layer is either a tree
or an ordered list, and cross-layer queries always fall back to interval logic, which is
defined even when nesting is not.

### Layer taxonomy by purpose: comprehension, manipulation, both

Layers differ not just in what they parse but in *what they are for*. This is a useful
organizing axis because it predicts which views and operations a layer needs:

| Layer | Primary purpose | Why |
| --- | --- | --- |
| Textual (sentences/tokens) | **Comprehension / analysis** | reading, diffing, summarizing, search, NLP |
| Markdown structure | **Both** | reading (render, outline) *and* manipulation (normalize, rewrite blocks) |
| Document structure (sections) | **Both** | navigation/zoom (comprehension) *and* move-section (manipulation) |
| Synthetic structure (divs/chunks) | **Manipulation / processing** | chunking for LLM passes, wrapping results, surgical splice-back |

The practical reading: **manipulation-oriented layers (synthetic divs, base blocks) are
the workhorses for data processing** — you chunk, transform, and reassemble against them,
and they must support exact reassembly. **Comprehension-oriented layers (sentences,
sections-as-TOC) are for understanding** — they must be cheap to project and query but
need not round-trip. Layers that serve **both** (Markdown blocks, sections) are where the
design must be most careful, since they are read *and* written. Building document visuals
(zoomable outlines, rendered overlays) draws on both kinds at once — a comprehension view
of structure used as a manipulation handle.

### Three implementation strata, and where flexibility lives

The broad survey's "model ≠ format ≠ implementation" applies directly, with the layered
model as the thing being separated:

1. **`DocGraph` — the contract.** A language-neutral, JSON-serializable projection of the
   enabled layers: source record, node table, per-layer views, annotations. One format,
   implementable in any language, parameterized by *which layers and what detail* are
   included. This is what crosses process and language boundaries.
2. **`TextDoc` — the parsing/analysis API.** The programmatic surface that builds layers
   from source and answers queries. Python today; could be reimplemented elsewhere. It is
   *an* implementation of the contract, not the contract.
3. **Serialization** — JSON now; Protobuf/columnar later — a projection of `DocGraph`, not
   the model.

The flexibility the project cares about lives in **stratum 1 + the layer framework**: if
the parsing layer yields these flexible, independently-enabled, offset-keyed layered
objects, then any consumer (a Python pipeline, a TS client, a visual UI, an annotation
store) gets exactly the layers/detail it needs from one format. The Python API can evolve
or be ported without changing the contract.

### The hard problem: offset invalidation under edits

The one place layers are *not* independent is editing. Mutating `source_text` shifts every
downstream offset, so all layers' spans must shift or invalidate together. Related systems
resolve this three ways, each cited in the prior briefs:

- **Reparse from canonical source** (our default): edits produce new source, layers
  rebuild. Simple; the layer framework is built for this.
- **Red-green / lossless trees**: immutable nodes + positions computed on demand, so
  identity survives reparse (compiler/IDE world).
- **CRDT ids**: per-element stable ids survive arbitrary edits (collaborative world).

For a read-mostly, reparse-from-source library this is the simplest of the three: treat the
node table as a cache off the immutable source, rebuild on edit, and persist references as
source-grounded SpanRefs (quote canonical, offsets as hints) so they re-anchor across
reparses. The layered framework does not make this harder; it just means "invalidate the
cache" invalidates all enabled layers at once.

## Key Insights

- **Documents are not one tree; they are several parses sharing a coordinate system.** The
  node-table-with-views architecture is not a compromise — it is the honest model. (This is
  the OHCO critique, recast for a practical library.)
- **Separable vs unified is a false dichotomy.** `TextNode`-style structural-only work is
  "the synthetic layer enabled alone." Unified and separable are the same model at
  different enablement levels, so we keep the cheap structural path *and* gain cross-layer
  queries when more layers are on.
- **Offset containment is the universal cross-layer relationship.** Within a layer, use its
  tree/list; across layers, use intervals. This is always defined, even when nesting is
  not, so overlap never breaks the model.
- **Layers carry a nesting guarantee** (well-nested → tree view; ordered → list view),
  generalizing `blocks()` vs `base_blocks()` to every dimension.
- **Layer purpose predicts layer requirements**: manipulation layers must round-trip
  exactly; comprehension layers must be cheap to project; "both" layers are where rigor
  matters most.
- **Flexibility lives in the contract + framework, not the Python API.** If the parsing
  layer emits flexible, enable-by-need, offset-keyed layered graphs, every downstream use
  — including ones not yet imagined — is a projection, not a refactor.
- **In-band and out-of-band metadata unify.** A discovered `data-*` span and an attached
  annotation are both payload-carrying spans; one framework serves both.

## Comparison Matrix

How prior approaches handle *multiple structural dimensions over one source*. Axes:
**Multi-layer** (≥2 coexisting structural parses, not one tree + notes); **Overlap** (can
layers cross-cut / overlap without contradiction); **Source-grounded** (offsets into
canonical source); **Enablement** (layers turned on à la carte); **Cross-layer query**
(relate layers without re-parsing). ✅ strong / ◐ partial / ✘ weak.

| Approach | Multi-layer | Overlap | Source-grounded | Enablement | Cross-layer query | Lesson for chopdiff |
| --- | --- | --- | --- | --- | --- | --- |
| Single AST (mdast, Marko, ProseMirror) | ✘ one tree | ✘ | ◐ | ✘ | n/a | The thing we are *not* doing |
| OHCO (one content hierarchy) | ✘ | ✘ | ◐ | ✘ | n/a | Its failure motivates layers |
| GODDAG / LMNL / TAG (overlapping markup) | ✅ | ✅ | ✅ | ◐ | ◐ | Data-model precedent for non-tree |
| UIMA CAS (Sofa + views + types) | ✅ typed layers | ✅ | ✅ offsets | ◐ | ◐ | Closest conceptual ancestor |
| NIF / stand-off NLP | ✅ tiers | ✅ | ✅ RFC5147 | ◐ | ◐ | Offset-grounded layering at scale |
| Tree-sitter injections | ✅ grammars | ◐ nested | ✅ byte | ◐ | ◐ | Layered parsing in a real tool |
| W3C Web Annotation | ◐ targets only | ✅ | ✅ | n/a | n/a | Selector model for one layer |
| **Proposed (this brief)** | ✅ | ✅ | ✅ code points | ✅ DAG | ✅ offset containment | — |

## Recommendations

> Draft — to refine after the prior-art pass and a use-case walk-through.

1. **Adopt the layered framing as the conceptual core of `DocGraph`/`TextDoc`:** one
   immutable source + a node table keyed to code-point offsets + independently-enabled
   parse layers, with cross-layer relationships computed by offset containment.
2. **Model the four current dimensions as the first layers** (textual, Markdown structure,
   document structure, synthetic structure), with the dependency DAG explicit (sections →
   Markdown headings). Keep the dependency graph shallow.
3. **Make enablement a parameter, not a fork.** Preserve the cheap structural-only path
   (today's `TextNode`) as "synthetic layer alone"; do not require full parsing for
   structural chunking.
4. **Give each layer a declared nesting guarantee** (tree vs ordered list), generalizing
   `blocks()`/`base_blocks()`.
5. **Keep the contract (`DocGraph`) language-neutral and parameterized by enabled
   layers + detail;** treat `TextDoc` as one implementation and serialization as a
   projection.
6. **Resolve cross-layer relations by interval logic, never stored cross-layer edges,** so
   overlap is always representable.
7. **Defer** lossless-tree identity and CRDT anchoring; rebuild layers from canonical
   source on edit and persist references as source-grounded SpanRefs.

## Next Steps

- [ ] Fold in verified prior-art citations (overlapping markup, UIMA/NIF tiers,
      tree-sitter injections, OHCO critique).
- [ ] Walk every existing use case (synthetic chunking, in-band metadata, surgical edit,
      section move, zoomable UI) through the layered lens and confirm each needs only
      offset-keyed spans + per-layer views + containment queries.
- [ ] Decide how `TextNode`/div parsing is expressed as the synthetic layer (reuse the
      existing parser; key its nodes into the shared table).
- [ ] Specify the layer-enablement API and dependency resolution in the TextDoc spec.
- [ ] Capture the consolidated framing as an Exploration section in
      `plan-2026-05-29-unified-document-model.md`, with offset-invalidation-under-edit as
      the resolved-by-reparse decision.

## Methodology

Builds on local review of `TextDoc`, `TextNode`, the div subsystem, the block-aware
work (v0.4.0), and the two prior research briefs. A dedicated research pass is gathering
primary sources for the overlapping-markup, multi-tier-annotation, layered-parsing, and
OHCO-critique threads; those citations will be folded into Findings.

## References

Local:

- [Cross-language document-model survey](research-2026-05-29-document-model.md)
- [Span-reference research](research-2026-05-30-span-references.md)
- [Unified document model plan](../specs/active/plan-2026-05-29-unified-document-model.md)
- [TextDoc + DocGraph design spec](../../textdoc-spec.md)
- [TextDoc](../../../src/chopdiff/docs/text_doc.py)
- [TextNode](../../../src/chopdiff/divs/text_node.py)

External: _to be added with the prior-art pass._

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
