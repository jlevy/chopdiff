from typing_extensions import override

from chopdiff.docs.token_diffs import SYMBOL_SEP, OpType, TokenDiff, diff_wordtoks


class TokenMapping:
    """
    Given two sequences of tokens, create a best-estimate mapping of how the tokens
    in the second sequence map to the tokens in the first sequence, based on an
    LCS-style diff.
    """

    def __init__(
        self,
        tokens1: list[str],
        tokens2: list[str],
        diff: TokenDiff | None = None,
        min_tokens: int = 10,
        max_diff_frac: float = 0.4,
    ):
        self.tokens1 = tokens1
        self.tokens2 = tokens2
        self.diff = diff or diff_wordtoks(self.tokens1, self.tokens2)
        self._validate(min_tokens, max_diff_frac)
        self.backmap: dict[int, int] = {}
        self._create_mapping()

    def map_back(self, offset2: int) -> int:
        """
        Map an offset in the second sequence back to the offset that most closely corresponds to it
        in the first sequence. This might be an exact match (e.g. the same word) or the closest token
        (e.g. the last word before a deleted or changed word).
        """
        return self.backmap[offset2]

    def _validate(self, min_wordtoks: int, max_diff_frac: float):
        if len(self.tokens1) < min_wordtoks or len(self.tokens2) < min_wordtoks:
            raise ValueError(f"Documents should have at least {min_wordtoks} wordtoks")

        nchanges = len(self.diff.changes())
        if float(nchanges) / len(self.tokens1) > max_diff_frac:
            raise ValueError(
                f"Documents have too many changes: {nchanges}/{len(self.tokens1)} ({float(nchanges) / len(self.tokens1):.2f} > {max_diff_frac})"
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
        """
        For debugging or logging, return a verbose, readable table of the mapping of each
        token in the second sequence to the first sequence.
        """
        return "\n".join(
            f"{i} {SYMBOL_SEP}{self.tokens2[i]}{SYMBOL_SEP} -> {self.map_back(i)} {SYMBOL_SEP}{self.tokens1[self.map_back(i)]}{SYMBOL_SEP}"
            for i in range(len(self.tokens2))
        )

    @override
    def __str__(self):
        return f"OffsetMapping(doc1 len {len(self.tokens1)}, doc2 len {len(self.tokens2)}, mapping len {len(self.backmap)})"
