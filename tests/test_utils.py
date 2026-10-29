import pytest
from autograder_gen.utils_submission import compare_outputs, normalize_output
from autograder_gen.utils_java import remove_package_line


def test_normalize_function():
    assert normalize_output("hello  \r\nworld   \r\n") == "hello\nworld"
    assert normalize_output("  \n  test  \t  \n \n ") == "  test"
    assert normalize_output("hello\n\nworld") == "hello\n\nworld"
    assert normalize_output("hello\n   \nworld") == "hello\n\nworld"
    assert normalize_output("\n\nhello\n\nworld\n\n") == "hello\n\nworld"
    assert normalize_output("hello\nworld   ") == "hello\nworld"
    assert normalize_output(None) == ""
    assert normalize_output("") == ""


def test_normalize_strips_leading_and_trailing_empty_lines():
    assert normalize_output("\nhello\nworld") == "hello\nworld"
    assert normalize_output("\n\n\nhello\nworld") == "hello\nworld"
    assert normalize_output("   \n \t \nhello\nworld") == "hello\nworld"
    assert normalize_output("hello\nworld\n") == "hello\nworld"
    assert normalize_output("hello\nworld\n\n\n") == "hello\nworld"
    assert normalize_output("hello\nworld\n   \n \t ") == "hello\nworld"
    assert normalize_output("\n\nhello\nworld\n\n") == "hello\nworld"


def test_normalize_removes_trailing_characters_on_last_line():
    assert normalize_output("hello\nworld   ") == "hello\nworld"
    assert normalize_output("hello\nworld\t  ") == "hello\nworld"
    assert normalize_output("single line   ") == "single line"
    assert normalize_output("single line \t \t ") == "single line"


def test_normalize_preserves_internal_empty_lines_and_indentation():
    assert normalize_output("first\n\nsecond") == "first\n\nsecond"
    assert normalize_output("first\n\n\nsecond") == "first\n\n\nsecond"
    assert normalize_output("first\n   \nsecond") == "first\n\nsecond"
    assert normalize_output("  def foo():\n      return 42") == "  def foo():\n      return 42"
    assert (
        normalize_output("\n\n  def foo():\n\n      return 42\n\n")
        == "  def foo():\n\n      return 42"
    )


def test_normalize_whitespace_only_strings():
    assert normalize_output("   ") == ""
    assert normalize_output("\n\n\n") == ""
    assert normalize_output("  \n \t \n  ") == ""


def test_remove_package_line_standard(tmp_path):
    f = tmp_path / "Solution.java"
    f.write_text("package coursework1;\npublic class Solution {\n}\n", encoding="utf-8")
    remove_package_line(f)
    assert f.read_text(encoding="utf-8") == "public class Solution {\n}\n"


def test_remove_package_line_with_comment_and_spaces(tmp_path):
    f = tmp_path / "Solution.java"
    f.write_text(
        "// student code\n  package   my.pkg.name ; // comment\npublic class Solution {}\n",
        encoding="utf-8",
    )
    remove_package_line(f)
    assert f.read_text(encoding="utf-8") == "// student code\npublic class Solution {}\n"


def test_remove_package_line_no_package(tmp_path):
    f = tmp_path / "Solution.java"
    content = "public class Solution {\n    // package test\n}\n"
    f.write_text(content, encoding="utf-8")
    remove_package_line(f)
    assert f.read_text(encoding="utf-8") == content


def test_remove_package_line_nonexistent(tmp_path):
    f = tmp_path / "Nonexistent.java"
    remove_package_line(f)


def test_compare_outputs_exact_match():
    assert compare_outputs("hello", "hello") is True
    assert compare_outputs("42", "42") is True
    assert compare_outputs("3.14", "3.14") is True


