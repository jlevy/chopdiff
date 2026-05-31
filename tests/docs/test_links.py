from textwrap import dedent

from chopdiff.docs.text_doc import TextDoc

_DOC = dedent(
    """
    # Title

    See [the site](https://example.com "Home") and [docs](https://docs.example.com) here.

    Plain paragraph with no links at all.

    A bare https://bare.example.com URL and an <https://auto.example.com> autolink.
    """
).strip()


def test_doc_links_identity():
    doc = TextDoc.from_text(_DOC)
    by_url = {link.url: link for link in doc.links()}
    assert set(by_url) == {
        "https://example.com",
        "https://docs.example.com",
        "https://bare.example.com",
        "https://auto.example.com",
    }
    site = by_url["https://example.com"]
    assert site.text == "the site"
    assert site.title == "Home"


def test_link_spans_round_trip_into_source():
    doc = TextDoc.from_text(_DOC)
    located = [link for link in doc.links() if link.span is not None]
    assert located, "expected at least some links to have recovered spans"
    for link in located:
        assert link.span is not None
        start, end = link.span
        slice_ = _DOC[start:end]
        assert link.text in slice_ or link.url in slice_


def test_block_and_section_link_rollup():
    doc = TextDoc.from_text(_DOC)
    section = doc.sections()[0]
    doc_with_spans = [lk for lk in doc.links() if lk.span is not None]
    # Section.links() returns links with recoverable spans, filtered to the section.
    # It must include every span-bearing doc link whose span falls in the section.
    assert len(section.links()) == len(doc_with_spans)
    # Links come only from the two paragraphs that contain them.
    with_links = [p for p in doc.paragraphs if p.links()]
    assert len(with_links) == 2


def test_link_to_sentence_association():
    doc = TextDoc.from_text(_DOC)
    site = next(link for link in doc.links() if link.url == "https://example.com")
    assert site.span is not None
    idx = doc.sentence_at_offset(site.span[0])
    assert idx is not None
    assert "the site" in doc.get_sent(idx).text


def test_no_links():
    doc = TextDoc.from_text("Just text. No links here at all.")
    assert doc.links() == []


def test_reference_link_resolved_across_blocks():
    # The reference definition lives in a separate block from the use; flowmark
    # resolves it only with the full document, so TextDoc.links() must parse
    # source_text once, not per-paragraph.
    text = 'See [Docs][d].\n\n[d]: https://example.com/docs "Docs"\n'
    doc = TextDoc.from_text(text)
    links = doc.links()
    assert len(links) == 1
    link = links[0]
    assert link.text == "Docs"
    assert link.url == "https://example.com/docs"
    assert link.title == "Docs"


def test_shortcut_reference_link_resolved_across_blocks():
    # Shortcut reference: `[Docs]` with separate `[Docs]: url` definition.
    text = "See [Docs].\n\n[Docs]: https://example.com/docs\n"
    doc = TextDoc.from_text(text)
    urls = {link.url for link in doc.links()}
    assert urls == {"https://example.com/docs"}


def test_reference_then_inline_link_span():
    """An inline link following a reference link must get a non-None span."""
    text = "See [Docs][d] and [Site](https://site.example).\n\n[d]: https://example.com/docs\n"
    doc = TextDoc.from_text(text)
    links = doc.links()
    by_url = {link.url: link for link in links}
    assert "https://example.com/docs" in by_url
    assert "https://site.example" in by_url
    # The inline link [Site] must have a recoverable span.
    site = by_url["https://site.example"]
    assert site.span is not None, "inline link after reference link should have a span"
    assert text[site.span[0] : site.span[1]] == "[Site](https://site.example)"


def test_image_then_inline_link_span():
    """An inline link following an image must get a non-None span."""
    text = "Look ![alt](https://img.example/p.png) and [link](https://link.example).\n"
    doc = TextDoc.from_text(text)
    links = doc.links()
    # images are included by extract_links; the plain link must still get a span.
    link = next((lk for lk in links if lk.url == "https://link.example"), None)
    assert link is not None
    assert link.span is not None, "inline link after image should have a span"
    assert text[link.span[0] : link.span[1]] == "[link](https://link.example)"


def test_inline_reference_inline_link_spans():
    """Inline, reference, inline: the second inline link must get a span too."""
    text = "A [first](https://first.example) then [Docs][d] then [last](https://last.example).\n\n[d]: https://example.com/docs\n"
    doc = TextDoc.from_text(text)
    links = doc.links()
    by_url = {link.url: link for link in links}
    first = by_url["https://first.example"]
    last = by_url["https://last.example"]
    assert first.span is not None
    assert text[first.span[0] : first.span[1]] == "[first](https://first.example)"
    assert last.span is not None
    assert text[last.span[0] : last.span[1]] == "[last](https://last.example)"
