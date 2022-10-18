import operator
from abc import abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from itertools import combinations
from typing import Callable, Generic, Iterable, List, Protocol, Tuple

from csp.types import (
    Arc,
    HasVar,
    NumValue,
    Ord,
    OrdValue,
    Value,
    Variable,
    VarTransform,
)


class BinConst(Protocol, Generic[Variable, Value]):
    @property
    @abstractmethod
    def vars(self) -> Tuple[Variable, Variable]:
        """
        If self represents relation C(x, y) then this property returns (x, y).
        """
        raise NotImplementedError

    @abstractmethod
    def _sat(self, x_val: Value, y_val: Value) -> bool:
        """Returns True iff x := x_val is consistent with y := y_val"""
        raise NotImplementedError

    @abstractmethod
    def __str__(self) -> str:
        raise NotImplementedError

    def __call__(self, arc: Arc[Variable], x_val: Value, y_val: Value) -> bool:
        """Same as `sat` but automatically swaps values based on `arc`"""
        # NOTE: apply values in order given by the arc (asymmetric contraints)
        return (
            self._sat(x_val=x_val, y_val=y_val)
            if arc == self.vars
            else self._sat(x_val=y_val, y_val=x_val)
        )

    def __and__(
        self, c: "BinConst[Variable, Value]"
    ) -> "ConstSet[Variable, Value]":
        composite: ConstSet[Variable, Value] = ConstSet(*self.vars)
        # TODO: if self is ConsSet, this repeats folding into new composite
        composite &= self
        composite &= c
        return composite


@dataclass
class ConstSet(Generic[Variable, Value], BinConst[Variable, Value]):
    x: Variable
    y: Variable
    cs: List[BinConst[Variable, Value]] = field(default_factory=list)

    def __post_init__(self) -> None:
        assert self.x != self.y, "x must be different from y"

    @property
    def vars(self) -> Tuple[Variable, Variable]:
        return self.x, self.y

    def _sat(self, x_val: Value, y_val: Value) -> bool:
        # NOTE: `self._sat` is only called via `__call__` which has already put
        #       (x_val, y_val) in correct order. Therefore it's safe to bypass
        #       the "arc check" in constraints contained in this set
        # pylint: disable=protected-access
        return all(c._sat(x_val, y_val) for c in self.cs)

    def __str__(self) -> str:
        return " & ".join(s for c in self.cs if (s := str(c)))

    def __iand__(
        self, c: BinConst[Variable, Value]
    ) -> "ConstSet[Variable, Value]":
        match c:
            case ConstSet(_, _, cs):
                self.cs.extend(cs)
            case _:
                self.cs.append(c)
        return self


@dataclass(frozen=True)
class PredicateConst(Generic[Variable, Value], BinConst[Variable, Value]):
    x: Variable | VarTransform[Variable, Value]
    y: Variable | VarTransform[Variable, Value]
    pred: Callable[[Value, Value], bool]
    op: str

    def __post_init__(self) -> None:
        assert self.x != self.y, "x must be different from y"

    @classmethod
    def var(cls, var: Variable | VarTransform[Variable, Value]) -> Variable:
        match var:
            case VarTransform(x, _):
                return x
            case x:
                return x

    @classmethod
    def transform(
        cls, var: Variable | VarTransform[Variable, Value], val: Value
    ) -> Value:
        match var:
            case VarTransform(_, f):
                return f(val)
            case _:
                return val

    @property
    def var_x(self) -> Variable:
        return self.var(self.x)

    @property
    def var_y(self) -> Variable:
        return self.var(self.y)

    @property
    def vars(self) -> Tuple[Variable, Variable]:
        return self.var_x, self.var_y

    def _sat(self, x_val: Value, y_val: Value) -> bool:
        x_val = self.transform(var=self.x, val=x_val)
        y_val = self.transform(var=self.y, val=y_val)
        return self.pred(x_val, y_val)

    @classmethod
    def repr(
        cls, var: Variable | VarTransform[Variable, Value], f: str = "f"
    ) -> str:
        match var:
            case VarTransform(x, _):
                return f"{f}({x})"
            case x:
                return str(x)

    def __str__(self) -> str:
        return f"{self.repr(self.x)} {self.op} {self.repr(self.y, f='g')}"


@dataclass(frozen=True)
class Same(Generic[Variable, Value], PredicateConst[Variable, Value]):
    pred: Callable[[Value, Value], bool] = operator.eq
    op: str = "="


@dataclass(frozen=True)
class Different(
    Generic[Variable, Value],
    PredicateConst[Variable, Value],
):
    pred: Callable[[Value, Value], bool] = operator.ne
    op: str = "!="


# pylint: disable=too-few-public-methods
class LessEq(Generic[Variable, Value], PredicateConst[Variable, Value]):
    def __init__(
        self,
        x: Variable | VarTransform[Variable, Value],
        y: Variable | VarTransform[Variable, Value],
    ) -> None:
        def pred(x: Value, y: Value) -> bool:
            # XXX: dymamic check => improve
            #  - also x is Ord shoudl imply y is Ord
            assert isinstance(x, Ord) and isinstance(y, Ord)
            return x <= y

        super().__init__(x, y, pred, op="<=")


# pylint: disable=too-few-public-methods
class LessThan(Generic[Variable, Value], PredicateConst[Variable, Value]):
    def __init__(
        self,
        x: Variable | VarTransform[Variable, Value],
        y: Variable | VarTransform[Variable, Value],
    ) -> None:
        def pred(x: Value, y: Value) -> bool:
            assert isinstance(x, Ord) and isinstance(y, Ord)
            return x < y

        super().__init__(x, y, pred, op="<")


