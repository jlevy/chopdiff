from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeAlias

from prettyfmt import abbrev_obj
from strif import replace_multiple
from typing_extensions import override

ValueRewriter: TypeAlias = Callable[[str], str | None]
"""
A value rewriter function takes an attribute value string and returns a new value or
None to skip rewriting.
"""

# Precompiled regex patterns for better performance
_TAG_NAME_EXTRACTOR = re.compile(r"<\s*([a-zA-Z][a-zA-Z0-9-]*)")
_SELF_CLOSING_DETECTOR = re.compile(r"/\s*>$")
_CLOSING_TAG_DETECTOR = re.compile(r"^<\s*/")


@dataclass(frozen=True)
class TagMatch:
    """
    A matched HTML tag with its properties, including exact offsets.
    """

    tag_name: str
    start_offset: int
    end_offset: int
    attribute_name: str | None
    attribute_value: str | None
    inner_text: str

    @override
    def __repr__(self):
        return abbrev_obj(self)


def _find_balanced_closing_tag(html: str, tag: str, start_pos: int) -> int | None:
    """
    Find the end position of the balanced closing tag for an element.

    Args:
        html: The HTML string to search in
        tag: The tag name to match
        start_pos: Position right after the opening tag

    Returns:
        Position right after the matching closing tag, or None if not found
    """
    # Pattern matches both opening and closing tags of the same name
    # This handles whitespace: <tag>, < tag>, </tag>, < /tag>, < / tag>, etc.
    pattern = re.compile(rf"<\s*/?\s*{re.escape(tag)}\b[^>]*>", flags=re.IGNORECASE)

    depth = 0
    for match in pattern.finditer(html, start_pos):
        if _CLOSING_TAG_DETECTOR.match(match.group(0)):
            # It's a closing tag
            if depth == 0:
                # This is the balanced close for our opener
                return match.end()
            depth -= 1
        else:
            # It's another opening tag of the same name
            depth += 1

    # No balanced closing tag found
    return None


def html_find_tag(
    html_string: str,
    tag_name: str | None = None,
    attr_name: str | None = None,
    attr_value: str | None = None,
) -> list[TagMatch]:
    """
    Find all HTML elements matching the specified tag name, attribute name, and attribute value.

    We want this to enable surgical HTML editing, so returns exact offsets.

    It seems this is a bit of a headache to do with regular HTML parsers, so we're
    using a hybrid approach: regex for finding potential matches with accurate offsets,
    then selectolax for robust validation and parsing of each match.
    Why does this seem necessary?
    - Pure selectolax/lxml/BeautifulSoup: Great parsers but don't expose byte offsets
    - Pure regex: Can get offsets but fragile with complex/malformed HTML
    - This hybrid: Regex finds candidates with offsets, selectolax validates/parses them
    - Result: Accurate offsets + robust parsing = surgical HTML editing capability

    Args:
        html_string: The HTML content to search
        tag_name: Optional tag name to match (e.g., "p", "div"). If None, matches any tag.
        attr_name: Optional attribute name to match (e.g., "class", "id")
        attr_value: Optional specific attribute value to match

    Returns:
        List of TagMatch objects containing matched elements with accurate native offsets
    """
    from selectolax.parser import HTMLParser

    matches: list[TagMatch] = []

    # First, find all HTML comments and track their positions
    comment_ranges: list[tuple[int, int]] = []
    comment_pattern = re.compile(r"<!--.*?-->", re.DOTALL)
    for comment_match in comment_pattern.finditer(html_string):
        comment_ranges.append((comment_match.start(), comment_match.end()))

    def is_in_comment(pos: int) -> bool:
        """Check if a position is inside any HTML comment."""
        for start, end in comment_ranges:
            if start <= pos < end:
                return True
        return False

    # Build a relaxed regex pattern to find potential tags
    if tag_name:
        # Match specific tag with optional attributes
        pattern = rf"<\s*{re.escape(tag_name)}(?:\s+[^>]*)?\s*/?>"
    else:
        # Match any tag
        pattern = r"<\s*([a-zA-Z][a-zA-Z0-9-]*)\s*[^>]*/?>"

    # Find all potential tag matches with regex (gives us accurate offsets)
    for match in re.finditer(pattern, html_string, re.IGNORECASE):
        start_offset = match.start()

        # Skip if this tag is inside a comment
        if is_in_comment(start_offset):
            continue

        tag_html = match.group()

        # Extract the actual tag name from the match if we didn't specify one
        if not tag_name:
            tag_match = _TAG_NAME_EXTRACTOR.match(tag_html)
            if tag_match:
                current_tag = tag_match.group(1).lower()
            else:
                continue
        else:
            current_tag = tag_name.lower()

        # Check if it's a self-closing tag (handles whitespace before >)
        is_self_closing = bool(_SELF_CLOSING_DETECTOR.search(tag_html))

        # Find the end of the element
        if is_self_closing:
            end_offset = match.end()
            element_html = tag_html
        else:
            # Look for the balanced closing tag to handle nested elements
            end_offset = _find_balanced_closing_tag(html_string, current_tag, match.end())
            if end_offset is not None:
                element_html = html_string[start_offset:end_offset]
            else:
                # No closing tag found, treat as self-closing
                end_offset = match.end()
                element_html = tag_html

        # Now use selectolax to parse and validate this specific element
        try:
            parser = HTMLParser(element_html)

            # Find the first real element (skip text nodes)
            target_element = None
            for elem in parser.tags(current_tag):
                target_element = elem
                break

            if not target_element:
                continue

            # Check attribute filters
            if attr_name:
                elem_attr_value = (
                    target_element.attrs.get(attr_name)
                    if hasattr(target_element, "attrs")
                    else None
                )

                # If we specified an attribute value, it must match
                if attr_value is not None and elem_attr_value != attr_value:
                    continue

                # If we only specified attribute name, the element must have it
                if attr_value is None and elem_attr_value is None:
                    continue

                actual_attr_value = elem_attr_value
            else:
                actual_attr_value = None

            # Get inner text
            inner_text = target_element.text(strip=False) if hasattr(target_element, "text") else ""

            # Add the validated match with accurate offsets
            matches.append(
                TagMatch(
                    tag_name=current_tag,
                    start_offset=start_offset,
                    end_offset=end_offset,
                    attribute_name=attr_name,
                    attribute_value=actual_attr_value,
                    inner_text=inner_text or "",
                )
            )

        except Exception:
            # If selectolax can't parse it, skip this match
            continue

    return matches


