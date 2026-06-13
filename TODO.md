# chopdiff: Open Work

A concise index of planned work, the specs that describe it, and the beads that track
it. Status as of 2026-06-11. v0.3.1 (block-aware model + DocGraph Phase 1) is released.
Since then, on `main`: the document model was extracted into the **`flexdoc`** package
(one wheel, two import roots — `src/flexdoc` and `src/chopdiff`); typed code/table/list
block metadata and `NodeKind.footnote_ref` were added; `block_type_counts()` was
removed; and a `read_time` util was salvaged.
See CHANGELOG **Unreleased** and
[plan-2026-06-11-flexdoc-extraction.md](docs/project/specs/active/plan-2026-06-11-flexdoc-extraction.md)
(Stage 1 done; Stages 2–4 — extract to a new repo and publish — are the next program).

Beads are tracked with `tbd` (git-native, on the `tbd-sync` branch).
View them with:

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

**Phase 1 code-complete (pending release with v0.3.1); later phases remain.** A
source-grounded, JSON-serializable `DocGraph` projected from `TextDoc`: a stable node
table (each node tagged with its parse **layer**) and derived views, and one general
`collect()` query (values/counts/groupings via standard Python) at any scope
(doc/section/block), recursive, over blocks and inline items, with the source-canonical
`SpanRef` reference model and composable `include`/`detail` serialization.
The **layered-parsing lens** (E9) frames the views as parse layers (textual / markdown /
document / synthetic) over one offset space, with cross-layer relationships as
offset-containment queries.
Subsumes the multi-level block-tallies work.

- Shipped in Phase 1 (on branch): recursive layer-tagged node table, `base_blocks()`,
  `collect()` with `subtree_of=`/`within=`/`overlaps=` relations, `SpanRef` (exact-quote
  resolution), the `DocGraph` Pydantic projection (`DocGraph/v0.1`), `to_yaml()`, and
  the `flexdoc.docs.debug` dumper.
- Remaining (later phases, via the four Phase-1 hooks): the synthetic (marker-tag)
  layer, cross-layer structural edits, and `SpanRef` fuzzy re-anchoring.
- Spec:
  [plan-2026-05-29-unified-document-model.md](docs/project/specs/active/plan-2026-05-29-unified-document-model.md)
  (status: **decisions settled (DR-1..DR-6) and E9 layered lens; Phase 1 implemented**).
  Design of record: [docs/textdoc-spec.md](docs/textdoc-spec.md).
- Research: the
  [document-model survey](docs/project/research/research-2026-05-29-document-model.md),
  [span-references](docs/project/research/research-2026-05-30-span-references.md), and
  [multi-layer parsing](docs/project/research/research-2026-05-30-multilayer-parsing.md)
  briefs.
- Beads: epic `chopdiff-8q8q`; decisions gate `chopdiff-0vy6` closed.
  **Next: break the remaining phases (synthetic layer, cross-layer edits, fuzzy
  re-anchoring) into beads.**

### Robustness Hardening: `docs/project/specs/active/`

Correctness and API-contract fixes from the engineering review, **re-reviewed 2026-05-29
against current v0.3.1 branch code**. Findings already fixed (console script, absolute
offsets, `from_text` doc honesty, publish `--locked`, quiet tests) are recorded as
resolved; the open items are verified with current evidence and grouped into three
phases.

- Spec:
  [plan-2026-05-26-robustness-hardening.md](docs/project/specs/active/plan-2026-05-26-robustness-hardening.md)
  (status: **Implemented (Phases 1–3) on branch, pending release**).
- Beads: epic `chopdiff-pdu2` → `chopdiff-pytp` (Phase 1), `chopdiff-y0cd` (Phase 2),
  `chopdiff-xvqb` (Phase 3), all closed, with per-finding child beads.
