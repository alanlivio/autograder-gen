import json
import subprocess
from pathlib import Path
import sys

SAMPLE_CONFIG = {
    "version": "1.0",
    "language": "python",
    "files_necessary": ["solution.py"],
    "questions": [
        {
            "name": "Q1",
            "marking_items": [
                {"target_file": "solution.py", "total_mark": 10, "type": "file_exists"}
            ],
        }
    ],
}


def test_cli_generates_autograder(tmp_path):
    # Paths
    config_path = tmp_path / "config.yaml"
    with open(config_path, "w") as f:
        json.dump(SAMPLE_CONFIG, f)

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    # Use the current Python interpreter
    python_executable = sys.executable

    # Run the CLI
    result = subprocess.run(
        [
            python_executable,
            "autograder_gen/cli.py",
            "--config",
            str(config_path),
            "--output",
            str(output_dir),
        ],
        capture_output=True,
        text=True,
    )

    # Output for debugging
    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)

    # Check exit code
    assert result.returncode == 0, f"CLI failed: {result.stderr}"

    # Check autograder.zip exists
    zip_path = output_dir / "autograder.zip"
    assert zip_path.exists(), "autograder.zip was not created by the CLI"


def test_cli_generates_all_assets(tmp_path):
    # Paths
    config_path = tmp_path / "config.yaml"
    with open(config_path, "w") as f:
        json.dump(SAMPLE_CONFIG, f)

    output_dir = tmp_path / "output_all"
    output_dir.mkdir()

    # Use the current Python interpreter
    python_executable = sys.executable

    # Run the CLI with new flags
    result = subprocess.run(
        [
            python_executable,
            "autograder_gen/cli.py",
            "--config",
            str(config_path),
            "--output",
            str(output_dir),
            "--with-description",
            "--with-skeletons",
        ],
        capture_output=True,
        text=True,
    )

    # Check exit code
    assert result.returncode == 0, f"CLI failed: {result.stderr}"

    # Check all assets exist
    assert (output_dir / "autograder.zip").exists()
    assert (output_dir / "description.docx").exists()
    assert (output_dir / "correct_answer.zip").exists()
    assert (output_dir / "wrong_answer.zip").exists()
