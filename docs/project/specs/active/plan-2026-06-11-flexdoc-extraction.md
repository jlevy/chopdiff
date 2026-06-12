# Feature: FlexDoc Package Extraction (Staged)

**Date:** 2026-06-11 (last updated 2026-06-11)

**Author:** Joshua Levy

**Status:** Draft

## Overview

The document/markdown model that chopdiff has grown — `TextDoc`, the block/section/inline
structure, the node table and `DocGraph`, span references, html-in-md, frontmatter — is a
general, reusable *document layer* that does not depend on chopdiff's diff and
windowed-transform machinery. This plan extracts it into a standalone package (working name
**FlexDoc**) so it can be used and evolved on its own, and so chopdiff becomes a thin
diff/transform layer built **on** FlexDoc.

FlexDoc's north star reaches past the extraction: to be one of the most flexible foundations
in Python for processing and understanding complex documents — for careful editing and for
deep analysis alike. The aim is to identify and understand a complex Markdown document at a
genuinely granular level along several independent axes at once: its **Markdown syntax**
(blocks, inline elements, exact spans, typed attributes), its **grammar and language**
(paragraphs, sentences, tokens, lemmas, and further linguistic structure), and, where useful,
**other structures** layered onto the same text (marked-up regions, citations, annotations).
That granularity is what enables the use cases driving this work: deep textual analysis,
source-grounded annotation and cleanup of documents, and structural editing that survives
reparse. The package extraction below is the enabling first step; the forward design (Stage 3)
is where FlexDoc grows into that role, on the layered model the unified-document-model plan has
already settled (see North star below).

The extraction is deliberately split into four stages, each on its own branch (and, from
Stage 2, its own repo). The first stage is the load-bearing one and the only one this branch
implements: a **pure, behavior-preserving in-repo refactor** that splits the code into two
import roots (`src/flexdoc/` and `src/chopdiff/`) shipped in a **single wheel**, with the
sole job of proving and *enforcing* a clean one-way dependency cut (`flexdoc` imports nothing
from `chopdiff`). Only once that boundary is real and green under the existing test suite do
we pay for separate packaging, a separate repo, and a breaking release. Everything after
Stage 1 then becomes mechanical or purely additive.

## Goals

- **A self-contained document-layer API.** `flexdoc` is the markdown/document model
  (parse → `TextDoc`/`DocGraph`, `collect()`, spans/`SpanRef`, sections, frontmatter, render,
  html-in-md), usable with no dependency on chopdiff.
- **Granular, multi-axis understanding.** Expose a document's structure at a fine grain across
  independent axes — Markdown syntax, linguistic structure, and other layered structures —
  over one shared, source-grounded coordinate space.
- **Flexible and extensible by construction.** New parse layers, node kinds, typed attributes,
  and analyzers are additive; they extend the model without reshaping its core, so FlexDoc
  adapts to new document structures and analyses without churn.
- **A correct, enforced one-way boundary (Stage 1).** `flexdoc` never imports `chopdiff`;
  `chopdiff` imports `flexdoc`. Enforced by a dependency-free test so the seam cannot rot.
- **Behavior preservation in Stage 1.** Same logic, same public behavior, same tests passing —
  only module locations and import paths change. No redesign, no new features.
- **A mechanical, low-risk split and release (Stage 2).** With the boundary already proven,
  giving `flexdoc` its own `pyproject.toml`, repo, dependency subset, and PyPI release is a
  lift-and-shift, and chopdiff's switch to depending on the external `flexdoc` is the single
  intended breaking release.
- **One policy throughout Stage 1.** One CI, one lint/type config, one supply-chain cool-off
  governing both import roots until the repo actually splits.

## Non-Goals

- **No behavior or API changes in Stage 1.** No new functionality, no signature changes, no
  surface redesign; the diff is moves + import rewrites + one enforcement test.
- **No separate build config or publishing in Stage 1.** One distribution, one wheel
  containing both import roots; `flexdoc` is not independently installable yet.
- **No synthetic-layer / `divs` fold-in into FlexDoc now.** Re-expressing `divs`/`TextNode`
  as FlexDoc's synthetic layer is Stage 4 (later, optional), aligned with the
  unified-document-model plan's Phase 3.
