---
type: is
id: is-01ksxcgg8zh17bn34e56pq0b38
title: base_blocks() sequential partition (docs/base_blocks.py)
kind: task
status: closed
priority: 2
version: 4
spec_path: docs/project/specs/active/plan-2026-05-29-unified-document-model.md
labels: []
dependencies:
  - type: blocks
    target: is-01ksxch9qc6yks6zwz9z4en15e
parent_id: is-01kss8gdn83f47wbrg3jve028r
created_at: 2026-05-30T21:26:44.767Z
updated_at: 2026-05-30T22:46:44.004Z
closed_at: 2026-05-30T22:46:44.003Z
close_reason: null
---
New src/chopdiff/docs/base_blocks.py. base_blocks(tree|text, *, item_partition_depth=6) -> list[BaseBlock(block, depth)].
- List items decompose to N nesting levels (default 6; -1 unlimited; 0 unsplit); blockquotes always atomic.
- Invariants: ordered; non-overlapping; complete cover; reassembly reproduces document exact except normalized paragraph-break whitespace; exact reconstruction via source_span.
Tests (tests/docs/test_base_blocks.py): cover/non-overlap/order; depth annotation; item_partition_depth modes; reassembly. Depends on recursive tree.
