---
type: is
id: is-01kxhhmw017jc4vef551kh6r2h
title: "R4: Apply collection ignore matchers in token sequence filters"
kind: bug
status: closed
priority: 2
version: 3
labels:
  - review-finding
dependencies: []
parent_id: is-01kxhh1t7n4zpy9x8pqtwh9fye
created_at: 2026-07-15T00:08:24.832Z
updated_at: 2026-07-15T00:16:26.301Z
closed_at: 2026-07-15T00:16:26.301Z
close_reason: Fixed token multiplicity checks and collection-based ignore matching; full tests and lint pass
---
`TokenMatcher` allows `list[str]`, but the implementation checks `str`, so collection-based ignore rules are silently skipped. Align runtime logic, types, docs, and tests.
