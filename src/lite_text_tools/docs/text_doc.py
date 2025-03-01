"""
Tools for handling documents consisting of sentences and paragraphs of text.
Compatible with Markdown.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pprint import pprint
from textwrap import dedent
from typing import Callable, Dict, Generator, Iterable, List, Optional, Tuple, TypeAlias

import regex
from flowmark.sentence_split_regex import split_sentences_regex
from funlog import tally_calls
from prettyfmt import fmt_words
from strif import abbrev_str

from .sizes import size, size_in_bytes, TextUnit
from .tiktoken_utils import tiktoken_len
from .wordtoks import (
    BOF_TOK,
    EOF_TOK,
    is_break_or_space,
    is_entity,
    is_header_tag,
    is_number,
    is_tag,
    is_word,
    join_wordtoks,
    PARA_BR_STR,
    PARA_BR_TOK,
    raw_text_to_wordtoks,
    SENT_BR_STR,
    SENT_BR_TOK,
    visualize_wordtoks,
    wordtok_len,
)


SYMBOL_PARA = "¶"

SYMBOL_SENT = "S"

Splitter: TypeAlias = Callable[[str], List[str]]

default_sentence_splitter: Splitter = split_sentences_regex
"""
The default sentence splitter. Can be replaced with a more advanced splitter like
Spacy. We default to the regex splitter because it's usable (in English), eliminates
the need for a dependency on Spacy, and is much faster than Spacy.
"""


def is_markdown_header(markdown: str) -> bool:
    """
    Is the start of this content a Markdown header?
    """
    return regex.match(r"^#+ ", markdown) is not None


@dataclass(frozen=True, order=True)
class SentIndex:
    """
    Point to a sentence in a TextDoc.
    """

    para_index: int
    sent_index: int

    def __str__(self):
        return f"{SYMBOL_PARA}{self.para_index},{SYMBOL_SENT}{self.sent_index}"


WordtokMapping: TypeAlias = Dict[int, SentIndex]
"""A mapping from wordtok index to sentences in a TextDoc."""

SentenceMapping: TypeAlias = Dict[SentIndex, List[int]]
"""A mapping from sentence index to wordtoks in a TextDoc."""


@dataclass
class Sentence:
    text: str
    char_offset: int  # Offset of the sentence in the original text.

    def size(self, unit: TextUnit) -> int:
        return size(self.text, unit)

    def as_wordtoks(self) -> List[str]:
        return raw_text_to_wordtoks(self.text)

    def is_markup(self) -> bool:
        """
        Is this sentence all markup, e.g. a <span> or <div> tag or some other content with no words?
        """
        wordtoks = self.as_wordtoks()
        is_all_markup = all(
            is_tag(wordtok) or is_break_or_space(wordtok) for wordtok in wordtoks
        )
        if is_all_markup:
            return True
        is_markup_no_words = (
            len(wordtoks) > 2
            and is_tag(wordtoks[0])
            and is_tag(wordtoks[-1])
            and all(not is_word(wordtok) for wordtok in wordtoks[1:-1])
        )
        if is_markup_no_words:
            return True
        return False

    def __str__(self):
        return repr(self.text)


@dataclass
class Paragraph:
    original_text: str
    sentences: List[Sentence]
    char_offset: int  # Offset of the paragraph in the original text.

    @classmethod
    @tally_calls(level="warning", min_total_runtime=5)
    def from_text(
        cls,
        text: str,
        char_offset: int = -1,
        sentence_splitter: Splitter = default_sentence_splitter,
    ) -> "Paragraph":
        # TODO: Lazily compute sentences for better performance.
        sent_values = sentence_splitter(text)
        sent_offset = 0
        sentences = []
        for sent_str in sent_values:
            sentences.append(Sentence(sent_str, sent_offset))
            sent_offset += len(sent_str) + len(SENT_BR_STR)
        return cls(original_text=text, sentences=sentences, char_offset=char_offset)

    def reassemble(self) -> str:
        return SENT_BR_STR.join(sent.text for sent in self.sentences)

    def replace_str(self, old: str, new: str):
        for sent in self.sentences:
            sent.text = sent.text.replace(old, new)

    def sent_iter(self, reverse: bool = False) -> Iterable[Tuple[int, Sentence]]:
        enum_sents = list(enumerate(self.sentences))
        return reversed(enum_sents) if reverse else enum_sents

    def size(self, unit: TextUnit) -> int:
        if unit == TextUnit.lines:
            return len(self.original_text.splitlines())
        if unit == TextUnit.paragraphs:
            return 1
        if unit == TextUnit.sentences:
            return len(self.sentences)

        if unit == TextUnit.tiktokens:
            return tiktoken_len(self.reassemble())

        base_size = sum(sent.size(unit) for sent in self.sentences)
        if unit == TextUnit.bytes:
            return base_size + (len(self.sentences) - 1) * size_in_bytes(SENT_BR_STR)
        if unit == TextUnit.chars:
            return base_size + (len(self.sentences) - 1) * len(SENT_BR_STR)
        if unit == TextUnit.words:
            return base_size
        if unit == TextUnit.wordtoks:
            return base_size + (len(self.sentences) - 1)

        raise ValueError(f"Unsupported unit for Paragraph: {unit}")

    def as_wordtok_to_sent(self) -> Generator[Tuple[str, int], None, None]:
        last_sent_index = len(self.sentences) - 1
        for sent_index, sent in enumerate(self.sentences):
            for wordtok in sent.as_wordtoks():
                yield wordtok, sent_index
            if sent_index != last_sent_index:
                yield SENT_BR_TOK, sent_index

    def as_wordtoks(self) -> Generator[str, None, None]:
        for wordtok, _ in self.as_wordtok_to_sent():
            yield wordtok

    def is_markup(self) -> bool:
        """
        Is this paragraph all markup, e.g. a <div> tag as a paragraph by itself?
        """
        return all(sent.is_markup() for sent in self.sentences)

    def is_header(self) -> bool:
        """
        Is this paragraph a Markdown or HTML header tag?
        """
        first_wordtok = next(self.as_wordtoks(), None)
        is_html_header = (
            first_wordtok and is_tag(first_wordtok) and is_header_tag(first_wordtok)
        )
        return is_html_header or is_markdown_header(self.original_text)


@dataclass
class TextDoc:
    paragraphs: List[Paragraph]

    @classmethod
    @tally_calls(level="warning", min_total_runtime=5)
    def from_text(
        cls, text: str, sentence_splitter: Splitter = default_sentence_splitter
    ) -> "TextDoc":
        text = text.strip()
        paragraphs = []
        char_offset = 0
        for para in text.split(PARA_BR_STR):
            stripped_para = para.strip()
            if stripped_para:
                paragraphs.append(
                    Paragraph.from_text(stripped_para, char_offset, sentence_splitter)
                )
                char_offset += len(para) + len(PARA_BR_STR)
        return cls(paragraphs=paragraphs)

    @classmethod
    def from_wordtoks(cls, wordtoks: List[str]) -> "TextDoc":
        return TextDoc.from_text(join_wordtoks(wordtoks))

    def reassemble(self) -> str:
        return PARA_BR_STR.join(paragraph.reassemble() for paragraph in self.paragraphs)

    def replace_str(self, old: str, new: str):
        for para in self.paragraphs:
            para.replace_str(old, new)

    def first_index(self) -> SentIndex:
        return SentIndex(0, 0)

    def last_index(self) -> SentIndex:
        return SentIndex(
            len(self.paragraphs) - 1, len(self.paragraphs[-1].sentences) - 1
        )

    def para_iter(self, reverse: bool = False) -> Iterable[Tuple[int, Paragraph]]:
        enum_paras = list(enumerate(self.paragraphs))
        return reversed(enum_paras) if reverse else enum_paras

    def sent_iter(self, reverse: bool = False) -> Iterable[Tuple[SentIndex, Sentence]]:
        for para_index, para in self.para_iter(reverse=reverse):
            for sent_index, sent in para.sent_iter(reverse=reverse):
                yield SentIndex(para_index, sent_index), sent

    def get_sent(self, index: SentIndex) -> Sentence:
        return self.paragraphs[index.para_index].sentences[index.sent_index]

    def set_sent(self, index: SentIndex, sent_str: str) -> None:
        old_sent = self.get_sent(index)
        self.paragraphs[index.para_index].sentences[index.sent_index] = Sentence(
            sent_str, old_sent.char_offset
        )

    def seek_to_sent(self, offset: int, unit: TextUnit) -> Tuple[SentIndex, int]:
        """
        Find the last sentence that starts before a given offset. Returns the SentIndex
        and the offset of the sentence start in the original document.
        """
        current_size = 0
        last_fit_index = None
        last_fit_offset = 0

        if unit == TextUnit.bytes:
            size_sent_break = size_in_bytes(SENT_BR_STR)
            size_para_break = size_in_bytes(PARA_BR_STR)
        elif unit == TextUnit.chars:
            size_sent_break = len(SENT_BR_STR)
            size_para_break = len(PARA_BR_STR)
        elif unit == TextUnit.words:
            size_sent_break = 0
            size_para_break = 0
        elif unit == TextUnit.wordtoks:
            size_sent_break = 1
            size_para_break = 1
        else:
            raise NotImplementedError(f"Unsupported unit for seek_doc: {unit}")

        for para_index, para in enumerate(self.paragraphs):
            for sent_index, sent in enumerate(para.sentences):
                sentence_size = sent.size(unit)
                last_fit_index = SentIndex(para_index, sent_index)
                last_fit_offset = current_size
                if current_size + sentence_size + size_sent_break <= offset:
                    current_size += sentence_size
                    if sent_index < len(para.sentences) - 1:
                        current_size += size_sent_break
                else:
                    return last_fit_index, last_fit_offset
            if para_index < len(self.paragraphs) - 1:
                current_size += size_para_break

        if last_fit_index is None:
            raise ValueError("Cannot seek into empty document")

        return last_fit_index, last_fit_offset

    def sub_doc(self, first: SentIndex, last: Optional[SentIndex] = None) -> "TextDoc":
        """
        Get a sub-document. Inclusive ranges. Preserves original paragraph and sentence offsets.
        """
        if not last:
            last = self.last_index()
        if last > self.last_index():
            raise ValueError(f"End index out of range: {last} > {self.last_index()}")
        if first < self.first_index():
            raise ValueError(
                f"Start index out of range: {first} < {self.first_index()}"
            )

        sub_paras = []
        for i in range(first.para_index, last.para_index + 1):
            para = self.paragraphs[i]
            if i == first.para_index and i == last.para_index:
                sub_paras.append(
                    Paragraph(
                        original_text=para.original_text,
                        sentences=para.sentences[
                            first.sent_index : last.sent_index + 1
                        ],
                        char_offset=para.char_offset,
                    )
                )
            elif i == first.para_index:
                sub_paras.append(
                    Paragraph(
                        original_text=para.original_text,
                        sentences=para.sentences[first.sent_index :],
                        char_offset=para.char_offset,
                    )
                )
            elif i == last.para_index:
                sub_paras.append(
                    Paragraph(
                        original_text=para.original_text,
                        sentences=para.sentences[: last.sent_index + 1],
                        char_offset=para.char_offset,
                    )
                )
            else:
                sub_paras.append(para)

        return TextDoc(sub_paras)

    def sub_paras(self, start: int, end: Optional[int] = None) -> "TextDoc":
        """
        Get a sub-document containing a range of paragraphs.
        """
        if end is None:
            end = len(self.paragraphs) - 1
        return TextDoc(self.paragraphs[start : end + 1])

    def prev_sent(self, index: SentIndex) -> SentIndex:
        if index.sent_index > 0:
            return SentIndex(index.para_index, index.sent_index - 1)
        elif index.para_index > 0:
            return SentIndex(
                index.para_index - 1,
                len(self.paragraphs[index.para_index - 1].sentences) - 1,
            )
        else:
            raise ValueError("No previous sentence")

    def append_sent(self, sent: Sentence) -> None:
        if len(self.paragraphs) == 0:
            self.paragraphs.append(
                Paragraph(original_text=sent.text, sentences=[sent], char_offset=0)
            )
        else:
            last_para = self.paragraphs[-1]
            last_para.sentences.append(sent)

    def size(self, unit: TextUnit) -> int:
        if unit == TextUnit.paragraphs:
            return len(self.paragraphs)
        if unit == TextUnit.sentences:
            return sum(len(para.sentences) for para in self.paragraphs)

        if unit == TextUnit.tiktokens:
            return tiktoken_len(self.reassemble())

        base_size = sum(para.size(unit) for para in self.paragraphs)
        n_para_breaks = max(len(self.paragraphs) - 1, 0)
        if unit == TextUnit.lines:
            return base_size + n_para_breaks
        if unit == TextUnit.bytes:
            return base_size + n_para_breaks * size_in_bytes(PARA_BR_STR)
        if unit == TextUnit.chars:
            return base_size + n_para_breaks * len(PARA_BR_STR)
        if unit == TextUnit.words:
            return base_size
        if unit == TextUnit.wordtoks:
            return base_size + n_para_breaks

        raise ValueError(f"Unsupported unit for TextDoc: {unit}")

    def size_summary(self) -> str:
        nbytes = self.size(TextUnit.bytes)
        if nbytes > 0:
            return (
                f"{nbytes} bytes ("
                f"{self.size(TextUnit.lines)} lines, "
                f"{self.size(TextUnit.paragraphs)} paragraphs, "
                f"{self.size(TextUnit.sentences)} sentences, "
                f"{self.size(TextUnit.words)} words, "
                # f"{self.size(TextUnit.wordtoks)} wordtoks, "
                f"{self.size(TextUnit.tiktokens)} tiktokens)"
            )
        else:
            return f"{nbytes} bytes"

    def as_wordtok_to_sent(
        self, bof_eof=False
    ) -> Generator[Tuple[str, SentIndex], None, None]:
        if bof_eof:
            yield BOF_TOK, self.first_index()

        last_para_index = len(self.paragraphs) - 1
        for para_index, para in enumerate(self.paragraphs):
            for wordtok, sent_index in para.as_wordtok_to_sent():
                yield wordtok, SentIndex(para_index, sent_index)
            if para_index != last_para_index:
                yield PARA_BR_TOK, SentIndex(para_index, len(para.sentences) - 1)

        if bof_eof:
            yield EOF_TOK, self.last_index()

    def as_wordtoks(self, bof_eof=False) -> Generator[str, None, None]:
        for wordtok, _sent_index in self.as_wordtok_to_sent(bof_eof=bof_eof):
            yield wordtok

    def wordtok_mappings(self) -> Tuple[WordtokMapping, SentenceMapping]:
        """
        Get mappings between wordtok indexes and sentence indexes.
        """
        sent_indexes = [
            sent_index for _wordtok, sent_index in self.as_wordtok_to_sent()
        ]

        wordtok_mapping = {i: sent_index for i, sent_index in enumerate(sent_indexes)}

        sent_mapping = defaultdict(list)
        for i, sent_index in enumerate(sent_indexes):
            sent_mapping[sent_index].append(i)

        return wordtok_mapping, sent_mapping

    def __str__(self):
        return f"TextDoc({self.size_summary()})"


## Tests

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
    def normalize(text):
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
    result = []
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
    assert doc.paragraphs[-2].is_markup() == True
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

    assert (
        size_summary
        == "726 bytes (37 lines, 16 paragraphs, 20 sentences, 82 words, 215 tiktokens)"
    )


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
    assert sent_offset == len(
        "This is the first paragraph. It has multiple sentences.\n\n"
    )

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
        wordtoks = raw_text_to_wordtoks(sentence)
        reassembled_sentence = "".join(wordtoks)
        assert reassembled_sentence == sentence

    assert raw_text_to_wordtoks(
        "Multiple     spaces and tabs\tand\nnewlines in between."
    ) == [
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
    assert raw_text_to_wordtoks("") == []
    assert raw_text_to_wordtoks("   ") == [" "]

    assert raw_text_to_wordtoks(_sentence_test_html) == [
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
        wordtok_len(wordtok) for wordtok in raw_text_to_wordtoks(_sentence_test_html)
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
