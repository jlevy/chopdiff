from textwrap import dedent

import pytest

from chopdiff.html.html_tags import (
    html_extract_attribute_value,
    html_find_tag,
    rewrite_html_img_urls,
    rewrite_html_tag_attr,
)


def test_rewrite_html_tag_attr_various_tags() -> None:
    """Test rewriting different HTML tags."""
    # Test img src
    html = '<img src="./photo.jpg">'
    result = rewrite_html_tag_attr(html, "img", "src", from_prefix="./", to_prefix="/static/")
    assert "/static/photo.jpg" in result
    assert "./photo.jpg" not in result

    # Test link href
    html = '<a href="./page.html">Link</a>'
    result = rewrite_html_tag_attr(html, "a", "href", from_prefix="./", to_prefix="/")
    assert "/page.html" in result
    assert "./page.html" not in result

    # Test script src
    html = '<script src="./app.js"></script>'
    result = rewrite_html_tag_attr(html, "script", "src", from_prefix="./", to_prefix="/js/")
    assert "/js/app.js" in result

    # Test link stylesheet
    html = '<link rel="stylesheet" href="./style.css">'
    result = rewrite_html_tag_attr(html, "link", "href", from_prefix="./", to_prefix="/css/")
    assert "/css/style.css" in result


def test_rewrite_html_tag_attr_unclosed_tags() -> None:
    """Test handling of unclosed/self-closing tags."""
    # Self-closing img tag
    html = '<img src="./photo.jpg" />'
    result = rewrite_html_tag_attr(html, "img", "src", from_prefix="./", to_prefix="/static/")
    assert "/static/photo.jpg" in result

    # Unclosed img tag (HTML5 style)
    html = '<img src="./photo.jpg">'
    result = rewrite_html_tag_attr(html, "img", "src", from_prefix="./", to_prefix="/static/")
    assert "/static/photo.jpg" in result

    # Mixed closed and unclosed
    html = '<img src="./a.jpg"><img src="./b.jpg" />'
    result = rewrite_html_tag_attr(html, "img", "src", from_prefix="./", to_prefix="/s/")
    assert "/s/a.jpg" in result
    assert "/s/b.jpg" in result


def test_rewrite_html_tag_attr_quote_styles() -> None:
    """Test different quote styles for attribute values."""
    # Double quotes
    html = '<img src="./photo.jpg">'
    result = rewrite_html_tag_attr(html, "img", "src", from_prefix="./", to_prefix="/")
    assert '"/photo.jpg"' in result

    # Single quotes
    html = "<img src='./photo.jpg'>"
    result = rewrite_html_tag_attr(html, "img", "src", from_prefix="./", to_prefix="/")
    assert "'/photo.jpg'" in result

    # Mixed quotes in same document
    html = """<img src="./a.jpg"><img src='./b.jpg'>"""
    result = rewrite_html_tag_attr(html, "img", "src", from_prefix="./", to_prefix="/")
    assert '"/a.jpg"' in result
    assert "'/b.jpg'" in result


def test_rewrite_html_tag_attr_custom_rewriter() -> None:
    """Test with custom value rewriter function."""

    def add_query_param(value: str) -> str | None:
        if "?" not in value:
            return value + "?v=1.0"
        return None

    html = '<img src="photo.jpg"><img src="other.jpg?existing=param">'
    result = rewrite_html_tag_attr(html, "img", "src", value_rewriter=add_query_param)
    assert "photo.jpg?v=1.0" in result
    assert "other.jpg?existing=param" in result  # Unchanged


def test_rewrite_html_tag_attr_complex_html() -> None:
    """Test with complex nested HTML structure."""
    html = dedent(
        """
        <div class="gallery">
            <img src="./images/photo1.jpg" alt="Photo 1" class="thumbnail">
            <div>
                <img src="./images/photo2.png" />
                <a href="./pages/about.html">About</a>
            </div>
        </div>
    """
    )

    # Rewrite images
    result = rewrite_html_tag_attr(
        html, "img", "src", from_prefix="./images/", to_prefix="/static/"
    )
    assert "/static/photo1.jpg" in result
    assert "/static/photo2.png" in result
    assert "./pages/about.html" in result  # Unchanged

    # Rewrite links
    result = rewrite_html_tag_attr(html, "a", "href", from_prefix="./pages/", to_prefix="/content/")
    assert "/content/about.html" in result
    assert "./images/photo1.jpg" in result  # Unchanged


