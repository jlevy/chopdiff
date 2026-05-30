---
type: is
id: is-01ksw0w9mky69h61p53gcka1n6
title: "P1b: sub_doc/sub_paras return independent copies"
kind: bug
status: open
priority: 1
version: 1
spec_path: docs/project/specs/active/plan-2026-05-26-robustness-hardening.md
labels: []
dependencies: []
parent_id: is-01kstdjj19rhp9k8qqw7sv81vk
created_at: 2026-05-30T08:44:13.843Z
updated_at: 2026-05-30T08:44:13.843Z
---
File: src/chopdiff/docs/text_doc.py, fns sub_doc(), sub_paras(). Bug: both alias live Paragraph/Sentence objects (sub_paras: paragraphs[start:end+1]; sub_doc reuses middle paras + shares Sentence objs), so word-window filtered_transform's remove_window_br mutates the caller's doc. Fix: deepcopy paragraphs (and sentences) on slice, matching filtered(). TDD: mutating a sub_doc/sub_paras sentence does not change parent; a word-window transform leaves the input TextDoc unchanged.
