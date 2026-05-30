---
type: is
id: is-01ksw0wbw7nffbs02gfpyqxd17
title: "P1h: TokenDiff.apply_to validates source identity"
kind: bug
status: open
priority: 1
version: 1
spec_path: docs/project/specs/active/plan-2026-05-26-robustness-hardening.md
labels: []
dependencies: []
parent_id: is-01kstdjj19rhp9k8qqw7sv81vk
created_at: 2026-05-30T08:44:16.134Z
updated_at: 2026-05-30T08:44:16.134Z
---
File: src/chopdiff/docs/token_diffs.py, fn apply_to(). Bug: checks only length, then ignores original_wordtoks entirely (output rebuilt from op.right; original_index is dead code) -> a diff applied to a different same-length list silently yields wrong output. Fix: verify each consumed op.left segment equals original_wordtoks[idx:idx+len(op.left)]; raise ValueError with offset context; use the cursor. TDD: same-length-but-mismatched source raises.