def test_rewrite_html_tag_attr_edge_cases() -> None:
    """Test edge cases and special scenarios."""
    # Empty HTML
    result = rewrite_html_tag_attr("", "img", "src", from_prefix="./", to_prefix="/")
    assert result == ""  # Empty input returns empty output

    # HTML with no matching tags
    html = "<div><p>No images here</p></div>"
    result = rewrite_html_tag_attr(html, "img", "src", from_prefix="./", to_prefix="/")
    assert "No images here" in result

    # Tags with no matching attributes
    html = '<img alt="Photo">'  # No src attribute
    result = rewrite_html_tag_attr(html, "img", "src", from_prefix="./", to_prefix="/")
    assert html == result  # Unchanged

    # Multiple attributes, only rewrite specified one
    html = '<img src="./photo.jpg" data-src="./data.jpg">'
    result = rewrite_html_tag_attr(html, "img", "src", from_prefix="./", to_prefix="/")
    assert "/photo.jpg" in result
    assert "./data.jpg" in result  # data-src unchanged


def test_rewrite_html_tag_attr_attribute_order() -> None:
    """Test that attribute order doesn't matter."""
    html1 = '<img src="./photo.jpg" alt="Photo" class="img">'
    html2 = '<img class="img" src="./photo.jpg" alt="Photo">'
    html3 = '<img alt="Photo" class="img" src="./photo.jpg">'

    for html in [html1, html2, html3]:
        result = rewrite_html_tag_attr(html, "img", "src", from_prefix="./", to_prefix="/")
        assert "/photo.jpg" in result
        assert "./photo.jpg" not in result


def test_rewrite_html_tag_attr_special_characters() -> None:
    """Test handling of special characters in attribute values."""
    html = '<a href="./page?param=value&other=123">Link</a>'
    result = rewrite_html_tag_attr(html, "a", "href", from_prefix="./", to_prefix="/app/")
    assert "/app/page?param=value&other=123" in result

    html = '<img src="./images/photo (1).jpg">'
    result = rewrite_html_tag_attr(
        html, "img", "src", from_prefix="./images/", to_prefix="/static/"
    )
    assert "/static/photo (1).jpg" in result


def test_rewrite_html_tag_attr_multiple_replacements() -> None:
    """Test multiple tags with same attribute get replaced."""
    html = dedent(
        """
        <link rel="stylesheet" href="./css/reset.css">
        <link rel="stylesheet" href="./css/main.css">
    """
    )
    result = rewrite_html_tag_attr(
        html, "link", "href", from_prefix="./css/", to_prefix="/static/css/"
    )
    assert "/static/css/reset.css" in result
    assert "/static/css/main.css" in result


