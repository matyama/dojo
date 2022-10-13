from functools import partial
from operator import itemgetter
from typing import Optional, Sequence

from csp.inference import AC3
from csp.model import Assign, AssignCtx, Problem
from csp.types import Assignment, Domain, Solution, Value, Var, Variable

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


def solve(csp: Problem[Variable, Value]) -> Solution[Variable, Value]:

    consistent = partial(Problem[Variable, Value].consistent, csp)
    complete = partial(Problem[Variable, Value].complete, csp)

    snd: itemgetter[int] = itemgetter(1)

    # TODO: generalize over this strategy
    # TODO: MRV tie-breaking => degree heuristic
    #       var with the most constraints on remaining vars
    def next_var(
        remaining: Sequence[bool], domains: Sequence[Domain[Value]]
    ) -> Var:
        """Min. remaining value (MRV) selection"""
        var, _ = min(
            ((x, len(d)) for x, d in enumerate(domains) if remaining[x]),
            key=snd,
        )
        return var

    inference_engine = AC3(csp)

    def backtracking_search(
        ctx: AssignCtx[Value],
        domains: Sequence[Domain[Value]],
    ) -> Optional[Assignment[Value]]:

        if complete(ctx.assignment):
            return ctx.assignment

        var = next_var(ctx.unassigned, domains)
        ctx.unassigned[var] = False

        # TODO: sorted(domains(var), key=some_strategy)
        #  - or rather keep domains sorted => must also apply to inference
        #    (`revised_domains`)
        #  - strategy => least constraining value (among remaining vars)
        for val in domains[var]:

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
