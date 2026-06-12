---
type: is
id: is-01ktywgcp3pe9rhjdgp927vkzn
title: "[epic] Migrate chopdiff to published flexdoc 0.1.0 (breaking release)"
kind: epic
status: closed
priority: 1
version: 9
spec_path: docs/project/specs/active/plan-2026-06-12-flexdoc-pypi-migration.md
labels: []
dependencies: []
child_order_hints:
  - is-01ktywgd27gtd1h7ajr4nmmc8f
  - is-01ktywgde57b688z8ka0460dtd
  - is-01ktywgdsce0bsppbf9t2h1h4g
  - is-01ktywge50y25hknmja557bkc1
  - is-01ktywgegrp5m4w4k0f3j1v45x
  - is-01ktywgewngat7as8bgpm6wmby
  - is-01ktywgfa4dea76rezd65szb3z
created_at: 2026-06-12T21:41:14.563Z
updated_at: 2026-06-12T21:52:58.468Z
closed_at: 2026-06-12T21:52:58.468Z
close_reason: "migration complete: deps rewired, code deleted, rename applied, CI/docs updated, acceptance gate green"
---
Rewire chopdiff onto PyPI flexdoc 0.1.0, delete in-repo src/flexdoc, apply TextDoc->FlexDoc rename, update CI/CHANGELOG/docs, validate end to end. Runbook: GitHub issue #27.
