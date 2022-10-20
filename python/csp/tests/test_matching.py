from typing import List

from csp.matching import hopcroft_karp, max_bipartite_matching


def test_max_matching() -> None:

    xs = list(range(4))
    ys = list(range(5))

    edges = {
        (0, 1),
        (0, 2),
        (0, 3),
        (0, 4),
        (1, 1),
        (1, 2),
        (2, 0),
        (2, 1),
        (2, 2),
        (2, 3),
        (3, 1),
        (3, 2),
    }

    feasible = [
        {(0, 3), (1, 1), (2, 0), (3, 2)},
        {(0, 3), (1, 2), (2, 0), (3, 1)},
        {(0, 4), (1, 1), (2, 0), (3, 2)},
        {(0, 4), (1, 2), (2, 0), (3, 1)},
    ]

    matching = max_bipartite_matching(xs, ys, edges)
    assert matching in feasible


def test_hopcroft_karp() -> None:

    xs = range(4)
    ys = range(5)

    edges = {
        (0, 1),
        (0, 2),
        (0, 3),
        (0, 4),
        (1, 1),
        (1, 2),
        (2, 0),
        (2, 1),
        (2, 2),
        (2, 3),
        (3, 1),
        (3, 2),
    }

    adj: List[List[int]] = [[] for _ in xs]
    for x, y in edges:
        adj[x].append(y)

    matching = hopcroft_karp(xs, ys, adj)

    # FIXME: possibley missing another fieasible solution
    #  => feasibility check: only X -> Y edges, distinct X and Y, cannot add e
    feasible = [
        {(0, 3), (1, 1), (2, 0), (3, 2)},
        {(0, 3), (1, 2), (2, 0), (3, 1)},
        {(0, 4), (1, 1), (2, 0), (3, 2)},
        {(0, 4), (1, 2), (2, 0), (3, 1)},
    ]

    assert matching in feasible
