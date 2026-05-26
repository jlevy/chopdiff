from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Generator, Iterable, Iterator
from copy import deepcopy
from dataclasses import dataclass
from enum import StrEnum
from functools import cache, cached_property
from typing import TypeAlias

import regex
from flowmark import flowmark_markdown, split_sentences_regex
from funlog import tally_calls
from marko import Markdown
from marko.block import (
    BlankLine,
    CodeBlock,
    FencedCode,
    Heading,
    HTMLBlock,
    List,
    Quote,
    SetextHeading,
)
from marko.ext.footnote import FootnoteDef
from marko.ext.gfm.elements import Table
from typing_extensions import override

from chopdiff.docs.sizes import TextUnit, size, size_in_bytes
from chopdiff.docs.wordtoks import (
    BOF_TOK,
    EOF_TOK,
    PARA_BR_STR,
    PARA_BR_TOK,
    SENT_BR_STR,
    SENT_BR_TOK,
    is_break_or_space,
    is_header_tag,
    is_tag,
    is_word,
    join_wordtoks,
    wordtokenize,
)
from chopdiff.util.tiktoken_utils import tiktoken_len

SYMBOL_PARA = "¶"

SYMBOL_SENT = "S"

FOOTNOTE_DEF_REGEX = regex.compile(r"^\[\^[^\]]+\]:")

Splitter: TypeAlias = Callable[[str], list[str]]

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


class BlockType(StrEnum):
    """
    The kind of Markdown block a `Paragraph` represents, determined by parsing the
    block with flowmark's Markdown (marko) parser. This reuses the same parser
    flowmark uses, so GFM tables, footnote definitions, and fenced code (including
    `#` lines inside code) are recognized correctly.

    `TextDoc` splits a document on blank lines, so each block is one
    blank-line-separated unit, and list handling depends on item spacing:

    - A "tight" list (no blank lines between items) is a single `list` block
      containing every item; nested sublists stay inside that one block.
    - A "loose" list (blank lines between items) yields one `list` block per
      item, and nesting is flattened (each item, parent or child, is its own
      block).
    - A continuation paragraph inside a list item (separated by a blank line) is
      classified as `paragraph`, since on its own it carries no list marker.

    Likewise, a fenced code block containing a blank line can be split across
    blocks. For exact block boundaries, preserved nesting, and reliable
    per-list-item granularity, a full-document Markdown parse is required (see
    the BlockDoc plan spec, #8).
    """

    paragraph = "paragraph"
    heading = "heading"
    list = "list"
    table = "table"
    code = "code"
    blockquote = "blockquote"
    html = "html"
    footnote = "footnote"


@cache
def _markdown_parser() -> Markdown:
    """Shared marko parser, configured the same way flowmark configures it."""
    return flowmark_markdown()


def _classify_block(text: str) -> BlockType:
    parsed = _markdown_parser().parse(text)
    element = next((el for el in parsed.children if not isinstance(el, BlankLine)), None)
    if isinstance(element, (Heading, SetextHeading)):
        return BlockType.heading
    if isinstance(element, FootnoteDef):
        return BlockType.footnote
    if isinstance(element, (FencedCode, CodeBlock)):
        return BlockType.code
    if isinstance(element, Quote):
        return BlockType.blockquote
    if isinstance(element, Table):
        return BlockType.table
    if isinstance(element, List):
        return BlockType.list
    if isinstance(element, HTMLBlock):
        return BlockType.html
    return BlockType.paragraph


@dataclass(frozen=True, order=True)
class SentIndex:
    """
    Point to a sentence in a `TextDoc`.
    """

    para_index: int
    sent_index: int

    @override
    def __str__(self):
        return f"{SYMBOL_PARA}{self.para_index},{SYMBOL_SENT}{self.sent_index}"


WordtokMapping: TypeAlias = dict[int, SentIndex]
"""A mapping from wordtok index to sentences in a TextDoc."""

SentenceMapping: TypeAlias = dict[SentIndex, list[int]]
"""A mapping from sentence index to wordtoks in a TextDoc."""


