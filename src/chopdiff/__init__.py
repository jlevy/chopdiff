"""
chopdiff is a library for diff filtering, token mapping, and windowed transforms, built on
the flexdoc document layer. It has no root-level public API by design; import from the
submodules, which carry the explicit public surfaces:

- `chopdiff.transforms` — sliding-window transforms, diff filters, window settings.
- `chopdiff.divs` — `TextNode` and HTML-`div` chunking.

The document model (`TextDoc`, the node table, `collect()`, `DocGraph`, `SpanRef`,
html-in-md, lemmatization) lives in the `flexdoc` package; import it from `flexdoc.docs`,
`flexdoc.html`, and `flexdoc.util`.

Root-level convenience re-exports may be added once the public-API surface (see
`docs/project/specs/active/plan-2026-05-29-unified-document-model.md`) is settled, so the
top-level API is designed once rather than piecemeal.
"""
