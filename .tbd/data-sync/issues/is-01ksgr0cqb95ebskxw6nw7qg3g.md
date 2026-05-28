---
type: is
id: is-01ksgr0cqb95ebskxw6nw7qg3g
title: Automate validation of supply-chain policy (tests)
kind: task
status: closed
priority: 1
version: 2
labels: []
dependencies: []
parent_id: is-01ksgpj76w79rwg3e67hn5efnj
created_at: 2026-05-25T23:37:32.138Z
updated_at: 2026-05-25T23:37:39.961Z
---
Add tests/test_supply_chain.py: assert pyproject and uv.lock cool-off cutoffs match (drift silently disables the cool-off) and every per-package exception is documented in the marker doc. Code change (Replacement namedtuple) already covered by existing tests/html/test_html_tags.py suite.
