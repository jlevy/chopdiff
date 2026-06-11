from __future__ import annotations

from math import ceil

CHARS_PER_TOKEN = 3.8
"""
Characters per token, used to estimate LLM token counts without a tokenizer or
network access.

This is a blended rule of thumb across current OpenAI, Anthropic, and Google
models: OpenAI (o200k_base / cl100k_base) and Google Gemini average ~4 characters
per token for English, while Anthropic suggests ~3.5. 3.8 splits the difference,
leaning slightly conservative so estimates rarely undercount. Typical accuracy is
within ~10-20% for English prose and Markdown; denser content (source code, heavy
markup) and non-English text use more tokens per character, so estimates there
skew low. For exact counts, use a specific model provider's tokenizer.

Sources:
- OpenAI: https://help.openai.com/en/articles/4936856-what-are-tokens-and-how-to-count-them
- Google Gemini: https://ai.google.dev/gemini-api/docs/tokens
- Anthropic: heuristic of ~3.5 English characters per token.
"""


def estimate_tokens(text: str, chars_per_token: float = CHARS_PER_TOKEN) -> int:
    """
    Estimate the number of LLM tokens in `text` using the characters-per-token rule
    of thumb (see `CHARS_PER_TOKEN`). Fast and dependency-free, but approximate
    (typically within ~10-20% for English prose and Markdown). Returns 0 for empty
    text.
    """
    if not text:
        return 0
    return ceil(len(text) / chars_per_token)
