import json
from pathlib import Path
import subprocess
import sys
import zipfile
import pytest

from autograder_gen.cli_gen import find_configs, main
from autograder_gen.version import __version__

SAMPLE_CONFIG = {
    "version": __version__,
    "language": "python",
    "files_necessary": ["solution.py"],
    "questions": [
        {
            "name": "Q1",
            "marking_items": [
                {"target_file": "solution.py", "total_mark": 10, "type": "program_output_test"}
            ],
        }
    ],
}

INVALID_CONFIG = {
    "version": __version__,
    "language": "python",
    "global_time_limit": 300,
}

UNSUPPORTED_LANG_CONFIG = {
    "version": __version__,
    "language": "brainfuck",
    "global_time_limit": 300,
    "files_necessary": ["solution.bf"],
    "questions": [],
}


def test_cli_generates_autograder(tmp_path):
    config_path = tmp_path / "config.yaml"
    with open(config_path, "w") as f:
        json.dump(SAMPLE_CONFIG, f)
    python_executable = sys.executable
    result = subprocess.run(
        [
            python_executable,
            "autograder_gen/cli_gen.py",
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
            "autograder_gen/cli_gen.py",
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
            "autograder_gen/cli_gen.py",
            str(config_path),
            flag,
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    assert (tmp_path / "autograder.zip").exists()
    assert (tmp_path / "description.docx").exists()
    assert not (tmp_path / "description.md").exists()


def test_cli_no_args_shows_help():
    python_executable = sys.executable
    result = subprocess.run(
        [python_executable, "autograder_gen/cli_gen.py"],
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
    assert "--verbose" not in result.stdout
    assert " -v" not in result.stdout
    assert "-v," not in result.stdout
    assert "--run-solution" not in result.stdout
    assert "--run-stubs" not in result.stdout


def test_cli_version_flag():
    python_executable = sys.executable
    result = subprocess.run(
        [python_executable, "autograder_gen/cli_gen.py", "--version"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert f"autograder-gen {__version__}" in result.stdout


def test_cli_missing_config():
    python_executable = sys.executable
    result = subprocess.run(
        [python_executable, "autograder_gen/cli_gen.py", "--description"],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0


def test_cli_invalid_config(tmp_path):
    config_path = tmp_path / "config.yaml"
    with open(config_path, "w") as f:
        json.dump(INVALID_CONFIG, f)
    result = subprocess.run(
        [sys.executable, "autograder_gen/cli_gen.py", str(config_path)],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "error" in result.stdout.lower() or "error" in result.stderr.lower()


def test_cli_unsupported_language(tmp_path):
    config_path = tmp_path / "config.yaml"
    with open(config_path, "w") as f:
        json.dump(UNSUPPORTED_LANG_CONFIG, f)
    result = subprocess.run(
        [sys.executable, "autograder_gen/cli_gen.py", str(config_path)],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert (
        "unsupported" in result.stdout.lower()
        or "unsupported" in result.stderr.lower()
        or "error" in result.stdout.lower()
        or "error" in result.stderr.lower()
    )


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
        [sys.executable, "autograder_gen/cli_gen.py", "-c", "config.yaml"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "unrecognized arguments: -c" in result.stderr


def test_cli_run_solution_unrecognized():
    result = subprocess.run(
        [
            sys.executable,
            "autograder_gen/cli_gen.py",
            "tests/examples/py_simple/config.yaml",
            "--run-solution",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "unrecognized arguments: --run-solution" in result.stderr


def test_cli_run_stubs_unrecognized():
    result = subprocess.run(
        [
            sys.executable,
            "autograder_gen/cli_gen.py",
            "tests/examples/py_simple/config.yaml",
            "--run-stubs",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "unrecognized arguments: --run-stubs" in result.stderr


def test_cli_verbose_unrecognized():
    result = subprocess.run(
        [
            sys.executable,
            "autograder_gen/cli_gen.py",
            "tests/examples/py_simple/config.yaml",
            "--verbose",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "unrecognized arguments: --verbose" in result.stderr


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


def test_cli_batch_flag_unrecognized(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "autograder_gen/cli_gen.py",
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
            "autograder_gen/cli_gen.py",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert (tmp_path / "autograder.zip").exists()
    assert (tmp_path / "stub_correct_answer.zip").exists()


def test_find_configs_single_file(tmp_path: Path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text(f"version: '{__version__}'", encoding="utf-8")
    assert find_configs(cfg) == [cfg]

    cfg_yml = tmp_path / "config.yml"
    cfg_yml.write_text(f"version: '{__version__}'", encoding="utf-8")
    assert find_configs(cfg_yml) == []

    cfg_other = tmp_path / "other.yaml"
    cfg_other.write_text(f"version: '{__version__}'", encoding="utf-8")
    assert find_configs(cfg_other) == []


def test_find_configs_directory_direct(tmp_path: Path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text(f"version: '{__version__}'", encoding="utf-8")
    assert find_configs(tmp_path) == [cfg]


def test_find_configs_directory_nested(tmp_path: Path):
    sub1 = tmp_path / "sub1"
    sub1.mkdir()
    cfg1 = sub1 / "config.yaml"
    cfg1.write_text(f"version: '{__version__}'", encoding="utf-8")

    sub2 = tmp_path / "sub2"
    sub2.mkdir()
    cfg2 = sub2 / "config.yaml"
    cfg2.write_text(f"version: '{__version__}'", encoding="utf-8")

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
        [sys.executable, "autograder_gen/cli_gen.py"],
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
    assert "--run-solution" not in normalized
    assert "--run-stubs" not in normalized
    assert "--verbose" not in normalized
    assert "--run-submission" not in normalized
    assert "--run-stub-submissions" not in normalized


def test_batch_gen_execution(tmp_path: Path, monkeypatch, capsys):
    cfg_path = tmp_path / "config.yaml"
    cfg_content = f"""version: '{__version__}'
language: python
required_files:
  - test.py
questions:
  - name: Q1
    marking_items:
      - name: Item 1
        total_mark: 10
        type: program_output_test
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
    cfg_content = f"""version: '{__version__}'
language: python
required_files:
  - test.py
questions:
  - name: Q1
    marking_items:
      - name: Item 1
        total_mark: 10
        type: program_output_test
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
    ]:
        assert asset_name in captured.out
        assert (tmp_path / asset_name).exists()
    assert not (tmp_path / "description.md").exists()


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
            "autograder_gen/cli_gen.py",
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


def test_cli_positional_single_config(tmp_path):
    config_path = tmp_path / "config.yaml"
    with open(config_path, "w") as f:
        json.dump(SAMPLE_CONFIG, f)
    result = subprocess.run(
        [
            sys.executable,
            "autograder_gen/cli_gen.py",
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
            "autograder_gen/cli_gen.py",
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
            "autograder_gen/cli_gen.py",
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