def test_rewrite_html_tag_attr_quote_escaping() -> None:
    """Test that replacement values with quotes are properly escaped."""

    # Test 1: Replacement contains double quotes, original uses double quotes
    html_double = '<img src="photo.jpg" alt="test">'

    def add_double_quotes(value: str) -> str | None:
        if value == "photo.jpg":
            return 'image"with"quotes.jpg'
        return None

    result_double = rewrite_html_tag_attr(html_double, "img", "src", add_double_quotes)
    # Should escape the quotes as &quot;
    assert 'src="image&quot;with&quot;quotes.jpg"' in result_double

    # Test 2: Replacement contains single quotes, original uses single quotes
    html_single = "<img src='photo.jpg' alt='test'>"

    def add_single_quotes(value: str) -> str | None:
        if value == "photo.jpg":
            return "image'with'quotes.jpg"
        return None

    result_single = rewrite_html_tag_attr(html_single, "img", "src", add_single_quotes)
    # Should escape the quotes as &#39;
    assert "src='image&#39;with&#39;quotes.jpg'" in result_single

    # Test 3: Replacement contains double quotes, original uses single quotes
    html_mixed1 = "<img src='photo.jpg'>"

    result_mixed1 = rewrite_html_tag_attr(html_mixed1, "img", "src", add_double_quotes)
    # Single quotes can contain double quotes without escaping
    assert """src='image"with"quotes.jpg'""" in result_mixed1

    # Test 4: Replacement contains single quotes, original uses double quotes
    html_mixed2 = '<img src="photo.jpg">'

    result_mixed2 = rewrite_html_tag_attr(html_mixed2, "img", "src", add_single_quotes)
    # Double quotes can contain single quotes without escaping
    assert '''src="image'with'quotes.jpg"''' in result_mixed2

    # Test 5: Complex case with multiple replacements and mixed quotes
    html_complex = dedent(
        """
        <a href="page1.html">Link 1</a>
        <a href='page2.html'>Link 2</a>
        <img src="photo.jpg">
        <img src='image.jpg'>
    """
    )

    def add_query_with_quotes(value: str) -> str | None:
        if value.endswith(".html"):
            return value + "?param=\"value\"&other='test'"
        elif value.endswith(".jpg"):
            return value + '?size="large"'
        return None

    result_complex = rewrite_html_tag_attr(html_complex, "a", "href", add_query_with_quotes)
    # Double quoted attributes should escape double quotes
    assert "href=\"page1.html?param=&quot;value&quot;&other='test'\"" in result_complex
    # Single quoted attributes should escape single quotes
    assert "href='page2.html?param=\"value\"&other=&#39;test&#39;'" in result_complex

    result_img = rewrite_html_tag_attr(result_complex, "img", "src", add_query_with_quotes)
    assert 'src="photo.jpg?size=&quot;large&quot;"' in result_img
    assert "src='image.jpg?size=\"large\"'" in result_img


def test_rewrite_html_tag_attr_quote_escaping_edge_cases() -> None:
    """Test edge cases for quote escaping."""

    # Test with HTML entities already in the value
    html = '<img src="photo.jpg">'

    def add_entities(value: str) -> str | None:
        return value + "?text=&lt;tag&gt;&amp;&quot;test&quot;"

    result = rewrite_html_tag_attr(html, "img", "src", add_entities)
    # Should double-escape the quotes but leave other entities alone
    assert "?text=&lt;tag&gt;&amp;&quot;test&quot;" in result

    # Test with backslashes and quotes
    def add_backslash_quotes(value: str) -> str | None:
        return value + r'?path=C:\Users\"John"'

    result2 = rewrite_html_tag_attr(html, "img", "src", add_backslash_quotes)
    assert r"C:\Users\&quot;John&quot;" in result2


def test_rewrite_html_img_urls_prefix() -> None:
    """Test rewriting image URLs with prefix replacement."""
    # Simple image
    html = '<img src="./images/photo.jpg">'
    result = rewrite_html_img_urls(html, from_prefix="./images/", to_prefix="/static/")
    assert "/static/photo.jpg" in result
    assert "./images/photo.jpg" not in result

    # Multiple images
    html = dedent(
        """
        <div>
            <img src="./images/photo1.jpg" alt="Photo 1">
            <img src="./images/photo2.png">
            <img src="/other/image.gif">
        </div>
    """
    )
    result = rewrite_html_img_urls(html, from_prefix="./images/", to_prefix="/static/")
    assert "/static/photo1.jpg" in result
    assert "/static/photo2.png" in result
    assert "/other/image.gif" in result  # Unchanged

    # No matching prefix
    html = '<img src="/already/absolute.jpg">'
    result = rewrite_html_img_urls(html, from_prefix="./images/", to_prefix="/static/")
    assert "/already/absolute.jpg" in result

    # Empty HTML
    result = rewrite_html_img_urls("", from_prefix="./", to_prefix="/")
    assert result == ""  # Empty input returns empty output

    # HTML with no images
    html = "<div><p>No images here</p></div>"
    result = rewrite_html_img_urls(html, from_prefix="./", to_prefix="/")
    assert "No images here" in result


