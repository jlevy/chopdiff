from typing import Callable, List, Tuple, TypeAlias, Union


Predicate: TypeAlias = Union[Callable[[str], bool], List[str]]


class _TokenSearcher:
    def __init__(self, toks: List[str]):
        self.toks = toks
        self._cur_idx = 0

    def at(self, index: int):
        if index is None:
            raise KeyError("Index cannot be None")
        # Convert negative indices to positive ones.
        self._cur_idx = index if index >= 0 else len(self.toks) + index
        return self

    def start(self):
        self._cur_idx = 0
        return self

    def end(self):
        self._cur_idx = len(self.toks)
        return self

    def seek_back(self, predicate: Predicate):
        if isinstance(predicate, list):
            allowed: List[str] = predicate
            predicate = lambda x: x in allowed
        for idx in range(self._cur_idx - 1, -1, -1):
            if predicate(self.toks[idx]):
                self._cur_idx = idx
                return self
        raise KeyError("No matching token found before the current index")

    def seek_forward(self, predicate: Predicate):
        if isinstance(predicate, list):
            allowed: List[str] = predicate
            predicate = lambda x: x in allowed
        for idx in range(self._cur_idx + 1, len(self.toks)):
            if predicate(self.toks[idx]):
                self._cur_idx = idx
                return self
        raise KeyError("No matching token found after the current index")

    def prev(self):
        if self._cur_idx - 1 < 0:
            raise KeyError("No previous token available")
        self._cur_idx -= 1
        return self

    def next(self):
        if self._cur_idx + 1 >= len(self.toks):
            raise KeyError("No next token available")
        self._cur_idx += 1
        return self

    def get_index(self) -> int:
        return self._cur_idx

    def get_token(self) -> Tuple[int, str]:
        return self._cur_idx, self.toks[self._cur_idx]


def search_tokens(wordtoks: List[str]) -> _TokenSearcher:
    """
    Fluent convenience function to search for offsets in an array of string tokens
    based on a predicate, previous, next, etc. Raises `KeyError` if any search
    has no matches.

    Example:
    ```
    index, token = (
        search_tokens(list_of_tokens)
            .at(my_offset)
            .seek_back(has_timestamp)
            .next()
            .get_token()
    )
    ```
    """
    return _TokenSearcher(wordtoks)
