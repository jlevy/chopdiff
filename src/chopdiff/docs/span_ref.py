"""
`SpanRef`: a durable, source-canonical span reference type.

The quoted text (`exact` plus optional `prefix`/`suffix` context) is the
CANONICAL durable anchor; the offsets (`start`/`end`) are a recomputable hint.
Resolution uses an exact offset fast path (check `source_text[start:end]`),
falling back to a quote search with prefix/suffix disambiguation. A `SpanRef`
survives reparsing and re-anchors after edits that shift offsets.
"""

from __future__ import annotations

from dataclasses import dataclass

from chopdiff.docs.node import Node

# Default context window size for prefix/suffix capture.
_CONTEXT_WINDOW = 24


@dataclass
class SpanRef:
    """
    A span reference carrying two coordinated anchors: a quoted text span
    (canonical, durable) and character offsets (a recomputable hint).

    `exact` is the verbatim text of the referenced span. `prefix` and
    `suffix` are short context windows around it for disambiguation.
    `start` and `end` are Unicode code-point offsets into the source text.
    """

    exact: str
    prefix: str | None = None
    suffix: str | None = None
    start: int | None = None
    end: int | None = None

    @classmethod
    def from_node(cls, node: Node, source_text: str) -> SpanRef:
        """
        Build a `SpanRef` from a `Node` that has a `source_span`. Fills `exact`
        from the source text, captures prefix/suffix context, and sets offsets.
        """
        if node.source_span is None:
            raise ValueError(f"Node {node.id} has no source_span")
        start, end = node.source_span
        return cls.from_span(source_text, start, end)

    @classmethod
    def from_span(cls, source_text: str, start: int, end: int) -> SpanRef:
        """
        Build a `SpanRef` from a source text and explicit offsets.
        """
        exact = source_text[start:end]
        prefix_start = max(0, start - _CONTEXT_WINDOW)
        prefix = source_text[prefix_start:start] if prefix_start < start else None
        suffix_end = min(len(source_text), end + _CONTEXT_WINDOW)
        suffix = source_text[end:suffix_end] if end < suffix_end else None
        return cls(exact=exact, prefix=prefix, suffix=suffix, start=start, end=end)

    def to_persisted(self) -> SpanRef:
        """
        Return a copy suitable for persistence: quote-canonical with no transient
        offsets. The persisted form references text, not positions.
        """
        return SpanRef(exact=self.exact, prefix=self.prefix, suffix=self.suffix)

    def to_text_fragment(self) -> str:
        """
        Produce a Chrome-style `#:~:text=` URL text-fragment directive.
        Format: `#:~:text=[prefix-,]exact[,-suffix]`.
        This is a lossy projection (prose, word-boundary, case-insensitive).
        """
        parts: list[str] = []
        if self.prefix:
            parts.append(f"{self.prefix}-,")
        parts.append(self.exact)
        if self.suffix:
            parts.append(f",-{self.suffix}")
        return "#:~:text=" + "".join(parts)


def resolve(span_ref: SpanRef, source_text: str) -> tuple[int, int] | None:
    """
    Resolve a `SpanRef` against `source_text`, returning the `(start, end)`
    offsets or None if the span cannot be found.

    Fast path: if `start`/`end` are present and the text at those offsets
    matches `exact`, return immediately. Otherwise, search the full text for
    `exact`, disambiguating with `prefix`/`suffix` if needed, and update
    the `SpanRef`'s offsets in place.
    """
    # Fast path: offsets are valid.
    if span_ref.start is not None and span_ref.end is not None:
        s, e = span_ref.start, span_ref.end
        if 0 <= s <= e <= len(source_text) and source_text[s:e] == span_ref.exact:
            return (s, e)

    # Slow path: search for the exact text in the source.
    exact = span_ref.exact
    if not exact:
        return None

    # Collect all occurrences.
    occurrences: list[int] = []
    search_start = 0
    while True:
        idx = source_text.find(exact, search_start)
        if idx < 0:
            break
        occurrences.append(idx)
        search_start = idx + 1

    if not occurrences:
        return None

    if len(occurrences) == 1:
        best = occurrences[0]
    else:
        # Disambiguate with prefix/suffix scoring.
        best = _best_match(occurrences, exact, span_ref.prefix, span_ref.suffix, source_text)

    start = best
    end = best + len(exact)
    # Update offsets in place for future fast-path use.
    span_ref.start = start
    span_ref.end = end
    return (start, end)


def _best_match(
    occurrences: list[int],
    exact: str,
    prefix: str | None,
    suffix: str | None,
    source_text: str,
) -> int:
    """
    Among multiple occurrences of `exact`, pick the one best matching the
    prefix/suffix context. Returns the start offset of the best match.
    """
    best_idx = occurrences[0]
    best_score = -1
    for idx in occurrences:
        score = 0
        if prefix is not None:
            pre_start = max(0, idx - len(prefix))
            actual_prefix = source_text[pre_start:idx]
            if actual_prefix == prefix:
                score += 2
            elif prefix.endswith(actual_prefix) or actual_prefix.endswith(prefix):
                score += 1
        if suffix is not None:
            end = idx + len(exact)
            suf_end = min(len(source_text), end + len(suffix))
            actual_suffix = source_text[end:suf_end]
            if actual_suffix == suffix:
                score += 2
            elif suffix.startswith(actual_suffix) or actual_suffix.startswith(suffix):
                score += 1
        if score > best_score:
            best_score = score
            best_idx = idx
    return best_idx
