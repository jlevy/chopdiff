from dataclasses import dataclass

from typing_extensions import override

from chopdiff.docs.sizes import TextUnit

WINDOW_BR = "<!--window-br-->"
"""Marker inserted into result documents to show where window breaks have occurred."""

WINDOW_BR_SEP = f"\n{WINDOW_BR}\n"


@dataclass(frozen=True)
class WindowSettings:
    """
    Size of the sliding window, the shift, and the min overlap required when stitching windows
    together. All sizes in wordtoks.
    """

    unit: TextUnit
    size: int
    shift: int
    min_overlap: int = 0
    separator: str = ""

    @override
    def __str__(self):
        return f"windowing size={self.size}, shift={self.shift}, min_overlap={self.min_overlap} {self.unit.value}"


WINDOW_NONE = WindowSettings(unit=TextUnit.wordtoks, size=0, shift=0, min_overlap=0, separator="")
"""
Do not use a sliding window.
"""

WINDOW_2K_WORDTOKS = WindowSettings(
    TextUnit.wordtoks,
    size=2048,
    shift=2048 - 256,
    min_overlap=8,
    separator=WINDOW_BR_SEP,
)
"""
Sliding, overlapping word-based window. Useful for finding paragraph breaks.
2K wordtoks is several paragraphs.
"""


WINDOW_1_PARA = WindowSettings(
    TextUnit.paragraphs, size=1, shift=1, min_overlap=0, separator=WINDOW_BR_SEP
)
"""Process 1 paragraph at a time."""


WINDOW_2_PARA = WindowSettings(
    TextUnit.paragraphs, size=2, shift=2, min_overlap=0, separator=WINDOW_BR_SEP
)
"""Process 2 paragraphs at a time."""


WINDOW_4_PARA = WindowSettings(
    TextUnit.paragraphs, size=4, shift=4, min_overlap=0, separator=WINDOW_BR_SEP
)
"""Process 4 paragraph at a time."""


WINDOW_8_PARA = WindowSettings(
    TextUnit.paragraphs, size=8, shift=8, min_overlap=0, separator=WINDOW_BR_SEP
)
"""Process 8 paragraphs at a time."""


WINDOW_16_PARA = WindowSettings(
    TextUnit.paragraphs, size=16, shift=16, min_overlap=0, separator=WINDOW_BR_SEP
)
"""Process 16 paragraphs at a time."""

WINDOW_32_PARA = WindowSettings(
    TextUnit.paragraphs, size=32, shift=32, min_overlap=0, separator=WINDOW_BR_SEP
)
"""Process 32 paragraphs at a time."""

WINDOW_64_PARA = WindowSettings(
    TextUnit.paragraphs, size=64, shift=64, min_overlap=0, separator=WINDOW_BR_SEP
)
"""Process 64 paragraphs at a time."""

WINDOW_128_PARA = WindowSettings(
    TextUnit.paragraphs, size=128, shift=128, min_overlap=0, separator=WINDOW_BR_SEP
)
"""Process 128 paragraphs at a time."""

WINDOW_256_PARA = WindowSettings(
    TextUnit.paragraphs, size=256, shift=256, min_overlap=0, separator=WINDOW_BR_SEP
)
"""Process 256 paragraphs at a time."""

WINDOW_512_PARA = WindowSettings(
    TextUnit.paragraphs, size=512, shift=512, min_overlap=0, separator=WINDOW_BR_SEP
)
"""Process 512 paragraphs at a time."""

WINDOW_1024_PARA = WindowSettings(
    TextUnit.paragraphs, size=1024, shift=1024, min_overlap=0, separator=WINDOW_BR_SEP
)
"""Process 1024 paragraphs at a time."""
