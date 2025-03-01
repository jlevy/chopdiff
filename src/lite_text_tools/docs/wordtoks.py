"""
Support for treating text as a sequence of word, punctuation, or whitespace
word tokens ("wordtoks").
"""

from dataclasses import dataclass
from textwrap import dedent
from typing import Dict, List, Optional, Tuple

import regex

from .search_tokens import search_tokens

# Note these parse as tokens and like HTML tags, so they can safely be mixed into inputs if desired.
SENT_BR_TOK = "<-SENT-BR->"
PARA_BR_TOK = "<-PARA-BR->"
BOF_TOK = "<-BOF->"
EOF_TOK = "<-EOF->"

SENT_BR_STR = " "
PARA_BR_STR = "\n\n"
BOF_STR = ""
EOF_STR = ""

SPACE_TOK = " "

SYMBOL_SEP = "⎪"

# Currently break on words, spaces, or any single other/punctuation character.
# HTML tags (of length <1024 chars, possibly with newlines) and entities are also a single token.
# TODO: Could add nicer support for Markdown formatting as well.
# Updated pattern to include HTML entities
_wordtok_pattern = regex.compile(
    r"(<(?:[^<>]|\n){0,1024}>|\&\w+;|\&\#\d+;|\w+|[^\w\s]|\s+)", regex.DOTALL
)

_para_br_pattern = regex.compile(r"\s*\n\n\s*")

# TODO: Is it worth using the regex package here to get \p{L} or is there a good
# enough way with re only?
_word_pat = regex.compile(r"\p{L}+", regex.UNICODE)

_number_pat = regex.compile(r"\d+")

_tag_pattern = regex.compile(r"<(/?)(\w+)([^>]*?)(/?)\s*>", regex.IGNORECASE)

_comment_pattern = regex.compile(r"<!--(.*?)-->", regex.DOTALL)


def wordtok_to_str(wordtok: str) -> str:
    """
    Convert a wordtok to a string.
    """
    if wordtok == SENT_BR_TOK:
        return SENT_BR_STR
    if wordtok == PARA_BR_TOK:
        return PARA_BR_STR
    if wordtok == BOF_TOK:
        return BOF_STR
    if wordtok == EOF_TOK:
        return EOF_STR
    return wordtok


def wordtok_len(wordtok: str) -> int:
    """
    Char length of a wordtok.
    """
    return len(wordtok_to_str(wordtok))


_whitespace = regex.compile(r"\s+")


def normalize_wordtok(wordtok: str) -> str:
    if wordtok.isspace():
        normalized = SPACE_TOK
    elif wordtok.startswith("<"):
        normalized = _whitespace.sub(" ", wordtok)
    else:
        normalized = wordtok
    return normalized


def raw_text_to_wordtok_offsets(
    text: str, bof_eof=False
) -> Tuple[List[str], List[int]]:
    """
    Same as `raw_text_to_wordtoks`, but returns a list of tuples `(wordtok, offset)`.
    """
    wordtoks = []
    offsets = []
    offset = 0
    for match in _wordtok_pattern.finditer(text):
        wordtok = normalize_wordtok(match.group())
        wordtoks.append(wordtok)
        offsets.append(offset)
        offset = match.end()

    if bof_eof:
        wordtoks = [BOF_TOK] + wordtoks + [EOF_TOK]
        offsets = [0] + offsets + [len(text)]

    return wordtoks, offsets


def raw_text_to_wordtoks(text: str, bof_eof=False) -> List[str]:
    """
    Convert text to word tokens, including words, whitespace, punctuation, and
    HTML tags. Does not parse paragraph or sentence breaks. Normalizes all
    whitespace to a single space character.
    """
    wordtoks, _offsets = raw_text_to_wordtok_offsets(text, bof_eof)
    return wordtoks


def insert_para_wordtoks(text: str) -> str:
    """
    Replace paragraph breaks in text with para break tokens.
    """
    return _para_br_pattern.sub(PARA_BR_TOK, text)


def _initial_wordtoks(text: str, max_chars: int) -> List[str]:
    sub_text = text[:max_chars]
    wordtoks = raw_text_to_wordtoks(sub_text)
    if wordtoks:
        wordtoks.pop()  # Drop any cut off token.
    return wordtoks


def first_wordtok(text: str) -> Optional[str]:
    wordtoks = _initial_wordtoks(text, 100)
    return wordtoks[0] if wordtoks else None


def join_wordtoks(wordtoks: List[str]) -> str:
    """
    Join wordtoks back into a sentence.
    """
    wordtoks = [wordtok_to_str(wordtok) for wordtok in wordtoks]
    return "".join(wordtoks)


def visualize_wordtoks(wordtoks: List[str]) -> str:
    """
    Visualize wordtoks for debugging.
    """
    return SYMBOL_SEP + SYMBOL_SEP.join(wordtoks) + SYMBOL_SEP


