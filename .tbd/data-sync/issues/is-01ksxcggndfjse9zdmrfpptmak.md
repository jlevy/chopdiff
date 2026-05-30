---
type: is
id: is-01ksxcggndfjse9zdmrfpptmak
title: Node table build + lazy cache on TextDoc (docs/node_table.py)
kind: task
status: closed
priority: 2
version: 9
spec_path: docs/project/specs/active/plan-2026-05-29-unified-document-model.md
labels: []
dependencies:
  - type: blocks
    target: is-01ksxcgh4v79ra9wbtavbq1fms
  - type: blocks
    target: is-01ksxch8y5z7y5ypw1ff58ck08
  - type: blocks
    target: is-01ksxch9bgx0cncw3d0pn3wya9
  - type: blocks
    target: is-01ksxch9qc6yks6zwz9z4en15e
  - type: blocks
    target: is-01ksxcha36288d2jvy8v11a0sw
  - type: blocks
    target: is-01ksxchatt9gc8cpg1c5zv5y3z
parent_id: is-01kss8gdn83f47wbrg3jve028r
created_at: 2026-05-30T21:26:45.165Z
updated_at: 2026-05-30T22:48:47.040Z
closed_at: 2026-05-30T22:48:47.040Z
close_reason: null
---
New src/chopdiff/docs/node_table.py. build_node_table(doc) -> NodeTable from recursive block tree (markdown), sections (document), paragraph/sentence editing view (textual).
- Stable ids (pre-order); wire parent/children; set layer, source_span, attrs (heading level, list ordered/tight, link url/title).
- NodeTable: nodes dict[id,Node], roots, indexes (by_kind, by_layer, interval lookup).
- Lazily cache on TextDoc keyed to immutable source_text (contract: do not reassign source_text).
Tests (tests/docs/test_node_table.py): ids stable; parent/children; layer tagging; span round-trips source slice. Depends on Node + recursive tree.
