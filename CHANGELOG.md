# Changelog

All notable changes to this project will be documented in this file.The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.3] - NEXT

### Changed

- Support for single-line `expected_input` in YAML configurations automatically ensuring a terminating newline.
- Moved Java test execution logic (`JavaRunner`),  refactored `JavaRunner` and added unit tests
- Support for `<STUDENT_ID>` placeholder replacement in expected outputs.
- CLI flag `--schema` to output JSON schema for the YAML configuration.

## [0.1.2] - 2026-10-07

### Changed

- Replaced WTForms with Pydantic and JSONEditor in the web application interface.

## [0.1.1] - 2026-09-30

### Added

- Autograder execution framework (`AutograderRun` and `AutograderRunner`) with test log reporting.
- Support for `manual_review` marking item types.
- Support for `retrieve_student_id` and student ID discovery from submission metadata or classlist.
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
