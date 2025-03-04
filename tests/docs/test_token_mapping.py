from textwrap import dedent

from chopdiff.docs.text_doc import TextDoc
from chopdiff.docs.token_mapping import TokenMapping
from chopdiff.docs.wordtoks import wordtokenize


def test_offset_mapping():
    doc1 = TextDoc.from_text("This is a simple test with some words.")
    doc2 = TextDoc.from_text(
        "This is<-PARA-BR->a simple pytest adding other words.<-SENT-BR->And another sentence."
    )

    mapping = TokenMapping(list(doc1.as_wordtoks()), list(doc2.as_wordtoks()))

    mapping_str = mapping.full_mapping_str()

    print(mapping.diff.as_diff_str(include_equal=True))
    print(mapping)
    print(mapping.backmap)
    print(mapping_str)

    assert (
        mapping_str
        == dedent(
            """
            0 ⎪This⎪ -> 0 ⎪This⎪
            1 ⎪ ⎪ -> 1 ⎪ ⎪
            2 ⎪is⎪ -> 2 ⎪is⎪
            3 ⎪<-PARA-BR->⎪ -> 3 ⎪ ⎪
            4 ⎪a⎪ -> 4 ⎪a⎪
            5 ⎪ ⎪ -> 5 ⎪ ⎪
            6 ⎪simple⎪ -> 6 ⎪simple⎪
            7 ⎪ ⎪ -> 7 ⎪ ⎪
            8 ⎪pytest⎪ -> 8 ⎪test⎪
            9 ⎪ ⎪ -> 9 ⎪ ⎪
            10 ⎪adding⎪ -> 10 ⎪with⎪
            11 ⎪ ⎪ -> 11 ⎪ ⎪
            12 ⎪other⎪ -> 12 ⎪some⎪
            13 ⎪ ⎪ -> 13 ⎪ ⎪
            14 ⎪words⎪ -> 14 ⎪words⎪
            15 ⎪.⎪ -> 15 ⎪.⎪
            16 ⎪<-SENT-BR->⎪ -> 15 ⎪.⎪
            17 ⎪And⎪ -> 15 ⎪.⎪
            18 ⎪ ⎪ -> 15 ⎪.⎪
            19 ⎪another⎪ -> 15 ⎪.⎪
            20 ⎪ ⎪ -> 15 ⎪.⎪
            21 ⎪sentence⎪ -> 15 ⎪.⎪
            22 ⎪.⎪ -> 15 ⎪.⎪
            """
        ).strip()
    )


def test_offset_mapping_longer():
    doc1 = dedent(
        """
        <span data-timestamp="5.60">Alright, guys.</span>
        <span data-timestamp="6.16">Here's the deal.</span>
        <span data-timestamp="7.92">You can follow me on my daily workouts.</span>
        """
    )
    doc2 = dedent(
        """
        Alright, guys. Here's the deal.
        You can follow me on my daily workouts.
        """
    )

    doc1_wordtoks = wordtokenize(doc1)
    doc2_wordtoks = list(TextDoc.from_text(doc2).as_wordtoks())

    mapping = TokenMapping(doc1_wordtoks, doc2_wordtoks)

    mapping_str = mapping.full_mapping_str()

    print(mapping.diff.as_diff_str(include_equal=True))
    print(mapping)
    print(mapping.backmap)
    print(mapping_str)

    assert (
        mapping_str
        == dedent(
            """
            0 ⎪Alright⎪ -> 2 ⎪Alright⎪
            1 ⎪,⎪ -> 3 ⎪,⎪
            2 ⎪ ⎪ -> 4 ⎪ ⎪
            3 ⎪guys⎪ -> 5 ⎪guys⎪
            4 ⎪.⎪ -> 6 ⎪.⎪
            5 ⎪ ⎪ -> 8 ⎪ ⎪
            6 ⎪Here⎪ -> 10 ⎪Here⎪
            7 ⎪'⎪ -> 11 ⎪'⎪
            8 ⎪s⎪ -> 12 ⎪s⎪
            9 ⎪ ⎪ -> 13 ⎪ ⎪
            10 ⎪the⎪ -> 14 ⎪the⎪
            11 ⎪ ⎪ -> 15 ⎪ ⎪
            12 ⎪deal⎪ -> 16 ⎪deal⎪
            13 ⎪.⎪ -> 17 ⎪.⎪
            14 ⎪<-SENT-BR->⎪ -> 20 ⎪<span data-timestamp="7.92">⎪
            15 ⎪You⎪ -> 21 ⎪You⎪
            16 ⎪ ⎪ -> 22 ⎪ ⎪
            17 ⎪can⎪ -> 23 ⎪can⎪
            18 ⎪ ⎪ -> 24 ⎪ ⎪
            19 ⎪follow⎪ -> 25 ⎪follow⎪
            20 ⎪ ⎪ -> 26 ⎪ ⎪
            21 ⎪me⎪ -> 27 ⎪me⎪
            22 ⎪ ⎪ -> 28 ⎪ ⎪
            23 ⎪on⎪ -> 29 ⎪on⎪
            24 ⎪ ⎪ -> 30 ⎪ ⎪
            25 ⎪my⎪ -> 31 ⎪my⎪
            26 ⎪ ⎪ -> 32 ⎪ ⎪
            27 ⎪daily⎪ -> 33 ⎪daily⎪
            28 ⎪ ⎪ -> 34 ⎪ ⎪
            29 ⎪workouts⎪ -> 35 ⎪workouts⎪
            30 ⎪.⎪ -> 36 ⎪.⎪
            """
        ).strip()
    )
