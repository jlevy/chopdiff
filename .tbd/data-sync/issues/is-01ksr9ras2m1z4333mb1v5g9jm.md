---
type: is
id: is-01ksr9ras2m1z4333mb1v5g9jm
title: "Phase 6: Add BlockType.ordered_list; carry List.ordered through to TextDoc"
kind: feature
status: closed
priority: 2
version: 5
spec_path: docs/project/specs/active/plan-2026-05-26-block-aware-doc.md
labels: []
dependencies:
  - type: blocks
    target: is-01ksr9rbyvszrytbtv8c1t97kg
parent_id: is-01kshh1bwwdg57dx0yybgm8b9m
created_at: 2026-05-28T22:02:23.393Z
updated_at: 2026-05-29T06:31:32.534Z
closed_at: 2026-05-29T06:31:32.533Z
close_reason: "Phase 6: BlockType.ordered_list added, carried from marko List.ordered via block_type_for(); list is bullet-only. Tests added."
---
After Phase 5 refactor, BlockType.ordered_list falls out as a trivial addition: the mapping table separates marko's List(ordered=True) from List(ordered=False).

Files:
- src/chopdiff/docs/block_types.py — add BlockType.ordered_list = 'ordered_list'. Mapping: List with .ordered=True → ordered_list; .ordered=False → list. Both kinds of children stay BlockType.list_item; ordered-ness is a property of the parent list.

Tests:
- tests/docs/test_blocks.py — add: '1. one\n2. two' → top-level [ordered_list]; tight ordered list decomposes into [list_item, list_item]; nested ordered inside bullet (and vice versa).
- tests/docs/test_block_types.py — Paragraph.block_type for an ordered-list block returns BlockType.ordered_list.

Semi-breaking note for CHANGELOG: callers matching BlockType.list expecting BOTH kinds will now miss ordered lists. Document the migration as part of the next minor release.
