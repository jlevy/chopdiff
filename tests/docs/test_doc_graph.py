"""
Tests for the DocGraph Pydantic schema, builder, and JSON Schema export.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from textwrap import dedent

from flexdoc.docs.doc_graph import (
    Detail,
    DocGraph,
    NodeModel,
    SourceInfo,
    Views,
)
from flexdoc.docs.node import Layer
from flexdoc.docs.text_doc import TextDoc

SCHEMA_PATH = (
    Path(__file__).resolve().parent.parent.parent / "src/flexdoc/docs/doc_graph_schema.json"
)

# A representative multi-section document with nested blocks and links.
SAMPLE_DOC = dedent("""
    # Introduction

    This is an intro paragraph with a [link](https://example.com).

    ## Details

    Here are some details:

    - Item one
    - Item two with `code`
    - Item three

    > A blockquote with a [ref](https://ref.example.com "Reference").

    ## Code Section

    ```python
    def hello():
        print("world")
    ```

    Final paragraph.
""").strip()


def _make_doc() -> TextDoc:
    return TextDoc.from_text(SAMPLE_DOC)


def test_doc_graph_model_validates():
    """The DocGraph Pydantic model validates with required fields."""
    source = SourceInfo(
        format="markdown",
        sha256="abc123",
    )
    node = NodeModel(
        id="n0001",
        kind="paragraph",
        layer="markdown",
    )
    views = Views()
    graph = DocGraph(source=source, nodes=[node], views=views)
    assert graph.schema_ == "DocGraph/v0.1"
    assert graph.source.offset_unit == "unicode_code_points"
    assert len(graph.annotations) == 0
    assert len(graph.layout) == 0
    assert len(graph.provenance) == 0


def test_schema_key_is_schema_not_schema_():
    """The JSON key must be `schema`, not `schema_`."""
    doc = _make_doc()
    graph = doc.graph()
    data = json.loads(graph.model_dump_json(by_alias=True))
    assert "schema" in data
    assert "schema_" not in data
    assert data["schema"] == "DocGraph/v0.1"


def test_source_sha256_matches():
    doc = _make_doc()
    graph = doc.graph()
    expected_sha = hashlib.sha256(SAMPLE_DOC.encode("utf-8")).hexdigest()
    assert graph.source.sha256 == expected_sha


def test_source_text_absent_by_default():
    doc = _make_doc()
    graph = doc.graph()
    assert graph.source.text is None


def test_source_text_present_with_detail_text():
    doc = _make_doc()
    graph = doc.graph(detail=frozenset({Detail.text}))
    assert graph.source.text == SAMPLE_DOC


def test_node_text_present_with_detail_text():
    doc = _make_doc()
    graph = doc.graph(detail=frozenset({Detail.text}))
    nodes_with_text = [n for n in graph.nodes if n.text is not None]
    assert len(nodes_with_text) > 0
    # Every node with a source_span and text should have text matching the source.
    for nm in nodes_with_text:
        assert nm.source_span is not None
        expected = SAMPLE_DOC[nm.source_span.start : nm.source_span.end]
        assert nm.text == expected


def test_default_include_is_markdown_and_document():
    doc = _make_doc()
    graph = doc.graph()
    layers_present = {n.layer for n in graph.nodes}
    assert "markdown" in layers_present
    assert "document" in layers_present
    assert "textual" not in layers_present


def test_include_textual_adds_sentences():
    doc = _make_doc()
    graph = doc.graph(include=frozenset({Layer.markdown, Layer.document, Layer.textual}))
    layers_present = {n.layer for n in graph.nodes}
    assert "textual" in layers_present
    sentence_nodes = [n for n in graph.nodes if n.kind == "sentence"]
    assert len(sentence_nodes) > 0
    assert len(graph.views.sentences) > 0


def test_include_document_auto_enables_markdown():
    """Enabling document alone must auto-enable markdown."""
    doc = _make_doc()
    graph = doc.graph(include=frozenset({Layer.document}))
    layers_present = {n.layer for n in graph.nodes}
    assert "markdown" in layers_present
    assert "document" in layers_present


def test_inline_nodes_excluded_by_default():
    doc = _make_doc()
    graph = doc.graph()
    inline_kinds = {"link", "code_span", "image", "inline_html"}
    inline_nodes = [n for n in graph.nodes if n.kind in inline_kinds]
    assert len(inline_nodes) == 0


def test_detail_inline_includes_inline_nodes():
    doc = _make_doc()
    graph = doc.graph(detail=frozenset({Detail.inline}))
    link_nodes = [n for n in graph.nodes if n.kind == "link"]
    assert len(link_nodes) > 0
    assert len(graph.views.links) > 0


def test_views_toc_populated():
    doc = _make_doc()
    graph = doc.graph()
    assert len(graph.views.toc) > 0
    # TOC entries should reference section nodes in the document layer.
    node_ids = {n.id for n in graph.nodes}
    for toc_id in graph.views.toc:
        assert toc_id in node_ids


def test_views_blocks_populated():
    doc = _make_doc()
    graph = doc.graph()
    assert len(graph.views.blocks) > 0
    node_ids = {n.id for n in graph.nodes}
    for block_id in graph.views.blocks:
        assert block_id in node_ids


def test_view_node_ids_resolve_to_nodes():
    """All node ids in every view resolve to actual nodes in the graph."""
    doc = _make_doc()
    graph = doc.graph(
        include=frozenset({Layer.markdown, Layer.document, Layer.textual}),
        detail=frozenset({Detail.inline}),
    )
    node_ids = {n.id for n in graph.nodes}
    for view_name in ("toc", "blocks", "links", "sentences"):
        view_ids = getattr(graph.views, view_name)
        for vid in view_ids:
            assert vid in node_ids, f"View '{view_name}' references node '{vid}' not in nodes"


def test_nodes_parent_children_consistency():
    """Every child id should exist, and parent references should be consistent."""
    doc = _make_doc()
    graph = doc.graph(
        include=frozenset({Layer.markdown, Layer.document, Layer.textual}),
        detail=frozenset({Detail.inline}),
    )
    node_map = {n.id: n for n in graph.nodes}
    for nm in graph.nodes:
        for cid in nm.children:
            assert cid in node_map, f"Node {nm.id} has child {cid} not in nodes"
        if nm.parent is not None:
            assert nm.parent in node_map, f"Node {nm.id} has parent {nm.parent} not in nodes"


def test_source_span_offsets_valid():
    """Every node's source_span offsets should be within the source text range."""
    doc = _make_doc()
    graph = doc.graph(detail=frozenset({Detail.text}))
    text_len = len(SAMPLE_DOC)
    for nm in graph.nodes:
        if nm.source_span is not None:
            assert 0 <= nm.source_span.start <= nm.source_span.end <= text_len, (
                f"Node {nm.id} span ({nm.source_span.start}, {nm.source_span.end}) "
                f"out of range [0, {text_len}]"
            )


def test_round_trip_json_serialization():
    """DocGraph round-trips through JSON."""
    doc = _make_doc()
    graph = doc.graph(detail=frozenset({Detail.text, Detail.inline}))
    json_str = graph.model_dump_json(by_alias=True)
    restored = DocGraph.model_validate_json(json_str)
    assert restored.schema_ == graph.schema_
    assert restored.source.sha256 == graph.source.sha256
    assert len(restored.nodes) == len(graph.nodes)
    assert restored.views.toc == graph.views.toc
    assert restored.views.blocks == graph.views.blocks
    assert restored.views.links == graph.views.links


def test_golden_snapshot():
    """
    Golden-test the serialized DocGraph for the sample document. Validates
    structure stability: schema version, node count ranges, key views, and
    that the JSON is well-formed with the expected top-level keys.
    """
    doc = _make_doc()
    graph = doc.graph(
        include=frozenset({Layer.markdown, Layer.document, Layer.textual}),
        detail=frozenset({Detail.text, Detail.inline}),
    )
    data = json.loads(graph.model_dump_json(by_alias=True))

    # Top-level keys.
    assert set(data.keys()) == {
        "schema",
        "source",
        "nodes",
        "views",
        "annotations",
        "layout",
        "provenance",
    }
    assert data["schema"] == "DocGraph/v0.1"
    assert data["source"]["offset_unit"] == "unicode_code_points"
    assert data["source"]["format"] == "markdown"
    assert data["source"]["text"] is not None

    # Nodes: the sample has multiple blocks, sections, sentences, and inline elements.
    assert len(data["nodes"]) > 10

    # Views: non-empty where expected.
    assert len(data["views"]["toc"]) >= 3
    assert len(data["views"]["blocks"]) >= 5
    assert len(data["views"]["links"]) >= 1
    assert len(data["views"]["sentences"]) >= 3

    # Reserved layers are empty lists.
    assert data["annotations"] == []
    assert data["layout"] == []
    assert data["provenance"] == []


def test_json_schema_export_matches_committed_file():
    """
    The committed JSON Schema file must match what DocGraph.model_json_schema()
    produces. If this test fails, regenerate with:
        python -c "from flexdoc.docs.doc_graph import DocGraph; ..."
    """
    current_schema = DocGraph.model_json_schema(by_alias=True)
    current_json = json.dumps(current_schema, indent=2, sort_keys=True) + "\n"

    if not SCHEMA_PATH.exists():
        SCHEMA_PATH.write_text(current_json)

    committed = SCHEMA_PATH.read_text()
    assert committed == current_json, (
        f"Committed JSON Schema at {SCHEMA_PATH} is out of date. "
        "Regenerate it by running the test suite (it auto-writes on first run) "
        "or manually."
    )


def test_include_markdown_only():
    """With only markdown, no document-layer nodes appear."""
    doc = _make_doc()
    graph = doc.graph(include=frozenset({Layer.markdown}))
    layers_present = {n.layer for n in graph.nodes}
    assert "markdown" in layers_present
    assert "document" not in layers_present
    assert len(graph.views.toc) == 0


def test_empty_document():
    """An empty document produces a valid DocGraph with no nodes."""
    doc = TextDoc.from_text("")
    graph = doc.graph()
    assert graph.schema_ == "DocGraph/v0.1"
    assert len(graph.nodes) == 0
    assert len(graph.views.blocks) == 0


def test_detail_enum_values():
    assert Detail.text == "text"
    assert Detail.inline == "inline"
    assert Detail.tokens == "tokens"
    assert Detail.coords == "coords"
