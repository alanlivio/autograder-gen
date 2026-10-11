import json
import zipfile
from pathlib import Path
import pytest
import yaml
import autograder_gen as ag
from autograder_gen.grader_utils import get_student_id, STUDENT_ID_FALLBACK


def test_retrieve_student_id_not_in_json_schema_and_internal_to_autograder_gen():
    schema = ag.Config.model_json_schema()
    assert "retrieve_student_id" not in schema.get("properties", {})

    data_without_script = {
        "version": "1.0",
        "language": "python",
        "files_necessary": ["solution.py"],
        "questions": [
            {
                "name": "Q1",
                "marking_items": [
                    {
                        "target_file": "solution.py",
                        "total_mark": 10,
                        "type": "output_comparison",
                    }
                ],
            }
        ],
    }
    cfg1 = ag.Config.model_validate(data_without_script)
    assert "retrieve_student_id" not in cfg1.get_config_summary()
    assert not hasattr(cfg1, "retrieve_student_id")
    engine1 = ag.Engine(cfg1, data_without_script)
    assert engine1.retrieve_student_id is False

    data_with_script = {
        "version": "1.0",
        "language": "python",
        "files_necessary": ["solution.py"],
        "questions": [
            {
                "name": "Q1",
                "marking_items": [
                    {
                        "target_file": "solution.py",
                        "total_mark": 10,
                        "type": "output_comparison",
                        "expected_output_script": "print(f'Hello {STUDENT_ID}')",
                    }
                ],
            }
        ],
    }
    cfg2 = ag.Config.model_validate(data_with_script)
    assert "retrieve_student_id" not in cfg2.get_config_summary()
    assert not hasattr(cfg2, "retrieve_student_id")
    engine2 = ag.Engine(cfg2, data_with_script)
    assert engine2.retrieve_student_id is True


def test_get_student_id_strip_non_digits(tmp_path: Path):
    meta = {
        "users": [
            {
                "sid": "ID-33931382",
                "email": "student@reading.ac.uk",
            }
        ]
    }
    meta_path = tmp_path / "submission_metadata.json"
    meta_path.write_text(json.dumps(meta), encoding="utf-8")

    result = get_student_id(autograder_root=tmp_path)
    assert result == "33931382"


def test_get_student_id_prioritizes_server_root_over_submission_dir(tmp_path: Path):
    server_meta = {"users": [{"sid": "11111111", "email": "real@example.com"}]}
    (tmp_path / "submission_metadata.json").write_text(json.dumps(server_meta), encoding="utf-8")

    sub_dir = tmp_path / "submission"
    sub_dir.mkdir()
    sub_meta = {"users": [{"sid": "22222222", "email": "fake@example.com"}]}
    (sub_dir / "submission_metadata.json").write_text(json.dumps(sub_meta), encoding="utf-8")

    result = get_student_id(autograder_root=tmp_path)
    assert result == "11111111"


