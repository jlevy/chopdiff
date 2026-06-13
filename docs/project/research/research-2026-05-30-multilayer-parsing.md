# Research: Multi-Layer, Multi-View Parsing over an Immutable Source

**Date:** 2026-05-30 (last updated 2026-05-30)

**Author:** Claude (with Joshua Levy)

**Status:** Complete (survey with primary-source citations)

> Companion to two prior briefs, which it builds on rather than repeats:
> [`research-2026-05-29-document-model.md`](research-2026-05-29-document-model.md) (the
> broad cross-language survey: stand-off markup, lossless trees, CRDTs, block-JSON,
> editor models, the model/format/implementation separation) and
> [`research-2026-05-30-span-references.md`](research-2026-05-30-span-references.md)
> (durable span references / Chrome Text Fragments / W3C selectors).
> This brief narrows to one question those two raised but did not fully develop: **what
> does it mean to treat a document as several coexisting, independently-enabled parses
> over one immutable source, and is that a coherent, novel, and useful framework?** It
> also develops, in the layered context, **how durable span references (Chrome Text
> Fragments, W3C selectors, fuzzy anchoring) anchor an annotation/reference layer** that
> survives reparse and edits, consolidating the span-reference brief into the layered
> model rather than leaving it as a separate concern.

## Overview

Chopdiff already parses the same source text several different ways:

- `TextDoc` parses it into a linear sequence of paragraphs, sentences, and word tokens.
- The block-aware work (v0.4.0) parses it into flowmark/marko Markdown block structure
  and a heading-derived section/TOC hierarchy.
- `TextNode` parses it into a tree of explicit HTML `<div>` regions, *without*
  interpreting the Markdown inside them.

The insight motivating this brief: these are not three competing document models to be
unified into one tree.
They are **four (or more) independent parses of one immutable source string, each
producing offset-keyed spans into that same string.** None is more “true” than the
others. They overlap and cross-cut: a heading-defined section can contain several
Markdown blocks; a `<div>` can open mid-block; a sentence can straddle two blocks; a
link is an inline range inside a block.
Forcing them into a single hierarchy loses information; keeping them as separate
coordinate-aligned layers over one source loses nothing.

The proposed framework, then, is a **flexible framework for layered parsing**: a backing
document (the immutable source plus a node table keyed to code-point offsets) over which
any number of *parse layers* can be turned on.
Each layer contributes nodes/spans; each layer exposes its own derived view (a tree or
an ordered list); relationships *between* layers are computed on demand by offset
containment rather than stored as edges.
Layers have dependencies (sections need headings, which need block parsing) and a cost,
so a document is “parsed to” some configuration of enabled layers rather than parsed
once and for all.

This is the conceptual core behind both `DocGraph` (the serialized, language-neutral
projection of the layers) and `TextDoc` (the Python parsing/analysis API that builds and
queries them). The non-tree insight itself is *not* new; overlapping-markup data models
(GODDAG, LMNL, TAG) and multi-tier NLP annotation (UIMA, annotation graphs) established
it decades ago, and the academic community explicitly retracted the “text is one
hierarchy” thesis (OHCO) in 1996. What is underexplored, and where this framework aims
to contribute, is **packaging that insight as a small, embeddable, source-grounded,
JSON-serializable library with à-la-carte layer enablement and an explicit dependency
graph**, rather than a full markup meta-language or a heavyweight NLP framework.
Getting that framework right is what buys flexibility for downstream uses we have not
yet imagined.

## Questions to Answer

1. Is “one immutable source, many coexisting independently-enabled parse layers” a
   coherent model, or does it collapse into either a single tree or an unmanageable
   graph?
2. What prior art exists for *multiple* coordinated structural layers over one text (as
   opposed to one tree and external annotations), and where does each fall short of a
   general framework?
3. How do Chopdiff’s existing parses (`TextDoc`, block/section, `TextNode` divs) map
   onto layers, and which are genuinely independent vs dependent?
4. What is the right relationship primitive *across* layers (stored edges, or computed
   offset containment), and when does containment break (overlap, mid-block boundaries)?
5. How should layers be classified by *purpose* (comprehension/reading vs
   manipulation/rewriting vs both), and does that classification inform the API?
6. What are the three implementation strata (contract `DocGraph` / parsing API `TextDoc`
   / serialization) and which one carries the flexibility?
