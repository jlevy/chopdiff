# Supply-Chain Security

This repo applies a lightweight supply-chain hardening policy.
**Read this before adding or upgrading any dependency.** It exists because the
open-source registries (PyPI included) are under steady attack: malicious package
versions get published, try to exfiltrate credentials or install persistence, and are
usually yanked within minutes to days.
Waiting out that window neutralizes most of the risk at the cost of slightly staler
dependencies.

This is the project-local flag file.
The full cross-ecosystem policy lives in the
[supply-chain-hardening guidebook](https://github.com/jlevy/supply-chain-hardening).

## The Rules Here

1. **14-day cool-off.** Never resolve to a package version less than 14 days old.
   In this uv project the cutoff is enforced by `exclude-newer` in `pyproject.toml`, so
   `uv lock`, `uv sync`, and `uv run` all honor it: dev and CI install the same vetted
   versions and nothing silently pulls a just-published release.
2. **Commit the lockfile; install frozen.** `uv.lock` is committed.
   Routine Make targets and CI use `--locked`, which fails if the lock and
   `pyproject.toml` have drifted.
   Never re-resolve without reviewing the lockfile diff like a code diff.
3. **Prefer wheels; review build code.** Building an sdist runs arbitrary code.
   Prefer prebuilt wheels (`uv` does by default) and treat any source build as code to
   review.
4. **Audit after changes.** Run `pip-audit` (CI runs it on every push) and address
   findings before merging.
5. **Don’t upgrade for its own sake.** The safest upgrade is the one you skip: each bump
   is fresh attack surface.
   Bump for a concrete reason: a needed feature, a fix, or a CVE.

## How the Cool-Off Is Configured

`pyproject.toml` carries the cutoff as a full RFC 3339 timestamp (uv rejects a bare date
in this field):

```toml
[tool.uv]
exclude-newer = "2026-06-30T00:00:00Z"
```

uv records this cutoff inside `uv.lock`. If the cutoff in config and lock disagree (for
example, if you set `UV_EXCLUDE_NEWER` to a different value), uv treats the lock as
stale and silently re-resolves **without** the cool-off, so keep the cutoff in
`pyproject.toml` rather than passing it only on the command line.

uv also merges user-level configuration into projects.
Make and CI therefore pass the explicit `.uv-policy.toml` mirror, which prevents
unrelated user settings from changing the project policy.
A supply-chain test requires that mirror to remain identical to `[tool.uv]` in
`pyproject.toml`. Set `UV_CONFIG_FILE=.uv-policy.toml` when running uv directly in this
repository.

## Upgrading Dependencies

Bumping the cutoff date is the upgrade action.
Set it to 14 days ago and re-lock:

```shell
# Move the cool-off window forward, then re-resolve within it.
NEW_CUTOFF="$(date -u -d '14 days ago' +%Y-%m-%dT00:00:00Z)"   # GNU date (Linux)
# macOS: NEW_CUTOFF="$(date -u -v-14d +%Y-%m-%dT00:00:00Z)"
sed -i "s|^exclude-newer = .*|exclude-newer = \"$NEW_CUTOFF\"|" pyproject.toml

make upgrade   # uv sync --upgrade --all-extras --all-groups
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

- **flexdoc 0.3.0** (published 2026-07-11, inside the window).
  First-party package authored and maintained by the same maintainer.
  The release fixes CRLF offset corruption, frontmatter parse leakage, ambiguous span
  resolution, and mutation of cached structural views, and it settles several pre-1.0
  APIs. chopdiff already imports token and diff helpers from their owning modules, so the
  0.3 export cleanup does not require compatibility shims here.
  The dependency is bounded to `<0.4.0` because FlexDoc documents breaking pre-1.0
  changes at each minor version.
  The maintainer explicitly authorized first-party cool-off exemptions for this upgrade
  on 2026-07-14. Remove the override after 0.3.0 clears the normal cutoff.

### Audit-Gate Ignores

None. The June 30 cutoff admits fixed `pip` and `msgpack` versions, so the audit runs
without suppressed advisories.

## Dev Hook Tooling

Two dev-time tools run via `uv tool run` (outside the project environment, so they never
enter `uv.lock`). Both are pinned and deliberately upgraded:

- **`flowmark-rs@0.3.1`** — the Markdown formatter (`make format`), wired into the
  `lefthook` pre-commit hook so commits are auto-formatted.
  CI does **not** gate on doc formatting.
  flowmark-rs is first-party (`github.com/jlevy/flowmark`, same maintainer) and 0.3.1 is
  older than the current project cutoff.
  Bump the pin deliberately.
  Reviewed-by: Joshua Levy.
- **`lefthook@2.1.9`** — the git hook manager (`make hooks-install`). Third-party but
  pinned and aged past the 14-day window (published 2026-05-29); `uv tool run` keeps it
  out of the project environment and adds no npm dependency.

## Untrusted Repositories

Treat any freshly cloned third-party repo as untrusted.
Don’t run `install` / `build` / `test` / `run` against it on a machine with credentials
until you’ve reviewed it: `build` backends, import-time code, and test files all execute
code. Prefer a container or sandbox.
