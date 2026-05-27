"""
Markdown block classification, shared by `text_doc` (per-paragraph block typing) and
`block_tree` (whole-document structural parsing). Kept in its own module so both can
depend on it without an import cycle.
"""

from __future__ import annotations

from enum import StrEnum
from functools import cache

from flowmark import flowmark_markdown
from marko import Markdown
from marko.block import (
    BlankLine,
    CodeBlock,
    FencedCode,
    Heading,
    HTMLBlock,
    List,
    Quote,
    SetextHeading,
)
from marko.ext.footnote import FootnoteDef
from marko.ext.gfm.elements import Table


class BlockType(StrEnum):
    """
    The kind of Markdown block a `Paragraph` represents, determined by parsing the
    block with flowmark's Markdown (marko) parser. This reuses the same parser
    flowmark uses, so GFM tables, footnote definitions, and fenced code (including
    `#` lines inside code) are recognized correctly.

    `TextDoc` splits a document on blank lines, so each block is one
    blank-line-separated unit, and list handling depends on item spacing:

    - A "tight" list (no blank lines between items) is a single `list` block
      containing every item; nested sublists stay inside that one block.
    - A "loose" list (blank lines between items) yields one `list` block per
      item, and nesting is flattened (each item, parent or child, is its own
      block).
    - A continuation paragraph inside a list item (separated by a blank line) is
      classified as `paragraph`, since on its own it carries no list marker.

    Likewise, a fenced code block containing a blank line can be split across
    blocks. For exact block boundaries, preserved nesting, and reliable
    per-list-item granularity, use the whole-document structural view
    `TextDoc.blocks()` (see `block_tree`).
    """

    paragraph = "paragraph"
    heading = "heading"
    list = "list"
    list_item = "list_item"
    table = "table"
    code = "code"
    blockquote = "blockquote"
    html = "html"
    footnote = "footnote"
    thematic_break = "thematic_break"


@cache
def markdown_parser() -> Markdown:
    """Shared marko parser, configured the same way flowmark configures it."""
    return flowmark_markdown()


def classify_block(text: str) -> BlockType:
    parsed = markdown_parser().parse(text)
    element = next((el for el in parsed.children if not isinstance(el, BlankLine)), None)
    if isinstance(element, (Heading, SetextHeading)):
        return BlockType.heading
    if isinstance(element, FootnoteDef):
        return BlockType.footnote
    if isinstance(element, (FencedCode, CodeBlock)):
        return BlockType.code
    if isinstance(element, Quote):
        return BlockType.blockquote
    if isinstance(element, Table):
        return BlockType.table
    if isinstance(element, List):
        return BlockType.list
    if isinstance(element, HTMLBlock):
        return BlockType.html
    return BlockType.paragraph
