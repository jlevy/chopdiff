---
type: is
id: is-01ksydxww7s71ab6exyr7r7323
title: base_blocks() emits overlapping parent+nested list-item spans (not a partition)
kind: bug
status: open
priority: 1
version: 1
spec_path: docs/project/specs/active/plan-2026-05-29-unified-document-model.md
labels: []
dependencies: []
created_at: 2026-05-31T07:10:46.662Z
updated_at: 2026-05-31T07:10:46.662Z
---
Review P1. base_blocks.py _emit_list_item appends a parent list_item whose span includes nested items, then appends nested items again -> overlap, breaks non-overlap/cover invariant (spec section 6). Fix: a list_item with nested lists emits a base block covering only its OWN (non-nested) content (span end = start of first nested list, trailing ws trimmed); nested items follow at depth+1. Add pairwise non-overlap + reconstruction tests for nested lists.
