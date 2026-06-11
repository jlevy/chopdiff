from collections.abc import Callable

from flexdoc.docs.token_diffs import diff_wordtoks
from flexdoc.docs.token_mapping import TokenMapping


def _raises_value_error(fn: Callable[[], object]) -> bool:
    try:
        fn()
        return False
    except ValueError:
        return True


def test_apply_to_validates_source_identity():
    a = ["a", " ", "b", " ", "c"]
    b = ["a", " ", "X", " ", "c"]
    diff = diff_wordtoks(a, b)
    # Applying to the genuine source reproduces the target.
    assert diff.apply_to(a) == b
    # Applying to a different but same-length source must raise, not silently return b.
    wrong = ["z", " ", "b", " ", "c"]
    assert len(wrong) == len(a)
    assert _raises_value_error(lambda: diff.apply_to(wrong))


def test_token_mapping_rejects_wholesale_replacement():
    # A full replacement is one REPLACE op, so the old op-count gate (1/20) passed it;
    # the changed-token gate rejects it.
    tokens1 = [f"w{i}" for i in range(20)]
    tokens2 = [f"x{i}" for i in range(20)]
    assert _raises_value_error(lambda: TokenMapping(tokens1, tokens2, max_diff_frac=0.4))


def test_token_mapping_accepts_small_change():
    tokens1 = [f"w{i}" for i in range(20)]
    tokens2 = list(tokens1)
    tokens2[5] = "changed"
    # One token changed out of 20 is well under the threshold.
    TokenMapping(tokens1, tokens2, max_diff_frac=0.4)
