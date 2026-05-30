# Feature: Robustness Hardening And Regression Coverage

**Date:** 2026-05-26 (fully re-reviewed and revised 2026-05-29 against current v0.4.0 code)

**Author:** Codex; revised by a fresh senior review

**Status:** **Implemented (Phases 1–3), 2026-05-29.** Re-reviewed against v0.4.0 code,
then implemented TDD: every open finding below now has a regression test and a fix on the
branch (165 tests, lint clean, build green). Pending release. Findings already fixed
before this pass are under "Resolved since the original review". Tracked under epic
`chopdiff-pdu2` (see "Tracking").

## Overview

Harden `chopdiff` for downstream consumers by fixing concrete correctness and API-contract
bugs found in the senior engineering review
([`docs/project/review/senior-engineering-review-chopdiff-pre-v0.3.0.md`](../../review/senior-engineering-review-chopdiff-pre-v0.3.0.md),
with a 2026-05-29 reconciliation appended), adding regression tests, and making failure
behavior explicit. The emphasis is correctness and contract clarity, not new features.

This is the foundation the document-model work builds on (see "Sequencing"), so it should
land first where its fixes touch offsets, sub-document copy semantics, and transform
safety.

## Resolved since the original review

These findings are **fixed in current code** (v0.3.0/v0.4.0 and this branch's work);
re-verified 2026-05-29. They are recorded here so the spec is honest about scope and not
re-done:

- **Broken console script** — `[project.scripts]` was removed; the package is library-only
  (`pyproject.toml` has no scripts; `src/chopdiff/__init__.py` is empty).
- **Sentence offsets not absolute** — offsets are now an `Offsets(doc_offset, block_offset)`
  record with absolute `doc_offset`; `source_text[sent.span] == sent.original_text` holds.
- **`from_text` "exact preservation" doc mismatch** — the docstring and README now state
  the normalization contract honestly (`source_text` is retained for exact spans;
  `reassemble()` is normalized, not byte-for-byte).
- **Publish workflow** installs from the lockfile (`uv sync --all-extras --locked`).
- **Noisy test output** — the `@tally_calls` decorators are gated (`level="warning"`,
  `min_total_runtime=5`), so a normal `uv run pytest` is quiet.

## Goals

- Fix the open correctness/contract bugs verified below; add a focused regression test for
  each.
- Make failure behavior explicit (real exceptions, not `assert`; documented best-effort vs
  strict modes).
- Keep fixes conservative and additive; note any behavior change in release notes.
- Preserve supply-chain posture; no new dependencies without human approval per
  `SUPPLY-CHAIN-SECURITY.md`.
- Keep `make lint`, `make test`, `make build`, and the audit gate green.

## Non-Goals

- No new LLM integrations or transform features.
- No Markdown/HTML parser rewrite.
- No parser-backed block segmentation here (done — shipped in v0.4.0).
- No silent change to text-normalization semantics without tests + release-note callout.
- No long-term backward-compat shims unless explicitly confirmed.

## Sequencing and relationship to other plans

Two active efforts: this hardening spec and
[`plan-2026-05-29-unified-document-model.md`](plan-2026-05-29-unified-document-model.md)
(the `DocGraph` design, gated on its open decisions). Recommended order:

1. **Core hardening first (Phase 1 here).** The unified document model extends `TextDoc`
   and reuses its offsets, sub-document slicing, and transform machinery. Building the
   `DocGraph` projection and its source-grounded `Reference` model on top of
   `sub_doc`/`sub_paras` that alias caller objects, a `filtered_transform` that can skip its
   filter, or chunking that mis-slices would inherit those bugs. These are also outright
   safety/data-loss bugs that should not wait. The doc-model is gated on its open decisions
   anyway, so Phase 1 here fits in that window.
2. **Then the unified document model Phase 1** (recursive node model + rollups), once its
   decisions are settled.
3. **Hardening Phases 2–3 (HTML polish, class matching, API surface) interleave with or
   follow** the doc-model work; they are not prerequisites.

Two compatibility-sensitive questions from the original review are now **answered by the
doc-model direction**, not re-opened here:

- *Exact `from_text` preservation?* No `preserve=True` mode. `from_text` stays normalizing;
  `source_text` is retained for exact spans; byte-for-byte exactness is a `DocGraph`
  concern (source canonical), per the unified plan and `textdoc-spec.md`.
- *Offset semantics?* Settled: absolute `Offsets`, shipped.

The one genuine remaining policy question is sub-document copy-vs-view semantics (Open
Questions).

## Background

The library has a strong core for LLM-oriented text transforms, but several open
implementation details undercut its safety and source-mapping promises. The fixes below
are grouped by severity and verified against current code; each notes whether the
originally-proposed fix still applies.

## Implementation Plan

Three phases, fewest needed. Phase 1 is the correctness/safety core (do first); Phases 2–3
are smaller-blast-radius hardening and cleanup.

### Phase 1: Core correctness and safety

- [ ] **`filtered_transform` enforces `diff_filter` without windowing.** Today the
      no-window path (`sliding_transforms.py`, `if not windowing or not windowing.size:`)
      returns `transform_func(doc)` directly, bypassing the filter (only the windowed path
      filters). Repro: `filtered_transform(TextDoc.from_text("hello"), lambda _:
      TextDoc.from_text("goodbye"), None, <reject-all filter>).reassemble()` returns
      `"goodbye"`. Fix: extract the transform-and-filter step into one helper used by both
      paths. Tests: `None`, `WINDOW_NONE`, and a real window setting all enforce the filter.
- [ ] **`sub_doc()` / `sub_paras()` copy semantics.** Both alias the original `Paragraph`/
      `Sentence` objects (`text_doc.py`: `sub_paras` does `paragraphs[start:end+1]`;
      `sub_doc` reuses middle paragraphs and shares `Sentence` objects), so a word-window
      `filtered_transform` calling `remove_window_br` mutates the caller's document. Fix:
      deep-copy on slice by default (matching `filtered()`), or — if a view API is wanted —
      add explicit `view_*` methods and make mutating helpers copy first (see Open
      Questions). Tests: mutating a sub-doc/sub-para does not change the parent; a
      word-window transform leaves the input `TextDoc` unchanged.
- [ ] **Paragraph windowing keeps full paragraphs.** `sliding_para_window()` builds windows
      with `sub_doc(SentIndex(i, 0), SentIndex(end_index, 0))`, which keeps only sentence 0
      of the ending paragraph (drops the rest). Fix: use `sub_paras(i, end_index)`. Tests:
      multi-sentence paragraphs with a no-op normalizer retain every sentence.
- [ ] **Div child chunking for div-leading documents.** `TextNode.slice_children()` uses
      exclusive `children[start:end]` while `chunk_generator()` passes an inclusive end
      (matching `sub_paras`' `[start:end+1]`), so the first child slice is empty; an
      empty-children node's `size()` then falls back to `self.contents` (the whole
      document), so chunking emits repeated whole-document chunks. Fix: make
      `slice_children` inclusive (`children[start:end+1]`) to match the convention, and make
      an empty child slice measure size 0. Tests: input with 3 top-level divs chunks into
      distinct, correctly-sized pieces.
- [ ] **Replace library `assert`s with explicit exceptions.** Runtime-validation asserts on
      library paths (stripped under `python -O`): `token_diffs.py` (`DiffOp.__post_init__`
      invariants; `TokenDiff.filter()` postconditions; `diff_wordtoks` difflib check),
      `divs/text_node.py` (`content_end >= 0`), `sliding_transforms.py` (the three
      `left_size()` checks). Fix: raise `ValueError`/`AssertionError(...)` (latter only for
      true internal invariants). Keep asserts only for impossible internal states.
- [ ] **`WindowSettings` invariants.** It is a frozen dataclass with no validation; negative
      `size`, `size>0` with `shift==0` (infinite loop), and `min_overlap>size` are silently
      accepted. Fix: `__post_init__` validation; add `__bool__` returning `bool(self.size)`
      so `WINDOW_NONE` is falsy (the no-window check currently relies on `not
      windowing.size`). Preserve `WINDOW_NONE` as the sentinel.
- [ ] **Word-window stitching failure semantics + error-message bug.** On a too-short
      aligned window the code `log.error(...)` and `continue`s (silent partial output); a
      separate path `raise ValueError("...%s...", n, toks)` passes `%s` args that are never
      interpolated (the message renders as a raw tuple). Alignment accepts any score. Fix:
      use an f-string for the error; add a caller policy
      (`on_alignment_failure="raise"|"skip"|"keep_original"`, default `raise`); optionally a
      score threshold. Tests: short-window alignment raises a readable error by default.
- [ ] **`TokenDiff.apply_to()` validates source identity.** It checks only that input length
      equals `left_size()` and then **ignores `original_wordtoks` entirely** — output is
      rebuilt from `op.right` and the `original_index` cursor is dead code, so a diff applied
      to a different same-length token list silently produces wrong output. Fix: verify each
      consumed `op.left` segment against `original_wordtoks[idx:idx+len(op.left)]`, raising
      `ValueError` with offset context on mismatch (and remove the dead cursor). Tests: a
      same-length but mismatched source raises.
- [ ] **`TokenMapping` confidence metric.** `_validate()` uses `len(self.diff.changes())`
      (number of diff *ops*) over `len(tokens1)`, so one `REPLACE` of 100 tokens passes the
      same gate as one of 1. Fix: use changed-*token* count (`self.diff.stats().nchanges()`)
      and document the denominator. Tests: a full-replacement mapping is rejected at a
      reasonable `max_diff_frac`.
- [ ] **Empty-document `as_wordtoks(bof_eof=True)`.** Raises `IndexError` via `last_index()`
      (`paragraphs[-1]`); `first_index()` returns an invalid `SentIndex(0,0)` on an empty
      doc. Fix: define empty-doc behavior — yield just `BOF_TOK`/`EOF_TOK`, or raise a clear
      `ValueError`; guard `first_index`/`last_index`. Tests: empty-doc wordtoks behave as
      defined.

### Phase 2: HTML helpers and smaller contracts

- [ ] **`html_find_tag()` nested self-closing same-name tags.** `_find_balanced_closing_tag`
      treats a nested `<div .../>` as an opener, so `<div id=outer>before <div id=inner/>
      after</div>` matches only the opening tag of `outer`. Fix: treat self-closing
      same-name tags as depth-neutral (it already has `_SELF_CLOSING_DETECTOR`). Tests:
      nested self-closing cases return the full enclosing span.
- [ ] **Validate tag/attribute names in `tag_with_attrs()`.** Tag and attribute names are
      interpolated unvalidated; `tag_with_attrs("span onmouseover=alert(1)", "x")` emits an
      injection-shaped tag (and a matching malformed closing tag), and `{"bad attr": "y"}`
      yields invalid markup. `_check_class_name()` exists but runs only in wrapper factories.
      Fix: validate tag and attribute names (strict HTML-name regex) inside
      `tag_with_attrs`; document `safe=`/trusted-input expectations.
- [ ] **`html_find_tag()` strict/diagnostic mode.** It catches all `selectolax` exceptions
      and `continue`s silently. Fix: add `strict: bool = False` (raise with tag/offset
      context when strict) and `logging.debug` for skipped candidates otherwise.
- [ ] **`html_extract_attribute_value()` missing vs empty.** Uses `if value:` so an empty
      attribute (`data-x=""`) is indistinguishable from a missing one. Fix: `if value is not
      None`. Tests: empty vs missing are distinguished.
- [ ] **`TimestampExtractor.extract_preceding()` exception cause.** Re-raises
      `ContentNotFound` without `from e`. Fix: chain with `from e`. Also revisit the global
      `B904` ignore in `pyproject.toml` (prefer per-line `# noqa: B904` so the check stays
      on elsewhere — a small repo-wide cleanup).
- [ ] **Class matching for parsed divs.** `CLASS_NAME_PATTERN` matches only double-quoted
      `class="..."`, stores the whole attribute as one `class_name` string, and
      `children_by_class_names()` uses exact equality, so `class="chunk selected"` won't
      match `"chunk"`. Fix: parse class names into a set/tuple (`class_names`), support
      single quotes, and match by membership/intersection; keep `class_name` as a
      convenience.
- [ ] **`parse_tag()` attribute breadth (low impact).** The regex captures only
      double-quoted, non-hyphenated `name="value"` (misses single-quoted, unquoted, boolean,
      hyphenated). Today attrs feed only tag-name checks, so impact is limited. Fix: either
      document `Tag.attrs` as best-effort/limited, or broaden the parse. Prefer documenting
      unless a consumer needs full attrs.

### Phase 3: API surface, examples, and docs

- [ ] **Root package API + naming.** `import chopdiff` exposes nothing (`__init__.py`
      empty). Decide root-level convenience exports vs. library-only with submodule imports;
      coordinate with the `DocGraph`/public-API direction so this is decided once.
- [ ] **Examples follow project rules.** Use `pathlib.Path` for file I/O; remove or
      implement the dead `--output` flag in `examples/insert_para_breaks.py`.
- [ ] Fix any remaining stale docs/typos surfaced during the work; run final validation
      (`make lint`, `make test`, `make build`, `pip-audit`).

## Testing Strategy

Focused regression tests, not broad snapshots:

- Transforms: filter enforced with `None`/`WINDOW_NONE`/window; identity transform leaves
  the input doc unchanged; alignment failure raises by default.
- Text model: sub-doc/sub-para mutation isolation; empty-doc wordtoks defined; offsets
  remain absolute (already covered, keep).
- Chunking: div-leading input with multiple top-level divs chunks correctly; empty child
  slice measures size 0.
- Diff/mapping: `apply_to()` rejects mismatched same-length source; `TokenMapping` rejects
  low-confidence (large-token-count) mappings.
- HTML: nested self-closing same-name; invalid tag/attr names rejected; empty vs missing
  attribute; multi-class matching.
- `WindowSettings`: invalid combinations raise; `WINDOW_NONE` still works (and is falsy).

```shell
make lint && make test && make build
uv run --locked --all-extras --group audit pip-audit
```

## Open Questions

- **Sub-document semantics.** Make `sub_doc`/`sub_paras` return independent copies by
  default (safest; recommended, and what the doc-model work wants), or keep them as live
  views and add explicit `view_*` plus copy-on-mutate in transform helpers? (`filtered()`
  already deep-copies.)
- **`html_find_tag` strict default.** Default to best-effort (`strict=False`) with opt-in
  strict, or strict-by-default for a rewriting library? Leaning best-effort default with a
  documented strict mode.
- **`parse_tag` attrs.** Document as best-effort, or invest in a fuller single-tag parse?
  Leaning document-as-limited unless a consumer needs it.

## Rollout Plan

- Land Phase 1 as a focused correctness release (target v0.4.1 or fold into the next minor),
  with mutation/filter/chunking behavior changes called out in release notes.
- Phases 2–3 follow or interleave with the document-model work.
- Implement reproduce-first (failing test, then minimal fix); keep CI and audit green.
- Update this spec status and close linked beads as phases land.

## Tracking

Recreated under epic `chopdiff-pdu2` (the original beads were lost from the store), with
one bead per phase: `chopdiff-pytp` (Phase 1, P1), `chopdiff-y0cd` (Phase 2, P2),
`chopdiff-xvqb` (Phase 3, P3).

## References

- [`docs/project/review/senior-engineering-review-chopdiff-pre-v0.3.0.md`](../../review/senior-engineering-review-chopdiff-pre-v0.3.0.md)
  (findings + 2026-05-29 reconciliation)
- [`plan-2026-05-29-unified-document-model.md`](plan-2026-05-29-unified-document-model.md)
  (sequencing; resolves the `from_text`/offset questions)
- [`docs/textdoc-spec.md`](../../../textdoc-spec.md) (design of record)
- `SUPPLY-CHAIN-SECURITY.md`

* * *

*This document follows the tbd [writing style guidelines](https://github.com/jlevy/tbd).*
