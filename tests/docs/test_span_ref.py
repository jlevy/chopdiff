"""
Tests for `SpanRef` and `resolve()`: round-trip construction, re-anchoring
after edits, persisted form resolution, and fast-path behavior.
"""

from __future__ import annotations

import dataclasses
from textwrap import dedent

from flexdoc.docs.node import Layer, NodeKind
from flexdoc.docs.node_table import build_node_table
from flexdoc.docs.span_ref import SpanRef, resolve, resolve_and_update
from flexdoc.docs.text_doc import TextDoc

_DOC_TEXT = dedent("""
    # Introduction

    This is the first paragraph with some content.

    ## Details

    Here are the details. A [sample link](https://example.com) is here.

    | col1 | col2 |
    | ---- | ---- |
    | val1 | val2 |

    Final paragraph.
""").strip()


def test_node_to_spanref_roundtrip():
    """Node -> SpanRef -> resolve returns the original span."""
    doc = TextDoc.from_text(_DOC_TEXT)
    table = build_node_table(doc)

    # Pick a heading node with a span.
    headings = [n for n in table.nodes.values() if n.kind == NodeKind.heading and n.source_span]
    assert len(headings) >= 1
    heading = headings[0]

    ref = SpanRef.from_node(heading, table.source_text)
    result = resolve(ref, table.source_text)

    assert result is not None
    assert result == heading.source_span


def test_resolve_after_prepending_text():
    """After prepending text (offsets shift), resolve still finds the span by quote."""
    doc = TextDoc.from_text(_DOC_TEXT)
    table = build_node_table(doc)

    # Pick the table node.
    tables = [n for n in table.nodes.values() if n.kind == NodeKind.table and n.source_span]
    assert len(tables) >= 1
    tbl = tables[0]

    ref = SpanRef.from_node(tbl, table.source_text)
    original_span = tbl.source_span
    assert original_span is not None

    # Prepend text to shift all offsets.
    prepended = "PREPENDED TEXT\n\n" + _DOC_TEXT
    shift = len("PREPENDED TEXT\n\n")

    # The old offsets are now wrong.
    result = resolve(ref, prepended)
    assert result is not None
    # The resolved span should be shifted by the prepended length.
    assert result == (original_span[0] + shift, original_span[1] + shift)
    # The text at the resolved span matches the exact.
    assert prepended[result[0] : result[1]] == ref.exact


def test_to_persisted_has_no_offsets_but_still_resolves():
    """to_persisted() drops offsets; the persisted form still resolves via quote."""
    doc = TextDoc.from_text(_DOC_TEXT)
    table = build_node_table(doc)

    # Pick a paragraph node.
    paras = [
        n
        for n in table.nodes.values()
        if n.kind == NodeKind.paragraph and n.layer == Layer.markdown and n.source_span
    ]
    assert len(paras) >= 1
    para = paras[0]

    ref = SpanRef.from_node(para, table.source_text)
    persisted = ref.to_persisted()

    # Persisted form has no offsets.
    assert persisted.start is None
    assert persisted.end is None

    # But it still resolves.
    result = resolve(persisted, table.source_text)
    assert result is not None
    assert result == para.source_span


def test_fast_path_returns_immediately():
    """When offsets are valid and text matches, the fast path is used."""
    ref = SpanRef(
        exact="sample link",
        prefix=None,
        suffix=None,
        start=_DOC_TEXT.find("sample link"),
        end=_DOC_TEXT.find("sample link") + len("sample link"),
    )
    assert ref.start is not None

    # Fast path: offsets are valid and text matches.
    result = resolve(ref, _DOC_TEXT)
    assert result is not None
    assert result == (ref.start, ref.end)


def test_from_span_captures_context():
    """from_span captures prefix and suffix context windows."""
    start = _DOC_TEXT.find("sample link")
    end = start + len("sample link")
    ref = SpanRef.from_span(_DOC_TEXT, start, end)

    assert ref.exact == "sample link"
    assert ref.prefix is not None
    assert ref.suffix is not None
    assert ref.start == start
    assert ref.end == end
    # Context windows are trimmed at doc edges.
    assert len(ref.prefix) <= 24
    assert len(ref.suffix) <= 24


