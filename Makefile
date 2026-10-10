MAKEFLAGS += -s --no-print-directory
.DEFAULT_GOAL := help
$(if $(filter Windows_NT,$(OS)),$(if $(shell where printf 2>nul),,$(error coreutils is not installed. Please run: winget install coreutils)))

.PHONY: help deps wheel install-global publish-pypi test run-examples format serve clean

help:
	@printf "%s\n" \
		"Usage: make [target]" \
		"" \
		"Targets:" \
		"  deps            Install dependencies" \
		"  test            Run pytest test suite" \
		"  wheel           Build wheel distribution and check with twine" \
		"  install-global  Build wheel and install globally" \
		"  publish-pypi    Build wheel and upload to PyPI" \
		"  run-examples    Run examples autograders and log student view results" \
		"  format          Format Python code using black" \
		"  serve           Start Flask web server" \
		"  clean           Clean build and temporary files"

deps:
	python -m pip install -e ".[dev]"

wheel:
	rm -rf dist build ./*.egg-info
	python -m build --wheel --no-isolation
	python -m twine check dist/*

GLOBAL_PYTHON ?= $(if $(wildcard /usr/bin/python3),/usr/bin/python3,python3)
install-global: wheel
	$(GLOBAL_PYTHON) -m pip install --force-reinstall --break-system-packages --find-links dist autograder-gen

publish-pypi: wheel
	python -m twine upload dist/*

test:
	python -m pytest

run-examples:
	PYTHONPATH=. python -m autograder_gen.cli tests/examples --run-stubs

format:
	python -m black .

serve:
	python autograder_gen/web/app.py --debug

clean:
	rm -rf dist build ./*.egg-info .pytest_cache tests/examples/*/*.zip tests/examples/*/description.* tests/examples/*/rubric.*
