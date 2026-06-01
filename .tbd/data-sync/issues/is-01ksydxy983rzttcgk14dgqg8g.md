---
type: is
id: is-01ksydxy983rzttcgk14dgqg8g
title: CHANGELOG/spec status not aligned with DocGraph work and pydantic dependency
kind: bug
status: closed
priority: 2
version: 2
spec_path: docs/project/specs/active/plan-2026-05-29-unified-document-model.md
labels: []
dependencies: []
created_at: 2026-05-31T07:10:48.103Z
updated_at: 2026-06-01T23:50:08.519Z
closed_at: 2026-06-01T23:50:08.514Z
close_reason: CHANGELOG now lists pydantic + DocGraph/node-model features; spec §14 marks them implemented (containers populate children)
---
Review P2. CHANGELOG omits the new pydantic dependency (pulls annotated-types, pydantic-core, typing-inspection) and the node-model/DocGraph features. docs/textdoc-spec.md section 14 still marks recursive node table, base_blocks, collect, DocGraph, SpanRef as in progress and says blocks() does not populate blockquote/list-item children (now it does). Update both, keeping common-doc-guidelines formatting.
