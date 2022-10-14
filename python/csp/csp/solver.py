from functools import partial
from typing import Optional, Sequence

from csp.heuristics import MRV, LeastConstraining
from csp.inference import AC3
from csp.model import CSP, Assign, AssignCtx
from csp.types import Assignment, Domain, Solution, Value, Variable

# TODO: API features
#  - MVP: bianry constraints
#  - alldiff([x, y, z]) constraints
#  - CSP problem builder API => DSL: csp += x != y
#  - constraints => connected components => solve independently

# TODO: representation
#  - use lists => {variables} => {idx: var} and further repr vars as ints
#  - consequence: Variable does not have to be Hash, possibly not even Eq
#  - assignment: List[Optional[Value]] ...as a WIP solution
#    - assignment[i] = Some(v) if x_i := v else None
#  - final solution: Optional[Dict[Variable, Value]] or without just Dict
#    => indicate failure bu an empty Dict (?)


# TODO: new parames: `inference_engine: Inference[...]`, `next_val: ...`
def solve(csp: CSP[Variable, Value]) -> Solution[Variable, Value]:

    consistent = partial(CSP[Variable, Value].consistent, csp)
    complete = partial(CSP[Variable, Value].complete, csp)

    next_var = MRV[Value](consts=[cs.keys() for cs in csp.consts])
    sort_domain = LeastConstraining[Variable, Value](csp)
    inference_engine = AC3(csp)

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

                # Infer feasible domains that are arc-consistent using AC3
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
