from dataclasses import dataclass
from typing import Tuple

import pytest

from csp.constraints import BinConst
from csp.inference import AC3, AC3Context, revise
from csp.model import Problem, VarCombinator


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


@pytest.fixture
def csp() -> Problem[str, int]:
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


def test_revise(csp: Problem[str, int]) -> None:

    x1, x2, x3 = csp.variables
    d_x1, d_x2, d_x3 = csp.domains
    c12 = csp.const(x1, x2)
    c23 = csp.const(x2, x3)

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


# TODO: example => different CSP
# x1 = x2 , x2 + 1 = x3
# D1 = {1, 2, 3}, D2 = {1, 2, 3}, D3 = {1, 2, 3}


def test_ac3(csp: Problem[str, int]) -> None:
    ac3 = AC3(csp)

    ctx = AC3Context(
        value=3, domains=csp.domains, unassigned=[False, True, True]
    )

    revised_domains = ac3.infer(var=0, ctx=ctx)
    assert revised_domains is not None
    # FIXME: D2 = {1, 2}
    assert revised_domains == [{3}, {2}, {3}]

    ctx = AC3Context(
        value=1, domains=csp.domains, unassigned=[False, True, True]
    )
    assert ac3.infer(var=0, ctx=ctx) is None
