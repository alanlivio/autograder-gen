# Building from Source

Run `make help` to inspect available Makefile targets.

## Environment Setup

Create and activate a virtual environment:

```bash
# Windows (PowerShell)
python -m venv .venv
. .venv\Scripts\Activate.ps1

# Linux / macOS (Bash)
python3 -m venv .venv
source .venv/bin/activate
```

## Install Dependencies

```bash
make deps
```

## Running Python Scripts

### CLI Generator

Run `autograder_gen/cli.py` directly using Python:

```bash
python autograder_gen/cli.py tests/examples/py_simple/config.yaml
```

Options:

- Generate assessment description (`description.docx` and `description.md`):

```bash
python autograder_gen/cli.py tests/examples/py_simple/config.yaml --description
```

- Run solution against an autograder configuration:

```bash
python autograder_gen/cli.py tests/examples/py_simple/config.yaml --run-solution
```

- Run autograder against generated stub submissions:

```bash
python autograder_gen/cli.py tests/examples/py_simple/config.yaml --run-stubs
```

### Batch Processing

Generate autograders for all configurations in a directory:

```bash
python autograder_gen/cli.py tests/examples --run-stubs
```

### Web Interface

Run `autograder_gen/web/app.py` directly to start the web server:

```bash
python autograder_gen/web/app.py
```

Or run via Makefile:

```bash
make serve
```

## Testing

Run the test suite:

```bash
make test
```

Or invoke pytest directly:

```bash
python -m pytest
```

## Formatting

Format Python code using Black:

```bash
make format
```

## Building Distribution Packages

Build wheel and source distributions:

```bash
make build
```

Or build wheel only and verify with twine:

```bash
make wheel
```

Run `make help` to see all available Makefile targets.
