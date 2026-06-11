from enum import Enum

from flexdoc.docs.wordtoks import wordtokenize
from flexdoc.html.html_plaintext import html_to_plaintext
from flexdoc.util.token_estimate import estimate_tokens


def size_in_bytes(text: str) -> int:
    return len(text.encode("utf-8"))


def size_in_wordtoks(text: str) -> int:
    return len(wordtokenize(text))


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
    tokens = "tokens"
    """Estimated LLM token count (heuristic, no tokenizer). See `estimate_tokens`."""


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
    elif unit == TextUnit.tokens:
        return estimate_tokens(text)
    else:
        raise NotImplementedError(f"Unsupported unit for string: {unit}")
