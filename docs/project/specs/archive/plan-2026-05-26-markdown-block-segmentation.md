# Feature: Parser-Backed Markdown Block Segmentation

**Date:** 2026-05-26 (last updated 2026-05-26)

**Author:** Codex

**Status:** Superseded (archived 2026-05-28)

> **Superseded by [`plan-2026-05-26-block-aware-doc.md`](plan-2026-05-26-block-aware-doc.md).**
> This draft proposed a separate parallel module (`MarkdownDoc`/`MarkdownBlock`)
> alongside `TextDoc`. After v0.3.0 made `TextDoc` block-aware, the maintainers chose
> to add spans, sections, and structural blocks *in place on `TextDoc`* rather than
> introduce a parallel model. Kept for reference: the Marko parser-subclass span
> attachment technique and GFM table handling here inform the structural-block layer of
> the active spec.

## Overview

Add a parser-backed way to segment Markdown documents into typed blocks for analytics,
selective transforms, and downstream document inspection.

The goal is to answer questions like:

- How many paragraphs, list items, block quotes, tables, and fenced code blocks are in
  this document?
- Which blocks are “true text” and should be counted as prose?
- Which blocks are tables, code, HTML, metadata, or other non-prose content?
- How large is the document in existing `TextUnit`s, sliced by block kind or broad
  analysis category?
- How many words, sentences, paragraphs, tokens, or bytes are in each Markdown section,
  with optional filters such as “prose only” or “exclude tables and code”?
- What source span does each block occupy so downstream tools can map analytics and
  transforms back to the original document?

This should use Marko’s Markdown parser rather than adding more regex heuristics to
`TextDoc`.

## Goals

- Parse Markdown into block records with stable block kind, source span, raw source
  text, and text-analysis category.
- Treat paragraphs, block quotes, and list items as prose/text blocks by default.
- Treat tables, fenced code, indented code, HTML blocks, footnote definitions, link
  reference definitions, and thematic breaks as distinct block kinds.
- Support GFM tables through Marko’s `gfm` extension.
- Reuse `TextDoc` for sentence, word, token, and size analysis inside text-like blocks.
- Avoid reparsing every block into its own `TextDoc` for normal analytics.
  Parse the source document once, then answer block and section size questions through
  offsets, spans, and cached per-unit indexes.
- Provide tally helpers that report existing `TextUnit` sizes by block kind, category,
  and section.
- Support section-level rollups based on Markdown headings, including nested heading
  levels.
- Keep this feature additive and avoid changing `TextDoc.from_text()` defaults.
- Avoid regex-only Markdown classification.
- Add focused tests for nested lists, ordered/bulleted/task lists, blockquotes, tables,
  code fences, indented code, HTML blocks, headings, and footnotes.

## Non-Goals

- Do not replace `TextDoc` as the primary sentence/paragraph/token model.
- Do not build a full Markdown editor or renderer.
- Do not guarantee perfect support for every Markdown extension beyond CommonMark plus
  the Marko GFM pieces we explicitly enable.
- Do not treat PR #7’s blank-line paragraph classification as the long-term design.
- Do not add a new Markdown parser dependency unless Marko cannot support the needed
  behavior.

## Background

PR #7, `jlevy/chopdiff#7`, proposes an additive `BlockType` enum,
`Paragraph.block_type`, `TextDoc.iter_blocks()`, and `TextDoc.filtered()` API. The PR is
useful as a short-term bridge.
The current PR implementation parses each blank-line `TextDoc` paragraph with Marko
through `flowmark_markdown()`, which is materially better than regex-only classification
and is reasonable to land before the fuller design if two small API fixes are made
first:

- Re-export `BlockType` from `chopdiff.docs`.
- Make `TextDoc.filtered()` avoid aliasing mutable `Paragraph` objects, or explicitly
  document and name it as a view.

Even with those fixes, PR #7 is still scoped to `TextDoc` paragraph chunks rather than a
full-document Markdown parse:

