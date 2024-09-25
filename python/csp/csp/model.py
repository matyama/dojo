import os
from abc import abstractmethod
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import cast, Generic, Protocol, TypeAlias, TypeVar

from csp.constraints import (
    AllDiff,
    BinConst,
    ConstSet,
    Different,
    GreaterEq,
    GreaterThan,
    LessEq,
    LessThan,
    Same,
    Unary,
)
from csp.types import (
    Arc,
    Assignment,
    Domain,
    DomainSet,
    HasVar,
    NumValue,
    OrdValue,
    Solution,
    Value,
    Var,
    Variable,
    VarTransform,
)


class X(Generic[Variable, Value]):  # pylint: disable=invalid-name
    """Variable wrapper capable of binding into `BinConst`"""

    __match_args__ = ("var",)

    var: Variable

    def __init__(self, var: Variable) -> None:
        self.var = var

    def __or__(self, p: Callable[[Value], bool]) -> Unary[Variable, Value]:
        return Unary(x=self.var, p=p)

    def __eq__(self, y: object) -> Same[Variable, Value]:  # type: ignore
        assert isinstance(y, self.__class__)
        return Same(x=self.var, y=y.var)

    def __ne__(self, y: object) -> Different[Variable, Value]:  # type: ignore
        assert isinstance(y, self.__class__)
        return Different(x=self.var, y=y.var)


class OrdX(Generic[Variable, OrdValue], X[Variable, OrdValue]):
    def __le__(
        self, y: "OrdX[Variable, OrdValue]" | Variable
    ) -> LessEq[Variable, OrdValue]:
        return LessEq(x=self.var, y=y.var if isinstance(y, HasVar) else y)

    def __lt__(
        self, y: "OrdX[Variable, OrdValue]" | Variable
    ) -> LessThan[Variable, OrdValue]:
        return LessThan(x=self.var, y=y.var if isinstance(y, HasVar) else y)

    def __ge__(
        self, y: "OrdX[Variable, OrdValue]" | Variable
    ) -> GreaterEq[Variable, OrdValue]:
        return GreaterEq(x=self.var, y=y.var if isinstance(y, HasVar) else y)

    def __gt__(
        self, y: "OrdX[Variable, OrdValue]" | Variable
    ) -> GreaterThan[Variable, OrdValue]:
        return GreaterThan(x=self.var, y=y.var if isinstance(y, HasVar) else y)


class NumX(Generic[Variable, NumValue], OrdX[Variable, NumValue]):
    def __add__(self, y: NumValue) -> VarTransform[Variable, NumValue]:
        return VarTransform(x=self.var, f=lambda x: x + y)

    def __sub__(self, y: NumValue) -> VarTransform[Variable, NumValue]:
        return VarTransform(x=self.var, f=lambda x: x - y)

    def __mul__(self, y: NumValue) -> VarTransform[Variable, NumValue]:
        return VarTransform(x=self.var, f=lambda x: x * y)


VarDom: TypeAlias = tuple[
    Variable | HasVar[Variable], Domain[Value] | Iterable[Value]
]


