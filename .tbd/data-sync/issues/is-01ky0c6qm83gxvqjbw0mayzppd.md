---
type: is
id: is-01ky0c6qm83gxvqjbw0mayzppd
title: Audit safe disk-space quick wins
kind: task
status: closed
priority: 1
version: 3
labels: []
dependencies: []
created_at: 2026-07-20T18:21:55.207Z
updated_at: 2026-07-20T18:24:45.178Z
closed_at: 2026-07-20T18:24:45.177Z
close_reason: Staged 3.06 GB of inactive reconstructible npm, Playwright, .venv, and node_modules data using trash only; verified 4.04 GB total in Trash. Preserved active uv/pnpm caches, worktrees, and all agent history/state.
---
Remeasure disk after Trash was emptied, identify inactive reconstructible caches and dependency artifacts with dust and live-writer checks, and stage only clearly safe candidates using trash.
