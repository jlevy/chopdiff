"""
The `collect()` query primitive over a `NodeTable`.

`collect()` is the single general query primitive for the document model (DR-4).
It gathers matching nodes from the node table, optionally scoped to a subtree,
filtered by kind, predicate, or offset containment. Results may overlap their
containers (query semantics, not partition semantics).

Counts, values, and groupings are left to the caller via plain Python
(e.g. `Counter(n.kind for n in collect(...))`).
"""

from __future__ import annotations

from collections.abc import Callable

from chopdiff.docs.node import Layer, Node, NodeKind, NodeTable

# Inline NodeKinds: elements that live inside a block.
INLINE_KINDS: frozenset[NodeKind] = frozenset(
    {NodeKind.link, NodeKind.code_span, NodeKind.image, NodeKind.inline_html}
)


def collect(
    table: NodeTable,
    scope: str | None = None,
    *,
    kinds: set[NodeKind] | None = None,
    where: Callable[[Node], bool] | None = None,
    recursive: bool = False,
    inline: bool = False,
    contains: tuple[int, int] | None = None,
    layer: set[Layer] | None = None,
) -> list[Node]:
    """
    Gather nodes from `table` matching the given filters, in document order.

    `scope`: a node id restricting results to that node's subtree (None for
    the whole document). `kinds`: restrict to these `NodeKind`s (None = any).
    `where`: additional predicate on each node. `recursive`: when True,
    descend into children recursively; when False, only direct children of the
    scope (or roots). `inline`: when True, include inline-kind nodes; when
    False, exclude them. `contains`: an optional `(start, end)` span;
    restrict results to nodes whose `source_span` is within that span
    (offset-containment, the cross-layer query mechanism). `layer`: restrict to
    these parse layers (None = all layers); since the same span can appear as
    nodes in several layers (e.g. a `markdown` block and a `textual` paragraph),
    scope by `layer` to avoid cross-layer duplicates.
    """
    if scope is not None:
        candidates = _subtree_nodes(table, scope, recursive)
    elif recursive:
        # Recursive from roots: all nodes in insertion order.
        candidates = list(table.nodes.values())
    else:
        # Non-recursive, no scope: just the root nodes.
        candidates = [table.nodes[rid] for rid in table.roots if rid in table.nodes]

    result: list[Node] = []
    for node in candidates:
        if not inline and node.kind in INLINE_KINDS:
            continue
        if layer is not None and node.layer not in layer:
            continue
        if kinds is not None and node.kind not in kinds:
            continue
        if contains is not None:
            if node.source_span is None:
                continue
            ns, ne = node.source_span
            cs, ce = contains
            if not (cs <= ns and ne <= ce):
                continue
        if where is not None and not where(node):
            continue
        result.append(node)

    # Sort by source_span start (then by span width descending) for deterministic
    # document order. Nodes without a span (e.g. reference links) have no position, so
    # they sort last by id rather than colliding at offset 0 with real document-start
    # nodes.
    def _sort_key(n: Node) -> tuple[int, int, int, str]:
        if n.source_span is None:
            return (1, 0, 0, n.id)
        start, end = n.source_span
        return (0, start, -(end - start), n.id)

    result.sort(key=_sort_key)
    return result


def _subtree_nodes(table: NodeTable, scope_id: str, recursive: bool) -> list[Node]:
    """
    Collect nodes from a subtree rooted at `scope_id`.
    When `recursive` is False, returns only the direct children.
    When `recursive` is True, returns all descendants (not including the scope
    node itself, matching the "collect within" semantics).
    """
    scope_node = table.nodes[scope_id]
    if not recursive:
        return [table.nodes[cid] for cid in scope_node.children if cid in table.nodes]

    # BFS/DFS to collect all descendants.
    result: list[Node] = []
    stack = list(scope_node.children)
    while stack:
        nid = stack.pop(0)
        if nid not in table.nodes:
            continue
        node = table.nodes[nid]
        result.append(node)
        stack.extend(node.children)
    return result
