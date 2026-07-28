---
type: is
id: is-01kykq6g450nbb3w2h7v8vqq4b
title: Stage verified disk cleanup candidates with trash
kind: task
status: closed
priority: 1
version: 3
labels: []
dependencies: []
created_at: 2026-07-28T06:39:36.067Z
updated_at: 2026-07-28T06:42:08.048Z
closed_at: 2026-07-28T06:42:08.047Z
close_reason: Staged 3,028,344,832 bytes across 11 verified reconstructible or merged-worktree paths using trash only. Listed Trash contents, verified all source paths moved, preserved agent logs/state and active worktrees, excluded active uv/Superhuman/current project data, and kept NFS unmounted.
---
Keep the NFS bundle mount detached. Revalidate and stage only ignored failed outputs, reconstructible dependencies, and clean merged Codex worktrees with trash; preserve agent logs/state and active worktrees.
