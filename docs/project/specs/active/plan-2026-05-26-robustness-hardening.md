# Feature: Robustness Hardening And Regression Coverage

**Date:** 2026-05-26 (last updated 2026-05-26)

**Author:** Codex

**Status:** Draft

## Overview

Harden `chopdiff` for downstream consumers by fixing concrete robustness issues found
in the senior engineering review, adding missing regression tests, and making safe,
clear implementation and documentation improvements before the next release.

The emphasis is correctness and API contract clarity, not new feature expansion.
Existing public behavior should remain compatible where it is already documented and
working. When a fix corrects behavior that was previously undocumented or contradicts
the docs, call out the compatibility risk in release notes.

## Goals

- Fix the concrete P1/P2 robustness bugs identified in
  `docs/review/senior-engineering-review.md`.
- Add focused regression tests for each fixed behavior.
- Make failure behavior explicit and actionable for library users.
- Improve downstream safety around transforms, chunking, offsets, token mapping, and
  HTML helpers.
- Keep fixes conservative: prefer small, testable patches over broad rewrites.
- Preserve the current supply-chain posture and avoid new dependencies unless a human
  explicitly approves them after reviewing `SUPPLY-CHAIN-SECURITY.md`.
- Keep `make lint`, `make test`, `make build`, and the audit gate passing.

## Non-Goals

- Do not add new LLM integrations or higher-level transform features.
- Do not perform a full parser rewrite for Markdown or HTML.
- Do not implement parser-backed Markdown block segmentation here; track that as a
  separate feature spec so robustness fixes can land first.
- Do not silently change major text-normalization semantics without either preserving
  the old behavior or documenting the compatibility impact.
- Do not broaden dependency scope unless a specific fix cannot be done cleanly with the
  current stack.
- Do not create long-term backward-compatibility shims unless the user confirms they
  are necessary.

## Background

The review found that `chopdiff` has a strong core design for LLM-oriented text
transforms, but several implementation details currently undercut the library's
promises around safety and source mapping:

- The package declares a broken `chopdiff` console script.
- `filtered_transform()` enforces `diff_filter` only when windowing is enabled.
- Sub-document APIs alias mutable `Paragraph` and `Sentence` objects, allowing
  transforms to mutate the caller's original document.
- If PR #7 lands first, its new `TextDoc.filtered()` API has the same copy-semantics
  risk unless it is fixed before merge.
- `Sentence.char_offset` is documented as an original-text offset but is currently
  paragraph-relative.
- `TextDoc.from_text()` normalizes input despite README wording that suggests exact
  preservation.
- Div child chunking mixes inclusive and exclusive slice semantics.
- Paragraph windows include only sentence 0 of the ending paragraph.
- `html_find_tag()` mishandles nested self-closing tags of the same name.
- Empty documents fail when boundary tokens are requested.
- `TokenMapping` validates by diff operation count instead of changed token count.
- Several runtime checks use `assert` instead of real exceptions.
- HTML tag generation and parsing have validation gaps.

This plan fixes the safe and clear issues first and records any remaining API-policy
choices explicitly.

## Design

### Approach

Use regression tests as the driver:

1. Add failing tests that capture the review findings.
2. Fix the smallest implementation area that owns each behavior.
3. Replace ambiguous failure modes with clear exceptions or documented behavior.
4. Update docs where the safe fix is contract clarification rather than default
   behavior change.
5. Run full validation after each phase.

The code should continue to follow the project Python rules:

- Use modern Python 3.11+ typing and absolute imports.
- Use `Path` for file paths in examples and tooling.
- Preserve exception causes when wrapping errors.
- Avoid runtime `assert` for public/library validation.
- Keep comments concise and explanatory.
- Add tests that cover behavior and edge cases, not implementation details.

### Components

- Packaging and release:
  - `pyproject.toml`
  - `src/chopdiff/__init__.py`
  - Optional new `src/chopdiff/cli.py`
  - `.github/workflows/publish.yml`
