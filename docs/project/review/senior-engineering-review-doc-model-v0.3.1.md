# Senior Engineering Review: TextDoc and DocGraph Document Model

**Audience:** chopdiff document-model maintainers and implementers\
**Scope:** uploaded review bundle: design docs, plans, core code, example output,
changelog, and existing review notes\
**Review mode:** static senior engineering review of the provided snapshot.
I did not run the project’s test suite here; the bundle itself says the model is
golden-tested and that 290 unit + golden tests pass.
Line references below are to the uploaded files.

* * *

## 1. Executive verdict

The direction is good.
The model is solving a real problem that a single tree cannot solve: Markdown
containment, heading sections, inline spans, future annotations, rendered regions,
synthetic chunks, provenance, and operations all overlap.
The strongest architectural idea is the one now stated in the spec and README: **one
immutable source string plus one Unicode-code-point offset space is the canonical
substrate; everything else is a derived projection**.

That vision should be preserved.

The implementation is not yet ready to freeze as a public stable model.
The remaining problems are mostly not “wrong architecture” problems.
They are **semantic alignment, API drift, durability, and scale** problems:

1. The docs describe `dg.collect()`, `dg.section(id)`, and `dg.node(id)` style query
   surfaces, but the implemented `DocGraph` is a Pydantic serialization object with no
   query API. The code exposes `TextDoc.collect()` instead.
   This is a real design/API mismatch, not a presentation issue.
2. `collect(scope=...)` means “descendants in the node’s own parent/children tree,” not
   “all nodes inside this section/block span.”
   That means a document-layer section node cannot directly collect Markdown
   links/tables inside it.
   The design’s stated “section-scoped rollup” story is therefore not implemented as
   described.
3. `collect(kinds={NodeKind.link})` returns no links unless the caller also knows to
   pass `inline=True`, because inline filtering happens before kind filtering.
   This contradicts the example-style mental model in the docs.
4. Sections are built from the blank-line paragraph editing view, not from structural
   Markdown heading nodes.
   That can create false sections when paragraph splitting disagrees with Markdown
   parsing, especially around fenced code blocks with blank lines.
5. `SpanRef` has the right conceptual anchor, but the implementation is still a minimal
   exact-quote resolver, not real fuzzy anchoring.
   It mutates its input, drops offsets on persistence, and emits unencoded text
   fragments.
6. The node table and structural blocks are cached mutable objects.
   That is risky for a read-mostly projection model: callers can accidentally poison
   future `graph()` or `collect()` results.
7. Node-table assembly repeatedly scans all blocks/sections/sentences for each inline
   node. That is likely fine for small documents, but it does not satisfy “parse cost ≈
   one Markdown parse” at large sizes or link-heavy workloads.
8. The codebase still has old wording and some code shape that treats the node table as
   canonical, while the better design says the offset space is canonical and the node
   table is one projection.

None of these require throwing away the design.
They require tightening the implementation around the design’s own spine.

**Recommended stance:** continue with the layered offset-space architecture, but do not
build annotation, synthetic, or cross-layer edit APIs until the query semantics, section
construction, `SpanRef`, and immutable snapshot boundary are fixed.

* * *

## 2. What is solid and should be preserved

### 2.1 Source + offset space as the substrate

This is the most important design decision.
The spec now says the canonical substrate is the source text plus exact `[start, end)`
spans in Unicode code points, and that structural models are derived projections.
The README says the same thing in plainer terms: block tree, section hierarchy, link
index, base-block partition, and node table are all projections over the same
source/offset space.

Keep this. It is the reason the model can support overlapping structures without
collapsing into an awkward “one tree plus exceptions” design.

### 2.2 Parser-backed structural Markdown blocks

`block_tree.py` is one of the best-aligned files in the bundle.
It uses `flowmark_markdown().parse(text)` and `block_span(element)`; it explicitly
states that chopdiff makes no block-boundary decisions of its own.
Containers recursively populate their children, and list tightness is metadata rather
than structure.

This is exactly the right posture for Markdown.
Avoid local regex logic for structural Markdown boundaries wherever possible.

### 2.3 Query vs. partition distinction

The distinction between `collect()` and `base_blocks()` is valuable:

- `collect()` is a query.
  Results may overlap their containers.
  That is correct for “find all tables” or “find all links in this span.”
- `base_blocks()` is a partition.
  It is ordered, non-overlapping, and intended for linear processing or resequencing.

This prevents a common model failure: trying to make one representation serve both
recursive semantic queries and linear document manipulation.

### 2.4 Mechanism over menu

The design’s “one query primitive, not dozens of blessed rollup methods” principle is
right. A low-level library should not grow `tables()`, `links_by_section()`,
`count_tables_in_blockquotes()`, `images_by_sentence()`, and so on.
It should expose a small set of composable primitives.

The issue is not the principle.
The issue is that the current primitive needs sharper semantics: subtree traversal,
offset containment, overlap, layer selection, and inline selection are different
operations and should be named accordingly.

### 2.5 DocGraph as projection, not runtime editor model

`DocGraph` should remain the language-neutral serialized projection.
It should not become a second editable document model competing with `TextDoc`. Editing
should flow through source/text operations, then reparse/rederive.

