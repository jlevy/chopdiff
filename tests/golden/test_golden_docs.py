"""
Golden-document tests: each source document under `documents/` is converted by the model
and serialized three ways (`report.yaml`, `docgraph.yaml`, `reassembled.md`); the
serializations are committed under `expected/<doc>/` and compared on every run.

This is transparent-box testing — one readable artifact per document shows every
projection at once, so any change to any view appears in a diff. Alongside the raw diff,
`test_model_invariants` enforces the model's hard guarantees programmatically, so a
semantic violation fails even if the goldens are regenerated without review.

Source documents are Markdown with YAML frontmatter (`name`, `description`, optional
`item_partition_depth`). Regenerate goldens after an intentional change with:

    UPDATE_GOLDEN=1 uv run pytest tests/golden/test_golden_docs.py

then review `git diff tests/golden/expected/`.
"""

from __future__ import annotations

import difflib
import os
from pathlib import Path

from frontmatter_format import fmf_read

from chopdiff.docs.debug import doc_graph_yaml, doc_report, doc_report_data
from chopdiff.docs.text_doc import TextDoc

_HERE = Path(__file__).parent
_DOCS_DIR = _HERE / "documents"
_EXPECTED_DIR = _HERE / "expected"
_UPDATE = bool(os.environ.get("UPDATE_GOLDEN"))


def _docs() -> list[Path]:
    return sorted(_DOCS_DIR.glob("*.md"))


def _load(path: Path) -> tuple[str, int]:
    """Return the document body and its `item_partition_depth` option (default 6)."""
    content, meta = fmf_read(path)
    depth = 6
    if meta and "item_partition_depth" in meta:
        depth = int(meta["item_partition_depth"])  # pyright: ignore[reportArgumentType]
    return content, depth


def _artifacts(content: str, depth: int) -> dict[str, str]:
    td = TextDoc.from_text(content)
    return {
        "report.yaml": doc_report(td, item_partition_depth=depth),
        "docgraph.yaml": doc_graph_yaml(td),
        "reassembled.md": td.reassemble(),
    }


def test_golden_artifacts():
    docs = _docs()
    assert docs, f"no corpus documents found in {_DOCS_DIR}"

    failures: list[str] = []
    for path in docs:
        content, depth = _load(path)
        artifacts = _artifacts(content, depth)
        dest = _EXPECTED_DIR / path.stem

        if _UPDATE:
            dest.mkdir(parents=True, exist_ok=True)
            for name, text in artifacts.items():
                (dest / name).write_text(text, encoding="utf-8")
            continue

        for name, actual in artifacts.items():
            golden_path = dest / name
            if not golden_path.exists():
                failures.append(f"{path.stem}/{name}: missing golden (run UPDATE_GOLDEN=1)")
                continue
            expected = golden_path.read_text(encoding="utf-8")
            if actual != expected:
                diff = "".join(
                    difflib.unified_diff(
                        expected.splitlines(keepends=True),
                        actual.splitlines(keepends=True),
                        fromfile=f"golden/{name}",
                        tofile=f"actual/{name}",
                    )
                )
                failures.append(f"{path.stem}/{name} differs:\n{diff}")

    if _UPDATE:
        return
    if failures:
        raise AssertionError("\n\n".join(failures))


def test_model_invariants():
    """The model's hard guarantees, checked independently of the golden diff."""
    docs = _docs()
    assert docs, f"no corpus documents found in {_DOCS_DIR}"

    for path in docs:
        content, depth = _load(path)
        td = TextDoc.from_text(content)
        source = td.source_text or td.reassemble()
        data = doc_report_data(td, item_partition_depth=depth)
        where = path.stem

        # Base-block partition is a complete cover of all non-whitespace source (P13).
        assert data["base_blocks"]["cover_ok"], (
            f"{where}: base_blocks left {data['base_blocks']['uncovered_nonspace']} "
            "non-whitespace chars uncovered"
        )

        # Every located inline node round-trips through SpanRef (P6/SpanRef).
        for row in data["spanrefs"]:
            assert row["ok"], f"{where}: SpanRef did not round-trip for {row['id']}"

        table = td.node_table()
        # Node ids unique and every parent/child reference resolves.
        assert len(table.nodes) == len({n.id for n in table.nodes.values()})
        for nid, n in table.nodes.items():
            if n.parent is not None:
                assert n.parent in table.nodes, f"{where}: dangling parent {n.parent} on {nid}"
            for cid in n.children:
                assert cid in table.nodes, f"{where}: dangling child {cid} on {nid}"
            # Source-backed block/section nodes are span-exact and whitespace-trimmed (P6).
            if n.source_span is not None:
                s, e = n.source_span
                assert 0 <= s <= e <= len(source)

        # DocGraph child references are all valid within the projection.
        ids = {nm.id for nm in td.graph().nodes}
        for nm in td.graph().nodes:
            for cid in nm.children:
                assert cid in ids, f"{where}: docgraph child {cid} missing for {nm.id}"

        # Normalized-form idempotence (P11): `reassemble()` produces the editing view's
        # normalized text (which may differ from the source for constructs the editing
        # view normalizes, e.g. multi-line reference definitions). Re-parsing and
        # re-reassembling that normalized text must be a fixed point.
        normalized = td.reassemble()
        renormalized = TextDoc.from_text(normalized).reassemble()
        assert normalized == renormalized, f"{where}: reassemble() is not idempotent"
