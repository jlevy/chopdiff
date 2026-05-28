from textwrap import dedent

from chopdiff.docs.block_tree import Block
from chopdiff.docs.block_types import BlockType
from chopdiff.docs.text_doc import TextDoc

_DOC = dedent(
    """
    # Title

    Intro paragraph here.

    - item one
    - item two
      - nested a
      - nested b
    - item three

    ```python
    x = 1

    y = 2
    ```

    | a | b |
    | - | - |
    | 1 | 2 |

    ---
    """
).strip()


def _types(blocks: list[Block]) -> list[BlockType]:
    return [b.type for b in blocks]


def test_top_level_block_types():
    doc = TextDoc.from_text(_DOC)
    assert _types(doc.blocks()) == [
        BlockType.heading,
        BlockType.paragraph,
        BlockType.list,
        BlockType.code,
        BlockType.table,
        BlockType.thematic_break,
    ]


def test_all_block_spans_round_trip():
    doc = TextDoc.from_text(_DOC)

    def check(blocks: list[Block]) -> None:
        for b in blocks:
            start, end = b.span
            assert _DOC[start:end] == _DOC[start:end].strip()  # span is trimmed
            assert end > start
            check(b.children)

    check(doc.blocks())


def test_fenced_code_with_blank_line_is_one_block():
    doc = TextDoc.from_text(_DOC)
    code = next(b for b in doc.blocks() if b.type == BlockType.code)
    code_src = _DOC[code.span[0] : code.span[1]]
    assert code_src.count("```") == 2  # whole fence kept together
    assert "x = 1" in code_src and "y = 2" in code_src


def test_tight_list_decomposes_into_items_with_nesting():
    doc = TextDoc.from_text(_DOC)
    lst = next(b for b in doc.blocks() if b.type == BlockType.list)
    items = lst.children
    assert all(c.type == BlockType.list_item for c in items)
    assert len(items) == 3
    # item two contains a nested list of two items
    nested = [c for c in items[1].children if c.type == BlockType.list]
    assert len(nested) == 1
    assert len(nested[0].children) == 2
    # each item's span round-trips and starts at its marker
    for item in items:
        assert _DOC[item.span[0] : item.span[1]].lstrip().startswith(("-", "*", "+"))


def test_blocks_top_level_structure_matches_marko():
    # Cross-check the top-level block count against marko (ignoring blank lines).
    from flowmark import flowmark_markdown
    from marko.block import BlankLine

    parsed = flowmark_markdown().parse(_DOC)
    marko_top = [c for c in parsed.children if not isinstance(c, BlankLine)]
    assert len(TextDoc.from_text(_DOC).blocks()) == len(marko_top)


def test_no_source_text_falls_back_to_reassembled():
    doc = TextDoc.from_wordtoks(list(TextDoc.from_text("A para. Two.").as_wordtoks()))
    # Still parses (uses reassembled text as the backing source).
    assert _types(doc.blocks()) == [BlockType.paragraph]


def test_heading_then_paragraph_without_blank_line():
    # ATX heading immediately followed by a paragraph (no blank line between) must
    # split into two distinct blocks, not one heading-classified region.
    text = "# Title\nParagraph immediately after.\n\n## Next\nBody."
    doc = TextDoc.from_text(text)
    assert _types(doc.blocks()) == [
        BlockType.heading,
        BlockType.paragraph,
        BlockType.heading,
        BlockType.paragraph,
    ]


def test_paragraph_then_heading_without_blank_line():
    text = "Some paragraph text.\n# Heading"
    doc = TextDoc.from_text(text)
    assert _types(doc.blocks()) == [BlockType.paragraph, BlockType.heading]


def test_paragraph_then_thematic_break_without_blank_line():
    text = "Some paragraph.\n---"
    doc = TextDoc.from_text(text)
    # CommonMark: a `---` right after a paragraph is a setext H2, not a thematic break.
    # Just ensure we agree with marko's call (it's one block).
    from marko.block import BlankLine

    from chopdiff.docs.block_types import markdown_parser

    parsed = markdown_parser().parse(text)
    marko_top = [c for c in parsed.children if not isinstance(c, BlankLine)]
    assert len(doc.blocks()) == len(marko_top)


def test_block_types_parity_with_marko_for_no_blank_transitions():
    # The structural block tree must agree with marko's top-level block count for
    # documents where blocks are adjacent without blank-line separators.
    from marko.block import BlankLine

    from chopdiff.docs.block_types import markdown_parser

    cases = [
        "# H1\nPara after.",
        "Para before.\n# H1",
        "# H1\n# H2",
        "# H1\n## H2\n### H3",
        "Para before fence.\n```\ncode\n```",
        "```\ncode\n```\nPara after fence.",
        "Para before break.\n\n***\n\nPara after break.",
    ]
    for text in cases:
        parsed = markdown_parser().parse(text)
        marko_top = [c for c in parsed.children if not isinstance(c, BlankLine)]
        ours = TextDoc.from_text(text).blocks()
        assert len(ours) == len(marko_top), f"block count mismatch on: {text!r}"
