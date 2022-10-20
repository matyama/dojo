from collections import deque
from typing import Deque, Iterable, Optional, Sequence, Tuple, TypeAlias

Node: TypeAlias = int
Edge: TypeAlias = Tuple[int, int]
Graph: TypeAlias = Sequence[Sequence[Node]]


def bfs_walk(
    graph: Graph,
    init: Node,
    queue: Optional[Deque[Node]] = None,
) -> Iterable[Tuple[int, int]]:
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
    queue: Deque[Node] = deque(maxlen=len(graph))
    for init in inits:
        yield from bfs_walk(graph, init, queue)
