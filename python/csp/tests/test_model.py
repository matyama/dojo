from csp.model import AssignCtx, OrdCSP


def test_model() -> None:
    csp = OrdCSP[str, int]()

    xs = [csp["x1"], csp["x2"]]
    ds = [{0, 1, 2}, {2, 3}]
    x, y = xs

    csp += zip(xs, ds)
    assert csp.num_vars == 2

    x_var, y_var = csp.var(x), csp.var(y)
    assert list(csp.iter_vars()) == [x_var, y_var]

    assert csp.variable(x_var) == x.var and csp.variable(y_var) == y.var

    csp += (x <= y) & (x != y)

    def even(v: int) -> bool:
        return v % 2 == 0

    csp += y | even

    s = csp.init()

    assert s == AssignCtx(assignment={y_var: 2}, unassigned=[True, False])
    assert not csp.complete(s.assignment)

    assert csp.consistent(x=x_var, x_val=1, a=s.assignment)
    assert csp.consistent(x=y_var, x_val=0, a=s.assignment)
    assert not csp.consistent(x=x_var, x_val=2, a=s.assignment)
