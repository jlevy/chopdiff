---
type: is
id: is-01ksw0wacyfftx14c5pevq498w
title: "P1d: div child chunking inclusive slice + zero-size empty slice"
kind: bug
status: closed
priority: 1
version: 2
spec_path: docs/project/specs/active/plan-2026-05-26-robustness-hardening.md
labels: []
dependencies: []
parent_id: is-01kstdjj19rhp9k8qqw7sv81vk
created_at: 2026-05-30T08:44:14.621Z
updated_at: 2026-05-30T09:00:40.052Z
closed_at: 2026-05-30T09:00:40.051Z
close_reason: slice_children inclusive (children[start:end+1]); div-leading chunking yields distinct chunks; test added.
---
Files: src/chopdiff/divs/text_node.py (slice_children(), size()), divs/chunk_utils.py (chunk_generator()). Bug: slice_children uses exclusive children[start:end] but chunk_generator passes an inclusive end (matching sub_paras [start:end+1]); first slice empty; empty-children size() falls back to whole-doc contents -> repeated whole-doc chunks. Fix: make slice_children inclusive (children[start:end+1]); empty child slice measures size 0. TDD: input with 3 top-level divs chunks into 3 distinct correctly-sized pieces.
