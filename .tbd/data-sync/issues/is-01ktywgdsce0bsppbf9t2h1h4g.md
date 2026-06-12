---
type: is
id: is-01ktywgdsce0bsppbf9t2h1h4g
title: Apply TextDoc->FlexDoc rename and import-path updates
kind: task
status: closed
priority: 1
version: 5
spec_path: docs/project/specs/active/plan-2026-06-12-flexdoc-pypi-migration.md
labels: []
dependencies:
  - type: blocks
    target: is-01ktywge50y25hknmja557bkc1
  - type: blocks
    target: is-01ktywgegrp5m4w4k0f3j1v45x
parent_id: is-01ktywgcp3pe9rhjdgp927vkzn
created_at: 2026-06-12T21:41:15.692Z
updated_at: 2026-06-12T21:46:10.294Z
closed_at: 2026-06-12T21:46:10.294Z
close_reason: rename applied; imports normalized; inlined diff-filter fixtures; lint+tests green
---
repren --literal TextDoc->FlexDoc and text_doc->flex_doc across src tests examples; prefer root import 'from flexdoc import FlexDoc' where only the class is used; clean __pycache__ before, .orig backups after.
