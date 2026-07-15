# Senior Engineering Review: chopdiff, July 2026

**Date:** 2026-07-14\
**Baseline:** `df1337bcbeba824388fb0ad251cc253540c9ffc6` (`origin/main`)\
**Tracking epic:** `chopdiff-xrw3`\
**Baseline verdict:** Changes required before the next release

## Scope

This review covers the full repository at the baseline above, not only a branch diff: 81
tracked files, including all 28 Python source, test, development-tool, and example
files. It assesses architecture, public APIs, implementation correctness, tests,
documentation, packaging, dependency policy, CI/CD, and the release workflow.

The baseline was exercised on macOS with CPython 3.14.6:

- `make install` from the committed lock, after isolating the repository from a
  user-level uv config that otherwise changed the lock options
- `make lint`: codespell, Ruff check/format, and BasedPyright; zero errors or warnings
- `make test`: 27 tests passed
- `uv build --wheel`: wheel built successfully
- isolated wheel install and imports: passed with the repository cutoff and exceptions
- `pip-audit`: failed on `msgpack 1.1.2` / `GHSA-6v7p-g79w-8964`; the separately ignored
  `PYSEC-2026-196` in `pip` also remains recorded in CI

The latest completed GitHub CI run for the baseline was green on 2026-06-13, before the
current advisory result.
The final branch must rerun the complete Python 3.11-3.14 matrix and wheel smoke test.

## Summary

The FlexDoc extraction left chopdiff with a coherent, appropriately small identity: diff
filtering, targeted `<div>` chunking, and windowed transforms over the standalone
document model. The dependency direction is clean, the wheel boundary is explicit, the
test-to-source ratio is strong for a small library, and the existing tests cover several
important regressions rather than trivial model construction.

Release readiness is blocked by two correctness issues in core transform contracts:
remove-only diff filters can admit inserted duplicate words, and word-window shifts do
not determine the next window start.
The public window generator can also repeat forever when called with a zero shift.
Exact `<div>` reassembly and collection-based token ignores have smaller but confirmed
contract defects.
The dependency and documentation state is a month behind the standalone
FlexDoc release line, and the current vulnerability audit no longer passes.

## Findings

### R1 — High — Remove-only diff filters lose token multiplicity

**Evidence:** `src/chopdiff/transforms/diff_filters.py:131` and
`src/chopdiff/transforms/diff_filters.py:143`; bead `chopdiff-ojox`.

`removes_words()` compares `set(right) - set(left)`, and `removes_word_lemmas()` uses
set inclusion. Both therefore accept `REPLACE(["cat"], ["cat", "cat"])`. This violates
the advertised remove-only policy and matters because these predicates enforce what an
LLM transform is allowed to change.

**Fix:** Compare word or lemma counts as multisets, preserving case behavior and still
allowing punctuation/whitespace changes.
Add duplicate-insertion and duplicate-removal regressions.

### R2 — High — Word-window shifts are not honored and direct zero shifts do not terminate

**Evidence:** `src/chopdiff/transforms/sliding_windows.py:15`,
`src/chopdiff/transforms/sliding_windows.py:42`, and
`src/chopdiff/transforms/sliding_transforms.py:172`; bead `chopdiff-fg1q`.

The generator increments `start_offset` by `window_shift` but assigns the next
`start_index` to the preceding `end_index`. A configured shift of 60 bytes therefore
starts the next window at the prior boundary sentence rather than the sentence at byte
60\. The numeric shift controls only successive end targets, so intended overlap or gap
semantics are not delivered.
Because `sliding_word_window()` is public, calling it directly with `window_shift=0`
repeats windows indefinitely even though `WindowSettings` protects the higher-level
path.

**Fix:** Validate positive size and shift in the public generators; derive each start
index from its numeric start offset; and add exact start/overlap coverage plus invalid
argument tests.
Preserve the existing sentence-boundary behavior when translating numeric
offsets.

### R3 — Medium — Exact `<div>` reassembly is not lossless