def test_rewrite_html_img_urls_custom_rewriter() -> None:
    """Test with custom URL rewriter function."""

    def cdn_rewriter(url: str) -> str | None:
        if url.startswith("./"):
            return f"https://cdn.example.com/{url[2:]}"
        return None

    html = '<img src="./photo.jpg"><img src="/absolute.jpg">'
    result = rewrite_html_img_urls(html, url_rewriter=cdn_rewriter)
    assert "https://cdn.example.com/photo.jpg" in result
    assert "/absolute.jpg" in result  # Unchanged


def test_rewrite_html_img_urls_complex_html() -> None:
    """Test with complex HTML containing various elements."""
    html = dedent(
        """
        <!DOCTYPE html>
        <html>
        <head>
            <link rel="icon" href="./favicon.ico">
        </head>
        <body>
            <img src="./images/header.jpg" alt="Header">
            <div class="content">
                <p>Some text</p>
                <img src="./images/content.png" />
            </div>
            <footer>
                <img src="./images/footer.gif">
            </footer>
        </body>
        </html>
    """
    )
    result = rewrite_html_img_urls(html, from_prefix="./images/", to_prefix="/static/img/")
    assert "/static/img/header.jpg" in result
    assert "/static/img/content.png" in result
    assert "/static/img/footer.gif" in result
    assert "./favicon.ico" in result  # Link unchanged


def test_rewrite_html_img_urls_edge_cases() -> None:
    """Test edge cases for image URL rewriting."""
    # Image with no src
    html = '<img alt="No source">'
    result = rewrite_html_img_urls(html, from_prefix="./", to_prefix="/")
    assert html == result

    # Unquoted attributes should be handled correctly
    html = "<img src=./photo.jpg>"  # No quotes
    result = rewrite_html_img_urls(html, from_prefix="./", to_prefix="/static/")
    # Should successfully rewrite unquoted attributes
    assert "/static/photo.jpg" in result
    assert "./photo.jpg" not in result


def test_rewrite_html_img_urls_attributes_preserved() -> None:
    """Test that other attributes are preserved during rewriting."""
    html = '<img src="./photo.jpg" alt="My Photo" class="thumbnail" id="img1" data-index="1">'
    result = rewrite_html_img_urls(html, from_prefix="./", to_prefix="/static/")
    assert "/static/photo.jpg" in result
    assert 'alt="My Photo"' in result
    assert 'class="thumbnail"' in result
    assert 'id="img1"' in result
    assert 'data-index="1"' in result


def test_rewrite_html_img_urls_mixed_quotes() -> None:
    """Test handling of mixed quote styles."""
    html = """<img src="./photo1.jpg" alt='First'><img src='./photo2.jpg' alt="Second">"""
    result = rewrite_html_img_urls(html, from_prefix="./", to_prefix="/images/")
    assert '"/images/photo1.jpg"' in result
    assert "'/images/photo2.jpg'" in result


def test_rewrite_html_img_urls_invalid_args() -> None:
    """Test error handling for invalid arguments."""
    with pytest.raises(ValueError):
        rewrite_html_img_urls("<img>", from_prefix="./")  # Missing to_prefix

    with pytest.raises(ValueError):
        rewrite_html_img_urls("<img>", to_prefix="/")  # Missing from_prefix

    # Should work with url_rewriter
    result = rewrite_html_img_urls("<img>", url_rewriter=lambda x: x)
    assert result == "<img>"


def test_html_find_tag_basic() -> None:
    """Test basic tag finding functionality."""
    html = "<div>Hello</div><p>World</p><span>Test</span>"

    # Find all tags
    matches = html_find_tag(html)
    assert len(matches) == 3

    # Find specific tag
    div_matches = html_find_tag(html, tag_name="div")
    assert len(div_matches) == 1
    assert div_matches[0].tag_name == "div"
    assert div_matches[0].inner_text == "Hello"

    # Find by attribute
    html2 = '<div id="main">Content</div><div class="sidebar">Side</div>'
    id_matches = html_find_tag(html2, attr_name="id")
    assert len(id_matches) == 1
    assert id_matches[0].attribute_value == "main"

    # Find by attribute value
    html3 = '<div class="box">A</div><div class="sidebar">B</div><div class="box">C</div>'
    box_matches = html_find_tag(html3, attr_name="class", attr_value="box")
    assert len(box_matches) == 2


