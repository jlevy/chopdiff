"""Test the insert_size_info example functionality."""

from textwrap import dedent

from examples.insert_size_info import insert_size_info


def test_insert_size_info_basic():
    """Test basic size info insertion after headers."""
    input_doc = dedent("""
        # Main Title
        
        Some introductory text here.
        
        ## Section One
        
        This section has content.
        
        ### Subsection 1.1
        
        Nested content here.
        """).strip()

    result = insert_size_info(input_doc)

    # Check that size-info divs are inserted after headers
    assert '<div class="size-info"' in result
    assert '# Main Title\n\n<div class="size-info"' in result
    assert '## Section One\n\n<div class="size-info"' in result
    assert '### Subsection 1.1\n\n<div class="size-info"' in result

    # Check that original content is preserved
    assert "Some introductory text here." in result
    assert "This section has content." in result
    assert "Nested content here." in result

    # Check data attributes are present
    assert 'data-words="' in result
    assert 'data-chars="' in result


def test_insert_size_info_preserves_structure():
    """Test that the document structure is preserved."""
    input_doc = dedent("""
        # Title
        
        First paragraph.
        
        Second paragraph.
        
        ## Section
        
        - List item 1
        - List item 2
        
        > A quote block
        
        ```python
        # Code block
        def foo():
            pass
        ```
        """).strip()

    result = insert_size_info(input_doc)

    # Original structure should be preserved
    assert "First paragraph." in result
    assert "Second paragraph." in result
    assert "- List item 1" in result
    assert "- List item 2" in result
    assert "> A quote block" in result
    assert "```python" in result
    assert "def foo():" in result

    # Size info should be added after headers only
    lines = result.split("\n")
    for i, line in enumerate(lines):
        if line.startswith("#"):
            # Next non-empty line should be a size-info div
            if i + 2 < len(lines) and lines[i + 1] == "":
                assert lines[i + 2].startswith('<div class="size-info"')


def test_insert_size_info_with_level_limits():
    """Test limiting which header levels get size info."""
    input_doc = dedent("""
        # H1
        
        Text.
        
        ## H2
        
        Text.
        
        ### H3
        
        Text.
        
        #### H4
        
        Text.
        """).strip()

    # Only levels 1-2
    result = insert_size_info(input_doc, min_level=1, max_level=2)

    # H1 and H2 should have size info
    assert '# H1\n\n<div class="size-info"' in result
    assert '## H2\n\n<div class="size-info"' in result

    # H3 and H4 should not
    assert '### H3\n\n<div class="size-info"' not in result
    assert '#### H4\n\n<div class="size-info"' not in result


def test_insert_size_info_brief_mode():
    """Test brief vs full mode for read time display."""
    input_doc = "# Title\n\nSome content here."

    # Brief mode
    brief_result = insert_size_info(input_doc, brief=True)
    assert "~" in brief_result  # Brief format uses ~

    # Full mode
    full_result = insert_size_info(input_doc, brief=False)
    # Full format doesn't use ~ but has more precise timing
    lines = full_result.split("\n")
    size_line = [line for line in lines if "size-info" in line][0]
    # Should have more detailed time format in full mode
    assert "to read" in size_line


def test_insert_size_info_empty_sections():
    """Test handling of empty sections."""
    input_doc = dedent("""
        # Title
        
        ## Empty Section
        
        ## Section with Content
        
        Some text here.
        """).strip()

    result = insert_size_info(input_doc)

    # All headers should get size info
    assert result.count('<div class="size-info"') == 3

    # Check that sections have appropriate word counts
    lines = result.split("\n")
    for i, line in enumerate(lines):
        if line == "## Empty Section":
            # Find the size-info div after this header
            size_div = lines[i + 2]
            # Empty section only has the text "Some text here." from sibling section
            assert 'data-words="3"' in size_div
        elif line == "## Section with Content":
            # This section has header text (4 words) + "Some text here." (3 words) = 7 words
            size_div = lines[i + 2]
            assert 'data-words="7"' in size_div
