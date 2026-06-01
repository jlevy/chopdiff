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
    # Pairwise non-overlap: each base block's span must end before (or at) the
    # next one's start, at every depth. The spec (section 6) promises an ordered,
    # non-overlapping, complete-cover partition.
    for i in range(len(bbs) - 1):
        cur_end = bbs[i].block.span[1]
        next_start = bbs[i + 1].block.span[0]
        assert cur_end <= next_start, (
            f"base block {i} span ends at {cur_end} but block {i + 1} starts at {next_start}"
        )


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


def test_nested_list_spans_pairwise_non_overlapping():
    """Parent list_item span must cover only its own content, not nested items."""
    text = dedent(
        """
        - item one
          - nested a
          - nested b
        - item two
        """
    ).strip()
    bbs = base_blocks(text)

    # Pairwise non-overlap: each base block's span must not overlap the next.
    for i in range(len(bbs) - 1):
        cur_end = bbs[i].block.span[1]
        next_start = bbs[i + 1].block.span[0]
        assert cur_end <= next_start, (
            f"base block {i} span ends at {cur_end} but block {i + 1} starts at {next_start}"
        )

    # Correct depths: parent own-content at d=0, nested items at d=1.
    td = _types_and_depths(bbs)
    assert td == [
        (BlockType.list_item, 0),
        (BlockType.list_item, 1),
        (BlockType.list_item, 1),
        (BlockType.list_item, 0),
    ]

    # The parent base block's text must not contain the nested item markers.
    parent_text = text[bbs[0].block.span[0] : bbs[0].block.span[1]]
    assert "- nested" not in parent_text
    assert "item one" in parent_text


def _covered_nonspace(text: str, bbs: list[BaseBlock]) -> set[int]:
    """Indexes of non-whitespace source chars covered by some base-block span."""
    covered: set[int] = set()
    for bb in bbs:
        s, e = bb.block.span
        covered.update(range(s, e))
    return {i for i in range(len(text)) if not text[i].isspace()} - covered


def test_cover_invariant_trailing_content_after_sublist():
    """A list item with content after a nested sublist must stay in the cover."""
    text = dedent(
        """
        - item one text

          - sub a
          - sub b

          trailing paragraph inside item one

        - item two
        """
    ).strip()
    bbs = base_blocks(text)
    missing = _covered_nonspace(text, bbs)
    assert not missing, (
        f"uncovered non-whitespace at {sorted(missing)}: {''.join(text[i] for i in sorted(missing))!r}"
    )


def test_cover_invariant_content_between_two_sublists():
    """Content between two sublists in one item must stay in the cover."""
    text = dedent(
        """
        - item one

          - sub a

          middle text between sublists

          - sub b

        - item two
        """
    ).strip()
    bbs = base_blocks(text)
    missing = _covered_nonspace(text, bbs)
    assert not missing, (
        f"uncovered non-whitespace at {sorted(missing)}: {''.join(text[i] for i in sorted(missing))!r}"
    )
    # And spans remain ordered and non-overlapping.
    for i in range(len(bbs) - 1):
        assert bbs[i].block.span[1] <= bbs[i + 1].block.span[0]


def _assert_partition(text: str, bbs: list[BaseBlock]) -> None:
    """Ordered, pairwise non-overlapping, every non-whitespace char covered exactly once."""
    spans = [bb.block.span for bb in bbs]
    assert spans == sorted(spans), "base blocks not in source order"
    for i in range(len(spans) - 1):
        assert spans[i][1] <= spans[i + 1][0], f"spans overlap at {i}: {spans[i]} / {spans[i + 1]}"
    counts: dict[int, int] = {}
    for s, e in spans:
        for i in range(s, e):
            counts[i] = counts.get(i, 0) + 1
    for i, ch in enumerate(text):
        if ch.isspace():
            continue
        assert counts.get(i, 0) == 1, f"char {i} ({ch!r}) covered {counts.get(i, 0)} times"


def test_continuation_content_keeps_real_type_not_list_item():
    """A list-item continuation paragraph after a sublist is typed `paragraph`, so it is
    distinguishable from an independent top-level list item."""
    text = dedent(
        """
        - item one text

          - sub a
          - sub b

          trailing paragraph inside item one

        - item two
        """
    ).strip()
    bbs = base_blocks(text)
    _assert_partition(text, bbs)

    td = _types_and_depths(bbs)
    # head(list_item,0), sub a(list_item,1), sub b(list_item,1),
    # continuation(paragraph,0), item two(list_item,0)
    assert td == [
        (BlockType.list_item, 0),
        (BlockType.list_item, 1),
        (BlockType.list_item, 1),
        (BlockType.paragraph, 0),
        (BlockType.list_item, 0),
    ]
    continuation = next(bb for bb in bbs if bb.block.type == BlockType.paragraph)
    assert (
        "trailing paragraph inside item one"
        in text[continuation.block.span[0] : continuation.block.span[1]]
    )


def test_partition_holds_for_content_between_two_sublists():
    text = dedent(
        """
        - item one

          - sub a

          middle text between sublists

          - sub b

        - item two
        """
    ).strip()
    bbs = base_blocks(text)
    _assert_partition(text, bbs)
    # The between-sublists content is a paragraph, not a list_item.
    paras = [bb for bb in bbs if bb.block.type == BlockType.paragraph]
    assert len(paras) == 1
    assert "middle text between sublists" in text[paras[0].block.span[0] : paras[0].block.span[1]]