The implementation mostly respects that.
The docs, however, sometimes imply `DocGraph` is also a rich runtime query object.
Pick one public story and make it consistent.

### 2.6 Deterministic debug/golden outputs

The debug dumper is a strong engineering practice.
The report includes source metadata, base-block cover checks, sections, node table,
links, and `SpanRef` round-trips.
The golden-testing plan is appropriate for a deterministic model.

Keep the transparent-box goldens, but add targeted tests for the semantic gaps listed
below. Goldens catch broad drift; targeted tests catch invariants that should never be
papered over by regenerating expected output.

* * *

## 3. Vision and goal clarity

The clearest vision statement is:

> A document is one source string plus a shared offset space.
> Textual structure, Markdown structure, document sections, synthetic regions,
> annotations, rendered geometry, and provenance are independent layers over that offset
> space. Within a layer, use parent/child trees where they are well-nested.
> Across layers, use interval relationships.
> `TextDoc` is the Python/editing surface; `DocGraph` is the serialized projection.

That is clean. The team should keep refining the docs and code toward this exact
statement.

The phrases to avoid or qualify:

- “The node table is canonical.”
  It is better described as the **id-addressed query/serialization projection** over the
  canonical offset substrate.
- “Any rollup at section scope” unless the API actually resolves section scope through
  offset containment.
- “Fuzzy re-anchor” unless the implementation uses actual fuzzy/edit-distance or
  confidence-based anchoring.
  The current code is exact substring search plus prefix/suffix scoring.
- “DocGraph query API” unless `DocGraph` actually exposes one.

A good public mental model would be:

```python
# Parse/editing surface.
doc = TextDoc.from_text(markdown)

# Read-only parsed snapshot over immutable source.
snapshot = doc.snapshot()

# Query over the snapshot.
links = snapshot.collect(within=section_id, kinds={NodeKind.link})

# Serialize for clients.
graph = snapshot.graph(include={Layer.markdown, Layer.document}, detail={Detail.inline})
```

This separates editing, querying, and serialization without sacrificing flexibility.

* * *

## 4. Highest-priority findings

### Finding 1 — P1: Documented query API does not match implemented API

**Evidence**

The spec documents query usage at `dg`, `dg.section(id)`, and `dg.node(id)` scope and
gives examples such as:

```python
dg.collect(kinds={NodeKind.table}, recursive=True)
dg.section(s3).collect(kinds={NodeKind.link}, recursive=True)
```

The implementation does not match this.
`DocGraph` is a Pydantic model with `to_yaml()` but no `collect()`, `section()`, or
`node()` methods. The actual convenience query method is `TextDoc.collect(...)`, which
delegates to `collect(self.node_table(), ...)`.

**Impact**

This is the most visible API drift.
A team member reading the spec will try an API that does not exist.
Worse, the migration note says `doc.graph().collect(...)`, but `doc.graph()` returns a
`DocGraph` serialization object.

**Recommendation**

Pick one of these two directions:

1. **Preferred:** keep `DocGraph` pure serialization and introduce a read-only
   `DocumentSnapshot` / `DocModel` query object:

   ```python
   snapshot = doc.snapshot()
   snapshot.collect(...)
   snapshot.section(section_id).collect(...)
   snapshot.graph(...)
   ```

   Then update spec examples from `dg.collect(...)` to `snapshot.collect(...)` or
   `doc.collect(...)`.

2. Add query methods to `DocGraph`, but then it is no longer just a wire projection.
   If this path is chosen, make `DocGraph` explicitly a rich value object, not only a
   schema object.

Do not leave the docs and code split.

* * *

### Finding 2 — P1: `collect(scope=...)` is subtree scope, not section/block span scope

**Evidence**

`collect()` treats `scope` as a node id whose candidates come from
`_subtree_nodes(table, scope, recursive)`. For a document-layer section node, its
children are document-layer subsection nodes.
Markdown blocks, inline links, textual paragraphs, and sentences are not descendants of
that document-layer section node.
Cross-layer containment is available only through the separate `contains=(start, end)`
filter.

**Impact**

The design requirement says rollups should be scoped by section and block, recursively,
across blocks and inline items.
The current `scope` parameter does not deliver that for cross-layer section queries.

For example, conceptually this should return links inside a section:

```python
doc.collect(scope=section_id, kinds={NodeKind.link}, recursive=True, inline=True)
```

But with current semantics, `scope=section_id` only traverses section descendants.
It will not walk into Markdown block children or inline nodes.

**Recommendation**

Separate the concepts in the API:

```python
collect(subtree_of=node_id, ...)        # within-layer parent/child tree
collect(within=node_id_or_span, ...)    # offset-contained cross-layer query
collect(overlapping=node_id_or_span, ...)  # partial-overlap query
```

Keep `scope` only if it is renamed or made unambiguous.
In a layered model, “scope” is too broad a word for a parent/child subtree.

A minimal backward-compatible version:

