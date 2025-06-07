"""
Formatting of Markdown with a small set of known HTML classes. We do this directly
ourselves to keep the HTML very minimal, control whitespace, and to avoid any
confusions of using full HTML escaping (like unnecessary &quot;s etc.)

Perhaps worth using FastHTML for this?
"""

import re
from collections.abc import Callable
from typing import TypeAlias


def escape_md_html(s: str, safe: bool = False) -> str:
    """
    Escape a string for Markdown with HTML. Don't escape single and double quotes.
    """
    if safe:
        return s
    s = s.replace("&", "&amp;")
    s = s.replace("<", "&lt;")
    s = s.replace(">", "&gt;")
    return s


def escape_attribute(s: str) -> str:
    """
    Escape a string for use as an HTML attribute. Escape single and double quotes.
    """
    s = escape_md_html(s)
    s = s.replace('"', "&quot;")
    s = s.replace("'", "&#39;")
    return s


ClassNames = str | list[str] | None
Attrs = dict[str, str | bool]

_TAGS_WITH_PADDING = ["div", "p"]


def tag_with_attrs(
    tag: str,
    text: str | None,
    class_name: ClassNames = None,
    *,
    attrs: Attrs | None = None,
    safe: bool = False,
    padding: str | None = None,
) -> str:
    """
    Create an HTML tag with optional class names and attributes.
    Boolean attribute values: True includes the attribute, False omits it.
    """
    class_value = ""
    if class_name is not None:
        if isinstance(class_name, str):
            class_value = class_name.strip()
        else:  # list[str]
            # Filter out empty strings and join
            filtered_classes = [cls for cls in class_name if cls.strip()]
            class_value = " ".join(filtered_classes)

    attr_str = f' class="{escape_attribute(class_value)}"' if class_value else ""
    if attrs:
        for k, v in attrs.items():
            if isinstance(v, bool):
                if v:  # Only include attribute if True
                    attr_str += f" {k}"
            else:  # string value
                attr_str += f' {k}="{escape_attribute(v)}"'
    # Default padding for div and p tags.
    if text is None:
        return f"<{tag}{attr_str} />"
    else:
        content = escape_md_html(text, safe)
        if padding is None:
            padding = "\n" if tag in _TAGS_WITH_PADDING else ""
        if padding:
            content = content.strip("\n")
            if not content:
                padding = ""
        return f"<{tag}{attr_str}>{padding}{content}{padding}</{tag}>"


def html_span(
    text: str,
    class_name: ClassNames = None,
    *,
    attrs: Attrs | None = None,
    safe: bool = False,
) -> str:
    """
    Write a span tag for use in Markdown, with the given text and optional class and attributes.
    """
    return tag_with_attrs("span", text, class_name, attrs=attrs, safe=safe)


def html_div(
    text: str,
    class_name: ClassNames = None,
    *,
    attrs: Attrs | None = None,
    safe: bool = False,
    padding: str | None = None,
) -> str:
    """
    Write a div tag for use in Markdown, with the given text and optional class and attributes.
    """
    return tag_with_attrs("div", text, class_name, attrs=attrs, safe=safe, padding=padding)


def html_a(
    text: str,
    href: str,
    class_name: ClassNames = None,
    *,
    attrs: Attrs | None = None,
    safe: bool = False,
) -> str:
    """
    Write an anchor tag with href, optional class and attributes.
    """
    link_attrs: Attrs = {"href": href}
    if attrs:
        link_attrs.update(attrs)
    return tag_with_attrs("a", text, class_name, attrs=link_attrs, safe=safe)


def html_b(
    text: str,
    class_name: ClassNames = None,
    *,
    attrs: Attrs | None = None,
    safe: bool = False,
) -> str:
    """
    Write a bold tag with optional class and attributes.
    """
    return tag_with_attrs("b", text, class_name, attrs=attrs, safe=safe)


def html_i(
    text: str,
    class_name: ClassNames = None,
    *,
    attrs: Attrs | None = None,
    safe: bool = False,
) -> str:
    """
    Write an italic tag with optional class and attributes.
    """
    return tag_with_attrs("i", text, class_name, attrs=attrs, safe=safe)


def html_img(
    src: str,
    alt: str,
    class_name: ClassNames = None,
    *,
    attrs: Attrs | None = None,
    safe: bool = False,
) -> str:
    img_attrs: Attrs = {"src": src, "alt": alt}
    if attrs:
        for k, v in attrs.items():
            img_attrs[k] = v
    return tag_with_attrs("img", None, class_name, attrs=img_attrs, safe=safe)


def html_join_blocks(*blocks: str | None) -> str:
    """
    Join block elements, with double newlines for better Markdown compatibility.
    Ignore empty strings or None.
    """
    return "\n\n".join(block.strip("\n") for block in blocks if block)


def md_para(text: str) -> str:
    """
    Add double newlines to the start and end of the text to make it a paragraph.
    """
    return "\n\n".join(text.split("\n"))


