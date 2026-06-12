---
type: is
id: is-01ktywge50y25hknmja557bkc1
title: Update CI wheel-smoke for single import root
kind: task
status: closed
priority: 1
version: 4
spec_path: docs/project/specs/active/plan-2026-06-12-flexdoc-pypi-migration.md
labels: []
dependencies:
  - type: blocks
    target: is-01ktywgewngat7as8bgpm6wmby
parent_id: is-01ktywgcp3pe9rhjdgp927vkzn
created_at: 2026-06-12T21:41:16.064Z
updated_at: 2026-06-12T21:46:38.181Z
closed_at: 2026-06-12T21:46:38.181Z
close_reason: wheel-smoke single import root; audit job unchanged
---
wheel-smoke builds/installs only the chopdiff wheel and imports chopdiff (flexdoc arrives as a dependency); drop two-import-root assertions; audit job keeps --all-extras.
