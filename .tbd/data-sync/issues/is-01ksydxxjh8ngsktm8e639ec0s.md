---
type: is
id: is-01ksydxxjh8ngsktm8e639ec0s
title: Section.links() drops reference-style links
kind: bug
status: open
priority: 1
version: 1
spec_path: docs/project/specs/active/plan-2026-05-29-unified-document-model.md
labels: []
dependencies: []
created_at: 2026-05-31T07:10:47.377Z
updated_at: 2026-05-31T07:10:47.377Z
---
Review P1. TextDoc.links() parses whole source, but Section.links() loops Paragraph.links() which cannot see reference defs elsewhere. Fix: derive section links from the document-level pass filtered by section span ownership; document the span=None reference-link limitation. Test: heading + reference link + def.
