---
type: is
id: is-01kss8gdybwa8q09qftg1nfe54
title: Settle unified-document-model design decisions (node-set vs tree, projection vs runtime, rollup surface, detail axis, schema home, phase-1 scope, reference selector set)
kind: task
status: open
priority: 1
version: 7
spec_path: docs/project/specs/active/plan-2026-05-29-unified-document-model.md
labels: []
dependencies: []
parent_id: is-01kss8gdn83f47wbrg3jve028r
created_at: 2026-05-29T06:59:50.347Z
updated_at: 2026-05-30T17:01:40.337Z
---
See 'Open decisions' in the spec. Blocks all implementation.

## Notes

Settled: DR-1 node-table; DR-2 projection; DR-3 Pydantic authoring; DR-4 single collect() primitive (no shortcuts); DR-5 composable include-layers for payload (no Detail ladder); plus 6 (minimal phase-1 scope), 8 (lazy-cache), 9 (count list-item wrapper paragraphs). ONLY OPEN: 7 (reference selectors) - recommendation: quote(exact+prefix/suffix) canonical + offset hint, Unicode code points, Chrome-Text-Fragment convertible; awaiting final confirm.
