"""
Footnote-reference (`[^label]`) inline nodes: recognized, span-exact, and labeled, and
not confused with footnote definitions (`[^label]:`). Regression for the prior silent
drop, where a footnote reference was mis-tagged as a `markdown_link` atomic and skipped.
"""

from __future__ import annotations

from textwrap import dedent

from flexdoc.docs.collect import collect
from flexdoc.docs.node import NodeKind
from flexdoc.docs.text_doc import TextDoc


def test_footnote_ref_collected_with_span_and_label():
    src = dedent("""
        See the note[^1] and another[^note].

        [^1]: First definition.
        [^note]: Second definition.
        """).strip()
    refs = collect(
        TextDoc.from_text(src).node_table(), kinds={NodeKind.footnote_ref}, recursive=True
    )

    assert [r.attrs["label"] for r in refs] == ["1", "note"]
    for r in refs:
        assert r.source_span is not None
        s, e = r.source_span
        assert src[s:e] == f"[^{r.attrs['label']}]"


def test_footnote_definition_is_not_a_reference():
    src = "[^1]: only a definition, no reference.\n"
    table = TextDoc.from_text(src).node_table()
    assert collect(table, kinds={NodeKind.footnote_ref}, recursive=True) == []