```python
def collect(
    table,
    scope: str | None = None,          # deprecated alias for subtree_of
    *,
    subtree_of: str | None = None,
    within: str | tuple[int, int] | None = None,
    overlaps: str | tuple[int, int] | None = None,
    ...
):
    ...
```

Then document section recipes using `within=section_id`, not `scope=section_id`.

* * *

### Finding 3 — P1: Explicit inline kind queries are filtered out unless `inline=True`

**Evidence**

`collect()` filters inline nodes before checking `kinds`:

```python
if not inline and node.kind in INLINE_KINDS:
    continue
if kinds is not None and node.kind not in kinds:
    continue
```

That means this intuitive query returns nothing unless the caller remembers
`inline=True`:

```python
doc.collect(kinds={NodeKind.link}, recursive=True)
```

The docs’ own examples use `kinds={NodeKind.link}` without showing `inline=True`.

**Impact**

This is a footgun in the main query primitive.
It weakens the “mechanism over menu” story because the mechanism behaves surprisingly
for common queries.

**Recommendation**

Make explicit kind selection override the inline-default filter:

```python
requested_inline = kinds is not None and bool(kinds & INLINE_KINDS)
include_inline = inline or requested_inline

if not include_inline and node.kind in INLINE_KINDS:
    continue
```

Alternatively remove the `inline` flag and make callers filter by `kinds`/`layer`; but
if the flag remains, explicit `kinds={link}` should work.

* * *

### Finding 4 — P1: Sections are built from paragraph heading detection, not structural heading nodes

**Evidence**

`TextDoc.sections()` loops through `self.paragraphs` and calls `para.heading_level()`.
`Paragraph.block_type` parses a blank-line-separated slice, and `block_types.py`
explicitly warns that the per-paragraph view can split loose lists and fenced code
blocks with blank lines.

**Impact**

The section model can diverge from the Markdown structural parse.
The clearest failure case is a fenced code block containing a blank line followed by a
`#`-prefixed line. The paragraph splitter can isolate the `#` line as its own paragraph,
and paragraph-level heading detection can treat it as a real section heading even though
Markdown structure says it is code.

This violates the design’s own preference for parser-backed structure.

**Recommendation**

Build sections from the structural Markdown layer:

1. Parse `doc.blocks()` once.
2. Walk structural heading blocks in document order.
3. Use parser-derived heading levels and spans.
4. Build a heading stack.
5. Derive section spans from heading boundaries.
6. Attribute textual paragraphs, Markdown blocks, and inline nodes to sections using
   interval containment.

This will also make document-layer section nodes more naturally connected to Markdown
heading nodes and reduce repeated heading parsing.

* * *

### Finding 5 — P1: `set_sent()` breaks source-reference semantics for edited sentences

**Evidence**

`TextDoc.set_sent()` replaces a sentence with:

```python
Sentence(sent_str, old_sent.offsets)
```

It does not preserve `old_sent.original_text`. `Sentence.span` uses `original_text`
length when present, otherwise the current editable `text` length.
Therefore, after a changed-length edit, the span no longer describes the original source
slice.

**Impact**

The broader `TextDoc` contract says offsets and original text are fixed references to
the source as parsed.
`set_sent()` silently changes that behavior for one sentence.

**Recommendation**

Either preserve the original source reference:

```python
self.paragraphs[index.para_index].sentences[index.sent_index] = Sentence(
    sent_str,
    old_sent.offsets,
    original_text=old_sent.original_text,
)
```

Or explicitly mark source references invalid after mutation.
Do not silently retain the offset while changing the span length.

This needs a targeted test:

```python
doc = TextDoc.from_text("Hello world.")
old_span = doc.get_sent(SentIndex(0, 0)).span

doc.set_sent(SentIndex(0, 0), "Hello much longer world.")

assert doc.get_sent(SentIndex(0, 0)).span == old_span
# or assert source_ref_state == INVALID, if that is the chosen contract
```

* * *

### Finding 6 — P1: `SpanRef` is directionally right but not annotation-ready

**What is right**

The concept is correct: a `SpanRef` carries a quote (`exact`, `prefix`, `suffix`) as the
durable anchor and offsets as recomputable hints.
This is the right split for annotations and source-grounded references.

**Current implementation issues**

- `to_persisted()` drops offsets entirely.
  The spec shape presents offsets as optional hints; the implementation removes them.
  Decide whether persisted refs keep position hints.
- `resolve()` mutates the passed-in `SpanRef` by writing `start`/`end`. That may be
  useful for caching, but it is surprising for a function named `resolve`.
- The fallback is exact substring search plus prefix/suffix scoring.
  That is not fuzzy anchoring after altered text.
- `to_text_fragment()` concatenates raw prefix/exact/suffix into a URL fragment without
  percent encoding.
- `_CONTEXT_WINDOW = 24` is fixed.
  That will be too small for repeated boilerplate or short repeated strings.

**Recommendation**

Before adding annotation storage or cross-layer edit operations, split the contract into
clear selector roles:

```python
@dataclass(frozen=True)
class SpanRef:
    exact: str
    prefix: str | None = None
    suffix: str | None = None
    position: TextPosition | None = None  # start, end, unit="unicode_code_points"
```

Expose explicit functions:

