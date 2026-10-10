import json
import zipfile
from pathlib import Path
import pytest
import yaml
import autograder_gen as ag
from autograder_gen.grader_utils import get_student_id


def test_config_retrieve_student_id_default():
    data = {
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
    cfg = ag.Config.model_validate(data)
    assert cfg.retrieve_student_id is False
    assert cfg.get_config_summary()["retrieve_student_id"] is False


def test_config_retrieve_student_id_enabled():
    data = {
        "version": "1.0",
        "language": "python",
        "retrieve_student_id": True,
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
    cfg = ag.Config.model_validate(data)
    assert cfg.retrieve_student_id is True
    assert cfg.get_config_summary()["retrieve_student_id"] is True


def test_get_student_id_from_metadata(tmp_path: Path):
    meta = {
        "users": [
            {
                "sid": "33931382",
                "email": "a.guedes@reading.ac.uk",
            }
        ]
    }
    meta_path = tmp_path / "submission_metadata.json"
    meta_path.write_text(json.dumps(meta), encoding="utf-8")

    result = get_student_id(autograder_root=tmp_path)
    assert result == "33931382"


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


def test_get_student_id_fallback_to_classlist(tmp_path: Path):
    meta = {
        "users": [
            {
                "sid": "",
                "email": "c.anstee@student.reading.ac.uk",
            }
        ]
    }
    meta_path = tmp_path / "submission_metadata.json"
    meta_path.write_text(json.dumps(meta), encoding="utf-8")

    classlist_file = tmp_path / "classlist.csv"
    classlist_file.write_text(
        "SPR code,Email address\n33931382,a.guedes@reading.ac.uk\n31018601,c.anstee@student.reading.ac.uk\n",
        encoding="utf-8",
    )

    result = get_student_id(autograder_root=tmp_path, classlist_path=classlist_file)
    assert result == "31018601"


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
    assert result == "12345678"


def test_generator_output_with_retrieve_student_id(tmp_path: Path):
    config_dict = {
        "version": "1.0",
        "language": "python",
        "retrieve_student_id": True,
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
    cfg = ag.Config.model_validate(config_dict)
    engine = ag.Engine(cfg, config_dict)
    out_dir = tmp_path / "out"
    zip_path = engine.generate(str(out_dir))

    with zipfile.ZipFile(zip_path, "r") as z:
        test_py = z.read("question_1_test.py").decode("utf-8")
        assert "get_student_id" in test_py
        assert "self.student_id = get_student_id()" in test_py
        assert 'os.environ["STUDENT_ID"] = self.student_id' in test_py

        run_tests_py = z.read("run_tests.py").decode("utf-8")
        assert 'os.environ["STUDENT_ID"] = get_student_id()' in run_tests_py

        run_autograder = z.read("run_autograder").decode("utf-8")
        assert 'cp "classlist.csv"' in run_autograder


def test_config_auto_enable_retrieve_student_id_from_placeholder():
    data = {
        "version": "1.0",
        "language": "python",
        "required_files": ["CW1P1.py"],
        "questions": [
            {
                "name": "Question 1 - Hello",
                "description": "Program prints greeting including student number. Format: 'Hello, student <student_id>.'",
                "marking_items": [
                    {
                        "name": "Hello Output Check",
                        "target_file": "CW1P1.py",
                        "total_mark": 15,
                        "type": "output_comparison",
                        "visibility": "visible",
                        "expected_input": "",
                        "expected_output": "Hello, student <STUDENT_ID>.",
                    }
                ],
            }
        ],
    }
    cfg = ag.Config.model_validate(data)
    assert cfg.retrieve_student_id is True
    assert cfg.get_config_summary()["retrieve_student_id"] is True


def test_question_hello_student_id_python(tmp_path: Path):
    config_dict = {
        "version": "1.0",
        "language": "python",
        "required_files": ["CW1P1.py"],
        "questions": [
            {
                "name": "Question 1 - Hello",
                "description": "Program prints greeting including student number. Format: 'Hello, student <student_id>.'",
                "marking_items": [
                    {
                        "name": "Hello Output Check",
                        "target_file": "CW1P1.py",
                        "total_mark": 15,
                        "type": "output_comparison",
                        "visibility": "visible",
                        "expected_input": "",
                        "expected_output": "Hello, student <STUDENT_ID>.",
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
                "description": "Program prints greeting including student number. Format: 'Hello, student <student_id>.'",
                "marking_items": [
                    {
                        "name": "Hello Output Check",
                        "target_file": "CW1P1.java",
                        "total_mark": 15,
                        "type": "output_comparison",
                        "visibility": "visible",
                        "expected_input": "",
                        "expected_output": "Hello, student <STUDENT_ID>.",
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
    cl_path = tmp_path / "classlist.csv"
    cl_path.write_text("11223344,test@example.com\n", encoding="utf-8")

    sid_cl = get_student_id(autograder_root=tmp_path, classlist_path=cl_path)
    captured_cl = capsys.readouterr().out
    assert sid_cl == "11223344"
    assert "[INFO] Checking student ID..." in captured_cl
    assert (
        "[INFO] Student ID not found in submission metadata; checking classlist.csv..."
        in captured_cl
    )
    assert "[INFO] Using student ID: 11223344" in captured_cl

    cl_path.write_text("55667788,other@example.com\n", encoding="utf-8")
    sid_def = get_student_id(autograder_root=tmp_path, classlist_path=cl_path)
    captured_def = capsys.readouterr().out
    assert sid_def == "12345678"
    assert "[INFO] Checking student ID..." in captured_def
    assert (
        "[INFO] Student ID not found in submission metadata; checking classlist.csv..."
        in captured_def
    )
    assert "[INFO] Student not found in classlist.csv; using default ID." in captured_def
    assert "[INFO] Using student ID: 12345678" in captured_def
