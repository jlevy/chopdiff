from textwrap import dedent
from typing import Iterable

import regex
from typing_extensions import override

from .extractor import Extractor, Match
from .search_tokens import search_tokens
from .wordtoks import raw_text_to_wordtok_offsets


class ContentError(ValueError):
    pass


# Match any span or div with a data-timestamp attribute.
_TIMESTAMP_RE = regex.compile(r'(?:<\w+[^>]*\s)?data-timestamp=[\'"](\d+(\.\d+)?)[\'"][^>]*>')


def extract_timestamp(wordtok: str):
    match = _TIMESTAMP_RE.search(wordtok)
    return float(match.group(1)) if match else None


def has_timestamp(wordtok: str):
    return bool(extract_timestamp(wordtok))


class TimestampExtractor(Extractor):
    """
    Extract the first timestamp of the form `<... data-timestamp="123.45">`.
    """

    def __init__(self, doc_str: str):
        self.doc_str = doc_str
        self.wordtoks, self.offsets = raw_text_to_wordtok_offsets(self.doc_str, bof_eof=True)

    @override
    def extract_all(self) -> Iterable[Match[float]]:
        """
        Extract all timestamps from the document.
        """
        for index, (wordtok, offset) in enumerate(zip(self.wordtoks, self.offsets)):
            timestamp = extract_timestamp(wordtok)
            if timestamp:
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
            raise ContentError(f"No timestamp found seeking back from {wordtok_offset}: {wordtok}")
        except KeyError as e:
            raise ContentError(f"No timestamp found searching back from {wordtok_offset}: {e}")


## Tests


def test_timestamp_extractor():
    doc_str = '<span data-timestamp="1.234">Sentence one.</span> <span data-timestamp="23">Sentence two.</span> Sentence three.'

    extractor = TimestampExtractor(doc_str)
    wordtoks = extractor.wordtoks

    results = []
    offsets = []
    for i, wordtok in enumerate(wordtoks):
        try:
            timestamp, _index, offset = extractor.extract_preceding(i)
        except ContentError:
            timestamp = None
            offset = -1
        results.append(f"{i}: {timestamp} ⎪{wordtok}⎪")
        offsets.append(offset)

    print("\n".join(results))
    print(offsets)

    assert (
        "\n".join(results)
        == dedent(
            """
            0: None ⎪<-BOF->⎪
            1: None ⎪<span data-timestamp="1.234">⎪
            2: 1.234 ⎪Sentence⎪
            3: 1.234 ⎪ ⎪
            4: 1.234 ⎪one⎪
            5: 1.234 ⎪.⎪
            6: 1.234 ⎪</span>⎪
            7: 1.234 ⎪ ⎪
            8: 1.234 ⎪<span data-timestamp="23">⎪
            9: 23.0 ⎪Sentence⎪
            10: 23.0 ⎪ ⎪
            11: 23.0 ⎪two⎪
            12: 23.0 ⎪.⎪
            13: 23.0 ⎪</span>⎪
            14: 23.0 ⎪ ⎪
            15: 23.0 ⎪Sentence⎪
            16: 23.0 ⎪ ⎪
            17: 23.0 ⎪three⎪
            18: 23.0 ⎪.⎪
            19: 23.0 ⎪<-EOF->⎪
            """
        ).strip()
    )

    assert offsets == [
        -1,
        -1,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        50,
        50,
        50,
        50,
        50,
        50,
        50,
        50,
        50,
        50,
        50,
    ]
