"""
Read-time caching contract for `TextDoc`: derivations are pure functions of the
immutable source, cache population is the only state change during a read, and that
population is idempotent, deterministic, and thread-safe (computed at most once even
under concurrent access).
"""

from __future__ import annotations

import copy
import pickle
import threading
from concurrent.futures import ThreadPoolExecutor

import marko.parser as marko_parser

from flexdoc.docs.block_tree import parse_blocks
from flexdoc.docs.text_doc import TextDoc, _block_links

_TEXT = (
    "# Title\n\n"
    + "\n\n".join(
        f"Paragraph {i} has a [link{i}](https://example.com/{i}) and `code{i}` inline. "
        f"It also has a second sentence number {i}."
        for i in range(60)
    )
    + "\n\n## Subsection\n\nClosing paragraph with [final](https://example.com/final).\n"
)


def test_shared_parse_matches_independent_parses():
    """blocks() and links() derived from the one shared parse equal independent parses."""
    doc = TextDoc.from_text(_TEXT)
    assert [(b.type, b.span) for b in doc.blocks()] == [
        (b.type, b.span) for b in parse_blocks(_TEXT)
    ]
    assert doc.links() == _block_links(_TEXT, 0)


def test_read_order_does_not_change_results():
    """Deriving links before blocks gives the same values as blocks before links."""
    d1 = TextDoc.from_text(_TEXT)
    b1 = [(b.type, b.span) for b in d1.blocks()]
    l1 = d1.links()

    d2 = TextDoc.from_text(_TEXT)
    l2 = d2.links()
    b2 = [(b.type, b.span) for b in d2.blocks()]

    assert b1 == b2
    assert l1 == l2


def test_caches_are_identity_stable_but_public_views_are_copies():
    doc = TextDoc.from_text(_TEXT)
    assert doc.node_table() is doc.node_table()
    assert doc._parsed() is doc._parsed()
    # Public blocks() returns a fresh list each call (so callers cannot poison the cache)
    # whose shared elements are equal.
    first, second = doc.blocks(), doc.blocks()
    assert first is not second
    assert first == second


def test_concurrent_reads_parse_once_and_return_one_table():
    """Under concurrent first access, the document is fully parsed exactly once and every
    reader observes the same cached node table."""
    doc = TextDoc.from_text(_TEXT)
    assert len(_TEXT) > 2000  # ensures the full-doc parse is distinguishable by length

    original_parse = marko_parser.Parser.parse
    full_doc_parses = 0
    count_lock = threading.Lock()

    def counting_parse(self: marko_parser.Parser, text: str):  # type: ignore[no-untyped-def]
        if len(text) > 2000:
            nonlocal full_doc_parses
            with count_lock:
                full_doc_parses += 1
        return original_parse(self, text)

    def read_table_id(_: int) -> int:
        return id(doc.node_table())

    marko_parser.Parser.parse = counting_parse  # type: ignore[method-assign]
    try:
        with ThreadPoolExecutor(max_workers=8) as pool:
            table_ids = list(pool.map(read_table_id, range(32)))
    finally:
        marko_parser.Parser.parse = original_parse  # type: ignore[method-assign]

    assert len(set(table_ids)) == 1
    assert full_doc_parses == 1


def test_textdoc_deepcopy_and_pickle_cold_and_warm():
    """The per-instance lock must not break value semantics: TextDoc stays deep-copyable
    and picklable, both before and after its caches are warmed (caches/lock are dropped
    and re-derived on the copy)."""
    doc = TextDoc.from_text(_TEXT)

    # Cold: no caches warmed yet.
    assert copy.deepcopy(doc) == doc
    assert pickle.loads(pickle.dumps(doc)) == doc

    # Warm the caches, then copy/pickle.
    doc.node_table()
    doc.blocks()
    doc.links()

    warm_copy = copy.deepcopy(doc)
    assert warm_copy == doc
    assert warm_copy.reassemble() == doc.reassemble()
    # The copy re-derives its own caches rather than sharing the original's objects.
    assert warm_copy.node_table() is not doc.node_table()
    assert [(b.type, b.span) for b in warm_copy.blocks()] == [
        (b.type, b.span) for b in doc.blocks()
    ]

    restored = pickle.loads(pickle.dumps(doc))
    assert restored == doc
    assert restored.links() == doc.links()
