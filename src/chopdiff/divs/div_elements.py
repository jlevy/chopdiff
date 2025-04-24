import logging

from chopdiff.divs.chunk_utils import chunk_children, chunk_paras
from chopdiff.divs.parse_divs import parse_divs
from chopdiff.divs.text_node import TextNode
from chopdiff.docs.sizes import TextUnit
from chopdiff.docs.text_doc import TextDoc
from chopdiff.docs.wordtoks import first_wordtok, is_div
from chopdiff.html.html_in_md import div_wrapper, html_join_blocks

log = logging.getLogger(__name__)


CHUNK = "chunk"
"""Class name for a chunk of text."""

ORIGINAL = "original"
"""Class name for the original content."""

RESULT = "result"
"""Class name for the result of an LLM action."""

GROUP = "group"
"""Class name for a generic combination of elements."""


def div(class_name: str, *blocks: str | None) -> str:
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
    new_child_blocks: list[str],
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