```python
persist(ref, include_position_hint=True) -> PersistedSpanRef
resolve(ref, source_text) -> ResolvedSpan | None        # no mutation
resolve_and_update(ref, source_text) -> SpanRef | None  # mutation/update explicit
to_text_fragment(ref, max_chars=...) -> str             # percent-encoded
```

Add confidence/failure states before production annotation UI depends on it.

* * *

### Finding 7 — P1/P2: Mutable cached projections can be poisoned by callers

**Evidence**

- `TextDoc.blocks()` returns a fresh list, but the `Block` objects inside are shared
  mutable dataclasses.
- `TextDoc.node_table()` returns the cached mutable `NodeTable` directly.
- `collect()` returns the cached mutable `Node` objects.
- `source_text` itself is a mutable dataclass field, but caches assume it is immutable
  after parse.

**Impact**

A caller can accidentally mutate a `Block`, `Node`, `NodeTable`, or `source_text` and
affect future `graph()`/`collect()` results.
This is especially risky because the design says structural projections are read-mostly
derived from immutable source.

**Recommendation**

Introduce an immutable parsed snapshot boundary:

```python
snapshot = doc.snapshot()
snapshot.blocks          # tuple/frozen block nodes or read-only wrappers
snapshot.node_table      # MappingProxyType / frozen nodes
snapshot.sections
snapshot.interval_index
snapshot.collect(...)
snapshot.graph(...)
```

Keep `TextDoc` mutable for editing/reassembly.
Make the parsed snapshot immutable and source-backed.
After edits, users explicitly create a new snapshot from the edited/reassembled source.

Minimal near-term hardening:

- Make `Block` and `Node` frozen dataclasses if possible.
- Return read-only mappings or copies from `node_table()`.
- Add a cache version/source hash check before using cached projections.
- Document that mutating returned nodes/blocks is unsupported until immutability lands.

* * *

### Finding 8 — P1/P2: Node-table assembly is likely super-linear

**Evidence**

For each inline link/code/image/html span, `node_table.py` performs repeated scans:

- `_find_innermost_block(...)` scans all Markdown block nodes.
- `_find_deepest_section(...)` scans all nodes to find section containment.
- `_find_sentence_node(...)` scans all nodes to find sentence containment.

Those functions are called for each locatable link and each atomic inline span.

**Impact**

This is `O(inline_items × nodes)` on top of parsing.
For small docs it is fine.
For link-heavy docs, generated docs, or large knowledge-base pages, it can become the
dominant cost.

**Recommendation**

Build an interval index once per parsed snapshot:

```python
index = IntervalIndex.from_nodes(nodes)
parent = index.innermost(offset, layer=Layer.markdown, block_only=True)
section = index.innermost(offset, layer=Layer.document, kind=NodeKind.section)
sentence = index.innermost(offset, layer=Layer.textual, kind=NodeKind.sentence)
inside = index.contained_by(span, layer=Layer.markdown)
overlap = index.overlapping(span, layer=Layer.synthetic)
```

This will also solve the cross-layer section query problem more cleanly than
special-casing sections.

* * *

## 5. Detailed architectural review

### 5.1 Canonical substrate vs. node table

The current design is strongest when it says: **the source/offset space is canonical;
the node table is a projection.**

Some module docstrings still say the node table is the canonical normalized form.
That wording should be removed from `node.py`, `node_table.py`, and any changelog/spec
remnants. It is not only a docs issue.
It affects how future contributors will build features.

Recommended final position:

- The source string and offset space are canonical.
- `blocks()`, `sections()`, `links()`, `base_blocks()`, and the node table are sibling
  projections sharing that substrate.
- The node table is the most important query/serialization projection because it assigns
  ids and layer tags.
- Public views do not have to literally project from the node table as long as they are
  derived from the same source/offset substrate and validated against each other.
- Cross-layer relationships should be computed from intervals, not stored as edges,
  unless stored only as cache accelerators.

This resolves the “node table vs.
projection” tension without forcing a costly inversion where every view must be
implemented on top of node ids.

### 5.2 Layers and duplication

The model honestly allows the same span to appear in multiple layers.
For example, a heading line is both:

- a Markdown `heading` node;
- a textual `paragraph` node;
- a textual `sentence` node;
- part of a document-layer `section` span.

That is not a bug. It is the layered model.
But the query API must make layer selection easy and obvious.

Recommendations:

- Keep `layer=` as an explicit filter.
- Add recipes for common queries:
  - Markdown block counts: `layer={Layer.markdown}`, non-inline.
  - Links in a section: `within=section_id`, `kinds={NodeKind.link}`.
  - Textual paragraphs only: `layer={Layer.textual}`, `kinds={NodeKind.paragraph}`.
  - Containing section for a link:
    `index.innermost(link.span[0], layer=Layer.document, kind=NodeKind.section)`.
- Consider making default examples always specify `layer=` when conceptual duplicates
  are possible.

### 5.3 Query API design

The current primitives are close, but `scope`, `contains`, `recursive`, `inline`, and
`layer` are doing too much without clear names.

A clearer API would separate four axes:

