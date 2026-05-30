---
type: is
id: is-01ksw0wc848rsg2yrrpeqa0fqp
title: "P1i: TokenMapping changed-token confidence metric"
kind: bug
status: closed
priority: 2
version: 2
spec_path: docs/project/specs/active/plan-2026-05-26-robustness-hardening.md
labels: []
dependencies: []
parent_id: is-01kstdjj19rhp9k8qqw7sv81vk
created_at: 2026-05-30T08:44:16.516Z
updated_at: 2026-05-30T08:58:36.221Z
closed_at: 2026-05-30T08:58:36.221Z
close_reason: TokenMapping uses changed-token count (stats().removed/len); full-replacement rejected; tests added.
---
File: src/chopdiff/docs/token_mapping.py, fn _validate(). Bug: uses len(self.diff.changes()) (number of diff OPS) over len(tokens1), so one REPLACE of 100 tokens passes the same gate as one of 1. Fix: use changed-TOKEN count (self.diff.stats().nchanges()); document denominator. TDD: a full-replacement mapping is rejected at a reasonable max_diff_frac.
