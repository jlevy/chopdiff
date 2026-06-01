# Feature: Golden-Document Testing and a Reusable Doc-Model Debug Dumper

**Date:** 2026-05-31 (last updated 2026-05-31)

**Author:** Joshua Levy

**Status:** Implemented

## Overview

chopdiff’s document model is fully deterministic and hermetic (no clock, network, LLM,
or randomness; node ids are a deterministic preorder counter, sha256 and token estimates
are deterministic). That makes it the ideal case for golden testing: no mock modes, no
unstable-field scrubbing.
This plan adds an end-to-end “golden document” test layer — a checked-in corpus of
source documents, each converted by the model and serialized several ways, with the
serializations committed as golden artifacts and compared on every run.

The serializer is built as a **reusable developer tool**, not test-only glue: a public
`chopdiff.docs.debug` dumper that can take any document and emit its model views in
clean standard formats.
Source documents are **Markdown with YAML frontmatter** (the frontmatter carries the
test’s options); golden outputs are **pure, deterministic YAML**. We reuse
`frontmatter-format` (first-party `jlevy` package, like `strif`/`flowmark`) for both the
frontmatter I/O and the clean YAML formatting rather than reinventing either.

The approach follows the golden-testing guideline’s transparent-box principle (capture
broad state, not narrow asserts) plus layered invariant assertions for the model’s hard
guarantees (cover, exact spans, round-trip, cross-serialization consistency).

## Goals

- **A reusable debug dumper (public).** `chopdiff.docs.debug` turns any `TextDoc` /
  `DocGraph` into clean, standard-format views (a multi-view report, the DocGraph, the
  reassembled source) usable from a REPL, a script, or the test harness.
- **Clean YAML for DocGraph.** A deterministic, readable YAML serialization of
  `DocGraph` alongside the existing JSON, via `frontmatter-format`’s `to_yaml_string`
  (block style, key-sorted, `|` block scalars for multi-line text).
- **A checked-in golden corpus.** A small set of representative Markdown+frontmatter
  source documents and their golden YAML serializations, reviewed and committed with
  code.
- **Transparent-box coverage + layered invariants.** One readable artifact per document
  shows every projection at once; targeted assertions enforce the model’s invariants
  regardless of golden match.
- **Reuse, don’t reinvent.** Adopt `frontmatter-format` for frontmatter parsing and
  clean YAML.

## Non-Goals

- No CLI / tryscript console-golden tests (chopdiff is a library, not a CLI).
- No mock-mode or unstable-field scrubbing machinery (not needed; the model is
  hermetic).
- Not a replacement for the focused unit tests — the golden corpus is the end-to-end
  net; targeted invariant tests stay as the assertion layer.
- No change to the `DocGraph/v0.1` schema; YAML is a second serialization of the same
  model, not a new contract.

## Background

- A prototype dumper (run during review) confirmed the model serializes
  deterministically and that one artifact can show source stats, the base-block
  partition with a live cover check, TOC, the full node table (all layers), links by
  section, SpanRef round-trips, and the DocGraph — all readable in well under the
  golden-size budget.
- `frontmatter-format` exposes `fmf_read` / `fmf_write(style=FmStyle.yaml)` / `Metadata`
  for Markdown-with-frontmatter, and `to_yaml_string(value, key_sort=…)` / `dump_yaml`
  (ruamel-backed) that already emit block-style, None-suppressed, key-sortable YAML with
  `|` block scalars for multi-line strings — exactly the clean deterministic YAML we
  want. It is MIT, first-party, `requires-python >=3.10`, and brings `ruamel.yaml`.

## Design

### Components

1. **`chopdiff.docs.debug` (public dumper).** Pure functions over public API:
   - `doc_report(doc: TextDoc) -> str` — the multi-view report as clean YAML: source
     metadata (sha, length, size summary), base-block partition with `cover_ok`,
     sections / TOC with rolled-up sizes, the full node table (id, layer, kind, span,
     parent, key attrs), links grouped by section, and SpanRef round-trips for located
     inline nodes.
   - `doc_graph_yaml(doc: TextDoc) -> str` — the document’s default DocGraph as clean
     YAML (a convenience over `doc.graph().to_yaml()`).
   - `dump_views(doc: TextDoc, dest: Path) -> None` — write the standard artifact set
     (`report.yaml`, `docgraph.yaml`, `reassembled.md`) for a document.
     The dumper builds plain dicts and serializes with
     `frontmatter_format.to_yaml_string` under a fixed key order, so output is
     deterministic and diff-friendly.
2. **DocGraph → YAML.** A `DocGraph.to_yaml()` (or `doc_graph_yaml`) that dumps the
   pydantic model via `to_yaml_string` with a stable key sort.
   JSON (`model_dump_json`) stays the canonical wire form; YAML is the human/golden
   form.
