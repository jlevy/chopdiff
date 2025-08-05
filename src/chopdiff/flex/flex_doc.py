"""
FlexDoc: Unified document interface with lazy loading for multiple views.
"""

from __future__ import annotations

from collections.abc import Iterator
from threading import RLock
from typing import Any

from typing_extensions import override

from chopdiff.divs.parse_divs import parse_divs
from chopdiff.divs.text_node import TextNode
from chopdiff.docs.sizes import TextUnit
from chopdiff.docs.text_doc import SentIndex, Splitter, TextDoc, default_sentence_splitter
from chopdiff.flex.thread_utils import synchronized
from chopdiff.sections.section_doc import SectionDoc
from chopdiff.sections.section_node import SectionNode


class FlexDoc:
    """
    Unified document interface with lazy parsing for different views.

    Provides thread-safe access to three document representations:
    - TextDoc: Token-based view for word/sentence/paragraph operations
    - TextNode: HTML div structure view for chunked content
    - SectionDoc: Markdown section hierarchy view

    All views are lazily loaded on first access and cached for efficiency.
    Thread safety is ensured through synchronized property access.

    Key properties (lazy loaded):
    - `text_doc`: Token-based view
    - `text_node`: Div-based view
    - `section_doc`: Section-based view

    Key methods:
    - `get_section_tokens()`: Get tokens for a specific section
    - `offset_to_coordinates()`: Map offset to all coordinate systems
    - `chunk_by_sections()`: Smart chunking respecting section boundaries
    - `get_stats()`: Comprehensive document statistics
    """

    def __init__(self, text: str, sentence_splitter: Splitter = default_sentence_splitter):
        """Initialize FlexDoc with document text."""
        self.original_text = text
        self.sentence_splitter = sentence_splitter
        self._lock = RLock()

        # Lazy-loaded views
        self._text_doc: TextDoc | None = None
        self._text_node: TextNode | None = None
        self._section_doc: SectionDoc | None = None

    @property
    @synchronized()
    def text_doc(self) -> TextDoc:
        """Get token-based view of the document (lazy loaded)."""
        if self._text_doc is None:
            self._text_doc = TextDoc.from_text(
                self.original_text, sentence_splitter=self.sentence_splitter
            )
        return self._text_doc

    @property
    @synchronized()
    def text_node(self) -> TextNode:
        """Get div-based view of the document (lazy loaded)."""
        if self._text_node is None:
            self._text_node = parse_divs(self.original_text, skip_whitespace=True)
        return self._text_node

    @property
    @synchronized()
    def section_doc(self) -> SectionDoc:
        """Get section-based view of the document (lazy loaded)."""
        if self._section_doc is None:
            self._section_doc = SectionDoc(self.original_text)
        return self._section_doc

    @synchronized()
    def get_section_tokens(self, section: SectionNode) -> list[str]:
        """Get word tokens for a specific section."""
        section_text = section.full_content
        section_doc = TextDoc.from_text(section_text, self.sentence_splitter)
        return list(section_doc.as_wordtoks())

    @synchronized()
    def get_section_text_doc(self, section: SectionNode) -> TextDoc:
        """Get a TextDoc instance for a specific section."""
        section_text = section.full_content
        return TextDoc.from_text(section_text, self.sentence_splitter)

    @synchronized()
    def offset_to_coordinates(self, offset: int) -> dict[str, Any]:
        """
        Map a character offset to all coordinate systems.

        Args:
            offset: Character position in the document

        Returns:
            Dict with keys:
            - offset: The input offset
            - section: SectionNode containing the offset
            - sentence: SentIndex of sentence containing the offset
            - paragraph: Paragraph index containing the offset
            - in_div: Whether offset is inside a div
            - div_path: List of div class names from root to offset
        """
        result: dict[str, Any] = {"offset": offset}

        # Find section
        result["section"] = self.section_doc.get_section_at_offset(offset)

        # Find sentence and paragraph
        if offset < len(self.original_text):
            # Find which sentence contains this offset
            sent_idx = None
            para_idx = None

            current_offset = 0
            for para_idx, para in enumerate(self.text_doc.paragraphs):
                para_start = current_offset
                para_end = para_start + len(para.reassemble())

                if para_start <= offset < para_end:
                    # Found the paragraph
                    result["paragraph"] = para_idx

                    # Find sentence within paragraph
                    sent_offset = 0
                    for sent_idx, sent in enumerate(para.sentences):
                        sent_end = sent_offset + len(sent.text)
                        if para_start + sent_offset <= offset < para_start + sent_end:
                            result["sentence"] = SentIndex(para_idx, sent_idx)
                            break
                        sent_offset = sent_end + 2  # Account for sentence break
                    break

                current_offset = para_end + 2  # Account for paragraph break

        # Find div information
        result["in_div"] = False
        div_path: list[str] = []
        result["div_path"] = div_path

        def find_div_at_offset(node: TextNode, path: list[str]) -> bool:
            if node.offset <= offset < node.end_offset:
                if node.class_name:
                    path.append(node.class_name)
                    result["in_div"] = True

                # Check children
                for child in node.children:
                    if find_div_at_offset(child, path):
                        return True

                return True
            return False

        find_div_at_offset(self.text_node, div_path)

        return result

    @synchronized()
    def chunk_by_sections(
        self,
        target_size: int,
        unit: TextUnit = TextUnit.words,
        respect_levels: list[int] | None = None,
    ) -> list[str]:
        """
        Chunk document into parts respecting section boundaries.

        Section levels in `respect_levels` force chunk boundaries (default: [1, 2]).
        """
        if respect_levels is None:
            respect_levels = [1, 2]

        chunks: list[str] = []
        current_sections: list[SectionNode] = []
        current_size = 0

        # Only iterate top-level sections to avoid duplicates
        # If respect_levels is set, use the minimum level
        if respect_levels:
            min_level = min(respect_levels)
            sections_to_process = [
                s for s in self.section_doc.iter_sections() if s.level == min_level
            ]
        else:
            # If no respect levels, process all sections individually
            sections_to_process = list(self.section_doc.iter_sections())

        for section in sections_to_process:
            # Calculate section size (includes all subsections)
            section_text = section.full_content
            section_doc = TextDoc.from_text(section_text, self.sentence_splitter)
            section_size = section_doc.size(unit)

            # Check if we should start new chunk
            # Break if adding this section would exceed target size
            will_exceed = current_size + section_size > target_size

            should_break = current_sections and will_exceed

            if should_break:
                # Emit current chunk
                chunk_text = self._merge_sections(current_sections)
                chunks.append(chunk_text)
                current_sections = []
                current_size = 0

            current_sections.append(section)
            current_size += section_size

        # Final chunk
        if current_sections:
            chunk_text = self._merge_sections(current_sections)
            chunks.append(chunk_text)

        return chunks

    def _merge_sections(self, sections: list[SectionNode]) -> str:
        """Merge multiple sections into a single text."""
        if not sections:
            return ""

        # Sort by offset to maintain order
        sorted_sections = sorted(sections, key=lambda s: s.start_offset)

        # Get text for each section
        parts: list[str] = []
        for section in sorted_sections:
            parts.append(section.full_content)

        # Join with appropriate spacing
        return "\n\n".join(parts)

    @synchronized()
    def iter_sections_with_tokens(self) -> Iterator[tuple[SectionNode, list[str]]]:
        """Iterate sections with their token representation."""
        for section in self.section_doc.iter_sections():
            tokens = self.get_section_tokens(section)
            yield section, tokens

    @synchronized()
    def get_stats(self) -> dict[str, Any]:
        """Get comprehensive statistics about the document from all three views."""
        # Check if document has actual HTML divs (not just text content)
        has_actual_divs = any(child.tag_name == "div" for child in self.text_node.children)

        stats: dict[str, Any] = {
            "size_chars": len(self.original_text),
            "section_stats": self.section_doc.get_stats(),
            "has_divs": has_actual_divs,
        }

        # Add token stats
        try:
            stats["token_stats"] = {
                "paragraphs": self.text_doc.size(TextUnit.paragraphs),
                "sentences": self.text_doc.size(TextUnit.sentences),
                "words": self.text_doc.size(TextUnit.words),
                "wordtoks": self.text_doc.size(TextUnit.wordtoks),
            }
        except Exception:
            stats["token_stats"] = None

        # Add div stats
        if stats["has_divs"]:
            div_summary = self.text_node.structure_summary()
            stats["div_stats"] = {
                "total_divs": sum(div_summary.values()),
                "div_types": list(div_summary.keys()),
            }
        else:
            stats["div_stats"] = None

        return stats

    @override
    def __repr__(self) -> str:
        """String representation for debugging."""
        size = len(self.original_text)
        loaded: list[str] = []
        if self._text_doc is not None:
            loaded.append("TextDoc")
        if self._text_node is not None:
            loaded.append("TextNode")
        if self._section_doc is not None:
            loaded.append("SectionDoc")

        loaded_str = f"loaded=[{', '.join(loaded)}]" if loaded else "loaded=[]"
        return f"FlexDoc(size={size} chars, {loaded_str})"
