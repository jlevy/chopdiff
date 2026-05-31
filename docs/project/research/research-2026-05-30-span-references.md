# Research: Stable Span/Range References for Documents

**Date:** 2026-05-30

**Author:** research agent (synthesized), for unified-document-model decision 7

**Status:** Complete (survey with primary-source citations)

> Informs Open decision 7 (reference selectors) in
> [`plan-2026-05-29-unified-document-model.md`](../specs/active/plan-2026-05-29-unified-document-model.md).
> Question: how do other systems reference a span of a document so the reference stays
> usable for annotations as the document changes, and can our `Reference` align with
> Chrome URL Text Fragments?

## Headline Conclusions

- **Mature annotation systems store *multiple coordinated selectors*, not one.** The
  recurring pattern: a **text quote (exact and prefix/suffix) is canonical for persistence**
  (it survives restructuring and supports fuzzy re-matching), while **character offsets and
  structural paths are *hints*** that accelerate matching when the document is unchanged.
- **Chrome Text Fragments are exactly a quote+prefix/suffix selector** (no offsets, no
  fallback), so our quote selector can be made convertible to/from `#:~:text=…`, as a
  lossy projection (drops offsets; constrained to prose/word-boundaries/case-insensitive).
- **Pin the offset unit.** W3C never resolved code-points-vs-UTF-16 for its position
  selector; this silently breaks cross-language clients. Use **Unicode code points** (Python
  native) and provide a UTF-16 conversion for JS interop.

## 1. Chrome Text Fragments (`#:~:text=`)

Grammar (WICG): the `:~:` delimiter separates the *fragment directive* from a normal
fragment; directives are `&`-joined.

```
#[element-id]:~:text=[prefix-,]textStart[,textEnd][,-suffix]
```

- `prefix-` ends with `-`; `-suffix` begins with `-`, syntactically distinguishing context
  from the matched text. `-`, `,`, `&` in content must be percent-encoded.
- **Exact vs range:** `textStart` alone = exact match; `textStart,textEnd` = range from the
  first `textStart` to the next `textEnd`.
- **Matching:** case-insensitive (UTS10 base-character, accent-insensitive), word-boundary
  constrained ("range" matches "mountain range", not "orange"), whitespace-flexible, each
  of prefix/start/end/suffix must sit within one block-level element (the overall range may
  cross blocks).
- **No robustness:** if the text changed and no match is found, the fragment is **silently
  ignored** (navigate to top). No fuzzy matching, no position fallback. The spec itself
  notes text fragments are "less stable than document structure," meant for transient
  links (search/sharing), not permanent references.
- **Security/privacy:** user-activation required; restricted to a lone browsing context;
  the `:~:` directive is stripped from script-visible URLs; word-boundary rule prevents
  character-by-character brute forcing; highlight via UA-only `::target-text`;
  `Document-Policy: force-load-at-top` opts out. Supported in Chrome/Edge/Opera/Safari and
  Firefox (since 2024); feature-detect via `document.fragmentDirective`.

Examples: `#:~:text=hello%20world`; `#:~:text=The quick,lazy dog` (range);
`#:~:text=example-,this is,-the text` (prefix/suffix); `#:~:text=foo&text=bar` (two).

## 2. W3C Web Annotation Selectors

- **TextQuoteSelector:** `exact` and `prefix` and `suffix`; most robust to edits (context
  disambiguates; quote enables fuzzy re-match).
- **TextPositionSelector:** `start`/`end` integer offsets; fast but brittle (any earlier
  insert/delete invalidates). **Unit unresolved** in the spec (code points vs UTF-16);
  a real interop hazard.
- **RangeSelector:** start/end via XPath/CSS selectors; tied to DOM.
- **`refinedBy`** composition (e.g. a section FragmentSelector refined by a quote);
  **`oa:Choice`** (ordered alternatives, the fallback mechanism), `oa:Composite`,
  `oa:List`.

## 3. Hypothesis / Apache Annotator: Fuzzy Anchoring (the Battle-Tested Practice)

Stores **three selectors** per annotation (RangeSelector, TextPositionSelector, and
TextQuoteSelector) as an unordered set, and re-anchors in priority order:

1. RangeSelector (DOM XPath) and verify against the quote;
2. TextPositionSelector offsets and verify against the quote;
3. TextQuoteSelector fuzzy search **hinted** by the position;
4. TextQuoteSelector full-document fuzzy search.

Fuzzy matching uses Google **diff-match-patch** (Bitap) with a `hint` offset and a
`threshold`; `dom-anchor-text-quote` stores ~32 chars of prefix/suffix. On success, offsets
are recomputed. None of the three is "canonical," but the **quote is what makes recovery
possible**.

