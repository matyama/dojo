from abc import abstractmethod
from collections import deque
from typing import (
    Generic,
    Iterable,
    Optional,
    Protocol,
    Sequence,
    TypeAlias,
    TypeVar,
)

from csp.constraints import BinConst
from csp.model import Assign, Problem
from csp.types import (
    Arc,
    Domain,
    DomainSet,
    DomainSetMut,
    Value,
    Var,
    VarArc,
    Variable,
)

C_contra = TypeVar("C_contra", contravariant=True)
I_co = TypeVar("I_co", covariant=True)


# TODO: impl other AC algs => decide on the interface
#  - Alternative API: infer(Assign, C) -> C ... C ~ generic inference ctx
class Inference(
    Protocol, Generic[C_contra, I_co, Value]
):  # pylint: disable=R0903
    @abstractmethod
    def infer(self, assign: Assign[Value], ctx: C_contra) -> Optional[I_co]:
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


AC3Context: TypeAlias = Sequence[Domain[Value]]


# XXX: explicitly subclass Inference?
#      `Generic[Value], Inference[AC3Context[Value], DomainSet[Value], Value]`
class AC3(Generic[Variable, Value]):  # pylint: disable=R0903
    # XXX: consider making consts and vars args
    #  => indicate that domains won't be used (should be passed to __call__)
    def __init__(self, csp: Problem[Variable, Value]) -> None:
        self._consts = csp.consts
        self._vars = csp.variables

    def _arc(self, x: Var, y: Var) -> Arc[Variable]:
        return self._vars[x], self._vars[y]

    @property
    def arc_iter(self) -> Iterable[VarArc]:
        return ((x, y) for x, ys in enumerate(self._consts) for y in ys)

    # TODO: generalize arcs to | Iterable[Arc[Variable]]
    def __call__(
        self,
        arcs: Iterable[VarArc],
        domains: Sequence[Domain[Value]] | DomainSetMut[Value],
    ) -> Optional[DomainSet[Value]]:

        match domains:
            case DomainSetMut(ds):
                revised_domains = ds
            case ds:
                revised_domains = [set(d) for d in ds]

        queue = deque(arcs)

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
        self, assign: Assign[Value], ctx: AC3Context[Value]
    ) -> Optional[DomainSet[Value]]:
        return self(
            arcs=self.arc_iter,
            domains=DomainSetMut(assign >> ctx),
        )
