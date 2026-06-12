from chopdiff.divs.parse_divs import parse_divs


def test_parsed_div_multi_class_matching():
    # A div whose class list includes "chunk" matches children_by_class_names("chunk"),
    # and single-quoted class attributes are parsed.
    text = "<div class='chunk selected'>one</div>\n\n<div class=\"chunk\">two</div>"
    root = parse_divs(text)
    matched = root.children_by_class_names("chunk")
    assert len(matched) == 2
