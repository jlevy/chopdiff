---
type: is
id: is-01kxhhmwfywta03vfgk3cq8pev
title: "R5: Harden locked developer and CI/CD workflows"
kind: task
status: closed
priority: 1
version: 3
labels:
  - review-finding
dependencies: []
parent_id: is-01kxhh1t7n4zpy9x8pqtwh9fye
created_at: 2026-07-15T00:08:25.341Z
updated_at: 2026-07-15T00:24:10.281Z
closed_at: 2026-07-15T00:24:10.280Z
close_reason: Pinned Actions to SHAs, upgraded vetted CI tools, locked routine commands, added macOS CI, removed audit suppression, and gated publishing on lint/test/audit
---
Prevent routine local commands from silently rewriting the lock, update vetted uv and GitHub Actions pins, add representative macOS CI, and require lint/audit before publishing.
