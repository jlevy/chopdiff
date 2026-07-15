# Development

## Setting Up uv

This project is set up to use [uv](https://docs.astral.sh/uv/) to manage Python and
dependencies. First, be sure you
[have uv installed](https://docs.astral.sh/uv/getting-started/installation/).

Then [fork the jlevy/chopdiff repo](https://github.com/jlevy/chopdiff/fork) (having your
own fork will make it easier to contribute) and
[clone it](https://docs.github.com/en/repositories/creating-and-managing-repositories/cloning-a-repository).

## Basic Developer Workflows

The `Makefile` simply offers shortcuts to `uv` commands for developer convenience.
(For clarity, GitHub Actions don’t use the Makefile and just call `uv` directly.)
Both pass the explicit `.uv-policy.toml` config so user-level uv settings cannot alter
the repository’s cool-off policy.
For direct uv commands, first run `export UV_CONFIG_FILE=.uv-policy.toml` in the
repository root.

```shell
# First, install all dependencies and set up your virtual environment.
# This runs `uv sync --locked --all-extras` to install the exact locked packages,
# including dev dependencies and optional dependencies.
make install

# One-time: install the git hooks (lefthook) that auto-format Markdown and
# Python on commit, so trivial formatting never reaches CI.
make hooks-install

# Run uv sync, lint, and test:
make

# Build wheel:
make build

# Linting (auto-fixes formatting and lint issues):
make lint

# Linting in check-only mode, matching CI (fails on issues, does not modify files):
make lint-check

# Auto-format all Markdown docs with flowmark (the lefthook pre-commit hook runs
# this automatically; run it by hand if you skipped hooks or want a manual pass):
make format

# Run tests:
make test

# Delete all the build artifacts:
make clean

# Upgrade dependencies to compatible versions:
make upgrade

# To run tests by hand:
uv run --locked pytest   # all tests
uv run --locked pytest -s src/module/some_file.py  # one test, showing outputs

# Build and install current dev executables, to let you use your dev copies
# as local tools:
uv tool install --editable .

# Dependency management directly with uv:
# Add a new dependency:
uv add package_name
# Add a development dependency:
uv add --dev package_name
# Update to latest compatible versions (including dependencies on git repos):
uv sync --upgrade
# Update a specific package:
uv lock --upgrade-package package_name
# Update dependencies on a package:
uv add package_name@latest

# Run a shell within the Python environment:
uv venv
source .venv/bin/activate
```

See [uv docs](https://docs.astral.sh/uv/) for details.

## IDE Setup

If you use VSCode or a fork like Cursor or Windsurf, you can install the following
extensions:

- [Python](https://marketplace.visualstudio.com/items?itemName=ms-python.python)

- [Based Pyright](https://marketplace.visualstudio.com/items?itemName=detachhead.basedpyright)
  for type checking. Note that this extension works with non-Microsoft VSCode forks like
  Cursor.

## Supply Chain Hardening

Dependencies are an attack surface.
Before adding or upgrading any dependency, follow
[**supply-chain-hardening**](https://github.com/jlevy/supply-chain-hardening), a concise
cross-ecosystem guide on installing dependencies safely.
Its key defaults:

- **Cool-off period:** Don’t install or upgrade to a release less than 14 days old
  (absent a documented exception)—most malicious publishes are caught within days.
  This project pins the cutoff in `[tool.uv] exclude-newer` in `pyproject.toml` (uv
  takes a date, not a duration), so `uv lock`, `uv sync`, and `uv run` all honor it.

- **Vet before adding:** Confirm the package is actually needed and its name is spelled
  correctly (typosquats are common), and prefer a little first-party code over a new
  dependency.

- **Pin, lock, and audit:** Commit your `uv.lock`, install frozen in CI
  (`uv sync --locked`), pin GitHub Actions to a commit SHA or immutable tag, and run a
  vulnerability audit (`pip-audit`, run by the CI `audit` job) after changes.

The full project policy, the upgrade procedure, and the active cool-off exceptions are
documented in [`SUPPLY-CHAIN-SECURITY.md`](../SUPPLY-CHAIN-SECURITY.md).

## Dependencies

chopdiff keeps a deliberately small dependency surface.
Each direct dependency and why it is here:

**Runtime:**

- [flexdoc](https://github.com/jlevy/flexdoc): Document model, tokenization, token
  diffs, source mappings, and Markdown/HTML helpers
- [flowmark](https://github.com/jlevy/flowmark): Markdown normalization for sliding
  paragraph windows
- [prettyfmt](https://github.com/jlevy/prettyfmt): Human-readable structural summaries
- [typing-extensions](https://github.com/python/typing_extensions): Python 3.11 support
  for newer typing features such as `@override`

FlexDoc owns its document-layer dependencies, including `cydifflib`, `marko`, `regex`,
`selectolax`, and the first-party `frontmatter-format`, `funlog`, and `strif` packages.
They should not become direct chopdiff dependencies unless chopdiff imports them
directly.

**Optional (`extras`):**

- [simplemma](https://github.com/adbar/simplemma): Lightweight multilingual lemmatizer

**Dev and tooling:**

- [pytest](https://docs.pytest.org/) and
  [pytest-sugar](https://github.com/Teemu/pytest-sugar): Test runner
- [ruff](https://docs.astral.sh/ruff/): Linter and formatter
- [basedpyright](https://docs.basedpyright.com/): Type checker
- [codespell](https://github.com/codespell-project/codespell): Spell checker for code
  and docs
- [rich](https://github.com/Textualize/rich): Console output for the lint script
- [pip-audit](https://github.com/pypa/pip-audit): Vulnerability audit (`audit` group;
  run in CI)

## Publishing Releases

See [publishing.md](publishing.md) for instructions on publishing to PyPI.

## Documentation

- [uv docs](https://docs.astral.sh/uv/)

- [basedpyright docs](https://docs.basedpyright.com/latest/)

* * *

*This file was built with
[simple-modern-uv](https://github.com/jlevy/simple-modern-uv).*
