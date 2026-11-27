import io
import json
import logging
import shutil
import time
import typing
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml
from docx import Document
from pydantic import ValidationError

import autograder_gen as ag
from autograder_gen.logger import (
    print_error,
    print_info,
    print_success,
    print_warning,
    setup_logging,
)
from autograder_gen.utils_description import generate_description_docx_buffer
from autograder_gen.utils_java import (
    assert_java_function_signature,
    call_java_function,
    generate_java_skeleton,
    infer_java_type,
)
from autograder_gen.utils_matlab import (
    _check_matlab_syntax,
    assert_matlab_function_signature,
    call_matlab_function,
    escape_matlab_str,
    format_matlab_arg,
    generate_matlab_skeleton,
    get_matlab_literal_str,
    get_octave_executable,
)
from autograder_gen.utils_python import (
    assert_python_function_signature,
    call_function_output_with_timeout,
    call_function_with_timeout,
    generate_python_skeleton,
    import_function_from_file,
)
from autograder_gen.utils_readme import generate_description_md, generate_readme_md
from autograder_gen.utils_submission import (
    STUDENT_ID_FALLBACK,
    StudentMessage,
    apply_wrong_location_deduction,
    assert_github_submission_test,
    assert_gitlab_submission_test,
    format_function_arg,
    get_student_id,
    resolve_target,
)
from autograder_gen.validator import Validator
from autograder_gen.version import __version__


def test_validator_type_hints_and_regression_bugs(tmp_path: Path):
    hints = typing.get_type_hints(Validator._validate_program_output_test_warnings)
    assert "question" in hints

    validator = Validator()
    bad_file = tmp_path / "list.yaml"
    bad_file.write_text("- a\n- b\n", encoding="utf-8")
    assert validator.validate_from_file(str(bad_file)) is False
    assert len(validator.get_errors()) == 1

    assert validator.validate_from_file(str(tmp_path / "missing.yaml")) is False
    assert len(validator.get_errors()) == 1
    assert "Error reading file" in validator.get_errors()[0]

    malformed = {
        "language": "python",
        "questions": [
            "not_a_dict",
            {"name": "Q1", "marking_items": [{"total_mark": "bad"}, "not_a_dict"]},
            {"name": "Q2", "manual_review": True, "total_mark": 5},
            {"name": "Q3", "manual_review": True, "total_mark": "nan_str"},
        ],
    }
    report = Validator.lint_config(malformed)
    assert report["valid"] is False
    assert report["total_marks"] == 5.0
    assert report["issues_summary"]["errors"] > 0

    report_with_warnings = Validator.lint_config(
        {
            "version": __version__,
            "language": "python",
            "required_submission_files": ["solution.py"],
            "questions": [
                {
                    "name": "Q1",
                    "marking_items": [
                        {
                            "target_file": "solution.py",
                            "total_mark": 0,
                        }
                    ],
                }
            ],
        }
    )
    assert report_with_warnings["valid"] is True
    assert report_with_warnings["issues_summary"]["warnings"] >= 1
    assert any(i["level"] == "warning" for i in report_with_warnings["issues"])

    manual_shorthand = {
        "version": __version__,
        "language": "python",
        "required_submission_files": ["report.pdf"],
        "questions": [
            {
                "name": "Report",
                "manual_review": True,
                "total_mark": 20,
                "target_file": "report.pdf",
            }
        ],
    }
    val_manual = Validator()
    assert val_manual.validate_json(manual_shorthand) is True
    assert not any("Total marks for all questions is 0" in w for w in val_manual.get_warnings())

    cfg = ag.Config.model_validate(manual_shorthand)
    assert validator._config_to_dict(cfg)["language"] == "python"
    assert validator._config_to_dict({"a": 1}) == {"a": 1}

    validator._validate_program_output_test_warnings(
        {
            "name": "DefaultTypeItem",
            "expected_output": "x",
            "expected_output_script": "print('x')",
        }
    )
    assert any("mutually exclusive" in e for e in validator.get_errors())

    validator.errors.clear()
    validator._validate_function_test(
        {"type": "function_return_test", "name": "BadTC", "test_cases": ["not_a_dict"]}
    )
    assert any("missing function_name" in e for e in validator.get_errors())
    assert any("invalid test_case structure" in e for e in validator.get_errors())


