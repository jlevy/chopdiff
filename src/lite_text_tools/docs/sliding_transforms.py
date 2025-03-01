"""
Transform text using sliding windows over a document, then reassembling the
transformed text.
"""

import logging
from math import ceil
from textwrap import dedent
from typing import Any, Callable, List, Optional, TypeAlias

from flowmark import normalize_markdown
from prettyfmt import fmt_lines

from .diff_filters import accept_all
from .sliding_windows import sliding_para_window, sliding_word_window
from .text_doc import Paragraph, TextDoc, TextUnit
from .token_diffs import diff_docs, DiffFilter, find_best_alignment
from .window_settings import WINDOW_BR, WINDOW_BR_SEP, WindowSettings
from .wordtoks import join_wordtoks


log = logging.getLogger(__name__)

TextDocTransform: TypeAlias = Callable[[TextDoc], TextDoc]

SaveFunc: TypeAlias = Callable[[str, str, Any], None]


def remove_window_br(doc: TextDoc):
    """
    Remove `<!--window-br-->` markers in a document.
    """
    doc.replace_str(WINDOW_BR, "")


def filtered_transform(
    doc: TextDoc,
    transform_func: TextDocTransform,
    windowing: Optional[WindowSettings],
    diff_filter: DiffFilter = accept_all,
    debug_save: Optional[SaveFunc] = None,
) -> TextDoc:
    """
    Apply a transform with sliding window across the input doc, enforcing the changes it's
    allowed to make with `diff_filter`.

    If windowing is None, apply the transform to the entire document at once.

    `debug_save` is an optional function that takes a message, a filename, and an object, and saves
    the object to a file for debugging.
    """
    has_filter = diff_filter != accept_all

    if not windowing or not windowing.size:
        transformed_doc = transform_func(doc)
    else:

        def transform_and_check_diff(input_doc: TextDoc) -> TextDoc:
            # Avoid having window breaks build up after multiple transforms.
            remove_window_br(input_doc)

            transformed_doc = transform_func(input_doc)

            if has_filter:
                # Check the transform did what it should have.
                diff = diff_docs(input_doc, transformed_doc)
                accepted_diff, rejected_diff = diff.filter(diff_filter)

                assert diff.left_size() == input_doc.size(TextUnit.wordtoks)
                assert accepted_diff.left_size() == input_doc.size(TextUnit.wordtoks)
                assert rejected_diff.left_size() == input_doc.size(TextUnit.wordtoks)

                log.info(
                    "Accepted transform changes:\n%s",
                    fmt_lines(str(accepted_diff).splitlines()),
                )

                # Note any rejections.
                rejected_changes = rejected_diff.changes()
                if rejected_changes:
                    log.info(
                        "Filtering extraneous changes:\n%s",
                        fmt_lines(rejected_diff.as_diff_str(False).splitlines()),
                    )

                # Apply only the accepted changes.
                final_doc = TextDoc.from_wordtoks(
                    accepted_diff.apply_to(list(input_doc.as_wordtoks()))
                )
                log.info(
                    "Word token changes:\n%s",
                    fmt_lines(
                        [
                            f"Accepted: {accepted_diff.stats()}",
                            f"Rejected: {rejected_diff.stats()}",
                        ]
                    ),
                )
            else:
                diff = None
                accepted_diff, rejected_diff = None, None
                final_doc = transformed_doc

            if debug_save:
                debug_save(
                    "Input doc normalized",
                    "filtered_transform",
                    normalize_markdown(input_doc.reassemble()),
                )
                debug_save(
                    "Output doc raw", "filtered_transform", transformed_doc.reassemble()
                )
                # log_save(
                #     "Output doc normalized",
                #     "filtered_transform",
                #     normalize_markdown(transformed_doc.reassemble()),
                # )
                if diff:
                    debug_save("Transform diff", "filtered_transform", diff)
                # if accepted_diff:
                #     log.save_object("Accepted diff", "filtered_transform", accepted_diff)
                if rejected_diff:
                    debug_save("Rejected diff", "filtered_transform", rejected_diff)

                debug_save("Final doc", "filtered_transform", final_doc.reassemble())

            return final_doc

        transformed_doc = sliding_window_transform(
            doc,
            transform_and_check_diff,
            windowing,
        )

    return transformed_doc


def sliding_window_transform(
    doc: TextDoc, transform_func: TextDocTransform, settings: WindowSettings
) -> TextDoc:
    if settings.unit == TextUnit.wordtoks:
        return sliding_wordtok_window_transform(doc, transform_func, settings)
    elif settings.unit == TextUnit.paragraphs:
        return sliding_para_window_transform(doc, transform_func, settings)
    else:
        raise ValueError(f"Unsupported sliding transform unit: {settings.unit}")


