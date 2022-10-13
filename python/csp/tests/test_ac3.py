from dataclasses import dataclass
from typing import Optional, Tuple

import pytest

from csp.constraints import BinConst
from csp.inference import AC3, revise
from csp.model import Assign, Problem, VarCombinator
from csp.types import DomainSet


# TODO: possibly move to constraints (with generic vars/vals)
#  - generalize boundary => operator (<, <=, >, >=, ==, !=) => Enum?
#  - Linear: HalfPlane (<, <=, >=, >), Line (==), ExcludeLine/Separation (!=)
@dataclass(frozen=True)
class HalfPlane(BinConst[str, int]):
    x: str
    y: str
    a: int = 1
    b: int = 1
    c: int = 0
    boundary: bool = True

    @property
    def vars(self) -> Tuple[str, str]:
        return self.x, self.y

    def _sat(self, x_val: int, y_val: int) -> bool:
        line = self.a * x_val + self.b * y_val
        return line >= self.c if self.boundary else line > self.c

    def __str__(self) -> str:
        op = ">=" if self.boundary else ">"
        return f"{self.a}*{self.x} + {self.b}*{self.y} {op} {self.c}"


@dataclass(frozen=True)
class Shifted(BinConst[str, int]):
    x: str
    y: str
    s: int

    @property
    def vars(self) -> Tuple[str, str]:
        return self.x, self.y

    def _sat(self, x_val: int, y_val: int) -> bool:
        return x_val + self.s == y_val

    def __str__(self) -> str:
        return f"{self.x} + {self.s} = {self.y}"


@pytest.fixture(name="a")
def csp_a() -> Problem[str, int]:
    csp: Problem[str, int] = Problem()

    x1: VarCombinator[str, int] = VarCombinator("x1")
    x2: VarCombinator[str, int] = VarCombinator("x2")
    x3: VarCombinator[str, int] = VarCombinator("x3")

    csp += (x1.var, {1, 2, 3})
    csp += (x2.var, {1, 2, 3})
    csp += (x3.var, {2, 3})

    csp += x1 > x2
    csp += (x2 != x3) & HalfPlane(x2.var, x3.var, c=4, boundary=False)

    return csp


@pytest.fixture(name="b")
def csp_b() -> Problem[str, int]:
    csp: Problem[str, int] = Problem()

    x1: VarCombinator[str, int] = VarCombinator("x1")
    x2: VarCombinator[str, int] = VarCombinator("x2")
    x3: VarCombinator[str, int] = VarCombinator("x3")

    csp += (x1.var, {1, 2, 3})
    csp += (x2.var, {1, 2, 3})
    csp += (x3.var, {1, 2, 3})

    csp += x1 == x2
    csp += Shifted(x=x2.var, y=x3.var, s=1)

    return csp


@pytest.fixture
def instance(
    request: pytest.FixtureRequest,
    a: Problem[str, int],
    b: Problem[str, int],
) -> Problem[str, int]:
    instances = {"a": a, "b": b}
    return instances[request.param]


def test_revise(a: Problem[str, int]) -> None:

    x1, x2, x3 = a.variables
    d_x1, d_x2, d_x3 = a.domains
    c12 = a.const(x1, x2)
    c23 = a.const(x2, x3)

    assert c12 is not None
    assert c23 is not None

    assert revise(arc=(x1, x2), domain_x=d_x1, domain_y=d_x2, const_xy=c12)
    assert d_x1 == {2, 3} and d_x2 == {1, 2, 3}

    assert revise(arc=(x2, x1), domain_x=d_x2, domain_y=d_x1, const_xy=c12)
    assert d_x2 == {1, 2} and d_x1 == {2, 3}

    assert revise(arc=(x2, x3), domain_x=d_x2, domain_y=d_x3, const_xy=c23)
    assert d_x2 == {2} and d_x3 == {2, 3}

    assert revise(arc=(x3, x2), domain_x=d_x3, domain_y=d_x2, const_xy=c23)
    assert d_x3 == {3} and d_x2 == {2}

    assert revise(arc=(x1, x2), domain_x=d_x1, domain_y=d_x2, const_xy=c12)
    assert d_x1 == {3} and d_x2 == {2}

    assert [d_x1, d_x2, d_x3] == [{3}, {2}, {3}]


@pytest.mark.parametrize(
    "instance,expected",
    [
        pytest.param("a", [{3}, {2}, {3}], id="A"),
        pytest.param("b", [{1, 2}, {1, 2}, {2, 3}], id="B"),
    ],
    indirect=["instance"],
)
def test_ac3(
    instance: Problem[str, int], expected: Optional[DomainSet[int]]
) -> None:
    ac3 = AC3(csp=instance)
    revised_domains = ac3(arcs=ac3.arc_iter, domains=instance.domains)
    assert revised_domains == expected


@pytest.mark.parametrize(
    "x,v,expected",
    [
        pytest.param("x1", 3, [{3}, {2}, {3}], id="x1 := 3"),
        pytest.param("x1", 1, None, id="x1 := 1"),
    ],
)
def test_infer(
    x: str, v: int, expected: Optional[DomainSet[int]], a: Problem[str, int]
) -> None:
    actual = AC3(a).infer(assign=Assign(var=a.var(x), val=v), ctx=a.domains)
    assert expected == actual
