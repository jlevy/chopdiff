from chopdiff.docs.text_doc import TextDoc
from chopdiff.docs.token_diffs import DiffOp, OpType, diff_wordtoks
from chopdiff.docs.wordtoks import PARA_BR_TOK, SENT_BR_TOK, is_break_or_space
from chopdiff.transforms.diff_filters import (
    WILDCARD_TOK,
    changes_whitespace,
    make_token_sequence_filter,
    no_word_lemma_changes,
    removes_word_lemmas,
    removes_words,
)


def test_filter_br_and_space():
    from ..docs.test_token_diffs import _short_text1, _short_text2, _short_text3

    wordtoks1 = list(TextDoc.from_text(_short_text1).as_wordtoks())
    wordtoks2 = list(TextDoc.from_text(_short_text2).as_wordtoks())
    wordtoks3 = list(TextDoc.from_text(_short_text3).as_wordtoks())

    diff = diff_wordtoks(wordtoks1, wordtoks2)

    accepted, rejected = diff.filter(changes_whitespace)

    accepted_result = accepted.apply_to(wordtoks1)
    rejected_result = rejected.apply_to(wordtoks1)

    print("---Filtered diff:")
    print("Original: " + "/".join(wordtoks1))
    print("Full diff:", diff)
    print("Accepted diff:", accepted)
    print("Rejected diff:", rejected)
    print("Accepted result: " + "/".join(accepted_result))
    print("Rejected result: " + "/".join(rejected_result))

    assert accepted_result == wordtoks3


def test_token_sequence_filter_with_predicate():
    insert_op = DiffOp(OpType.INSERT, [], [SENT_BR_TOK, "<h1>", "Title", "</h1>", PARA_BR_TOK])
    delete_op = DiffOp(OpType.DELETE, [SENT_BR_TOK, "<h1>", "Old Title", "</h1>", PARA_BR_TOK], [])
    replace_op = DiffOp(OpType.REPLACE, ["Some", "text"], ["New", "text"])
    equal_op = DiffOp(OpType.EQUAL, ["Unchanged"], ["Unchanged"])

    action = OpType.INSERT
    filter_fn = make_token_sequence_filter(
        [is_break_or_space, "<h1>", WILDCARD_TOK, "</h1>", is_break_or_space], action
    )

    assert filter_fn(insert_op)
    assert not filter_fn(delete_op)  # action is INSERT
    assert not filter_fn(replace_op)
    assert not filter_fn(equal_op)

    ignore_whitespace_filter_fn = make_token_sequence_filter(
        ["<h1>", WILDCARD_TOK, "</h1>"],
        action=OpType.INSERT,
        ignore=is_break_or_space,
    )

    insert_op_with_whitespace = DiffOp(
        OpType.INSERT,
        [],
        [" ", SENT_BR_TOK, " ", "<h1>", "Title", "</h1>", " ", PARA_BR_TOK, " "],
    )

    assert ignore_whitespace_filter_fn(insert_op_with_whitespace)
    assert not ignore_whitespace_filter_fn(delete_op)  # action is INSERT
    assert not ignore_whitespace_filter_fn(replace_op)
    assert not ignore_whitespace_filter_fn(equal_op)


def test_no_word_changes_lemmatized():
    assert not no_word_lemma_changes(DiffOp(OpType.INSERT, [], ["the"]))
    assert not no_word_lemma_changes(DiffOp(OpType.DELETE, ["the"], []))
    assert not no_word_lemma_changes(
        DiffOp(
            OpType.REPLACE,
            ["The", "dogs", "were", "running", "fast"],
            ["The", "dog", "was", "running"],
        )
    )
    assert no_word_lemma_changes(
        DiffOp(
            OpType.REPLACE,
            ["The", "dogs", "were", "running"],
            ["The", "dog", "was", "running"],
        )
    )


def test_removes_words():
    assert removes_words(DiffOp(OpType.DELETE, ["Hello", " "], []))
    assert removes_words(DiffOp(OpType.REPLACE, ["Hello", " ", "world"], ["world"]))
    assert not removes_words(DiffOp(OpType.REPLACE, ["Hello", " ", "world"], ["World"]))
    assert removes_word_lemmas(DiffOp(OpType.REPLACE, ["Hello", " ", "world"], ["World"]))

    assert not removes_words(
        DiffOp(OpType.REPLACE, ["Hello", "*", "world"], ["hello", "*", "world"])
    )
    assert removes_word_lemmas(
        DiffOp(OpType.REPLACE, ["Hello", "*", "world"], ["hello", "*", "world"])
    )

    assert removes_words(DiffOp(OpType.DELETE, ["Hello", "world"], []))
    assert removes_word_lemmas(DiffOp(OpType.DELETE, ["Hello", "world"], []))
