"""
Typed, parser-authoritative metadata for code, table, and list blocks.

The structs (`CodeInfo`, `TableInfo`, `ListInfo`) and the pure extractors that read them
off a marko block element are the single place that knows how to pull a
language/dimension/list fact from the parse. Both the structural `Block` path (the
density-invariant source of truth) and the `Paragraph` editing-view path reuse these, so
neither re-parses and both agree.

Extraction is parser-authoritative: every fact comes from a marko element attribute
(`FencedCode.lang`, `Table.num_of_cols` and per-cell `.align`, `List.ordered`/`.start`/
subtree), never a regex over source text, matching `block_types.py`'s rule.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from marko.block import CodeBlock, FencedCode, List, ListItem
from marko.element import Element
from marko.ext.gfm.elements import Table, TableCell, TableRow

Alignment = Literal["left", "center", "right"] | None
"""A table column's alignment, or `None` when the delimiter row leaves it undefined."""


@dataclass(frozen=True)
class CodeInfo:
    """Typed metadata for a code block."""

    language: str | None
    """Fenced info-string language; `None` for an indented code block (no info string)."""
    line_count: int
    """Body lines, excluding the fence lines."""


@dataclass(frozen=True)
class TableInfo:
    """Typed metadata for a GFM table."""

    rows: int
    """Total rows, including the header row."""
    cols: int
    """Columns (marko `Table.num_of_cols`)."""
    cells: int
    """`rows * cols`."""
    alignments: list[Alignment]
    """Per-column alignment, length `cols`."""


@dataclass(frozen=True)
class ListInfo:
    """Typed metadata for a list block."""

    ordered: bool
    start: int | None
    """`List.start` when ordered (e.g. `3` for `3.`), else `None`."""
    max_depth: int
    """`1` for a flat list, `2` with one level of nested sublist, and so on."""
    item_count: int
    """Direct `list_item` children."""


def _code_body(element: FencedCode | CodeBlock) -> str:
    """The code block's body text: its `RawText` children concatenated."""
    parts: list[str] = []
    for child in getattr(element, "children", []) or []:
        raw = getattr(child, "children", None)
        if isinstance(raw, str):
            parts.append(raw)
    return "".join(parts)


def code_info_for(element: Element) -> CodeInfo | None:
    """`CodeInfo` if `element` is a fenced or indented code block, else `None`."""
    if not isinstance(element, (FencedCode, CodeBlock)):
        return None
    lang = getattr(element, "lang", "") or ""
    return CodeInfo(language=lang or None, line_count=len(_code_body(element).splitlines()))


def table_info_for(element: Element) -> TableInfo | None:
    """`TableInfo` if `element` is a GFM table, else `None`."""
    if not isinstance(element, Table):
        return None
    table_rows = [c for c in element.children if isinstance(c, TableRow)]
    cols = int(getattr(element, "num_of_cols", 0) or 0)
    header_cells = (
        [c for c in table_rows[0].children if isinstance(c, TableCell)] if table_rows else []
    )
    alignments: list[Alignment] = [getattr(c, "align", None) for c in header_cells]
    rows = len(table_rows)
    return TableInfo(rows=rows, cols=cols, cells=rows * cols, alignments=alignments)


def _list_max_depth(element: List) -> int:
    """Max list nesting: `1` for a flat list, `+1` per level of nested sublist."""
    deepest = 0
    for item in element.children:
        if not isinstance(item, ListItem):
            continue
        for sub in getattr(item, "children", []) or []:
            if isinstance(sub, List):
                deepest = max(deepest, _list_max_depth(sub))
    return 1 + deepest


def list_info_for(element: Element) -> ListInfo | None:
    """`ListInfo` if `element` is a list, else `None`."""
    if not isinstance(element, List):
        return None
    ordered = bool(element.ordered)
    start = int(element.start) if ordered and getattr(element, "start", None) is not None else None
    item_count = sum(1 for c in element.children if isinstance(c, ListItem))
    return ListInfo(
        ordered=ordered, start=start, max_depth=_list_max_depth(element), item_count=item_count
    )


## Tests


def _parse_first(markdown: str) -> Element:
    from flowmark import flowmark_markdown
    from marko.block import BlankLine

    parsed = flowmark_markdown().parse(markdown)
    return next(el for el in parsed.children if not isinstance(el, BlankLine))


def test_code_info_extractor():
    assert code_info_for(_parse_first("```python\nx = 1\ny = 2\n```\n")) == CodeInfo("python", 2)
    # Indented code has no info string, so language is None.
    assert code_info_for(_parse_first("    indented\n    code\n")) == CodeInfo(None, 2)
    # A non-code element yields None.
    assert code_info_for(_parse_first("just a paragraph\n")) is None


def test_table_info_extractor():
    table = _parse_first("| a | b | c |\n|:--|:-:|--:|\n| 1 | 2 | 3 |\n| 4 | 5 | 6 |\n")
    info = table_info_for(table)
    assert info == TableInfo(rows=3, cols=3, cells=9, alignments=["left", "center", "right"])
    assert table_info_for(_parse_first("paragraph\n")) is None


def test_list_info_extractor():
    ordered = _parse_first("3. a\n4. b\n   - nested1\n   - nested2\n5. c\n")
    assert list_info_for(ordered) == ListInfo(ordered=True, start=3, max_depth=2, item_count=3)
    flat = _parse_first("- a\n- b\n")
    assert list_info_for(flat) == ListInfo(ordered=False, start=None, max_depth=1, item_count=2)
    assert list_info_for(_parse_first("paragraph\n")) is None
