"""Integration tests for cross-view operations in chopdiff."""

from textwrap import dedent

from chopdiff import FlexDoc, TextUnit


class TestFlexDocIntegration:
    """Integration tests for FlexDoc cross-view operations."""

    def test_mixed_markdown_and_divs(self):
        """Test document with both Markdown headers and HTML divs."""
        text = dedent("""
            # Introduction
            
            This document demonstrates FlexDoc's ability to handle mixed content.
            
            <div class="note">
            This is an important note about the introduction.
            </div>
            
            ## Background
            
            Some background information goes here.
            
            <div class="example">
            <div class="code">
            print("Hello, World!")
            </div>
            <div class="output">
            Hello, World!
            </div>
            </div>
            
            ## Methodology
            
            Our methodology involves several steps.
            
            # Results
            
            <div class="result" id="result-1">
            First result with data.
            </div>
            
            # Conclusion
            
            Final thoughts on the project.
        """).strip()

        doc = FlexDoc(text)

        # Test 1: Navigate sections and check content
        intro_section = doc.section_doc.find_section_by_path("Introduction")
        assert intro_section is not None
        assert "mixed content" in intro_section.body_content

        # Test 2: Check div detection
        stats = doc.get_stats()
        assert stats["has_divs"]
        assert "note" in str(stats["div_stats"]["div_types"])

        # Test 3: Get tokens for a specific section
        background_section = doc.section_doc.find_section_by_path("Introduction", "Background")
        assert background_section is not None
        tokens = doc.get_section_tokens(background_section)
        assert "background" in [t.lower() for t in tokens]

        # Test 4: Cross-reference offset to all coordinate systems
        note_offset = text.find("important note")
        coords = doc.offset_to_coordinates(note_offset)

        assert coords["section"].title == "Introduction"
        assert coords["in_div"]
        assert "note" in coords["div_path"]

        # Test 5: Smart chunking that respects sections
        chunks = doc.chunk_by_sections(target_size=100, unit=TextUnit.chars, respect_levels=[1])

        # Should have 3 chunks (Introduction, Results, Conclusion)
        assert len(chunks) == 3
        assert "Introduction" in chunks[0]
        assert "Results" in chunks[1]
        assert "Conclusion" in chunks[2]

    def test_performance_with_large_document(self):
        """Test that lazy loading works efficiently with large documents."""
        # Create a large document
        sections: list[str] = []
        for i in range(50):
            sections.append(f"# Section {i}\n\nContent for section {i}.")

        text = "\n\n".join(sections)
        doc = FlexDoc(text)

        # Initially nothing should be loaded
        assert doc._text_doc is None
        assert doc._section_doc is None
        assert doc._text_node is None

        # Access only section view
        section_nodes = list(doc.section_doc.iter_sections(max_level=1))
        assert len(section_nodes) == 50

        # Other views should still not be loaded
        assert doc._text_doc is None
        assert doc._text_node is None

    def test_empty_document_handling(self):
        """Test that all views handle empty documents gracefully."""
        doc = FlexDoc("")

        # All views should work without errors
        assert len(list(doc.section_doc.iter_sections())) == 0
        assert doc.text_doc.size(TextUnit.chars) == 0
        assert len(doc.text_node.children) == 0

        # Stats should work
        stats = doc.get_stats()
        assert stats["size_chars"] == 0
        assert stats["section_stats"]["total_sections"] == 0

    def test_complex_navigation(self):
        """Test complex navigation scenarios."""
        text = dedent("""
            # Book
            
            ## Part I
            
            ### Chapter 1
            #### Section 1.1
            ##### Subsection 1.1.1
            Content here.
            
            ### Chapter 2
            Content for chapter 2.
            
            ## Part II
            
            ### Chapter 3
            Final chapter.
        """).strip()

        doc = FlexDoc(text)

        # Navigate by path
        chapter1 = doc.section_doc.find_section_by_path("Book", "Part I", "Chapter 1")
        assert chapter1 is not None
        assert chapter1.level == 3

        # Get all chapters (level 3)
        chapters = doc.section_doc.get_sections_at_level(3)
        assert len(chapters) == 3
        assert [c.title for c in chapters] == ["Chapter 1", "Chapter 2", "Chapter 3"]

        # Find section at specific offset
        offset = text.find("Content here")
        section = doc.section_doc.get_section_at_offset(offset)
        assert section.title == "Subsection 1.1.1"

        # Get TOC with limited depth
        toc = doc.section_doc.get_toc(max_level=3)
        assert len(toc) == 6  # Book, Part I, Chapter 1, Chapter 2, Part II, Chapter 3

    def test_round_trip_preservation(self):
        """Test that content is preserved through parsing and reassembly."""
        text = dedent("""
            # Header One
            
            First paragraph with **bold** text.
            
            <div class="special">
            Div content with <span>nested HTML</span>.
            </div>
            
            ## Header Two
            
            Final paragraph.
        """).strip()

        doc = FlexDoc(text)

        # TextDoc should preserve content
        reassembled = doc.text_doc.reassemble()
        assert "**bold**" in reassembled
        assert '<div class="special">' in reassembled

        # Section content should be exact
        section = doc.section_doc.root.children[0]
        assert section.full_content == text

    def test_mixed_coordinate_queries(self):
        """Test querying the same content through different views."""
        text = dedent("""
            # Main Section
            
            <div class="content">
            This is the main content of the document.
            It has multiple sentences.
            </div>
            
            More content outside the div.
        """).strip()

        doc = FlexDoc(text)

        # Find offset of "multiple sentences"
        target_offset = text.find("multiple sentences")

        # Query through all views
        coords = doc.offset_to_coordinates(target_offset)

        # Should be in Main Section
        assert coords["section"].title == "Main Section"

        # Should be inside a div
        assert coords["in_div"]
        assert coords["div_path"] == ["content"]

        # Should have paragraph and sentence info
        assert "paragraph" in coords
        assert "sentence" in coords

        # Get the sentence through TextDoc
        sent_idx = coords["sentence"]
        sentence = doc.text_doc.get_sent(sent_idx)
        assert "multiple sentences" in sentence.text
