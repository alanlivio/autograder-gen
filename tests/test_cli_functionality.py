import subprocess
from pathlib import Path

import sys


def test_cli_generates_autograder(tmp_path):
    # Paths
    config_path = Path('examples/py_simple/config.json')
    output_dir = tmp_path / 'output'
    output_dir.mkdir()

    # Use the venv Python if available
    venv_python = Path('.venv/Scripts/python.exe')
    python_executable = str(venv_python) if venv_python.exists() else sys.executable

    # Run the CLI
    result = subprocess.run([
        python_executable, 'autograder_gen/cli.py',
        '--config', str(config_path),
        '--output', str(output_dir)
    ], capture_output=True, text=True)

    # Output for debugging
    print('STDOUT:', result.stdout)
    print('STDERR:', result.stderr)

    # Check exit code
    assert result.returncode == 0, f"CLI failed: {result.stderr}"

    # Check autograder.zip exists
    zip_path = output_dir / 'autograder.zip'
    assert zip_path.exists(), "autograder.zip was not created by the CLI" 