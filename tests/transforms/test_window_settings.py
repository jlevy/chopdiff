from collections.abc import Callable

from chopdiff.docs.sizes import TextUnit
from chopdiff.transforms.window_settings import WINDOW_NONE, WindowSettings


def _raises(fn: Callable[[], object]) -> bool:
    try:
        fn()
        return False
    except ValueError:
        return True


def test_window_settings_rejects_invalid_combinations():
    # Negative size.
    assert _raises(lambda: WindowSettings(TextUnit.wordtoks, size=-5, shift=10))
    # Positive size with zero shift would loop forever.
    assert _raises(lambda: WindowSettings(TextUnit.wordtoks, size=100, shift=0))
    # Overlap larger than the window.
    assert _raises(lambda: WindowSettings(TextUnit.wordtoks, size=10, shift=5, min_overlap=20))
    # Negative overlap.
    assert _raises(lambda: WindowSettings(TextUnit.wordtoks, size=10, shift=5, min_overlap=-1))


def test_window_none_is_valid_and_falsy():
    # The no-window sentinel must remain constructible and is falsy (size 0).
    assert not WINDOW_NONE
    assert bool(WindowSettings(TextUnit.wordtoks, size=2048, shift=1792, min_overlap=8))


def test_valid_window_settings_construct():
    w = WindowSettings(TextUnit.wordtoks, size=2048, shift=1792, min_overlap=8)
    assert w.size == 2048
