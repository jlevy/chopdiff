"""
Structural block tree for a Markdown document, with exact source spans.

This is the opt-in, whole-document structural view (`TextDoc.blocks()`) that resolves
what blank-line paragraph splitting cannot: it keeps a fenced code block whole even when
it contains blank lines, and it decomposes a tight list into individual `list_item`s with
nested sublists. Offsets are read directly from the source by a line scanner (marko does
not expose source positions), and the top-level block structure is cross-checked against
marko in the tests.

Scope: correct for well-formed, common Markdown. A *loose* list (blank lines between
items) is split into separate single-item list blocks by the blank-line boundary, the
same limitation `BlockType` documents; lazy continuation lines are not specially handled.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import regex

from chopdiff.docs.block_types import BlockType, classify_block

_LIST_MARKER_RE = regex.compile(r"^(\s*)([-*+]|\d+[.)])\s")
_FENCE_RE = regex.compile(r"^\s{0,3}(```+|~~~+)")
_THEMATIC_BREAK_RE = regex.compile(r"^\s{0,3}([-*_])(\s*\1){2,}\s*$")


@dataclass
class Block:
    """
    A structural block with an exact `[start, end)` span into the source.

    `children` holds nested blocks: a `list` block's children are its `list_item`s, and a
    `list_item`'s children include any nested list. Leaf blocks (paragraph, heading,
    code, table, blockquote, etc.) have no children. `span` is trimmed of surrounding
    whitespace, so `source[start:end]` is the block's exact text.
    """

    type: BlockType
    span: tuple[int, int]
    children: list[Block] = field(default_factory=list)


def _lines_with_offsets(text: str) -> list[tuple[int, str]]:
    offsets: list[tuple[int, str]] = []
    pos = 0
    for line in text.splitlines(keepends=True):
        offsets.append((pos, line))
        pos += len(line)
    return offsets


def _trim(text: str, lo: int, hi: int) -> tuple[int, int]:
    while lo < hi and text[lo].isspace():
        lo += 1
    while hi > lo and text[hi - 1].isspace():
        hi -= 1
    return lo, hi


def _region_span(text: str, lines: list[tuple[int, str]], a: int, b: int) -> tuple[int, int]:
    lo = lines[a][0]
    hi = lines[b - 1][0] + len(lines[b - 1][1])
    return _trim(text, lo, hi)


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip())


def parse_blocks(text: str) -> list[Block]:
    """Parse `text` into a tree of structural `Block`s with exact source spans."""
    lines = _lines_with_offsets(text)
    return _parse_region(text, lines, 0, len(lines))


def _parse_region(text: str, lines: list[tuple[int, str]], start_i: int, end_i: int) -> list[Block]:
    blocks: list[Block] = []
    i = start_i
    while i < end_i:
        line = lines[i][1]
        if not line.strip():
            i += 1
            continue
        fence = _FENCE_RE.match(line)
        if fence:
            marker = fence.group(1)[0] * 3
            j = i + 1
            while j < end_i and not lines[j][1].lstrip().startswith(marker):
                j += 1
            if j < end_i:
                j += 1  # include the closing fence line
            blocks.append(Block(BlockType.code, _region_span(text, lines, i, j)))
            i = j
            continue
        # Otherwise, accumulate until the next blank line.
        j = i
        while j < end_i and lines[j][1].strip():
            j += 1
        span = _region_span(text, lines, i, j)
        block_text = text[span[0] : span[1]]
        if _THEMATIC_BREAK_RE.match(block_text):
            blocks.append(Block(BlockType.thematic_break, span))
        else:
            btype = classify_block(block_text)
            block = Block(btype, span)
            if btype == BlockType.list:
                block.children = _parse_list_items(text, lines, i, j)
            blocks.append(block)
        i = j
    return blocks


def _parse_list_items(
    text: str, lines: list[tuple[int, str]], start_i: int, end_i: int
) -> list[Block]:
    base_indent: int | None = None
    starts: list[int] = []
    for k in range(start_i, end_i):
        m = _LIST_MARKER_RE.match(lines[k][1])
        if m:
            indent = len(m.group(1))
            if base_indent is None:
                base_indent = indent
            if indent == base_indent:
                starts.append(k)
    if not starts:
        return []
    starts.append(end_i)
    items: list[Block] = []
    for idx in range(len(starts) - 1):
        a, b = starts[idx], starts[idx + 1]
        item = Block(BlockType.list_item, _region_span(text, lines, a, b))
        item.children = _parse_nested_lists(text, lines, a + 1, b, base_indent or 0)
        items.append(item)
    return items


def _parse_nested_lists(
    text: str, lines: list[tuple[int, str]], start_i: int, end_i: int, base_indent: int
) -> list[Block]:
    sub = [
        k
        for k in range(start_i, end_i)
        if lines[k][1].strip() and _indent(lines[k][1]) > base_indent
    ]
    if not sub or not _LIST_MARKER_RE.match(lines[sub[0]][1]):
        return []
    first, last = sub[0], sub[-1]
    nested = Block(BlockType.list, _region_span(text, lines, first, last + 1))
    nested.children = _parse_list_items(text, lines, first, last + 1)
    return [nested]