```python
collect(
    subtree_of: str | None = None,       # parent/children within a layer
    within: str | tuple[int, int] | None = None,    # full interval containment
    overlaps: str | tuple[int, int] | None = None,  # partial interval overlap
    kinds: set[NodeKind] | None = None,
    layer: set[Layer] | None = None,
    where: Callable[[Node], bool] | None = None,
) -> list[Node]
```

Then `recursive` becomes an implementation detail of `subtree_of`, not a global semantic
flag.

A compact alternative:

```python
collect(relation=SubtreeOf(node_id), kinds=...)
collect(relation=ContainedBy(section_id), kinds=...)
collect(relation=Overlaps(span), kinds=...)
collect(relation=Contains(span), kinds=...)
```

This is more abstract, but it matches the model: **tree relationships and interval
relationships are different relationship types**.

### 5.4 Sections and TOC

The section model should be rebuilt around Markdown heading nodes.

Questions the team should explicitly answer and encode in tests:

- Do headings inside blockquotes create document sections?
  Many tools do not treat quoted headings as document headings; some Markdown ASTs still
  parse them as headings inside quote nodes.
- Do HTML headings count as sections?
- Do setext headings behave exactly like ATX headings?
- Should headings inside list items become document sections?
- What happens with malformed headings or unmatched code fences?

The current paragraph-based builder blurs those policy choices.
A structural builder forces them to be explicit.

### 5.5 Base blocks

The base-block partition is useful and should stay.
The current caveats are important:

- Exact reconstruction is by slicing source spans and preserving gaps, not by
  concatenating base-block rendered text.
- List markers and indentation can be outside trimmed child spans.
- Continuation paragraphs inside list items retain their real block type, which is the
  right choice.
- `item_partition_depth` is powerful but needs thorough tests for `0`, `1`, default `6`,
  and `-1`.

Recommendation: add helper APIs for reconstruction so consumers do not invent lossy
concatenation:

```python
reconstruct_from_base_blocks(source_text, base_blocks, include_gaps=True)
move_base_block(source_text, block_id_or_span, target_index, new_depth=...)
```

Even if editing helpers are later, a reconstruction helper will clarify the contract.

### 5.6 Inline links, images, and atomic spans

The model’s choice to make inline items nodes with a block parent is correct.
The span recovery remains a heuristic layer.

Potential edge cases to test:

- duplicate URLs;
- a URL that is a substring of another URL;
- repeated link text;
- link text with nested brackets;
- inline link titles;
- URLs with escaped or nested parentheses;
- reference-style images;
- image titles;
- autolinks that can also look like HTML atomics;
- reference definitions outside the current section;
- bare URLs adjacent to punctuation.

Where possible, push for parser-provided source positions upstream rather than expanding
local substring heuristics indefinitely.

### 5.7 DocGraph schema and serialization

`DocGraph` is small and readable.
The `include`/`detail` split is good.
The current schema still needs contract hardening before cross-language clients rely on
it.

Issues:

- `NodeModel.attrs: dict[str, object]` is too loose for a language-neutral contract.
  Use a recursive `JSONValue` type and validate it.
- `Detail.tokens` and `Detail.coords` are public enum values but reserved.
  That is acceptable if clearly documented, but consumers may assume they work.
- `included_ids` is built and never read in `build_doc_graph()`.
- `_is_parent_included()` only checks parent layer, while child filtering uses
  `_node_included()` and also respects `include_inline`. Use the same predicate for
  both.
- `views.blocks` currently means all included Markdown non-inline nodes, including
  nested block nodes. Document that explicitly.
- There is no formal schema evolution policy yet: additive fields, reserved arrays,
  version bumps, and compatibility expectations should be stated.

### 5.8 Mutability and cache ownership

`TextDoc` currently blends two responsibilities:

1. mutable editing/reassembly view;
2. owner of source-backed cached parse projections.

The docs acknowledge this, but the code does not enforce it.
The risk will grow with annotations, synthetic layers, operations, and layout.

Recommended model:

```python
class TextDoc:
    # mutable editing view
    def reassemble(self) -> str: ...
    def set_sent(...): ...
    def snapshot(self) -> DocumentSnapshot: ...

@dataclass(frozen=True)
class DocumentSnapshot:
    source_text: str
    blocks: tuple[Block, ...]
    node_table: FrozenNodeTable
    sections: tuple[SectionNode, ...]
    interval_index: IntervalIndex
    def collect(...): ...
    def graph(...): ...
```

This does not make the library heavier for users.
It makes the lifecycle honest: source-backed analysis is immutable; editing produces a
new source or invalidates snapshots.

### 5.9 TextDoc module size

`text_doc.py` is too large for the next phase.
It currently holds:

- `TextDoc`;
- `Paragraph`;
- `Sentence`;
- `Offsets`;
- `SentIndex`;
- `Section`;
- link recovery;
- heading helpers;
- sizing;
- word token bridge;
- `collect()` bridge;
- `graph()` bridge;
- caches.

Suggested split:

- `editing.py`: `TextDoc`, `Paragraph`, `Sentence`, `Offsets`, `SentIndex`, reassembly,
  edits.
