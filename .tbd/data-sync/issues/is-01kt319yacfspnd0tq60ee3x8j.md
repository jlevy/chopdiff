---
type: is
id: is-01kt319yacfspnd0tq60ee3x8j
title: "A3: Harden SpanRef: percent-encode text fragment, non-mutating resolve, persisted offsets policy"
kind: task
status: open
priority: 1
version: 2
spec_path: docs/project/review/senior-engineering-review-doc-model-v0.3.1.md
labels: []
dependencies:
  - type: blocks
    target: is-01kt31bbr8a9rsc9zh6rp3d7gd
parent_id: is-01kt319dt4d9cykh6kep8x2z86
created_at: 2026-06-02T02:06:22.028Z
updated_at: 2026-06-02T02:07:26.532Z
---
Finding 6 (P1). span_ref.py: (a) to_text_fragment() concatenates raw prefix/exact/suffix with no percent-encoding (span_ref.py:68-80) -> invalid fragments for spaces/punctuation/Unicode; (b) resolve() mutates the passed-in SpanRef's start/end in place (span_ref.py:125-127) -> surprising; provide a non-mutating resolve() and an explicit resolve_and_update(); (c) to_persisted() drops offsets entirely (span_ref.py:61-66) -> decide whether persisted refs keep position hints. Fuzzy/edit-distance anchoring is explicitly OUT of scope for now (defer to annotation milestone).
