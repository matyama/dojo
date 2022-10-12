from typing import Tuple

from csp.model import AssignCtx, Problem, Vars


def test_model() -> None:
    csp: Problem[Tuple[int, int], int] = Problem()

    v_x, d_x = (0, 0), {0, 1, 2}
    v_y, d_y = (1, 1), {2}

    csp += Vars([(v_x, d_x), (v_y, d_y)])
    assert csp.num_vars == 2

    x_i, y_i = csp.var(v_x), csp.var(v_y)
    assert list(csp.iter_vars()) == [x_i, y_i]

    # TODO: propery-based test: variable . var_id = id = var_id . variable
    assert csp.variable(x_i) == v_x and csp.variable(y_i) == v_y

    x, y = csp.var_comb(v_x), csp.var_comb(v_y)
    csp += (x <= y) & (x != y)

    s = csp.init()

    assert s == AssignCtx(assignment={y_i: 2}, unassigned=[True, False])
    assert not csp.complete(s.assignment)

    assert csp.consistent(x=x_i, x_val=1, a=s.assignment)
    assert csp.consistent(x=y_i, x_val=0, a=s.assignment)
    assert not csp.consistent(x=x_i, x_val=2, a=s.assignment)
