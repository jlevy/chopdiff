---
type: is
id: is-01kt3gy0vvq1j34rbqe975k47r
title: "Address PR #16 senior review: deepcopy/pickle regression + doc consistency"
kind: bug
status: closed
priority: 1
version: 2
spec_path: docs/project/review/senior-engineering-review-doc-model-v0.3.1.md
labels: []
dependencies: []
parent_id: is-01kt319dt4d9cykh6kep8x2z86
created_at: 2026-06-02T06:39:28.635Z
updated_at: 2026-06-02T06:43:38.617Z
closed_at: 2026-06-02T06:43:38.617Z
close_reason: Fixed copy/pickle regression (__getstate__/__setstate__), spec SpanRef + node-table/live-view wording, alias-conflict errors; added regression + brute-force tests
---
Senior review of PR #16. P1: TextDoc no longer deep-copyable/pickleable after adding _cache_lock (RLock) — regression in a core dataclass. Fix via __getstate__/__setstate__ dropping caches+lock, fresh RLock on restore; tests for cold and warm. P2: docs/textdoc-spec.md SpanRef section still describes mutating/fuzzy resolve — update to pure resolve() + resolve_and_update() + fuzzy deferred. P3: block_type_counts() 'live block tree/current content' docstring and spec 'calculated over the node table' wording conflict with source-backed cache contract — reword. Non-blocking: brute-force IntervalIndex.innermost equivalence test; raise on conflicting alias pairs (scope+subtree_of, contains+within); clarify contains stays span-only; fix stale contains=section.span test docstring.