@dataclass
class Sentence:
    """
    A sentence in a `TextDoc`. `text` is the editable content (used by
    `reassemble()`); `char_offset` is a fixed reference to the source set at parse
    time and is not updated by edits.

    `char_offset` follows the `TextDoc` convention: it is relative to the immediate
    parent, which for a sentence is its paragraph (the offset within
    `Paragraph.original_text`). Use `TextDoc.char_offset_in_doc` for the absolute
    offset in the document. See `TextDoc` for the full contract.
    """

    text: str
    char_offset: int  # Offset of the sentence within its paragraph's text.

    def size(self, unit: TextUnit) -> int:
        return size(self.text, unit)

    def as_wordtoks(self) -> list[str]:
        return wordtokenize(self.text)

    def is_markup(self) -> bool:
        """
        Is this sentence all markup, e.g. a <span> or <div> tag or some other content with no words?
        """
        wordtoks = self.as_wordtoks()
        is_all_markup = all(is_tag(wordtok) or is_break_or_space(wordtok) for wordtok in wordtoks)
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

    @override
    def __str__(self):
        return repr(self.text)


@dataclass
class Paragraph:
    """
    A paragraph (one blank-line-separated block) in a `TextDoc`.

    `original_text` and `char_offset` are fixed references to the source as parsed
    and are not updated by edits; `sentences` holds the editable content used by
    `reassemble()`. `block_type` is derived from `original_text` and cached, so it
    assumes `original_text` is not reassigned after construction.

    `char_offset` follows the `TextDoc` convention: it is relative to the immediate
    parent, which for a paragraph is the document, so it is already the absolute
    offset of the paragraph in the document text. See `TextDoc` for the full
    contract.
    """

    original_text: str
    sentences: list[Sentence]
    char_offset: int  # Offset of the paragraph in the document text.

    @classmethod
    @tally_calls(level="warning", min_total_runtime=5)
    def from_text(
        cls,
        text: str,
        char_offset: int = -1,
        sentence_splitter: Splitter = default_sentence_splitter,
    ) -> Paragraph:
        # TODO: Lazily compute sentences for better performance.
        sent_values = sentence_splitter(text)
        sentences: list[Sentence] = []
        cursor = 0
        for sent_str in sent_values:
            # Locate each sentence's exact position within the paragraph so the
            # offset is correct regardless of the original inter-sentence spacing.
            idx = text.find(sent_str, cursor)
            if idx < 0:
                idx = cursor
            sentences.append(Sentence(sent_str, idx))
            cursor = idx + len(sent_str)
        return cls(original_text=text, sentences=sentences, char_offset=char_offset)

    def reassemble(self) -> str:
        return SENT_BR_STR.join(sent.text for sent in self.sentences)

    def replace_str(self, old: str, new: str):
        for sent in self.sentences:
            sent.text = sent.text.replace(old, new)

    def sent_iter(self, reverse: bool = False) -> Iterable[tuple[int, Sentence]]:
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

    def as_wordtok_to_sent(self) -> Generator[tuple[str, int], None, None]:
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
        is_html_header = first_wordtok and is_tag(first_wordtok) and is_header_tag(first_wordtok)
        return is_html_header or is_markdown_header(self.original_text)

    def is_footnote_def(self) -> bool:
        """
        Is this paragraph a Markdown footnote definition block (e.g. "[^id]: text")?
        """
        if len(self.sentences) == 0:
            return False
        initial_text = self.sentences[0].text
        return FOOTNOTE_DEF_REGEX.match(initial_text) is not None

    @cached_property
    def block_type(self) -> BlockType:
        """
        Classify this block by its Markdown kind. See `BlockType` for caveats about
        blank-line splitting (e.g. a list is one block, not one block per item).

        Cached: derived from `original_text`, which does not change after parsing.
        """
        text = self.original_text.strip()
        if not text:
            return BlockType.paragraph
        block_type = _classify_block(text)
        # marko treats a single-line HTML tag as an inline-HTML paragraph rather than
        # an HTML block, so fall back to chopdiff's own markup check for those.
        if block_type == BlockType.paragraph and self.is_markup():
            return BlockType.html
        return block_type


