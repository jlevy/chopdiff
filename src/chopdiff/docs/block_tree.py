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

Containers (lists, list items, blockquotes) fully populate their block children
recursively, so a table inside a blockquote or a paragraph inside a list item is
reachable in the tree. The top-level `blocks()`/`parse_blocks` ordering and the `Block`
dataclass shape are unchanged.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field

from flowmark import flowmark_markdown
from flowmark.markdown_ast import block_span
from marko.block import BlankLine, CodeBlock, List, ListItem
from marko.block import Quote as MarkoQuote
from marko.element import Element

from chopdiff.docs.block_types import BlockType, block_type_for


@dataclass
class Block:
    """
    A structural block with an exact `[start, end)` span into the source.

    `children` holds nested blocks: a `list`/`ordered_list` block's children are its
    `list_item`s, and a `list_item`'s children are ALL its block children (paragraphs,
    nested lists, tables, code, etc.). A `blockquote`'s children are its nested blocks.
    Leaf blocks (heading, code, table, thematic_break, etc.) have no children. `span` is
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


def parse_blocks(text: str, parsed: Element | None = None) -> list[Block]:
    """
    Parse `text` into a tree of structural `Block`s with exact source spans.

    `parsed` is the marko parse of `text`; pass it to reuse a shared parse (the caller
    guarantees it is the parse of exactly this `text`), else `text` is parsed here.
    """
    return _blocks_from(text, parsed if parsed is not None else flowmark_markdown().parse(text))


def walk_blocks(blocks: list[Block], _depth: int = 0) -> Iterator[tuple[Block, int]]:
    """
    Depth-first traversal of a block tree, yielding `(block, depth)` pairs.
    Top-level blocks have depth 0; their children have depth 1, and so on.
    """
    for block in blocks:
        yield block, _depth
        yield from walk_blocks(block.children, _depth + 1)


def _trim(text: str, lo: int, hi: int, *, keep_leading: bool = False) -> tuple[int, int]:
    """Shrink a span to drop surrounding whitespace (marko spans include trailing newlines
    and a nested element's leading indentation/marker line). When `keep_leading` is True,
    only trailing whitespace is stripped (for indented code blocks whose leading spaces are
    syntax)."""
    if not keep_leading:
        while lo < hi and text[lo].isspace():
            lo += 1
    while hi > lo and text[hi - 1].isspace():
        hi -= 1
    return lo, hi


def _blocks_from(text: str, parent: Element) -> list[Block]:
    """
    Build `Block`s from `parent`'s block children, skipping blank lines. Every
    container populates all its block children recursively: a `list` decomposes into
    `list_item`s, a `list_item` keeps all its block children (paragraphs, nested lists,
    tables, code, etc.), and a `blockquote` keeps all its nested blocks.
    """
    blocks: list[Block] = []
    children: list[Element] = getattr(parent, "children", []) or []
    for element in children:
        if isinstance(element, BlankLine):
            continue
        block_type = block_type_for(element)
        # Indented code blocks: preserve leading whitespace (the 4-space indent is syntax).
        span = _trim(text, *block_span(element), keep_leading=isinstance(element, CodeBlock))
        tight: bool | None = None
        if isinstance(element, List):
            sub = _blocks_from(text, element)
            tight = element.tight
        elif isinstance(element, (ListItem, MarkoQuote)):
            sub = _blocks_from(text, element)
        else:
            sub = []
        blocks.append(Block(block_type, span, sub, tight))
    return blocks
