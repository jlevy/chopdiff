from chopdiff.docs.text_doc import SentIndex, TextDoc
from chopdiff.docs.wordtoks import BOF_TOK, EOF_TOK


def test_sub_doc_is_independent_copy():
    doc = TextDoc.from_text(
        "The first sentence here. The second sentence here.\n\nAnother paragraph here now."
    )
    before = doc.reassemble()
    sub = doc.sub_doc(SentIndex(0, 0), SentIndex(0, 0))
    sub.paragraphs[0].sentences[0].text = "MUTATED."
    assert "MUTATED" not in doc.reassemble()
    assert doc.reassemble() == before


def test_sub_paras_is_independent_copy():
    doc = TextDoc.from_text("Paragraph one here today.\n\nParagraph two here today.")
    before = doc.reassemble()
    sub = doc.sub_paras(0, 0)
    sub.paragraphs[0].sentences[0].text = "MUTATED."
    assert "MUTATED" not in doc.reassemble()
    assert doc.reassemble() == before


def test_empty_doc_as_wordtoks_bof_eof():
    doc = TextDoc.from_text("")
    # Empty doc with boundary tokens yields just BOF/EOF (mapped to a sentinel), no crash.
    assert list(doc.as_wordtoks(bof_eof=True)) == [BOF_TOK, EOF_TOK]
    assert list(doc.as_wordtoks(bof_eof=False)) == []
    # The wordtok->sentence mapping is also stable on an empty doc.
    assert [tok for tok, _idx in doc.as_wordtok_to_sent(bof_eof=True)] == [BOF_TOK, EOF_TOK]
