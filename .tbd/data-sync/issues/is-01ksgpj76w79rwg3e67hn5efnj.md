---
type: is
id: is-01ksgpj76w79rwg3e67hn5efnj
title: Supply-chain hardening + full dependency upgrade
kind: epic
status: closed
priority: 1
version: 13
labels: []
dependencies: []
child_order_hints:
  - is-01ksgpjhms9r8e8nz2w7x1v81t
  - is-01ksgpjhwb2v8qec0v2ww8fd6k
  - is-01ksgpjj44exp9q485r92f2pjd
  - is-01ksgpjjd0mqg4hmtrkr2bvgwz
  - is-01ksgpjjmjw9e35jsgatrr3brc
  - is-01ksgpjk1vpp0mmcr7200zxey7
  - is-01ksgpjkaxcjtdk6b1ez6de5zn
  - is-01ksgq32gchrcex8e3w90q61q5
  - is-01ksgq32ry5jameq3gckwgxxe9
  - is-01ksgq330x11zgw9tp80m71pk3
  - is-01ksgr0cqb95ebskxw6nw7qg3g
created_at: 2026-05-25T23:12:19.163Z
updated_at: 2026-05-26T06:38:09.425Z
closed_at: 2026-05-26T06:38:09.424Z
close_reason: "Shipped in PR #5 (merged): 14-day cool-off via exclude-newer, committed lockfile, --locked CI installs, pip-audit --all-extras gate, documented strif/idna exceptions, hardened .claude session hooks (pinned + user-local + checksum-verified gh), and the simple-modern-uv v0.2.26 template upgrade."
---
Apply the supply-chain-hardening guideline to this uv/Python repo: add the SUPPLY-CHAIN-SECURITY.md marker doc, enforce the 14-day cool-off on the full upgrade, document all deps, add an audit gate, and ensure all docs follow the writing-style guidelines.