- Document model:
  - `src/chopdiff/docs/text_doc.py`
  - `src/chopdiff/docs/token_diffs.py`
  - `src/chopdiff/docs/token_mapping.py`
  - `src/chopdiff/docs/wordtoks.py`
- Transforms:
  - `src/chopdiff/transforms/sliding_transforms.py`
  - `src/chopdiff/transforms/sliding_windows.py`
  - `src/chopdiff/transforms/window_settings.py`
- Div chunking:
  - `src/chopdiff/divs/chunk_utils.py`
  - `src/chopdiff/divs/text_node.py`
  - `src/chopdiff/divs/parse_divs.py`
- HTML helpers:
  - `src/chopdiff/html/html_in_md.py`
  - `src/chopdiff/html/html_tags.py`
  - `src/chopdiff/html/timestamps.py`
- Examples and docs:
  - `examples/insert_para_breaks.py`
  - `examples/backfill_timestamps.py`
  - `README.md`
  - `docs/development.md`
  - `docs/publishing.md`

### API Changes

- Fix the existing console entry point by either:
  - adding a minimal `chopdiff.cli:main` with help/version behavior, or
  - removing the broken script if the package is intended to stay library-only.
  The safer default is a minimal CLI because the package already publishes the command.
- Make `filtered_transform()` enforce `diff_filter` consistently with and without
  windowing.
- Make subdocument/window APIs avoid accidental mutation of the source document. This
  corrects undocumented behavior and should be noted in release notes.
- Make `Sentence.char_offset` match its documented original-text meaning, or rename and
  document relative-offset behavior if a compatibility decision says not to change it.
- Clarify `TextDoc.from_text()` normalization. Do not silently change the default unless
  tests and docs are updated together. If exact preservation is needed now, add a new
  explicit API rather than overloading implicit behavior.
- Tighten validation in `WindowSettings`, token diff application, token mapping, and
  HTML helpers.

## Implementation Plan

### Phase 1: Correct Release Blockers And Transform/Chunking Bugs

- [ ] Add an installed-command regression test for `uv run chopdiff` or an equivalent
      subprocess smoke test.
- [ ] Fix the broken console script by adding a minimal CLI or removing the entry point.
- [ ] Add tests proving `filtered_transform()` applies `diff_filter` for `None`,
      `WINDOW_NONE`, and normal window settings.
- [ ] Refactor filtering so whole-document and windowed transforms share the same
      enforcement path.
- [ ] Add a regression test proving word-window transforms do not mutate the caller's
      original `TextDoc`.
- [ ] Fix subdocument/window mutation by copying paragraph and sentence objects where a
      returned subdocument may be mutated.
- [ ] If PR #7 has landed, add `TextDoc.filtered()` to the same copy-semantics
      regression tests and fix path.
- [ ] Add multi-sentence paragraph-window tests with a no-op normalizer.
- [ ] Fix `sliding_para_window()` to include full paragraphs.
- [ ] Add div-leading chunking tests with multiple top-level divs.
- [ ] Fix `chunk_children()`/`chunk_generator()` slice semantics and empty-slice size
      behavior.

### Phase 2: Harden Core Contracts And Error Handling

- [ ] Add tests for `Sentence.char_offset` across paragraphs and leading whitespace.
- [ ] Fix sentence offsets to be absolute, or update the API/docs if preserving
      relative offsets is chosen.
- [ ] Add empty-document tests for `as_wordtoks(bof_eof=True)`, `first_index()`, and
      `last_index()`.
- [ ] Define and implement clear empty-document behavior.
- [ ] Add tests proving `TokenMapping` rejects large replacements.
- [ ] Validate `TokenMapping` using changed-token counts or a documented confidence
      score instead of diff operation count.
- [ ] Add tests proving `TokenDiff.apply_to()` rejects same-length but mismatched source
      tokens.
- [ ] Validate consumed source tokens in `TokenDiff.apply_to()`.
- [ ] Replace runtime `assert` checks in public/library validation paths with clear
      exceptions.
