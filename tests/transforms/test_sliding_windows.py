from pprint import pprint
from textwrap import dedent

from flexdoc import FlexDoc
from flexdoc.docs.sizes import TextUnit, size

from chopdiff.transforms.sliding_windows import sliding_word_window

_example_text = dedent(
    """
    This is the first paragraph. It has multiple sentences.

    This is the second paragraph. It also has multiple sentences. And it continues.
    
    Here is the third paragraph. More sentences follow. And here is another one.
    """
).strip()


def test_sliding_window():
    doc = FlexDoc.from_text(_example_text)
    window_size = 80
    window_shift = 60

    windows = list(sliding_word_window(doc, window_size, window_shift, TextUnit.bytes))
    pprint(windows)

    sentence_windows = [
        [[sent.text for sent in para.sentences] for para in doc.paragraphs] for doc in windows
    ]

    assert sentence_windows == [
        [["This is the first paragraph.", "It has multiple sentences."]],
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
        [["More sentences follow.", "And here is another one."]],
    ]

    for sub_doc in windows:
        sub_text = sub_doc.reassemble()

        print(f"\n\n---Sub-document length {size(sub_text, TextUnit.bytes)}")
        pprint(sub_text)

        assert size(sub_text, TextUnit.bytes) <= window_size

        assert sub_text in doc.reassemble()


def test_sliding_word_window_rejects_zero_shift():
    doc = FlexDoc.from_text(_example_text)

    try:
        next(sliding_word_window(doc, 80, 0, TextUnit.bytes))
    except ValueError as exc:
        assert str(exc) == "Window shift must be positive, got 0"
    else:
        raise AssertionError("Expected a non-positive window shift to be rejected")


def test_sliding_word_window_rejects_zero_size():
    doc = FlexDoc.from_text(_example_text)

    try:
        next(sliding_word_window(doc, 0, 60, TextUnit.bytes))
    except ValueError as exc:
        assert str(exc) == "Window size must be positive, got 0"
    else:
        raise AssertionError("Expected a non-positive window size to be rejected")
