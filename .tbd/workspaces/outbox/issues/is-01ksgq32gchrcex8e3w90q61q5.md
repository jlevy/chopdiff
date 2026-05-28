---
type: is
id: is-01ksgq32gchrcex8e3w90q61q5
title: Review + allow strif 3.1.0 as documented cool-off exception
kind: task
status: closed
priority: 1
version: 2
labels: []
dependencies: []
parent_id: is-01ksgpj76w79rwg3e67hn5efnj
created_at: 2026-05-25T23:21:31.403Z
updated_at: 2026-05-25T23:23:31.441Z
---
Owner-approved. Full source diff of 3.0.1->3.1.0 reviewed: bug fixes (keep_backup/dest_path.exists, fd-leak os.close, copy_to_backup no-op), atomic path.replace, new atomic_write_text/bytes, HashAlgorithm Literal, Insertion/Replacement now NamedTuples. Zero deps, no build hooks, no network/install scripts. Safe. Allow via uv exclude-newer-package; fix html_tags.py to pass Replacement namedtuples.
