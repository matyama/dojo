from abc import abstractmethod
from collections import deque
from dataclasses import dataclass
from typing import (
    Generic,
    Iterable,
    List,
    Optional,
    Protocol,
    Sequence,
    Set,
    Tuple,
    TypeAlias,
    TypeVar,
)

from csp.bfs import bfs
from csp.constraints import AllDiff, BinConst
from csp.matching import hopcroft_karp
from csp.model import CSP, Assign
from csp.scc import tarjan_scc
from csp.types import (
    Arc,
    Domain,
    DomainSet,
    DomainSetMut,
    Value,
    Var,
    VarArc,
    Variable,
)

C_contra = TypeVar("C_contra", contravariant=True)
I_co = TypeVar("I_co", covariant=True)


# TODO: impl other AC algs => decide on the interface
#  - Alternative API: infer(Assign, C) -> C ... C ~ generic inference ctx
class Inference(
    Protocol, Generic[C_contra, I_co, Value]
):  # pylint: disable=R0903
    @abstractmethod
    def infer(self, assign: Assign[Value], ctx: C_contra) -> Optional[I_co]:
        raise NotImplementedError


def revise(
    arc: Arc[Variable],
    domain_x: Domain[Value],
    domain_y: Domain[Value],
    const_xy: BinConst[Variable, Value],
) -> bool:
    """
    Procedure that deletes any value from `domain_x` which is inconsistent
    with values from `domain_y` under constraints represented by `const_xy`.

    Returns: True iff `domain_x` has been changed.
    Complexity: O(d^2) where d is the max domain size

    WARN: If a call to `revise` returns True, the contents of `domain_x` has
    been modified (some entries were removed). Otherwise, it's kept unchanged.

    Note: All binary constraints should be combined into one composed
    constraint - see `CompositeConst`.
    """
    deleted = False
    # XXX: list -> another shallow copy, and called inside `while queue`
    for x_val in list(domain_x):
        # Ban x_val if there's no possible y_val consistent with const_xy
        if all(not const_xy(arc, x_val, y_val) for y_val in domain_y):
            domain_x.remove(x_val)
            deleted = True
    return deleted


AC3Context: TypeAlias = Sequence[Domain[Value]]


# XXX: explicitly subclass Inference?
#      `Generic[Value], Inference[AC3Context[Value], DomainSet[Value], Value]`
class AC3(Generic[Variable, Value]):  # pylint: disable=R0903
    # XXX: consider making consts and vars args
    #  => indicate that domains won't be used (should be passed to __call__)
    def __init__(self, csp: CSP[Variable, Value]) -> None:
        self._consts = csp.consts
        self._vars = csp.variables

    def _arc(self, x: Var, y: Var) -> Arc[Variable]:
        return self._vars[x], self._vars[y]

    @property
    def arc_iter(self) -> Iterable[VarArc]:
        return ((x, y) for x, ys in enumerate(self._consts) for y in ys)

    # TODO: could be reduced to O(n^2 * d^2)
    # TODO: generalize arcs to | Iterable[Arc[Variable]]
    def __call__(
        self,
        arcs: Iterable[VarArc],
        domains: Sequence[Domain[Value]] | DomainSetMut[Value],
    ) -> Optional[DomainSet[Value]]:
        """
        Complexity: O(n^3 * d^2) where
          - n is the number of variables
          - d is the maximum domain size
        """

        match domains:
            case DomainSetMut(ds):
                revised_domains = ds
            case ds:
                revised_domains = [set(d) for d in ds]

        queue = deque(arcs)

        # O(n^2) iterations
        while queue:
            x, y = queue.popleft()
            if revise(
                arc=self._arc(x, y),
                domain_x=revised_domains[x],
                domain_y=revised_domains[y],
                const_xy=self._consts[x][y],
            ):
                if not revised_domains[x]:
                    return None
                # Add arcs (z, x) for all constraints x -> z for z other than y
                queue.extend((z, x) for z in self._consts[x] if z != y)

        return revised_domains

    def infer(
        self, assign: Assign[Value], ctx: AC3Context[Value]
    ) -> Optional[DomainSet[Value]]:
        return self(
            arcs=self.arc_iter,
            domains=DomainSetMut(assign >> ctx),
        )


Edge: TypeAlias = Tuple[int, int]


@dataclass(frozen=True)
class ValueGraph(Generic[Value]):
    xs: Sequence[Var]
    vs: Sequence[Value]
    edges: Set[Edge]
    adj: Sequence[Sequence[int]]

    @classmethod
    def new(
        cls,
        xs: Sequence[Var],
        ds: Sequence[Domain[Value]],
    ) -> "ValueGraph[Value]":
        vs = list({v for d in ds for v in d})
        vals = {v: j for j, v in enumerate(vs)}

        edges: Set[Edge] = set()
        adj: List[List[int]] = []
        for i, x in enumerate(xs):
            adj_x: List[int] = []
            domain = ds[x]
            for v in domain:
                adj_x.append(vals[v])
                edges.add((i, vals[v]))
            adj.append(adj_x)

        return cls(xs, vs, edges, adj)

    @property
    def n_vars(self) -> int:
        return len(self.xs)

    @property
    def n_vals(self) -> int:
        return len(self.vs)

    def var(self, i: int) -> Var:
        return self.xs[i]

    def val(self, j: int) -> Value:
        return self.vs[j]


