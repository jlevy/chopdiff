"""
Node model for the DocGraph document model.

Pure data definitions: `Node`, `NodeKind`, `Layer`, and `NestingGuarantee`. No parsing
logic lives here; these are the types the block tree, base-block partition, and (later)
the full DocGraph projection are built from.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class NodeKind(StrEnum):
    """
    All block and inline element kinds recognized by the document model.

    Block kinds mirror `BlockType` one-to-one. Inline kinds cover elements that live
    inside a block (links, code spans, images, inline HTML). The `section` kind
    represents heading-hierarchy nodes in the document layer.
    """

    # Block kinds (same values as BlockType).
    paragraph = "paragraph"
    heading = "heading"
    list = "list"
    ordered_list = "ordered_list"
    list_item = "list_item"
    table = "table"
    code = "code"
    blockquote = "blockquote"
    html = "html"
    footnote = "footnote"
    thematic_break = "thematic_break"

    # Inline kinds.
    link = "link"
    code_span = "code_span"
    image = "image"
    inline_html = "inline_html"

    # Document-layer kind.
    section = "section"

    # Textual-layer kind (sentences within the editing view).
    sentence = "sentence"


class Layer(StrEnum):
    """
    Parse dimensions over the shared offset space. Each layer produces a set of nodes
    tagged with its name; cross-layer relationships are offset-containment queries,
    not stored edges.
    """

    textual = "textual"
    markdown = "markdown"
    document = "document"
    synthetic = "synthetic"


class NestingGuarantee(StrEnum):
    """
    Declares how a layer's nodes relate structurally. A `tree` layer projects to a
    well-nested tree view; an `ordered_list` layer projects to a sequential list view.
    """

    tree = "tree"
    ordered_list = "ordered_list"


LAYER_NESTING: dict[Layer, NestingGuarantee] = {
    Layer.textual: NestingGuarantee.ordered_list,
    Layer.markdown: NestingGuarantee.tree,
    Layer.document: NestingGuarantee.tree,
    Layer.synthetic: NestingGuarantee.tree,
}


@dataclass
class Node:
    """
    A single element in the document's node table. Nodes are addressable by `id` and
    `source_span`, and grouped by `layer`. Within a layer, `parent`/`children` form
    the containment structure; cross-layer relationships use offset containment.
    """

    id: str
    kind: NodeKind
    layer: Layer
    parent: str | None
    children: list[str] = field(default_factory=list)
    source_span: tuple[int, int] | None = None
    attrs: dict[str, object] = field(default_factory=dict)


@dataclass
class NodeTable:
    """
    A flat, id-addressed table of all parsed elements in a document, covering
    markdown, document, and textual layers over the same source text.

    The source string and its Unicode code-point offset space are canonical; this
    table is the id-addressed query/serialization projection over that substrate
    (as are the block tree, section tree, etc. — sibling projections, not derived
    from the table). Within a layer, `parent`/`children` form the containment
    structure; cross-layer relationships use interval containment via
    `containing()` and `contained_by()`.
    """

    nodes: dict[str, Node] = field(default_factory=dict)
    roots: list[str] = field(default_factory=list)
    source_text: str = ""

    def node(self, nid: str) -> Node:
        """Look up a node by id; raises `KeyError` if not found."""
        return self.nodes[nid]

    def by_kind(self, kind: NodeKind) -> list[Node]:
        """All nodes of a given kind, in insertion order."""
        return [n for n in self.nodes.values() if n.kind == kind]

    def by_layer(self, layer: Layer) -> list[Node]:
        """All nodes in a given layer, in insertion order."""
        return [n for n in self.nodes.values() if n.layer == layer]

    def children_of(self, nid: str) -> list[Node]:
        """The child nodes of the node with `nid`."""
        parent = self.nodes[nid]
        return [self.nodes[cid] for cid in parent.children]

    def containing(self, span: tuple[int, int]) -> list[Node]:
        """
        All nodes whose `source_span` fully contains `span` (i.e. the node's span
        encloses the query span). Useful for cross-layer containment queries like
        "which section contains this link."
        """
        start, end = span
        return [
            n
            for n in self.nodes.values()
            if n.source_span is not None and n.source_span[0] <= start and end <= n.source_span[1]
        ]

    def contained_by(self, span: tuple[int, int]) -> list[Node]:
        """
        All nodes whose `source_span` is fully contained within `span`. Useful for
        queries like "which blocks are inside this region."
        """
        start, end = span
        return [
            n
            for n in self.nodes.values()
            if n.source_span is not None and start <= n.source_span[0] and n.source_span[1] <= end
        ]
