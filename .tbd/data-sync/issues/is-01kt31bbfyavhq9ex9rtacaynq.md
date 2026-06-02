---
type: is
id: is-01kt31bbfyavhq9ex9rtacaynq
title: "C4: Split text_doc.py into editing/links/sections/snapshot/queries modules"
kind: chore
status: open
priority: 3
version: 1
spec_path: docs/project/review/senior-engineering-review-doc-model-v0.3.1.md
labels: []
dependencies: []
parent_id: is-01kt319dt4d9cykh6kep8x2z86
created_at: 2026-06-02T02:07:08.286Z
updated_at: 2026-06-02T02:07:08.286Z
---
Section 5.9. text_doc.py is ~1450 lines holding TextDoc, Paragraph, Sentence, Offsets, SentIndex, Section, link recovery, heading helpers, sizing, collect/graph bridges, caches. Suggested split: editing.py, links.py, sections.py, snapshot.py, queries.py, keeping public imports stable via re-export. Do this AFTER the snapshot/sections/query changes land so it moves settled code, not churn.
