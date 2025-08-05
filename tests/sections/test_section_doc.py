"""Tests for SectionDoc class."""

from textwrap import dedent

import pytest

from chopdiff.docs.sizes import TextUnit
from chopdiff.sections.section_doc import SectionDoc


class TestSectionDocParsing:
    """Test basic document parsing."""

    def test_parse_empty_document(self):
        """Test parsing empty document."""
        doc = SectionDoc("")

        assert doc.original_text == ""
        assert doc.root.level == 0
        assert doc.root.title is None
        assert len(doc.root.children) == 0
        assert list(doc.iter_sections()) == []

    def test_parse_no_headers(self):
        """Test parsing document with no headers."""
        text = "This is just plain text.\nWith multiple lines.\nBut no headers."
        doc = SectionDoc(text)

        assert doc.root.level == 0
        assert len(doc.root.children) == 0
        assert doc.root.body_content == text.strip()
        assert list(doc.iter_sections()) == []

    def test_parse_single_header(self):
        """Test parsing document with single header."""
        text = "# Main Title\n\nSome content here."
        doc = SectionDoc(text)

        sections = list(doc.iter_sections())
        assert len(sections) == 1

        section = sections[0]
        assert section.level == 1
        assert section.title == "Main Title"
        assert section.header_text == "# Main Title"
        assert section.body_content == "Some content here."
        assert section.start_offset == 0
        assert section.header_end_offset == 13  # Including newline

    def test_parse_multiple_headers_same_level(self):
        """Test parsing document with multiple headers at same level."""
        text = dedent("""
            # First Section
            
            First content.
            
            # Second Section
            
            Second content.
            
            # Third Section
            
            Third content.
        """).strip()

        doc = SectionDoc(text)
        sections = list(doc.iter_sections())

        assert len(sections) == 3
        assert all(s.level == 1 for s in sections)
        assert [s.title for s in sections] == ["First Section", "Second Section", "Third Section"]

        # Check content boundaries
        assert sections[0].body_content == "First content."
        assert sections[1].body_content == "Second content."
        assert sections[2].body_content == "Third content."

    def test_parse_nested_headers(self):
        """Test parsing document with nested headers."""
        text = dedent("""
            # Chapter 1
            
            Chapter intro.
            
            ## Section 1.1
            
            Section content.
            
            ### Subsection 1.1.1
            
            Subsection content.
            
            ## Section 1.2
            
            Another section.
            
            # Chapter 2
            
            Chapter 2 content.
        """).strip()

        doc = SectionDoc(text)

        # Check all sections
        all_sections = list(doc.iter_sections())
        assert len(all_sections) == 5

        # Check level 1 sections
        chapters = doc.get_sections_at_level(1)
        assert len(chapters) == 2
        assert chapters[0].title == "Chapter 1"
        assert chapters[1].title == "Chapter 2"

        # Check nesting
        ch1 = chapters[0]
        assert len(ch1.children) == 2
        assert ch1.children[0].title == "Section 1.1"
        assert ch1.children[1].title == "Section 1.2"

        # Check deep nesting
        sec11 = ch1.children[0]
        assert len(sec11.children) == 1
        assert sec11.children[0].title == "Subsection 1.1.1"
        assert sec11.children[0].level == 3

    def test_parse_with_preamble(self):
        """Test parsing document with content before first header."""
        text = dedent("""
            This is preamble text.
            Before any headers.
            
            # First Header
            
            Header content.
        """).strip()

        doc = SectionDoc(text)

        # Root should contain preamble
        assert doc.root.body_content == "This is preamble text.\nBefore any headers."

        sections = list(doc.iter_sections())
        assert len(sections) == 1
        assert sections[0].title == "First Header"


