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
from flowmark.atomic_spans import iter_atomic_spans
from flowmark.markdown_ast import extract_links
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
from chopdiff.util.token_estimate import estimate_tokens

SYMBOL_PARA = "¶"

SYMBOL_SENT = "S"

FOOTNOTE_DEF_REGEX = regex.compile(r"^\[\^[^\]]+\]:")

_PARA_BREAK_REGEX = regex.compile(r"(?:[ \t\r]*\n){2,}[ \t\r]*")
r"""
A paragraph break: a run of whitespace containing two or more newlines (a blank
line). Blank lines that contain only spaces, tabs, or `\r` still count, and any
number of consecutive blank lines collapse into a single break.
"""

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


def _heading_element(text: str) -> Heading | SetextHeading | None:
    parsed = _markdown_parser().parse(text)
    for element in parsed.children:
        if isinstance(element, (Heading, SetextHeading)):
            return element
    return None


def _inline_text(element: object) -> str:
    """Concatenate the plain text of an inline (or heading) element subtree."""
    children = getattr(element, "children", None)
    if isinstance(children, str):
        return children
    if isinstance(children, list):
        return "".join(_inline_text(child) for child in children)  # pyright: ignore[reportUnknownArgumentType]
    return ""


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


@dataclass(frozen=True)
class Offsets:
    """
    Character offsets of a parsed element, with the same shape for paragraphs,
    sentences, and any future parsed units.

    - `doc_offset`: absolute offset in the document.
    - `block_offset`: offset relative to the start of the enclosing block — the
      document for a paragraph (so it equals `doc_offset`), or the paragraph for a
      sentence.
    """

    doc_offset: int
    block_offset: int


@dataclass(frozen=True)
class Link:
    """
    A link found in a document. `text`, `url`, and `title` are the parsed identity
    (reference links resolved, autolinks and bare URLs included), via flowmark's
    `markdown_ast.extract_links`. `span` is the link's absolute `[start, end)` offsets in
    the source when they could be recovered (the common inline/autolink case), else
    `None` — e.g. reference links, whose rendered text has no contiguous source span.
    """

    text: str
    url: str
    title: str | None
    span: tuple[int, int] | None


# Atomic-span pattern names (from flowmark.atomic_spans) that correspond to links.
_LINK_ATOMIC_NAMES = frozenset({"markdown_link", "autolink", "bare_url"})


def _block_links(block_text: str, doc_offset: int) -> list[Link]:
    """
    Links in a single block. Identity comes from `extract_links` (always correct);
    spans are recovered by aligning, in document order, with the link-like atomic spans
    from `iter_atomic_spans`. When the two lists disagree in count (reference links,
    images, shortcut refs), identity is kept and spans are left `None`.
    """
    identities = extract_links(_markdown_parser().parse(block_text))
    link_spans = [
        span
        for span in iter_atomic_spans(block_text)
        if span.is_atomic and span.name in _LINK_ATOMIC_NAMES
    ]
    if len(identities) == len(link_spans):
        return [
            Link(idn.text, idn.url, idn.title, (doc_offset + sp.start, doc_offset + sp.end))
            for idn, sp in zip(identities, link_spans, strict=True)
        ]
    return [Link(idn.text, idn.url, idn.title, None) for idn in identities]


