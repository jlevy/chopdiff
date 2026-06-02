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

from collections import deque
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
    subtree_of: str | None = None,
    within: str | tuple[int, int] | None = None,
    overlaps: str | tuple[int, int] | None = None,
    contains: tuple[int, int] | None = None,
    kinds: set[NodeKind] | None = None,
    where: Callable[[Node], bool] | None = None,
    recursive: bool = False,
    inline: bool = False,
    layer: set[Layer] | None = None,
) -> list[Node]:
    """
    Gather nodes from `table` matching the given filters, in document order.

    Two distinct relations select candidates. The tree relation `subtree_of` is a
    node id restricting results to that node's within-layer parent/child subtree
    (`recursive` descends the whole subtree, else only direct children). The
    interval relations are cross-layer and offset-based, each accepting a node id
    or an explicit `(start, end)` span: `within` keeps nodes whose span is
    contained in the region (region's span for a node id); `overlaps` keeps nodes
    whose span intersects the region. With no relation, candidates are the root
    nodes (or all nodes when `recursive`); supplying an interval relation scans all
    nodes, so `within=section_id` needs no `recursive=True`.

    `scope` is a deprecated alias for `subtree_of`; `contains` is a deprecated,
    span-only alias for `within` (use `within` for the node-id form). Passing an
    alias together with its modern name raises `ValueError`. `kinds`: restrict to
    these `NodeKind`s (None = any).
    `where`: additional `Node -> bool` predicate. `inline`: include inline-kind
    nodes; an explicit `kinds` naming inline kinds (e.g. `{NodeKind.link}`) implies
    this, so the common case works without `inline=True`. `layer`: restrict to
    these parse layers (None = all); since the same span can appear in several
    layers (e.g. a `markdown` block and a `textual` paragraph), scope by `layer` to
    avoid cross-layer duplicates.
    """
    if scope is not None and subtree_of is not None:
        raise ValueError("pass either `subtree_of` or its deprecated alias `scope`, not both")
    if contains is not None and within is not None:
        raise ValueError("pass either `within` or its deprecated alias `contains`, not both")
    subtree_of = subtree_of if subtree_of is not None else scope
    within_ref = within if within is not None else contains

    want_within = within_ref is not None
    want_overlaps = overlaps is not None
    within_region = _resolve_region(table, within_ref)
    overlaps_region = _resolve_region(table, overlaps)
    # A relation whose node id has no span matches nothing.
    if (want_within and within_region is None) or (want_overlaps and overlaps_region is None):
        return []

    if subtree_of is not None:
        candidates = _subtree_nodes(table, subtree_of, recursive)
    elif recursive or want_within or want_overlaps:
        # Recursive, or any interval relation: consider all nodes in insertion order.
        candidates = list(table.nodes.values())
    else:
        # No relation, non-recursive: just the root nodes.
        candidates = [table.nodes[rid] for rid in table.roots if rid in table.nodes]

    # An explicit kind selection that names inline kinds implies inline inclusion,
    # so `collect(kinds={NodeKind.link})` is not silently emptied by the inline guard.
    include_inline = inline or (kinds is not None and bool(kinds & INLINE_KINDS))

    result: list[Node] = []
    for node in candidates:
        if not include_inline and node.kind in INLINE_KINDS:
            continue
        if layer is not None and node.layer not in layer:
            continue
        if kinds is not None and node.kind not in kinds:
            continue
        if within_region is not None and not _span_within(node.source_span, within_region):
            continue
        if overlaps_region is not None and not _span_overlaps(node.source_span, overlaps_region):
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


def _resolve_region(table: NodeTable, ref: str | tuple[int, int] | None) -> tuple[int, int] | None:
    """Resolve an interval-relation argument to a span: a node id maps to its
    `source_span` (None if it has none), a tuple is returned as-is."""
    if ref is None:
        return None
    if isinstance(ref, str):
        return table.nodes[ref].source_span
    return ref


def _span_within(span: tuple[int, int] | None, region: tuple[int, int]) -> bool:
    """True when `span` is fully contained in `region` (subset-or-equal)."""
    if span is None:
        return False
    return region[0] <= span[0] and span[1] <= region[1]


def _span_overlaps(span: tuple[int, int] | None, region: tuple[int, int]) -> bool:
    """True when `span` intersects `region` (half-open intervals)."""
    if span is None:
        return False
    return span[0] < region[1] and region[0] < span[1]


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

    # BFS to collect all descendants.
    result: list[Node] = []
    queue: deque[str] = deque(scope_node.children)
    while queue:
        nid = queue.popleft()
        if nid not in table.nodes:
            continue
        node = table.nodes[nid]
        result.append(node)
        queue.extend(node.children)
    return result