def test_compare_outputs_float_tolerance_when_not_strict():
    assert compare_outputs("4341.403447", "4341.40345", strict_float=False) is True
    assert compare_outputs("0.523598", "0.52360", strict_float=False) is True
    assert compare_outputs("0.0", "0.00000", strict_float=False) is True
    assert compare_outputs("10.00001", "10.0", strict_float=False) is True
    assert compare_outputs("10.5", "10.0", strict_float=False) is False


def test_compare_outputs_float_requires_exact_when_strict():
    assert compare_outputs("4341.403447", "4341.40345", strict_float=True) is False
    assert compare_outputs("3.14159", "3.14159", strict_float=True) is True
    assert compare_outputs("0.0", "0.0", strict_float=True) is True


def test_compare_outputs_non_numeric_fallback():
    assert compare_outputs("abc", "abd", strict_float=False) is False
    assert compare_outputs("result: 42.0", "result: 42.00", strict_float=False) is False


def test_java_runner_code_defined():
    from autograder_gen.utils_java import JAVA_RUNNER_CODE

    assert "public class JavaRunner" in JAVA_RUNNER_CODE
    assert "convertArg" in JAVA_RUNNER_CODE


def test_call_java_function_execution(tmp_path):
    from autograder_gen.utils_java import call_java_function

    java_file = tmp_path / "Calculator.java"
    java_file.write_text(
        "public class Calculator {\n"
        "    public static int add(int a, int b) {\n"
        "        return a + b;\n"
        "    }\n"
        "}\n",
        encoding="utf-8",
    )
    result = call_java_function(
        file_path=java_file,
        function_name="add",
        args=[2, 3],
        timeout_seconds=10,
        source_dir=tmp_path,
    )
    assert result.strip() == "5"


def test_call_java_function_arrays_and_objects(tmp_path):
    from autograder_gen.utils_java import call_java_function

    java_file = tmp_path / "Solution.java"
    java_file.write_text(
        "public class Solution {\n"
        "    public int[] doubleElements(int[] arr) {\n"
        "        int[] res = new int[arr.length];\n"
        "        for (int i = 0; i < arr.length; i++) res[i] = arr[i] * 2;\n"
        "        return res;\n"
        "    }\n"
        "    public static String greet(String name) {\n"
        '        return "Hello, " + name + "!";\n'
        "    }\n"
        "    public static int[][] getMatrix() {\n"
        "        return new int[][]{{1, 2}, {3, 4}};\n"
        "    }\n"
        "}\n",
        encoding="utf-8",
    )
    res_arr = call_java_function(
        file_path=java_file,
        function_name="doubleElements",
        args=["{1, 2, 3}"],
        timeout_seconds=10,
        source_dir=tmp_path,
    )
    assert res_arr.strip() == "[2, 4, 6]"

    res_str = call_java_function(
        file_path=java_file,
        function_name="greet",
        args=['"Alice"'],
        timeout_seconds=10,
        source_dir=tmp_path,
    )
    assert res_str.strip() == "Hello, Alice!"

    res_matrix = call_java_function(
        file_path=java_file,
        function_name="getMatrix",
        args=[],
        timeout_seconds=10,
        source_dir=tmp_path,
    )
    assert res_matrix.strip() == "[[1, 2], [3, 4]]"


def test_javarunner_compilation_failure_logged_and_hidden_from_student(tmp_path, capsys, caplog):
    import logging
    import pytest
    from autograder_gen.utils_java import call_java_function

    java_file = tmp_path / "Solution.java"
    java_file.write_text(
        "public class Solution {\n"
        "    public static int add(int a, int b) {\n"
        "        return a + b;\n"
        "    }\n"
        "}\n",
        encoding="utf-8",
    )
    broken_runner = tmp_path / "JavaRunner.java"
    broken_runner.write_text("invalid syntax error in JavaRunner", encoding="utf-8")

    with caplog.at_level(logging.ERROR):
        with pytest.raises(RuntimeError) as exc_info:
            call_java_function(
                file_path=java_file,
                function_name="add",
                args=[1, 2],
                timeout_seconds=10,
                source_dir=tmp_path,
            )

    captured = capsys.readouterr()
    assert "syntax error" not in captured.out
    assert "JavaRunner.java" not in captured.out
    assert "syntax error" not in str(exc_info.value)
    assert "JavaRunner.java" not in str(exc_info.value)

    error_logs = [record for record in caplog.records if record.levelno == logging.ERROR]
    assert len(error_logs) > 0
    assert any("JavaRunner" in record.message for record in error_logs)