def test_html_find_tag_complex() -> None:
    """Test with complex nested HTML."""
    html = dedent(
        """
        <div class="outer" id="container">
            <p class="text">First paragraph</p>
            <div class="inner">
                <p>Nested paragraph</p>
                <span id="special">Special text</span>
            </div>
            <p class="text">Last paragraph</p>
        </div>
    """
    ).strip()

    # Find all p tags
    p_matches = html_find_tag(html, tag_name="p")
    assert len(p_matches) == 3

    # Find tags with class attribute
    class_matches = html_find_tag(html, attr_name="class")
    assert len(class_matches) >= 4  # outer, inner, and at least 2 p.text

    # Find specific class value
    text_matches = html_find_tag(html, tag_name="p", attr_name="class", attr_value="text")
    assert len(text_matches) == 2


def test_html_extract_attribute_value() -> None:
    """Test html_extract_attribute_value function."""
    extractor = html_extract_attribute_value("href")

    # Simple case
    html = '<a href="/page.html">Link</a>'
    assert extractor(html) == "/page.html"

    # Multiple elements, returns first
    html = '<div><a href="/first.html">First</a><a href="/second.html">Second</a></div>'
    assert extractor(html) == "/first.html"

    # No matching attribute
    html = "<div>No links here</div>"
    assert extractor(html) is None

    # Different attribute
    src_extractor = html_extract_attribute_value("src")
    html = '<img src="/image.jpg">'
    assert src_extractor(html) == "/image.jpg"


def test_html_find_tag_edge_cases() -> None:
    """Test edge cases for tag finding."""
    # Empty HTML
    matches = html_find_tag("")
    assert len(matches) == 0

    # Self-closing tags
    html = '<br><img src="test.jpg"><input type="text">'
    matches = html_find_tag(html)
    assert len(matches) == 3

    # Malformed HTML (unclosed tags)
    html = "<div>Unclosed<p>Paragraph"
    matches = html_find_tag(html)
    # Should handle gracefully
    assert len(matches) >= 0

    # Special characters in attributes
    html = '<div data-test="value with spaces" id="test-id">Content</div>'
    matches = html_find_tag(html, attr_name="data-test")
    assert len(matches) == 1
    assert matches[0].attribute_value == "value with spaces"


