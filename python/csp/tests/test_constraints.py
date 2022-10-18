from functools import reduce
from operator import and_

from csp.constraints import BinConst, Different, LessEq
from csp.types import VarTransform


def test_composite() -> None:
    x1 = VarTransform[str, int](x="x1", f=lambda v: 2 * v)
    x2 = "x2"

    c1: BinConst[str, int] = LessEq(x1, x2)
    c2: BinConst[str, int] = Different(x1, x2)

    c = c1 & c2

    assert str(c) == "f(x1) <= x2 & f(x1) != x2"
    assert c(arc=(x1.x, x2), x_val=1, y_val=4)
    assert c(arc=(x2, x1.x), x_val=4, y_val=1)
    assert not c(arc=(x1.x, x2), x_val=2, y_val=2)
    assert not c(arc=(x1.x, x2), x_val=1, y_val=2)

    r = reduce(and_, [c1, c2])
    assert str(r) == str(c)
