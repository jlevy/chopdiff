"""Tests for thread safety utilities."""

import time
from concurrent.futures import ThreadPoolExecutor
from threading import RLock

import pytest

from chopdiff.flex.thread_utils import synchronized


class TestSynchronizedDecorator:
    """Test the synchronized decorator."""

    def test_basic_synchronization(self):
        """Test basic method synchronization."""

        class Counter:
            def __init__(self):
                self._lock = RLock()
                self.count = 0

            @synchronized()
            def increment(self):
                # Simulate some work
                current = self.count
                time.sleep(0.001)  # Small delay to increase chance of race condition
                self.count = current + 1

        counter = Counter()

        # Run multiple threads incrementing the counter
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(counter.increment) for _ in range(100)]
            for future in futures:
                future.result()

        # Without synchronization, we'd likely see count < 100 due to race conditions
        assert counter.count == 100

    def test_custom_lock_attribute(self):
        """Test using custom lock attribute name."""

        class SafeBox:
            def __init__(self):
                self.my_special_lock = RLock()
                self.items = []

            @synchronized(lock_attr="my_special_lock")
            def add_item(self, item):
                self.items.append(item)

            @synchronized(lock_attr="my_special_lock")
            def get_items(self):
                return list(self.items)

        box = SafeBox()

        # Add items from multiple threads
        def add_numbers():
            for i in range(10):
                box.add_item(i)

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(add_numbers) for _ in range(5)]
            for future in futures:
                future.result()

        items = box.get_items()
        assert len(items) == 50
        # Each number 0-9 should appear exactly 5 times
        for i in range(10):
            assert items.count(i) == 5

    def test_missing_lock_attribute(self):
        """Test error when lock attribute is missing."""

        class BadClass:
            @synchronized()
            def method(self):
                pass

        obj = BadClass()
        with pytest.raises(AttributeError):
            obj.method()

    def test_wrong_lock_type(self):
        """Test error when lock attribute is not an RLock."""

        class WrongLockType:
            def __init__(self):
                self._lock = "not a lock"

            @synchronized()
            def method(self):
                pass

        obj = WrongLockType()
        with pytest.raises(AttributeError, match="Expected RLock"):
            obj.method()

    def test_reentrant_lock(self):
        """Test that RLock allows reentrant calls."""

        class ReentrantClass:
            def __init__(self):
                self._lock = RLock()
                self.call_count = 0

            @synchronized()
            def outer_method(self):
                self.call_count += 1
                return self.inner_method()

            @synchronized()
            def inner_method(self):
                self.call_count += 1
                return self.call_count

        obj = ReentrantClass()
        result = obj.outer_method()

        # Both methods should have been called
        assert result == 2
        assert obj.call_count == 2

    def test_exception_handling(self):
        """Test that lock is released even when exception occurs."""

        class ExceptionClass:
            def __init__(self):
                self._lock = RLock()
                self.call_count = 0

            @synchronized()
            def failing_method(self):
                self.call_count += 1
                raise ValueError("Test exception")

            @synchronized()
            def normal_method(self):
                self.call_count += 1
                return self.call_count

        obj = ExceptionClass()

        # Method should fail
        with pytest.raises(ValueError):
            obj.failing_method()

        # Should have been called once
        assert obj.call_count == 1

        # Can still call other synchronized methods (lock was released)
        result = obj.normal_method()
        assert result == 2

        # Can call multiple times
        result = obj.normal_method()
        assert result == 3

    def test_method_attributes_preserved(self):
        """Test that decorated method preserves attributes."""

        class DocClass:
            def __init__(self):
                self._lock = RLock()

            @synchronized()
            def documented_method(self, x: int, y: int) -> int:
                """Add two numbers."""
                return x + y

        obj = DocClass()

        # Check that docstring is preserved
        assert obj.documented_method.__doc__ == "Add two numbers."

        # Check that name is preserved
        assert obj.documented_method.__name__ == "documented_method"

    def test_concurrent_access_patterns(self):
        """Test various concurrent access patterns."""

        class SharedResource:
            def __init__(self):
                self._lock = RLock()
                self.data = {}
                self.read_count = 0
                self.write_count = 0

            @synchronized()
            def write(self, key, value):
                self.write_count += 1
                time.sleep(0.001)  # Simulate work
                self.data[key] = value

            @synchronized()
            def read(self, key):
                self.read_count += 1
                time.sleep(0.001)  # Simulate work
                return self.data.get(key)

            @synchronized()
            def read_write(self, key, transform):
                old_value = self.read(key)
                new_value = transform(old_value)
                self.write(key, new_value)
                return new_value

        resource = SharedResource()

        def worker(worker_id):
            # Each worker does some reads and writes
            for i in range(5):
                resource.write(f"worker_{worker_id}_item_{i}", i)
                resource.read(f"worker_{worker_id}_item_{i}")

                # Test reentrant operation
                resource.read_write("shared_counter", lambda x: (x or 0) + 1)

        # Run workers concurrently
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker, i) for i in range(10)]
            for future in futures:
                future.result()

        # Verify results
        assert resource.read("shared_counter") == 50  # 10 workers * 5 increments
        assert resource.write_count >= 50
        assert resource.read_count >= 50

        # Verify each worker's data
        for worker_id in range(10):
            for i in range(5):
                key = f"worker_{worker_id}_item_{i}"
                assert resource.read(key) == i
