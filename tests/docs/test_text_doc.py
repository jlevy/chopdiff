from pprint import pprint
from textwrap import dedent

import regex
from prettyfmt import fmt_words
from strif import abbrev_str

from chopdiff.docs.sizes import TextUnit
from chopdiff.docs.text_doc import SentIndex, TextDoc
from chopdiff.docs.wordtoks import (
    PARA_BR_TOK,
    is_break_or_space,
    is_entity,
    is_header_tag,
    is_number,
    is_tag,
    is_word,
    join_wordtoks,
    visualize_wordtoks,
    wordtok_len,
    wordtokenize,
)

_med_test_doc = dedent(
    """
        # Title

        Hello World. This is an example sentence. And here's another one!

        ## Subtitle

        This is a new paragraph.
        It has several sentences.
        There may be line breaks within a paragraph, but these should not affect handlingof the paragraph.
        There are also [links](http://www.google.com) and **bold** and *italic* text.

        ### Itemized List

        - Item 1

        - Item 2

        - Item 3

        ### Numbered List

        1. Item 1

        2. Item 2

        3. Item 3

        Testing some embedded HTML tags.

        <h3>An HTML header</h3>

        <!--window-br-->
        
        <span class="citation timestamp-link"
        data-src="resources/https_www_youtube_com_watch_v_da_2h2b4fau.resource.yml"
        data-timestamp="352.81">⏱️<a
        href="https://www.youtube.com/watch?v=Da-2h2B4faU&t=352.81s">05:52</a>&nbsp;</span>

        """
).strip()


def test_document_parse_reassemble():
    text = _med_test_doc
    doc = TextDoc.from_text(text)

    print("\n---Original:")
    pprint(text)
    print("\n---Parsed:")
    pprint(doc)

    reassembled_text = doc.reassemble()

    # Should be exactly the same except for within-paragraph line breaks.
    def normalize(text: str) -> str:
        return regex.sub(r"\s+", " ", text.replace("\n\n", "<PARA>"))

    assert normalize(reassembled_text) == normalize(text)

    # Check offset of a paragraph towards the end of the document.
    last_para = doc.paragraphs[-1]
    last_para_char_offset = text.rindex(last_para.original_text)
    assert last_para.char_offset == last_para_char_offset


def test_markup_detection():
    text = _med_test_doc
    doc = TextDoc.from_text(text)

    print("Paragraph markup and header detection:")
    result: list[str] = []
    for para in doc.paragraphs:
        result.append(
            fmt_words(
                abbrev_str(para.original_text, 10),
                "is_markup" if para.is_markup() else "",
                "is_header" if para.is_header() else "",
            )
        )

    print("\n".join(result))
    assert (
        "\n".join(result)
        == dedent(
            """
            # Title is_header
            Hello Wor…
            ## Subtit… is_header
            This is a…
            ### Itemi… is_header
            - Item 1
            - Item 2
            - Item 3
            ### Numbe… is_header
            1. Item 1
            2. Item 2
            3. Item 3
            Testing s…
            <h3>An HT… is_header
            <!--windo… is_markup
            <span cla… is_markup
            """
        ).strip()
    )

    print("Last paragraphs:")
    print(list(doc.paragraphs[-2].as_wordtoks()))
    print(list(doc.paragraphs[-1].as_wordtoks()))

    wordtoks = doc.paragraphs[-1].as_wordtoks()
    result = []
    for wordtok in wordtoks:
        result.append(
            fmt_words(
                visualize_wordtoks([wordtok]),
                "is_break_or_space" if is_break_or_space(wordtok) else "",
                "is_word" if is_word(wordtok) else "",
                "is_number" if is_number(wordtok) else "",
                "is_tag" if is_tag(wordtok) else "",
                "is_header_tag" if is_header_tag(wordtok) else "",
                "is_entity" if is_entity(wordtok) else "",
            )
        )
    print("\n".join(result))

    assert (
        "\n".join(result)
        == dedent(
            """
            ⎪<span class="citation timestamp-link" data-src="resources/https_www_youtube_com_watch_v_da_2h2b4fau.resource.yml" data-timestamp="352.81">⎪ is_tag
            ⎪⏱⎪
            ⎪️⎪
            ⎪<a href="https://www.youtube.com/watch?v=Da-2h2B4faU&t=352.81s">⎪ is_tag
            ⎪05⎪ is_number
            ⎪:⎪
            ⎪52⎪ is_number
            ⎪</a>⎪ is_tag
            ⎪&nbsp;⎪ is_entity
            ⎪</span>⎪ is_tag
            """
        ).strip()
    )

    assert doc.paragraphs[-2].sentences[0].text == "<!--window-br-->"
    assert doc.paragraphs[-2].is_markup()
    assert doc.paragraphs[-1].sentences[-1].is_markup()


