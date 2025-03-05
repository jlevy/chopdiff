from abc import ABC, abstractmethod
from typing import Iterable, Tuple, TypeAlias, TypeVar


T = TypeVar("T")

Match: TypeAlias = Tuple[T, int, int]
"""Match, index, and offset of content found by an extractor."""


class ContentNotFound(ValueError):
    """
    Exception raised when content is not found by an extractor.
    """


class Extractor[T](ABC):
    """
    Abstract base class for extractors that extract information from a document at a
    given location. We use a class and not a pure function since we may need to
    preprocess the document.
    """

    @abstractmethod
    def extract_all(self) -> Iterable[Match[T]]:
        pass

    @abstractmethod
    def extract_preceding(self, wordtok_offset: int) -> Match[T]:
        pass
