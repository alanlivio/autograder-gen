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
    assert "usage: autograder-gen [TARGET ...]" in result.stdout
    assert "--version" in result.stdout
    assert "TARGET" in result.stdout
    assert "--config" not in result.stdout
    assert "--batch" not in result.stdout
    assert "--description" in result.stdout
    normalized = " ".join(result.stdout.split())
    assert "stub_correct_answer.zip, stub_wrong_answer.zip" in normalized


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


def test_cli_config_flag_unrecognized(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["--config", "config.yaml"])
    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert "unrecognized arguments: --config" in captured.err


def test_cli_config_shortcut_unrecognized(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["-c", "config.yaml"])
    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert "unrecognized arguments: -c" in captured.err


def test_cli_config_shortcut_subprocess_unrecognized():
    result = subprocess.run(
        [sys.executable, "autograder_gen/cli.py", "-c", "config.yaml"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "unrecognized arguments: -c" in result.stderr


def test_cli_run_solution_folder():
    python_executable = sys.executable
    result = subprocess.run(
        [
            python_executable,
            "autograder_gen/cli.py",
            "tests/examples/py_simple/config.yaml",
            "--run-solution",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "solution.log" in result.stdout
    assert "[AutograderRunner: Student View]" not in result.stdout
    assert (Path("tests/examples/py_simple") / "solution.log").exists()


def test_cli_run_solution_zip(tmp_path):
    cfg_src = Path("tests/examples/py_simple/config.yaml").read_text(encoding="utf-8")
    (tmp_path / "config.yaml").write_text(cfg_src, encoding="utf-8")
    sub_zip = tmp_path / "solution.zip"
    with zipfile.ZipFile(sub_zip, "w") as z:
        for f in Path("tests/examples/py_simple/correct_answer").iterdir():
            z.write(f, f.name)
    python_executable = sys.executable
    result = subprocess.run(
        [
            python_executable,
            "autograder_gen/cli.py",
            str(tmp_path / "config.yaml"),
            "--run-solution",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "solution.log" in result.stdout
    assert "[AutograderRunner: Student View]" not in result.stdout


def test_cli_run_solution_auto_config(monkeypatch):
    monkeypatch.chdir("tests/examples/py_simple")
    result = subprocess.run(
        [
            sys.executable,
            str(Path("../../../autograder_gen/cli.py").resolve()),
            "--run-solution",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "solution.log" in result.stdout
    assert "[AutograderRunner: Student View]" not in result.stdout


def test_cli_run_solution_verbose():
    python_executable = sys.executable
    result = subprocess.run(
        [
            python_executable,
            "autograder_gen/cli.py",
            "tests/examples/py_simple/config.yaml",
            "--run-solution",
            "--verbose",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "[AutograderRunner: Student View]" in result.stdout
    assert "solution.log" in result.stdout


def test_cli_run_solution_not_found(tmp_path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text(Path("tests/examples/py_simple/config.yaml").read_text(encoding="utf-8"), encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            "autograder_gen/cli.py",
            str(cfg),
            "--run-solution",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "Solution not found" in result.stderr


def test_cli_run_stubs_with_config():
    python_executable = sys.executable
    result = subprocess.run(
        [
            python_executable,
            "autograder_gen/cli.py",
            "tests/examples/py_simple/config.yaml",
            "--run-stubs",
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


def test_cli_run_stubs_with_zip(tmp_path):
    cfg_src = Path("tests/examples/py_simple/config.yaml").read_text(encoding="utf-8")
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(cfg_src, encoding="utf-8")
    python_executable = sys.executable
    gen_result = subprocess.run(
        [
            python_executable,
            "autograder_gen/cli.py",
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
            str(autograder_zip),
            "--run-stubs",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "stub_correct_answer.log" in result.stdout
    assert "[AutograderRunner: Student View]" not in result.stdout


def test_cli_run_stubs_with_generated_zip_missing_config(tmp_path):
    cfg_src = Path("tests/examples/py_simple/config.yaml").read_text(encoding="utf-8")
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(cfg_src, encoding="utf-8")
    python_executable = sys.executable
    gen_result = subprocess.run(
        [
            python_executable,
            "autograder_gen/cli.py",
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
            str(autograder_zip),
            "--run-stubs",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "autograder_gen.yaml not found in zip archive" in result.stderr


def test_cli_run_stubs_does_not_accept_arg():
    python_executable = sys.executable
    result = subprocess.run(
        [
            python_executable,
            "autograder_gen/cli.py",
            "--run-stubs=tests/examples/py_simple/config.yaml",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "ignored explicit argument" in result.stderr


def test_cli_run_submission_flag_unrecognized(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["--run-submission", "answer"])
    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert "unrecognized arguments: --run-submission" in captured.err


def test_cli_run_stub_submissions_flag_unrecognized(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["--run-stub-submissions"])
    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert "unrecognized arguments: --run-stub-submissions" in captured.err


def test_cli_run_stubs_and_solution_together():
    python_executable = sys.executable
    result = subprocess.run(
        [
            python_executable,
            "autograder_gen/cli.py",
            "tests/examples/py_simple/config.yaml",
            "--run-stubs",
            "--run-solution",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "stub_correct_answer.log" in result.stdout
    assert "solution.log" in result.stdout
    assert (Path("tests/examples/py_simple") / "solution.log").exists()


def test_cli_batch_flag_unrecognized(tmp_path):
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
    assert result.returncode == 2
    assert "unrecognized arguments: --batch" in result.stderr


def test_cli_batch_generation(tmp_path):
    config_path = tmp_path / "config.yaml"
    with open(config_path, "w") as f:
        json.dump(SAMPLE_CONFIG, f)
    result = subprocess.run(
        [
            sys.executable,
            "autograder_gen/cli.py",
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
    assert "unrecognized arguments: --batch" in captured.err


def test_batch_with_description_missing_targets(capsys):
    sys.argv = ["autograder-gen", "--batch", "--description"]
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert "unrecognized arguments: --batch" in captured.err


def test_batch_cli_subprocess_no_args():
    result = subprocess.run(
        [sys.executable, "autograder_gen/cli.py"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "usage:" in result.stdout.lower()
    assert "TARGET" in result.stdout
    assert "--batch" not in result.stdout
    assert "--config" not in result.stdout
    normalized = " ".join(result.stdout.split())
    assert (
        "Configuration YAML file(s) or directories with config.yaml inside (default: ./config.yaml)"
        in normalized
    )
    assert "Generate description.docx and description.md for the assessment" in normalized
    assert "--run-solution" in normalized
    assert "--run-stubs" in normalized
    assert "--run-submission" not in normalized
    assert "--run-stub-submissions" not in normalized


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

    monkeypatch.setattr(sys, "argv", ["autograder-gen", str(tmp_path)])
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

    monkeypatch.setattr(sys, "argv", ["autograder-gen", str(tmp_path), "--description"])
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
        sys, "argv", ["autograder-gen", str(tmp_path), "--run-stubs"]
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


def test_batch_run_solution_folder(tmp_path: Path, monkeypatch, capsys):
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

    sub_dir = tmp_path / "solution"
    sub_dir.mkdir()
    (sub_dir / "solution.py").write_text("def add(a, b): return a + b\n", encoding="utf-8")

    monkeypatch.setattr(
        sys,
        "argv",
        ["autograder-gen", str(tmp_path), "--run-solution"],
    )
    main()

    captured = capsys.readouterr()
    assert "solution.log" in captured.out
    assert (tmp_path / "solution.log").exists()
    log_content = (tmp_path / "solution.log").read_text(encoding="utf-8")
    assert "Total Score = 10" in log_content


def test_batch_run_solution_multiple_folders(tmp_path: Path, monkeypatch, capsys):
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
        ans_dir = sub_project / "solution"
        ans_dir.mkdir()
        (ans_dir / "solution.py").write_text("def add(a, b): return a + b\n", encoding="utf-8")

    monkeypatch.setattr(
        sys,
        "argv",
        ["autograder-gen", str(tmp_path), "--run-solution"],
    )
    main()

    captured = capsys.readouterr()
    assert (tmp_path / "project_1" / "solution.log").exists()
    assert (tmp_path / "project_2" / "solution.log").exists()


def test_batch_run_solution_not_found(tmp_path: Path, monkeypatch, capsys):
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
        ["autograder-gen", str(tmp_path), "--run-solution"],
    )
    main()

    captured = capsys.readouterr()
    assert "[NOT FOUND]" in captured.err


def test_batch_run_solution_verbose(tmp_path: Path, monkeypatch, capsys):
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

    sub_dir = tmp_path / "solution"
    sub_dir.mkdir()
    (sub_dir / "solution.py").write_text("def add(a, b): return a + b\n", encoding="utf-8")

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "autograder-gen",
            str(tmp_path),
            "--run-solution",
            "--verbose",
        ],
    )
    main()

    captured = capsys.readouterr()
    assert "[AutograderRunner: Student View]" in captured.out
    assert "solution.log" in captured.out


def test_batch_run_stubs_and_solution_together(tmp_path: Path, monkeypatch, capsys):
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

    sub_dir = tmp_path / "solution"
    sub_dir.mkdir()
    (sub_dir / "solution.py").write_text("def add(a, b): return a + b\n", encoding="utf-8")

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "autograder-gen",
            str(tmp_path),
            "--run-stubs",
            "--run-solution",
        ],
    )
    main()

    captured = capsys.readouterr()
    assert "stub_correct_answer.log" in captured.out
    assert "solution.log" in captured.out
    assert (tmp_path / "solution.log").exists()


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


def test_cli_positional_single_config(tmp_path):
    config_path = tmp_path / "config.yaml"
    with open(config_path, "w") as f:
        json.dump(SAMPLE_CONFIG, f)
    result = subprocess.run(
        [
            sys.executable,
            "autograder_gen/cli.py",
            str(config_path),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert (tmp_path / "autograder.zip").exists()


def test_cli_positional_directory(tmp_path):
    sub = tmp_path / "sub"
    sub.mkdir()
    with open(sub / "config.yaml", "w") as f:
        json.dump(SAMPLE_CONFIG, f)
    result = subprocess.run(
        [
            sys.executable,
            "autograder_gen/cli.py",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert (sub / "autograder.zip").exists()


def test_cli_positional_multiple_configs(tmp_path):
    sub1 = tmp_path / "sub1"
    sub1.mkdir()
    cfg1 = sub1 / "config.yaml"
    with open(cfg1, "w") as f:
        json.dump(SAMPLE_CONFIG, f)

    sub2 = tmp_path / "sub2"
    sub2.mkdir()
    cfg2 = sub2 / "config.yaml"
    with open(cfg2, "w") as f:
        json.dump(SAMPLE_CONFIG, f)

    result = subprocess.run(
        [
            sys.executable,
            "autograder_gen/cli.py",
            str(cfg1),
            str(cfg2),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert (sub1 / "autograder.zip").exists()
    assert (sub2 / "autograder.zip").exists()


def test_cli_zero_args_defaults_to_config(tmp_path, monkeypatch):
    config_path = tmp_path / "config.yaml"
    with open(config_path, "w") as f:
        json.dump(SAMPLE_CONFIG, f)
    monkeypatch.chdir(tmp_path)
    ret = main([])
    assert ret == 0
    assert (tmp_path / "autograder.zip").exists()
