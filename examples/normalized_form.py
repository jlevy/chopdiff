# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "chopdiff",
# ]
# ///
"""
Exercise chopdiff's normalized-form views over a single document: the section tree,
per-section structural block slices, link rollups per section, and density-invariant
block/item tallies.

Everything printed here is a *calculated view* over one parse — chopdiff stores no
counts. The structural block tree is density-invariant, so tight and loose spacing of
the same list produce identical tallies.

Run with: `uv run examples/normalized_form.py`
"""

from collections import Counter
from textwrap import dedent

from flexdoc.docs import Block, BlockType, Section, TextDoc

_SAMPLE = dedent(
    """
    # Project Overview

    A short intro with a [homepage](https://example.com) link.

    ## Features

    - fast parsing
    - exact source spans
      - paragraphs
      - sentences
    - link extraction

    ## Roadmap

    Planned milestones, in order:

    1. ship block spans
    2. ship the normalized form

    See the [tracking issue](https://example.com/issues/1) for details.

    | Milestone | Status |
    | --------- | ------ |
    | spans     | done   |
    | rollups   | wip    |

    ```python
    # density does not change the tally
    doc = TextDoc.from_text(text)
    ```
    """
).strip()


def show_section_tree(sections: list[Section], depth: int = 0) -> None:
    for section in sections:
        slice_types = [b.type.value for b in section.blocks() if b.type != BlockType.heading]
        print(f"  {'  ' * depth}{'#' * section.level} {section.title}  -> {slice_types}")
        show_section_tree(section.children, depth + 1)


def show_own_links(sections: list[Section]) -> None:
    """Walk the whole section tree, printing each section's own-content links (a derived
    rollup: links from the section's own paragraphs, not its subsections)."""
    for section in sections:
        own_links = [link for para in section.own_blocks() for link in para.links()]
        for link in own_links:
            print(f"  {section.title}: [{link.text}]({link.url})")
        show_own_links(section.children)


def count_descending(blocks: list[Block], counter: Counter[BlockType]) -> None:
    """Opt-in deep tally: descend into children (e.g. to count list_items)."""
    for block in blocks:
        counter[block.type] += 1
        count_descending(block.children, counter)


def main() -> None:
    doc = TextDoc.from_text(_SAMPLE)

    print("--- Section tree with per-section block-type slices (headings dropped) ---")
    show_section_tree(doc.sections())

    print("\n--- Own-content links rolled up per section ---")
    show_own_links(doc.sections())

    print("\n--- Top-level block-type tally (whole document, no descent) ---")
    for block_type, n in sorted(Counter(b.type for b in doc.blocks()).items()):
        print(f"  {block_type.value}: {n}")

    print("\n--- Deep tally (descending into list items) ---")
    deep: Counter[BlockType] = Counter()
    count_descending(doc.blocks(), deep)
    for block_type, n in sorted(deep.items()):
        print(f"  {block_type.value}: {n}")

    print("\n--- Density invariance: tight vs. loose list, identical tallies ---")
    tight = TextDoc.from_text("- a\n- b\n- c")
    loose = TextDoc.from_text("- a\n\n- b\n\n- c")
    tight_deep: Counter[BlockType] = Counter()
    loose_deep: Counter[BlockType] = Counter()
    count_descending(tight.blocks(), tight_deep)
    count_descending(loose.blocks(), loose_deep)
    print(f"  tight: {dict(sorted((k.value, v) for k, v in tight_deep.items()))}")
    print(f"  loose: {dict(sorted((k.value, v) for k, v in loose_deep.items()))}")
    assert tight_deep == loose_deep
    print("  -> identical (density-invariant)")


if __name__ == "__main__":
    main()
