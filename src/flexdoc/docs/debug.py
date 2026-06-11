"""
Reusable developer tool for dumping a document's model views in clean, standard
formats. Works on any `TextDoc`: use it from a REPL, a script, or the golden-test
harness to see every projection the model derives from one source.

Three views, all deterministic (the model is hermetic — node ids are a stable preorder
counter, sha256 and token estimates are deterministic), so output is byte-stable and
diff-friendly:

- `doc_report(doc)` — a multi-view YAML report: source stats, the base-block partition
  with a live cover check, sections/TOC, the full node table (all layers), links by
  section, and SpanRef round-trips.
- `doc_graph_yaml(doc)` — the `DocGraph` projection as clean YAML.
- `dump_views(doc, dest)` — write the standard artifact set (`report.yaml`,
  `docgraph.yaml`, `reassembled.md`) into a directory.

Spans are rendered as compact `"start:end"` strings (Unicode code points), matching the
`data-source-span` convention in `flexdoc.docs.render`.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from strif import atomic_output_file

from flexdoc.docs.base_blocks import base_blocks
from flexdoc.docs.doc_graph import clean_yaml
from flexdoc.docs.node import NodeKind
from flexdoc.docs.sizes import TextUnit
from flexdoc.docs.span_ref import SpanRef, resolve
from flexdoc.docs.text_doc import TextDoc

# Inline kinds that carry a locatable span worth round-tripping through SpanRef.
_LOCATABLE_INLINE = frozenset({NodeKind.link, NodeKind.image, NodeKind.code_span})


def _span_str(span: tuple[int, int] | None) -> str | None:
    return f"{span[0]}:{span[1]}" if span is not None else None


def doc_report_data(doc: TextDoc, *, item_partition_depth: int = 6) -> dict[str, Any]:
    """
    The multi-view report as a plain (ordered) dict, ready to serialize. Captures broad
    state rather than narrow slices, so any change to any view shows up in a diff.
    """
    source_text = doc.source_text or doc.reassemble()

    # Base-block partition with a live complete-cover check.
    bbs = base_blocks(source_text, item_partition_depth=item_partition_depth)
    covered: set[int] = set()
    for bb in bbs:
        covered.update(range(bb.block.span[0], bb.block.span[1]))
    uncovered = {i for i in range(len(source_text)) if not source_text[i].isspace()} - covered
    base_block_rows = [
        {
            "depth": bb.depth,
            "type": bb.block.type.value,
            "span": _span_str(bb.block.span),
            "text": source_text[bb.block.span[0] : bb.block.span[1]],
        }
        for bb in bbs
    ]

    # Sections / TOC, flattened in document order with rolled-up sizes.
    section_rows: list[dict[str, Any]] = []

    def _walk(sections: list[Any]) -> None:
        for sec in sections:
            section_rows.append(
                {
                    "level": sec.level,
                    "title": sec.title,
                    "span": _span_str(sec.span),
                    "words": sec.size(TextUnit.words),
                }
            )
            _walk(sec.children)

    _walk(doc.sections())

    # Full node table, every layer, in id order.
    table = doc.node_table()
    node_rows = [
        {
            "id": nid,
            "layer": n.layer.value,
            "kind": n.kind.value,
            "span": _span_str(n.source_span),
            "parent": n.parent,
            "attrs": dict(n.attrs) if n.attrs else None,
        }
        for nid, n in table.nodes.items()
    ]

    # Links (and images) with the model's own section attribution.
    link_rows: list[dict[str, Any]] = []
    for n in table.nodes.values():
        if n.kind not in (NodeKind.link, NodeKind.image):
            continue
        section_id = n.attrs.get("section")
        section_title = None
        if isinstance(section_id, str) and section_id in table.nodes:
            section_title = table.nodes[section_id].attrs.get("title")
        link_rows.append(
            {
                "kind": n.kind.value,
                "text": n.attrs.get("text"),
                "url": n.attrs.get("url"),
                "span": _span_str(n.source_span),
                "section": section_title,
            }
        )

    # SpanRef round-trips: persist quote-canonical, then re-resolve against the source.
    spanref_rows: list[dict[str, Any]] = []
    for n in table.nodes.values():
        if n.kind not in _LOCATABLE_INLINE or n.source_span is None:
            continue
        ref = SpanRef.from_node(n, source_text)
        resolved = resolve(ref.to_persisted(), source_text)
        spanref_rows.append(
            {
                "id": n.id,
                "exact": ref.exact,
                "resolved": _span_str(resolved),
                "ok": resolved == n.source_span,
            }
        )

    return {
        "source": {
            "sha256": hashlib.sha256(source_text.encode("utf-8")).hexdigest(),
            "length": len(source_text),
            "size_summary": doc.size_summary(),
        },
        "base_blocks": {
            "cover_ok": not uncovered,
            "uncovered_nonspace": len(uncovered),
            "blocks": base_block_rows,
        },
        "sections": section_rows,
        "node_table": node_rows,
        "links": link_rows,
        "spanrefs": spanref_rows,
    }


def doc_report(doc: TextDoc, *, item_partition_depth: int = 6) -> str:
    """The multi-view report as clean, deterministic YAML."""
    return clean_yaml(doc_report_data(doc, item_partition_depth=item_partition_depth))


def doc_graph_yaml(doc: TextDoc) -> str:
    """The default `DocGraph` projection (markdown + document layers) as clean YAML."""
    return doc.graph().to_yaml()


def dump_views(doc: TextDoc, dest: Path | str, *, item_partition_depth: int = 6) -> None:
    """
    Write the standard artifact set for `doc` into directory `dest`: `report.yaml`,
    `docgraph.yaml`, and `reassembled.md`. Files are written atomically.
    """
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    artifacts = {
        "report.yaml": doc_report(doc, item_partition_depth=item_partition_depth),
        "docgraph.yaml": doc_graph_yaml(doc),
        "reassembled.md": doc.reassemble(),
    }
    for name, content in artifacts.items():
        with atomic_output_file(dest / name) as tmp:
            tmp.write_text(content, encoding="utf-8")
