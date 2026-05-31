---
type: is
id: is-01ksxchaetnpynrsnzn82taqcd
title: TextDoc.graph(include=, detail=) builder (docs/doc_graph.py + text_doc.py)
kind: task
status: closed
priority: 2
version: 3
spec_path: docs/project/specs/active/plan-2026-05-29-unified-document-model.md
labels: []
dependencies:
  - type: blocks
    target: is-01ksxchb6p1gs5d2vj2p5n18jz
parent_id: is-01kss8gdn83f47wbrg3jve028r
created_at: 2026-05-30T21:27:11.577Z
updated_at: 2026-05-31T06:45:17.523Z
closed_at: 2026-05-31T06:45:17.523Z
close_reason: TextDoc.graph(include=, detail=) builder; document auto-enables markdown
---
TextDoc.graph(*, include:frozenset[Layer]=default, detail:frozenset[Detail]=()) -> DocGraph.
- Build projection from node table; include selects which layers' nodes/views serialize (document auto-enables markdown); detail adds node text/inline/tokens/derived coords. No fixed ladder (DR-5).
Tests (tests/docs/test_doc_graph.py): structural-core-only is small; include/detail add expected payload; document pulls in markdown. Depends on schema + collect.
