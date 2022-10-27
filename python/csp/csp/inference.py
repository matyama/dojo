from abc import abstractmethod
from collections import deque
from dataclasses import dataclass
from typing import (
    Dict,
    Generic,
    Iterable,
    List,
    Mapping,
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
    Domain,
    DomainSet,
    DomainSetMut,
    Transform,
    Value,
    Var,
    VarArc,
    VArc,
    Variable,
)

C_contra = TypeVar("C_contra", contravariant=True)
I_co = TypeVar("I_co", covariant=True)


class Inference(
    Protocol, Generic[C_contra, I_co, Value]
):  # pylint: disable=R0903
    @abstractmethod
    def infer(self, assign: Assign[Value], ctx: C_contra) -> Optional[I_co]:
        raise NotImplementedError


class RevisionCtx(Generic[Value]):
    """
    Value iteration state used by revision in AC-3.1 (Zhang, Yap)

    Complexity: value ordering constructed in O(n*d), all other operations O(1)
    """

    _last: dict[tuple[Var, Value, Var], tuple[Value, int]]
    _ds: list[list[Value]]

    def __init__(self, ds: Sequence[Domain[Value]]) -> None:
        """`ds` should be initial domains before any revision"""
        self._last = {}
        # XXX: make this efficient (somehow) => make clients handle the copy
        self._ds = [list(d) for d in ds]

    def resume(self, x: Var, x_val: Value, y: Var) -> tuple[Value | None, int]:
        """
        Retrieve the last y value (and its index) with consistent C(x, y)
        """
        item = self._last.get((x, x_val, y))
        return item if item is not None else (None, -1)

    # pylint: disable=too-many-arguments
    def save(self, x: Var, x_val: Value, y: Var, y_val: Value, i: int) -> None:
        """Cache the fact that (x_val, y_val@i) satisfied C(x, y)"""
        self._last[x, x_val, y] = y_val, i

    def next(self, y: Var, i: int) -> Value | None:
        """Get next y value following index i or None if no such exists"""
        d = self._ds[y]
        return d[i + 1] if i + 1 < len(d) else None


# XXX: `y_val in domain_y` will still hash-iter over the domain
def exists(
    arc: VArc[Variable],
    x_val: Value,
    domain_y: Domain[Value],
    const_xy: BinConst[Variable, Value],
    ctx: RevisionCtx[Value],
) -> bool:
    """
    Revision helper procedure for AC-3.1 (Zhang, Yap).

    Returns `True` iff there exists `y_val` in the revision `ctx`, and
    `domain_y`, such that `x := x_val` and `y := y_val` for `x` and `y` from
    the `arc`, is consistent under common constraint `const_xy`.
    """
    x_var, x, y_var, y = arc

    y_val, i = ctx.resume(x, x_val, y)

    if y_val is not None and y_val in domain_y:
        return True

    while (y_val := ctx.next(y, i)) is not None:
        i += 1
        if y_val in domain_y and const_xy((x_var, y_var), x_val, y_val):
            ctx.save(x, x_val, y, y_val, i)
            return True

    return False


def revise(
    arc: VArc[Variable],
    domain_x: Domain[Value],
    domain_y: Domain[Value],
    const_xy: BinConst[Variable, Value],
    ctx: RevisionCtx[Value],
) -> bool:
    """
    Procedure that deletes any value from `domain_x` which is inconsistent
    with values from `domain_y` under constraints represented by `const_xy`.

    Returns: True iff `domain_x` has been changed.
    Complexity: O(d^2) where d is the max domain size
    TODO: update complexity => AC-3.1

    WARN: If a call to `revise` returns True, the contents of `domain_x` has
    been modified (some entries were removed). Otherwise, it's kept unchanged.

    Note: All binary constraints should be combined into one composed
    constraint - see `CompositeConst`.
    """
    deleted = False
    # XXX: list -> another shallow copy, and called inside `while queue`
    for x_val in list(domain_x):
        # Ban x_val if there's no possible y_val consistent with const_xy
        if not exists(arc, x_val, domain_y, const_xy, ctx):
            domain_x.remove(x_val)
            deleted = True
    return deleted


