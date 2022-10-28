from collections import Counter
from collections.abc import Iterable, Sequence
from functools import partial
from multiprocessing import Pool, cpu_count

from csp.heuristics import MRV, LeastConstraining
from csp.inference import InferenceEngine
from csp.model import CSP, Assign, AssignCtx
from csp.scc import strongly_connected_components
from csp.types import Assignment, Domain, Solution, Value, Var, Variable
from csp.utils import recursionlimit


def solve(
    csp: CSP[Variable, Value], processes: int | None = None
) -> Solution[Variable, Value]:

    # estimate required recursion limit
    recursion_limit = 2 * (csp.num_vars + csp.num_vals)

    with recursionlimit(limit=recursion_limit, non_decreasing=True):
        match _split(csp):
            case [orig]:
                return _solve(orig)
            case subs:
                processes = processes if processes is not None else cpu_count()
                # print(f"CSP intance split into {len(subs)} independent CSPs")
                if processes > 0:
                    with Pool(processes=processes) as pool:
                        solution = {
                            var: val
                            for s in pool.imap_unordered(_solve, subs)
                            for var, val in s.items()
                        }
                else:
                    solution = {
                        var: val
                        for s in map(_solve, subs)
                        for var, val in s.items()
                    }
                return solution if len(solution) == csp.num_vars else {}


def _split(csp: CSP[Variable, Value]) -> list[CSP[Variable, Value]]:
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

    # TODO: return and collects stats
    stats = Counter[str]()
    stats["vars"] = csp.num_vars
    stats["binary"] = sum(len(cs) for cs in csp.consts)
    stats["global"] = len(csp.globals)
    # print(stats)

    def backtracking_search(
        ctx: AssignCtx[Value],
        domains: Sequence[Domain[Value]],
    ) -> Assignment[Value] | None:

        if complete(ctx.assignment):
            return ctx.assignment

        stats["states"] += 1

        var = next_var(ctx.unassigned, domains)
        ctx.unassigned[var] = False

        # TODO: debug logging support
        # print(
        #    f"var={var}",
        #    f"|A|={len(ctx.assignment)}",
        #    # f"ds={domains}",
        #    f"ord={vals}",
        # )

        for val in sort_domain(var, domains, ctx.unassigned):

            # Check if assignment var := val is consistent
            if consistent(var, val, ctx.assignment):
                # print(f"x{var} := {val} >> {ctx.assignment}")
                ctx.assignment[var] = val
                stats["inferences"] += 1

                # Infer feasible domains
                revised_domains = inference_engine.infer(
                    assign=Assign(var, val), ctx=domains
                )
                # print(f">>> revised [x{var} := {val}]: {revised_domains}")
                # stats["revised"] += num_revised

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
    # print(stats)

    return csp.as_solution(assignment) if assignment is not None else {}