def test_validator_unexpected_exception(monkeypatch):
    def _boom(_data):
        raise RuntimeError("boom")

    monkeypatch.setattr(ag.Config, "model_validate", _boom)
    v = Validator()
    assert v.validate_json({}) is False
    assert any("Unexpected error: boom" in e for e in v.get_errors())


def test_logger_helpers_and_no_duplicate_handlers(capsys):
    root_logger = logging.getLogger()
    setup_logging(verbose=False)
    count_first = len(
        [h for h in root_logger.handlers if getattr(h, "_autograder_gen_handler", False)]
    )
    setup_logging(verbose=True)
    count_second = len(
        [h for h in root_logger.handlers if getattr(h, "_autograder_gen_handler", False)]
    )
    assert count_first == 1
    assert count_second == 1

    print_success("ok")
    print_info("info")
    print_warning("warn")
    print_error("err")
    captured = capsys.readouterr()
    assert "[OK] ok" in captured.out
    assert "[INFO] info" in captured.out
    assert "[WARNING] warn" in captured.out
    assert "[ERROR] err" in captured.err


def test_config_uncovered_branches(tmp_path: Path, monkeypatch):
    with pytest.raises(ValidationError, match="visibility must be one of"):
        ag.MarkingItem(
            target_file="solution.py",
            total_mark=5,
            type="program_output_test",
            visibility="invalid_vis",
        )

    with pytest.raises(ValidationError):
        ag.Config.model_validate(
            {
                "version": __version__,
                "language": "python",
                "excluded_student_ids": {"bad": "dict"},
                "required_submission_files": ["solution.py"],
                "questions": [
                    {
                        "name": "Q1",
                        "marking_items": [
                            {
                                "target_file": "solution.py",
                                "total_mark": 5,
                                "type": "program_output_test",
                            }
                        ],
                    }
                ],
            }
        )

    invalid_schema_yaml = tmp_path / "invalid_schema.yaml"
    invalid_schema_yaml.write_text("language: python\nquestions: []\n", encoding="utf-8")
    with pytest.raises(ValidationError):
        ag.Config.parse(invalid_schema_yaml)

    upper_yaml = tmp_path / "UPPER.YAML"
    upper_yaml.write_text(
        yaml.dump(
            {
                "version": __version__,
                "language": "python",
                "required_submission_files": ["solution.py"],
                "questions": [
                    {
                        "name": "Q1",
                        "marking_items": [
                            {
                                "target_file": "solution.py",
                                "total_mark": 5,
                                "type": "program_output_test",
                            }
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    parsed_upper = ag.Config.parse(upper_yaml)
    assert parsed_upper.total_score == 5

    monkeypatch.setattr(Path, "exists", lambda _self: False)
    for lang in ("python", "java", "matlab"):
        fallback = ag.Config.get_example_config_yaml(lang)
        assert f"language: {lang}" in fallback


def test_description_docx_md_and_readme_all_item_types():
    config_dict = {
        "version": __version__,
        "language": "python",
        "required_submission_files": ["solution.py", "report.pdf"],
        "required_autograder_files": ["data.txt"],
        "questions": [
            {
                "name": "Comprehensive Question",
                "description": "Implement all required functions and scripts.",
                "expected_output_script": "print(f'QScript {STUDENT_ID}')",
                "marking_items": [
                    {
                        "name": "Program Output Static",
                        "target_file": "solution.py",
                        "total_mark": 5,
                        "type": "program_output_test",
                        "expected_input": "10",
                        "expected_output": "100",
                    },
                    {
                        "name": "Program Output Script",
                        "target_file": "solution.py",
                        "total_mark": 5,
                        "type": "program_output_test",
                        "expected_input": "2",
                    },
                    {
                        "name": "Signature Check",
                        "target_file": "solution.py",
                        "total_mark": 3,
                        "type": "function_signature_test",
                        "function_name": "add",
                        "expected_parameters": "a: int, b: int",
                        "expected_return_type": "int",
                    },
                    {
                        "name": "Return Check",
                        "target_file": "solution.py",
                        "total_mark": 4,
                        "type": "function_return_test",
                        "function_name": "add",
                        "test_cases": [{"args": [1, 2], "expected": "3"}],
                    },
                    {
                        "name": "Output Check",
                        "target_file": "solution.py",
                        "total_mark": 4,
                        "type": "function_output_test",
                        "function_name": "greet",
                        "test_cases": [{"args": ["Ada"], "expected": "Hi Ada"}],
                    },
                    {
                        "name": "Git Check",
                        "total_mark": 2,
                        "type": "git_submission_test",
                    },
                    {
                        "name": "GitLab Check",
                        "total_mark": 2,
                        "type": "gitlab_submission_test",
                    },
                    {
                        "name": "GitHub Check",
                        "total_mark": 2,
                        "type": "github_submission_test",
                    },
                    {
                        "name": "Report Review",
                        "target_file": "report.pdf",
                        "total_mark": 5,
                        "type": "manual_review",
                    },
                    {
                        "name": "Oral Review",
                        "total_mark": 3,
                        "type": "manual_review",
                    },
                ],
            }
        ],
    }
    cfg = ag.Config.model_validate(config_dict)

    docx_buf = generate_description_docx_buffer(cfg)
    doc = Document(docx_buf)
    full_text = "\n".join(p.text for p in doc.paragraphs)
    assert "Implement all required functions and scripts." in full_text
    assert f"QScript {STUDENT_ID_FALLBACK}" in full_text
    assert "parameters (a: int, b: int), return type int" in full_text
    assert "must return expected values" in full_text
    assert "must print expected standard output" in full_text
    assert "Git repository (GitLab or GitHub)" in full_text
    assert "GitLab repository" in full_text
    assert "GitHub repository" in full_text
    assert "Qualitative evaluation of 'report.pdf'" in full_text
    assert "Qualitative evaluation (manual review by instructor)." in full_text

    md_text = generate_description_md(cfg)
    assert "Implement all required functions and scripts." in md_text
    assert f"QScript {STUDENT_ID_FALLBACK}" in md_text
    assert "parameters `a: int, b: int`, return type `int`" in md_text
    assert "GitLab repository" in md_text
    assert "GitHub repository" in md_text
    assert "Qualitative evaluation of `report.pdf`" in md_text

    readme_text = generate_readme_md(cfg)
    assert "GitHub repository" in readme_text
    assert "GitLab repository" in readme_text
    assert "Git repository (GitLab or GitHub)" in readme_text


def test_utils_submission_edge_cases(tmp_path: Path):
    corrupt_meta = tmp_path / "submission_metadata.json"
    corrupt_meta.write_text("{not valid json", encoding="utf-8")
    assert get_student_id(autograder_root=tmp_path) == str(STUDENT_ID_FALLBACK)

    direct = tmp_path / "direct.py"
    direct.write_text("x = 1\n", encoding="utf-8")
    wrong_set = set()
    assert resolve_target(tmp_path, "direct.py", False, wrong_set) == direct
    assert "direct.py" not in wrong_set

    dir_same_name = tmp_path / "nested" / "app.py"
    dir_same_name.mkdir(parents=True)
    assert resolve_target(tmp_path, "app.py", False, wrong_set) == tmp_path / "app.py"

    assert apply_wrong_location_deduction("other.py", 10.0, 0.5, wrong_set) is None

    class _DummyTest:
        _testMethodName = "test_sample"

        def test_sample(self):
            pass

    wrong_set.add("moved.py")
    inst = _DummyTest()
    awarded = apply_wrong_location_deduction("moved.py", 10.0, 0.25, wrong_set, inst)
    assert awarded == 7.5
    assert getattr(_DummyTest.test_sample, "__score__") == 7.5

    assert format_function_arg("'abc'") == '"abc"'
    assert format_function_arg('"') == '"""'
    assert format_function_arg((1, 2)) == "(1, 2)"
    assert format_function_arg({"k": 1}) == '{"k": 1}'
    assert format_function_arg(None) == "None"

    assert "foo.py" in StudentMessage.WRONG_FILE.format(target_file="foo.py")

    empty_dir = tmp_path / "isolated" / "empty_git"
    empty_dir.mkdir(parents=True)
    with pytest.raises(AssertionError):
        assert_gitlab_submission_test(empty_dir, autograder_root=empty_dir)
    with pytest.raises(AssertionError):
        assert_github_submission_test(empty_dir, autograder_root=empty_dir)


def test_python_timeout_does_not_hang_and_signature_edge_cases(tmp_path: Path):
    import threading

    stop_return = threading.Event()
    stop_print = threading.Event()

    def slow_return():
        stop_return.wait(5)
        return 1

    def slow_print():
        stop_print.wait(5)

    start = time.monotonic()
    with pytest.raises(TimeoutError):
        call_function_with_timeout(slow_return, [], {}, timeout_seconds=0.05)
    assert time.monotonic() - start < 1.0
    stop_return.set()

    start = time.monotonic()
    with pytest.raises(TimeoutError):
        call_function_output_with_timeout(slow_print, [], {}, timeout_seconds=0.05)
    assert time.monotonic() - start < 1.0
    stop_print.set()

    failing_mod = tmp_path / "boom.py"
    failing_mod.write_text("raise RuntimeError('import failure')\n", encoding="utf-8")
    with pytest.raises(ImportError, match="Failed to import"):
        import_function_from_file(failing_mod, "fn")

    def generic_fn(
        mapping: dict[str, int], items: list[int] = [1, 2], flag: bool = True
    ) -> dict[str, int]:
        return mapping

    assert_python_function_signature(
        generic_fn,
        "generic_fn",
        expected_parameters="mapping: dict[str, int], items: list[int] = [1, 2], flag: bool = True",
        expected_return_type="dict[str, int]",
    )

    def typed_fn(a: str, b: float = 1.0, c=None):
        return a

    with pytest.raises(AssertionError, match="has type"):
        assert_python_function_signature(typed_fn, "typed_fn", expected_parameters="a: int, b, c")

    assert_python_function_signature(
        typed_fn, "typed_fn", expected_parameters="a: str, b: float = 1, c = None"
    )

    with pytest.raises(AssertionError, match="has default"):
        assert_python_function_signature(
            typed_fn, "typed_fn", expected_parameters="a: str, b: float = 2, c = None"
        )

    def bad_conv(a="abc"):
        return a

    with pytest.raises(AssertionError, match="has default"):
        assert_python_function_signature(bad_conv, "bad_conv", expected_parameters="a = 5")

    assert_python_function_signature(bad_conv, "bad_conv", expected_parameters="a = abc")
    with pytest.raises(AssertionError, match="has default"):
        assert_python_function_signature(bad_conv, "bad_conv", expected_parameters="a = xyz")


def test_python_skeleton_edge_cases():
    config_dict = {
        "version": __version__,
        "language": "python",
        "required_submission_files": ["solution.py"],
        "questions": [
            {
                "name": "Q1",
                "expected_output_script": "print('from_question_script')",
                "marking_items": [
                    {
                        "target_file": "solution.py",
                        "total_mark": 5,
                        "type": "function_signature_test",
                        "function_name": "no_params_typed",
                        "expected_return_type": "int",
                    },
                    {
                        "target_file": "solution.py",
                        "total_mark": 5,
                        "type": "function_return_test",
                        "function_name": "with_kwargs",
                        "expected_parameters": "a, b=1",
                        "test_cases": [
                            {"args": [2], "kwargs": {"b": 3}, "expected": "None"},
                            {"args": [], "kwargs": {}, "expected": "0"},
                        ],
                    },
                    {
                        "target_file": "solution.py",
                        "total_mark": 5,
                        "type": "function_return_test",
                        "function_name": "no_args_fn",
                        "test_cases": [
                            {"args": [], "kwargs": {"x": 1}, "expected": "42"},
                        ],
                    },
                    {
                        "target_file": "solution.py",
                        "total_mark": 5,
                        "type": "function_output_test",
                        "function_name": "printer",
                        "test_cases": [{"args": ["hi"], "expected": "hi"}],
                    },
                    {
                        "target_file": "solution.py",
                        "total_mark": 5,
                        "type": "program_output_test",
                        "expected_input": "a",
                        "expected_output": "override_static",
                    },
                ],
            }
        ],
    }
    cfg = ag.Config.model_validate(config_dict)
    correct_src = generate_python_skeleton(cfg, "solution.py", correct=True)
    assert "def no_params_typed(*args, **kwargs) -> int:" in correct_src
    assert "b == 3" in correct_src
    assert "not args and kwargs == {'x': 1}" in correct_src
    assert "override_static" in correct_src
    assert "from_question_script" not in correct_src

    wrong_src = generate_python_skeleton(cfg, "solution.py", correct=False)
    assert "return 'wrong_answer'" in wrong_src
    assert "print('wrong_answer', end='')" in wrong_src


def test_template_escaping_and_duplicate_item_names(tmp_path: Path):
    config_dict = {
        "version": __version__,
        "language": "python",
        "required_submission_files": ["solution.py"],
        "questions": [
            {
                "name": 'Question {1} "Quotes"',
                "marking_items": [
                    {
                        "name": "Don't fail",
                        "target_file": "solution.py",
                        "total_mark": 5,
                        "type": "program_output_test",
                        "expected_input": 'line1 "quoted"\nline2\\path',
                        "expected_output": 'say "hello" and """triple"""\nC:\\dir\\file',
                    },
                    {
                        "name": "Don't fail",
                        "target_file": "solution.py",
                        "total_mark": 5,
                        "type": "program_output_test",
                        "expected_input": "second",
                        "expected_output": "second_out",
                    },
                ],
            }
        ],
    }
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(yaml.dump(config_dict), encoding="utf-8")

    runner = ag.AutograderRun(cfg_path, save_log=False)
    res = runner.run_autograder_for_generated_submissions()
    tests = res["correct_answer"]["tests"]
    assert len(tests) == 2
    assert sum(t["score"] for t in tests) == 10


def test_autograder_gen_uncovered_branches(tmp_path: Path):
    extra_dir = tmp_path / "assets"
    extra_dir.mkdir()
    (extra_dir / "helper.txt").write_text("asset", encoding="utf-8")

    config_dict = {
        "version": __version__,
        "language": "python",
        "required_submission_files": ["pkg/sub/solution.py"],
        "required_autograder_files": ["assets"],
        "questions": [
            {
                "name": "Nested",
                "marking_items": [
                    {
                        "target_file": "pkg/sub/solution.py",
                        "total_mark": 10,
                        "type": "program_output_test",
                        "expected_output": "ok",
                    }
                ],
            }
        ],
    }
    cfg = ag.Config.model_validate(config_dict)
    gen = ag.AutograderGen(cfg, config_dict, base_dir=tmp_path)

    out_dir = tmp_path / "out"
    (out_dir / "temp_autograder").mkdir(parents=True)
    zip_path = gen.generate(str(out_dir), generate_description=True)
    assert (out_dir / "description.docx").exists()

    with zipfile.ZipFile(zip_path, "r") as zf:
        assert "assets/helper.txt" in zf.namelist()

    zip_bytes = Path(zip_path).read_bytes()
    assert gen.verify_autograder_zip(zip_bytes)["valid"] is True

    fake_obj = SimpleNamespace(namelist=lambda: ["run_autograder", "setup.sh", "source/a.py"])
    ver_obj = gen.verify_autograder_zip(fake_obj)
    assert ver_obj["valid"] is True
    assert any("folder structures" in c for c in ver_obj["checks"])

    gen.temp_dir = tmp_path / "manual_temp"
    gen.temp_dir.mkdir()
    (gen.temp_dir / "run_autograder").write_text("#!/bin/bash\n", encoding="utf-8")
    assert gen.verify_autograder_zip(None)["valid"] is True

    blocker = tmp_path / "blocker_file"
    blocker.write_text("x", encoding="utf-8")
    with pytest.raises(ValueError, match="Failed to create"):
        ag.create_directory(str(blocker / "child"))


@pytest.mark.skipif(shutil.which("javac") is None, reason="javac is not installed")
def test_java_utils_coverage_and_skeleton_fixes(tmp_path: Path):
    with pytest.raises(AssertionError, match="WRONG_FILE"):
        call_java_function(tmp_path / "Missing.java", "fn", [], 5, tmp_path)

    with pytest.raises(AssertionError, match="WRONG_FILE"):
        assert_java_function_signature(tmp_path / "Missing.java", "fn", tmp_path)

    bad_java = tmp_path / "Broken.java"
    bad_java.write_text("public class Broken { void x( { } }\n", encoding="utf-8")
    with pytest.raises(AssertionError, match="COMPILATION_ERROR"):
        call_java_function(bad_java, "x", [], 5, tmp_path)
    with pytest.raises(AssertionError, match="COMPILATION_ERROR"):
        assert_java_function_signature(bad_java, "x", tmp_path)

    pkg_java = tmp_path / "PkgDemo.java"
    pkg_java.write_text(
        "package demo;\n"
        "public class PkgDemo {\n"
        '    public static int failNow() { throw new RuntimeException("kaboom"); }\n'
        "    public static String echo(String s) { return s; }\n"
        "    public static int typed(int a, String b) { return a; }\n"
        "}\n",
        encoding="utf-8",
    )
    assert (
        assert_java_function_signature(
            pkg_java,
            "typed",
            tmp_path,
            expected_parameters="a: int, b: String",
            expected_return_type="int",
            remove_package=True,
        )
        is True
    )
    with pytest.raises(AssertionError, match="parameter 2 has type"):
        assert_java_function_signature(
            pkg_java,
            "typed",
            tmp_path,
            expected_parameters="a: int, b: double",
        )
    assert call_java_function(pkg_java, "echo", ['"'], 10, tmp_path) == '"'
    with pytest.raises(RuntimeError, match="Error executing failNow"):
        call_java_function(pkg_java, "failNow", [], 10, tmp_path)

    assert infer_java_type([1.5, 2.5]) == "double[]"
    assert infer_java_type("{a, b}", desc="ArrayList") == "java.util.ArrayList<String>"
    assert infer_java_type("{a, b}") == "String[]"
    assert infer_java_type("{1, 2}", desc="list") == "java.util.ArrayList<Integer>"
    assert infer_java_type("{1.2, 2.3}", desc="list") == "java.util.ArrayList<Double>"
    assert infer_java_type("3000000000") == "long"
    assert infer_java_type("3.14") == "double"

    java_cfg_dict = {
        "version": __version__,
        "language": "java",
        "required_submission_files": ["TypesTest.java"],
        "questions": [
            {
                "name": "Java Types",
                "marking_items": [
                    {
                        "name": "Sig Only",
                        "target_file": "TypesTest.java",
                        "total_mark": 2,
                        "type": "function_signature_test",
                        "function_name": "sigOnly",
                        "expected_parameters": "int a, String b",
                        "expected_return_type": "boolean",
                    },
                    {
                        "name": "Long Test",
                        "target_file": "TypesTest.java",
                        "total_mark": 2,
                        "type": "function_return_test",
                        "function_name": "bigVal",
                        "test_cases": [{"args": [3000000000], "expected": "4000000000"}],
                    },
                    {
                        "name": "ArrayList Int",
                        "description": "Return ArrayList of integers",
                        "target_file": "TypesTest.java",
                        "total_mark": 2,
                        "type": "function_return_test",
                        "function_name": "intList",
                        "test_cases": [{"args": [[1, 2]], "expected": "[3, 4]"}],
                    },
                    {
                        "name": "ArrayList Double",
                        "target_file": "TypesTest.java",
                        "total_mark": 2,
                        "type": "function_return_test",
                        "function_name": "doubleList",
                        "test_cases": [{"args": ["{1.5, 2.5}"], "expected": "[1.5, 2.5]"}],
                    },
                    {
                        "name": "ArrayList String",
                        "target_file": "TypesTest.java",
                        "total_mark": 2,
                        "type": "function_return_test",
                        "function_name": "strList",
                        "test_cases": [{"args": [["a", "b"]], "expected": "[a, b]"}],
                    },
                    {
                        "name": "String Array",
                        "target_file": "TypesTest.java",
                        "total_mark": 2,
                        "type": "function_return_test",
                        "function_name": "strArr",
                        "test_cases": [{"args": [["x", "y"]], "expected": "[x, y]"}],
                    },
                    {
                        "name": "Matrix 2D",
                        "target_file": "TypesTest.java",
                        "total_mark": 2,
                        "type": "function_return_test",
                        "function_name": "mat",
                        "test_cases": [{"args": [[[1, 2], [3, 4]]], "expected": "[1, 2]"}],
                    },
                    {
                        "name": "Bool and Str",
                        "target_file": "TypesTest.java",
                        "total_mark": 2,
                        "type": "function_return_test",
                        "function_name": "checkFlag",
                        "test_cases": [{"args": [True, "hi", 1.5], "expected": "false"}],
                    },
                    {
                        "name": "Void Output",
                        "target_file": "TypesTest.java",
                        "total_mark": 2,
                        "type": "function_output_test",
                        "function_name": "say",
                        "test_cases": [{"args": ["world"], "expected": "hello world"}],
                    },
                    {
                        "name": "Main Script 1",
                        "target_file": "TypesTest.java",
                        "total_mark": 1,
                        "type": "program_output_test",
                        "expected_input": "in1",
                        "expected_output_script": "print(f'OUT1_{STUDENT_ID}')",
                    },
                    {
                        "name": "Main Script 2",
                        "target_file": "TypesTest.java",
                        "total_mark": 1,
                        "type": "program_output_test",
                        "expected_input": "in2",
                        "expected_output_script": "print(f'OUT2_{STUDENT_ID}')",
                    },
                ],
            }
        ],
    }
    java_cfg = ag.Config.model_validate(java_cfg_dict)
    correct_java = generate_java_skeleton(java_cfg, "TypesTest.java", correct=True)
    wrong_java = generate_java_skeleton(java_cfg, "TypesTest.java", correct=False)

    assert "3000000000L" in correct_java
    assert "4000000000L" in correct_java
    assert "public static boolean sigOnly(int a, String b)" in correct_java

    src_correct = tmp_path / "TypesTest.java"
    src_correct.write_text(correct_java, encoding="utf-8")
    import subprocess

    c1 = subprocess.run(["javac", str(src_correct)], capture_output=True, text=True, cwd=tmp_path)
    assert (
        c1.returncode == 0
    ), f"Correct Java skeleton failed to compile: {c1.stderr}\n{correct_java}"

    src_wrong = tmp_path / "TypesTest.java"
    src_wrong.write_text(wrong_java, encoding="utf-8")
    c2 = subprocess.run(["javac", str(src_wrong)], capture_output=True, text=True, cwd=tmp_path)
    assert c2.returncode == 0, f"Wrong Java skeleton failed to compile: {c2.stderr}\n{wrong_java}"


@pytest.mark.skipif(
    shutil.which("octave-cli") is None and shutil.which("octave") is None,
    reason="octave is not installed",
)
def test_matlab_utils_coverage_and_multiline_bug_fix(tmp_path: Path, monkeypatch):
    assert format_matlab_arg("true") == "true"
    assert format_matlab_arg("'quoted'") == "'quoted'"
    assert format_matlab_arg(None) == "None"
    assert get_matlab_literal_str("false") == "false"
    assert get_matlab_literal_str("3.14") == "3.14"

    assert escape_matlab_str("simple") == "'simple'"
    assert escape_matlab_str("line1\nline2") == "sprintf('line1\\nline2')"
    assert escape_matlab_str("100%\nnext") == "sprintf('100%%\\nnext')"

    with pytest.raises(AssertionError, match="WRONG_FILE"):
        call_matlab_function(tmp_path / "missing.m", "fn", [], 5, tmp_path)
    with pytest.raises(AssertionError, match="WRONG_FILE"):
        assert_matlab_function_signature(tmp_path / "missing.m", "fn", tmp_path)

    bad_m = tmp_path / "bad.m"
    bad_m.write_text("x = (1 + 2;\n", encoding="utf-8")
    with pytest.raises(AssertionError, match="COMPILATION_ERROR"):
        _check_matlab_syntax(bad_m, tmp_path)

    m_file = tmp_path / "edge.m"
    m_file.write_text(
        "1;\n"
        "function [x, y] = pair_fn(a, b)\n"
        "    x = a; y = b;\n"
        "end\n"
        "function echo_str(s)\n"
        "    fprintf('%s', s);\n"
        "end\n"
        "function res = ret_str(s)\n"
        "    res = s;\n"
        "end\n"
        "function res = boom()\n"
        "    error('matlab runtime failure');\n"
        "end\n",
        encoding="utf-8",
    )
    assert assert_matlab_function_signature(
        m_file,
        "pair_fn",
        tmp_path,
        expected_parameters="double a, double b",
        expected_return_type="array",
    )
    with pytest.raises(AssertionError, match="has no return value"):
        assert_matlab_function_signature(
            m_file, "echo_str", tmp_path, expected_parameters="s", expected_return_type="double"
        )
    assert call_matlab_function(m_file, "ret_str", ['say "hi"'], 10, tmp_path).strip() == 'say "hi"'
    with pytest.raises(RuntimeError, match="Error executing boom"):
        call_matlab_function(m_file, "boom", [], 10, tmp_path)

    matlab_multiline_cfg = {
        "version": __version__,
        "language": "matlab",
        "required_submission_files": ["multi.m"],
        "questions": [
            {
                "name": "Multiline MATLAB",
                "marking_items": [
                    {
                        "name": "Multiline IO",
                        "target_file": "multi.m",
                        "total_mark": 5,
                        "type": "program_output_test",
                        "expected_input": "first\nsecond",
                        "expected_output": "line 1\nline 2 (100%)",
                    },
                    {
                        "name": "Script IO",
                        "target_file": "multi.m",
                        "total_mark": 5,
                        "type": "program_output_test",
                        "expected_input": "third",
                        "expected_output_script": "print(f'ID_{STUDENT_ID}\\nDONE')",
                    },
                    {
                        "name": "Empty Cases Fn",
                        "target_file": "multi.m",
                        "total_mark": 0,
                        "type": "function_signature_test",
                        "function_name": "helper",
                        "expected_parameters": "double val",
                    },
                ],
            }
        ],
    }
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(yaml.dump(matlab_multiline_cfg), encoding="utf-8")
    runner = ag.AutograderRun(cfg_path, save_log=False)
    res = runner.run_autograder_for_generated_submissions()
    assert sum(t["score"] for t in res["correct_answer"]["tests"]) == 10

    single_script_cfg = ag.Config.model_validate(
        {
            "version": __version__,
            "language": "matlab",
            "required_submission_files": ["single.m"],
            "questions": [
                {
                    "name": "Single Script",
                    "marking_items": [
                        {
                            "target_file": "single.m",
                            "total_mark": 5,
                            "type": "program_output_test",
                            "expected_output_script": "print(STUDENT_ID)",
                        }
                    ],
                }
            ],
        }
    )
    single_src = generate_matlab_skeleton(single_script_cfg, "single.m", correct=True)
    assert f"Fallback student ID: {STUDENT_ID_FALLBACK}" in single_src

    monkeypatch.setattr(shutil, "which", lambda _cmd: None)
    assert get_octave_executable() == "octave"
    _check_matlab_syntax(bad_m, tmp_path)
