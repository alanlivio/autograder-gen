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
usage: autograder-gen [-h] [--version] [--config CONFIG |
                      --batch DIR_OR_CONFIG [DIR_OR_CONFIG ...]]
                      [--description] [--run-submission DIR_OR_ZIP]
                      [--run-stub-submissions] [--verbose]

Generate Gradescope autograder script from YAML configuration. Generated files
will be at the same folder as the config (autograder.zip, stub submissions for
testing such as stub_correct_answer.zip, stub_wrong_answer.zip, and optionally
description.docx and description.md when --description is specified).

options:
  -h, --help            show this help message and exit
  --version             show program's version number and exit
  --config, -c CONFIG   Path to YAML configuration file
  --batch, -b DIR_OR_CONFIG [DIR_OR_CONFIG ...]
                        One or more directories to search or config files to
                        batch process
  --description         Generate description.docx and description.md for the
                        assessment
  --run-submission, -r DIR_OR_ZIP
                        Use submission directory or zip file relative to
                        config to be run (can be specified multiple times)
  --run-stub-submissions
                        Run autograder for generated stub submissions
                        (stub_correct_answer.zip, stub_wrong_answer.zip,
                        stub_compiler_error.zip,
                        stub_correct_answer_wrong_location.zip)
  --verbose, -v         Print full autograder execution logs instead of only
                        paths to log files
```

### Examples

Generate an autograder package:

```bash
autograder-gen --config config.yaml
```

Generate assessment description (`description.docx` and `description.md`):

```bash
autograder-gen --config config.yaml --description
```

Run student submission against an autograder configuration:

```bash
autograder-gen --config config.yaml --run-submission submission.zip
```

Run autograder against generated stub submissions:

```bash
autograder-gen --config config.yaml --run-stub-submissions
```

## Batch Processing

Use `autograder-gen --batch` to process multiple configuration files or directories at once. When passing a directory, each subfolder should be a config folder containing a `config.yaml` (or `config.yml`):

Batch generate autograders:

```bash
autograder-gen --batch path/to/assignments/
```

Batch run stub submissions:

```bash
autograder-gen --batch path/to/assignments/ --run-stub-submissions
```

Batch run student submission:

```bash
autograder-gen --batch path/to/assignments/ --run-submission submission.zip
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
