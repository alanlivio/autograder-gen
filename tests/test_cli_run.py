from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from autograder_gen.cli_run import main
from autograder_gen.version import __version__


def test_cli_run_help():
    result = subprocess.run(
        [sys.executable, "autograder_gen/cli_run.py", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "usage: autograder-run" in result.stdout
    assert "--stubs" not in result.stdout
    assert "--verbose" not in result.stdout
    assert " -v" not in result.stdout
    assert "-v," not in result.stdout


def test_cli_run_no_args_shows_help():
    result = subprocess.run(
        [sys.executable, "autograder_gen/cli_run.py"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "usage: autograder-run" in result.stdout


def test_cli_run_version():
    result = subprocess.run(
        [sys.executable, "autograder_gen/cli_run.py", "--version"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert f"autograder-run {__version__}" in result.stdout


def test_cli_run_rejects_verbose():
    result = subprocess.run(
        [
            sys.executable,
            "autograder_gen/cli_run.py",
            "tests/examples/py_simple/config.yaml",
            "--verbose",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "unrecognized arguments: --verbose" in result.stderr


def test_cli_run_stubs_flag_removed():
    result = subprocess.run(
        [
            sys.executable,
            "autograder_gen/cli_run.py",
            "tests/examples/py_simple/config.yaml",
            "--stubs",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "unrecognized arguments: --stubs" in result.stderr


def test_cli_run_stubs():
    result = subprocess.run(
        [
            sys.executable,
            "autograder_gen/cli_run.py",
            "tests/examples/py_simple/config.yaml",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "# log tests/examples/py_simple/config.yaml" in result.stdout
    assert "solution.log" not in result.stdout
    assert "stub_correct_answer.log" in result.stdout
    assert "stub_wrong_answer.log" in result.stdout
    assert "stub_compiler_error.log" in result.stdout
    assert "stub_correct_answer_wrong_location.log" in result.stdout
    assert "[AutograderRunner: Student View]" not in result.stdout

    correct_log = Path("tests/examples/py_simple/stub_correct_answer.log")
    assert correct_log.exists()
    correct_content = correct_log.read_text(encoding="utf-8")
    assert "Summary per Question:" in correct_content
    assert "# Total Score = 10, Actual Score = 10" in correct_content
    assert "See student message below." in correct_content


def test_cli_run_batch_stubs(tmp_path: Path, monkeypatch, capsys):
    cfg_path = tmp_path / "config.yaml"
    cfg_content = f"""version: '{__version__}'
language: python
required_files:
  - solution.py
questions:
  - name: Q1
    marking_items:
      - name: Item 1
        total_mark: 10
        type: function_return_test
        target_file: solution.py
        function_name: add
        test_cases:
          - args: [1, 2]
            expected: "3"
"""
    cfg_path.write_text(cfg_content, encoding="utf-8")

    monkeypatch.setattr(sys, "argv", ["autograder-run", str(tmp_path)])
    ret = main()
    assert ret == 0

    captured = capsys.readouterr()
    assert "# log" in captured.out
    assert "solution.log" not in captured.out
    for log_name in [
        "stub_correct_answer.log",
        "stub_wrong_answer.log",
        "stub_compiler_error.log",
        "stub_correct_answer_wrong_location.log",
    ]:
        assert log_name in captured.out
        assert (tmp_path / log_name).exists()
        log_text = (tmp_path / log_name).read_text(encoding="utf-8")
        assert "Summary per Question:" in log_text


def test_cli_run_solution_and_stubs(tmp_path: Path, monkeypatch, capsys):
    assignment = tmp_path / "week_05_arrays"
    assignment.mkdir()
    (assignment / "config.yaml").write_text(
        Path("tests/examples/py_simple/config.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    solution = assignment / "solution"
    solution.mkdir()
    for f in Path("tests/examples/py_simple/correct_answer").iterdir():
        (solution / f.name).write_bytes(f.read_bytes())

    monkeypatch.chdir(tmp_path)
    ret = main(["week_05_arrays"])
    assert ret == 0

    captured = capsys.readouterr()
    assert "# log week_05_arrays/config.yaml" in captured.out
    assert "week_05_arrays/solution.log" in captured.out
    assert "week_05_arrays/stub_correct_answer.log" in captured.out
    solution_log = (assignment / "solution.log").read_text(encoding="utf-8")
    assert "# Total Score = 10, Actual Score = 10" in solution_log


def test_cli_run_target_without_config(tmp_path: Path):
    result = subprocess.run(
        [
            sys.executable,
            "autograder_gen/cli_run.py",
            str(tmp_path / "nonexistent.zip"),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "config.yaml not found" in result.stderr
