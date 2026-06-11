"""
A lightweight per-layer index over node source spans for offset-containment
queries, so node-table assembly does not rescan the whole table for each inline
element. See `flexdoc.docs.node_table`.
"""

from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass, field

from flexdoc.docs.node import Layer, Node, NodeKind

# One entry per spanned node: (start, end, kind, id).
_Entry = tuple[int, int, NodeKind, str]


@dataclass
class _LayerEntries:
    entries: list[_Entry] = field(default_factory=list)
    starts: list[int] = field(default_factory=list)


@dataclass
class IntervalIndex:
    """
    Per-layer index of node spans, built once and queried for containment.

    Within a layer, node spans are well-nested, so the innermost (narrowest) node
    containing an offset is the containing node with the greatest start. Entries
    are sorted by start; `innermost` bisects to the candidates that start at or
    before the offset and scans back to the first that still contains it. For an
    inline element's offset (always inside a leaf node) this returns on the first
    step; an offset in a gap costs a short walk bounded by nesting depth, never a
    full-table scan.
    """

    layers: dict[Layer, _LayerEntries]

    @classmethod
    def from_nodes(cls, nodes: dict[str, Node]) -> IntervalIndex:
        layers: dict[Layer, _LayerEntries] = {}
        for nid, node in nodes.items():
            if node.source_span is None:
                continue
            le = layers.setdefault(node.layer, _LayerEntries())
            le.entries.append((node.source_span[0], node.source_span[1], node.kind, nid))
        for le in layers.values():
            # Sort by start ascending, then by end descending so an enclosing node
            # precedes the nodes it contains when their starts coincide.
            le.entries.sort(key=lambda e: (e[0], -e[1]))
            le.starts = [e[0] for e in le.entries]
        return cls(layers=layers)

    def innermost(self, offset: int, layer: Layer, kind: NodeKind | None = None) -> str | None:
        """
        The id of the narrowest node in `layer` whose span contains `offset`
        (half-open: `start <= offset < end`), optionally restricted to `kind`,
        or None if no such node exists.
        """
        le = self.layers.get(layer)
        if le is None:
            return None
        # Candidates start at or before the offset; scan back to the closest one
        # that still contains it (the deepest, i.e. narrowest, for nested spans).
        for i in range(bisect_right(le.starts, offset) - 1, -1, -1):
            _start, end, node_kind, nid = le.entries[i]
            if end <= offset:
                continue
            if kind is not None and node_kind != kind:
                continue
            return nid
        return None
