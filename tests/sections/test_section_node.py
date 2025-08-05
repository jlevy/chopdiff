"""Tests for SectionNode class."""

from chopdiff.sections.section_node import SectionNode


class TestSectionNodeConstruction:
    """Test SectionNode construction and basic properties."""

    def test_create_root_node(self):
        """Test creating a root section node."""
        root = SectionNode(level=0, title=None, start_offset=0, end_offset=100, header_end_offset=0)

        assert root.level == 0
        assert root.title is None
        assert root.start_offset == 0
        assert root.end_offset == 100
        assert root.header_end_offset == 0
        assert root.parent is None
        assert root.children == []
        assert root._original_text is None

    def test_create_header_node(self):
        """Test creating a section node with header."""
        section = SectionNode(
            level=2, title="Introduction", start_offset=10, end_offset=50, header_end_offset=25
        )

        assert section.level == 2
        assert section.title == "Introduction"
        assert section.start_offset == 10
        assert section.end_offset == 50
        assert section.header_end_offset == 25
        assert section.body_start_offset == 25

    def test_node_with_parent_and_children(self):
        """Test node relationships."""
        root = SectionNode(0, None, 0, 100, 0)
        child1 = SectionNode(1, "Chapter 1", 0, 50, 10, parent=root)
        child2 = SectionNode(1, "Chapter 2", 50, 100, 60, parent=root)

        root.children = [child1, child2]

        assert child1.parent == root
        assert child2.parent == root
        assert len(root.children) == 2
        assert root.children[0] == child1
        assert root.children[1] == child2


class TestSectionNodeContent:
    """Test content extraction from SectionNode."""

    def test_set_original_text(self):
        """Test setting original text reference."""
        text = "# Title\n\nContent here.\n\n## Subtitle\n\nMore content."

        root = SectionNode(0, None, 0, len(text), 0)
        child = SectionNode(1, "Title", 0, 35, 8, parent=root)
        root.children = [child]

        root.set_original_text(text)

        assert root._original_text == text
        assert child._original_text == text

    def test_header_text(self):
        """Test extracting header text."""
        text = "# Main Title\n\nSome content here."
        section = SectionNode(1, "Main Title", 0, len(text), 13)
        section.set_original_text(text)

        assert section.header_text == "# Main Title"

    def test_body_content_no_subsections(self):
        """Test body content extraction without subsections."""
        text = "# Title\n\nThis is the body content.\nWith multiple lines.\n"
        section = SectionNode(1, "Title", 0, len(text), 8)
        section.set_original_text(text)

        expected = "This is the body content.\nWith multiple lines."
        assert section.body_content == expected

    def test_body_content_with_subsections(self):
        """Test body content extraction with subsections."""
        text = "# Main\n\nMain body content.\n\n## Sub\n\nSub content."

        main = SectionNode(1, "Main", 0, len(text), 7)
        sub = SectionNode(2, "Sub", 28, len(text), 34, parent=main)
        main.children = [sub]
        main.set_original_text(text)

        # Body content should only include content before subsection
        assert main.body_content == "Main body content."
        assert sub.body_content == "Sub content."

    def test_full_content(self):
        """Test full content extraction including subsections."""
        text = "# Main\n\nMain body.\n\n## Sub\n\nSub body."

        main = SectionNode(1, "Main", 0, len(text), 7)
        main.set_original_text(text)

        assert main.full_content == text

    def test_root_body_content(self):
        """Test body content for root node."""
        text = "Preamble text.\n\n# First Header\n\nContent."

        root = SectionNode(0, None, 0, len(text), 0)
        first = SectionNode(1, "First Header", 16, len(text), 31, parent=root)
        root.children = [first]
        root.set_original_text(text)

        assert root.body_content == "Preamble text."