- Lists are one blank-line block, not individual list items.
- Loose lists and fenced code blocks with blank lines can be split incorrectly.
- Tables are classified only after `TextDoc` has already split the source into
  blank-line paragraphs.
- Existing offsets are approximate because the classification is layered on
  `TextDoc.from_text()`.

The user asked whether this should leverage “marco”; in this repo the relevant parser is
Marko. Marko is already installed transitively through `flowmark`, and Marko 2.2.2 is
present in the locked environment.
It exposes block node types such as:

- `marko.block.Paragraph`
- `marko.block.Heading`
- `marko.block.SetextHeading`
- `marko.block.List`
- `marko.block.ListItem`
- `marko.block.Quote`
- `marko.block.FencedCode`
- `marko.block.CodeBlock`
- `marko.block.HTMLBlock`
- `marko.block.ThematicBreak`
- `marko.block.LinkRefDef`
- `marko.ext.gfm.elements.Table`

Marko does not attach source spans to elements by default.
However, its parser uses a `Source.pos` cursor while parsing blocks, so a small parser
subclass can attach start and end offsets to parsed block elements without
reimplementing Markdown recognition.

This feature should follow the robustness work, especially the fixes around offsets,
empty documents, and `TextDoc` copy semantics.

## Design

### Approach

Create a new full-document parser-backed module rather than expanding `TextDoc`’s coarse
paragraph-level block classification.

Proposed module:

```text
src/chopdiff/docs/markdown_blocks.py
```

Core model:

```python
class MarkdownBlockKind(StrEnum):
    document = "document"
    paragraph = "paragraph"
    heading = "heading"
    list = "list"
    list_item = "list_item"
    blockquote = "blockquote"
    table = "table"
    fenced_code = "fenced_code"
    indented_code = "indented_code"
    html = "html"
    thematic_break = "thematic_break"
    link_reference = "link_reference"
    footnote = "footnote"
    unknown = "unknown"


class MarkdownBlockCategory(StrEnum):
    text = "text"
    table = "table"
    code = "code"
    html = "html"
    metadata = "metadata"
    structural = "structural"
    unknown = "unknown"


@dataclass(frozen=True)
class MarkdownBlock:
    kind: MarkdownBlockKind
    category: MarkdownBlockCategory
    text: str
    start_offset: int
    end_offset: int
    source_text: str
    depth: int = 0
    list_ordered: bool | None = None
    list_start: int | None = None
    heading_level: int | None = None
    code_language: str | None = None


@dataclass(frozen=True)
class MarkdownSection:
    heading: MarkdownBlock | None
    blocks: tuple[MarkdownBlock, ...]
    level: int
    title: str
    start_offset: int
    end_offset: int
```

Expose parser APIs:

```python
def parse_markdown_doc(
    markdown: str,
    *,
    extensions: Iterable[str] = ("gfm",),
    include_containers: bool = False,
) -> MarkdownDoc:
    ...


def markdown_text_doc(block: MarkdownBlock) -> TextDoc:
    ...
```

`MarkdownDoc` should be a lightweight value object around the block list and original
Markdown source:

```python
@dataclass(frozen=True)
class MarkdownDoc:
    source: str
    blocks: tuple[MarkdownBlock, ...]
    text_doc: TextDoc

    def iter_blocks(
        self,
        *,
        include_kinds: set[MarkdownBlockKind] | None = None,
        include_categories: set[MarkdownBlockCategory] | None = None,
        exclude_kinds: set[MarkdownBlockKind] | None = None,
        exclude_categories: set[MarkdownBlockCategory] | None = None,
    ) -> Iterator[MarkdownBlock]:
        ...

    def tally(
        self,
        unit: TextUnit,
        *,
        by: Literal["kind", "category"] = "kind",
        include_kinds: set[MarkdownBlockKind] | None = None,
        include_categories: set[MarkdownBlockCategory] | None = None,
        exclude_kinds: set[MarkdownBlockKind] | None = None,
        exclude_categories: set[MarkdownBlockCategory] | None = None,
    ) -> dict[MarkdownBlockKind | MarkdownBlockCategory, int]:
        ...

    def sections(self) -> tuple[MarkdownSection, ...]:
        ...

    def tally_sections(
        self,
        unit: TextUnit,
        *,
        include_kinds: set[MarkdownBlockKind] | None = None,
        include_categories: set[MarkdownBlockCategory] | None = None,
        exclude_kinds: set[MarkdownBlockKind] | None = None,
        exclude_categories: set[MarkdownBlockCategory] | None = None,
    ) -> dict[str, int]:
        ...
```

