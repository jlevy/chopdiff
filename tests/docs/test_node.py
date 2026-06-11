"""
Tests for the pure node-model types: `NodeKind`/`BlockType` parity, inline-kind
membership, and the `LAYER_NESTING` invariant.
"""

from __future__ import annotations

from flexdoc.docs.block_types import BlockType
from flexdoc.docs.node import LAYER_NESTING, Layer, NestingGuarantee, Node, NodeKind


def test_block_kinds_match_block_type_values():
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
            NodeKind.footnote_ref,
            NodeKind.section,
            NodeKind.sentence,
        )
    }
    assert block_node_kinds == block_type_values


def test_inline_kinds_exist():
    inline_kinds = {
        NodeKind.link,
        NodeKind.code_span,
        NodeKind.image,
        NodeKind.inline_html,
        NodeKind.footnote_ref,
    }
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
