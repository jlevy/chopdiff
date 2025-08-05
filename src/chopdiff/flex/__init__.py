# flake8: noqa: F401
"""Flexible document interface with lazy loading."""

from chopdiff.flex.flex_doc import FlexDoc
from chopdiff.flex.thread_utils import synchronized

__all__ = ["synchronized", "FlexDoc"]
