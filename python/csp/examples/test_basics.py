from dataclasses import dataclass
from typing import Tuple

from csp.model import BinConst, Problem
from csp.solver import solve


# TODO: replace by a generalized linear constraint
@dataclass(frozen=True)
class Linear(BinConst[str, int]):
    """C_a(x, y) iff a*x = y"""

    a: int
    x: str
    y: str

    @property
    def vars(self) -> Tuple[str, str]:
        return self.x, self.y

    def _sat(self, x_val: int, y_val: int) -> bool:
        return self.a * x_val == y_val

    def __str__(self) -> str:
        return f"{self.a}*{self.x} = {self.y}"


def test_custom_constraint() -> None:
    csp: Problem[str, int] = Problem()

    x, y = "x", "y"

    csp += (x, {1, 2, 3})
    csp += (y, {4, 5, 6})

    csp += Linear(2, x, y)

    assignment = solve(csp)
    assert assignment in [{x: 2, y: 4}, {x: 3, y: 6}]
