---
type: is
id: is-01ksw0wcm97g8ej0x439t1mnpa
title: "P1j: empty-doc as_wordtoks(bof_eof=True) behavior"
kind: bug
status: open
priority: 2
version: 1
spec_path: docs/project/specs/active/plan-2026-05-26-robustness-hardening.md
labels: []
dependencies: []
parent_id: is-01kstdjj19rhp9k8qqw7sv81vk
created_at: 2026-05-30T08:44:16.905Z
updated_at: 2026-05-30T08:44:16.905Z
---
File: src/chopdiff/docs/text_doc.py (first_index(), last_index(), as_wordtok_to_sent()). Bug: empty doc -> last_index() does paragraphs[-1] (IndexError); first_index() returns invalid SentIndex(0,0). Fix: define empty-doc behavior (yield only BOF_TOK/EOF_TOK, or raise clear ValueError); guard first/last_index. TDD: empty-doc wordtoks behave as defined.
