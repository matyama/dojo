from abc import abstractmethod
from collections import deque
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
from csp.matching import max_bipartite_matching
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


# Resources:
#  - https://en.wikipedia.org/wiki/Matching_(graph_theory)
#  - https://en.wikipedia.org/wiki/Maximally-matchable_edge
#  - https://doi.org/10.1016%2Fj.tcs.2011.12.071
#  - alldiff.pdf: https://www.andrew.cmu.edu/user/vanhoeve/papers/alldiff.pdf
#  - alldiff.pdf, p. 23 (description), p. 24 (Algorithm 2)
#    - dag G_M = (X \cup D_X, A) with arc set
#      A = {(u, v) | (u, v) in M} \cup {(v, u) | (v, u) not in M}
#    - vertex v is *M-free* if M does not cover v


# TODO: check complexity (link alldiff arxiv): O(m*sqrt(n))
#  - n ... number of variables involved in the alldiff constraint
#  - m = \sum_{i=1}{n} |D_i|
#  - i.e. m is the sum of domain sizes of the variables involved in the const.
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

        # O(m) in case domains must be copied
        match domains:
            case DomainSetMut(ds):
                revised_domains = ds
            case ds:
                revised_domains = [d.copy() for d in ds]

        # O(n + m)
        xs = [self._vars[x] for x in constraint.iter_vars()]
        vs = list({v for d in revised_domains for v in d})
        vals = {v: j for j, v in enumerate(vs)}

        # build value graph G = (X, D(X), E):  O(TODO)
        # XXX: mypy issue
        # edges = {
        #    (i, val_ids[v])
        #    for i, x in enumerate(xs)
        #    for d in revised_domains[x]
        #    for v in d
        # }
        edges = set()
        # XXX: remvoe adj if unused [relevant for hopcroft_karp]
        # adj = []
        for i, x in enumerate(xs):
            # adj_x = []
            domain = revised_domains[x]
            for v in domain:
                # adj_x.append(vals[v])
                edges.add((i, vals[v]))
            # adj.append(adj_x)

        # XXX: idea - class Edge(i, j, consistent: bool) => mark in-place
        #  1. matching: (i, j) in M => consistent
        #  2. remove(edges)
        #    - make graph by checking consistent (i.e. in M)
        #    - filter scc arcs => mark consistent
        #    - filter dfs => mark consistent
        #  3. walk inconsistent edges => filter domains

        # compute maximum matching M in G
        #  - TODO: complexity
        matching = max_bipartite_matching(
            xs=range(len(xs)), ys=range(len(vs)), edges=edges
        )

        if len(matching) < len(xs):
            return None

        edges = self._remove_inconsitent(
            n=len(xs), n_vals=len(vs), edges=edges, matching=matching
        )

        # O(TODO) loop
        for i, j in edges:
            domain = revised_domains[xs[i]]
            domain.remove(vs[j])
            if not domain:
                return None

        return revised_domains

    @classmethod
    def _remove_inconsitent(
        cls,
        n: int,
        n_vals: int,
        edges: Set[Tuple[int, int]],
        matching: Set[Tuple[int, int]],
    ) -> Set[Tuple[int, int]]:
        # construct DAG G_M, while marking all arcs not in M as unused
        #  - nodes = xs ++ ys: O(n + m)
        #  => variable if node < n else value
        graph: List[List[int]] = [[] for _ in range(n + n_vals)]
        # XXX: is this really the best approach?
        #  => alternative: [True] * len(graph)
        free = set(range(len(graph)))

        # TODO: consider modifying edges inplace
        edges = edges - matching

        # x -> v if (x, v) in M else v -> x
        for i, j in matching:
            graph[i].append(j + n)
            free.discard(i)
            free.discard(j + n)

        # v -> x if (x, v) not in M
        for i, j in edges:
            graph[j + n].append(i)

        # XXX: check duplicated nodes in graph's adj. lists

        # Runs in O(n + m) - Tarjan
        scc = tarjan_scc(graph)

        # mark all arcs in a SCC as used
        #  - Arcs between vertices in the same SCC belong to an even
        #    M-alternating circuit in G, and are marked as "consistent".
        #  - i.e. this leaves unmarked only the arcs _between_ components

        # XXX: cloning unused just to remove is really sad
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


# Identify edges in **any** max. matching (A \cup B, E):
#  1. find a max matching covering A
#  2. compute even alternating paths which begin at a free vertex
#  3. compute even alternating cycles
#
# alternating path ~ a path that begins with an unmatched vertex and whose
#                    edges belong alternately to the matching and not
#
# augmenting path ~ an alternating path that starts from and ends on free v.

# TODO: imple GAC-3(G) from Bartak, lecture 08 (?) => general n-ary const alg
