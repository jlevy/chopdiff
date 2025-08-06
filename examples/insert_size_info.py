#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "chopdiff",
#     "prettyfmt",
# ]
# ///

"""
Insert document size information after each section header.

This script walks through a Markdown document section by section and inserts
a <div class="size-info"> element after each heading containing statistics
about that section (word count, sentence count, reading time, etc.).
"""

import argparse
import sys
from pathlib import Path

from chopdiff import FlexDoc, TextUnit
from chopdiff.sections import SectionNode
from chopdiff.util.read_time import format_read_time


def create_size_info_div(
    section: SectionNode, doc: FlexDoc, words_per_minute: int = 225, brief: bool = True
) -> str:
    """
    Create a size info div for a section.

    Args:
        section: The section to analyze
        doc: The FlexDoc containing the section
        words_per_minute: Reading speed for time estimates
        brief: If True, use brief time format

    Returns:
        HTML div string with size information
    """
    # Get section statistics
    section_doc = doc.get_section_text_doc(section)

    # Calculate metrics
    words = section_doc.size(TextUnit.words)
    sentences = section_doc.size(TextUnit.sentences)
    paragraphs = section_doc.size(TextUnit.paragraphs)
    chars = section_doc.size(TextUnit.chars)

    # Format reading time (with minimum_time=0 to show all times)
    read_time = format_read_time(words, words_per_minute, brief=brief, minimum_time=0)

    # Calculate subsection count
    subsection_count = len(section.children)

    # Build the info parts
    info_parts: list[str] = []

    if words > 0:
        info_parts.append(f"{words:,} words")

    if sentences > 0:
        info_parts.append(f"{sentences} sentence{'s' if sentences != 1 else ''}")

    if paragraphs > 1:  # Only show if more than just the header
        info_parts.append(f"{paragraphs} paragraph{'s' if paragraphs != 1 else ''}")

    if subsection_count > 0:
        info_parts.append(f"{subsection_count} subsection{'s' if subsection_count != 1 else ''}")

    if read_time:  # Only add if read_time is not empty
        info_parts.append(f"~{read_time} to read")

    # Create the div
    if info_parts:
        info_text = " • ".join(info_parts)
        return f'<div class="size-info" data-words="{words}" data-chars="{chars}">{info_text}</div>'
    else:
        return ""


def insert_size_info(
    text: str,
    min_level: int = 1,
    max_level: int = 3,
) -> str:
    """
    Insert size info divs after section headers in a Markdown document.

    Args:
        text: The Markdown document text
        min_level: Minimum heading level to process (1-6)
        max_level: Maximum heading level to process (1-6)

    Returns:
        Modified document with size info divs inserted
    """
    # Parse the document
    doc = FlexDoc(text)

    # Collect all sections to process (in reverse order to maintain offsets)
    sections_to_process: list[SectionNode] = []
    for section in doc.section_doc.iter_sections(min_level=min_level, max_level=max_level):
        sections_to_process.append(section)

    # Sort by offset in reverse order (process from end to start)
    sections_to_process.sort(key=lambda s: s.header_end_offset, reverse=True)

    # Convert text to list for easier manipulation
    result = text

    # Process each section
    for section in sections_to_process:
        # Create the size info div
        size_div = create_size_info_div(section, doc)

        if size_div:
            # Find the end of the header line
            header_end = section.header_end_offset

            # Insert the div after the header
            # Add a newline before the div if needed
            insert_text = f"\n{size_div}\n"

            # Insert at the header end position
            result = result[:header_end] + insert_text + result[header_end:]

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Insert size information after section headers in Markdown documents.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s document.md
  %(prog)s document.md --output document_with_stats.md
  %(prog)s document.md --wpm 200 --verbose
  %(prog)s document.md --max-level 2
  cat document.md | %(prog)s - > output.md
        """,
    )

    parser.add_argument("file", type=str, help="Markdown file to process (use '-' for stdin)")

    parser.add_argument("-o", "--output", type=str, help="Output file (default: stdout)")

    parser.add_argument(
        "--wpm",
        "--words-per-minute",
        type=int,
        default=225,
        dest="wpm",
        help="Reading speed for time estimates (default: 225)",
    )

    parser.add_argument(
        "--verbose",
        action="store_false",
        dest="brief",
        help="Use verbose time format (e.g., '2 minutes 30 seconds' instead of '2m 30s')",
    )

    parser.add_argument(
        "--min-level",
        type=int,
        default=1,
        choices=[1, 2, 3, 4, 5, 6],
        help="Minimum heading level to process (default: 1)",
    )

    parser.add_argument(
        "--max-level",
        type=int,
        default=3,
        choices=[1, 2, 3, 4, 5, 6],
        help="Maximum heading level to process (default: 3)",
    )

    args = parser.parse_args()

    # Read input
    if args.file == "-":
        text = sys.stdin.read()
    else:
        path = Path(args.file)
        if not path.exists():
            print(f"Error: File '{args.file}' not found", file=sys.stderr)
            sys.exit(1)
        text = path.read_text()

    # Process the document
    result = insert_size_info(
        text,
        min_level=args.min_level,
        max_level=args.max_level,
    )

    # Write output
    if args.output:
        output_path = Path(args.output)
        output_path.write_text(result)
        print(f"Size information added to {args.output}")
    else:
        print(result, end="")


if __name__ == "__main__":
    main()
