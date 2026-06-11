from chopdiff.transforms.sliding_windows import sliding_para_window
from flexdoc.docs.text_doc import TextDoc


def _identity_norm(s: str) -> str:
    return s


def test_sliding_para_window_keeps_all_sentences():
    # Paragraph windows must include every sentence of each paragraph, not just the first.
    # (Sentences must be long enough that the splitter actually splits them.)
    doc = TextDoc.from_text(
        "Alpha alpha alpha. Beta beta beta.\n\nGamma gamma gamma. Delta delta delta."
    )
    assert len(doc.paragraphs[0].sentences) == 2  # guard: the splitter really split
    windows = [w.reassemble() for w in sliding_para_window(doc, 1, normalizer=_identity_norm)]
    assert len(windows) == 2
    assert "Alpha alpha alpha." in windows[0] and "Beta beta beta." in windows[0]
    assert "Gamma gamma gamma." in windows[1] and "Delta delta delta." in windows[1]
