from csp.model import CSP, AssignCtx


def test_model() -> None:
    csp = CSP[str, int]()

    xs = [csp["x1"], csp["x2"]]
    ds = [{0, 1, 2}, {2}]
    x, y = xs

    csp += zip(xs, ds)
    assert csp.num_vars == 2

    x_var, y_var = csp.var(x), csp.var(y)
    assert list(csp.iter_vars()) == [x_var, y_var]

    # TODO: propery-based test: variable . var_id = id = var_id . variable
    assert csp.variable(x_var) == x.var and csp.variable(y_var) == y.var

    csp += (x <= y) & (x != y)

    s = csp.init()

    assert s == AssignCtx(assignment={y_var: 2}, unassigned=[True, False])
    assert not csp.complete(s.assignment)

    assert csp.consistent(x=x_var, x_val=1, a=s.assignment)
    assert csp.consistent(x=y_var, x_val=0, a=s.assignment)
    assert not csp.consistent(x=x_var, x_val=2, a=s.assignment)
