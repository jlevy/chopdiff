---
type: is
id: is-01ksydxx7r7mb2mjfyjs7xerqs
title: Link span recovery loses spans after a reference link or image
kind: bug
status: open
priority: 1
version: 1
spec_path: docs/project/specs/active/plan-2026-05-29-unified-document-model.md
labels: []
dependencies: []
created_at: 2026-05-31T07:10:47.031Z
updated_at: 2026-05-31T07:10:47.031Z
---
Review P1. text_doc.py _block_links advances span_idx only on match, so an earlier no-span identity (reference link) or a leading image desyncs the cursor and later inline links get span=None (losing block/section/sentence association). Fix: reconcile identities to atomic spans by scanning ahead/skipping non-matching atomics. Tests: reference-then-inline, image-then-inline, inline-reference-inline.
