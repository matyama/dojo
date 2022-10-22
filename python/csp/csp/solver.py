import sys
from collections import Counter
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

    # TODO: contextualize this (decorator / ctx manager)
    #  - https://stackoverflow.com/a/50120316
    old_rec_limit = sys.getrecursionlimit()
    new_rec_limit = _estimate_recursion_depth(csp)
    sys.setrecursionlimit(max(old_rec_limit, new_rec_limit))

    match _split(csp):
        case [orig]:
            return _solve(orig)
        case subs:
            print(f">>> CSP intance split into {len(subs)} independent CSPs")
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

    # FIXME: global constraints => not taken into account here
    next_var = MRV[Variable, Value](csp)
    sort_domain = LeastConstraining[Variable, Value](csp)
    inference_engine = InferenceEngine(csp)

    stats = Counter[str]()
    stats["vars"] = csp.num_vars
    stats["binary"] = sum(len(cs) for cs in csp.consts)
    stats["global"] = len(csp.globals)
    print(stats)

    def backtracking_search(
        ctx: AssignCtx[Value],
        domains: Sequence[Domain[Value]],
    ) -> Optional[Assignment[Value]]:

        if complete(ctx.assignment):
            return ctx.assignment

        stats["states"] += 1

        var = next_var(ctx.unassigned, domains)
        ctx.unassigned[var] = False

        vals = list(sort_domain(var, domains, ctx.unassigned))
        # print(
        #    f"var={var}",
        #    f"|A|={len(ctx.assignment)}",
        #    # f"ds={domains}",
        #    f"ord={vals}",
        # )

        # for val in sort_domain(var, domains, ctx.unassigned):
        for val in vals:

            # Check if assignment var := val is consistent
            if consistent(var, val, ctx.assignment):
                # print(f"x{var} := {val} >> {ctx.assignment}")
                ctx.assignment[var] = val
                stats["inferences"] += 1

                # num_vals_start = sum(
                #    len(d) for d in (Assign(var, val) >> domains)
                # )

                # XXX: 10-Queens => prunes init x0 := 0 even tho binary finds a
                #      solution with this assignment => alldiff inference bug
                #      => revised_domains is None ???
                #      => after multiple iters: fails on |M| >= |X|
                #          - due to missing value in some input domains
                # even with single iteration: x0 := 0 => revised_domains
                #  - compared to binary, missing some values => unsound infer
                #  - e.g. 1: 3, 5: 2
                #
                # but alldiff inference works on examples from papers, so the
                # issue is probably on the side of VarTransofrm
                #  - Queens => debug => 1st alldiff(xs) looks fine
                #    (for x0 := 0 filters 0 from all other domains)
                #  - TODO: debug the other two constraints (i.e. with f)

                # Infer feasible domains
                revised_domains = inference_engine.infer(
                    assign=Assign(var, val), ctx=domains
                )
                # print(f">>> revised [x{var} := {val}]: {revised_domains}")

                # num_vals_end = sum(len(d) for d in revised_domains or [])
                # stats["revised"] += num_vals_start - num_vals_end

                # Check if the inference found this sub-space feasible
                if revised_domains is not None:
                    # print(f">>> searching deeper with x{var} := {val}")
                    assignment = backtracking_search(ctx, revised_domains)
                    if assignment is not None:
                        return assignment

                    stats["backtracks"] += 1
                    # print(f">>> backtracking from x{var} := {val}")
                else:
                    stats["pruned"] += 1
                    # print(f">>> PRUNED: x{var} := {val}")

                del ctx.assignment[var]
            else:
                stats["inconsistent"] += 1

        ctx.unassigned[var] = True
        return None

    # Solve Sudoku CSP
    assignment = backtracking_search(
        ctx=csp.init(),
        domains=csp.domains,
    )

    # TODO: rather return as an extra part of the output
    print(assignment)
    print(stats)

    return csp.as_solution(assignment) if assignment is not None else {}


def _estimate_recursion_depth(csp: CSP[Variable, Value]) -> int:
    n_vars = csp.num_vars
    n_vals = len({v for d in csp.domains for v in d})
    return 2 * (n_vars + n_vals)
