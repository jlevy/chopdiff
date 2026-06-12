---
title: flexdoc 0.1.0 Integration Review
description: Issues found while migrating chopdiff onto the published flexdoc 0.1.0, for upstream fixes in jlevy/flexdoc
author: Joshua Levy (github.com/jlevy) with LLM assistance
---
# flexdoc 0.1.0 Integration Review (for Upstream)

**Date:** 2026-06-12

**Context:** Findings from migrating chopdiff onto the published flexdoc 0.1.0 per
[chopdiff#27](https://github.com/jlevy/chopdiff/issues/27) and
`docs/project/specs/active/plan-2026-06-12-flexdoc-pypi-migration.md`. The migration
succeeded: chopdiff's full suite (divs/transforms/util, 27 tests) passes against the
PyPI package, the wheel smoke test passes in an isolated venv, and resolution is clean.
These are upstream issues for jlevy/flexdoc, not blockers. None were worked around with
shims; where chopdiff needed an adjustment it imports from the defining module and
references this doc.

## Issues to fix upstream

### 1. `Splitter` and `default_sentence_splitter` are not exported from any public namespace

`Splitter` appears in the public `FlexDoc.from_text()` signature
(`sentence_splitter: Splitter = default_sentence_splitter`), but neither name is
importable from `flexdoc` or `flexdoc.docs` (`flexdoc.docs.__all__` omits both). The
only import location is the `flexdoc.docs.paragraphs` submodule, where they are
defined (`paragraphs.py:51` and `:53`).

Repro:

```python
from flexdoc.docs import Splitter  # ImportError
```

Downstream effect: anyone passing a custom splitter (chopdiff's
`chopdiff.divs.text_node` does) must guess the defining module. chopdiff now imports
`from flexdoc.docs.paragraphs import Splitter, default_sentence_splitter` with a
comment pointing here.

Suggested fix: add `Splitter` and `default_sentence_splitter` to
`flexdoc.docs.__all__` (they are part of the `from_text` API surface); consider the
root export too.

### 2. `flexdoc.docs.flex_doc` has no `__all__`, so re-imported names trip strict type checkers

`flex_doc.py` imports `Paragraph`, `Splitter`, and `default_sentence_splitter` for its
own use. Because the module has no `__all__` (and no redundant `x as x` aliases),
basedpyright/pyright in default strictness flags importing them from there:

```
warning: "Splitter" is not exported from module "flexdoc.docs.flex_doc"
  (reportPrivateImportUsage)
```

This bites exactly the migration path the 0.1.0 handoff recommends: a mechanical
`text_doc` to `flex_doc` module rename of legacy imports such as
`from chopdiff.docs.text_doc import Paragraph, TextDoc` produces imports that work at
runtime but fail strict type checking. Suggested fix: add an explicit `__all__` to
`flexdoc.docs.flex_doc` covering its public surface, and/or state the canonical import
locations (`flexdoc` root for `FlexDoc`, `flexdoc.docs` for `Paragraph` etc.) in the
flexdoc CHANGELOG migration notes.

### 3. Migration-runbook gap: cross-test-package imports are not covered

The chopdiff#27 runbook's deletion list (`tests/docs/`, `tests/html/`, `tests/golden/`)
was verified against `src/` and `examples/` imports but not against imports between
test packages. `tests/transforms/test_diff_filters.py` imported fixture texts from the
deleted `tests/docs/test_token_diffs.py`
(`from ..docs.test_token_diffs import _short_text1, ...`), which broke after deletion;
the fixtures are now inlined in the chopdiff test. If other downstreams follow the
same split, the flexdoc migration notes should mention checking for test-to-test
imports across the boundary.

## Verified clean (no action needed)

- Wheel + sdist on PyPI with `py.typed`; sdist includes `docs/flexdoc-spec.md`,
  `CHANGELOG.md`, and the three migrated examples.
- Root exports as documented: `FlexDoc`, `DocGraph`, `Detail`, `SpanRef`, `BlockType`,
  `NodeKind`, `Layer`, `TextUnit`.
- `flexdoc.html` and `flexdoc.util` define `__all__`; everything chopdiff imports
  (`TextUnit`, `BlockType`, `Paragraph`, wordtok constants/functions, diff types,
  `div_wrapper`/`html_join_blocks`/`Attrs`/`ClassNames`, `tag_with_attrs`) resolves
  under the expected names.
- Parse behavior is unchanged: chopdiff's sliding-window and diff-filter tests pass
  byte-for-byte against the published package.
- Dependency graph matches the in-repo copy (marko, cydifflib, funlog, regex, strif,
  frontmatter-format, pydantic, selectolax, flowmark, prettyfmt, typing-extensions);
  resolution under chopdiff's cool-off policy required only the recorded flexdoc
  exception.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
