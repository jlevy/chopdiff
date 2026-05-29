# Senior Engineering Review: chopdiff Package (pre-v0.3.0, commit 0ad8288)

Review date: 2026-05-26

## Scope

This review covers the full `chopdiff` package as currently checked out at commit
`0ad8288`, including:

- Package metadata, build configuration, release workflows, and supply-chain posture.
- Public API exports and downstream consumer ergonomics.
- Core document model, word-tokenization, diffs, token mapping, div chunking, HTML
  helpers, timestamp extraction, and sliding-window transforms.
- Test coverage, examples, and documentation.
- The project instructions plus tbd Python, general coding, comment, testing, and
  error-handling guidelines.

This was a review pass, not a fix pass. I did not intentionally change implementation
code.

## Post-v0.3.0 Reconciliation (2026-05-29)

This file remains the historical review of commit `0ad8288`; line references and probes
below intentionally describe that pre-v0.3.0 state. Current `origin/main` has since
resolved some findings and left others open.

Resolved or materially changed:

- The broken console script was removed; `chopdiff` is library-only for now.
- `Paragraph.char_offset` / `Sentence.char_offset` were replaced by
  `Offsets(doc_offset, block_offset)`, with sentence `doc_offset` now absolute.
- `TextDoc.filtered()` deep-copies matched blocks.
- The mandatory `tiktoken` dependency was removed and replaced by a token estimate.
- The publish workflow now installs with `uv sync --all-extras --locked`.

Still open after local probes on 2026-05-29:

- `filtered_transform()` still ignores `diff_filter` when windowing is disabled.
- `sub_doc()` and `sub_paras()` still alias live paragraph/sentence objects.
- `TextDoc.from_text("  hello  ").reassemble()` still returns `"hello"`, so exact source
  references should not be documented as exact full-document reassembly.
- `html_find_tag()` still truncates an outer same-name tag when a nested same-name tag is
  self-closing.
- `TextDoc.from_text("").as_wordtoks(bof_eof=True)` still raises `IndexError`.
- `TokenMapping`, `TokenDiff.apply_to()`, runtime `assert`s, HTML attribute/name
  validation, strict HTML parsing diagnostics, empty attribute handling, and
  `WindowSettings` validation still need hardening.

## Validation Performed

Commands run:

- `make lint-check`
  - Passed.
  - `ruff check`, `ruff format --check`, `codespell`, and `basedpyright` all reported
    zero errors.
- `make test`
  - Passed: 79 tests.
- `make build`
  - Passed.
  - Built `dist/chopdiff-0.2.7.dev6+0ad8288.tar.gz` and
    `dist/chopdiff-0.2.7.dev6+0ad8288-py3-none-any.whl`.
- `uv run --locked --all-extras --group audit pip-audit`
  - Passed for third-party dependencies: no known vulnerabilities found.
  - The local editable package `chopdiff` was skipped because it is not a PyPI
    dependency, which is expected.
- `uv tree --outdated --all-groups`
  - Resolved successfully under the active `exclude-newer` policy.
  - I did not bypass the repo's 14-day cool-off policy to inspect releases newer than
    the configured cutoff.

Targeted probes were also run for behavior not covered by the current test suite:

- `uv run chopdiff`
  - Fails with `ImportError: cannot import name 'main' from 'chopdiff'`.
- `filtered_transform(..., windowing=None, diff_filter=changes_whitespace)`
  - Returns an illegal word change unchanged, so the filter is ignored without
    windowing.
- Word-window `filtered_transform` on a document containing `<!--window-br-->`
  - Mutates the caller's original `TextDoc`.
- `sliding_para_window` with a normalizer disabled on multi-sentence paragraphs
  - Drops all but the first sentence of each selected paragraph.
- `chunk_children` on a parsed div document
  - Produces repeated whole-document chunks instead of child chunks.
- `html_find_tag` with a nested self-closing same-name tag
  - Returns the outer div as only its opening tag and misreads the inner id.
- `TextDoc.from_text("")` followed by `as_wordtoks(bof_eof=True)`
  - Raises `IndexError`.
- `TokenMapping` on two completely different same-length token lists
  - Passes validation because validation counts diff operations, not changed tokens.

## Executive Summary

`chopdiff` has a useful core idea: preserve enough text structure and token mapping to
make LLM-oriented transforms auditable, filterable, and stitchable. The code is compact,
typed, reasonably easy to read, and already has meaningful coverage for many happy-path
behaviors.

The main release risk is that several core API contracts are currently stronger in the
README and docstrings than in the implementation. Exact preservation, safe chunking,
diff-filter enforcement, and stable offsets are key promises for downstream consumers,
and there are concrete cases where those promises fail. Before widening downstream use,
the package should harden its invariants, clarify mutability/copy semantics, and add
regression tests around boundary behavior.

