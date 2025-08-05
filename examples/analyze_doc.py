#!/usr/bin/env python3
"""
Document structure analyzer using chopdiff.

Analyzes a Markdown document section by section, providing statistics
on paragraphs, sentences, words, and estimated reading time.
"""

import argparse
import sys
from pathlib import Path
from typing import TYPE_CHECKING

# Add the parent directory to the path to import chopdiff
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from chopdiff import FlexDoc, TextUnit
from chopdiff.sections import SectionNode

# pip install rich
if TYPE_CHECKING:
    from rich.console import Console
    from rich.table import Table
    from rich.text import Text
    from rich.tree import Tree

has_rich = False
try:
    from rich.console import Console
    from rich.table import Table
    from rich.text import Text
    from rich.tree import Tree

    has_rich = True
except ImportError:
    pass


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
    total_words = doc.text_doc.size(TextUnit.words)
    total_read_time = total_words / words_per_minute

    if has_rich:
        console = Console()

        # Create root tree
        tree = Tree(Text("Document Structure", style="bold blue"), guide_style="blue")

        # Add summary
        tree.add(
            Text(
                f"Total: {total_words:,} words • {format_time(total_read_time)} read time",
                style="italic cyan",
            )
        )

        def add_section_to_tree(section: SectionNode, parent_tree: Tree) -> None:
            """Recursively add sections to the rich tree."""
            section_doc = doc.get_section_text_doc(section)
            paragraphs = section_doc.size(TextUnit.paragraphs)
            sentences = section_doc.size(TextUnit.sentences)
            words = section_doc.size(TextUnit.words)
            read_time = words / words_per_minute

            # Choose style based on level
            if section.level == 0:
                title_style = "bold magenta"
                title = "[Document Root]"
            elif section.level == 1:
                title_style = "bold green"
                title = section.title or "[Untitled]"
            elif section.level == 2:
                title_style = "green"
                title = section.title or "[Untitled]"
            else:
                title_style = "white"
                title = section.title or "[Untitled]"

            # Create node text
            node_text = Text(title, style=title_style)

            # Add statistics if content exists
            if words > 0:
                stats = f"\n{paragraphs} para • {sentences} sent • {words:,} words • {format_time(read_time)}"
                node_text.append(stats, style="dim white")

            # Add to tree
            if section.level == 0:
                # For root, add children directly to main tree
                for child in section.children:
                    add_section_to_tree(child, tree)
            else:
                # Add this section and its children
                section_tree = parent_tree.add(node_text)
                for child in section.children:
                    add_section_to_tree(child, section_tree)

        # Build the tree
        add_section_to_tree(doc.section_doc.root, tree)

        # Display
        console.print()
        console.print(tree)
    else:
        # Fallback to original implementation without rich
        print("Document Analysis")
        print(f"   Total: {total_words:,} words • {format_time(total_read_time)} read time")
        print()

        def print_section(section: SectionNode, prefix: str = "", is_last: bool = True) -> None:
            section_doc = doc.get_section_text_doc(section)
            paragraphs = section_doc.size(TextUnit.paragraphs)
            sentences = section_doc.size(TextUnit.sentences)
            words = section_doc.size(TextUnit.words)
            read_time = words / words_per_minute

            connector = "└── " if is_last else "├── "
            extension = "    " if is_last else "│   "

            if section.level == 0:
                title = "[Document Root]"
            else:
                title = section.title or "[Untitled]"

            print(f"{prefix}{connector}{title}")

            stats_prefix = prefix + extension
            if words > 0:
                print(
                    f"{stats_prefix}   {paragraphs} para • {sentences} sent • {words} words • {format_time(read_time)}"
                )

            children = section.children
            for i, child in enumerate(children):
                is_last_child = i == len(children) - 1
                print_section(child, stats_prefix, is_last_child)

        print_section(doc.section_doc.root, "", True)


def analyze_sections_flat(doc: FlexDoc, words_per_minute: int = 250) -> None:
    """Print section statistics in a flat table format."""
    if has_rich:
        console = Console()
        table = Table(
            title="Document Section Analysis", show_header=True, header_style="bold magenta"
        )

        # Add columns
        table.add_column("Level", style="cyan", width=6)
        table.add_column("Title", style="green", width=40)
        table.add_column("Paragraphs", justify="right", style="yellow")
        table.add_column("Sentences", justify="right", style="yellow")
        table.add_column("Words", justify="right", style="yellow")
        table.add_column("Read Time", justify="right", style="blue")

        total_stats = {"paragraphs": 0, "sentences": 0, "words": 0}

        for section in doc.section_doc.iter_sections():
            section_doc = doc.get_section_text_doc(section)
            paragraphs = section_doc.size(TextUnit.paragraphs)
            sentences = section_doc.size(TextUnit.sentences)
            words = section_doc.size(TextUnit.words)
            read_time = words / words_per_minute

            total_stats["paragraphs"] += paragraphs
            total_stats["sentences"] += sentences
            total_stats["words"] += words

            # Format title with indentation
            indent = "  " * (section.level - 1)
            title = f"{indent}{section.title}" if section.title else f"{indent}[Untitled]"

            # Choose style based on level
            style = "bold" if section.level == 1 else "normal"

            table.add_row(
                str(section.level),
                title,
                str(paragraphs),
                str(sentences),
                f"{words:,}",
                format_time(read_time),
                style=style,
            )

        # Add totals row
        total_read_time = total_stats["words"] / words_per_minute
        table.add_row(
            "TOTAL",
            "",
            str(total_stats["paragraphs"]),
            str(total_stats["sentences"]),
            f"{total_stats['words']:,}",
            format_time(total_read_time),
            style="bold red",
        )

        console.print()
        console.print(table)
    else:
        # Fallback to original implementation
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

            total_stats["paragraphs"] += paragraphs
            total_stats["sentences"] += sentences
            total_stats["words"] += words

            indent = "  " * (section.level - 1)
            title = (
                f"{indent}{section.title[: 38 - len(indent)]}"
                if section.title
                else f"{indent}[Untitled]"
            )

            print(
                f"{section.level:<6} {title:<40} {paragraphs:>10} {sentences:>10} {words:>8} {format_time(read_time):>10}"
            )

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

    if has_rich:
        console = Console()
        console.print(f"\n[bold blue]Analysis of:[/bold blue] [cyan]{filename}[/cyan]")
    else:
        print(f"\nAnalysis of: {filename}\n")

    if args.flat:
        analyze_sections_flat(doc, args.words_per_minute)
    else:
        print_section_tree(doc, args.words_per_minute)

    if not has_rich:
        print()


if __name__ == "__main__":
    main()
