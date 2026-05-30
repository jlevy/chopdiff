"""
Node table: a flat, id-addressed table of all parsed elements in a document,
covering three layers (markdown, document, textual) over the same source text.

`build_node_table(doc)` constructs the table once from a `TextDoc`; the result
is cached lazily on `TextDoc.node_table` (safe because `source_text` is immutable
after parse).

The node table is the canonical normalized form from which derived views
(block tree, section tree, inline index, etc.) are cheap projections.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from flowmark.atomic_spans import iter_atomic_spans

from chopdiff.docs.block_tree import Block, parse_blocks
from chopdiff.docs.node import Layer, Node, NodeKind
from chopdiff.docs.text_doc import TextDoc

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
        if block.type.value == "heading":
            if block.span:
                # We don't have source_text here; level is inferred from
                # the leading '#' characters (set below in build_node_table
                # where source_text is available).
                pass
            attrs["_block"] = block
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
        # Recurse into block children.
        if block.children:
            node.children = _build_markdown_nodes(block.children, nid, counter, nodes)
    return child_ids


def _is_image_link(text: str) -> bool:  # pyright: ignore[reportUnusedFunction]
    """Check if a markdown_link atomic span is actually an image (`![...](...)`).
    Images are preceded by `!` in the source, which is part of the span text
    captured by the atomic pattern `![...](...)` or detected by a preceding `!`."""
    return text.startswith("![")


def _build_inline_nodes(
    source_text: str,
    doc: TextDoc,
    block_nodes: dict[str, Node],
    counter: list[int],
    nodes: dict[str, Node],
) -> None:
    """
    Add inline nodes (links, code spans, images, inline HTML) to the node table.

    Uses flowmark's `iter_atomic_spans` for code spans, images, and inline HTML,
    and `_block_links` / `doc.links()` for links (which handles reference-link
    resolution). Each inline node's parent is its containing block node; section
    and sentence associations are stored in `attrs`.
    """
    # Build a sorted list of markdown block nodes for parent lookup.
    md_blocks = [
        (n.source_span, nid)
        for nid, n in block_nodes.items()
        if n.layer == Layer.markdown and n.source_span is not None
    ]
    md_blocks.sort(key=lambda x: (x[0][0], -x[0][1]))

    def _find_parent_block(offset: int) -> str | None:
        """Find the innermost (narrowest) block containing `offset`."""
        best: str | None = None
        best_width = float("inf")
        for span, nid in md_blocks:
            if span[0] <= offset < span[1]:
                width = span[1] - span[0]
                if width < best_width:
                    best_width = width
                    best = nid
        return best

    def _section_for_offset(offset: int, sections: list[object]) -> str | None:  # pyright: ignore[reportUnusedParameter]
        """Find the section node id containing `offset` (from document-layer nodes)."""
        # Search deepest match by checking all section nodes.
        best: str | None = None
        best_width = float("inf")
        for nid, n in nodes.items():
            if n.layer == Layer.document and n.kind == NodeKind.section and n.source_span:
                s, e = n.source_span
                if s <= offset < e and (e - s) < best_width:
                    best_width = e - s
                    best = nid
        return best

    def _sentence_for_offset(offset: int) -> str | None:
        """Find the sentence node id containing `offset` (from textual-layer nodes)."""
        # Search sentence nodes directly.
        best: str | None = None
        best_width = float("inf")
        for nid, n in nodes.items():
            if n.layer == Layer.textual and n.source_span:
                s, e = n.source_span
                if s <= offset < e and (e - s) < best_width:
                    best_width = e - s
                    best = nid
        return best

    seen_spans: set[tuple[int, int]] = set()

    # Use doc.links() for links (handles reference resolution correctly).
    for link in doc.links():
        if link.span is not None:
            if link.span in seen_spans:
                continue
            seen_spans.add(link.span)
            nid = _next_id(counter)
            parent = _find_parent_block(link.span[0])
            attrs: dict[str, object] = {"url": link.url, "text": link.text}
            if link.title:
                attrs["title"] = link.title
            section_id = _section_for_offset(link.span[0], [])
            if section_id:
                attrs["section"] = section_id
            sent_idx = doc.sentence_at_offset(link.span[0])
            if sent_idx is not None:
                sent_nid = _sentence_for_offset(link.span[0])
                if sent_nid:
                    attrs["sentence"] = sent_nid

            # Determine if this is an image link by checking source.
            kind = NodeKind.link
            start = link.span[0]
            if start > 0 and source_text[start - 1] == "!":
                kind = NodeKind.image
                # Adjust span to include the `!`.
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
            nodes[nid] = node
            if parent and parent in nodes:
                nodes[parent].children.append(nid)
        else:
            # Reference link with no exact span: still add as a node.
            nid = _next_id(counter)
            attrs = {"url": link.url, "text": link.text}
            if link.title:
                attrs["title"] = link.title
            node = Node(
                id=nid,
                kind=NodeKind.link,
                layer=Layer.markdown,
                parent=None,
                source_span=None,
                attrs=attrs,
            )
            nodes[nid] = node

    # Use iter_atomic_spans for code spans, inline HTML.
    for atomic in iter_atomic_spans(source_text):
        if not atomic.is_atomic or atomic.name is None:
            continue
        if atomic.name not in _INLINE_ATOMIC_KINDS:
            continue
        kind = _INLINE_ATOMIC_KINDS[atomic.name]

        # Skip links and images already handled above.
        if atomic.name == "markdown_link":
            continue

        span = (atomic.start, atomic.end)
        if span in seen_spans:
            continue
        seen_spans.add(span)

        nid = _next_id(counter)
        parent = _find_parent_block(span[0])
        attrs = {}
        if kind == NodeKind.code_span:
            # Strip backtick delimiters for the content.
            content = atomic.text
            # Remove leading/trailing backticks.
            stripped = content.strip("`")
            attrs["content"] = stripped.strip()
        elif kind == NodeKind.inline_html:
            attrs["tag"] = atomic.text

        section_id = _section_for_offset(span[0], [])
        if section_id:
            attrs["section"] = section_id
        sent_nid = _sentence_for_offset(span[0])
        if sent_nid:
            attrs["sentence"] = sent_nid

        node = Node(
            id=nid,
            kind=kind,
            layer=Layer.markdown,
            parent=parent,
            source_span=span,
            attrs=attrs,
        )
        nodes[nid] = node
        if parent and parent in nodes:
            nodes[parent].children.append(nid)


@dataclass
class NodeTable:
    """
    A flat, id-addressed table of all parsed elements in a document, covering
    markdown, document, and textual layers over the same source text.

    The table is the canonical normalized form; derived views (block tree, section
    tree, etc.) are projections of it. Within a layer, `parent`/`children` form
    the containment structure; cross-layer relationships use interval containment
    via `containing()` and `contained_by()`.
    """

    nodes: dict[str, Node] = field(default_factory=dict)
    roots: list[str] = field(default_factory=list)
    source_text: str = ""

    def node(self, nid: str) -> Node:
        """Look up a node by id; raises `KeyError` if not found."""
        return self.nodes[nid]

    def by_kind(self, kind: NodeKind) -> list[Node]:
        """All nodes of a given kind, in insertion order."""
        return [n for n in self.nodes.values() if n.kind == kind]

    def by_layer(self, layer: Layer) -> list[Node]:
        """All nodes in a given layer, in insertion order."""
        return [n for n in self.nodes.values() if n.layer == layer]

    def children_of(self, nid: str) -> list[Node]:
        """The child nodes of the node with `nid`."""
        parent = self.nodes[nid]
        return [self.nodes[cid] for cid in parent.children]

    def containing(self, span: tuple[int, int]) -> list[Node]:
        """
        All nodes whose `source_span` fully contains `span` (i.e. the node's span
        encloses the query span). Useful for cross-layer containment queries like
        "which section contains this link."
        """
        start, end = span
        return [
            n
            for n in self.nodes.values()
            if n.source_span is not None and n.source_span[0] <= start and end <= n.source_span[1]
        ]

    def contained_by(self, span: tuple[int, int]) -> list[Node]:
        """
        All nodes whose `source_span` is fully contained within `span`. Useful for
        queries like "which blocks are inside this region."
        """
        start, end = span
        return [
            n
            for n in self.nodes.values()
            if n.source_span is not None and start <= n.source_span[0] and n.source_span[1] <= end
        ]


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
    root_ids = _build_markdown_nodes(blocks, None, counter, nodes)
    roots.extend(root_ids)

    # Post-process: set heading level attrs from source text.
    for node in list(nodes.values()):
        if node.kind == NodeKind.heading and node.source_span:
            text = source_text[node.source_span[0] : node.source_span[1]]
            # ATX heading: count leading '#' chars.
            stripped = text.lstrip()
            level = 0
            for ch in stripped:
                if ch == "#":
                    level += 1
                else:
                    break
            if level > 0:
                node.attrs["level"] = level
            else:
                # Setext heading: check for underline pattern.
                lines = text.strip().splitlines()
                if len(lines) >= 2:
                    underline = lines[-1].strip()
                    if all(c == "=" for c in underline):
                        node.attrs["level"] = 1
                    elif all(c == "-" for c in underline):
                        node.attrs["level"] = 2
        # Clean up temporary _block attr.
        node.attrs.pop("_block", None)

    # Document layer: sections from heading hierarchy.
    def _build_section_nodes(
        sections: Sequence[object],
        parent_id: str | None,
    ) -> list[str]:
        from chopdiff.docs.text_doc import Section

        child_ids: list[str] = []
        for sec in sections:
            assert isinstance(sec, Section)
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
                node.children = _build_section_nodes(sec.children, nid)
        return child_ids

    sections = doc.sections()
    section_root_ids = _build_section_nodes(sections, None)
    roots.extend(section_root_ids)

    # Textual layer: paragraphs and sentences.
    for para in doc.paragraphs:
        para_nid = _next_id(counter)
        para_attrs: dict[str, object] = {}
        para_node = Node(
            id=para_nid,
            kind=NodeKind.paragraph,
            layer=Layer.textual,
            parent=None,
            children=[],
            source_span=para.span,
            attrs=para_attrs,
        )
        nodes[para_nid] = para_node
        roots.append(para_nid)
        for sent in para.sentences:
            sent_nid = _next_id(counter)
            sent_node = Node(
                id=sent_nid,
                kind=NodeKind.paragraph,
                layer=Layer.textual,
                parent=para_nid,
                children=[],
                source_span=sent.span,
                attrs={"text": sent.text},
            )
            nodes[sent_nid] = sent_node
            para_node.children.append(sent_nid)

    # Inline nodes (markdown layer): links, code spans, images, inline HTML.
    block_nodes = {nid: n for nid, n in nodes.items() if n.layer == Layer.markdown}
    _build_inline_nodes(source_text, doc, block_nodes, counter, nodes)

    return NodeTable(nodes=nodes, roots=roots, source_text=source_text)