7. What is the hardest open problem (offset invalidation under edits) and how do related
   systems handle it?
8. How do durable span references (Chrome Text Fragments, W3C selectors, fuzzy
   anchoring) work, how do they differ, and how does a reference anchor a layer so it
   survives reparse and edits?

## Scope

Included: the *layering* question specifically: coexisting parses, enablement and
dependencies, cross-layer relationships, layer purpose taxonomy, how this reframes the
node-table-with-views architecture already recommended in the broad survey, and **how
durable span references anchor an annotation/reference layer** (consolidating and
building on `research-2026-05-30-span-references.md`).

Excluded (covered elsewhere, cited not repeated): the full editor/parser/CRDT/PDF survey
and the comparison matrix (see `research-2026-05-29-document-model.md`); choice of
Markdown parser (Marko vs djot); offset-unit choice (settled: Unicode code points).
No new dependency selection and no implementation code here.

## Findings

### Prior art: multiple coordinated layers over one source

The layered framing is novel as a *practical embeddable library design*, but the
underlying idea (that one text needs several coexisting structures) has a long and
mostly academic lineage.
The recurring lesson across four traditions is the same: **the single tree is the thing
that breaks, and the fix is to share one anchor space (text leaves or character offsets)
across independent structural layers.** That is exactly the node-table-keyed-to-offsets
substrate proposed here.
What is largely *missing* from the prior art is à-la-carte enablement with a dependency
graph and a deliberately small, JSON-serializable, language-neutral contract; most prior
systems are either full markup meta-languages or heavyweight NLP frameworks.

#### Overlapping / concurrent markup

The text-encoding community hit the single-tree wall directly and produced a sequence of
non-tree data models:

- **SGML CONCUR** (ISO 8879:1986) already allowed multiple DTDs over one document, each
  a different hierarchy, the conceptual precedent for concurrent layers, though rarely
  implemented.
- **MECS** and its successor **TexMECS** (Huitfeldt; Sperberg-McQueen) permit elements
  to *overlap* rather than nest; TexMECS drops even MECS’s same-type non-overlap
  restriction.
- **GODDAG** (Sperberg-McQueen & Huitfeldt, 2000/2004) is the canonical data structure:
  multiple markup trees share the same ordered leaf (text) nodes, and overlap is
  represented by nodes with multiple parents, forming a DAG over shared leaves.
  This is the direct ancestor of “many trees, one anchor space.”
- **LMNL** (Tennison & Piez, 2002) replaces the element hierarchy with named *ranges*
  over a string plus structured *annotations*; ranges freely overlap and hierarchy is
  *derived, not prescribed*, strikingly close to “spans over source, views derived by
  containment.”
- **XConcur** (Witt & Schonefeld) layers N independent XML hierarchies over one source,
  each separately extractable and validatable; XConcur-CL adds cross-layer constraints.
- **TAG / TAGML** (Huygens ING, 2017) models text as a property *hypergraph*: hyperedges
  connect a markup node to multiple text nodes, so overlap and discontinuity are native.
- **Standoff properties** (rooted in 1990s TIPSTER) keep annotations as offset-keyed
  `{start, end, type}` records over immutable text, the lightweight, JSON-friendly end
  of this spectrum, and the closest in spirit to chopdiff’s intended weight.

The takeaway: every one of these abandoned the single tree, and the durable common
denominator is *shared leaves / shared offsets and independent structural layers*.
Chopdiff’s contribution is not the non-tree insight (well-established) but packaging it
as a small, enable-by-need, source-grounded, serializable model rather than a markup
meta-language.

#### Stand-off and multi-tier annotation (NLP / linguistics)

The linguistics tradition independently arrived at “many layers, one immutable source,”
and crucially treats layers as *tiers*: flat, independent segmentations rather than one
hierarchy:

- **UIMA CAS** supports multiple *views*, each with its own Subject of Analysis and its
  own annotation index, all sharing one type system and CAS, the closest enterprise
  ancestor of typed layers over a shared base.
- **NIF 2.0** anchors all annotation to RFC 5147 character-offset URIs over an immutable
  `Context` string; independent layers (POS, entities, parses) are just different RDF
  triples over the same offsets.
  This validates code-point offsets as the cross-layer lingua franca.
