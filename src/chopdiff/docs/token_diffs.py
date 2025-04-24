from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import TypeAlias

import cydifflib as difflib
from funlog import log_calls, tally_calls
from typing_extensions import override

from chopdiff.docs.text_doc import TextDoc

log = logging.getLogger(__name__)


SYMBOL_SEP = "⎪"


class OpType(Enum):
    EQUAL = "equal"
    INSERT = "insert"
    DELETE = "delete"
    REPLACE = "replace"

    def as_symbol(self):
        abbrev = {
            OpType.EQUAL: " ",
            OpType.INSERT: "+",
            OpType.DELETE: "-",
            OpType.REPLACE: "±",
        }
        return abbrev[self]

    def as_abbrev(self):
        abbrev = {
            OpType.EQUAL: "keep",
            OpType.INSERT: "add ",
            OpType.DELETE: "del ",
            OpType.REPLACE: "repl",
        }
        return abbrev[self]


@dataclass(frozen=True)
class DiffOp:
    action: OpType
    left: list[str]
    right: list[str]

    def __post_init__(self):
        if self.action == OpType.REPLACE:
            assert self.left and self.right
        elif self.action == OpType.EQUAL:
            assert self.left == self.right
        elif self.action == OpType.INSERT:
            assert not self.left
        elif self.action == OpType.DELETE:
            assert not self.right

    def left_str(self, show_toks: bool = True) -> str:
        s = f"{self.action.as_abbrev()} {len(self.left):4} toks"
        if show_toks:
            s += f": - {SYMBOL_SEP}{''.join(tok for tok in self.left)}{SYMBOL_SEP}"
        return s

    def right_str(self, show_toks: bool = True) -> str:
        s = f"{self.action.as_abbrev()} {len(self.right):4} toks"
        if show_toks:
            s += f": + {SYMBOL_SEP}{''.join(tok for tok in self.right)}{SYMBOL_SEP}"
        return s

    def equal_str(self, show_toks: bool = True) -> str:
        s = f"{self.action.as_abbrev()} {len(self.left):4} toks"
        if show_toks:
            s += f":   {SYMBOL_SEP}{''.join(tok for tok in self.left)}{SYMBOL_SEP}"
        return s

    def all_changed(self) -> list[str]:
        return [] if self.action == OpType.EQUAL else self.left + self.right


@dataclass(frozen=True)
class DiffStats:
    added: int
    removed: int
    input_size: int

    def nchanges(self) -> int:
        return self.added + self.removed

    @override
    def __str__(self):
        return f"add/remove +{self.added}/-{self.removed} out of {self.input_size} total"


DiffFilter: TypeAlias = Callable[[DiffOp], bool]

DIFF_FILTER_NONE: DiffFilter = lambda op: True
"""
Diff filter that accepts all diff operations.
"""


