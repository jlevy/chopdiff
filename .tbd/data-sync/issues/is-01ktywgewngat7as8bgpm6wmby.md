---
type: is
id: is-01ktywgewngat7as8bgpm6wmby
title: End-to-end acceptance gate (lint, test, wheel smoke, example)
kind: task
status: closed
priority: 1
version: 4
spec_path: docs/project/specs/active/plan-2026-06-12-flexdoc-pypi-migration.md
labels: []
dependencies:
  - type: blocks
    target: is-01ktywgfa4dea76rezd65szb3z
parent_id: is-01ktywgcp3pe9rhjdgp927vkzn
created_at: 2026-06-12T21:41:16.821Z
updated_at: 2026-06-12T21:51:21.730Z
closed_at: 2026-06-12T21:51:21.730Z
close_reason: lint+27 tests green vs PyPI flexdoc; wheel smoke in isolated venv passed; example verified to LLM call; code grep clean
---
make install/lint/test zero errors; uv pip list shows flexdoc 0.1.0 from PyPI; uv build --wheel + isolated-venv smoke (import chopdiff, sliding_para_window, FlexDoc, tiny transform); run examples/insert_para_breaks.py; grep TextDoc|chopdiff.docs|chopdiff.html clean in code.
