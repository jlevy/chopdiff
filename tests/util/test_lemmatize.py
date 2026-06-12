from chopdiff.util.lemmatize import lemmatize, lemmatized_equal


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