- **ELAN** and **Praat TextGrid** use stacked, independent *tiers* over one media
  timeline (utterance / word / phoneme / gesture), with ELAN distinguishing independent
  from dependent tiers, a direct precedent for the layer *dependency* idea (sections
  depend on headings the way a word tier depends on an utterance tier).
- **Annotation graphs** (Bird & Liberman, 2001) formalize all of this: annotations are
  labeled edges over shared anchor nodes; different annotation types are independent
  subgraphs, no single tree privileged, the closest formal statement of “node table with
  typed layers.”

#### Multi-grammar / layered parsing in tools

Working editors and parsers already do layered parsing over one buffer, which is direct
evidence the approach is implementable and performant:

- **Tree-sitter injections** restrict a parser to byte ranges (`included_ranges`), so a
  host grammar (HTML) and embedded grammars (JS, CSS) each produce their own tree over
  the same buffer; editors literally call these “language layers” and they nest
  recursively. This is the strongest engineering precedent for *enabling* parsers per
  region/dimension.
- **LSP semantic tokens** are an offset-keyed annotation layer *on top of* syntax
  highlighting, a semantic layer that needs type information the grammar layer cannot
  provide, merged with it at render time.
  Precedent for “comprehension layer over a structural layer.”
- **TextMate / VS Code injection grammars** and **Emacs Polymode / MMM-Mode** add scoped
  sub-grammars or multiple major modes to regions of one buffer, the same layering at
  the editor level.

#### The OHCO thesis and its overlapping-hierarchy critique

The academic framing of exactly why one tree is insufficient:

- **OHCO:** “What is Text, Really?”
  (DeRose, Durand, Mylonas, Renear, 1990). Argued text *is* an Ordered Hierarchy of
  Content Objects, the theoretical justification for SGML/XML tree markup.
- **The retraction:** “Refining Our Notion of What Text Really Is” (Renear, Mylonas,
  Durand, 1996). Three of the same authors concede, after TEI experience, that real
  documents exhibit *multiple concurrent overlapping hierarchies* and that no version of
  OHCO survives counterexample.
  This is the canonical statement that a document is **not** a single tree.

Chopdiff’s model is, in effect, the post-OHCO position operationalized: do not pick one
hierarchy; keep several as layers over a shared anchor space, and compute relationships
between them on demand.

### The backing document: source and node table keyed to offsets

The substrate every layer shares is small and boring on purpose:

- **Immutable `source_text`:** Canonical, never mutated in place; edits produce a new
  source and a reparse (see the broad survey’s “Markdown source should remain
  canonical”).
- **Offset coordinate system:** Unicode code points (settled; matches Python `str`
  indexing and W3C text selectors; UTF-16/byte conversions are derived, not canonical).
- **A node table:** Each node has a stable id (within one parse), a `kind`, a
  `source_span` `[start, end)` in code points, and a `layer` it belongs to.
  The table is the meeting place: nodes from different layers coexist because they are
  all just spans into the same string.

Crucially, there is **no single parent pointer that spans layers.** Within a layer a
node may have a parent (block tree, section tree); across layers, “containment” is a
*query* over offsets, not a stored edge.
This is what lets layers overlap without contradiction.

### Layers are independent parses, with a dependency DAG

The four dimensions the project has identified, restated as layers with their inputs:

| Layer | Produces | Reads | Depends on |
| --- | --- | --- | --- |
| **Textual** | paragraphs, sentences, word tokens | `source_text` | — |
| **Markdown structure** | block elements (recursive), inline (links, code, emphasis) | `source_text` | — |
| **Document structure** | section / heading hierarchy and TOC | headings | Markdown structure |
| **Synthetic structure** | regions marked by a small defined set of marker tags (today `<div>` / `<span>`), chunk groupings | `source_text` (tag scan only) | — |

Three properties follow:

1. **Most layers parse straight from the source:** Textual, Markdown, and synthetic
   layers each need only `source_text`. They can be enabled in any combination.
   Only the document-structure layer has a hard upstream dependency (sections are
   derived from Markdown headings).
   The dependency graph is shallow: a DAG, mostly flat.

2. **Enablement is a configuration, not an architecture fork:** A document can be held
   with only the synthetic layer on (the cheap div-chunking path: carve `<div>` regions,
   process chunks, reassemble—*no* Markdown or sentence parsing).
   Or textual+Markdown for analysis.
   Or all four. The `TextNode`-as-separable-subsystem design that exists today is, in
   this framing, simply “the synthetic layer with the others left off.”
   That resolves the separable-vs-unified tension: it is the same model at different
   enablement levels, not two architectures.

