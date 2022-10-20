from typing import Iterable, Sequence, Tuple

import pytest

from csp.constraints import AllDiff
from csp.inference import AC3, AllDiffInference
from csp.model import CSP
from csp.types import DomainSet


@pytest.mark.parametrize(
    "assignment",
    [
        pytest.param(
            [("x1", 2), ("x2", 3), ("x3", 1)],
            id="consistent",
        ),
        pytest.param(
            [("x1", 2), ("x2", 3), ("x3", 1), ("x4", 3)],
            id="consistent-extra-assignment",
        ),
        pytest.param(
            [("x1", 2), ("x2", 3), ("x4", 3)],
            id="consistent-partial-assignment",
        ),
        pytest.param(
            [("x1", 2), ("x2", 2), ("x3", 1), ("x4", 3)],
            marks=pytest.mark.xfail,
            id="inconsistent",
        ),
    ],
)
def test_alldiff_consistency(assignment: Iterable[Tuple[str, int]]) -> None:
    alldiff = AllDiff[str, int](["x1", "x2", "x3"])
    assert alldiff(assignment)


# Examples:
#  - https://www.andrew.cmu.edu/user/vanhoeve/papers/alldiff.pdf
#  - https://www.cs.upc.edu/~larrosa/MAI-CPP-files/CP/CSP-GlobalMiniZinc.pdf
@pytest.mark.parametrize(
    "xs,ds,expected",
    [
        pytest.param(
            ["x1", "x2", "x3"],
            [{1, 2}, {1, 2}, {1, 2, 3}],
            [{1, 2}, {1, 2}, {3}],
            id="n=3 d=3",
        ),
        pytest.param(
            ["x1", "x2", "x3", "x4"],
            [{2, 3, 4, 5}, {2, 3}, {1, 2, 3, 4}, {2, 3}],
            [{4, 5}, {2, 3}, {1, 4}, {2, 3}],
            id="n=4 d=5",
        ),
        pytest.param(
            ["x1", "x2", "x3", "x4", "x5", "x6"],
            [{1, 2}, {2, 3}, {1, 3}, {3, 4}, {2, 4, 5, 6}, {5, 6, 7}],
            [{1, 2}, {2, 3}, {1, 3}, {4}, {5, 6}, {5, 6, 7}],
            id="n=6 d=7",
        ),
    ],
)
def test_alldiff_inference(
    xs: Sequence[str], ds: DomainSet[int], expected: DomainSet[int]
) -> None:

    csp = CSP[str, int]()

    csp += zip(xs, ds)

    alldiff = AllDiff[str, int](xs)
    csp += alldiff

    inference = AllDiffInference(csp)
    ds_alldiff, reduced = inference(domains=ds)
    assert reduced
    assert ds_alldiff == expected

    # replicate alldiff in the csp instance
    for diff_const in alldiff.iter_binary():
        csp += diff_const

    ac3 = AC3(csp)
    ds_ac3, _ = ac3(arcs=ac3.arc_iter, domains=ds)
    assert ds_ac3 is not None

    def count_vals(ds: DomainSet[int]) -> int:
        return sum(len(d) for d in ds)

    assert count_vals(ds_alldiff) < count_vals(ds_ac3)
