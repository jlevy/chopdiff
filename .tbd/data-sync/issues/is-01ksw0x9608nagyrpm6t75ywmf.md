---
type: is
id: is-01ksw0x9608nagyrpm6t75ywmf
title: "P2c: html_find_tag strict/diagnostic mode"
kind: task
status: closed
priority: 2
version: 2
spec_path: docs/project/specs/active/plan-2026-05-26-robustness-hardening.md
labels: []
dependencies: []
parent_id: is-01kstdjj9r7ctvwkqxnpsk6hww
created_at: 2026-05-30T08:44:46.144Z
updated_at: 2026-05-30T09:03:55.790Z
closed_at: 2026-05-30T09:03:55.789Z
close_reason: html_find_tag strict mode raises with context; best-effort logs debug; test added.
---
File: src/chopdiff/html/html_tags.py (~213 except Exception: continue). Bug: swallows all selectolax errors silently. Fix: add strict: bool=False (raise with tag/offset context when strict); logging.debug otherwise. TDD: strict=True surfaces a parse failure.
