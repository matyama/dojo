from functools import partial
from typing import Iterable, List, Optional, Sequence

from csp.heuristics import MRV, LeastConstraining
from csp.inference import InferenceEngine
from csp.model import CSP, Assign, AssignCtx
from csp.scc import strongly_connected_components
from csp.types import Assignment, Domain, Solution, Value, Var, Variable


# TODO: API features
#  - new parames: `inference_engine: Inference[...]`, `next_val: ...`
def solve(csp: CSP[Variable, Value]) -> Solution[Variable, Value]:
    match _split(csp):
        case [orig]:
            return _solve(orig)
        case subs:
            # TODO: solve multiple independent CSPs in parallel
            solutions: Iterable[Solution[Variable, Value]] = map(_solve, subs)
            solution = {var: val for s in solutions for var, val in s.items()}
            return solution if len(solution) == csp.num_vars else {}


def _split(csp: CSP[Variable, Value]) -> List[CSP[Variable, Value]]:
    # TODO: take into account global consts and split those as well if possible
    if csp.globals:
        return [csp]
    const_graph = [list(ys.keys()) for ys in csp.consts]
    scc = strongly_connected_components(graph=const_graph)

    def sub_csp(component: Iterable[Var]) -> CSP[Variable, Value]:
        sub = CSP[Variable, Value]()

        for x in component:
            sub += csp.variables[x], csp.domains[x]

        for x in component:
            # NOTE: since this is a SCC, all neighbors of x are in it as well
            for c in csp.consts[x].values():
                sub += c

        return sub

    return [sub_csp(component) for component in scc] if len(scc) > 1 else [csp]


def _solve(csp: CSP[Variable, Value]) -> Solution[Variable, Value]:

    consistent = partial(CSP[Variable, Value].consistent, csp)
    complete = partial(CSP[Variable, Value].complete, csp)

    next_var = MRV[Value](consts=[cs.keys() for cs in csp.consts])
    sort_domain = LeastConstraining[Variable, Value](csp)
    inference_engine = InferenceEngine(csp)

    def backtracking_search(
        ctx: AssignCtx[Value],
        domains: Sequence[Domain[Value]],
    ) -> Optional[Assignment[Value]]:

        if complete(ctx.assignment):
            return ctx.assignment

        var = next_var(ctx.unassigned, domains)
        ctx.unassigned[var] = False

        for val in sort_domain(var, domains, ctx.unassigned):

            # Check if assignment var := val is consistent
            if consistent(var, val, ctx.assignment):
                ctx.assignment[var] = val

                # Infer feasible domains
                revised_domains = inference_engine.infer(
                    assign=Assign(var, val), ctx=domains
                )

                # Check if the inference found this sub-space feasible
                if revised_domains is not None:
                    assignment = backtracking_search(ctx, revised_domains)
                    if assignment is not None:
                        return assignment

                del ctx.assignment[var]

        ctx.unassigned[var] = True
        return None

    # Solve Sudoku CSP
    assignment = backtracking_search(
        ctx=csp.init(),
        domains=csp.domains,
    )

    return csp.as_solution(assignment) if assignment is not None else {}
