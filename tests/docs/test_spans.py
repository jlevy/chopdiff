from textwrap import dedent

from chopdiff.docs.sizes import TextUnit
from chopdiff.docs.text_doc import BlockType, SentIndex, TextDoc

_DOC = dedent(
    """
    # Title

    First paragraph. Second sentence here.

    Another paragraph with one sentence.
    """
).strip()


def test_paragraph_span_round_trips_into_source():
    doc = TextDoc.from_text(_DOC)
    for para in doc.paragraphs:
        start, end = para.span
        assert _DOC[start:end] == para.original_text
        assert para.end_offset == end


def test_sentence_span_round_trips_for_verbatim_prose():
    doc = TextDoc.from_text(_DOC)
    for _index, sent in doc.sent_iter():
        start, end = sent.span
        assert _DOC[start:end] == sent.text


def test_source_text_is_retained_verbatim():
    doc = TextDoc.from_text(_DOC)
    assert doc.source_text == _DOC


def test_block_at_offset():
    doc = TextDoc.from_text(_DOC)
    assert doc.block_at_offset(0) is doc.paragraphs[0]
    inside = _DOC.index("Another paragraph")
    assert doc.block_at_offset(inside) is doc.paragraphs[-1]
    # An offset in the blank-line gap between blocks, and one past the end, map to nothing.
    assert doc.block_at_offset(len(_DOC) + 5) is None


def test_sentence_at_offset():
    doc = TextDoc.from_text(_DOC)
    idx = doc.sentence_at_offset(_DOC.index("Second sentence"))
    assert idx is not None
    assert idx == SentIndex(1, 1)
    assert doc.get_sent(idx).text == "Second sentence here."
    assert doc.sentence_at_offset(len(_DOC) + 5) is None


def test_sub_doc_and_filtered_preserve_source_text():
    doc = TextDoc.from_text(_DOC)
    assert doc.sub_doc(SentIndex(0, 0), SentIndex(0, 0)).source_text == _DOC
    assert doc.sub_paras(0, 0).source_text == _DOC
    assert doc.filtered(include={BlockType.paragraph}).source_text == _DOC


def test_from_wordtoks_has_reassembled_source_text():
    doc = TextDoc.from_text(_DOC)
    rebuilt = TextDoc.from_wordtoks(list(doc.as_wordtoks()))
    # Synthetic docs have no original source; source_text is the reassembled text.
    assert rebuilt.source_text == rebuilt.reassemble()


def test_sentence_spans_exact_with_irregular_whitespace_and_links():
    # Double space between sentences + an inline link: spans must round-trip exactly
    # (verbatim) and a sentence boundary must never bisect the link.
    text = "First sentence here.  Second [linked](http://x.com) sentence ends now."
    doc = TextDoc.from_text(text)
    sents = [sent for _index, sent in doc.sent_iter()]
    assert len(sents) == 2
    for sent in sents:
        assert sent.original_text is not None
        start, end = sent.span
        assert text[start:end] == sent.original_text
    assert sents[1].original_text is not None
    assert "[linked](http://x.com)" in sents[1].original_text


def test_spans_consistent_with_offsets_and_sizes():
    doc = TextDoc.from_text(_DOC)
    para = doc.paragraphs[1]
    assert para.span[0] == para.offsets.doc_offset
    assert para.span[1] - para.span[0] == para.size(TextUnit.chars)
