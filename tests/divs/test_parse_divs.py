from textwrap import dedent

from chopdiff.divs.parse_divs import parse_divs, parse_divs_by_class
from chopdiff.divs.text_node import TextNode

_test_text = dedent(
    """

    <div class="outer">
        Outer content paragraph 1.

        Outer content paragraph 2.
        <div class="inner">
            Inner content.
            <div>
                Nested content.
            </div>

            <div class="nested-inner">

                Nested inner content.
                <div>
                    Deeply nested content.
                </div>
            </div>

            
        </div>
        Outer content paragraph 3.
    </div>
    """
)


def _strip_lines(text: str) -> list[str]:
    return [line.strip() for line in text.strip().split("\n")]


def test_parse_divs():
    def validate_node(node: TextNode, original_text: str):
        assert node.original_text == original_text
        assert 0 <= node.content_start <= len(original_text)
        assert 0 <= node.content_end <= len(original_text)
        assert node.content_start <= node.content_end
        assert node.contents == original_text[node.content_start : node.content_end]
        assert (
            node.begin_marker is None
            or original_text[node.offset : node.offset + len(node.begin_marker)]
            == node.begin_marker
        )
        assert (
            node.end_marker is None
            or original_text[node.content_end : node.content_end + len(node.end_marker)]
            == node.end_marker
        )

        for child in node.children:
            validate_node(child, original_text)

    node = parse_divs(_test_text, skip_whitespace=False)

    node_no_whitespace = parse_divs(_test_text, skip_whitespace=True)

    reassembled = node.reassemble(padding="")

    print()
    print(f"Original text (length {len(_test_text)}):")
    print(_test_text)

    print()
    print("Parsed text:")
    print(node)

    print()
    print("Parsed text (no whitespace):")
    print(node_no_whitespace)

    print()
    print(f"Reassembled text (length {len(reassembled)}):")
    print(reassembled)

    print()
    print("Reassembled text (normalized padding):")
    print(node.reassemble())

    validate_node(node, _test_text)

    assert reassembled.count("<div") == reassembled.count("</div")

    assert node.reassemble(padding="") == _test_text


def test_structure_summary_str_1():
    doc = """
        <div class="chunk">Chunk1</div>
        <div class="chunk">Chunk2</div>
        <div class="chunk">Chunk3</div>
        """

    node = parse_divs(doc)
    summary_str = node.structure_summary_str() or ""

    print()
    print("Structure summary:")
    print(summary_str)

    expected_summary = dedent(
        """
        HTML structure:
            3  div.chunk
        """
    ).strip()

    assert _strip_lines(summary_str) == _strip_lines(expected_summary)


def test_structure_summary_str_2():
    node = parse_divs(_test_text)
    summary_str = node.structure_summary_str() or ""

    print()
    print("Structure summary:")
    print(summary_str)

    expected_summary = dedent(
        """
        HTML structure:
            1  div.outer
            1  div.outer > div.inner
            1  div.outer > div.inner > div
            1  div.outer > div.inner > div.nested-inner
            1  div.outer > div.inner > div.nested-inner > div
        """
    ).strip()

    assert _strip_lines(summary_str) == _strip_lines(expected_summary)


def test_parse_chunk_divs():
    text = dedent(
        """
        <div class="chunk">

        Chunk 1 text.

        </div>

        <div class="chunk">

        Chunk 2 text.

        </div>

        <div class="chunk">Empty chunk.</div>

        """
    )

    chunk_divs = parse_divs_by_class(text, "chunk")

    print("\n---test_parse_chunk_divs---")
    for chunk_div in chunk_divs:
        print(chunk_div.reassemble())
        print("---")

    assert chunk_divs[0].reassemble() == """<div class="chunk">\n\nChunk 1 text.\n\n</div>"""
    assert chunk_divs[0].contents.strip() == "Chunk 1 text."
    assert len(chunk_divs) == 3
