# autograder_gen

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

`autograder_gen` is a tool for lecturers to automatically generate assessment scripts for [Grading a Programming Assignment](https://guides.gradescope.com/hc/en-us/articles/22066635961357-Grading-a-Programming-Assignment) on Gradescope. It supports filling out an interactive web form or providing a YAML configuration, which then generates a packaged ZIP file ready to be uploaded to Gradescope. The project validates your YAML configuration, renders test scripts using Jinja2 templates, and packages everything for immediate upload to Gradescope.

## Installation

Install the package via pip:

```bash
pip install autograder-gen
```

## CLI Usage

The package provides two command-line tools:

- `autograder-gen`: Generates Gradescope autograders and test stub packages from configuration files.
- `autograder-run`: Runs student submissions or test stubs against an autograder.

### Generating Autograders (`autograder-gen`)

```text
autograder-gen
usage: autograder-gen [TARGET ...] [-h] [--version] [--description]

Generate Gradescope autograder script from YAML configuration.

positional arguments:
  TARGET          Configuration YAML file(s) or directories with
                  config.yaml inside (default: ./config.yaml)

options:
  -h, --help      show this help message and exit
  --version       show program's version number and exit
  --description   Generate description.docx and description.md for the
                  assessment
```

#### Examples

Single config:

```bash
autograder-gen lab/config.yaml
# OR (directory with a config.yaml)
autograder-gen lab
# OR (zero arguments defaults to ./config.yaml)
autograder-gen
```

Multiple configs or directories:

```bash
autograder-gen lab1/config.yaml lab2/config.yaml
# OR
autograder-gen lab1/ lab2/
# OR directory containing subfolders with config.yaml
autograder-gen path/to/assignments/
```

### Running Submissions (`autograder-run`)

Use `autograder-run` to execute submissions or stubs against an autograder configuration:

```bash
autograder-run config.yaml student_submission.zip
# OR (in directory with config.yaml)
autograder-run student_submission.zip
```

Run autograder against generated stub submissions:

```bash
autograder-run config.yaml --stubs
# OR directory containing subfolders with config.yaml
autograder-run path/to/assignments/ --stubs
```

## Web Interface

Launch the interactive web interface:

```bash
autograder-gen-web
```

## Building from Source

For development instructions, building from source, and running Python source files directly, see [BUILD.md](BUILD.md).

## Authors

- **Alan Guedes** – [@alanlivio](https://github.com/alanlivio): maintainer
- **Giorgio Werberich Scur** – [@giorgioscur](https://github.com/giorgioscur): intial contributions

## License

Contributions are welcome and will be credited. This project is licensed under the [MIT License](LICENSE).  
The University of Reading retains rights of original contributions.