- **No FlexDoc API cleanups or new use-case coverage in Stage 1.** Those are Stage 3, done
  after the package stands alone.
- **No backward-compatibility shims.** Per the project rules, we do not add alias modules or
  re-export shims to keep old `chopdiff.docs.*` paths working; the import paths move and the
  break lands intentionally in the Stage 2/3 release.
- **The forward vision is staged, not retrofitted.** Stages 1–2 add no behavior; the flexible,
  extensible document-understanding design is Stage 3+, deliberately kept out of the refactor.
- **No heavy analysis dependencies in the core.** Linguistic/NLP, layout, and domain-specific
  analysis attach through optional, pluggable analyzers and extras; FlexDoc's base model keeps
  its current light dependency set (and the supply-chain cool-off).

## Background

### Where the code is today

chopdiff is a single distribution with a src layout (`src/chopdiff/`, one `pyproject.toml`,
hatch wheel target `src/chopdiff`, git-based dynamic versioning, supply-chain `exclude-newer`
at the root). Its public stance (`chopdiff/__init__.py`) is "no root-level public API; import
from the submodules." The five top-level submodules are:

- `docs/` — the document model: `TextDoc`, paragraphs/sentences, the block tree and block
  types, sections, the node table, `collect()`, `DocGraph`, `SpanRef`, token diffs/mapping,
  word tokenization, sizes.
- `html/` — html-in-md, html↔plaintext, html tag helpers, the content extractor, timestamps.
- `util/` — lemmatization and token estimation.
- `transforms/` — sliding-window transforms, diff filters, window settings.
- `divs/` — `<div>`/`<span>` structural chunking (`TextNode`, `parse_divs`, chunk utils).

### The dependency graph decides the cut

Mapping the internal imports across the five modules makes the boundary almost entirely
forced, not a matter of taste:

- `docs/` ↔ `html/` are **mutually dependent**: `docs/sizes.py` imports
  `html.html_plaintext`, and `html/timestamps.py` imports `docs.search_tokens`/`docs.wordtoks`.
  Separating them would mean editing code, not moving it, so they stay on the same side.
- `util/` imports nothing internal (a leaf) and `docs/` depends on it, so `util/` follows
  `docs/`.
- `{docs, html, util}` is **closed**: nothing in it imports `divs` or `transforms`. This is
  the clean FlexDoc cluster.
- `transforms/` depends only on `docs` + `util` (both FlexDoc) and nothing imports it — it is
  the chopdiff side.
- `divs/` is a **pure consumer** (imports `docs` + `html`; nothing depends on it), so it can
  sit on either side without affecting the boundary. See Open Questions.

A consequence of moving whole modules (to preserve code): `docs/token_diffs.py` — the diff
*primitives* — travels into FlexDoc with the rest of `docs/`, because it is cyclically tied to
`docs.text_doc`. So FlexDoc carries the token-diff *algorithm*; chopdiff keeps the diff
*filters* and windowed transforms. Relocating `token_diffs` later is a separate finer refactor
(Stage 3 candidate), not a Stage-1 move.

### External dependencies, preliminary partition

From the third-party imports per module (finalized precisely in Stage 2 by the boundary, when
each side gets its own `pyproject.toml`):

- **FlexDoc** (`docs`/`html`/`util`): `flowmark`, `marko`, `cydifflib`, `funlog`, `regex`,
  `strif`, `frontmatter-format`, `pydantic`, `prettyfmt`, `selectolax`. No optional extras.
- **chopdiff** after extraction (`transforms`, plus `divs` if it stays): `flexdoc`, plus the
  small set its own code uses directly (`flowmark`, `prettyfmt`), plus the optional extra
  `simplemma` (for `chopdiff.util.lemmatize`, used only by `transforms.diff_filters`).
  chopdiff becomes a thin layer over FlexDoc.

`lemmatize` was moved out of FlexDoc into `chopdiff.util` (it is used only by the diff
filters, not by the document model), so `simplemma` is chopdiff's optional extra, not
FlexDoc's — keeping the FlexDoc core dependency-light.

### What FlexDoc houses, and a naming caveat