- `links.py`: `Link`, `_block_links`, link/span recovery tests.
- `sections.py`: structural section builder and `Section` data.
- `snapshot.py`: cached immutable source-backed parse snapshot.
- `queries.py`: collect, interval relations, interval index.
- `doc_graph.py`: serialization only.

Keep public imports stable by re-exporting from the existing package surface.

* * *

## 6. Granular issue log

Severity key:

- **P0:** release blocker / data corruption risk.
- **P1:** high priority; fix before relying on annotation/synthetic layers, large
  documents, or stable public APIs.
- **P2:** medium priority correctness, ergonomics, or maintainability issue.
- **P3:** cleanup, docs, or polish.

I do not see a P0 in the provided snapshot.

### P1 issues

| Issue | Evidence | Impact | Recommendation |
| --- | --- | --- | --- |
| Docs show `DocGraph` query API that does not exist | `textdoc-spec.md` examples use `dg.collect`, `dg.section`; `DocGraph` only has serialization methods | Users follow broken examples; API boundary unclear | Add `DocumentSnapshot`/query object or implement query methods on `DocGraph`; update docs |
| `collect(scope=...)` is subtree-only | `collect.py` uses `_subtree_nodes()` when `scope` is present | Section-scoped cross-layer rollups do not work directly | Rename to `subtree_of`; add `within` / `overlaps` interval queries |
| Explicit inline kind query needs `inline=True` | `collect()` excludes inline before `kinds` | `collect(kinds={link})` returns nothing by default | Make explicit inline `kinds` imply inline inclusion, or fix all docs/recipes |
| Sections built from paragraph view | `TextDoc.sections()` walks `self.paragraphs` and calls `heading_level()` | False sections when paragraph splitting disagrees with Markdown parse | Build sections from structural heading blocks |
| `set_sent()` drops `original_text` | New `Sentence(sent_str, old_sent.offsets)` omits original source | Edited sentence spans can become wrong | Preserve `old_sent.original_text` or mark source refs invalid |
| `SpanRef.to_text_fragment()` not URL-encoded | Raw string concatenation | Invalid/ambiguous fragments for spaces, punctuation, Unicode | Percent-encode and add browser-compatible tests |
| `SpanRef.resolve()` mutates input | Writes `span_ref.start/end` | Surprising side effect in reference resolver | Return immutable result; add explicit update variant |
| Cached projections are mutable | Cached `NodeTable`, shared `Block`/`Node` dataclasses | Callers can poison later graph/query results | Freeze/read-only snapshot or defensive copies |
| Node table assembly scans repeatedly | Per-inline parent/section/sentence lookup scans nodes | Link-heavy docs can be slow | Add interval index / sweep-line association |

### P2 issues

| Issue | Impact | Recommendation |
| --- | --- | --- |
| Old “node table is canonical” wording remains in module docstrings | Maintainers get conflicting model guidance | Replace with “node table is an id-addressed projection over source/offset substrate” |
| `attrs: dict[str, object]` too loose | Weak cross-language schema | Define and validate JSON-compatible value type |
| `Detail.tokens` and `Detail.coords` reserved but public | Consumers may assume behavior exists | Mark as reserved clearly or defer enum values |
| `included_ids` unused | Minor code clutter | Remove |
| Parent filtering is less strict than child filtering | Future partial-detail modes could point to omitted parents | Use `_node_included()` for parent checks |
| `collect(layer=None)` returns conceptual duplicates | Correct but surprising | Document recommended `layer=` recipes prominently |
| `sections()` and `toc()` recompute | Repeated cost | Cache sections in immutable snapshot after structural rewrite |
| `source_text` reassignment can stale caches | Inconsistent parse results | Freeze source in snapshot or invalidate caches on reassignment |
| `block_type_counts()` compatibility unclear | Spec says superseded; code keeps method | Retain as compatibility helper or deprecate explicitly |
| Link/image span recovery heuristic | Potential mis-binding edge cases | Expand tests; prefer parser positions upstream |
| `base_blocks()` reparses each call | Could matter if used heavily by UI | Cache by `(source_hash, item_partition_depth)` if benchmark warrants |
| `NodeTable.containing/contained_by` only support full containment | Synthetic regions may partially overlap Markdown blocks | Add overlap relation before synthetic layer |
| Node id order not pinned for ports | Rust/TS clients could produce different ids | Specify traversal and id assignment in schema tests |
| `LAYER_NESTING` not enforced | Future layers can violate assumptions | Add invariant validation per layer |

### P3 issues

| Issue | Recommendation |
| --- | --- |
| Tests live inside `node.py` under `## Tests` | Move to normal test modules |
| `collect._subtree_nodes()` uses `list.pop(0)` | Use `collections.deque` |
| `TextDoc` docstring typo “Markown” | Fix |
| Changelog still has older canonical wording | Update before release |
| Empty `frozenset()` defaults are safe but noisy with pyright ignores | Use module-level `EMPTY_DETAIL` if desired |
| Debug docs could teach query recipes | Add small query recipe section |

* * *

## 7. Suggested near-term action plan

### Next PR: semantic correctness and docs alignment

