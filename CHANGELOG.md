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
  code, blockquote, html, footnote) and `Paragraph.block_type`, classified by parsing
  each block with flowmark's Markdown (marko) parser. `TextDoc.iter_blocks(include=,
  exclude=)` and `TextDoc.filtered(include=, exclude=)` iterate or sub-select blocks by
  type (e.g. process only paragraphs and list items, skipping headings and tables), and
  aggregate counts such as sentences/words across paragraph blocks.
- **Exact source references.** Paragraph and sentence `Offsets` round-trip into the
  original text; `TextDoc` documents a clear contract for offsets and in-place editing.

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
