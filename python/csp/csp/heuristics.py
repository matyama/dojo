from abc import abstractmethod
from operator import itemgetter
from typing import AbstractSet, Generic, Protocol, Sequence

from csp.types import Domain, Value, Var


class VarSelect(Protocol, Generic[Value]):  # pylint: disable=R0903
    @abstractmethod
    def __call__(
        self, remaining: Sequence[bool], domains: Sequence[Domain[Value]]
    ) -> Var:
        raise NotImplementedError


class MRV(Generic[Value], VarSelect[Value]):  # pylint: disable=R0903
    """
    Min. remaining value (MRV) selection.

    Tie-breaker (degree heuristic): Choose the variable with the most
    constraints on remaining variables.
    """

    # domain size then most constraints
    _key = itemgetter(1, 2)

    def __init__(self, consts: Sequence[AbstractSet[Var]]) -> None:
        self._consts = consts

    def _active_degree(self, x: Var, remaining: Sequence[bool]) -> int:
        return len([y for y in self._consts[x] if remaining[y]])

    def __call__(
        self, remaining: Sequence[bool], domains: Sequence[Domain[Value]]
    ) -> Var:
        var, _, _ = min(
            (
                (x, len(d), -self._active_degree(x, remaining))
                for x, d in enumerate(domains)
                if remaining[x]
            ),
            key=self._key,
        )
        return var
