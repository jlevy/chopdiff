from collections.abc import Callable, Generator
from typing import TypeVar

from chopdiff.divs.text_node import TextNode
from chopdiff.docs.sizes import TextUnit
from chopdiff.docs.text_doc import TextDoc

T = TypeVar("T")


def chunk_generator(
    doc: T,
    condition: Callable[[T], bool],
    slicer: Callable[[T, int, int], T],
    total_size: int,
) -> Generator[T, None, None]:
    """
    Walk through the elements of a document and yield sequential subdocs once they meet
    a specific condition.
    """

    start_index = 0
    current_index = 0

    while current_index < total_size:
        current_doc = slicer(doc, start_index, current_index)

        if condition(current_doc):
            yield current_doc
            start_index = current_index + 1
            current_index = start_index
        else:
            current_index += 1

    if start_index < total_size:
        yield slicer(doc, start_index, total_size)


def chunk_paras(doc: TextDoc, min_size: int, unit: TextUnit) -> Generator[TextDoc, None, None]:
    """
    Generate TextDoc chunks where each chunk is at least the specified minimum size.
    """

    def condition(slice: TextDoc) -> bool:
        return slice.size(unit) >= min_size

    def slicer(doc: TextDoc, start: int, end: int) -> TextDoc:
        return doc.sub_paras(start, end)

    total_paragraphs = len(doc.paragraphs)

    yield from chunk_generator(doc, condition, slicer, total_paragraphs)


def chunk_children(
    node: TextNode, min_size: int, unit: TextUnit
) -> Generator[TextNode, None, None]:
    """
    Generate TextNode chunks where each chunk is at least the specified minimum size.
    """

    def condition(slice: TextNode) -> bool:
        return slice.size(unit) >= min_size

    def slicer(node: TextNode, start: int, end: int) -> TextNode:
        return node.slice_children(start, end)

    total_children = len(node.children)

    yield from chunk_generator(node, condition, slicer, total_children)
