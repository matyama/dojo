import logging
import multiprocessing as mp
import sys
from types import TracebackType


class recursionlimit:
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


def create_logger(
    name: str = "csp", level: int | str = logging.INFO, use_mp: bool = False
) -> logging.Logger:
    logger = mp.get_logger() if use_mp else logging.getLogger(name=name)

    logger.setLevel(level)

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)8s] [%(processName)18s] %(message)s"
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    if not logger.handlers:
        logger.addHandler(handler)

    return logger
