---
type: is
id: is-01ksxch8y5z7y5ypw1ff58ck08
title: collect() query primitive + offset-containment (docs/collect.py)
kind: task
status: closed
priority: 2
version: 5
spec_path: docs/project/specs/active/plan-2026-05-29-unified-document-model.md
labels: []
dependencies:
  - type: blocks
    target: is-01ksxch9qc6yks6zwz9z4en15e
  - type: blocks
    target: is-01ksxchaetnpynrsnzn82taqcd
parent_id: is-01kss8gdn83f47wbrg3jve028r
created_at: 2026-05-30T21:27:10.021Z
updated_at: 2026-05-30T22:54:01.985Z
closed_at: 2026-05-30T22:54:01.985Z
close_reason: null
---
New src/chopdiff/docs/collect.py. collect(scope, *, kinds=None, where=None, recursive=False, inline=False, contains=None) -> list[Node].
- Scope handles: document (whole table), section(id), node(id)/block.
- contains/containment mode: nodes whose span is within a given span (cross-layer query).
- Returns Nodes; counts/values/groupings are plain Python (Counter), documented with worked examples. No per-kind rollup methods (DR-4).
Tests (tests/docs/test_collect.py): tally by kind; nested table found recursively; links in a section; containment query; query-vs-partition distinction. Depends on node table + inline nodes.
