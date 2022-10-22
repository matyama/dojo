from itertools import combinations
from typing import List, TypeAlias

import pytest

from csp.constraints import AllDiff
from csp.model import CSP, Model
from csp.solver import solve
from csp.types import Solution

Queen: TypeAlias = int
Row: TypeAlias = int


class Queens(Model[int, List[Row], Queen, Row]):
    def into_csp(self, instance: int) -> CSP[Queen, Row]:
        n = instance
        assert n > 0

        # https://developers.google.com/optimization/cp/queens
        csp = CSP[Queen, Row]()

        xs = [csp[x] for x in range(n)]
        ds = [range(n)] * n

        csp += zip(xs, ds)

        # distinct rows
        csp += AllDiff(xs)

        # distinct diagonals (up & down)
        csp += AllDiff(xs[i] + i for i in range(n))
        csp += AllDiff(xs[i] - i for i in range(n))

        return csp

    def from_csp(self, solution: Solution[Queen, Row]) -> List[Row]:
        n = len(solution)

        queens = [0] * n
        for col, row in solution.items():
            queens[col] = row

        return queens


@pytest.fixture(name="model")
def make_model() -> Queens:
    return Queens()


@pytest.mark.parametrize("n", [1, 4, 5, 6, 7, 8, 9], ids=lambda n: f"N={n}")
def test_feasible(n: int, model: Queens) -> None:
    csp = model.into_csp(n)
    solution = solve(csp)
    queens = model.from_csp(solution)

    assert len(set(queens)) == n

    for i, j in combinations(range(n), 2):
        assert abs(queens[i] - queens[j]) != abs(i - j)


@pytest.mark.parametrize("n", [2, 3], ids=lambda n: f"N={n}")
def test_infeasible(n: int, model: Queens) -> None:
    csp = model.into_csp(n)
    solution = solve(csp)
    assert not solution


# @pytest.mark.execution_timeout(12)
def test_1k(model: Queens) -> None:
    # XXX: scale this to 1k
    n = 10

    csp = model.into_csp(instance=n)
    solution = solve(csp)
    queens = model.from_csp(solution)

    assert len(set(queens)) == n

    for i, j in combinations(range(n), 2):
        assert abs(queens[i] - queens[j]) != abs(i - j)
