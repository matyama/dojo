from typing import List, TypeAlias

import pytest

from csp.model import Model, Problem, Solution, Vars
from csp.solver import solve

# Rook = column
Rook: TypeAlias = int
Row: TypeAlias = int
BoardSize: TypeAlias = int
Positions: TypeAlias = List[Row]


class Rooks(Model[BoardSize, Positions, Rook, Row]):
    def into_csp(self, instance: BoardSize) -> Problem[Rook, Row]:

        csp: Problem[Rook, Row] = Problem()

        csp += Vars((rook, range(instance)) for rook in range(instance))

        for col_x in range(instance):
            x = csp.var_comb(col_x)
            for col_y in range(instance):
                if col_x < col_y:
                    y = csp.var_comb(col_y)
                    csp += x != y

        return csp

    def from_csp(self, solution: Solution[Rook, Row]) -> Positions:
        positions = [0] * len(solution)
        for rook, row in solution.items():
            positions[rook] = row
        return positions


@pytest.fixture
def rooks() -> Rooks:
    return Rooks()


@pytest.mark.parametrize("n", list(range(1, 10)), ids=lambda n: f"N={n}")
def test_rooks(n: BoardSize, rooks: Rooks) -> None:
    csp = rooks.into_csp(instance=n)

    solution = solve(csp)
    assert solution

    positions = rooks.from_csp(solution)

    # validate that each row has been occupied exactly once
    assert len(set(positions)) == n
