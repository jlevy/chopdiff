from textwrap import dedent

from chopdiff.docs.sizes import TextUnit
from chopdiff.docs.text_doc import BlockType, TextDoc

DOC = dedent(
    """
    # Title

    Intro paragraph one. Second sentence here.

    - list item one
    - list item two
    - list item three

    Another paragraph after the list.

    | Col A | Col B |
    | ----- | ----- |
    | a     | b     |

    > A blockquote line.
    > Still quoting.

    [^note]: A footnote definition.

    Final paragraph with two sentences. And the second one.
    """
).strip()


def test_block_type_classification():
    doc = TextDoc.from_text(DOC)
    types = [p.block_type for p in doc.paragraphs]
    assert types == [
        BlockType.heading,
        BlockType.paragraph,
        BlockType.list,
        BlockType.paragraph,
        BlockType.table,
        BlockType.blockquote,
        BlockType.footnote,
        BlockType.paragraph,
    ]


def test_iter_blocks_include_exclude():
    doc = TextDoc.from_text(DOC)

    paras = list(doc.iter_blocks(include={BlockType.paragraph}))
    assert len(paras) == 3

    text_blocks = list(doc.iter_blocks(include={BlockType.paragraph, BlockType.list}))
    assert len(text_blocks) == 4

    no_headings_tables = list(doc.iter_blocks(exclude={BlockType.heading, BlockType.table}))
    assert all(p.block_type not in {BlockType.heading, BlockType.table} for p in no_headings_tables)
    assert len(no_headings_tables) == 6


def test_filtered_counts_paragraphs_only():
    doc = TextDoc.from_text(DOC)
    paragraphs_only = doc.filtered(include={BlockType.paragraph})

    # Three paragraph blocks: 2 + 1 + 2 sentences.
    assert paragraphs_only.size(TextUnit.sentences) == 5
    # Word count of only the paragraph blocks, excluding heading/list/table/etc.
    expected_words = sum(
        p.size(TextUnit.words) for p in doc.paragraphs if p.block_type == BlockType.paragraph
    )
    assert paragraphs_only.size(TextUnit.words) == expected_words


def test_setext_heading_classified_as_heading():
    doc = TextDoc.from_text(
        dedent(
            """
            Setext Heading One
            ==================

            Body paragraph.
            """
        ).strip()
    )
    assert doc.paragraphs[0].block_type == BlockType.heading
    assert doc.paragraphs[1].block_type == BlockType.paragraph


def test_code_fence_not_a_heading():
    doc = TextDoc.from_text(
        dedent(
            """
            ```python
            # This is a comment, not a heading
            x = 1
            ```
            """
        ).strip()
    )
    assert doc.paragraphs[0].block_type == BlockType.code


def test_empty_filter_returns_empty_doc():
    doc = TextDoc.from_text(DOC)
    empty = doc.filtered(include=set())
    assert empty.size(TextUnit.words) == 0
    assert empty.size(TextUnit.sentences) == 0


def test_filtered_returns_independent_copy():
    doc = TextDoc.from_text(DOC)
    before = doc.reassemble()
    filtered = doc.filtered(include={BlockType.paragraph})
    filtered.replace_str("paragraph", "XXXXX")
    assert doc.reassemble() == before


# The following tests document how list spacing affects blocking, since TextDoc
# splits on blank lines (see BlockType docstring).


def test_tight_list_is_one_block():
    doc = TextDoc.from_text(
        dedent(
            """
            - item one
            - item two
            - item three
            """
        ).strip()
    )
    assert len(doc.paragraphs) == 1
    assert doc.paragraphs[0].block_type == BlockType.list


def test_loose_list_is_one_block_per_item():
    doc = TextDoc.from_text(
        dedent(
            """
            - item one

            - item two

            - item three
            """
        ).strip()
    )
    assert len(doc.paragraphs) == 3
    assert all(p.block_type == BlockType.list for p in doc.paragraphs)


def test_nested_tight_list_is_one_block():
    doc = TextDoc.from_text(
        dedent(
            """
            - parent one
              - child a
              - child b
            - parent two
            """
        ).strip()
    )
    assert len(doc.paragraphs) == 1
    assert doc.paragraphs[0].block_type == BlockType.list


def test_nested_loose_list_is_flattened_into_list_blocks():
    doc = TextDoc.from_text(
        dedent(
            """
            - parent one

              - child a

            - parent two
            """
        ).strip()
    )
    assert len(doc.paragraphs) == 3
    assert all(p.block_type == BlockType.list for p in doc.paragraphs)


def test_list_item_continuation_paragraph_is_paragraph():
    doc = TextDoc.from_text(
        dedent(
            """
            - item one first para

              item one second para

            - item two
            """
        ).strip()
    )
    types = [p.block_type for p in doc.paragraphs]
    assert types == [BlockType.list, BlockType.paragraph, BlockType.list]
