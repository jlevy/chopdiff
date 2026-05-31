"""
Sequential base-block partition of a Markdown document.

A base block is a unit of the flat, depth-annotated partition described in
textdoc-spec section 6. The partition is ordered by source position, spans are
non-overlapping, and it is a complete cover of the document. Reassembling the
base blocks in order reproduces the document exactly except for normalized
paragraph-break whitespace (runs of blank lines between blocks).

Leaf/atomic blocks (heading, paragraph, table, code, thematic_break, html, and
a whole blockquote) are each one base block. Lists decompose so each list item
at every nesting level is its own base block with increasing depth.
"""

from __future__ import annotations

from dataclasses import dataclass

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


def base_blocks(text: str, *, item_partition_depth: int = 6) -> list[BaseBlock]:
    """
    Produce the flat, depth-annotated sequential block partition.

    - `item_partition_depth = N` (default 6): split list items down to N nesting
      levels; content nested deeper stays whole inside its depth-N base block.
    - `item_partition_depth = -1`: unlimited; split at every nesting level.
    - `item_partition_depth = 0`: lists are not split; each list is one base block.

    Blockquotes are always one base block regardless of depth.

    Invariants: the result is ordered by source position, spans are non-overlapping,
    and the partition is a complete cover (reassembling reproduces the document
    except for normalized paragraph-break whitespace between blocks).
    """
    blocks = parse_blocks(text)
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
    Emit a list item as a base block. If the item contains nested lists and we
    have not exceeded `max_depth`, emit a block whose span covers only the item's
    OWN content (from item start to the start of its first nested list child,
    with trailing whitespace trimmed), then recurse into each nested list at
    depth+1. A leaf list item (no nested lists) emits its full span.
    """
    nested_lists = [c for c in item.children if c.type in _LIST_TYPES]
    at_depth_limit = max_depth != -1 and current_nesting >= max_depth

    if not nested_lists or at_depth_limit:
        out.append(BaseBlock(block=item, depth=depth))
    else:
        # The item's own content runs from item start to the start of its first
        # nested list child. Trim trailing whitespace from the source so the span
        # covers only meaningful content.
        first_nested_start = min(c.span[0] for c in nested_lists)
        own_start = item.span[0]
        own_end = first_nested_start
        while own_end > own_start and text[own_end - 1].isspace():
            own_end -= 1
        own_block = Block(
            type=item.type,
            span=(own_start, own_end),
            children=[],
            tight=item.tight,
        )
        out.append(BaseBlock(block=own_block, depth=depth))
        for child in item.children:
            if child.type in _LIST_TYPES:
                for nested_item in child.children:
                    _emit_list_item(
                        text, nested_item, depth + 1, max_depth, current_nesting + 1, out
                    )
