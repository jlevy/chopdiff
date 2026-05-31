---
type: is
id: is-01ksydxy983rzttcgk14dgqg8g
title: CHANGELOG/spec status not aligned with DocGraph work and pydantic dependency
kind: bug
status: open
priority: 2
version: 1
spec_path: docs/project/specs/active/plan-2026-05-29-unified-document-model.md
labels: []
dependencies: []
created_at: 2026-05-31T07:10:48.103Z
updated_at: 2026-05-31T07:10:48.103Z
---
Review P2. CHANGELOG omits the new pydantic dependency (pulls annotated-types, pydantic-core, typing-inspection) and the node-model/DocGraph features. docs/textdoc-spec.md section 14 still marks recursive node table, base_blocks, collect, DocGraph, SpanRef as in progress and says blocks() does not populate blockquote/list-item children (now it does). Update both, keeping common-doc-guidelines formatting.