@dataclass
class TokenDiff:
    """
    A diff of two texts as a sequence of EQUAL, INSERT, and DELETE operations on wordtoks.
    """

    ops: list[DiffOp]

    def left_size(self) -> int:
        return sum(len(op.left) for op in self.ops)

    def right_size(self) -> int:
        return sum(len(op.right) for op in self.ops)

    def changes(self) -> list[DiffOp]:
        return [op for op in self.ops if op.action != OpType.EQUAL]

    def stats(self) -> DiffStats:
        wordtoks_added = sum(len(op.right) for op in self.ops if op.action != OpType.EQUAL)
        wordtoks_removed = sum(len(op.left) for op in self.ops if op.action != OpType.EQUAL)
        return DiffStats(wordtoks_added, wordtoks_removed, self.left_size())

    def apply_to(self, original_wordtoks: list[str]) -> list[str]:
        """
        Apply a complete diff (including equality ops) to a list of wordtoks.
        """
        result: list[str] = []
        original_index = 0

        if len(original_wordtoks) != self.left_size():
            raise AssertionError(
                f"Diff should be complete: original wordtoks length {len(original_wordtoks)} != diff length {self.left_size()}"
            )

        for op in self.ops:
            if op.left:
                original_index += len(op.left)
            if op.right:
                result.extend(op.right)

        return result

    def filter(self, accept_fn: DiffFilter | None) -> tuple[TokenDiff, TokenDiff]:
        """
        Return two diffs, one that only has accepted operations and one that only has
        rejected operations.
        """
        if not accept_fn:
            accept_fn = DIFF_FILTER_NONE

        accepted_ops: list[DiffOp] = []
        rejected_ops: list[DiffOp] = []

        for op in self.ops:
            if op.action == OpType.EQUAL:
                # For equal ops, all tokens are both accepted and rejected.
                accepted_ops.append(op)
                rejected_ops.append(op)
            else:
                # We accept or reject the DiffOp as a whole, not token by token, since token by
                # token would give odd results, like deleting words but leaving whitespace.
                if accept_fn(op):
                    accepted_ops.append(op)
                    rejected_ops.append(DiffOp(OpType.EQUAL, op.left, op.left))
                else:
                    accepted_ops.append(DiffOp(OpType.EQUAL, op.left, op.left))
                    rejected_ops.append(op)

        assert len(accepted_ops) == len(self.ops)
        assert len(accepted_ops) == len(rejected_ops)

        accepted_diff, rejected_diff = TokenDiff(accepted_ops), TokenDiff(rejected_ops)

        assert accepted_diff.left_size() == self.left_size()
        assert rejected_diff.left_size() == self.left_size()

        return accepted_diff, rejected_diff

    def _diff_lines(self, include_equal: bool = False) -> list[str]:
        if len(self.ops) == 0:
            return ["(No changes)"]

        pos = 0
        lines: list[str] = []
        for op in self.ops:
            if op.action == OpType.EQUAL:
                if include_equal:
                    lines.append(f"at pos {pos:4} {op.equal_str()}")
            elif op.action == OpType.INSERT:
                lines.append(f"at pos {pos:4} {op.right_str()}")
            elif op.action == OpType.DELETE:
                lines.append(f"at pos {pos:4} {op.left_str()}")
            elif op.action == OpType.REPLACE:
                lines.append(f"at pos {pos:4} {op.left_str()}")
                lines.append(f"       {'':4} {op.right_str()}")

            pos += len(op.left)
        return lines

    def as_diff_str(self, include_equal: bool = True) -> str:
        diff_str = "\n".join(self._diff_lines(include_equal=include_equal))
        return f"TextDiff: {self.stats()}:\n{diff_str}"

    @override
    def __str__(self):
        return self.as_diff_str()


def diff_docs(doc1: TextDoc, doc2: TextDoc) -> TokenDiff:
    """
    Calculate the LCS-style diff between two documents based on words.
    """

    diff = diff_wordtoks(list(doc1.as_wordtoks()), list(doc2.as_wordtoks()))

    # log.save_object("doc1 wordtoks", "diff_docs", "\n".join(list(doc1.as_wordtoks())))
    # log.save_object("doc2 wordtoks", "diff_docs", "\n".join(list(doc2.as_wordtoks())))
    # log.save_object("diff", "diff_docs", diff)

    return diff


