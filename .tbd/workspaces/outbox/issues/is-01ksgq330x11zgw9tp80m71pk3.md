---
type: is
id: is-01ksgq330x11zgw9tp80m71pk3
title: Fix exclude-newer guidance in tbd guideline + simple-modern-uv
kind: task
status: open
priority: 2
version: 2
labels: []
dependencies: []
parent_id: is-01ksgpj76w79rwg3e67hn5efnj
created_at: 2026-05-25T23:21:31.933Z
updated_at: 2026-05-25T23:37:39.748Z
---
Findings: (1) tbd supply-chain-hardening guideline says UV_EXCLUDE_NEWER='14 days' but uv 0.8.17 rejects relative durations - needs absolute date/timestamp. (2) [tool.uv] exclude-newer requires full RFC3339 timestamp (bare date rejected in config though accepted on CLI). (3) uv ignores the lockfile and re-resolves WITHOUT cool-off if env cutoff differs from lock's recorded cutoff - must persist exclude-newer in pyproject so dev+CI agree. (4) simple-modern-uv template ships no supply-chain hardening. File issues on jlevy/tbd and jlevy/simple-modern-uv. NOTE: GitHub MCP is scoped to jlevy/chopdiff only, so cannot file cross-repo from here - prepare drafts.

## Notes

BLOCKED on cross-repo access: GitHub MCP here is scoped to jlevy/chopdiff only; cannot file on jlevy/tbd or jlevy/simple-modern-uv. Drafts ready:

TBD GUIDELINE (supply-chain-hardening): uv row says UV_EXCLUDE_NEWER='14 days' but uv 0.8.17 rejects relative durations (needs absolute date/timestamp). [tool.uv] exclude-newer needs a full RFC3339 timestamp (bare date rejected in config, accepted on CLI). If env cutoff differs from the lock's recorded cutoff, uv discards the lock and re-resolves WITHOUT the cool-off. Recommend: commit exclude-newer in pyproject.toml and install --locked in CI.

SIMPLE-MODERN-UV TEMPLATE: ships no supply-chain hardening. Consider shipping by default: [tool.uv] exclude-newer cutoff, a SUPPLY-CHAIN-SECURITY.md marker, and a pip-audit CI gate.
