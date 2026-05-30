---
type: is
id: is-01ksw0xcayrk7p611eetqzhwrb
title: "P3b: examples use pathlib.Path; remove dead --output"
kind: task
status: open
priority: 3
version: 1
spec_path: docs/project/specs/active/plan-2026-05-26-robustness-hardening.md
labels: []
dependencies: []
parent_id: is-01kstdjjj25gp4h9jrnnxkwnzd
created_at: 2026-05-30T08:44:49.374Z
updated_at: 2026-05-30T08:44:49.374Z
---
File: examples/insert_para_breaks.py (open() at ~109; unused -o/--output at ~104). Fix: use Path(...).read_text(); remove or implement --output. TDD: example imports cleanly; smoke-run where no network needed.