## 4. Offset-Based Identifiers (for Comparison)

- **RFC 5147** (`text/plain`): `#char=0,99`, `#line=10,19`, with optional `;length=` or
  `;md5=` **integrity checks** (detect change; no recovery). Character counting is
  encoding-aware (one char per multi-byte line ending; BOM excluded).
- **W3C Media Fragments:** `t=10,20`, `xywh=…`; pure offsets, no content-aware robustness.

## 5. Strategy Comparison

| Strategy | Robust to edits | Disambiguation | Compact | Standard |
|---|---|---|---|---|
| Offset span | Fragile (shifts) | Perfect if unchanged | Two ints | RFC 5147, TextPositionSelector |
| Text quote (exact) | Moderate | Poor if repeated | ~ selection | TextQuoteSelector |
| Quote and prefix/suffix | Good (fuzzy-able) | Good | exact and ~32×2 | TextQuoteSelector, Chrome TF |
| Structural path | Fragile to restructure | Good | Moderate | RangeSelector |
| Multi-selector ensemble | Best | Excellent | Large | Hypothesis, `oa:Choice` |

## 6. Offset-Unit Pitfall

`len("🤦🏼‍♂️")` = 5 (Python code points), 7 (JS UTF-16), 17 (Rust UTF-8 bytes). Declare the
unit. Use **Unicode code points**; provide `to_utf16_offsets()` for JS.

## 7. Recommended `Reference` Shape (for chopdiff)

A small type carrying **both** a syntactic span and a quoted span:

```python
class Reference:
    # Quoted span — canonical durable anchor (survives edits; Text-Fragment compatible)
    exact: str
    prefix: str = ""        # ~32-128 chars of context
    suffix: str = ""
    # Syntactic span — exact within the current source; a recomputable HINT, code points
    start: int | None = None
    end: int | None = None
    # (node_id is an in-memory handle only and is NEVER persisted)
```

- **Persist the quote as canonical; treat offsets as hints** recomputed on reload/reparse.
- **Re-anchor** like Hypothesis: fast offset path (verify against `exact`) → offset-hinted
  fuzzy → full-document fuzzy → update offsets.
- **Chrome Text Fragment** export from the quote is a **lossy projection** (drops offsets;
  emit only for prose where word-boundary and case-insensitive matching is acceptable;
  truncate prefix/suffix to ~50 chars for URL length).
- **Do not** store XPath/DOM selectors (environment-specific), the Text-Fragment URL
  itself (it's a rendering), or make `exact` optional.
- **Incompatibilities to bridge:** Text Fragments have no offsets (accept lossy); require
  word boundaries (no sub-word/code targets); match case-insensitively (store/flag when
  case matters and refuse emission); block-boundary rule is HTML-only (irrelevant for
  plain text).

## Sources

WICG: [spec](https://wicg.github.io/scroll-to-text-fragment/),
[README](https://github.com/WICG/scroll-to-text-fragment/blob/main/README.md),
[grammar](https://github.com/WICG/scroll-to-text-fragment/blob/main/index.bs),
[word-boundary #137](https://github.com/WICG/scroll-to-text-fragment/issues/137);
[MDN Text Fragments](https://github.com/mdn/content/blob/main/files/en-us/web/uri/reference/fragment/text_fragments/index.md).
W3C: [Annotation Model](https://www.w3.org/TR/annotation-model/),
[Vocabulary](https://www.w3.org/TR/annotation-vocab/),
[selectors #93](https://github.com/w3c/web-annotation/issues/93),
[unit #206](https://github.com/w3c/web-annotation/issues/206),
[code points vs UTF-16 #350](https://github.com/w3c/web-annotation/issues/350),
[Media Fragments](https://www.w3.org/TR/media-frags/).
Hypothesis: [fuzzy anchoring](https://web.hypothes.is/blog/fuzzy-anchoring/),
[dev list](https://groups.google.com/a/list.hypothes.is/g/dev/c/JCH8BRkp-cs),
[selector JSON](https://gist.github.com/BigBlueHat/e7bff9b2b7c7336edf010f11aa28eb87),
[dom-anchor-text-quote](https://github.com/tilgovi/dom-anchor-text-quote),
[Apache Annotator](https://github.com/apache/incubator-annotator),
[diff-match-patch](https://github.com/google/diff-match-patch).
Other: [RFC 5147](https://datatracker.ietf.org/doc/html/rfc5147),
[Readium annotations](https://github.com/readium/annotations),
[string length](https://hsivonen.fi/string-length/).
