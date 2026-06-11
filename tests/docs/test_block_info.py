"""
Typed block metadata at the `Block` (structural) and `Paragraph` (editing-view) levels,
and its flow into markdown node `attrs`. Extractor unit tests live inline in
`flexdoc.docs.block_info`.
"""

from __future__ import annotations

from textwrap import dedent

from flexdoc.docs.block_info import CodeInfo, ListInfo, TableInfo
from flexdoc.docs.block_tree import Block
from flexdoc.docs.block_types import BlockType
from flexdoc.docs.node import NodeKind
from flexdoc.docs.text_doc import TextDoc

DOC = dedent("""
    # Title

    ```python
    x = 1
    y = 2
    ```

    | a | b | c |
    |:--|:-:|--:|
    | 1 | 2 | 3 |

    1. one
    2. two
       - nested
    3. three
    """).strip()


def _find(blocks: list[Block], btype: BlockType) -> Block | None:
    for b in blocks:
        if b.type == btype:
            return b
        found = _find(b.children, btype)
        if found is not None:
            return found
    return None


def test_block_typed_metadata():
    blocks = TextDoc.from_text(DOC).blocks()

    code = _find(blocks, BlockType.code)
    assert code is not None
    assert code.code_info == CodeInfo("python", 2)
    assert code.table_info is None and code.list_info is None

    table = _find(blocks, BlockType.table)
    assert table is not None
    assert table.table_info == TableInfo(
        rows=2, cols=3, cells=6, alignments=["left", "center", "right"]
    )

    olist = _find(blocks, BlockType.ordered_list)
    assert olist is not None
    assert olist.list_info == ListInfo(ordered=True, start=1, max_depth=2, item_count=3)


def test_paragraph_metadata_matches_block_for_tight_single_block():
    # A single fenced code block is one Block and one covering Paragraph; both agree.
    para = TextDoc.from_text("```python\nx = 1\ny = 2\n```").paragraphs[0]
    assert para.code_info == CodeInfo("python", 2)
    assert para.table_info is None and para.list_info is None


def test_metadata_flows_into_node_attrs():
    table = TextDoc.from_text(DOC).node_table()

    code = table.by_kind(NodeKind.code)[0]
    assert code.attrs["language"] == "python"
    assert code.attrs["line_count"] == 2

    tbl = table.by_kind(NodeKind.table)[0]
    assert tbl.attrs["cols"] == 3
    assert tbl.attrs["cells"] == 6
    assert tbl.attrs["alignments"] == ["left", "center", "right"]

    olist = table.by_kind(NodeKind.ordered_list)[0]
    assert olist.attrs["item_count"] == 3
    assert olist.attrs["max_depth"] == 2
    assert olist.attrs["start"] == 1
