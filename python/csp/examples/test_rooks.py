from itertools import combinations
from typing import TypeAlias

import pytest

from csp.model import CSP, Model, Solution
from csp.solver import solve

# Rook = column
Rook: TypeAlias = int
Row: TypeAlias = int
BoardSize: TypeAlias = int
Positions: TypeAlias = list[Row]


class Rooks(Model[BoardSize, Positions, Rook, Row]):
    def into_csp(self, instance: BoardSize) -> CSP[Rook, Row]:
        csp = CSP[Rook, Row]()

        xs = [csp[rook] for rook in range(instance)]
        ds = [range(instance)] * instance

        csp += zip(xs, ds)

        for x, y in combinations(xs, 2):
            csp += x != y

        return csp

    def from_csp(self, solution: Solution[Rook, Row]) -> Positions:
        positions = [0] * len(solution)
        for rook, row in solution.items():
            positions[rook] = row
        return positions


@pytest.fixture(name="rooks")
def make_rooks() -> Rooks:
    return Rooks()


@pytest.mark.parametrize("n", list(range(1, 10)), ids=lambda n: f"N={n}")
def test_rooks(n: BoardSize, rooks: Rooks) -> None:
    csp = rooks.into_csp(instance=n)

    solution = solve(csp)
    assert solution

    positions = rooks.from_csp(solution)

    # validate that each row has been occupied exactly once
    assert len(set(positions)) == n
