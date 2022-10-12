.PHONY: all check fmt lint tests
.DEFAULT_GOAL := all

install:
	poetry env use python3.10
	poetry install

fmt:
	isort .
	black .

lint:
	flake8 .
	pylint csp tests examples
	mypy .

tests:
	pytest

check: lint tests

all: fmt check
