from textwrap import dedent

from chopdiff.docs.text_doc import SentIndex, TextDoc


def test_paragraph_offsets_reference_original_text():
    # Leading newlines, extra blank lines between paragraphs, and trailing space:
    # offsets must still index the unmodified input back to each paragraph.
    text = "\n\n# Title\n\n\n\nFirst paragraph. Second sentence.\n\nLast one.\n\n"
    doc = TextDoc.from_text(text)
    for p in doc.paragraphs:
        assert text[p.char_offset : p.char_offset + len(p.original_text)] == p.original_text


def test_sentence_offsets_reference_paragraph_text():
    # Irregular inter-sentence spacing: find-based offsets stay exact.
    doc = TextDoc.from_text("First sentence here.  Second one follows.")
    para = doc.paragraphs[0]
    assert len(para.sentences) == 2
    for s in para.sentences:
        assert para.original_text[s.char_offset : s.char_offset + len(s.text)] == s.text


def test_char_offset_in_doc_references_the_document():
    text = "Intro para.\n\nSecond para. It has two sentences."
    doc = TextDoc.from_text(text)
    for para_i, para in enumerate(doc.paragraphs):
        for sent_i, sent in enumerate(para.sentences):
            abs_off = doc.char_offset_in_doc(SentIndex(para_i, sent_i))
            assert text[abs_off : abs_off + len(sent.text)] == sent.text


def test_offsets_are_into_unstripped_input():
    # No doc-level strip: the offset points past the leading whitespace to the
    # actual content in the original string.
    text = "\n\n   Indented start. Next.\n"
    doc = TextDoc.from_text(text)
    p = doc.paragraphs[0]
    assert p.original_text == "Indented start. Next."
    assert text[p.char_offset :].startswith("Indented start.")


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
    table = doc.paragraphs[1]
    assert text[table.char_offset : table.char_offset + len(table.original_text)] == (
        table.original_text
    )
