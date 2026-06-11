from collections import Counter
from textwrap import dedent

from flexdoc.docs.block_types import BlockType
from flexdoc.docs.sizes import TextUnit
from flexdoc.docs.text_doc import TextDoc

_DOC = dedent(
    """
    # Top

    Intro paragraph of top.

    ## Sub A

    Body of A. Two sentences here.

    ## Sub B

    Body of B.

    # Top Two

    Final paragraph.
    """
).strip()


def test_sections_tree_structure():
    doc = TextDoc.from_text(_DOC)
    secs = doc.sections()
    assert [(s.level, s.title) for s in secs] == [(1, "Top"), (1, "Top Two")]
    assert [(c.level, c.title) for c in secs[0].children] == [(2, "Sub A"), (2, "Sub B")]
    assert secs[1].children == []


def test_section_span_covers_heading_through_subtree():
    doc = TextDoc.from_text(_DOC)
    top = doc.sections()[0]
    start, end = top.span
    assert _DOC[start:].startswith("# Top")
    covered = _DOC[start:end]
    assert "Body of B." in covered  # through the last subsection's content
    assert "Top Two" not in covered  # but not the next top-level section


def test_rolled_up_size_sums_subtree():
    doc = TextDoc.from_text(_DOC)
    top = doc.sections()[0]
    own = top.size(TextUnit.words, subtree=False)
    full = top.size(TextUnit.words, subtree=True)
    assert full > own
    # Words are additive across blocks, so subtree == own + each child's subtree.
    assert full == own + sum(c.size(TextUnit.words, subtree=True) for c in top.children)


def test_section_blocks_are_scoped_and_in_span():
    doc = TextDoc.from_text(_DOC)
    top = doc.sections()[0]
    types = [b.type for b in top.blocks()]
    # Top's OWN content only: its heading and intro paragraph, not Sub A/Sub B content.
    assert types == [BlockType.heading, BlockType.paragraph]
    s_start, s_end = top.span
    for b in top.blocks():
        assert s_start <= b.span[0] and b.span[1] <= s_end


def test_section_block_type_tally_per_section():
    # Per-section block-type tally is `Counter(b.type for b in section.blocks())` now that
    # the block_type_counts() convenience is removed (superseded by collect()/blocks()).
    doc = TextDoc.from_text(_DOC)
    top = doc.sections()[0]
    assert Counter(b.type for b in top.blocks()) == {BlockType.heading: 1, BlockType.paragraph: 1}
    sub_a = top.children[0]
    assert Counter(b.type for b in sub_a.blocks()) == {BlockType.heading: 1, BlockType.paragraph: 1}


def test_block_type_tally_is_density_invariant():
    # A loose vs. tight list yields the same tally over blocks() (density invariance);
    # the tree is a pure function of source_text, so nothing is cached.
    tight = TextDoc.from_text("# H\n\n- a\n- b\n- c")
    loose = TextDoc.from_text("# H\n\n- a\n\n- b\n\n- c")
    assert Counter(b.type for b in tight.blocks()) == Counter(b.type for b in loose.blocks())
    assert Counter(b.type for b in tight.blocks())[BlockType.list] == 1


def test_toc_is_flat_document_order():
    doc = TextDoc.from_text(_DOC)
    assert [(lvl, title) for lvl, title, _span in doc.toc()] == [
        (1, "Top"),
        (2, "Sub A"),
        (2, "Sub B"),
        (1, "Top Two"),
    ]


def test_section_size_tree_renders_titles_and_sizes():
    doc = TextDoc.from_text(_DOC)
    tree = doc.section_size_tree(units=(TextUnit.words,))
    for title in ("Top", "Sub A", "Sub B", "Top Two"):
        assert title in tree


def test_setext_heading_section():
    doc = TextDoc.from_text("Title\n=====\n\nBody here.")
    secs = doc.sections()
    assert len(secs) == 1
    assert secs[0].level == 1
    assert secs[0].title == "Title"


def test_no_headings_means_no_sections():
    doc = TextDoc.from_text("Just a paragraph. No headings here.")
    assert doc.sections() == []
    assert doc.toc() == []


def test_section_links_includes_reference_links():
    """Section.links() must see reference-style links resolved at the document level."""
    text = "# A\n\nSee [Docs][d].\n\n[d]: https://example.com/docs\n"
    doc = TextDoc.from_text(text)
    doc_links = doc.links()
    assert len(doc_links) == 1
    assert doc_links[0].url == "https://example.com/docs"
    section_links = doc.sections()[0].links()
    # The section must include the reference link (resolved from the document).
    assert len(section_links) >= 1
    assert any(lk.url == "https://example.com/docs" for lk in section_links)


def test_section_links_include_reference_links():
    """Section.links() derives from the document-level parse, so reference-style links
    (defined in a separate block) are attributed to their section (z8b2)."""
    from flexdoc.docs.text_doc import TextDoc

    text = "# Heading\n\nSee [docs][d] for more.\n\n[d]: https://docs.example\n"
    section = TextDoc.from_text(text).sections()[0]
    urls = {lk.url for lk in section.links()}
    assert "https://docs.example" in urls


def test_heading_inside_code_fence_is_not_a_section():
    """A '#'-prefixed line inside a fenced code block (which blank-line paragraph
    splitting can isolate) must not become a section; only the real heading counts."""
    md = dedent(
        """
        # Real

        ```
        text

        # Not a heading
        ```

        After.
        """
    ).strip()
    doc = TextDoc.from_text(md)
    assert [title for _, title, _ in doc.toc()] == ["Real"]