Keep a convenience alias if useful:

```python
def parse_markdown_blocks(markdown: str, **kwargs: object) -> list[MarkdownBlock]:
    return list(parse_markdown_doc(markdown, **kwargs).blocks)
```

Default block output should prioritize analytics-friendly leaves:

- Emit `paragraph` blocks for ordinary paragraphs.
- Emit each `list_item` as its own text block, including nested list items.
- Emit each `blockquote` as a text block by default, preserving quote source text.
- Emit `table`, `fenced_code`, `indented_code`, and `html` as non-prose blocks.
- Emit headings separately from paragraph prose.
- Optionally include container blocks such as `list` when `include_containers=True`.

### Source Spans

Use a small Marko parser subclass to attach parser cursor spans:

- Override `Parser.parse_source()`.
- Capture `start_pos = source.pos` before a block element matches and parses.
- Capture `end_pos = source.pos` after parse.
- Attach source positions to the resulting block element.
- Recurse normally so nested `ListItem` and `Quote` children receive spans.

Marko preprocesses CRLF into LF. To keep offsets accurate for original input:

- Normalize only for Marko parsing.
- Build a mapping from normalized offsets back to original string offsets.
- Store original-string offsets on `MarkdownBlock`.
- Use `markdown[start_offset:end_offset]` as the raw source block text.

If exact spans are too fragile for an edge case, fail explicitly in strict mode rather
than silently returning approximate offsets.

### Offset-Backed Analytics

The implementation should not build a fresh `TextDoc` for every block during ordinary
analytics. That would repeat sentence splitting, word tokenization, tiktoken counting,
and Markdown/HTML normalization work many times.

Instead:

- `MarkdownDoc` should own one `TextDoc` parsed from the full Markdown source.
- Robustness work should make `TextDoc` offsets absolute and reliable enough to map
  Markdown blocks back to paragraphs/sentences/tokens.
- Add or reuse offset-based `TextDoc` APIs such as:

```python
def size_span(self, start_offset: int, end_offset: int, unit: TextUnit) -> int:
    ...


def sub_doc_span(self, start_offset: int, end_offset: int) -> TextDoc:
    ...
```

- Internally cache indexes from source offsets to paragraph, sentence, wordtok, and
  token boundaries where it materially improves repeated tallies.
- `MarkdownDoc.tally()` and `MarkdownDoc.tally_sections()` should sum sizes over block
  spans using those indexes, not by slicing source strings and reparsing each block.
- `markdown_text_doc(block)` can still exist as a convenience API for callers that want
  a standalone `TextDoc`, but it should not be the core tally mechanism.

There is one important semantic wrinkle: raw Markdown source spans include syntactic
markers such as list bullets, quote markers, heading markers, code fences, and table
pipes. For source-size units (`bytes`, `chars`) this is exactly correct.
For prose analytics (`words`, `sentences`, `paragraphs`, `wordtoks`, `tiktokens`) each
block should also carry an `analysis_span` or `analysis_text` policy:

- For plain paragraphs, the analysis span is the source span.
- For list items, analysis should exclude the bullet/number/task marker when feasible.
- For blockquotes, analysis should exclude the leading quote marker when feasible.
- For headings, analysis may exclude heading markers, but headings are structural by
  default and excluded from prose-only counts.
