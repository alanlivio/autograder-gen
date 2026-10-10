"""
AutograderGen package.
"""

from autograder_gen.version import __version__
from autograder_gen.config import (
    Config,
    Question,
    MarkingItem,
    DEFAULT_LANGUAGE_RUNTIMES,
    DEFAULT_RUNTIME_SUMMARY,
    DEFAULT_RUNTIME_TIP,
)
from autograder_gen.autograder_gen import (
    AutograderGen,
    Engine,
    validate_file_path,
    validate_directory_path,
    create_directory,
    get_file_extension,
    is_supported_language_file,
    sanitize_filename,
    format_error_message,
)
from autograder_gen.logger import (
    setup_logging,
    print_error,
    print_info,
    print_success,
    print_warning,
)
from autograder_gen.validator import Validator
from autograder_gen.autograder_run import AutograderRun, AutograderRunner
from autograder_gen.grader_utils import (
    StudentMessage,
    normalize_output,
    remove_package_line,
    JAVA_RUNNER_CODE,
    ensure_java_runner,
    call_java_function,
)

__all__ = [
    "__version__",
    "Config",
    "Question",
    "MarkingItem",
    "DEFAULT_LANGUAGE_RUNTIMES",
    "DEFAULT_RUNTIME_SUMMARY",
    "DEFAULT_RUNTIME_TIP",
    "AutograderGen",
    "Engine",
    "Validator",
    "AutograderRun",
    "AutograderRunner",
    "StudentMessage",
    "normalize_output",
    "remove_package_line",
    "JAVA_RUNNER_CODE",
    "ensure_java_runner",
    "call_java_function",
    "validate_file_path",
    "validate_directory_path",
    "create_directory",
    "get_file_extension",
    "is_supported_language_file",
    "sanitize_filename",
    "format_error_message",
    "setup_logging",
    "print_error",
    "print_info",
    "print_success",
    "print_warning",
]