def test_html_find_tag_accurate_offsets() -> None:
    """Test the hybrid regex+selectolax approach for accurate offsets with robust parsing."""
    # Test 1: Simple case with exact positions
    html = '<div>Start</div><p id="test">Middle</p><span>End</span>'

    # Find the p tag
    p_matches = html_find_tag(html, tag_name="p")
    assert len(p_matches) == 1
    p_match = p_matches[0]

    # Verify the offsets are correct and native (no regex involved)
    assert p_match.start_offset == html.index('<p id="test">')
    extracted = html[p_match.start_offset : p_match.end_offset]
    assert extracted == '<p id="test">Middle</p>'

    # Test 2: Surgical editing using native offsets
    # Replace just the content of the p tag using exact offsets
    new_content = "REPLACED"
    # Find where "Middle" starts within the p tag
    content_start = html.index(">Middle</p>") + 1
    content_end = content_start + len("Middle")
    modified = html[:content_start] + new_content + html[content_end:]
    assert modified == '<div>Start</div><p id="test">REPLACED</p><span>End</span>'

    # Test 3: Multiple similar tags with accurate positions
    html2 = '<img src="1.jpg"><img src="2.jpg"><img src="3.jpg">'
    img_matches = html_find_tag(html2, tag_name="img")
    assert len(img_matches) == 3

    # Verify each img tag has correct native offsets
    expected_positions = [
        (0, len('<img src="1.jpg">')),
        (len('<img src="1.jpg">'), len('<img src="1.jpg"><img src="2.jpg">')),
        (len('<img src="1.jpg"><img src="2.jpg">'), len(html2)),
    ]

    for i, (match, (expected_start, expected_end)) in enumerate(
        zip(img_matches, expected_positions, strict=True), 1
    ):
        assert match.start_offset == expected_start
        assert match.end_offset == expected_end
        extracted = html2[match.start_offset : match.end_offset]
        assert f'src="{i}.jpg"' in extracted
        assert extracted.startswith("<img")
        assert extracted.endswith(">")

    # Test 4: Nested tags with proper offset tracking
    html3 = dedent(
        """
        <div class="outer">
            <p>First</p>
            <div class="inner">
                <p>Second</p>
            </div>
            <p>Third</p>
        </div>
    """
    ).strip()

    # Find all p tags
    p_matches = html_find_tag(html3, tag_name="p")
    assert len(p_matches) == 3

    # Verify native offsets allow exact extraction
    for match in p_matches:
        extracted = html3[match.start_offset : match.end_offset]
        assert extracted.startswith("<p>")
        assert extracted.endswith("</p>")
        # The inner text should match what's between the tags
        assert match.inner_text.strip() in extracted

    # Test 5: Complex attributes with native offset accuracy
    html4 = '<div id="a" class="b" data-value="test">Content</div>'
    div_matches = html_find_tag(html4, tag_name="div", attr_name="id")
    assert len(div_matches) == 1

    # Native offsets should give us the exact element
    extracted = html4[div_matches[0].start_offset : div_matches[0].end_offset]
    assert extracted == html4  # It's the only element
    assert div_matches[0].start_offset == 0
    assert div_matches[0].end_offset == len(html4)

    # Test 6: Self-closing tags
    html5 = '<br/><img src="test.jpg"/><input type="text"/>'

    br_matches = html_find_tag(html5, tag_name="br")
    assert len(br_matches) == 1
    assert html5[br_matches[0].start_offset : br_matches[0].end_offset] == "<br/>"

    img_matches = html_find_tag(html5, tag_name="img")
    assert len(img_matches) == 1
    assert html5[img_matches[0].start_offset : img_matches[0].end_offset] == '<img src="test.jpg"/>'

    input_matches = html_find_tag(html5, tag_name="input")
    assert len(input_matches) == 1
    assert (
        html5[input_matches[0].start_offset : input_matches[0].end_offset] == '<input type="text"/>'
    )


def test_html_find_tag_offset_advantages() -> None:
    """Demonstrate advantages of the hybrid regex+selectolax approach."""
    # Complex HTML that would be challenging for regex
    html = """
    <div class="container" id='main' data-info="complex value with = and quotes">
        <p class="text">Paragraph with <b>nested <i>formatting</i></b></p>
        <img src="image.jpg" alt='Single quotes' class="img-responsive">
        <a href="/page?param=value&other=123" title="Link & special chars">Link</a>
    </div>
    """

    # Find all elements - resiliparse handles this cleanly
    all_matches = html_find_tag(html)

    # Each match should have accurate native offsets
    for match in all_matches:
        extracted = html[match.start_offset : match.end_offset]
        # Should be a valid HTML element
        assert extracted.lstrip().startswith("<")
        assert extracted.rstrip().endswith(">")

    # Find specific elements with complex attributes
    div_matches = html_find_tag(html, tag_name="div", attr_name="data-info")
    assert len(div_matches) == 1

    # The offset should capture the entire div including all its contents
    extracted_div = html[div_matches[0].start_offset : div_matches[0].end_offset]
    assert "complex value with = and quotes" in extracted_div
    assert "</div>" in extracted_div

    # Find links with query parameters
    a_matches = html_find_tag(html, tag_name="a")
    assert len(a_matches) == 1

    extracted_link = html[a_matches[0].start_offset : a_matches[0].end_offset]
    assert "param=value&other=123" in extracted_link
    assert "Link & special chars" in extracted_link


