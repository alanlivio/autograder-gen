try:
    from run_shared import (
        normalize_output,
        compare_outputs,
        STUDENT_ID_FALLBACK,
        get_student_id,
        eval_expected_output_script,
        resolve_target,
        apply_wrong_location_deduction,
        StudentMessageStr,
        StudentMessage,
        format_function_arg,
        format_function_call,
    )
except ImportError:
    from autograder_gen.run_shared import (
        normalize_output,
        compare_outputs,
        STUDENT_ID_FALLBACK,
        get_student_id,
        eval_expected_output_script,
        resolve_target,
        apply_wrong_location_deduction,
        StudentMessageStr,
        StudentMessage,
        format_function_arg,
        format_function_call,
    )

try:
    from run_java import (
        remove_package_line,
        JAVA_RUNNER_CODE,
        ensure_java_runner,
        call_java_function,
    )
except ImportError:
    try:
        from autograder_gen.run_java import (
            remove_package_line,
            JAVA_RUNNER_CODE,
            ensure_java_runner,
            call_java_function,
        )
    except ImportError:
        pass

try:
    from run_python import (
        call_function_with_timeout,
        call_function_output_with_timeout,
        import_function_from_file,
        check_function_signature,
    )
except ImportError:
    try:
        from autograder_gen.run_python import (
            call_function_with_timeout,
            call_function_output_with_timeout,
            import_function_from_file,
            check_function_signature,
        )
    except ImportError:
        pass

__all__ = [
    "normalize_output",
    "compare_outputs",
    "STUDENT_ID_FALLBACK",
    "get_student_id",
    "eval_expected_output_script",
    "resolve_target",
    "apply_wrong_location_deduction",
    "StudentMessageStr",
    "StudentMessage",
    "remove_package_line",
    "JAVA_RUNNER_CODE",
    "ensure_java_runner",
    "call_java_function",
    "call_function_with_timeout",
    "call_function_output_with_timeout",
    "import_function_from_file",
    "check_function_signature",
    "format_function_arg",
    "format_function_call",
]
