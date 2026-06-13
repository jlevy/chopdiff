from flexdoc import FlexDoc
from flexdoc.docs.sizes import TextUnit

from chopdiff.transforms.sliding_transforms import sliding_wordtok_window_transform
from chopdiff.transforms.window_settings import WindowSettings


def _shrink_after_first():
    """Transform that passes the first window through and empties later ones."""
    state = {"n": 0}

    def transform(d: FlexDoc) -> FlexDoc:
        state["n"] += 1
        return d if state["n"] == 1 else FlexDoc.from_text("")

    return transform


def test_wordtok_window_alignment_failure_raises_readable_error():
    doc = FlexDoc.from_text("alpha beta. gamma delta. epsilon zeta. eta theta.")
    settings = WindowSettings(TextUnit.wordtoks, size=10, shift=8, min_overlap=2)
    raised: str | None = None
    try:
        sliding_wordtok_window_transform(doc, _shrink_after_first(), settings)
    except ValueError as e:
        raised = str(e)
    assert raised is not None
    # The old code passed %s args to ValueError and never interpolated them.
    assert "%s" not in raised
    assert "min_overlap" in raised


def test_wordtok_window_alignment_failure_skip_does_not_raise():
    doc = FlexDoc.from_text("alpha beta. gamma delta. epsilon zeta. eta theta.")
    settings = WindowSettings(TextUnit.wordtoks, size=10, shift=8, min_overlap=2)
    out = sliding_wordtok_window_transform(
        doc, _shrink_after_first(), settings, on_alignment_failure="skip"
    )
    assert out is not None
