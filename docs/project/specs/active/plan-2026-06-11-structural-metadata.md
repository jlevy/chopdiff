# Feature: Typed Structural Metadata and Markdown-Layer Completion

**Date:** 2026-06-11 (last updated 2026-06-11)

**Author:** Joshua Levy

**Status:** Partially implemented (additive surface landed; see Implementation Status).

> **Implementation Status (2026-06-11).** Landed on branch `claude/eager-hawking-nyy2zz`
> (atop the FlexDoc Stage-1 extraction, so the files below now live under `src/flexdoc/`,
> not `src/chopdiff/`):
>
> - ✔︎ **Typed block metadata (#18/#19/#20).** `flexdoc/docs/block_info.py`
>   (`CodeInfo`/`TableInfo`/`ListInfo` + extractors, inline tests); carried on `Block`;
>   flattened into markdown node `attrs`; `Paragraph.code_info`/`.table_info`/`.list_info`.
> - ✔︎ **`NodeKind.footnote_ref` (#21).** Added to `collect.INLINE_KINDS`; recognized in
>   `node_table._build_inline_nodes` (fixes the silent drop); `tests/docs/test_footnote_ref.py`.
> - ✔︎ **`block_type_counts()` removal (breaking).** Removed from `TextDoc`/`Section`;
>   callers/tests/examples migrated to `Counter(b.type for b in ...blocks())`; `CHANGELOG.md`
>   records the migration.
> - ✔︎ **`read_time.py` salvage.** `flexdoc/util/read_time.py` (`format_read_time`, with its
>   inline tests) recovered from the abandoned branch and exported from `flexdoc.util`;
>   depends only on `prettyfmt.fmt_timedelta` (already available).
> - ‼︎ **Deferred for review** (not yet implemented): the frontmatter isolation (#22; reworks
>   `from_text`'s span model, higher regression risk) and the `docs/textdoc-spec.md` /
>   `TODO.md` updates. Checkboxes below are unchanged; this banner is the source of truth for
>   what landed.

## Overview

Five downstream requests from [pprose](https://github.com/jlevy/practical-prose)
(chopdiff issues [#18](https://github.com/jlevy/chopdiff/issues/18)–[#22](https://github.com/jlevy/chopdiff/issues/22),
filed after the 0.3.1 upgrade) all ask the document model for typed structural metadata it
does not yet expose: per-code-block language and line count, per-table dimensions and
alignments, per-list ordered/start/depth/item-count, a typed footnote-reference inline
kind, and isolation of leading YAML frontmatter. None is blocking — pprose has source-text
or regex workarounds for each — but together they are not a grab bag: they are the
**markdown layer's typed-attribute surface reaching completeness**, plus one missing
document-level region (frontmatter).

This plan lands them as a **model-correct increment, not a convenience patch**. The
metadata's source of truth is the markdown-layer node's `attrs` (so it flows into
`collect()` and `DocGraph` for free), surfaced through typed accessors on the structural
`Block`, with thin delegating conveniences on `Paragraph` for the editing-view callers the
issues were filed against. Extraction is **parser-authoritative** throughout (marko element
attributes), consistent with `block_types.py`'s "the parser decides, no regex" rule.

The increment is deliberately shaped to sit on the **durable surface** the model is being
moved toward as a standalone document-model package (working name *FlexDoc*): the node
table, `Block`, `collect()`, and `DocGraph`, not the density-dependent blank-line editing
view. The package extraction itself is a separate design doc; this plan finalizes the
markdown and document layers it will be built around.

## Goals

- **Complete the markdown layer's typed attributes (P7).** Every block kind carries its full
  parser-derived metadata in node `attrs`: code (`language`, `line_count`), table (`rows`,
  `cols`, `cells`, `alignments`), list (existing `ordered`/`tight` plus `start`, `max_depth`,
  `item_count`).
- **Complete the inline kind taxonomy (P7).** Add `NodeKind.footnote_ref` so footnote
  references come from the same typed inline walk as links / code spans / images, fixing the
  current silent drop.
- **Recognize frontmatter as a first-class non-content region.** `from_text` isolates a
  leading YAML frontmatter block; it is excluded from `paragraphs`, structural views, and
  prose counts, and exposed verbatim via `TextDoc.frontmatter`.
- **Expose the metadata as typed structs** (`CodeInfo` / `TableInfo` / `ListInfo`), computed
  once and shared by the structural `Block` path and the `Paragraph` editing-view path.
- **Keep one source of truth (P12, P15).** Compute from the existing shared marko parse; no
  extra parse, no stored counts that can drift — `attrs` are per-element parse facts,
  re-derivable from the node's own span/subtree.

## Non-Goals

- No new query mechanism. Typed per-element accessors are **attributes, not rollups**; the
  one query primitive stays `collect()` (DR-4). See Resolved Decisions.
- No `DocGraph/v0.1` schema-shape change. `attrs` is an open map; new keys are additive
  within the existing schema (matches the doc-model-refinements non-goal).
- No synthetic/annotation layer work, no cross-layer edits, no `SpanRef` fuzzy re-anchoring
  — those remain later phases of the unified-document-model plan.
- No package extraction in this plan. Folding `divs/` in as the synthetic layer and splitting
  out the FlexDoc package are separate, subsequent work; this plan only ensures the surface is
  the right one to extract.
- No parsed-frontmatter API (a metadata `dict`) or document-layer frontmatter node in v1; the
  raw block plus exclusion is the v1 floor, with a clean path to both (Open Questions).

## Background

Where the model is after v0.3.1 (released; see `CHANGELOG.md`): `TextDoc` is block-aware
(`blocks()` structural tree with exact spans), section-aware, link-aware, and projects a
layer-tagged node table, the `base_blocks()` partition, `collect()`, and the `DocGraph`
Pydantic schema. The design of record is `docs/textdoc-spec.md`; principles are cited as
P1–P18 there.

The node table already attaches typed `attrs` to markdown-layer nodes — heading `level`,
list `tight`/`ordered`, link `url`/`title`, image `url`/`text`, code-span `content`,
inline-HTML `tag`. The five requests fill the gaps in exactly that surface. Confirmed
against the live parser (marko via flowmark 0.7.1):

- **Code (#18):** `FencedCode.lang` is the info-string language (`""` for an indented
  `CodeBlock` → `None`); the fenced body is its `RawText` child.
- **List (#20):** `List.ordered`, `List.start` (e.g. `3` for `3.`), `List.tight` are on the
  element; `item_count` and `max_depth` come from the structural subtree.
- **Table (#19):** `Table.num_of_cols` gives columns; each cell's `.align` is
  `"left"/"center"/"right"` (`None` when undefined); rows come from `head` + body rows.
- **Footnote ref (#21):** marko parses `[^1]` as a `FootnoteRef` inline element, **but**
  `flowmark.atomic_spans.iter_atomic_spans` tags `[^1]` as a `markdown_link` atomic. In
  `node_table._build_inline_nodes` a `markdown_link` that `doc.links()` did not resolve and
  is not an image is **skipped**, so footnote references are currently *silently dropped*
  from the node table. This is both the bug and the fix site.
- **Frontmatter (#22):** chopdiff already depends on `frontmatter-format`, which exposes
  `fmf_has_frontmatter`, `fmf_read_frontmatter_raw`, and `fmf_strip_frontmatter`; `from_text`
  currently treats a leading `---` block as ordinary content, so it leaks into `paragraphs`
  and prose counts.

Two adjacent items ride along because they share the same surface and release window:

- The v0.3.1 `TextDoc.block_type_counts()` / `Section.block_type_counts()` accessors are
  already documented as **superseded by `collect()`** (`textdoc-spec.md` §9) and slated for
  removal "in the next minor." This plan removes them so downstream migrates once, alongside
  the new `attrs`.
- `src/chopdiff/util/read_time.py` is an orphaned but useful util stranded on the abandoned
  `feature/extend-chopdiff-section-iteration` branch (whose `SectionDoc`/`FlexDoc` runtime
  models are an explicit non-goal, `textdoc-spec.md` §13). It is salvaged here as a small
  additive util.

## Design

### Approach

One pure extraction module, two consumers, parser-authoritative throughout.

- **`src/chopdiff/docs/block_info.py`** (new): the typed structs and the pure extractors that
  map a marko element to them. The extractors are the single place that knows how to read a
  language/dimension/list fact off the parse.
- **Structural path (source of truth):** `block_tree._blocks_from` already holds the marko
  element when it builds each `Block`; it computes the typed info there and stores it on the
  `Block` (the way `tight` is already carried). `node_table._build_markdown_nodes` flattens
  it into the markdown node's `attrs`, so `collect()` and `DocGraph` see it with no extra
  work.
- **Editing-view path (convenience):** `Paragraph._block_info` already parses
  `original_text` and grabs the first element; it reuses the same extractors on that element,
  so `Paragraph.code_info` etc. are self-contained (work on a standalone paragraph) and add
  **no extra parse**.

Because both call sites already have a marko element in hand, the extraction is shared and
neither path re-parses. The structural `Block`/node path is the **correct, density-invariant**
home (the markdown layer); the `Paragraph` path is the convenience the issues asked for,
carrying the same density caveat already documented for `Paragraph.block_type` (a loose list
is one block per item; a blank-line-split code fence is several blocks). That caveat is
restated on the new `Paragraph` accessors.

### Components

| Area | Files |
| --- | --- |
| Typed structs + extractors | `src/chopdiff/docs/block_info.py` (new), `tests/docs/test_block_info.py` (new) |
| Structural carrier | `src/chopdiff/docs/block_tree.py` (`Block` gains typed info + accessors) |
| Node attrs (DocGraph) | `src/chopdiff/docs/node_table.py` (`_build_markdown_nodes`, `_build_inline_nodes`) |
| Inline taxonomy | `src/chopdiff/docs/node.py` (`NodeKind.footnote_ref`), `src/chopdiff/docs/collect.py` (`INLINE_KINDS`) |
| Editing-view convenience | `src/chopdiff/docs/text_doc.py` (`Paragraph._block_info`, accessors; `TextDoc.frontmatter`; `from_text`) |
| `block_type_counts()` removal | `src/chopdiff/docs/text_doc.py`, callers, tests, examples |
| Read-time util | `src/chopdiff/util/read_time.py` (salvaged) |
| Docs | `docs/textdoc-spec.md`, `CHANGELOG.md`, `TODO.md` |

### API Changes

**New typed structs (`block_info.py`), frozen dataclasses:**

```python
Alignment = Literal["left", "center", "right"] | None

@dataclass(frozen=True)
class CodeInfo:
    language: str | None   # fenced info-string first token; None for indented code
    line_count: int        # body lines, excluding the fence lines

@dataclass(frozen=True)
class TableInfo:
    rows: int              # total rows, including the header row
    cols: int              # columns (marko Table.num_of_cols)
    cells: int             # rows * cols
    alignments: list[Alignment]   # per column, length == cols

@dataclass(frozen=True)
class ListInfo:
    ordered: bool
    start: int | None      # List.start when ordered, else None
    max_depth: int         # 1 = flat list; 2 = one level of nested sublist; ...
    item_count: int        # direct list_item children
```

**New pure extractors (`block_info.py`):** `code_info_for(element) -> CodeInfo | None`,
`table_info_for(element) -> TableInfo | None`, `list_info_for(element) -> ListInfo | None`
(each returns `None` when the element is not of that kind).

**Structural accessors (primary, density-invariant):**

```python
Block.code_info  -> CodeInfo | None    # non-None iff type == code
Block.table_info -> TableInfo | None   # non-None iff type == table
Block.list_info  -> ListInfo | None    # non-None iff type in {list, ordered_list}
```

**Editing-view conveniences (delegating; documented density caveat):**

```python
Paragraph.code_info / .table_info / .list_info   # same return types
```

(The exact flat names from #18 — `code_language` / `code_line_count` — are available as
`Paragraph.code_info.language` / `.line_count`; see Open Questions on whether to also add the
flat aliases pprose literally requested.)

**Node `attrs` (markdown layer; flow into `DocGraph` automatically):**

- code node: `language`, `line_count`
- table node: `rows`, `cols`, `cells`, `alignments`
- list node: existing `ordered`, `tight` plus `start`, `max_depth`, `item_count`
- footnote-ref node: `label`

**Inline taxonomy:** `NodeKind.footnote_ref` added; added to `collect.INLINE_KINDS` so
`collect(kinds={NodeKind.footnote_ref})` implies `inline=True` like the other inline kinds.

**Frontmatter:**

```python
TextDoc.frontmatter -> str | None   # verbatim leading YAML block, fences included; None if absent
```

`from_text` isolates the block; it is excluded from `paragraphs`, `blocks()`, `sections()`,
the node table, and every size/prose count. `source_text` retains the full original (so it
round-trips), spans stay absolute, and the body parses exactly as if the frontmatter were
absent. Invariant preserved: `source_text[unit.span[0]:unit.span[1]] == unit.original_text`.

**Removed (breaking):** `TextDoc.block_type_counts()` and `Section.block_type_counts()`.
Migration: `Counter(b.type for b in doc.blocks())`, or
`Counter(n.kind for n in doc.collect(recursive=True, layer={Layer.markdown}))`.

**Added (util):** `chopdiff.util.read_time.format_read_time(...)`.

## Implementation Plan

### Phase 1: Typed block metadata + surface consolidation

The bulk: #18 / #19 / #20, plus the two adjacent cleanups that share the release.

- [ ] Add `block_info.py`: `CodeInfo` / `TableInfo` / `ListInfo` and the pure extractors,
  reading marko attributes (`FencedCode.lang`, `Table.num_of_cols` + cell `.align`,
  `List.ordered`/`.start`/subtree). Inline tests under a `## Tests` section for the
  extractors over fenced/indented code, ordered/unordered/nested lists, and tables with
  mixed alignments.
- [ ] Carry the info on `Block` (computed in `block_tree._blocks_from` where the element is in
  hand) and expose `Block.code_info` / `.table_info` / `.list_info`.
- [ ] Populate markdown-node `attrs` from the block info in
  `node_table._build_markdown_nodes` (additive keys; existing `tight`/`ordered` unchanged).
- [ ] Reuse the extractors in `Paragraph._block_info`; add `Paragraph.code_info` /
  `.table_info` / `.list_info` with the density caveat in their docstrings.
- [ ] Remove `TextDoc.block_type_counts()` / `Section.block_type_counts()`; migrate internal
  callers/tests/examples to `collect()` / `blocks()`; record the migration in `CHANGELOG.md`.
- [ ] Salvage `src/chopdiff/util/read_time.py` (with its inline tests) from the abandoned
  branch; confirm its `prettyfmt.fmt_timedelta` dependency is already satisfied.
- [ ] Update `docs/textdoc-spec.md` §5 (block-type model: per-kind typed `attrs`) and §9
  (note typed attrs are element attributes, not rollups; `block_type_counts()` removed);
  refresh the stale `TODO.md` status (v0.3.1 is released).
- [ ] `make lint` and `make test` clean.

### Phase 2: Inline + document-region completion

Independent of Phase 1: #21 and #22.

- [ ] Add `NodeKind.footnote_ref` and include it in `collect.INLINE_KINDS`.
- [ ] In `node_table._build_inline_nodes`, recognize footnote-reference atomics (a
  `markdown_link` atomic whose text starts `[^` and is not a `:`-suffixed definition); emit a
  `footnote_ref` node with exact span and `attrs={"label": ...}`. Add tests: a `[^1]`
  reference is collected via `collect(kinds={NodeKind.footnote_ref})` with the right span and
  label, and footnote *definitions* (`[^1]:`) are not mistaken for references.
- [ ] In `TextDoc.from_text`, detect and isolate a leading YAML frontmatter block via
  `frontmatter-format`; store it; build `paragraphs` and the structural parse over the body
  (shifting spans by the content offset) so no paragraph/block/section/node originates inside
  the frontmatter region. Add `TextDoc.frontmatter`.
- [ ] Tests: a document with frontmatter excludes it from `paragraphs`, `blocks()`,
  `sections()`, the node table, and `size(...)`; `frontmatter` returns the verbatim block;
  the span/round-trip invariant holds; a document without frontmatter is unchanged
  (`frontmatter is None`).
- [ ] Update `docs/textdoc-spec.md` (inline kinds include `footnote_ref`; a short
  frontmatter note) and `CHANGELOG.md`.
- [ ] `make lint` and `make test` clean.

## Testing Strategy

- Extractors are unit-tested directly over small marko parses (Phase 1 inline tests): fenced
  vs indented code (language `None`, correct `line_count`), ordered list with `start`,
  nested lists (`max_depth`, `item_count`), tables with left/center/right/default columns.
- Structural-vs-editing parity: for a tight single-block list/table/code, `Block.*_info` and
  the covering `Paragraph.*_info` agree; for a loose list, the `Block` view is whole-list and
  the `Paragraph` view is per-item (asserts the documented caveat, not a bug).
- Node attrs / DocGraph: the new keys appear on the right nodes and serialize; `collect()`
  over `kinds` returns nodes carrying them.
- footnote_ref: collected with exact span and label; definitions excluded; a footnote ref no
  longer silently dropped (regression test for the current behavior).
- frontmatter: exclusion across all views, verbatim `frontmatter`, preserved span/round-trip
  invariant, and the no-frontmatter path unchanged.
- `block_type_counts()` removal: no remaining references in `src/`, `tests/`, or `examples/`;
  migration snippet in the changelog verified to produce the same tallies.
- `make lint` and `make test` clean after each phase.

## Rollout Plan

- Two phases, each independently shippable and additive except the `block_type_counts()`
  removal.
- The removal is the one breaking change → **minor version bump** under the pre-1.0 policy;
  call it out in `CHANGELOG.md` under breaking changes with the migration. Everything else is
  additive (`attrs` keys, `NodeKind` member, `frontmatter` property, typed accessors, the
  read-time util).
- Notify pprose: it can drop its source-text/regex workarounds for #18–#22 and use the typed
  accessors / node attrs; the frontmatter detect-and-skip becomes `TextDoc.frontmatter`.

## Resolved Decisions

- **Structural-first placement (not the literal `Paragraph.X` patch).** The metadata's source
  of truth is the markdown-layer node `attrs` + the structural `Block`; `Paragraph` gets thin
  delegating conveniences. Rationale: the editing view is density-dependent (the issues' own
  caveats flag tables/code/loose-lists), and the durable surface for the forthcoming FlexDoc
  package is the node table / `Block` / `collect()` / `DocGraph`. Landing on that surface
  makes the features a model increment, not a second surface to deprecate. (Confirmed with the
  maintainer, 2026-06-11.)
- **Typed structs, not loose attrs-only accessors.** `CodeInfo` / `TableInfo` / `ListInfo`
  give a self-describing surface fit for a standalone package and match the structs #19/#20
  already proposed. The flat `attrs` keys still exist for `collect()`/`DocGraph` consumers.
- **Typed per-element accessors are consistent with "mechanism over menu" (DR-4/P4).** They
  are element **attributes** (like `heading_level()`, `List.ordered`, `Link.url`), not
  per-kind **rollups**. The objection DR-4 forbids is blessed aggregate queries
  (`tables()`/`code_blocks()`); `collect()` remains the only query mechanism. Recorded so the
  distinction is explicit.
- **Parser-authoritative extraction.** All facts come from marko element attributes, never a
  regex over source text, matching `block_types.py`'s rule. The footnote-ref span comes from
  flowmark's atomic tokenizer, not a hand-rolled regex.
- **Cleanups ride along.** `block_type_counts()` removal, `read_time.py` salvage, and the
  `TODO.md` refresh are bundled into this release so downstream migrates once. (Confirmed with
  the maintainer, 2026-06-11.)

## Open Questions

- **Flat `Paragraph.code_language` / `code_line_count` aliases?** Issue #18 names them flat,
  while #19/#20 want structs. The canonical surface here is the struct (`code_info.language`);
  thin flat aliases can be added if pprose prefers the literal names. Default: struct only,
  confirm with pprose.
- **`TableInfo.rows` convention.** Defined here as total rows including the header. If pprose
  reports data rows separately, add a `header: bool`/`data_rows` field rather than overload
  `rows`. Confirm against the pprose metric.
- **Frontmatter as more than a raw string.** v1 exposes the verbatim block and excludes it.
  Natural additive extensions (not in v1): a parsed-metadata `dict` via `fmf_read`, and/or a
  first-class `document`-layer (or dedicated metadata-layer) frontmatter node so it is
  addressable by `collect()` and serialized in `DocGraph`. Designed to be additive.

## References

- Downstream issues: chopdiff
  [#18](https://github.com/jlevy/chopdiff/issues/18) (code),
  [#19](https://github.com/jlevy/chopdiff/issues/19) (table),
  [#20](https://github.com/jlevy/chopdiff/issues/20) (list),
  [#21](https://github.com/jlevy/chopdiff/issues/21) (footnote_ref),
  [#22](https://github.com/jlevy/chopdiff/issues/22) (frontmatter).
- Design of record: `docs/textdoc-spec.md` (principles P1–P18; markdown/document layers).
- Unified document model plan: `plan-2026-05-29-unified-document-model.md` (later phases:
  synthetic / annotation layers, cross-layer edits).
- Doc-model refinements (precedent for `attrs` / layer-aware `collect()`):
  `plan-2026-05-31-doc-model-refinements.md`.
- FlexDoc package extraction: [`plan-2026-06-11-flexdoc-extraction.md`](plan-2026-06-11-flexdoc-extraction.md)
  (the standalone document-model package this surface is being shaped toward).

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
