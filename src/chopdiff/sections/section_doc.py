"""
SectionDoc: Document parsed as a tree of sections based on Markdown headers.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from typing import Any

from chopdiff.docs.sizes import TextUnit
from chopdiff.sections.section_node import SectionNode


class SectionDoc:
    """
    Document parsed as a tree of sections based on Markdown headers.

    Each section contains its header and all content until the next header
    of equal or higher level, including any subsections.
    """

    def __init__(self, text: str):
        """
        Parse a document into a section tree.

        Args:
            text: The document text to parse
        """
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
        """
        Find all Markdown headers in text with their offsets.

        Returns:
            List of tuples: (start_offset, end_offset, level, title)
        """
        headers = []

        # Regex pattern for Markdown headers
        # Matches 1-6 # symbols at line start, followed by space and text
        header_pattern = re.compile(r"^(#{1,6})\s+(.+?)$", re.MULTILINE)

        for match in header_pattern.finditer(text):
            start_offset = match.start()
            end_offset = match.end()

            # Find the actual end of line (including newline if present)
            line_end = text.find("\n", end_offset)
            if line_end != -1:
                end_offset = line_end + 1
            else:
                # Last line without newline
                end_offset = len(text)

            level = len(match.group(1))
            title = match.group(2).strip()

            headers.append((start_offset, end_offset, level, title))

        return headers

    def _build_section_tree(
        self, headers: list[tuple[int, int, int, str]], text: str
    ) -> SectionNode:
        """
        Build hierarchical section tree from headers.

        Args:
            headers: List of (start_offset, end_offset, level, title) tuples
            text: Original document text

        Returns:
            Root SectionNode containing the document tree
        """
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
        """
        Iterate sections within specified level range.

        Args:
            min_level: Minimum section level to include (default: 1)
            max_level: Maximum section level to include (default: None = no limit)

        Yields:
            SectionNode objects matching the level criteria
        """
        for section in self.root.iter_descendants(include_self=False):
            if section.level >= min_level and (max_level is None or section.level <= max_level):
                yield section

    def get_sections_at_level(self, level: int) -> list[SectionNode]:
        """
        Get all sections at a specific level.

        Args:
            level: The section level (1-6)

        Returns:
            List of sections at the specified level
        """
        return list(self.iter_sections(min_level=level, max_level=level))

    def get_section_at_offset(self, offset: int) -> SectionNode:
        """
        Find the deepest section containing the given character offset.

        Args:
            offset: Character position in the document

        Returns:
            The most specific section containing the offset, or root if offset is invalid
        """

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

        Args:
            *path_components: Sequence of section titles forming a path

        Returns:
            The section at the specified path, or None if not found

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

        Args:
            max_level: Maximum heading level to include (default: 3)
            include_path: Whether to include the full path for each entry

        Returns:
            List of dicts with keys:
            - level: Section level (1-6)
            - title: Section title
            - path: Full path to section (if include_path=True)
            - offset: Character offset of section start
            - has_children: Whether section has subsections
            - size: Size of section in characters
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

        Args:
            unit: Unit of measurement (only TextUnit.chars supported)

        Returns:
            Size in specified units

        Raises:
            NotImplementedError: If unit other than chars is requested
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

        Returns:
            Dict with keys:
            - total_sections: Total number of sections
            - max_depth: Maximum section nesting depth
            - sections_by_level: Dict mapping level to count
            - avg_section_size: Average section size in characters
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

    def __repr__(self) -> str:  # pyright: ignore[reportImplicitOverride]
        """String representation for debugging."""
        stats = self.get_stats()
        return (
            f"SectionDoc(sections={stats['total_sections']}, "
            f"max_depth={stats['max_depth']}, "
            f"size={len(self.original_text)} chars)"
        )
