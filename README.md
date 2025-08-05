# chopdiff

`chopdiff` is a small library of tools I've developed to make it easier to do fairly
complex transformations of text documents, especially for LLM applications, where you
want to manipulate text, Markdown, and HTML documents in a clean way.

Basically, it lets you parse, diff, and transform text at the level of words, sentences,
paragraphs, and "chunks" (paragraphs grouped in an HTML tag like a `<div>`). It aims to
have minimal dependencies.

Example use cases:

- **Filter diffs:** Diff two documents and only accept changes that fit a specific
  filter. For example, you can ask an LLM to edit a transcript, only inserting paragraph
  breaks but enforcing that the LLM can't do anything except insert whitespace.
  Or let it only edit punctuation, whitespace, and lemma variants of words.
  Or only change one word at a time (e.g. for spell checking).

- **Backfill information:** Match edited text against a previous version of a document
  (using a word-level LCS diff), then pull information from one doc to another.
  For example, say you have a timestamped transcript and an edited summary.
  You can then backfill timestamps of each paragraph into the edited text.

- **Windowed transforms:** Walk through a large document N paragraphs, N sentences, or N
  tokens at a time, processing the results with an LLM call, then "stitching together"
  the results, even if the chunks overlap.

## Installation

Drop the `extras` if you don't want the dependency on `simplemma` (it's about 70MB).

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
processing text, don't want a big dependency (like a full XML parser or NLP toolkit) and
also want full control over the original source format (since the original text is
exactly preserved, even whitespace—every sentence, paragraph, and token is mapped back
to the original text).

