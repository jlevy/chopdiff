from chopdiff.transforms.sliding_transforms import filtered_transform
from chopdiff.transforms.window_settings import WINDOW_NONE
from flexdoc.docs.text_doc import TextDoc
from flexdoc.docs.token_diffs import DiffOp


def _reject_all(op: DiffOp) -> bool:  # pyright: ignore[reportUnusedParameter]
    return False


def _accept_all(op: DiffOp) -> bool:  # pyright: ignore[reportUnusedParameter]
    return True


def _to_goodbye(_doc: TextDoc) -> TextDoc:
    return TextDoc.from_text("goodbye")


def _identity(doc: TextDoc) -> TextDoc:
    return doc


def test_filtered_transform_enforces_filter_without_windowing():
    # A reject-all filter must keep the original even when windowing is disabled.
    doc = TextDoc.from_text("hello")
    out_none = filtered_transform(doc, _to_goodbye, None, diff_filter=_reject_all)
    assert out_none.reassemble() == "hello"

    out_window_none = filtered_transform(doc, _to_goodbye, WINDOW_NONE, diff_filter=_reject_all)
    assert out_window_none.reassemble() == "hello"


def test_filtered_transform_accepts_changes_when_filter_allows():
    doc = TextDoc.from_text("hello")
    out = filtered_transform(doc, _to_goodbye, None, diff_filter=_accept_all)
    assert out.reassemble() == "goodbye"


def test_filtered_transform_does_not_mutate_input():
    doc = TextDoc.from_text("First one. Second two.")
    before = doc.reassemble()
    filtered_transform(doc, _identity, None, diff_filter=_accept_all)
    assert doc.reassemble() == before
