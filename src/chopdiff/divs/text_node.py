from __future__ import annotations

from collections.abc import Callable
from copy import copy
from dataclasses import dataclass, field

from prettyfmt import fmt_lines
from typing_extensions import override

from chopdiff.docs.sizes import TextUnit
from chopdiff.docs.text_doc import Splitter, TextDoc, default_sentence_splitter
from chopdiff.html.html_in_md import div_wrapper


@dataclass
class TextNode:
    """
    A node in parsed structured text, with reference offsets into the original text.
    Useful for parsing Markdown broken into div tags.
    """

    original_text: str

    # Offsets into the original text.
    offset: int
    content_start: int
    content_end: int

    tag_name: str | None = None
    class_name: str | None = None
    begin_marker: str | None = None
    end_marker: str | None = None

    children: list[TextNode] = field(default_factory=list)

    @property
    def end_offset(self) -> int:
        assert self.content_end >= 0
        return self.content_end + len(self.end_marker) if self.end_marker else self.content_end

    @property
    def contents(self) -> str:
        return self.original_text[self.content_start : self.content_end]

    def text_doc(self, sentence_splitter: Splitter = default_sentence_splitter) -> TextDoc:
        return TextDoc.from_text(self.contents, sentence_splitter=sentence_splitter)

    def slice_children(self, start: int, end: int) -> TextNode:
        if not self.children:
            raise ValueError("Cannot slice_children on a non-container node.")
        else:
            node_copy = copy(self)
            node_copy.children = node_copy.children[start:end]
            return node_copy

    def size(self, unit: TextUnit) -> int:
        if self.children:
            return sum(child.size(unit) for child in self.children)
        else:
            return self.text_doc().size(unit)

    def structure_summary(self) -> dict[str, int]:
        """
        Recursively tally the number of non-empty leaf nodes of different types as CSS-style paths.
        For example

        { "_total": 7, "div.chunk": 5, "div.chunk > div.summary": 2, "div.chunk > div.content": 5 }

        would mean that there were 7 chunk divs, each with a content div, and 2 with
        a summary div within it.
        """

        def path_join(*selectors: str) -> str:
            return " > ".join(selectors)

        def tally_recursive(node: TextNode, path: list[str], tally: dict[str, int]) -> None:
            # Skip leaf nodes.
            if not node.children and not node.tag_name and not node.class_name:
                return

            tag_selector = node.tag_name if node.tag_name else ""
            class_selector = f".{node.class_name}" if node.class_name else ""
            selector = f"{tag_selector}{class_selector}"
            new_path = path + [selector] if selector else path

            # Increment counts.
            path_key = path_join(*new_path)
            if path_key:
                tally[path_key] = tally.get(path_key, 0) + 1

            for child in node.children:
                tally_recursive(child, new_path, tally)

        tally: dict[str, int] = {}
        tally_recursive(self, [], tally)

        sorted_tally = dict(sorted(tally.items()))
        return sorted_tally

    def structure_summary_str(self) -> str | None:
        structure_summary = self.structure_summary()
        if not structure_summary:
            return None
        else:
            return "HTML structure:\n" + fmt_lines(
                [f"{count:6d}  {path}" for path, count in self.structure_summary().items()],
                prefix="",
            )

    def size_summary(self) -> str:
        """
        Return a summary of the size of the doc as well as a summary of its
        div/HTML structure.
        """
        summary = self.text_doc().size_summary()
        if structure_summary_str := self.structure_summary_str():
            summary += "\n" + structure_summary_str
        return summary

    def is_whitespace(self) -> bool:
        """
        Is this node whitespace only?
        """
        return not self.children and self.contents.strip() == ""

    def children_by_class_names(self, *class_names: str, recursive: bool = False) -> list[TextNode]:
        def collect_children(node: TextNode) -> list[TextNode]:
            matching_children = [
                child for child in node.children if child.class_name in class_names
            ]
            if recursive:
                for child in node.children:
                    matching_children.extend(collect_children(child))
            return matching_children

        return collect_children(self)

    def child_by_class_name(self, class_name: str) -> TextNode | None:
        nodes = self.children_by_class_names(class_name, recursive=False)
        if len(nodes) == 0:
            return None
        if len(nodes) > 1:
            raise ValueError(f"Multiple children with class name {class_name}")
        return nodes[0]

    def reassemble(self, padding: str = "\n\n") -> str:
        """
        Reassemble as string. If padding is provided (not ""), then strip, skip whitespace,
        and insert our own padding.
        """
        strip_fn: Callable[[str], str] = lambda s: s.strip() if padding else s
        skip_whitespace = bool(padding)

        if not self.children:
            if not self.tag_name:
                return strip_fn(self.contents)
            else:
                wrap = div_wrapper(self.class_name, padding=padding)
                return wrap(strip_fn(self.contents))
        else:
            padded_children = (padding or "").join(
                child.reassemble(padding)
                for child in self.children
                if (not skip_whitespace or not child.is_whitespace())
            )
            if not self.tag_name:
                return padded_children
            else:
                wrap = div_wrapper(self.class_name, padding=padding)
                return wrap(padded_children)

    @override
    def __str__(self):
        """
        Return a recursive, formatted string representation of the node and its children.
        """
        return self._str_recursive()

    def _str_recursive(self, level: int = 0, max_len: int = 40) -> str:
        indent = "    " * level
        content_preview = self.contents
        if len(content_preview) > max_len:
            content_preview = content_preview[:20] + "…" + content_preview[-20:]
        result = (
            f"{indent}TextNode(tag_name={self.tag_name} class_name={self.class_name} offset={self.offset},"
            f" content_start={self.content_start}, content_end={self.content_end}) "
            f"{repr(content_preview)}\n"
        )
        for child in self.children:
            result += child._str_recursive(level + 1)
        return result
