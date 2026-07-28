---
type: is
id: is-01kykpw1x7ysr0rdg4yw5fjy1c
title: Diagnose macOS Trash blocked by NFS-backed symlink
kind: bug
status: closed
priority: 1
version: 3
labels: []
dependencies: []
created_at: 2026-07-28T06:33:53.827Z
updated_at: 2026-07-28T06:34:50.289Z
closed_at: 2026-07-28T06:34:50.285Z
close_reason: "Confirmed root cause: Finder and trash operations block while resolving a symlink into a hard,nointr NFS mount whose localhost server is gone and whose status is not responding. Finder stack sample shows alias/symlink realpath and remote-volume enumeration blocked. No Trash contents were modified by this diagnostic."
---
Determine why Finder cannot open Trash while a trash process is stuck on a symlink into the finterm NFS mount. Diagnose without emptying or deleting Trash contents.
