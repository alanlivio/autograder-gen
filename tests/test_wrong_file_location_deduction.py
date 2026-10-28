import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path
import pytest
import yaml
from pydantic import ValidationError
import autograder_gen as ag
from autograder_gen.version import __version__


def test_config_wrong_file_location_deduction_default():
    data = {
        "version": __version__,
        "language": "python",
        "files_necessary": ["solution.py"],
        "questions": [
            {
                "name": "Q1",
                "marking_items": [
                    {
                        "target_file": "solution.py",
                        "total_mark": 10,
                        "type": "program_output_test",
                    }
                ],
            }
        ],
    }
    cfg = ag.Config.model_validate(data)
    assert cfg.wrong_file_location_deduction == 0.0


def test_config_wrong_file_location_deduction_custom():
    data = {
        "version": __version__,
        "language": "python",
        "wrong_file_location_deduction": 0.5,
        "files_necessary": ["solution.py"],
        "questions": [
            {
                "name": "Q1",
                "marking_items": [
                    {
                        "target_file": "solution.py",
                        "total_mark": 10,
                        "type": "program_output_test",
                    }
                ],
            }
        ],
    }
    cfg = ag.Config.model_validate(data)
    assert cfg.wrong_file_location_deduction == 0.5


def test_config_wrong_file_location_deduction_requires_strict_false():
    data = {
        "version": __version__,
        "language": "python",
        "strict_file_location": True,
        "wrong_file_location_deduction": 0.5,
        "files_necessary": ["solution.py"],
        "questions": [
            {
                "name": "Q1",
                "marking_items": [
                    {
                        "target_file": "solution.py",
                        "total_mark": 10,
                        "type": "program_output_test",
                    }
                ],
            }
        ],
    }
    with pytest.raises(ValidationError) as exc:
        ag.Config.model_validate(data)
    assert (
        "wrong_file_location_deduction is only supported when strict_file_location is False"
        in str(exc.value)
    )


def test_config_wrong_file_location_deduction_out_of_bounds_fails():
    base_data = {
        "version": __version__,
        "language": "python",
        "files_necessary": ["solution.py"],
        "questions": [
            {
                "name": "Q1",
                "marking_items": [
                    {
                        "target_file": "solution.py",
                        "total_mark": 10,
                        "type": "program_output_test",
                    }
                ],
            }
        ],
    }
    with pytest.raises(ValidationError) as exc:
        ag.Config.model_validate({**base_data, "wrong_file_location_deduction": -0.1})
    assert "wrong_file_location_deduction must be between 0.0 and 1.0" in str(exc.value)

    with pytest.raises(ValidationError) as exc:
        ag.Config.model_validate({**base_data, "wrong_file_location_deduction": 1.5})
    assert "wrong_file_location_deduction must be between 0.0 and 1.0" in str(exc.value)


def test_wrong_file_location_deduction_execution(tmp_path: Path):
    config_dict = {
        "version": __version__,
        "language": "python",
        "strict_file_location": False,
        "wrong_file_location_deduction": 0.5,
        "files_necessary": ["solution.py"],
        "questions": [
            {
                "name": "File Check",
                "marking_items": [
                    {
                        "target_file": "solution.py",
                        "total_mark": 10.0,
                        "type": "program_output_test",
                        "expected_output": "hello",
                    }
                ],
            }
        ],
    }
    cfg = ag.Config.model_validate(config_dict)
    generator = ag.Engine(cfg, config_dict)
    gen_dir = tmp_path / "generated"
    output_zip = generator.generate(str(gen_dir))

    work_dir = tmp_path / "run"
    work_dir.mkdir()
    with zipfile.ZipFile(output_zip, "r") as z:
        z.extractall(work_dir)

    submission_dir = work_dir / "submission"
    sub_folder = submission_dir / "nested" / "dir"
    sub_folder.mkdir(parents=True)
    (sub_folder / "solution.py").write_text("print('hello')", encoding="utf-8")

    results_path = work_dir / "results.json"
    process = subprocess.run(
        [sys.executable, str(work_dir / "run_tests.py")],
        cwd=work_dir,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "PYTHONPATH": str(work_dir),
            "GRADESCOPE_RESULTS_PATH": str(results_path),
            "GRADESCOPE_SOURCE_PATH": str(submission_dir),
        },
    )
    assert results_path.exists(), f"results.json not created. stderr: {process.stderr}"
    with open(results_path, "r", encoding="utf-8") as f:
        results = json.load(f)

    test_res = results["tests"][0]
    assert test_res["score"] == 5.0
    assert test_res["max_score"] == 10.0


