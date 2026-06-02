---
type: is
id: is-01kt3d5f3dcfnjdyw03db1bxz1
title: "Perf: parse marko AST once and share across blocks()/links()/base_blocks()"
kind: feature
status: open
priority: 2
version: 1
spec_path: docs/project/review/senior-engineering-review-doc-model-v0.3.1.md
labels: []
dependencies: []
parent_id: is-01kt319dt4d9cykh6kep8x2z86
created_at: 2026-06-02T05:33:38.285Z
updated_at: 2026-06-02T05:33:38.285Z
---
Discovered via profiling after B1. Scaling is linear (B1 works), but marko parsing is ~78-81% of node_table build, and the SAME source is fully parsed by marko multiple times per build: parse_blocks (blocks()) and _block_links (links()) each run an independent full parse, and base_blocks() a third. Measured on a 66KB doc: one full parse=154ms; fresh node_table=381ms with 2 full parses=309ms (81%). Prototype sharing one parse (flowmark_markdown().parse once, then _blocks_from + extract_links over the same Document) is 2.06x faster on the blocks+links portion (331ms->160ms) with identical block trees and link counts.

Fix: cache the marko Document on TextDoc keyed to the immutable source_text (a _parsed() accessor); route parse_blocks/_block_links/base_blocks through it instead of re-parsing. Verify extract_links and _blocks_from only read the AST (no mutation). Expected ~40% reduction in node_table build, more when base_blocks is also used. Natural home for the cached AST is the future DocumentSnapshot (C1).

Minor secondary win: _heading_element is parsed up to 3x per heading (block_type + heading_level + heading_title); memoize or compute level+title once per heading.
