---
type: is
id: is-01ksxcha36288d2jvy8v11a0sw
title: DocGraph Pydantic schema models + Layer/Detail (docs/doc_graph.py)
kind: task
status: open
priority: 2
version: 3
spec_path: docs/project/specs/active/plan-2026-05-29-unified-document-model.md
labels: []
dependencies:
  - type: blocks
    target: is-01ksxchaetnpynrsnzn82taqcd
  - type: blocks
    target: is-01ksxchb6p1gs5d2vj2p5n18jz
parent_id: is-01kss8gdn83f47wbrg3jve028r
created_at: 2026-05-30T21:27:11.206Z
updated_at: 2026-05-30T21:27:30.697Z
---
New src/chopdiff/docs/doc_graph.py (Pydantic, DR-3).
- DocGraph{schema:'DocGraph/v0.1', source:SourceInfo, nodes:list[NodeModel], views:Views, annotations=[] layout=[] provenance=[] reserved}.
- SourceInfo{format, offset_unit:'unicode_code_points', sha256, text?}; NodeModel mirrors Node (+ optional text/coords); Views{toc, blocks, links, sentences as id arrays}; annotation target = SpanRef shape.
- Layer (reuse node.Layer) + Detail enum {text, inline, tokens, coords}. offset_unit pinned to code points.
Tests (tests/docs/test_doc_graph.py): model validates; JSON emits expected keys; schema string == DocGraph/v0.1. Depends on node table + SpanRef.
