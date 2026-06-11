"""
flexdoc is the document-layer library underlying chopdiff: a source-grounded, layered
model of Markdown and text. It has no root-level public API by design; import from the
submodules, which carry the explicit public surfaces:

- `flexdoc.docs` — `TextDoc`, `Paragraph`, `Sentence`, `Section`, `Block`, `BlockType`,
  the node table, `collect()`, `DocGraph`, `SpanRef`, token diffs/mappings, and word-token
  utilities.
- `flexdoc.html` — html-in-md, html/plaintext conversion, HTML tag helpers, the content
  extractor, and timestamp extraction.
- `flexdoc.util` — lemmatization and token estimation.

Root-level convenience re-exports may be added once the public-API surface (see
`docs/project/specs/active/plan-2026-05-29-unified-document-model.md`) is settled, so the
top-level API is designed once rather than piecemeal.
"""
