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


## Tests


def test_block_kinds_match_block_type_values():
    from chopdiff.docs.block_types import BlockType

    block_type_values = {bt.value for bt in BlockType}
    block_node_kinds = {
        nk.value
        for nk in NodeKind
        if nk
        not in (
            NodeKind.link,
            NodeKind.code_span,
            NodeKind.image,
            NodeKind.inline_html,
            NodeKind.section,
            NodeKind.sentence,
        )
    }
    assert block_node_kinds == block_type_values


def test_inline_kinds_exist():
    inline_kinds = {NodeKind.link, NodeKind.code_span, NodeKind.image, NodeKind.inline_html}
    assert all(k in NodeKind for k in inline_kinds)
    assert NodeKind.section not in inline_kinds
    assert NodeKind.sentence not in inline_kinds


def test_layer_nesting_covers_every_layer():
    for layer in Layer:
        assert layer in LAYER_NESTING, f"LAYER_NESTING missing {layer}"


def test_nesting_guarantee_values():
    assert LAYER_NESTING[Layer.textual] == NestingGuarantee.ordered_list
    assert LAYER_NESTING[Layer.markdown] == NestingGuarantee.tree
    assert LAYER_NESTING[Layer.document] == NestingGuarantee.tree
    assert LAYER_NESTING[Layer.synthetic] == NestingGuarantee.tree


def test_node_defaults():
    n = Node(id="n_0001", kind=NodeKind.paragraph, layer=Layer.markdown, parent=None)
    assert n.children == []
    assert n.source_span is None
    assert n.attrs == {}
