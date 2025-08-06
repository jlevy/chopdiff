"""
Utilities for calculating and formatting reading time estimates.
"""

from prettyfmt import fmt_timedelta


DEFAULT_WORDS_PER_MINUTE = 225


def format_read_time(
    word_count: int,
    words_per_minute: int = DEFAULT_WORDS_PER_MINUTE,
    brief: bool = True,
    minimum_time: float = 3.0,
) -> str:
    """
    Calculate and format reading time as a human-readable string.

    Args:
        word_count: Number of words in the text
        words_per_minute: Reading speed (default: 225 WPM)
        brief: If True, use abbreviated format (e.g., "2m 30s" instead of "2 minutes 30 seconds")
        minimum_time: Minimum time in minutes to display (default: 3.0). Returns empty string if below. 0 disables.

    Returns:
        Formatted reading time string, or empty string if below minimum_time
    """
    if word_count <= 0 or words_per_minute <= 0:
        return ""

    minutes = word_count / words_per_minute

    # Check minimum time threshold
    if minimum_time > 0 and minutes < minimum_time:
        return ""

    # Convert to seconds for fmt_timedelta
    seconds = minutes * 60

    # Use prettyfmt to format the time nicely
    return fmt_timedelta(seconds, brief=brief)


## Tests


def test_format_read_time():
    """Test reading time formatting."""
    # Test minimum time threshold (default 3 minutes)
    assert format_read_time(600, 225) == ""  # 2.67 minutes < 3 minutes
    assert format_read_time(674, 225) == ""  # 2.996 minutes < 3 minutes
    assert format_read_time(675, 225) in ["3m", "180s"]  # Exactly 3 minutes
    assert format_read_time(900, 225) in ["4m", "240s"]  # 4 minutes > threshold

    # Test with minimum_time disabled
    assert format_read_time(225, 225, minimum_time=0) in ["1m", "60s"]
    assert format_read_time(112, 225, minimum_time=0) == "30s"

    # Test verbose format
    assert format_read_time(900, 225, brief=False) in ["4 minutes", "240 seconds"]

    # Test edge cases
    assert format_read_time(0, 225) == ""
    assert format_read_time(-100, 225) == ""
    assert format_read_time(100, 0) == ""
