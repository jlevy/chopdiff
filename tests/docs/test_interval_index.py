"""
Tests for `IntervalIndex`: innermost-containing lookups over nested node spans,
including kind filtering and offsets that fall in gaps.
"""

from __future__ import annotations

from textwrap import dedent

from flexdoc.docs.interval_index import IntervalIndex
from flexdoc.docs.node import Layer, NodeKind
from flexdoc.docs.node_table import build_node_table
from flexdoc.docs.text_doc import TextDoc

_DOC = dedent("""
    # Top

    Intro paragraph with a [link](https://example.com) inside.

    ## Sub

    Another paragraph here.
""").strip()


def test_innermost_picks_narrowest_nested_span():
    """For nested markdown spans, innermost returns the deepest (narrowest) container,
    and the kind filter selects a specific enclosing kind."""
    table = build_node_table(TextDoc.from_text(_DOC))
    index = IntervalIndex.from_nodes(table.nodes)
    link_off = _DOC.index("https://example.com")

    # Unfiltered: the narrowest markdown node containing the offset is the link itself.
    narrowest = index.innermost(link_off, Layer.markdown)
    assert narrowest is not None
    assert table.node(narrowest).kind == NodeKind.link

    # Filtered to paragraphs: the enclosing paragraph block.
    para_id = index.innermost(link_off, Layer.markdown, kind=NodeKind.paragraph)
    assert para_id is not None
    para = table.node(para_id)
    assert para.kind == NodeKind.paragraph
    assert para.source_span is not None
    assert para.source_span[0] <= link_off < para.source_span[1]


def test_innermost_kind_filter_selects_section_and_sentence():
    table = build_node_table(TextDoc.from_text(_DOC))
    index = IntervalIndex.from_nodes(table.nodes)
    link_off = _DOC.index("https://example.com")

    section_id = index.innermost(link_off, Layer.document, kind=NodeKind.section)
    assert section_id is not None
    assert table.node(section_id).attrs.get("title") == "Top"

    sent_id = index.innermost(link_off, Layer.textual, kind=NodeKind.sentence)
    assert sent_id is not None
    assert table.node(sent_id).kind == NodeKind.sentence


def test_innermost_matches_bruteforce_minwidth_scan():
    """Over a richly nested document, `innermost` returns a narrowest-containing node for
    every offset and layer/kind, matching a brute-force min-width scan (pins the
    same-layer-nesting assumption the index relies on)."""
    rich = (
        "# Top\n\n"
        "Intro with a [link](https://example.com) here.\n\n"
        "> Quote with `code` inside.\n>\n> | a | b |\n> | - | - |\n> | 1 | 2 |\n\n"
        "## Sub\n\n"
        "- item one\n- item two with [two](https://example.com/2)\n  - nested\n\n"
        "Final sentence."
    )
    table = build_node_table(TextDoc.from_text(rich))
    index = IntervalIndex.from_nodes(table.nodes)

    def min_containing_width(offset: int, layer: Layer, kind: NodeKind | None) -> int | None:
        widths = [
            n.source_span[1] - n.source_span[0]
            for n in table.nodes.values()
            if n.layer == layer
            and n.source_span is not None
            and (kind is None or n.kind == kind)
            and n.source_span[0] <= offset < n.source_span[1]
        ]
        return min(widths) if widths else None

    cases = [
        (Layer.markdown, None),
        (Layer.document, NodeKind.section),
        (Layer.textual, NodeKind.sentence),
    ]
    for offset in range(len(rich) + 1):
        for layer, kind in cases:
            got = index.innermost(offset, layer, kind)
            expected_width = min_containing_width(offset, layer, kind)
            if expected_width is None:
                assert got is None, (offset, layer, kind)
            else:
                assert got is not None, (offset, layer, kind)
                span = table.node(got).source_span
                assert span is not None
                assert span[1] - span[0] == expected_width, (offset, layer, kind)


def test_innermost_returns_none_outside_any_span():
    table = build_node_table(TextDoc.from_text(_DOC))
    index = IntervalIndex.from_nodes(table.nodes)
    # An offset past the end of the document is contained by nothing.
    assert index.innermost(len(_DOC) + 100, Layer.markdown) is None
    # A layer with no indexed nodes yields None.
    assert index.innermost(0, Layer.synthetic) is None
