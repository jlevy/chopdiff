---
type: is
id: is-01kss8gdn83f47wbrg3jve028r
title: "[epic] Flexible unified document model (DocGraph): node table, layers, collect(), SpanRef, and serialized projection"
kind: epic
status: closed
priority: 2
version: 18
spec_path: docs/project/specs/active/plan-2026-05-29-unified-document-model.md
labels: []
dependencies: []
child_order_hints:
  - is-01kss8gdybwa8q09qftg1nfe54
  - is-01kss86kw6hwhh3qn62y748vbc
  - is-01ksxcgfgd0b4ygkg30vjc698m
  - is-01ksxcgfvsx7mha7pwdg5b95pp
  - is-01ksxcgg8zh17bn34e56pq0b38
  - is-01ksxcggndfjse9zdmrfpptmak
  - is-01ksxcgh4v79ra9wbtavbq1fms
  - is-01ksxch8y5z7y5ypw1ff58ck08
  - is-01ksxch9bgx0cncw3d0pn3wya9
  - is-01ksxch9qc6yks6zwz9z4en15e
  - is-01ksxcha36288d2jvy8v11a0sw
  - is-01ksxchaetnpynrsnzn82taqcd
  - is-01ksxchatt9gc8cpg1c5zv5y3z
  - is-01ksxchb6p1gs5d2vj2p5n18jz
created_at: 2026-05-29T06:59:50.056Z
updated_at: 2026-05-31T06:45:25.532Z
closed_at: 2026-05-31T06:45:25.531Z
close_reason: Phases 1-2 implemented end to end (node model, recursive tree, base_blocks, node table+inline, collect, SpanRef, DocGraph Pydantic projection). Phases 3-4 (synthetic layer, cross-layer edits) deferred by design.
---
Unified JSON-serializable DocumentOverview projected from TextDoc: stable node set + derived views + flexible value/count rollups at any scope (doc/section/block), recursive, incl. inline items and block<->inline relationships, optional detail levels. Exploration + proposed design in spec; gated on Open decisions.
