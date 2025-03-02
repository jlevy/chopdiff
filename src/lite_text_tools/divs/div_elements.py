import logging
from textwrap import dedent
from typing import List, Optional

from ..divs.chunk_utils import chunk_children, chunk_paras
from ..divs.parse_divs import parse_divs, parse_divs_single
from ..divs.text_node import TextNode
from ..docs.text_doc import TextDoc, TextUnit
from ..docs.wordtoks import first_wordtok, is_div
from ..html.html_in_md import div_wrapper, html_join_blocks

log = logging.getLogger(__name__)


CHUNK = "chunk"
"""Class name for a chunk of text."""

ORIGINAL = "original"
"""Class name for the original content."""

RESULT = "result"
"""Class name for the result of an LLM action."""

GROUP = "group"
"""Class name for a generic combination of elements."""


def div(class_name: str, *blocks: Optional[str]) -> str:
    """
    Convenience to create Markdown-compatible div with HTML in its own paragraphs.
    """
    return div_wrapper(class_name=class_name, padding="\n\n")(html_join_blocks(*blocks))


def div_get_original(element: TextNode, child_name: str = ORIGINAL) -> str:
    """
    Get content of the named child element if it exists, otherwise use the whole contents.
    """
    child = element.child_by_class_name(child_name)
    return child.contents if child else element.contents


def div_insert_wrapped(
    element: TextNode,
    new_child_blocks: List[str],
    container_class: str = CHUNK,
    original_class: str = ORIGINAL,
    at_front: bool = True,
) -> str:
    """
    Insert new children into a div element. As a base case, wrap the original
    content in a child div if it's not already present as a child.
    """

    original_element = element.child_by_class_name(original_class)
    if original_element:
        prev_contents = element.contents
    else:
        prev_contents = div(original_class, element.contents)

    if at_front:
        blocks = [*new_child_blocks, prev_contents]
    else:
        blocks = [prev_contents, *new_child_blocks]

    return div(container_class, html_join_blocks(*blocks))


def chunk_text_as_divs(text: str, min_size: int, unit: TextUnit, class_name: str = CHUNK) -> str:
    """
    Add HTML divs around "chunks" of text paragraphs or top-level divs, where each chunk
    is at least the specified minimum size.
    """

    if is_div(first_wordtok(text)):
        log.info("Chunking paragraphs using divs.")
        parsed = parse_divs(text)
        div_chunks = chunk_children(parsed, min_size, unit)
        chunk_strs = [chunk.reassemble() for chunk in div_chunks]
        size_summary = parsed.size_summary()
    else:
        log.info("Chunking paragraphs using newlines.")
        doc = TextDoc.from_text(text)
        doc_chunks = chunk_paras(doc, min_size, unit)
        chunk_strs = [chunk.reassemble() for chunk in doc_chunks]
        size_summary = doc.size_summary()

    result_divs = [div(class_name, chunk_str) for chunk_str in chunk_strs]

    log.info("Added %s div chunks on doc:\n%s", len(result_divs), size_summary)

    return "\n\n".join(result_divs)


## Tests


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
