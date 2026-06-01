"""
Tests for the `collect()` query primitive and `TextDoc.collect()` convenience.
"""

from __future__ import annotations

from collections import Counter
from textwrap import dedent

from chopdiff.docs.collect import collect
from chopdiff.docs.node import Layer, NodeKind, NodeTable
from chopdiff.docs.node_table import build_node_table
from chopdiff.docs.text_doc import TextDoc

# A rich document with nested structure: headings, a blockquote containing a table,
# a list with a nested code block, inline links, and code spans.
_RICH_DOC = dedent("""
    # Section One

    Some intro text with a [link one](https://one.example.com) here.

    > Blockquote preamble.
    >
    > | col1 | col2 |
    > | ---- | ---- |
    > | a    | b    |

    ## Section Two

    A paragraph with `code_span` in it.

    - list item alpha
    - list item beta with [link two](https://two.example.com)
      - nested item

    ```python
    x = 1
    ```
""").strip()


def _doc_and_table() -> tuple[TextDoc, NodeTable]:
    doc = TextDoc.from_text(_RICH_DOC)
    table = build_node_table(doc)
    return doc, table


def test_tally_by_kind_via_counter():
    """Counting by kind via Counter over collect results (the canonical idiom)."""
    _, table = _doc_and_table()
    tally = Counter(n.kind for n in collect(table, recursive=True))
    # Should find headings, paragraphs, blockquote, table, list, code, list_items, etc.
    assert tally[NodeKind.heading] >= 2
    assert tally[NodeKind.blockquote] >= 1
    assert tally[NodeKind.table] >= 1
    assert tally[NodeKind.code] >= 1
    assert tally[NodeKind.list] >= 1


def test_nested_table_in_blockquote_found_recursively():
    """A table nested in a blockquote IS returned by recursive collect with kinds={table}."""
    _, table = _doc_and_table()
    tables = collect(table, kinds={NodeKind.table}, recursive=True)
    assert len(tables) >= 1
    # Verify the table node is actually inside a blockquote.
    for t in tables:
        assert t.kind == NodeKind.table
        # Walk up the parent chain to confirm blockquote ancestry.
        parent_id = t.parent
        found_bq = False
        while parent_id is not None:
            parent_node = table.node(parent_id)
            if parent_node.kind == NodeKind.blockquote:
                found_bq = True
                break
            parent_id = parent_node.parent
        assert found_bq


def test_non_recursive_returns_only_roots():
    """Non-recursive collect (the default) returns only root-level nodes."""
    _, table = _doc_and_table()
    roots = collect(table, recursive=False)
    # All returned nodes should be roots (no parent, or at least in the roots list).
    root_ids = set(table.roots)
    for n in roots:
        assert n.id in root_ids


def test_links_via_inline_flag():
    """Links are inline nodes; they require `inline=True` to appear."""
    _, table = _doc_and_table()
    # Without inline flag, no links returned.
    no_inline = collect(table, kinds={NodeKind.link}, recursive=True, inline=False)
    assert len(no_inline) == 0

    # With inline flag, links are returned.
    with_inline = collect(table, kinds={NodeKind.link}, recursive=True, inline=True)
    assert len(with_inline) >= 2


def test_scope_restricts_to_subtree():
    """Scoped collect restricts results to the given node's subtree."""
    _, table = _doc_and_table()
    # Find the blockquote node.
    bqs = [n for n in table.nodes.values() if n.kind == NodeKind.blockquote]
    assert len(bqs) >= 1
    bq = bqs[0]

    # Scoped recursive collect should find the table inside the blockquote.
    scoped = collect(table, scope=bq.id, recursive=True)
    table_nodes = [n for n in scoped if n.kind == NodeKind.table]
    assert len(table_nodes) >= 1

    # But should NOT find headings (they are outside the blockquote).
    heading_nodes = [n for n in scoped if n.kind == NodeKind.heading]
    assert len(heading_nodes) == 0


def test_where_predicate():
    """The `where` predicate provides an escape hatch for arbitrary filtering."""
    _, table = _doc_and_table()
    # Find only heading nodes with level 2.
    h2s = collect(
        table,
        kinds={NodeKind.heading},
        recursive=True,
        where=lambda n: n.attrs.get("level") == 2,
    )
    assert len(h2s) >= 1
    for h in h2s:
        assert h.attrs.get("level") == 2


def test_contains_cross_layer_query():
    """
    `contains` restricts results to nodes whose source_span falls within the
    given span, enabling cross-layer queries.
    """
    _, table = _doc_and_table()
    # Find section nodes from the document layer.
    sections = [
        n for n in table.nodes.values() if n.kind == NodeKind.section and n.layer == Layer.document
    ]
    assert len(sections) >= 1
    # Use the first section's span as the containment boundary.
    sec = sections[0]
    assert sec.source_span is not None

    # Cross-layer query: find markdown-layer blocks contained within this section's span.
    contained = collect(
        table,
        recursive=True,
        contains=sec.source_span,
    )
    # All results must have spans within the section.
    for n in contained:
        assert n.source_span is not None
        assert sec.source_span[0] <= n.source_span[0]
        assert n.source_span[1] <= sec.source_span[1]

    # There should be markdown-layer nodes in the result (cross-layer).
    md_nodes = [n for n in contained if n.layer == Layer.markdown]
    assert len(md_nodes) >= 1