@tally_calls(level="warning", min_total_runtime=5)
def diff_wordtoks(wordtoks1: list[str], wordtoks2: list[str]) -> TokenDiff:
    """
    Perform an LCS-style diff on two lists of wordtoks.
    """
    s = difflib.SequenceMatcher(None, wordtoks1, wordtoks2, autojunk=False)  # pyright: ignore
    diff: list[DiffOp] = []

    # log.message(f"Diffing {len(wordtoks1)} wordtoks against {len(wordtoks2)} wordtoks")
    # log.save_object("wordtoks1", "diff_wordtoks", "".join(wordtoks1))
    # log.save_object("wordtoks2", "diff_wordtoks", "".join(wordtoks2))
    # log.save_object("diff opcodes", "diff_wordtoks", "\n".join(str(o) for o in s.get_opcodes()))

    for tag, i1, i2, j1, j2 in s.get_opcodes():  # pyright: ignore
        if tag == "equal":
            slice1 = wordtoks1[i1:i2]
            assert slice1 == wordtoks2[j1:j2]
            diff.append(DiffOp(OpType.EQUAL, slice1, slice1))
        elif tag == "insert":
            diff.append(DiffOp(OpType.INSERT, [], wordtoks2[j1:j2]))
        elif tag == "delete":
            diff.append(DiffOp(OpType.DELETE, wordtoks1[i1:i2], []))
        elif tag == "replace":
            diff.append(DiffOp(OpType.REPLACE, wordtoks1[i1:i2], wordtoks2[j1:j2]))

    return TokenDiff(diff)


ScoredDiff: TypeAlias = tuple[float, TokenDiff]


def scored_diff_wordtoks(wordtoks1: list[str], wordtoks2: list[str]) -> ScoredDiff:
    """
    Calculate the number of wordtoks added and removed between two lists of tokens.
    Score is (wordtoks_added + wordtoks_removed) / min(len(doc1), len(doc2)),
    which is 0 for identical docs.
    """

    if len(wordtoks1) == 0 or len(wordtoks2) == 0:
        raise ValueError("Cannot score diff for empty documents")

    diff = diff_wordtoks(wordtoks1, wordtoks2)
    score = float(diff.stats().nchanges()) / min(len(wordtoks1), len(wordtoks2))
    return score, diff


@log_calls(level="message", if_slower_than=0.25)
def find_best_alignment(
    list1: list[str],
    list2: list[str],
    min_overlap: int,
    max_overlap: int | None = None,
    scored_diff: Callable[[list[str], list[str]], ScoredDiff] = scored_diff_wordtoks,
    give_up_score: float = 0.75,
    give_up_count: int = 30,
) -> tuple[int, ScoredDiff]:
    """
    Find the best alignment of two lists of values, where edit distance is smallest but overlap is
    at least min_overlap and at most max_overlap. Returns offset into list1 and diff object.
    """
    len1, len2 = len(list1), len(list2)
    best_offset = -1
    best_score = float("inf")
    best_diff = None
    max_overlap = min(len1, len2, max_overlap) if max_overlap is not None else min(len1, len2)

    if min_overlap > len1 or min_overlap > len2:
        raise ValueError(
            f"Minimum overlap {min_overlap} should never exceed the length of one of the lists ({len1}, {len2})"
        )

    log.info(
        "Finding best alignment: List lengths: lengths %s and %s with overlap of %s to %s",
        len1,
        len2,
        min_overlap,
        max_overlap,
    )

    # To make this a bit more efficient we check if we have a run of increasing scores and
    # give up if we have many in a row.
    scores_increasing = 0
    prev_score = float("-inf")

    # Slide the second list over the first list, starting from the end of the first list.
    # TODO: This could be much more efficient by being cleverer about reusing diff calculations.s
    for overlap in range(min_overlap, max_overlap + 1):
        start1 = len1 - overlap
        end1 = len1
        start2 = 0
        end2 = overlap

        score, diff = scored_diff(list1[start1:end1], list2[start2:end2])

        log.info("Offset %s: Overlap %s: Score %f", start1, overlap, score)

        if score < best_score:
            best_score = score
            best_offset = start1
            best_diff = diff
            scores_increasing = 0
        elif score >= give_up_score and score >= prev_score:
            scores_increasing += 1
            if scores_increasing >= give_up_count:
                log.info(
                    "Giving up after %s increasing scores, last score %s > %s",
                    give_up_count,
                    score,
                    give_up_score,
                )
                break

        prev_score = score

    if best_diff is None:
        raise ValueError("No alignment found")

    return best_offset, (best_score, best_diff)
