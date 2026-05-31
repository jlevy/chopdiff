---
type: is
id: is-01ksw0xbv39fmw4cbpgn7te023
title: "P3a: decide root package API / naming"
kind: task
status: closed
priority: 3
version: 2
spec_path: docs/project/specs/active/plan-2026-05-26-robustness-hardening.md
labels: []
dependencies: []
parent_id: is-01kstdjjj25gp4h9jrnnxkwnzd
created_at: 2026-05-30T08:44:48.866Z
updated_at: 2026-05-30T09:08:48.521Z
closed_at: 2026-05-30T09:08:48.521Z
close_reason: Documented library-only root API in __init__.py; root re-exports deferred to DocOverview public-API work.
---
File: src/chopdiff/__init__.py (empty). Decide root-level convenience exports vs library-only with submodule imports; coordinate with the DocOverview/public-API direction so it's decided once. Likely: keep library-only for now and document, OR re-export TextDoc/TextUnit/etc. TDD/check: documented decision; if exporting, an import smoke test.
