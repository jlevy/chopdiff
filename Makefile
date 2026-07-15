# Makefile for easy development workflows.
# See docs/development.md for docs.
# Note GitHub Actions call uv directly, not this Makefile.

.DEFAULT_GOAL := default

.PHONY: default install hooks-install lint lint-check format test upgrade build clean

# An explicit config file prevents unrelated user-level uv settings from changing the
# project resolution policy. Its values mirror [tool.uv] in pyproject.toml.
UV := uv --config-file $(CURDIR)/.uv-policy.toml

# Markdown formatter, pinned for reproducibility. Run in an isolated uv tool
# environment, so it is independent of the project environment. The
# Excluded paths live in .flowmarkignore.
FLOWMARK_VERSION := 0.3.1
FLOWMARK := $(UV) tool run flowmark-rs@$(FLOWMARK_VERSION)

# Git hook manager, pinned. Installed and run in an isolated uv tool environment.
LEFTHOOK := $(UV) tool run lefthook@2.1.9

default: install lint test

install:
	$(UV) sync --locked --all-extras

# One-time: install the git hooks that auto-format on commit (see lefthook.yml).
hooks-install:
	$(LEFTHOOK) install

lint:
	$(UV) run --locked python devtools/lint.py

# Check-only lint, matching CI (does not modify files).
lint-check:
	$(UV) run --locked python devtools/lint.py --check

# Auto-format all Markdown in place. The lefthook pre-commit hook delegates here,
# so commits are formatted before they ever reach CI. Pass `.` as the sole target
# so flowmark traverses the repo and honors .flowmarkignore + .gitignore.
format:
	$(FLOWMARK) --auto .

test:
	$(UV) run --locked pytest

upgrade:
	$(UV) sync --upgrade --all-extras --dev

build:
	$(UV) build --no-sources

clean:
	-rm -rf dist/
	-rm -rf *.egg-info/
	-rm -rf .pytest_cache/
	-rm -rf .mypy_cache/
	-rm -rf .venv/
	-find . -type d -name "__pycache__" -exec rm -rf {} +