## Priority Findings

### P1: The published console script is broken

References:

- `pyproject.toml:69`
- `src/chopdiff/__init__.py:1`

`pyproject.toml` declares:

```toml
[project.scripts]
chopdiff = "chopdiff:main"
```

But `src/chopdiff/__init__.py` is empty and no `main` object exists. Running the
installed script fails immediately:

```text
ImportError: cannot import name 'main' from 'chopdiff'
```

This affects every installed package user because console entry points are part of the
distribution metadata. The PyPA entry point specification expects `console_scripts`
targets to refer to an importable function that can be called with no arguments.

Recommendation:

- If `chopdiff` is intended to be library-only, remove `[project.scripts]`.
- If a CLI is intended, add a small `chopdiff.cli:main` and test `uv run chopdiff`.

### P1: `filtered_transform` ignores `diff_filter` when windowing is disabled

References:

- `src/chopdiff/transforms/sliding_transforms.py:35`
- `src/chopdiff/transforms/sliding_transforms.py:51`
- `src/chopdiff/transforms/sliding_transforms.py:53`

The function promises to apply a transform and enforce allowed changes via
`diff_filter`. The enforcement logic is nested inside the windowed path. If `windowing`
is `None` or `WINDOW_NONE`, the transform result is returned without diff filtering.

Observed behavior:

```python
filtered_transform(
    TextDoc.from_text("hello"),
    lambda _: TextDoc.from_text("goodbye"),
    None,
    changes_whitespace,
).reassemble()
# "goodbye"
```

That violates the core safety use case of the library. A caller can reasonably use
`filtered_transform` on a small document without windowing and expect the same filter
contract.

Recommendation:

- Factor transform-and-filter into a single helper used by both whole-document and
  windowed paths.
- Add tests for `windowing=None`, `WINDOW_NONE`, and a real window setting with the
  same illegal transform.

### P1: Sub-document APIs alias mutable sentence and paragraph objects

References:

- `src/chopdiff/docs/text_doc.py:323`
- `src/chopdiff/docs/text_doc.py:334`
- `src/chopdiff/docs/text_doc.py:341`
- `src/chopdiff/docs/text_doc.py:362`
- `src/chopdiff/docs/text_doc.py:366`
- `src/chopdiff/transforms/sliding_transforms.py:57`
- `src/chopdiff/transforms/sliding_transforms.py:59`

`TextDoc.sub_doc()` and `TextDoc.sub_paras()` reuse existing `Paragraph` and `Sentence`
objects. That makes subdocuments mutable views rather than independent values. The
public API does not document this, and several transform paths mutate their input
windows.

Concrete issue:

- Word-window `filtered_transform` calls `remove_window_br(input_doc)`.
- Word windows are created via `sub_doc()`.
- Because subdocuments share `Sentence` objects, this mutates the caller's original
  document.

Observed behavior:

```text
Input original doc: A <!--window-br--> marker. B sentence.
After word-window filtered_transform: A  marker. B sentence.
```

This is a downstream-consumer hazard. Transform callbacks may also mutate windows
directly, accidentally corrupting the original document.

Recommendation:

- Decide and document whether `TextDoc` is mutable or value-like.
- Prefer immutable or copy-on-slice semantics for library safety.
- If view semantics are needed for performance, expose explicit `view_*` APIs and make
  mutating helpers operate on copies.
- Add identity and mutation regression tests around `sub_doc()`, `sub_paras()`,
  `sliding_word_window()`, and `filtered_transform()`.

### P1: Sentence offsets are not absolute despite docstrings saying they are

References:

- `src/chopdiff/docs/text_doc.py:80`
- `src/chopdiff/docs/text_doc.py:120`
- `src/chopdiff/docs/text_doc.py:135`
- `src/chopdiff/docs/text_doc.py:213`

`Sentence.char_offset` is documented as the offset of the sentence in the original text.
`Paragraph.char_offset` is also an original-text offset. But `Paragraph.from_text()`
stores sentence offsets relative to the paragraph:

```python
sentences.append(Sentence(sent_str, sent_offset))
```

It does not add the paragraph `char_offset`. For a two-paragraph document, the second
paragraph can have `Paragraph.char_offset == 8` and its first sentence
`Sentence.char_offset == 0`.

This matters because the package's value proposition is exact mapping back to source
text. Consumers doing timestamp insertion, annotations, surgical rewriting, or UI
highlighting will get wrong offsets.

Recommendation:

- Store absolute offsets in `Sentence.char_offset`, or rename the field to make relative
  semantics explicit.
