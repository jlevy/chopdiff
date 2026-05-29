# chopdiff — Open Work

A concise index of planned work, the specs that describe it, and the beads that track
it. Status as of 2026-05-28 (post-v0.3.0).

Beads are tracked with `tbd` (git-native, on the `tbd-sync` branch). View them with:

```shell
tbd list           # open issues
tbd show <id>      # details + working notes (e.g. tbd show chopdiff-ptf0)
```

## Active plans

### Robustness hardening — `docs/project/specs/active/`

Correctness and API-contract fixes from the engineering review. Several findings were
already resolved in v0.3.0 (exact source offsets, console-script removal, tiktoken
dropped, nested self-closing tag fix, documented mutation contract); the rest are open.

- Spec: [plan-2026-05-26-robustness-hardening.md](docs/project/specs/active/plan-2026-05-26-robustness-hardening.md)
- Beads:
  - `chopdiff-3o4e` (P1, feature) — umbrella
    - `chopdiff-ptf0` (P1) — Phase 1: release blockers, transform/chunking bugs
    - `chopdiff-2cgj` (P1) — Phase 2: TextDoc diff/mapping/offset contracts
    - `chopdiff-z3js` (P2) — Phase 3: HTML helpers, docs, release workflow

### Block-aware document model — `docs/project/specs/active/`

Builds on v0.3.0's block-aware `TextDoc`: exact `[start, end)` spans, a section/TOC
hierarchy, inline-link rollups, link-aware sentences, and an opt-in structural-block
tree — all in place on `TextDoc`, not a parallel model.

- Spec: [plan-2026-05-26-block-aware-doc.md](docs/project/specs/active/plan-2026-05-26-block-aware-doc.md)
- Bead: `chopdiff-jh56` (P2, feature) — blocked by `chopdiff-2cgj` (needs hardened
  TextDoc offset/copy contracts first)

## Source material

- Engineering review (pre-v0.3.0, commit `0ad8288`):
  [docs/review/senior-engineering-review-chopdiff-pre-v0.3.0.md](docs/review/senior-engineering-review-chopdiff-pre-v0.3.0.md)
  — origin of the robustness findings.
- Research survey:
  [docs/project/research/research-2026-05-29-document-model.md](docs/project/research/research-2026-05-29-document-model.md)
  — source-grounded, cross-language document model; informs the block-aware plan.

## Known gaps not yet in any plan

Surfaced by the review reconciliation; fold into the robustness spec when picked up:

- `parse_tag()` extracts only double-quoted `\w+` attributes (misses single-quoted,
  unquoted, hyphenated, boolean attrs).
- No root-level `chopdiff` public API; no decision recorded on whether to add one.
- CI runs Ubuntu only; no wheel install/import smoke test.

## Archive

- [docs/project/specs/archive/plan-2026-05-26-markdown-block-segmentation.md](docs/project/specs/archive/plan-2026-05-26-markdown-block-segmentation.md)
  — superseded by the block-aware-doc plan (proposed a parallel `MarkdownDoc` module;
  the chosen direction extends `TextDoc` in place).
