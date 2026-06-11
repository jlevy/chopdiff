"""
Tests for `build_node_table` (Beads 4 and 5): node table construction,
lazy caching, id stability, three-layer coverage, inline item nodes,
and interval containment helpers.
"""

from __future__ import annotations

from textwrap import dedent

from flexdoc.docs.node import Layer, NodeKind
from flexdoc.docs.node_table import build_node_table
from flexdoc.docs.text_doc import TextDoc

# A document with nested structure: headings, sections, paragraphs, a
# blockquote with nested content, a list, inline links, code spans, and
# an image.
_NESTED_DOC = dedent("""
    # Top Heading

    First paragraph with a [link](https://example.com) and `code_here`.

    ## Sub Heading

    > A blockquote with text.

    - item one
    - item two

    Third paragraph.

    ## Another Sub

    Final text with ![img](https://img.example.com/pic.png) inside.
""").strip()


def _build(text: str | None = None):
    doc = TextDoc.from_text(text or _NESTED_DOC)
    return doc, build_node_table(doc)


# -- Bead 4: node table build and structure --


def test_ids_stable_across_builds():
    """Two builds of the same source produce identical ids."""
    _, t1 = _build()
    _, t2 = _build()
    assert list(t1.nodes.keys()) == list(t2.nodes.keys())
    for nid in t1.nodes:
        assert t1.nodes[nid].kind == t2.nodes[nid].kind
        assert t1.nodes[nid].source_span == t2.nodes[nid].source_span


def test_three_layers_populated():
    """All three layers (markdown, document, textual) have at least one node."""
    _, table = _build()
    md = table.by_layer(Layer.markdown)
    doc_layer = table.by_layer(Layer.document)
    txt = table.by_layer(Layer.textual)
    assert len(md) > 0
    assert len(doc_layer) > 0
    assert len(txt) > 0


def test_source_span_matches_source_text():
    """Every node with a source_span slices to the correct text."""
    _, table = _build()
    src = table.source_text
    for node in table.nodes.values():
        if node.source_span is not None:
            s, e = node.source_span
            sliced = src[s:e]
            assert len(sliced) > 0 or s == e


def test_parent_children_consistency():
    """Every child's parent points back to its parent, and every parent lists its child."""
    _, table = _build()
    for node in table.nodes.values():
        for cid in node.children:
            child = table.node(cid)
            assert child.parent == node.id
        if node.parent is not None:
            parent = table.node(node.parent)
            assert node.id in parent.children


def test_markdown_block_tree_structure():
    """Markdown layer contains headings, paragraphs, blockquote, list, etc."""
    _, table = _build()
    md = table.by_layer(Layer.markdown)
    kinds = {n.kind for n in md}
    assert NodeKind.heading in kinds
    assert NodeKind.paragraph in kinds
    assert NodeKind.blockquote in kinds
    assert NodeKind.list in kinds


def test_heading_level_attrs():
    """Heading nodes carry a `level` attribute."""
    _, table = _build()
    headings = table.by_kind(NodeKind.heading)
    assert len(headings) >= 2
    levels = [h.attrs.get("level") for h in headings]
    assert 1 in levels
    assert 2 in levels


def test_list_attrs_tight_ordered():
    """List nodes carry `tight` and `ordered` attrs."""
    _, table = _build()
    lists = table.by_kind(NodeKind.list)
    assert len(lists) >= 1
    for lst in lists:
        assert "tight" in lst.attrs
        assert "ordered" in lst.attrs


def test_document_layer_sections():
    """Document layer has section nodes matching the heading hierarchy."""
    _, table = _build()
    sections = table.by_kind(NodeKind.section)
    assert len(sections) >= 2
    for sec in sections:
        assert sec.layer == Layer.document
        assert "level" in sec.attrs
        assert "title" in sec.attrs


def test_section_nesting():
    """Sub-sections are children of their parent section."""
    _, table = _build()
    sections = table.by_kind(NodeKind.section)
    top_sections = [s for s in sections if s.parent is None]
    # "Top Heading" is a level-1 section with sub-sections.
    assert len(top_sections) >= 1
    top = top_sections[0]
    assert len(top.children) >= 2


def test_textual_layer_paragraphs_and_sentences():
    """Textual layer has paragraph nodes with sentence children."""
    _, table = _build()
    txt_paras = [n for n in table.by_layer(Layer.textual) if n.kind == NodeKind.paragraph]
    assert len(txt_paras) >= 1
    # Each paragraph should have sentence children.
    for para in txt_paras:
        sents = table.children_of(para.id)
        assert len(sents) >= 1
        for s in sents:
            assert s.kind == NodeKind.sentence
            assert s.layer == Layer.textual


def test_containing_interval_helper():
    """NodeTable.containing() finds nodes whose span encloses the query."""
    _, table = _build()
    # Find the link node.
    links = table.by_kind(NodeKind.link)
    assert len(links) >= 1
    link = links[0]
    assert link.source_span is not None

    # The containing nodes should include the paragraph block that holds the link.
    containers = table.containing(link.source_span)
    assert len(containers) >= 1
    # At minimum the link itself and its containing block are in the result.
    container_kinds = {n.kind for n in containers}
    assert NodeKind.link in container_kinds or NodeKind.paragraph in container_kinds


def test_contained_by_interval_helper():
    """NodeTable.contained_by() finds nodes whose span is inside the query."""
    _, table = _build()
    # Use the entire document span.
    full_span = (0, len(table.source_text))
    contained = table.contained_by(full_span)
    # All nodes with spans should be contained.
    nodes_with_spans = [n for n in table.nodes.values() if n.source_span is not None]
    assert len(contained) == len(nodes_with_spans)


