---
type: is
id: is-01kt319xssaqmb17awyf0t58ga
title: "A1: collect(kinds={inline_kind}) should not require inline=True"
kind: bug
status: in_progress
priority: 1
version: 2
spec_path: docs/project/review/senior-engineering-review-doc-model-v0.3.1.md
labels: []
dependencies: []
parent_id: is-01kt319dt4d9cykh6kep8x2z86
created_at: 2026-06-02T02:06:21.497Z
updated_at: 2026-06-02T04:03:26.173Z
---
Finding 3 (P1). In collect.py the inline guard runs before the kinds filter (collect.py:62-67), so collect(kinds={NodeKind.link}, recursive=True) returns nothing unless the caller also passes inline=True. Fix: when kinds explicitly selects inline kinds, imply inline inclusion (requested_inline = kinds is not None and bool(kinds & INLINE_KINDS); include_inline = inline or requested_inline). Add a targeted test. Verified against code.
