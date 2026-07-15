"""
Automated validation of the supply-chain hardening policy. See
SUPPLY-CHAIN-SECURITY.md. These guard mistakes that can silently weaken reproducibility
or the cool-off:

- The cool-off cutoff in `pyproject.toml` and `uv.lock` drifting apart, which makes
  uv discard the lockfile and re-resolve *without* the cool-off.
- Adding a per-package cool-off exception without recording it in the marker doc.
- Using a mutable GitHub Action reference.
- Letting routine developer or CI commands re-resolve the environment.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent
_PYPROJECT = _REPO_ROOT / "pyproject.toml"
_LOCK = _REPO_ROOT / "uv.lock"
_MAKEFILE = _REPO_ROOT / "Makefile"
_MARKER = _REPO_ROOT / "SUPPLY-CHAIN-SECURITY.md"
_POLICY_CONFIG = _REPO_ROOT / ".uv-policy.toml"
_WORKFLOWS = _REPO_ROOT / ".github" / "workflows"


def _uv_config() -> dict[str, object]:
    return tomllib.loads(_PYPROJECT.read_text())["tool"]["uv"]


def test_cool_off_cutoff_matches_lockfile() -> None:
    config_cutoff = _uv_config()["exclude-newer"]
    lock_cutoff = tomllib.loads(_LOCK.read_text())["options"]["exclude-newer"]
    assert config_cutoff == lock_cutoff


def test_explicit_uv_policy_matches_project_config() -> None:
    assert tomllib.loads(_POLICY_CONFIG.read_text()) == _uv_config()
    for workflow in sorted([*_WORKFLOWS.glob("*.yml"), *_WORKFLOWS.glob("*.yaml")]):
        workflow_text = workflow.read_text()
        if "run: uv " in workflow_text:
            assert "UV_CONFIG_FILE: .uv-policy.toml" in workflow_text


def test_cool_off_exceptions_are_documented() -> None:
    exceptions = _uv_config().get("exclude-newer-package", {})
    assert isinstance(exceptions, dict)
    marker = _MARKER.read_text()
    undocumented = [pkg for pkg in exceptions if pkg not in marker]
    assert not undocumented


def test_github_actions_are_pinned_to_commit_shas() -> None:
    unpinned: list[str] = []
    for workflow in sorted([*_WORKFLOWS.glob("*.yml"), *_WORKFLOWS.glob("*.yaml")]):
        for line_number, line in enumerate(workflow.read_text().splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            action_value = stripped.partition("uses:")[2].strip()
            if not action_value:
                continue
            action = action_value.split(maxsplit=1)[0]
            if action.startswith("./"):
                continue
            _, separator, revision = action.rpartition("@")
            if not separator or not re.fullmatch(r"[0-9a-f]{40}", revision):
                unpinned.append(f"{workflow.name}:{line_number}: {action}")

    assert not unpinned


def test_routine_make_targets_use_the_lockfile() -> None:
    routine_targets = {"install", "lint", "lint-check", "test"}
    current_target: str | None = None
    checked_targets: set[str] = set()
    unlocked: list[str] = []

    for line in _MAKEFILE.read_text().splitlines():
        if line and not line[0].isspace() and ":" in line:
            current_target = line.partition(":")[0]
        elif current_target in routine_targets and line.startswith("\t"):
            command = line.strip()
            if command.startswith(("uv ", "$(UV) ")) and (
                " sync " in command or " run " in command
            ):
                checked_targets.add(current_target)
                if "--locked" not in command:
                    unlocked.append(f"{current_target}: {command}")

    assert not unlocked
    assert checked_targets == routine_targets


def test_workflow_sync_and_run_commands_use_the_lockfile() -> None:
    unlocked: list[str] = []
    for workflow in sorted([*_WORKFLOWS.glob("*.yml"), *_WORKFLOWS.glob("*.yaml")]):
        for line_number, line in enumerate(workflow.read_text().splitlines(), start=1):
            command = line.partition("run:")[2].strip()
            if command.startswith(("uv sync ", "uv run ")) and "--locked" not in command:
                unlocked.append(f"{workflow.name}:{line_number}: {command}")

    assert not unlocked


def test_standalone_script_dependencies_are_exactly_pinned() -> None:
    unpinned: list[str] = []
    for script in sorted((_REPO_ROOT / "examples").glob("*.py")):
        lines = script.read_text().splitlines()
        if "# /// script" not in lines:
            continue
        start = lines.index("# /// script") + 1
        end = lines.index("# ///", start)
        metadata = tomllib.loads("\n".join(line.removeprefix("# ") for line in lines[start:end]))
        dependencies = metadata.get("dependencies", [])
        for dependency in dependencies:
            if "==" not in dependency:
                unpinned.append(f"{script.name}: {dependency}")

        lock_path = script.with_name(f"{script.name}.lock")
        if not lock_path.exists():
            unpinned.append(f"{script.name}: missing script lockfile")
            continue
        lock = tomllib.loads(lock_path.read_text())
        locked_requirements = {
            f"{requirement['name']}{requirement['specifier']}"
            for requirement in lock["manifest"]["requirements"]
        }
        for dependency in dependencies:
            if dependency not in locked_requirements:
                unpinned.append(f"{script.name}: not in script lockfile: {dependency}")

        project_uv = _uv_config()
        script_uv = metadata.get("tool", {}).get("uv", {})
        if script_uv.get("exclude-newer") != project_uv.get("exclude-newer"):
            unpinned.append(f"{script.name}: project cutoff mismatch")
        if script_uv.get("exclude-newer-package") != project_uv.get("exclude-newer-package"):
            unpinned.append(f"{script.name}: package exception mismatch")

    assert not unpinned