def test_get_student_id_ignores_environment_variable(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("STUDENT_ID", "99999999")
    meta = {"users": [{"sid": "88888888", "email": "test@example.com"}]}
    (tmp_path / "submission_metadata.json").write_text(json.dumps(meta), encoding="utf-8")

    result = get_student_id(autograder_root=tmp_path)
    assert result == "88888888"


def test_stubs_submission_metadata_only_when_gitlab_or_github():
    config_dict = {
        "version": "1.0",
        "language": "python",
        "required_files": ["solution.py"],
        "questions": [
            {
                "name": "Check",
                "marking_items": [
                    {
                        "target_file": "solution.py",
                        "total_mark": 10,
                        "type": "output_comparison",
                    }
                ],
            }
        ],
    }
    cfg = ag.Config.model_validate(config_dict)
    engine = ag.Engine(cfg, config_dict)
    buf = engine.generate_correct_answer_zip()
    with zipfile.ZipFile(buf, "r") as zf:
        assert "submission_metadata.json" not in zf.namelist()

    config_dict["questions"][0]["marking_items"].append({
        "type": "gitlab_submission_exists",
        "total_mark": 5,
    })
    cfg = ag.Config.model_validate(config_dict)
    engine = ag.Engine(cfg, config_dict)
    buf_gl = engine.generate_correct_answer_zip()
    with zipfile.ZipFile(buf_gl, "r") as zf:
        assert "submission_metadata.json" in zf.namelist()
        data = json.loads(zf.read("submission_metadata.json").decode("utf-8"))
        assert data == {"submission_method": "GitLab"}
        assert "users" not in data


def test_get_student_id_default_fallback(tmp_path: Path):
    meta = {
        "users": [
            {
                "sid": "",
                "email": "unknown@student.reading.ac.uk",
            }
        ]
    }
    meta_path = tmp_path / "submission_metadata.json"
    meta_path.write_text(json.dumps(meta), encoding="utf-8")

    result = get_student_id(autograder_root=tmp_path)
    assert result == str(STUDENT_ID_FALLBACK)


def test_generator_output_with_retrieve_student_id(tmp_path: Path):
    config_dict = {
        "version": "1.0",
        "language": "python",
        "files_necessary": ["solution.py"],
        "questions": [
            {
                "name": "Check File",
                "marking_items": [
                    {
                        "target_file": "solution.py",
                        "total_mark": 10,
                        "type": "output_comparison",
                        "expected_output_script": "print(STUDENT_ID)",
                    }
                ],
            }
        ],
    }
    cfg = ag.Config.model_validate(config_dict)
    engine = ag.Engine(cfg, config_dict)
    assert engine.retrieve_student_id is True
    out_dir = tmp_path / "out"
    zip_path = engine.generate(str(out_dir))

    with zipfile.ZipFile(zip_path, "r") as z:
        test_py = z.read("question_1_test.py").decode("utf-8")
        assert "get_student_id" in test_py
        assert "self.student_id = get_student_id()" in test_py
        assert 'os.environ["STUDENT_ID"] = self.student_id' in test_py
        assert 'os.environ.get("STUDENT_ID"' not in test_py
        assert 'student_id = getattr(self, "student_id", None)' in test_py

        run_tests_py = z.read("run_tests.py").decode("utf-8")
        assert 'os.environ["STUDENT_ID"] = get_student_id()' in run_tests_py

        run_autograder = z.read("run_autograder").decode("utf-8")
        assert "submission_metadata.json" in run_autograder
        assert "classlist.csv" not in run_autograder

    with zipfile.ZipFile(out_dir / "stub_correct_answer.zip", "r") as z:
        assert "solution.py" in z.namelist()
        stub_content = z.read("solution.py").decode("utf-8")
        assert str(STUDENT_ID_FALLBACK) in stub_content
        assert f"# Fallback student ID: {STUDENT_ID_FALLBACK}" in stub_content
        assert "submission_metadata.json" not in z.namelist()


def test_question_hello_student_id_python(tmp_path: Path):
    config_dict = {
        "version": "1.0",
        "language": "python",
        "required_files": ["CW1P1.py"],
        "questions": [
            {
                "name": "Question 1 - Hello",
                "description": "Program prints greeting including student number.",
                "marking_items": [
                    {
                        "name": "Hello Output Check",
                        "target_file": "CW1P1.py",
                        "total_mark": 15,
                        "type": "output_comparison",
                        "visibility": "visible",
                        "expected_input": "",
                        "expected_output_script": "print(f'Hello, student {STUDENT_ID}.')",
                    }
                ],
            }
        ],
    }
    cfg_file = tmp_path / "config.yaml"
    with open(cfg_file, "w", encoding="utf-8") as f:
        yaml.dump(config_dict, f)

    meta = {
        "users": [
            {
                "sid": "33931382",
                "email": "student@reading.ac.uk",
            }
        ]
    }

    sub_dir = tmp_path / "sub_correct"
    sub_dir.mkdir()
    (sub_dir / "submission_metadata.json").write_text(json.dumps(meta), encoding="utf-8")
    (sub_dir / "CW1P1.py").write_text(
        'import os\nsid = os.environ.get("STUDENT_ID", "")\nprint(f"Hello, student {sid}.")\n',
        encoding="utf-8",
    )

    runner = ag.AutograderRunner(cfg_file)
    results = runner.run_autograder_for_submission(sub_dir)
    assert "tests" in results
    total_score = sum(t.get("score", 0) for t in results["tests"])
    assert total_score == 15

    sub_wrong = tmp_path / "sub_wrong"
    sub_wrong.mkdir()
    (sub_wrong / "submission_metadata.json").write_text(json.dumps(meta), encoding="utf-8")
    (sub_wrong / "CW1P1.py").write_text(
        'print("Hello, student wrong_id.")\n',
        encoding="utf-8",
    )
    runner_wrong = ag.AutograderRunner(cfg_file)
    results_wrong = runner_wrong.run_autograder_for_submission(sub_wrong)
    total_score_wrong = sum(t.get("score", 0) for t in results_wrong["tests"])
    assert total_score_wrong == 0


def test_question_hello_student_id_java(tmp_path: Path):
    config_dict = {
        "version": "1.0",
        "language": "java",
        "required_files": ["CW1P1.java"],
        "questions": [
            {
                "name": "Question 1 - Hello",
                "description": "Program prints greeting including student number.",
                "marking_items": [
                    {
                        "name": "Hello Output Check",
                        "target_file": "CW1P1.java",
                        "total_mark": 15,
                        "type": "output_comparison",
                        "visibility": "visible",
                        "expected_input": "",
                        "expected_output_script": "print(f'Hello, student {STUDENT_ID}.')",
                    }
                ],
            }
        ],
    }
    cfg_file = tmp_path / "config.yaml"
    with open(cfg_file, "w", encoding="utf-8") as f:
        yaml.dump(config_dict, f)

    meta = {
        "users": [
            {
                "sid": "33931382",
                "email": "student@reading.ac.uk",
            }
        ]
    }

    sub_dir = tmp_path / "sub_correct"
    sub_dir.mkdir()
    (sub_dir / "submission_metadata.json").write_text(json.dumps(meta), encoding="utf-8")
    (sub_dir / "CW1P1.java").write_text(
        'public class CW1P1 {\n    public static void main(String[] args) {\n        String sid = System.getenv("STUDENT_ID");\n        System.out.println("Hello, student " + sid + ".");\n    }\n}\n',
        encoding="utf-8",
    )

    runner = ag.AutograderRunner(cfg_file)
    results = runner.run_autograder_for_submission(sub_dir)
    assert "tests" in results
    total_score = sum(t.get("score", 0) for t in results["tests"])
    assert total_score == 15

    assert "_file_check_log" in results
    log_content = results["_file_check_log"]
    assert "[INFO] Checking student ID..." in log_content
    assert "[INFO] Using student ID: 33931382" in log_content
    assert "[INFO] Environment: " in log_content
    assert "[INFO] Checking required file: CW1P1.java..." in log_content
    assert "[INFO] File 'CW1P1.java' exists." in log_content

    sub_wrong = tmp_path / "sub_wrong"
    sub_wrong.mkdir()
    (sub_wrong / "submission_metadata.json").write_text(json.dumps(meta), encoding="utf-8")
    (sub_wrong / "CW1P1.java").write_text(
        'public class CW1P1 {\n    public static void main(String[] args) {\n        System.out.println("Hello, student 00000000.");\n    }\n}\n',
        encoding="utf-8",
    )
    runner_wrong = ag.AutograderRunner(cfg_file)
    results_wrong = runner_wrong.run_autograder_for_submission(sub_wrong)
    total_score_wrong = sum(t.get("score", 0) for t in results_wrong["tests"])
    assert total_score_wrong == 0


def test_student_id_log_messages(tmp_path: Path, capsys):
    meta = {"users": [{"sid": "98765432", "email": "test@example.com"}]}
    meta_path = tmp_path / "submission_metadata.json"
    meta_path.write_text(json.dumps(meta), encoding="utf-8")

    sid = get_student_id(autograder_root=tmp_path)
    captured = capsys.readouterr().out
    assert sid == "98765432"
    assert "[INFO] Checking student ID..." in captured
    assert "[INFO] Using student ID: 98765432" in captured

    meta_empty = {"users": [{"sid": "", "email": "test@example.com"}]}
    meta_path.write_text(json.dumps(meta_empty), encoding="utf-8")

    sid_def = get_student_id(autograder_root=tmp_path)
    captured_def = capsys.readouterr().out
    assert sid_def == str(STUDENT_ID_FALLBACK)
    assert "[INFO] Checking student ID..." in captured_def
    assert (
        "[ERROR] Student ID not found in submission metadata. Please notify the module instructor."
        in captured_def
    )
    assert f"[INFO] Using student ID: {STUDENT_ID_FALLBACK}" in captured_def


def test_generate_warns_for_retrieve_student_id(tmp_path: Path, capsys):
    config_dict = {
        "version": "1.0",
        "language": "python",
        "files_necessary": ["solution.py"],
        "questions": [
            {
                "name": "Check File",
                "marking_items": [
                    {
                        "target_file": "solution.py",
                        "total_mark": 10,
                        "type": "output_comparison",
                        "expected_output_script": "print(STUDENT_ID)",
                    }
                ],
            }
        ],
    }
    cfg = ag.Config.model_validate(config_dict)
    engine = ag.Engine(cfg, config_dict)
    assert engine.retrieve_student_id is True
    engine.generate(str(tmp_path / "out_warn"))
    captured = capsys.readouterr().out
    expected_warn = (
        "To allow student id retreive go to Gradescope -> Course dashboard's left sidebar -> "
        "click Roster -> Click Sync Roster (if linked to Blackboard/Moodle/Canvas)."
    )
    assert expected_warn in captured

    cfg_file = tmp_path / "out_warn" / "config.yaml"
    with open(cfg_file, "w", encoding="utf-8") as f:
        yaml.dump(config_dict, f)
    runner = ag.AutograderRun(cfg_file)
    capsys.readouterr()
    runner.run_autograder_for_generated_submissions()
    captured_stubs = capsys.readouterr().out
    assert expected_warn not in captured_stubs

    config_no_script = {
        "version": "1.0",
        "language": "python",
        "files_necessary": ["solution.py"],
        "questions": [
            {
                "name": "Check File",
                "marking_items": [
                    {
                        "target_file": "solution.py",
                        "total_mark": 10,
                        "type": "output_comparison",
                    }
                ],
            }
        ],
    }
    cfg_no_script = ag.Config.model_validate(config_no_script)
    engine_no_script = ag.Engine(cfg_no_script, config_no_script)
    assert engine_no_script.retrieve_student_id is False
    engine_no_script.generate(str(tmp_path / "out_nowarn"))
    captured_no_script = capsys.readouterr().out
    assert expected_warn not in captured_no_script


def test_expected_output_script_config_and_validation():
    from autograder_gen.validator import Validator

    config_dict = {
        "version": "1.0",
        "language": "python",
        "required_files": ["main.py"],
        "questions": [
            {
                "name": "Q1",
                "marking_items": [
                    {
                        "target_file": "main.py",
                        "total_mark": 10,
                        "type": "output_comparison",
                        "expected_output_script": "print(f'Hello {STUDENT_ID}')",
                    }
                ],
            }
        ],
    }
    cfg = ag.Config.model_validate(config_dict)
    engine = ag.Engine(cfg, config_dict)
    assert engine.retrieve_student_id is True
    validator = Validator()
    assert validator.validate_json(config_dict) is True
    assert not any("null expected_output" in w for w in validator.warnings)

    bad_config = {
        "version": "1.0",
        "language": "python",
        "required_files": ["main.py"],
        "questions": [
            {
                "name": "Q1",
                "marking_items": [
                    {
                        "target_file": "main.py",
                        "total_mark": 10,
                        "type": "output_comparison",
                        "expected_output_script": "print(f'Hello ",
                    }
                ],
            }
        ],
    }
    bad_val = Validator()
    assert bad_val.validate_json(bad_config) is False
    assert any("invalid expected_output_script syntax" in err for err in bad_val.errors)


def test_stubs_include_submission_metadata_and_correct_skeleton_with_expected_output_script():
    config_dict = {
        "version": "1.0",
        "language": "python",
        "required_files": ["calc.py"],
        "questions": [
            {
                "name": "Calc",
                "marking_items": [
                    {
                        "target_file": "calc.py",
                        "total_mark": 10,
                        "type": "output_comparison",
                        "expected_input": "5\n",
                        "expected_output_script": "n = int(input().strip()); print(f'Ans: {int(STUDENT_ID) * n}')",
                    }
                ],
            }
        ],
    }
    cfg = ag.Config.model_validate(config_dict)
    engine = ag.Engine(cfg, config_dict)
    assert engine.retrieve_student_id is True
    buf = engine.generate_correct_answer_zip()
    with zipfile.ZipFile(buf, "r") as zf:
        assert "submission_metadata.json" not in zf.namelist()
        content = zf.read("calc.py").decode("utf-8")
        assert f"Ans: {STUDENT_ID_FALLBACK * 5}" in content
        assert f"Fallback student ID: {STUDENT_ID_FALLBACK}" in content

    buf_wrong = engine.generate_wrong_answer_zip()
    with zipfile.ZipFile(buf_wrong, "r") as zf:
        assert "submission_metadata.json" not in zf.namelist()

    buf_loc = engine.generate_wrong_file_location_zip()
    with zipfile.ZipFile(buf_loc, "r") as zf:
        assert "src/submission_metadata.json" not in zf.namelist()


def test_expected_output_script_java_skeleton():
    config_dict = {
        "version": "1.0",
        "language": "java",
        "required_files": ["App.java"],
        "questions": [
            {
                "name": "App",
                "marking_items": [
                    {
                        "target_file": "App.java",
                        "total_mark": 10,
                        "type": "output_comparison",
                        "expected_output_script": "print(f'JAVA_SID_{STUDENT_ID}')",
                    }
                ],
            }
        ],
    }
    cfg = ag.Config.model_validate(config_dict)
    engine = ag.Engine(cfg, config_dict)
    buf = engine.generate_correct_answer_zip()
    with zipfile.ZipFile(buf, "r") as zf:
        assert "submission_metadata.json" not in zf.namelist()
        content = zf.read("App.java").decode("utf-8")
        assert f"JAVA_SID_{STUDENT_ID_FALLBACK}" in content
        assert f"Fallback student ID: {STUDENT_ID_FALLBACK}" in content
        assert content.count(f"JAVA_SID_{STUDENT_ID_FALLBACK}") == 1
        assert "inStr" not in content


def test_java_void_function_skeleton_does_not_create_sortcomparison_csv():
    config_dict = {
        "version": "1.0",
        "language": "java",
        "required_files": ["CW1P3.java"],
        "questions": [
            {
                "name": "Q3",
                "marking_items": [
                    {
                        "target_file": "CW1P3.java",
                        "total_mark": 10,
                        "type": "function_test",
                        "function_name": "display",
                        "test_cases": [
                            {"args": [28], "expected": "28"}
                        ],
                    }
                ],
            }
        ],
    }
    cfg = ag.Config.model_validate(config_dict)
    engine = ag.Engine(cfg, config_dict)
    buf = engine.generate_correct_answer_zip()
    with zipfile.ZipFile(buf, "r") as zf:
        content = zf.read("CW1P3.java").decode("utf-8")
        assert "sortComparison.csv" not in content
        assert "Files.writeString" not in content


def test_autograder_run_with_expected_output_script_python(tmp_path: Path):
    config_dict = {
        "version": "1.0",
        "language": "python",
        "required_files": ["solution.py"],
        "questions": [
            {
                "name": "Script Output Test",
                "marking_items": [
                    {
                        "name": "Dynamic Output",
                        "target_file": "solution.py",
                        "total_mark": 20,
                        "type": "output_comparison",
                        "expected_output_script": "print(f'Computed for {STUDENT_ID}: {int(STUDENT_ID) * 2}')",
                    }
                ],
            }
        ],
    }
    cfg_file = tmp_path / "config.yaml"
    with open(cfg_file, "w", encoding="utf-8") as f:
        yaml.dump(config_dict, f)

    sub_dir = tmp_path / "submission"
    sub_dir.mkdir()
    meta = {"users": [{"sid": "42", "email": "s42@example.com"}]}
    (sub_dir / "submission_metadata.json").write_text(json.dumps(meta), encoding="utf-8")
    (sub_dir / "solution.py").write_text(
        'print("Computed for 42: 84")\n',
        encoding="utf-8",
    )

    runner = ag.AutograderRunner(cfg_file)
    results = runner.run_autograder_for_submission(sub_dir)
    assert "tests" in results
    total_score = sum(t.get("score", 0) for t in results["tests"])
    assert total_score == 20

    sub_custom = tmp_path / "sub_custom"
    sub_custom.mkdir()
    meta_custom = {"users": [{"sid": "100", "email": "s100@example.com"}]}
    (sub_custom / "submission_metadata.json").write_text(json.dumps(meta_custom), encoding="utf-8")
    (sub_custom / "solution.py").write_text(
        'print("Computed for 100: 200")\n',
        encoding="utf-8",
    )
    runner_custom = ag.AutograderRunner(cfg_file)
    results_custom = runner_custom.run_autograder_for_submission(sub_custom)
    total_score_custom = sum(t.get("score", 0) for t in results_custom["tests"])
    assert total_score_custom == 20

    sub_wrong = tmp_path / "sub_wrong"
    sub_wrong.mkdir()
    (sub_wrong / "submission_metadata.json").write_text(json.dumps(meta), encoding="utf-8")
    (sub_wrong / "solution.py").write_text(
        'print("Computed for 42: 9999")\n',
        encoding="utf-8",
    )
    runner_wrong = ag.AutograderRunner(cfg_file)
    results_wrong = runner_wrong.run_autograder_for_submission(sub_wrong)
    total_score_wrong = sum(t.get("score", 0) for t in results_wrong["tests"])
    assert total_score_wrong == 0


def test_expected_output_script_scope_only_has_uppercase_student_id(tmp_path: Path):
    config_dict = {
        "version": "1.0",
        "language": "python",
        "required_files": ["solution.py"],
        "questions": [
            {
                "name": "Scope Test",
                "marking_items": [
                    {
                        "target_file": "solution.py",
                        "total_mark": 10,
                        "type": "output_comparison",
                        "expected_output_script": "print(student_id)",
                    }
                ],
            }
        ],
    }
    cfg_file = tmp_path / "config.yaml"
    with open(cfg_file, "w", encoding="utf-8") as f:
        yaml.dump(config_dict, f)

    sub_dir = tmp_path / "submission"
    sub_dir.mkdir()
    meta = {"users": [{"sid": "42", "email": "s42@example.com"}]}
    (sub_dir / "submission_metadata.json").write_text(json.dumps(meta), encoding="utf-8")
    (sub_dir / "solution.py").write_text('print("42")\n', encoding="utf-8")

    runner = ag.AutograderRunner(cfg_file)
    results = runner.run_autograder_for_submission(sub_dir)
    assert results["tests"][0]["score"] == 0
    assert "name 'student_id' is not defined" in results["tests"][0]["output"]


def test_expected_output_script_expected_input_only_via_input(tmp_path: Path):
    config_dict = {
        "version": "1.0",
        "language": "python",
        "required_files": ["solution.py"],
        "questions": [
            {
                "name": "Scope Input Test",
                "marking_items": [
                    {
                        "target_file": "solution.py",
                        "total_mark": 10,
                        "type": "output_comparison",
                        "expected_input": "hello_input\n",
                        "expected_output_script": "print(expected_input)",
                    }
                ],
            }
        ],
    }
    cfg_file = tmp_path / "config.yaml"
    with open(cfg_file, "w", encoding="utf-8") as f:
        yaml.dump(config_dict, f)

    sub_dir = tmp_path / "submission"
    sub_dir.mkdir()
    meta = {"users": [{"sid": "42", "email": "s42@example.com"}]}
    (sub_dir / "submission_metadata.json").write_text(json.dumps(meta), encoding="utf-8")
    (sub_dir / "solution.py").write_text('print("hello_input")\n', encoding="utf-8")

    runner = ag.AutograderRunner(cfg_file)
    results = runner.run_autograder_for_submission(sub_dir)
    assert results["tests"][0]["score"] == 0
    assert "name 'expected_input' is not defined" in results["tests"][0]["output"]

    config_dict["questions"][0]["marking_items"][0]["expected_output_script"] = (
        "val = input().strip(); print(f'{val}_{STUDENT_ID}')"
    )
    with open(cfg_file, "w", encoding="utf-8") as f:
        yaml.dump(config_dict, f)

    (sub_dir / "solution.py").write_text('print("hello_input_42")\n', encoding="utf-8")
    runner_ok = ag.AutograderRunner(cfg_file)
    results_ok = runner_ok.run_autograder_for_submission(sub_dir)
    assert results_ok["tests"][0]["score"] == 10


def test_autograder_run_with_custom_student_id_no_stubs(tmp_path: Path):
    config_dict = {
        "version": "1.0",
        "language": "python",
        "required_files": ["solution.py"],
        "questions": [
            {
                "name": "Custom SID Test",
                "marking_items": [
                    {
                        "name": "Dynamic Output",
                        "target_file": "solution.py",
                        "total_mark": 25,
                        "type": "output_comparison",
                        "expected_output_script": "print(f'CUSTOM_SID_{STUDENT_ID}')",
                    }
                ],
            }
        ],
    }
    cfg_file = tmp_path / "config.yaml"
    with open(cfg_file, "w", encoding="utf-8") as f:
        yaml.dump(config_dict, f)

    sub_dir = tmp_path / "custom_submission"
    sub_dir.mkdir()
    custom_sid = "98765432"
    assert custom_sid != str(STUDENT_ID_FALLBACK)

    meta = {"users": [{"sid": custom_sid, "email": "custom_user@example.com"}]}
    (sub_dir / "submission_metadata.json").write_text(json.dumps(meta), encoding="utf-8")
    (sub_dir / "solution.py").write_text(
        f'print("CUSTOM_SID_{custom_sid}")\n',
        encoding="utf-8",
    )

    runner = ag.AutograderRunner(cfg_file)
    results = runner.run_autograder_for_submission(sub_dir)
    assert "tests" in results
    total_score = sum(t.get("score", 0) for t in results["tests"])
    assert total_score == 25
    assert f"Using student ID: {custom_sid}" in results.get("_stdout", "")


def test_autograder_run_stubs_using_fallback_student_id(tmp_path: Path):
    config_dict = {
        "version": "1.0",
        "language": "python",
        "required_files": ["solution.py"],
        "questions": [
            {
                "name": "Stub Fallback Test",
                "marking_items": [
                    {
                        "name": "Output Item",
                        "target_file": "solution.py",
                        "total_mark": 20,
                        "type": "output_comparison",
                        "expected_output_script": "print(STUDENT_ID)",
                    }
                ],
            }
        ],
    }
    cfg_file = tmp_path / "config.yaml"
    with open(cfg_file, "w", encoding="utf-8") as f:
        yaml.dump(config_dict, f)

    runner = ag.AutograderRunner(cfg_file)
    results = runner.run_autograder_for_generated_submissions()
    correct_score = sum(t.get("score", 0) for t in results["correct_answer"]["tests"])
    wrong_score = sum(t.get("score", 0) for t in results["wrong_answer"]["tests"])
    compiler_score = sum(t.get("score", 0) for t in results["compiler_error"]["tests"])
    assert correct_score == 20
    assert wrong_score == 0
    assert compiler_score == 0


