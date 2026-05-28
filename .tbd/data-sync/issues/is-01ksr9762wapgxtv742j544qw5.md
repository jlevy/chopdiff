---
type: is
id: is-01ksr9762wapgxtv742j544qw5
title: "flowmark #52 P2: Document.span uses original input length, must use Source preprocessed-buffer length"
kind: bug
status: closed
priority: 2
version: 3
labels: []
dependencies: []
created_at: 2026-05-28T21:53:01.531Z
updated_at: 2026-05-28T21:54:02.553Z
closed_at: 2026-05-28T21:54:02.552Z
close_reason: "Fixed: CustomParser.parse now sets doc.span = (0, len(text.replace('\\r\\n', '\\n'))), matching marko's Source._preprocess_text so the root coordinate space agrees with every descendant span. Test strengthened to assert block_span(doc) == (0, normalized_len)."
---