def sliding_wordtok_window_transform(
    doc: TextDoc, transform_func: TextDocTransform, settings: WindowSettings
) -> TextDoc:
    """
    Apply a transformation function to each TextDoc in a sliding window over the given document,
    stepping through wordtoks, then reassemble the transformed document. Uses best effort to
    stitch the results together seamlessly by searching for the best alignment (minimum wordtok
    edit distance) of each transformed window.
    """
    if settings.unit != TextUnit.wordtoks:
        raise ValueError(f"This sliding window expects wordtoks, not {settings.unit}")

    windows = sliding_word_window(doc, settings.size, settings.shift, TextUnit.wordtoks)

    nwordtoks = doc.size(TextUnit.wordtoks)
    nbytes = doc.size(TextUnit.bytes)
    nwindows = ceil(nwordtoks / settings.shift)
    sep_wordtoks = [settings.separator] if settings.separator else []

    log.info(
        "Sliding word transform: Begin on doc: total %s wordtoks, %s bytes, %s windows, %s",
        nwordtoks,
        nbytes,
        nwindows,
        settings,
    )

    output_wordtoks: List[str] = []
    for i, window in enumerate(windows):
        log.info(
            "Sliding word transform window %s/%s (%s wordtoks, %s bytes), at %s wordtoks so far",
            i + 1,
            nwindows,
            window.size(TextUnit.wordtoks),
            window.size(TextUnit.bytes),
            len(output_wordtoks),
        )

        transformed_window = transform_func(window)

        new_wordtoks = list(transformed_window.as_wordtoks())

        if not output_wordtoks:
            output_wordtoks = new_wordtoks
        else:
            if len(output_wordtoks) < settings.min_overlap:
                raise ValueError(
                    "Output wordtoks too short to align with min_overlap %s: %s",
                    settings.min_overlap,
                    output_wordtoks,
                )
            if len(new_wordtoks) < settings.min_overlap:
                log.error(
                    "New wordtoks too short to align with min_overlap %s, skipping: %s",
                    settings.min_overlap,
                    new_wordtoks,
                )
                continue

            offset, (score, diff) = find_best_alignment(
                output_wordtoks, new_wordtoks, settings.min_overlap
            )

            log.info(
                "Sliding word transform: Best alignment of window %s is at token offset %s (score %s, %s)",
                i,
                offset,
                score,
                diff.stats(),
            )

            output_wordtoks = output_wordtoks[:offset] + sep_wordtoks + new_wordtoks

    log.info(
        "Sliding word transform: Done, output total %s wordtoks",
        len(output_wordtoks),
    )

    # An alternate approach would be to accumulate the document sentences instead of wordtoks to
    # avoid re-parsing, but this is probably a little simpler.
    output_doc = TextDoc.from_text(join_wordtoks(output_wordtoks))

    return output_doc


def sliding_para_window_transform(
    doc: TextDoc,
    transform_func: TextDocTransform,
    settings: WindowSettings,
    normalizer: Callable[[str], str] = normalize_markdown,
) -> TextDoc:
    """
    Apply a transformation function to each TextDoc, stepping through paragraphs `settings.size`
    at a time, then reassemble the transformed document.
    """
    if settings.unit != TextUnit.paragraphs:
        raise ValueError(f"This sliding window expects paragraphs, not {settings.unit}")
    if settings.size != settings.shift:
        raise ValueError("Paragraph window transform requires equal size and shift")

    windows = sliding_para_window(doc, settings.size, normalizer)

    nwindows = ceil(doc.size(TextUnit.paragraphs) / settings.size)

    log.info(
        "Sliding paragraph transform: Begin on doc: %s windows of size %s paragraphs on total %s",
        nwindows,
        settings.size,
        doc.size_summary(),
    )

    transformed_paras: List[Paragraph] = []
    for i, window in enumerate(windows):
        log.info(
            "Sliding paragraph transform: Window %s/%s input is %s",
            i,
            nwindows,
            window.size_summary(),
        )

        new_doc = transform_func(window)
        if i > 0:
            try:
                new_doc.paragraphs[0].sentences[0].text = (
                    settings.separator + new_doc.paragraphs[0].sentences[0].text
                )
            except (KeyError, IndexError):
                pass
        transformed_paras.extend(new_doc.paragraphs)

    transformed_text = "\n\n".join(para.reassemble() for para in transformed_paras)
    new_text_doc = TextDoc.from_text(transformed_text)

    log.info(
        "Sliding paragraph transform: Done, output total %s",
        new_text_doc.size_summary(),
    )

    return new_text_doc


## Tests

_example_text = dedent(
    """
    This is the first paragraph. It has multiple sentences.

    This is the second paragraph. It also has multiple sentences. And it continues.
    
    Here is the third paragraph. More sentences follow. And here is another one.
    """
).strip()


def test_sliding_word_window_transform():
    long_text = (_example_text + "\n\n") * 2
    doc = TextDoc.from_text(long_text)

    # Simple transformation that converts all text to uppercase.
    def transform_func(window: TextDoc) -> TextDoc:
        transformed_text = window.reassemble().upper()
        return TextDoc.from_text(transformed_text)

    transformed_doc = sliding_window_transform(
        doc,
        transform_func,
        WindowSettings(TextUnit.wordtoks, 80, 60, min_overlap=5, separator="|"),
    )
    print("---Wordtok transformed doc:")
    print(transformed_doc.reassemble())

    assert transformed_doc.reassemble().count("|") == 2

    long_text = (_example_text + "\n\n") * 20
    doc = TextDoc.from_text(long_text)
    transformed_doc = sliding_window_transform(
        doc, transform_func, WindowSettings(TextUnit.wordtoks, 80, 60, min_overlap=5)
    )
    assert transformed_doc.reassemble() == long_text.upper().strip()


def test_sliding_para_window_transform():
    def transform_func(window: TextDoc) -> TextDoc:
        transformed_text = window.reassemble().upper()
        return TextDoc.from_text(transformed_text)

    text = "\n\n".join(f"Paragraph {i}." for i in range(7))
    doc = TextDoc.from_text(text)

    transformed_doc = sliding_para_window_transform(
        doc,
        transform_func,
        WindowSettings(
            TextUnit.paragraphs,
            3,
            3,
            separator=WINDOW_BR_SEP,
        ),
    )

    print("---Paragraph transformed doc:")
    print(transformed_doc.reassemble())

    assert (
        transformed_doc.reassemble()
        == dedent(
            """
            PARAGRAPH 0.

            PARAGRAPH 1.

            PARAGRAPH 2.

            <!--window-br--> PARAGRAPH 3.

            PARAGRAPH 4.

            PARAGRAPH 5.

            <!--window-br--> PARAGRAPH 6.
            """
        ).strip()
    )