class TestSectionNodeNavigation:
    """Test navigation methods of SectionNode."""

    def test_iter_descendants(self):
        """Test iterating over descendants."""
        root = SectionNode(0, None, 0, 100, 0)
        ch1 = SectionNode(1, "Ch1", 0, 50, 5, parent=root)
        ch2 = SectionNode(1, "Ch2", 50, 100, 55, parent=root)
        sub1 = SectionNode(2, "Sub1", 10, 30, 15, parent=ch1)
        sub2 = SectionNode(2, "Sub2", 30, 50, 35, parent=ch1)

        root.children = [ch1, ch2]
        ch1.children = [sub1, sub2]

        # Include self
        descendants = list(root.iter_descendants(include_self=True))
        assert len(descendants) == 5
        assert descendants[0] == root
        assert descendants[1] == ch1
        assert descendants[2] == sub1
        assert descendants[3] == sub2
        assert descendants[4] == ch2

        # Exclude self
        descendants = list(root.iter_descendants(include_self=False))
        assert len(descendants) == 4
        assert root not in descendants

    def test_find_section_by_title(self):
        """Test finding sections by title."""
        root = SectionNode(0, None, 0, 100, 0)
        intro = SectionNode(1, "Introduction", 0, 30, 10, parent=root)
        background = SectionNode(2, "Background", 10, 20, 15, parent=intro)
        conclusion = SectionNode(1, "Conclusion", 30, 100, 40, parent=root)

        root.children = [intro, conclusion]
        intro.children = [background]

        # Recursive search
        assert root.find_section_by_title("Background") == background
        assert root.find_section_by_title("Conclusion") == conclusion
        assert root.find_section_by_title("NotFound") is None

        # Non-recursive search
        assert root.find_section_by_title("Background", recursive=False) is None
        assert root.find_section_by_title("Introduction", recursive=False) == intro

    def test_get_path(self):
        """Test getting path from root to section."""
        root = SectionNode(0, None, 0, 100, 0)
        ch1 = SectionNode(1, "Chapter 1", 0, 50, 10, parent=root)
        sec1 = SectionNode(2, "Section 1.1", 10, 30, 20, parent=ch1)
        sub1 = SectionNode(3, "Subsection 1.1.1", 20, 30, 25, parent=sec1)

        root.children = [ch1]
        ch1.children = [sec1]
        sec1.children = [sub1]

        assert root.get_path() == []
        assert ch1.get_path() == ["Chapter 1"]
        assert sec1.get_path() == ["Chapter 1", "Section 1.1"]
        assert sub1.get_path() == ["Chapter 1", "Section 1.1", "Subsection 1.1.1"]

    def test_get_depth(self):
        """Test calculating node depth."""
        root = SectionNode(0, None, 0, 100, 0)
        ch1 = SectionNode(1, "Ch1", 0, 50, 10, parent=root)
        sub1 = SectionNode(2, "Sub1", 10, 30, 20, parent=ch1)

        root.children = [ch1]
        ch1.children = [sub1]

        assert root.get_depth() == 0
        assert ch1.get_depth() == 1
        assert sub1.get_depth() == 2

    def test_is_leaf(self):
        """Test checking if node is a leaf."""
        root = SectionNode(0, None, 0, 100, 0)
        parent = SectionNode(1, "Parent", 0, 100, 10, parent=root)
        child = SectionNode(2, "Child", 10, 50, 20, parent=parent)

        root.children = [parent]
        parent.children = [child]

        assert not root.is_leaf()
        assert not parent.is_leaf()
        assert child.is_leaf()


class TestSectionNodeSiblings:
    """Test sibling navigation methods."""

    def test_get_siblings(self):
        """Test getting sibling nodes."""
        root = SectionNode(0, None, 0, 100, 0)
        ch1 = SectionNode(1, "Ch1", 0, 30, 5)
        ch2 = SectionNode(1, "Ch2", 30, 60, 35)
        ch3 = SectionNode(1, "Ch3", 60, 100, 65)

        root.children = [ch1, ch2, ch3]
        ch1.parent = ch2.parent = ch3.parent = root

        assert ch1.get_siblings() == [ch2, ch3]
        assert ch2.get_siblings() == [ch1, ch3]
        assert ch3.get_siblings() == [ch1, ch2]
        assert root.get_siblings() == []

    def test_get_next_previous_sibling(self):
        """Test getting next and previous siblings."""
        root = SectionNode(0, None, 0, 100, 0)
        ch1 = SectionNode(1, "Ch1", 0, 30, 5)
        ch2 = SectionNode(1, "Ch2", 30, 60, 35)
        ch3 = SectionNode(1, "Ch3", 60, 100, 65)

        root.children = [ch1, ch2, ch3]
        ch1.parent = ch2.parent = ch3.parent = root

        # Next sibling
        assert ch1.get_next_sibling() == ch2
        assert ch2.get_next_sibling() == ch3
        assert ch3.get_next_sibling() is None

        # Previous sibling
        assert ch1.get_previous_sibling() is None
        assert ch2.get_previous_sibling() == ch1
        assert ch3.get_previous_sibling() == ch2


class TestSectionNodeRepr:
    """Test string representation."""

    def test_repr(self):
        """Test __repr__ method."""
        section = SectionNode(
            level=2, title="Test Section", start_offset=100, end_offset=500, header_end_offset=120
        )

        repr_str = repr(section)
        assert "level=2" in repr_str
        assert '"Test Section"' in repr_str
        assert "offset=100:500" in repr_str
        assert "children=0" in repr_str

        # Add children
        child = SectionNode(3, "Child", 150, 200, 160, parent=section)
        section.children = [child]

        repr_str = repr(section)
        assert "children=1" in repr_str
