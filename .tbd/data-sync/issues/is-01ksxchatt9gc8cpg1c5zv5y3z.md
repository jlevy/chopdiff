---
type: is
id: is-01ksxchatt9gc8cpg1c5zv5y3z
title: "Render helpers: data-node-id / data-source-span (docs/render.py)"
kind: task
status: closed
priority: 2
version: 2
spec_path: docs/project/specs/active/plan-2026-05-29-unified-document-model.md
labels: []
dependencies: []
parent_id: is-01kss8gdn83f47wbrg3jve028r
created_at: 2026-05-30T21:27:11.961Z
updated_at: 2026-05-31T06:45:17.859Z
closed_at: 2026-05-31T06:45:17.859Z
close_reason: Render helpers data-node-id/data-source-span in docs/render.py
---
New src/chopdiff/docs/render.py: helpers to annotate rendered HTML/Markdown with data-node-id and data-source-span so a rendered selection resolves to a node and thence to source (pairs with SpanRef).
Tests (tests/docs/test_render.py): attributes present and resolvable back through the node table. Depends on node table.
