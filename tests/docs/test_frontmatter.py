"""
Frontmatter isolation (editing view): a leading YAML block is a non-content region —
excluded from paragraphs/sentences/size and exposed verbatim via `TextDoc.frontmatter`,
while `source_text` keeps the full original and spans stay absolute. Detector unit tests
live inline in `flexdoc.docs.frontmatter`; structural-view exclusion is tested separately.
"""

from __future__ import annotations

from textwrap import dedent

from flexdoc.docs.sizes import TextUnit
from flexdoc.docs.text_doc import TextDoc

_FM = "---\ntitle: Hello\ntags: [a, b]\n---\n\n"
_BODY = (
    dedent("""
    # Heading

    First paragraph with some words.

    Second paragraph here.
    """).strip()
    + "\n"
)


def test_frontmatter_property_and_paragraph_exclusion():
    doc = TextDoc.from_text(_FM + _BODY)
    assert doc.frontmatter == "---\ntitle: Hello\ntags: [a, b]\n---\n"
    assert doc.source_text == _FM + _BODY  # full original retained
    content_offset = len(_FM)
    assert all(p.span[0] >= content_offset for p in doc.paragraphs)
    assert all("title: Hello" not in p.original_text for p in doc.paragraphs)


def test_frontmatter_excluded_from_size():
    with_fm = TextDoc.from_text(_FM + _BODY)
    body_only = TextDoc.from_text(_BODY)
    for unit in (TextUnit.words, TextUnit.wordtoks):
        assert with_fm.size(unit) == body_only.size(unit)


def test_span_roundtrip_invariant_holds_with_frontmatter():
    doc = TextDoc.from_text(_FM + _BODY)
    for p in doc.paragraphs:
        assert doc.source_text[p.span[0] : p.span[1]] == p.original_text


def test_thematic_break_is_not_frontmatter():
    # A leading `---` with no closing delimiter is a thematic break, not frontmatter.
    doc = TextDoc.from_text("---\n\n# Real Heading\n\nBody.\n")
    assert doc.frontmatter is None
    assert doc.source_text == "---\n\n# Real Heading\n\nBody.\n"
