# chopdiff: Open Work

Status as of 2026-07-14. The document model has been extracted to the separately
published [FlexDoc](https://github.com/jlevy/flexdoc) package; chopdiff now owns the
diff-filtering, div-chunking, and windowed-transform layer built on top of it.

## Tracking

Work is tracked with `tbd` in the git-native bead store:

```shell
tbd list --status open
tbd ready
tbd show <id>
```

The current full-library review is recorded in
[the July 2026 senior engineering review](docs/project/review/senior-engineering-review-chopdiff-2026-07.md).

## Chopdiff Backlog

- `chopdiff-rjlc`: add exact provider-keyed token counts as opt-in extras.
- `chopdiff-rz7x`: regenerate the README OpenAI example transcript; this requires an API
  key and is intentionally not part of automated validation.
- `chopdiff-rvw3`: replace the machine-local path in the committed Codex hook config.
- `chopdiff-d5y6`: fix shared `exclude-newer` guidance in tbd and simple-modern-uv.

Run `tbd list --status open` for the authoritative current list rather than duplicating
bead status in this file.

## FlexDoc-Owned Work

The older unified-document-model and document-model review specs under `docs/project/`
are historical records.
Their remaining snapshot, schema, query, `SpanRef`, synthetic-layer, and source-layout
work belongs in the FlexDoc repository, not in chopdiff.
Legacy beads under `chopdiff-cea0` remain useful as migration context until they are
transferred or closed.

The current FlexDoc design of record is
[flexdoc’s document model specification](https://github.com/jlevy/flexdoc/blob/main/docs/flexdoc-spec.md).
