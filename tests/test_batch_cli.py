import sys
from pathlib import Path
import pytest

from autograder_gen.batch import find_configs, main as batch_main
from autograder_gen.batch_gen import main as batch_gen_main
from autograder_gen.batch_run import main as batch_run_main


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


def test_batch_main_no_args(capsys):
    sys.argv = ["autograder-gen-batch"]
    with pytest.raises(SystemExit) as exc_info:
        batch_main()
    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert "usage:" in captured.err.lower()


def test_batch_run_main_no_args(capsys):
    sys.argv = ["autograder-run-batch"]
    with pytest.raises(SystemExit) as exc_info:
        batch_run_main()
    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert "usage:" in captured.err.lower()


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

    monkeypatch.setattr(sys, "argv", ["autograder-gen-batch", str(tmp_path)])
    batch_main()

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


def test_batch_gen_with_descriptions(tmp_path: Path, monkeypatch, capsys):
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

    monkeypatch.setattr(sys, "argv", ["autograder-gen-batch", "--descriptions", str(tmp_path)])
    batch_main()

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
        sys, "argv", ["autograder-gen-batch", "--run-stub-submissions", str(tmp_path)]
    )
    batch_main()

    captured = capsys.readouterr()
    for log_name in [
        "stub_correct_answer.log",
        "stub_wrong_answer.log",
        "stub_compiler_error.log",
        "stub_correct_answer_wrong_location.log",
    ]:
        assert log_name in captured.out
        assert (tmp_path / log_name).exists()


def test_legacy_batch_run_main(tmp_path: Path, monkeypatch, capsys):
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

    monkeypatch.setattr(sys, "argv", ["autograder-run-batch", str(tmp_path)])
    batch_run_main()

    captured = capsys.readouterr()
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
        ["autograder-gen-batch", str(tmp_path), "--run-submission", "my_submission"],
    )
    batch_main()

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
        ["autograder-gen-batch", str(tmp_path), "--run-submission", "correct_answer"],
    )
    batch_main()

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
        ["autograder-gen-batch", str(tmp_path), "--run-submission", "nonexistent_dir"],
    )
    batch_main()

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
            "autograder-gen-batch",
            str(tmp_path),
            "--run-submission",
            "answer",
            "--verbose",
        ],
    )
    batch_main()

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
            "autograder-gen-batch",
            str(tmp_path),
            "--run-submission",
            "correct_answer",
            "--run-submission",
            "wrong_answer",
        ],
    )
    batch_main()

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
            "autograder-gen-batch",
            str(tmp_path),
            "--run-stub-submissions",
            "--run-submission",
            "custom_answer",
        ],
    )
    batch_main()

    captured = capsys.readouterr()
    assert "stub_correct_answer.log" in captured.out
    assert "stub_wrong_answer.log" in captured.out
    assert "custom_answer.log" in captured.out
    assert (tmp_path / "custom_answer.log").exists()


