from chopdiff.docs.text_doc import TextDoc
from chopdiff.docs.token_diffs import diff_wordtoks, DiffOp, OpType
from chopdiff.docs.wordtoks import is_break_or_space, PARA_BR_TOK, SENT_BR_TOK
from chopdiff.transforms.diff_filters import (
    changes_whitespace,
    make_token_sequence_filter,
    no_word_lemma_changes,
    removes_word_lemmas,
    removes_words,
    WILDCARD_TOK,
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

    assert filter_fn(insert_op) == True
    assert filter_fn(delete_op) == False  # action is INSERT
    assert filter_fn(replace_op) == False
    assert filter_fn(equal_op) == False

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

    assert ignore_whitespace_filter_fn(insert_op_with_whitespace) == True
    assert ignore_whitespace_filter_fn(delete_op) == False  # action is INSERT
    assert ignore_whitespace_filter_fn(replace_op) == False
    assert ignore_whitespace_filter_fn(equal_op) == False


def test_no_word_changes_lemmatized():
    assert no_word_lemma_changes(DiffOp(OpType.INSERT, [], ["the"])) == False
    assert no_word_lemma_changes(DiffOp(OpType.DELETE, ["the"], [])) == False
    assert (
        no_word_lemma_changes(
            DiffOp(
                OpType.REPLACE,
                ["The", "dogs", "were", "running", "fast"],
                ["The", "dog", "was", "running"],
            )
        )
        == False
    )
    assert (
        no_word_lemma_changes(
            DiffOp(
                OpType.REPLACE,
                ["The", "dogs", "were", "running"],
                ["The", "dog", "was", "running"],
            )
        )
        == True
    )


def test_removes_words():

    assert removes_words(DiffOp(OpType.DELETE, ["Hello", " "], [])) == True
    assert removes_words(DiffOp(OpType.REPLACE, ["Hello", " ", "world"], ["world"])) == True
    assert removes_words(DiffOp(OpType.REPLACE, ["Hello", " ", "world"], ["World"])) == False
    assert removes_word_lemmas(DiffOp(OpType.REPLACE, ["Hello", " ", "world"], ["World"])) == True

    assert (
        removes_words(DiffOp(OpType.REPLACE, ["Hello", "*", "world"], ["hello", "*", "world"]))
        == False
    )
    assert (
        removes_word_lemmas(
            DiffOp(OpType.REPLACE, ["Hello", "*", "world"], ["hello", "*", "world"])
        )
        == True
    )

    assert removes_words(DiffOp(OpType.DELETE, ["Hello", "world"], [])) == True
    assert removes_word_lemmas(DiffOp(OpType.DELETE, ["Hello", "world"], [])) == True