@dataclass
class Sentence:
    """
    A sentence in a `TextDoc`. `text` is the editable content (used by
    `reassemble()`); `offsets` is a fixed reference to the source set at parse time
    and is not updated by edits. Offsets are exact when the sentence is a verbatim
    slice of the paragraph (prose); for content where the splitter normalizes
    whitespace (e.g. tables), the offset is a best-effort position. See `TextDoc`
    for the full contract.
    """

    text: str
    offsets: Offsets

    @property
    def span(self) -> tuple[int, int]:
        """
        Absolute `[start, end)` character offsets of this sentence in the document.
        Exact (round-trips against the source) for verbatim sentences; best-effort
        where the splitter normalized whitespace (see class docstring).
        """
        return self.offsets.doc_offset, self.offsets.doc_offset + len(self.text)

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

    `original_text` and `offsets` are fixed references to the source as parsed and
    are not updated by edits; `sentences` holds the editable content used by
    `reassemble()`. `block_type` is derived from `original_text` and cached, so it
    assumes `original_text` is not reassigned after construction. See `TextDoc` for
    the full contract.
    """

    original_text: str
    sentences: list[Sentence]
    offsets: Offsets

    @property
    def end_offset(self) -> int:
        """Absolute end offset (exclusive) of this paragraph in the document."""
        return self.offsets.doc_offset + len(self.original_text)

    @property
    def span(self) -> tuple[int, int]:
        """
        Absolute `[start, end)` character offsets of this paragraph in the document,
        such that `source_text[start:end] == original_text`.
        """
        return self.offsets.doc_offset, self.end_offset

    @classmethod
    @tally_calls(level="warning", min_total_runtime=5)
    def from_text(
        cls,
        text: str,
        doc_offset: int = 0,
        sentence_splitter: Splitter = default_sentence_splitter,
    ) -> Paragraph:
        # TODO: Lazily compute sentences for better performance.
        sent_values = sentence_splitter(text)
        sentences: list[Sentence] = []
        cursor = 0
        for sent_str in sent_values:
            # Locate each sentence's position within the paragraph. Sentence
            # splitters may normalize whitespace (e.g. inside a table), so when the
            # sentence is not a verbatim slice we fall back to the running cursor.
            idx = text.find(sent_str, cursor)
            if idx < 0:
                idx = cursor
            sentences.append(
                Sentence(sent_str, Offsets(doc_offset=doc_offset + idx, block_offset=idx))
            )
            cursor = idx + len(sent_str)
        return cls(
            original_text=text,
            sentences=sentences,
            offsets=Offsets(doc_offset=doc_offset, block_offset=doc_offset),
        )

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

        if unit == TextUnit.tokens:
            return estimate_tokens(self.reassemble())

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

    def heading_level(self) -> int | None:
        """The Markdown heading level (1-6) if this block is a heading, else None."""
        if self.block_type != BlockType.heading:
            return None
        element = _heading_element(self.original_text.strip())
        return element.level if element is not None else None

    def heading_title(self) -> str | None:
        """The heading text without `#` markers if this block is a heading, else None."""
        if self.block_type != BlockType.heading:
            return None
        element = _heading_element(self.original_text.strip())
        return _inline_text(element).strip() if element is not None else None

    def links(self) -> list[Link]:
        """Links in this block, in order (identity always; absolute span when recoverable)."""
        return _block_links(self.original_text, self.offsets.doc_offset)


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
      `offsets` on paragraphs and sentences are exact references into the text
      passed to `from_text` (the input is not normalized) and are not updated when
      content is mutated, so they remain valid as references back to the source.

    - Offsets: every paragraph and sentence carries an `Offsets` record with both
      `doc_offset` (absolute in the document) and `block_offset` (relative to the
      enclosing block — the document for a paragraph, the paragraph for a sentence).

    - In-place editing is supported for *building transformed output*: mutate
      sentence text (`replace_str`, `set_sent`) or restructure the paragraph and
      sentence lists (`sub_doc`, `sub_paras`, `filtered`, `append_sent`), then call
      `reassemble()`. This is safe as long as you do not rely on the source
      references tracking your edits: after editing, `original_text`, the `offsets`,
      and cached values like `Paragraph.block_type` still describe the *original*
      blocks. To get offsets/classification for edited content, re-parse with
      `TextDoc.from_text(doc.reassemble())`.

    - `filtered()` returns an independent deep copy; `iter_blocks()` and the
      `paragraphs`/`sentences` lists expose this document's live objects.

    - `source_text` is the document text the offsets index into. For a parsed doc it is
      the unmodified input; `sub_doc`/`sub_paras`/`filtered` carry the same `source_text`
      (their offsets still point into it). Docs built from synthetic content
      (`from_wordtoks`) set it to the reassembled text. `block_at_offset` /
      `sentence_at_offset` map an absolute offset back to the unit that contains it.
    """

    paragraphs: list[Paragraph]
    source_text: str = ""

    @classmethod
    @tally_calls(level="warning", min_total_runtime=5)
    def from_text(
        cls, text: str, sentence_splitter: Splitter = default_sentence_splitter
    ) -> TextDoc:
        """
        Parse a document from a string. Paragraphs are split on blank lines (two or
        more newlines, including blank lines that contain only whitespace). The
        input is not normalized, so every offset is an exact reference into `text`;
        e.g. `text[p.offsets.doc_offset : p.offsets.doc_offset + len(p.original_text)]`
        round-trips to `p.original_text`.
        """
        paragraphs: list[Paragraph] = []
        spans: list[tuple[int, int]] = []
        start = 0
        for m in _PARA_BREAK_REGEX.finditer(text):
            spans.append((start, m.start()))
            start = m.end()
        spans.append((start, len(text)))
        for span_start, span_end in spans:
            piece = text[span_start:span_end]
            stripped = piece.strip()
            if stripped:
                # Doc offset of the stripped content within the original text.
                doc_offset = span_start + (len(piece) - len(piece.lstrip()))
                paragraphs.append(Paragraph.from_text(stripped, doc_offset, sentence_splitter))
        return cls(paragraphs=paragraphs, source_text=text)

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

    def block_at_offset(self, offset: int) -> Paragraph | None:
        """
        The paragraph whose span contains `offset` (an absolute character offset into
        the source), or `None` if `offset` falls in inter-block whitespace or outside
        the document.
        """
        for para in self.paragraphs:
            start, end = para.span
            if start <= offset < end:
                return para
        return None

    def sentence_at_offset(self, offset: int) -> SentIndex | None:
        """
        The `SentIndex` of the sentence whose span contains `offset`, or `None` if none
        does (inter-block/inter-sentence whitespace, or outside the document).
        """
        for para_index, para in enumerate(self.paragraphs):
            p_start, p_end = para.span
            if not (p_start <= offset < p_end):
                continue
            for sent_index, sent in enumerate(para.sentences):
                start, end = sent.span
                if start <= offset < end:
                    return SentIndex(para_index, sent_index)
            return None
        return None

    def sections(self) -> list[Section]:
        """
        The heading hierarchy as a tree of top-level `Section`s. A section owns the
        blocks from its heading up to the next heading of equal-or-higher level; deeper
        headings become nested `children`. Content before the first heading (preamble)
        belongs to no section. Derived from heading levels; no whole-document re-parse.
        """
        roots: list[Section] = []
        stack: list[Section] = []
        for para in self.paragraphs:
            level = para.heading_level()
            if level is None:
                if stack:
                    stack[-1].blocks.append(para)
                continue
            section = Section(heading=para, level=level, blocks=[], children=[])
            while stack and stack[-1].level >= level:
                stack.pop()
            if stack:
                stack[-1].children.append(section)
            else:
                roots.append(section)
            stack.append(section)
        return roots

    def links(self) -> list[Link]:
        """All links in the document, in document order. See `Link`."""
        result: list[Link] = []
        for para in self.paragraphs:
            result.extend(para.links())
        return result

    def toc(self) -> list[tuple[int, str, tuple[int, int]]]:
        """Flat table of contents in document order: `(level, title, span)` per heading."""
        entries: list[tuple[int, str, tuple[int, int]]] = []

        def walk(sections: list[Section]) -> None:
            for section in sections:
                entries.append((section.level, section.title, section.span))
                walk(section.children)

        walk(self.sections())
        return entries

    def section_size_tree(self, units: tuple[TextUnit, ...] = (TextUnit.words,)) -> str:
        """
        Render the section hierarchy as an indented tree with rolled-up sizes per
        section (each line covers the section and all its subsections).
        """
        lines: list[str] = []

        def walk(sections: list[Section], depth: int) -> None:
            for section in sections:
                sizes = ", ".join(f"{section.size(unit)} {unit.value}" for unit in units)
                lines.append(f"{'  ' * depth}{'#' * section.level} {section.title}  ({sizes})")
                walk(section.children, depth + 1)

        walk(self.sections(), 0)
        return "\n".join(lines)

    def get_sent(self, index: SentIndex) -> Sentence:
        return self.paragraphs[index.para_index].sentences[index.sent_index]

    def set_sent(self, index: SentIndex, sent_str: str) -> None:
        old_sent = self.get_sent(index)
        self.paragraphs[index.para_index].sentences[index.sent_index] = Sentence(
            sent_str, old_sent.offsets
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
                        offsets=para.offsets,
                    )
                )
            elif i == first.para_index:
                sub_paras.append(
                    Paragraph(
                        original_text=para.original_text,
                        sentences=para.sentences[first.sent_index :],
                        offsets=para.offsets,
                    )
                )
            elif i == last.para_index:
                sub_paras.append(
                    Paragraph(
                        original_text=para.original_text,
                        sentences=para.sentences[: last.sent_index + 1],
                        offsets=para.offsets,
                    )
                )
            else:
                sub_paras.append(para)

        return TextDoc(sub_paras, source_text=self.source_text)

    def sub_paras(self, start: int, end: int | None = None) -> TextDoc:
        """
        Get a sub-document containing a range of paragraphs.
        """
        if end is None:
            end = len(self.paragraphs) - 1
        return TextDoc(self.paragraphs[start : end + 1], source_text=self.source_text)

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
            [deepcopy(para) for para in self.iter_blocks(include=include, exclude=exclude)],
            source_text=self.source_text,
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
                Paragraph(original_text=sent.text, sentences=[sent], offsets=Offsets(0, 0))
            )
        else:
            last_para = self.paragraphs[-1]
            last_para.sentences.append(sent)

    def size(self, unit: TextUnit) -> int:
        if unit == TextUnit.paragraphs:
            return len(self.paragraphs)
        if unit == TextUnit.sentences:
            return sum(len(para.sentences) for para in self.paragraphs)

        if unit == TextUnit.tokens:
            return estimate_tokens(self.reassemble())

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
                f"~{self.size(TextUnit.tokens)} tok)"
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


