---
type: is
id: is-01ksrzg02t2707q1aeeq4m33ex
title: Consolidate the two grounded-document-model research docs into one subsuming doc
kind: task
status: closed
priority: 2
version: 3
labels: []
dependencies: []
created_at: 2026-05-29T04:22:18.970Z
updated_at: 2026-05-29T04:26:50.444Z
closed_at: 2026-05-29T04:26:50.444Z
close_reason: Consolidated both research docs into docs/project/research/research-2026-05-29-document-model.md; all content mapped (overview, questions, scope, project context, full findings, unified 22-approach matrix, options A-F + G-I, JSON sketch, use-case mapping, implementation phases, risks, recommendations, next steps, methodology, references). Removed the two originals; updated TODO index. Pushed in c6d3659.
---
Two overlapping research docs exist by different agents:
- research-2026-05-29-grounded-document-model.md (Codex): broad survey, 16-row comparison matrix, Options A-F, recommended Option F (source-grounded graph + views), JSON sketch, use-case mapping, implementation phases (near/medium/later), risks, references.
- research-2026-05-29-document-model-layering.md (Claude): model/serialization/impl separation; collapses visual-UI + multi-view into one model->views requirement; adds prior art (stand-off annotation UIMA/brat/GATE/W3C, lossless red-green trees, CRDTs, block-JSON editors, djot); 6-row matrix.

Goal: create a third doc that subsumes both, mapping ALL content systematically so nothing is lost, then remove the two originals. Keep the comparison table + structure from the layering doc; merge in the broader survey content, the larger matrix, JSON sketch, use-case mapping, and implementation phases from the grounded doc.

Content blocks to map (checklist):
[ ] Overview + motivation (both)
[ ] Questions to answer (both)
[ ] Scope incl/excl (both)
[ ] Existing project context: TextDoc, TextNode, active specs (grounded)
[ ] Findings: grounding patterns, Markdown ASTs (Marko/mdast/CommonMark), cross-format (Pandoc), DOM, editor models (ProseMirror/Slate/Quill), incremental parsers (Tree-sitter/Lezer), layout extraction (PDF.js/Docling), semantic XML (DocBook/JATS/TEI) (grounded)
[ ] Findings: model/serialization/impl separation; zoom==views; stand-off annotation; red-green trees; CRDTs; block-JSON editors; djot (layering)
[ ] Key insights (both, dedup)
[ ] Unified comparison matrix (merge 16-row grounded + 6-row layering into one)
[ ] Options A-F considered (grounded) + layering Options A-C
[ ] Recommended direction + JSON sketch (grounded)
[ ] Use-case mapping (grounded)
[ ] Implementation implications: near/medium/later (grounded)
[ ] Risks (grounded)
[ ] Recommendations (both)
[ ] Next steps (both)
[ ] Methodology + References (both, merge)
