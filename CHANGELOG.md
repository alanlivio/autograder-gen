# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-10-28

### Added

- Question-level `expected_output_script` to dynamically generate expected standard output using `input()`, `print()`, and `STUDENT_ID`. Property `excluded_student_ids` allows instructors to submit stubs at Gradescope without student ID collision.
- Standardized automated marking item types: `program_output_test`, `function_return_test`, `function_output_test`, `function_signature_test`, `gitlab_submission_test`, and `github_submission_test`.
- Runtime assertion helpers (`assert_python_function_signature`, `assert_java_function_signature`, `assert_gitlab_submission_test`, `assert_github_submission_test`, `assert_output_matches`).

### Changed

- Automatically terminate single-line `expected_input` with a newline.
- Refactored `JavaRunner` and added unit tests for primitive types, arrays, matrices, and objects.
- Split function testing templates into dedicated `function_return_test.j2` and `function_output_test.j2`, and removed redundant `_method` suffix across all subtemplates.
- Replaced `retrieve_student_id` with question-level `expected_output_script`.

## [0.1.2] - 2026-10-07

### Changed

- Replaced WTForms with Pydantic and JSONEditor in the web application interface.

## [0.1.1] - 2026-09-30

### Added

- Autograder execution framework (`AutograderRun` and `AutograderRunner`) with test log reporting.
- Support for `manual_review` marking item types.
- Support for `retrieve_student_id` to set environment variable `STUDENT_ID` from `submission_metadata.json` or `classlist.csv`.
- Support for GitLab and GitHub submission existence checks.
- Support for strict float comparisons (`strict_float`) and strict file locations (`strict_file_location`).
- CLI options `--run-solution` and `--run-stubs`.

### Changed

- Standardized configuration schema using Pydantic models.
- Allowed floating-point values for `total_mark`.
- Renamed `files_necessary` configuration property to `required_files`.

## [0.1.0] - 2026-08-11

### Added

- Initial release of `autograder-gen`.
- Generation of Gradescope autograder archives from YAML configuration.
- Support for Python and Java programming languages.
- Web application interface for building and previewing autograder configurations.
- CLI tool `autograder-gen` for autograder generation, documentation exports, and stub verification.