The model being extracted is already substantial and designed, not a sketch: per the design of
record (`docs/textdoc-spec.md` §14), v0.3.1 already ships the node table, the single `collect()`
query primitive, the `base_blocks()` partition, the `DocGraph/v0.1` Pydantic schema, and the
`SpanRef` contract (exact + prefix/suffix; fuzzy re-anchoring deferred). The remaining
unified-document-model phases (annotation, synthetic, cross-layer edits, layout) are in progress.
So Stage 1 relocates a mature, source-grounded layered model; it does not build one — which is
exactly why a clean module extraction is feasible now.

**Naming caveat.** textdoc-spec §13 lists "FlexDoc" among its **non-goals** — but as the name of
a *rejected competing runtime model* (`BlockDoc`/`SectionDoc`/`FlexDoc`, from an abandoned
branch), distinct from `TextDoc`/`DocGraph`. The package working-named FlexDoc here is the
opposite of that non-goal: it is the **home of the existing `TextDoc`/`DocGraph`**, not a second
model. The collision is only in the name; whether to keep "FlexDoc" (with an explicit
disambiguation in textdoc-spec) or rename is an open decision (see Open Questions).

### Relation to the other active plans

This is the "FlexDoc package extraction" design doc that
[`plan-2026-06-11-structural-metadata.md`](plan-2026-06-11-structural-metadata.md) and
[`plan-2026-05-29-unified-document-model.md`](plan-2026-05-29-unified-document-model.md)
both reference as forthcoming. The structural-metadata plan completes the markdown layer's
typed-attribute surface and is sequenced **before** Stage 1, so the extraction lifts a
finalized surface rather than churning it afterward. The unified-document-model plan owns the
document model FlexDoc will house; its Phase 3 (the synthetic layer) is this plan's Stage 4.

## Design

### Approach

Four stages, separated so risk is paid down before cost is incurred, and so the work is
**incremental early and ambitious late**: Stages 1–2 are deliberately mechanical,
behavior-preserving partial refactors (move code, prove the boundary, split the repo), while
Stages 3–4 are the thorough, careful forward design that grows FlexDoc into a flexible,
extensible document-understanding layer (see North star below). Stage 1 is the only one
implemented on this branch; Stages 2–4 are mapped here so the whole series is legible, and
each will be detailed on its own branch when reached.

### The module cut

| Module | Destination | Reason |
| --- | --- | --- |
| `docs/` | **flexdoc** | The document model core; mutually dependent with `html/`. |
| `html/` | **flexdoc** | html-in-md/plaintext/tags/extractor/timestamps; cycle with `docs/`. |
| `util/` | **flexdoc** | Leaf utilities `docs/` depends on. |
| `transforms/` | **chopdiff** | Diff filters + windowed transforms; depend on flexdoc. |
| `divs/` | **chopdiff** (recommended; open) | Pure consumer; becomes flexdoc's synthetic layer at Stage 4. |

### Stage 1 — pure in-repo refactor (this branch)

One wheel, two import roots, behavior preserved, boundary enforced.

- **Layout:** create `src/flexdoc/` and move `docs/`, `html/`, `util/` (and `divs/` per the
  open decision) into it; `transforms/` (and `divs/` if it stays) remain under `src/chopdiff/`.
- **Import rewrites:** `chopdiff.{docs,html,util}` → `flexdoc.{docs,html,util}` everywhere —
  the moved code, the remaining chopdiff code (`transforms`, `divs`, `__init__`), tests,
  `examples/`, and `devtools/`. Mechanical, no logic edits.
- **`src/flexdoc/__init__.py`:** a module docstring describing FlexDoc's public surface
  (the document-model portion of the current `chopdiff/__init__.py` doc), same "import from
  submodules" stance.
- **`chopdiff/__init__.py`:** update its submodule inventory (drop the `docs`/`html` entries
  that moved out). No re-export shims (project rule); the `chopdiff.docs.*` paths simply
  cease to exist, which is acceptable on an unreleased branch and is what makes the Stage 2/3
  release intentionally breaking.
- **Build:** `[tool.hatch.build.targets.wheel] packages = ["src/chopdiff", "src/flexdoc"]` —
  still one distribution named `chopdiff`, now containing two import packages. `pytest`
  `testpaths` already covers `src`; basedpyright `include` already covers `src`.
