# Golden-Document Tests

End-to-end “transparent box” tests for the document model.
Each source document under `documents/` is converted by the model and serialized three
ways; the serializations are committed under `expected/<doc>/` and compared on every
run. One readable artifact per document shows every projection at once, so any change to
any view appears in a diff.

## Layout

```
documents/<doc>.md          source: Markdown with YAML frontmatter (name, description,
                            optional item_partition_depth)
expected/<doc>/report.yaml      multi-view report (base blocks + cover, sections/TOC,
                                full node table, links by section, SpanRef round-trips)
expected/<doc>/docgraph.yaml    the DocGraph projection as clean YAML
expected/<doc>/reassembled.md   the editing view's reassembled (normalized) text
```

The serializer is the public, reusable `flexdoc.docs.debug` dumper (`doc_report`,
`doc_graph_yaml`, `dump_views`) — usable on any document from a REPL or script, not just
here.

## Running and updating

```bash
uv run pytest tests/golden/test_golden_docs.py            # compare against goldens
UPDATE_GOLDEN=1 uv run pytest tests/golden/test_golden_docs.py   # regenerate goldens
git diff tests/golden/expected/                           # review the behavioral diff
```

After an intentional model change, regenerate, then **review the diff as a behavioral
change**: if it is expected, commit the updated goldens; if not, it is a regression —
fix the code.

## Two layers of checking

- `test_golden_artifacts` — raw diff against the committed serializations (catches any
  unanticipated change anywhere in the output).
- `test_model_invariants` — the model’s hard guarantees, enforced independently of the
  golden diff so a semantic violation fails even if goldens are blindly regenerated:
  base-block complete cover, SpanRef round-trips, unique node ids with valid
  parent/child and DocGraph child references, span bounds, and `reassemble()`
  idempotence.

## Why no mocks or scrubbing

The model is deterministic and hermetic — no clock, network, LLM, or randomness; node
ids are a stable preorder counter, sha256 and token estimates are deterministic.
So there is nothing to mock and no unstable field to scrub: output is byte-stable across
runs.

## Determinism note

Node ids (`n0001…`) are deterministic and meaningful, so they appear verbatim in the
goldens (not pattern-matched).
Spans are Unicode code points, rendered `start:end`.
