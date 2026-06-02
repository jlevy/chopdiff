---
type: is
id: is-01kt31ban660t6ex1vjx05mrgs
title: "C1: Introduce immutable DocumentSnapshot; freeze/read-protect Node/Block/NodeTable projections"
kind: feature
status: open
priority: 2
version: 3
spec_path: docs/project/review/senior-engineering-review-doc-model-v0.3.1.md
labels: []
dependencies:
  - type: blocks
    target: is-01kt31baz91ypbx3z4qm6209g8
  - type: blocks
    target: is-01kt31bbfyavhq9ex9rtacaynq
parent_id: is-01kt319dt4d9cykh6kep8x2z86
created_at: 2026-06-02T02:07:07.429Z
updated_at: 2026-06-02T02:07:25.977Z
---
Findings 7 (P1/P2) + section 5.8/10.1. Cached projections are mutable: node_table() returns the cached NodeTable, collect() returns shared Node objects, blocks() returns Block dataclasses that are shared mutable (blocks()/links() already return shallow copies, so this is partially mitigated). Introduce a frozen, source-backed DocumentSnapshot owning blocks/node_table/sections/interval_index, with collect()/graph(). TextDoc stays the mutable editing view; edits produce a new snapshot. Large public-API change -> PRODUCT DECISION REQUIRED on the public surface (snapshot() vs keeping methods on TextDoc).
