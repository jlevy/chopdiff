---
type: is
id: is-01kt31anq6fgamdfxh6061ycqq
title: "B2: First-class interval query relations in collect(): within / overlaps (+ rename scope->subtree_of)"
kind: feature
status: closed
priority: 1
version: 5
spec_path: docs/project/review/senior-engineering-review-doc-model-v0.3.1.md
labels: []
dependencies:
  - type: blocks
    target: is-01kt31baz91ypbx3z4qm6209g8
  - type: blocks
    target: is-01kt31bc0b0cf6kjcgd2zetf5x
parent_id: is-01kt319dt4d9cykh6kep8x2z86
created_at: 2026-06-02T02:06:45.989Z
updated_at: 2026-06-02T05:27:08.535Z
closed_at: 2026-06-02T05:27:08.535Z
close_reason: collect() gained subtree_of/within/overlaps; scope/contains kept as deprecated aliases
---
Finding 2 (P1) + section 5.3. collect(scope=...) is parent/child subtree only (collect.py:51-52,93); 'contains' supports full containment only. Add explicit axes: subtree_of (within-layer tree), within (offset containment, incl. section_id -> cross-layer rollups), overlaps (partial overlap). Keep scope as a deprecated alias for subtree_of. This is what makes doc.collect(within=section_id, kinds={link}) work. Coordinate the public query surface with A2/C2.