@dataclass
class TextDoc:
    """
    A class for parsing and handling documents consisting of sentences and paragraphs
    of text. Preserves original text, tracking offsets of each sentence and paragraph.
    Compatible with Markdown and Markown with HTML tags.

    Contract and intended use:

    - A `TextDoc` is a snapshot of a *parsed source document*, meant for analysis
      (sizing, classifying, diffing, windowing) and for generating *new* text via
      `reassemble()`. It is not a live, self-updating DOM.

    - Source references are fixed at parse time. `Paragraph.original_text` and the
      `char_offset`s on paragraphs and sentences are exact references into the text
      passed to `from_text` (the input is not normalized) and are not updated when
      content is mutated, so they remain valid as references back to the source.

    - Offset convention: every `char_offset` is relative to the immediate parent.
      A paragraph's parent is the document (so `Paragraph.char_offset` is absolute
      in the document), and a sentence's parent is its paragraph. Use
      `char_offset_in_doc` for a sentence's absolute offset in the document.

    - In-place editing is supported for *building transformed output*: mutate
      sentence text (`replace_str`, `set_sent`) or restructure the paragraph and
      sentence lists (`sub_doc`, `sub_paras`, `filtered`, `append_sent`), then call
      `reassemble()`. This is safe as long as you do not rely on the source
      references tracking your edits: after editing, `original_text`, the
      `char_offset`s, and cached values like `Paragraph.block_type` still describe
      the *original* blocks. To get offsets/classification for edited content,
      re-parse with `TextDoc.from_text(doc.reassemble())`.

    - `filtered()` returns an independent deep copy; `iter_blocks()` and the
      `paragraphs`/`sentences` lists expose this document's live objects.
    """

    paragraphs: list[Paragraph]

    @classmethod
    @tally_calls(level="warning", min_total_runtime=5)
    def from_text(
        cls, text: str, sentence_splitter: Splitter = default_sentence_splitter
    ) -> TextDoc:
        """
        Parse a document from a string. The input is not normalized, so each
        paragraph's `char_offset` is an exact reference into `text`:
        `text[p.char_offset : p.char_offset + len(p.original_text)] == p.original_text`.
        """
        paragraphs: list[Paragraph] = []
        pos = 0
        for piece in text.split(PARA_BR_STR):
            stripped = piece.strip()
            if stripped:
                # Offset of the stripped content within the original text.
                offset = pos + (len(piece) - len(piece.lstrip()))
                paragraphs.append(Paragraph.from_text(stripped, offset, sentence_splitter))
            pos += len(piece) + len(PARA_BR_STR)
        return cls(paragraphs=paragraphs)

    @classmethod
    def from_wordtoks(cls, wordtoks: list[str]) -> TextDoc:
        """
        Parse a document from a list of wordtoks.
        """
        return TextDoc.from_text(join_wordtoks(wordtoks))

    def reassemble(self) -> str:
        """
        Reassemble the document from its paragraphs.
        """
        return PARA_BR_STR.join(paragraph.reassemble() for paragraph in self.paragraphs)

    def replace_str(self, old: str, new: str):
        for para in self.paragraphs:
            para.replace_str(old, new)

    def first_index(self) -> SentIndex:
        return SentIndex(0, 0)

    def last_index(self) -> SentIndex:
        return SentIndex(len(self.paragraphs) - 1, len(self.paragraphs[-1].sentences) - 1)

    def para_iter(self, reverse: bool = False) -> Iterable[tuple[int, Paragraph]]:
        enum_paras = list(enumerate(self.paragraphs))
        return reversed(enum_paras) if reverse else enum_paras

    def sent_iter(self, reverse: bool = False) -> Iterable[tuple[SentIndex, Sentence]]:
        for para_index, para in self.para_iter(reverse=reverse):
            for sent_index, sent in para.sent_iter(reverse=reverse):
                yield SentIndex(para_index, sent_index), sent

    def get_sent(self, index: SentIndex) -> Sentence:
        return self.paragraphs[index.para_index].sentences[index.sent_index]

    def char_offset_in_doc(self, index: SentIndex) -> int:
        """
        Absolute character offset of a sentence in the document, combining the
        paragraph's offset (`Paragraph.char_offset`) with the sentence's
        paragraph-relative offset (`Sentence.char_offset`).
        """
        para = self.paragraphs[index.para_index]
        return para.char_offset + para.sentences[index.sent_index].char_offset

    def set_sent(self, index: SentIndex, sent_str: str) -> None:
        old_sent = self.get_sent(index)
        self.paragraphs[index.para_index].sentences[index.sent_index] = Sentence(
            sent_str, old_sent.char_offset
        )

    def seek_to_sent(self, offset: int, unit: TextUnit) -> tuple[SentIndex, int]:
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

    def sub_doc(self, first: SentIndex, last: SentIndex | None = None) -> TextDoc:
        """
        Get a sub-document. Inclusive ranges. Preserves original paragraph and sentence offsets.
        """
        if not last:
            last = self.last_index()
        if last > self.last_index():
            raise ValueError(f"End index out of range: {last} > {self.last_index()}")
        if first < self.first_index():
            raise ValueError(f"Start index out of range: {first} < {self.first_index()}")

        sub_paras: list[Paragraph] = []
        for i in range(first.para_index, last.para_index + 1):
            para = self.paragraphs[i]
            if i == first.para_index and i == last.para_index:
                sub_paras.append(
                    Paragraph(
                        original_text=para.original_text,
                        sentences=para.sentences[first.sent_index : last.sent_index + 1],
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

    def sub_paras(self, start: int, end: int | None = None) -> TextDoc:
        """
        Get a sub-document containing a range of paragraphs.
        """
        if end is None:
            end = len(self.paragraphs) - 1
        return TextDoc(self.paragraphs[start : end + 1])

    def iter_blocks(
        self,
        *,
        include: set[BlockType] | None = None,
        exclude: set[BlockType] | None = None,
    ) -> Iterator[Paragraph]:
        """
        Iterate over blocks (paragraphs), optionally filtering by `BlockType`.
        `include` keeps only the given types; `exclude` drops the given types. If
        both are given, a block must be in `include` and not in `exclude`.

        Yields this document's own `Paragraph` objects (not copies), so in-place
        edits such as `replace_str` affect this document. Use `filtered` for an
        independent sub-document.
        """
        for para in self.paragraphs:
            block_type = para.block_type
            if include is not None and block_type not in include:
                continue
            if exclude is not None and block_type in exclude:
                continue
            yield para

    def filtered(
        self,
        *,
        include: set[BlockType] | None = None,
        exclude: set[BlockType] | None = None,
    ) -> TextDoc:
        """
        Return a new sub-document containing only the blocks matching the given
        `BlockType` filter, e.g.
        `doc.filtered(include={BlockType.paragraph}).size(TextUnit.words)` gives
        the total words across all paragraph blocks.

        The returned document deep-copies the matched blocks, so it is independent
        of this document: editing one does not affect the other. (Use `iter_blocks`
        to edit this document's blocks in place.)
        """
        return TextDoc(
            [deepcopy(para) for para in self.iter_blocks(include=include, exclude=exclude)]
        )

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
                f"{self.size(TextUnit.paragraphs)} paras, "
                f"{self.size(TextUnit.sentences)} sents, "
                f"{self.size(TextUnit.words)} words, "
                # f"{self.size(TextUnit.wordtoks)} wordtoks, "
                f"{self.size(TextUnit.tiktokens)} tiktoks)"
            )
        else:
            return f"{nbytes} bytes"

    def as_wordtok_to_sent(
        self, bof_eof: bool = False
    ) -> Generator[tuple[str, SentIndex], None, None]:
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

    def as_wordtoks(self, bof_eof: bool = False) -> Generator[str, None, None]:
        for wordtok, _sent_index in self.as_wordtok_to_sent(bof_eof=bof_eof):
            yield wordtok

    def wordtok_mappings(self) -> tuple[WordtokMapping, SentenceMapping]:
        """
        Get mappings between wordtok indexes and sentence indexes.
        """
        sent_indexes = [sent_index for _wordtok, sent_index in self.as_wordtok_to_sent()]

        wordtok_mapping = {i: sent_index for i, sent_index in enumerate(sent_indexes)}

        sent_mapping = defaultdict(list)
        for i, sent_index in enumerate(sent_indexes):
            sent_mapping[sent_index].append(i)

        return wordtok_mapping, sent_mapping

    @override
    def __str__(self):
        return f"TextDoc({self.size_summary()})"
