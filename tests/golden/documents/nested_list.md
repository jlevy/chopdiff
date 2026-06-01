---
name: nested_list
description: Deeply nested list with content after a sublist, partitioned at
  item_partition_depth=2 so the cover invariant and the depth cap are both exercised.
item_partition_depth: 2
---
# Nested List

- level one item
  - level two item
    - level three item
      - level four item

    text between deep sublists at level two

  more level-one content after the sublist
- second top-level item
