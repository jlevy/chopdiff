---
name: malformed
description: Malformed Markdown (unterminated code fence, ragged table, stray markers) to
  confirm the model degrades to best-effort structure and never throws (P17).
---
# Malformed

A paragraph then an unterminated fence:

```python
def f():
    return 1

## A heading that is actually inside the open fence?

| ragged | table
| - |
| one | two | three |

- item with [an unclosed link](http://x.example
