import json
from pathlib import Path
import subprocess
import sys
import zipfile
import pytest

from autograder_gen.cli import find_configs, main
from autograder_gen.version import __version__

SAMPLE_CONFIG = {
    "version": "1.0",
    "language": "python",
    "files_necessary": ["solution.py"],
    "questions": [
        {
            "name": "Q1",
            "marking_items": [
                {"target_file": "solution.py", "total_mark": 10, "type": "output_comparison"}
            ],
        }
    ],
}


def test_cli_generates_autograder(tmp_path):
    config_path = tmp_path / "config.yaml"
    with open(config_path, "w") as f:
        json.dump(SAMPLE_CONFIG, f)
    python_executable = sys.executable
    result = subprocess.run(
        [
            python_executable,
            "autograder_gen/cli.py",
            "--config",
            str(config_path),
        ],
        capture_output=True,
        text=True,
    )
    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)
    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    zip_path = tmp_path / "autograder.zip"
    assert zip_path.exists(), "autograder.zip was not created by the CLI"


def test_cli_generates_all_assets(tmp_path):
    config_path = tmp_path / "config.yaml"
    with open(config_path, "w") as f:
        json.dump(SAMPLE_CONFIG, f)
    python_executable = sys.executable
    result = subprocess.run(
        [
            python_executable,
            "autograder_gen/cli.py",
            "--config",
            str(config_path),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    assert (tmp_path / "autograder.zip").exists()
    assert not (tmp_path / "description.docx").exists()
    assert not (tmp_path / "description.md").exists()
    assert not (tmp_path / "rubric.csv").exists()
    assert (tmp_path / "stub_correct_answer.zip").exists()
    assert (tmp_path / "stub_wrong_answer.zip").exists()
    assert (tmp_path / "stub_compiler_error.zip").exists()
    assert (tmp_path / "stub_correct_answer_wrong_location.zip").exists()


@pytest.mark.parametrize("flag", ["--description", "--description"])
def test_cli_generates_description(tmp_path, flag):
    config_path = tmp_path / "config.yaml"
    with open(config_path, "w") as f:
        json.dump(SAMPLE_CONFIG, f)
    python_executable = sys.executable
    result = subprocess.run(
        [
            python_executable,
            "autograder_gen/cli.py",
            "--config",
            str(config_path),
            flag,
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    assert (tmp_path / "autograder.zip").exists()
    assert (tmp_path / "description.docx").exists()
    assert (tmp_path / "description.md").exists()


def test_cli_no_args_shows_help():
    python_executable = sys.executable
    result = subprocess.run(
        [python_executable, "autograder_gen/cli.py"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "usage:" in result.stdout.lower()
    assert "--version" in result.stdout
    assert "--config" in result.stdout
    assert "--description" in result.stdout
    assert "stub_correct_answer.zip, stub_wrong_answer.zip" in result.stdout


def test_cli_version_flag():
    python_executable = sys.executable
    result = subprocess.run(
        [python_executable, "autograder_gen/cli.py", "--version"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert f"autograder-gen {__version__}" in result.stdout


def test_cli_missing_config():
    python_executable = sys.executable
    result = subprocess.run(
        [python_executable, "autograder_gen/cli.py", "--description"],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0


def test_cli_config_shortcut_only_receives_one_file(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["-c", "config1.yaml", "config2.yaml"])
    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert "unrecognized arguments: config2.yaml" in captured.err


def test_cli_config_long_flag_only_receives_one_file(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["--config", "config1.yaml", "config2.yaml"])
    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert "unrecognized arguments: config2.yaml" in captured.err


def test_cli_config_shortcut_subprocess_only_receives_one_file():
    result = subprocess.run(
        [sys.executable, "autograder_gen/cli.py", "-c", "config1.yaml", "config2.yaml"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "unrecognized arguments: config2.yaml" in result.stderr


def test_cli_run_submission_folder():
    python_executable = sys.executable
    result = subprocess.run(
        [
            python_executable,
            "autograder_gen/cli.py",
            "--config",
            "tests/examples/py_simple/config.yaml",
            "--run-submission",
            "tests/examples/py_simple/correct_answer",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "submission.log" in result.stdout
    assert "[AutograderRunner: Student View]" not in result.stdout
    assert (Path("tests/examples/py_simple") / "submission.log").exists()


def test_cli_run_submission_zip(tmp_path):
    sub_zip = tmp_path / "submission.zip"
    with zipfile.ZipFile(sub_zip, "w") as z:
        for f in Path("tests/examples/py_simple/correct_answer").iterdir():
            z.write(f, f.name)
    python_executable = sys.executable
    result = subprocess.run(
        [
            python_executable,
            "autograder_gen/cli.py",
            "--config",
            "tests/examples/py_simple/config.yaml",
            "--run-submission",
            str(sub_zip),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "submission.log" in result.stdout
    assert "[AutograderRunner: Student View]" not in result.stdout


def test_cli_run_submission_auto_config():
    python_executable = sys.executable
    result = subprocess.run(
        [
            python_executable,
            "autograder_gen/cli.py",
            "--run-submission",
            "tests/examples/py_simple/correct_answer",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "submission.log" in result.stdout
    assert "[AutograderRunner: Student View]" not in result.stdout


def test_cli_run_submission_verbose():
    python_executable = sys.executable
    result = subprocess.run(
        [
            python_executable,
            "autograder_gen/cli.py",
            "--config",
            "tests/examples/py_simple/config.yaml",
            "--run-submission",
            "tests/examples/py_simple/correct_answer",
            "--verbose",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "[AutograderRunner: Student View]" in result.stdout
    assert "submission.log" in result.stdout


def test_cli_run_submission_not_found():
    python_executable = sys.executable
    result = subprocess.run(
        [
            python_executable,
            "autograder_gen/cli.py",
            "--config",
            "tests/examples/py_simple/config.yaml",
            "--run-submission",
            "nonexistent_submission_dir",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0


def test_cli_run_stubs_submissions_with_config():
    python_executable = sys.executable
    result = subprocess.run(
        [
            python_executable,
            "autograder_gen/cli.py",
            "--config",
            "tests/examples/py_simple/config.yaml",
            "--run-stub-submissions",
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


def test_cli_run_stubs_submissions_with_zip(tmp_path):
    cfg_src = Path("tests/examples/py_simple/config.yaml").read_text(encoding="utf-8")
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(cfg_src, encoding="utf-8")
    python_executable = sys.executable
    gen_result = subprocess.run(
        [
            python_executable,
            "autograder_gen/cli.py",
            "--config",
            str(cfg_file),
        ],
        capture_output=True,
        text=True,
    )
    assert gen_result.returncode == 0
    autograder_zip = tmp_path / "autograder.zip"
    assert autograder_zip.exists()

    with zipfile.ZipFile(autograder_zip, "a") as z:
        z.writestr("autograder_gen.yaml", cfg_src)

    result = subprocess.run(
        [
            python_executable,
            "autograder_gen/cli.py",
            "--config",
            str(autograder_zip),
            "--run-stub-submissions",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "stub_correct_answer.log" in result.stdout
    assert "[AutograderRunner: Student View]" not in result.stdout


def test_cli_run_stubs_submissions_with_generated_zip_missing_config(tmp_path):
    cfg_src = Path("tests/examples/py_simple/config.yaml").read_text(encoding="utf-8")
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(cfg_src, encoding="utf-8")
    python_executable = sys.executable
    gen_result = subprocess.run(
        [
            python_executable,
            "autograder_gen/cli.py",
            "--config",
            str(cfg_file),
        ],
        capture_output=True,
        text=True,
    )
    assert gen_result.returncode == 0
    autograder_zip = tmp_path / "autograder.zip"
    assert autograder_zip.exists()

    result = subprocess.run(
        [
            python_executable,
            "autograder_gen/cli.py",
            "--config",
            str(autograder_zip),
            "--run-stub-submissions",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "autograder_gen.yaml not found in zip archive" in result.stderr


def test_cli_run_stubs_submissions_does_not_accept_arg():
    python_executable = sys.executable
    result = subprocess.run(
        [
            python_executable,
            "autograder_gen/cli.py",
            "--run-stub-submissions",
            "tests/examples/py_simple/config.yaml",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "unrecognized arguments: tests/examples/py_simple/config.yaml" in result.stderr


def test_cli_run_multiple_submissions():
    python_executable = sys.executable
    result = subprocess.run(
        [
            python_executable,
            "autograder_gen/cli.py",
            "--config",
            "tests/examples/py_simple/config.yaml",
            "--run-submission",
            "correct_answer",
            "--run-submission",
            "wrong_answer",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "correct_answer.log" in result.stdout
    assert "wrong_answer.log" in result.stdout
    assert (Path("tests/examples/py_simple") / "correct_answer.log").exists()
    assert (Path("tests/examples/py_simple") / "wrong_answer.log").exists()


def test_cli_run_stubs_and_submissions_together():
    python_executable = sys.executable
    result = subprocess.run(
        [
            python_executable,
            "autograder_gen/cli.py",
            "--config",
            "tests/examples/py_simple/config.yaml",
            "--run-stub-submissions",
            "--run-submission",
            "correct_answer",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "stub_correct_answer.log" in result.stdout
    assert "stub_wrong_answer.log" in result.stdout
    assert "correct_answer.log" in result.stdout
    assert (Path("tests/examples/py_simple") / "correct_answer.log").exists()


def test_cli_mutually_exclusive_config_and_batch(tmp_path):
    config_path = tmp_path / "config.yaml"
    with open(config_path, "w") as f:
        json.dump(SAMPLE_CONFIG, f)
    result = subprocess.run(
        [
            sys.executable,
            "autograder_gen/cli.py",
            "--config",
            str(config_path),
            "--batch",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert (
        "not allowed with argument --config" in result.stderr.lower()
        or "mutually exclusive" in result.stderr.lower()
    )


def test_cli_batch_generation(tmp_path):
    config_path = tmp_path / "config.yaml"
    with open(config_path, "w") as f:
        json.dump(SAMPLE_CONFIG, f)
    result = subprocess.run(
        [
            sys.executable,
            "autograder_gen/cli.py",
            "--batch",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert (tmp_path / "autograder.zip").exists()
    assert (tmp_path / "stub_correct_answer.zip").exists()


def test_find_configs_single_file(tmp_path: Path):
    cfg = tmp_path / "config.yml"
    cfg.write_text("version: '1.0'", encoding="utf-8")
    assert find_configs(cfg) == [cfg]


def test_find_configs_directory_direct(tmp_path: Path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text("version: '1.0'", encoding="utf-8")
    assert find_configs(tmp_path) == [cfg]


def test_find_configs_directory_nested(tmp_path: Path):
    sub1 = tmp_path / "sub1"
    sub1.mkdir()
    cfg1 = sub1 / "config.yml"
    cfg1.write_text("version: '1.0'", encoding="utf-8")

    sub2 = tmp_path / "sub2"
    sub2.mkdir()
    cfg2 = sub2 / "config.yaml"
    cfg2.write_text("version: '1.0'", encoding="utf-8")

    configs = find_configs(tmp_path)
    assert len(configs) == 2
    assert cfg1 in configs
    assert cfg2 in configs


def test_batch_missing_targets(capsys):
    sys.argv = ["autograder-gen", "--batch"]
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert "usage:" in captured.err.lower()


def test_batch_with_description_missing_targets(capsys):
    sys.argv = ["autograder-gen", "--batch", "--description"]
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert "usage:" in captured.err.lower()


def test_batch_cli_subprocess_no_args():
    result = subprocess.run(
        [sys.executable, "autograder_gen/cli.py"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "usage:" in result.stdout.lower()
    assert "--batch" in result.stdout
    assert "DIR_OR_CONFIG [DIR_OR_CONFIG ...]" in result.stdout
    normalized = " ".join(result.stdout.split())
    assert "One or more directories to search or config files to batch process" in normalized
    assert "Generate description.docx and description.md for the assessment" in normalized
    assert "--run-submission, -r DIR_OR_ZIP" in normalized
    assert (
        "Use submission directory or zip file relative to config to be run (can be specified multiple times)"
        in normalized
    )


def test_batch_gen_execution(tmp_path: Path, monkeypatch, capsys):
    cfg_path = tmp_path / "config.yaml"
    cfg_content = """version: '1.0'
language: python
required_files:
  - test.py
questions:
  - name: Q1
    marking_items:
      - name: Item 1
        total_mark: 10
        type: output_comparison
        target_file: test.py
"""
    cfg_path.write_text(cfg_content, encoding="utf-8")

    monkeypatch.setattr(sys, "argv", ["autograder-gen", "--batch", str(tmp_path)])
    main()

    captured = capsys.readouterr()
    for asset_name in [
        "autograder.zip",
        "stub_correct_answer.zip",
        "stub_wrong_answer.zip",
        "stub_compiler_error.zip",
        "stub_correct_answer_wrong_location.zip",
    ]:
        assert asset_name in captured.out
        assert (tmp_path / asset_name).exists()
    assert not (tmp_path / "description.docx").exists()
    assert not (tmp_path / "description.md").exists()


def test_batch_gen_with_description(tmp_path: Path, monkeypatch, capsys):
    cfg_path = tmp_path / "config.yaml"
    cfg_content = """version: '1.0'
language: python
required_files:
  - test.py
questions:
  - name: Q1
    marking_items:
      - name: Item 1
        total_mark: 10
        type: output_comparison
        target_file: test.py
"""
    cfg_path.write_text(cfg_content, encoding="utf-8")

    monkeypatch.setattr(sys, "argv", ["autograder-gen", "--batch", str(tmp_path), "--description"])
    main()

    captured = capsys.readouterr()
    for asset_name in [
        "autograder.zip",
        "stub_correct_answer.zip",
        "stub_wrong_answer.zip",
        "stub_compiler_error.zip",
        "stub_correct_answer_wrong_location.zip",
        "description.docx",
        "description.md",
    ]:
        assert asset_name in captured.out
        assert (tmp_path / asset_name).exists()


def test_batch_run_stub_submissions_flag(tmp_path: Path, monkeypatch, capsys):
    cfg_path = tmp_path / "config.yaml"
    cfg_content = """version: '1.0'
language: python
required_files:
  - solution.py
questions:
  - name: Q1
    marking_items:
      - name: Item 1
        total_mark: 10
        type: function_test
        target_file: solution.py
        function_name: add
        test_cases:
          - args: [1, 2]
            expected: "3"
"""
    cfg_path.write_text(cfg_content, encoding="utf-8")

    monkeypatch.setattr(
        sys, "argv", ["autograder-gen", "--batch", str(tmp_path), "--run-stub-submissions"]
    )
    main()

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


def test_batch_run_submission_folder(tmp_path: Path, monkeypatch, capsys):
    cfg_path = tmp_path / "config.yaml"
    cfg_content = """version: '1.0'
language: python
required_files:
  - solution.py
questions:
  - name: Q1
    marking_items:
      - name: Item 1
        total_mark: 10
        type: function_test
        target_file: solution.py
        function_name: add
        test_cases:
          - args: [1, 2]
            expected: "3"
"""
    cfg_path.write_text(cfg_content, encoding="utf-8")

    sub_dir = tmp_path / "my_submission"
    sub_dir.mkdir()
    (sub_dir / "solution.py").write_text("def add(a, b): return a + b\n", encoding="utf-8")

    monkeypatch.setattr(
        sys,
        "argv",
        ["autograder-gen", "--batch", str(tmp_path), "--run-submission", "my_submission"],
    )
    main()

    captured = capsys.readouterr()
    assert "submission.log" in captured.out
    assert (tmp_path / "submission.log").exists()
    log_content = (tmp_path / "submission.log").read_text(encoding="utf-8")
    assert "Total Score = 10" in log_content


def test_batch_run_submission_multiple_folders(tmp_path: Path, monkeypatch, capsys):
    for i in (1, 2):
        sub_project = tmp_path / f"project_{i}"
        sub_project.mkdir()
        (sub_project / "config.yaml").write_text(
            """version: '1.0'
language: python
required_files:
  - solution.py
questions:
  - name: Q1
    marking_items:
      - name: Item 1
        total_mark: 10
        type: function_test
        target_file: solution.py
        function_name: add
        test_cases:
          - args: [1, 2]
            expected: "3"
""",
            encoding="utf-8",
        )
        ans_dir = sub_project / "correct_answer"
        ans_dir.mkdir()
        (ans_dir / "solution.py").write_text("def add(a, b): return a + b\n", encoding="utf-8")

    monkeypatch.setattr(
        sys,
        "argv",
        ["autograder-gen", "--batch", str(tmp_path), "--run-submission", "correct_answer"],
    )
    main()

    captured = capsys.readouterr()
    assert (tmp_path / "project_1" / "submission.log").exists()
    assert (tmp_path / "project_2" / "submission.log").exists()


def test_batch_run_submission_not_found(tmp_path: Path, monkeypatch, capsys):
    cfg_path = tmp_path / "config.yaml"
    cfg_content = """version: '1.0'
language: python
required_files:
  - solution.py
questions:
  - name: Q1
    marking_items:
      - name: Item 1
        total_mark: 10
        type: function_test
        target_file: solution.py
        function_name: add
        test_cases:
          - args: [1, 2]
            expected: "3"
"""
    cfg_path.write_text(cfg_content, encoding="utf-8")

    monkeypatch.setattr(
        sys,
        "argv",
        ["autograder-gen", "--batch", str(tmp_path), "--run-submission", "nonexistent_dir"],
    )
    main()

    captured = capsys.readouterr()
    assert "[NOT FOUND]" in captured.err


def test_batch_run_submission_verbose(tmp_path: Path, monkeypatch, capsys):
    cfg_path = tmp_path / "config.yaml"
    cfg_content = """version: '1.0'
language: python
required_files:
  - solution.py
questions:
  - name: Q1
    marking_items:
      - name: Item 1
        total_mark: 10
        type: function_test
        target_file: solution.py
        function_name: add
        test_cases:
          - args: [1, 2]
            expected: "3"
"""
    cfg_path.write_text(cfg_content, encoding="utf-8")

    sub_dir = tmp_path / "answer"
    sub_dir.mkdir()
    (sub_dir / "solution.py").write_text("def add(a, b): return a + b\n", encoding="utf-8")

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "autograder-gen",
            "--batch",
            str(tmp_path),
            "--run-submission",
            "answer",
            "--verbose",
        ],
    )
    main()

    captured = capsys.readouterr()
    assert "[AutograderRunner: Student View]" in captured.out
    assert "submission.log" in captured.out


def test_batch_run_multiple_submissions(tmp_path: Path, monkeypatch, capsys):
    cfg_path = tmp_path / "config.yaml"
    cfg_content = """version: '1.0'
language: python
required_files:
  - solution.py
questions:
  - name: Q1
    marking_items:
      - name: Item 1
        total_mark: 10
        type: function_test
        target_file: solution.py
        function_name: add
        test_cases:
          - args: [1, 2]
            expected: "3"
"""
    cfg_path.write_text(cfg_content, encoding="utf-8")

    sub_dir1 = tmp_path / "correct_answer"
    sub_dir1.mkdir()
    (sub_dir1 / "solution.py").write_text("def add(a, b): return a + b\n", encoding="utf-8")

    sub_dir2 = tmp_path / "wrong_answer"
    sub_dir2.mkdir()
    (sub_dir2 / "solution.py").write_text("def add(a, b): return a - b\n", encoding="utf-8")

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "autograder-gen",
            "--batch",
            str(tmp_path),
            "--run-submission",
            "correct_answer",
            "--run-submission",
            "wrong_answer",
        ],
    )
    main()

    captured = capsys.readouterr()
    assert "correct_answer.log" in captured.out
    assert "wrong_answer.log" in captured.out
    assert (tmp_path / "correct_answer.log").exists()
    assert (tmp_path / "wrong_answer.log").exists()


def test_batch_run_stubs_and_submissions_together(tmp_path: Path, monkeypatch, capsys):
    cfg_path = tmp_path / "config.yaml"
    cfg_content = """version: '1.0'
language: python
required_files:
  - solution.py
questions:
  - name: Q1
    marking_items:
      - name: Item 1
        total_mark: 10
        type: function_test
        target_file: solution.py
        function_name: add
        test_cases:
          - args: [1, 2]
            expected: "3"
"""
    cfg_path.write_text(cfg_content, encoding="utf-8")

    sub_dir = tmp_path / "custom_answer"
    sub_dir.mkdir()
    (sub_dir / "solution.py").write_text("def add(a, b): return a + b\n", encoding="utf-8")

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "autograder-gen",
            "--batch",
            str(tmp_path),
            "--run-stub-submissions",
            "--run-submission",
            "custom_answer",
        ],
    )
    main()

    captured = capsys.readouterr()
    assert "stub_correct_answer.log" in captured.out
    assert "stub_wrong_answer.log" in captured.out
    assert "custom_answer.log" in captured.out
    assert (tmp_path / "custom_answer.log").exists()


def test_cli_batch_logs_found_configs_first(tmp_path):
    sub1 = tmp_path / "sub1"
    sub1.mkdir()
    with open(sub1 / "config.yaml", "w") as f:
        json.dump(SAMPLE_CONFIG, f)

    sub2 = tmp_path / "sub2"
    sub2.mkdir()
    with open(sub2 / "config.yaml", "w") as f:
        json.dump(SAMPLE_CONFIG, f)

    result = subprocess.run(
        [
            sys.executable,
            "autograder_gen/cli.py",
            "--batch",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    lines = [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]
    config_lines = [line for line in lines if line.startswith("Found config:")]
    assert len(config_lines) == 2
    assert any("sub1" in line for line in config_lines)
    assert any("sub2" in line for line in config_lines)


def test_cli_schema_flag(capsys):
    ret = main(["--schema"])
    assert ret == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["title"] == "Config"
    assert "properties" in data
    assert "$defs" in data


def test_cli_schema_subprocess():
    result = subprocess.run(
        [
            sys.executable,
            "autograder_gen/cli.py",
            "--schema",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["title"] == "Config"
    assert "properties" in data
