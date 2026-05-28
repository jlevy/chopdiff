---
type: is
id: is-01ksqnw9h1kjvcd5dgenv2tj6g
title: TextDoc.blocks() merges adjacent Markdown blocks without blank lines
kind: bug
status: closed
priority: 1
version: 3
labels: []
dependencies: []
created_at: 2026-05-28T16:15:01.665Z
updated_at: 2026-05-28T16:20:58.026Z
closed_at: 2026-05-28T16:20:58.026Z
close_reason: "Fixed: block_tree's _parse_region now recognizes ATX heading, fenced code, and thematic break lines as single-line / hard-boundary blocks, terminates accumulation at hard starters and at paragraph→list transitions, and treats =/- underlines after non-blank text as setext heading boundaries. Reviewer's repro (# Title\\nParagraph...) now yields heading/paragraph/heading/paragraph. New parity tests cross-check block count against marko for several no-blank-line cases."
---
