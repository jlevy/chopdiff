---
type: is
id: is-01ksw0xadc0sbrj45y45ar5p3v
title: "P2f: parsed-div class matching (class_names set, single quotes)"
kind: bug
status: open
priority: 2
version: 1
spec_path: docs/project/specs/active/plan-2026-05-26-robustness-hardening.md
labels: []
dependencies: []
parent_id: is-01kstdjj9r7ctvwkqxnpsk6hww
created_at: 2026-05-30T08:44:47.404Z
updated_at: 2026-05-30T08:44:47.404Z
---
Files: src/chopdiff/divs/parse_divs.py (CLASS_NAME_PATTERN double-quote only; stores whole class string), divs/text_node.py (children_by_class_names exact equality; only class_name:str|None). Bug: class='chunk selected' won't match 'chunk'. Fix: parse class names into a set/tuple (class_names), support single quotes, match by membership/intersection; keep class_name convenience. TDD: children_by_class_names('chunk') matches class='chunk selected'.
