from abc import ABC, abstractmethod
from typing import Any, Iterable, Tuple, TypeAlias, TypeVar


T = TypeVar("T")

Match: TypeAlias = Tuple[T, int, int]
"""Match, index, and offset."""


class Extractor(ABC):
    """
    Abstract base class for extractors that extract information from a document at a given location.
    We use a class not a pure function since we may need to preprocess the document.
    """

    def __init__(self, doc_str: str):
        self.doc_str = doc_str

    @abstractmethod
    def extract_all(self) -> Iterable[Match[Any]]:
        pass

    @abstractmethod
    def extract_preceding(self, wordtok_offset: int) -> Match[Any]:
        pass