1. Fix spec examples and migration notes so they refer to the implemented query object.
2. Rename or supplement `scope` with explicit `subtree_of` and `within` semantics.
3. Make `collect(kinds={inline_kind})` work without requiring `inline=True`.
4. Build `sections()` from structural Markdown heading blocks.
5. Fix `set_sent()` source-reference behavior.
6. URL-encode `SpanRef.to_text_fragment()` and make `resolve()` mutation explicit or
   remove it.
7. Update stale “node table is canonical” wording in `node.py`, `node_table.py`, and the
   changelog.
8. Remove `included_ids` and move tests out of `node.py`.

### Next milestone: parsed snapshot and interval queries

1. Introduce `DocumentSnapshot` as the immutable source-backed parsed view.
2. Move cached blocks/node table/sections/links into the snapshot.
3. Add an interval index and route parent/section/sentence attribution through it.
4. Add `within` and `overlaps` query relations.
5. Freeze or read-protect `Node`, `Block`, and `NodeTable` outputs.
6. Add microbenchmarks for large docs and link-heavy docs.

### Before annotation/synthetic layers

1. Finalize `SpanRef` persistence shape, mutation policy, context window configuration,
   URL-fragment encoding, and failure/confidence semantics.
2. Add partial-overlap fixtures for synthetic tags that cross Markdown block boundaries.
3. Define a multi-target/discontiguous annotation strategy.
4. Define operation records for cross-layer structural edits.
5. Pin node-id order and offset conversions for Rust/TypeScript clients.

* * *

## 8. Test additions that would materially improve confidence

Add these targeted tests in addition to the existing golden corpus:

### Query semantics

```python
def test_collect_link_kind_includes_inline_implicitly():
    doc = TextDoc.from_text("[x](https://example.com)")
    links = doc.collect(kinds={NodeKind.link}, recursive=True)
    assert len(links) == 1
```

```python
def test_section_within_collects_cross_layer_links():
    doc = TextDoc.from_text("# A\n\nSee [x](https://example.com).")
    section = first_section_node(doc)
    links = doc.collect(within=section.id, kinds={NodeKind.link})
    assert len(links) == 1
```

### Section correctness

```python
def test_heading_inside_fenced_code_with_blank_line_is_not_section():
    md = """# Real\n\n```\ntext\n\n# Not a heading\n```\n"""
    doc = TextDoc.from_text(md)
    assert [title for _, title, _ in doc.toc()] == ["Real"]
```

### Editing/source-reference contract

```python
def test_set_sent_preserves_original_span_or_invalidates_it():
    doc = TextDoc.from_text("Short.")
    before = doc.get_sent(SentIndex(0, 0)).span
    doc.set_sent(SentIndex(0, 0), "A much longer replacement.")
    after = doc.get_sent(SentIndex(0, 0)).span
    assert after == before  # if preserving source refs is the contract
```

### SpanRef

```python
def test_text_fragment_percent_encoded():
    ref = SpanRef(exact="a b # c, π")
    assert ref.to_text_fragment() == "#:~:text=a%20b%20%23%20c%2C%20%CF%80"
```

```python
def test_resolve_does_not_mutate_unless_explicit():
    ref = SpanRef(exact="target")
    before = dataclasses.replace(ref)
    resolve(ref, "target")
    assert ref == before
```

### Link/image edge cases

- duplicate link text, different URLs;
- duplicate URLs, different text;
- URL substring of another URL;
- escaped parentheses in URL;
- inline link with title;
- reference-style image;
- image title;
- bare URL next to punctuation;
- reference definition outside section.

### Performance

- 1 MB Markdown with many headings and paragraphs;
- 10k links in one document;
- deeply nested lists at `item_partition_depth=-1`;
- repeated paragraph text for `SpanRef` disambiguation;
- many synthetic-like marker spans crossing Markdown boundaries.

Set budgets for:

- `TextDoc.from_text()`;
- `doc.blocks()`;
- `doc.node_table()` / snapshot build;
- `doc.graph()`;
- common `collect(within=section_id, kinds={...})` calls.

* * *

## 9. Areas of uncertainty the team should decide explicitly

### Target document size

If typical documents are under a few hundred KB, current scan-based node assembly may be
fine short term. If multi-MB docs, generated docs, or link-heavy docs are in scope, the
interval index is urgent.

### Section policy

Decide and test:

- headings inside blockquotes;
- headings inside list items;
- HTML headings;
- setext headings;
- malformed heading-like text;
- headings inside fenced code.

### Exactness policy

The model has three different exactness levels:

1. source-span exact (`source_text[start:end]`);
2. Markdown-object equivalent after normalization;
3. lossy normalized `reassemble()` output.

These should be stated everywhere consumers might confuse them, especially around base
blocks and editing.

### Annotation durability

Quote + prefix/suffix is a good floor.
Production annotations usually need:

- confidence scores;
- fuzzy matching;
- multi-selector fallback;
- human-visible unresolved states;
- multi-target and discontiguous annotations.

Decide which subset v1 will support before the annotation layer lands.

### Synthetic overlap

Synthetic regions may partially overlap Markdown blocks.
The current `containing()` / `contained_by()` helpers only express full containment.
Decide whether partial overlap is valid, invalid, or valid with special semantics.

### Editing boundary

Today there is sentence-level mutation in the editing view.
Future structural operations are described as source transforms anchored by `SpanRef`.
Define whether these are two separate edit mechanisms or one operation model with two
frontends.

### Cross-language contract

For Rust/TypeScript clients, pin:

- node id format;
- traversal/order that assigns ids;
- Unicode code point offset rules;
- UTF-8 byte and UTF-16 conversion tests;
- JSONValue constraints for `attrs`.

* * *

## 10. Simplification ideas that preserve flexibility

### 10.1 Introduce `DocumentSnapshot`

This is the single highest-leverage simplification.

```python
doc = TextDoc.from_text(markdown)
snapshot = doc.snapshot()

