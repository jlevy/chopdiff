"""
Automated validation of the supply-chain hardening policy. See
SUPPLY-CHAIN-SECURITY.md. These guard the two mistakes that are easy to make and
silently weaken the cool-off:

- The cool-off cutoff in `pyproject.toml` and `uv.lock` drifting apart, which makes
  uv discard the lockfile and re-resolve *without* the cool-off.
- Adding a per-package cool-off exception without recording it in the marker doc.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent
_PYPROJECT = _REPO_ROOT / "pyproject.toml"
_LOCK = _REPO_ROOT / "uv.lock"
_MARKER = _REPO_ROOT / "SUPPLY-CHAIN-SECURITY.md"


def _uv_config() -> dict[str, object]:
    return tomllib.loads(_PYPROJECT.read_text())["tool"]["uv"]


def test_cool_off_cutoff_matches_lockfile() -> None:
    config_cutoff = _uv_config()["exclude-newer"]
    lock_cutoff = tomllib.loads(_LOCK.read_text())["options"]["exclude-newer"]
    assert config_cutoff == lock_cutoff


def test_cool_off_exceptions_are_documented() -> None:
    exceptions = _uv_config().get("exclude-newer-package", {})
    assert isinstance(exceptions, dict)
    marker = _MARKER.read_text()
    undocumented = [pkg for pkg in exceptions if pkg not in marker]
    assert not undocumented
