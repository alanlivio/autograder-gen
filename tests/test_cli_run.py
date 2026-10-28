from __future__ import annotations

import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from autograder_gen.cli_run import find_configs, main, resolve_config
from autograder_gen.version import __version__


def test_cli_run_help():
    result = subprocess.run(
        [sys.executable, "autograder_gen/cli_run.py", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "usage: autograder-run" in result.stdout
    assert "--stubs" in result.stdout
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


def test_cli_run_missing_submission_error():
    result = subprocess.run(
        [
            sys.executable,
            "autograder_gen/cli_run.py",
            "tests/examples/py_simple/config.yaml",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "submission file or directory is required" in result.stderr


def test_cli_run_submission_explicit(tmp_path: Path):
    cfg_src = Path("tests/examples/py_simple/config.yaml").read_text(encoding="utf-8")
    (tmp_path / "config.yaml").write_text(cfg_src, encoding="utf-8")
    sub_zip = tmp_path / "custom_submission.zip"
    with zipfile.ZipFile(sub_zip, "w") as z:
        for f in Path("tests/examples/py_simple/correct_answer").iterdir():
            z.write(f, f.name)

    result = subprocess.run(
        [
            sys.executable,
            "autograder_gen/cli_run.py",
            str(tmp_path / "config.yaml"),
            str(sub_zip),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "submission.log" in result.stdout
    log_path = tmp_path / "submission.log"
    assert log_path.exists()
    content = log_path.read_text(encoding="utf-8")
    assert "Summary per Question:" in content
    assert "# Total Score = 10, Actual Score = 10" in content


def test_cli_run_submission_implicit_config(tmp_path: Path, monkeypatch):
    cfg_src = Path("tests/examples/py_simple/config.yaml").read_text(encoding="utf-8")
    (tmp_path / "config.yaml").write_text(cfg_src, encoding="utf-8")
    sub_zip = tmp_path / "student.zip"
    with zipfile.ZipFile(sub_zip, "w") as z:
        for f in Path("tests/examples/py_simple/correct_answer").iterdir():
            z.write(f, f.name)

    monkeypatch.chdir(tmp_path)
    result = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).resolve().parent.parent / "autograder_gen" / "cli_run.py"),
            str(sub_zip),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "submission.log" in result.stdout
    assert (tmp_path / "submission.log").exists()


def test_cli_run_stubs():
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
    assert result.returncode == 0
    assert "# log stubs for tests/examples/py_simple/config.yaml" in result.stdout
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

    monkeypatch.setattr(sys, "argv", ["autograder-run", str(tmp_path), "--stubs"])
    ret = main()
    assert ret == 0

    captured = capsys.readouterr()
    assert "# log stubs for" in captured.out
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


def test_cli_run_submission_not_found(tmp_path: Path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        Path("tests/examples/py_simple/config.yaml").read_text(encoding="utf-8"), encoding="utf-8"
    )
    result = subprocess.run(
        [
            sys.executable,
            "autograder_gen/cli_run.py",
            str(cfg),
            str(tmp_path / "nonexistent.zip"),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "Submission not found" in result.stderr


def test_resolve_config(tmp_path: Path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text("language: python\n", encoding="utf-8")
    assert resolve_config(cfg) == cfg
    assert resolve_config(tmp_path) == cfg
    assert resolve_config(tmp_path / "missing") is None
