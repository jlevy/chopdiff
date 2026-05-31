---
type: is
id: is-01ksxcgfgd0b4ygkg30vjc698m
title: Node model, NodeKind, and Layer enum (docs/node.py)
kind: task
status: closed
priority: 2
version: 4
spec_path: docs/project/specs/active/plan-2026-05-29-unified-document-model.md
labels: []
dependencies:
  - type: blocks
    target: is-01ksxcggndfjse9zdmrfpptmak
parent_id: is-01kss8gdn83f47wbrg3jve028r
created_at: 2026-05-30T21:26:43.981Z
updated_at: 2026-05-30T22:46:43.280Z
closed_at: 2026-05-30T22:46:43.280Z
close_reason: null
---
New module src/chopdiff/docs/node.py (pure data, no parsing).
- Node dataclass: id:str, kind:NodeKind, layer:Layer, parent:str|None, children:list[str], source_span:tuple[int,int]|None, attrs:dict.
- NodeKind StrEnum: block kinds (reuse BlockType values) + inline kinds (link, code_span, image, inline_html) + document kind (section).
- Layer StrEnum: textual, markdown, document, synthetic (synthetic reserved, not built).
- NestingGuarantee enum {tree, ordered_list} + LAYER_NESTING map.
Tests (tests/docs/test_node.py): kind/layer membership; LAYER_NESTING coverage. Foundational.
