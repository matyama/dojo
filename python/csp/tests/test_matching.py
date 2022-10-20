from dataclasses import dataclass
from typing import List, Sequence, Set, Tuple

import pytest

from csp.matching import hopcroft_karp, max_bipartite_matching


@dataclass(frozen=True)
class BipGraph:
    xs: Sequence[int]
    ys: Sequence[str]
    edges: Set[Tuple[int, str]]

    @property
    def adj(self) -> List[List[int]]:
        xs_ix = {x: i for i, x in enumerate(self.xs)}
        ys_ix = {y: j for j, y in enumerate(self.ys)}

        adj: List[List[int]] = [[] for _ in self.xs]
        for x, y in self.edges:
            i, j = xs_ix[x], ys_ix[y]
            adj[i].append(j)

        return adj


@pytest.fixture(name="graph")
def example() -> BipGraph:
    """
    Source: https://www.andrew.cmu.edu/user/vanhoeve/papers/alldiff.pdf
    """
    return BipGraph(
        xs=range(1, 5),
        ys="ABCDE",
        edges={
            (1, "B"),
            (1, "C"),
            (1, "D"),
            (1, "E"),
            (2, "B"),
            (2, "C"),
            (3, "A"),
            (3, "B"),
            (3, "C"),
            (3, "D"),
            (4, "B"),
            (4, "C"),
        },
    )


def validate_max_matching(
    edges: Set[Tuple[int, str]], matching: Set[Tuple[int, str]]
) -> None:
    xs = [x for x, _ in matching]
    ys = [y for _, y in matching]

    # matching
    assert len(set(xs)) == len(xs)
    assert len(set(ys)) == len(ys)

    x_set, y_set = set(xs), set(ys)

    # maximum cardinality
    for x, y in edges - matching:
        assert x in x_set or y in y_set


def test_max_matching(graph: BipGraph) -> None:

    matching = max_bipartite_matching(
        xs=graph.xs, ys=graph.ys, edges=graph.edges
    )

    validate_max_matching(edges=graph.edges, matching=matching)


def test_hopcroft_karp(graph: BipGraph) -> None:

    matching = hopcroft_karp(xs=graph.xs, ys=graph.ys, adj=graph.adj)
    print(matching)

    validate_max_matching(edges=graph.edges, matching=matching)
