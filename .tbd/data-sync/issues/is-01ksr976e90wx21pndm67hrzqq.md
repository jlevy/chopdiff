---
type: is
id: is-01ksr976e90wx21pndm67hrzqq
title: "flowmark #52 P3: HTMLBlock advertised in span contract but disabled by CustomHTMLBlock.match"
kind: bug
status: closed
priority: 3
version: 3
labels: []
dependencies: []
created_at: 2026-05-28T21:53:01.897Z
updated_at: 2026-05-28T21:56:16.023Z
closed_at: 2026-05-28T21:56:16.022Z
close_reason: "Fixed: removed HTMLBlock from the documented covered set in flowmark.markdown_ast. flowmark intentionally disables marko's block HTML (CustomHTMLBlock.match() returns False), so HTML-shaped input has always fallen back to a Paragraph. Test renamed to test_html_block_input_falls_back_to_paragraph_with_a_span and asserts the fallback explicitly."
---
