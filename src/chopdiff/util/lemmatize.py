def lemmatize(text: str, lang: str = "en") -> str:
    """
    Returns a string of lemmatized tokens using simplemma.
    """
    try:
        import simplemma
    except ImportError:
        raise ImportError(
            "simplemma is an optional dependency of chopdiff. Add it to use lemmatization."
        )

    tokens = simplemma.simple_tokenizer(text)
    lemmatized_tokens = [simplemma.lemmatize(token, lang=lang) for token in tokens]
    return " ".join(lemmatized_tokens)


def lemmatized_equal(text1: str, text2: str, case_sensitive: bool = False) -> bool:
    """
    Compare two texts to see if they are the same except for lemmatization.
    Ignores whitespace. Does not ignore punctuation.
    """
    if not case_sensitive:
        text1 = text1.lower()
        text2 = text2.lower()
    return lemmatize(text1) == lemmatize(text2)