Wrapper: TypeAlias = Callable[[str], str]
"""Wraps a string to identify it in some way."""


def identity_wrapper(text: str) -> str:
    return text


def _check_class_name(class_name: ClassNames) -> None:
    if class_name:
        if isinstance(class_name, str):
            # Allow modern CSS class naming including BEM notation (block__element--modifier)
            if class_name.strip() and not re.match(r"^[a-zA-Z_][\w_-]*$", class_name):
                raise ValueError(f"Expected a valid CSS class name but got: '{class_name}'")
        else:  # list[str]
            for cls in class_name:
                if cls.strip() and not re.match(r"^[a-zA-Z_][\w_-]*$", cls):
                    raise ValueError(f"Expected a valid CSS class name but got: '{cls}'")


def html_p(
    text: str,
    class_name: ClassNames = None,
    *,
    attrs: Attrs | None = None,
    safe: bool = False,
    padding: str | None = None,
) -> str:
    """
    Write a p tag for use in Markdown, with the given text and optional class and attributes.
    """
    return tag_with_attrs("p", text, class_name, attrs=attrs, safe=safe, padding=padding)


def html_tag(
    tag: str,
    text: str | None = None,
    class_name: ClassNames = None,
    *,
    attrs: Attrs | None = None,
    safe: bool = False,
    padding: str | None = None,
) -> str:
    """
    Generic function to create any HTML tag with optional class and attributes.
    """
    return tag_with_attrs(tag, text, class_name, attrs=attrs, safe=safe, padding=padding)


def div_wrapper(
    class_name: ClassNames = None,
    *,
    attrs: Attrs | None = None,
    safe: bool = True,
    padding: str | None = "\n\n",
) -> Wrapper:
    _check_class_name(class_name)

    def div_wrapper_func(text: str) -> str:
        return html_div(text, class_name, attrs=attrs, safe=safe, padding=padding)

    return div_wrapper_func


def span_wrapper(
    class_name: ClassNames = None,
    *,
    attrs: Attrs | None = None,
    safe: bool = True,
) -> Wrapper:
    _check_class_name(class_name)

    def span_wrapper_func(text: str) -> str:
        return html_span(text, class_name, attrs=attrs, safe=safe)

    return span_wrapper_func


def tag_wrapper(
    tag: str,
    class_name: ClassNames = None,
    *,
    attrs: Attrs | None = None,
    safe: bool = True,
    padding: str | None = None,
) -> Wrapper:
    """
    Generic wrapper factory for any HTML tag.
    """
    _check_class_name(class_name)

    def tag_wrapper_func(text: str) -> str:
        return html_tag(tag, text, class_name, attrs=attrs, safe=safe, padding=padding)

    return tag_wrapper_func


## Tests


def test_html():
    assert escape_md_html("&<>") == "&amp;&lt;&gt;"
    assert escape_attribute("\"'&<>") == "&quot;&#39;&amp;&lt;&gt;"
    assert (
        tag_with_attrs("span", "text", class_name="foo", attrs={"id": "a"})
        == '<span class="foo" id="a">text</span>'
    )
    assert (
        html_span("text", class_name="foo", attrs={"id": "a"})
        == '<span class="foo" id="a">text</span>'
    )
    assert (
        html_div("text 1<2", class_name="foo", attrs={"id": "a"})
        == '<div class="foo" id="a">\ntext 1&lt;2\n</div>'
    )
    assert html_div("text") == "<div>\ntext\n</div>"


def test_boolean_attrs():
    assert tag_with_attrs("input", None, attrs={"disabled": True}) == "<input disabled />"
    assert tag_with_attrs("input", None, attrs={"disabled": False}) == "<input />"
    assert (
        tag_with_attrs("input", None, attrs={"disabled": True, "required": True, "id": "test"})
        == '<input disabled required id="test" />'
    )
    assert (
        tag_with_attrs("input", None, attrs={"disabled": False, "required": True})
        == "<input required />"
    )


def test_class_names():
    assert (
        tag_with_attrs("div", "text", class_name=["foo", "bar"])
        == '<div class="foo bar">\ntext\n</div>'
    )
    assert tag_with_attrs("span", "text", class_name="single") == '<span class="single">text</span>'
    assert tag_with_attrs("span", "text", class_name=None) == "<span>text</span>"
    assert tag_with_attrs("span", "text", class_name=[]) == "<span>text</span>"
    assert tag_with_attrs("span", "text", class_name="") == "<span>text</span>"
    assert tag_with_attrs("span", "text", class_name=["", ""]) == "<span>text</span>"
    assert (
        tag_with_attrs("span", "text", class_name=["foo", "", "bar"])
        == '<span class="foo bar">text</span>'
    )


def test_padding():
    assert tag_with_attrs("span", "text") == "<span>text</span>"
    assert tag_with_attrs("div", "text") == "<div>\ntext\n</div>"
    assert tag_with_attrs("p", "text") == "<p>\ntext\n</p>"
    assert tag_with_attrs("div", "text", padding="") == "<div>text</div>"
    assert tag_with_attrs("div", "", padding="\n") == "<div></div>"


