---
type: is
id: is-01ksw0wa0k0kd6ndnvbcjp03mb
title: "P1c: sliding_para_window keeps full ending paragraph"
kind: bug
status: closed
priority: 1
version: 2
spec_path: docs/project/specs/active/plan-2026-05-26-robustness-hardening.md
labels: []
dependencies: []
parent_id: is-01kstdjj19rhp9k8qqw7sv81vk
created_at: 2026-05-30T08:44:14.226Z
updated_at: 2026-05-30T08:54:13.857Z
closed_at: 2026-05-30T08:54:13.857Z
close_reason: sliding_para_window uses sub_paras(); test confirms all sentences of the ending paragraph are kept.
---
File: src/chopdiff/transforms/sliding_windows.py, fn sliding_para_window(). Bug: windows built via sub_doc(SentIndex(i,0), SentIndex(end_index,0)) keep only sentence 0 of the ending paragraph. Fix: use sub_paras(i, end_index). TDD: multi-sentence paragraphs with a no-op normalizer retain every sentence in each window.
