---
type: is
id: is-01ksqrs8wnrxdgyp0ezdbphfaj
title: "Phase 5: Refactor chopdiff to consume flowmark block spans (delete classify_block, block_tree regex scanner)"
kind: task
status: closed
priority: 1
version: 9
spec_path: docs/project/specs/active/plan-2026-05-26-block-aware-doc.md
labels: []
dependencies:
  - type: blocks
    target: is-01ksr9ras2m1z4333mb1v5g9jm
  - type: blocks
    target: is-01ksr9rb2d5cnfr03dh59jt0n5
  - type: blocks
    target: is-01ksr9rbbqj317g4q4nsmkw65n
  - type: blocks
    target: is-01ksr9rbn9bh3t5tjjy1m9eyyj
parent_id: is-01kshh1bwwdg57dx0yybgm8b9m
created_at: 2026-05-28T17:05:48.437Z
updated_at: 2026-05-29T06:31:32.277Z
closed_at: 2026-05-29T06:31:32.277Z
close_reason: "Phase 5 done: deleted regex block scanner/classify_block/markdown_parser singleton; block_tree walks flowmark's annotated tree via block_span; net -103 LOC. 144 tests green, lint clean. Reference-link + no-blank-line bugs fixed by construction."
---
Mechanical refactor once flowmark ships block spans. Goal: net negative code in chopdiff.

Files to touch:
- src/chopdiff/docs/block_types.py — collapse to: BlockType enum (unchanged values for now); ONE dict[type[marko.BlockElement], BlockType] mapping. Delete classify_block, delete @cache markdown_parser singleton.
- src/chopdiff/docs/block_tree.py — delete _LIST_MARKER_RE, _FENCE_RE, _THEMATIC_BREAK_RE, _ATX_HEADING_RE, _SETEXT_UNDERLINE_RE, _HARD_STARTERS, _line_kind, _parse_region, _parse_list_items, _parse_nested_lists. Replace parse_blocks(text) with: parse the text once via flowmark.flowmark_markdown(), walk via flowmark.markdown_ast.walk_elements, and build Block(type, span, children) from each block element's class and .span.
- src/chopdiff/docs/text_doc.py — Paragraph.block_type: parse paragraph fragment via flowmark, take the first non-BlankLine child's class through the mapping table. Drop the classify_block import.
- Imports / re-exports updated to keep public surface unchanged (BlockType, Block, parse_blocks).

Tests:
- tests/docs/test_blocks.py — keep all parity-vs-marko tests; they should pass with no edits (and the no-blank-line tests now pass for free because marko makes the decision).
- tests/docs/test_block_types.py — keep all; check that classify-via-mapping returns the same BlockType values.
- Full chopdiff suite must stay green (currently 137 tests).
- Confirm the two senior-review correctness bugs from PR #12 (reference-link drop, no-blank-line block boundaries) stay fixed by construction.

API surface stays additive — TextDoc.blocks() shape unchanged. Internal-only refactor.
