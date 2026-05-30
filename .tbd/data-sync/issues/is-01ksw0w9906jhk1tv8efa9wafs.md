---
type: is
id: is-01ksw0w9906jhk1tv8efa9wafs
title: "P1a: filtered_transform enforces diff_filter without windowing"
kind: bug
status: open
priority: 1
version: 1
spec_path: docs/project/specs/active/plan-2026-05-26-robustness-hardening.md
labels: []
dependencies: []
parent_id: is-01kstdjj19rhp9k8qqw7sv81vk
created_at: 2026-05-30T08:44:13.472Z
updated_at: 2026-05-30T08:44:13.472Z
---
File: src/chopdiff/transforms/sliding_transforms.py, fn filtered_transform(). Bug: the no-window path (if not windowing or not windowing.size) returns transform_func(doc) directly, skipping the diff_filter enforcement that lives only inside transform_and_check_diff (windowed path). Fix: extract a single transform-and-filter helper applied to the whole-doc result too. TDD: failing test that a reject-all filter keeps the original on windowing=None and WINDOW_NONE; also passes with a real window.
