---
type: is
id: is-01kxhhmt8t68wg30se0mnyr0ee
title: "R1: Preserve token multiplicity in remove-only diff filters"
kind: bug
status: closed
priority: 1
version: 3
labels:
  - review-finding
dependencies: []
parent_id: is-01kxhh1t7n4zpy9x8pqtwh9fye
created_at: 2026-07-15T00:08:23.065Z
updated_at: 2026-07-15T00:16:26.289Z
closed_at: 2026-07-15T00:16:26.288Z
close_reason: Fixed token multiplicity checks and collection-based ignore matching; full tests and lint pass
---
`removes_words` and `removes_word_lemmas` compare sets, so inserting duplicate words is accepted. Use multiset semantics and regression tests.