**Evidence:** `src/chopdiff/divs/text_node.py:164` and
`src/chopdiff/divs/parse_divs.py:52`; bead `chopdiff-e64o`.

`TextNode` retains the original opening and closing markers, and the public description
says `padding=""` can reassemble the original document exactly.
The implementation instead rebuilds every tag through `div_wrapper()`. A valid
`class="chunk selected"` raises validation because the whole class list is passed as one
class name, while attributes such as `id` and `data-*` would be discarded.

**Fix:** In exact mode, reassemble with the retained original markers.
Keep normalized mode’s intentional wrapper normalization.
Add a nested round-trip with multiple classes and non-class attributes.

### R4 — Medium — Collection-based token ignores are silently skipped

**Evidence:** `src/chopdiff/transforms/diff_filters.py:29` and
`src/chopdiff/transforms/diff_filters.py:89`; bead `chopdiff-8w3n`.

`TokenMatcher` permits `list[str]`, but the runtime branch checks
`isinstance(ignore, str)`. Passing `ignore=[" "]` therefore performs no filtering and
can reject a sequence the caller explicitly asked to ignore.

**Fix:** Accept a read-only collection of token strings or a predicate, implement both
branches directly, document the behavior, and test both forms.

### R5 — Medium — Developer and CI/CD dependency gates are not fully reproducible

**Evidence:** `Makefile:20`, `.github/workflows/ci.yml:35`,
`.github/workflows/ci.yml:49`, `.github/workflows/publish.yml:16`, and
`.github/workflows/publish.yml:35`; bead `chopdiff-xn52`.

`make install`, `make lint`, and `make test` invoke uv without `--locked`. On the review
host, uv merged user-level per-package exceptions and silently rewrote the lock options
during routine setup.
GitHub Actions use movable version tags despite the development guide requiring commit
SHAs.
The release workflow tests but does not run lint or the vulnerability audit, so its
manual trigger can publish without the complete merge gate.
CI also claims OS independence while testing only Ubuntu.

**Fix:** Make routine developer commands locked while leaving `make upgrade` as the
explicit resolution path; pin vetted action releases by commit SHA; update the vetted uv
tool version; add one representative macOS matrix entry; and run check-only lint plus an
unignored audit before publishing.

### R6 — Medium — Maintained documentation describes obsolete FlexDoc ownership and status

**Evidence:** `README.md:126`, `README.md:130`, `docs/development.md:115`, `TODO.md:4`,
and `docs/project/specs/active/plan-2026-06-11-flexdoc-extraction.md:7`; bead
`chopdiff-xtmw`.

FlexDoc 0.3.0 intentionally stopped re-exporting token mapping and search names from
`flexdoc.docs`, but the README still locates them there.
The development guide calls several FlexDoc transitives direct chopdiff dependencies.
`TODO.md` and the extraction plan still present standalone publication and the external
dependency rewire as future work even though main already completed both.

**Fix:** Point API names to their owning modules, separate direct from transitive
dependencies, make the current TODO chopdiff-specific, and mark completed extraction
stages as historical while linking deferred FlexDoc work to the FlexDoc repository.

### R7 — Medium — The standalone example resolves unpinned code and writes non-atomically

**Evidence:** `examples/insert_para_breaks.py:1`, `examples/insert_para_breaks.py:100`,
and `examples/insert_para_breaks.py:115`; bead `chopdiff-x6ab`.

The PEP 723 script runs three unpinned packages, bypassing the project’s committed lock
and cool-off. It also lacks complete return annotations and uses `Path.write_text()` for
the requested output even though the repository’s file-writing convention is atomic.

**Fix:** Pin the standalone script’s exact package versions under the same cutoff or
first-party exception policy, add full annotations, and use a script-declared `strif`
atomic write helper.
Keep OpenAI out of chopdiff’s runtime dependency set.

### R8 — Medium — User-level uv policy can invalidate routine locked commands

