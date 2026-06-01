# Changelog

All notable changes to chopdiff are documented here.
This project uses [semantic versioning](https://semver.org/); while pre-1.0, breaking
changes bump the **minor** version (see `docs/publishing.md`).

## Unreleased

Adds the DocGraph node model and its supporting infrastructure: a recursive node table
with layers, the `base_blocks()` sequential partition, `collect()` query primitive,
`SpanRef` span-reference type, and the `DocGraph` Pydantic projection (schema
“DocGraph/v0.1”).

### New Features

- **Recursive node table with layers.** The canonical node table fully populates
  container children (blockquotes, list items) and tags each node with its parse `layer`
  (textual, markdown, document, synthetic).
  Cross-layer relationships are offset-containment queries over a shared id space.
- **`base_blocks()` sequential partition.** A flat, depth-annotated, non-overlapping
  partition whose spans cover every non-whitespace character exactly once.
  Lists decompose so each list item is its own base block with increasing `depth`
  (list-item continuation content keeps its own real type, e.g. `paragraph`, not
  `list_item`); blockquotes stay atomic.
  Exact source reconstruction is via each block’s `source_span` (not by concatenating
  block text).
- **`collect()` query primitive.** One general query
  (`collect(kinds=, where=, recursive=, inline=, layer=)`) at document, section, and
  block scope, superseding `block_type_counts()` convenience accessors.
  The `layer=` filter scopes a query to one or more parse layers (default: all layers),
  since the same span can appear as nodes in several layers.
- **`SpanRef` span-reference type.** Quote-canonical, offset-hinted span references for
  durable annotation anchoring (exact fast path within a parse, fuzzy re-anchor across
  edits).
- **`DocGraph` Pydantic projection.** `TextDoc.graph(include=, detail=)` builds a
  serialized, language-neutral JSON contract (schema “DocGraph/v0.1”) with composable
  `Layer` and `Detail` axes.
- **`TextDoc.base_blocks()` method.** A thin method over the `base_blocks` free
  function, so the sequential partition has the same ergonomic surface as `blocks()`.
- **Reusable debug dumper (`chopdiff.docs.debug`).** `doc_report`, `doc_graph_yaml`, and
  `dump_views` turn any document into clean, deterministic standard-format views (a
  multi-view report, the DocGraph, the reassembled source) for REPL/script debugging and
  golden testing.
- **`DocGraph.to_yaml()`.** A clean, deterministic YAML serialization of the projection
  alongside the existing JSON (block style, `|` block scalars, `None`/empty suppressed).

### Fixes

- **`base_blocks()` complete-cover fix.** Content following (or between) a nested
  sublist inside a list item was dropped from the partition; the partition is now a
  complete cover again (verified by a cover-invariant test over all non-whitespace
  source).
- **Structural-parse memoization.** `TextDoc.blocks()` is now cached on the immutable
  `source_text`, and `Section.blocks()` / `Section.links()` slice that single cached
  parse instead of re-parsing the whole document per section (a TOC walk was quadratic).

### Documentation

- **Grounded design principles.** `docs/textdoc-spec.md` now leads with an explicit,
  three-tier principle set (P1–P18) and a pitfalls/decisions note; the goals cite the
  principles they realize.
  The canonical substrate is stated as the source text + offset space, with the node
  table as one projection (not a rival store).

### Dependencies

- New runtime dependency: `pydantic>=2.13.4` (brings `annotated-types`, `pydantic-core`,
  `typing-inspection` as transitive dependencies).
  Required for the `DocGraph` schema.
- New runtime dependency: `frontmatter-format>=0.3.0` (first-party; brings
  `ruamel-yaml`). Used for clean deterministic YAML (`DocGraph.to_yaml`, the debug
  dumper) and the Markdown-with-frontmatter golden-test corpus.

### Compatibility

- **Additive at the API surface.** The DocGraph work adds public names (`base_blocks`,
  `collect`, `SpanRef`, `DocGraph`, `NodeModel`, `Node`, `NodeTable`, `NodeKind`,
  `Layer`, `Detail`, `Views`, `build_doc_graph`, …) without removing or renaming any
  existing export. `Section.block_type_counts()` / `TextDoc.block_type_counts()` are
  retained; `collect()` is the preferred general query, not a replacement.
- **Net release vs. v0.3.0.** Taken together with v0.4.0 (below), the upcoming release
  removes no public symbol present in v0.3.0; every new capability is reached through
  new methods, types, and exports.
  The only behavior changes an existing caller can observe are the two noted under
  v0.4.0: `BlockType.list` is now bullet-only, and default sentence splitting is now
  span-aware (boundaries may differ; see below).

## v0.4.0

Makes `TextDoc` block-aware end to end: an exact-span structural block tree, a section
hierarchy with rolled-up stats, inline-link rollups, and link-aware sentence spans.
The structural view is the canonical normalized form, with every other view (sections,
block-type slices, tallies) derived from it: no stored counts.
Block boundaries and spans now come straight from flowmark’s parser, so chopdiff carries
no Markdown block-detection regex of its own.

### Breaking Changes

- **`BlockType.list` is now bullet-only; ordered lists are `BlockType.ordered_list`.**
  Ordered-ness is carried from marko’s `List.ordered`. Callers that matched
  `BlockType.list` to cover *both* list kinds now miss ordered lists; match
  `{BlockType.list, BlockType.ordered_list}` for either.
- **Default sentence splitting is now span-aware.** `TextDoc.from_text()` with the
  default splitter now routes through `flowmark.atomic_spans.split_sentences_with_spans`
  instead of calling `split_sentences_regex` directly, so sentences never bisect a link,
  code span, or autolink.
  Sentence boundaries can therefore differ from v0.3.0 for text containing those
  constructs. `default_sentence_splitter` is unchanged and passing an explicit splitter
  preserves the previous behavior.

### New Features

- **Opt-in structural block tree with exact spans.** `TextDoc.blocks()` returns a
  `Block(type, span, children, tight)` tree whose boundaries and `[start, end)` spans
  come directly from flowmark’s parser (marko’s own source positions), so a fenced code
  block stays whole through internal blank lines and a list always decomposes into
  `list_item`s with nested sublists.
  The tree is **density-invariant**: tight and loose spacing of the same list produce
  identical block/item counts; `Block.tight` records the CommonMark spacing.
- **Per-section structure and tallies.** `Section.blocks()` scopes the structural tree
  to a section’s own content (document-absolute spans), and
  `Section.block_type_counts()` / `TextDoc.block_type_counts()` give derived
  `Counter[BlockType]` tallies over the live tree (no stored counts).
  `Section.content` holds the section’s own paragraphs (renamed from `Section.blocks`,
  which is now the structural method).
- **Sections, TOC, and rolled-up size stats.** `TextDoc.sections()` returns a tree of
  `Section`s over the heading hierarchy; `TextDoc.toc()` returns a flat
  `(level, title, span)` list.
  `Section.size(unit, subtree=True|False)`, `Section.size_summary()`, and
  `TextDoc.section_size_tree(units=…)` roll up sizes per section in any `TextUnit`.
- **Exact `[start, end)` spans on paragraphs and sentences.** Every `Paragraph` and
  `Sentence` exposes a document-relative `span`; `TextDoc.source_text` is retained so
  each unit’s `original_text` round-trips into the source.
  `TextDoc.block_at_offset(o)` and `sentence_at_offset(o)` invert spans.
- **Inline-link rollups and link-aware sentence spans.** `Link(text, url, title, span)`
  via `Paragraph.links()`, `Section.links()`, and `TextDoc.links()`—identity from
  flowmark’s `extract_links` (reference links resolve across the whole document), spans
  recovered from `iter_atomic_spans`. The default sentence splitter is now
  `flowmark.atomic_spans.split_sentences_with_spans`, so sentence spans are exact for
  all content and never bisect a link, code span, or autolink.
- **More block types:** `BlockType` gains `ordered_list`, `list_item`, and
  `thematic_break`.
- **New public exports:** `Block`, `Link`, `Section`.

### Internal

- **Dropped chopdiff’s regex block scanner.** `TextDoc.blocks()` and
  `Paragraph.block_type` now walk flowmark’s annotated parse tree and map marko classes
  to `BlockType` through a single table; the per-line regex scanner, `classify_block`,
  and the cached `markdown_parser` singleton are gone (net negative code).
  Because chopdiff no longer makes block-boundary decisions, two earlier bugs are fixed
  by construction: reference links resolve across block boundaries, and adjacent blocks
  with no blank line between them split correctly.

### Dependencies

- Requires `flowmark>=0.7.1` for the authoritative block spans
  ([jlevy/flowmark#52](https://github.com/jlevy/flowmark/pull/52)); recorded as a
  reviewed first-party cool-off exception in `SUPPLY-CHAIN-SECURITY.md`. No new
  transitive dependencies over 0.7.0.

### Full Changelog

https://github.com/jlevy/chopdiff/compare/v0.3.0...v0.4.0

## v0.3.0

This is a cleanup release that hardens the build, makes `TextDoc` source-referenced and
Markdown-block-aware, and removes the mandatory `tiktoken` (network) dependency.
It contains several intentional breaking changes for a cleaner API.

### Breaking Changes

- **Token counting is now a dependency-free estimate.** The `tiktoken` dependency is
  removed (along with `requests`/`urllib3` at install time), so chopdiff no longer
  downloads a tokenizer or needs network access to size or summarize a document.
  - `TextUnit.tiktokens` is renamed to `TextUnit.tokens` and now returns a heuristic
    estimate (`chopdiff.util.token_estimate.estimate_tokens`, ~3.8 characters/token, a
    blend of current OpenAI/Anthropic/Google rules of thumb).
  - `chopdiff.util.tiktoken_utils` and `tiktoken_len` are removed.
    Migrate `from chopdiff.util.tiktoken_utils import tiktoken_len` to
    `from chopdiff.util.token_estimate import estimate_tokens`.
  - `size_summary()` reports the estimate as `~N tok`.
  - Exact, provider-keyed token counts (tiktoken/OpenAI, and network-based counters for
    other providers) are planned as opt-in extras in a future release.
- **Character offsets are now an `Offsets` record.** `Paragraph.char_offset` and
  `Sentence.char_offset` (plain ints) are replaced by an
  `Offsets(doc_offset, block_offset)` record on both:
  - `doc_offset` is the absolute offset in the document; `block_offset` is relative to
    the enclosing block (the document for a paragraph, the paragraph for a sentence).
  - `TextDoc.char_offset_in_doc(index)` is removed; use
    `doc.get_sent(index).offsets.doc_offset`.
  - Offsets are now exact references into the unmodified input text (the document is no
    longer stripped during parsing).
- **Paragraph splitting recognizes all blank lines.** Paragraphs split on two or more
  newlines, including blank lines that contain only whitespace; runs of blank lines
  collapse into a single break.
  Previously only a literal `\n\n` split.
- **Removed the unused `chopdiff` console-script entry point.** chopdiff is a library
  with no CLI; the entry point pointed at a non-existent `main`.

### New Features

- **Markdown block-type classification.** `BlockType` (heading, paragraph, list, table,
  code, blockquote, html, footnote) and `Paragraph.block_type`, classified by parsing
  each block with flowmark’s Markdown (marko) parser.
  `TextDoc.iter_blocks(include=, exclude=)` and `TextDoc.filtered(include=, exclude=)`
  iterate or sub-select blocks by type (e.g. process only paragraphs and list items,
  skipping headings and tables), and aggregate counts such as sentences/words across
  paragraph blocks.
- **Exact source references.** Paragraph and sentence `Offsets` round-trip into the
  original text; `TextDoc` documents a clear contract for offsets and in-place editing.

### Infrastructure

- Supply-chain hardening: a 14-day dependency cool-off (`exclude-newer`), a committed
  lockfile, frozen `uv sync --locked` installs in CI, and a `pip-audit` gate.
  See `SUPPLY-CHAIN-SECURITY.md`.
- Upgraded to the simple-modern-uv template v0.2.26 (Python 3.14 in the CI matrix, uv
  0.11.12, basedpyright 1.39.3, docs under `docs/`).
- The release workflow now installs from the committed lockfile (`--locked`) for
  reproducible release builds.

### Full Changelog

https://github.com/jlevy/chopdiff/compare/v0.2.6...v0.3.0