def test_javarunner_execution_failure_logged_and_hidden_from_student(tmp_path, capsys, caplog):
    import logging
    import pytest
    import subprocess
    from autograder_gen.utils_java import call_java_function

    java_file = tmp_path / "Solution.java"
    java_file.write_text(
        "public class Solution {\n"
        "    public static int add(int a, int b) {\n"
        "        return a + b;\n"
        "    }\n"
        "}\n",
        encoding="utf-8",
    )
    runner_file = tmp_path / "JavaRunner.java"
    runner_file.write_text(
        "public class JavaRunner {\n"
        "    public static void main(String[] args) {\n"
        '        System.err.println("[JAVARUNNER_ERROR] Internal fatal crash");\n'
        "        System.exit(2);\n"
        "    }\n"
        "}\n",
        encoding="utf-8",
    )
    subprocess.run(["javac", str(runner_file)], cwd=tmp_path, check=True)

    with caplog.at_level(logging.ERROR):
        with pytest.raises(RuntimeError) as exc_info:
            call_java_function(
                file_path=java_file,
                function_name="add",
                args=[1, 2],
                timeout_seconds=10,
                source_dir=tmp_path,
            )

    captured = capsys.readouterr()
    assert "Internal fatal crash" not in captured.out
    assert "Internal fatal crash" not in str(exc_info.value)

    error_logs = [record for record in caplog.records if record.levelno == logging.ERROR]
    assert len(error_logs) > 0
    assert any("JavaRunner" in record.message for record in error_logs)


def test_modular_utils_submission_utilities(tmp_path):
    from autograder_gen.utils_submission import (
        resolve_target,
        apply_wrong_location_deduction,
        eval_expected_output_script,
    )

    # Test eval_expected_output_script
    out = eval_expected_output_script("print(f'Hello {STUDENT_ID}')", student_id="9999")
    assert out.strip() == "Hello 9999"

    # Test resolve_target
    sub_dir = tmp_path / "subdir"
    sub_dir.mkdir()
    target = sub_dir / "mysolution.py"
    target.write_text("x = 1\n", encoding="utf-8")

    wrong_set = set()
    found = resolve_target(tmp_path, "mysolution.py", strict_file_location=False, wrong_location_files=wrong_set)
    assert found == target
    assert "mysolution.py" in wrong_set

    # Test apply_wrong_location_deduction
    awarded = apply_wrong_location_deduction("mysolution.py", total_mark=10.0, deduction_rate=0.2, wrong_location_files=wrong_set)
    assert awarded == 8.0


def test_modular_utils_python_utilities(tmp_path):
    from autograder_gen.utils_python import (
        import_function_from_file,
        call_function_with_timeout,
        check_function_signature,
    )

    py_file = tmp_path / "my_module.py"
    py_file.write_text(
        "def compute(a: int, b: int = 10) -> int:\n"
        "    return a + b\n\n"
        "def slow_func():\n"
        "    import time\n"
        "    time.sleep(1)\n",
        encoding="utf-8",
    )

    func = import_function_from_file(py_file, "compute")
    assert callable(func)
    assert func(2, 3) == 5

    # Test timeout
    slow = import_function_from_file(py_file, "slow_func")
    with pytest.raises(TimeoutError):
        call_function_with_timeout(slow, [], {}, timeout_seconds=0.05)

    # Test signature check success
    check_function_signature(func, "compute", expected_parameters="a: int, b: int = 10", expected_return_type="int")

    # Test signature check failure parameter count
    with pytest.raises(AssertionError) as exc_param:
        check_function_signature(func, "compute", expected_parameters="a, b, c")
    assert "expected 3" in str(exc_param.value)

    # Test signature check failure return type
    with pytest.raises(AssertionError) as exc_ret:
        check_function_signature(func, "compute", expected_parameters="a: int, b: int = 10", expected_return_type="str")
    assert "expected 'str'" in str(exc_ret.value)


