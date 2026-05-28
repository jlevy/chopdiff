---
type: is
id: is-01ksr9rbn9bh3t5tjjy1m9eyyj
title: "Phase 6: Derived element/tally rollups (no stored counts; flexible block/section/doc level)"
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
created_at: 2026-05-28T22:02:24.296Z
updated_at: 2026-05-28T22:03:43.564Z
---
Derived element/tally rollups — calculated fields, never stored counts.

Files:
- src/chopdiff/docs/text_doc.py — exposes (or documents) the canonical pattern: 'Counter(b.block_type for b in section.blocks())' to count by type; 'sum(len(b.links()) for b in section.blocks())' to count links per section.

Decide if any thin wrappers are worth it (e.g. Section.block_type_counts() / TextDoc.block_type_counts()) — the design principle is to keep these as derivable views, not stored fields. A one-line @property over the existing iterators is acceptable.

Tests:
- test_derived_tallies: per-section counts of paragraph/list/table; verify that adding/removing content propagates without manual reindexing; verify the principle 'no stored counts anywhere'.

Deps: depends on chopdiff-1x4u.
