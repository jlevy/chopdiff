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


def test_frontmatter_excluded_from_structural_views():
    doc = TextDoc.from_text(_FM + _BODY)
    co = len(_FM)
    assert doc.blocks() and all(b.span[0] >= co for b in doc.blocks())
    assert doc.sections() and all(s.span[0] >= co for s in doc.sections())
    assert all(bb.block.span[0] >= co for bb in doc.base_blocks())
    table = doc.node_table()
    assert all(n.source_span is None or n.source_span[0] >= co for n in table.nodes.values())


def test_yaml_frontmatter_is_not_a_section():
    # `title: Hello\n---` can parse as a setext H2; it must not become a document section.
    doc = TextDoc.from_text(_FM + _BODY)
    assert [s.title for s in doc.sections()] == ["Heading"]


def test_body_blocks_unperturbed_by_frontmatter():
    co = len(_FM)
    with_fm = TextDoc.from_text(_FM + _BODY).blocks()
    body_only = TextDoc.from_text(_BODY).blocks()
    assert [b.type for b in with_fm] == [b.type for b in body_only]
    # Same structure, spans shifted by exactly the frontmatter length.
    assert [b.span for b in with_fm] == [(s + co, e + co) for s, e in (b.span for b in body_only)]
