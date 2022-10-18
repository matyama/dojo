from abc import abstractmethod
from dataclasses import dataclass
from typing import (
    Callable,
    Dict,
    Generic,
    Hashable,
    List,
    Protocol,
    Set,
    Tuple,
    TypeAlias,
    TypeVar,
    runtime_checkable,
)


# XXX: having to resort to `@runtime_checkable` is really sad
#  - also it only checks presence of methods, not their signatures
@runtime_checkable
class Eq(Protocol):
    @abstractmethod
    def __eq__(self, other: object) -> bool:
        raise NotImplementedError

    def __ne__(self, other: object) -> bool:
        return not self == other


OrdSelf = TypeVar("OrdSelf", bound="Ord")


# Source: https://github.com/python/typing/issues/59#issuecomment-353878355
@runtime_checkable
class Ord(Eq, Protocol):
    @abstractmethod
    def __lt__(self: OrdSelf, rhs: OrdSelf) -> bool:
        raise NotImplementedError

    def __gt__(self: OrdSelf, rhs: OrdSelf) -> bool:
        return (not self < rhs) and self != rhs

    def __le__(self: OrdSelf, rhs: OrdSelf) -> bool:
        return self < rhs or self == rhs

    def __ge__(self: OrdSelf, rhs: OrdSelf) -> bool:
        return not self < rhs


@runtime_checkable
class Hash(Eq, Hashable, Protocol):  # pylint: disable=too-few-public-methods
    """Marker protocol for types that are Eq + Hashable"""

    # NOTE: re-defintions from `Eq` and `Hashable` to make pylint happy

    @abstractmethod
    def __eq__(self, other: object) -> bool:
        raise NotImplementedError

    @abstractmethod
    def __hash__(self) -> int:
        return super().__hash__()


NumSelf = TypeVar("NumSelf", bound="Num")


# XXX: Div (int is not Div!), Neg, [Zero, One]
# XXX: `@runtime_checkable` only added due to `X.__add__`
@runtime_checkable
class Num(Ord, Protocol):
    def __add__(self: NumSelf, rhs: NumSelf) -> NumSelf:
        raise NotImplementedError

    def __sub__(self: NumSelf, rhs: NumSelf) -> NumSelf:
        raise NotImplementedError

    def __mul__(self: NumSelf, rhs: NumSelf) -> NumSelf:
        raise NotImplementedError


# XXX: consider using NewType instead of just TypeAlias
Var: TypeAlias = int
Variable = TypeVar("Variable", bound=Hash)


# pylint: disable=too-few-public-methods
@runtime_checkable
class HasVar(Protocol, Generic[Variable]):
    var: Variable


Arc: TypeAlias = Tuple[Variable, Variable]
VarArc: TypeAlias = Tuple[Var, Var]

Value = TypeVar("Value")
OrdValue = TypeVar("OrdValue", bound=Ord)
NumValue = TypeVar("NumValue", bound=Num)

# TODO: some compact repr for domains => protocol
#  - e.g. D = {0..n} could be represented compactly as `range(n)`
#  - `__contains__` (operator `in`) and `__iter__` and `remove(v)`! and
#    efficient clone => Protocol(Iterable, Contains, Sized)
#  - remove(v) for `range(a, b)` => split interval => interval trees or
#    splitable lists
#    => remove([a, b], v) -> [[a, v-1], [v+1, b]] ... list of intervals
#    => remove always splits at most one interval
#    => domain always shrinks or is cloned
#    => remove(v, [..., [v, v], ...]) => drop [v, v] from the interval list
#       this requires linked-list to remove and reconnect in O(1)
#    => interval linked-list is empty => domain is empty
#    => interval linked-list is sorted => remove => logarithmic lookup
Domain: TypeAlias = Set[Value]
DomainSet: TypeAlias = List[Domain[Value]]


# TODO: DomainSetMut = NewType("DomainSetMut", DomainSet)
#       blocked by https://github.com/python/mypy/issues/3331
@dataclass(frozen=True)
class DomainSetMut(Generic[Value]):
    ds: DomainSet[Value]


Transform: TypeAlias = Callable[[Value], Value]


@dataclass(frozen=True)
class VarTransform(Generic[Variable, Value]):
    x: Variable
    f: Transform[Value]


Assignment: TypeAlias = Dict[Var, Value]

# An assignment but indexed by domain `Variable`s instead of internal `Var`s
Solution: TypeAlias = Dict[Variable, Value]
