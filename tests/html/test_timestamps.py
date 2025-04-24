from textwrap import dedent

from chopdiff.html.extractor import ContentNotFound
from chopdiff.html.timestamps import TimestampExtractor


def test_timestamp_extractor():
    doc_str = '<span data-timestamp="1.234">Sentence one.</span> <span data-timestamp="23">Sentence two.</span> Sentence three.'

    extractor = TimestampExtractor(doc_str)
    wordtoks = extractor.wordtoks

    results: list[str] = []
    offsets: list[int] = []
    for i, wordtok in enumerate(wordtoks):
        try:
            timestamp, _index, offset = extractor.extract_preceding(i)
        except ContentNotFound:
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
