# Supply-Chain Security

This repo applies a lightweight supply-chain hardening policy. **Read this before
adding or upgrading any dependency.** It exists because the open-source registries
(PyPI included) are under steady attack: malicious package versions get published,
try to exfiltrate credentials or install persistence, and are usually yanked within
minutes to days. Waiting out that window neutralizes most of the risk at the cost of
slightly staler dependencies.

This is the project-local flag file. The full cross-ecosystem policy lives in the
[supply-chain-hardening guidebook](https://github.com/jlevy/supply-chain-hardening).

## The Rules Here

1. **14-day cool-off.** Never resolve to a package version less than 14 days old.
   In this uv project the cutoff is enforced by `exclude-newer` in `pyproject.toml`,
   so `uv lock`, `uv sync`, and `uv run` all honor it: dev and CI install the same
   vetted versions and nothing silently pulls a just-published release.
2. **Commit the lockfile; install frozen.** `uv.lock` is committed. CI installs with
   `uv sync --locked`, which fails if the lock and `pyproject.toml` have drifted.
   Never re-resolve without reviewing the lockfile diff like a code diff.
3. **Prefer wheels; review build code.** Building an sdist runs arbitrary code. Prefer
   prebuilt wheels (`uv` does by default) and treat any source build as code to review.
4. **Audit after changes.** Run `pip-audit` (CI runs it on every push) and address
   findings before merging.
5. **Don't upgrade for its own sake.** The safest upgrade is the one you skip: each
   bump is fresh attack surface. Bump for a concrete reason: a needed feature, a fix,
   or a CVE.

## How the Cool-Off Is Configured

`pyproject.toml` carries the cutoff as a full RFC 3339 timestamp (uv rejects a bare
date in this field):

```toml
[tool.uv]
exclude-newer = "2026-05-11T00:00:00Z"
```

uv records this cutoff inside `uv.lock`. If the cutoff in config and lock disagree (for
example, if you set `UV_EXCLUDE_NEWER` to a different value), uv treats the lock as
stale and silently re-resolves **without** the cool-off, so keep the cutoff in
`pyproject.toml` rather than passing it only on the command line.

## Upgrading Dependencies

Bumping the cutoff date is the upgrade action. Set it to 14 days ago and re-lock:

```shell
# Move the cool-off window forward, then re-resolve within it.
NEW_CUTOFF="$(date -u -d '14 days ago' +%Y-%m-%dT00:00:00Z)"   # GNU date (Linux)
# macOS: NEW_CUTOFF="$(date -u -v-14d +%Y-%m-%dT00:00:00Z)"
sed -i "s|^exclude-newer = .*|exclude-newer = \"$NEW_CUTOFF\"|" pyproject.toml

make upgrade   # uv sync --upgrade --all-extras --dev
make lint test
```

Review the `uv.lock` diff before committing: confirm the version jumps are expected and
that no unexpected new dependency appeared.

## Exception Process

When a version inside the 14-day window is genuinely needed, take the exception
**explicitly and on the record**. Pin it with a per-package override and document the
reason. Agents never self-approve an exception: a human signs off.

uv supports per-package cutoffs:

```toml
[tool.uv.exclude-newer-package]
some-package = "2026-05-24T00:00:00Z"
```

When the over-age package no longer needs the exception (its normal-cutoff version has
caught up), remove the override and re-lock.

### Active Exceptions

- **idna 3.15** (published 2026-05-12, inside the window). Fixes CVE-2026-45409,
  reported against the in-window 3.14 by `pip-audit`. idna is a widely used,
  pure-Python package. The fix is ~13 days old, one day short of the floor. Approved by
  the maintainer, 2026-05-25. Remove this override once 3.15 clears the 14-day window.

- **strif 3.1.0** (published 2026-05-23, inside the window). First-party,
  zero-dependency package. Its full `3.0.1 → 3.1.0` source diff was reviewed before
  the override was added: bug fixes (backup-path check, file-descriptor leak), an
  atomic `Path.replace`, new `atomic_write_text`/`atomic_write_bytes` helpers, and
  `Insertion`/`Replacement` changed from tuple type aliases to `NamedTuple`s. No new
  dependencies, build hooks, network calls, or install scripts. Reviewed and approved
  by the maintainer, 2026-05-25.

- **flowmark 0.7.1** (published 2026-05-29, inside the window). First-party package,
  authored and maintained by the same maintainer. Adopted for the authoritative block
  spans added in [jlevy/flowmark#52](https://github.com/jlevy/flowmark/pull/52):
  `flowmark_markdown().parse(text)` now attaches `element.span = (start, end)` to every
  block element at every nesting level, read straight from marko's own `Source.pos`, and
  `flowmark.markdown_ast.block_span` / `walk_elements` expose it. chopdiff adopts this to
  drop its own regex block scanner (Phase 5). The full `0.7.0 → 0.7.1` source diff was
  reviewed: the span-recording overrides in `formats/flowmark_markdown.py`
  (`CustomListItem`, `parse_source`, `parse`), the `block_span` helper in
  `markdown_ast.py`, and CLI/skill-install changes (`--surfaces`). No dependency changes
  (`Requires-Dist` identical to 0.7.0), no build hooks, no network calls, no install
  scripts. Reviewed and approved by the maintainer, 2026-05-29. Remove this override once
  0.7.1 clears the 14-day window.

- **flexdoc 0.1.0** (published 2026-06-12, inside the window). First-party package,
  authored and maintained by the same maintainer: the document model extracted from
  this repo's own `src/flexdoc/` (Stage 1 of the flexdoc extraction plan), refined and
  published from jlevy/flexdoc. Parse behavior is identical to the in-repo copy (golden
  fixtures byte-for-byte); only Python surfaces changed (`TextDoc` renamed `FlexDoc`,
  editing-view method renames, keyword-only `collect()`). The maintainer directed this
  migration in [chopdiff#27](https://github.com/jlevy/chopdiff/issues/27), which is the
  sign-off. Remove this override once 0.1.0 clears the 14-day window.

### Audit-Gate Ignores

Distinct from the cool-off overrides above: `pip-audit --ignore-vuln <ID>` suppresses a
specific advisory at the audit gate (`.github/workflows/ci.yml`). Use it only for a finding
in a **tool dependency that chopdiff does not ship** and that has no fix available within
the cool-off window. It does not change dependency resolution or the cool-off.

- **PYSEC-2026-196 in `pip`.** `pip` is only present as a transitive dependency of the
  `pip-audit` tool (audit group); it is not a chopdiff runtime/dev dependency and is never
  shipped in the chopdiff wheel. The fix (`pip` 26.1.2) is newer than the `exclude-newer`
  cutoff (2026-05-11), so there is no within-policy bump. Ignored at the audit gate to keep
  CI green; applied at the maintainer's direction and **pending explicit ratification**.
  Remove the `--ignore-vuln PYSEC-2026-196` once the cutoff advances past pip 26.1.2's
  release (it then resolves normally and the advisory clears).

## Untrusted Repositories

Treat any freshly cloned third-party repo as untrusted. Don't run `install` / `build` /
`test` / `run` against it on a machine with credentials until you've reviewed it:
`build` backends, import-time code, and test files all execute code. Prefer a container
or sandbox.
