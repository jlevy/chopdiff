"""
Markdown block classification, shared by `text_doc` (per-paragraph block typing) and
`block_tree` (whole-document structural parsing). Kept in its own module so both can
depend on it without an import cycle.

Classification is a single mapping from marko block-element classes to `BlockType`,
applied to elements produced by `flowmark.flowmark_markdown`. There is no regex or
heuristic here: the parser decides what each block is, and `block_type_for` looks up the
class.
"""

from __future__ import annotations

from enum import StrEnum

from marko.block import (
    CodeBlock,
    FencedCode,
    Heading,
    HTMLBlock,
    List,
    ListItem,
    Paragraph,
    Quote,
    SetextHeading,
    ThematicBreak,
)
from marko.element import Element
from marko.ext.footnote import FootnoteDef
from marko.ext.gfm.elements import Table


class BlockType(StrEnum):
    """
    The kind of Markdown block, determined by the marko class flowmark's parser assigns
    to it (see `block_type_for`). GFM tables, footnote definitions, and fenced code
    (including `#` lines inside code) are recognized correctly because the parser, not a
    regex, makes the call.

    Bulleted lists are `list`; ordered (numbered) lists are `ordered_list`, carrying
    marko's `List.ordered`. Both kinds decompose into `list_item` children in the
    structural view.

    The per-paragraph view (`Paragraph.block_type`) splits a document on blank lines, so
    list handling depends on item spacing:

    - A "tight" list (no blank lines between items) is a single `list`/`ordered_list`
      block containing every item; nested sublists stay inside that one block.
    - A "loose" list (blank lines between items) yields one block per item, and nesting
      is flattened (each item, parent or child, is its own block).
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
    ordered_list = "ordered_list"
    list_item = "list_item"
    table = "table"
    code = "code"
    blockquote = "blockquote"
    html = "html"
    footnote = "footnote"
    thematic_break = "thematic_break"


_BLOCK_TYPE_BY_CLASS: dict[type[Element], BlockType] = {
    Heading: BlockType.heading,
    SetextHeading: BlockType.heading,
    Paragraph: BlockType.paragraph,
    FencedCode: BlockType.code,
    CodeBlock: BlockType.code,
    ThematicBreak: BlockType.thematic_break,
    Quote: BlockType.blockquote,
    List: BlockType.list,
    ListItem: BlockType.list_item,
    Table: BlockType.table,
    FootnoteDef: BlockType.footnote,
    HTMLBlock: BlockType.html,
}


def block_type_for(element: Element) -> BlockType:
    """
    Map a marko block element to its `BlockType` via `_BLOCK_TYPE_BY_CLASS`, walking the
    element's MRO so flowmark's subclasses (e.g. `CustomListItem`, `CustomFencedCode`)
    resolve to their base type. Unmapped block elements fall back to `paragraph`.

    Ordered-ness is an instance property, not a class, so a `List` resolves to
    `ordered_list` or `list` based on `List.ordered`.
    """
    if isinstance(element, List):
        return BlockType.ordered_list if element.ordered else BlockType.list
    for cls in type(element).__mro__:
        block_type = _BLOCK_TYPE_BY_CLASS.get(cls)
        if block_type is not None:
            return block_type
    return BlockType.paragraph