class TestSectionDocNavigation:
    """Test document navigation methods."""

    def test_iter_sections_with_levels(self):
        """Test iterating sections with level filters."""
        text = dedent("""
            # H1
            ## H2A
            ### H3
            ## H2B
            # H1B
            #### H4
        """).strip()

        doc = SectionDoc(text)

        # All sections
        all_secs = list(doc.iter_sections())
        assert len(all_secs) == 6

        # Min level
        level2plus = list(doc.iter_sections(min_level=2))
        assert len(level2plus) == 4
        assert all(s.level >= 2 for s in level2plus)

        # Max level
        level2max = list(doc.iter_sections(max_level=2))
        assert len(level2max) == 4
        assert all(s.level <= 2 for s in level2max)

        # Range
        level2to3 = list(doc.iter_sections(min_level=2, max_level=3))
        assert len(level2to3) == 3
        assert all(2 <= s.level <= 3 for s in level2to3)

    def test_get_section_at_offset(self):
        """Test finding section by character offset."""
        text = dedent("""
            # Main
            
            Main content.
            
            ## Sub
            
            Sub content.
        """).strip()

        doc = SectionDoc(text)

        # Offset in main section header
        section = doc.get_section_at_offset(3)  # Inside "# Main"
        assert section.title == "Main"

        # Offset in main section body
        section = doc.get_section_at_offset(15)  # Inside "Main content"
        assert section.title == "Main"

        # Offset in subsection
        section = doc.get_section_at_offset(35)  # Inside "## Sub"
        assert section.title == "Sub"

        # Offset at boundaries
        section = doc.get_section_at_offset(0)  # Start
        assert section.title == "Main"

        # Invalid offset returns root
        section = doc.get_section_at_offset(1000)
        assert section == doc.root

    def test_find_section_by_path(self):
        """Test finding section by title path."""
        text = dedent("""
            # Book
            ## Chapter 1
            ### Introduction
            ### Background
            ## Chapter 2
            ### Methods
            ### Results
        """).strip()

        doc = SectionDoc(text)

        # Single level path
        section = doc.find_section_by_path("Book")
        assert section is not None
        assert section.title == "Book"

        # Multi-level path
        section = doc.find_section_by_path("Book", "Chapter 1", "Background")
        assert section is not None
        assert section.title == "Background"
        assert section.level == 3

        # Partial path
        section = doc.find_section_by_path("Book", "Chapter 2")
        assert section is not None
        assert section.title == "Chapter 2"

        # Invalid path
        section = doc.find_section_by_path("Book", "Chapter 3")
        assert section is None

        section = doc.find_section_by_path("NonExistent")
        assert section is None


class TestSectionDocTOC:
    """Test table of contents generation."""

    def test_get_toc_basic(self):
        """Test basic TOC generation."""
        text = dedent("""
            # Chapter 1
            ## Section 1.1
            ### Subsection 1.1.1
            ## Section 1.2
            # Chapter 2
        """).strip()

        doc = SectionDoc(text)
        toc = doc.get_toc()

        assert len(toc) == 5

        # Check first entry
        assert toc[0]["level"] == 1
        assert toc[0]["title"] == "Chapter 1"
        assert toc[0]["has_children"]
        assert toc[0]["path"] == ["Chapter 1"]
        assert toc[0]["offset"] == 0

        # Check nested entry
        assert toc[2]["level"] == 3
        assert toc[2]["title"] == "Subsection 1.1.1"
        assert not toc[2]["has_children"]
        assert toc[2]["path"] == ["Chapter 1", "Section 1.1", "Subsection 1.1.1"]

    def test_get_toc_max_level(self):
        """Test TOC with max level limit."""
        text = dedent("""
            # H1
            ## H2
            ### H3
            #### H4
            ##### H5
        """).strip()

        doc = SectionDoc(text)

        toc_all = doc.get_toc(max_level=6)
        assert len(toc_all) == 5

        toc_limited = doc.get_toc(max_level=3)
        assert len(toc_limited) == 3
        assert all(entry["level"] <= 3 for entry in toc_limited)

    def test_get_toc_without_path(self):
        """Test TOC without path information."""
        text = "# Title\n## Subtitle"
        doc = SectionDoc(text)

        toc = doc.get_toc(include_path=False)
        assert len(toc) == 2
        assert "path" not in toc[0]
        assert "path" not in toc[1]