def is_break_or_space(wordtok: str) -> bool:
    """
    Any kind of paragraph break, sentence break, or space (including
    the beginning or end of the document).
    """
    return (
        wordtok == PARA_BR_TOK
        or wordtok == SENT_BR_TOK
        or wordtok.isspace()
        or wordtok == BOF_TOK
        or wordtok == EOF_TOK
    )


def is_word(wordtok: str) -> bool:
    """
    Is this wordtok a word, not punctuation or whitespace or a number?
    """
    return bool(
        len(wordtok) > 0 and _word_pat.match(wordtok) and not _number_pat.match(wordtok)
    )


def is_number(wordtok: str) -> bool:
    """
    Is this wordtok a number?
    """
    return bool(_number_pat.match(wordtok))


def is_whitespace_or_punct(wordtok: str) -> bool:
    """
    Is this wordtok whitespace or punctuation?
    """
    return bool(not is_word(wordtok) and not is_number(wordtok))


@dataclass(frozen=True)
class Tag:
    """
    An HTML tag or comment.
    """

    name: str
    is_open: bool
    is_close: bool
    attrs: Dict[str, str]
    comment: Optional[str] = None


def parse_tag(wordtok: Optional[str] = None) -> Optional[Tag]:
    """
    Parse a wordtok to determine if it's an HTML tag and extract its components.
    """
    if not wordtok:
        return None

    match = _tag_pattern.match(wordtok)
    if not match:
        match = _comment_pattern.match(wordtok)
        if not match:
            return None
        return Tag(
            name="", is_open=False, is_close=False, attrs={}, comment=match.group(1)
        )

    is_open = not bool(match.group(1))
    is_close = bool(match.group(1) or match.group(4))
    tag_name = match.group(2).lower()
    attrs_str = match.group(3).strip()

    attrs = {}
    if attrs_str:
        attr_pattern = regex.compile(r'(\w+)\s*=\s*"([^"]*)"')
        for attr_match in attr_pattern.finditer(attrs_str):
            attr_name, attr_value = attr_match.groups()
            attrs[attr_name] = attr_value

    return Tag(name=tag_name, is_open=is_open, is_close=is_close, attrs=attrs)


def is_tag(
    wordtok: Optional[str] = None, tag_names: Optional[List[str]] = None
) -> bool:
    """
    Check if a wordtok is an HTML tag and optionally if it's in the specified tag names.
    """
    tag = parse_tag(wordtok)
    return bool(
        tag and (not tag_names or tag.name in [name.lower() for name in tag_names])
    )


def is_tag_close(wordtok: str, tag_names: Optional[List[str]] = None) -> bool:
    """
    Check if a wordtok is an HTML close tag and optionally if it's in the specified tag names.
    """
    tag = parse_tag(wordtok)
    return bool(
        tag
        and tag.is_close
        and (not tag_names or tag.name in [name.lower() for name in tag_names])
    )


def is_tag_open(wordtok: str, tag_names: Optional[List[str]] = None) -> bool:
    """
    Check if a wordtok is an HTML open tag and optionally if it's in the specified tag names.
    """
    tag = parse_tag(wordtok)
    return bool(
        tag
        and tag.is_open
        and (not tag_names or tag.name in [name.lower() for name in tag_names])
    )


def is_div(wordtok: Optional[str] = None) -> bool:
    return is_tag(wordtok, tag_names=["div"])


def is_entity(wordtok: Optional[str] = None) -> bool:
    """
    Check if a wordtok is an HTML entity.
    """
    return bool(wordtok and wordtok.startswith("&") and wordtok.endswith(";"))


header_tags = ["h1", "h2", "h3", "h4", "h5", "h6"]


def is_header_tag(wordtok: str) -> bool:
    """
    Is this wordtok an HTML header tag?
    """
    return is_tag(wordtok, tag_names=header_tags)


## Tests

_test_doc = dedent(
    """
    Hello, world!
    This is an "example sentence with punctuation.
    "Special characters: @#%^&*()"
    <span data-timestamp="5.60">Alright, guys.</span>

    <span data-timestamp="6.16">Here's the deal.</span>
    <span data-timestamp="7.92">You can follow me on my daily workouts.&nbsp;<span class="citation timestamp-link" data-src="resources/the_time_is_now.resource.yml"
    data-timestamp="10.29"><a
    href="https://www.youtube.com/">00:10</a></span>
    """
).strip()


