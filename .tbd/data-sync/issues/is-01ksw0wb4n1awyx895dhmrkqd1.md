---
type: is
id: is-01ksw0wb4n1awyx895dhmrkqd1
title: "P1f: WindowSettings invariants + falsy WINDOW_NONE"
kind: bug
status: closed
priority: 1
version: 2
spec_path: docs/project/specs/active/plan-2026-05-26-robustness-hardening.md
labels: []
dependencies: []
parent_id: is-01kstdjj19rhp9k8qqw7sv81vk
created_at: 2026-05-30T08:44:15.381Z
updated_at: 2026-05-30T08:54:14.178Z
closed_at: 2026-05-30T08:54:14.178Z
close_reason: WindowSettings __post_init__ validation + __bool__; tests cover invalid combos and falsy WINDOW_NONE.
---
File: src/chopdiff/transforms/window_settings.py. Bug: frozen dataclass with no validation; accepts size<0, size>0 with shift==0 (infinite loop), min_overlap>size. Fix: __post_init__ validation; add __bool__ returning bool(self.size) so WINDOW_NONE is falsy. Preserve WINDOW_NONE sentinel. TDD: invalid combos raise ValueError; WINDOW_NONE is falsy and still works in filtered_transform.