Note you may wish to also use this in conjunction with a Markdown parser or
auto-formatter, as it can make documents and diffs more readable.
You may wish to use [**flowmark**](https://github.com/jlevy/flowmark) for this alongside
chopdiff.

## Overview

More on what's here:

- The [`TextDoc`](src/chopdiff/docs/text_doc.py) class allows parsing of documents into
  sentences and paragraphs.
  By default, this uses only regex heuristics for speed and simplicity, but optionally
  you can use a sentence splitter of your choice, like Spacy.

- Tokenization using ["wordtoks"](src/chopdiff/docs/wordtoks.py) that lets you measure
  size and extract subdocs via arbitrary units of paragraphs, sentences, words, chars,
  or tokens, with mappings between each, e.g. mapping sentence 3 of paragraph 2 to its
  corresponding character or token offset.
  The tokenization is simple but flexible, including whitespace (sentence or paragraph
  breaks) and HTML tags as single tokens.
  It also maintains exact offsets of each token in the original document text.

- [Word-level diffs](src/chopdiff/docs/token_diffs.py) that don't work at the line level
  (like usual git-style diffs) but rather treat whitespace, sentence, and paragraph
  breaks as indidivdual tokens.
  It performs LCS-style token-based diffs with
  [cydifflib](https://github.com/rapidfuzz/cydifflib), which is significantly faster
  than Python's built-in [difflib](https://docs.python.org/3.10/library/difflib.html).

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

- Lightweight "chunking" of documents by wrapping paragraphs in `<div>`s to indicate
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

- **Section-based document parsing** with [`SectionDoc`](src/chopdiff/sections/section_doc.py)
  that creates a hierarchical tree structure of Markdown sections. Each section node
  contains the header and all content until the next section at the same or higher level,
  allowing easy iteration over document structure at any heading level.

- **Unified document interface** through [`FlexDoc`](src/chopdiff/flex/flex_doc.py) that
  provides lazy, thread-safe access to all three document views (tokens, divs, sections).
  This allows you to parse once and work with the document through whichever lens is most
  appropriate for your task, with automatic cross-view navigation.

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
   sections based on headers. Best for navigating document structure and extracting
   content by heading.

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

This is an example of diff filtering (see
[insert_para_breaks.py](examples/insert_para_breaks.py) for full code):

```python
import argparse
import logging
from textwrap import dedent

import openai
from flowmark import fill_text

from chopdiff.docs import TextDoc
from chopdiff.transforms import changes_whitespace, filtered_transform, WINDOW_2K_WORDTOKS

def llm_insert_para_breaks(input_text: str) -> str:
    """
    Call OpenAI to insert paragraph breaks on a chunk of text.
    Note there is no guarantee this might not make other
    non-whitespace changes.
    """
    client = openai.OpenAI()

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a careful and precise editor."},
            {
                "role": "user",
                "content": dedent(
                    f"""
                    Break the following text into paragraphs.

                    Original text:

                    {input_text}

                    Formatted text:
                    """
                ),
            },
        ],
        temperature=0.0,
    )

    return response.choices[0].message.content or ""


def insert_paragraph_breaks(text: str) -> str:
    # Create a TextDoc from the input text
    doc = TextDoc.from_text(text)
    print(f"Input document: {doc.size_summary()}")

    # Define the transformation function.
    # Note in this case we run the LLM on strings, but you could also work directly
    # on the TextDoc if appropriate.
    def transform(doc: TextDoc) -> TextDoc:
        return TextDoc.from_text(llm_insert_para_breaks(doc.reassemble()))

    # Apply the transformation with windowing and filtering.
    #
    # This will walk along the document in approximately 2K "wordtok" chunks
    # (~1000 words) and apply the transformation to each chunk. Chunks can
    # slightly overlap to make this more robust.
    #
    # The change on each chunk will then be filtered to only include whitespace
    # changes.
    #
    # Finally each change will be "stitched back" to form the original document,
    # by looking for the right alignment of words between the original and the
    # transformed chunk.
    #
    # (Turn on logging to see these details.)
    result_doc = filtered_transform(
        doc, transform, windowing=WINDOW_2K_WORDTOKS, diff_filter=changes_whitespace
    )

    print(f"Output document: {result_doc.size_summary()}")

    # Return the transformed text
    return result_doc.reassemble()
```

Running this shows how it works.
Note GPT-4o-mini makes a typo correction, even though it wasn't requested.
But the diff filter enforces that the output exactly contains only paragraph breaks:

```
$ uv run examples/insert_para_breaks.py examples/gettysberg.txt 

--- Original --------------------------------------------------------------

four score and seven years ago our fathers brought forth on this continent, a new
nation, conceived in Liberty, and dedicated to the proposition that all men are created
equal. Now we are engaged in a great civil war, testing whether that nation, or any
nation so conceived and so dedicated, can long endure. We are met on a great
battle-field of that war. We have come to dedicate a portion of that field, as a final
resting place for those who here gave their lives that that nation might live. It is
altogether fitting and proper that we should do this. But, in a larger sense, we can not
dedicate—we can not consecrate—we can not hallow—this ground. The brave men, living and
dead, who struggled here, have consecrated it, far above our poor power to add or
detract. The world will little note, nor long remember what we say here, but it can
never forget what they did here. It is for us the living, rather, to be dedicated here
to the unfinished work which they who fought here have thus far so nobly advanced. It is
rather for us to be here dedicated to the great task remaining before us—that from these
honored dead we take increased devotion to that cause for which they gave the last full
measure of devotion—that we here highly resolve that these dead shall not have died in
vain—that this nation, under God, shall have a new birth of freedom—and that government
of the people, by the people, for the people, shall not perish from the earth.

Input document: 1466 bytes (17 lines, 1 paragraphs, 10 sentences, 264 words, 311 tiktokens)

INFO:chopdiff.docs.sliding_transforms:Sliding word transform: Begin on doc: total 575 wordtoks, 1466 bytes, 1 windows, windowing size=2048, shift=1792, min_overlap=8 wordtoks
INFO:chopdiff.docs.sliding_transforms:Sliding word transform window 1/1 (575 wordtoks, 1466 bytes), at 0 wordtoks so far
INFO:httpx:HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
INFO:chopdiff.docs.sliding_transforms:Accepted transform changes:
    TextDiff: add/remove +3/-3 out of 575 total:
    at pos    0 keep    1 toks:   ⎪four⎪
    at pos    1 keep   62 toks:   ⎪ score and seven years ago our fathers brought forth on this continent, a new nation, conceived in Liberty, and dedicated to the proposition that all men are created equal.⎪
    at pos   63 repl    1 toks: - ⎪<-SENT-BR->⎪
                repl    1 toks: + ⎪<-PARA-BR->⎪
    at pos   64 keep  153 toks:   ⎪Now we are engaged in a great civil war, testing whether that nation, or any nation so conceived and so dedicated, can long endure.<-SENT-BR->We are met on a great battle-field of that war.<-SENT-BR->We have come to dedicate a portion of that field, as a final resting place for those who here gave their lives that that nation might live.<-SENT-BR->It is altogether fitting and proper that we should do this.⎪
    at pos  217 repl    1 toks: - ⎪<-SENT-BR->⎪
                repl    1 toks: + ⎪<-PARA-BR->⎪
    at pos  218 keep  132 toks:   ⎪But, in a larger sense, we can not dedicate—we can not consecrate—we can not hallow—this ground.<-SENT-BR->The brave men, living and dead, who struggled here, have consecrated it, far above our poor power to add or detract.<-SENT-BR->The world will little note, nor long remember what we say here, but it can never forget what they did here.⎪
    at pos  350 repl    1 toks: - ⎪<-SENT-BR->⎪
                repl    1 toks: + ⎪<-PARA-BR->⎪
    at pos  351 keep  224 toks:   ⎪It is for us the living, rather, to be dedicated here to the unfinished work which they who fought here have thus far so nobly advanced.<-SENT-BR->It is rather for us to be here dedicated to the great task remaining before us—that from these honored dead we take increased devotion to that cause for which they gave the last full measure of devotion—that we here highly resolve that these dead shall not have died in vain—that this nation, under God, shall have a new birth of freedom—and that government of the people, by the people, for the people, shall not perish from the earth.⎪
INFO:chopdiff.docs.sliding_transforms:Filtering extraneous changes:
    TextDiff: add/remove +1/-1 out of 575 total:
    at pos    0 repl    1 toks: - ⎪four⎪
                repl    1 toks: + ⎪Four⎪
INFO:chopdiff.docs.sliding_transforms:Word token changes:
    Accepted: add/remove +3/-3 out of 575 total
    Rejected: add/remove +1/-1 out of 575 total
INFO:chopdiff.docs.sliding_transforms:Sliding word transform: Done, output total 575 wordtoks

Output document: 1469 bytes (7 lines, 4 paragraphs, 10 sentences, 264 words, 311 tiktokens)

--- With Paragraph Breaks -------------------------------------------------

four score and seven years ago our fathers brought forth on this continent, a new
nation, conceived in Liberty, and dedicated to the proposition that all men are created
equal.

Now we are engaged in a great civil war, testing whether that nation, or any nation so
conceived and so dedicated, can long endure. We are met on a great battle-field of that
war. We have come to dedicate a portion of that field, as a final resting place for
those who here gave their lives that that nation might live. It is altogether fitting
and proper that we should do this.

But, in a larger sense, we can not dedicate—we can not consecrate—we can not hallow—this
ground. The brave men, living and dead, who struggled here, have consecrated it, far
above our poor power to add or detract. The world will little note, nor long remember
what we say here, but it can never forget what they did here.

It is for us the living, rather, to be dedicated here to the unfinished work which they
who fought here have thus far so nobly advanced. It is rather for us to be here
dedicated to the great task remaining before us—that from these honored dead we take
increased devotion to that cause for which they gave the last full measure of
devotion—that we here highly resolve that these dead shall not have died in vain—that
this nation, under God, shall have a new birth of freedom—and that government of the
people, by the people, for the people, shall not perish from the earth.
$
```

### Backfilling Timestamps

Here is an example of backfilling data from one text file to another similar but not
identical text file (see [backfill_timestamps.py](examples/backfill_timestamps.py) for
code). As you can see, the text is aligned by mapping the words and then the timestamps
inserted at the end of each paragraph based on the first sentence of each paragraph:

```
$ uv run examples/backfill_timestamps.py 

--- Source text (with timestamps) -----------------------------------------


<span data-timestamp="0.0">Welcome to this um ... video about Python programming.</span>
<span data-timestamp="15.5">First, we'll talk about variables. Variables are containers for storing data values.</span>
<span data-timestamp="25.2">Then let's look at functions. Functions help us organize and reuse code.</span>


--- Target text (without timestamps) --------------------------------------


## Introduction

Welcome to this video about Python programming.

First, we'll talk about variables. Next, let's look at functions. Functions help us organize and reuse code.


--- Diff ------------------------------------------------------------------

TextDiff: add/remove +9/-32 out of 87 total:
at pos    0 keep    1 toks:   ⎪<-BOF->⎪
at pos    1 add     2 toks: + ⎪##⎪
at pos    1 keep    1 toks:   ⎪ ⎪
at pos    2 repl    1 toks: - ⎪<span data-timestamp="0.0">⎪
            repl    2 toks: + ⎪Introduction<-PARA-BR->⎪
at pos    3 keep    5 toks:   ⎪Welcome to this⎪
at pos    8 del     6 toks: - ⎪ um ...⎪
at pos   14 keep    9 toks:   ⎪ video about Python programming.⎪
at pos   23 repl    3 toks: - ⎪</span> <span data-timestamp="15.5">⎪
            repl    1 toks: + ⎪<-PARA-BR->⎪
at pos   26 keep   13 toks:   ⎪First, we'll talk about variables.⎪
at pos   39 repl   19 toks: - ⎪ Variables are containers for storing data values.</span> <span data-timestamp="25.2">Then⎪
            repl    3 toks: + ⎪<-SENT-BR->Next,⎪
at pos   58 keep   11 toks:   ⎪ let's look at functions.⎪
at pos   69 repl    1 toks: - ⎪ ⎪
            repl    1 toks: + ⎪<-SENT-BR->⎪
at pos   70 keep   14 toks:   ⎪Functions help us organize and reuse code.⎪
at pos   84 del     2 toks: - ⎪</span> ⎪
at pos   86 keep    1 toks:   ⎪<-EOF->⎪

--- Token mapping ---------------------------------------------------------

0 ⎪<-BOF->⎪ -> 0 ⎪<-BOF->⎪
1 ⎪#⎪ -> 0 ⎪<-BOF->⎪
2 ⎪#⎪ -> 0 ⎪<-BOF->⎪
3 ⎪ ⎪ -> 1 ⎪ ⎪
4 ⎪Introduction⎪ -> 2 ⎪<span data-timestamp="0.0">⎪
5 ⎪<-PARA-BR->⎪ -> 2 ⎪<span data-timestamp="0.0">⎪
6 ⎪Welcome⎪ -> 3 ⎪Welcome⎪
7 ⎪ ⎪ -> 4 ⎪ ⎪
8 ⎪to⎪ -> 5 ⎪to⎪
9 ⎪ ⎪ -> 6 ⎪ ⎪
10 ⎪this⎪ -> 7 ⎪this⎪
11 ⎪ ⎪ -> 14 ⎪ ⎪
12 ⎪video⎪ -> 15 ⎪video⎪
13 ⎪ ⎪ -> 16 ⎪ ⎪
14 ⎪about⎪ -> 17 ⎪about⎪
15 ⎪ ⎪ -> 18 ⎪ ⎪
16 ⎪Python⎪ -> 19 ⎪Python⎪
17 ⎪ ⎪ -> 20 ⎪ ⎪
18 ⎪programming⎪ -> 21 ⎪programming⎪
19 ⎪.⎪ -> 22 ⎪.⎪
20 ⎪<-PARA-BR->⎪ -> 25 ⎪<span data-timestamp="15.5">⎪
21 ⎪First⎪ -> 26 ⎪First⎪
22 ⎪,⎪ -> 27 ⎪,⎪
23 ⎪ ⎪ -> 28 ⎪ ⎪
24 ⎪we⎪ -> 29 ⎪we⎪
25 ⎪'⎪ -> 30 ⎪'⎪
26 ⎪ll⎪ -> 31 ⎪ll⎪
27 ⎪ ⎪ -> 32 ⎪ ⎪
28 ⎪talk⎪ -> 33 ⎪talk⎪
29 ⎪ ⎪ -> 34 ⎪ ⎪
30 ⎪about⎪ -> 35 ⎪about⎪
31 ⎪ ⎪ -> 36 ⎪ ⎪
32 ⎪variables⎪ -> 37 ⎪variables⎪
33 ⎪.⎪ -> 38 ⎪.⎪
34 ⎪<-SENT-BR->⎪ -> 57 ⎪Then⎪
35 ⎪Next⎪ -> 57 ⎪Then⎪
36 ⎪,⎪ -> 57 ⎪Then⎪
37 ⎪ ⎪ -> 58 ⎪ ⎪
38 ⎪let⎪ -> 59 ⎪let⎪
39 ⎪'⎪ -> 60 ⎪'⎪
40 ⎪s⎪ -> 61 ⎪s⎪
41 ⎪ ⎪ -> 62 ⎪ ⎪
42 ⎪look⎪ -> 63 ⎪look⎪
43 ⎪ ⎪ -> 64 ⎪ ⎪
44 ⎪at⎪ -> 65 ⎪at⎪
45 ⎪ ⎪ -> 66 ⎪ ⎪
46 ⎪functions⎪ -> 67 ⎪functions⎪
47 ⎪.⎪ -> 68 ⎪.⎪
48 ⎪<-SENT-BR->⎪ -> 69 ⎪ ⎪
49 ⎪Functions⎪ -> 70 ⎪Functions⎪
50 ⎪ ⎪ -> 71 ⎪ ⎪
51 ⎪help⎪ -> 72 ⎪help⎪
52 ⎪ ⎪ -> 73 ⎪ ⎪
53 ⎪us⎪ -> 74 ⎪us⎪
54 ⎪ ⎪ -> 75 ⎪ ⎪
55 ⎪organize⎪ -> 76 ⎪organize⎪
56 ⎪ ⎪ -> 77 ⎪ ⎪
57 ⎪and⎪ -> 78 ⎪and⎪
58 ⎪ ⎪ -> 79 ⎪ ⎪
59 ⎪reuse⎪ -> 80 ⎪reuse⎪
60 ⎪ ⎪ -> 81 ⎪ ⎪
61 ⎪code⎪ -> 82 ⎪code⎪
62 ⎪.⎪ -> 83 ⎪.⎪
63 ⎪<-EOF->⎪ -> 86 ⎪<-EOF->⎪
>> Seeking back tok 1 (<-PARA-BR->) to para start tok 1 (#), map back to source tok 0 (<-BOF->)
>> Failed to extract timestamp at doc token 1 (<-PARA-BR->) -> source token 0 (<-BOF->): ¶0,S0
>> Seeking back tok 6 (<-PARA-BR->) to para start tok 6 (Welcome), map back to source tok 3 (Welcome)
>> Adding timestamp to sentence: 'Welcome to this video about Python programming.'
>> Seeking back tok 21 (<-EOF->) to para start tok 21 (First), map back to source tok 26 (First)
>> Adding timestamp to sentence: 'Functions help us organize and reuse code.'

--- Result (with backfilled timestamps) -----------------------------------

## Introduction

Welcome to this video about Python programming. <span class="timestamp">⏱️00:00</span> 

First, we'll talk about variables. Next, let's look at functions. Functions help us organize and reuse code. <span class="timestamp">⏱️00:15</span> 
$
```

### Document Structure Analysis

The [analyze_doc.py](examples/analyze_doc.py) example shows how to walk through all sections of a document and gather detailed statistics:

```
$ uv run examples/analyze_doc.py examples/sample_doc.md

📊 Analysis of: sample_doc.md

📄 Document Analysis
   Total: 355 words • 1.4m read time

└── 📖 [Document Root]
       39 para • 42 sent • 355 words • 1.4m
    ├── 📂 Technical Documentation Guide
    │      36 para • 38 sent • 318 words • 1.3m
    │   ├── 📂 Getting Started
    │   │      9 para • 10 sent • 78 words • 18s
    │   │   ├── 📑 Prerequisites
    │   │   │      3 para • 3 sent • 33 words • 7s
    │   │   └── 📑 Installation
    │   │          4 para • 4 sent • 29 words • 6s
    │   ├── 📂 Core Concepts
    │   │      9 para • 9 sent • 78 words • 18s
    │   │   ├── 📑 Document Structure
    │   │   │      3 para • 3 sent • 31 words • 7s
    │   │   └── 📑 Style Guidelines
    │   │          4 para • 4 sent • 35 words • 8s
    │   ├── 📂 Advanced Features
    │   │      8 para • 8 sent • 67 words • 16s
    │   │   ├── 📑 Templates
    │   │   │      3 para • 3 sent • 28 words • 6s
    │   │   └── 📑 Automation
    │   │          3 para • 3 sent • 28 words • 6s
    │   └── 📂 Best Practices
    │          8 para • 8 sent • 72 words • 17s
    │       ├── 📑 Review Process
    │       │      3 para • 3 sent • 29 words • 6s
    │       └── 📑 Maintenance
    │              3 para • 3 sent • 33 words • 7s
    └── 📑 Conclusion
           3 para • 4 sent • 37 words • 8s
```

The analyzer also supports a flat table format:

```
$ uv run examples/analyze_doc.py examples/sample_doc.md --flat

📊 Analysis of: sample_doc.md

Level  Title                                    Paragraphs  Sentences    Words  Read Time
----------------------------------------------------------------------------------------------
1      Technical Documentation Guide                    36         38      318       1.3m
2        Getting Started                                 9         10       78        18s
3          Prerequisites                                 3          3       33         7s
3          Installation                                  4          4       29         6s
2        Core Concepts                                   9          9       78        18s
3          Document Structure                            3          3       31         7s
3          Style Guidelines                              4          4       35         8s
2        Advanced Features                               8          8       67        16s
3          Templates                                     3          3       28         6s
3          Automation                                    3          3       28         6s
2        Best Practices                                  8          8       72        17s
3          Review Process                                3          3       29         6s
3          Maintenance                                   3          3       33         7s
1      Conclusion                                        3          4       37         8s
----------------------------------------------------------------------------------------------
TOTAL                                                   99        103      896       3.6m
```

Key features:
- Hierarchical tree view of document structure
- Per-section statistics (paragraphs, sentences, words)
- Estimated reading time based on configurable words-per-minute
- Support for both tree and flat table output formats
- Can read from files or stdin

This demonstrates using FlexDoc to:
- Navigate the section hierarchy with `section_doc.iter_sections()`
- Get per-section TextDoc instances with `get_section_text_doc()`
- Calculate detailed statistics using `TextDoc.size()` with different units
- Access section relationships (parent, children, siblings)

### Section Navigation

Here's an example of using SectionDoc to navigate a Markdown document by its section
structure:

```python
from chopdiff import SectionDoc

# Parse a markdown document
text = """
# Introduction

Welcome to our guide.

## Getting Started

Here's how to begin.

### Installation

First, install the package.

## Advanced Topics

Let's dive deeper.

# Conclusion

Thanks for reading!
"""

# Create a SectionDoc
doc = SectionDoc(text)

# Iterate over all sections
for section in doc.iter_sections():
    print(f"Level {section.level}: {section.title}")
    
# Get sections at a specific level
h2_sections = doc.get_sections_at_level(2)
for section in h2_sections:
    print(f"## {section.title}")
    print(section.body_content[:50] + "...")
    
# Find a section by title
for section in doc.iter_sections():
    if section.title == "Getting Started":
        # Navigate the hierarchy
        print(f"Parent: {section.parent.title if section.parent else 'None'}")
        print(f"Children: {[child.title for child in section.children]}")
        print(f"Path: {section.get_path()}")
        break

# Or find by path components
intro_section = doc.find_section_by_path("Chapter 1", "Introduction")
```

### Cross-View Navigation with FlexDoc

FlexDoc enables working with the same document through different lenses:

```python
from chopdiff import FlexDoc

# Create a FlexDoc
doc = FlexDoc(markdown_text)

# Find which section contains a specific token
token_idx = 42  # Some token of interest
section = doc.find_section_containing_token(token_idx)
print(f"Token {token_idx} is in section: {section.title}")

# Get all tokens within a section
section = doc.section_doc.find_section_by_title("Introduction")
start_token, end_token = doc.section_to_token_range(section)
tokens = doc.text_doc.tokens()[start_token:end_token]

# Smart chunking that respects section boundaries
chunks = doc.chunk_by_sections(max_chunk_size=1000, respect_levels={1, 2})
for i, chunk in enumerate(chunks):
    print(f"Chunk {i}: {chunk.start_offset}-{chunk.end_offset}")
    print(f"Sections: {[s.title for s in chunk.sections]}")
```

* * *

## Project Docs

For how to install uv and Python, see [installation.md](installation.md).

For development workflows, see [development.md](development.md).

For instructions on publishing to PyPI, see [publishing.md](publishing.md).

* * *

*This project was built from
[simple-modern-uv](https://github.com/jlevy/simple-modern-uv).*
