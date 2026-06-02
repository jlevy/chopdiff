---
type: is
id: is-01kt31bb7hyhw5zg0p23fv3yca
title: "C3: Harden DocGraph schema: JSONValue attrs, reserved-detail docs, node-id order, schema evolution policy"
kind: task
status: open
priority: 2
version: 1
spec_path: docs/project/review/senior-engineering-review-doc-model-v0.3.1.md
labels: []
dependencies: []
parent_id: is-01kt319dt4d9cykh6kep8x2z86
created_at: 2026-06-02T02:07:08.017Z
updated_at: 2026-06-02T02:07:08.017Z
---
Findings section 5.7 / P2. attrs: dict[str,object] is too loose for a language-neutral contract -> define+validate a recursive JSONValue type. Document that Detail.tokens/coords are reserved. Pin node-id traversal/assignment order for Rust/TS ports. State a schema evolution policy (additive fields, reserved arrays, version bumps). Matters before cross-language clients depend on DocGraph/v0.1.
