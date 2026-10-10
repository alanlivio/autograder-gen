from autograder_gen.grader_utils import (
    compare_outputs,
    normalize_output,
    remove_package_line,
)


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
    from autograder_gen.grader_utils import JAVA_RUNNER_CODE

    assert "public class JavaRunner" in JAVA_RUNNER_CODE
    assert "convertArg" in JAVA_RUNNER_CODE


def test_call_java_function_execution(tmp_path):
    from autograder_gen.grader_utils import call_java_function

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
    from autograder_gen.grader_utils import call_java_function

    java_file = tmp_path / "Solution.java"
    java_file.write_text(
        "public class Solution {\n"
        "    public int[] doubleElements(int[] arr) {\n"
        "        int[] res = new int[arr.length];\n"
        "        for (int i = 0; i < arr.length; i++) res[i] = arr[i] * 2;\n"
        "        return res;\n"
        "    }\n"
        "    public static String greet(String name) {\n"
        "        return \"Hello, \" + name + \"!\";\n"
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


def test_javarunner_compilation_failure_logged_and_hidden_from_student(
    tmp_path, capsys, caplog
):
    import logging
    import pytest
    from autograder_gen.grader_utils import call_java_function

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


def test_javarunner_execution_failure_logged_and_hidden_from_student(
    tmp_path, capsys, caplog
):
    import logging
    import pytest
    import subprocess
    from autograder_gen.grader_utils import call_java_function

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
        "        System.err.println(\"[JAVARUNNER_ERROR] Internal fatal crash\");\n"
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

