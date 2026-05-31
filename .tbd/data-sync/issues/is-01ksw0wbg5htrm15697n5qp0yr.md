---
type: is
id: is-01ksw0wbg5htrm15697n5qp0yr
title: "P1g: word-window stitching ValueError format + alignment-failure policy"
kind: bug
status: closed
priority: 1
version: 2
spec_path: docs/project/specs/active/plan-2026-05-26-robustness-hardening.md
labels: []
dependencies: []
parent_id: is-01kstdjj19rhp9k8qqw7sv81vk
created_at: 2026-05-30T08:44:15.748Z
updated_at: 2026-05-30T08:54:14.504Z
closed_at: 2026-05-30T08:54:14.504Z
close_reason: Fixed ValueError format-string bug; added on_alignment_failure policy (raise default/skip); tests cover both.
---
File: src/chopdiff/transforms/sliding_transforms.py (stitching ~191-206). Bugs: ValueError('...%s...', n, toks) never interpolates (renders raw tuple); too-short new_wordtoks path log.error+continue silently drops a window; alignment accepts any score. Fix: f-string error; add on_alignment_failure='raise'|'skip'|'keep_original' (default raise). TDD: short-window alignment raises a readable error by default.
