---
type: is
id: is-01ksr9rbyvszrytbtv8c1t97kg
title: "Phase 6: End-to-end example for normalized form (section tree, block-type slices, link rollups, density-invariant tallies)"
kind: task
status: closed
priority: 3
version: 4
spec_path: docs/project/specs/active/plan-2026-05-26-block-aware-doc.md
labels: []
dependencies: []
parent_id: is-01kshh1bwwdg57dx0yybgm8b9m
created_at: 2026-05-28T22:02:24.602Z
updated_at: 2026-05-29T06:31:33.782Z
closed_at: 2026-05-29T06:31:33.782Z
close_reason: "Phase 6: examples/normalized_form.py exercises section tree, per-section block-type slices, link rollups, and density-invariant tallies end to end."
---
End-to-end runnable example demonstrating the full normalized form:

examples/normalized_form.py:
- Build a TextDoc from a representative document (sections, lists both ordered and bullet, table, code block, links).
- Print section tree.
- Print block-type slices per section (no headings, only paragraphs and lists, etc.).
- Print all links rolled up per section.
- Print density-invariant tally: count of lists, list items, tables, etc.

Should run end-to-end with 'uv run examples/normalized_form.py' against the next chopdiff release.

Deps: blocked on all four Phase 6 features (chopdiff-3ygz, chopdiff-3bdw, chopdiff-kvsg, chopdiff-1aew).
