---
type: is
id: is-01ksgsszsr1771m1mgxsy4d0cv
title: Resolve copier conflicts + apply 4 reconciliation decisions
kind: task
status: closed
priority: 1
version: 2
labels: []
dependencies: []
parent_id: is-01ksgry3wfqr23jybnz5yr8qtb
created_at: 2026-05-26T00:08:59.448Z
updated_at: 2026-05-26T01:38:38.074Z
---
Decisions: (1) keep #5 cool-off (pyproject exclude-newer + --locked + pip-audit), drop template env-var step; (2) follow template for agent rules (delete .cursor/rules, commit CLAUDE.md+AGENTS.md static); (3) adopt Python 3.14 + uv 0.11.12; (4) PR#5 review: pin&verify .claude hooks + add --all-extras to audit job. All on branch claude/upgrade-simple-modern-uv.
