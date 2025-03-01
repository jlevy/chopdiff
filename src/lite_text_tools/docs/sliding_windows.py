"""
Sliding windows of text on a text doc.
"""

import logging
from pprint import pprint
from textwrap import dedent
from typing import Callable, Generator

from flowmark import normalize_markdown

from .text_doc import SentIndex, size, TextDoc, TextUnit


log = logging.getLogger(__name__)


def sliding_word_window(
    doc: TextDoc, window_size: int, window_shift: int, unit: TextUnit
) -> Generator[TextDoc, None, None]:
    """
    Generate TextDoc sub-documents in a sliding window over the given document.
    """
    total_size = doc.size(unit)
    start_offset = 0
    start_index, _ = doc.seek_to_sent(start_offset, unit)

    while start_offset < total_size:
        end_offset = start_offset + window_size
        end_index, _ = doc.seek_to_sent(end_offset, unit)

        # Sentence may extend past the window, so back up to ensure it fits.
        sub_doc = doc.sub_doc(start_index, end_index)
        try:
            while sub_doc.size(unit) > window_size:
                end_index = doc.prev_sent(end_index)
                sub_doc = doc.sub_doc(start_index, end_index)
        except ValueError:
            raise ValueError(
                f"Window size {window_size} too small for sentence at offset {start_offset}"
            )

        yield sub_doc

        start_offset += window_shift
        start_index = end_index


def sliding_para_window(
    doc: TextDoc, nparas: int, normalizer: Callable[[str], str] = normalize_markdown
) -> Generator[TextDoc, None, None]:
    """
    Generate TextDoc sub-documents taking `nparas` paragraphs at a time.
    """
    for i in range(0, len(doc.paragraphs), nparas):
        end_index = min(i + nparas - 1, len(doc.paragraphs) - 1)
        sub_doc = doc.sub_doc(SentIndex(i, 0), SentIndex(end_index, 0))

        # XXX It's important we re-normalize especially because LLMs can output itemized lists with just
        # one newline, but for Markdown we want separate paragraphs for each list item.
        formatted_sub_doc = TextDoc.from_text(normalizer(sub_doc.reassemble()))

        yield formatted_sub_doc


## Tests

_example_text = dedent(
    """
    This is the first paragraph. It has multiple sentences.

    This is the second paragraph. It also has multiple sentences. And it continues.
    
    Here is the third paragraph. More sentences follow. And here is another one.
    """
).strip()


def test_sliding_window():
    doc = TextDoc.from_text(_example_text)
    window_size = 80
    window_shift = 60

    windows = list(sliding_word_window(doc, window_size, window_shift, TextUnit.bytes))
    pprint(windows)

    sentence_windows = [
        [[sent.text for sent in para.sentences] for para in doc.paragraphs]
        for doc in windows
    ]

    assert sentence_windows == [
        [["This is the first paragraph.", "It has multiple sentences."]],
        [["It has multiple sentences."], ["This is the second paragraph."]],
        [
            [
                "This is the second paragraph.",
                "It also has multiple sentences.",
                "And it continues.",
            ]
        ],
        [
            ["And it continues."],
            ["Here is the third paragraph.", "More sentences follow."],
        ],
    ]

    for sub_doc in windows:
        sub_text = sub_doc.reassemble()

        print(f"\n\n---Sub-document length {size(sub_text, TextUnit.bytes)}")
        pprint(sub_text)

        assert size(sub_text, TextUnit.bytes) <= window_size

        assert sub_text in doc.reassemble()
