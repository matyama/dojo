# CSP
Pure Python implementation of a
[CSP](https://en.wikipedia.org/wiki/Constraint_satisfaction_problem) solver.

# Instance builder API
Current implementation supports basic problem building API:
```python
# create new CSP instance
csp: Problem[Node, Color] = Problem()

# register variables with their value domains
for n in nodes:
    csp += (n, set("rgb"))

# add binary constraints
for n1, n2 in edges:
    x, y = csp.var_comb(n1), csp.var_comb(n2)
    csp += x != y

# run the solver once finished with building the instance
coloring = solve(csp)
```

# Examples
 - [Sudoku](examples/test_sudoku.py)
 - [Graph coloring](examples/test_coloring.py) (Graph is the map of Australia)
