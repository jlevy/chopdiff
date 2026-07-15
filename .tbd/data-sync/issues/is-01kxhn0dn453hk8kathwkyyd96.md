---
type: is
id: is-01kxhn0dn453hk8kathwkyyd96
title: "PR #30 review R2: Sdist check masks archive-read failures"
kind: bug
status: closed
priority: 1
version: 3
labels: []
dependencies: []
parent_id: is-01kxhn010xfz7tz514kja2a6dh
created_at: 2026-07-15T01:07:09.091Z
updated_at: 2026-07-15T01:10:26.724Z
closed_at: 2026-07-15T01:10:26.723Z
close_reason: Fixed with a fail-closed Python sdist validator that rejects missing, unreadable, and repository-polluted archives; covered by regression tests and a real build validation.
---
PR #30, .github/workflows/ci.yml:116-122. The tar-to-grep pipeline can return success when the sdist is missing, empty, or unreadable. Make manifest validation fail closed and test missing, invalid, and forbidden-content archives. Review thread: PRRT_kwDOOBrMzs6Q8TT3.