- If both are useful, expose both `paragraph_offset` and `document_offset`.
- Add tests for sentence offsets across paragraphs, leading whitespace, and normalized
  internal line breaks.

### P1: `TextDoc.from_text()` does not preserve exact input text

References:

- `src/chopdiff/docs/text_doc.py:213`
- `src/chopdiff/docs/text_doc.py:227`
- `src/chopdiff/docs/text_doc.py:230`
- `src/chopdiff/docs/text_doc.py:231`
- `README.md:50`
- `README.md:79`

The README says the original source format is exactly preserved, including whitespace,
and that sentences, paragraphs, and tokens are mapped back to the original text.
`TextDoc.from_text()` strips the whole document, strips each paragraph, and skips empty
paragraphs.

Observed behavior:

```python
TextDoc.from_text("  hello  ").reassemble()
# "hello"
```

This may be acceptable for normalized Markdown workflows, but it is not exact
preservation. It also makes offsets ambiguous because stripped paragraph text no longer
starts at the stored raw paragraph offset when paragraphs have leading whitespace.

Recommendation:

- Split the API into explicit modes, for example:
  - `TextDoc.from_text(text, preserve=True)` for exact preservation.
  - `TextDoc.from_normalized_text(text)` for current behavior.
- Alternatively, change the README/docstrings to honestly state normalization rules.
- Add tests for leading/trailing whitespace, empty paragraphs, and within-paragraph
  indentation.

### P1: Div child chunking is currently broken for already-divided documents

References:

- `src/chopdiff/divs/chunk_utils.py:11`
- `src/chopdiff/divs/chunk_utils.py:25`
- `src/chopdiff/divs/chunk_utils.py:35`
- `src/chopdiff/divs/chunk_utils.py:55`
- `src/chopdiff/divs/chunk_utils.py:65`
- `src/chopdiff/divs/text_node.py:48`
- `src/chopdiff/divs/text_node.py:56`
- `src/chopdiff/divs/div_elements.py:83`

`chunk_generator()` assumes the `slicer` end index is inclusive. `TextDoc.sub_paras()`
uses inclusive semantics, but `TextNode.slice_children()` uses normal Python exclusive
slicing. The first slice for child chunking is therefore empty (`children[0:0]`).

An empty child slice then becomes a `TextNode` with no children, so `TextNode.size()`
falls back to measuring `self.contents`, which is the whole original document. That
causes the empty slice to satisfy the size condition and yields repeated whole-document
chunks.

Observed behavior for three top-level divs:

```text
root children: 3
chunk child counts: [0, 0, 0]
chunk contents: full original document repeated
```

This directly affects `chunk_text_as_divs()` when input already starts with a div.

Recommendation:

- Standardize slicer semantics. The simplest fix is to make `chunk_generator()` use
  exclusive end indexes and adjust `chunk_paras()`, or make `slice_children()` inclusive
  through a wrapper.
- Make empty child slices have size zero, not whole-document size.
- Add tests for div-leading input with multiple top-level divs.

### P1: Paragraph windowing drops sentence content

References:

- `src/chopdiff/transforms/sliding_windows.py:47`
- `src/chopdiff/transforms/sliding_windows.py:53`
- `src/chopdiff/transforms/sliding_windows.py:55`

`sliding_para_window()` creates windows using:

```python
doc.sub_doc(SentIndex(i, 0), SentIndex(end_index, 0))
```

For a paragraph window, the end index should include the full ending paragraph. This
code includes only sentence `0` of the ending paragraph. For `nparas=1`, it keeps only
the first sentence of every paragraph.

The default `fill_markdown` normalizer can obscure this in some cases, but the slicing
bug is still present.

Recommendation:

- Use `doc.sub_paras(i, end_index)` for paragraph windows, or compute the actual last
  sentence of `end_index`.
- Add tests with multi-sentence paragraphs and a no-op normalizer.

### P1: `html_find_tag()` fails on nested self-closing tags of the same name

References:

- `src/chopdiff/html/html_tags.py:42`
- `src/chopdiff/html/html_tags.py:56`
- `src/chopdiff/html/html_tags.py:60`
- `src/chopdiff/html/html_tags.py:66`
- `src/chopdiff/html/html_tags.py:157`

`_find_balanced_closing_tag()` increments depth for any same-name opening tag and does
not recognize nested self-closing tags. Example:

```html
<div id=outer>before <div id=inner/> after</div>
```

Observed matches:

```text
outer -> <div id=outer>
inner/ -> <div id=inner/>
```

The outer match should include the full enclosing div. This breaks the documented goal
of surgical HTML editing with accurate offsets.

