# Makefile for easy development workflows.
# See docs/development.md for docs.
# Note GitHub Actions call uv directly, not this Makefile.

.DEFAULT_GOAL := default

.PHONY: default install hooks-install lint lint-check format test upgrade build clean

# Markdown formatter, pinned for reproducibility. Run via uvx (outside the
# project env), so it is independent of the project's cool-off pin. The
# Excluded paths live in .flowmarkignore.
FLOWMARK_VERSION := 0.3.1
FLOWMARK := uvx flowmark-rs@$(FLOWMARK_VERSION)

# Git hook manager, pinned. Installed and run via uvx (no npm dependency).
LEFTHOOK := uvx lefthook@2.1.9

default: install lint test

install:
	uv sync --locked --all-extras

# One-time: install the git hooks that auto-format on commit (see lefthook.yml).
hooks-install:
	$(LEFTHOOK) install

lint:
	uv run --locked python devtools/lint.py

# Check-only lint, matching CI (does not modify files).
lint-check:
	uv run --locked python devtools/lint.py --check

# Auto-format all Markdown in place. The lefthook pre-commit hook delegates here,
# so commits are formatted before they ever reach CI. Pass `.` as the sole target
# so flowmark traverses the repo and honors .flowmarkignore + .gitignore.
format:
	$(FLOWMARK) --auto .

test:
	uv run --locked pytest

upgrade:
	uv sync --upgrade --all-extras --dev

build:
	uv build --no-sources

clean:
	-rm -rf dist/
	-rm -rf *.egg-info/
	-rm -rf .pytest_cache/
	-rm -rf .mypy_cache/
	-rm -rf .venv/
	-find . -type d -name "__pycache__" -exec rm -rf {} +
