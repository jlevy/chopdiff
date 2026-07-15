---
type: is
id: is-01kxhngx2nmc3gy40p8z0711nf
title: "PR #30 review R3: Example pins pre-FlexDoc chopdiff"
kind: bug
status: closed
priority: 1
version: 3
labels: []
dependencies: []
parent_id: is-01kxhn010xfz7tz514kja2a6dh
created_at: 2026-07-15T01:16:09.172Z
updated_at: 2026-07-15T01:20:05.122Z
closed_at: 2026-07-15T01:20:05.121Z
close_reason: Fixed by sourcing chopdiff editably from the same checkout in PEP 723 metadata, regenerating the script lock, and testing metadata plus lock alignment. Isolated help execution and a lock export vulnerability audit pass.
---
PR #30, examples/insert_para_breaks.py:3-27. The PEP 723 environment pins PyPI chopdiff 0.3.1, whose pre-extraction document model is incompatible with the example's FlexDoc 0.3 workflow. Make the locked script resolve the chopdiff source from the same repository checkout and verify the isolated help/import path. Review thread: PRRT_kwDOOBrMzs6Q8lOX.
