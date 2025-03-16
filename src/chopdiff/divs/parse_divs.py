import copy
import re

from chopdiff.divs.text_node import TextNode

DIV_TAGS = re.compile(r"(<div\b[^>]*>|</div>)", re.IGNORECASE)

CLASS_NAME_PATTERN = re.compile(r"\bclass=\"([^\"]+)\"", re.IGNORECASE)


def parse_divs(text: str, skip_whitespace: bool = True) -> TextNode:
    """
    Parse a string recursively into `TextNode`s based on `<div>` tags.

    All offsets are relative to the original text. Text outside of a div tag is
    included as a `TextNode` with None markers.

    We do our own parsing to keep this simple and exactly preserve formatting.
    """
    parsed = _parse_divs_recursive(
        text,
        0,
        TextNode(original_text=text, offset=0, content_start=0, content_end=len(text)),
    )

    if skip_whitespace:
        parsed = _skip_whitespace_nodes(parsed)

    return parsed


def parse_divs_single(text: str, skip_whitespace: bool = True) -> TextNode:
    """
    Same as parse_divs but unwraps any singleton child.
    """
    divs = parse_divs(text, skip_whitespace=skip_whitespace)
    if len(divs.children) == 1:
        return divs.children[0]
    else:
        return divs


def _skip_whitespace_nodes(node: TextNode) -> TextNode:
    filtered_node = copy.copy(node)
    filtered_node.children = [
        _skip_whitespace_nodes(child) for child in node.children if not child.is_whitespace()
    ]
    return filtered_node


def _parse_divs_recursive(
    text: str,
    start_offset: int,
    result: TextNode,
) -> TextNode:
    current_offset = start_offset

    while current_offset < len(text):
        match = DIV_TAGS.search(text, current_offset)

        if not match:
            # No more div tags, add remaining content as a child node
            if current_offset < len(text):
                result.children.append(
                    TextNode(
                        original_text=text,
                        offset=current_offset,
                        content_start=current_offset,
                        content_end=len(text),
                    )
                )
            break

        if match.start() > current_offset:
            # Add content before the div tag as a child node.
            result.children.append(
                TextNode(
                    original_text=text,
                    offset=current_offset,
                    content_start=current_offset,
                    content_end=match.start(),
                )
            )

        tag = match.group(1)
        is_end_tag = tag.startswith("</")

        if is_end_tag:
            # Closing tag. We're done with this node.
            result.end_marker = tag
            result.content_end = match.start()
            current_offset = match.end()
            break
        else:
            # Opening tag. Create a new child node and recurse.
            class_match = CLASS_NAME_PATTERN.search(tag)
            class_name = class_match.group(1) if class_match else None

            child_node = TextNode(
                original_text=text,
                offset=match.start(),
                content_start=match.end(),
                content_end=len(text),
                tag_name="div",
                class_name=class_name,
                begin_marker=tag,
            )

            child_node = _parse_divs_recursive(text, match.end(), child_node)

            result.children.append(child_node)

            current_offset = child_node.end_offset

    return result


def parse_divs_by_class(text: str, class_name: str) -> list[TextNode]:
    """
    Parse div chunks into TextNodes.
    """

    text_node = parse_divs(text)

    matched_divs = text_node.children_by_class_names(class_name, recursive=True)

    if not matched_divs:
        raise ValueError(f"No `{class_name}` divs found in text.")

    return matched_divs