@dataclass
class Section:
    """
    A document section: a heading plus the content it owns, with nested subsections.

    `blocks` are this section's own content blocks (excluding the heading line and any
    subsections); `children` are nested `Section`s. Built by `TextDoc.sections()`. Sizes
    are rolled up by reusing `TextDoc.size` over the section's blocks, so every
    `TextUnit` aggregates uniformly.
    """

    heading: Paragraph
    level: int
    blocks: list[Paragraph]
    children: list[Section]

    @property
    def title(self) -> str:
        return self.heading.heading_title() or ""

    def own_blocks(self) -> list[Paragraph]:
        """The heading plus this section's own content blocks (no subsections)."""
        return [self.heading, *self.blocks]

    def subtree_blocks(self) -> list[Paragraph]:
        """All blocks of this section and its subsections, in document order."""
        result = self.own_blocks()
        for child in self.children:
            result.extend(child.subtree_blocks())
        return result

    @property
    def span(self) -> tuple[int, int]:
        """`[start, end)` covering the heading through the end of the last subtree block."""
        blocks = self.subtree_blocks()
        return blocks[0].span[0], blocks[-1].span[1]

    def size(self, unit: TextUnit, subtree: bool = True) -> int:
        """
        Size in `unit`, rolled up over the whole subtree by default (`subtree=True`) or
        the section's own content only (`subtree=False`). Reuses `TextDoc.size`.
        """
        blocks = self.subtree_blocks() if subtree else self.own_blocks()
        return TextDoc(blocks).size(unit)

    def size_summary(self, subtree: bool = True) -> str:
        blocks = self.subtree_blocks() if subtree else self.own_blocks()
        return TextDoc(blocks).size_summary()

    def links(self) -> list[Link]:
        """All links in this section's subtree, in document order."""
        result: list[Link] = []
        for block in self.subtree_blocks():
            result.extend(block.links())
        return result
