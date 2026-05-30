---
type: is
id: is-01kss8gdybwa8q09qftg1nfe54
title: Settle unified-document-model design decisions (node-set vs tree, projection vs runtime, rollup surface, detail axis, schema home, phase-1 scope, reference selector set)
kind: task
status: open
priority: 1
version: 5
spec_path: docs/project/specs/active/plan-2026-05-29-unified-document-model.md
labels: []
dependencies: []
parent_id: is-01kss8gdn83f47wbrg3jve028r
created_at: 2026-05-29T06:59:50.347Z
updated_at: 2026-05-30T16:42:02.143Z
---
See 'Open decisions' in the spec. Blocks all implementation.

## Notes

Settled 2026-05-29: DR-1 node-table-with-views; DR-2 DocOverview projection of TextDoc; DR-3 Pydantic schema authoring (JSON Schema/Zod later); DR-4 one general collect() rollup primitive, no blessed per-kind shortcuts. Remaining open: 4 (detail axis), 6 (phase-1 scope), 7 (reference selectors), 8 (caching), 9 (list-item paragraph counting).
