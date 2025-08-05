"""
Section node for hierarchical document structure based on Markdown headers.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import override


@dataclass
class SectionNode:
    """
    A section in a document, containing header and all descendant content.

    A section represents a complete unit of a document including:
    - The header line itself
    - All content until the next header of equal or higher level
    - All subsections (headers of lower level)
    """

    # Section metadata
    level: int  # 0 for root, 1-6 for headers
    title: str | None  # Header text, None for root

    # Content tracking with character offsets
    start_offset: int  # Start position in original text
    end_offset: int  # End position in original text (exclusive)
    header_end_offset: int  # End of header line (including newline)

    # Tree structure
    parent: SectionNode | None = None
    children: list[SectionNode] = field(default_factory=list)

    # Original text reference (set after construction)
    _original_text: str | None = field(default=None, repr=False)

    def set_original_text(self, text: str) -> None:
        """Set reference to original text for content extraction."""
        self._original_text = text
        for child in self.children:
            child.set_original_text(text)

    @property
    def body_start_offset(self) -> int:
        """Start of body content (after header)."""
        return self.header_end_offset

    @property
    def body_content(self) -> str:
        """
        Get body content excluding subsection headers.

        This returns only the content that belongs directly to this section,
        not including any subsection headers or their content.
        """
        if not self._original_text:
            return ""

        # For root node, body is everything before first child
        if self.level == 0:
            if self.children:
                return self._original_text[
                    self.body_start_offset : self.children[0].start_offset
                ].strip()
            else:
                return self._original_text[self.body_start_offset : self.end_offset].strip()

        # Find where first subsection starts
        if self.children:
            first_child_start = min(child.start_offset for child in self.children)
            return self._original_text[self.body_start_offset : first_child_start].strip()
        else:
            return self._original_text[self.body_start_offset : self.end_offset].strip()

    @property
    def full_content(self) -> str:
        """Get full section content including subsections."""
        if not self._original_text:
            return ""
        return self._original_text[self.start_offset : self.end_offset]

    @property
    def header_text(self) -> str:
        """Get just the header line text."""
        if not self._original_text or self.level == 0:
            return ""
        return self._original_text[self.start_offset : self.header_end_offset].strip()

    def iter_descendants(self, include_self: bool = True) -> Iterator[SectionNode]:
        """
        Iterate over all descendants in depth-first order.

        Args:
            include_self: Whether to include this node in the iteration

        Yields:
            SectionNode objects in depth-first order
        """
        if include_self:
            yield self
        for child in self.children:
            yield from child.iter_descendants(include_self=True)

    def find_section_by_title(self, title: str, recursive: bool = True) -> SectionNode | None:
        """
        Find first descendant section with matching title.

        Args:
            title: Title to search for (case-sensitive)
            recursive: Whether to search in all descendants or just direct children

        Returns:
            First matching section or None if not found
        """
        if recursive:
            for section in self.iter_descendants(include_self=True):
                if section.title == title:
                    return section
        else:
            if self.title == title:
                return self
            for child in self.children:
                if child.title == title:
                    return child
        return None

    def get_path(self) -> list[str]:
        """
        Get path from root to this section as list of titles.

        Returns:
            List of titles from root to this section (excluding root)
        """
        path: list[str] = []
        current = self
        while current and current.title is not None:
            path.append(current.title)
            current = current.parent
        return list(reversed(path))

    def get_depth(self) -> int:
        """
        Get depth of this node in the tree.

        Returns:
            0 for root, 1 for direct children of root, etc.
        """
        depth = 0
        current = self.parent
        while current:
            depth += 1
            current = current.parent
        return depth

    def is_leaf(self) -> bool:
        """Check if this section has no subsections."""
        return len(self.children) == 0

    def get_size_chars(self) -> int:
        """Get size of full content in characters."""
        return len(self.full_content)

    def get_siblings(self) -> list[SectionNode]:
        """Get list of sibling sections (excluding self)."""
        if not self.parent:
            return []
        return [child for child in self.parent.children if child is not self]

    def get_next_sibling(self) -> SectionNode | None:
        """Get next sibling section or None if last child."""
        if not self.parent:
            return None
        siblings = self.parent.children
        try:
            idx = siblings.index(self)
            if idx < len(siblings) - 1:
                return siblings[idx + 1]
        except ValueError:
            pass
        return None

    def get_previous_sibling(self) -> SectionNode | None:
        """Get previous sibling section or None if first child."""
        if not self.parent:
            return None
        siblings = self.parent.children
        try:
            idx = siblings.index(self)
            if idx > 0:
                return siblings[idx - 1]
        except ValueError:
            pass
        return None

    @override
    def __repr__(self) -> str:
        """String representation for debugging."""
        title_str = f'"{self.title}"' if self.title else "None"
        return (
            f"SectionNode(level={self.level}, title={title_str}, "
            f"offset={self.start_offset}:{self.end_offset}, "
            f"children={len(self.children)})"
        )
