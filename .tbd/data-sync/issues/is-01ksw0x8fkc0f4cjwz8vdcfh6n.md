---
type: is
id: is-01ksw0x8fkc0f4cjwz8vdcfh6n
title: "P2a: html_find_tag nested self-closing same-name tags"
kind: bug
status: closed
priority: 2
version: 2
spec_path: docs/project/specs/active/plan-2026-05-26-robustness-hardening.md
labels: []
dependencies: []
parent_id: is-01kstdjj9r7ctvwkqxnpsk6hww
created_at: 2026-05-30T08:44:45.427Z
updated_at: 2026-05-30T09:03:55.442Z
closed_at: 2026-05-30T09:03:55.441Z
close_reason: Nested self-closing same-name tags depth-neutral; outer match spans full element; test added.
---
File: src/chopdiff/html/html_tags.py, fn _find_balanced_closing_tag(). Bug: nested <div .../> counted as an opener, so <div id=outer>before <div id=inner/> after</div> matches only outer's opening tag. Fix: treat self-closing same-name tags as depth-neutral (use existing _SELF_CLOSING_DETECTOR). TDD: nested self-closing returns the full enclosing span.
