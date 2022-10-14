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

# Examples
 - [Sudoku](examples/test_sudoku.py)
 - [N Rooks](examples/test_rooks.py)
 - [Graph coloring](examples/test_coloring.py) (Graph is the map of Australia)


# Typing
This CSP library is fully type annotated and type-checked via `mypy` with the
exeption of some limitations mentioned below.

Additionally, it passes `flake8` and `pylint` checks.

## Known issues & limitations
 - The type variable `Value` is currently not bound to `Eq`/`Ord` typeclass, so
   when one constructs a binary contraint `x < y` for types which do not
   implement `__lt__`, a runtime error is raised.
 - CSP instance is homogeneous in its variable and value type, meaning that if
   one uses for instance the `Linear` constraint, the `Value` type must be an
   instnce of `Num` even though only a subset of variables is involved.