**Evidence:** `Makefile:20`, `pyproject.toml:102`, and validation on the maintainer’s
development environment; bead `chopdiff-lv0e`.

uv merges user-level configuration with project configuration, including entries in
`exclude-newer-package`. The maintainer’s first-party exceptions therefore changed the
effective lock options, causing `make test` with `--locked` to fail before running any
tests. The lock protected the repository from mutation, but routine commands were not
portable across otherwise valid uv environments.

**Fix:** Keep `pyproject.toml` canonical, add a tested `.uv-policy.toml` mirror, and
pass it explicitly from Make and CI so user-level policy cannot be merged.
Document the equivalent `UV_CONFIG_FILE` setting for direct uv commands.

### R9 — Medium — The source distribution bundles generated caches and automation

**Evidence:** the baseline `uv build` source archive included `.tbd/docs`, agent skills,
Claude hooks, GitHub workflows, historical plans, and other repository-only files; bead
`chopdiff-w1m4`.

Hatch’s default sdist selection traverses the repository when no explicit file selection
is configured. The resulting archive was much larger than the distributable source and
exposed internal development material that is irrelevant to package consumers.

**Fix:** Restrict the sdist to `src/chopdiff`; Hatch always adds the build metadata,
README, license, and `pyproject.toml`. Build the wheel from that sdist and add a CI
manifest check that rejects repository-only directories.

## Dependency Assessment

The direct runtime surface remains justified: chopdiff directly imports FlexDoc,
Flowmark, Prettyfmt, and `typing_extensions`; `simplemma` remains correctly optional.
Do not add FlexDoc’s transitives as direct dependencies unless chopdiff imports them.

The reviewed upgrade target is:

- `flexdoc 0.1.0 -> 0.3.0`; first-party release from 2026-07-11, explicitly authorized
  to bypass the cool-off.
  Constrain to `<0.4.0` because FlexDoc documents breaking pre-1.0 changes at each minor
  and already plans a 0.4.0 API change.
- `flowmark 0.7.1 -> 0.7.2`; first-party and older than the new cutoff.
- Prettyfmt 0.4.1, Strif 3.1.0, Funlog 0.2.1, Frontmatter Format 0.3.0, and
  `flowmark-rs` 0.3.1 are already current.
- Keep Lefthook 2.1.9: 2.1.10 was released 2026-07-08 and is not first-party, so it does
  not clear the 2026-06-30 cutoff.
- Move the repository cutoff to 2026-06-30 and remove expired exceptions.
  Retain a precise, documented FlexDoc exception for 0.3.0 rather than a blanket future
  bypass.
- Update CI’s setup-uv action to vetted v8.2.0 and uv to 0.11.25. Newer setup-uv and uv
  releases are inside the cutoff.
  Update checkout to vetted v7.0.0.
- Re-resolve all transitives, inspect the complete `uv.lock` diff, and require an
  unignored `pip-audit` result.
  In particular, resolve `msgpack` to 1.2.1 or later and remove the stale `pip` advisory
  ignore once the new cutoff admits its fix.

## Design Assessment

The current package boundary is cleaner than retaining a second document model inside
chopdiff. FlexDoc owns parsing, tokenization, mappings, and diffs; chopdiff composes
those primitives into policy filters and transforms.
This direction avoids duplicate models and keeps the dependency graph one-way.
The owning-module imports used by source code are also resilient to FlexDoc 0.3’s export
cleanup.

The transform layer’s main weakness is that its behavioral contracts are expressed in
names and prose but not consistently as invariants.
Window size, shift, overlap, and filter acceptance affect correctness and should be
validated at every public entry point, with tests that assert coverage and permitted
edits rather than only output shape.
The targeted div parser is reasonable for marker-based chunking, but exact and
normalized modes need to remain explicit: exact mode should preserve retained source
markers, while normalized mode may intentionally discard unsupported HTML detail.

A general HTML parser would handle malformed markup more comprehensively, but adopting
one here would broaden semantics and dependencies without solving the marker-oriented
use case better. Retaining the small parser with honest boundaries is preferable.