def test_html_find_tag_nested_elements() -> None:
    """Test finding tags with nested elements of the same type."""
    # Nested divs
    html = '<div id="outer">Outer <div id="inner">Inner</div> content</div>'
    matches = html_find_tag(html, tag_name="div", attr_name="id")
    assert len(matches) == 2

    # The outer div should include everything
    outer_match = [m for m in matches if m.attribute_value == "outer"][0]
    assert (
        html[outer_match.start_offset : outer_match.end_offset]
        == '<div id="outer">Outer <div id="inner">Inner</div> content</div>'
    )

    # The inner div should only include its content
    inner_match = [m for m in matches if m.attribute_value == "inner"][0]
    assert html[inner_match.start_offset : inner_match.end_offset] == '<div id="inner">Inner</div>'

    # Deeply nested divs
    html = "<div>1<div>2<div>3</div>2</div>1</div>"
    matches = html_find_tag(html, tag_name="div")
    assert len(matches) == 3


def test_html_find_tag_self_closing_with_whitespace() -> None:
    """Test finding self-closing tags with various whitespace patterns."""
    # Different self-closing formats
    test_cases = [
        "<br/>",
        "<br />",
        "<br  />",
        "<br / >",
        '<img src="test.jpg"/>',
        '<img src="test.jpg" />',
        '<img src="test.jpg"  />',
        '<input type="text" / >',
    ]

    for html in test_cases:
        matches = html_find_tag(html)
        assert len(matches) == 1, f"Failed to find tag in: {html}"
        assert matches[0].start_offset == 0
        assert matches[0].end_offset == len(html)


def test_html_find_tag_closing_tag_whitespace() -> None:
    """Test handling of closing tags with whitespace."""
    # Closing tags with whitespace
    test_cases = [
        ("<div>content</div>", "content"),
        ("<div>content< /div>", "content"),
        ("<div>content<  /div>", "content"),
        ("<div>content< / div>", "content"),
        ("<div>content<  /  div>", "content"),
    ]

    for html, expected_text in test_cases:
        matches = html_find_tag(html, tag_name="div")
        assert len(matches) == 1, f"Failed to find tag in: {html}"
        assert matches[0].start_offset == 0
        assert matches[0].end_offset == len(html)
        assert expected_text in matches[0].inner_text


def test_html_find_tag_mixed_nested_and_self_closing() -> None:
    """Test mixed nested elements and self-closing tags."""
    html = '<div><img src="1.jpg"/><div><br />text</div><img src="2.jpg" /></div>'

    # Find all tags
    all_matches = html_find_tag(html)
    assert len(all_matches) == 5  # outer div, img, inner div, br, img

    # Find only divs
    div_matches = html_find_tag(html, tag_name="div")
    assert len(div_matches) == 2

    # Find only imgs
    img_matches = html_find_tag(html, tag_name="img")
    assert len(img_matches) == 2
    for match in img_matches:
        # Verify they are treated as self-closing
        assert "/>" in html[match.start_offset : match.end_offset]


def test_html_find_tag_ignores_comments() -> None:
    """Test that tags inside HTML comments are ignored."""
    # Simple comment with tag inside
    html = '<!-- <img src="commented.jpg"> --><img src="real.jpg">'
    matches = html_find_tag(html, tag_name="img", attr_name="src")
    assert len(matches) == 1
    assert matches[0].attribute_value == "real.jpg"

    # Multiple comments
    html = dedent(
        """
        <!-- <div id="commented">Should be ignored</div> -->
        <div id="real">Real content</div>
        <!-- Another comment with <p>tag</p> -->
        <p>Real paragraph</p>
        """
    )
    div_matches = html_find_tag(html, tag_name="div", attr_name="id")
    assert len(div_matches) == 1
    assert div_matches[0].attribute_value == "real"

    p_matches = html_find_tag(html, tag_name="p")
    assert len(p_matches) == 1
    assert p_matches[0].inner_text == "Real paragraph"

    # Comment in the middle of content
    html = "<div>Before <!-- <span>commented</span> --> After</div>"
    span_matches = html_find_tag(html, tag_name="span")
    assert len(span_matches) == 0

    # Nested comments (not valid HTML but should handle gracefully)
    html = '<!-- outer <!-- inner <img src="nested.jpg"> --> --><img src="real.jpg">'
    img_matches = html_find_tag(html, tag_name="img", attr_name="src")
    assert len(img_matches) == 1
    assert img_matches[0].attribute_value == "real.jpg"