# pylint: disable=too-few-public-methods
class GreaterEq(Generic[Variable, Value], PredicateConst[Variable, Value]):
    def __init__(
        self,
        x: Variable | VarTransform[Variable, Value],
        y: Variable | VarTransform[Variable, Value],
    ) -> None:
        def pred(x: Value, y: Value) -> bool:
            assert isinstance(x, Ord) and isinstance(y, Ord)
            return x >= y

        super().__init__(x, y, pred, op=">=")


# pylint: disable=too-few-public-methods
class GreaterThan(Generic[Variable, Value], PredicateConst[Variable, Value]):
    def __init__(
        self,
        x: Variable | VarTransform[Variable, Value],
        y: Variable | VarTransform[Variable, Value],
    ) -> None:
        def pred(x: Value, y: Value) -> bool:
            assert isinstance(x, Ord) and isinstance(y, Ord)
            return x > y

        super().__init__(x, y, pred, op=">")


# @dataclass(frozen=True)
# class LessEq(Generic[Value], PredicateConst[Value]):
#    pred: Callable[[Value, Value], bool] = operator.le
#    op: str = "<="
#
#
# @dataclass(frozen=True)
# class LessThan(Generic[Value], PredicateConst[Value]):
#    pred: Callable[[Value, Value], bool] = operator.lt
#    op: str = "<"
#
#
# @dataclass(frozen=True)
# class GreaterEq(Generic[Value], PredicateConst[Value]):
#    pred: Callable[[Value, Value], bool] = operator.ge
#    op: str = ">="
#
#
# @dataclass(frozen=True)
# class GreaterThan(Generic[Value], PredicateConst[Value]):
#    pred: Callable[[Value, Value], bool] = operator.gt
#    op: str = ">"


class Space2D(Enum):
    LINE = "=", operator.eq
    SPLIT = "!=", operator.ne
    LOWER_OPEN = "<", operator.lt
    LOWER_CLOSED = "<=", operator.le
    UPPER_CLOSED = ">=", operator.ge
    UPPER_OPEN = ">", operator.gt


@dataclass(frozen=True)
class Linear(Generic[Variable, NumValue], BinConst[Variable, NumValue]):
    """
    Defines a 2D sub-space by a line `a*x + b*y = c`.

    The part of planar space is determined by `space` as:
     - Line: `==` (default)
     - Split: `!=`
     - Half-plane:
       - Lower: `<` (open) or `<=` (closed)
       - Upper: `>` (open) or `>=` (closed)
    """

    a: NumValue
    x: Variable | VarTransform[Variable, NumValue]
    b: NumValue
    y: Variable | VarTransform[Variable, NumValue]
    c: NumValue
    space: Space2D = Space2D.LINE

    @classmethod
    def var(cls, var: Variable | VarTransform[Variable, NumValue]) -> Variable:
        match var:
            case VarTransform(x, _):
                return x
            case x:
                return x

    @classmethod
    def transform(
        cls, var: Variable | VarTransform[Variable, NumValue], val: NumValue
    ) -> NumValue:
        match var:
            case VarTransform(_, f):
                return f(val)
            case _:
                return val

    @property
    def var_x(self) -> Variable:
        return self.var(self.x)

    @property
    def var_y(self) -> Variable:
        return self.var(self.y)

    @property
    def vars(self) -> Tuple[Variable, Variable]:
        return self.var_x, self.var_y

    def _sat(self, x_val: NumValue, y_val: NumValue) -> bool:
        x_val = self.transform(var=self.x, val=x_val)
        y_val = self.transform(var=self.y, val=y_val)
        # XXX: better would be to have the defining line as
        #      a*x + b*y + c = 0 ...but then `pred` would need to take a 0
        line = self.a * x_val + self.b * y_val
        _, pred = self.space.value
        # NOTE: cast should be sould by the definition of Ord, Num and Space2D
        p: Callable[[OrdValue, OrdValue], bool] = pred
        return p(line, self.c)

    @classmethod
    def repr(
        cls, var: Variable | VarTransform[Variable, NumValue], f: str = "f"
    ) -> str:
        match var:
            case VarTransform(x, _):
                return f"{f}({x})"
            case x:
                return str(x)

    def __str__(self) -> str:
        op, _ = self.space.value
        x = self.repr(self.x, f="f")
        y = self.repr(self.y, f="g")
        return f"{self.a}*{x} + {self.b}*{y} {op} {self.c}"


@dataclass(frozen=True)
class Unary(Generic[Variable, Value]):
    x: Variable
    p: Callable[[Value], bool]


# TODO: this is an ad-hoc definition - make some nice API
# TODO: don't convert to binary consts, solve as a matching problem (X, Vals)
class AllDiff(Generic[Variable, Value]):
    xs: Iterable[Variable | HasVar[Variable] | VarTransform[Variable, Value]]

    def __init__(
        self,
        xs: Iterable[
            Variable | HasVar[Variable] | VarTransform[Variable, Value]
        ],
    ) -> None:
        self.xs = xs

    def iter_binary(self) -> Iterable[Different[Variable, Value]]:
        for x, y in combinations(self.xs, 2):
            if isinstance(x, HasVar):
                x = x.var
            if isinstance(y, HasVar):
                y = y.var
            yield Different(x, y)
