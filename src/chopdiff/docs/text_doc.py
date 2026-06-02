from __future__ import annotations

import threading
from bisect import bisect_left
from collections import Counter, defaultdict
from collections.abc import Callable, Generator, Iterable, Iterator
from copy import deepcopy
from dataclasses import dataclass, field
from functools import cached_property, wraps
from typing import NamedTuple, TypeAlias, TypeVar

import regex
from flowmark import flowmark_markdown, split_sentences_regex
from flowmark.atomic_spans import iter_atomic_spans, split_sentences_with_spans
from flowmark.markdown_ast import extract_links
from funlog import tally_calls
from marko.block import BlankLine, Document, Heading, SetextHeading
from typing_extensions import override

from chopdiff.docs.base_blocks import BaseBlock, base_blocks
from chopdiff.docs.block_tree import Block, parse_blocks
from chopdiff.docs.block_types import BlockType, block_type_for
from chopdiff.docs.collect import collect as _collect
from chopdiff.docs.doc_graph import _DEFAULT_INCLUDE, Detail, DocGraph, build_doc_graph
from chopdiff.docs.node import Layer, Node, NodeKind, NodeTable
from chopdiff.docs.node_table import build_node_table
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


class _BlockInfo(NamedTuple):
    """A paragraph's classification from one parse: its `BlockType` and, for headings,
    the level and title. Caches the small derived values, not the marko `Document`."""

    block_type: BlockType
    heading_level: int | None
    heading_title: str | None


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
    the source when they could be recovered: inline links, autolinks (`<url>`), bare URLs,
    and reference links whose bracketed use is locatable all get a span. `span` is `None`
    only when the construct cannot be located in the source.
    """

    text: str
    url: str
    title: str | None
    span: tuple[int, int] | None


def _block_links(block_text: str, doc_offset: int, *, parsed: Document | None = None) -> list[Link]:
    """
    Links in a text region. Identity comes from `extract_links` (always correct,
    including reference links resolved against definitions anywhere in the region);
    spans are recovered by aligning, in document order, with the bracketed link atomic
    spans from `iter_atomic_spans` (`markdown_link`), then a forward literal search for
    autolinks and bare URLs (which flowmark does not emit as link atomics). Identities
    that still cannot be located keep their identity but get `span=None`.

    A forward character cursor (`char_cursor`) advances past each located span so that
    bracketed matches, autolinks, bare URLs, and repeated URLs resolve in document order
    without one no-span identity desyncing the next.

    `parsed` is the marko parse of `block_text`; pass it to reuse a shared parse (the
    caller guarantees it is the parse of exactly this `block_text`), else it is parsed
    here.
    """
    identities = extract_links(
        parsed if parsed is not None else flowmark_markdown().parse(block_text)
    )
    # Only `markdown_link` atomics are bracketed `[...]` link constructs; autolinks come
    # through as `html_open_tag` and bare URLs are not atomic, so both are handled by the
    # literal fallback below.
    link_spans = [
        span
        for span in iter_atomic_spans(block_text)
        if span.is_atomic and span.name == "markdown_link"
    ]
    used: set[int] = set()
    result: list[Link] = []
    scan_start = 0
    char_cursor = 0
    for idn in identities:
        located: tuple[int, int] | None = None

        # Bracketed links: match the next unused `markdown_link` atomic by URL (inline)
        # or by link text (reference links, where the URL is in a separate definition).
        for j in range(scan_start, len(link_spans)):
            if j in used:
                continue
            sp = link_spans[j]
            if (idn.url and idn.url in sp.text) or (
                idn.text and idn.text in sp.text and sp.text.startswith("[")
            ):
                located = (sp.start, sp.end)
                used.add(j)
                scan_start = j + 1
                break

        # Autolinks / bare URLs: locate the verbatim URL forward from the cursor; include
        # the surrounding angle brackets when present (an autolink `<url>`).
        if located is None and idn.url:
            idx = block_text.find(idn.url, char_cursor)
            if idx >= 0:
                start, end = idx, idx + len(idn.url)
                if (
                    start > 0
                    and block_text[start - 1] == "<"
                    and end < len(block_text)
                    and block_text[end] == ">"
                ):
                    start, end = start - 1, end + 1
                located = (start, end)

        if located is not None:
            char_cursor = max(char_cursor, located[1])
            result.append(
                Link(
                    idn.text, idn.url, idn.title, (doc_offset + located[0], doc_offset + located[1])
                )
            )
        else:
            result.append(Link(idn.text, idn.url, idn.title, None))
    return result


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
    original_text: str | None = None

    @property
    def span(self) -> tuple[int, int]:
        """
        Absolute `[start, end)` character offsets of this sentence in the document.
        Exact when `original_text` (the verbatim source slice) is set — the default
        splitter sets it via flowmark's offset-preserving splitter, so
        `source_text[start:end] == original_text`. Falls back to `len(text)` for
        sentences produced by a custom (non-span-aware) splitter or by editing.
        """
        length = len(self.original_text if self.original_text is not None else self.text)
        return self.offsets.doc_offset, self.offsets.doc_offset + length

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
        sentences: list[Sentence] = []
        if sentence_splitter is default_sentence_splitter:
            # Default path: flowmark's offset-preserving, atomic-aware splitter gives
            # exact verbatim spans (never bisecting a link/code span). Keep
            # `Sentence.text` whitespace-normalized (as the regex splitter produced)
            # for backward-compatible wordtok/diff/reassemble behavior; `original_text`
            # holds the verbatim slice so `span` is exact.
            for sent_span in split_sentences_with_spans(text):
                normalized = " ".join(sent_span.text.split())
                sentences.append(
                    Sentence(
                        normalized,
                        Offsets(
                            doc_offset=doc_offset + sent_span.start, block_offset=sent_span.start
                        ),
                        original_text=sent_span.text,
                    )
                )
        else:
            # Custom splitter (returns plain strings): locate each sentence by search;
            # offsets are best-effort where the splitter normalized whitespace.
            cursor = 0
            for sent_str in sentence_splitter(text):
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
    def _block_info(self) -> _BlockInfo:
        """
        Classify this paragraph and extract heading level/title from a single parse of
        `original_text` (which does not change after parsing). Cached; the marko document
        is not retained. See `BlockType` for blank-line-splitting caveats.
        """
        text = self.original_text.strip()
        if not text:
            return _BlockInfo(BlockType.paragraph, None, None)
        parsed = flowmark_markdown().parse(text)
        element = next((el for el in parsed.children if not isinstance(el, BlankLine)), None)
        block_type = block_type_for(element) if element is not None else BlockType.paragraph
        # marko treats a single-line HTML tag as an inline-HTML paragraph rather than
        # an HTML block, so fall back to chopdiff's own markup check for those.
        if block_type == BlockType.paragraph and self.is_markup():
            block_type = BlockType.html
        if isinstance(element, (Heading, SetextHeading)):
            return _BlockInfo(block_type, element.level, _inline_text(element).strip())
        return _BlockInfo(block_type, None, None)

    @property
    def block_type(self) -> BlockType:
        """This paragraph's Markdown block kind (see `_block_info`)."""
        return self._block_info.block_type

    def heading_level(self) -> int | None:
        """The Markdown heading level (1-6) if this block is a heading, else None."""
        return self._block_info.heading_level

    def heading_title(self) -> str | None:
        """The heading text without `#` markers if this block is a heading, else None."""
        return self._block_info.heading_title

    def links(self) -> list[Link]:
        """Links in this block, in order (identity always; absolute span when recoverable)."""
        return _block_links(self.original_text, self.offsets.doc_offset)


