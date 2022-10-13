import operator
from abc import abstractmethod
from dataclasses import dataclass, field
from typing import Callable, Generic, List, Protocol, Tuple

from csp.types import Arc, Ord, Value, Variable


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
            self._sat(x_val, y_val)
            if arc == self.vars
            else self._sat(y_val, x_val)
        )

    # TODO: try to override `and` to get DSL like `c = c1 and c2`
    #  - `and` works only on bool values, and with refs
    #  - in contrast, this works as `c = c1 & c2`
    def __and__(
        self, c: "BinConst[Variable, Value]"
    ) -> "ConstSet[Variable, Value]":
        composite: ConstSet[Variable, Value] = ConstSet(*self.vars)
        # TODO: if self is ConsSet, this repeats folding into new composite
        composite &= self
        composite &= c
        return composite


# TODO: cs list duplicates (x, y) => could be just sat callables
#  => `vars` are necessary in (csp +=) to index/find C(x, y)
#  => this could be just an internall accumulator and not part of public API
#     (i.e. `csp += const_set` would not be allowed)
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
    x: Variable
    y: Variable
    pred: Callable[[Value, Value], bool]
    op: str

    def __post_init__(self) -> None:
        assert self.x != self.y, "x must be different from y"

    @property
    def vars(self) -> Tuple[Variable, Variable]:
        return self.x, self.y

    def _sat(self, x_val: Value, y_val: Value) -> bool:
        return self.pred(x_val, y_val)

    def __str__(self) -> str:
        return f"x[{self.x}] {self.op} x[{self.y}]"


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
    def __init__(self, x: Variable, y: Variable) -> None:
        def pred(x: Value, y: Value) -> bool:
            # XXX: dymamic check => improve
            #  - also x is Ord shoudl imply y is Ord
            assert isinstance(x, Ord) and isinstance(y, Ord)
            return x <= y

        super().__init__(x, y, pred, op="<=")


# pylint: disable=too-few-public-methods
class LessThan(Generic[Variable, Value], PredicateConst[Variable, Value]):
    def __init__(self, x: Variable, y: Variable) -> None:
        def pred(x: Value, y: Value) -> bool:
            assert isinstance(x, Ord) and isinstance(y, Ord)
            return x < y

        super().__init__(x, y, pred, op="<")


# pylint: disable=too-few-public-methods
class GreaterEq(Generic[Variable, Value], PredicateConst[Variable, Value]):
    def __init__(self, x: Variable, y: Variable) -> None:
        def pred(x: Value, y: Value) -> bool:
            assert isinstance(x, Ord) and isinstance(y, Ord)
            return x >= y

        super().__init__(x, y, pred, op=">=")


# pylint: disable=too-few-public-methods
class GreaterThan(Generic[Variable, Value], PredicateConst[Variable, Value]):
    def __init__(self, x: Variable, y: Variable) -> None:
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
#

# TODO: Value must be Num (Add, Sub, Mul, Div)
#
# class LinEq(Generic[Value], PredicateConst]Value):
#
#    def __init__(self, x: Var, y: Var, a: Value, b: Value, c: Value) -> None:
#        def linear(x: Value, y: Value) -> bool:
#            return a * x + b * y + c == 0
#
#        # FIXME: PredicateConst only supports infix position
#        op = ""
#        super().__init__(x, y, pred=linear, op=op)


# XXX
#  - Linear: HalfPlane (<, <=, >=, >), Line (==), ExcludeLine/Separation (!=)
# class Space2D(Enum):
#    HalfPlane = "< | <= | >= | >"
#    Line = "== (boundary=True) | != (boundary=False)"
#    # Separation = "!="

# XXX Value => Numeric: Eq, Ord, Add, Sub, Mul, Div, Neg, [Zero, One]
# @dataclass(frozen=True)
# class Linear(BinConst[Variable, Value]):
#    a: Value
#    x: Variable
#    b: Value
#    y: Variable
#    c: Value
#    boundary: bool = True
#
#    @property
#    def vars(self) -> Tuple[str, str]:
#        return self.x, self.y
#
#    def _sat(self, x_val: int, y_val: int) -> bool:
#        line = self.a * x_val + self.b * y_val
#        return line >= self.c if self.boundary else line > self.c
#
#    def __str__(self) -> str:
#        op = ">=" if self.boundary else ">"
#        return f"{self.a}*{self.x} + {self.b}*{self.y} {op} {self.c}"