def test_contains_finds_inline_links_in_span():
    """
    `contains` with `inline=True` can find inline links within a given text region.
    """
    _, table = _doc_and_table()
    # Find the span of "Section One" content (before "## Section Two").
    sec_two_start = _RICH_DOC.find("## Section Two")
    assert sec_two_start > 0

    # Find links in the first section's span.
    links = collect(
        table,
        recursive=True,
        inline=True,
        kinds={NodeKind.link},
        contains=(0, sec_two_start),
    )
    # "link one" should be found; "link two" should not (it's in section two).
    urls = [n.attrs.get("url") for n in links]
    assert "https://one.example.com" in urls
    assert "https://two.example.com" not in urls


def test_query_vs_partition_overlapping_results():
    """
    Demonstrate that collect is a query, not a partition: it may return nodes
    that overlap their containers. A blockquote and a table inside it can both
    appear in results, which is correct for counting/gathering.
    """
    _, table = _doc_and_table()
    # Collect both blockquotes and tables recursively.
    results = collect(
        table,
        kinds={NodeKind.blockquote, NodeKind.table},
        recursive=True,
    )
    bqs = [n for n in results if n.kind == NodeKind.blockquote]
    tables = [n for n in results if n.kind == NodeKind.table]
    assert len(bqs) >= 1
    assert len(tables) >= 1

    # The table's span is inside the blockquote's span: they overlap in the result.
    bq_span = bqs[0].source_span
    tbl_span = tables[0].source_span
    assert bq_span is not None and tbl_span is not None
    assert bq_span[0] <= tbl_span[0] and tbl_span[1] <= bq_span[1]


def test_deterministic_document_order():
    """Results are returned in deterministic document order (by source_span)."""
    _, table = _doc_and_table()
    results = collect(table, recursive=True)
    spans = [n.source_span for n in results if n.source_span is not None]
    # Verify sorted by start offset.
    starts = [s[0] for s in spans]
    assert starts == sorted(starts)


def test_textdoc_collect_convenience():
    """TextDoc.collect() is a convenience that delegates to collect() over node_table()."""
    doc = TextDoc.from_text(_RICH_DOC)
    tables = doc.collect(kinds={NodeKind.table}, recursive=True)
    assert len(tables) >= 1
    assert all(n.kind == NodeKind.table for n in tables)


def test_textdoc_collect_with_scope():
    """TextDoc.collect() works with scope parameter."""
    doc = TextDoc.from_text(_RICH_DOC)
    nt = doc.node_table()
    bqs = [n for n in nt.nodes.values() if n.kind == NodeKind.blockquote]
    assert len(bqs) >= 1
    scoped = doc.collect(scope=bqs[0].id, recursive=True)
    table_nodes = [n for n in scoped if n.kind == NodeKind.table]
    assert len(table_nodes) >= 1


def test_code_spans_inline():
    """Code spans are inline nodes and require inline=True."""
    doc = TextDoc.from_text(_RICH_DOC)
    spans_no = doc.collect(kinds={NodeKind.code_span}, recursive=True, inline=False)
    assert len(spans_no) == 0
    spans_yes = doc.collect(kinds={NodeKind.code_span}, recursive=True, inline=True)
    assert len(spans_yes) >= 1


def test_collect_layer_filters_cross_layer_duplicates():
    """A bare paragraph kind appears in both markdown and textual layers; `layer=`
    selects one, eliminating cross-layer duplicate spans."""
    td = TextDoc.from_text("A short paragraph.\n\nAnother paragraph.\n")

    both = td.collect(kinds={NodeKind.paragraph}, recursive=True)
    md_only = td.collect(kinds={NodeKind.paragraph}, recursive=True, layer={Layer.markdown})
    txt_only = td.collect(kinds={NodeKind.paragraph}, recursive=True, layer={Layer.textual})

    # Default (no layer) returns both layers; each single-layer query is a strict subset.
    assert len(md_only) == 2
    assert len(txt_only) == 2
    assert len(both) == len(md_only) + len(txt_only)
    assert {n.layer for n in md_only} == {Layer.markdown}
    # Single-layer results have no duplicate spans.
    md_spans = [n.source_span for n in md_only]
    assert len(md_spans) == len(set(md_spans))


def test_collect_layer_does_not_silently_drop_sections():
    """The default (no `layer`) must still surface document-layer sections; restricting
    to markdown is what hides them (the deliberate, explicit choice)."""
    td = TextDoc.from_text("# Title\n\nBody paragraph.\n")
    assert td.collect(kinds={NodeKind.section}, recursive=True)  # default: found
    assert td.collect(kinds={NodeKind.section}, recursive=True, layer={Layer.markdown}) == []


def test_textdoc_base_blocks_matches_free_function():
    from chopdiff.docs.base_blocks import base_blocks as base_blocks_fn

    text = "- one\n  - a\n  - b\n- two\n"
    td = TextDoc.from_text(text)
    method = td.base_blocks()
    fn = base_blocks_fn(text)
    assert [(b.block.span, b.depth) for b in method] == [(b.block.span, b.depth) for b in fn]