# XXX: explicitly subclass Inference?
#      `Generic[Value], Inference[AC3Context[Value], DomainSet[Value], Value]`
class AC3(Generic[Variable, Value]):  # pylint: disable=R0903
    """Arc consistency mechanism (version 3.1) for binary constraints"""

    # XXX: consider making consts and vars args
    #  => indicate that domains won't be used (should be passed to __call__)
    def __init__(self, csp: CSP[Variable, Value]) -> None:
        self._consts = csp.consts
        self._vars = csp.variables

    def _arc(self, x: Var, y: Var) -> VArc[Variable]:
        return self._vars[x], x, self._vars[y], y

    @property
    def arc_iter(self) -> Iterable[VarArc]:
        return ((x, y) for x, ys in enumerate(self._consts) for y in ys)

    # TODO: generalize arcs to | Iterable[Arc[Variable]]
    def __call__(
        self,
        arcs: Iterable[VarArc],
        domains: Sequence[Domain[Value]] | DomainSetMut[Value],
    ) -> Tuple[Optional[DomainSet[Value]], bool]:
        """
        Implements AC-3.1 (Zhang, Yap)

        Complexity: O(n^2 * d^2) where
          - n is the number of variables
          - d is the maximum domain size
        """

        match domains:
            case DomainSetMut(ds):
                revised_domains = ds
            case ds:
                revised_domains = [set(d) for d in ds]

        # XXX: O(n*d) ... clones domains => improve?
        ctx = RevisionCtx(revised_domains)

        queue = deque(arcs)
        revised = False

        while queue:
            x, y = queue.popleft()
            if revise(
                arc=self._arc(x, y),
                domain_x=revised_domains[x],
                domain_y=revised_domains[y],
                const_xy=self._consts[x][y],
                ctx=ctx,
            ):
                if not revised_domains[x]:
                    return None, True
                # Add arcs (z, x) for all constraints x -> z for z other than y
                queue.extend((z, x) for z in self._consts[x] if z != y)
                revised = True

        return revised_domains, revised

    def infer(
        self, assign: Assign[Value], ctx: Sequence[Domain[Value]]
    ) -> Optional[DomainSet[Value]]:
        revised_domains, _ = self(
            arcs=self.arc_iter,
            domains=DomainSetMut(assign >> ctx),
        )
        return revised_domains


Edge: TypeAlias = Tuple[int, int]


@dataclass(frozen=True)
class ValueGraph(Generic[Value]):
    """
    Bipartite graph G = (xs + vs, edges)

    Attributes:
      - `xs`: set of variables
      - `vs`: set of values (after transformations): `vs[j] = f(vs_dom[i][j])`
      - `vs_dom`: set of domain values (before transformation):
        `f(vs_dom[i][j]) = vs[j]`
      - `edges`: `(i, j) in edges` iff `vs[j] = f(vs_dom[i][j])` and
        `vs_dom[i][j] in dom(xs[i])`
      - `adj`: adjacency list correspoding to edges:
        `(i, j) in edges => j in adj[i]`
    """

    xs: Sequence[Var]
    vs: Sequence[Value]
    vs_dom: Mapping[Edge, Value]
    edges: Set[Edge]
    adj: Sequence[Sequence[int]]

    @classmethod
    def new(
        cls,
        xs: Sequence[Tuple[Var, Optional[Transform[Value]]]],
        ds: Sequence[Domain[Value]],
    ) -> "ValueGraph[Value]":

        vs = cls._values(xs, ds)
        vals = {v: j for j, v in enumerate(vs)}

        vs_dom: Dict[Edge, Value] = {}
        edges: Set[Edge] = set()
        adj: List[List[int]] = []

        for i, (x, f) in enumerate(xs):
            adj_x: List[int] = []

            for v_dom in ds[x]:
                # TODO: f is re-evaluated here => cache under key (x, v_dom)
                v = f(v_dom) if f is not None else v_dom
                j = vals[v]
                vs_dom[i, j] = v_dom
                adj_x.append(j)
                edges.add((i, j))

            adj.append(adj_x)

        return cls(
            xs=[x for x, _ in xs], vs=vs, vs_dom=vs_dom, edges=edges, adj=adj
        )

    @classmethod
    def _values(
        cls,
        xs: Sequence[Tuple[Var, Optional[Transform[Value]]]],
        ds: Sequence[Domain[Value]],
    ) -> List[Value]:
        vs: Set[Value] = set()
        for x, f in xs:
            vs.update(map(f, ds[x]) if f is not None else ds[x])
        return list(vs)

    @property
    def n_vars(self) -> int:
        return len(self.xs)

    @property
    def n_vals(self) -> int:
        return len(self.vs)


