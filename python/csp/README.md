# CSP
Pure Python implementation of a
[CSP](https://en.wikipedia.org/wiki/Constraint_satisfaction_problem)
solver.

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
- `Num` value types: `Linear` can model planar spaces such as
  `a*x + b*y = c`
  - Note: `Linear` can be used in its generalized form
    `a*f(x) + b*g(y) = c` by specifying `x` (and `y`) as
    `VarTransform(x, f)`

Conveniently, binary constraints can be combined together:
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
 - `csp += AllDiff([x1, x2, x3])`, see this
   [paper](https://www.andrew.cmu.edu/user/vanhoeve/papers/alldiff.pdf)
   for algorithm details

# Examples
 - [Sudoku](examples/test_sudoku.py)
 - [N Rooks](examples/test_rooks.py)
 - [N Queens](examples/test_queens.py)
 - [Graph coloring](examples/test_coloring.py)

# Implementation details
The `solve(csp)` algorithm is standard _backtracking search_ with
_arc consistency_ checking (**AC-3.1**) and heuristics:
 - *Variable selection*: _minimal remaining values_ (`MRV`) with
   _degree heuristic_ for tie-breaking
 - *Value prioritization*: _least constraining value first_
   (`LeastConstrainig`)

# Environment
 - `BINARY_ONLY` controls whether CSP will turn all global (currently
   *alldiff*) constraints into corresponding set of binary constraints
   (`BINARY_ONLY=true`) or not (`BINARY_ONLY=false`, default)

## Splitting into independent instances
The `solve(csp)` function uses Tarjan's algorithm for finding strongly
connected components of the constraint graph to build a set of
independent CSPs.

Variables of these CSPs share no constraints between each other and thus
can be solved independently. Currently this is done in sequence but
extension to parallel execution is possible.

# Typing
This CSP library is fully type annotated and type-checked via `mypy`
with the exception of some limitations mentioned below.

Additionally, it passes `flake8` and `pylint` checks.

## Known issues & limitations
 - A small inconvenience is that if one wants to use binders supporting
   ordering operations (e.g. `x < y`), `OrdCSP` must be used to enforce
   `OrdValue`. Similarly with arithmetic operations and `NumCSP`.
 - Plain `Value` currently has an `Eq` bound, but realistically it
   should be `Hash` as well since `Domain` stores values in a `set`.
 - CSP instance is homogeneous in its variable and value type, meaning
   that if one uses for instance the `Linear` constraint, the `Value`
   type must be an instance of `Num` even though only a subset of
   variables is involved.


# Benchmarks
Profiling scripts and benchmarks can be found in directory/module
`benchmarks`.

One can use the optional dependency
[`scalene`](https://github.com/plasma-umass/scalene) to run them for
instance as follows:
```console
scalene --cli --cpu-only --profile-only='bench_' benchmarks/bench_matching.py
```
