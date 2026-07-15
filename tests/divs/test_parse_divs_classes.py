from chopdiff.divs.parse_divs import parse_divs


def test_parsed_div_multi_class_matching():
    # A div whose class list includes "chunk" matches children_by_class_names("chunk"),
    # and single-quoted class attributes are parsed.
    text = "<div class='chunk selected'>one</div>\n\n<div class=\"chunk\">two</div>"
    root = parse_divs(text)
    matched = root.children_by_class_names("chunk")
    assert len(matched) == 2


def test_reassemble_without_padding_preserves_original_div_tags():
    text = (
        '<div id="outer" class="chunk selected" data-kind="demo">'
        "<div class='content'>one</div>"
        "</div>"
    )

    assert parse_divs(text, skip_whitespace=False).reassemble(padding="") == text
