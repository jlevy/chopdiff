from textwrap import dedent

from flexdoc.docs.block_types import BlockType
from flexdoc.docs.sizes import TextUnit
from flexdoc.docs.text_doc import TextDoc


def serialize_blocks(doc: TextDoc) -> str:
    """
    Render a TextDoc's blocks transparently: one line per block with its index,
    classified `BlockType`, and a single-line preview. Used for golden tests that
    show exactly how a document is split and classified.
    """
    lines: list[str] = []
    for i, p in enumerate(doc.paragraphs):
        preview = p.original_text.replace("\n", "\\n")
        if len(preview) > 50:
            preview = preview[:50] + "..."
        lines.append(f"[{i}] {p.block_type.value}: {preview}")
    return "\n".join(lines)


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


def test_source_references_are_stable_under_edits():
    # Editing content updates reassemble() but not the fixed source references
    # (original_text, offsets) or the cached block_type.
    doc = TextDoc.from_text(DOC)
    para = doc.paragraphs[1]
    original_text, offsets, block_type = para.original_text, para.offsets, para.block_type
    para.replace_str("paragraph", "PARA")
    assert "PARA" in para.reassemble()
    assert para.original_text == original_text
    assert para.offsets == offsets
    assert para.block_type == block_type


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


def test_ordered_list_block_type():
    doc = TextDoc.from_text("1. one\n2. two\n3. three")
    assert len(doc.paragraphs) == 1
    assert doc.paragraphs[0].block_type == BlockType.ordered_list


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


# A rich document exercising the non-obvious paths: ATX/setext/trailing-hash
# headings, a link-first paragraph, inline and standalone HTML, tight and loose
# bulleted and ordered lists, blockquotes wrapping a list and a table (nested
# blocks classify by their OUTER type), a table, fenced code containing a `#`
# line, and a footnote definition.
RICH_DOC = dedent(
    """
    # Heading One

    A normal paragraph with two sentences. Here is the second.

    Setext Heading
    ==============

    [Leading link](http://example.com) starts this paragraph, then more text.

    Some prose with <span>inline html</span> in the middle.

    <!-- a standalone comment -->

    - tight item a
    - tight item b

    1. ordered one
    2. ordered two

    - loose item a

    - loose item b

    > A blockquote paragraph here.

    > - quoted list item one
    > - quoted list item two

    > | q1 | q2 |
    > | -- | -- |
    > | a  | b  |

    | Col A | Col B |
    | ----- | ----- |
    | x     | y     |

    ```python
    # not a heading
    code = 1
    ```

    [^fn]: A footnote definition body.

    ## Heading Two ##
    """
).strip()


EXPECTED_RICH_BLOCKS = r"""
[0] heading: # Heading One
[1] paragraph: A normal paragraph with two sentences. Here is the...
[2] heading: Setext Heading\n==============
[3] paragraph: [Leading link](http://example.com) starts this par...
[4] paragraph: Some prose with <span>inline html</span> in the mi...
[5] html: <!-- a standalone comment -->
[6] list: - tight item a\n- tight item b
[7] ordered_list: 1. ordered one\n2. ordered two
[8] list: - loose item a
[9] list: - loose item b
[10] blockquote: > A blockquote paragraph here.
[11] blockquote: > - quoted list item one\n> - quoted list item two
[12] blockquote: > | q1 | q2 |\n> | -- | -- |\n> | a  | b  |
[13] table: | Col A | Col B |\n| ----- | ----- |\n| x     | y ...
[14] code: ```python\n# not a heading\ncode = 1\n```
[15] footnote: [^fn]: A footnote definition body.
[16] heading: ## Heading Two ##
""".strip()


def test_rich_document_block_structure_golden():
    doc = TextDoc.from_text(RICH_DOC)
    assert serialize_blocks(doc) == EXPECTED_RICH_BLOCKS


def test_nested_blocks_classify_by_outer_type():
    # A blockquote wrapping a list or a table is classified `blockquote`; the
    # inner block type is intentionally not surfaced at this level.
    doc = TextDoc.from_text(RICH_DOC)
    by_type: dict[BlockType, list[str]] = {}
    for p in doc.paragraphs:
        by_type.setdefault(p.block_type, []).append(p.original_text)
    quotes = by_type[BlockType.blockquote]
    assert any(q.startswith("> -") for q in quotes)  # list inside a quote
    assert any(q.startswith("> |") for q in quotes)  # table inside a quote


def test_block_offsets_reference_the_source_document():
    # chopdiff references the backing text by offset; each block's doc_offset
    # indexes the source back to its own content.
    doc = TextDoc.from_text(RICH_DOC)
    for p in doc.paragraphs:
        start = p.offsets.doc_offset
        assert RICH_DOC[start : start + len(p.original_text)] == p.original_text