- For tables/code/HTML, count source sizes by span; prose-like size units require an
  explicit documented policy.

The first implementation can start with source spans and exact source-size units, but
the design should leave room for per-block analysis spans so prose counts do not require
reparsing block strings later.

### Text Block Semantics

For analytics, distinguish block kind from category:

- `paragraph`, `list_item`, and `blockquote` are `MarkdownBlockCategory.text`.
- `heading` is its own kind and can be either `text` or `structural`; default should be
  `structural` so paragraph-prose counts can exclude headings easily.
- `table` is `MarkdownBlockCategory.table`.
- `fenced_code` and `indented_code` are `MarkdownBlockCategory.code`.
- `html` is `MarkdownBlockCategory.html`.
- `footnote` and `link_reference` are `MarkdownBlockCategory.metadata`.

Callers can then tally by exact Markdown kind or by broad analysis category.

### Size And Tally Semantics

The tally API should use the existing `TextUnit` enum so analytics line up with
`TextDoc`:

- `TextUnit.bytes` and `TextUnit.chars` are measured on `MarkdownBlock.source_text` by
  default, preserving Markdown syntax in source-size analytics.
- `TextUnit.words`, `TextUnit.sentences`, `TextUnit.paragraphs`, `TextUnit.wordtoks`,
  and `TextUnit.tiktokens` are measured through the document-level `TextDoc` and offset
  indexes wherever possible.
- For `MarkdownBlockCategory.text`, use the prose text that should be analyzed.
  For list items this should exclude the bullet/number marker from analysis text while
  retaining it in `source_text`.
- For tables/code/HTML, support source-size tallies in bytes/chars.
  Word/sentence tallies for non-text categories should be explicit and documented:
  - default: count words/tokens over raw source only when the caller includes that
    category;
  - better: expose a `content_mode` option later if consumers need table-cell text,
    code-token text, or rendered/plaintext HTML.
- `TextUnit.paragraphs` for block analytics should mean the number of analyzed text
  paragraphs contributed by a block.
  For a list item, this is usually 1. For a table or fenced code block, this is 0 unless
  the caller explicitly requests source counting.

This lets callers ask:

```python
doc = parse_markdown_doc(markdown)
doc.tally(TextUnit.words, by="category")
doc.tally(TextUnit.tiktokens, include_categories={MarkdownBlockCategory.text})
doc.tally_sections(TextUnit.words, include_categories={MarkdownBlockCategory.text})
doc.tally_sections(TextUnit.paragraphs, exclude_kinds={MarkdownBlockKind.heading})
```

### Section Semantics

Sections should be derived from Markdown headings:

- A section starts at a heading and includes subsequent blocks until the next heading of
  the same or higher level.
- Content before the first heading belongs to a root/untitled section with
  `heading=None`.
- Nested headings create nested logical sections.
  The first implementation can return a flat list with heading level and source span; a
  later version can add a tree if needed.
- Section tallies should include descendant content by default, because that is the
  natural “how big is this section?”
  question. If needed later, add `include_descendants=False`.

Section rollups should preserve the same block filters as document tallies so a caller
can compare, for example, prose word counts by section while excluding tables and code.

### Relationship To PR #7

Assume PR #7 may land first as an interim API for release users.
This spec should build on that baseline rather than requiring it to be reverted.
The follow-on implementation should preserve the parts that are useful while replacing
the parts that are constrained by `TextDoc`’s blank-line paragraph model.

Possible reuse from PR #7:

- The idea of a `StrEnum` block type.
- Include/exclude filtering convenience.
- Some test cases as black-box behavioral examples.
- The direct `marko` dependency, if the merged PR already adds it.

Changes from PR #7:

- Classification is full-document parser-backed, not paragraph-local.
- List items are individual blocks.
- Tables come from Marko GFM table nodes.
- Fenced code and loose lists are not split just because of blank lines.
- Blocks carry source spans and raw source text.

Compatibility stance:

