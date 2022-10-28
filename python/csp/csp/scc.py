from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import TypeAlias

Graph: TypeAlias = Sequence[Sequence[int]]
Component: TypeAlias = set[int]


@dataclass
class Node:
    # graph data
    node_id: int

    # SCC data
    index: int
    lowlink: int

    # stack data
    pred: "Node | None"
    instack: bool

    @classmethod
    def new(cls, n: int) -> "Node":
        return cls(node_id=n, index=0, lowlink=0, pred=None, instack=False)

    @property
    def unvisited(self) -> bool:
        return self.index == 0


Stack: TypeAlias = Node | None


class Tarjan:
    """Class representing the global state of Tarjan's SCC algorithm"""

    _graph: Graph
    _nodes: dict[int, Node]
    _stack: Stack
    _index: int

    def __init__(self, graph: Graph) -> None:
        self._graph = graph
        self._nodes = {}
        self._stack = None
        self._index = 0

    def _node(self, n: int) -> Node:
        x = self._nodes.get(n)
        if x is not None:
            return x

        x = Node.new(n)
        self._nodes[n] = x
        return x

    def iter_nodes(self) -> Iterable[Node]:
        return map(self._node, range(len(self._graph)))

    def _iter_adj(self, n: Node) -> Iterable[Node]:
        return map(self._node, self._graph[n.node_id])

    def _stack_push(self, n: Node) -> None:
        n.pred = self._stack
        n.instack = True
        self._stack = n

    def _stack_pop(self) -> Node:
        """Warn: panics when stack is empty"""
        assert self._stack is not None
        n = self._stack
        self._stack = n.pred
        n.pred = None
        n.instack = False
        return n

    def _scc_pop(self, n: Node) -> Component:
        """Side-effect: pops nodes from the stack until n is reached"""
        scc: Component = set()
        while True:
            x = self._stack_pop()
            scc.add(x.node_id)
            if x is n:
                return scc

    def find_scc(self, n: Node) -> Iterable[Component]:
        self._index += 1
        n.index = self._index
        n.lowlink = self._index
        self._stack_push(n)

        for adj in self._iter_adj(n):
            if adj.unvisited:
                yield from self.find_scc(adj)
                n.lowlink = min(n.lowlink, adj.lowlink)
            elif adj.instack:
                n.lowlink = min(n.lowlink, adj.index)

        if n.lowlink == n.index:
            # generate new SCC containing node n
            yield self._scc_pop(n)


def strongly_connected_components(graph: Graph) -> list[Component]:
    """
    Finds strongly connected components of given directed graph using Tarjan's
    SCC algorithm.

    Runs in O(|V| + |E|) worst-case time where |V| is the number of nodes and
    |E| the number of edges in the graph.
    """
    search = Tarjan(graph)

    components: list[Component] = []
    for n in search.iter_nodes():
        if n.unvisited:
            components.extend(search.find_scc(n))

    return components


def tarjan_scc(graph: Graph) -> list[int]:
    """
    Finds SCC in the same way as `strongly_connected_components` but rather
    than a set of components this function returns an inverse mapping
    `<node_id> -> <component_id>`.

    I.e. `x` and `y` are in the same SCC iff `component[x] == component[y]`.
    """
    # XXX: this pre-alloc essentially doubles the work
    #  => represent Graph with Nodes => assign Node.scc_id inplace
    component = [0] * len(graph)

    # TODO: extend Node with scc_id and assign in _stack_pop instead
    #   => single graph traversal
    for scc_id, nodes in enumerate(strongly_connected_components(graph)):
        for n in nodes:
            component[n] = scc_id

    return component
