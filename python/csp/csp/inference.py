from abc import abstractmethod
from collections import deque
from dataclasses import dataclass
from typing import (
    Generic,
    Iterable,
    Optional,
    Protocol,
    Sequence,
    Tuple,
    TypeVar,
)

from csp.constraints import BinConst
from csp.model import Assign, Problem
from csp.types import Arc, Domain, DomainSet, Value, Var, Variable

C_contra = TypeVar("C_contra", contravariant=True)


# TODO: impl other AC algs => decide on the interface
class Inference(Protocol, Generic[C_contra, Value]):  # pylint: disable=R0903
    @abstractmethod
    def infer(self, var: Var, ctx: C_contra) -> Optional[DomainSet[Value]]:
        raise NotImplementedError


def revise(
    arc: Arc[Variable],
    domain_x: Domain[Value],
    domain_y: Domain[Value],
    const_xy: BinConst[Variable, Value],
) -> bool:
    """
    Procedure that deletes any value from `domain_x` which is inconsistent
    with values from `domain_y` under constraints represented by `const_xy`.

    Returns: True iff `domain_x` has been changed.
    Complexity: O(d^2) where d is the max domain size

    WARN: If a call to `revise` returns True, the contents of `domain_x` has
    been modified (some entries were removed). Otherwise, it's kept unchanged.

    Note: All binary constraints should be combined into one composed
    constraint - see `CompositeConst`.
    """
    deleted = False
    # XXX: list -> another shallow copy, and called inside `while queue`
    for x_val in list(domain_x):
        # Ban x_val if there's no possible y_val consistent with const_xy
        if all(not const_xy(arc, x_val, y_val) for y_val in domain_y):
            domain_x.remove(x_val)
            deleted = True
    return deleted


# TODO: it's not clear wheter to include value or make the assumption that
#       the state of `domains` must already correspond to the state of
#       `unassigned`
#  - the issue here is that `revise`/`ac3` modifies the input domains
#  => so these must be deep-copied beforehand for the case when inference fails
#     (i.e. rollback)
@dataclass(frozen=True)
class AC3Context(Generic[Value]):
    value: Value
    domains: Sequence[Domain[Value]]
    unassigned: Sequence[bool]


# XXX: explicitly subclass Inference?
#      `Generic[Value], Inference[AC3Context[Value], Value]`
class AC3(Generic[Variable, Value]):  # pylint: disable=R0903
    def __init__(self, csp: Problem[Variable, Value]) -> None:
        self._consts = csp.consts
        self._vars = csp.variables

    def _arc(self, x: Var, y: Var) -> Arc[Variable]:
        return self._vars[x], self._vars[y]

    # TODO: AC3 input is just a set of arcs/edges, assignment info is optional
    def __call__(
        self, arcs: Iterable[Arc[Variable]] | Iterable[Tuple[Var, Var]]
    ) -> Optional[DomainSet[Value]]:
        # TODO
        return None

    def _check_consistency(
        self,
        assignment: Assign[Value],
        domains: Sequence[Domain[Value]],
        unassigned: Sequence[bool],
    ) -> Optional[DomainSet[Value]]:
        revised_domains = assignment >> domains
        var = assignment.var

        # For maintaining AC it's enough to consider remaining neighbors of var
        queue = deque((x, var) for x in self._consts[var] if unassigned[x])

        while queue:
            x, y = queue.popleft()
            if revise(
                arc=self._arc(x, y),
                domain_x=revised_domains[x],
                domain_y=revised_domains[y],
                const_xy=self._consts[x][y],
            ):
                if not revised_domains[x]:
                    return None
                # Add arcs (z, x) for all constraints x -> z for z other than y
                queue.extend((z, x) for z in self._consts[x] if z != y)

        return revised_domains

    def infer(
        self, var: Var, ctx: AC3Context[Value]
    ) -> Optional[DomainSet[Value]]:
        assert not ctx.unassigned[var], f"x{var} should be assigned in {ctx}"
        return self._check_consistency(
            assignment=Assign(var=var, val=ctx.value),
            domains=ctx.domains,
            unassigned=ctx.unassigned,
        )
