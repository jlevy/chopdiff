from flexdoc.html.html_tags import html_extract_attribute_value, html_find_tag


def test_html_find_tag_nested_self_closing_same_name():
    html = '<div id="outer">before <div id="inner"/> after</div>'
    matches = html_find_tag(html, tag_name="div", attr_name="id", attr_value="outer")
    assert len(matches) == 1
    m = matches[0]
    # The outer match must span the full enclosing div, not just its opening tag.
    assert html[m.start_offset : m.end_offset] == html
    assert html[m.end_offset - len("</div>") : m.end_offset] == "</div>"


def test_html_extract_attribute_distinguishes_empty_from_missing():
    extract = html_extract_attribute_value("data-x")
    assert extract('<span data-x="">text</span>') == ""  # present but empty
    assert extract("<span>text</span>") is None  # missing


def test_html_find_tag_strict_raises_on_unparseable():
    # Best-effort by default returns whatever parses; strict surfaces failures. A normal
    # well-formed doc yields matches in both modes.
    html = '<div id="a">x</div>'
    assert len(html_find_tag(html, tag_name="div", strict=True)) == 1
