---
type: is
id: is-01kxhvx0w6y2r5280gjdwsam3j
title: Fix non-isolated build interpreter selection
kind: bug
status: closed
priority: 1
version: 3
labels: []
dependencies: []
parent_id: is-01ksgry3wfqr23jybnz5yr8qtb
created_at: 2026-07-15T03:07:37.734Z
updated_at: 2026-07-15T03:14:03.547Z
closed_at: 2026-07-15T03:14:03.547Z
close_reason: "Implemented in PR #31; local lint, 44-test Python 3.11-3.14 matrix, clean build, artifact validation, wheel smoke, audit, and all GitHub checks passed."
---
simple-modern-uv v0.4.0 installs locked build backends into .venv, but uv build --no-build-isolation does not select that environment automatically under uv 0.11.25. Select .venv/bin/python explicitly in Make and GitHub workflows and add regression coverage.
