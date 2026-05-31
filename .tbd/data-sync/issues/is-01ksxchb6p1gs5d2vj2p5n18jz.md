---
type: is
id: is-01ksxchb6p1gs5d2vj2p5n18jz
title: Round-trip + golden tests; standalone JSON Schema export
kind: task
status: closed
priority: 2
version: 2
spec_path: docs/project/specs/active/plan-2026-05-29-unified-document-model.md
labels: []
dependencies: []
parent_id: is-01kss8gdn83f47wbrg3jve028r
created_at: 2026-05-30T21:27:12.342Z
updated_at: 2026-05-31T06:45:18.214Z
closed_at: 2026-05-31T06:45:18.213Z
close_reason: Golden + round-trip tests; committed doc_graph_schema.json with sync test
---
Golden/snapshot test of graph() output for a representative doc (tests/docs/test_doc_graph_golden.py); round-trip node ids <-> views; emit the standalone language-neutral JSON Schema from the Pydantic models (committed file) with a test that it stays in sync (decision 5). Depends on schema + graph.
