---
type: is
id: is-01kt31anzhe1ygy2xtz3d5afw1
title: "B3: Build sections() from structural Markdown heading blocks, not paragraph heading detection"
kind: bug
status: open
priority: 1
version: 2
spec_path: docs/project/review/senior-engineering-review-doc-model-v0.3.1.md
labels: []
dependencies:
  - type: blocks
    target: is-01kt31bbfyavhq9ex9rtacaynq
parent_id: is-01kt319dt4d9cykh6kep8x2z86
created_at: 2026-06-02T02:06:46.257Z
updated_at: 2026-06-02T02:07:26.222Z
---
Finding 4 (P1). text_doc.py:603-634 sections() walks self.paragraphs and uses para.heading_level(); block_types warns the per-paragraph view can mis-split fenced code with blank lines, producing false sections (e.g. a '#'-prefixed line inside a code fence). build_node_table already builds structural markdown heading nodes (node_table.py:69-89) separately from doc.sections() document-layer nodes, so the two can disagree. Rebuild sections from structural heading blocks (levels+spans from the parser), attribute content by interval containment, and unify with the markdown heading nodes. Encode section-policy decisions (headings in blockquotes/lists/HTML/setext/code) as tests.
