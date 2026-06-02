---
type: is
id: is-01kt319dt4d9cykh6kep8x2z86
title: "Spec: Address senior eng review of doc model v0.3.1"
kind: epic
status: open
priority: 2
version: 18
spec_path: docs/project/review/senior-engineering-review-doc-model-v0.3.1.md
labels: []
dependencies: []
child_order_hints:
  - is-01kt319xssaqmb17awyf0t58ga
  - is-01kt319y28m03dmy21284ddjvv
  - is-01kt319yacfspnd0tq60ee3x8j
  - is-01kt319yjw3qnemeh96hfyr77q
  - is-01kt31a7sptqjfs8jt0710rydp
  - is-01kt31a82j8v9aqddc8f5ee1vz
  - is-01kt31anf160w4d18t4b0hbdjk
  - is-01kt31anq6fgamdfxh6061ycqq
  - is-01kt31anzhe1ygy2xtz3d5afw1
  - is-01kt31ban660t6ex1vjx05mrgs
  - is-01kt31baz91ypbx3z4qm6209g8
  - is-01kt31bb7hyhw5zg0p23fv3yca
  - is-01kt31bbfyavhq9ex9rtacaynq
  - is-01kt31bbr8a9rsc9zh6rp3d7gd
  - is-01kt31bc0b0cf6kjcgd2zetf5x
  - is-01kt3d5f3dcfnjdyw03db1bxz1
  - is-01kt3gy0vvq1j34rbqe975k47r
created_at: 2026-06-02T02:06:05.124Z
updated_at: 2026-06-02T06:39:28.635Z
---
Track and address the findings from the v0.3.1 senior engineering review of the TextDoc/DocGraph document model. Architecture (source string + Unicode code-point offset space as canonical substrate; layered projections) is endorsed and preserved. Work is grouped into three tiers: A = cheap correctness/clarity fixes (low risk); B = structural correctness needing an interval index (sections rebuild, query relations); C = larger architecture needing product decisions (DocumentSnapshot immutability, schema hardening, SpanRef selector family, module split). No P0 in the snapshot.
