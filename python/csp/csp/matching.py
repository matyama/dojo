import sys
from collections import deque
from typing import (
    Deque,
    Iterable,
    List,
    Optional,
    Sequence,
    Set,
    Tuple,
    TypeAlias,
    TypeVar,
    cast,
)

X = TypeVar("X")
Y = TypeVar("Y")


Edge: TypeAlias = Tuple[X, Y]


def max_bipartite_matching(
    xs: Sequence[X], ys: Sequence[Y], edges: Set[Edge[X, Y]]
) -> Set[Edge[X, Y]]:
    """
    Find a maximum matching in given bipartite graph `G = (xs, ys, edges)`.

    Note that the implementation is a DFS - essentially simplified
    Ford-Fulkerson max-flow algorithm, adapted to bipartite graphs.

    Complexity (worst-case): `O(|xs+ys|*|edges|)`
    """

    # matching[j] = x if (x, ys[j]) in max_matching else None
    matching: List[Optional[X]] = [None] * len(ys)

    def search(x: X, m: List[Optional[X]], seen: List[bool]) -> bool:
        for j, y in enumerate(ys):
            if (x, y) in edges and not seen[j]:
                seen[j] = True
                if m[j] is None or search(cast(X, m[j]), m, seen):
                    m[j] = x
                    return True
        return False

    for x in xs:
        search(x, matching, seen=[False] * len(ys))

    return {(x, ys[j]) for j, x in enumerate(matching) if x is not None}


# XXX: alternatively take `edges: Set[Edge[X, Y]]`
def hopcroft_karp(
    xs: Sequence[X], ys: Sequence[Y], adj: Sequence[Sequence[int]]
) -> Set[Edge[X, Y]]:
    """
    Hopcroft & Karp (1973):
     - Input: bipartite graph `G = (xs, ys, <edges defined by adj>)`
     - Output: edges in a maximum matching
     - Complexity (worst-case): `O(|edges|*sqrt(|xs + ys|))`
     - [wiki](https://en.wikipedia.org/wiki/Hopcroft%E2%80%93Karp_algorithm)

    Note that `adj` list is given as a mapping `<xs index> -> <indices to ys>`.
    """

    nil = 0
    inf = sys.maxsize

    m = len(xs)

    # NOTE: +/- 1 shifts due to nil = 0
    pair_u = [nil] * (m + 1)
    pair_v = [nil] * (len(ys) + 1)
    dist = [0] * (m + 1)

    def iter_adj(u: int) -> Iterable[int]:
        assert u != nil
        for v in adj[u - 1]:
            yield v + 1

    def bfs(q: Deque[int]) -> bool:
        for u in range(1, m + 1):
            if pair_u[u] == nil:
                dist[u] = 0
                q.append(u)
            else:
                dist[u] = inf

        dist[nil] = inf

        while q:
            u = q.popleft()
            if dist[u] < dist[nil]:
                # NOTE: implied u != nil otherwise dist[u] == dist[nil]
                for v in iter_adj(u):
                    if dist[pair_v[v]] == inf:
                        dist[pair_v[v]] = dist[u] + 1
                        q.append(pair_v[v])

        return dist[nil] != inf

    def dfs(u: int) -> bool:
        if u == nil:
            return True

        for v in iter_adj(u):
            if dist[pair_v[v]] == dist[u] + 1:
                if dfs(pair_v[v]):
                    pair_v[v] = u
                    pair_u[u] = v
                    return True

        dist[u] = inf
        return False

    queue: Deque[int] = deque(maxlen=m + 1)
    while bfs(queue):
        for u in range(1, m + 1):
            if pair_u[u] == nil:
                dfs(u)

    return {(xs[u], ys[v - 1]) for u, v in enumerate(pair_u[1:]) if v != nil}
