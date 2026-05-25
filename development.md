# Development

## Setting Up uv

This project is set up to use [uv](https://docs.astral.sh/uv/) to manage Python and
dependencies. First, be sure you
[have uv installed](https://docs.astral.sh/uv/getting-started/installation/).

Then [fork the jlevy/chopdiff
repo](https://github.com/jlevy/chopdiff/fork) (having your own
fork will make it easier to contribute) and
[clone it](https://docs.github.com/en/repositories/creating-and-managing-repositories/cloning-a-repository).

## Basic Developer Workflows

The `Makefile` simply offers shortcuts to `uv` commands for developer convenience.
(For clarity, GitHub Actions don't use the Makefile and just call `uv` directly.)

```shell
# First, install all dependencies and set up your virtual environment.
# This simply runs `uv sync --all-extras` to install all packages,
# including dev dependencies and optional dependencies.
make install

# Run uv sync, lint, and test (and also generate agent rules):
make

# Build wheel:
make build

# Linting:
make lint

# Run tests:
make test

# Delete all the build artifacts:
make clean

# Upgrade dependencies to compatible versions:
make upgrade

# To run tests by hand:
uv run pytest   # all tests
uv run pytest -s src/module/some_file.py  # one test, showing outputs

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

## Dependencies

chopdiff keeps a deliberately small dependency surface. Each direct dependency and why
it is here:

**Runtime:**

- [strif](https://github.com/jlevy/strif) — Zero-dependency string and file utilities
  (atomic writes, hashing, `replace_multiple`).
- [flowmark](https://github.com/jlevy/flowmark) — Markdown line-wrapping and
  auto-formatting.
- [prettyfmt](https://github.com/jlevy/prettyfmt) — Human-friendly object and value
  formatting (used in `__repr__`s).
- [funlog](https://github.com/jlevy/funlog) — Logging and timing decorators.
- [cydifflib](https://github.com/rapidfuzz/CyDifflib) — Fast drop-in replacement for the
  standard library `difflib`, used for token-level diffing.
- [tiktoken](https://github.com/openai/tiktoken) — OpenAI BPE tokenizer, used for token
  counting.
- [regex](https://github.com/mrabarnett/mrab-regex) — Regex engine with Unicode features
  beyond the standard library `re`.
- [selectolax](https://github.com/rushter/selectolax) — Fast HTML parser (lexbor), used
  for HTML-aware chunking.

**Optional (`extras`):**

- [simplemma](https://github.com/adbar/simplemma) — Lightweight multilingual lemmatizer.

**Dev and tooling:**

- [pytest](https://docs.pytest.org/) + [pytest-sugar](https://github.com/Teemu/pytest-sugar) — Test runner.
- [ruff](https://docs.astral.sh/ruff/) — Linter and formatter.
- [basedpyright](https://docs.basedpyright.com/) — Type checker.
- [codespell](https://github.com/codespell-project/codespell) — Spell checker for code and docs.
- [rich](https://github.com/Textualize/rich) — Console output for the lint script.
- [pip-audit](https://github.com/pypa/pip-audit) — Vulnerability audit (`audit` group; run in CI).

Dependencies are upgraded under a 14-day cool-off. See
[SUPPLY-CHAIN-SECURITY.md](SUPPLY-CHAIN-SECURITY.md).

## Agent Rules

See [.cursor/rules](.cursor/rules) for agent rules.
These are written for [Cursor](https://www.cursor.com/) but are also used by other
agents because the Makefile will generate `CLAUDE.md` and `AGENTS.md` from the same
rules.

```shell
make agent-rules
```

## IDE setup

If you use VSCode or a fork like Cursor or Windsurf, you can install the following
extensions:

- [Python](https://marketplace.visualstudio.com/items?itemName=ms-python.python)

- [Based Pyright](https://marketplace.visualstudio.com/items?itemName=detachhead.basedpyright)
  for type checking. Note that this extension works with non-Microsoft VSCode forks like
  Cursor.

## Documentation

- [uv docs](https://docs.astral.sh/uv/)

- [basedpyright docs](https://docs.basedpyright.com/latest/)

* * *

*This file was built with
[simple-modern-uv](https://github.com/jlevy/simple-modern-uv).*
