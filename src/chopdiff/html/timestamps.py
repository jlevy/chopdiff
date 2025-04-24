from collections.abc import Iterable

import regex
from typing_extensions import override

from chopdiff.docs.search_tokens import search_tokens
from chopdiff.docs.wordtoks import wordtokenize_with_offsets
from chopdiff.html.extractor import ContentNotFound, Extractor, Match

# Match any span or div with a data-timestamp attribute.
_TIMESTAMP_RE = regex.compile(r'(?:<\w+[^>]*\s)?data-timestamp=[\'"](\d+(\.\d+)?)[\'"][^>]*>')


def extract_timestamp(wordtok: str) -> float | None:
    match = _TIMESTAMP_RE.search(wordtok)
    return float(match.group(1)) if match else None


def has_timestamp(wordtok: str) -> bool:
    return extract_timestamp(wordtok) is not None


class TimestampExtractor(Extractor[float]):
    """
    Extract timestamps of the form `<... data-timestamp="123.45">` from a document.
    """

    def __init__(self, doc_str: str):
        self.doc_str = doc_str
        self.wordtoks, self.offsets = wordtokenize_with_offsets(self.doc_str, bof_eof=True)

    @override
    def extract_all(self) -> Iterable[Match[float]]:
        """
        Extract all timestamps from the document.
        """
        for index, (wordtok, offset) in enumerate(zip(self.wordtoks, self.offsets, strict=False)):
            timestamp = extract_timestamp(wordtok)
            if timestamp is not None:
                yield timestamp, index, offset

    @override
    def extract_preceding(self, wordtok_offset: int) -> Match[float]:
        try:
            index, wordtok = (
                search_tokens(self.wordtoks).at(wordtok_offset).seek_back(has_timestamp).get_token()
            )
            if wordtok:
                timestamp = extract_timestamp(wordtok)
                if timestamp is not None:
                    return timestamp, index, self.offsets[index]
            raise ContentNotFound(
                f"No timestamp found seeking back from token {wordtok_offset}: {wordtok!r}"
            )
        except KeyError as e:
            raise ContentNotFound(
                f"No timestamp found searching back from token {wordtok_offset}: {e}"
            )
