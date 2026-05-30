---
type: is
id: is-01ksw0warj418pwxnzds00swaa
title: "P1e: replace library asserts with explicit exceptions"
kind: task
status: closed
priority: 1
version: 2
spec_path: docs/project/specs/active/plan-2026-05-26-robustness-hardening.md
labels: []
dependencies: []
parent_id: is-01kstdjj19rhp9k8qqw7sv81vk
created_at: 2026-05-30T08:44:14.994Z
updated_at: 2026-05-30T09:00:40.387Z
closed_at: 2026-05-30T09:00:40.387Z
close_reason: All library validation asserts converted to ValueError/AssertionError across token_diffs, text_node, sliding_transforms; remaining asserts are inline tests.
---
Files: token_diffs.py (DiffOp.__post_init__ invariants; TokenDiff.filter() postconditions; diff_wordtoks difflib check), divs/text_node.py (content_end>=0), transforms/sliding_transforms.py (3 left_size() checks). Fix: raise ValueError for input validation; raise AssertionError(msg) only for true internal invariants. Keep harmless internal asserts. TDD: invalid inputs raise ValueError (not bare assert).
