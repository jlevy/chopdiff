---
type: is
id: is-01ksr9rafqbkx4v7egankdpcya
title: "Track: flowmark next release with block-span support (PR #52)"
kind: task
status: open
priority: 1
version: 4
spec_path: docs/project/specs/active/plan-2026-05-26-block-aware-doc.md
labels: []
dependencies:
  - type: blocks
    target: is-01ksqrs8wnrxdgyp0ezdbphfaj
parent_id: is-01kshh1bwwdg57dx0yybgm8b9m
created_at: 2026-05-28T22:02:23.095Z
updated_at: 2026-05-28T22:03:12.673Z
---
Tracking bead — no code change in this repo. Watch jlevy/flowmark for the next release that includes PR #52 (block spans). When merged + published to PyPI:

1. Verify the release passes chopdiff's 14-day cool-off (or document and approve the first-party exception in SUPPLY-CHAIN-SECURITY.md, same pattern as the v0.7.0 exception).
2. Bump flowmark in pyproject.toml.
3. Unblock chopdiff-1x4u (the refactor).

PR status link: https://github.com/jlevy/flowmark/pull/52
