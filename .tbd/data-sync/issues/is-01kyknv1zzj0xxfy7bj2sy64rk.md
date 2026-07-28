---
type: is
id: is-01kyknv1zzj0xxfy7bj2sy64rk
title: Audit and clean stale Codex worktrees
kind: task
status: closed
priority: 1
version: 3
labels: []
dependencies: []
created_at: 2026-07-28T06:15:52.574Z
updated_at: 2026-07-28T06:26:21.755Z
closed_at: 2026-07-28T06:26:21.750Z
close_reason: Audit completed. Identified about 4.5 GiB of safe trash-only candidates, preserved open or active worktrees, and documented a stuck trash process on an NFS-backed symlink. No cleanup was staged because this request was for review.
---
Measure current disk use, identify inactive clean Codex worktrees whose commits are already merged, and stage only verified safe worktrees and reconstructible caches using trash.
