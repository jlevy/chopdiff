---
type: is
id: is-01ktywgde57b688z8ka0460dtd
title: Delete moved flexdoc code, tests, golden fixtures, examples
kind: task
status: closed
priority: 1
version: 4
spec_path: docs/project/specs/active/plan-2026-06-12-flexdoc-pypi-migration.md
labels: []
dependencies:
  - type: blocks
    target: is-01ktywgdsce0bsppbf9t2h1h4g
parent_id: is-01ktywgcp3pe9rhjdgp927vkzn
created_at: 2026-06-12T21:41:15.333Z
updated_at: 2026-06-12T21:43:21.305Z
closed_at: 2026-06-12T21:43:21.305Z
close_reason: moved parse_divs test to tests/divs; deleted src/flexdoc, tests/{docs,html,golden}, boundary test, 3 examples
---
Move test_parsed_div_multi_class_matching from tests/html/test_html_validation_and_classes.py to tests/divs/ first. Then git rm -r src/flexdoc tests/docs tests/html tests/golden tests/test_package_boundary.py and the three flexdoc-only examples (normalized_form, doc_structure, backfill_timestamps). Keep insert_para_breaks.py + gettysberg.txt.
