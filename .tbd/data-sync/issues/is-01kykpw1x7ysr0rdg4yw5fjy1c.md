---
type: is
id: is-01kykpw1x7ysr0rdg4yw5fjy1c
title: Diagnose macOS Trash blocked by NFS-backed symlink
kind: bug
status: closed
priority: 1
version: 6
labels: []
dependencies: []
created_at: 2026-07-28T06:33:53.827Z
updated_at: 2026-07-28T06:38:41.385Z
closed_at: 2026-07-28T06:38:41.384Z
close_reason: Force-unmounted the dead finterm NFS mount, verified it is absent, confirmed Finder left uninterruptible I/O, confirmed trash listing responds with zero bytes, and reopened Trash in Finder. No files were removed by this fix.
---
Determine why Finder cannot open Trash while a trash process is stuck on a symlink into the finterm NFS mount. Diagnose without emptying or deleting Trash contents.
