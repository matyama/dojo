from abc import abstractmethod
from collections.abc import Iterable, Mapping, Sequence
from operator import itemgetter
from typing import Generic, Protocol

from csp.constraints import ConstSet
from csp.model import CSP
from csp.types import Domain, Value, Var, Variable


class VarSelect(Protocol, Generic[Value]):  # pylint: disable=R0903
    @abstractmethod
    def __call__(
        self, remaining: Sequence[bool], domains: Sequence[Domain[Value]]
    ) -> Var:
        raise NotImplementedError


class MRV(Generic[Variable, Value], VarSelect[Value]):  # pylint: disable=R0903
    """
    Min. remaining value (MRV) selection.

    Tie-breaker (degree heuristic): Choose the variable with the most
    constraints on remaining variables.
    """

    # domain size then most constraints
    _key = itemgetter(1, 2)
    _consts: Sequence[set[Var]]

    def __init__(self, csp: CSP[Variable, Value]) -> None:
        self._consts = [set(cs.keys()) for cs in csp.consts]
        # TODO: compute degree on globals, don't turn them into binary
        pairs = (b.vars for c in csp.globals for b in c.iter_binary())
        for x_var, y_var in pairs:
            x, y = csp.var(x_var), csp.var(y_var)
            self._consts[x].add(y)
            self._consts[y].add(x)

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


class DomainSort(Protocol, Generic[Value]):  # pylint: disable=R0903
    @abstractmethod
    def __call__(
        self,
        x: Var,
        domains: Sequence[Domain[Value]],
        unassigned: Sequence[bool],
    ) -> Iterable[Value]:
        raise NotImplementedError


class LeastConstraining(Generic[Variable, Value], DomainSort[Value]):  # pylint: disable=too-few-public-methods
    """
    Heuristic which yields values from the domain of given variable x in order
    of the "least constraining" values.

    This means that the value that rules out the fewest values in the remaining
    variables (involved in constraints with x) is returned first.

    Runs in `O(|C(x, u)|*|D_x|*|D_y|)` time where
     - `|C(x, u)|` is the number of constraints between x and its neighbors u
       which have not yet been assigned a value
     - `|D_i|` is the current domain size of variable i
    """

    _consts: Sequence[Mapping[Var, ConstSet[Variable, Value]]]

    def __init__(self, csp: CSP[Variable, Value]) -> None:
        self._vars = csp.variables
        # TODO: hack that works for alldiff but is inefficient and not general
        # self._consts = csp.consts
        consts = [
            {y: ConstSet(x=c.x, y=c.y, cs=list(c.cs)) for y, c in cs.items()}
            for cs in csp.consts
        ]
        bin_consts = (b for c in csp.globals for b in c.iter_binary())
        for c in bin_consts:
            x_var, y_var = c.vars
            x, y = csp.var(x_var), csp.var(y_var)
            acc = consts[x].get(y, ConstSet(x_var, y_var))
            acc &= c
            consts[x][y] = acc
            consts[y][x] = acc

        self._consts = consts

    def __call__(
        self,
        x: Var,
        domains: Sequence[Domain[Value]],
        unassigned: Sequence[bool],
    ) -> Iterable[Value]:
        x_var = self._vars[x]
        consts_x = [
            (y, self._vars[y], c)
            for y, c in self._consts[x].items()
            if unassigned[y]
        ]

        def count_inconsistent(x_val: Value) -> int:
            return sum(
                1
                for y, y_var, c in consts_x
                for y_val in domains[y]
                if not c(arc=(x_var, y_var), x_val=x_val, y_val=y_val)
            )

        sorted_domain = sorted(
            ((x_val, count_inconsistent(x_val)) for x_val in domains[x]),
            key=itemgetter(1),
        )

        for x_val, _ in sorted_domain:
            yield x_val