Recommendation:

- Treat self-closing same-name tags as depth-neutral.
- Consider using the parser for structural matching and a source-position strategy only
  for final offsets, or constrain/document the supported HTML subset.
- Add nested/self-closing regression tests.

## P2 Findings

### `TextDoc.as_wordtoks(bof_eof=True)` crashes on empty documents

References:

- `src/chopdiff/docs/text_doc.py:256`
- `src/chopdiff/docs/text_doc.py:259`
- `src/chopdiff/docs/text_doc.py:433`
- `src/chopdiff/docs/text_doc.py:436`
- `src/chopdiff/docs/text_doc.py:447`

Empty documents are representable (`TextDoc.from_text("")` returns zero paragraphs),
but `as_wordtoks(bof_eof=True)` calls `first_index()` and `last_index()`, which assume
at least one paragraph and one sentence. The result is `IndexError`.

Recommendation:

- Define empty-document semantics explicitly.
- Either yield only `BOF_TOK` and `EOF_TOK` mapped to a sentinel, or reject
  `bof_eof=True` on empty docs with a clear `ValueError`.

### `TokenMapping` validation measures diff operation count instead of changed tokens

References:

- `src/chopdiff/docs/token_mapping.py:36`
- `src/chopdiff/docs/token_mapping.py:40`
- `src/chopdiff/docs/token_mapping.py:41`
- `src/chopdiff/docs/token_diffs.py:123`

`TokenMapping._validate()` computes:

```python
nchanges = len(self.diff.changes())
```

That is the number of non-equal diff operations, not the number of changed tokens. A
complete replacement of 50 tokens by 50 unrelated tokens can be one `REPLACE` op and
pass a `max_diff_frac=0.4` gate.

Recommendation:

- Use `self.diff.stats().nchanges()` or a more explicit alignment confidence score.
- Divide by `min(len(tokens1), len(tokens2))` or document why source length alone is the
  right denominator.
- Return structured validation details so callers can tune thresholds.

### `TokenDiff.apply_to()` validates length but not source-token identity

References:

- `src/chopdiff/docs/token_diffs.py:128`
- `src/chopdiff/docs/token_diffs.py:135`
- `src/chopdiff/docs/token_diffs.py:140`

`apply_to()` checks only that the input length matches the diff left size. It does not
verify that each `op.left` segment matches the corresponding source tokens. Applying a
diff to a different same-length token list can silently produce invalid output.

Recommendation:

- Validate each consumed left segment against `original_wordtoks`.
- Raise `ValueError` with offset context on mismatch.

### Runtime validation uses `assert` in library code

References:

- `src/chopdiff/docs/token_diffs.py:52`
- `src/chopdiff/docs/token_diffs.py:174`
- `src/chopdiff/docs/token_diffs.py:179`
- `src/chopdiff/divs/text_node.py:38`
- `src/chopdiff/transforms/sliding_transforms.py:68`

Several library invariants rely on `assert`. Assertions can be disabled with optimized
Python execution and should not be used for runtime API validation in a library.

Recommendation:

- Replace public/runtime validation asserts with `ValueError`, `TypeError`, or a small
  package-specific exception hierarchy.
- Keep asserts only for impossible internal states where optimized removal is harmless.

### HTML tag generation does not validate tag or attribute names

References:

- `src/chopdiff/html/html_in_md.py:42`
- `src/chopdiff/html/html_in_md.py:64`
- `src/chopdiff/html/html_in_md.py:66`
- `src/chopdiff/html/html_in_md.py:194`
- `src/chopdiff/html/html_in_md.py:220`

Values are escaped, but tag names and attribute names are interpolated directly. For
example, `tag_with_attrs("span onmouseover=alert(1)", "x")` produces executable-looking
markup. `attrs={"bad attr": "y"}` produces invalid markup.

This is not necessarily exploitable if tag and attribute names are always constants, but
the public helper API does not enforce that. For downstream consumers, this should be
hardened.

Recommendation:

- Validate tag names and attribute names with strict HTML-name regexes.
- Run class-name validation in `tag_with_attrs()`, not only wrapper factories.
- Consider making `safe=True` unavailable for helpers that may receive untrusted text,
  or document it as trusted-input only.

### `parse_tag()` only extracts a narrow attribute subset

References:

- `src/chopdiff/docs/wordtoks.py:47`
- `src/chopdiff/docs/wordtoks.py:223`
- `src/chopdiff/docs/wordtoks.py:225`

`parse_tag()` only captures double-quoted attributes with `\w+` names. It misses common
HTML forms:

- Single-quoted attributes.
- Unquoted attributes.
- Hyphenated attributes such as `data-id`.
- Boolean attributes.

