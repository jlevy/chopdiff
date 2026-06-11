"""
Enforces the FlexDoc package boundary: `flexdoc` must not import `chopdiff`.

This is the one-way dependency cut the package split exists to guarantee (see
`docs/project/specs/active/plan-2026-06-11-flexdoc-extraction.md`, Stage 1). It is
deliberately dependency-free (stdlib `ast` only) so the seam cannot rot and the check runs
anywhere without extra tooling.
"""

from __future__ import annotations

import ast
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_FLEXDOC_SRC = _REPO_ROOT / "src" / "flexdoc"


def _imported_top_modules(tree: ast.Module) -> set[str]:
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            # node.level > 0 is a relative import (never crosses the package root);
            # node.module is the absolute portion for `from x import y`.
            if node.level == 0 and node.module:
                modules.add(node.module)
    return modules


def test_flexdoc_does_not_import_chopdiff():
    offenders: list[str] = []
    for path in sorted(_FLEXDOC_SRC.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for module in _imported_top_modules(tree):
            if module == "chopdiff" or module.startswith("chopdiff."):
                offenders.append(f"{path.relative_to(_REPO_ROOT)}: imports {module}")
    if offenders:
        raise AssertionError(
            "flexdoc must not import chopdiff (one-way boundary):\n  " + "\n  ".join(offenders)
        )
