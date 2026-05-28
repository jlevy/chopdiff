# Changelog

All notable changes to chopdiff are documented here. This project uses
[semantic versioning](https://semver.org/); while pre-1.0, breaking changes bump the
**minor** version (see `docs/publishing.md`).

## v0.3.0

This is a cleanup release that hardens the build, makes `TextDoc` source-referenced and
Markdown-block-aware, and removes the mandatory `tiktoken` (network) dependency. It
contains several intentional breaking changes for a cleaner API.

### Breaking changes

- **Token counting is now a dependency-free estimate.** The `tiktoken` dependency is
  removed (along with `requests`/`urllib3` at install time), so chopdiff no longer
  downloads a tokenizer or needs network access to size or summarize a document.
  - `TextUnit.tiktokens` is renamed to `TextUnit.tokens` and now returns a heuristic
    estimate (`chopdiff.util.token_estimate.estimate_tokens`, ~3.8 characters/token,
    a blend of current OpenAI/Anthropic/Google rules of thumb).
  - `chopdiff.util.tiktoken_utils` and `tiktoken_len` are removed. Migrate
    `from chopdiff.util.tiktoken_utils import tiktoken_len` to
    `from chopdiff.util.token_estimate import estimate_tokens`.
  - `size_summary()` reports the estimate as `~N tok`.
  - Exact, provider-keyed token counts (tiktoken/OpenAI, and network-based counters
    for other providers) are planned as opt-in extras in a future release.
- **Character offsets are now an `Offsets` record.** `Paragraph.char_offset` and
  `Sentence.char_offset` (plain ints) are replaced by an `Offsets(doc_offset,
  block_offset)` record on both:
  - `doc_offset` is the absolute offset in the document; `block_offset` is relative to
    the enclosing block (the document for a paragraph, the paragraph for a sentence).
  - `TextDoc.char_offset_in_doc(index)` is removed; use
    `doc.get_sent(index).offsets.doc_offset`.
  - Offsets are now exact references into the unmodified input text (the document is no
    longer stripped during parsing).
- **Paragraph splitting recognizes all blank lines.** Paragraphs split on two or more
  newlines, including blank lines that contain only whitespace; runs of blank lines
  collapse into a single break. Previously only a literal `\n\n` split.
- **Removed the unused `chopdiff` console-script entry point.** chopdiff is a library
  with no CLI; the entry point pointed at a non-existent `main`.

### New features

- **Markdown block-type classification.** `BlockType` (heading, paragraph, list, table,
  code, blockquote, html, footnote, plus `list_item` and `thematic_break`) and
  `Paragraph.block_type`, classified by parsing each block with flowmark's Markdown
  (marko) parser. `TextDoc.iter_blocks(include=, exclude=)` and `TextDoc.filtered(...)`
  iterate or sub-select blocks by type.
- **Exact `[start, end)` spans.** Every `Paragraph` and `Sentence` exposes a
  document-relative `span`; `TextDoc.source_text` is retained so each unit's
  `original_text` round-trips into the source. `TextDoc.block_at_offset(o)` and
  `sentence_at_offset(o)` invert spans.
- **Sections, TOC, and rolled-up size stats.** `TextDoc.sections()` returns a tree of
  `Section`s over the heading hierarchy; `TextDoc.toc()` returns a flat
  `(level, title, span)` list. `Section.size(unit, subtree=True|False)`,
  `Section.size_summary()`, and `TextDoc.section_size_tree(units=…)` roll up sizes per
  section in any `TextUnit`, reusing the existing `size` machinery.
- **Opt-in structural block tree.** `TextDoc.blocks()` returns a `Block(type, span,
  children)` tree that keeps a fenced code block whole even with internal blank lines
  and decomposes a tight list into `list_item`s with nested sublists. Block boundaries
  recognize ATX headings, fenced code, thematic breaks, setext underlines, and
  paragraph→list transitions without requiring blank-line separators.
- **Inline-link rollups + link-aware sentence spans.** `Link(text, url, title, span)`
  via `Paragraph.links()`, `Section.links()`, and `TextDoc.links()` — identity from
  flowmark's `extract_links` (reference links resolve across the whole document), spans
  recovered from `iter_atomic_spans`. The default sentence splitter is now
  `flowmark.atomic_spans.split_sentences_with_spans`, so sentence spans are exact for
  all content and never bisect a link, code span, or autolink.
- **New public exports:** `Block`, `BlockType`, `Link`, `Offsets`, `Section`.

### Dependencies

- Requires `flowmark>=0.7.0` (public inline API: `flowmark.atomic_spans` +
  `flowmark.markdown_ast`). Pulls in `pathspec` transitively; recorded as a reviewed
  first-party cool-off exception in `SUPPLY-CHAIN-SECURITY.md`.

### Infrastructure

- Supply-chain hardening: a 14-day dependency cool-off (`exclude-newer`), a committed
  lockfile, frozen `uv sync --locked` installs in CI, and a `pip-audit` gate. See
  `SUPPLY-CHAIN-SECURITY.md`.
- Upgraded to the simple-modern-uv template v0.2.26 (Python 3.14 in the CI matrix, uv
  0.11.12, basedpyright 1.39.3, docs under `docs/`).
- The release workflow now installs from the committed lockfile (`--locked`) for
  reproducible release builds.

### Full changelog

https://github.com/jlevy/chopdiff/compare/v0.2.6...v0.3.0