def test_format_function_call_and_student_messages():
    from autograder_gen.utils_submission import (
        StudentMessage,
        format_function_call,
        format_function_arg,
    )

    assert StudentMessage.COMPARING_OUTPUT == "## Comparing output"
    assert StudentMessage.COMPARING_RETURN == "## Comparing return"
    assert StudentMessage.FUNCTION_CALL == "### Function call:"
    assert StudentMessage.EXPECTED_RETURN == "### Expected return:"
    assert StudentMessage.EXPECTED_OUTPUT == "### Expected output:"
    assert StudentMessage.ACTUAL_RETURN == "### Actual return:"
    assert StudentMessage.ACTUAL_OUTPUT == "### Actual output:"
    assert (
        StudentMessage.CORRECT_ANSWER_FUNCTION_RETURN.format(function_name="calc")
        == "[CORRECT_ANSWER] Return value matches expected for function 'calc'."
    )
    assert (
        StudentMessage.WRONG_ANSWER_FUNCTION_RETURN.format(function_name="calc")
        == "[WRONG_ANSWER] Return value mismatch for function 'calc'."
    )
    assert (
        StudentMessage.CORRECT_ANSWER_FUNCTION_OUTPUT.format(function_name="display")
        == "[CORRECT_ANSWER] Output matches expected for std output of function 'display'."
    )
    assert (
        StudentMessage.WRONG_ANSWER_FUNCTION_OUTPUT.format(function_name="display")
        == "[WRONG_ANSWER] Output mismatch for std output of function 'display'."
    )

    # Primitive numbers and empty args
    assert format_function_call("display", [28]) == "display(28)"
    assert format_function_call("display", []) == "display()"
    assert format_function_call("display") == "display()"

    # Java array expressions formatted without redundant surrounding quotes
    assert (
        format_function_call("longestPlateau", ["{1, 3, 3, 3, 2, 1}"])
        == "longestPlateau({1, 3, 3, 3, 2, 1})"
    )
    assert (
        format_function_call("countPeaks", ["{{1, 2, 1}, {2, 5, 2}, {1, 2, 1}}"])
        == "countPeaks({{1, 2, 1}, {2, 5, 2}, {1, 2, 1}})"
    )
    assert (
        format_function_call(
            "average_grades", ["{{51, 83, 28}, {0, 38, 95}}", "{30, 40, 30}"]
        )
        == "average_grades({{51, 83, 28}, {0, 38, 95}}, {30, 40, 30})"
    )

    # String arguments formatted with quotes
    assert format_function_call("isPalindrome", ["radar"]) == 'isPalindrome("radar")'
    assert format_function_call("cardCompare", ["4H", "3S"]) == 'cardCompare("4H", "3S")'

    # Python keyword arguments and lists
    assert format_function_call("add", [1, 2]) == "add(1, 2)"
    assert format_function_call("filter_items", [[1, 2, 3]], {"reverse": True}) == "filter_items([1, 2, 3], reverse=True)"


def test_call_function_output_with_timeout():
    from autograder_gen.utils_python import call_function_output_with_timeout

    def printer(msg):
        print(f"Hello, {msg}!", end="")

    out = call_function_output_with_timeout(printer, ["world"], {}, timeout_seconds=5)
    assert out == "Hello, world!"


