---
type: is
id: is-01ksr9rbbqj317g4q4nsmkw65n
title: "Phase 6: Section.blocks() for per-section structural slicing"
kind: feature
status: open
priority: 2
version: 4
spec_path: docs/project/specs/active/plan-2026-05-26-block-aware-doc.md
labels: []
dependencies:
  - type: blocks
    target: is-01ksr9rbyvszrytbtv8c1t97kg
parent_id: is-01kshh1bwwdg57dx0yybgm8b9m
created_at: 2026-05-28T22:02:23.991Z
updated_at: 2026-05-28T22:03:43.266Z
---
Per-section structural blocks: scope blocks() to a section.

Files:
- src/chopdiff/docs/text_doc.py — add Section.blocks() that returns the slice of the full block tree whose spans fall within section.span. Or: re-parse only the section's text (might be cleaner since marko's parse on the section produces its own block tree).
- Consider: an iterator helper on Section that walks ONLY blocks at the top level of the section's content (excluding the heading), filtered by BlockType.

Tests:
- New test_section_blocks: section.blocks() returns the right top-level types; per-section block-type Counter works; spans are inside section.span.

Deps: depends on chopdiff-1x4u.
