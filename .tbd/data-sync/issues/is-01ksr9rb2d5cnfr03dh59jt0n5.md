---
type: is
id: is-01ksr9rb2d5cnfr03dh59jt0n5
title: "Phase 6: Density-invariant TextDoc.blocks() (tight flag on list, no spacing-driven decomposition)"
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
created_at: 2026-05-28T22:02:23.693Z
updated_at: 2026-05-29T06:31:32.788Z
closed_at: 2026-05-29T06:31:32.788Z
close_reason: "Phase 6: blocks() is density-invariant (one list with N list_items for tight and loose); Block.tight records CommonMark density. Test added."
---
Density-invariant lists: tight vs. loose markdown must produce identical tallies.

Once Phase 5 lands, this is mostly free — marko already produces List → ListItem children regardless of blank-line density. Remaining work:

Files:
- src/chopdiff/docs/block_tree.py — when building Block from a marko List, carry tight=True/False (CommonMark notion; marko sets List.tight after parse). Decide whether to expose as Block.tight (extra field) or attribute through a derived helper.
- src/chopdiff/docs/text_doc.py — same density invariance must hold at the paragraph view boundary: TextDoc.from_text still blank-line-splits into Paragraphs (editing view) so a loose list becomes N paragraphs there — that's by design. Document the contract clearly.

Tests:
- New test_density_invariance: '- a\n- b\n- c' vs '- a\n\n- b\n\n- c' both produce identical TextDoc.blocks() counts and structures (one list with three list_items). Tally invariance is the explicit assertion.

Deps: depends on chopdiff-1x4u (the refactor).
