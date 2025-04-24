from pprint import pprint
from textwrap import dedent

from chopdiff.docs.sizes import TextUnit, size
from chopdiff.docs.text_doc import TextDoc
from chopdiff.transforms.sliding_windows import sliding_word_window

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
        [[sent.text for sent in para.sentences] for para in doc.paragraphs] for doc in windows
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
