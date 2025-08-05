"""Thread safety utilities for FlexDoc."""

from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar, cast

T = TypeVar("T", bound=Callable[..., Any])


def synchronized(lock_attr: str = "_lock") -> Callable[[T], T]:
    """
    Decorator for thread-safe method access using an instance lock.

    This decorator acquires a lock before executing the decorated method
    and releases it afterwards. The lock must be an attribute of the
    instance (default name: '_lock').

    Args:
        lock_attr: Name of the lock attribute on the instance

    Returns:
        Decorator function

    Example:
        ```python
        class ThreadSafeClass:
            def __init__(self):
                self._lock = RLock()
                self._data = None

            @synchronized()
            def get_data(self):
                if self._data is None:
                    self._data = expensive_operation()
                return self._data
        ```
    """

    def decorator(func: T) -> T:
        @wraps(func)
        def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            lock = getattr(self, lock_attr)
            # Check if it's a lock-like object (has acquire/release methods)
            if not (
                hasattr(lock, "acquire") and hasattr(lock, "release") and hasattr(lock, "__enter__")
            ):
                raise AttributeError(f"Expected RLock at {lock_attr}, got {type(lock).__name__}")
            with lock:
                return func(self, *args, **kwargs)

        return cast(T, wrapper)

    return decorator
