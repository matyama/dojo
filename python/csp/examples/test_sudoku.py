from collections.abc import Iterable
from itertools import product
from typing import TypeAlias

from csp.constraints import AllDiff
from csp.model import CSP, Domain, Model, Solution
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

    sudoku = Sudoku()
    csp = sudoku.into_csp(puzzle)

    # Solve Sudoku CSP
    solution = solve(csp)

    board = sudoku.from_csp(solution)

    sudoku.validate(board)
    assert board == expected


Digit: TypeAlias = int
Cell: TypeAlias = tuple[int, int]
SudokuBoard: TypeAlias = list[list[Digit]]


class Sudoku(Model[SudokuBoard, SudokuBoard, Cell, Digit]):
    N = 9
    VALS = set(range(1, N + 1))

    @classmethod
    def validate(cls, s: SudokuBoard) -> None:
        for row in s:
            assert set(row) == cls.VALS

        for col in range(cls.N):
            assert {s[row][col] for row in range(cls.N)} == cls.VALS

        block = list(product(range(3), repeat=2))
        for i, j in product(range(0, cls.N, 3), repeat=2):
            assert {s[i + x][j + y] for x, y in block} == cls.VALS

    @classmethod
    def domain(cls, val: int) -> Domain[Digit] | Iterable[Digit]:
        return {val} if val > 0 else range(1, cls.N + 1)

    def into_csp(self, instance: SudokuBoard) -> CSP[Cell, Digit]:
        assert len(instance) == self.N
        assert len(instance[0]) == self.N

        csp = CSP[Cell, Digit]()

        # Domains for all variables (positions on the board)
        csp += (
            ((row, col), self.domain(val))
            for row, vals in enumerate(instance)
            for col, val in enumerate(vals)
        )

        # Values in each row must all be different
        for row in range(self.N):
            csp += AllDiff((row, col) for col in range(self.N))

        # Values in each column must all be different
        for col in range(self.N):
            csp += AllDiff((row, col) for row in range(self.N))

        # Values in each 3x3 block must all be different
        block = list(product(range(3), repeat=2))
        for i, j in product(range(0, self.N, 3), repeat=2):
            csp += AllDiff((i + x, j + y) for x, y in block)

        return csp

    def from_csp(self, solution: Solution[Cell, Digit]) -> SudokuBoard:
        board = [[0] * self.N for _ in range(self.N)]

        # Fill the board from the final solution
        for (row, col), val in solution.items():
            board[row][col] = val

        return board