class AllDiffInference(Generic[Variable, Value]):  # pylint: disable=R0903
    def __init__(self, csp: CSP[Variable, Value]) -> None:
        self._vars = csp.vars

    # TODO: check - should run in O(m*sqrt(n))
    # TODO: impl Inference
    # TODO: incremental checking
    #  - alldiff.pdf, p. 24 (paragraph below Algorithm 2)
    #  - CSP containts other contraints => domains change => update G/M
    #  - make use of current value graph and current max matching to compute a
    #    new max matching
    def __call__(
        self,
        constraint: AllDiff[Variable, Value],
        domains: Sequence[Domain[Value]] | DomainSetMut[Value],
    ) -> Optional[DomainSet[Value]]:
        """
        Infer inconsistent domain values in given global `AllDiff` constraint.

        Returns reduced domains or `None` if the current `domains` are
        inconsistent with the `constraint`.

        [source](https://www.andrew.cmu.edu/user/vanhoeve/papers/alldiff.pdf)
         - Algorithm 2 on page 24 (see description on page 23)
         - Goal: identify edges in **any** maximum matching in (X & D(X), E):
            1. find a maximum matching covering X
            1. compute even alternating cycles
            1. compute even alternating paths which begin at a free vertex

        Complexity: `O(m*sqrt(n))` where
         - `n` is the number of variables involved in the alldiff `constraint`
         - `m = sum_i |D_i|`, i.e. `m` is the sum of domain sizes of the
           variables involved in the `constraint`

        Note: Current implementation does not use incremental checking as
        mentioned in the paper. We rather always build new value graph and
        recompute maximum matching from scratch.
        """

        # O(m) in case domains must be copied
        match domains:
            case DomainSetMut(ds):
                revised_domains = ds
            case ds:
                revised_domains = [d.copy() for d in ds]

        # build value graph G = (X, D(X), E):  O(TODO)
        graph = ValueGraph.new(
            xs=[self._vars[x] for x in constraint.iter_vars()],
            ds=revised_domains,
        )

        # XXX: idea - class Edge(i, j, consistent: bool) => mark in-place
        #  1. matching: (i, j) in M => consistent
        #  2. remove(edges)
        #    - make graph by checking consistent (i.e. in M)
        #    - filter scc arcs => mark consistent
        #    - filter dfs => mark consistent
        #  3. walk inconsistent edges => filter domains

        # compute maximum matching M in G
        matching = hopcroft_karp(
            xs=range(graph.n_vars), ys=range(graph.n_vals), adj=graph.adj
        )

        if len(matching) < graph.n_vars:
            return None

        inconsistent = self._remove_inconsitent(
            n=graph.n_vars,
            n_vals=graph.n_vals,
            edges=graph.edges,
            matching=matching,
        )

        for i, j in inconsistent:
            domain = revised_domains[graph.var(i)]
            domain.remove(graph.val(j))
            if not domain:
                return None

        return revised_domains

    @classmethod
    def _remove_inconsitent(
        cls,
        n: int,
        n_vals: int,
        edges: Set[Edge],
        matching: Set[Edge],
    ) -> Set[Edge]:
        # construct directed G_M = (xs + ys, edges with reversed e not in M)
        #  => variable if node < n else value
        graph: List[List[int]] = [[] for _ in range(n + n_vals)]
        # XXX: is this really the best approach?
        #  => alternative: [True] * len(graph)
        free = set(range(len(graph)))

        # TODO: consider modifying edges inplace
        # mark all arcs not in M as unused
        edges = edges - matching

        # x -> v if (x, v) in M else v -> x
        for i, j in matching:
            graph[i].append(j + n)
            free.discard(i)
            free.discard(j + n)

        # v -> x if (x, v) not in M
        for i, j in edges:
            graph[j + n].append(i)

        # Runs in O(n + m) - Tarjan
        scc = tarjan_scc(graph)

        # mark all arcs in a SCC as used
        #  - Arcs between vertices in the same SCC belong to an even
        #    M-alternating circuit in G, and are marked as "consistent".
        #  - i.e. this leaves unmarked only the arcs _between_ components

        # XXX: cloning all unused edges just to remove some is really sad
        for i, j in list(edges):
            if scc[i] == scc[j + n]:
                edges.remove((i, j))

        # perform BFS in G_M starting from M-free vertices, and mark all
        # traversed arcs as used

        # XXX: maxlen => use the fact that gm was constructed from bipartite G
        # XXX: could visited be shared? => graph BFS?

        for src, dst in bfs(graph, inits=free):
            # check if arc starts from a variable: var -> val
            arc = (src, dst - n) if src < n else (dst, src - n)
            edges.discard(arc)

        # return unused
        return edges
