---
type: is
id: is-01kxhk31wxk6543tq60b88c2vf
title: "R8: Isolate project uv policy from user config"
kind: bug
status: closed
priority: 1
version: 3
labels: []
dependencies: []
parent_id: is-01kxhh1t7n4zpy9x8pqtwh9fye
created_at: 2026-07-15T00:33:38.204Z
updated_at: 2026-07-15T00:35:55.885Z
closed_at: 2026-07-15T00:35:55.884Z
close_reason: Isolated Make and CI with a tested project policy mirror; ordinary make now passes despite conflicting user uv settings
---
Routine locked uv commands fail when uv merges unrelated user-level exclude-newer-package entries. Add and validate an explicit project policy mirror for Make/CI/direct developer commands without weakening the canonical pyproject cutoff.