_DerivedT = TypeVar("_DerivedT")


def _memoized_derivation(
    attr_name: str,
) -> Callable[[Callable[[TextDoc], _DerivedT]], Callable[[TextDoc], _DerivedT]]:
    """
    Memoize a zero-arg `TextDoc` derivation into `attr_name`, computed at most once.

    Filling the cache is the only state change that happens during a read, and it is
    idempotent and thread-safe: a lock-free fast path returns an already-cached value,
    otherwise the instance's reentrant lock serializes the first computation so
    concurrent readers compute it once and all observe the same object. This is sound
    only because every memoized derivation is a pure, deterministic function of the
    immutable-after-parse `source_text` (see the `TextDoc` contract); the lock is
    reentrant so a derivation may call other memoized derivations (e.g. `node_table()`
    uses `blocks()` and `links()`).
    """

    def decorator(func: Callable[[TextDoc], _DerivedT]) -> Callable[[TextDoc], _DerivedT]:
        @wraps(func)
        def wrapper(self: TextDoc) -> _DerivedT:
            cached = getattr(self, attr_name)
            if cached is not None:
                return cached
            with self._cache_lock:
                cached = getattr(self, attr_name)
                if cached is None:
                    cached = func(self)
                    setattr(self, attr_name, cached)
                return cached

        return wrapper

    return decorator


