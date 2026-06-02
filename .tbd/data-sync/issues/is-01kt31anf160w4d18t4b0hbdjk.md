---
type: is
id: is-01kt31anf160w4d18t4b0hbdjk
title: "B1: Add an interval index for cross-layer containment/overlap queries"
kind: feature
status: closed
priority: 1
version: 5
spec_path: docs/project/review/senior-engineering-review-doc-model-v0.3.1.md
labels: []
dependencies:
  - type: blocks
    target: is-01kt31anq6fgamdfxh6061ycqq
  - type: blocks
    target: is-01kt31anzhe1ygy2xtz3d5afw1
  - type: blocks
    target: is-01kt31ban660t6ex1vjx05mrgs
parent_id: is-01kt319dt4d9cykh6kep8x2z86
created_at: 2026-06-02T02:06:45.729Z
updated_at: 2026-06-02T05:18:31.284Z
closed_at: 2026-06-02T05:18:31.284Z
close_reason: IntervalIndex added; node-table build is now linear (was O(inline*nodes))
---
Finding 8 (P1/P2). node_table.py builds inline nodes by calling _find_innermost_block / _find_deepest_section / _find_sentence_node per inline item, each a full scan: O(inline_items x nodes). Add an IntervalIndex built once per parse, exposing innermost(offset, layer/kind), contained_by(span, layer), overlapping(span, layer). Route node-table parent/section/sentence attribution through it. This is the substrate that B2 and B3 build on. Add microbenchmarks for link-heavy / large docs.
