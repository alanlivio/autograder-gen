import shutil
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import pytest
import yaml
from autograder_gen.version import __version__
import autograder_gen as ag


@pytest.mark.parametrize("example_name", ["python", "java", "matlab"])
def test_examples_run_autograder_sh(example_name):
    if example_name == "java" and shutil.which("javac") is None:
        pytest.skip("javac is not installed")
    if (
        example_name == "matlab"
        and shutil.which("octave-cli") is None
        and shutil.which("octave") is None
    ):
        pytest.skip("octave is not installed")

    base_dir = Path(__file__).parent.parent.parent
    example_dir = base_dir / "tests/examples" / example_name
    config_path = example_dir / "config.yaml"
    solution_dir = example_dir / "solution"

    runner = ag.AutograderRun(config_path)
    sol_res = runner.run_autograder_for_submission(
        solution_dir, log_path=example_dir / "solution.log"
    )
    assert sum(t.get("score", 0) for t in sol_res["tests"]) == 10

    stub_res = runner.run_autograder_for_generated_submissions()
    assert sum(t.get("score", 0) for t in stub_res["correct_answer"]["tests"]) == 10
    assert sum(t.get("score", 0) for t in stub_res["wrong_answer"]["tests"]) == 0
    assert sum(t.get("score", 0) for t in stub_res["compiler_error"]["tests"]) == 0
    assert sum(t.get("score", 0) for t in stub_res["correct_answer_wrong_location"]["tests"]) == 10


def test_autograder_runner_config_obj(tmp_path):
    cfg_data = {
        "version": __version__,
        "language": "python",
        "required_submission_files": ["solution.py"],
        "questions": [
            {
                "name": "Q1",
                "marking_items": [
                    {
                        "target_file": "solution.py",
                        "total_mark": 10,
                        "type": "function_return_test",
                        "function_name": "add",
                        "test_cases": [{"args": [1, 2], "expected": "3"}],
                    }
                ],
            }
        ],
    }
    no_ext_file = tmp_path / "custom_config_file"
    no_ext_file.write_text(yaml.dump(cfg_data), encoding="utf-8")

    runner = ag.AutograderRun(no_ext_file)
    assert runner.config_obj is not None
    assert runner.config_obj.total_score == 10


def test_run_autograder_for_generated_submissions():
    base_dir = Path(__file__).parent.parent.parent
    config_path = base_dir / "tests/examples/python/config.yaml"
    runner = ag.AutograderRun(config_path)

    results = runner.run_autograder_for_generated_submissions()
    assert "correct_answer" in results
    assert "wrong_answer" in results
    assert "compiler_error" in results
    assert "correct_answer_wrong_location" in results
    assert "correct_answer_with_wrong_location" in results

    correct_score = sum(t.get("score", 0) for t in results["correct_answer"]["tests"])
    wrong_score = sum(t.get("score", 0) for t in results["wrong_answer"]["tests"])
    compiler_score = sum(t.get("score", 0) for t in results["compiler_error"]["tests"])
    wrong_loc_score = sum(
        t.get("score", 0) for t in results["correct_answer_wrong_location"]["tests"]
    )

    assert correct_score == 10
    assert wrong_score == 0
    assert compiler_score == 0
    assert wrong_loc_score == 10

    assert "log_path" in results["correct_answer"]
    assert "log_path" in results["wrong_answer"]
    assert "log_path" in results["compiler_error"]
    assert "log_path" in results["correct_answer_wrong_location"]
    correct_log = Path(results["correct_answer"]["log_path"])
    wrong_log = Path(results["wrong_answer"]["log_path"])
    compiler_log = Path(results["compiler_error"]["log_path"])
    wrong_loc_log = Path(results["correct_answer_wrong_location"]["log_path"])
    assert correct_log.exists()
    assert wrong_log.exists()
    assert compiler_log.exists()
    assert wrong_loc_log.exists()
    assert correct_log.name == "stub_correct_answer.log"
    assert wrong_log.name == "stub_wrong_answer.log"
    assert compiler_log.name == "stub_compiler_error.log"
    assert wrong_loc_log.name == "stub_correct_answer_wrong_location.log"
    assert "# Total Score = 10, Actual Score = 10" in correct_log.read_text(encoding="utf-8")
    assert "# Total Score = 10, Actual Score = 0" in wrong_log.read_text(encoding="utf-8")
    assert "# Total Score = 10, Actual Score = 0" in compiler_log.read_text(encoding="utf-8")
    assert "# Total Score = 10, Actual Score = 10" in wrong_loc_log.read_text(encoding="utf-8")

    correct_text = correct_log.read_text(encoding="utf-8")
    wrong_loc_text = wrong_loc_log.read_text(encoding="utf-8")
    assert "[INFO] Checking required file: function_return.py..." in correct_text
    assert "[INFO] File 'function_return.py' exists." in correct_text
    assert "[INFO] Checking required file: function_return.py..." in wrong_loc_text
    assert "[WARNING] Required file function_return.py not found in submission" in wrong_loc_text
    assert "[INFO] Found file 'function_return.py' at" in wrong_loc_text
