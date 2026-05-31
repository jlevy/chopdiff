# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "chopdiff",
# ]
# ///
"""
Show chopdiff's document-structure features: the section hierarchy with rolled-up
size stats, the flat table of contents, and exact source spans / offset lookups.

Run with: `uv run examples/doc_structure.py`
"""

from textwrap import dedent

from chopdiff.docs import Block, BlockType, TextDoc, TextUnit

_SAMPLE = dedent(
    """
    # Introduction

    Chopdiff parses text into paragraphs and sentences. It tracks exact offsets.

    ## Goals

    Be fast. Be accurate. Stay dependency-light. See the [docs](https://example.com/docs).

    ## Non-goals

    We do not render Markdown here.

    # Usage

    Parse a document, then iterate or measure its blocks.
    """
).strip()


_BLOCK_SAMPLE = dedent(
    """
    # Setup

    Install, then configure.

    - clone the repo
    - install deps
      - runtime
      - dev
    - run the tests

    ```bash
    uv sync

    uv run pytest
    ```
    """
).strip()


def main() -> None:
    doc = TextDoc.from_text(_SAMPLE)

    print("--- Section size tree (words + sentences, rolled up) ---")
    print(doc.section_size_tree(units=(TextUnit.words, TextUnit.sentences)))

    print("\n--- Table of contents (level, title, span) ---")
    for level, title, span in doc.toc():
        print(f"  {'  ' * (level - 1)}{title}  @{span}")

    print("\n--- Per-section rolled-up word counts ---")
    for section in doc.sections():
        own = section.size(TextUnit.words, subtree=False)
        whole = section.size(TextUnit.words, subtree=True)
        print(f"  {section.title}: {own} words own, {whole} words including subsections")

    print("\n--- Exact spans and offset lookup ---")
    offset = _SAMPLE.index("dependency-light")
    block = doc.block_at_offset(offset)
    sent_index = doc.sentence_at_offset(offset)
    assert block is not None and sent_index is not None
    print(f"  offset {offset} is in block {block.original_text[:30]!r}...")
    print(f"  and in sentence {doc.get_sent(sent_index).text!r}")

    print("\n--- Total words across paragraph blocks only ---")
    paragraphs_only = doc.filtered(include={BlockType.paragraph})
    print(
        f"  {paragraphs_only.size(TextUnit.words)} words in {len(paragraphs_only.paragraphs)} paragraphs"
    )

    print("\n--- Structural block tree (whole-document view) ---")
    block_doc = TextDoc.from_text(_BLOCK_SAMPLE)

    def show_blocks(blocks: list[Block], depth: int = 0) -> None:
        for block in blocks:
            preview = _BLOCK_SAMPLE[block.span[0] : block.span[1]].splitlines()[0]
            print(f"  {'  ' * depth}{block.type.value}: {preview!r}")
            show_blocks(block.children, depth + 1)

    show_blocks(block_doc.blocks())

    print("\n--- Links (text, url, span) and the sentence each is in ---")
    for link in doc.links():
        where = ""
        if link.span is not None:
            sent_index = doc.sentence_at_offset(link.span[0])
            if sent_index is not None:
                where = f" — in sentence {doc.get_sent(sent_index).text!r}"
        print(f"  [{link.text}]({link.url})  @{link.span}{where}")


if __name__ == "__main__":
    main()