- **Boundary enforcement:** `tests/test_package_boundary.py` walks `src/flexdoc/**/*.py`,
  parses each with `ast`, and asserts no `import`/`from` targets `chopdiff`. Stdlib only, no
  new dependency.

### Stage 2 — extract FlexDoc to its own repo and publish (later branch)

With the boundary proven, this is lift-and-shift plus packaging.

- New standalone repo for `flexdoc`; move `src/flexdoc/` and its tests, preserving history
  where practical (`git filter-repo`/subtree).
- Give `flexdoc` its own `pyproject.toml`: build-system, dynamic versioning, the dependency
  **subset** (partitioned from the analysis above and confirmed by the boundary), and a
  mirror of the supply-chain `exclude-newer` cool-off and lint/type config.
- Publish `flexdoc` to PyPI (confirm the distribution name).
- In chopdiff: delete the moved modules, add `flexdoc>=<first published>` as a dependency,
  drop the now-flexdoc-only dependencies from chopdiff's `pyproject.toml`, and rewrite the
  remaining code's imports to the external `flexdoc`.

### North star: a layered, extensible document model

What makes FlexDoc flexible is not a feature list but a shape: a **stable node table over a
single source-grounded coordinate space**, with the document's many structures expressed as
**independent, composable parse layers** rather than one privileged tree. This is the
architecture the design of record (`docs/textdoc-spec.md`, principles P1–P5) and the
unified-document-model plan (E9, DR-1..DR-6) settled, and much of it already ships (Background);
FlexDoc is its home and polished public form, **not a new or competing model**. The granularity
the vision asks for falls out of three properties:

- **One coordinate space, many layers** (P1, P3). Every layer (textual, markdown, document,
  synthetic, annotation, ...) anchors to the same Unicode-code-point offsets; a node is
  `{id, kind, layer, parent, children, source_span, attrs}`. Layers coexist by span, so
  structures that overlap or cross-cut — a section spanning sibling blocks, a link inside a
  sentence inside a `<div>` — are all representable without forcing one hierarchy.
- **One query, any grain** (P4). A single `collect()` primitive — selecting by `kinds`/`where`,
  by within-layer subtree (`subtree_of`, `recursive`), or by cross-layer offset-containment
  (`within`/`overlaps`), restricted by `layer` — answers everything from "every code block's
  language" to "which sentences fall inside this annotated region"; values, counts, and
  relationships are ordinary Python over the result, not a fixed menu.
- **One reference type** (DR-6). `SpanRef` (quote-canonical, offset-hinted) anchors annotations
  and edits to the text so they survive reparse — what makes source-grounded annotation and
  structural editing tractable.

The three understanding axes the vision names map directly onto layers, and each is an
**extension axis, not a fixed schema**:

| Axis | Layer(s) | State today | How it extends |
| --- | --- | --- | --- |
| Markdown syntax | `markdown` | Most complete (blocks, inline, typed `attrs`, exact spans) | New element kinds / typed `attrs` as additive node fields. |
| Grammar and language | `textual` (+ optional analyzers) | Seeds: paragraphs, sentences, word tokens, lemmas | Pluggable analyzers add POS, syntax, language, entities as nodes/attrs — opt-in, not in the core. |
| Other structures | `synthetic`, `annotation`, later `layout` | Reserved / partial (`divs` today) | New marker-tag vocabularies and stand-off layers key into the same node table. |

Two principles keep this flexible without becoming heavy or unstable:

- **Keep the core light; make enrichment pluggable.** The base model parses Markdown and text
  structure with the existing light dependencies. Heavier or domain-specific analysis
  (linguistic NLP backends, layout, citation parsing) attaches through a small analyzer/layer
  interface as **optional extras**, so granular language understanding is available without
  forcing those dependencies (or their supply-chain weight) on every consumer.
- **Extend by adding layers and kinds, never by reshaping the core.** A new structure is a new
  `Layer` and/or `NodeKind` with `attrs`; a new analysis is a function producing nodes against
  the shared offsets. The node table, `collect()`, and `SpanRef` do not change — the whole
  reason for the node-table-not-one-tree decision (DR-1).

### Stage 3 — FlexDoc as a first-class, extensible document-layer API (later, its own repo)

