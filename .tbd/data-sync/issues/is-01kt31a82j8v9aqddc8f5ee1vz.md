---
type: is
id: is-01kt31a82j8v9aqddc8f5ee1vz
title: "A6: Small cleanups: drop unused included_ids, unify parent-inclusion predicate, move node.py tests, deque, typo"
kind: chore
status: open
priority: 3
version: 1
spec_path: docs/project/review/senior-engineering-review-doc-model-v0.3.1.md
labels: []
dependencies: []
parent_id: is-01kt319dt4d9cykh6kep8x2z86
created_at: 2026-06-02T02:06:32.018Z
updated_at: 2026-06-02T02:06:32.018Z
---
P3 cleanups verified in code: (a) doc_graph.py:173,209 builds included_ids and never reads it -> remove; (b) doc_graph.py _is_parent_included() only checks layer while child filtering uses _node_included() incl. inline -> use _node_included() for parent checks too (Finding 7.7 / P2); (c) move node.py inline '## Tests' into tests/ module; (d) collect.py _subtree_nodes uses list.pop(0) -> collections.deque; (e) fix 'Markown' typo in TextDoc docstring. Low risk.
