# CSP
Pure Python implementation of a
[CSP](https://en.wikipedia.org/wiki/Constraint_satisfaction_problem) solver.

# Instance builder API
Current implementation supports basic problem building API:
```python
# create new CSP instance
csp = CSP[Node, Color]()

# register variables with their value domains
for n in nodes:
    csp[n] = set("rgb")

# add binary constraints
for x, y in edges:
    csp += csp[x] != csp[y]

# run the solver once finished with building the instance
coloring = solve(csp)
```

# Supported Features

## Binary Constraints
- `Eq` value types: `csp += x == y` or `csp += x != y`
- `Ord` value types: `csp += x < y`, similarly for `<=`, `>=`, and `>`
- `Num` value types: `Linear` can model planar spaces such as `a*x + b*y = c`
  - Note: `Linear` can be used in its generalized form `a*f(x) + b*g(y) = c` by
    specifying `x` (and `y`) as `VarTransform(x, f)`

Convenienly, binary constraints can be combined together:
```python
csp += (x >= y) & (x > z) & (x >= w)
```

## Unary Constraints
```python
x = csp["x"]

csp += x, range(10)

def even(v: int) -> bool:
  return v % 2 == 0

# results in domain(x) = {0, 2, 4, 6, 8}
csp += x | even
```

## Global Constraints
 - `csp += AllDiff([x1, x2, x3])`, note: current implementation naively converts
   the _alldiff_ constraint into an equivalent set of binary constraints

# Examples
 - [Sudoku](examples/test_sudoku.py)
 - [N Rooks](examples/test_rooks.py)
 - [N Queens](examples/test_queens.py)
 - [Graph coloring](examples/test_coloring.py)

# Implementation details
The `solve(csp)` algorithm is standard _backtracking search_ with
_arc consistency_ checking (_AC3_) and heuristics:
 - *Variable selection*: _minimal remaining values_ (`MRV`) with
   _degree heuristic_ for tie-breaking
 - *Value prioritization*: _least constraining value first_ (`LeastConstrainig`)

## Splitting into independent instances
The `solve(csp)` function uses Tarjan's algorithm for finding strongly
connected components of the constraint graph to build a set of
independent CSPs.

Variables of these CSPs share no constraints between each other and thus
can be solved independently. Currently this is done in sequence but
extension to parallel execution is possible.

# Typing
This CSP library is fully type annotated and type-checked via `mypy` with the
exeption of some limitations mentioned below.

Additionally, it passes `flake8` and `pylint` checks.

## Known issues & limitations
 - The type variable `Value` is currently not bound to `Eq`/`Ord` typeclass, so
   when one constructs a binary contraint `x < y` for types which do not
   implement `__lt__`, a runtime error is raised.
 - Similar dynamic check is used when constructing simple `VarTransform`s such
   as `x + 1` (here values mut be instances of `Num`)
 - CSP instance is homogeneous in its variable and value type, meaning that if
   one uses for instance the `Linear` constraint, the `Value` type must be an
   instnce of `Num` even though only a subset of variables is involved.
