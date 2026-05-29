"""
Structural block tree for a Markdown document, with exact source spans.

This is the opt-in, whole-document structural view (`TextDoc.blocks()`) that resolves
what blank-line paragraph splitting cannot: it keeps a fenced code block whole even when
it contains blank lines, and it decomposes a list into individual `list_item`s with
nested sublists regardless of item spacing.

Block boundaries and spans come straight from flowmark's parser: every block element
produced by `flowmark_markdown().parse(text)` carries an authoritative
`element.span = (start, end)` read from marko's own parser state (see
`flowmark.markdown_ast.block_span`). chopdiff makes no block-boundary decisions of its
own, so there is no regex scanner and no per-line heuristic.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from flowmark import flowmark_markdown
from flowmark.markdown_ast import block_span
from marko.block import BlankLine, List, ListItem
from marko.element import Element

from chopdiff.docs.block_types import BlockType, block_type_for


@dataclass
class Block:
    """
    A structural block with an exact `[start, end)` span into the source.

    `children` holds nested blocks: a `list`/`ordered_list` block's children are its
    `list_item`s, and a `list_item`'s children are any nested lists. Leaf blocks
    (paragraph, heading, code, table, blockquote, etc.) have no children. `span` is
    trimmed of surrounding whitespace, so `source[start:end]` is the block's exact text.

    `tight` carries CommonMark list density for `list`/`ordered_list` blocks (`True` when
    items have no blank lines between them), and is `None` for every other block type.
    The block tree is density-invariant: a loose list still decomposes into one list
    block with the same `list_item` children as its tight form, so `tight` records the
    spacing without changing the structure or the tallies.
    """

    type: BlockType
    span: tuple[int, int]
    children: list[Block] = field(default_factory=list)
    tight: bool | None = None


def parse_blocks(text: str) -> list[Block]:
    """Parse `text` into a tree of structural `Block`s with exact source spans."""
    return _blocks_from(text, flowmark_markdown().parse(text))


def _trim(text: str, lo: int, hi: int) -> tuple[int, int]:
    """Shrink a span to drop surrounding whitespace (marko spans include trailing newlines
    and a nested element's leading indentation/marker line)."""
    while lo < hi and text[lo].isspace():
        lo += 1
    while hi > lo and text[hi - 1].isspace():
        hi -= 1
    return lo, hi


def _blocks_from(text: str, parent: Element) -> list[Block]:
    """
    Build `Block`s from `parent`'s block children, skipping blank lines. Recursion is
    limited to lists: a `list` decomposes into its `list_item`s, and a `list_item` keeps
    only its nested lists as children (its own paragraph text is not surfaced as a child,
    matching the per-paragraph view's "classify by outer type" contract).
    """
    blocks: list[Block] = []
    children: list[Element] = getattr(parent, "children", []) or []
    for element in children:
        if isinstance(element, BlankLine):
            continue
        block_type = block_type_for(element)
        span = _trim(text, *block_span(element))
        tight: bool | None = None
        if isinstance(element, List):
            sub = _blocks_from(text, element)
            tight = element.tight
        elif isinstance(element, ListItem):
            sub = [
                b
                for b in _blocks_from(text, element)
                if b.type in (BlockType.list, BlockType.ordered_list)
            ]
        else:
            sub = []
        blocks.append(Block(block_type, span, sub, tight))
    return blocks
