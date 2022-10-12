from functools import reduce
from operator import and_

from csp.constraints import BinConst, Different, LessEq


def test_composite() -> None:

    x0, x1 = 0, 1

    c1: BinConst[int, int] = LessEq(x0, x1)
    c2: BinConst[int, int] = Different(x0, x1)

    c = c1 & c2

    assert str(c) == "x[0] <= x[1] & x[0] != x[1]"
    assert c.sat(x_val=2, y_val=4)
    assert not c.sat(x_val=4, y_val=2)
    assert not c.sat(x_val=2, y_val=2)

    r = reduce(and_, [c1, c2])
    assert str(r) == str(c)
