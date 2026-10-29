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
        assert_file_exists,
        assert_output_matches,
        assert_function_return_matches,
        assert_function_output_matches,
        assert_gitlab_submission_test,
        assert_gitlab_submission_exists,
        assert_github_submission_test,
        assert_github_submission_exists,
        assert_git_submission_test,
        assert_git_submission_exists,
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
        assert_file_exists,
        assert_output_matches,
        assert_function_return_matches,
        assert_function_output_matches,
        assert_gitlab_submission_test,
        assert_gitlab_submission_exists,
        assert_github_submission_test,
        assert_github_submission_exists,
        assert_git_submission_test,
        assert_git_submission_exists,
    )

try:
    from run_java import (
        remove_package_line,
        JAVA_RUNNER_CODE,
        ensure_java_runner,
        call_java_function,
        assert_java_function_signature,
        check_java_function_signature,
    )
except ImportError:
    try:
        from autograder_gen.run_java import (
            remove_package_line,
            JAVA_RUNNER_CODE,
            ensure_java_runner,
            call_java_function,
            assert_java_function_signature,
            check_java_function_signature,
        )
    except ImportError:
        pass

try:
    from run_python import (
        call_function_with_timeout,
        call_function_output_with_timeout,
        call_python_function,
        call_python_function_output,
        import_function_from_file,
        assert_python_function_signature,
        check_python_function_signature,
        check_function_signature,
    )
except ImportError:
    try:
        from autograder_gen.run_python import (
            call_function_with_timeout,
            call_function_output_with_timeout,
            call_python_function,
            call_python_function_output,
            import_function_from_file,
            assert_python_function_signature,
            check_python_function_signature,
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
    "assert_java_function_signature",
    "check_java_function_signature",
    "call_function_with_timeout",
    "call_function_output_with_timeout",
    "call_python_function",
    "call_python_function_output",
    "import_function_from_file",
    "assert_python_function_signature",
    "check_python_function_signature",
    "check_function_signature",
    "format_function_arg",
    "format_function_call",
    "assert_file_exists",
    "assert_output_matches",
    "assert_function_return_matches",
    "assert_function_output_matches",
    "assert_gitlab_submission_test",
    "assert_gitlab_submission_exists",
    "assert_github_submission_test",
    "assert_github_submission_exists",
    "assert_git_submission_test",
    "assert_git_submission_exists",
]