def test_wrong_file_location_deduction_not_applied_when_location_correct(tmp_path: Path):
    config_dict = {
        "version": __version__,
        "language": "python",
        "strict_file_location": False,
        "wrong_file_location_deduction": 0.5,
        "files_necessary": ["solution.py"],
        "questions": [
            {
                "name": "File Check",
                "marking_items": [
                    {
                        "target_file": "solution.py",
                        "total_mark": 10.0,
                        "type": "program_output_test",
                        "expected_output": "hello",
                    }
                ],
            }
        ],
    }
    cfg = ag.Config.model_validate(config_dict)
    generator = ag.Engine(cfg, config_dict)
    gen_dir = tmp_path / "generated"
    output_zip = generator.generate(str(gen_dir))

    work_dir = tmp_path / "run"
    work_dir.mkdir()
    with zipfile.ZipFile(output_zip, "r") as z:
        z.extractall(work_dir)

    submission_dir = work_dir / "submission"
    submission_dir.mkdir()
    (submission_dir / "solution.py").write_text("print('hello')", encoding="utf-8")

    results_path = work_dir / "results.json"
    process = subprocess.run(
        [sys.executable, str(work_dir / "run_tests.py")],
        cwd=work_dir,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "PYTHONPATH": str(work_dir),
            "GRADESCOPE_RESULTS_PATH": str(results_path),
            "GRADESCOPE_SOURCE_PATH": str(submission_dir),
        },
    )
    assert results_path.exists(), f"results.json not created. stderr: {process.stderr}"
    with open(results_path, "r", encoding="utf-8") as f:
        results = json.load(f)

    test_res = results["tests"][0]
    assert test_res["score"] == 10.0
    assert test_res["max_score"] == 10.0


def test_wrong_file_location_deduction_multiple_items_execution(tmp_path: Path):
    config_dict = {
        "version": __version__,
        "language": "python",
        "strict_file_location": False,
        "wrong_file_location_deduction": 0.5,
        "files_necessary": ["solution.py"],
        "questions": [
            {
                "name": "Q1 10pts",
                "marking_items": [
                    {
                        "target_file": "solution.py",
                        "total_mark": 10.0,
                        "type": "program_output_test",
                        "expected_output": "hello",
                    }
                ],
            },
            {
                "name": "Q2 20pts",
                "marking_items": [
                    {
                        "target_file": "solution.py",
                        "total_mark": 20.0,
                        "type": "program_output_test",
                        "expected_output": "hello",
                    }
                ],
            },
        ],
    }
    cfg = ag.Config.model_validate(config_dict)
    generator = ag.Engine(cfg, config_dict)
    gen_dir = tmp_path / "generated"
    output_zip = generator.generate(str(gen_dir))

    work_dir = tmp_path / "run"
    work_dir.mkdir()
    with zipfile.ZipFile(output_zip, "r") as z:
        z.extractall(work_dir)

    submission_dir = work_dir / "submission"
    sub_folder = submission_dir / "nested" / "dir"
    sub_folder.mkdir(parents=True)
    (sub_folder / "solution.py").write_text("print('hello')", encoding="utf-8")

    results_path = work_dir / "results.json"
    process = subprocess.run(
        [sys.executable, str(work_dir / "run_tests.py")],
        cwd=work_dir,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "PYTHONPATH": str(work_dir),
            "GRADESCOPE_RESULTS_PATH": str(results_path),
            "GRADESCOPE_SOURCE_PATH": str(submission_dir),
        },
    )
    assert results_path.exists(), f"results.json not created. stderr: {process.stderr}"
    with open(results_path, "r", encoding="utf-8") as f:
        results = json.load(f)

    tests = results["tests"]
    assert len(tests) == 2
    assert tests[0]["score"] == 5.0
    assert tests[0]["max_score"] == 10.0
    assert tests[1]["score"] == 10.0
    assert tests[1]["max_score"] == 20.0


def test_wrong_file_location_autograder_run_log(tmp_path: Path):
    config_dict = {
        "version": __version__,
        "language": "python",
        "strict_file_location": False,
        "wrong_file_location_deduction": 0.5,
        "required_files": ["solution.py"],
        "questions": [
            {
                "name": "Q1",
                "marking_items": [
                    {
                        "target_file": "solution.py",
                        "total_mark": 10.0,
                        "type": "program_output_test",
                        "expected_output": "hello",
                    }
                ],
            }
        ],
    }
    cfg_file = tmp_path / "config.yaml"
    with open(cfg_file, "w", encoding="utf-8") as f:
        yaml.dump(config_dict, f)

    sub_dir = tmp_path / "sub"
    (sub_dir / "nested").mkdir(parents=True)
    (sub_dir / "nested" / "solution.py").write_text("print('hello')", encoding="utf-8")

    runner = ag.AutograderRunner(cfg_file)
    results = runner.run_autograder_for_submission(sub_dir)
    assert (
        "Found file 'solution.py' at ./nested/solution.py, penalties will be applied"
        in results["_file_check_log"]
        or "Found file 'solution.py' at nested/solution.py, penalties will be applied"
        in results["_file_check_log"]
    )
