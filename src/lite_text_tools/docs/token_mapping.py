from textwrap import dedent
from typing import Dict, List, Optional

from .text_doc import TextDoc
from .token_diffs import diff_wordtoks, OpType, SYMBOL_SEP, TokenDiff
from .wordtoks import raw_text_to_wordtoks


class TokenMapping:
    """
    Given two sequences of word tokens, create a mapping from offsets
    """

    def __init__(
        self,
        wordtoks1: List[str],
        wordtoks2: List[str],
        diff: Optional[TokenDiff] = None,
        min_wordtoks: int = 10,
        max_diff_frac: float = 0.4,
    ):
        self.wordtoks1 = wordtoks1
        self.wordtoks2 = wordtoks2
        self.diff = diff or diff_wordtoks(self.wordtoks1, self.wordtoks2)
        self._validate(min_wordtoks, max_diff_frac)
        self.backmap: Dict[int, int] = {}
        self._create_mapping()

    def map_back(self, offset2: int) -> int:
        return self.backmap[offset2]

    def _validate(self, min_wordtoks: int, max_diff_frac: float):
        if len(self.wordtoks1) < min_wordtoks or len(self.wordtoks2) < min_wordtoks:
            raise ValueError(f"Documents should have at least {min_wordtoks} wordtoks")

        nchanges = len(self.diff.changes())
        if float(nchanges) / len(self.wordtoks1) > max_diff_frac:
            raise ValueError(
                f"Documents have too many changes: {nchanges}/{len(self.wordtoks1)} ({float(nchanges) / len(self.wordtoks1):.2f} > {max_diff_frac})"
            )

    def _create_mapping(self):
        offset1 = 0
        offset2 = 0
        last_offset1 = 0

        for op in self.diff.ops:
            if op.action == OpType.EQUAL:
                for _ in op.left:
                    self.backmap[offset2] = offset1
                    last_offset1 = offset1
                    offset1 += 1
                    offset2 += 1
            elif op.action == OpType.DELETE:
                for _ in op.left:
                    last_offset1 = offset1
                    offset1 += 1
            elif op.action == OpType.INSERT:
                for _ in op.right:
                    self.backmap[offset2] = last_offset1
                    offset2 += 1
            elif op.action == OpType.REPLACE:
                for _ in op.left:
                    last_offset1 = offset1
                    offset1 += 1
                for _ in op.right:
                    self.backmap[offset2] = last_offset1
                    offset2 += 1

    def full_mapping_str(self):
        return "\n".join(
            f"{i} {SYMBOL_SEP}{self.wordtoks2[i]}{SYMBOL_SEP} -> {self.map_back(i)} {SYMBOL_SEP}{self.wordtoks1[self.map_back(i)]}{SYMBOL_SEP}"
            for i in range(len(self.wordtoks2))
        )

    def __str__(self):
        return f"OffsetMapping(doc1 len {len(self.wordtoks1)}, doc2 len {len(self.wordtoks2)}, mapping len {len(self.backmap)})"


## Tests


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

    doc1_wordtoks = raw_text_to_wordtoks(doc1)
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