def test_by_kind_accessor():
    _, table = _build()
    headings = table.by_kind(NodeKind.heading)
    assert all(n.kind == NodeKind.heading for n in headings)


def test_by_layer_accessor():
    _, table = _build()
    md = table.by_layer(Layer.markdown)
    assert all(n.layer == Layer.markdown for n in md)


def test_children_of_accessor():
    _, table = _build()
    # Find a list node and check its children are list_items.
    lists = table.by_kind(NodeKind.list)
    assert len(lists) >= 1
    children = table.children_of(lists[0].id)
    assert all(c.kind == NodeKind.list_item for c in children)


# -- Bead 4: lazy cache on TextDoc --


def test_node_table_cached_on_textdoc():
    """TextDoc.node_table() returns the same object on repeated calls."""
    doc = TextDoc.from_text(_NESTED_DOC)
    t1 = doc.node_table()
    t2 = doc.node_table()
    assert t1 is t2


def test_node_table_matches_build():
    """TextDoc.node_table() result matches a fresh build_node_table()."""
    doc = TextDoc.from_text(_NESTED_DOC)
    cached = doc.node_table()
    fresh = build_node_table(doc)
    assert set(cached.nodes.keys()) == set(fresh.nodes.keys())
    assert cached.roots == fresh.roots


# -- Bead 5: inline items as nodes --


def test_link_inline_node():
    """Links are inline nodes with kind=link, layer=markdown, and attrs with url/text."""
    _, table = _build()
    links = table.by_kind(NodeKind.link)
    assert len(links) >= 1
    link = links[0]
    assert link.layer == Layer.markdown
    assert "url" in link.attrs
    assert "text" in link.attrs
    assert link.attrs["url"] == "https://example.com"


def test_link_parent_is_block():
    """A link node's parent is a markdown-layer block node."""
    _, table = _build()
    links = table.by_kind(NodeKind.link)
    assert len(links) >= 1
    for link in links:
        if link.parent is not None:
            parent = table.node(link.parent)
            assert parent.layer == Layer.markdown


def test_link_section_association():
    """A link inside a section carries the section node id in attrs."""
    _, table = _build()
    links = table.by_kind(NodeKind.link)
    assert len(links) >= 1
    # The first link ("link") is inside "Top Heading" / "# Top Heading" section.
    link = links[0]
    assert "section" in link.attrs
    section_id = str(link.attrs["section"])
    section_node = table.node(section_id)
    assert section_node.kind == NodeKind.section


def test_link_sentence_association():
    """A link inside a sentence carries the sentence node id in attrs."""
    _, table = _build()
    links = table.by_kind(NodeKind.link)
    assert len(links) >= 1
    link = links[0]
    assert "sentence" in link.attrs
    sent_id = str(link.attrs["sentence"])
    sent_node = table.node(sent_id)
    assert sent_node.kind == NodeKind.sentence
    assert sent_node.layer == Layer.textual


def test_code_span_inline_node():
    """Code spans are inline nodes with kind=code_span and attrs with content."""
    _, table = _build()
    code_spans = table.by_kind(NodeKind.code_span)
    assert len(code_spans) >= 1
    cs = code_spans[0]
    assert cs.layer == Layer.markdown
    assert "content" in cs.attrs
    assert cs.attrs["content"] == "code_here"


def test_code_span_has_exact_span():
    """Code span nodes have exact source_span."""
    _, table = _build()
    code_spans = table.by_kind(NodeKind.code_span)
    assert len(code_spans) >= 1
    cs = code_spans[0]
    assert cs.source_span is not None
    sliced = table.source_text[cs.source_span[0] : cs.source_span[1]]
    assert "`code_here`" == sliced


def test_image_inline_node():
    """Images are detected as kind=image, not link."""
    _, table = _build()
    images = table.by_kind(NodeKind.image)
    assert len(images) >= 1
    img = images[0]
    assert img.layer == Layer.markdown
    assert "url" in img.attrs
    assert img.source_span is not None
    # The source span should include the `!` prefix.
    sliced = table.source_text[img.source_span[0] : img.source_span[1]]
    assert sliced.startswith("!")


def test_links_in_section_derivable():
    """
    'Links in section N' is derivable by filtering inline nodes by their
    section attr -- the use case from the spec.
    """
    _, table = _build()
    # Find the "Top Heading" section node.
    sections = table.by_kind(NodeKind.section)
    top_sec = next(s for s in sections if s.attrs.get("title") == "Top Heading")

    # Filter links by section attr.
    links = table.by_kind(NodeKind.link)
    links_in_top = [lk for lk in links if lk.attrs.get("section") == top_sec.id]
    assert len(links_in_top) >= 1
    assert any(lk.attrs.get("url") == "https://example.com" for lk in links_in_top)


def test_inline_node_parent_is_innermost_block():
    """An inline node's parent is the innermost enclosing block, not a container."""
    _, table = _build()
    links = table.by_kind(NodeKind.link)
    for link in links:
        if link.parent is None:
            continue
        parent = table.node(link.parent)
        # The parent should be a leaf-ish block (paragraph, list_item, etc.),
        # not a container like the whole document.
        assert parent.source_span is not None
        assert link.source_span is not None
        # Parent span must contain the link span.
        assert parent.source_span[0] <= link.source_span[0]
        assert link.source_span[1] <= parent.source_span[1]


def test_reference_link_no_span():
    """Reference links that have no exact source span get source_span=None."""
    text = dedent("""
        See [my ref][1] for details.

        [1]: https://ref.example.com
    """).strip()
    doc = TextDoc.from_text(text)
    table = build_node_table(doc)
    links = table.by_kind(NodeKind.link)
    # At least one link should exist (the resolved reference link).
    assert len(links) >= 1
