from csp.heuristics import MRV, LeastConstraining
from csp.model import CSP


def test_mrv() -> None:
    x, y, z, w = 0, 1, 2, 3

    # note: x: {z, w} => x: |{z}| because remaining[w] = False
    consts = [{z, w}, {z}, {x, y}, {x}]

    next_val = MRV[int](consts)

    domains = [{1}, {1, 2}, {1}, {1}]
    remaining = [True, True, True, False]

    # (<var>, <domain size>, <no. unassigned neighbors>)
    # note: w not included because remaining[w] = Falase
    # min [(x, 1, -1), (y, 2, -1), (z, 1, -2)] = (z, 1, -2)
    assert next_val(remaining, domains) == z


def test_least_constraining_domain_sort() -> None:

    csp = CSP[str, int]()
    sort_domain = LeastConstraining(csp)

    xs = [csp["x"], csp["y"], csp["z"], csp["w"]]
    ds = [{1, 2, 3}, {1, 2, 3}, {2, 3, 4}, {2}]
    x, y, z, w = xs

    csp += zip(xs, ds)

    csp += (x >= y) & (x > z) & (x >= w)

    vals = sort_domain(
        x=csp.var("x"),
        domains=[{1, 2, 3}, {1, 2}, {2, 4}, {2}],
        unassigned=[False, True, True, False],
    )

    # min [(v=1, 3), (v=2, 2), (v=3, 1)]
    assert list(vals) == [3, 2, 1]