class CSP(Generic[Variable, Value]):
    """CSP problem instance builder"""

    _var_ids: dict[Variable, Var]
    _vars: list[Variable]
    _doms: DomainSet[Value]
    _consts: list[dict[Var, ConstSet[Variable, Value]]]
    _global: list[AllDiff[Variable, Value]]
    _scoped_global: list[list[AllDiff[Variable, Value]]]
    # TODO: global constraints
    #  - generalize from just `AllDiff` to `GlobalConst`
    #  - either a s `_globals: list[GlobalConst]` ... `_globals[x]` includes x
    #  - or make a new dataclass ConstRef(x: Var, binary: dict, global: list)
    #    and include these as elements of `_consts`
    #  => probably better handled separately due to different inference methods
    _binary_only: bool

    def __init__(self, binary_only: bool = False) -> None:
        self._var_ids = {}
        self._vars = []
        self._doms = []
        self._consts = []
        self._global = []
        self._scoped_global = []
        self._binary_only = bool(os.environ.get("BINARY_ONLY", binary_only))

    def __iadd__(
        self,
        item: (
            VarDom[Variable, Value]
            | Iterable[VarDom[Variable, Value]]
            | BinConst[Variable, Value]
            | Unary[Variable, Value]
            | AllDiff[Variable, Value]
        ),
    ) -> "CSP[Variable, Value]":
        self._register(item)
        return self

    def _register(
        self,
        item: (
            VarDom[Variable, Value]
            | Iterable[VarDom[Variable, Value]]
            | BinConst[Variable, Value]
            | Unary[Variable, Value]
            | AllDiff[Variable, Value]
        ),
    ) -> None:
        match item:
            # NOTE: VarDom(var_dom), but mypy doesn't like type aliases here
            case tuple(var_dom):
                self._register_var(var_dom)

            case Unary(var, _):
                x = self._var_ids.get(var)
                if x is None:
                    raise ValueError(f"{var} with domain must first be added")

                # NOTE: unary constraints can be encoded by directly reducing
                #       variables's domain
                self._doms[x] = {v for v in self._doms[x] if item.p(v)}

            # TODO: generalize to global constraints
            case AllDiff(_, _, _):
                self._register_global(item)

            case xs if isinstance(xs, Iterable):
                for vd in xs:
                    # TODO: this cast makes mypy happy, but is quite sad
                    var_dom = cast(VarDom[Variable, Value], vd)
                    self += var_dom

            case const:
                self._register_binary(const)

    def _register_var(self, item: VarDom[Variable, Value]) -> None:
        x, d = item

        if isinstance(x, HasVar):
            x = x.var

        # materialize domain if necessary
        if not isinstance(d, set):
            d = set(d)

        x_var = self._var_ids.get(x)
        if x_var is not None:
            self._doms[x_var] = d
        else:
            self._var_ids[x] = len(self._vars)
            self._vars.append(x)
            self._doms.append(d)
            self._consts.append({})
            self._scoped_global.append([])

            assert len(self._consts) == len(self._vars)

    def _register_binary(self, item: BinConst[Variable, Value]) -> None:
        var_a, var_b = item.vars
        # NOTE: asserts that a, b have been registered before
        a, b = self.var(var_a), self.var(var_b)
        # NOTE: pylint seems to be quite confused (`Var: TypeAlias = int`)
        # pylint: disable=invalid-sequence-index
        acc = self._consts[a].get(b, ConstSet(var_a, var_b))
        acc &= item
        self._consts[a][b] = acc
        self._consts[b][a] = acc

    def _register_global(self, item: AllDiff[Variable, Value]) -> None:
        if self._binary_only:
            # TODO: transforming other global constraints is not so simple
            for c in item.iter_binary():
                self += c
        else:
            # TODO: check if item already exists between globals
            self._global.append(item)
            for x in map(self.var, item.scope):
                self._scoped_global[x].append(item)

    @property
    def num_vars(self) -> int:
        return len(self._vars)

    @property
    def num_vals(self) -> int:
        return len({v for d in self._doms for v in d})

    @property
    def domains(self) -> Sequence[Domain[Value]]:
        return self._doms

    @property
    def variables(self) -> Sequence[Variable]:
        return self._vars

    @property
    def vars(self) -> Mapping[Variable, Var]:
        return self._var_ids

    @property
    def consts(self) -> Sequence[Mapping[Var, ConstSet[Variable, Value]]]:
        return self._consts

    # TODO: generalize AllDiff => GlobalConst
    @property
    def globals(self) -> Sequence[AllDiff[Variable, Value]]:
        return self._global

    # XXX: used only in tests
    def const(
        self, x: Variable, y: Variable
    ) -> BinConst[Variable, Value] | None:
        var_x, var_y = self.var(x), self.var(y)
        # NOTE: pylint seems to be quite confused (`Var: TypeAlias = int`)
        # pylint: disable=invalid-sequence-index
        return self._consts[var_x].get(var_y)

    def arc(self, x: Var, y: Var) -> Arc[Variable]:
        return self._vars[x], self._vars[y]

    def __getitem__(self, x: Variable) -> X[Variable, Value]:
        """Create new `Variable` wrapper `X` and bind the `Value` type to it"""
        return X(var=x)

    def __setitem__(
        self,
        x: Variable | HasVar[Variable],
        d: Domain[Value] | Iterable[Value],
    ) -> None:
        """Alterative syntax for `csp += x, d`"""
        self += x, d

    # XXX: might not be necessary anymore or used just internally for Assign.
    def variable(self, i: Var) -> Variable:
        return self._vars[i]

    def var(self, x: Variable | X[Variable, Value]) -> Var:
        match x:
            case X(var):
                return self._var_ids[var]
            case var:
                return self._var_ids[var]

    def iter_vars(self) -> Iterable[Var]:
        return range(len(self._vars))

    # XXX: does Problem concern about Assignment?
    # TODO: extract outside => use `domains` property?
    def init(self) -> "AssignCtx[Value]":
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

        return AssignCtx(assignment, unassigned)

    def as_solution(self, a: Assignment[Value]) -> Solution[Variable, Value]:
        return {self.variable(x): v for x, v in a.items()}

    def complete(self, a: Assignment[Value]) -> bool:
        return len(a) == self.num_vars

    def consistent(self, x: Var, x_val: Value, a: Assignment[Value]) -> bool:
        """
        Check if x := x_val is consistent with assignment a under constraints.

        Note: Re-assignment of a variable is considered consistent.
        """
        # globally consistent

        # TODO: assignment = itertools.chain([assign], map(..., a.items()))
        #  - if re-assignment is not possible, otherwise leave this
        assignment = {self.variable(i): v for i, v in a.items()}
        assignment[self.variable(x)] = x_val

        if not all(c(assignment.items()) for c in self._scoped_global[x]):
            return False

        # binary consistent
        return all(
            c(self.arc(x, y), x_val, y_val)
            for y, c in self._consts[x].items()
            if (y_val := a.get(y)) is not None
        )