This is where FlexDoc takes up its role; it is meant to be thorough and careful, and it is
detailed in FlexDoc's own forthcoming specs rather than frozen here. The shape of the work:

- **Settle the public surface.** Decide and document FlexDoc's top-level API (including the
  root-level convenience re-exports `chopdiff/__init__.py` currently defers), so the model is
  designed once as a coherent, discoverable document-layer API — parse, query (`collect`),
  spans/`SpanRef`, sections, frontmatter, render, html-in-md.
- **Make the driving use cases first-class and covered.** Deep textual analysis,
  source-grounded annotation and document cleanup, and reparse-stable structural editing each
  have a clear, tested path with worked examples (the `examples/normalized_form.py` pattern).
- **Land the remaining layered-model phases in FlexDoc.** The model core already ships
  (textdoc-spec §14: node table, `collect()`, `base_blocks()`, `DocGraph/v0.1`, the `SpanRef`
  contract); the remaining unified-document-model phases — the annotation layer, cross-layer
  structural edits, and operation/provenance/layout — land here (the synthetic layer is Stage 4).
- **Deepen the axes deliberately:** *Markdown syntax* to whatever granularity downstream
  analysis needs (already most complete after the structural-metadata plan); *grammar and
  language* via a small, optional **analyzer interface** that grows POS / syntactic / language
  / entity nodes through pluggable, opt-in backends, never pulling heavy NLP into the core;
  *other structures* through the synthetic and (later) annotation/layout layers.
- **Lock in the extension contract.** A documented, stable way to add a `Layer`, a `NodeKind`,
  typed `attrs`, and an analyzer, so third parties extend FlexDoc without forking it; treat
  `token_diffs`'s placement (kept in FlexDoc for v1) as a candidate cleanup here.

Detailed design, dependency choices, and the analyzer interface are FlexDoc's own specs; this
plan fixes the direction and the invariants (layered model, light core, additive extension).

### Stage 4 — fold in the synthetic layer (optional, later)

Once FlexDoc is cleaned, optionally pull the **synthetic document layer** into it:
re-express `divs`/`TextNode`/`parse_divs` as the synthetic layer keyed into the node table,
per the unified-document-model plan's Phase 3. Not done immediately, and only if wanted; if
`divs` stayed in chopdiff at Stage 1, this is where it migrates into FlexDoc.

### API Changes

- **Stage 1 (unreleased):** import paths move (`chopdiff.docs|html|util` → `flexdoc.*`). No
  signature or behavior changes. chopdiff's own surface loses the `docs`/`html` submodules.
- **Stage 2/3 (released):** chopdiff depends on the external `flexdoc`; the moved import paths
  are the breaking change. New `flexdoc` public package.

## Implementation Plan

Only **Stage 1** is implemented on this branch; it is sequenced after
`plan-2026-06-11-structural-metadata.md` lands so the extracted surface is final. Stages 2–4
are mapped for the program and detailed on their own branches.

### Stage 1: pure in-repo refactor (this branch)

- [x] Create `src/flexdoc/` and move `docs/`, `html/`, `util/` into it via `git mv` (renames
      preserved); `transforms/` and `divs/` stay under `src/chopdiff/` (`divs/` kept in
      chopdiff per the recommended option; migrates to flexdoc at Stage 4).
- [x] Add `src/flexdoc/__init__.py` with the document-layer public-surface docstring and a
      `src/flexdoc/py.typed` marker; update `chopdiff/__init__.py`'s submodule inventory.
- [x] Rewrite all `chopdiff.{docs,html,util}` imports to `flexdoc.*` across `src/`, `tests/`,
      and `examples/` (64 `.py` files). No logic edits.
- [x] Update `pyproject.toml` wheel target to `["src/chopdiff", "src/flexdoc"]`.
- [x] Add `tests/test_package_boundary.py`: assert (via `ast`, stdlib only) that no
      `src/flexdoc` module imports `chopdiff`.
- [x] `make lint` and `make test` clean (314 passed); `uv build` produces one wheel
      (`chopdiff-*.whl`) whose top-level packages are `chopdiff` and `flexdoc`, and both
      `import flexdoc` and `import chopdiff` succeed.

### Stage 2: extract and publish FlexDoc (later branch / new repo)