_simple_test_doc = dedent(
    """
    This is the first paragraph. It has multiple sentences.

    This is the second paragraph. It also has multiple sentences. And it continues.
    
    Here is the third paragraph. More sentences follow. And here is another one.
    """
).strip()


def test_doc_sizes():
    text = _med_test_doc
    doc = TextDoc.from_text(text)
    print("\n---Sizes:")
    size_summary = doc.size_summary()
    print(size_summary)

    assert size_summary == "726 bytes (37 lines, 16 paras, 20 sents, 82 words, 215 tiktoks)"


def test_seek_doc():
    doc = TextDoc.from_text(_simple_test_doc)

    offset = 1
    sent_index, sent_offset = doc.seek_to_sent(offset, TextUnit.bytes)
    print(f"Seeked to {sent_index} offset {sent_offset} for offset {offset} bytes")
    assert sent_index == SentIndex(para_index=0, sent_index=0)
    assert sent_offset == 0

    offset = len("This is the first paragraph.")
    sent_index, sent_offset = doc.seek_to_sent(offset, TextUnit.bytes)
    print(f"Seeked to {sent_index} offset {sent_offset} for offset {offset} bytes")
    assert sent_index == SentIndex(para_index=0, sent_index=0)
    assert sent_offset == 0

    offset = len("This is the first paragraph. ")
    sent_index, sent_offset = doc.seek_to_sent(offset, TextUnit.bytes)
    print(f"Seeked to {sent_index} offset {sent_offset} for offset {offset} bytes")
    assert sent_index == SentIndex(para_index=0, sent_index=1)
    assert sent_offset == offset

    offset = len(
        "This is the first paragraph. It has multiple sentences.\n\nThis is the second paragraph."
    )
    sent_index, sent_offset = doc.seek_to_sent(offset, TextUnit.bytes)
    print(f"Seeked to {sent_index} offset {sent_offset} for offset {offset} bytes")
    assert sent_index == SentIndex(para_index=1, sent_index=0)
    assert sent_offset == len("This is the first paragraph. It has multiple sentences.\n\n")

    offset = len(_simple_test_doc) + 10
    sent_index, sent_offset = doc.seek_to_sent(offset, TextUnit.bytes)
    print(f"Seeked to {sent_index} offset {sent_offset} for offset {offset} bytes")
    assert sent_index == SentIndex(para_index=2, sent_index=2)


_short_test_doc = dedent(
    """
    Paragraph one lorem ipsum.
    Sentence 1a lorem ipsum. Sentence 1b lorem ipsum. Sentence 1c lorem ipsum.
    
    Paragraph two lorem ipsum. Sentence 2a lorem ipsum. Sentence 2b lorem ipsum. Sentence 2c lorem ipsum.
    
    Paragraph three lorem ipsum. Sentence 3a lorem ipsum. Sentence 3b lorem ipsum. Sentence 3c lorem ipsum.
    """
).strip()


def test_sub_doc():
    doc = TextDoc.from_text(_short_test_doc)

    sub_doc_start = SentIndex(1, 1)
    sub_doc_end = SentIndex(2, 1)
    sub_doc = doc.sub_doc(sub_doc_start, sub_doc_end)

    expected_text = dedent(
        """
        Sentence 2a lorem ipsum. Sentence 2b lorem ipsum. Sentence 2c lorem ipsum.
        
        Paragraph three lorem ipsum. Sentence 3a lorem ipsum.
        """
    ).strip()
    expected_sub_doc = TextDoc.from_text(expected_text)

    print("---Original:")
    pprint(doc)
    print("---Subdoc:")
    pprint(sub_doc)

    # Confirm reassembled text is correct.
    assert sub_doc.reassemble() == expected_sub_doc.reassemble()

    # Confirm sentences and offsets are preserved in sub-doc.
    orig_sentences = [sent for _index, sent in doc.sent_iter()]
    sub_sentences = [sent for _index, sent in sub_doc.sent_iter()]
    assert orig_sentences[5:10] == sub_sentences

    # Confirm indexing and reverse iteration.
    assert doc.sub_doc(SentIndex(0, 0), None) == doc
    reversed_sentences = [sent for _index, sent in doc.sent_iter(reverse=True)]
    assert reversed_sentences == list(reversed(orig_sentences))


