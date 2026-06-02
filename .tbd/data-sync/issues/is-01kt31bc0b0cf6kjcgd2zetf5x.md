---
type: is
id: is-01kt31bc0b0cf6kjcgd2zetf5x
title: "C6: Add overlap relation + partial-overlap semantics for synthetic layer; add edge-case + perf test corpus"
kind: task
status: open
priority: 3
version: 1
spec_path: docs/project/review/senior-engineering-review-doc-model-v0.3.1.md
labels: []
dependencies: []
parent_id: is-01kt319dt4d9cykh6kep8x2z86
created_at: 2026-06-02T02:07:08.811Z
updated_at: 2026-06-02T02:07:08.811Z
---
P2/P3 + section 8. NodeTable.containing/contained_by express full containment only; synthetic regions may partially overlap markdown blocks -> add overlap relation (ties to B1/B2) and decide partial-overlap validity. Add targeted tests: link/image edge cases (duplicate URLs, URL-substring, nested brackets, titles, reference-style images, escaped parens, bare URLs by punctuation), headings-in-code-fence, repeated-text SpanRef disambiguation, Unicode offsets; and perf budgets for from_text/blocks/node_table/graph/collect.
