from enum import Enum

from lite_text_tools.docs.tiktoken_utils import tiktoken_len
from lite_text_tools.docs.wordtoks import raw_text_to_wordtoks

from lite_text_tools.html.html_plaintext import html_to_plaintext


def size_in_bytes(text: str) -> int:
    return len(text.encode("utf-8"))


def size_in_wordtoks(text: str) -> int:
    return len(raw_text_to_wordtoks(text))


class TextUnit(Enum):
    """
    Text units of measure.
    """

    lines = "lines"
    bytes = "bytes"
    chars = "chars"
    words = "words"
    wordtoks = "wordtoks"
    paragraphs = "paragraphs"
    sentences = "sentences"
    tiktokens = "tiktokens"


def size(text: str, unit: TextUnit) -> int:
    if unit == TextUnit.lines:
        return len(text.splitlines())
    elif unit == TextUnit.bytes:
        return size_in_bytes(text)
    elif unit == TextUnit.chars:
        return len(text)
    elif unit == TextUnit.words:
        # Roughly accurate for HTML, text, or Markdown docs.
        return len(html_to_plaintext(text).split())
    elif unit == TextUnit.wordtoks:
        return size_in_wordtoks(text)
    elif unit == TextUnit.tiktokens:
        return tiktoken_len(text)
    else:
        raise NotImplementedError(f"Unsupported unit for string: {unit}")