- [ ] Add `WindowSettings.__post_init__()` validation while preserving `WINDOW_NONE`.
- [ ] Preserve exception causes in wrapped errors such as
      `TimestampExtractor.extract_preceding()`.

### Phase 3: Harden HTML Helpers, Docs, And Release Workflow

- [ ] Add tests for nested self-closing same-name tags in `html_find_tag()`.
- [ ] Fix same-name self-closing tag handling in balanced tag matching.
- [ ] Add validation tests for invalid HTML tag names, invalid attribute names, and
      class names supplied directly to `tag_with_attrs()`.
- [ ] Validate tag names, attribute names, and class names at the HTML helper boundary.
- [ ] Add or document strict/best-effort behavior for `html_find_tag()` and rewrite
      helpers.
- [ ] Improve class parsing for div helpers where safe: handle multi-class attributes
      and common quote styles.
- [ ] Add tests for empty attribute values in `html_extract_attribute_value()`.
- [ ] Preserve missing versus empty attribute values.
- [ ] Update README and docstrings to distinguish exact preservation from normalized
      parsing.
- [ ] Fix stale docs and typos called out in the review.
- [ ] Update examples to use `Path`; implement or remove the unused `--output` option
      in `examples/insert_para_breaks.py`.
- [ ] Align publish workflow dependency installation with CI by using the committed
      lockfile unless there is a documented reason not to.
- [ ] Run final validation: `make lint`, `make test`, `make build`, and
      `uv run --locked --all-extras --group audit pip-audit`.

## Testing Strategy

Add focused tests rather than broad snapshots:

- CLI smoke test:
  - The installed command exits successfully for `--help` or `--version`.
- Transform tests:
  - Illegal transforms are filtered in no-window and windowed modes.
  - Identity transforms leave original input documents unchanged.
  - Alignment and min-overlap failures produce explicit behavior.
- Text model tests:
  - Offsets are absolute or explicitly documented otherwise.
  - Empty documents have stable behavior.
  - Subdocuments do not mutate parents unless an explicit view API is added.
- Chunking tests:
  - Paragraph and div chunking include all expected content.
  - Empty chunks do not measure as whole-document chunks.
- Diff and mapping tests:
  - `TokenMapping` rejects low-confidence mappings.
  - `TokenDiff.apply_to()` validates source identity.
- HTML tests:
  - Nested self-closing tags of the same name.
  - Invalid tag and attribute names.
  - Empty attribute values.
  - Multi-class div matching.
- Documentation and examples:
  - Existing tests continue to pass.
  - Examples import cleanly or have smoke tests where network credentials are not
    required.

Validation commands:

```shell
make lint
make test
make build
uv run --locked --all-extras --group audit pip-audit
```

## Rollout Plan

- Implement in small commits or beads grouped by subsystem.
- Keep behavior changes covered by tests and documented in release notes.
- Treat offset semantics and default preservation semantics as compatibility-sensitive.
- Do not publish until CI and audit pass on the final branch.
- After implementation, update this spec status and close linked beads.

## Open Questions

- Should the existing `chopdiff` console command become a minimal utility command, or
  should the entry point be removed because this is library-only?
- Should `TextDoc.from_text()` remain a normalizing parser with clearer docs, or should
  exact preservation become the default in a breaking release?
- If `Sentence.char_offset` changes from relative to absolute, should release notes
  treat that as a bug fix or a compatibility-impacting API change?
- Should subdocument views remain available for performance under an explicit
  `view_*` API, or should all public subdocument APIs return independent values?

## References

- `docs/review/senior-engineering-review.md`
- `docs/project/specs/active/plan-2026-05-26-markdown-block-segmentation.md`
- `SUPPLY-CHAIN-SECURITY.md`
- `AGENTS.md`
- tbd guidelines applied:
  - `python-rules`
  - `general-coding-rules`
  - `general-comment-rules`
  - `general-testing-rules`
  - `error-handling-rules`
