from textwrap import dedent

from chopdiff.docs.sizes import TextUnit
from chopdiff.docs.text_doc import TextDoc
from chopdiff.transforms.sliding_transforms import (
    sliding_para_window_transform,
    sliding_window_transform,
)
from chopdiff.transforms.window_settings import WINDOW_BR_SEP, WindowSettings

_example_text = dedent(
    """
    This is the first paragraph. It has multiple sentences.

    This is the second paragraph. It also has multiple sentences. And it continues.
    
    Here is the third paragraph. More sentences follow. And here is another one.
    """
).strip()


def test_sliding_word_window_transform():
    long_text = (_example_text + "\n\n") * 2
    doc = TextDoc.from_text(long_text)

    # Simple transformation that converts all text to uppercase.
    def transform_func(window: TextDoc) -> TextDoc:
        transformed_text = window.reassemble().upper()
        return TextDoc.from_text(transformed_text)

    transformed_doc = sliding_window_transform(
        doc,
        transform_func,
        WindowSettings(TextUnit.wordtoks, 80, 60, min_overlap=5, separator="|"),
    )
    print("---Wordtok transformed doc:")
    print(transformed_doc.reassemble())

    assert transformed_doc.reassemble().count("|") == 2

    long_text = (_example_text + "\n\n") * 20
    doc = TextDoc.from_text(long_text)
    transformed_doc = sliding_window_transform(
        doc, transform_func, WindowSettings(TextUnit.wordtoks, 80, 60, min_overlap=5)
    )
    assert transformed_doc.reassemble() == long_text.upper().strip()


def test_sliding_para_window_transform():
    def transform_func(window: TextDoc) -> TextDoc:
        transformed_text = window.reassemble().upper()
        return TextDoc.from_text(transformed_text)

    text = "\n\n".join(f"Paragraph {i}." for i in range(7))
    doc = TextDoc.from_text(text)

    transformed_doc = sliding_para_window_transform(
        doc,
        transform_func,
        WindowSettings(
            TextUnit.paragraphs,
            3,
            3,
            separator=WINDOW_BR_SEP,
        ),
    )

    print("---Paragraph transformed doc:")
    print(transformed_doc.reassemble())

    assert (
        transformed_doc.reassemble()
        == dedent(
            """
            PARAGRAPH 0.

            PARAGRAPH 1.

            PARAGRAPH 2.

            <!--window-br--> PARAGRAPH 3.

            PARAGRAPH 4.

            PARAGRAPH 5.

            <!--window-br--> PARAGRAPH 6.
            """
        ).strip()
    )
