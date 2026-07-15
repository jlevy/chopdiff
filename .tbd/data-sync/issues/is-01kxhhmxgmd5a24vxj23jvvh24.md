---
type: is
id: is-01kxhhmxgmd5a24vxj23jvvh24
title: "R7: Harden the standalone OpenAI example"
kind: task
status: closed
priority: 2
version: 3
labels:
  - review-finding
dependencies: []
parent_id: is-01kxhh1t7n4zpy9x8pqtwh9fye
created_at: 2026-07-15T00:08:26.388Z
updated_at: 2026-07-15T00:29:46.302Z
closed_at: 2026-07-15T00:29:46.301Z
close_reason: Pinned and locked the standalone script under the project cutoff, added full annotations and atomic output, and validated isolated execution plus vulnerability audit
---
Remove unpinned zero-install dependency resolution, add complete annotations, and use atomic output without expanding Chopdiff runtime dependencies.