def test_signature_student_messages_and_java_signature_check(tmp_path):
    from autograder_gen.utils_submission import StudentMessage
    from autograder_gen.utils_java import check_java_function_signature

    assert StudentMessage.CHECKING_FUNCTION_SIGNATURE == "## Checking signature"
    assert (
        StudentMessage.CORRECT_FUNCTION_SIGNATURE.format(function_name="calc")
        == "[CORRECT_ANSWER] Function 'calc' signature is correct"
    )
    assert (
        StudentMessage.WRONG_FUNCTION_SIGNATURE.format(function_name="calc", reason="expected 2 parameters")
        == "[WRONG_ANSWER] Function 'calc' signature mismatch: expected 2 parameters."
    )

    java_file = tmp_path / "Solution.java"
    java_file.write_text(
        "public class Solution {\n"
        "    public static int add(int a, int b) {\n"
        "        return a + b;\n"
        "    }\n"
        "}\n",
        encoding="utf-8",
    )
    assert check_java_function_signature(
        file_path=java_file,
        function_name="add",
        source_dir=tmp_path,
        expected_parameters="int a, int b",
        expected_return_type="int",
    ) is True

    with pytest.raises(AssertionError) as exc_missing:
        check_java_function_signature(
            file_path=java_file,
            function_name="missingMethod",
            source_dir=tmp_path,
        )
    assert "[WRONG_ANSWER] Function 'missingMethod' signature mismatch:" in str(exc_missing.value)

    with pytest.raises(AssertionError) as exc_params:
        check_java_function_signature(
            file_path=java_file,
            function_name="add",
            source_dir=tmp_path,
            expected_parameters="int a, int b, int c",
        )
    assert "[WRONG_ANSWER] Function 'add' signature mismatch:" in str(exc_params.value)

    with pytest.raises(AssertionError) as exc_ret:
        check_java_function_signature(
            file_path=java_file,
            function_name="add",
            source_dir=tmp_path,
            expected_parameters="int a, int b",
            expected_return_type="String",
        )
    assert "[WRONG_ANSWER] Function 'add' signature mismatch:" in str(exc_ret.value)

    # Test assert_java_function_signature directly
    from autograder_gen.utils_java import assert_java_function_signature

    assert (
        assert_java_function_signature(
            file_path=java_file,
            function_name="add",
            source_dir=tmp_path,
            expected_parameters="int a, int b",
            expected_return_type="int",
        )
        is True
    )


def test_assert_python_function_signature():
    from autograder_gen.utils_python import (
        assert_python_function_signature,
        check_python_function_signature,
        call_python_function,
        call_python_function_output,
    )

    def sample_func(x: int, y: str = "hello") -> bool:
        print(f"printing {y}")
        return x > 0

    assert_python_function_signature(
        sample_func,
        "sample_func",
        expected_parameters="x: int, y: str = 'hello'",
        expected_return_type="bool",
    )
    check_python_function_signature(
        sample_func,
        "sample_func",
        expected_parameters="x: int, y: str = 'hello'",
        expected_return_type="bool",
    )

    # Test execution callers
    ret = call_python_function(sample_func, [5], {}, timeout_seconds=5)
    assert ret is True

    out = call_python_function_output(sample_func, [5], {}, timeout_seconds=5)
    assert "printing hello" in out


def test_comparison_assertion_helpers(tmp_path):
    from autograder_gen.utils_submission import (
        assert_file_exists,
        assert_output_matches,
        assert_function_return_matches,
        assert_function_output_matches,
    )

    dummy_file = tmp_path / "solution.py"
    dummy_file.write_text("print('hello')", encoding="utf-8")

    assert_file_exists(dummy_file, "solution.py")
    with pytest.raises(AssertionError):
        assert_file_exists(tmp_path / "missing.py", "missing.py")

    assert_output_matches("hello\n", "hello", "solution.py")
    with pytest.raises(AssertionError):
        assert_output_matches("wrong", "hello", "solution.py")

    assert_function_return_matches("42", "42", "my_func")
    with pytest.raises(AssertionError):
        assert_function_return_matches("0", "42", "my_func")

    assert_function_output_matches("result", "result", "my_func")
    with pytest.raises(AssertionError):
        assert_function_output_matches("bad", "result", "my_func")