class AllDiffInference(Generic[Variable, Value]):  # pylint: disable=R0903
    def __init__(self, csp: CSP[Variable, Value]) -> None:
        self._vars = csp.vars
        # TODO: [c for c in csp.globals if isinstance(c, AllDiff)]
        self._consts = csp.globals

    def infer(
        self, assign: Assign[Value], ctx: Sequence[Domain[Value]]
    ) -> Optional[DomainSet[Value]]:
        revised_domains, _ = self(domains=DomainSetMut(assign >> ctx))
        return revised_domains

    def __call__(
        self,
        domains: Sequence[Domain[Value]] | DomainSetMut[Value],
    ) -> Tuple[Optional[DomainSet[Value]], bool]:

        if not isinstance(domains, DomainSetMut):
            domains = DomainSetMut([d.copy() for d in domains])

        revised = False
        change = True

        # while domains keep being reduced or have been proven inconsistent
        while change:
            change = False

            for c in self._consts:

                revised_domains, reduced = self.infer_alldiff(c, domains)
                revised |= reduced

                if revised_domains is None:
                    return None, revised

                domains = DomainSetMut(revised_domains)
                change |= reduced

        return domains.ds, revised

    # TODO: check - should run in O(m*sqrt(n))
    # TODO: incremental checking
    #  - alldiff.pdf, p. 24 (paragraph below Algorithm 2)
    #  - CSP containts other contraints => domains change => update G/M
    #  - make use of current value graph and current max matching to compute a
    #    new max matching
    def infer_alldiff(
        self,
        constraint: AllDiff[Variable, Value],
        domains: Sequence[Domain[Value]] | DomainSetMut[Value],
    ) -> Tuple[Optional[DomainSet[Value]], bool]:
        """
        Infer inconsistent domain values in given global `AllDiff` constraint.

        Returns reduced domains or `None` if the current `domains` are
        inconsistent with the `constraint`, and a flag indicating whether any
        domain has been reduced.

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
            xs=[(self._vars[x], f) for x, f in constraint.iter_transforms()],
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
            return None, True

        inconsistent = self._remove_inconsitent(
            n=graph.n_vars,
            n_vals=graph.n_vals,
            edges=graph.edges,
            matching=matching,
        )

        for i, j in inconsistent:
            domain = revised_domains[graph.xs[i]]
            domain.remove(graph.vs_dom[i, j])
            if not domain:
                return None, True

        return revised_domains, bool(inconsistent)

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

        # XXX: maxlen => use the fact that graph was built from bipartite G
        # XXX: could visited be shared? => graph BFS?

        for src, dst in bfs(graph, inits=free):
            # check if arc starts from a variable: var -> val
            arc = (src, dst - n) if src < n else (dst, src - n)
            edges.discard(arc)

        # return unused
        return edges


class InferenceEngine(Generic[Variable, Value]):  # pylint: disable=R0903
    """
    Combined inference mechanism that alternates arc and hyper-arc consistency
    as long as input variable domains keep changing (reducing).

    Note that currently the only hyper-arc consistency that we support is the
    alldiff global constraint.
    """

    def __init__(self, csp: CSP[Variable, Value]) -> None:
        self._binary = AC3(csp)
        self._global = AllDiffInference(csp)
        # TODO: generalize AllDiff => GlobalConst

    def infer(
        self, assign: Assign[Value], ctx: Sequence[Domain[Value]]
    ) -> Optional[DomainSet[Value]]:
        domains = DomainSetMut(assign >> ctx)
        revised = True

        # alternate between global and binary inference till domains stabilize
        while revised:
            revised = False

            # Infer feasible domains that are hyper-arc consistent
            revised_domains, reduced = self._global(domains)

            if revised_domains is None:
                return None

            domains = DomainSetMut(revised_domains)
            revised |= reduced

            # Infer feasible domains that are arc-consistent using AC3
            revised_domains, reduced = self._binary(
                arcs=self._binary.arc_iter, domains=domains
            )

            if revised_domains is None:
                return None

            domains = DomainSetMut(revised_domains)
            revised |= reduced

        return domains.ds
