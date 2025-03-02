from textwrap import dedent

from chopdiff.divs.div_elements import CHUNK, chunk_text_as_divs, div, div_insert_wrapped
from chopdiff.divs.parse_divs import parse_divs_single
from chopdiff.docs.sizes import TextUnit


def test_div_insert_child():
    node1 = parse_divs_single("Chunk text.")
    node2 = parse_divs_single(div(CHUNK, "Chunk text."))

    child_str = div("new", "New child text.")

    new_result1 = div_insert_wrapped(node1, [child_str])
    new_result2 = div_insert_wrapped(node2, [child_str])

    print("\n---test_div_insert_child---")
    print("\nnode1:")
    print(node1.original_text)
    print("\nnode2:")
    print(node2.original_text)
    print("\nnew_child_str:")
    print(child_str)
    print("\nnew_result1:")
    print(new_result1)
    print("\nnew_result2:")
    print(new_result2)

    assert (
        new_result1
        == dedent(
            """
            <div class="chunk">

            <div class="new">

            New child text.

            </div>

            <div class="original">

            Chunk text.

            </div>

            </div>
            """
        ).strip()
    )

    assert new_result2 == new_result1

    node3 = parse_divs_single(new_result1)

    another_child_str = div("another", "Another child text.")

    new_result3 = div_insert_wrapped(node3, [another_child_str])
    print("\nnew_result3:")
    print(new_result3)

    assert (
        new_result3
        == dedent(
            """
            <div class="chunk">

            <div class="another">

            Another child text.

            </div>

            <div class="new">

            New child text.

            </div>

            <div class="original">

            Chunk text.

            </div>

            </div>
            """
        ).strip()
    )


_med_test_doc = dedent(
    """
        # Title

        Hello World. This is an example sentence. And here's another one!

        ## Subtitle

        This is a new paragraph.
        It has several sentences.
        There may be line breaks within a paragraph, but these should not affect handlingof the paragraph.
        There are also [links](http://www.google.com) and **bold** and *italic* text.

        ### Itemized List

        - Item 1

        - Item 2

        - Item 3

        <div>  extra 
        </div>

        Blah blah.
        """
).strip()


def test_chunk_text_into_divs():
    assert chunk_text_as_divs("", 7, TextUnit.words) == ""
    assert (
        chunk_text_as_divs("hello", 100, TextUnit.words) == '<div class="chunk">\n\nhello\n\n</div>'
    )

    chunked = chunk_text_as_divs(_med_test_doc, 7, TextUnit.words)

    print("\n---test_chunk_paras_as_divs---")
    print("Chunked doc:\n---\n" + chunked + "\n---")

    expected_first_chunk = dedent(
        """
        <div class="chunk">

        # Title

        Hello World. This is an example sentence. And here's another one!

        </div>
        """
    ).strip()

    assert chunked.startswith(expected_first_chunk)
    assert chunked.endswith("</div>")
    assert chunked.count("<div class=") == 4
    assert chunked.count("</div>") == 5  # Extra spurious </div>.
