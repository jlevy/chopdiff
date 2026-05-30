---
type: is
id: is-01ksxch9bgx0cncw3d0pn3wya9
title: SpanRef type + resolution (docs/span_ref.py)
kind: task
status: open
priority: 2
version: 3
spec_path: docs/project/specs/active/plan-2026-05-29-unified-document-model.md
labels: []
dependencies:
  - type: blocks
    target: is-01ksxch9qc6yks6zwz9z4en15e
  - type: blocks
    target: is-01ksxcha36288d2jvy8v11a0sw
parent_id: is-01kss8gdn83f47wbrg3jve028r
created_at: 2026-05-30T21:27:10.448Z
updated_at: 2026-05-30T21:27:29.401Z
---
New src/chopdiff/docs/span_ref.py. SpanRef dataclass {exact:str, prefix:str|None, suffix:str|None, start:int|None, end:int|None}.
- SpanRef.from_node(node, doc): fill exact quote + prefix/suffix context + offsets.
- resolve(span_ref, doc) -> Node|span: exact offset fast path, then quote search with prefix/suffix fuzzy re-anchor, updating offsets.
- to_persisted(): drop transient offsets/node_id, keep quote canonical. Optional to_text_fragment() (#:~:text=).
Tests (tests/docs/test_span_ref.py): node->ref->resolve round-trip; survives reparse; fuzzy re-anchor after edit; persisted form quote-canonical. Depends on node table.