def test_tokenization():
    doc = TextDoc.from_text(_short_test_doc)
    wordtoks = list(doc.as_wordtoks())

    print("\n---Tokens:")
    pprint(wordtoks)

    assert wordtoks[:6] == ["Paragraph", " ", "one", " ", "lorem", " "]
    assert wordtoks[-7:] == [" ", "3c", " ", "lorem", " ", "ipsum", "."]
    assert wordtoks.count(PARA_BR_TOK) == 2
    assert join_wordtoks(wordtoks) == _short_test_doc.replace(
        "\n", " ", 1
    )  # First \n is not a para break.


def test_wordtok_mappings():
    doc = TextDoc.from_text(_short_test_doc)

    print("\n---Mapping:")
    wordtok_mapping, sent_mapping = doc.wordtok_mappings()
    pprint(wordtok_mapping)
    pprint(sent_mapping)

    assert wordtok_mapping[0] == SentIndex(0, 0)
    assert wordtok_mapping[1] == SentIndex(0, 0)
    assert wordtok_mapping[4] == SentIndex(0, 0)
    assert wordtok_mapping[9] == SentIndex(0, 1)

    assert sent_mapping[SentIndex(0, 0)] == [0, 1, 2, 3, 4, 5, 6, 7, 8]
    assert sent_mapping[SentIndex(2, 3)] == [99, 100, 101, 102, 103, 104, 105, 106]


_sentence_tests = [
    "Hello, world!",
    "This is an example sentence with punctuation.",
    "And here's another one!",
    "Special characters: @#%^&*()",
]

_sentence_test_html = 'This is <span data-timestamp="1.234">a test</span>.'


def test_wordtokization():
    for sentence in _sentence_tests:
        wordtoks = wordtokenize(sentence)
        reassembled_sentence = "".join(wordtoks)
        assert reassembled_sentence == sentence

    assert wordtokenize("Multiple     spaces and tabs\tand\nnewlines in between.") == [
        "Multiple",
        " ",
        "spaces",
        " ",
        "and",
        " ",
        "tabs",
        " ",
        "and",
        " ",
        "newlines",
        " ",
        "in",
        " ",
        "between",
        ".",
    ]
    assert wordtokenize("") == []
    assert wordtokenize("   ") == [" "]

    assert wordtokenize(_sentence_test_html) == [
        "This",
        " ",
        "is",
        " ",
        '<span data-timestamp="1.234">',
        "a",
        " ",
        "test",
        "</span>",
        ".",
    ]

    assert len(_sentence_test_html) == sum(
        wordtok_len(wordtok) for wordtok in wordtokenize(_sentence_test_html)
    )


def test_html_tokenization():
    doc = TextDoc.from_text(_sentence_test_html)
    wordtoks = list(doc.as_wordtoks())

    print("\n---HTML Tokens:")
    pprint(wordtoks)

    assert wordtoks == [
        "This",
        " ",
        "is",
        " ",
        '<span data-timestamp="1.234">',
        "a",
        " ",
        "test",
        "</span>",
        ".",
    ]
    assert list(map(is_tag, wordtoks)) == [
        False,
        False,
        False,
        False,
        True,
        False,
        False,
        False,
        True,
        False,
    ]
    assert list(map(is_break_or_space, wordtoks)) == [
        False,
        True,
        False,
        True,
        False,
        False,
        True,
        False,
        False,
        False,
    ]


def test_tiktoken_len():
    doc = TextDoc.from_text(_med_test_doc)

    len = doc.size(TextUnit.tiktokens)
    print("--Tiktoken len:")
    print(len)

    assert len > 100
