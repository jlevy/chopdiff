"""
Reading-time estimates from a word count.
"""

from __future__ import annotations

from prettyfmt import fmt_timedelta

DEFAULT_WORDS_PER_MINUTE = 225


def format_read_time(
    word_count: int,
    words_per_minute: int = DEFAULT_WORDS_PER_MINUTE,
    brief: bool = True,
    minimum_time: float = 3.0,
) -> str:
    """
    Human-readable reading-time estimate for `word_count` words (e.g. `"4m"`, or
    `"4 minutes"` with `brief=False`).

    Returns `""` for empty/invalid input, and also when the estimate is below
    `minimum_time` minutes (default 3.0; set `0` to always return an estimate) — the
    convention for "too short to bother showing."
    """
    if word_count <= 0 or words_per_minute <= 0:
        return ""

    minutes = word_count / words_per_minute
    if minimum_time > 0 and minutes < minimum_time:
        return ""

    return fmt_timedelta(minutes * 60, brief=brief)


## Tests


def test_format_read_time():
    # Below the default 3-minute threshold -> empty.
    assert format_read_time(600, 225) == ""  # 2.67 min
    assert format_read_time(674, 225) == ""  # 2.996 min
    assert format_read_time(675, 225) in ["3m", "180s"]  # exactly 3 min
    assert format_read_time(900, 225) in ["4m", "240s"]

    # Threshold disabled.
    assert format_read_time(225, 225, minimum_time=0) in ["1m", "60s"]
    assert format_read_time(112, 225, minimum_time=0) == "30s"

    # Verbose format.
    assert format_read_time(900, 225, brief=False) in ["4 minutes", "240 seconds"]

    # Invalid input.
    assert format_read_time(0, 225) == ""
    assert format_read_time(-100, 225) == ""
    assert format_read_time(100, 0) == ""
