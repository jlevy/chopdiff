# chopdiff

`chopdiff` is a small library of tools I’ve developed to make it easier to do fairly
complex transformations of text documents, especially for LLM applications, where you
want to manipulate text, Markdown, and HTML documents in a clean way.

Basically, it lets you parse, diff, and transform text at the level of words, sentences,
paragraphs, and “chunks” (paragraphs grouped in an HTML tag like a `<div>`). It aims to
have minimal dependencies.

Example use cases:

- **Filter diffs:** Diff two documents and only accept changes that fit a specific
  filter. For example, you can ask an LLM to edit a transcript, only inserting paragraph
  breaks but enforcing that the LLM can’t do anything except insert whitespace.
  Or let it only edit punctuation, whitespace, and lemma variants of words.
  Or only change one word at a time (e.g. for spell checking).

- **Backfill information:** Match edited text against a previous version of a document
  (using a word-level LCS diff), then pull information from one doc to another.
  For example, say you have a timestamped transcript and an edited summary.
  You can then backfill timestamps of each paragraph into the edited text.

- **Windowed transforms:** Walk through a large document N paragraphs, N sentences, or N
  tokens at a time, processing the results with an LLM call, then “stitching together”
  the results, even if the chunks overlap.

## Installation

Drop the `extras` if you don’t want the dependency on `simplemma` (it’s about 70MB).

Full deps:

```shell
# Using uv (recommended)
uv add chopdiff[extras]
# Using poetry
poetry add chopdiff -E extras
# Using pip
pip install chopdiff[extras]
```

Basic deps:

```shell
# Using uv (recommended)
uv add chopdiff
# Using poetry
poetry add chopdiff
# Using pip
pip install chopdiff
```

## Comparison to Alternatives

