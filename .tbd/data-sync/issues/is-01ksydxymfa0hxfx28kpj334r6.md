---
type: is
id: is-01ksydxymfa0hxfx28kpj334r6
title: Committed .codex/hooks.json hard-codes a machine-local absolute path
kind: bug
status: open
priority: 3
version: 1
spec_path: docs/project/specs/active/plan-2026-05-29-unified-document-model.md
labels: []
dependencies: []
created_at: 2026-05-31T07:10:48.463Z
updated_at: 2026-05-31T07:10:48.463Z
---
Review P2. .codex/hooks.json:9 hard-codes /Users/levy/wrk/.../tbd-closing-reminder.sh; fails in other checkouts. Pre-existing (not in this PR diff vs main). Decide: make repo-relative, gitignore, or remove .codex/ from the library repo. Pending user decision.