This is a **handoff runbook for a fresh agent working in a new repo.** Stage 1 already did
the hard part (the one-way boundary is proven and enforced), so this is copy-and-rewire
plus packaging. The partition below was computed from the merged Stage-1 tree; re-verify
each fact against the source before relying on it (commands given inline).

**Step 1 — Create the new `flexdoc` repo and copy the package.**

- [ ] Copy `src/flexdoc/` verbatim into the new repo as `src/flexdoc/` (the whole package:
      `docs/`, `html/`, `util/`, `__init__.py`, `py.typed`). Inline tests (`## Tests`
      sections in e.g. `block_info.py`, `read_time.py`, `wordtoks.py`) travel with their
      modules. Preserve git history if practical (`git filter-repo --path src/flexdoc` or
      `git subtree split`), else a plain copy is fine.
- [ ] Copy the document-model **tests**: `tests/docs/`, `tests/html/`, and `tests/golden/`
      (including `tests/golden/documents/`, `tests/golden/expected/`, and
      `tests/golden/README.md`), plus `tests/__init__.py`. **Do not** copy
      `tests/test_package_boundary.py` (the boundary becomes a real package dependency) or
      `tests/test_supply_chain.py` (write a fresh one for the new repo's settings).
      `tests/divs/`, `tests/transforms/`, and `tests/util/` (now `chopdiff.util.lemmatize`)
      stay in chopdiff.
- [ ] Copy the document-model **examples** that import only `flexdoc.*`
      (`examples/normalized_form.py`, `examples/doc_structure.py`, and
      `examples/backfill_timestamps.py` — it uses `flexdoc.html`). `insert_para_breaks.py`
      uses `chopdiff.transforms`, so it stays in chopdiff. Verify with
      `grep -l "chopdiff\.\(transforms\|divs\)" examples/*.py`.
- [ ] Copy the **design history** (this model's docs): `docs/textdoc-spec.md` (the design
      of record — it already describes the flexdoc document model), the research briefs
      `docs/project/research/*`, and the plan specs `plan-2026-05-29-unified-document-model.md`,
      `plan-2026-06-11-structural-metadata.md`, `plan-2026-05-31-doc-model-refinements.md`,
      `plan-2026-05-31-golden-doc-testing.md`, and this extraction plan. Leave chopdiff's
      own copies in place (or cross-link).

**Step 2 — Scaffold the new repo's tooling (mirror chopdiff's).**

- [ ] `flexdoc/pyproject.toml`: `[project] name = "flexdoc"`, `requires-python = ">=3.11"`;
      build-system `hatchling` + `uv-dynamic-versioning`;
      `[tool.hatch.build.targets.wheel] packages = ["src/flexdoc"]`. Copy chopdiff's
      `[tool.uv] exclude-newer` cool-off and `[tool.uv.exclude-newer-package]` exceptions,
      and the `[tool.ruff]`/`[tool.basedpyright]` (`include = ["src", "tests"]`)/
      `[tool.codespell]`/`[tool.pytest.ini_options]` (`testpaths = ["src", "tests"]`) blocks.
- [ ] **Dependencies** (`[project.dependencies]`): `flowmark`, `marko`, `cydifflib`,
      `funlog`, `regex`, `strif`, `frontmatter-format`, `pydantic`, `prettyfmt`,
      `selectolax`, `typing-extensions`. **No optional extras** — `simplemma`/`lemmatize`
      stayed in chopdiff. Re-derive and confirm the exact set with:
      `grep -rhoE '^(from|import) [a-z_]+' src/flexdoc | grep -oE '^[a-z_]+ [a-z_]+' | awk '{print $2}' | sort -u`
      then drop stdlib and `flexdoc` itself. Keep version floors at chopdiff's current pins.
- [ ] Copy `Makefile`, `devtools/lint.py`, `.github/workflows/ci.yml` (including the
      `wheel-smoke` job and the audit-gate `--ignore-vuln` note),
      `.github/workflows/publish.yml`, `SUPPLY-CHAIN-SECURITY.md`, `.gitignore`, `LICENSE`,
      and a fresh `README.md` + `CHANGELOG.md`. `src/flexdoc/py.typed` is already present.
- [ ] `uv lock` to generate `flexdoc`'s own committed lockfile; `make install`.

