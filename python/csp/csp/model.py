from abc import abstractmethod
from dataclasses import dataclass
from typing import (
    Dict,
    Generic,
    Iterable,
    List,
    Mapping,
    Optional,
    Protocol,
    Sequence,
    Tuple,
    TypeVar,
)

from csp.constraints import BinConst, ConstSet, Different, LessEq
from csp.types import Assignment, Domain, DomainSet, Value, Var, Variable


class VarCombinator(Generic[Variable, Value]):
    _var: Variable
    _csp: "Problem[Variable, Value]"

    def __init__(self, x: Variable, csp: "Problem[Variable, Value]") -> None:
        self._var = x
        self._csp = csp

    def __ne__(self, y: object) -> Different[Variable, Value]:  # type: ignore
        assert isinstance(y, self.__class__)
        return Different(x=self._var, y=y._var)

    # XXX: this combinator should only be available to OrdValue
    #  - check dynamically => somehow reveal LessEq[OrdValue]
    #  - assert statically => probably requires splitting VarCombinator
    #  - NOTE: CSP instance always has _single_ concrete Value
    def __le__(
        self, y: "VarCombinator[Variable, Value]"
    ) -> LessEq[Variable, Value]:
        return LessEq(x=self._var, y=y._var)


@dataclass(frozen=True)
class Vars(Generic[Variable, Value]):
    var_iter: Iterable[Tuple[Variable, Domain[Value]]]


class Problem(Generic[Variable, Value]):
    """CSP problem instance builder"""

    _var_ids: Dict[Variable, Var]
    _vars: List[Variable]
    _doms: DomainSet[Value]
    _consts: List[Dict[Var, ConstSet[Variable, Value]]]

    def __init__(self) -> None:
        self._var_ids = {}
        self._vars = []
        self._doms = []
        self._consts = []

    # TODO: extensions:
    #  - accept unary constraints => filter out domain instead of adding to
    #    const
    #  - accept initial assignment => trivial unary constraint

    # TODO: accept Const instances defined over Variable for convenience
    def __iadd__(
        self,
        item: Tuple[Variable, Domain[Value]]
        | Vars[Variable, Value]
        | BinConst[Variable, Value],
    ) -> "Problem[Variable, Value]":
        # TODO: use `match item`: case (x, d) ..case Vars(var_iter) ..case c
        #  - mypy seems to have an issue parsing this match => crash
        if isinstance(item, tuple):
            x, d = item
            assert x not in self._var_ids, f"x{x} already recorded"
            self._var_ids[x] = len(self._vars)
            self._vars.append(x)
            self._doms.append(d)
            self._consts.append({})
            assert len(self._consts) == len(self._vars)
        elif isinstance(item, Vars):
            for var_dom in item.var_iter:
                self += var_dom
        else:
            var_a, var_b = item.vars  # type: Tuple[Variable, Variable]
            # NOTE: asserts that a, b have been registered before
            a, b = self.var(var_a), self.var(var_b)
            acc = self._consts[a].get(b, ConstSet(var_a, var_b))
            acc &= item
            self._consts[a][b] = acc
            self._consts[b][a] = acc

        return self

    @property
    def num_vars(self) -> int:
        return len(self._vars)

    @property
    def domains(self) -> Sequence[Domain[Value]]:
        return self._doms

    @property
    def consts(self) -> Sequence[Mapping[Var, ConstSet[Variable, Value]]]:
        return self._consts

    # XXX: might not be necessary anymorea or used just internally for Assign.
    def variable(self, i: Var) -> Variable:
        return self._vars[i]

    def var_comb(self, x: Variable) -> VarCombinator[Variable, Value]:
        return VarCombinator(x=x, csp=self)

    def var(self, x: Variable) -> Var:
        return self._var_ids[x]

    def iter_vars(self) -> Iterable[Var]:
        return range(len(self._vars))

    # XXX: does Problem concern about Assignment?
    # TODO: extract outside => use `domains` property?
    def init(self) -> "Solution[Value]":
        """
        Generate an initial assignment and an indicator of unassigned variables
        """
        assignment = {
            var: next(iter(domain))
            for var, domain in enumerate(self._doms)
            if len(domain) == 1
        }

        # XXX: consider numpy => https://stackoverflow.com/a/13052254
        #  - only add this dependency if it's gonna be used somewhere else
        #  - alternatively, this could be an array (fixed-size) ...from iter
        unassigned = [x not in assignment for x in self.iter_vars()]

        return Solution(assignment, unassigned)

    def complete(self, a: Assignment[Value]) -> bool:
        return len(a) == self.num_vars

    def consistent(
        self,
        x: Var,
        x_val: Value,
        a: Assignment[Value],
    ) -> bool:
        """
        Check if x := x_val is consistent with assignment a under constraints.

        Note: Re-assignment of a variable is considered consistent.
        """
        return all(
            c.sat(x_val, y_val)
            for y, c in self._consts[x].items()
            if (y_val := a.get(y)) is not None
        )


@dataclass(frozen=True)
class Assign(Generic[Value]):
    var: Var
    val: Value

    def __rshift__(self, domains: Sequence[Domain[Value]]) -> DomainSet[Value]:
        # XXX: deep-copy!
        # deepcopy domain set
        domains = [set(d) for d in domains]
        domains[self.var] = {self.val}
        return domains


@dataclass
class Solution(Generic[Value]):
    assignment: Assignment[Value]
    unassigned: List[bool]


I_contra = TypeVar("I_contra", contravariant=True)
S_co = TypeVar("S_co", covariant=True)


class Model(Protocol, Generic[I_contra, S_co, Variable, Value]):
    @abstractmethod
    def into_csp(self, instance: I_contra) -> Problem[Variable, Value]:
        raise NotImplementedError

    # TODO: consider just Assignment = Dict[Variable, Value]
    @abstractmethod
    def from_csp(
        self, csp_solution: Assignment[Value], csp: Problem[Variable, Value]
    ) -> S_co:
        raise NotImplementedError

    def try_from_csp(
        self,
        solution: Optional[Assignment[Value]],
        csp: Problem[Variable, Value],
    ) -> Optional[S_co]:
        return self.from_csp(solution, csp) if solution is not None else None
