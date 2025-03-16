from textwrap import dedent

from chopdiff.docs.text_doc import SentIndex, TextDoc
from chopdiff.docs.token_diffs import DiffStats, diff_wordtoks, find_best_alignment

_short_text1 = dedent(
    """
    Paragraph one. Sentence 1a. Sentence 1b. Sentence 1c.
    
    Paragraph two. Sentence 2a. Sentence 2b. Sentence 2c.
    
    Paragraph three. Sentence 3a. Sentence 3b. Sentence 3c.
    """
).strip()


_short_text2 = dedent(
    """
    Paragraph one. Sentence 1a. Sentence 1b. Sentence 1c.
    Paragraph two blah. Sentence 2a. Sentence 2b. Sentence 2c.
    
    Paragraph three! Sentence 3a. Sentence 3b.
    """
).strip()

# _short_text3 contains all the whitespace and break-only changes from _short_text1 to _short_text2.
_short_text3 = dedent(
    """
    Paragraph one. Sentence 1a. Sentence 1b. Sentence 1c.
    Paragraph two. Sentence 2a. Sentence 2b. Sentence 2c.
    
    Paragraph three. Sentence 3a. Sentence 3b. Sentence 3c.
    """
).strip()


def test_lcs_diff_wordtoks():
    wordtoks1 = list(TextDoc.from_text(_short_text1).as_wordtoks())
    wordtoks2 = list(TextDoc.from_text(_short_text2).as_wordtoks())

    diff = diff_wordtoks(wordtoks1, wordtoks2)

    print("---Diff:")
    print(diff.as_diff_str(True))

    print("---Diff stats:")
    print(diff.stats())
    assert diff.stats() == DiffStats(added=5, removed=8, input_size=59)

    expected_diff = dedent(
        """
        TextDiff: add/remove +5/-8 out of 59 total:
        at pos    0 keep   19 toks:   ⎪Paragraph one. Sentence 1a. Sentence 1b. Sentence 1c.⎪
        at pos   19 repl    1 toks: - ⎪<-PARA-BR->⎪
                    repl    1 toks: + ⎪ ⎪
        at pos   20 keep    3 toks:   ⎪Paragraph two⎪
        at pos   23 add     2 toks: + ⎪ blah⎪
        at pos   23 keep    1 toks:   ⎪.⎪
        at pos   24 repl    1 toks: - ⎪ ⎪
                    repl    1 toks: + ⎪<-SENT-BR->⎪
        at pos   25 keep   18 toks:   ⎪Sentence 2a. Sentence 2b. Sentence 2c.<-PARA-BR->Paragraph three⎪
        at pos   43 repl    1 toks: - ⎪.⎪
                    repl    1 toks: + ⎪!⎪
        at pos   44 keep   10 toks:   ⎪<-SENT-BR->Sentence 3a. Sentence 3b.⎪
        at pos   54 del     5 toks: - ⎪ Sentence 3c.⎪
        """
    ).strip()

    assert str(diff.as_diff_str(True)) == expected_diff


def test_apply_to():
    wordtoks1 = list(TextDoc.from_text(_short_text1).as_wordtoks())
    wordtoks2 = list(TextDoc.from_text(_short_text2).as_wordtoks())

    diff = diff_wordtoks(wordtoks1, wordtoks2)

    print("---Before apply:")
    print("/".join(wordtoks1))
    print(diff)
    result = diff.apply_to(wordtoks1)
    print("---Result of apply:")
    print("/".join(result))
    print("---Expected:")
    print("/".join(wordtoks2))
    assert result == wordtoks2

    wordtoks3 = ["a", "b", "c", "d", "e"]
    wordtoks4 = ["a", "x", "c", "y", "e"]
    diff2 = diff_wordtoks(wordtoks3, wordtoks4)
    result2 = diff2.apply_to(wordtoks3)
    assert result2 == wordtoks4


def test_find_best_alignment():
    wordtoks1 = list(TextDoc.from_text(_short_text1).as_wordtoks())
    wordtoks2 = list(TextDoc.from_text(_short_text1).sub_doc(SentIndex(1, 1)).as_wordtoks())
    wordtoks3 = wordtoks2 + ["Extra", "wordtoks", "at", "the", "end"]
    wordtoks4 = list(wordtoks3)
    wordtoks4[0] = "X"
    wordtoks4[3] = "Y"

    print("---Alignment:")
    print("/".join(wordtoks1))
    print("/".join(wordtoks2))
    offset, (score, diff) = find_best_alignment(wordtoks1, wordtoks2, 1)
    print(f"Offset: {offset}, Score: {score}")
    print(diff)
    print()
    assert offset == 39
    assert score == 0.0
    assert diff.changes() == []

    offset, (score, diff) = find_best_alignment(wordtoks1, wordtoks3, 3)
    print(f"Offset: {offset}, Score: {score}")
    print(diff)
    print()
    assert offset == 39
    assert score == 0.0
    assert diff.changes() == []

    offset, (score, diff) = find_best_alignment(wordtoks1, wordtoks4, 3)
    print(f"Offset: {offset}, Score: {score}")
    print(diff)
    print()
    assert offset == 39
    assert score > 0 and score < 0.3
    assert diff.stats().nchanges() == 4
