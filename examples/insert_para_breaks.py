# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "chopdiff==0.3.1",
#     "flexdoc==0.3.0",
#     "flowmark==0.7.2",
#     "openai==2.44.0",
#     "strif==3.1.0",
# ]
# [tool.uv]
# exclude-newer = "2026-06-30T00:00:00Z"
# [tool.uv.exclude-newer-package]
# flexdoc = "2026-07-12T00:00:00Z"
# ///
from __future__ import annotations

import argparse
import logging
from pathlib import Path
from textwrap import dedent

import openai  # pyright: ignore[reportMissingImports]  # Standalone script dependency.
from flexdoc import FlexDoc
from flowmark import fill_text
from strif import atomic_output_file

from chopdiff.transforms import WINDOW_2K_WORDTOKS, changes_whitespace, filtered_transform

logging.basicConfig(format=">> %(message)s")
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


def heading(text: str) -> str:
    return "\n--- " + text + " " + "-" * (70 - len(text)) + "\n"


def insert_paragraph_breaks(text: str) -> str:
    # Create a FlexDoc from the input text
    doc = FlexDoc.from_text(text)

    # Handy calculations of document size in paragraphs, sentences, etc.
    print(f"\nInput document: {doc.size_summary()}")

    # Define the transformation function.
    # Note in this case we run the LLM on strings, but you could also work directly
    # on the FlexDoc if appropriate.
    def transform(doc: FlexDoc) -> FlexDoc:
        return FlexDoc.from_text(llm_insert_para_breaks(doc.reassemble()))

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

    print(heading("Output document"))
    print(f"\nOutput document: {result_doc.size_summary()}")

    # Return the transformed text
    return result_doc.reassemble()


def llm_insert_para_breaks(input_text: str) -> str:
    """
    Call OpenAI to insert paragraph breaks on a chunk of text.
    This works best on a smaller chunk of text and might make
    other non-whitespace changes.
    """
    client: openai.OpenAI = openai.OpenAI()

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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Insert paragraph breaks in text files, making no other changes of any kind to a document."
    )
    parser.add_argument("input_file", help="Path to the input text file")
    parser.add_argument("-o", "--output", help="Path to the output file (default: stdout)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    input_text = Path(args.input_file).read_text(encoding="utf-8")

    result = insert_paragraph_breaks(input_text)
    formatted = fill_text(result)

    if args.output:
        output_path = Path(args.output)
        with atomic_output_file(output_path) as temp_path:
            temp_path.write_text(formatted, encoding="utf-8")
        print(f"Wrote paragraph-broken text to {output_path}")
    else:
        print(heading("Original"))
        print(fill_text(input_text))
        print(heading("With paragraph breaks"))
        print(formatted)


if __name__ == "__main__":
    main()