- Keep `BlockType`, `Paragraph.block_type`, `TextDoc.iter_blocks()`, and
  `TextDoc.filtered()` working as convenience APIs if PR #7 lands.
- Treat those APIs as coarse paragraph-level helpers, not as the primary analytics API.
- Add the richer `MarkdownDoc`/`MarkdownBlock` APIs alongside them.
- If naming overlap becomes confusing, document `BlockType` as the coarse `TextDoc`
  classifier and `MarkdownBlockKind` as the precise parser-backed classifier.

### Components

- New module:
  - `src/chopdiff/docs/markdown_blocks.py`
- Public exports:
  - `src/chopdiff/docs/__init__.py`
- Tests:
  - `tests/docs/test_markdown_blocks.py`
- Documentation:
  - `README.md`
  - Possibly `docs/development.md` if dependency notes change
- Dependency metadata:
  - `pyproject.toml` if `marko` becomes a direct dependency

### API Changes

Additive public API:

- `MarkdownBlockKind`
- `MarkdownBlockCategory`
- `MarkdownBlock`
- `MarkdownSection`
- `MarkdownDoc`
- `parse_markdown_doc()`
- `parse_markdown_blocks()`
- Possibly `MarkdownBlock.as_text_doc()` or `markdown_text_doc()`

Potential later API, not required in the first implementation:

- `TextDoc.from_markdown_blocks()`
- `TextDoc.iter_markdown_blocks()`
- `MarkdownDoc` wrapper around the block list

## Implementation Plan

### Phase 0: Land And Stabilize PR #7 Baseline

- [ ] Re-export `BlockType` from `src/chopdiff/docs/__init__.py`.
- [ ] Make `TextDoc.filtered()` copy paragraphs and sentences rather than aliasing the
  source document, unless it is deliberately renamed/documented as a view.
- [ ] Keep the direct `marko` dependency if PR #7 adds it, and confirm the lockfile diff
  does not introduce a new package artifact under `SUPPLY-CHAIN-SECURITY.md`.
- [ ] Add a short README note or docstring language that `Paragraph.block_type` is a
  coarse paragraph-level classifier.
- [ ] Preserve PR #7 tests as regression coverage for the interim API.

### Phase 1: Prototype Full-Document Parser-Backed Blocks

- [ ] Add `markdown_blocks.py` with enums and `MarkdownBlock`.
- [ ] Add `MarkdownDoc` as the owner of the full source, parsed blocks, and a single
  document-level `TextDoc`.
- [ ] Add a Marko parser subclass that annotates block elements with normalized source
  offsets.
- [ ] Add normalized-to-original offset mapping for CRLF-safe source spans.
- [ ] Implement traversal from Marko AST elements to `MarkdownBlock` records.
- [ ] Enable Marko GFM extension for tables by default.
- [ ] Add direct `marko` dependency in `pyproject.toml` if it is not already present
  from PR #7. Since Marko is already locked transitively through `flowmark`, this should
  not introduce a new package artifact, but still review the lockfile diff under
  `SUPPLY-CHAIN-SECURITY.md`.

### Phase 2: Block Semantics And TextDoc Integration

- [ ] Define which node types produce default blocks and which are containers.
- [ ] Add offset-based `TextDoc` range APIs needed by block analytics, after the
  robustness plan fixes absolute offsets.
- [ ] Build cached offset indexes for repeated block and section tallies where useful.
- [ ] Emit individual list-item blocks, including nested ordered, bulleted, and task
  list items.
- [ ] Emit blockquote text blocks without losing nested paragraph text.
- [ ] Emit table, fenced-code, indented-code, HTML, thematic-break, link-reference, and
  footnote blocks distinctly.
- [ ] Add helper to analyze text-category blocks with `TextDoc`.
- [ ] Add `MarkdownDoc.tally()` for existing `TextUnit`s grouped by block kind or
  category.
- [ ] Ensure `MarkdownDoc.tally()` uses full-document offsets rather than reparsing each
  block in the normal path.
