---
type: is
id: is-01ktywgd27gtd1h7ajr4nmmc8f
title: Supply-chain exception + dependency rewire (pyproject, lock)
kind: task
status: closed
priority: 1
version: 3
spec_path: docs/project/specs/active/plan-2026-06-12-flexdoc-pypi-migration.md
labels: []
dependencies:
  - type: blocks
    target: is-01ktywgde57b688z8ka0460dtd
parent_id: is-01ktywgcp3pe9rhjdgp927vkzn
created_at: 2026-06-12T21:41:14.951Z
updated_at: 2026-06-12T21:42:37.353Z
closed_at: 2026-06-12T21:42:37.353Z
close_reason: pyproject rewired, exception recorded, lock reviewed
---
Add flexdoc cool-off exception (exclude-newer-package 2026-06-13T00:00:00Z) + SUPPLY-CHAIN-SECURITY.md Active Exceptions entry; add flexdoc>=0.1.0; drop marko/cydifflib/funlog/regex/strif/frontmatter-format/pydantic/selectolax; add typing_extensions (direct import, previously via pydantic); wheel packages back to src/chopdiff only; uv lock and review diff.
