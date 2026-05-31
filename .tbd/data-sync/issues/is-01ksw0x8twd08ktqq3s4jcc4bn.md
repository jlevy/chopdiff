---
type: is
id: is-01ksw0x8twd08ktqq3s4jcc4bn
title: "P2b: tag_with_attrs validates tag/attribute names"
kind: bug
status: closed
priority: 2
version: 2
spec_path: docs/project/specs/active/plan-2026-05-26-robustness-hardening.md
labels: []
dependencies: []
parent_id: is-01kstdjj9r7ctvwkqxnpsk6hww
created_at: 2026-05-30T08:44:45.788Z
updated_at: 2026-05-30T09:06:41.666Z
closed_at: 2026-05-30T09:06:41.666Z
close_reason: tag_with_attrs validates tag/attr names; tests cover valid (incl. data-id/custom) and rejected names.
---
File: src/chopdiff/html/html_in_md.py, fn tag_with_attrs(). Bug: tag and attr names interpolated unvalidated; tag_with_attrs('span onmouseover=alert(1)', 'x') emits injection-shaped opening+closing tags; {'bad attr':'y'} -> invalid markup. Fix: validate tag/attr names (strict HTML-name regex); document safe= trusted-input. TDD: invalid tag/attr names raise ValueError.
