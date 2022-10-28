import random
from collections.abc import Sequence
from dataclasses import dataclass

from csp.matching import hopcroft_karp, max_bipartite_matching


@dataclass(frozen=True)
class ValueGraph:
    xs: Sequence[str]
    ys: Sequence[int]
    edges: set[tuple[str, int]]

    # pylint: disable=duplicate-code
    @property
    def adj(self) -> list[list[int]]:
        xs_ix = {x: i for i, x in enumerate(self.xs)}
        ys_ix = {y: j for j, y in enumerate(self.ys)}

        adj: list[list[int]] = [[] for _ in self.xs]
        for x, y in self.edges:
            i, j = xs_ix[x], ys_ix[y]
            adj[i].append(j)

        return adj


def random_value_graph() -> ValueGraph:
    m = random.randrange(100, 500, 50)
    n = random.randrange(m, 2 * m, 50)
    xs = [f"x{i}" for i in range(m)]
    ds = random.sample(range(m // 2), k=m, counts=[m] * (m // 2))
    vs = range(n)
    edges = {(x, v) for x, d in zip(xs, ds) for v in random.sample(vs, k=d)}
    return ValueGraph(xs=xs, ys=vs, edges=edges)


def bench_dfs(
    xs: Sequence[str], ys: Sequence[int], edges: set[tuple[str, int]]
) -> None:
    max_bipartite_matching(xs, ys, edges)


def bench_hopcroft_karp(
    xs: Sequence[str], ys: Sequence[int], adj: Sequence[Sequence[int]]
) -> None:
    hopcroft_karp(xs, ys, adj)


if __name__ == "__main__":
    for _ in range(100):
        graph = random_value_graph()
        bench_dfs(xs=graph.xs, ys=graph.ys, edges=graph.edges)
        bench_hopcroft_karp(xs=graph.xs, ys=graph.ys, adj=graph.adj)