@dataclass
class TextDoc:
    """
    A class for parsing and handling documents consisting of sentences and paragraphs
    of text. Preserves original text, tracking offsets of each sentence and paragraph.
    Compatible with Markdown and Markdown with HTML tags.

    Contract and intended use:

    - A `TextDoc` is a snapshot of a *parsed source document*, meant for analysis
      (sizing, classifying, diffing, windowing) and for generating *new* text via
      `reassemble()`. It is not a live, self-updating DOM.

    - Source references are fixed at parse time. `Paragraph.original_text` and the
      `offsets` on paragraphs and sentences point back into the text passed to
      `from_text`, but `from_text` stores stripped block text and `reassemble()`
      normalizes paragraph separators. Use these references for source mapping, not as
      a byte-for-byte full-document preservation model. They are not updated when
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

    - Read-time thread-safety. The derived views — `blocks()`, `links()`, `sections()`,
      `base_blocks()`, `node_table()`, `graph()`, `collect()`, and the size/TOC helpers —
      are read-only with respect to your data: they are pure, deterministic functions of
      `source_text` and never mutate paragraphs or sentences. The *only* state change
      during such a read is idempotent population of internal caches. The document-level
      caches (the shared marko parse, the block tree, the link list, the node table) are
      filled under a per-instance reentrant lock, so concurrent readers compute each at
      most once and all observe the same value. A few per-element values (e.g.
      `Paragraph.block_type`) are memoized with `cached_property`, which is not lock-
      guarded but is equally idempotent and deterministic — a pure function of that
      element's immutable `original_text` — so a concurrent recompute is harmless (it
      yields the same value). Because every derivation is deterministic, the result is
      identical whether or not a cache was warm and regardless of read order. The
      *editing* methods (`set_sent`, `replace_str`, `append_sent`, `sub_doc`, `filtered`,
      etc.) do mutate and are not thread-safe; do not edit a document while another thread
      reads it. Editing also does not invalidate the source-backed caches (they remain
      keyed to the parsed `source_text`); re-parse with `from_text(doc.reassemble())` to
      analyze edited content.
    """

    paragraphs: list[Paragraph]
    source_text: str = ""
    # Reentrant lock guarding idempotent cache population (see the class contract and
    # `_memoized_derivation`). Per-instance so reads of different documents never contend;
    # reentrant so a derivation may use other memoized derivations.
    _cache_lock: threading.RLock = field(
        default_factory=threading.RLock, init=False, compare=False, repr=False
    )
    _cached_parsed: Document | None = field(default=None, init=False, compare=False, repr=False)
    _cached_node_table: NodeTable | None = field(
        default=None, init=False, compare=False, repr=False
    )
    _cached_blocks: list[Block] | None = field(default=None, init=False, compare=False, repr=False)
    _cached_links: list[Link] | None = field(default=None, init=False, compare=False, repr=False)

    @_memoized_derivation("_cached_parsed")
    def _parsed(self) -> Document:
        """
        The single shared marko parse of `source_text`, computed once. `blocks()` and
        `links()` (and `base_blocks()`) derive from this one parse rather than each
        re-parsing the whole document. See the class contract on read-time caching.
        """
        return flowmark_markdown().parse(self.source_text or self.reassemble())

    @_memoized_derivation("_cached_node_table")
    def node_table(self) -> NodeTable:
        """
        The node table for this document, computed once and cached. A pure function of
        the immutable `source_text` (see the class contract on read-time caching).
        """
        return build_node_table(self)

    @classmethod
    @tally_calls(level="warning", min_total_runtime=5)
    def from_text(
        cls, text: str, sentence_splitter: Splitter = default_sentence_splitter
    ) -> TextDoc:
        """
        Parse a document from a string. Paragraphs are split on blank lines (two or
        more newlines, including blank lines that contain only whitespace). The
        stored block strips surrounding whitespace, so offsets point to the stored
        block content inside `text`: for each paragraph, the slice starting at
        `p.offsets.doc_offset` with length `len(p.original_text)` round-trips to
        `p.original_text`. `reassemble()` produces normalized editable text, not a
        byte-for-byte copy of the full input.
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
        belongs to no section.

        Headings come from the structural parse — top-level `heading` blocks of
        `blocks()` — not the blank-line paragraph view, so a `#`-prefixed line that the
        paragraph splitter isolates from inside a fenced code block is not mistaken for a
        section heading, and headings nested in blockquotes or list items (which are not
        top-level blocks) do not start document sections.
        """
        source_text = self.source_text or self.reassemble()
        # Start offsets of top-level structural heading blocks, sorted for bisect lookup.
        heading_starts = sorted(
            block.span[0] for block in self.blocks() if block.type == BlockType.heading
        )
        roots: list[Section] = []
        stack: list[Section] = []
        for para in self.paragraphs:
            # A paragraph is a heading iff its span contains a top-level structural
            # heading start (a real ATX/setext heading is one paragraph and one block).
            para_start, para_end = para.span
            idx = bisect_left(heading_starts, para_start)
            is_heading = idx < len(heading_starts) and heading_starts[idx] < para_end
            level = para.heading_level() if is_heading else None
            if level is None:
                if stack:
                    stack[-1].content.append(para)
                continue
            section = Section(
                heading=para,
                level=level,
                content=[],
                children=[],
                source_text=source_text,
                _doc=self,
            )
            while stack and stack[-1].level >= level:
                stack.pop()
            if stack:
                stack[-1].children.append(section)
            else:
                roots.append(section)
            stack.append(section)
        return roots

    @_memoized_derivation("_cached_links")
    def _link_list(self) -> list[Link]:
        return _block_links(self.source_text or self.reassemble(), 0, parsed=self._parsed())

    def links(self) -> list[Link]:
        """
        All links in the document, in document order. Derived from the document's single
        shared parse (see the class contract on read-time caching), so reference-style
        links (`[text][ref]` with `[ref]: url` in a separate block) resolve correctly.
        Returns a fresh shallow copy each call so mutating the result cannot poison the
        cache (`Link` is frozen, so the shared elements are safe). See `Link`.
        """
        return list(self._link_list())

    @_memoized_derivation("_cached_blocks")
    def _block_list(self) -> list[Block]:
        return parse_blocks(self.source_text or self.reassemble(), self._parsed())

    def blocks(self) -> list[Block]:
        """
        The document's structural block tree (opt-in), with exact source spans. Unlike
        the blank-line `paragraphs`, this keeps a fenced code block whole (even with
        internal blank lines) and decomposes a tight list into `list_item`s with nested
        sublists. Derived from the document's single shared parse (see the class contract
        on read-time caching), so `sections()`, `links()`, and the node table all reuse
        one parse. See `chopdiff.docs.block_tree`.

        Returns a fresh shallow copy of the cached list each call, so reordering/filtering
        the result cannot poison the shared cache; the `Block` objects themselves are
        shared and must be treated as read-only.
        """
        return list(self._block_list())

    def base_blocks(self, *, item_partition_depth: int = 6) -> list[BaseBlock]:
        """
        The flat, depth-annotated sequential base-block partition of the document: a
        complete, ordered, non-overlapping cover whose reassembly reproduces the source
        (except normalized paragraph-break whitespace). A thin method over the
        `chopdiff.docs.base_blocks.base_blocks` free function; see it for the
        `item_partition_depth` semantics. Distinct from `blocks()`, which is the
        recursive structural tree (a query view, not a partition). Reuses the document's
        single shared parse.
        """
        return base_blocks(
            self.source_text or self.reassemble(),
            item_partition_depth=item_partition_depth,
            parsed=self._parsed(),
        )

    def block_type_counts(self) -> Counter[BlockType]:
        """
        Tally of top-level structural block types in the document. A derived view over
        `blocks()` (no stored counts), density-invariant by construction — `Counter` over
        the live block tree, so it always reflects current content.
        """
        return Counter(block.type for block in self.blocks())

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
        # Preserve the replaced sentence's `original_text` so its `span` keeps
        # pointing at the original source slice (the documented contract: source
        # references describe the original blocks, not the edited content, which
        # lives in `text`). Dropping it would make `span` describe the new text's
        # length at the old offset, i.e. neither the old nor a valid source slice.
        old_sent = self.get_sent(index)
        self.paragraphs[index.para_index].sentences[index.sent_index] = Sentence(
            sent_str, old_sent.offsets, original_text=old_sent.original_text
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

        # Deep-copy so the sub-document is an independent value: callers (and transform
        # helpers like remove_window_br) must not mutate the original through a slice.
        return TextDoc([deepcopy(p) for p in sub_paras], source_text=self.source_text)

    def sub_paras(self, start: int, end: int | None = None) -> TextDoc:
        """
        Get a sub-document containing a range of paragraphs. Returns an independent deep
        copy, so mutating the sub-document does not affect this one.
        """
        if end is None:
            end = len(self.paragraphs) - 1
        return TextDoc(
            [deepcopy(p) for p in self.paragraphs[start : end + 1]],
            source_text=self.source_text,
        )

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
        # An empty document has no sentences; boundary tokens map to a sentinel index so
        # `as_wordtoks(bof_eof=True)` yields just BOF/EOF instead of raising on last_index().
        if not self.paragraphs:
            if bof_eof:
                yield BOF_TOK, SentIndex(0, 0)
                yield EOF_TOK, SentIndex(0, 0)
            return

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

    def collect(
        self,
        scope: str | None = None,
        *,
        subtree_of: str | None = None,
        within: str | tuple[int, int] | None = None,
        overlaps: str | tuple[int, int] | None = None,
        contains: tuple[int, int] | None = None,
        kinds: set[NodeKind] | None = None,
        where: Callable[[Node], bool] | None = None,
        recursive: bool = False,
        inline: bool = False,
        layer: set[Layer] | None = None,
    ) -> list[Node]:
        """
        Convenience that calls `collect()` over `self.node_table()`. See
        `chopdiff.docs.collect.collect` for parameter details.
        """
        return _collect(
            self.node_table(),
            scope,
            subtree_of=subtree_of,
            within=within,
            overlaps=overlaps,
            contains=contains,
            kinds=kinds,
            where=where,
            recursive=recursive,
            inline=inline,
            layer=layer,
        )

    def graph(
        self,
        *,
        include: frozenset[Layer] | None = None,
        detail: frozenset[Detail] = frozenset(),  # pyright: ignore[reportCallInDefaultInitializer]
    ) -> DocGraph:
        """
        Build a `DocGraph` projection of this document. `include` selects which
        layers to serialize (default: markdown + document); `detail` controls
        payload richness (see `Detail`). See `chopdiff.docs.doc_graph` for the
        full contract.
        """
        effective_include = include if include is not None else _DEFAULT_INCLUDE
        return build_doc_graph(self.node_table(), include=effective_include, detail=detail)

    @override
    def __str__(self):
        return f"TextDoc({self.size_summary()})"


@dataclass
class Section:
    """
    A document section: a heading plus the content it owns, with nested subsections.

    `content` are this section's own content paragraphs (excluding the heading line and
    any subsections); `children` are nested `Section`s. Built by `TextDoc.sections()`.
    Sizes are rolled up by reusing `TextDoc.size` over the section's paragraphs, so every
    `TextUnit` aggregates uniformly.

    Two views of the same content, both derived (nothing stored as counts):

    - the *editing* view — `content`, `own_blocks()`, `subtree_blocks()` — returns the
      blank-line `Paragraph`s, matching the document's paragraph view;
    - the *structural* view — `blocks()` — returns the density-invariant structural
      `Block` tree scoped to this section.
    """

    heading: Paragraph
    level: int
    content: list[Paragraph]
    children: list[Section]
    source_text: str = ""
    _doc: TextDoc | None = field(default=None, compare=False, repr=False)

    def _all_blocks(self) -> list[Block]:
        """The whole-document structural parse, shared via the owning doc's cache when
        available (standalone sections fall back to a direct parse)."""
        if self._doc is not None:
            return self._doc.blocks()
        return parse_blocks(self.source_text)

    def _all_links(self) -> list[Link]:
        """The whole-document link list, shared via the owning doc's cache when
        available (standalone sections fall back to a direct parse)."""
        if self._doc is not None:
            return self._doc.links()
        return _block_links(self.source_text, 0)

    @property
    def title(self) -> str:
        return self.heading.heading_title() or ""

    def own_blocks(self) -> list[Paragraph]:
        """The heading plus this section's own content paragraphs (no subsections)."""
        return [self.heading, *self.content]

    def blocks(self) -> list[Block]:
        """
        The structural block tree (see `TextDoc.blocks`) restricted to this section's
        own content — the heading and the blocks it owns, excluding subsections. Spans
        are document-absolute, and the slice is density-invariant like the whole-document
        tree, so per-section block-type tallies are spacing-independent.
        """
        own = self.own_blocks()
        start, end = own[0].span[0], own[-1].span[1]
        return [
            block for block in self._all_blocks() if start <= block.span[0] and block.span[1] <= end
        ]

    def block_type_counts(self) -> Counter[BlockType]:
        """
        Tally of top-level structural block types in this section's own content. A
        derived view over `blocks()` (no stored counts), density-invariant by
        construction.
        """
        return Counter(block.type for block in self.blocks())

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
        """
        All links in this section's subtree, in document order. Derived from a
        document-level parse of `source_text` (so reference links resolve across
        blocks) and filtered to links whose span falls within the section's span.
        Links with `span=None` (e.g. reference definitions with no recoverable
        inline span) are omitted because they cannot be attributed to a section
        by offset alone.
        """
        sec_start, sec_end = self.span
        return [
            link
            for link in self._all_links()
            if link.span is not None and sec_start <= link.span[0] and link.span[1] <= sec_end
        ]
