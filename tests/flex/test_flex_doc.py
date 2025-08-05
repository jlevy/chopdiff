"""Tests for FlexDoc unified document interface."""

import threading
from concurrent.futures import ThreadPoolExecutor
from textwrap import dedent

from chopdiff.docs.sizes import TextUnit
from chopdiff.flex.flex_doc import FlexDoc


class TestFlexDocBasics:
    """Test basic FlexDoc functionality."""

    def test_create_flex_doc(self):
        """Test creating a FlexDoc instance."""
        text = "# Title\n\nSome content here."
        doc = FlexDoc(text)

        assert doc.original_text == text
        assert doc._text_doc is None  # Not loaded yet
        assert doc._text_node is None
        assert doc._section_doc is None

    def test_lazy_loading_text_doc(self):
        """Test that text_doc is loaded lazily."""
        text = "This is a paragraph.\n\nThis is another paragraph."
        doc = FlexDoc(text)

        # Not loaded initially
        assert doc._text_doc is None

        # Access triggers loading
        text_doc = doc.text_doc
        assert text_doc is not None
        assert doc._text_doc is text_doc

        # Subsequent access returns same instance
        assert doc.text_doc is text_doc

    def test_lazy_loading_section_doc(self):
        """Test that section_doc is loaded lazily."""
        text = "# Header\n\nContent."
        doc = FlexDoc(text)

        # Not loaded initially
        assert doc._section_doc is None

        # Access triggers loading
        section_doc = doc.section_doc
        assert section_doc is not None
        assert doc._section_doc is section_doc

        # Check content
        sections = list(section_doc.iter_sections())
        assert len(sections) == 1
        assert sections[0].title == "Header"

    def test_lazy_loading_text_node(self):
        """Test that text_node is loaded lazily."""
        text = '<div class="test">Content</div>'
        doc = FlexDoc(text)

        # Not loaded initially
        assert doc._text_node is None

        # Access triggers loading
        text_node = doc.text_node
        assert text_node is not None
        assert doc._text_node is text_node

    def test_repr(self):
        """Test string representation."""
        text = "# Test\n\nContent"
        doc = FlexDoc(text)

        # Initially nothing loaded
        assert repr(doc) == f"FlexDoc(size={len(text)} chars, loaded=[])"

        # Access some views
        _ = doc.text_doc
        _ = doc.section_doc

        repr_str = repr(doc)
        assert "TextDoc" in repr_str
        assert "SectionDoc" in repr_str
        assert "TextNode" not in repr_str  # Not loaded


class TestFlexDocCrossView:
    """Test cross-view operations."""

    def test_get_section_tokens(self):
        """Test getting tokens for a section."""
        text = dedent("""
            # Main Section
            
            This is the main content.
            With multiple sentences.
            
            ## Subsection
            
            Subsection content here.
        """).strip()

        doc = FlexDoc(text)

        # Get main section
        main_section = doc.section_doc.root.children[0]
        assert main_section.title == "Main Section"

        # Get tokens
        tokens = doc.get_section_tokens(main_section)
        assert isinstance(tokens, list)
        assert len(tokens) > 0

        # Should include header and content tokens
        assert "#" in tokens
        assert "Main" in tokens
        assert "content" in tokens

    def test_get_section_text_doc(self):
        """Test creating TextDoc for a section."""
        text = dedent("""
            # Section One
            
            First paragraph.
            
            Second paragraph.
            
            # Section Two
            
            Another section.
        """).strip()

        doc = FlexDoc(text)

        # Get first section
        section_one = doc.section_doc.root.children[0]

        # Get TextDoc for section
        section_doc = doc.get_section_text_doc(section_one)

        assert section_doc.size(TextUnit.paragraphs) == 3  # Header + 2 paragraphs
        assert section_doc.size(TextUnit.sentences) >= 3

    def test_offset_to_coordinates(self):
        """Test mapping offset to all coordinate systems."""
        text = dedent("""
            # Chapter 1
            
            First paragraph here.
            
            <div class="note">
            This is a note.
            </div>
            
            ## Section 1.1
            
            More content.
        """).strip()

        doc = FlexDoc(text)

        # Test offset in first paragraph
        coords = doc.offset_to_coordinates(15)  # Inside "First paragraph"

        assert coords["offset"] == 15
        assert coords["section"].title == "Chapter 1"
        assert coords["paragraph"] == 1  # Second paragraph (header is 0)
        assert "sentence" in coords

        # Test offset in div
        div_offset = text.find("This is a note")
        coords = doc.offset_to_coordinates(div_offset)

        assert coords["in_div"]
        assert "note" in coords["div_path"]

        # Test offset in subsection
        subsection_offset = text.find("More content")
        coords = doc.offset_to_coordinates(subsection_offset)

        assert coords["section"].title == "Section 1.1"