snapshot.blocks
snapshot.sections
snapshot.node_table
snapshot.interval_index
snapshot.collect(within=..., kinds=..., layer=...)
snapshot.graph(include=..., detail=...)
```

Benefits:

- separates mutable editing from immutable source-backed parse state;
- gives one home for caches;
- makes query API discoverable;
- keeps `DocGraph` pure serialization;
- makes future synthetic/annotation layers easier to compose.

### 10.2 Make interval relations first-class

Do not hide cross-layer relationships behind a generic `contains` tuple.
Model them directly:

```python
ContainedBy(section_id)
Contains(span)
Overlaps(span)
SubtreeOf(node_id)
```

This is still mechanism-over-menu.
It just names the core mechanisms.

### 10.3 Keep `collect()` minimal but add recipes

Avoid adding dozens of convenience methods.
Instead add a short query recipe page:

```python
# Markdown block counts only
Counter(n.kind for n in snapshot.collect(layer={Layer.markdown}, recursive=True))

# Links in a section
snapshot.collect(within=section_id, kinds={NodeKind.link})

# Tables inside blockquotes
snapshot.collect(subtree_of=blockquote_id, kinds={NodeKind.table})

# Sentences containing code spans
for code in snapshot.collect(kinds={NodeKind.code_span}):
    sentence = snapshot.containing(code, layer={Layer.textual}, kind=NodeKind.sentence)

# Source span to containing section/block/sentence
snapshot.interval_index.containing(span)
```

This preserves API flexibility and reduces user confusion.

### 10.4 Treat `SpanRef` as a small selector family

Keep the public `SpanRef` name, but internally model selectors:

- `TextQuoteSelector`: `exact`, `prefix`, `suffix`;
- `TextPositionSelector`: `start`, `end`, `unit`;
- optional `TextHashSelector` for large spans;
- future `StructuralPathSelector` or editor anchor only when needed.

This aligns with annotation prior art without making v1 heavy.

### 10.5 Use layer providers for unbuilt layers

Instead of growing `node_table.py` for each future layer, define a provider protocol:

```python
class LayerProvider(Protocol):
    layer: Layer
    nesting: NestingGuarantee

    def build_nodes(
        self,
        source_text: str,
        existing_nodes: NodeTable,
        intervals: IntervalIndex,
    ) -> list[Node]: ...
```

Then markdown, textual, document, synthetic, annotations, layout, and provenance can be
plugged into the same builder pipeline.

* * *

## 11. Recommended definition of done for the next stable milestone

I would consider the model ready for broader team/API adoption when these are true:

- The spec, README, changelog, and module docstrings consistently say source + offset
  space is canonical and the node table is a projection.
- The query API has explicit, tested subtree vs.
  interval semantics.
- Section-scoped cross-layer queries work directly.
- Explicit inline-kind queries work without a hidden `inline=True` requirement.
- Sections/TOC are built from structural Markdown heading blocks.
- Editing APIs have explicit, tested source-reference behavior.
- `SpanRef` persistence, mutation, text-fragment encoding, and exact-vs-fuzzy behavior
  are settled.
- Parsed projections are immutable/read-only or have explicit cache invalidation.
- Node-table assembly uses an interval index or has benchmark evidence that scans are
  acceptable at target sizes.
- The golden corpus includes headings-in-code, link/image edge cases, repeated text
  anchors, Unicode offsets, and section-scoped queries.
- `DocGraph/v0.1` constrains JSON values and documents node-id order.
- Synthetic and annotation layers have at least one executable spike validating partial
  overlap and durable anchoring.

* * *

## 12. Bottom line

The architecture is worth keeping.
The right abstraction is not “a document is a tree”; it is “a document is source text
plus offset-addressed layers.”
That is the right foundation for sections, Markdown structure, inline elements,
synthetic regions, annotations, rendered mappings, and provenance.

The next work should be practical and concrete:

1. Fix the query API mismatch.
2. Make cross-layer interval queries first-class.
3. Build sections from structural headings.
4. Harden `SpanRef` before annotations depend on it.
5. Introduce an immutable parsed snapshot.
6. Add an interval index.
7. Tighten the serialized schema.
8. Split `text_doc.py` before adding more layers.

With those changes, the model can remain flexible without becoming vague, and it can
become much easier for the team to explain, test, port, and evolve.
