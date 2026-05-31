---
type: is
id: is-01ksw0xat5tjq5ah8ma0y3f6mh
title: "P2g: parse_tag attribute coverage (document or broaden)"
kind: task
status: closed
priority: 3
version: 2
spec_path: docs/project/specs/active/plan-2026-05-26-robustness-hardening.md
labels: []
dependencies: []
parent_id: is-01kstdjj9r7ctvwkqxnpsk6hww
created_at: 2026-05-30T08:44:47.813Z
updated_at: 2026-05-30T09:06:42.752Z
closed_at: 2026-05-30T09:06:42.752Z
close_reason: parse_tag docstring documents Tag.attrs as best-effort (double-quoted only); chosen over broadening per spec.
---
File: src/chopdiff/docs/wordtoks.py (parse_tag regex ~225 captures only double-quoted non-hyphenated name="value"). Low impact (attrs feed only tag-name checks). Fix: document Tag.attrs as best-effort/limited (preferred), or broaden the regex for single-quoted/unquoted/boolean/hyphenated. TDD: docstring states the limitation (or, if broadened, tests cover the new forms).