def html_extract_attribute_value(attr_name: str) -> Callable[[str], str | None]:
    """
    Create a function that extracts the value of a specific attribute from HTML content.

    Uses selectolax for robust HTML parsing instead of regex.

    Args:
        attr_name: The name of the attribute to extract

    Returns:
        A function that takes HTML string and returns the attribute value or None
    """
    from selectolax.parser import HTMLParser

    def extractor(html_string: str) -> str | None:
        tree = HTMLParser(html_string)

        # Find first element with the specified attribute
        for element in tree.css(f"[{attr_name}]"):
            value = element.attrs.get(attr_name)
            if value:
                return value

        return None

    return extractor


def rewrite_html_tag_attr(
    html: str,
    tag_name: str,
    attr_name: str,
    value_rewriter: ValueRewriter | None = None,
    *,
    from_prefix: str | None = None,
    to_prefix: str | None = None,
) -> str:
    """
    Rewrite attribute values for specified HTML tags using the provided rewriter function or
    prefix replacement.

    Does robust parsing and surgical replacement, preserving the original HTML exactly
    except for the replaced attribute values.

    Works with closed and unclosed tags, with any attribute order and quoting style.

    Args:
        html: The HTML content to process
        tag_name: The HTML tag name to target (e.g., "img", "a", "script")
        attr_name: The attribute name to rewrite (e.g., "src", "href")
        value_rewriter: Optional custom rewriter function that takes an attribute value and returns
                        a new value to replace it, or None to skip rewriting that value
        from_prefix: If value_rewriter is None, this prefix will be matched and replaced
        to_prefix: If value_rewriter is None, the replacement prefix for from_prefix

    Returns:
        The HTML content with rewritten attribute values

    Raises:
        ValueError: If neither value_rewriter nor both from_prefix and to_prefix are provided

    Examples:
        >>> # Rewrite img src attributes
        >>> rewrite_html_tag_attr('<img src="./photo.jpg">', "img", "src", from_prefix="./", to_prefix="/static/")
        '<img src="/static/photo.jpg">'

        >>> # Rewrite link hrefs
        >>> rewrite_html_tag_attr('<a href="./page.html">Link</a>', "a", "href", from_prefix="./", to_prefix="/")
        '<a href="/page.html">Link</a>'
    """
    # Validate arguments
    if value_rewriter is None:
        if from_prefix is None or to_prefix is None:
            raise ValueError("Either provide value_rewriter or both from_prefix and to_prefix")

        # Create a simple prefix rewriter
        def prefix_rewriter(value: str) -> str | None:
            if value.startswith(from_prefix):
                return value.replace(from_prefix, to_prefix, 1)
            return None

        value_rewriter = prefix_rewriter

    # Use our html_find_tag to get accurate offsets
    matches = html_find_tag(html, tag_name=tag_name, attr_name=attr_name)

    # Collect all replacements to make using strif.replace_multiple
    replacements: list[tuple[int, int, str]] = []  # (start, end, new_value)

    # Process each matched element
    for match in matches:
        if match.attribute_value:
            new_value = value_rewriter(match.attribute_value)
            if new_value is not None and new_value != match.attribute_value:
                # Extract the element HTML
                element_html = html[match.start_offset : match.end_offset]

                # Match the attribute with various quote styles (including unquoted)
                # First try quoted version
                quoted_pattern = re.compile(
                    rf'\b{re.escape(attr_name)}\s*=\s*(["\'])({re.escape(match.attribute_value)})\1',
                    re.IGNORECASE,
                )
                attr_match = quoted_pattern.search(element_html)

                if attr_match:
                    # Quoted attribute value
                    # Get the quote character used (single or double)
                    quote_char = attr_match.group(1)

                    # Escape the new value appropriately for the quote style
                    if quote_char == '"':
                        # For double quotes, escape any double quotes in the value
                        escaped_new_value = new_value.replace('"', "&quot;")
                    else:
                        # For single quotes, escape any single quotes in the value
                        escaped_new_value = new_value.replace("'", "&#39;")

                    # Calculate absolute positions
                    attr_value_start = match.start_offset + attr_match.start(2)
                    attr_value_end = match.start_offset + attr_match.end(2)
                    replacements.append((attr_value_start, attr_value_end, escaped_new_value))
                else:
                    # Try unquoted attribute pattern
                    # Unquoted values end at whitespace or >
                    unquoted_pattern = re.compile(
                        rf"\b{re.escape(attr_name)}\s*=\s*({re.escape(match.attribute_value)})(?=\s|>|/)",
                        re.IGNORECASE,
                    )
                    attr_match = unquoted_pattern.search(element_html)
                    if attr_match:
                        # For unquoted attributes, we don't need to escape quotes
                        # but we should avoid spaces in the replacement value
                        # Calculate absolute positions
                        attr_value_start = match.start_offset + attr_match.start(1)
                        attr_value_end = match.start_offset + attr_match.end(1)
                        replacements.append((attr_value_start, attr_value_end, new_value))

    if replacements:
        return replace_multiple(html, replacements)
    return html


