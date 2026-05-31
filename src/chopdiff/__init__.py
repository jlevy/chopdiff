"""
chopdiff is a library; it has no root-level public API by design. Import from the
submodules, which carry the explicit public surfaces:

- `chopdiff.docs` — `TextDoc`, `Paragraph`, `Sentence`, `Section`, `Block`, `BlockType`,
  token diffs/mappings, and word-token utilities.
- `chopdiff.transforms` — sliding-window transforms, diff filters, window settings.
- `chopdiff.divs` — `TextNode` and HTML-`div` chunking.
- `chopdiff.html` — HTML tag helpers and timestamp extraction.

Root-level convenience re-exports may be added once the `DocOverview` public-API surface
(see `docs/project/specs/active/plan-2026-05-29-unified-document-model.md`) is settled, so
the top-level API is designed once rather than piecemeal.
"""