class TestFlexDocChunking:
    """Test document chunking functionality."""

    def test_chunk_by_sections_basic(self):
        """Test basic section-based chunking."""
        text = dedent("""
            # Chapter 1
            
            Short content.
            
            # Chapter 2
            
            Another short chapter.
            
            # Chapter 3
            
            Final chapter content.
        """).strip()

        doc = FlexDoc(text)

        # Chunk with high target size (should get one chunk)
        chunks = doc.chunk_by_sections(target_size=1000, unit=TextUnit.chars)
        assert len(chunks) == 1

        # Chunk with small target size and respect level 1
        chunks = doc.chunk_by_sections(target_size=20, unit=TextUnit.chars, respect_levels=[1])
        assert len(chunks) == 3  # Each chapter in its own chunk

    def test_chunk_by_sections_nested(self):
        """Test chunking with nested sections."""
        text = dedent("""
            # Part 1
            
            ## Chapter 1.1
            
            Some content here that is long enough to be meaningful.
            
            ## Chapter 1.2
            
            More content in this chapter with multiple words.
            
            # Part 2
            
            ## Chapter 2.1
            
            Final chapter content goes here.
        """).strip()

        doc = FlexDoc(text)

        # Respect only level 1 boundaries
        chunks = doc.chunk_by_sections(target_size=100, unit=TextUnit.chars, respect_levels=[1])

        assert len(chunks) == 2  # Part 1 and Part 2
        assert "Part 1" in chunks[0]
        assert "Part 2" in chunks[1]

        # Don't respect any levels (pure size-based)
        chunks = doc.chunk_by_sections(target_size=50, unit=TextUnit.chars, respect_levels=[])

        assert len(chunks) > 2  # Should split more finely


class TestFlexDocThreadSafety:
    """Test thread safety of FlexDoc."""

    def test_concurrent_view_access(self):
        """Test concurrent access to different views."""
        text = dedent("""
            # Title
            
            Content paragraph one.
            
            <div class="box">
            Div content.
            </div>
            
            Content paragraph two.
        """).strip()

        doc = FlexDoc(text)
        results = {}
        errors = []

        def access_text_doc():
            try:
                td = doc.text_doc
                results["text_doc_paras"] = td.size(TextUnit.paragraphs)
            except Exception as e:
                errors.append(f"text_doc: {e}")

        def access_section_doc():
            try:
                sd = doc.section_doc
                results["section_count"] = len(list(sd.iter_sections()))
            except Exception as e:
                errors.append(f"section_doc: {e}")

        def access_text_node():
            try:
                tn = doc.text_node
                results["has_divs"] = len(tn.children) > 0
            except Exception as e:
                errors.append(f"text_node: {e}")

        # Run all accesses concurrently
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(access_text_doc),
                executor.submit(access_section_doc),
                executor.submit(access_text_node),
            ]
            for future in futures:
                future.result()

        # Check no errors
        assert len(errors) == 0

        # Check all views were accessed
        assert "text_doc_paras" in results
        assert "section_count" in results
        assert "has_divs" in results

    def test_concurrent_same_view_access(self):
        """Test concurrent access to the same view."""
        text = "# Header\n\n" + "\n\n".join([f"Paragraph {i}." for i in range(100)])
        doc = FlexDoc(text)

        access_count = 0
        access_lock = threading.Lock()

        def access_section_doc():
            nonlocal access_count
            sections = list(doc.section_doc.iter_sections())
            with access_lock:
                access_count += len(sections)

        # Many threads accessing same view
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(access_section_doc) for _ in range(50)]
            for future in futures:
                future.result()

        # Each thread should see 1 section, 50 threads total
        assert access_count == 50

    def test_lazy_loading_thread_safety(self):
        """Test that lazy loading happens only once even with concurrent access."""
        text = "# Test\n\nContent"

        doc = FlexDoc(text)

        # Access from multiple threads
        results = []

        def access_text_doc():
            td = doc.text_doc
            results.append(td)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(access_text_doc) for _ in range(50)]
            for future in futures:
                future.result()

        # All threads should get the same instance
        assert len(results) == 50
        first_instance = results[0]
        assert all(td is first_instance for td in results)

        # The text_doc should have been created exactly once
        assert doc._text_doc is first_instance


class TestFlexDocStatistics:
    """Test document statistics functionality."""

    def test_get_stats_basic(self):
        """Test basic statistics gathering."""
        text = dedent("""
            # Main Title
            
            First paragraph with some content.
            
            Second paragraph here.
            
            ## Subsection
            
            Subsection content.
        """).strip()

        doc = FlexDoc(text)
        stats = doc.get_stats()

        assert stats["size_chars"] == len(text)
        assert "section_stats" in stats
        assert stats["section_stats"]["total_sections"] == 2

        assert "token_stats" in stats
        assert stats["token_stats"]["paragraphs"] >= 3
        assert stats["token_stats"]["sentences"] >= 3

        assert not stats["has_divs"]
        assert stats["div_stats"] is None

    def test_get_stats_with_divs(self):
        """Test statistics with div content."""
        text = dedent("""
            <div class="wrapper">
            <div class="content">
            Text here.
            </div>
            <div class="footer">
            Footer text.
            </div>
            </div>
        """).strip()

        doc = FlexDoc(text)
        stats = doc.get_stats()

        assert stats["has_divs"]
        assert stats["div_stats"] is not None
        assert stats["div_stats"]["total_divs"] > 0
        assert "wrapper" in str(stats["div_stats"]["div_types"])


class TestFlexDocIteration:
    """Test iteration methods."""

    def test_iter_sections_with_tokens(self):
        """Test iterating sections with their tokens."""
        text = dedent("""
            # Section A
            
            Content for A.
            
            # Section B
            
            Content for B.
        """).strip()

        doc = FlexDoc(text)

        sections_and_tokens = list(doc.iter_sections_with_tokens())

        assert len(sections_and_tokens) == 2

        # Check first section
        section_a, tokens_a = sections_and_tokens[0]
        assert section_a.title == "Section A"
        assert len(tokens_a) > 0
        assert any("Content" in tok for tok in tokens_a)

        # Check second section
        section_b, tokens_b = sections_and_tokens[1]
        assert section_b.title == "Section B"
        assert len(tokens_b) > 0
