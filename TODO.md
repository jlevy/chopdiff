# chopdiff: Open Work

A concise index of planned work, the specs that describe it, and the beads that track
it. Status as of 2026-06-02 (v0.4.0 — block-aware model + DocGraph Phase 1 — code-complete
on branch, pending release; latest published release is v0.3.0).

Beads are tracked with `tbd` (git-native, on the `tbd-sync` branch). View them with:

```shell
tbd list           # open issues
tbd show <id>      # details + working notes (e.g. tbd show chopdiff-1x4u)
```

> **Bead-store note (2026-05-29):** the synced store is on tbd format `f04`, newer than
> the published `tbd` CLI (≤ 0.1.30 supports `f03`), so closing/syncing beads needs a
> newer `tbd`. The block-aware epic below is code-complete but its beads still read
> `open`; close them with a compatible `tbd`.

## Active Plans

### Flexible Unified Document Model (DocGraph): `docs/project/specs/active/`

**Phase 1 code-complete (pending release with v0.4.0); later phases remain.** A
source-grounded, JSON-serializable `DocGraph` projected from `TextDoc`: a stable node
table (each node tagged with its parse **layer**) and derived views, and one general
`collect()` query (values/counts/groupings via standard Python) at any scope
(doc/section/block), recursive, over blocks and inline items, with the source-canonical
`SpanRef` reference model and composable `include`/`detail` serialization. The
**layered-parsing lens** (E9) frames the views as parse layers (textual / markdown /
document / synthetic) over one offset space, with cross-layer relationships as
offset-containment queries. Subsumes the multi-level block-tallies work.

- Shipped in Phase 1 (on branch): recursive layer-tagged node table, `base_blocks()`,
  `collect()` with `subtree_of=`/`within=`/`overlaps=` relations, `SpanRef`
  (exact-quote resolution), the `DocGraph` Pydantic projection (`DocGraph/v0.1`),
  `to_yaml()`, and the `chopdiff.docs.debug` dumper.
- Remaining (later phases, via the four Phase-1 hooks): the synthetic (marker-tag)
  layer, cross-layer structural edits, and `SpanRef` fuzzy re-anchoring.
- Spec: [plan-2026-05-29-unified-document-model.md](docs/project/specs/active/plan-2026-05-29-unified-document-model.md)
  (status: **decisions settled (DR-1..DR-6) and E9 layered lens; Phase 1 implemented**).
  Design of record: [docs/textdoc-spec.md](docs/textdoc-spec.md).
- Research: the [document-model survey](docs/project/research/research-2026-05-29-document-model.md),
  [span-references](docs/project/research/research-2026-05-30-span-references.md), and
  [multi-layer parsing](docs/project/research/research-2026-05-30-multilayer-parsing.md) briefs.
- Beads: epic `chopdiff-8q8q`; decisions gate `chopdiff-0vy6` closed. **Next: break the
  remaining phases (synthetic layer, cross-layer edits, fuzzy re-anchoring) into beads.**

### Robustness Hardening: `docs/project/specs/active/`

Correctness and API-contract fixes from the engineering review, **re-reviewed 2026-05-29
against current v0.4.0 code**. Findings already fixed (console script, absolute offsets,
`from_text` doc honesty, publish `--locked`, quiet tests) are recorded as resolved; the
open items are verified with current evidence and grouped into three phases.

- Spec: [plan-2026-05-26-robustness-hardening.md](docs/project/specs/active/plan-2026-05-26-robustness-hardening.md)
  (status: **Implemented (Phases 1–3) on branch, pending release**).
- Beads: epic `chopdiff-pdu2` → `chopdiff-pytp` (Phase 1), `chopdiff-y0cd` (Phase 2),
  `chopdiff-xvqb` (Phase 3), all closed, with per-finding child beads.
- Done TDD: filter-bypass, `sub_doc`/`sub_paras` copy semantics, paragraph windowing, div
  chunking, library asserts→exceptions, `WindowSettings` validation, stitching, `apply_to`
  identity, `TokenMapping` metric, empty-doc wordtoks (Phase 1); nested self-closing,
  tag/attr validation, strict mode, empty-vs-missing attr, multi-class matching, exception
  cause, `parse_tag` docs (Phase 2); root-API docstring, examples `Path`/`--output`,
  validation (Phase 3). Foundation for the document-model work is now in place.

## Completed

### Block-Aware Document Model / Normalized Form: Shipped in v0.4.0 (PR #12)

`TextDoc` gained exact `[start, end)` spans, a section/TOC hierarchy with rolled-up
stats, inline-link rollups, link-aware sentences, and an opt-in structural block
tree—all in place on `TextDoc`, not a parallel model. Phase 5 then replaced
chopdiff's regex block scanner with flowmark's authoritative block spans (flowmark
0.7.1), and Phase 6 added the normalized-form views: `BlockType.ordered_list`,
density-invariant lists
(`Block.tight`), `Section.blocks()`, and derived `block_type_counts()` rollups (no stored
counts).

- Design of record: [docs/textdoc-spec.md](docs/textdoc-spec.md).
- Implementation plan (archived): [plan-2026-05-26-block-aware-doc.md](docs/project/specs/archive/plan-2026-05-26-block-aware-doc.md).
- Epic `chopdiff-d6js` and children: `chopdiff-3dwm` (flowmark track), `chopdiff-1x4u`
  (Phase 5 refactor), `chopdiff-3ygz` / `-3bdw` / `-kvsg` / `-1aew` (Phase 6 features),
  `chopdiff-0c4c` (end-to-end example). All code-complete; see the bead-store note above
  about closing them.

## Source Material

- Engineering review (pre-v0.3.0):
  [docs/project/review/senior-engineering-review-chopdiff-pre-v0.3.0.md](docs/project/review/senior-engineering-review-chopdiff-pre-v0.3.0.md)
  (origin of the robustness findings).
- Research survey (background on related systems, including stand-off markup, lossless trees,
  CRDT, block-JSON, and djot, informing the document model):
  [docs/project/research/research-2026-05-29-document-model.md](docs/project/research/research-2026-05-29-document-model.md).

## Known Gaps Not Yet in Any Plan

Surfaced by the review reconciliation; fold into the robustness spec when picked up:

- `parse_tag()` extracts only double-quoted `\w+` attributes (misses single-quoted,
  unquoted, hyphenated, boolean attrs).
- No root-level `chopdiff` public API; no decision recorded on whether to add one.
- CI runs Ubuntu only; no wheel install/import smoke test.

## Archive

- [docs/project/specs/archive/plan-2026-05-26-block-aware-doc.md](docs/project/specs/archive/plan-2026-05-26-block-aware-doc.md)
  (completed; shipped in v0.4.0). Superseded as a living doc by `docs/textdoc-spec.md`.
- [docs/project/specs/archive/plan-2026-05-26-markdown-block-segmentation.md](docs/project/specs/archive/plan-2026-05-26-markdown-block-segmentation.md)
  (superseded by the block-aware-doc plan; proposed a parallel `MarkdownDoc` module;
  the chosen direction extends `TextDoc` in place).
- [docs/project/specs/archive/plan-2026-05-29-multilevel-block-tallies.md](docs/project/specs/archive/plan-2026-05-29-multilevel-block-tallies.md)
  (folded into the unified document model plan; kept for its detailed nested-block/caching
  trade-off analysis; its four decisions are now in that plan's Open decisions).