- Done TDD: filter-bypass, `sub_doc`/`sub_paras` copy semantics, paragraph windowing,
  div chunking, library asserts→exceptions, `WindowSettings` validation, stitching,
  `apply_to` identity, `TokenMapping` metric, empty-doc wordtoks (Phase 1); nested
  self-closing, tag/attr validation, strict mode, empty-vs-missing attr, multi-class
  matching, exception cause, `parse_tag` docs (Phase 2); root-API docstring, examples
  `Path`/`--output`, validation (Phase 3). Foundation for the document-model work is now
  in place.

## Completed

### Block-Aware Document Model / Normalized Form: Shipped in v0.3.1 (PR #12)

`TextDoc` gained exact `[start, end)` spans, a section/TOC hierarchy with rolled-up
stats, inline-link rollups, link-aware sentences, and an opt-in structural block
tree—all in place on `TextDoc`, not a parallel model.
Phase 5 then replaced chopdiff’s regex block scanner with flowmark’s authoritative block
spans (flowmark 0.7.1), and Phase 6 added the normalized-form views:
`BlockType.ordered_list`, density-invariant lists (`Block.tight`), `Section.blocks()`,
and derived `block_type_counts()` rollups (no stored counts; `block_type_counts()` was
later removed post-v0.3.1, superseded by `collect()`).

- Design of record: [docs/textdoc-spec.md](docs/textdoc-spec.md).
- Implementation plan (archived):
  [plan-2026-05-26-block-aware-doc.md](docs/project/specs/archive/plan-2026-05-26-block-aware-doc.md).
- Epic `chopdiff-d6js` and children: `chopdiff-3dwm` (flowmark track), `chopdiff-1x4u`
  (Phase 5 refactor), `chopdiff-3ygz` / `-3bdw` / `-kvsg` / `-1aew` (Phase 6 features),
  `chopdiff-0c4c` (end-to-end example).
  All code-complete; see the bead-store note above about closing them.

## Source Material

- Engineering review (pre-v0.3.0):
  [docs/project/review/senior-engineering-review-chopdiff-pre-v0.3.0.md](docs/project/review/senior-engineering-review-chopdiff-pre-v0.3.0.md)
  (origin of the robustness findings).
- Research survey (background on related systems, including stand-off markup, lossless
  trees, CRDT, block-JSON, and djot, informing the document model):
  [docs/project/research/research-2026-05-29-document-model.md](docs/project/research/research-2026-05-29-document-model.md).

## Known Gaps Not Yet in Any Plan

Surfaced by the review reconciliation:

- `parse_tag()` extracts only double-quoted `\w+` attributes (misses single-quoted,
  unquoted, hyphenated, boolean attrs).
  The limitation is documented as intentional; hardening it is a candidate for the
  FlexDoc public-surface work (extraction Stage 3).
- No root-level public API on `chopdiff`/`flexdoc`; the decision is deferred to FlexDoc
  Stage 3 (settle the document-layer public surface, including root-level re-exports).
- The deprecated `collect()` aliases `scope=`/`contains=` remain; remove when the public
  surface is settled (FlexDoc Stage 3).
- CI runs Ubuntu only.
  (A wheel install/import smoke test is added in the post-extraction cleanup, validating
  the two-import-root wheel.)

## Archive

- [docs/project/specs/archive/plan-2026-05-26-block-aware-doc.md](docs/project/specs/archive/plan-2026-05-26-block-aware-doc.md)
  (completed; shipping in v0.3.1). Superseded as a living doc by `docs/textdoc-spec.md`.
- [docs/project/specs/archive/plan-2026-05-26-markdown-block-segmentation.md](docs/project/specs/archive/plan-2026-05-26-markdown-block-segmentation.md)
  (superseded by the block-aware-doc plan; proposed a parallel `MarkdownDoc` module; the
  chosen direction extends `TextDoc` in place).
- [docs/project/specs/archive/plan-2026-05-29-multilevel-block-tallies.md](docs/project/specs/archive/plan-2026-05-29-multilevel-block-tallies.md)
  (folded into the unified document model plan; kept for its detailed
  nested-block/caching trade-off analysis; its four decisions are now in that plan’s
  Open decisions).
