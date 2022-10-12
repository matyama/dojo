from abc import abstractmethod
from collections import deque
from dataclasses import dataclass
from typing import Generic, Optional, Protocol, Sequence, TypeVar

from csp.constraints import BinConst
from csp.model import Assign, Problem
from csp.types import Domain, DomainSet, Value, Var, Variable

C_contra = TypeVar("C_contra", contravariant=True)


# TODO: impl other AC algs => decide on the interface
class Inference(Protocol, Generic[C_contra, Value]):  # pylint: disable=R0903
    @abstractmethod
    def infer(self, var: Var, ctx: C_contra) -> Optional[DomainSet[Value]]:
        raise NotImplementedError


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

    # XXX: procedure => mutates `domain_x` => document
    def _revise(
        self,
        domain_x: Domain[Value],
        domain_y: Domain[Value],
        const_xy: BinConst[Variable, Value],
    ) -> bool:
        """
        Note: All binary constraints should be combined into one composed
        constraint - see `CompositeConst`.
        """
        deleted = False
        # XXX: list -> another shallow copy, and called inside `while queue`
        for x_val in list(domain_x):
            # Ban x_val if there's no possible y_val consistent with const_xy
            if all(not const_xy.sat(x_val, y_val) for y_val in domain_y):
                domain_x.remove(x_val)
                deleted = True
        return deleted

    def _check_consistency(
        self,
        assignment: Assign[Value],
        revised_domains: Sequence[Domain[Value]],
        unassigned: Sequence[bool],
    ) -> Optional[DomainSet[Value]]:
        revised_domains = assignment >> revised_domains
        var = assignment.var

        # For maintaining AC it's enough to consider remaining neighbors of var
        queue = deque((x, var) for x in self._consts[var] if unassigned[x])

        while queue:
            x, y = queue.popleft()
            if self._revise(
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
            revised_domains=ctx.domains,
            unassigned=ctx.unassigned,
        )
