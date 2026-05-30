---
type: is
id: is-01ksw0x9k841c0w2gg0bzcgmp5
title: "P2d: html_extract_attribute_value distinguishes missing vs empty"
kind: bug
status: closed
priority: 2
version: 2
spec_path: docs/project/specs/active/plan-2026-05-26-robustness-hardening.md
labels: []
dependencies: []
parent_id: is-01kstdjj9r7ctvwkqxnpsk6hww
created_at: 2026-05-30T08:44:46.567Z
updated_at: 2026-05-30T09:03:56.132Z
closed_at: 2026-05-30T09:03:56.132Z
close_reason: html_extract_attribute_value returns '' for present-empty, None for missing; test added.
---
File: src/chopdiff/html/html_tags.py (~239 'if value:'). Bug: empty attr (data-x="") indistinguishable from missing (both None). Fix: 'if value is not None'. TDD: empty returns '' and missing returns None.
