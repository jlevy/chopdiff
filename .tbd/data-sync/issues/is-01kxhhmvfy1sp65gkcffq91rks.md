---
type: is
id: is-01kxhhmvfy1sp65gkcffq91rks
title: "R3: Make exact TextNode div reassembly lossless"
kind: bug
status: closed
priority: 1
version: 3
labels:
  - review-finding
dependencies: []
parent_id: is-01kxhh1t7n4zpy9x8pqtwh9fye
created_at: 2026-07-15T00:08:24.317Z
updated_at: 2026-07-15T00:19:49.011Z
closed_at: 2026-07-15T00:19:49.009Z
close_reason: Exact reassembly now emits original div markers and attributes; normalized reassembly remains unchanged; 31 tests and lint pass
---
`TextNode.reassemble(padding="")` reconstructs tags through `div_wrapper`, raising on valid multiple classes and discarding non-class attributes. Reuse original markers in exact mode.
