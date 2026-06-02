"""
Sequential base-block partition of a Markdown document.

A base block is a unit of the flat, depth-annotated partition described in
textdoc-spec section 6. The partition is ordered by source position, its spans are
non-overlapping, and together they cover every non-whitespace character of the
document exactly once (the gaps are inter-block and structural whitespace). It is the
view for block-by-block processing and resequencing.

Each base block retains its exact `source_span`, so exact source reconstruction is
available by slicing the source at those spans (or via the structural `blocks()` tree).
Reassembling the rendered base-block *text* is lossy for list-item continuation content:
list markers and continuation indentation are whitespace outside the trimmed spans, so a
naive text concatenation normalizes them. Reconstruct from offsets when exactness matters.

Leaf/atomic blocks (heading, paragraph, table, code, thematic_break, html, and
a whole blockquote) are each one base block. Lists decompose: each list item at every
nesting level is its own base block with increasing depth, and a list item's continuation
content (paragraphs after or between nested sublists) is emitted with its own real block
type at the item's depth — never relabeled `list_item`.
"""

from __future__ import annotations

from dataclasses import dataclass

from marko.element import Element

from chopdiff.docs.block_tree import Block, parse_blocks
from chopdiff.docs.block_types import BlockType

# Block types that are always atomic (never decomposed into child base blocks).
_ATOMIC_TYPES = frozenset(
    {
        BlockType.heading,
        BlockType.paragraph,
        BlockType.table,
        BlockType.code,
        BlockType.thematic_break,
        BlockType.html,
        BlockType.footnote,
        BlockType.blockquote,
    }
)

# Block types representing lists that decompose into list_item children.
_LIST_TYPES = frozenset({BlockType.list, BlockType.ordered_list})


@dataclass
class BaseBlock:
    """
    A single unit of the sequential base-block partition. Carries the underlying
    `Block` (with its type, span, and children) and the `depth` indicating nesting
    level (0 for top-level blocks, increasing for nested list items).
    """

    block: Block
    depth: int


def base_blocks(
    text: str, *, item_partition_depth: int = 6, parsed: Element | None = None
) -> list[BaseBlock]:
    """
    Produce the flat, depth-annotated sequential block partition.

    - `item_partition_depth = N` (default 6): split list items down to N nesting
      levels; content nested deeper stays whole inside its depth-N base block.
    - `item_partition_depth = -1`: unlimited; split at every nesting level.
    - `item_partition_depth = 0`: lists are not split; each list is one base block.

    Blockquotes are always one base block regardless of depth.

    `parsed` is the marko parse of `text`; pass it to reuse a shared parse, else `text`
    is parsed here.

    Invariants: the result is ordered by source position, spans are non-overlapping, and
    together they cover every non-whitespace character exactly once. Exact source
    reconstruction is via each block's `source_span` (not by concatenating block text;
    see the module docstring for the continuation-content caveat).
    """
    blocks = parse_blocks(text, parsed)
    result: list[BaseBlock] = []
    _collect_base_blocks(text, blocks, 0, item_partition_depth, result)
    return result


def _collect_base_blocks(
    text: str,
    blocks: list[Block],
    depth: int,
    max_depth: int,
    out: list[BaseBlock],
) -> None:
    """
    Recursively collect base blocks. Lists decompose into their list_item
    children; list items decompose further if they contain nested lists (up to
    `max_depth`). Atomic blocks and blockquotes are emitted whole.
    """
    for block in blocks:
        if block.type in _ATOMIC_TYPES:
            out.append(BaseBlock(block=block, depth=depth))
        elif block.type in _LIST_TYPES:
            if max_depth == 0:
                # Lists not split: emit the whole list as one base block.
                out.append(BaseBlock(block=block, depth=depth))
            else:
                # Decompose: each list_item child becomes a base block (or further
                # decomposes if it contains nested lists).
                for item in block.children:
                    _emit_list_item(text, item, depth, max_depth, 1, out)
        elif block.type == BlockType.list_item:
            # A bare list_item at the top level (unusual) is treated as atomic.
            out.append(BaseBlock(block=block, depth=depth))
        else:
            # Any other block type not explicitly handled: emit as atomic.
            out.append(BaseBlock(block=block, depth=depth))


def _emit_list_item(
    text: str,
    item: Block,
    depth: int,
    max_depth: int,
    current_nesting: int,
    out: list[BaseBlock],
) -> None:
    """
    Emit a list item as base blocks. A leaf item (no nested lists, or at the depth
    limit) emits its full span as one block. Otherwise the item decomposes, in source
    order, into:

    - one `list_item` head block spanning from the item start (the list marker) through
      its lead content up to the first nested sublist, at `depth`;
    - each nested sublist's items, recursed at `depth + 1`;
    - each *continuation* block (content after or between sublists) emitted with its own
      real block type (e.g. `paragraph`), at `depth`.

    Continuation content keeps its real type rather than being mislabeled `list_item`, so
    a consumer can tell a continuation paragraph apart from an independent list item.
    Spans are non-overlapping and cover every non-whitespace character. Exact source
    reconstruction is via each block's `source_span` (or the structural `blocks()` tree),
    not by concatenating base-block text: list-marker and continuation indentation are
    whitespace outside the trimmed spans.
    """
    nested_lists = [c for c in item.children if c.type in _LIST_TYPES]
    at_depth_limit = max_depth != -1 and current_nesting >= max_depth

    if not nested_lists or at_depth_limit:
        out.append(BaseBlock(block=item, depth=depth))
        return

    # Head: the marker plus lead content up to the first nested sublist, typed list_item.
    first_nested_start = min(c.span[0] for c in nested_lists)
    head_end = first_nested_start
    while head_end > item.span[0] and text[head_end - 1].isspace():
        head_end -= 1
    if head_end > item.span[0]:
        head = Block(type=item.type, span=(item.span[0], head_end), children=[], tight=item.tight)
        out.append(BaseBlock(block=head, depth=depth))

    # Then, in source order: recurse into each sublist; emit each continuation block
    # (any non-list child past the head) with its own real type.
    for child in item.children:
        if child.type in _LIST_TYPES:
            for nested_item in child.children:
                _emit_list_item(text, nested_item, depth + 1, max_depth, current_nesting + 1, out)
        elif child.span[1] > head_end:
            out.append(BaseBlock(block=child, depth=depth))