def rewrite_html_img_urls(
    html: str,
    url_rewriter: ValueRewriter | None = None,
    *,
    from_prefix: str | None = None,
    to_prefix: str | None = None,
) -> str:
    """
    Rewrite image URLs in HTML content using the provided rewriter function or prefix replacement.

    This is a convenience function that delegates to rewrite_html_tag_attr for img src attributes.

    Args:
        html: The HTML content to process
        url_rewriter: Optional custom rewriter function that takes a URL string and returns
                      a new URL string to replace it, or None to skip rewriting that URL
        from_prefix: If url_rewriter is None, this prefix will be matched and replaced
        to_prefix: If url_rewriter is None, the replacement prefix for from_prefix

    Returns:
        The HTML content with rewritten image URLs

    Raises:
        ValueError: If neither url_rewriter nor both from_prefix and to_prefix are provided

    Examples:
        >>> # Using prefix replacement
        >>> rewrite_html_img_urls('<img src="./photo.jpg">', from_prefix="./", to_prefix="/static/")
        '<img src="/static/photo.jpg">'
    """
    return rewrite_html_tag_attr(
        html,
        "img",
        "src",
        url_rewriter,  # Note: url_rewriter is correct here since this function specifically handles URLs
        from_prefix=from_prefix,
        to_prefix=to_prefix,
    )
