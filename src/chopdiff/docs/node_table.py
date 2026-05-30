# pyright: reportImportCycles=false
"""
Node table: a flat, id-addressed table of all parsed elements in a document,
covering three layers (markdown, document, textual) over the same source text.

`build_node_table(doc)` constructs the table once from a `TextDoc`; the result
is cached lazily on `TextDoc.node_table()` (safe because `source_text` is
immutable after parse).

The node table is the canonical normalized form from which derived views
(block tree, section tree, inline index, etc.) are cheap projections.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from flowmark.atomic_spans import iter_atomic_spans

from chopdiff.docs.block_tree import Block, parse_blocks
from chopdiff.docs.node import Layer, Node, NodeKind, NodeTable

if TYPE_CHECKING:
    from chopdiff.docs.text_doc import Section, TextDoc  # pyright: ignore[reportImportCycles]


# Atomic-span pattern names that map to inline NodeKinds.
_INLINE_ATOMIC_KINDS: dict[str, NodeKind] = {
    "markdown_link": NodeKind.link,
    "inline_code_span": NodeKind.code_span,
    "html_open_tag": NodeKind.inline_html,
    "html_close_tag": NodeKind.inline_html,
}


def _next_id(counter: list[int]) -> str:
    """Deterministic id from a preorder counter: `n0001`, `n0002`, ..."""
    idx = counter[0]
    counter[0] += 1
    return f"n{idx:04d}"


def _node_kind_for_block(block: Block) -> NodeKind:
    """Map a `BlockType` value to its corresponding `NodeKind`."""
    return NodeKind(block.type.value)


def _build_markdown_nodes(
    blocks: list[Block],
    source_text: str,
    parent_id: str | None,
    counter: list[int],
    nodes: dict[str, Node],
) -> list[str]:
    """
    Recursively build markdown-layer nodes from the structural block tree.
    Returns the list of child ids for the caller to wire into its `children`.
    """
    child_ids: list[str] = []
    for block in blocks:
        nid = _next_id(counter)
        child_ids.append(nid)
        attrs: dict[str, object] = {}

        # Heading level extracted directly from source text.
        if block.type.value == "heading" and block.span:
            block_text = source_text[block.span[0] : block.span[1]]
            stripped = block_text.lstrip()
            level = 0
            for ch in stripped:
                if ch == "#":
                    level += 1
                else:
                    break
            if level > 0:
                attrs["level"] = level
            else:
                # Setext heading: check for underline pattern.
                lines = block_text.strip().splitlines()
                if len(lines) >= 2:
                    underline = lines[-1].strip()
                    if underline and all(c == "=" for c in underline):
                        attrs["level"] = 1
                    elif underline and all(c == "-" for c in underline):
                        attrs["level"] = 2

        if block.tight is not None:
            attrs["tight"] = block.tight
            attrs["ordered"] = block.type.value == "ordered_list"

        node = Node(
            id=nid,
            kind=_node_kind_for_block(block),
            layer=Layer.markdown,
            parent=parent_id,
            children=[],
            source_span=block.span,
            attrs=attrs,
        )
        nodes[nid] = node

        if block.children:
            node.children = _build_markdown_nodes(block.children, source_text, nid, counter, nodes)
    return child_ids


def _find_innermost_block(offset: int, md_blocks: list[tuple[tuple[int, int], str]]) -> str | None:
    """Find the innermost (narrowest) markdown block node containing `offset`."""
    best: str | None = None
    best_width = float("inf")
    for span, nid in md_blocks:
        if span[0] <= offset < span[1]:
            width = span[1] - span[0]
            if width < best_width:
                best_width = width
                best = nid
    return best


def _find_deepest_section(offset: int, nodes: dict[str, Node]) -> str | None:
    """Find the deepest (narrowest) section node containing `offset`."""
    best: str | None = None
    best_width = float("inf")
    for nid, n in nodes.items():
        if n.layer == Layer.document and n.kind == NodeKind.section and n.source_span:
            s, e = n.source_span
            if s <= offset < e and (e - s) < best_width:
                best_width = e - s
                best = nid
    return best


def _find_sentence_node(offset: int, nodes: dict[str, Node]) -> str | None:
    """Find the narrowest textual-layer sentence node containing `offset`."""
    best: str | None = None
    best_width = float("inf")
    for nid, n in nodes.items():
        if n.layer == Layer.textual and n.kind == NodeKind.sentence and n.source_span:
            s, e = n.source_span
            if s <= offset < e and (e - s) < best_width:
                best_width = e - s
                best = nid
    return best


def _build_inline_nodes(
    source_text: str,
    doc: TextDoc,
    all_nodes: dict[str, Node],
    counter: list[int],
) -> None:
    """
    Add inline nodes (links, code spans, images, inline HTML) to the node table.

    Uses `doc.links()` for links (handles reference-link resolution), and
    flowmark's `iter_atomic_spans` for code spans and inline HTML. Each inline
    node's parent is its containing block node; section and sentence associations
    are stored in `attrs`.
    """
    # Sorted list of markdown block nodes for parent lookup.
    md_blocks: list[tuple[tuple[int, int], str]] = [
        (n.source_span, nid)
        for nid, n in all_nodes.items()
        if n.layer == Layer.markdown and n.source_span is not None
    ]
    md_blocks.sort(key=lambda x: (x[0][0], -x[0][1]))

    seen_spans: set[tuple[int, int]] = set()

    # Links via doc.links() (handles reference resolution correctly).
    for link in doc.links():
        if link.span is not None:
            if link.span in seen_spans:
                continue
            seen_spans.add(link.span)
            nid = _next_id(counter)
            parent = _find_innermost_block(link.span[0], md_blocks)
            attrs: dict[str, object] = {"url": link.url, "text": link.text}
            if link.title:
                attrs["title"] = link.title

            section_id = _find_deepest_section(link.span[0], all_nodes)
            if section_id:
                attrs["section"] = section_id
            sent_nid = _find_sentence_node(link.span[0], all_nodes)
            if sent_nid:
                attrs["sentence"] = sent_nid

            # Distinguish images from links: `!` immediately precedes the `[`.
            kind = NodeKind.link
            start = link.span[0]
            if start > 0 and source_text[start - 1] == "!":
                kind = NodeKind.image
                adjusted_span: tuple[int, int] = (start - 1, link.span[1])
            else:
                adjusted_span = link.span

            node = Node(
                id=nid,
                kind=kind,
                layer=Layer.markdown,
                parent=parent,
                source_span=adjusted_span,
                attrs=attrs,
            )
            all_nodes[nid] = node
            if parent and parent in all_nodes:
                all_nodes[parent].children.append(nid)
        else:
            # Reference link with no exact span.
            nid = _next_id(counter)
            ref_attrs: dict[str, object] = {"url": link.url, "text": link.text}
            if link.title:
                ref_attrs["title"] = link.title
            node = Node(
                id=nid,
                kind=NodeKind.link,
                layer=Layer.markdown,
                parent=None,
                source_span=None,
                attrs=ref_attrs,
            )
            all_nodes[nid] = node

    # Code spans, inline HTML, and images via iter_atomic_spans.
    for atomic in iter_atomic_spans(source_text):
        if not atomic.is_atomic or atomic.name is None:
            continue
        if atomic.name not in _INLINE_ATOMIC_KINDS:
            continue

        span = (atomic.start, atomic.end)

        # For markdown_link spans: links were already handled above via doc.links().
        # Only process unhandled ones here (images, which extract_links skips).
        if atomic.name == "markdown_link":
            if span in seen_spans:
                continue
            # Check if this is an image (preceded by `!`).
            if atomic.start > 0 and source_text[atomic.start - 1] == "!":
                kind = NodeKind.image
                span = (atomic.start - 1, atomic.end)
            else:
                # A non-image markdown_link not found by doc.links(); skip.
                continue
        else:
            kind = _INLINE_ATOMIC_KINDS[atomic.name]

        if span in seen_spans:
            continue
        seen_spans.add(span)

        nid = _next_id(counter)
        parent = _find_innermost_block(span[0], md_blocks)
        inline_attrs: dict[str, object] = {}
        if kind == NodeKind.code_span:
            content = atomic.text
            stripped = content.strip("`")
            inline_attrs["content"] = stripped.strip()
        elif kind == NodeKind.inline_html:
            inline_attrs["tag"] = atomic.text
        elif kind == NodeKind.image:
            inline_attrs["url"] = ""
            # Extract URL from the image markdown: ![alt](url)
            text = source_text[span[0] : span[1]]
            paren_start = text.find("(")
            paren_end = text.rfind(")")
            if paren_start >= 0 and paren_end > paren_start:
                inline_attrs["url"] = text[paren_start + 1 : paren_end]
            # Extract alt text.
            bracket_start = text.find("[")
            bracket_end = text.find("]")
            if bracket_start >= 0 and bracket_end > bracket_start:
                inline_attrs["text"] = text[bracket_start + 1 : bracket_end]

        section_id = _find_deepest_section(span[0], all_nodes)
        if section_id:
            inline_attrs["section"] = section_id
        sent_nid = _find_sentence_node(span[0], all_nodes)
        if sent_nid:
            inline_attrs["sentence"] = sent_nid

        node = Node(
            id=nid,
            kind=kind,
            layer=Layer.markdown,
            parent=parent,
            source_span=span,
            attrs=inline_attrs,
        )
        all_nodes[nid] = node
        if parent and parent in all_nodes:
            all_nodes[parent].children.append(nid)


def _build_section_nodes(
    sections: list[Section],
    parent_id: str | None,
    counter: list[int],
    nodes: dict[str, Node],
) -> list[str]:
    """Build document-layer section nodes from the heading hierarchy."""
    child_ids: list[str] = []
    for sec in sections:
        nid = _next_id(counter)
        child_ids.append(nid)
        attrs: dict[str, object] = {
            "level": sec.level,
            "title": sec.title,
        }
        node = Node(
            id=nid,
            kind=NodeKind.section,
            layer=Layer.document,
            parent=parent_id,
            children=[],
            source_span=sec.span,
            attrs=attrs,
        )
        nodes[nid] = node
        if sec.children:
            node.children = _build_section_nodes(sec.children, nid, counter, nodes)
    return child_ids


def build_node_table(doc: TextDoc) -> NodeTable:
    """
    Construct a `NodeTable` from a `TextDoc`, building nodes from three layers:

    - **markdown**: every structural block from the recursive block tree, plus
      inline elements (links, code spans, images, inline HTML).
    - **document**: one node per section from the heading hierarchy.
    - **textual**: paragraphs and sentences from the editing view.

    Node ids are deterministic preorder indexes (`n0001`, `n0002`, ...), stable
    within a parse of the same source text.
    """
    source_text = doc.source_text or doc.reassemble()
    nodes: dict[str, Node] = {}
    roots: list[str] = []
    counter: list[int] = [1]

    # Markdown layer: structural blocks.
    blocks = parse_blocks(source_text)
    root_ids = _build_markdown_nodes(blocks, source_text, None, counter, nodes)
    roots.extend(root_ids)

    # Document layer: sections from heading hierarchy.
    sections = doc.sections()
    section_root_ids = _build_section_nodes(sections, None, counter, nodes)
    roots.extend(section_root_ids)

    # Textual layer: paragraphs and sentences.
    for para in doc.paragraphs:
        para_nid = _next_id(counter)
        para_node = Node(
            id=para_nid,
            kind=NodeKind.paragraph,
            layer=Layer.textual,
            parent=None,
            children=[],
            source_span=para.span,
            attrs={},
        )
        nodes[para_nid] = para_node
        roots.append(para_nid)
        for sent in para.sentences:
            sent_nid = _next_id(counter)
            sent_node = Node(
                id=sent_nid,
                kind=NodeKind.sentence,
                layer=Layer.textual,
                parent=para_nid,
                children=[],
                source_span=sent.span,
                attrs={"text": sent.text},
            )
            nodes[sent_nid] = sent_node
            para_node.children.append(sent_nid)

    # Inline nodes (markdown layer): links, code spans, images, inline HTML.
    _build_inline_nodes(source_text, doc, nodes, counter)

    return NodeTable(nodes=nodes, roots=roots, source_text=source_text)
