---
type: is
id: is-01kt319yjw3qnemeh96hfyr77q
title: "A4: Decide and implement set_sent() source-reference contract"
kind: bug
status: open
priority: 1
version: 1
spec_path: docs/project/review/senior-engineering-review-doc-model-v0.3.1.md
labels: []
dependencies: []
parent_id: is-01kt319dt4d9cykh6kep8x2z86
created_at: 2026-06-02T02:06:22.299Z
updated_at: 2026-06-02T02:06:22.299Z
---
Finding 5 (P1). text_doc.py:719-723 builds Sentence(sent_str, old_sent.offsets) leaving original_text=None, so Sentence.span falls back to len(new text): a changed-length edit makes the span describe neither the old nor a valid source slice. Needs a contract decision: preserve old_sent.original_text (span keeps pointing at original source slice) OR explicitly mark the source ref invalid after mutation. Implement chosen contract + targeted test. DESIGN DECISION REQUIRED before coding.