That makes the returned `Tag.attrs` incomplete for downstream users.

Recommendation:

- Either document `Tag.attrs` as best-effort and limited, or switch to a small robust
  parser for a single tag token.

### Class matching for parsed divs is too narrow for normal CSS class usage

References:

- `src/chopdiff/divs/parse_divs.py:8`
- `src/chopdiff/divs/parse_divs.py:96`
- `src/chopdiff/divs/text_node.py:126`
- `src/chopdiff/divs/text_node.py:129`

`CLASS_NAME_PATTERN` only handles double-quoted `class="..."`, stores the full class
attribute as one string, and `children_by_class_names()` checks exact equality. A div
with `class="chunk selected"` will not match `children_by_class_names("chunk")`.

Recommendation:

- Store `class_names: tuple[str, ...]` separately from the original class attribute.
- Support single quotes and normal whitespace-separated class lists.
- Keep `class_name` only as a backward-compatible convenience if needed.

### `html_find_tag()` swallows parser exceptions without diagnostics

References:

- `src/chopdiff/html/html_tags.py:165`
- `src/chopdiff/html/html_tags.py:213`

The function catches all exceptions from `selectolax` and silently skips the match. That
is okay for best-effort extraction, but it conflicts with the error-handling guideline
when callers depend on complete rewriting.

Recommendation:

- Add a `strict: bool = False` option.
- In strict mode, raise with offset and tag context.
- In best-effort mode, at least consider debug logging for skipped candidates.

### `html_extract_attribute_value()` cannot distinguish missing and empty attributes

References:

- `src/chopdiff/html/html_tags.py:220`
- `src/chopdiff/html/html_tags.py:238`
- `src/chopdiff/html/html_tags.py:240`

The extractor returns a value only if it is truthy. An explicitly empty attribute value
returns `None`, the same as a missing attribute.

Recommendation:

- Use `if attr_name in element.attrs` and return `element.attrs.get(attr_name)`.

### `TimestampExtractor.extract_preceding()` drops the exception cause

References:

- `src/chopdiff/html/timestamps.py:43`
- `src/chopdiff/html/timestamps.py:55`
- `src/chopdiff/html/timestamps.py:56`

The method catches `KeyError` and raises `ContentNotFound` without `from e`. This loses
the exception chain. The project currently disables Ruff `B904`, but the error-handling
guideline still recommends preserving cause when wrapping failures.

Recommendation:

- Raise `ContentNotFound(...) from e`.
- Consider an `extract_at_or_preceding()` API because the current `seek_back` semantics
  intentionally skip the timestamp token at the current offset.

### `WindowSettings` has no invariant checks

References:

- `src/chopdiff/transforms/window_settings.py:13`
- `src/chopdiff/transforms/window_settings.py:20`
- `src/chopdiff/transforms/window_settings.py:21`
- `src/chopdiff/transforms/window_settings.py:22`
- `src/chopdiff/transforms/sliding_transforms.py:162`

`WindowSettings` allows invalid combinations such as positive size with zero shift,
negative sizes, or `min_overlap > size`. Some invalid settings fail later with less
actionable errors.

Recommendation:

- Add `__post_init__()` validation.
- Keep `WINDOW_NONE` as an explicit sentinel if zero values need to remain supported.

### Word-window stitching has limited failure semantics

References:

- `src/chopdiff/transforms/sliding_transforms.py:191`
- `src/chopdiff/transforms/sliding_transforms.py:197`
- `src/chopdiff/transforms/sliding_transforms.py:205`
- `src/chopdiff/transforms/sliding_transforms.py:217`

If a transformed window is too short to align, the code logs an error and continues.
For a library transform, that can silently produce partial output.

Recommendation:

- Default to raising on alignment failure.
- Optionally support `on_alignment_failure="raise" | "skip" | "keep_original"` for
  callers that explicitly want best effort.
- Return a structured transform report with accepted windows, skipped windows, scores,
  and rejected diffs.

## P3 Findings And Cleanup

### Root package API is empty

References:

- `src/chopdiff/__init__.py:1`
- `src/chopdiff/docs/__init__.py:47`
- `src/chopdiff/divs/__init__.py:17`
- `src/chopdiff/html/__init__.py:35`
- `src/chopdiff/transforms/__init__.py:39`

The subpackage APIs have explicit exports, but `import chopdiff` exposes nothing. That
is fine if intentional, but most downstream consumers will expect either a documented
root API or no root-level examples/scripts.

Recommendation:

- Decide between:
  - Root-level convenience exports for the most common APIs, or
  - A library-only root with docs consistently using `chopdiff.docs`,
    `chopdiff.transforms`, etc.