- [ ] Define and test source-size versus analysis-text semantics for non-prose blocks.
- [ ] Add include/exclude filtering helpers if they remain simple and clearly useful.

### Phase 3: Section Rollups

- [ ] Add `MarkdownSection` and section extraction based on heading levels.
- [ ] Add section source spans that include all blocks in the section.
- [ ] Add `MarkdownDoc.tally_sections()` with the same filters as `tally()`.
- [ ] Add tests for root content before the first heading, nested headings, sibling
  headings, and filtered prose-only section word counts.

### Phase 4: Documentation, Tests, And PR Resolution

- [ ] Add tests for paragraphs, headings, blockquotes, nested lists, task lists, ordered
  lists, loose lists, tables, fenced code with blank lines, indented code, HTML blocks,
  footnotes, link references, thematic breaks, CRLF input, and empty input.
- [ ] Add tests proving raw source spans reassemble the original block text.
- [ ] Add tests proving document-level and section-level tallies match direct `TextDoc`
  calculations for equivalent filtered text.
- [ ] Add tests or benchmarks that repeated tallies do not construct one `TextDoc` per
  block.
- [ ] Document the feature in README with analytics examples.
- [ ] Document how the precise parser-backed APIs relate to PR #7’s coarse
  paragraph-level `TextDoc` helpers.
- [ ] Run `make lint`, `make test`, and `make build`.

## Testing Strategy

Tests should be behavior-oriented:

- Parse a mixed Markdown fixture and assert ordered block kinds/categories.
- Assert list items are separate blocks.
- Assert tables are recognized through GFM parsing.
- Assert fenced code containing blank lines remains one block.
- Assert blockquote source spans include quote markers while text analysis can still use
  `TextDoc`.
- Assert source spans slice back to the expected original raw text.
- Assert CRLF source offsets map back to the original string.
- Assert `tally(TextUnit.words, by="kind")` and `tally(TextUnit.words, by="category")`
  produce expected counts.
- Assert section tallies are correct for nested headings and block-type filters.
- Assert empty input returns an empty block list.
- Assert all exported types pass basedpyright.

Avoid golden snapshots for the entire Marko AST; the public contract is the
`MarkdownBlock` list, not Marko internals.

## Rollout Plan

- Land PR #7 first if it includes the small public-export and copy-semantics fixes.
- Land the full parser-backed feature after the robustness tasks that fix source offsets
  and `TextDoc` subdocument semantics.
- Keep the API additive and separate from `TextDoc.from_text()`.
- Document limitations clearly, especially around Markdown extensions.
- Treat PR #7 as a short-term convenience layer, not as the final analytics
  implementation.

## Open Questions

- Should headings count as `text` or `structural` by default for analytics?
- Should blockquotes emit one aggregate `blockquote` block, nested paragraph blocks, or
  both with `include_containers=True`?
- Should list item `text` include the Markdown bullet/number marker in `text`, or should
  raw source text preserve the marker while the analysis text strips it?
- Should footnote definitions be `footnote` metadata blocks, text blocks, or both?
- For non-text blocks, should word/token tallies default to raw Markdown source,
  extracted plaintext, or zero unless explicitly included?
- Should section tallies include descendant subsections by default, or only direct child
  blocks?
- If PR #7 lands `BlockType`, should `MarkdownBlockKind` keep a separate name for
  precision, or should the richer API eventually consolidate on one enum?

## References

- PR #7: `https://github.com/jlevy/chopdiff/pull/7`
- `docs/project/specs/active/plan-2026-05-26-robustness-hardening.md`
- `docs/project/review/senior-engineering-review-chopdiff-pre-v0.3.0.md`
- `SUPPLY-CHAIN-SECURITY.md`
- Marko local version inspected: 2.2.2
- Marko modules inspected:
  - `marko.parser.Parser`
  - `marko.source.Source`
  - `marko.block`
  - `marko.ext.gfm.elements`
