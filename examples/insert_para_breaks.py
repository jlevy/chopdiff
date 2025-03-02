import argparse
import logging
from textwrap import dedent

import openai
from chopdiff.docs.diff_filters import changes_whitespace
from chopdiff.docs.sliding_transforms import filtered_transform
from chopdiff.docs.text_doc import TextDoc
from chopdiff.docs.window_settings import WINDOW_2K_WORDTOKS
from flowmark import fill_text


def llm_insert_para_breaks(input_text: str) -> str:
    """
    Call OpenAI to insert paragraph breaks on a chunk of text.
    This works best on a smaller chunk of text and might make
    other non-whitespace changes.
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


def main():
    parser = argparse.ArgumentParser(description="Insert paragraph breaks in text files.")
    parser.add_argument("input_file", help="Path to the input text file")
    parser.add_argument("-o", "--output", help="Path to the output file (default: stdout)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    with open(args.input_file, "r", encoding="utf-8") as f:
        input_text = f.read()

    def heading(text: str):
        print("\n--- " + text + " " + "-" * (70 - len(text)) + "\n")

    heading("Original")
    print(fill_text(input_text))

    result = insert_paragraph_breaks(input_text)

    heading("With Paragraph Breaks")
    print(fill_text(result))


if __name__ == "__main__":
    main()