def test_rewrite_html_tag_attr_ignores_comments() -> None:
    """Test that rewrite functions ignore tags inside HTML comments."""
    # Image in comment should not be rewritten
    html = '<!-- <img src="./commented.jpg"> --><img src="./real.jpg">'
    result = rewrite_html_img_urls(html, from_prefix="./", to_prefix="/static/")
    assert "./commented.jpg" in result  # Should remain unchanged in comment
    assert "/static/real.jpg" in result  # Should be rewritten
    assert '<!-- <img src="./commented.jpg"> -->' in result

    # Multiple tags with comments
    html = dedent(
        """
        <!-- Commented out old code
        <img src="./old/photo1.jpg">
        <img src="./old/photo2.jpg">
        -->
        <img src="./new/photo.jpg">
        """
    )
    result = rewrite_html_img_urls(html, from_prefix="./", to_prefix="/cdn/")
    assert "./old/photo1.jpg" in result  # Should remain unchanged
    assert "./old/photo2.jpg" in result  # Should remain unchanged
    assert "/cdn/new/photo.jpg" in result  # Should be rewritten

    # Link rewriting with comments
    html = '<!-- <a href="./old.html">Old</a> --><a href="./new.html">New</a>'
    result = rewrite_html_tag_attr(html, "a", "href", from_prefix="./", to_prefix="/pages/")
    assert "./old.html" in result  # Should remain unchanged in comment
    assert "/pages/new.html" in result  # Should be rewritten


def test_html_find_tag_unquoted_attributes() -> None:
    """Test finding tags with unquoted attribute values."""
    # Simple unquoted attribute
    html = "<img src=photo.jpg>"
    matches = html_find_tag(html, tag_name="img", attr_name="src")
    assert len(matches) == 1
    assert matches[0].attribute_value == "photo.jpg"

    # Multiple unquoted attributes
    html = "<img src=photo.jpg width=100 height=200>"
    matches = html_find_tag(html, tag_name="img")
    assert len(matches) == 1

    # Mixed quoted and unquoted
    html = '<img src="quoted.jpg" width=100>'
    matches = html_find_tag(html, tag_name="img", attr_name="src")
    assert len(matches) == 1
    assert matches[0].attribute_value == "quoted.jpg"

    # Unquoted with path
    html = "<img src=./images/photo.jpg>"
    matches = html_find_tag(html, tag_name="img", attr_name="src")
    assert len(matches) == 1
    assert matches[0].attribute_value == "./images/photo.jpg"

    # Unquoted attribute value ending at tag close
    html = "<a href=page.html>Link</a>"
    matches = html_find_tag(html, tag_name="a", attr_name="href")
    assert len(matches) == 1
    assert matches[0].attribute_value == "page.html"


def test_rewrite_html_tag_attr_unquoted_attributes() -> None:
    """Test rewriting unquoted attribute values."""
    # Simple unquoted src
    html = "<img src=./photo.jpg>"
    result = rewrite_html_img_urls(html, from_prefix="./", to_prefix="/static/")
    assert "<img src=/static/photo.jpg>" in result or '<img src="/static/photo.jpg">' in result

    # Unquoted href
    html = "<a href=./page.html>Link</a>"
    result = rewrite_html_tag_attr(html, "a", "href", from_prefix="./", to_prefix="/")
    assert "<a href=/page.html>" in result or '<a href="/page.html">' in result

    # Mixed quoted and unquoted in same document
    html = '<img src="./quoted.jpg"><img src=./unquoted.jpg>'
    result = rewrite_html_img_urls(html, from_prefix="./", to_prefix="/cdn/")
    assert '"/cdn/quoted.jpg"' in result
    assert "/cdn/unquoted.jpg" in result

    # Unquoted with spaces after (should stop at space)
    html = "<img src=photo.jpg alt=Photo>"
    result = rewrite_html_img_urls(html, from_prefix="photo", to_prefix="/images/photo")
    assert "/images/photo.jpg" in result
