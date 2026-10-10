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
