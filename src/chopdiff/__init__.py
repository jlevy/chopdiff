# flake8: noqa: F401
"""
Chopdiff: Library for parsing and manipulating structured text documents.

Main components:
- TextDoc: Token-based document representation
- TextNode: HTML div-based document structure
- SectionDoc: Markdown section hierarchy
- FlexDoc: Unified interface with lazy loading for all views
"""

# Core document types
# Div-based parsing
from chopdiff.divs.parse_divs import parse_divs, parse_divs_by_class, parse_divs_single
from chopdiff.divs.text_node import TextNode
from chopdiff.docs.sizes import TextUnit
from chopdiff.docs.text_doc import Splitter, TextDoc, default_sentence_splitter
from chopdiff.docs.wordtoks import join_wordtoks, wordtokenize

# Unified interface
from chopdiff.flex.flex_doc import FlexDoc
from chopdiff.flex.thread_utils import synchronized

# HTML utilities
from chopdiff.html.html_in_md import (
    div_wrapper,
    html_a,
    html_b,
    html_div,
    html_i,
    html_img,
    html_span,
    span_wrapper,
    tag_wrapper,
)

# Section-based parsing
from chopdiff.sections.section_doc import SectionDoc
from chopdiff.sections.section_node import SectionNode

__all__ = [
    # Core document types
    "TextDoc",
    "TextUnit",
    "Splitter",
    "default_sentence_splitter",
    "wordtokenize",
    "join_wordtoks",
    # Div parsing
    "parse_divs",
    "parse_divs_single",
    "parse_divs_by_class",
    "TextNode",
    # Section parsing
    "SectionDoc",
    "SectionNode",
    # Unified interface
    "FlexDoc",
    "synchronized",
    # HTML utilities
    "html_div",
    "html_span",
    "html_a",
    "html_b",
    "html_i",
    "html_img",
    "div_wrapper",
    "span_wrapper",
    "tag_wrapper",
]
