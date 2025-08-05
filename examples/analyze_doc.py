#!/usr/bin/env python3
"""
Document structure analyzer using chopdiff.

Analyzes a Markdown document section by section, providing statistics
on paragraphs, sentences, words, and estimated reading time.
"""

import argparse
import sys
from pathlib import Path

from chopdiff import FlexDoc, TextUnit
from chopdiff.sections import SectionNode


def format_time(minutes: float) -> str:
    """Format reading time in a human-readable way."""
    if minutes < 1:
        return f"{int(minutes * 60)}s"
    elif minutes < 60:
        return f"{minutes:.1f}m"
    else:
        hours = int(minutes // 60)
        mins = int(minutes % 60)
        return f"{hours}h {mins}m"


def print_section_tree(doc: FlexDoc, words_per_minute: int = 250) -> None:
    """Print document statistics as a tree structure."""
    # Document header
    total_words = doc.text_doc.size(TextUnit.words)
    total_read_time = total_words / words_per_minute

    print("📄 Document Analysis")
    print(f"   Total: {total_words:,} words • {format_time(total_read_time)} read time")
    print()

    # Process each section
    def print_section(section: SectionNode, prefix: str = "", is_last: bool = True) -> None:
        # Get section statistics
        section_doc = doc.get_section_text_doc(section)
        paragraphs = section_doc.size(TextUnit.paragraphs)
        sentences = section_doc.size(TextUnit.sentences)
        words = section_doc.size(TextUnit.words)
        read_time = words / words_per_minute

        # Tree characters
        connector = "└── " if is_last else "├── "
        extension = "    " if is_last else "│   "

        # Format title
        if section.level == 0:
            title = "📖 [Document Root]"
            icon = ""
        else:
            icon = "📑" if section.is_leaf() else "📂"
            title = section.title or "[Untitled]"

        # Print section line
        print(f"{prefix}{connector}{icon} {title}")

        # Print statistics
        stats_prefix = prefix + extension
        if words > 0:  # Only show stats if section has content
            print(
                f"{stats_prefix}   {paragraphs} para • {sentences} sent • {words} words • {format_time(read_time)}"
            )

        # Process children
        children = section.children
        for i, child in enumerate(children):
            is_last_child = i == len(children) - 1
            print_section(child, stats_prefix, is_last_child)

    # Start with root
    print_section(doc.section_doc.root, "", True)


def analyze_sections_flat(doc: FlexDoc, words_per_minute: int = 250) -> None:
    """Print section statistics in a flat table format."""
    print(
        f"{'Level':<6} {'Title':<40} {'Paragraphs':>10} {'Sentences':>10} {'Words':>8} {'Read Time':>10}"
    )
    print("-" * 94)

    total_stats = {"paragraphs": 0, "sentences": 0, "words": 0}

    for section in doc.section_doc.iter_sections():
        section_doc = doc.get_section_text_doc(section)
        paragraphs = section_doc.size(TextUnit.paragraphs)
        sentences = section_doc.size(TextUnit.sentences)
        words = section_doc.size(TextUnit.words)
        read_time = words / words_per_minute

        # Update totals
        total_stats["paragraphs"] += paragraphs
        total_stats["sentences"] += sentences
        total_stats["words"] += words

        # Format title with indentation
        indent = "  " * (section.level - 1)
        title = (
            f"{indent}{section.title[: 38 - len(indent)]}"
            if section.title
            else f"{indent}[Untitled]"
        )

        print(
            f"{section.level:<6} {title:<40} {paragraphs:>10} {sentences:>10} {words:>8} {format_time(read_time):>10}"
        )

    # Print totals
    print("-" * 94)
    total_read_time = total_stats["words"] / words_per_minute
    print(
        f"{'TOTAL':<6} {'':<40} {total_stats['paragraphs']:>10} {total_stats['sentences']:>10} {total_stats['words']:>8} {format_time(total_read_time):>10}"
    )


def main():
    parser = argparse.ArgumentParser(
        description="Analyze document structure and reading statistics.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s document.md
  %(prog)s document.md --flat
  %(prog)s document.md --words-per-minute 200
  cat document.md | %(prog)s -
        """,
    )

    parser.add_argument("file", type=str, help="Markdown file to analyze (use '-' for stdin)")

    parser.add_argument(
        "--flat", action="store_true", help="Show flat table format instead of tree"
    )

    parser.add_argument(
        "--words-per-minute",
        type=int,
        default=250,
        help="Reading speed for time estimates (default: 250)",
    )

    args = parser.parse_args()

    # Read input
    if args.file == "-":
        text = sys.stdin.read()
        filename = "stdin"
    else:
        path = Path(args.file)
        if not path.exists():
            print(f"Error: File '{args.file}' not found", file=sys.stderr)
            sys.exit(1)
        text = path.read_text()
        filename = path.name

    # Analyze document
    doc = FlexDoc(text)

    print(f"\n📊 Analysis of: {filename}\n")

    if args.flat:
        analyze_sections_flat(doc, args.words_per_minute)
    else:
        print_section_tree(doc, args.words_per_minute)

    print()


if __name__ == "__main__":
    main()
