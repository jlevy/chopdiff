# Feature: TextDoc Frontmatter Isolation (#22)

**Date:** 2026-06-11 (last updated 2026-06-11)

**Author:** Joshua Levy

**Status:** Implemented

## Overview

`TextDoc.from_text` currently treats a leading YAML frontmatter block (`---\n…\n---`) as
ordinary content, so it leaks into `paragraphs`, the structural views, the node table,
and every prose/size count.
This feature recognizes frontmatter as a first-class **non-content region**: it is
excluded from every view and count, exposed verbatim via `TextDoc.frontmatter`, while
`source_text` keeps the full original and all spans stay absolute.
This is the last open item of issues #18–#22 (the markdown-layer completion).

## Goals

- A leading YAML frontmatter block is excluded from `paragraphs`/`sentences`,
  `blocks()`, `sections()`, the node table, `base_blocks()`, and all `size(...)` counts.
- `TextDoc.frontmatter -> str | None` returns the verbatim block (delimiters included),
  or `None` when absent.
- `source_text` retains the full original (round-trips); spans stay absolute, so
  `source_text[unit.span[0]:unit.span[1]] == unit.original_text` still holds.
- The body parses to the same structure as if the frontmatter were absent.
- The no-frontmatter path is byte-for-byte unchanged.

## Non-Goals

- No parsed-frontmatter API (a metadata `dict`) and no document-layer frontmatter *node*
  in v1 — the raw block plus exclusion is the floor, with a clean additive path to both
  later.
- Only YAML `---` frontmatter (the `FmStyle.yaml` delimiters).
  HTML/code frontmatter styles are out of scope for v1.

## Background

`frontmatter-format` (already a dependency) is **file-based** — every `fmf_*` function
takes a `pathlib.Path`, so it cannot parse an in-memory string and is unusable in the
`from_text(str)` hot path.
flexdoc therefore detects the block itself at the string level, matching `FmStyle.yaml`
delimiters (opening `---` line, closing `---` line).
This also keeps file I/O out of parsing.

The structural views all derive from the full `source_text`: `_parsed()` parses it,
`_block_list()` is `parse_blocks(source_text, _parsed())`, `base_blocks()` and the node
table’s inline pass (`iter_atomic_spans(source_text)`) scan it.
Because the frontmatter is delimited by `---` lines, marko parses it into blocks
entirely within the leading region and the body blocks are unaffected (a `---` line is a
thematic break / setext rule, never a container that swallows the body).
So the lowest-risk design is **filter the frontmatter region out of the views** rather
than reparse the body and thread an offset through the span model: spans stay absolute
straight from the full parse, and exclusion is a single `span >= content_offset` guard
at each view boundary, regardless of how marko interprets the frontmatter text.

## Design

### Approach

Detect the block once from `source_text`; build the editing view over the body; filter
the frontmatter region out of the structural views.
`frontmatter` and the body offset are pure derivations of the immutable `source_text`
(no new stored state, so copy/pickle are unchanged).

### Components

| Area | Change |
| --- | --- |
| Detection | `flexdoc.docs.frontmatter.split_frontmatter(text) -> tuple[str |
| `TextDoc` derivations | `frontmatter` and `_content_offset()` memoized derivations over `source_text` (= `split_frontmatter(source_text)`). |
| Editing view | `from_text` splits the **body** (`text[content_offset:]`) on blank lines, shifting each paragraph’s `doc_offset` by `content_offset` (absolute spans); `source_text` stays the full `text`. Paragraphs/sentences/`size` then exclude frontmatter for free. |
| Structural views | `_block_list()` drops top-level blocks with `span[0] < content_offset`; `TextDoc.base_blocks()` drops base blocks in the region; `node_table._build_inline_nodes` skips links/atomics starting before `content_offset`. `sections()` and markdown nodes derive from `blocks()`, so they follow automatically. |

### API Changes

- **Added:** `TextDoc.frontmatter -> str | None`;
  `flexdoc.docs.frontmatter.split_frontmatter`.
- No signature changes elsewhere; all exclusions are internal.

## Implementation Plan

One phase, two implementation steps (editing view, then structural views), then docs.

### Phase 1: Frontmatter isolation

- [x] `split_frontmatter` detector + inline tests (with/without frontmatter,
  body-immediately, CRLF, a `---` thematic break that is *not* frontmatter).
- [x] `from_text` isolates the block; `TextDoc.frontmatter` + `_content_offset()`;
  paragraphs built over the body with shifted absolute offsets.
- [x] Filter the frontmatter region from `_block_list()`, `base_blocks()`, and the node
  table’s inline/link pass.
- [x] Tests + `docs/textdoc-spec.md` §8/§3 note and `CHANGELOG.md` (additive).

## Testing Strategy

- Detector unit tests (inline): frontmatter present/absent, body immediately after the
  close, CRLF, and a leading `---` thematic break (no closing `---`) that must **not**
  be treated as frontmatter.
- A document with frontmatter: excluded from `paragraphs`, `blocks()`, `sections()`,
  `node_table()`, `base_blocks()`, and `size(...)`; `frontmatter` returns the verbatim
  block; the span/round-trip invariant holds.
- **Body-equivalence:** `blocks()`/`sections()` of `frontmatter + body` equal those of
  `body` alone (modulo the absolute offset), proving the frontmatter does not perturb
  the body parse.
- No-frontmatter path unchanged (`frontmatter is None`; identical
  paragraphs/blocks/counts).

## Rollout Plan

Additive and behavior-preserving for frontmatter-free documents, so a normal additive
release (`TextDoc.frontmatter` is new surface).
Note it in `CHANGELOG.md` under Unreleased.

## Open Questions

- Parsed-frontmatter `dict` (`fmf`-style) and a first-class document-layer frontmatter
  node are natural additive follow-ups; deferred to keep v1 the minimal floor.

## References

- Issue [#22](https://github.com/jlevy/chopdiff/issues/22).
- Markdown-layer plan (origin of #18–#22):
  [`plan-2026-06-11-structural-metadata.md`](plan-2026-06-11-structural-metadata.md).
- Design of record: [`docs/textdoc-spec.md`](../../../textdoc-spec.md).

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
