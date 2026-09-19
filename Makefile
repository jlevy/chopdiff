# Makefile for easy development workflows.
# See docs/development.md for docs.
# Note GitHub Actions call uv directly, not this Makefile.

.DEFAULT_GOAL := default

.PHONY: default install hooks-install lint lint-check format test audit upgrade build clean

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

# Vulnerability auditor, pinned. Isolated so pip-audit (and pip) never enter uv.lock.
# 2.10.1 published 2026-06-10; older than the project cutoff. Bump deliberately.
PIP_AUDIT_VERSION := 2.10.1
PIP_AUDIT := $(UV) tool run pip-audit@$(PIP_AUDIT_VERSION)
AUDIT_REQS := /tmp/chopdiff-audit-requirements.txt

default: install lint test

install:
	$(UV) sync --locked --all-extras --all-groups

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

# Audit locked runtime, extras, and dev/build deps. Does not install pip-audit
# into the project environment; see SUPPLY-CHAIN-SECURITY.md.
audit:
	$(UV) export --locked --all-extras --all-groups --no-emit-project -o $(AUDIT_REQS)
	$(PIP_AUDIT) -r $(AUDIT_REQS)

upgrade:
	$(UV) sync --upgrade --all-extras --all-groups

build: install
	$(UV) build --python .venv/bin/python --no-build-isolation --no-sources

clean:
	-rm -rf dist/
	-rm -rf *.egg-info/
	-rm -rf .pytest_cache/
	-rm -rf .ruff_cache/
	-rm -rf .mypy_cache/
	-rm -rf .venv/
	-find . -type d -name "__pycache__" -exec rm -rf {} +
