"""
Render helpers that emit `data-node-id` and `data-source-span` attributes on
HTML elements so a rendered selection resolves back to a node and thence to
source text (textdoc-spec section 12, E8/D5).
"""

from __future__ import annotations

from flexdoc.docs.node import Node


def render_node_attrs(node: Node) -> str:
    """
    Return an HTML attribute string (`data-node-id="..." data-source-span="..."`)
    for embedding in a rendered element. The span is formatted as `start:end`
    in Unicode code-point offsets, matching `DocGraph`'s `offset_unit`.
    """
    parts = [f'data-node-id="{node.id}"']
    if node.source_span is not None:
        parts.append(f'data-source-span="{node.source_span[0]}:{node.source_span[1]}"')
    return " ".join(parts)


def wrap_with_node_attrs(node: Node, tag: str, inner_html: str) -> str:
    """
    Wrap `inner_html` in an HTML `tag` element carrying the node's data
    attributes. For example, `wrap_with_node_attrs(node, "span", "hello")`
    produces `<span data-node-id="n0001" data-source-span="0:5">hello</span>`.
    """
    attrs = render_node_attrs(node)
    return f"<{tag} {attrs}>{inner_html}</{tag}>"


def parse_source_span_attr(attr_value: str) -> tuple[int, int] | None:
    """
    Parse a `data-source-span` attribute value (`"start:end"`) back to an
    offset tuple, returning None if the format is invalid.
    """
    parts = attr_value.split(":")
    if len(parts) != 2:
        return None
    try:
        return (int(parts[0]), int(parts[1]))
    except ValueError:
        return None


## Tests


def test_render_node_attrs_with_span():
    from flexdoc.docs.node import Layer, NodeKind

    node = Node(
        id="n0001", kind=NodeKind.paragraph, layer=Layer.markdown, parent=None, source_span=(10, 25)
    )
    result = render_node_attrs(node)
    assert result == 'data-node-id="n0001" data-source-span="10:25"'


def test_render_node_attrs_no_span():
    from flexdoc.docs.node import Layer, NodeKind

    node = Node(id="n0002", kind=NodeKind.link, layer=Layer.markdown, parent=None, source_span=None)
    result = render_node_attrs(node)
    assert result == 'data-node-id="n0002"'


def test_wrap_with_node_attrs():
    from flexdoc.docs.node import Layer, NodeKind

    node = Node(
        id="n0003", kind=NodeKind.heading, layer=Layer.markdown, parent=None, source_span=(0, 8)
    )
    result = wrap_with_node_attrs(node, "h1", "Title")
    assert result == '<h1 data-node-id="n0003" data-source-span="0:8">Title</h1>'


def test_parse_source_span_attr():
    assert parse_source_span_attr("10:25") == (10, 25)
    assert parse_source_span_attr("0:0") == (0, 0)
    assert parse_source_span_attr("invalid") is None
    assert parse_source_span_attr("10:abc") is None


def test_round_trip():
    """A node's span survives render-then-parse."""
    from flexdoc.docs.node import Layer, NodeKind

    node = Node(
        id="n0010", kind=NodeKind.paragraph, layer=Layer.markdown, parent=None, source_span=(42, 99)
    )
    html = wrap_with_node_attrs(node, "div", "content")
    # Extract the data-source-span value.
    import re

    match = re.search(r'data-source-span="([^"]+)"', html)
    assert match is not None
    parsed = parse_source_span_attr(match.group(1))
    assert parsed == node.source_span