def test_resolve_with_multiple_occurrences_uses_context():
    """When exact text appears multiple times, prefix/suffix disambiguate."""
    text = "The word apple is here. And apple is also here. Finally apple again."
    # Create a ref for the second occurrence.
    second_start = text.find("apple", text.find("apple") + 1)
    ref = SpanRef.from_span(text, second_start, second_start + len("apple"))

    # Resolve should find the second occurrence using context.
    result = resolve(ref, text)
    assert result is not None
    assert result == (second_start, second_start + len("apple"))


def test_resolve_returns_none_for_missing_text():
    """resolve returns None when the exact text is not found."""
    ref = SpanRef(exact="NONEXISTENT TEXT THAT DOES NOT APPEAR")
    result = resolve(ref, _DOC_TEXT)
    assert result is None


def test_to_text_fragment():
    """to_text_fragment produces a Chrome-style text fragment with encoded components."""
    ref = SpanRef(exact="sample link", prefix="A [", suffix="]")
    frag = ref.to_text_fragment()
    assert frag == "#:~:text=A%20%5B-,sample%20link,-%5D"


def test_to_text_fragment_percent_encoded():
    """Spaces, delimiters, and non-ASCII in the exact text are percent-encoded."""
    ref = SpanRef(exact="a b # c, π")
    assert ref.to_text_fragment() == "#:~:text=a%20b%20%23%20c%2C%20%CF%80"


def test_resolve_does_not_mutate():
    """resolve() is pure: it never writes offsets back into the SpanRef."""
    ref = SpanRef(exact="target")
    before = dataclasses.replace(ref)
    result = resolve(ref, "before target after")
    assert result is not None
    assert ref == before


def test_resolve_and_update_writes_offsets():
    """resolve_and_update() writes the recomputed offsets back for fast-path reuse."""
    ref = SpanRef(exact="target")
    result = resolve_and_update(ref, "before target after")
    assert result is not None
    assert (ref.start, ref.end) == result


def test_to_persisted_can_keep_position_hint():
    """to_persisted keeps offsets only when explicitly asked."""
    ref = SpanRef(exact="x", start=3, end=4)
    assert ref.to_persisted().start is None
    kept = ref.to_persisted(include_position_hint=True)
    assert (kept.start, kept.end) == (3, 4)


def test_resolve_survives_reparse():
    """A SpanRef built from one parse resolves correctly after a reparse."""
    doc1 = TextDoc.from_text(_DOC_TEXT)
    table1 = build_node_table(doc1)

    # Build ref from first parse.
    headings = [n for n in table1.nodes.values() if n.kind == NodeKind.heading and n.source_span]
    heading = headings[0]
    ref = SpanRef.from_node(heading, table1.source_text)

    # Reparse the same text.
    doc2 = TextDoc.from_text(_DOC_TEXT)
    table2 = build_node_table(doc2)

    # Resolve against the reparsed source.
    result = resolve(ref, table2.source_text)
    assert result is not None
    assert result == heading.source_span


def test_persisted_resolves_after_edit():
    """A persisted SpanRef (no offsets) resolves after text is edited elsewhere."""
    ref = SpanRef.from_span(
        _DOC_TEXT,
        _DOC_TEXT.find("Final paragraph"),
        _DOC_TEXT.find("Final paragraph") + len("Final paragraph."),
    )
    persisted = ref.to_persisted()

    # Edit the document: change "Introduction" to "Intro" (earlier in doc).
    edited = _DOC_TEXT.replace("# Introduction", "# Intro")
    result = resolve(persisted, edited)
    assert result is not None
    assert edited[result[0] : result[1]] == persisted.exact


def test_from_span_at_document_edges():
    """from_span handles spans at the very start or end of the document."""
    # Start of document.
    ref_start = SpanRef.from_span(_DOC_TEXT, 0, len("# Introduction"))
    assert ref_start.prefix is None  # Nothing before start of doc.
    assert ref_start.suffix is not None
    assert ref_start.exact == "# Introduction"

    # End of document.
    end_text = "Final paragraph."
    end_start = _DOC_TEXT.rfind(end_text)
    ref_end = SpanRef.from_span(_DOC_TEXT, end_start, end_start + len(end_text))
    assert ref_end.prefix is not None
    assert ref_end.suffix is None  # Nothing after end of doc.
    assert ref_end.exact == end_text
