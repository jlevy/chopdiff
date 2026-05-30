from collections.abc import Callable

from chopdiff.divs.parse_divs import parse_divs
from chopdiff.html.html_in_md import tag_with_attrs


def _raises_value_error(fn: Callable[[], object]) -> bool:
    try:
        fn()
        return False
    except ValueError:
        return True


def test_tag_with_attrs_validates_names():
    # Valid names still work, including hyphenated attributes and custom elements.
    assert tag_with_attrs("span", "x", attrs={"data-id": "1"}) == '<span data-id="1">x</span>'
    # Injection-shaped tag name and malformed attribute name are rejected.
    assert _raises_value_error(lambda: tag_with_attrs("span onmouseover=alert(1)", "x"))
    assert _raises_value_error(lambda: tag_with_attrs("span", "x", attrs={"bad attr": "y"}))


def test_parsed_div_multi_class_matching():
    # A div whose class list includes "chunk" matches children_by_class_names("chunk"),
    # and single-quoted class attributes are parsed.
    text = "<div class='chunk selected'>one</div>\n\n<div class=\"chunk\">two</div>"
    root = parse_divs(text)
    matched = root.children_by_class_names("chunk")
    assert len(matched) == 2
