"""
SectionDoc: Document parsed as a tree of sections based on Markdown headers.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from typing_extensions import override

try:
    from marko import Markdown
    from marko.block import Heading
    from marko.element import Element
    from marko.ext.gfm import GFM
except ImportError:
    # Fall back to using flowmark's marko if direct import fails
    from marko import Markdown
    from marko.block import Heading
    from marko.element import Element
    from marko.ext.gfm import GFM

from chopdiff.docs.sizes import TextUnit
from chopdiff.sections.section_node import SectionNode


class SectionDoc:
    """
    Document parsed as a tree of sections based on Markdown headers.

    Each section contains its header and all content until the next header
    of equal or higher level, including any subsections.

    Key properties:
    - `original_text`: The original document text
    - `root`: Root SectionNode of the section tree

    Key methods:
    - `iter_sections()`: Iterate sections within level range
    - `get_sections_at_level()`: Get all sections at specific level
    - `get_section_at_offset()`: Find section containing character offset
    - `find_section_by_path()`: Navigate by path of titles
    - `get_toc()`: Generate table of contents
    - `get_stats()`: Get document structure statistics
    """

    def __init__(self, text: str):
        """Parse a document into a section tree."""
        self.original_text = text
        self.root = self._parse_sections(text)
        self.root.set_original_text(text)

    def _parse_sections(self, text: str) -> SectionNode:
        """Parse text into section tree based on Markdown headers."""
        # Find all headers with their positions
        headers = self._find_headers_with_offsets(text)

        # Build the section tree
        return self._build_section_tree(headers, text)

    def _find_headers_with_offsets(self, text: str) -> list[tuple[int, int, int, str]]:
        """Find all Markdown headers in text with their offsets using proper parsing."""
        headers: list[tuple[int, int, int, str]] = []

        # Create a markdown parser
        # We'll use GFM extension for better compatibility
        parser = Markdown(extensions=[GFM])

        # Parse the document
        doc = parser.parse(text)

        # Traverse the document tree to find all heading elements
        self._collect_headers(doc, text, headers)

        # Sort headers by their start offset to ensure proper ordering
        headers.sort(key=lambda h: h[0])

        return headers

    def _collect_headers(
        self, element: Element, text: str, headers: list[tuple[int, int, int, str]]
    ) -> None:
        """Recursively collect headers from the markdown element tree."""
        if isinstance(element, Heading):
            # Get the header level
            level = element.level

            # Get the header text by rendering its children
            title = self._get_header_text(element)

            # Find the position in the original text
            # Marko doesn't directly provide character offsets, so we need to find it
            # We'll use the line number information if available
            start_offset, end_offset = self._find_element_offset(element, text)

            if start_offset is not None and end_offset is not None:
                headers.append((start_offset, end_offset, level, title))

        # Recursively process children
        if hasattr(element, "children"):
            children = getattr(element, "children", [])
            if isinstance(children, list):
                for child in children:
                    if isinstance(child, Element):
                        self._collect_headers(child, text, headers)

    def _get_header_text(self, heading: Heading) -> str:
        """Extract the text content from a heading element."""
        text_parts: list[str] = []

        def extract_text(elem: Any) -> None:
            if isinstance(elem, str):
                text_parts.append(elem)
            elif hasattr(elem, "children"):
                if isinstance(elem.children, str):
                    text_parts.append(elem.children)
                elif isinstance(elem.children, list):
                    for child in elem.children:
                        extract_text(child)

        extract_text(heading)
        return "".join(text_parts).strip()

    def _find_element_offset(self, element: Element, text: str) -> tuple[int | None, int | None]:
        """Find the character offset of an element in the original text."""
        # Marko elements have line/column information
        if hasattr(element, "line_number"):
            # Convert line number to character offset
            lines = text.split("\n")
            line_num = getattr(element, "line_number", 1) - 1  # 0-based

            if 0 <= line_num < len(lines):
                # Calculate start offset
                start_offset = sum(len(lines[i]) + 1 for i in range(line_num))  # +1 for newline

                # Find the actual header in this line
                line = lines[line_num]
                # The line should start with # symbols
                if line.lstrip().startswith("#"):
                    # Adjust for leading whitespace
                    start_offset += len(line) - len(line.lstrip())

                # End offset is the end of the line
                end_offset = start_offset + len(line)
                if line_num < len(lines) - 1:
                    end_offset += 1  # Include newline

                return start_offset, end_offset

        # Fallback: search for the header text in the document
        # This is less accurate but works when line numbers aren't available
        if isinstance(element, Heading):
            header_text = self._get_header_text(element)
            header_prefix = "#" * element.level + " " + header_text

            # Search for this header in the text
            idx = text.find(header_prefix)
            if idx != -1:
                end_idx = text.find("\n", idx)
                if end_idx == -1:
                    end_idx = len(text)
                else:
                    end_idx += 1  # Include newline
                return idx, end_idx

        return None, None

    def _build_section_tree(
        self, headers: list[tuple[int, int, int, str]], text: str
    ) -> SectionNode:
        """Build hierarchical section tree from headers."""
        # Create root section
        root = SectionNode(
            level=0, title=None, start_offset=0, end_offset=len(text), header_end_offset=0
        )

        if not headers:
            # No headers in document
            return root

        # Stack to track current section hierarchy
        section_stack = [root]

        for i, (header_start, header_end, level, title) in enumerate(headers):
            # Pop sections from stack until we find the appropriate parent
            # A section at level N is a child of the nearest section with level < N
            while section_stack[-1].level >= level:
                section_stack.pop()

            # Determine section end (start of next section at same or higher level)
            section_end = len(text)
            for j in range(i + 1, len(headers)):
                next_start, _, next_level, _ = headers[j]
                if next_level <= level:
                    section_end = next_start
                    break

            # Create the section node
            section = SectionNode(
                level=level,
                title=title,
                start_offset=header_start,
                end_offset=section_end,
                header_end_offset=header_end,
                parent=section_stack[-1],
            )

            # Update previous sibling's end offset if needed
            if section_stack[-1].children:
                prev_sibling = section_stack[-1].children[-1]
                # Only update if the previous sibling would overlap
                if prev_sibling.end_offset > header_start:
                    prev_sibling.end_offset = header_start

            # Add to parent and stack
            section_stack[-1].children.append(section)
            section_stack.append(section)

        return root

    def iter_sections(
        self, min_level: int = 1, max_level: int | None = None
    ) -> Iterator[SectionNode]:
        """Iterate sections within specified level range."""
        for section in self.root.iter_descendants(include_self=False):
            if section.level >= min_level and (max_level is None or section.level <= max_level):
                yield section

    def get_sections_at_level(self, level: int) -> list[SectionNode]:
        """Get all sections at a specific level (1-6)."""
        return list(self.iter_sections(min_level=level, max_level=level))

    def get_section_at_offset(self, offset: int) -> SectionNode:
        """Find the deepest section containing the given character offset."""

        def _find_deepest(node: SectionNode) -> SectionNode | None:
            if not (node.start_offset <= offset < node.end_offset):
                return None

            # Check children for more specific match
            for child in node.children:
                if deeper := _find_deepest(child):
                    return deeper

            return node

        return _find_deepest(self.root) or self.root

    def find_section_by_path(self, *path_components: str) -> SectionNode | None:
        """
        Navigate to a section by following a path of titles.

        Example:
            doc.find_section_by_path("Chapter 1", "Introduction", "Background")
        """
        current = self.root

        for component in path_components:
            found = False
            for child in current.children:
                if child.title == component:
                    current = child
                    found = True
                    break

            if not found:
                return None

        return current if current != self.root else None

    def get_toc(self, max_level: int = 3, include_path: bool = True) -> list[dict[str, Any]]:
        """
        Generate table of contents for the document.

        Returns list of dicts with keys: level, title, path (if include_path),
        offset, has_children, size.
        """
        toc = []

        for section in self.iter_sections(max_level=max_level):
            entry: dict[str, Any] = {
                "level": section.level,
                "title": section.title,
                "offset": section.start_offset,
                "has_children": bool(section.children),
                "size": section.get_size_chars(),
            }

            if include_path:
                entry["path"] = section.get_path()

            toc.append(entry)

        return toc

    def size(self, unit: TextUnit = TextUnit.chars) -> int:
        """
        Get size of the document in specified units.

        Note: Currently only supports character count. For other units,
        use FlexDoc which integrates with TextDoc.
        """
        if unit == TextUnit.chars:
            return len(self.original_text)
        else:
            raise NotImplementedError(
                f"SectionDoc only supports TextUnit.chars. Use FlexDoc for {unit} support."
            )

    def get_stats(self) -> dict[str, Any]:
        """
        Get statistics about the document structure.

        Returns dict with keys: total_sections, max_depth, sections_by_level, avg_section_size.
        """
        sections = list(self.iter_sections())

        if not sections:
            return {
                "total_sections": 0,
                "max_depth": 0,
                "sections_by_level": {},
                "avg_section_size": 0,
            }

        sections_by_level: dict[int, int] = {}
        total_size = 0
        max_depth = 0

        for section in sections:
            level = section.level
            sections_by_level[level] = sections_by_level.get(level, 0) + 1
            total_size += section.get_size_chars()
            max_depth = max(max_depth, section.get_depth())

        return {
            "total_sections": len(sections),
            "max_depth": max_depth,
            "sections_by_level": dict(sorted(sections_by_level.items())),
            "avg_section_size": total_size // len(sections) if sections else 0,
        }

    @override
    def __repr__(self) -> str:
        """String representation for debugging."""
        stats = self.get_stats()
        return (
            f"SectionDoc(sections={stats['total_sections']}, "
            f"max_depth={stats['max_depth']}, "
            f"size={len(self.original_text)} chars)"
        )
