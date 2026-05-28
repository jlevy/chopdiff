---
type: is
id: is-01ksqnw98kc6cve3vn8f5d9rgx
title: TextDoc.links() drops reference-style cross-block links
kind: bug
status: closed
priority: 1
version: 3
labels: []
dependencies: []
created_at: 2026-05-28T16:15:01.395Z
updated_at: 2026-05-28T16:17:19.557Z
closed_at: 2026-05-28T16:17:19.557Z
close_reason: "Fixed: TextDoc.links() now parses source_text once at the doc level, resolving reference-style links across blocks. Atomic-span alignment is now by URL containment, so reference/unlocated identities keep their identity with span=None without dropping inline link spans. New tests in test_links.py cover full and shortcut reference forms."
---
