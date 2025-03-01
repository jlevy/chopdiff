import simplemma


def lemmatize(text: str, lang: str = "en") -> str:
    """
    Returns a string of lemmatized tokens using simplemma.
    """
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


## Tests


def test_lemmatize():
    assert lemmatize("running") == "run"
    assert lemmatize("better") == "good"
    assert lemmatize("The cats are running") == "the cat be run"
    assert lemmatize("Hello, world!") == "hello , world !"
    assert lemmatize("I have 3 cats.") == "I have 3 cat ."
    assert lemmatized_equal("The cat runs", "The cats running")
    assert not lemmatized_equal("The cat  runs", "The dog runs")
    assert lemmatized_equal("The CAT runs", "the cats RUN")
    assert not lemmatized_equal("The CAT runs", "the cats RAN", case_sensitive=True)
