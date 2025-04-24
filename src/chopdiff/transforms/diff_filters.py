from collections.abc import Callable
from typing import TypeAlias

from typing_extensions import override

from chopdiff.docs.token_diffs import DiffFilter, DiffOp, OpType
from chopdiff.docs.wordtoks import (
    is_break_or_space,
    is_tag_close,
    is_tag_open,
    is_whitespace_or_punct,
    is_word,
)
from chopdiff.util.lemmatize import lemmatize, lemmatized_equal


class WildcardToken:
    """
    Wildcard token that matches any number of tokens (including zero).
    """

    @override
    def __str__(self):
        return "*"


WILDCARD_TOK = WildcardToken()

TokenMatcher: TypeAlias = list[str] | Callable[[str], bool]

TokenPattern: TypeAlias = str | Callable[[str], bool] | WildcardToken


def _matches_pattern(tokens: list[str], pattern: list[TokenPattern]) -> bool:
    def match_from(i: int, j: int) -> bool:
        while i <= len(tokens) and j < len(pattern):
            pattern_elem = pattern[j]
            if pattern_elem == WILDCARD_TOK:
                # If '*' is the last pattern element, it matches any remaining tokens.
                if j + 1 == len(pattern):
                    return True
                # Advance pattern index to next pattern after ANY_TOKEN.
                j += 1
                while i < len(tokens):
                    if match_from(i, j):
                        return True
                    i += 1
                return False
            else:
                if i >= len(tokens):
                    return False
                token = tokens[i]
                if isinstance(pattern_elem, str):
                    if token != pattern_elem:
                        return False
                elif callable(pattern_elem):
                    if not pattern_elem(token):
                        return False
                else:
                    return False
                i += 1
                j += 1
        # Skip any remaining ANY_TOKEN in the pattern.
        while j < len(pattern) and pattern[j] == WILDCARD_TOK:
            j += 1
        # The tokens match the pattern if both indices are at the end.
        return i == len(tokens) and j == len(pattern)

    return match_from(0, 0)


def make_token_sequence_filter(
    pattern: list[TokenPattern],
    action: OpType | None = None,
    ignore: TokenMatcher | None = None,
) -> DiffFilter:
    """
    Returns a `DiffFilter` that accepts `DiffOps` where the tokens match the given pattern.
    The pattern is a list where each element can be a string or a predicate function that
    takes a token and returns a bool (True if the token matches).
    The '*' in the pattern list matches any number of tokens (including zero).
    If `action` is specified, only `DiffOps` with that action are considered.
    """

    def filter_fn(diff_op: DiffOp) -> bool:
        if action and diff_op.action != action:
            return False

        tokens = diff_op.all_changed()
        if ignore and isinstance(ignore, str):
            tokens = [tok for tok in tokens if tok not in ignore]
        elif ignore and callable(ignore):
            tokens = [tok for tok in tokens if not ignore(tok)]

        return _matches_pattern(tokens, pattern)

    return filter_fn


def changes_whitespace(diff_op: DiffOp) -> bool:
    """
    Only accepts changes to sentence and paragraph breaks and whitespace.
    """

    return all(is_break_or_space(tok) for tok in diff_op.all_changed())


def changes_whitespace_or_punct(diff_op: DiffOp) -> bool:
    """
    Only accepts changes to punctuation and whitespace.
    """

    return all(is_whitespace_or_punct(tok) for tok in diff_op.all_changed())


def no_word_lemma_changes(diff_op: DiffOp) -> bool:
    """
    Only accept changes that preserve the lemmatized form of words.
    """
    if diff_op.action == OpType.EQUAL:
        return True
    elif diff_op.action == OpType.REPLACE:
        return lemmatized_equal(
            " ".join(tok for tok in diff_op.left if is_word(tok)),
            " ".join(tok for tok in diff_op.right if is_word(tok)),
        )
    else:
        return len([tok for tok in diff_op.all_changed() if is_word(tok)]) == 0


def removes_words(diff_op: DiffOp) -> bool:
    """
    Only accept changes that remove words. Changes to spaces and punctuation are allowed.
    """
    if diff_op.action == OpType.DELETE or diff_op.action == OpType.EQUAL:
        return True
    elif diff_op.action == OpType.REPLACE or diff_op.action == OpType.INSERT:
        return all(is_whitespace_or_punct(tok) for tok in set(diff_op.right) - set(diff_op.left))
    else:
        return False


def removes_word_lemmas(diff_op: DiffOp) -> bool:
    """
    Only accept changes that remove words or replace them with their lemmatized forms.
    Changes to spaces and punctuation are allowed.
    """
    if diff_op.action == OpType.DELETE or diff_op.action == OpType.EQUAL:
        return True
    elif diff_op.action == OpType.REPLACE or diff_op.action == OpType.INSERT:
        left_words = [tok for tok in diff_op.left if is_word(tok)]
        right_words = [tok for tok in diff_op.right if is_word(tok)]

        left_lemmas = [lemmatize(word) for word in left_words]
        right_lemmas = [lemmatize(word) for word in right_words]

        return set(right_lemmas).issubset(set(left_lemmas))
    else:
        return False


def adds_headings(diff_op: DiffOp) -> bool:
    """
    Only accept changes that add contents within header tags.
    """
    headers = ["h1", "h2", "h3", "h4", "h5", "h6"]
    is_header = lambda tok: is_tag_open(tok, tag_names=headers)  # pyright: ignore
    is_header_close = lambda tok: is_tag_close(tok, tag_names=headers)  # pyright: ignore
    matcher = make_token_sequence_filter(
        [is_header, WILDCARD_TOK, is_header_close],
        action=OpType.INSERT,
        ignore=is_break_or_space,
    )
    return matcher(diff_op)