def test_safe_mode():
    assert tag_with_attrs("div", "<script>", safe=True) == "<div>\n<script>\n</div>"
    assert tag_with_attrs("div", "<script>", safe=False) == "<div>\n&lt;script&gt;\n</div>"


def test_html_functions():
    assert html_a("link", "http://example.com") == '<a href="http://example.com">link</a>'
    assert (
        html_a("link", "http://example.com", class_name="external")
        == '<a class="external" href="http://example.com">link</a>'
    )
    assert (
        html_a("link", "http://example.com", attrs={"target": "_blank"})
        == '<a href="http://example.com" target="_blank">link</a>'
    )

    assert html_b("bold") == "<b>bold</b>"
    assert html_b("bold", class_name="emphasis") == '<b class="emphasis">bold</b>'

    assert html_i("italic") == "<i>italic</i>"
    assert html_i("italic", attrs={"title": "emphasis"}) == '<i title="emphasis">italic</i>'

    assert html_p("paragraph") == "<p>\nparagraph\n</p>"
    assert html_p("paragraph", class_name="intro") == '<p class="intro">\nparagraph\n</p>'

    assert html_img("pic.jpg", "A picture") == '<img src="pic.jpg" alt="A picture" />'
    assert (
        html_img("pic.jpg", "A picture", attrs={"loading": "lazy"})
        == '<img src="pic.jpg" alt="A picture" loading="lazy" />'
    )


def test_html_tag():
    assert html_tag("section", "content") == "<section>content</section>"
    assert (
        html_tag("section", "content", class_name="main")
        == '<section class="main">content</section>'
    )
    assert html_tag("hr", None) == "<hr />"
    assert html_tag("article", "text", padding="\n") == "<article>\ntext\n</article>"


def test_html_join_blocks():
    assert html_join_blocks("block1", "block2") == "block1\n\nblock2"
    assert html_join_blocks("block1", None, "block2") == "block1\n\nblock2"
    assert html_join_blocks("", "block2") == "block2"


def test_div_wrapper():
    safe_wrapper = div_wrapper(class_name="foo")
    assert safe_wrapper("<div>text</div>") == '<div class="foo">\n\n<div>text</div>\n\n</div>'

    unsafe_wrapper = div_wrapper(class_name="foo", safe=False)
    assert (
        unsafe_wrapper("<div>text</div>")
        == '<div class="foo">\n\n&lt;div&gt;text&lt;/div&gt;\n\n</div>'
    )

    bool_wrapper = div_wrapper(attrs={"hidden": True})
    assert bool_wrapper("content") == "<div hidden>\n\ncontent\n\n</div>"

    list_wrapper = div_wrapper(class_name=["foo", "bar"])
    assert list_wrapper("content") == '<div class="foo bar">\n\ncontent\n\n</div>'

    empty_wrapper = div_wrapper(class_name=[])
    assert empty_wrapper("content") == "<div>\n\ncontent\n\n</div>"

    empty_str_wrapper = div_wrapper(class_name="")
    assert empty_str_wrapper("content") == "<div>\n\ncontent\n\n</div>"


def test_span_wrapper():
    wrapper = span_wrapper(class_name="highlight", attrs={"data-id": "123"})
    assert wrapper("text") == '<span class="highlight" data-id="123">text</span>'

    list_wrapper = span_wrapper(class_name=["highlight", "bold"])
    assert list_wrapper("text") == '<span class="highlight bold">text</span>'

    empty_wrapper = span_wrapper(class_name=[])
    assert empty_wrapper("text") == "<span>text</span>"

    empty_str_wrapper = span_wrapper(class_name="")
    assert empty_str_wrapper("text") == "<span>text</span>"


def test_check_class_name():
    # Valid single class names
    _check_class_name("foo")
    _check_class_name("foo-bar")
    _check_class_name("_private")
    _check_class_name("block__element--modifier")  # BEM notation
    _check_class_name(None)

    # Valid list of class names
    _check_class_name(["foo", "bar"])
    _check_class_name(["foo-bar", "_private"])

    # Empty list should be valid (no class name)
    _check_class_name([])

    # Empty string should be valid (no class name)
    _check_class_name("")

    # Invalid class names should raise
    try:
        _check_class_name("123invalid")
        raise AssertionError("Should have raised")
    except ValueError:
        pass

    try:
        _check_class_name(["valid", "123invalid"])
        raise AssertionError("Should have raised")
    except ValueError:
        pass


def test_tag_wrapper():
    section_wrapper = tag_wrapper("section", class_name="content")
    assert section_wrapper("text") == '<section class="content">text</section>'

    header_wrapper = tag_wrapper("header", padding="\n")
    assert header_wrapper("title") == "<header>\ntitle\n</header>"

    # Test with empty content
    empty_wrapper = tag_wrapper("div")
    assert empty_wrapper("") == "<div></div>"