**Step 3 — Verify `flexdoc` standalone.**

- [ ] `make lint` and `make test` green in the new repo (the doc-model suite + goldens run
      unchanged; regen goldens only if intentionally changed).
- [ ] `uv build --wheel` produces `flexdoc-*.whl`; isolated import smoke test
      (`uv pip install` into a throwaway venv, `import flexdoc; from flexdoc.docs import TextDoc`).
      The boundary is now structural: `flexdoc` has no `chopdiff` dependency at all.

**Step 4 — Publish `flexdoc`.**

- [ ] Confirm the distribution name `flexdoc` is available on PyPI (`uv pip index versions
      flexdoc`, or check pypi.org); pick an alternative if taken (see Open Questions).
- [ ] Tag and publish `flexdoc 0.1.0` (its own independent version line) via `publish.yml`.

**Step 5 — Rewire chopdiff to depend on the external `flexdoc` (the breaking release).**

- [ ] In chopdiff: `git rm -r src/flexdoc/` and remove the moved tests
      (`tests/{docs,html,golden}/`) and `tests/test_package_boundary.py`; keep
      `tests/{divs,transforms,util}/`. The `chopdiff.{transforms,divs,util}` code already
      imports `flexdoc.*` for the document model, so **no import rewrite is needed** — those
      imports now resolve to the external package.
- [ ] `pyproject.toml`: add `flexdoc>=<first published>`; **remove** the now-flexdoc-only
      deps (`marko`, `cydifflib`, `funlog`, `regex`, `strif`, `frontmatter-format`,
      `pydantic`, `selectolax`); **keep** `flowmark` and `prettyfmt` (used directly by
      `transforms`/`divs`) and the `extras = ["simplemma"]` group (used by
      `chopdiff.util.lemmatize`). Remove `src/flexdoc` from the wheel target (back to
      `packages = ["src/chopdiff"]`). `uv lock`.
- [ ] `make lint` and `make test` green against the published `flexdoc`; the `wheel-smoke`
      job now imports only `chopdiff` (with `flexdoc` pulled as a dependency).
- [ ] `CHANGELOG.md`: this is chopdiff's first release depending on external `flexdoc` — a
      **breaking** release (the `chopdiff.docs|html|util.*` paths are gone). Note the
      migration (`pip install flexdoc`; `chopdiff.docs.* -> flexdoc.docs.*`).

### Stage 3: FlexDoc as a first-class, extensible document-layer API (later, its own repo)

- [ ] Settle and document FlexDoc's public surface (including the deferred root-level
      re-exports) as one coherent document-layer API.
- [ ] Make the driving use cases first-class and tested — deep textual analysis,
      source-grounded annotation/cleanup, reparse-stable editing — with worked examples.
- [ ] Land the remaining unified-document-model phases (annotation, cross-layer edits, layout)
      in FlexDoc; the model core already ships (textdoc-spec §14).
- [ ] Add the optional **analyzer interface** for the grammar/language axis (opt-in backends,
      light core preserved); deepen the Markdown and other-structure axes as needed.
- [ ] Document the extension contract (add a `Layer` / `NodeKind` / `attrs` / analyzer);
      revisit `token_diffs` placement.

### Stage 4: synthetic layer (optional, later)

- [ ] Re-express `divs`/`TextNode` as FlexDoc's synthetic layer (unified-document-model
      Phase 3), keyed into the node table by span.

## Testing Strategy

- **Stage 1 acceptance is behavior preservation:** the existing `src/` inline tests and
  `tests/` suite pass unchanged after the moves and import rewrites — that is the proof no
  behavior shifted. Plus the new boundary test, and a build smoke check that one wheel exposes
  both `flexdoc` and `chopdiff`. `make lint` and `make test` clean.
- **Stage 2:** `flexdoc`'s suite passes standalone in its repo; chopdiff's suite passes
  against the published `flexdoc`; both repos green in CI.
- **Stages 3–4:** per the unified-document-model plan and FlexDoc's own forthcoming specs.

## Rollout Plan

- **Stage 1** ships nothing — it is an unreleased branch; no version change. It is the
  correctness gate for everything after.
