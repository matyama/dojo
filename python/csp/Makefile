.PHONY: all check fmt lint tests
.DEFAULT_GOAL := all

install:
	poetry env use python3.12
	poetry install

fmt:
	ruff check --select I --fix .
	ruff format

lint:
	ruff format --check
	ruff check
	mypy .

tests:
	pytest

check: lint tests

all: fmt check
