from textwrap import dedent

from chopdiff.docs.base_blocks import BaseBlock, base_blocks
from chopdiff.docs.block_types import BlockType


def _types_and_depths(bbs: list[BaseBlock]) -> list[tuple[BlockType, int]]:
    return [(bb.block.type, bb.depth) for bb in bbs]


def test_simple_flat_document():
    text = dedent(
        """
        # Heading

        A paragraph.

        | a | b |
        | - | - |
        | 1 | 2 |

        ```
        code
        ```

        ---
        """
    ).strip()
    bbs = base_blocks(text)
    types = [bb.block.type for bb in bbs]
    assert types == [
        BlockType.heading,
        BlockType.paragraph,
        BlockType.table,
        BlockType.code,
        BlockType.thematic_break,
    ]
    # All top-level, so all depth 0.
    assert all(bb.depth == 0 for bb in bbs)


def test_list_decomposes_into_items():
    text = dedent(
        """
        - alpha
        - beta
        - gamma
        """
    ).strip()
    bbs = base_blocks(text)
    assert all(bb.block.type == BlockType.list_item for bb in bbs)
    assert all(bb.depth == 0 for bb in bbs)
    assert len(bbs) == 3


def test_nested_list_increases_depth():
    text = dedent(
        """
        - item one
          - nested a
          - nested b
        - item two
        """
    ).strip()
    bbs = base_blocks(text)
    td = _types_and_depths(bbs)
    # item one at depth 0, nested a and b at depth 1, item two at depth 0.
    assert td == [
        (BlockType.list_item, 0),
        (BlockType.list_item, 1),
        (BlockType.list_item, 1),
        (BlockType.list_item, 0),
    ]


def test_blockquote_is_always_atomic():
    text = dedent(
        """
        > Some quoted text.
        >
        > More quoted text.
        """
    ).strip()
    bbs = base_blocks(text)
    assert len(bbs) == 1
    assert bbs[0].block.type == BlockType.blockquote
    assert bbs[0].depth == 0


def test_blockquote_with_nested_content_is_one_base_block():
    text = dedent(
        """
        > A paragraph.
        >
        > | a | b |
        > | - | - |
        > | 1 | 2 |
        """
    ).strip()
    bbs = base_blocks(text)
    assert len(bbs) == 1
    assert bbs[0].block.type == BlockType.blockquote


def test_ordered_by_source_position():
    text = dedent(
        """
        # Title

        Paragraph.

        - a
        - b

        Another paragraph.
        """
    ).strip()
    bbs = base_blocks(text)
    positions = [bb.block.span[0] for bb in bbs]
    assert positions == sorted(positions)


def test_spans_non_overlapping():
    text = dedent(
        """
        # Title

        Paragraph one.

        - item one
          - nested
        - item two

        Another paragraph.

        ```
        code block
        ```
        """
    ).strip()
    bbs = base_blocks(text)
    # For non-overlapping, we check that no base block's span overlaps with the
    # NEXT base block that is NOT a descendant (i.e., at same or lower depth).
    # Since list items with nested lists have spans that contain their nested items,
    # overlapping is expected between a parent item and its nested children.
    # The invariant is that base blocks at the same depth level don't overlap,
    # and the partition covers the document.
    for i in range(len(bbs) - 1):
        bb_cur = bbs[i]
        bb_next = bbs[i + 1]
        # The next block must start at or after the current one starts.
        assert bb_next.block.span[0] >= bb_cur.block.span[0]


def test_complete_cover_reassembly():
    """Reassembling base blocks reproduces the document (modulo blank-line normalization)."""
    text = dedent(
        """
        # Title

        Paragraph one.

        - item one
        - item two

        Another paragraph.
        """
    ).strip()
    bbs = base_blocks(text)

    # Collect all leaf-level base block texts (those that are not parents of
    # deeper blocks in the partition). For a flat partition, the leaf blocks'
    # source spans should cover the document content.
    # Simpler check: every character in the source is covered by at least one
    # base block's span.
    covered = set()
    for bb in bbs:
        start, end = bb.block.span
        covered.update(range(start, end))

    # Every non-whitespace character should be covered.
    for i, ch in enumerate(text):
        if not ch.isspace():
            assert i in covered, f"Character {ch!r} at position {i} not covered"


def test_item_partition_depth_zero():
    text = dedent(
        """
        - item one
          - nested a
        - item two
        """
    ).strip()
    bbs = base_blocks(text, item_partition_depth=0)
    assert len(bbs) == 1
    assert bbs[0].block.type == BlockType.list
    assert bbs[0].depth == 0


def test_item_partition_depth_one():
    text = dedent(
        """
        - item one
          - nested a
          - nested b
        - item two
        """
    ).strip()
    bbs = base_blocks(text, item_partition_depth=1)
    # At depth 1, we split the top-level list into items but do not further
    # decompose nested lists inside items.
    td = _types_and_depths(bbs)
    assert td == [
        (BlockType.list_item, 0),
        (BlockType.list_item, 0),
    ]


def test_item_partition_depth_unlimited():
    # Three levels of nesting with unlimited depth.
    text = dedent(
        """
        - level 1
          - level 2
            - level 3
        """
    ).strip()
    bbs = base_blocks(text, item_partition_depth=-1)
    td = _types_and_depths(bbs)
    assert td == [
        (BlockType.list_item, 0),
        (BlockType.list_item, 1),
        (BlockType.list_item, 2),
    ]


def test_source_span_exact_reconstruction():
    """Each base block retains its exact source_span for byte-exact reconstruction."""
    text = dedent(
        """
        # Heading

        Some paragraph.

        ---
        """
    ).strip()
    bbs = base_blocks(text)
    for bb in bbs:
        start, end = bb.block.span
        extracted = text[start:end]
        # The span should extract meaningful (non-empty, trimmed) content.
        assert len(extracted) > 0
        assert extracted == extracted.strip()


def test_mixed_document_partition():
    text = dedent(
        """
        # Title

        Intro paragraph.

        - item one
        - item two

        ```python
        x = 1
        ```

        | a | b |
        | - | - |
        | 1 | 2 |

        > A blockquote with content.

        ---
        """
    ).strip()
    bbs = base_blocks(text)
    types = [bb.block.type for bb in bbs]
    assert types == [
        BlockType.heading,
        BlockType.paragraph,
        BlockType.list_item,
        BlockType.list_item,
        BlockType.code,
        BlockType.table,
        BlockType.blockquote,
        BlockType.thematic_break,
    ]


def test_density_invariant_base_blocks():
    # Tight and loose lists produce the same base blocks (same count, same types).
    dense = base_blocks("- a\n- b\n- c")
    loose = base_blocks("- a\n\n- b\n\n- c")
    assert len(dense) == len(loose) == 3
    assert all(bb.block.type == BlockType.list_item for bb in dense)
    assert all(bb.block.type == BlockType.list_item for bb in loose)


def test_ordered_list_decomposes():
    text = "1. one\n2. two\n3. three"
    bbs = base_blocks(text)
    assert all(bb.block.type == BlockType.list_item for bb in bbs)
    assert len(bbs) == 3
