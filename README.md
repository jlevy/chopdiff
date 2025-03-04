# chopdiff

`chopdiff` is a small library of tools I've developed for use especially with LLMs that
let you handle Markdown and text document edits.

It aims to have minimal dependencies and be useful for various LLM applications where
you want to manipulate text, Markdown, and lightweight (not fully parsed) HTML
documents.

Example use cases:

- **Filtered diffs:** Diff two documents, and only accept changes that fit a specific
  filter. For example, ask an LLM to edit a transcript, only inserting paragraph breaks
  but enforcing that the LLM can't do anything except insert whitespace.

- **Backfill information:** Match edited text against a timestamped transcript, then
  backfill the timestamps into the edited text.

- **Windowed transforms:** Walk through a document N paragraphs, N sentences, or N
  tokens at a time, processing the results with an LLM call, then recombining the
  results.

More on what's here:

- The [`TextDoc`](src/chopdiff/docs/text_doc.py) class allows parsing of documents into
  sentences and paragraphs.
  By default, this uses only regex heuristics for speed and simplicity, but optionally
  you can use a sentence splitter of your choice, like Spacy.

- Word-based tokenization (using [wordtoks](src/chopdiff/docs/wordtoks.py) that is lets
  you measure size and extract subdocs via arbitrary units of paragraphs, sentences,
  words, chars, or tokens, with mappings between each, e.g. mapping sentence 3 of
  paragraph 2 to its corresponding character or token offset.
  The tokenization is simple but HTML-aware so words, punctuation, and HTML are all
  single tokens. It also maintains exact offsets of each token with the original document
  text.

- [Word-level diffs](src/chopdiff/docs/token_diffs.py) that don't work at the line level
  (like usual git diffs) but rather treat whitespace, sentence, and paragraph breaks as
  indidivdual tokens. You can perform LCS-style token-based diffs with
  [cydifflib](https://pypi.org/project/cydifflib/), which is quite fast—significantly
  faster than Python's built-in
  [difflib](https://docs.python.org/3.10/library/difflib.html).

- [Filtering](src/chopdiff/transforms/diff_filters.py) of these text-based diffs based
  on specific criteria.
  For example, only adding or removing words, only changing whitespace, only changing
  word lemmas, etc.

- The [`TokenMapping`](src/chopdiff/docs/token_mapping.py) class offers word-based
  mappings between docs, allowing you to find what part of a doc corresponds with
  another doc as a token index mappings.

- Lightweight "chunking" of documents by wrapping paragraphs in named `<div>`s to
  indicate chunks. [`TextNode`](src/chopdiff/divs/text_node.py) offers simple recursive
  parsing around `<div>` tags.
  This is not a general HTML parser, but rather a way to chunk documents into named
  pieces. Unlike more complex parsers, the `TextNode` parser operates on character
  offsets, so maintains the original document exactly and allows exact reassembly if
  desired.

- The word-based token mapping allows
  [transformation](src/chopdiff/transforms/sliding_transforms.py) of documents via
  sliding windows, transforming text (e.g. via an LLM call one window at a time, with
  overlapping windows), then re-stitching the results back together with best
  alignments.

All this is done very simply in memory, and with only regex or basic Markdown parsing to
keep things simple and with few dependencies.

`chopdiff` has no heavier dependencies like full XML or BeautifulSoup parsing or Spacy
or nltk for sentence splitting (though you can use these as custom sentence parsers if
you like).

## Installation

```
pip install chopdiff
```

## Examples

See the [examples/](/examples/) directory.

### Inserting Paragraph Breaks

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
$ python examples/insert_para_breaks.py examples/gettysberg.txt 

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

## Development

For development workflows, see [development.md](development.md).

* * *

*This project was built from
[simple-modern-poetry](https://github.com/jlevy/simple-modern-poetry).*
