---
type: is
id: is-01kszj09ybdv7yaxdfbm2afcam
title: "Phase 3: Add layer= filter to collect() and TextDoc.collect(); eliminate cross-layer duplicate nodes; tests"
kind: feature
status: closed
priority: 2
version: 3
spec_path: docs/project/specs/active/plan-2026-05-31-doc-model-refinements.md
labels: []
dependencies: []
created_at: 2026-05-31T17:41:14.314Z
updated_at: 2026-05-31T17:59:41.365Z
closed_at: 2026-05-31T17:59:41.364Z
close_reason: layer= added to collect()/TextDoc.collect(), default all; tests added
---
## Notes

DECISION: layer=set[Layer]|None=None, default=all layers (no privileged default). Principle P4 + never-silently-drop: default-to-markdown would make collect(kinds={section}) silently empty. Additive. See plan Resolved Decisions.
