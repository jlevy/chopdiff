---
type: is
id: is-01ksxch9qc6yks6zwz9z4en15e
title: Wire node table into TextDoc; Section.blocks() cache; supersede block_type_counts; exports
kind: task
status: closed
priority: 2
version: 3
spec_path: docs/project/specs/active/plan-2026-05-29-unified-document-model.md
labels: []
dependencies: []
parent_id: is-01kss8gdn83f47wbrg3jve028r
created_at: 2026-05-30T21:27:10.827Z
updated_at: 2026-05-30T23:00:58.887Z
closed_at: 2026-05-30T23:00:58.887Z
close_reason: null
---
In text_doc.py / docs/__init__.py:
- Add TextDoc.node_table() (cached), TextDoc.base_blocks(), TextDoc.collect(), TextDoc.span_ref(...).
- Make Section.blocks() slice the cached node table instead of re-parsing per section.
- Reimplement block_type_counts() as a thin wrapper over collect() (keep for back-compat, mark superseded; note backward-compat in changelog).
- Export Node, NodeKind, Layer, SpanRef, base_blocks from chopdiff.docs.
Phase-1 integration tests: nested counting/locating; per-section value+count rollups; density invariance; section slicing; SpanRef round-trips survive reparse. Depends on recursive tree, node table, collect, span_ref, base_blocks, inline.
