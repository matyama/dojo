import sys
from types import TracebackType


class recursionlimit:  # pylint: disable=invalid-name
    _limit: int
    _old_limit: int

    def __init__(self, limit: int, non_decreasing: bool = False) -> None:
        assert limit > 0, "recursion limit must be a positive int"
        self._limit = limit
        self._old_limit = limit
        self._non_decreasing = non_decreasing

    def __enter__(self) -> "recursionlimit":
        self._old_limit = sys.getrecursionlimit()
        new_limit = (
            max(self._old_limit, self._limit)
            if self._non_decreasing
            else self._limit
        )
        sys.setrecursionlimit(new_limit)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        sys.setrecursionlimit(self._old_limit)
