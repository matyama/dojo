from dataclasses import dataclass
from typing import Tuple

from csp.constraints import Linear, Space2D
from csp.model import CSP
from csp.solver import solve


def test_linear_constraint() -> None:
    csp = CSP[str, int]()

    x, y = "x", "y"

    csp += x, {1, 2, 3}
    csp += y, {4, 5, 6}

    # line: 2x = y
    csp += Linear(a=2, x=x, b=-1, y=y, c=0)

    # TODO: `solve(csp, exhaustive=True)` => keep searching
    assignment = solve(csp)
    assert assignment in [{x: 2, y: 4}, {x: 3, y: 6}]
