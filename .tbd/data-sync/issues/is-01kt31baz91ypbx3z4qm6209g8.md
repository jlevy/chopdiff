---
type: is
id: is-01kt31baz91ypbx3z4qm6209g8
title: "C2: Decide query-object public story (DocumentSnapshot.collect vs DocGraph methods) and align all docs"
kind: task
status: open
priority: 2
version: 1
spec_path: docs/project/review/senior-engineering-review-doc-model-v0.3.1.md
labels: []
dependencies: []
parent_id: is-01kt319dt4d9cykh6kep8x2z86
created_at: 2026-06-02T02:07:07.753Z
updated_at: 2026-06-02T02:07:07.753Z
---
Finding 1 (P1, design portion). The review offers two directions: (1 preferred) keep DocGraph pure serialization, add a read-only DocumentSnapshot/query object; or (2) add query methods to DocGraph (then it's a rich value object, not just a wire schema). Pick one, then make spec/README/migration consistent. Depends on the C1 snapshot decision. PRODUCT DECISION REQUIRED.
