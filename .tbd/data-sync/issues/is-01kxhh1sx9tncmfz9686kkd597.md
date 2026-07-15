---
type: is
id: is-01kxhh1sx9tncmfz9686kkd597
title: Upgrade justified dependencies including first-party libraries
kind: task
status: closed
priority: 1
version: 4
labels:
  - dependencies
dependencies:
  - type: blocks
    target: is-01kxhh1th1pw92hzk06zdfpbhn
parent_id: is-01kxhh1rsgzfj5r2t4ndw58x1v
created_at: 2026-07-14T23:58:00.103Z
updated_at: 2026-07-15T00:12:22.599Z
closed_at: 2026-07-15T00:12:22.598Z
close_reason: Upgraded flexdoc 0.1.0->0.3.0, flowmark 0.7.1->0.7.2, and vetted lock packages under the 2026-06-30 cutoff; retained precise first-party FlexDoc exception; removed expired exceptions; reviewed the 60-package tree; lint/type/tests pass; pip-audit passes with no ignores.
---
Audit direct and transitive versions, prioritize maintainer-owned flexdoc, flowmark, prettyfmt, strif, funlog and related first-party packages, apply the user-approved first-party cool-off exemption precisely, review the lock diff, and run a vulnerability audit.
