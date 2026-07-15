---
type: is
id: is-01kxhhmtvzg0p9e80j2tq03xyq
title: "R2: Honor word-window shifts and validate public window generators"
kind: bug
status: open
priority: 1
version: 1
labels:
  - review-finding
dependencies: []
parent_id: is-01kxhh1t7n4zpy9x8pqtwh9fye
created_at: 2026-07-15T00:08:23.678Z
updated_at: 2026-07-15T00:08:23.678Z
---
`sliding_word_window` advances the numeric offset but starts from the previous end sentence, and zero shift repeats forever. Apply start offsets consistently and reject invalid direct arguments.
