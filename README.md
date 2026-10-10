# autograder_gen

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

`autograder_gen` is a tool for lecturers to automatically generate assessment scripts for [Grading a Programming Assignment](https://guides.gradescope.com/hc/en-us/articles/22066635961357-Grading-a-Programming-Assignment) on Gradescope. It supports filling out an interactive web form or providing a YAML configuration, which then generates a packaged ZIP file ready to be uploaded to Gradescope. The project validates your YAML configuration, renders test scripts using Jinja2 templates, and packages everything for immediate upload to Gradescope.

## Supported Languages and Default Runtimes

`autograder_gen` generates autograders configured for Gradescope's Ubuntu container environments (Ubuntu 22.04 LTS by default). The default execution runtimes for supported languages are:

- **Python (`language: python`)**:
  - System **Python 3** (Python 3.10 on Ubuntu 22.04 LTS) via `python3` and `python3-dev`.
  - Includes `pip3` and `gradescope-utils`.
- **Java (`language: java`)**:
  - **OpenJDK 25** via `openjdk-25-jdk`.
  - Standard `javac` compiler and `java` runtime.

If your assessment requires a specific version (such as Python 3.11/3.12 or OpenJDK 17/21) or third-party packages, specify custom installation steps in the `setup_commands` configuration list.

## Installation

Install the package via pip:

```bash
pip install autograder-gen
```

## CLI Usage

When installed, `autograder-gen` generates Gradescope autograders directly from configuration files. Running without parameters displays usage help:

```bash
autograder-gen
```

```text
usage: autograder-gen [TARGET ...] [-h] [--version] [--description]
                      [--run-solution] [--run-stubs] [--verbose]
                      [--schema]

Generate Gradescope autograder script from YAML configuration.

positional arguments:
  TARGET          Configuration YAML file(s) or directories with
                  config.yaml inside (default: ./config.yaml)

options:
  -h, --help      show this help message and exit
  --version       show program's version number and exit
  --description   Generate description.docx and description.md for the
                  assessment
  --run-solution  Run autograder for a solution submission (solution/ or
                  solution.zip) in the same directory as config.yaml
  --run-stubs     Generate and run stub submissions (stub_correct_answer.zip,
                  stub_wrong_answer.zip, stub_compiler_error.zip,
                  stub_correct_answer_wrong_location.zip)
  --verbose, -v   Print full autograder execution logs instead of only paths to
                  log files
  --schema        Print JSON schema for the YAML configuration file and exit
```

### Examples

Single config:

```bash
autograder-gen lab/config.yaml
# OR (directory with a config.yaml)
autograder-gen lab
# OR (zero arguments defaults to ./config.yaml)
autograder-gen
```

Multiple configs:

```bash
autograder-gen lab1/config.yaml lab2/config.yaml
# OR
autograder-gen lab1/ lab2/config.yaml
# OR
autograder-gen lab1/ lab2/
```

Show configuration JSON schema:

```bash
autograder-gen --schema
```

Generate assessment description (`description.docx` and `description.md`):

```bash
autograder-gen config.yaml --description
```

Run solution against an autograder configuration:

```bash
autograder-gen config.yaml --run-solution
```

Run autograder against generated stub submissions:

```bash
autograder-gen config.yaml --run-stubs
```

## Batch Processing

Pass a directory or multiple configuration files as targets to process them together. When passing a directory, each subfolder containing a `config.yaml` (or `config.yml`) will be processed:

Batch generate autograders:

```bash
autograder-gen path/to/assignments/
```

Batch run stub submissions:

```bash
autograder-gen path/to/assignments/ --run-stubs
```

Batch run solution:

```bash
autograder-gen path/to/assignments/ --run-solution
```

## Web Interface

Launch the interactive web interface:

```bash
autograder-gen-web
```

## Development and Building from Source

For development instructions, building from source, and running Python source files directly, see [BUILD.md](BUILD.md).

## Authors

- **Alan Guedes** – [@alanlivio](https://github.com/alanlivio): maintainer
- **Giorgio Werberich Scur** – [@giorgioscur](https://github.com/giorgioscur): intial contributions

## License

Contributions are welcome and will be credited. This project is licensed under the [MIT License](LICENSE).  
The University of Reading retains rights of original contributions.
