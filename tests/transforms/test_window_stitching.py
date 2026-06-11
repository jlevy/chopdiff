from chopdiff.transforms.sliding_transforms import sliding_wordtok_window_transform
from chopdiff.transforms.window_settings import WindowSettings
from flexdoc.docs.sizes import TextUnit
from flexdoc.docs.text_doc import TextDoc


def _shrink_after_first():
    """Transform that passes the first window through and empties later ones."""
    state = {"n": 0}

    def transform(d: TextDoc) -> TextDoc:
        state["n"] += 1
        return d if state["n"] == 1 else TextDoc.from_text("")

    return transform


def test_wordtok_window_alignment_failure_raises_readable_error():
    doc = TextDoc.from_text("alpha beta. gamma delta. epsilon zeta. eta theta.")
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
    doc = TextDoc.from_text("alpha beta. gamma delta. epsilon zeta. eta theta.")
    settings = WindowSettings(TextUnit.wordtoks, size=10, shift=8, min_overlap=2)
    out = sliding_wordtok_window_transform(
        doc, _shrink_after_first(), settings, on_alignment_failure="skip"
    )
    assert out is not None
