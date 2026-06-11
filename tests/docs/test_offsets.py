from textwrap import dedent

from flexdoc.docs.text_doc import TextDoc


def _assert_offsets_round_trip(text: str, doc: TextDoc) -> None:
    """
    Paragraph offsets must reference `text` exactly. Sentence `doc_offset` is always
    `paragraph.doc_offset + block_offset`; the slice round-trips when the sentence is
    a verbatim slice of the paragraph (true for prose, but sentence splitters may
    normalize whitespace inside non-prose blocks like tables).
    """
    for para in doc.paragraphs:
        p_start = para.offsets.doc_offset
        assert text[p_start : p_start + len(para.original_text)] == para.original_text
        # A paragraph's enclosing block is the document, so block_offset == doc_offset.
        assert para.offsets.block_offset == para.offsets.doc_offset
        for sent in para.sentences:
            assert sent.offsets.doc_offset == para.offsets.doc_offset + sent.offsets.block_offset
            if sent.text in para.original_text:
                bo = sent.offsets.block_offset
                assert para.original_text[bo : bo + len(sent.text)] == sent.text
                do = sent.offsets.doc_offset
                assert text[do : do + len(sent.text)] == sent.text


def test_paragraph_and_sentence_offsets_reference_original_text():
    text = "Intro para. Second sentence.\n\nSecond para. It has two sentences."
    _assert_offsets_round_trip(text, TextDoc.from_text(text))


def test_irregular_inter_sentence_spacing():
    doc = TextDoc.from_text("First sentence here.  Second one follows.")
    para = doc.paragraphs[0]
    assert len(para.sentences) == 2
    _assert_offsets_round_trip("First sentence here.  Second one follows.", doc)


def test_offsets_are_into_unstripped_input():
    # No doc-level strip: offsets point past leading whitespace to the content.
    text = "\n\n   Indented start. Next.\n"
    doc = TextDoc.from_text(text)
    p = doc.paragraphs[0]
    assert p.original_text == "Indented start. Next."
    assert text[p.offsets.doc_offset :].startswith("Indented start.")
    _assert_offsets_round_trip(text, doc)


# Paragraph splitting: blank lines are two or more newlines (including blank lines
# that contain only whitespace). Splitting must not alter content or offsets.


def test_three_or_more_newlines_collapse_to_one_break():
    for n in range(2, 7):
        text = "First para." + ("\n" * n) + "Second para."
        doc = TextDoc.from_text(text)
        assert [p.original_text for p in doc.paragraphs] == ["First para.", "Second para."]
        _assert_offsets_round_trip(text, doc)


def test_whitespace_only_blank_line_is_a_break():
    # A blank line containing a space/tab still separates paragraphs.
    text = "First para.\n \nSecond para.\n\t\nThird para."
    doc = TextDoc.from_text(text)
    assert [p.original_text for p in doc.paragraphs] == [
        "First para.",
        "Second para.",
        "Third para.",
    ]
    _assert_offsets_round_trip(text, doc)


def test_single_newline_is_not_a_break():
    text = "Line one continues\nonto line two."
    doc = TextDoc.from_text(text)
    assert len(doc.paragraphs) == 1


def test_leading_and_trailing_whitespace():
    for text in [
        "\n\n\nOnly para.",
        "Only para.\n\n\n",
        "   \n\n  Only para.  \n\n   ",
        "Only para.",
    ]:
        doc = TextDoc.from_text(text)
        assert [p.original_text for p in doc.paragraphs] == ["Only para."]
        _assert_offsets_round_trip(text, doc)


def test_whitespace_only_document_has_no_paragraphs():
    assert TextDoc.from_text("   \n\n  \t\n").paragraphs == []


def test_multiline_block_offset_round_trips():
    text = dedent(
        """
        Intro.

        | Col A | Col B |
        | ----- | ----- |
        | x     | y     |
        """
    ).strip()
    doc = TextDoc.from_text(text)
    assert len(doc.paragraphs) == 2
    _assert_offsets_round_trip(text, doc)
