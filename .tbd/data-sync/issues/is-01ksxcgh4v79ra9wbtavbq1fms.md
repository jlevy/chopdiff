---
type: is
id: is-01ksxcgh4v79ra9wbtavbq1fms
title: Inline items as nodes with parent/section/sentence (docs/node_table.py)
kind: task
status: open
priority: 2
version: 3
spec_path: docs/project/specs/active/plan-2026-05-29-unified-document-model.md
labels: []
dependencies:
  - type: blocks
    target: is-01ksxch8y5z7y5ypw1ff58ck08
  - type: blocks
    target: is-01ksxch9qc6yks6zwz9z4en15e
parent_id: is-01kss8gdn83f47wbrg3jve028r
created_at: 2026-05-30T21:26:45.659Z
updated_at: 2026-05-30T21:27:28.638Z
---
Fold existing Link/_block_links and add code-span/inline detection into the node table as inline nodes (markdown layer; kind link/code_span/...), parent=containing block node, computed section and sentence via sentence_at_offset. Reuse flowmark atomic spans for exact link spans.
Tests: inline nodes with correct parent/sentence; 'links in section N' via collect(inline=True). Depends on node table.
