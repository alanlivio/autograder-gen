# autograder_gen

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

`autograder_gen` is a tool for lecturers to automatically generate assessment scripts for [Grading a Programming Assignment](https://guides.gradescope.com/hc/en-us/articles/22066635961357-Grading-a-Programming-Assignment) on Gradescope. It supports filling out an interactive web form or providing a YAML configuration, which then generates a packaged ZIP file ready to be uploaded to Gradescope. The project validates your YAML configuration, renders test scripts using Jinja2 templates, and packages everything for immediate upload to Gradescope.

## Installation

Install the package via pip:

```bash
pip install autograder_gen
```

## CLI Usage

When installed, `autograder-gen` generates Gradescope autograders directly from configuration files. Running without parameters displays usage help:

```bash
autograder-gen
```

```text
usage: autograder-gen [-h] [--config CONFIG] [--descriptions]
                      [--run-submission RUN_SUBMISSIONS]
                      [--run-stub-submissions [RUN_STUBS_SUBMISSIONS]]
                      [--verbose]

Generate Gradescope autograder script from YAML configuration. Generated files
will be at the same folder as the config (autograder.zip, stub submissions for
testing, and optionally description.docx and description.md when
--descriptions is specified).

options:
  -h, --help            show this help message and exit
  --config, -c CONFIG   Path to YAML configuration file
  --descriptions, --description
                        Generate description.docx and description.md
                        assessment descriptions
  --run-submission, -r RUN_SUBMISSIONS
                        Path or folder name of submission directory or zip
                        file to run (can be specified multiple times)
  --run-stub-submissions [RUN_STUBS_SUBMISSIONS]
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

Generate assessment descriptions (`description.docx` and `description.md`):

```bash
autograder-gen --config config.yaml --descriptions
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

Use `autograder-gen-batch` to process multiple configuration files or directories at once:

```bash
# Generate autograders for all configurations in a folder
autograder-gen-batch path/to/assignments/

# Run autograders for stub submissions across all configurations
autograder-gen-batch path/to/assignments/ --run-stub-submissions
```

## Web Interface

Launch the interactive web interface:

```bash
autograder-gen-web
```

## Development and Building from Source

For development instructions, building from source, and running Python source files directly, see [BUILD.md](BUILD.md). 

## Authors

- **Alan Guedes** – [@alanlivio](https://github.com/alanlivio)  
- **Giorgio Werberich Scur** – [@giorgioscur](https://github.com/giorgioscur)

## License

Contributions are welcome and will be credited. This project is licensed under the [MIT License](LICENSE).  
The University of Reading retains rights of original contributions.