3. **Corpus.** `tests/golden/documents/*.md`, each Markdown with a YAML frontmatter
   block carrying the test’s name, a description, and options (e.g.
   `item_partition_depth`, which `include` layers / `detail` flags to dump).
   ~6 documents covering: kitchen-sink (headings, nested + ordered lists,
   blockquote-with-table, inline + image links, code span); deep-nested list (base-block
   depth + cover); tight-vs-loose list pair (density invariance); footnotes + reference
   links (`span=None` handling); inline HTML / `<div>` (synthetic-layer precursor);
   malformed Markdown (P17 tolerance); a unicode/emoji doc (code-point offsets).
4. **Golden artifacts.**
   `tests/golden/expected/<doc>/{report.yaml,docgraph.yaml, reassembled.md}` — sharded
   per document (guideline: many small artifacts), pure YAML + the reassembled Markdown.
5. **Harness.** `tests/golden/test_golden_docs.py`: discover each source doc, read its
   frontmatter for options via `fmf_read`, build the `TextDoc`, render the artifacts,
   compare to the goldens, and fail on diff.
   `UPDATE_GOLDEN=1` rewrites the goldens.
6. **Layered invariant assertions** (run every time, independent of golden match):
   base-block cover over all non-whitespace source (P13); `source_text[s:e] == quote`
   for every source-backed node/sentence (P6); node ids unique and every
   `parent`/`children` ref resolves; DocGraph child refs valid; `reassemble()`
   round-trips at the Markdown-object level (P11); and a cross-serialization check that
   the DocGraph node spans equal the report’s node spans (the copies agree).
7. **Docs.** `tests/golden/README.md` documenting the corpus, the artifact set, and the
   update/review workflow.

### Dependency

`frontmatter-format` is adopted for frontmatter I/O and clean YAML (brings
`ruamel.yaml`). Adoption follows `SUPPLY-CHAIN-SECURITY.md` (add an `exclude-newer`
cool-off entry, commit the lockfile, install frozen).
It is first-party (`jlevy`), matching the existing `strif` / `flowmark` review pattern.
See Open Decisions for runtime-vs-extra placement.

### API Changes

- **Additive (public):** new module `chopdiff.docs.debug` (`doc_report`,
  `doc_graph_yaml`, `dump_views`) and a `DocGraph.to_yaml()` method.
  No existing surface changes.

## Implementation Plan

### Phase 1: Reusable dumper + DocGraph YAML

- [x] Adopt `frontmatter-format` per `SUPPLY-CHAIN-SECURITY.md` (cool-off entry,
  lockfile).
- [x] Add `DocGraph.to_yaml()` (clean, key-sorted YAML via `to_yaml_string`); keep JSON.
- [x] Build `chopdiff.docs.debug` with `doc_report`, `doc_graph_yaml`, `dump_views`,
  emitting deterministic clean YAML; export it.
- [x] A few inline/unit checks that the dumper is deterministic (same input → identical
  bytes) and that YAML re-parses to the expected structure.

### Phase 2: Golden corpus and harness

- [x] Create `tests/golden/documents/*.md` (Markdown + frontmatter) covering the cases
  above.
- [x] Implement `tests/golden/test_golden_docs.py`: per-doc render + compare,
  `UPDATE_GOLDEN` rewrite, and the layered invariant assertions.
- [x] Generate and review the initial golden artifacts; commit them.
- [x] Add `tests/golden/README.md` (corpus + update/review workflow).
- [x] Confirm `make lint` and `make test` clean and that an intentional model change
  shows up as a reviewable golden diff.

## Testing Strategy

- The corpus + golden compare is the end-to-end transparent-box layer; the invariant
  assertions are the targeted layer (guideline principle 7), so a semantic violation
  fails even if goldens are blindly regenerated.
- Determinism is verified by re-rendering and byte-comparing; no scrubbing needed.
- Keep total golden YAML well under the size budget (small docs, sharded artifacts).

## Rollout Plan

- Additive: a new public module, a new method, a new test tree, one new (first-party)
  dependency. Land Phase 1 then Phase 2; each is independently shippable.

## Open Decisions

- **`frontmatter-format` placement — runtime dependency vs optional `[debug]` extra.**
  Recommended: **runtime dependency**, since the dumper is meant to be reused and
  `frontmatter-format` is small and first-party.
  Alternative: keep core lean by gating the YAML/dumper behind a `chopdiff[debug]` extra
  (+ dev dependency for the harness) with a clear ImportError when absent.
  Decide before Phase 1.
- **Artifact granularity** — sharded `report.yaml` / `docgraph.yaml` / `reassembled.md`
  (recommended, per guideline) vs one combined report.
  Sharded keeps each diff focused.

## References

- Golden-testing guideline: `tbd guidelines golden-testing-guidelines`
- Doc-model design of record: `docs/textdoc-spec.md`
- Doc-model refinements plan: `plan-2026-05-31-doc-model-refinements.md`
- `frontmatter-format`: https://github.com/jlevy/frontmatter-format (source in `attic/`)
- Supply-chain policy: `SUPPLY-CHAIN-SECURITY.md`

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
