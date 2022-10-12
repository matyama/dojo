from abc import abstractmethod
from typing import (
    Dict,
    Hashable,
    List,
    Protocol,
    Set,
    TypeAlias,
    TypeVar,
    runtime_checkable,
)


# XXX: having to resort to `@runtime_checkable` is really sad
#  - also it only check presence of methods, not their signatures
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


# XXX: consider using NewType instead of just TypeAlias => need consts[var] tho
Var: TypeAlias = int
Variable = TypeVar("Variable", bound=Hash)
Value = TypeVar("Value")
# NOTE: dont't enforce bound here => check dynamically in constraints
# Value = TypeVar("Value", bound=Ord)
OrdValue = TypeVar("OrdValue", bound=Ord)

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

Assignment: TypeAlias = Dict[Var, Value]

# An assignment but indexed by domain `Variable`s instead of internal `Var`s
Solution: TypeAlias = Dict[Variable, Value]
