---
type: is
id: is-01ksxcgfvsx7mha7pwdg5b95pp
title: Make structural block tree fully recursive (docs/block_tree.py)
kind: task
status: closed
priority: 2
version: 6
spec_path: docs/project/specs/active/plan-2026-05-29-unified-document-model.md
labels: []
dependencies:
  - type: blocks
    target: is-01ksxcgg8zh17bn34e56pq0b38
  - type: blocks
    target: is-01ksxcggndfjse9zdmrfpptmak
  - type: blocks
    target: is-01ksxch9qc6yks6zwz9z4en15e
parent_id: is-01kss8gdn83f47wbrg3jve028r
created_at: 2026-05-30T21:26:44.344Z
updated_at: 2026-05-30T22:46:43.628Z
closed_at: 2026-05-30T22:46:43.628Z
close_reason: null
---
Edit src/chopdiff/docs/block_tree.py _blocks_from so every container (Quote/blockquote, ListItem) populates ALL block children recursively, not just nested lists. Keep Block shape and top-level blocks() ordering; preserve density invariance. Add a depth-aware walk helper to support base_blocks.
Tests (tests/docs/test_blocks.py): table/code nested in blockquote or list_item appears as a Block; loose vs tight lists yield identical structure/tallies.
