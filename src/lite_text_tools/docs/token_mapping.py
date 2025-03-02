from typing import Dict, List, Optional

from lite_text_tools.docs.token_diffs import diff_wordtoks, OpType, SYMBOL_SEP, TokenDiff


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
