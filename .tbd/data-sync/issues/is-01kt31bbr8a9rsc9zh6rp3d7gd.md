---
type: is
id: is-01kt31bbr8a9rsc9zh6rp3d7gd
title: "C5: Settle SpanRef as a selector family before annotation/synthetic layers"
kind: task
status: open
priority: 3
version: 1
spec_path: docs/project/review/senior-engineering-review-doc-model-v0.3.1.md
labels: []
dependencies: []
parent_id: is-01kt319dt4d9cykh6kep8x2z86
created_at: 2026-06-02T02:07:08.552Z
updated_at: 2026-06-02T02:07:08.552Z
---
Findings 6 (forward-looking) + sections 9/10.4. Before annotations depend on it: model TextQuoteSelector (exact/prefix/suffix) + TextPositionSelector (start/end/unit) + optional hash selector; add confidence/failure states; make context window configurable (currently fixed _CONTEXT_WINDOW=24, span_ref.py:18); decide fuzzy-matching subset for v1. Builds on A3. Gate behind the annotation-layer milestone.