There are full-blown Markdown and HTML parsing libs (such as
[Marko](https://github.com/frostming/marko) and
[BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)) but these tend
to focus specifically on fully parsing documents as parse trees.
On the other end of the spectrum, there are NLP libraries (like
[spaCy](https://github.com/explosion/spaCy)) that do more expensive, full language
parsing and sentence segmentation.

This is a lightweight alternative to those approaches when you are just focusing on
processing text, don’t want a big dependency (like a full XML parser or NLP toolkit) and
also want full control over the original source format (since the original text is
exactly preserved, even whitespace—every sentence, paragraph, and token is mapped back
to the original text).

Note you may wish to also use this in conjunction with a Markdown parser or
auto-formatter, as it can make documents and diffs more readable.
You may wish to use [**flowmark**](https://github.com/jlevy/flowmark) for this alongside
chopdiff.

## Overview

More on what’s here:

- The [`TextDoc`](src/chopdiff/docs/text_doc.py) class allows parsing of documents into
  sentences and paragraphs.
  By default, this uses only regex heuristics for speed and simplicity, but optionally
  you can use a sentence splitter of your choice, like Spacy.

- Tokenization using [“wordtoks”](src/chopdiff/docs/wordtoks.py) that lets you measure
  size and extract subdocs via arbitrary units of paragraphs, sentences, words, chars,
  or tokens, with mappings between each, e.g. mapping sentence 3 of paragraph 2 to its
  corresponding character or token offset.
  The tokenization is simple but flexible, including whitespace (sentence or paragraph
  breaks) and HTML tags as single tokens.
  It also maintains exact offsets of each token in the original document text.

- [Word-level diffs](src/chopdiff/docs/token_diffs.py) that don’t work at the line level
  (like usual git-style diffs) but rather treat whitespace, sentence, and paragraph
  breaks as indidivdual tokens.
  It performs LCS-style token-based diffs with
  [cydifflib](https://github.com/rapidfuzz/cydifflib), which is significantly faster
  than Python’s built-in [difflib](https://docs.python.org/3.10/library/difflib.html).

- [Filtering](src/chopdiff/transforms/diff_filters.py) of these text-based diffs based
  on specific criteria.
  For example, only adding or removing words, only changing whitespace, only changing
  word lemmas, etc.

- The [`TokenMapping`](src/chopdiff/docs/token_mapping.py) class offers word-based
  mappings between docs, allowing you to find what part of a doc corresponds with
  another doc as a token index mappings.

- [`search_tokens`](src/chopdiff/docs/search_tokens.py) gives simple way to search back
  and forth among the tokens of a document.
  That is, you can seek forward or backward to any desired token (HTML tag, word,
  punctuation, or sentence or paragraph break matching a predicate) from any given
  position.

- Lightweight “chunking” of documents by wrapping paragraphs in `<div>`s to indicate
  chunks. [`TextNode`](src/chopdiff/divs/text_node.py) offers simple recursive parsing
  around `<div>` tags.
  This is not a general HTML parser, but rather a way to chunk documents into named
  pieces. Unlike more complex parsers, the `TextNode` parser operates on character
  offsets, so maintains the original document exactly and allows exact reassembly if
  desired.

- The word-based token mapping allows
  [transformation](src/chopdiff/transforms/sliding_transforms.py) of documents via
  sliding windows, transforming text (e.g. via an LLM call one window at a time, with
  overlapping windows), then re-stitching the results back together with best
  alignments.

- **Section-based document parsing** with
  [`SectionDoc`](src/chopdiff/sections/section_doc.py) that creates a hierarchical tree
  structure of Markdown sections.
  Each section node contains the header and all content until the next section at the
  same or higher level, allowing easy iteration over document structure at any heading
  level.

- **Unified document interface** through [`FlexDoc`](src/chopdiff/flex/flex_doc.py) that
  provides lazy, thread-safe access to all three document views (tokens, divs,
  sections). This allows you to parse once and work with the document through whichever
  lens is most appropriate for your task, with automatic cross-view navigation.

All this is done very simply in memory, and with only regex or basic Markdown parsing to
keep things simple and with few dependencies.

`chopdiff` has no heavier dependencies like full XML or BeautifulSoup parsing or Spacy
or nltk for sentence splitting (though you can use these as custom sentence parsers if
you like).

## Document Views

`chopdiff` provides three complementary ways to view and process documents:

1. **Token View (`TextDoc`)**: Parse documents into tokens, sentences, and paragraphs.
   Best for word-level operations, diffs, and transformations.

2. **Div View (`TextNode`)**: Parse documents by HTML `<div>` structure for chunking.
   Best for documents with explicit structural divisions.

3. **Section View (`SectionDoc`)**: Parse Markdown documents into a hierarchical tree of
   sections based on headers.
   Best for navigating document structure and extracting content by heading.

The **`FlexDoc`** class provides unified access to all three views with lazy loading and
thread safety:

```python
from chopdiff import FlexDoc

# Create a FlexDoc from markdown text
doc = FlexDoc(markdown_text)

# Access any view as needed - parsing happens on first access
paras = doc.text_doc.paragraphs  # Token view - paragraphs
sections = list(doc.section_doc.iter_sections())  # Section view - all sections
has_divs = any(child.tag_name == "div" for child in doc.text_node.children)  # Div view

# Navigate between views using character offsets
coords = doc.offset_to_coordinates(100)  # Get all coordinate systems at offset 100
section = coords["section"]  # SectionNode containing the offset
paragraph_idx = coords["paragraph"]  # Paragraph index
sentence = coords["sentence"]  # SentIndex (paragraph, sentence) tuple

# Get tokens for a specific section
section = doc.section_doc.get_section_at_offset(100)
tokens = doc.get_section_tokens(section)

# Section-aware chunking
from chopdiff import TextUnit
chunks = doc.chunk_by_sections(
    target_size=2000,  # Target size for each chunk
    unit=TextUnit.words,  # Unit for measuring size (words, chars, etc.)
    respect_levels=[1, 2]  # Keep h1 and h2 sections intact
)
```

### Thread Safety with FlexDoc

FlexDoc is thread-safe and all views are lazily loaded:

```python
from concurrent.futures import ThreadPoolExecutor
from chopdiff import FlexDoc

doc = FlexDoc(large_document)

# Views are loaded only when accessed
def process_section(section):
    # This is thread-safe - each thread can access views
    tokens = doc.get_section_tokens(section)
    return len(tokens)

# Process sections in parallel
with ThreadPoolExecutor(max_workers=4) as executor:
    sections = list(doc.section_doc.iter_sections())
    token_counts = list(executor.map(process_section, sections))
```

## Examples

Here are a couple examples to illustrate how all this works, with verbose logging to see
the output. See the [examples/](examples/) directory.

### Inserting Paragraph Breaks

This example demonstrates using an LLM to identify and insert paragraph boundaries in
text that lacks proper formatting.
The script uses OpenAI’s API to mark paragraph break locations, then uses `chopdiff`'s
filtering capabilities to transform these markers into actual paragraph breaks.

```bash
$ uv run examples/insert_para_breaks.py examples/gettysberg.txt
```

See [examples/insert_para_breaks.py](examples/insert_para_breaks.py) for the full
implementation.

### Backfilling Timestamps

This example shows how to align content across multiple versions of a transcript,
backfilling timestamps from a source document to a target document that’s missing them.
This is useful for synchronizing edited transcripts with their original timestamped
versions.

```bash
$ uv run examples/backfill_timestamps.py
```

See [examples/backfill_timestamps.py](examples/backfill_timestamps.py) for the full
implementation.

### Document Structure Analysis

Analyze the structure of a Markdown document with detailed statistics per section.
This example walks through all sections hierarchically, calculating word counts,
sentence counts, paragraph counts, and estimated reading times for each section.

```bash
# Tree view (default)
$ uv run examples/analyze_doc.py examples/sample_doc.md

# Flat table view
$ uv run examples/analyze_doc.py examples/sample_doc.md --flat
```

See [examples/analyze_doc.py](examples/analyze_doc.py) for the full implementation.

### Inserting Document Statistics

The `insert_size_info.py` example demonstrates how to enhance Markdown documents by
automatically inserting size and reading time information after section headers.

This illustrates inserting “chunks” of content into HTML in a structural way for each
section.

```bash
# Insert size info divs after headers (levels 1-3 by default)
$ uv run examples/insert_size_info.py README.md > README_with_stats.md

# Customize header levels and reading speed
$ uv run examples/insert_size_info.py doc.md --min-level 2 --max-level 4 --wpm 200
```

The script inserts HTML `<div>` elements with statistics like word count, character
count, reading time, and subsection count:

```markdown
## Section Title

<div class="size-info" data-words="150" data-chars="900">150 words • 10 sentences • 3 paragraphs • 2 subsections • ~45s to read</div>

Section content continues here...
```

See [examples/insert_size_info.py](examples/insert_size_info.py) for the full
implementation.

### Section Navigation

Use `SectionDoc` to navigate Markdown documents by their hierarchical section structure.
You can iterate sections, find sections by title or path, and navigate the parent-child
relationships between sections:

```python
from chopdiff import SectionDoc

doc = SectionDoc(markdown_text)

# Iterate all sections
for section in doc.iter_sections():
    print(f"Level {section.level}: {section.title}")

# Find sections at a specific level
h2_sections = doc.get_sections_at_level(2)

# Navigate hierarchy
section = doc.find_section_by_title("Getting Started")
print(f"Parent: {section.parent.title if section.parent else 'None'}")
print(f"Children: {[child.title for child in section.children]}")
```

### Cross-View Navigation with FlexDoc

`FlexDoc` provides unified access to all three document views (tokens, divs, sections)
with automatic cross-view navigation:

```python
from chopdiff import FlexDoc, TextUnit

doc = FlexDoc(markdown_text)

# Navigate between views using character offsets
coords = doc.offset_to_coordinates(100)
section = coords["section"]  # Section containing offset 100
paragraph_idx = coords["paragraph"]  # Paragraph index at offset 100

# Get tokens for a specific section
section = doc.section_doc.find_section_by_title("Introduction")
tokens = doc.get_section_tokens(section)

# Smart chunking that respects section boundaries
chunks = doc.chunk_by_sections(
    target_size=2000,
    unit=TextUnit.words,
    respect_levels=[1, 2]  # Keep h1/h2 sections intact
)
```

* * *

## Project Docs

For how to install uv and Python, see [installation.md](installation.md).

For development workflows, see [development.md](development.md).

For instructions on publishing to PyPI, see [publishing.md](publishing.md).

* * *

*This project was built from
[simple-modern-uv](https://github.com/jlevy/simple-modern-uv).*
