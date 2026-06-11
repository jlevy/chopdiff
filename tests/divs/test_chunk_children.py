from textwrap import dedent

from chopdiff.divs.div_elements import chunk_text_as_divs
from flexdoc.docs.sizes import TextUnit


def test_chunk_text_as_divs_with_div_leading_input():
    # Three top-level divs: each should become its own chunk, not a repeated whole document.
    text = dedent(
        """
        <div class="item">Alpha alpha alpha.</div>

        <div class="item">Beta beta beta.</div>

        <div class="item">Gamma gamma gamma.</div>
        """
    ).strip()
    out = chunk_text_as_divs(text, min_size=1, unit=TextUnit.words)
    # Each distinct content appears exactly once (the bug repeated the whole document).
    assert out.count("Alpha alpha alpha.") == 1
    assert out.count("Beta beta beta.") == 1
    assert out.count("Gamma gamma gamma.") == 1
