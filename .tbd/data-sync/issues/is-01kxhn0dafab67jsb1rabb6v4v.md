---
type: is
id: is-01kxhn0dafab67jsb1rabb6v4v
title: "PR #30 review R1: Publish omits sdist manifest gate"
kind: bug
status: closed
priority: 1
version: 3
labels: []
dependencies: []
parent_id: is-01kxhn010xfz7tz514kja2a6dh
created_at: 2026-07-15T01:07:08.749Z
updated_at: 2026-07-15T01:10:27.171Z
closed_at: 2026-07-15T01:10:27.170Z
close_reason: Fixed by running the shared tested sdist validator in publish.yml after uv build and before uv publish; workflow-order regression test added.
---
PR #30, .github/workflows/publish.yml:49. The publish workflow builds and immediately publishes the sdist without running the minimal-manifest validation enforced by CI. Add the same fail-closed validation before uv publish. Review thread: PRRT_kwDOOBrMzs6Q8TTz.
