# chopdiff — Open Work

A concise index of planned work, the specs that describe it, and the beads that track
it. Status as of 2026-05-29 (v0.4.0 in review on PR #12).

Beads are tracked with `tbd` (git-native, on the `tbd-sync` branch). View them with:

```shell
tbd list           # open issues
tbd show <id>      # details + working notes (e.g. tbd show chopdiff-1x4u)
```

> **Bead-store note (2026-05-29):** the synced store is on tbd format `f04`, newer than
> the published `tbd` CLI (≤ 0.1.30 supports `f03`), so closing/syncing beads needs a
> newer `tbd`. The block-aware epic below is code-complete but its beads still read
> `open`; close them with a compatible `tbd`.

## Active plans

### Robustness hardening — `docs/project/specs/active/`

Correctness and API-contract fixes from the engineering review. Several findings were
already resolved in v0.3.0 (exact source offsets, console-script removal, tiktoken
dropped, nested self-closing tag fix, documented mutation contract); the rest are open.

- Spec: [plan-2026-05-26-robustness-hardening.md](docs/project/specs/active/plan-2026-05-26-robustness-hardening.md)
  (status: Draft).
- Beads: the earlier umbrella/phase beads (`chopdiff-3o4e`, `-ptf0`, `-2cgj`, `-z3js`)
  are **no longer in the synced store** — recreate the tracking beads when this work is
  picked up.

## Completed

### Block-aware document model / normalized form — shipped in v0.4.0 (PR #12)

`TextDoc` gained exact `[start, end)` spans, a section/TOC hierarchy with rolled-up
stats, inline-link rollups, link-aware sentences, and an opt-in structural block tree —
all in place on `TextDoc`, not a parallel model. Phase 5 then replaced chopdiff's regex
block scanner with flowmark's authoritative block spans (flowmark 0.7.1), and Phase 6
added the normalized-form views: `BlockType.ordered_list`, density-invariant lists
(`Block.tight`), `Section.blocks()`, and derived `block_type_counts()` rollups (no stored
counts).

- Design of record: [docs/textdoc-spec.md](docs/textdoc-spec.md).
- Implementation plan (archived): [plan-2026-05-26-block-aware-doc.md](docs/project/specs/archive/plan-2026-05-26-block-aware-doc.md).
- Epic `chopdiff-d6js` + children: `chopdiff-3dwm` (flowmark track), `chopdiff-1x4u`
  (Phase 5 refactor), `chopdiff-3ygz` / `-3bdw` / `-kvsg` / `-1aew` (Phase 6 features),
  `chopdiff-0c4c` (end-to-end example). All code-complete; see the bead-store note above
  about closing them.

## Source material

- Engineering review (pre-v0.3.0):
  [docs/project/review/senior-engineering-review-chopdiff-pre-v0.3.0.md](docs/project/review/senior-engineering-review-chopdiff-pre-v0.3.0.md)
  — origin of the robustness findings.
- Research survey (background on related systems — stand-off markup, lossless trees,
  CRDT, block-JSON, djot — informing the document model):
  [docs/project/research/research-2026-05-29-document-model.md](docs/project/research/research-2026-05-29-document-model.md).

## Known gaps not yet in any plan

Surfaced by the review reconciliation; fold into the robustness spec when picked up:

- `parse_tag()` extracts only double-quoted `\w+` attributes (misses single-quoted,
  unquoted, hyphenated, boolean attrs).
- No root-level `chopdiff` public API; no decision recorded on whether to add one.
- CI runs Ubuntu only; no wheel install/import smoke test.

## Archive

- [docs/project/specs/archive/plan-2026-05-26-block-aware-doc.md](docs/project/specs/archive/plan-2026-05-26-block-aware-doc.md)
  — completed; shipped in v0.4.0. Superseded as a living doc by `docs/textdoc-spec.md`.
- [docs/project/specs/archive/plan-2026-05-26-markdown-block-segmentation.md](docs/project/specs/archive/plan-2026-05-26-markdown-block-segmentation.md)
  — superseded by the block-aware-doc plan (proposed a parallel `MarkdownDoc` module;
  the chosen direction extends `TextDoc` in place).