### Public API naming needs consolidation

Current surface includes:

- `TextDoc`, `Paragraph`, `Sentence`, `SentIndex`.
- `wordtoks`, `TokenDiff`, `TokenMapping`.
- `divs`, `html`, `transforms`.
- `TextUnit` with `wordtoks` and `tiktokens`.

The concepts are useful but not yet organized around stable consumer workflows. A
downstream user has to learn internal nouns before understanding which API to use.

Recommendation:

- Define primary workflows in docs and exports:
  - Parse and measure a document.
  - Diff and filter a document.
  - Map offsets between two documents.
  - Chunk a document.
  - Run a windowed transform safely.
- Keep lower-level helpers public only if their contracts are stable.

### PR #7 is a reasonable interim Markdown block API with two fixes

PR #7 adds `BlockType`, `Paragraph.block_type`, `TextDoc.iter_blocks()`, and
`TextDoc.filtered()`. The current PR implementation uses Marko through
`flowmark_markdown()` for paragraph-local classification, so it is no longer the
regex-only approach that would be inappropriate as a foundation.

Recommendation:

- Land PR #7 as a short-term release improvement if it first re-exports `BlockType`
  from `chopdiff.docs`.
- Fix `TextDoc.filtered()` so it copies paragraph and sentence objects rather than
  returning a new `TextDoc` that aliases the original mutable objects.
- Document `Paragraph.block_type` as a coarse paragraph-level classifier, not a precise
  Markdown AST block API.
- Keep the fuller parser-backed block segmentation plan separate. It should still own
  source spans, list-item blocks, section rollups, offset-backed tallies, and analytics
  filtered by block kind or category.

### Examples do not fully follow project Python guidelines

References:

- `examples/insert_para_breaks.py:109`
- `examples/insert_para_breaks.py:104`
- `examples/backfill_timestamps.py:123`

Examples use direct `open()` instead of `Path.read_text()` and do not write output even
though `--output` exists in `insert_para_breaks.py`. The examples are not central
library code, but examples often become copied downstream code.

Recommendation:

- Use `Path`.
- Either implement `--output` with `strif.atomic_output_file` or remove the option.
- Add a smoke test for examples that do not require network credentials.

### Test output is noisy in normal pytest runs

Many tests use `print()` and `pprint()`. That is sometimes useful with `pytest -s`, but
pytest captures output by default. It is not a blocker.

Recommendation:

- Keep prints only where they help diagnose failures.
- Prefer direct assertions for expected behavior and shorter test fixtures for
  maintainability.

### Documentation still has template residue and some stale wording

References:

- `docs/publishing.md:19`
- `docs/publishing.md:31`
- `docs/publishing.md:70`
- `src/chopdiff/docs/text_doc.py:214`
- `src/chopdiff/docs/wordtoks.py:3`

Examples:

- Publishing docs still use `OWNER` and `PROJECT` placeholders.
- `TextDoc` docstring says `Markown`.
- `wordtoks.py` docstring says `setnence`.
- README examples refer to logged module names that no longer match the package layout
  in at least one place.

Recommendation:

- Do a docs cleanup pass after the API contract fixes.
- Keep docs aligned with actual preservation and normalization behavior.

## Subsystem Design Assessment

### Package And Release Design

Strengths:

- `src/` layout and `py.typed` are appropriate for a typed library.
- `uv`, lockfile, CI, and dependency groups are modern.
- Dynamic versioning is practical for release automation.
- Supply-chain policy is explicit and tested.

Risks:

- Broken console script is release-blocking if the script remains in metadata.
- Publish workflow computes `UV_EXCLUDE_NEWER` at runtime and uses `uv sync --all-extras`
  without `--locked`, while CI uses `uv sync --all-extras --locked`. This weakens
  consistency between CI and release.
- CI only runs Ubuntu despite `Operating System :: OS Independent`.

Recommendations:

- Make release install behavior match CI: `uv sync --all-extras --locked`.
- Avoid a second runtime cool-off mechanism in publish unless there is a specific
  release reason. The project already stores `exclude-newer` in `pyproject.toml`.
- Add a release smoke test that installs the built wheel and imports key APIs.
- If the CLI remains, test the installed console command.
- Consider adding Windows and macOS CI once the dependency wheel story is understood.

Relevant external references:

- [PyPA entry points specification](https://packaging.python.org/en/latest/specifications/entry-points/):
  console scripts refer to importable object references, and wrappers call the
  referenced function.
- [uv `exclude-newer` setting](https://docs.astral.sh/uv/reference/settings/#exclude-newer):
  the resolver limits candidate artifacts by upload time and accepts RFC 3339
  timestamps or durations.
- [uv package publishing guide](https://docs.astral.sh/uv/guides/package/#publishing-your-package):
  trusted publishing from GitHub Actions does not require credentials once configured
  with PyPI.

### Core `TextDoc` Model

Strengths:

- The object model is simple and understandable.
- Sentence, paragraph, and token traversal APIs are convenient.
- `TextUnit` gives a unified measurement vocabulary.
- Tests cover basic parsing, size summaries, subdocuments, token mappings, and markup
  detection.

Risks:

- Preservation semantics are ambiguous.
- Mutability and slicing aliasing are not documented.
- Offsets are inconsistent.
- Empty documents are not fully supported.

Recommended design direction:

- Make `TextDoc` a reliable value object for downstream users.
- Define normalization as an explicit operation, not implicit constructor behavior.
- Keep offset data absolute and test it extensively.
- Add a small `Span` or `TextRange` abstraction if the library will keep mapping source
  ranges into transformed documents.

### Word Tokens

Strengths:

- Treating HTML tags, entities, punctuation, words, and normalized whitespace as tokens
  is a good pragmatic fit for LLM editing guardrails.
- The special BOF/EOF/SENT/PARA tokens make diffing and alignment easier.
- Tokenization tests cover common text and HTML spans.

Risks:

- Token values normalize whitespace, while offsets point into the original text. This is
  useful but should be documented as a lossy token value with source offsets.
- `Tag.attrs` parsing is incomplete.
- The sentinel tokens are plain strings that could collide with user content.

Recommendations:

- Document tokenization invariants precisely.
- Consider a structured token type for advanced consumers while preserving string-token
  convenience APIs.
- If sentinel collisions matter, add escaping or reserve-token validation.

### Diff Filtering And Token Mapping

Strengths:

- LCS-style word-token diffs are a strong foundation for constrained LLM edits.
- `TokenDiff.filter()` is easy to reason about.
- Filters like `changes_whitespace`, `removes_words`, and lemma-preserving filters map
  directly to useful LLM safety policies.

Risks:

- Whole-operation filtering can be coarse when a single `REPLACE` mixes allowed and
  disallowed changes.
- `TokenMapping` validation currently underestimates large replacements.
- Diff application does not verify token identity.
- Lemmatization depends on optional `simplemma` but filters import lemmatize helpers
  unconditionally. This is okay until the lemmatizing filters are called, but docs
  should make that lazy optional behavior explicit.

Recommendations:

- Add structured diff validation and reporting.
- Consider splitting mixed replace operations where safe, or document that filters work
  at opcode granularity.
- Add confidence metrics to `TokenMapping`.

### HTML Helpers

Strengths:

- The package correctly avoids pulling in a heavy HTML framework for simple Markdown
  HTML snippets.
- Attribute-value escaping exists.
- HTML rewrite tests are broad and cover quote styles, comments, nested elements, and
  unquoted attributes.

Risks:

- Tag and attribute names are not validated.
- `html_find_tag()` is a hybrid parser that still has structural edge cases.
- Silent exception swallowing can hide missed rewrites.

Recommendations:

- Separate "HTML snippet generation" from "surgical HTML source rewrite" in docs and
  API naming.
- Harden name validation.
- Add strict mode for rewrite/extraction.
- Consider representing rewrite results as `{text, replacements, skipped, warnings}`.

### Div Parsing And Chunking

Strengths:

- `TextNode` is a useful lightweight tree for Markdown documents with div wrappers.
- Offset-preserving parsing is valuable for reassembly.
- Structure summaries are useful for diagnostics.

Risks:

- Child chunking is currently broken.
- The parser only understands div tags and a narrow class syntax.
- Malformed or unmatched divs are tolerated without a structured warning.

Recommendations:

- Fix chunk semantics before relying on div-based chunking.
- Add parse diagnostics for unmatched tags.
- Store class lists and original markers separately.

### Sliding Transforms

Strengths:

- The overall design fits LLM workflows: transform chunks, filter diffs, stitch output.
- `WindowSettings` presets make common usage simple.
- Logging gives helpful visibility when debugging.

Risks:

- No-window filtering is skipped.
- Word-window transforms can mutate original docs through subdocument aliasing.
- Paragraph windows drop content.
- Alignment failures are logged and skipped rather than surfaced as structured failures.
- Stitching can be expensive and has limited configurability around maximum overlap,
  score thresholds, and failure policy.

Recommendations:

- Make filtering independent of windowing.
- Make windows immutable copies or clearly documented views.
- Return a transform report object for downstream observability.
- Add property-style tests for identity transforms, whitespace-only transforms, illegal
  transforms, and overlapping windows.

### Tests

Strengths:

- The suite is fast.
- Tests cover meaningful behavior across subsystems.
- Supply-chain policy has regression tests.
- Type checking covers source, tests, devtools, and examples.

Coverage gaps:

- Installed console script.
- Wheel install/import smoke test.
- Empty documents.
- Exact preservation and offset contracts.
- Subdocument mutation aliasing.
- `filtered_transform` without windowing.
- Div-leading chunking.
- Multi-sentence paragraph windows.
- TokenMapping large replacement validation.
- HTML nested self-closing same-name tags.
- Strict error paths and malformed inputs.

Recommendation:

- Add focused regression tests for each P1/P2 finding before broad refactors.
- Keep the tests small and behavior-oriented.

### Modern Python And tbd Guideline Compliance

What is already good:

- Uses Python 3.11+ syntax and type annotations.
- Uses `collections.abc` in most places.
- Uses `typing_extensions.override`.
- Uses `uv`, dependency groups, `ruff`, `basedpyright`, and `pytest`.
- Uses absolute imports.
- Package is typed with `py.typed`.

Areas to improve:

- Replace `assert` runtime validation with real exceptions.
- Add `from __future__ import annotations` consistently in typed modules where useful.
- Use `StrEnum` for string-valued enums such as `TextUnit` and `OpType` if compatibility
  with plain strings would help downstream users.
- Preserve wrapped exception causes with `raise ... from e`.
- Use `Path` in examples instead of direct `open()`.
- Avoid broad `except Exception` unless paired with strict mode or diagnostics.
- Reduce obvious or stale comments when touching nearby code.
- Add concise docstrings to exported functions that currently lack them, especially
  public helpers in `wordtoks`, `sizes`, and transforms.

## Suggested Release Roadmap

### Before the next patch release

Fix release blockers and high-risk correctness bugs:

- Remove or implement the `chopdiff` console script.
- Make `filtered_transform` enforce filters with and without windowing.
- If PR #7 is targeted for the same release, land it after the `BlockType` export and
  `TextDoc.filtered()` copy-semantics fixes.
- Fix `sliding_para_window` to include full paragraphs.
- Fix div child chunking.
- Prevent word-window transforms from mutating the caller's document.
- Fix absolute sentence offsets or update the public contract.
- Add regression tests for all of the above.

### Before broader downstream adoption

Stabilize contracts:

- Decide exact-preservation versus normalized-text API boundaries.
- Define `TextDoc` mutability and copy semantics.
- Harden empty-document behavior.
- Replace assert-based validation.
- Improve `TokenMapping` confidence and validation.
- Validate HTML tag and attribute names.
- Add strict modes for best-effort extractors/re-writers.

### Before a 1.0-style stable API

Consolidate and clarify:

- Publish a root-level API policy.
- Document supported HTML and Markdown subsets.
- Add a transform report type.
- Add wheel install smoke tests and installed CLI tests.
- Add OS matrix CI or document Linux-only support if dependencies constrain it.
- Revisit dependency lower bounds and optional extras naming.

## Dependency And Upgrade Notes

The dependency setup is modern and comparatively strong:

- `uv.lock` is committed.
- `exclude-newer` is configured.
- CI installs with `--locked`.
- `pip-audit` runs in CI and passed locally.
- Active cool-off exceptions are documented.

No dependency upgrade is currently recommended from this review. The higher-value work
is correctness and API contract hardening. I did not bypass the 14-day cool-off policy
to inspect newer-than-cutoff releases.

One release workflow concern remains:

- `.github/workflows/publish.yml` uses a runtime `UV_EXCLUDE_NEWER` and `uv sync
  --all-extras`, while CI uses the committed lockfile with `uv sync --all-extras
  --locked`.

For release reproducibility, publish should install the same locked environment CI
validated unless there is an explicit reason to re-resolve at release time.

## Documentation Improvements

The README is useful, but it currently overpromises exact preservation. The docs should
be updated after contract fixes to clarify:

- Whether `TextDoc.from_text()` preserves or normalizes input.
- Whether token whitespace values are normalized.
- Whether offsets are absolute or relative.
- Whether subdocuments are copies or views.
- Which HTML forms are supported by lightweight parsing.
- What happens when alignment fails in sliding transforms.
- Which APIs are stable for downstream consumers.

## Final Assessment

The package is promising and already useful for constrained text transforms, but it is
not yet robust enough to treat its current API contracts as stable for broad downstream
use. The next engineering step should not be adding more features. It should be a
focused hardening release that fixes the P1 correctness issues, writes regression tests
for boundary cases, and clarifies the central design contracts: preservation,
mutability, offsets, filtering, and failure behavior.