## Documentation

Current user-facing documentation should own only chopdiff behavior and link to
FlexDoc’s current specification for the document model.
Historical review and plan documents can remain as design records, but completed plans
should say they are implemented or superseded rather than acting as parallel task lists.
This review is the current chopdiff engineering snapshot; beads remain the execution
record.

## Non-Blocking Suggestions

- Rename the generic optional extra `extras` in a future breaking release to something
  capability-specific such as `lemmatize`; retain the current name for compatibility in
  this pass.
- Consider a check-only Markdown-format CI gate if formatting drift becomes recurring.
  The current pre-commit hook is sufficient while the repository remains single-
  maintainer and the final branch is formatted before commit.
- Add measured coverage only if it changes test decisions.
  The current behavioral tests are more valuable than a percentage target by itself.

## False Positives / Do Not Fix

- chopdiff’s empty root API is intentional and documented; do not add convenience
  exports piecemeal.
- `flowmark` and `prettyfmt` are valid direct dependencies even though FlexDoc also
  depends on them, because chopdiff imports both directly.
- `simplemma` is intentionally optional and large; do not move it into core runtime
  dependencies.
- The div parser is intentionally not a general HTML parser.
  Harden its declared exact round-trip behavior without expanding it into an HTML5
  parser.
- The generated tbd integration changes are expected from the user-requested v0.4.0
  metadata migration and should be reviewed as generated infrastructure, not rewritten
  manually.

## Execution Order

1. Upgrade and audit dependencies (`chopdiff-o93x`).
2. Fix R1-R4 with focused regressions (`chopdiff-ojox`, `chopdiff-fg1q`,
   `chopdiff-e64o`, `chopdiff-8w3n`).
3. Address workflow, docs, example, local-policy, and artifact findings
   (`chopdiff-xn52`, `chopdiff-xtmw`, `chopdiff-x6ab`, `chopdiff-lv0e`,
   `chopdiff-w1m4`).
4. Run full local and pull-request validation (`chopdiff-va1h`) and update this document
   with final disposition before merge.

## Final Disposition

**Final verdict:** Locally release-ready; pull-request CI pending.

All findings were reproduced, tracked as beads, fixed, and covered by regression checks
where automation is meaningful.

| Finding | Status | Result |
| --- | --- | --- |
| R1 | Resolved | Multiset comparisons reject duplicate word and lemma insertion. |
| R2 | Resolved | Window starts honor shifts and public generators validate positive values. |
| R3 | Resolved | Exact div reassembly preserves original tags and attributes. |
| R4 | Resolved | Collection and predicate token ignores both work. |
| R5 | Resolved | Routine commands are locked; actions are SHA-pinned; release gates are complete. |
| R6 | Resolved | Maintained docs now reflect standalone FlexDoc ownership and current APIs. |
| R7 | Resolved | The standalone script is annotated, atomic, exact-pinned, and transitively locked. |
| R8 | Resolved | Explicit uv policy prevents user configuration from changing project resolution. |
| R9 | Resolved | The sdist contains only package source and mandatory build metadata. |

## Final Local Validation

- `make`: locked sync, Ruff, BasedPyright, codespell, and 36 tests passed.
- Isolated CPython 3.11, 3.12, 3.13, and 3.14 environments: 36 tests passed on each.
- Project and standalone-script lock checks passed.
- Project and standalone-script vulnerability audits reported no known vulnerabilities.
- YAML parsing passed for both GitHub Actions workflows.
- The sdist built successfully, passed the minimal-manifest check, and produced the
  wheel from the archive.
- The wheel metadata and contents were inspected; an isolated Python 3.11 install with
  extras passed functional smoke tests across filters, lemmatization, divs, and windows.
- The standalone OpenAI script’s isolated `--help` path passed without making an API
  request. A live OpenAI transformation was intentionally not run because it requires
  credentials and incurs external cost.
