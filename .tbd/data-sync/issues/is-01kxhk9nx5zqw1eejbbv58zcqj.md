---
type: is
id: is-01kxhk9nx5zqw1eejbbv58zcqj
title: "R9: Restrict the source distribution manifest"
kind: bug
status: closed
priority: 1
version: 3
labels: []
dependencies: []
parent_id: is-01kxhh1t7n4zpy9x8pqtwh9fye
created_at: 2026-07-15T00:37:15.301Z
updated_at: 2026-07-15T00:38:12.775Z
closed_at: 2026-07-15T00:38:12.774Z
close_reason: Restricted the sdist to package source and required metadata, added a CI manifest gate, and verified wheel-from-sdist plus isolated install
---
Hatch's default sdist selection bundles .tbd/docs, agent integrations, workflows, and unrelated repository files. Restrict the sdist to build-required source and add a CI regression check while preserving wheel-from-sdist builds.
