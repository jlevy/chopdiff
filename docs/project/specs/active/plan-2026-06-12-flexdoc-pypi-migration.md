---
title: Migrate chopdiff to Published flexdoc 0.1.0
description: Rewire chopdiff onto the PyPI flexdoc package, delete the in-repo copy, apply the FlexDoc rename, and ship the breaking release
author: Joshua Levy (github.com/jlevy) with LLM assistance
---
# Feature: Migrate chopdiff to Published flexdoc 0.1.0

**Date:** 2026-06-12

**Author:** Joshua Levy (via agent session)

**Status:** Implemented (runbook handed off in
[issue #27](https://github.com/jlevy/chopdiff/issues/27))

## Overview

flexdoc 0.1.0 is live on PyPI (published 2026-06-12 via trusted publishing).
It is the document model extracted from chopdiff Stage 1 (`src/flexdoc/` in this repo),
refined pre-publish with intentional hard cuts.
This plan rewires chopdiff to depend on `flexdoc` from PyPI, deletes the in-repo copy,
applies the `TextDoc` to `FlexDoc` rename, and ships chopdiff’s one intended breaking
release, tested end to end.

## Goals

- chopdiff depends on `flexdoc>=0.1.0` from PyPI; no `flexdoc` import root ships in the
  chopdiff wheel.
- All moved code (`src/flexdoc/`, its tests, golden fixtures, and flexdoc-only examples)
  is deleted from this repo.
- All `TextDoc` references in code become `FlexDoc`; module-path imports use
  `flexdoc.docs.flex_doc` or, preferably, the root `from flexdoc import FlexDoc`.
- CI (including the `wheel-smoke` job) is green against the published package.
- CHANGELOG and docs describe the breaking change with a downstream migration note.
- Any flexdoc 0.1.0 problems discovered during integration are collected in an upstream
  review doc (`docs/project/review/`) rather than worked around locally.

## Non-Goals

- No compatibility aliases or shims anywhere.
  The break is intentional and the maintainer has explicitly rejected back-compat
  scaffolding.
- No behavior changes to chopdiff’s own diff/transform/divs layer.
- No fixes to flexdoc itself in this repo; upstream issues are recorded for the flexdoc
  repo instead.

## Background

The flexdoc extraction was staged in
`docs/project/specs/active/plan-2026-06-11-flexdoc-extraction.md`: Stage 1 split the
document layer into a second in-repo import root (`src/flexdoc/`) shipped inside the
chopdiff wheel. The extraction session then moved that code to `jlevy/flexdoc`, refined
it (class rename `TextDoc` to `FlexDoc`, editing-view method renames, keyword-only
`collect()`), and published 0.1.0. Parse behavior is identical (golden fixtures
byte-for-byte); only Python surfaces changed.
Design of record: `docs/flexdoc-spec.md` in jlevy/flexdoc.

What changed in published flexdoc vs.
our in-repo copy, and what it means here:

1. `TextDoc` is renamed `FlexDoc`; module `flexdoc.docs.text_doc` is now
   `flexdoc.docs.flex_doc`. Root exports: `FlexDoc`, `DocGraph`, `Detail`, `SpanRef`,
   `BlockType`, `NodeKind`, `Layer`, `TextUnit`.
2. Editing-view method renames (`block_at_offset` to `paragraph_at_offset`,
   `iter_blocks` to `iter_paragraphs`, `Section.own_blocks`/`subtree_blocks` to
   `own_paragraphs`/`subtree_paragraphs`): chopdiff `src/` and `examples/` use none of
   these; only docstrings/comments may mention them.
3. `collect()` is keyword-only and the `scope`/`contains` aliases are gone: chopdiff src
   does not use them.
4. `_block_links` is public `block_links` in `flexdoc.docs.links`: chopdiff src did not
   import it.
5. Everything chopdiff actually imports (`TextDoc` to `FlexDoc`, `TextUnit`,
   `BlockType`, `Block`, `Section`, `Paragraph`, `Splitter`,
   `default_sentence_splitter`, wordtok constants/functions, `TokenMapping`, diff types,
   `search_tokens`, html helpers, `TimestampExtractor`, `ContentNotFound`) exists in
   flexdoc 0.1.0 under the same names, via `flexdoc.docs` / `flexdoc.html`.

## Design

### Approach

Execute the migration as a strict sequence: unblock dependency resolution (supply-chain
exception for the hours-old package), rewire `pyproject.toml`, delete the moved code,
apply the rename mechanically with repren, fix CI, update CHANGELOG/docs, then run the
acceptance gate.
chopdiff’s remaining test suite (divs/transforms/util) exercises flexdoc
deeply (sliding windows, diff filters over FlexDoc docs); it passing against the PyPI
package IS the integration test.

### Components

- `pyproject.toml`: dependencies, `exclude-newer-package` exception, wheel targets.
- `SUPPLY-CHAIN-SECURITY.md`: Active Exceptions entry for flexdoc 0.1.0.
- `src/chopdiff/{divs,transforms}`: import-path and class-name updates.
- `tests/{divs,transforms,util}`: kept; `tests/{docs,html,golden}` and
  `tests/test_package_boundary.py`: deleted (moved upstream; the package boundary is now
  structural).
- `examples/`: keep `insert_para_breaks.py` + `gettysberg.txt`; delete the three
  flexdoc-only examples (they ship with flexdoc).
- `.github/workflows/`: `wheel-smoke` job builds/installs only the chopdiff wheel.
- `CHANGELOG.md`, `README.md`, `docs/textdoc-spec.md` (superseded by flexdoc’s spec).

### API Changes

Breaking for downstream users (pre-1.0 minor bump):

- `chopdiff.docs.TextDoc` is now `flexdoc.FlexDoc`.
- `chopdiff.docs|html|util.*` (document-layer modules) are now
  `flexdoc.docs|html|util.*`.
- `collect(scope=, contains=)` is now keyword-only `collect(subtree_of=, within=)`.
- Editing-view renames: `block_at_offset` to `paragraph_at_offset`, `iter_blocks` to
  `iter_paragraphs`, `Section.own_blocks`/`subtree_blocks` to
  `own_paragraphs`/`subtree_paragraphs`.

chopdiff’s own surface (`chopdiff.divs`, `chopdiff.transforms`, `chopdiff.util`) is
unchanged apart from type signatures now referring to `flexdoc.FlexDoc`.

## Implementation Plan

### Phase 1: Dependency rewire

- [x] Supply-chain exception: `[tool.uv.exclude-newer-package]` gets
  `flexdoc = "2026-06-13T00:00:00Z"`; record an Active Exceptions entry in
  `SUPPLY-CHAIN-SECURITY.md` (first-party, same maintainer, directed migration is the
  sign-off; precedent: strif/flowmark entries; note “remove once 0.1.0 clears the
  window”).
- [x] `pyproject.toml`: add `flexdoc>=0.1.0`; remove now flexdoc-only deps (`marko`,
  `cydifflib`, `funlog`, `regex`, `strif`, `frontmatter-format`, `pydantic`,
  `selectolax`); keep `flowmark`, `prettyfmt`, and `extras = ["simplemma"]`; add
  `typing_extensions` (chopdiff imports it directly; it previously arrived via
  pydantic); wheel target back to `packages = ["src/chopdiff"]`.
- [x] `uv lock` (force with `uv lock --upgrade-package flexdoc` if it resolves stale);
  review the lock diff like code.

### Phase 2: Code removal, rename, CI, docs

- [x] Move `test_parsed_div_multi_class_matching` from
  `tests/html/test_html_validation_and_classes.py` into `tests/divs/` (it tests
  `chopdiff.divs.parse_divs`; the rest of the file is flexdoc’s).
- [x]
  `git rm -r src/flexdoc/ tests/docs/ tests/html/ tests/golden/ tests/test_package_boundary.py examples/normalized_form.py examples/doc_structure.py examples/backfill_timestamps.py`.
- [x] Rename mechanically:
  `uvx repren@latest --literal --from TextDoc --to FlexDoc src tests examples`, then
  `--from text_doc --to flex_doc` for module-path imports; prefer
  `from flexdoc import FlexDoc` where files import only the class; clean `__pycache__`
  first and delete repren `.orig` backups after.
- [x] CI: `wheel-smoke` builds/installs only the chopdiff wheel and imports `chopdiff`
  (flexdoc arrives as a dependency); drop the two-import-root assertions; audit job
  keeps `--all-extras`.
- [x] CHANGELOG: breaking-release entry (pre-1.0 minor bump from latest tag) with the
  downstream migration note from API Changes above; point to flexdoc’s CHANGELOG for the
  full list.
- [x] Docs: README/usage say the document model lives in flexdoc (link repo + PyPI);
  replace `docs/textdoc-spec.md` with a short pointer to flexdoc’s
  `docs/flexdoc-spec.md`; leave dated plan/research/review docs as history.

### Phase 3: Acceptance gate and upstream review

- [x] `make install`, `make lint`, `make test`: zero warnings/errors.
- [x] Verify resolution: `uv pip list | grep flexdoc` shows 0.1.0 from PyPI;
  `grep -rn "src/flexdoc" pyproject.toml` empty.
- [x] `uv build --wheel`; isolated-venv smoke: install the chopdiff wheel, then
  `import chopdiff; from chopdiff.transforms import sliding_para_window; from flexdoc import FlexDoc`
  and run a tiny transform end to end.
- [x] Run `examples/insert_para_breaks.py` (skip the LLM call if no API key; verify the
  doc-construction path).
- [x] `grep -rn "TextDoc\|chopdiff.docs\|chopdiff.html" src tests examples`: only
  historical docs may match; code must be clean.
- [x] Assemble any flexdoc 0.1.0 issues found during integration into
  `docs/project/review/flexdoc-0.1.0-integration-review.md` for upstream.
- [ ] PR per repo convention; CI green (6 jobs) before merge; then tag the breaking
  release per `docs/publishing.md`.

## Testing Strategy

The kept suite (`tests/{divs,transforms,util}`) runs against the PyPI flexdoc and
exercises it deeply (sliding windows, diff filters over FlexDoc docs).
The wheel-smoke isolated-venv check proves the published artifact graph works without
the repo checkout. The example script is the end-to-end sanity run.

## Rollout Plan

One PR on `claude/dreamy-mendel-jhy9ad`; merge when CI is green; tag the breaking
release (pre-1.0 minor bump) per `docs/publishing.md`.

## Open Questions

- None blocking; known traps from the upstream session are recorded below.

Known traps (encountered and solved upstream):

- Cool-off + fresh-package interaction: the exception entry and
  `uv lock --upgrade-package flexdoc` are the fixes.
  Ad-hoc `uv pip install flexdoc` checks must run OUTSIDE the repo directory or the
  project cool-off blocks them.
- repren matches `.pyc` files and leaves `.orig` backups: clean `__pycache__` first,
  delete backups after.
- If pyright reports new import-cycle errors after file renames, it is the
  alphabetical-checking-order artifact; cycle suppressions belong in the first-sorted
  file of the chain.

## References

- [Issue #27: migration handoff](https://github.com/jlevy/chopdiff/issues/27)
- `docs/project/specs/active/plan-2026-06-11-flexdoc-extraction.md` (Stage 1; “Step 5”
  there is this runbook)
- flexdoc: <https://github.com/jlevy/flexdoc>, <https://pypi.org/project/flexdoc/>
- `SUPPLY-CHAIN-SECURITY.md`, `docs/publishing.md`

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
