# pyright: reportImportCycles=false
"""
Pydantic v2 schema for the DocGraph serialized projection and the builder
that derives it from a `TextDoc`.

`DocGraph` is the language-neutral JSON contract described in textdoc-spec section 10.
It is a derived, read-only snapshot: the Python core is `TextDoc`; edits go through
`TextDoc`/source and re-derive. Authored as Pydantic models (DR-3) that emit a
JSON Schema.
"""

from __future__ import annotations

import hashlib
from enum import StrEnum
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field

from chopdiff.docs.collect import INLINE_KINDS
from chopdiff.docs.node import Layer, Node, NodeKind

if TYPE_CHECKING:
    from chopdiff.docs.text_doc import TextDoc


class Detail(StrEnum):
    """
    Payload sub-options controlling richness within enabled layers (DR-5, E9).
    These are not top-level layers but detail flags: `text` adds per-node source
    text, `inline` includes inline nodes, `tokens` and `coords` add those payloads.
    """

    text = "text"
    inline = "inline"
    tokens = "tokens"
    coords = "coords"


class SourceInfo(BaseModel):
    """Source metadata for the document backing a `DocGraph`."""

    model_config = ConfigDict(populate_by_name=True)

    format: str
    offset_unit: Literal["unicode_code_points"] = "unicode_code_points"
    sha256: str
    text: str | None = None


class SourceSpan(BaseModel):
    """A `[start, end)` span in Unicode code points."""

    model_config = ConfigDict(populate_by_name=True)

    start: int
    end: int


class NodeModel(BaseModel):
    """
    Serialization model for a single node. Mirrors the runtime `Node` dataclass
    with JSON-friendly field types. `source_span` is a `{start, end}` object
    (or null for unlocatable nodes like reference links).
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str
    kind: str
    layer: str
    parent: str | None = None
    children: list[str] = Field(default_factory=list)
    source_span: SourceSpan | None = None
    attrs: dict[str, object] = Field(default_factory=dict)
    text: str | None = None


class Views(BaseModel):
    """Derived view indexes: arrays of node ids for common projections."""

    model_config = ConfigDict(populate_by_name=True)

    toc: list[str] = Field(default_factory=list)
    blocks: list[str] = Field(default_factory=list)
    links: list[str] = Field(default_factory=list)
    sentences: list[str] = Field(default_factory=list)


class DocGraph(BaseModel):
    """
    The DocGraph serialized projection (textdoc-spec section 10). A single,
    source-anchored JSON object from which any view (block tree, section tree,
    inline index) and any rollup is derivable.

    The `schema` JSON key carries the version string; in Python it is accessed
    as `schema_` (with `Field(alias="schema")`).
    """

    model_config = ConfigDict(populate_by_name=True)

    schema_: str = Field(default="DocGraph/v0.1", alias="schema")
    source: SourceInfo
    nodes: list[NodeModel]
    views: Views

    # Reserved layers for later phases.
    annotations: list[object] = Field(default_factory=list)
    layout: list[object] = Field(default_factory=list)
    provenance: list[object] = Field(default_factory=list)


# Default layers included when none are specified.
_DEFAULT_INCLUDE: frozenset[Layer] = frozenset({Layer.markdown, Layer.document})


def build_doc_graph(
    doc: TextDoc,
    *,
    include: frozenset[Layer] = _DEFAULT_INCLUDE,
    detail: frozenset[Detail] = frozenset(),  # pyright: ignore[reportCallInDefaultInitializer]
) -> DocGraph:
    """
    Build a `DocGraph` from a `TextDoc`.

    `include` selects which layers' nodes and views are serialized. Enabling
    `Layer.document` auto-enables `Layer.markdown` (its dependency). The
    structural core (ids, kinds, layer, parent/children, source_span) is
    always present for included layers.

    `detail` controls payload richness: `Detail.text` adds per-node source
    text (and includes `source.text`); `Detail.inline` includes inline nodes;
    `Detail.tokens` and `Detail.coords` are reserved for future payloads.
    """
    # Auto-enable markdown when document is included.
    layers = set(include)
    if Layer.document in layers:
        layers.add(Layer.markdown)
    enabled_layers = frozenset(layers)

    table = doc.node_table()
    source_text = table.source_text

    include_inline = Detail.inline in detail
    include_text = Detail.text in detail

    # Build the node list, filtering by enabled layers (and inline detail).
    node_models: list[NodeModel] = []
    included_ids: set[str] = set()

    for nid, node in table.nodes.items():
        if node.layer not in enabled_layers:
            continue
        if node.kind in INLINE_KINDS and not include_inline:
            continue

        span_model: SourceSpan | None = None
        if node.source_span is not None:
            span_model = SourceSpan(start=node.source_span[0], end=node.source_span[1])

        node_text: str | None = None
        if include_text and node.source_span is not None:
            node_text = source_text[node.source_span[0] : node.source_span[1]]

        # Filter children to only those that are included.
        filtered_children = [
            cid
            for cid in node.children
            if _node_included(table.nodes[cid], enabled_layers, include_inline)
        ]

        node_models.append(
            NodeModel(
                id=nid,
                kind=node.kind.value,
                layer=node.layer.value,
                parent=node.parent
                if node.parent and _is_parent_included(node.parent, table.nodes, enabled_layers)
                else None,
                children=filtered_children,
                source_span=span_model,
                attrs=node.attrs,
                text=node_text,
            )
        )
        included_ids.add(nid)

    # Build views from included nodes.
    toc_ids: list[str] = []
    block_ids: list[str] = []
    link_ids: list[str] = []
    sentence_ids: list[str] = []

    for nm in node_models:
        kind = nm.kind
        layer = nm.layer
        if kind == NodeKind.section.value and layer == Layer.document.value:
            toc_ids.append(nm.id)
        if layer == Layer.markdown.value and kind not in {k.value for k in INLINE_KINDS}:
            block_ids.append(nm.id)
        if kind == NodeKind.link.value:
            link_ids.append(nm.id)
        if kind == NodeKind.sentence.value and layer == Layer.textual.value:
            sentence_ids.append(nm.id)

    sha = hashlib.sha256(source_text.encode("utf-8")).hexdigest()

    source_info = SourceInfo(
        format="markdown",
        sha256=sha,
        text=source_text if include_text else None,
    )

    views = Views(
        toc=toc_ids,
        blocks=block_ids,
        links=link_ids,
        sentences=sentence_ids,
    )

    return DocGraph(
        source=source_info,
        nodes=node_models,
        views=views,
    )


def _node_included(
    node: Node,
    enabled_layers: frozenset[Layer],
    include_inline: bool,
) -> bool:
    """Check whether a node would be included given the current layer/detail settings."""
    if node.layer not in enabled_layers:
        return False
    if node.kind in INLINE_KINDS and not include_inline:
        return False
    return True


def _is_parent_included(
    parent_id: str,
    nodes: dict[str, Node],
    enabled_layers: frozenset[Layer],
) -> bool:
    """Check whether a parent node's layer is enabled."""
    parent = nodes.get(parent_id)
    if parent is None:
        return False
    return parent.layer in enabled_layers
