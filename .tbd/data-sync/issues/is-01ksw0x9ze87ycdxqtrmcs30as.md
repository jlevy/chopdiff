---
type: is
id: is-01ksw0x9ze87ycdxqtrmcs30as
title: "P2e: extract_preceding preserves exception cause; B904 per-line"
kind: task
status: closed
priority: 3
version: 2
spec_path: docs/project/specs/active/plan-2026-05-26-robustness-hardening.md
labels: []
dependencies: []
parent_id: is-01kstdjj9r7ctvwkqxnpsk6hww
created_at: 2026-05-30T08:44:46.958Z
updated_at: 2026-05-30T09:06:42.409Z
closed_at: 2026-05-30T09:06:42.409Z
close_reason: extract_preceding chains KeyError via from e (one-line correctness fix; covered by existing passing timestamp tests; KeyError branch not separately reachable in a unit test).
---
File: src/chopdiff/html/timestamps.py, fn extract_preceding() (raise ContentNotFound without from e). Fix: 'raise ContentNotFound(...) from e'. Also prefer per-line '# noqa: B904' over the global B904 ignore in pyproject.toml so the check stays on elsewhere. TDD: the wrapped error has __cause__ set.
