---
type: is
id: is-01kt31a7sptqjfs8jt0710rydp
title: "A5: Replace 'node table is canonical' wording with 'projection over offset substrate'"
kind: task
status: closed
priority: 2
version: 3
spec_path: docs/project/review/senior-engineering-review-doc-model-v0.3.1.md
labels: []
dependencies: []
parent_id: is-01kt319dt4d9cykh6kep8x2z86
created_at: 2026-06-02T02:06:31.733Z
updated_at: 2026-06-02T04:09:08.649Z
closed_at: 2026-06-02T04:09:08.649Z
close_reason: "node.py/node_table.py/CHANGELOG reworded: offset space canonical, node table is a projection"
---
Finding P2 / section 5.1. node.py:105 (NodeTable docstring) and node_table.py:9 call the node table 'the canonical normalized form'. The endorsed model is: source string + offset space is canonical; the node table is the id-addressed query/serialization projection. Update these docstrings, the changelog, and any spec remnants. Wording affects how future contributors build features.