class TestSectionDocStats:
    """Test document statistics."""

    def test_get_stats_empty(self):
        """Test stats for empty document."""
        doc = SectionDoc("")
        stats = doc.get_stats()

        assert stats["total_sections"] == 0
        assert stats["max_depth"] == 0
        assert stats["sections_by_level"] == {}
        assert stats["avg_section_size"] == 0

    def test_get_stats_with_sections(self):
        """Test stats for document with sections."""
        text = dedent("""
            # Chapter 1
            
            Some content here.
            
            ## Section 1.1
            
            More content.
            
            ## Section 1.2
            
            Even more content.
            
            # Chapter 2
            
            Final content.
        """).strip()

        doc = SectionDoc(text)
        stats = doc.get_stats()

        assert stats["total_sections"] == 4
        assert stats["max_depth"] == 2  # Root -> Chapter -> Section
        assert stats["sections_by_level"] == {1: 2, 2: 2}
        assert stats["avg_section_size"] > 0

    def test_size_method(self):
        """Test size calculation."""
        text = "# Header\n\nContent with 30 characters."
        doc = SectionDoc(text)

        assert doc.size(TextUnit.chars) == len(text)

        # Other units not supported
        with pytest.raises(NotImplementedError):
            doc.size(TextUnit.words)


class TestSectionDocOffsets:
    """Test precise offset tracking."""

    def test_header_offset_tracking(self):
        """Test that header offsets are tracked correctly."""
        text = "# First\n\nContent.\n\n## Second\n\nMore."
        doc = SectionDoc(text)

        sections = list(doc.iter_sections())

        # First header: "# First\n"
        assert sections[0].start_offset == 0
        assert sections[0].header_end_offset == 8
        assert text[sections[0].start_offset : sections[0].header_end_offset] == "# First\n"

        # Second header: "## Second\n"
        assert sections[1].start_offset == 19
        assert sections[1].header_end_offset == 29
        assert text[sections[1].start_offset : sections[1].header_end_offset] == "## Second\n"

    def test_section_boundaries(self):
        """Test that section boundaries don't overlap."""
        text = dedent("""
            # A
            Content A.
            # B
            Content B.
            # C
            Content C.
        """).strip()

        doc = SectionDoc(text)
        sections = list(doc.iter_sections())

        # Check no overlaps
        for i in range(len(sections) - 1):
            assert sections[i].end_offset <= sections[i + 1].start_offset

        # Check full coverage
        assert sections[0].start_offset == 0
        assert sections[-1].end_offset == len(text)

    def test_windows_line_endings(self):
        """Test parsing with Windows line endings."""
        text = "# Header\r\n\r\nContent here.\r\n"
        doc = SectionDoc(text)

        sections = list(doc.iter_sections())
        assert len(sections) == 1
        assert sections[0].title == "Header"
        assert sections[0].body_content == "Content here."


class TestSectionDocCodeBlocks:
    """Test handling of code blocks in section parsing."""

    def test_headers_in_code_blocks_ignored(self):
        """Headers inside code blocks should not be parsed as sections."""
        text = dedent("""
            # Real Header
            
            Some content.
            
            ```python
            # This is a comment, not a header
            def foo():
                pass
            ```
            
            ## Another Real Header
            
            ```
            # Shell comment
            echo "hello"
            ```
            
            More content.
            """).strip()

        doc = SectionDoc(text)
        sections = list(doc.iter_sections())

        # Should only have 2 real headers (root is excluded by default)
        assert len(sections) == 2
        assert sections[0].level == 1 and sections[0].title == "Real Header"
        assert sections[1].level == 2 and sections[1].title == "Another Real Header"

    def test_nested_code_blocks(self):
        """Test code blocks with nested content."""
        text = dedent("""
            # Main Section
            
            ```markdown
            # This is example markdown
            ## Not a real header
            ```
            
            ## Real Subsection
            """).strip()

        doc = SectionDoc(text)
        sections = list(doc.iter_sections())

        assert len(sections) == 2
        assert sections[0].title == "Main Section"
        assert sections[1].title == "Real Subsection"


class TestSectionDocRepr:
    """Test string representation."""

    def test_repr(self):
        """Test __repr__ method."""
        text = dedent("""
            # H1
            ## H2
            ### H3
        """).strip()

        doc = SectionDoc(text)
        repr_str = repr(doc)

        assert "SectionDoc" in repr_str
        assert "sections=3" in repr_str
        assert "max_depth=" in repr_str
        assert f"size={len(text)} chars" in repr_str