class OrdCSP(Generic[Variable, OrdValue], CSP[Variable, OrdValue]):
    """CSP builder that provides binders for variables that support OrdValue"""

    def __iadd__(
        self,
        item: (
            VarDom[Variable, OrdValue]
            | Iterable[VarDom[Variable, OrdValue]]
            | BinConst[Variable, OrdValue]
            | Unary[Variable, OrdValue]
            | AllDiff[Variable, OrdValue]
        ),
    ) -> "OrdCSP[Variable, OrdValue]":
        self._register(item)
        return self

    def __getitem__(self, x: Variable) -> OrdX[Variable, OrdValue]:
        """
        Create new `Variable` wrapper `OrdX` and bind the `OrdValue` type to it
        """
        return OrdX(var=x)


class NumCSP(Generic[Variable, NumValue], OrdCSP[Variable, NumValue]):
    """CSP builder that provides binders for variables that support NumValue"""

    def __iadd__(
        self,
        item: (
            VarDom[Variable, NumValue]
            | Iterable[VarDom[Variable, NumValue]]
            | BinConst[Variable, NumValue]
            | Unary[Variable, NumValue]
            | AllDiff[Variable, NumValue]
        ),
    ) -> "NumCSP[Variable, NumValue]":
        self._register(item)
        return self

    def __getitem__(self, x: Variable) -> NumX[Variable, NumValue]:
        """
        Create new `Variable` wrapper `NumX` and bind the `NumValue` type to it
        """
        return NumX(var=x)


@dataclass(frozen=True)
class Assign(Generic[Value]):
    var: Var
    val: Value

    def __rshift__(self, domains: Sequence[Domain[Value]]) -> DomainSet[Value]:
        # XXX: deep-copy! (note: not fully deep, but copies all the sets)
        # deepcopy domain set
        domains = [set(d) for d in domains]
        domains[self.var] = {self.val}
        return domains


@dataclass
class AssignCtx(Generic[Value]):
    assignment: Assignment[Value]
    unassigned: list[bool]


I_contra = TypeVar("I_contra", contravariant=True)
S_co = TypeVar("S_co", covariant=True)


class Model(Protocol, Generic[I_contra, S_co, Variable, Value]):
    @abstractmethod
    def into_csp(self, instance: I_contra) -> CSP[Variable, Value]:
        raise NotImplementedError

    @abstractmethod
    def from_csp(self, solution: Solution[Variable, Value]) -> S_co:
        raise NotImplementedError