def test_html_doc():
    wordtoks = raw_text_to_wordtoks(_test_doc, bof_eof=True)

    print("\n---Wordtoks test:")
    print(visualize_wordtoks(wordtoks))

    print("\n---Wordtoks with para br:")
    wordtoks_with_para = raw_text_to_wordtoks(
        insert_para_wordtoks(_test_doc), bof_eof=True
    )
    print(visualize_wordtoks(wordtoks_with_para))

    assert (
        visualize_wordtoks(wordtoks)
        == """⎪<-BOF->⎪Hello⎪,⎪ ⎪world⎪!⎪ ⎪This⎪ ⎪is⎪ ⎪an⎪ ⎪"⎪example⎪ ⎪sentence⎪ ⎪with⎪ ⎪punctuation⎪.⎪ ⎪"⎪Special⎪ ⎪characters⎪:⎪ ⎪@⎪#⎪%⎪^⎪&⎪*⎪(⎪)⎪"⎪ ⎪<span data-timestamp="5.60">⎪Alright⎪,⎪ ⎪guys⎪.⎪</span>⎪ ⎪<span data-timestamp="6.16">⎪Here⎪'⎪s⎪ ⎪the⎪ ⎪deal⎪.⎪</span>⎪ ⎪<span data-timestamp="7.92">⎪You⎪ ⎪can⎪ ⎪follow⎪ ⎪me⎪ ⎪on⎪ ⎪my⎪ ⎪daily⎪ ⎪workouts⎪.⎪&nbsp;⎪<span class="citation timestamp-link" data-src="resources/the_time_is_now.resource.yml" data-timestamp="10.29">⎪<a href="https://www.youtube.com/">⎪00⎪:⎪10⎪</a>⎪</span>⎪<-EOF->⎪"""
    )

    assert (
        visualize_wordtoks(wordtoks_with_para)
        == """⎪<-BOF->⎪Hello⎪,⎪ ⎪world⎪!⎪ ⎪This⎪ ⎪is⎪ ⎪an⎪ ⎪"⎪example⎪ ⎪sentence⎪ ⎪with⎪ ⎪punctuation⎪.⎪ ⎪"⎪Special⎪ ⎪characters⎪:⎪ ⎪@⎪#⎪%⎪^⎪&⎪*⎪(⎪)⎪"⎪ ⎪<span data-timestamp="5.60">⎪Alright⎪,⎪ ⎪guys⎪.⎪</span>⎪<-PARA-BR->⎪<span data-timestamp="6.16">⎪Here⎪'⎪s⎪ ⎪the⎪ ⎪deal⎪.⎪</span>⎪ ⎪<span data-timestamp="7.92">⎪You⎪ ⎪can⎪ ⎪follow⎪ ⎪me⎪ ⎪on⎪ ⎪my⎪ ⎪daily⎪ ⎪workouts⎪.⎪&nbsp;⎪<span class="citation timestamp-link" data-src="resources/the_time_is_now.resource.yml" data-timestamp="10.29">⎪<a href="https://www.youtube.com/">⎪00⎪:⎪10⎪</a>⎪</span>⎪<-EOF->⎪"""
    )

    print("\n---Searching tokens")

    print(search_tokens(wordtoks).at(0).seek_forward(["example"]).get_token())
    print(search_tokens(wordtoks).at(-1).seek_back(["follow"]).get_token())
    print(
        search_tokens(wordtoks)
        .at(-1)
        .seek_back(["Special"])
        .seek_forward(is_tag)
        .get_token()
    )

    assert search_tokens(wordtoks).at(0).seek_forward(["example"]).get_token() == (
        14,
        "example",
    )
    assert search_tokens(wordtoks).at(-1).seek_back(["follow"]).get_token() == (
        63,
        "follow",
    )
    assert search_tokens(wordtoks).at(-1).seek_back(["Special"]).seek_forward(
        is_tag
    ).get_token() == (39, '<span data-timestamp="5.60">')


def test_tag_functions():
    assert parse_tag("<div>") == Tag(name="div", is_open=True, is_close=False, attrs={})
    assert parse_tag("</div>") == Tag(
        name="div", is_open=False, is_close=True, attrs={}
    )
    assert parse_tag("<div/>") == Tag(name="div", is_open=True, is_close=True, attrs={})
    assert parse_tag("<!-- Comment -->") == Tag(
        name="", is_open=False, is_close=False, attrs={}, comment=" Comment "
    )

    assert is_tag("foo") == False
    assert is_tag("<a") == False
    assert is_tag("<div>") == True
    assert is_tag("</div>") == True
    assert is_tag("<span>") == True
    assert is_tag("<div>", ["div"]) == True
    assert is_tag("<div>", ["span"]) == False
    assert is_tag("<div/>") == True

    assert is_tag_close("</div>") == True
    assert is_tag_close("<div>") == False
    assert is_tag_close("</div>", ["div"]) == True
    assert is_tag_close("</div>", ["span"]) == False
    assert is_tag_close("<div/>") == True
    assert is_tag_open("<div>") == True
    assert is_tag_open("</div>") == False
    assert is_tag_open("<div>", ["div"]) == True
    assert is_tag_open("<div>", ["span"]) == False

    assert is_entity("&amp;") == True
    assert is_entity("nbsp;") == False