3. **Cost tracks enablement:** Sentence splitting and full Markdown inline parsing are
   the expensive layers; a structural `<div>` scan is cheap.
   Pricing parsing by layer lets a caller pay only for what a use case needs.

The synthetic layer is a general “structure from marker tags” mechanism, not a `<div>`
special case. “Synthetic” means structure that is not inherent in the prose or Markdown
but is added via a small, defined whitelist of marker tags, and that whitelist can hold
different kinds of tags: standard HTML containers (`<div>`/`<span>`, today), custom
semantic tags (`<chunk>`), or comment-delimited Markdoc-style directives
(`<!-- chunk id="foo" -->`). Each region becomes a node carrying its tag name and
attributes, so a new marker tag is a whitelist entry, not new parser code.
(Only `<div>`/`<span>` are parsed today; the rest is the design principle.)

### Cross-layer relationships are offset-containment queries

Because every node is a span in one coordinate system, the universal relationship
operator is interval containment/overlap, not tree navigation:

- “Which Markdown blocks fall inside this `<div class="chunk">`?” → blocks whose span ⊆
  the div span.
- “Which section contains this link?”
  → the section whose span contains the link span.
- “Is this `<span data-timestamp>` inside a single sentence?”
  → sentence span ⊇ span span.

This is the payoff of the shared coordinate system: in-band metadata discovered during
parsing (a `data-timestamp` span from the synthetic layer) and an out-of-band annotation
attached externally (a SpanRef) become *the same kind of thing*, a span carrying a
payload, and relate to every other layer by the same containment query.
The bridge between in-band and out-of-band metadata is structural, not manual.

### Referencing portions of a document: span references as a layer

An out-of-band annotation needs a way to say *which* portion of the document it targets,
and that reference must survive two things the layered model takes for granted: reparse
(the node table is a cache, rebuilt from source, so node ids are not durable) and edits
(offsets shift). A raw offset pair fails both.
The mature systems all converge on the same answer: **store multiple coordinated
selectors, make a text quote canonical, treat offsets as a hint.** That answer is what
makes references a well-behaved *layer* rather than a fragile pointer.
This section consolidates the span-reference brief into the layered model.

#### How the major formats reference a span

- **Chrome / WICG Text Fragments** (`#:~:text=…`). Grammar:
  `#[element-id]:~:text=[prefix-,]textStart[,textEnd][,-suffix]`. `textStart` alone is
  an exact match; `textStart,textEnd` is a range; a trailing `prefix-` and leading
  `-suffix` supply disambiguating context.
  Matching is case-insensitive (Unicode base-character, accent-insensitive),
  **word-boundary constrained** ("range" matches “mountain range”, not “orange”),
  whitespace-flexible, and each piece must sit within one block-level element.
  Critically, there is **no robustness fallback**: if no match is found the fragment is
  *silently ignored*. The spec itself calls text fragments “less stable than document
  structure”; they are designed for *transient* links (search result highlights,
  sharing), not durable anchors.
  `-`, `,`, `&` in content are percent-encoded; the `:~:` directive is stripped from
  script-visible URLs; a user gesture is required (anti-abuse).
  Supported in Chrome/Edge/Opera/Safari and Firefox (2024+); feature-detect via
  `document.fragmentDirective`.
- **W3C Web Annotation selectors.** The reference vocabulary: `TextQuoteSelector`
  (`exact` + `prefix` + `suffix`; most robust, context disambiguates and the quote
  enables fuzzy re-match); `TextPositionSelector` (`start`/`end` integer offsets; fast
  but brittle, and the spec **never resolved code-points vs UTF-16**, a real interop
  hazard); `RangeSelector` (start/end via XPath/CSS; DOM-tied).
  Composition is first-class: `refinedBy` (e.g. a section fragment refined by a quote)
  and `oa:Choice` (ordered alternatives, the fallback mechanism).
  This is the menu chopdiff’s reference type draws from.