- **Stage 2** publishes `flexdoc` on its own version line (starting at its own `0.x`).
- **Stage 3 release** is chopdiff's first release depending on the external `flexdoc`; because
  the document-model import paths moved (`chopdiff.docs.*` → `flexdoc.*`), it is **breaking**,
  flagged in `CHANGELOG.md` with a migration note, under the pre-1.0 minor-bump policy.
- Each repo keeps its own supply-chain `exclude-newer` cool-off; `flexdoc`'s `pyproject.toml`
  mirrors chopdiff's policy.

## Resolved Decisions

- **Intermediate one-wheel / two-import-root layout (maintainer-confirmed).** Stage 1 ships a
  single distribution with `src/flexdoc/` and `src/chopdiff/` as two import roots. It is a
  standard temporary Python layout that proves the dependency cut before any packaging cost.
- **The cut is forced by the import graph.** `{docs, html, util}` → flexdoc (a closed
  cluster; `docs`↔`html` cycle; `util` a leaf under `docs`); `transforms` → chopdiff. Only
  `divs` is a free choice.
- **Whole-module moves, no logic edits (preserve code).** Stage 1 is moves + import rewrites
  + one test; `token_diffs` travels into flexdoc as a consequence of the `docs` cycle.
- **No backward-compatibility shims.** Old `chopdiff.docs.*` paths are not aliased; the break
  is intentional and lands in the Stage 2/3 release (project rule on backward compatibility).
- **Boundary enforced by a dependency-free test**, not a new lint dependency, honoring the
  supply-chain cool-off.

## Open Questions

- **`divs/` placement for Stage 1.** Resolved for Stage 1: **kept in chopdiff** (the
  recommended option — it is chunking, matching chopdiff's identity, and keeps flexdoc a
  minimal closed core), to migrate into FlexDoc as the synthetic layer at Stage 4. Still
  revisitable before that migration; it does not affect the rest of the boundary.
- **FlexDoc distribution name.** Is `flexdoc` available on PyPI? Confirm at Stage 2.
- **`token_diffs` long-term home.** Forced into flexdoc for v1 by the `docs` cycle; whether to
  relocate the diff primitives to chopdiff later (Stage 3) is open.
- **Test-file relocation timing.** Stage 1 can either rewrite doc-model test imports in place
  or co-locate them under a flexdoc-mirroring tree now to make the Stage 2 move a clean lift.
  Leaning: rewrite in place at Stage 1, relocate at Stage 2.
- **Sequencing confirmation.** Stage 1 assumes `plan-2026-06-11-structural-metadata.md` lands
  first so the extracted surface is final.
- **Depth and backends of the grammar/language axis.** How far the textual layer goes (POS,
  syntax, language ID, entities) and which optional backends sit behind the analyzer interface
  are FlexDoc Stage-3 decisions, constrained by the light-core and supply-chain principles.
- **Which "other structures" to prioritize** (citations, code structure, domain markup) as
  synthetic/annotation layers.
- **The extension-interface shape** — how a third party registers a `Layer`/`NodeKind`/analyzer
  — to be designed in FlexDoc's own spec.
- **The name "FlexDoc".** It collides with textdoc-spec §13's non-goal (a rejected competing
  runtime model of the same name). Keep it with an explicit disambiguation, or choose a
  non-colliding name, before Stage 2 publishes.

## References

- Design of record: [`docs/textdoc-spec.md`](../../../textdoc-spec.md).
- Unified document model (houses the model FlexDoc owns; synthetic layer = its Phase 3 / this
  plan's Stage 4): [`plan-2026-05-29-unified-document-model.md`](plan-2026-05-29-unified-document-model.md).
- Markdown-layer completion (prerequisite; references this extraction doc):
  [`plan-2026-06-11-structural-metadata.md`](plan-2026-06-11-structural-metadata.md).
- Layered-model backing:
  [`research-2026-05-30-multilayer-parsing.md`](../../research/research-2026-05-30-multilayer-parsing.md)
  and [`research-2026-05-30-span-references.md`](../../research/research-2026-05-30-span-references.md).
- Downstream consumer driving the surface: chopdiff issues
  [#18](https://github.com/jlevy/chopdiff/issues/18)–[#22](https://github.com/jlevy/chopdiff/issues/22)
  (pprose).

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
