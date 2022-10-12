from itertools import combinations, product
from typing import List, Tuple, TypeAlias

from csp.model import Assignment, Domain, Model, Problem, Vars
from csp.solver import solve


def test_sudoku() -> None:
    puzzle = [
        [5, 3, 0, 0, 7, 0, 0, 0, 0],
        [6, 0, 0, 1, 9, 5, 0, 0, 0],
        [0, 9, 8, 0, 0, 0, 0, 6, 0],
        [8, 0, 0, 0, 6, 0, 0, 0, 3],
        [4, 0, 0, 8, 0, 3, 0, 0, 1],
        [7, 0, 0, 0, 2, 0, 0, 0, 6],
        [0, 6, 0, 0, 0, 0, 2, 8, 0],
        [0, 0, 0, 4, 1, 9, 0, 0, 5],
        [0, 0, 0, 0, 8, 0, 0, 7, 9],
    ]

    expected = [
        [5, 3, 4, 6, 7, 8, 9, 1, 2],
        [6, 7, 2, 1, 9, 5, 3, 4, 8],
        [1, 9, 8, 3, 4, 2, 5, 6, 7],
        [8, 5, 9, 7, 6, 1, 4, 2, 3],
        [4, 2, 6, 8, 5, 3, 7, 9, 1],
        [7, 1, 3, 9, 2, 4, 8, 5, 6],
        [9, 6, 1, 5, 3, 7, 2, 8, 4],
        [2, 8, 7, 4, 1, 9, 6, 3, 5],
        [3, 4, 5, 2, 8, 6, 1, 7, 9],
    ]
    assert Sudoku.valid(expected)

    sudoku = Sudoku()
    csp = sudoku.into_csp(puzzle)

    # Solve Sudoku CSP
    csp_solution = solve(csp)

    actual = sudoku.try_from_csp(csp_solution, csp)
    assert actual is not None
    assert sudoku.valid(actual)
    # assert expected == actual


Digit: TypeAlias = int
Cell: TypeAlias = Tuple[int, int]
SudokuBoard: TypeAlias = List[List[Digit]]


class Sudoku(Model[SudokuBoard, SudokuBoard, Cell, Digit]):
    N = 9
    VALS = set(range(1, N + 1))

    @classmethod
    def valid(cls, s: SudokuBoard) -> bool:
        for row in s:
            assert set(row) == cls.VALS

        for col in range(cls.N):
            assert {s[row][col] for row in range(cls.N)} == cls.VALS

        for i, j in product(range(0, cls.N, 3), repeat=2):
            block_vals = {
                s[i + row][j + col] for row in range(3) for col in range(3)
            }
            assert block_vals == cls.VALS

        return True

    @classmethod
    def domain(cls, val: int) -> Domain[Digit]:
        return {val} if val > 0 else set(range(1, cls.N + 1))

    def into_csp(self, instance: SudokuBoard) -> Problem[Cell, Digit]:
        assert len(instance) == self.N
        assert len(instance[0]) == self.N

        csp: Problem[Cell, Digit] = Problem()

        # Domains for all variables (positions on the board)
        csp += Vars(
            ((row, col), self.domain(val))
            for row, vals in enumerate(instance)
            for col, val in enumerate(vals)
        )

        # Constraints
        for i in range(self.N):

            # Values in each row must all be different
            row_vars = ((i, col) for col in range(self.N))
            for v_x, v_y in combinations(row_vars, 2):
                # TODO: cache vars above {Variable: Var}
                x, y = csp.var_comb(v_x), csp.var_comb(v_y)
                csp += x != y

            # Values in each column must all be different
            col_vars = ((row, i) for row in range(self.N))
            for v_x, v_y in combinations(col_vars, 2):
                x, y = csp.var_comb(v_x), csp.var_comb(v_y)
                csp += x != y

        # Values in each 3x3 square must all be different
        for i, j in product(range(0, self.N, 3), repeat=2):
            block = (
                (i + row, j + col) for row in range(3) for col in range(3)
            )
            for v_x, v_y in combinations(block, 2):
                x, y = csp.var_comb(v_x), csp.var_comb(v_y)
                csp += x != y

        return csp

    def from_csp(
        self, csp_solution: Assignment[Digit], csp: Problem[Cell, Digit]
    ) -> SudokuBoard:
        solution = [[0] * self.N] * self.N

        # Fill the board from the final solution
        for x, val in csp_solution.items():
            row, col = csp.variable(x)
            solution[row][col] = val

        return solution
