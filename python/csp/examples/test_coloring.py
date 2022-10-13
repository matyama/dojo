from enum import Enum, auto
from re import T
from typing import Dict, List, TypeAlias

from csp.model import CSP, Model, Solution
from csp.solver import solve


class Territory(Enum):
    WA = auto()
    NT = auto()
    Q = auto()
    NSW = auto()
    V = auto()
    SA = auto()
    T = auto()


class Color(Enum):
    R = auto()
    G = auto()
    B = auto()


Map: TypeAlias = Dict[Territory, List[Territory]]
Coloring: TypeAlias = Dict[Territory, Color]


class Australia(Model[Map, Coloring, Territory, Color]):
    MAP: Map = {
        Territory.WA: [Territory.NT, Territory.SA],
        Territory.NT: [Territory.WA, Territory.SA, Territory.Q],
        Territory.SA: [
            Territory.WA,
            Territory.NT,
            Territory.Q,
            Territory.NSW,
            Territory.V,
        ],
        Territory.Q: [Territory.NT, Territory.SA, Territory.NSW],
        Territory.NSW: [Territory.Q, Territory.V, Territory.SA],
        Territory.V: [Territory.NSW, Territory.SA],
        Territory.T: [],
    }

    def into_csp(self, instance: Map) -> CSP[Territory, Color]:
        csp = CSP[Territory, Color]()

        # Variable = Territory
        csp += ((t, set(Color)) for t in instance)

        # Constraints: territory != neighbor
        for t, ts in instance.items():
            for n in ts:
                csp += csp[t] != csp[n]

        return csp

    def from_csp(self, solution: Solution) -> Coloring:
        return solution


def test_coloring() -> None:
    australia = Australia()
    csp = australia.into_csp(instance=australia.MAP)

    coloring = solve(csp)

    # coloring Australia map with 3 colors should have a solution
    assert coloring

    # validate the coloring
    for t, ts in australia.MAP.items():
        assert all(coloring[t] != coloring[neighbor] for neighbor in ts)
