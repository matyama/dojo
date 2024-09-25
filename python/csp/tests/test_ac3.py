import pytest

from csp.constraints import Linear, Space2D
from csp.inference import AC3, RevisionCtx, revise
from csp.model import CSP, Assign, OrdCSP
from csp.types import DomainSet


@pytest.fixture(name="a")
def csp_a() -> CSP[str, int]:
    csp = OrdCSP[str, int]()

    x1, x2, x3 = csp["x1"], csp["x2"], csp["x3"]

    csp[x1] = {1, 2, 3}
    csp[x2] = {1, 2, 3}
    csp[x3] = {2, 3}

    csp += x1 > x2
    csp += x2 != x3
    csp += Linear(a=1, x=x2.var, b=1, y=x3.var, c=4, space=Space2D.UPPER_OPEN)

    return csp


@pytest.fixture(name="b")
def csp_b() -> CSP[str, int]:
    csp = CSP[str, int]()

    x1, x2, x3 = csp["x1"], csp["x2"], csp["x3"]
    csp[x1] = {1, 2, 3}
    csp[x2] = {1, 2, 3}
    csp[x3] = {1, 2, 3}

    csp += x1 == x2
    # shift: x + 1 = y
    csp += Linear(a=1, x=x2.var, b=-1, y=x3.var, c=-1)

    return csp


@pytest.fixture(name="instance")
def dispatch_instance(
    request: pytest.FixtureRequest, a: CSP[str, int], b: CSP[str, int]
) -> CSP[str, int]:
    instances = {"a": a, "b": b}
    return instances[request.param]


def test_revise(a: CSP[str, int]) -> None:
    x1, x2, x3 = a.variables
    x1_var, x2_var, x3_var = a.var(x1), a.var(x2), a.var(x3)
    d_x1, d_x2, d_x3 = a.domains
    c12 = a.const(x1, x2)
    c23 = a.const(x2, x3)

    ctx = RevisionCtx(a.domains)

    assert c12 is not None
    assert c23 is not None

    assert revise(
        arc=(x1, x1_var, x2, x2_var),
        domain_x=d_x1,
        domain_y=d_x2,
        const_xy=c12,
        ctx=ctx,
    )
    assert d_x1 == {2, 3} and d_x2 == {1, 2, 3}

    assert revise(
        arc=(x2, x2_var, x1, x1_var),
        domain_x=d_x2,
        domain_y=d_x1,
        const_xy=c12,
        ctx=ctx,
    )
    assert d_x2 == {1, 2} and d_x1 == {2, 3}

    assert revise(
        arc=(x2, x2_var, x3, x3_var),
        domain_x=d_x2,
        domain_y=d_x3,
        const_xy=c23,
        ctx=ctx,
    )
    assert d_x2 == {2} and d_x3 == {2, 3}

    assert revise(
        arc=(x3, x3_var, x2, x2_var),
        domain_x=d_x3,
        domain_y=d_x2,
        const_xy=c23,
        ctx=ctx,
    )
    assert d_x3 == {3} and d_x2 == {2}

    assert revise(
        arc=(x1, x1_var, x2, x2_var),
        domain_x=d_x1,
        domain_y=d_x2,
        const_xy=c12,
        ctx=ctx,
    )
    assert d_x1 == {3} and d_x2 == {2}

    assert [d_x1, d_x2, d_x3] == [{3}, {2}, {3}]


@pytest.mark.parametrize(
    "instance,expected",
    [
        pytest.param("a", [{3}, {2}, {3}], id="A"),
        pytest.param("b", [{1, 2}, {1, 2}, {2, 3}], id="B"),
    ],
    indirect=["instance"],
)
def test_ac3(instance: CSP[str, int], expected: DomainSet[int] | None) -> None:
    ac3 = AC3(csp=instance)
    revised_domains, _ = ac3(arcs=ac3.arc_iter, domains=instance.domains)
    assert revised_domains == expected


@pytest.mark.parametrize(
    "x,v,expected",
    [
        pytest.param("x1", 3, [{3}, {2}, {3}], id="x1 := 3"),
        pytest.param("x1", 1, None, id="x1 := 1"),
    ],
)
def test_infer(
    x: str, v: int, expected: DomainSet[int] | None, a: CSP[str, int]
) -> None:
    actual = AC3(a).infer(assign=Assign(var=a.var(x), val=v), ctx=a.domains)
    assert expected == actual
