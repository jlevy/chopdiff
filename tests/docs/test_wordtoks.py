from textwrap import dedent

from chopdiff.docs.search_tokens import search_tokens
from chopdiff.docs.wordtoks import (
    insert_para_wordtoks,
    is_entity,
    is_tag,
    is_tag_close,
    is_tag_open,
    parse_tag,
    Tag,
    visualize_wordtoks,
    wordtokenize,
)


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
    wordtoks = wordtokenize(_test_doc, bof_eof=True)

    print("\n---Wordtoks test:")
    print(visualize_wordtoks(wordtoks))

    print("\n---Wordtoks with para br:")
    wordtoks_with_para = wordtokenize(insert_para_wordtoks(_test_doc), bof_eof=True)
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
    print(search_tokens(wordtoks).at(-1).seek_back(["Special"]).seek_forward(is_tag).get_token())

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
    assert parse_tag("</div>") == Tag(name="div", is_open=False, is_close=True, attrs={})
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
