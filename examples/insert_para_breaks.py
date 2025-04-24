# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "chopdiff",
#     "flowmark",
#     "openai",
# ]
# ///
import argparse
import logging
from textwrap import dedent

import openai  # pyright: ignore  # Not a project dep.
from flowmark import fill_text

from chopdiff.docs import TextDoc
from chopdiff.transforms import WINDOW_2K_WORDTOKS, changes_whitespace, filtered_transform

logging.basicConfig(format=">> %(message)s")
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


def heading(text: str):
    return "\n--- " + text + " " + "-" * (70 - len(text)) + "\n"


def insert_paragraph_breaks(text: str) -> str:
    # Create a TextDoc from the input text
    doc = TextDoc.from_text(text)

    # Handy calculations of document size in paragraphs, sentences, etc.
    print(f"\nInput document: {doc.size_summary()}")

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


def main():
    parser = argparse.ArgumentParser(
        description="Insert paragraph breaks in text files, making no other changes of any kind to a document."
    )
    parser.add_argument("input_file", help="Path to the input text file")
    parser.add_argument("-o", "--output", help="Path to the output file (default: stdout)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    with open(args.input_file, encoding="utf-8") as f:
        input_text = f.read()

    print(heading("Original"))
    print(fill_text(input_text))

    result = insert_paragraph_breaks(input_text)

    print(heading("With paragraph breaks"))
    print(fill_text(result))


if __name__ == "__main__":
    main()
