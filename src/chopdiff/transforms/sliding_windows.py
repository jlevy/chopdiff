"""
Sliding windows of text on a text doc.
"""

import logging
from collections.abc import Callable, Generator

from flexdoc import FlexDoc
from flexdoc.docs.sizes import TextUnit
from flowmark import fill_markdown

log = logging.getLogger(__name__)


def sliding_word_window(
    doc: FlexDoc, window_size: int, window_shift: int, unit: TextUnit
) -> Generator[FlexDoc, None, None]:
    """
    Generate FlexDoc sub-documents in a sliding window over the given document.
    """
    if window_size <= 0:
        raise ValueError(f"Window size must be positive, got {window_size}")
    if window_shift <= 0:
        raise ValueError(f"Window shift must be positive, got {window_shift}")

    total_size = doc.size(unit)
    start_offset = 0

    while start_offset < total_size:
        start_index, _ = doc.seek_to_sent(start_offset, unit)
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


def sliding_para_window(
    doc: FlexDoc, nparas: int, normalizer: Callable[[str], str] = fill_markdown
) -> Generator[FlexDoc, None, None]:
    """
    Generate FlexDoc sub-documents taking `nparas` paragraphs at a time.
    """
    if nparas <= 0:
        raise ValueError(f"Paragraph window size must be positive, got {nparas}")

    for i in range(0, len(doc.paragraphs), nparas):
        end_index = min(i + nparas - 1, len(doc.paragraphs) - 1)
        # Use whole-paragraph slicing so every sentence of the ending paragraph is kept
        # (`sub_doc(..., SentIndex(end_index, 0))` would keep only its first sentence).
        sub_doc = doc.sub_paras(i, end_index)

        # XXX It's important we re-normalize especially because LLMs can output itemized lists with just
        # one newline, but for Markdown we want separate paragraphs for each list item.
        formatted_sub_doc = FlexDoc.from_text(normalizer(sub_doc.reassemble()))

        yield formatted_sub_doc
