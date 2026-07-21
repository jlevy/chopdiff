---
type: is
id: is-01ky12vqg6dkcy5m2hje8yzt1c
title: Explain recurring disk exhaustion
kind: task
status: closed
priority: 1
version: 3
labels: []
dependencies: []
created_at: 2026-07-21T00:57:51.877Z
updated_at: 2026-07-21T01:02:00.470Z
closed_at: 2026-07-21T01:02:00.469Z
close_reason: "Audit complete: free space fell from 9.3 to 3.1 GiB. APFS VM/swap grew about 4 GiB and active uv cache grew about 2 GiB, explaining the physical loss. Secondary logical growth includes an inactive 4.4 GB Flexdoc worktree dominated by ignored venv data and ~0.8 GB of temporary review environments. No files removed."
---
Run a read-only APFS-aware audit, compare with the prior 9.3 GiB free baseline, and rank the recurring contributors to disk exhaustion.
