# chopdiff

`chopdiff` is a small library of tools I've developed for use especially with
LLMs that let you handle Markdown and text document edits.

It aims to have minimal dependencies and be useful for various LLM applications where
you want to manipulate text, Markdown, and lightweight (not fully parsed) HTML
documents.

It offers support for:

- Parsing of documents into sentences and paragraphs (by default using regex heuristics
  or using a sentence splitter of your choice, like Spacy).

- Measure size and extract pieces of documents, using arbitrary units of paragraphs,
  sentences and indexing of these documents at the paragraph

- Support for lightweight "chunking" of documents by wrappign paragraphs in named
  `<div>`s to indicate chunks.

- Text-based diffing at the word level.

- Filtering of text-based diffs based on specific criteria.

- Transformation of documents via windows, then re-stitching the result.

All this is done very simply in memory, and with only regex or basic Markdown parsing to
keep things simple and with few dependencies.
This doesn't depend on anything

Example use cases:

- Walk through a document N paragraphs, N sentences, or N chunks at a time, processing
  the results with an LLM call and recombining the result.

- Ask an LLM to edit a transcript, only inserting paragraph breaks but enforcing that
  the LLM can't do anything except insert whitespace.

## Development

For development workflows, see [development.md](development.md).

* * *

*This project was built from
[simple-modern-poetry](https://github.com/jlevy/simple-modern-poetry).*
