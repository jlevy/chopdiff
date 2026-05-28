---
type: is
id: is-01ksgpjj44exp9q485r92f2pjd
title: Full dependency upgrade under 14-day cool-off
kind: task
status: closed
priority: 1
version: 3
labels: []
dependencies: []
parent_id: is-01ksgpj76w79rwg3e67hn5efnj
created_at: 2026-05-25T23:12:30.340Z
updated_at: 2026-05-25T23:23:31.678Z
---
Run uv sync --upgrade with UV_EXCLUDE_NEWER set to a 14-day-old cutoff. Review lockfile diff. Bump pyproject lower bounds only where warranted.
