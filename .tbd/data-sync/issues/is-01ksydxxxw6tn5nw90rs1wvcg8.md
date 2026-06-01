---
type: is
id: is-01ksydxxxw6tn5nw90rs1wvcg8
title: Structural block spans strip syntax-bearing indentation for indented code
kind: bug
status: closed
priority: 2
version: 2
spec_path: docs/project/specs/active/plan-2026-05-29-unified-document-model.md
labels: []
dependencies: []
created_at: 2026-05-31T07:10:47.739Z
updated_at: 2026-06-01T23:49:33.016Z
closed_at: 2026-06-01T23:49:33.015Z
close_reason: Verified fixed on main with regression test
---
Review P2. block_tree.py _trim strips all leading whitespace; for indented code blocks the leading 4 spaces are syntax, not padding, so the span is not exact. Fix: for code blocks trim only trailing padding, preserve leading indentation. Add indented-code span round-trip test (and keep fenced-code behavior).
