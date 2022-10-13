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
