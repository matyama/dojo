from collections import deque
from collections.abc import Iterable, Sequence
from typing import TypeAlias

Node: TypeAlias = int
Edge: TypeAlias = tuple[int, int]
Graph: TypeAlias = Sequence[Sequence[Node]]


def bfs_walk(
    graph: Graph, init: Node, queue: deque[Node] | None = None
) -> Iterable[Edge]:
    queue = queue if queue is not None else deque(maxlen=len(graph))

    queue.append(init)
    visited = [False] * len(graph)
    visited[init] = True

    while queue:
        node = queue.popleft()

        for adj in graph[node]:
            if not visited[adj]:
                queue.append(adj)
                visited[adj] = True
                yield node, adj


def bfs(graph: Graph, inits: Iterable[Node]) -> Iterable[Edge]:
    queue: deque[Node] = deque(maxlen=len(graph))
    for init in inits:
        yield from bfs_walk(graph, init, queue)