- **Hypothesis / Apache Annotator, fuzzy anchoring (the battle-tested practice).**
  Stores *three* selectors per annotation (Range, TextPosition, and TextQuote) and
  re-anchors in priority order: (1) DOM range, verified against the quote; (2) position
  offsets, verified against the quote; (3) quote fuzzy-search *hinted* by the offset;
  (4) quote full-document fuzzy search.
  Fuzzy matching uses Google diff-match-patch (Bitap) with a hint offset and threshold;
  ~32 chars of prefix/suffix are stored.
  **None of the three is “canonical,” but the quote is what makes recovery possible;**
  offsets are recomputed on success.
- **RFC 5147 (`text/plain`) and W3C Media Fragments** (for comparison).
  Pure offset/line identifiers (`#char=0,99`, `#line=10,19`, `t=10,20`), optionally with
  `;length=`/`;md5=` **integrity checks** that *detect* change but offer no recovery.
  Useful precedent for “offsets plus an integrity hint,” not for robustness.

#### Strategy comparison

| Strategy | Robust to edits | Disambiguation | Compact | Standard |
| --- | --- | --- | --- | --- |
| Offset span | Fragile (shifts) | Perfect if unchanged | Two ints | RFC 5147, `TextPositionSelector` |
| Text quote (exact only) | Moderate | Poor if repeated | ~ selection | `TextQuoteSelector` |
| Quote + prefix/suffix | Good (fuzzy-able) | Good | exact + ~32×2 | `TextQuoteSelector`, Chrome TF |
| Structural path | Fragile to restructure | Good | Moderate | `RangeSelector` |
| Multi-selector ensemble | Best | Excellent | Larger | Hypothesis, `oa:Choice` |

The lesson is consistent across all of them, and it is the offset-unit pitfall too:
`len("🤦🏼‍♂️")` is 5 code points, 7 UTF-16 units, 17 UTF-8 bytes, so the unit must be
declared. Chopdiff pins **Unicode code points** (Python-native, matches W3C text
selection) and treats UTF-16/byte forms as derived conversions.

#### `SpanRef`: chopdiff’s reference, and why it is a layer

The recommended shape carries *both* a durable quote and a recomputable offset hint, and
deliberately never persists the in-memory node id:

```python
class SpanRef:
    # Quoted span — canonical durable anchor (survives edits; Text-Fragment compatible)
    exact: str
    prefix: str = ""        # ~32-128 chars of context
    suffix: str = ""
    # Offset span — exact within the current source; a recomputable HINT, code points
    start: int | None = None
    end: int | None = None
    # (node_id is an in-memory handle only and is NEVER persisted)
```

Naming note: the type is `SpanRef` rather than a bare `Reference`, which is too generic
for a low-level library.
The first version is at least as expressive as Chrome’s prefix/suffix+exact model;
refinement (multiple coordinated selectors, structural paths, `oa:Choice`-style
alternatives) is expected once the annotation layer is exercised.

This is exactly what makes references a *layer* in the framework rather than a pointer:

