# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "chopdiff",
#     "flowmark",
# ]
# ///
import logging
from textwrap import dedent

from chopdiff.docs import BOF_TOK, EOF_TOK, PARA_BR_TOK, TextDoc, TokenMapping, search_tokens
from chopdiff.html import ContentNotFound, TimestampExtractor

logging.basicConfig(format=">> %(message)s")
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


def format_timestamp(timestamp: float) -> str:
    hours, remainder = divmod(timestamp, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"
    else:
        return f"{int(minutes):02}:{int(seconds):02}"


def add_timestamp(text: str, timestamp: float) -> str:
    return f'{text} <span class="timestamp">⏱️{format_timestamp(timestamp)}</span> '


def heading(text: str):
    return "\n--- " + text + " " + "-" * (70 - len(text)) + "\n"


def backfill_timestamps(target_text: str, source_text: str) -> str:
    """
    Backfill timestamps from a source document into a target document.
    The source document should have timestamps in `<span>`s with a `data-timestamp` attribute.
    The target document should have mostly similar text but no timestamps.
    """

    print(heading("Source text (with timestamps)"))
    print(source_text)

    print(heading("Target text (without timestamps)"))
    print(target_text)

    # Parse the target document into wordtoks.
    target_doc = TextDoc.from_text(target_text)
    extractor = TimestampExtractor(source_text)
    source_wordtoks = extractor.wordtoks

    # Create a mapping between source and target docs.
    target_wordtoks = list(target_doc.as_wordtoks(bof_eof=True))
    token_mapping = TokenMapping(source_wordtoks, target_wordtoks)

    print(heading("Diff"))
    print(token_mapping.diff.as_diff_str())

    print(heading("Token mapping"))
    print(token_mapping.full_mapping_str())

    for wordtok_offset, (wordtok, sent_index) in enumerate(
        target_doc.as_wordtok_to_sent(bof_eof=True)
    ):
        # Look for each end of paragraph or end of doc.
        if wordtok in [PARA_BR_TOK, EOF_TOK]:
            # Find the start of the paragraph.
            start_para_index, start_para_wordtok = (
                search_tokens(target_wordtoks)
                .at(wordtok_offset)
                .seek_back([BOF_TOK, PARA_BR_TOK])
                .next()
                .get_token()
            )

            wordtok_offset = start_para_index

            source_wordtok_offset = token_mapping.map_back(wordtok_offset)

            log.info(
                "Seeking back tok %s (%s) to para start tok %s (%s), map back to source tok %s (%s)",
                wordtok_offset,
                wordtok,
                start_para_index,
                start_para_wordtok,
                source_wordtok_offset,
                source_wordtoks[source_wordtok_offset],
            )

            try:
                timestamp, _index, _offset = extractor.extract_preceding(source_wordtok_offset)
                sent = target_doc.get_sent(sent_index)

                if sent.is_markup():
                    log.info("Skipping markup-only sentence: %s", sent.text)
                    continue

                log.info("Adding timestamp to sentence: %s", sent)

                sent.text = add_timestamp(sent.text, timestamp)

            except ContentNotFound:
                # Missing timestamps shouldn't be fatal.
                log.warning(
                    "Failed to extract timestamp at doc token %s (%s) -> source token %s (%s): %s",
                    wordtok_offset,
                    wordtok,
                    source_wordtok_offset,
                    source_wordtoks[source_wordtok_offset],
                    sent_index,
                )

    result = target_doc.reassemble()

    print(heading("Result (with backfilled timestamps)"))
    print(result)

    return result


def main():
    # Example source text with timestamps:
    source_text = dedent(
        """
        <span data-timestamp="0.0">Welcome to this um ... video about Python programming.</span>
        <span data-timestamp="15.5">First, we'll talk about variables. Variables are containers for storing data values.</span>
        <span data-timestamp="25.2">Then let's look at functions. Functions help us organize and reuse code.</span>
      """
    )

    # Example target text (similar content but edited, with no timestamps):
    target_text = dedent(
        """
        ## Introduction

        Welcome to this video about Python programming.
        
        First, we'll talk about variables. Next, let's look at functions. Functions help us organize and reuse code.
        """
    )

    backfill_timestamps(target_text, source_text)


if __name__ == "__main__":
    main()