- **The annotation/reference layer is the out-of-band layer:** It is ordered and
  overlap-tolerant (a SpanRef can straddle paragraphs), so by the nesting-guarantee rule
  its view is a list, not a tree.
  It is the one layer whose nodes are authored externally rather than parsed from
  source, but it anchors to the same offset coordinate space as every parsed layer, so
  cross-layer containment queries work unchanged ("which section / block / sentence
  contains this annotation?").
- **Re-anchoring is the layered model’s reparse, applied to references:** When source
  changes the node table is rebuilt; a SpanRef re-resolves to nodes by the Hypothesis
  order (offset hint verified against `exact`, then offset-hinted fuzzy, then
  full-document fuzzy) and its offsets are recomputed.
  Persistence is quote-canonical precisely because node ids and offsets do not survive
  reparse; the quote does.
- **In-band and out-of-band unify through SpanRef:** A parsed in-band span (a
  `<span data-timestamp>` from the synthetic layer) is *already* source-grounded, so it
  can emit a SpanRef for free; an externally-authored annotation *is* a SpanRef plus a
  payload. One reference mechanism serves both, which is why the in-band/out-of-band
  bridge is structural.
- **Chrome Text Fragment export is a lossy projection** of a SpanRef: emit
  `#:~:text=[prefix-,]exact[,-suffix]` for prose where word-boundary and
  case-insensitive matching is acceptable, truncating context to ~50 chars for URL
  length, and drop the offsets.
  Do *not* store the Text-Fragment URL itself (it is a rendering) or DOM/XPath selectors
  (environment-specific).
  This gives shareable, browser-native deep links out of the same references used
  internally.

### Two view shapes per layer: well-nested tree vs ordered list

Offset containment reconstructs a clean tree *only* when a layer’s spans are
well-nested.
That holds for Markdown blocks and (usually) for `<div>` regions, but not in
general:

- A SpanRef annotation can straddle two paragraphs.
- A `<div>` can legally open mid-block or cross a Markdown boundary.
- Sections nest cleanly among themselves but cross block containment.

So each layer should declare its **nesting guarantee**:

- **Well-nested** → its view is a tree (e.g. `blocks()`, the section tree).
- **Ordered only** → its view is a sequential list with overlap-tolerant queries (e.g.
  `base_blocks()`, a flat annotation layer).

This is exactly the `blocks()` (structural tree) vs `base_blocks()` (sequential
partition) distinction from the TextDoc spec, generalized: *every* layer is either a
tree or an ordered list, and cross-layer queries always fall back to interval logic,
which is defined even when nesting is not.

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
the workhorses for data processing**: you chunk, transform, and reassemble against them,
and they must support exact reassembly.
**Comprehension-oriented layers (sentences, sections-as-TOC) are for understanding**:
they must be cheap to project and query but need not round-trip.
Layers that serve **both** (Markdown blocks, sections) are where the design must be most
careful, since they are read *and* written.
Building document visuals (zoomable outlines, rendered overlays) draws on both kinds at
once: a comprehension view of structure used as a manipulation handle.

### Three implementation strata, and where flexibility lives

The broad survey’s “model ≠ format ≠ implementation” applies directly, with the layered
model as the thing being separated:

1. **`DocGraph`, the contract:** A language-neutral, JSON-serializable projection of the
   enabled layers: source record, node table, per-layer views, annotations.
   One format, implementable in any language, parameterized by *which layers and what
   detail* are included.
   This is what crosses process and language boundaries.
2. **`TextDoc`, the parsing/analysis API:** The programmatic surface that builds layers
   from source and answers queries.
   Python today; could be reimplemented elsewhere.
   It is *an* implementation of the contract, not the contract.
3. **Serialization:** JSON now; Protobuf/columnar later.
   A projection of `DocGraph`, not the model.

The flexibility the project cares about lives in **stratum 1 and the layer framework**:
if the parsing layer yields these flexible, independently-enabled, offset-keyed layered
objects, then any consumer (a Python pipeline, a TS client, a visual UI, an annotation
store) gets exactly the layers/detail it needs from one format.
The Python API can evolve or be ported without changing the contract.

### The hard problem: offset invalidation under edits

The one place layers are *not* independent is editing.
Mutating `source_text` shifts every downstream offset, so all layers’ spans must shift
or invalidate together.
Related systems resolve this three ways, each cited in the prior briefs:

- **Reparse from canonical source** (our default): edits produce new source, layers
  rebuild. Simple; the layer framework is built for this.
- **Red-green / lossless trees**: immutable nodes and positions computed on demand, so
  identity survives reparse (compiler/IDE world).
- **CRDT ids**: per-element stable ids survive arbitrary edits (collaborative world).

For a read-mostly, reparse-from-source library this is the simplest of the three: treat
the node table as a cache off the immutable source, rebuild on edit, and persist
references as source-grounded SpanRefs (quote canonical, offsets as hints) so they
re-anchor across reparses.
The layered framework does not make this harder; it just means “invalidate the cache”
invalidates all enabled layers at once.

## Key Insights

- **Documents are not one tree; they are several parses sharing a coordinate system:**
  The node-table-with-views architecture is not a compromise; it is the honest model.
  (This is the OHCO critique, recast for a practical library.)
- **Separable vs unified is a false dichotomy:** `TextNode`-style structural-only work
  is “the synthetic layer enabled alone.”
  Unified and separable are the same model at different enablement levels, so we keep
  the cheap structural path *and* gain cross-layer queries when more layers are on.
- **Offset containment is the universal cross-layer relationship:** Within a layer, use
  its tree/list; across layers, use intervals.
  This is always defined, even when nesting is not, so overlap never breaks the model.
- **Layers carry a nesting guarantee** (well-nested → tree view; ordered → list view),
  generalizing `blocks()` vs `base_blocks()` to every dimension.
- **Layer purpose predicts layer requirements**: manipulation layers must round-trip
  exactly; comprehension layers must be cheap to project; “both” layers are where rigor
  matters most.
- **Flexibility lives in the contract and framework, not the Python API:** If the
  parsing layer emits flexible, enable-by-need, offset-keyed layered graphs, every
  downstream use (including ones not yet imagined) is a projection, not a refactor.
- **In-band and out-of-band metadata unify:** A discovered `data-*` span and an attached
  annotation are both payload-carrying spans; one framework serves both.
- **A reference is a layer, not a pointer:** Durable span references (quote canonical,
  offsets as hints, node id never persisted) anchor the out-of-band annotation layer to
  the same offset space as parsed layers, so they survive reparse via fuzzy re-anchoring
  (Hypothesis order) and relate to every other layer by containment.
  Chrome Text Fragments are a lossy export, not the storage form.

## Comparison Matrix

How prior approaches handle *multiple structural dimensions over one source*. Axes:
**Multi-layer** (≥2 coexisting structural parses, not one tree and notes); **Overlap**
(can layers cross-cut / overlap without contradiction); **Source-grounded** (offsets
into canonical source); **Enablement** (layers turned on à la carte); **Cross-layer
query** (relate layers without re-parsing).
✅ strong / ◐ partial / ✘ weak.

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

> Draft, to refine after the prior-art pass and a use-case walk-through.

1. **Adopt the layered framing as the conceptual core of `DocGraph`/`TextDoc`:** one
   immutable source, a node table keyed to code-point offsets, and independently-enabled
   parse layers, with cross-layer relationships computed by offset containment.
2. **Model the four current dimensions as the first layers** (textual, Markdown
   structure, document structure, synthetic structure), with the dependency DAG explicit
   (sections → Markdown headings).
   Keep the dependency graph shallow.
3. **Make enablement a parameter, not a fork:** Preserve the cheap structural-only path
   (today’s `TextNode`) as “synthetic layer alone”; do not require full parsing for
   structural chunking.
4. **Give each layer a declared nesting guarantee** (tree vs ordered list), generalizing
   `blocks()`/`base_blocks()`.
5. **Keep the contract (`DocGraph`) language-neutral and parameterized by enabled layers
   and detail;** treat `TextDoc` as one implementation and serialization as a
   projection.
6. **Resolve cross-layer relations by interval logic, never stored cross-layer edges,**
   so overlap is always representable.
7. **Defer** lossless-tree identity and CRDT anchoring; rebuild layers from canonical
   source on edit and persist references as source-grounded SpanRefs.

## Next Steps

- [x] Fold in verified prior-art citations (overlapping markup, UIMA/NIF tiers,
  tree-sitter injections, OHCO critique).
- [x] Cover span-reference formats in depth (Chrome Text Fragments, W3C selectors, fuzzy
  anchoring, `SpanRef`) and tie them to the annotation layer.
- [ ] Walk every existing use case (synthetic chunking, in-band metadata, surgical edit,
  section move, zoomable UI) through the layered lens and confirm each needs only
  offset-keyed spans, per-layer views, and containment queries.
- [ ] Decide how `TextNode`/div parsing is expressed as the synthetic layer (reuse the
  existing parser; key its nodes into the shared table).
- [ ] Specify the layer-enablement API and dependency resolution in the TextDoc spec.
- [ ] Capture the consolidated framing as an Exploration section in
  `plan-2026-05-29-unified-document-model.md`, with offset-invalidation-under-edit as
  the resolved-by-reparse decision.

## Methodology

Builds on local review of `TextDoc`, `TextNode`, the div subsystem, the block-aware work
(v0.4.0), and the two prior research briefs.
A dedicated research pass gathered primary sources for the overlapping-markup,
multi-tier-annotation, layered-parsing, and OHCO-critique threads (folded into
Findings). The span-reference section consolidates the primary-source findings of
`research-2026-05-30-span-references.md` (Chrome Text Fragments, W3C selectors,
Hypothesis fuzzy anchoring, RFC 5147) into the layered model.
A few primary pages returned 403 to automated fetches (TexMECS, xconcur.org, the MPI
ELAN page, the LSP 3.16 spec page); those claims are corroborated by consistent
secondary sources and noted where confidence is lower.
No new benchmarks were run; claims about specific systems reflect their documented
designs.

## References

Local:

- [Cross-language document-model survey](research-2026-05-29-document-model.md)
- [Span-reference research](research-2026-05-30-span-references.md)
- [Unified document model plan](../specs/active/plan-2026-05-29-unified-document-model.md)
- [TextDoc + DocGraph design spec](../../textdoc-spec.md)
- [TextDoc](../../../src/chopdiff/docs/text_doc.py)
- [TextNode](../../../src/chopdiff/divs/text_node.py)

**External:** overlapping / concurrent markup:

- [SGML CONCUR (Library of Congress format description)](https://www.loc.gov/preservation/digital/formats/fdd/fdd000465.shtml)
- [MECS (Huitfeldt)](https://xml.coverpages.org/MECS-200105.html)
- [TexMECS specification](http://mlcd.blackmesatech.com/mlcd/2003/Papers/texmecs.html)
  (403 to automated fetch; see secondary sources)
- [GODDAG (Sperberg-McQueen & Huitfeldt, LNCS 2023)](https://link.springer.com/chapter/10.1007/978-3-540-39916-2_12)
- [LMNL (Tennison & Piez, Extreme Markup 2002)](http://conferences.idealliance.org/extreme/html/2002/Tennison02/EML2002Tennison02.html)
- [LMNL links page (Piez)](http://piez.org/wendell/LMNL/lmnl-page.html)
- [XConcur](https://www.xconcur.org/) (403 to automated fetch)
- [TAG / TAGML (Huygens ING)](https://github.com/HuygensING/TAG)
- [TAG paper (Haentjens Dekker & Birnbaum, Balisage 2017)](https://www.balisage.net/Proceedings/vol21/html/HaentjensDekker01/BalisageVol21-HaentjensDekker01.html)
- [Standoff properties editor](https://github.com/argimenes/standoff-properties-editor)

**External:** stand-off / multi-tier annotation:

- [UIMA Overview & SDK (CAS, Sofa, views)](https://uima.apache.org/d/uimaj-current/oas.html)
- [NIF 2.0 Core specification](https://persistence.uni-leipzig.org/nlp2rdf/specification/core.html)
- [ELAN (MPI)](https://archive.mpi.nl/tla/elan) /
  [EAF spec (CLARIN)](https://standards.clarin.eu/sis/views/view-spec.xq?id=SpecEAF)
- [Praat TextGrid](https://www.fon.hum.uva.nl/praat/manual/TextGrid.html)
- [Annotation graphs (Bird & Liberman, 2001)](https://arxiv.org/abs/cs/0010033)

**External:** layered parsing in tools:

- [Tree-sitter multi-language parsing](https://tree-sitter.github.io/tree-sitter/using-parsers/3-advanced-parsing.html)
- [LSP semantic tokens (3.17 spec)](https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/)
- [TextMate injection grammars](https://macromates.com/blog/2012/injection-grammars-project-variables/)
  /
  [VS Code syntax highlighting](https://code.visualstudio.com/api/language-extensions/syntax-highlight-guide)
- [Polymode](https://polymode.github.io/) /
  [MMM Mode](https://mmm-mode.sourceforge.net/)

**External:** OHCO and its critique:

- [OHCO: “What is Text, Really?” (DeRose et al., 1990)](https://link.springer.com/article/10.1007/BF02941632)
- [Overlapping-hierarchy critique (Renear et al., 1996)](https://www.ideals.illinois.edu/items/9468)

**External:** span references / annotation targeting (see also the span-reference
brief):

- [WICG Scroll-To-Text-Fragment spec](https://wicg.github.io/scroll-to-text-fragment/) /
  [README](https://github.com/WICG/scroll-to-text-fragment/blob/main/README.md)
- [MDN Text Fragments](https://developer.mozilla.org/en-US/docs/Web/URI/Reference/Fragment/Text_fragments)
- [W3C Web Annotation Data Model](https://www.w3.org/TR/annotation-model/) /
  [Vocabulary](https://www.w3.org/TR/annotation-vocab/)
- [Hypothesis fuzzy anchoring](https://web.hypothes.is/blog/fuzzy-anchoring/) /
  [Apache Annotator](https://github.com/apache/incubator-annotator) /
  [diff-match-patch](https://github.com/google/diff-match-patch)
- [RFC 5147 (text/plain fragments)](https://datatracker.ietf.org/doc/html/rfc5147) /
  [W3C Media Fragments](https://www.w3.org/TR/media-frags/)

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
