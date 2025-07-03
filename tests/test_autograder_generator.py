import os
import zipfile
import tempfile
import shutil
import json
from pathlib import Path
import pytest

from autograder_core.generator import AutograderGenerator
from autograder_core.config import ConfigParser

SAMPLE_CONFIG_PATH = 'cli/config/sample_config.json'

@pytest.fixture
def temp_output_dir():
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d)

def test_autograder_zip_contains_expected_files(temp_output_dir):
    # Parse the sample config
    config_parser = ConfigParser(SAMPLE_CONFIG_PATH)
    config = config_parser.parse()
    generator = AutograderGenerator(config)
    zip_path = generator.generate(temp_output_dir)

    # Check that the zip file exists
    assert os.path.exists(zip_path)
    
    # Check contents of the zip
    with zipfile.ZipFile(zip_path, 'r') as z:
        namelist = z.namelist()
        # Basic expected files
        expected_files = [
            'setup.sh',
            'run_autograder',
            'run_tests.py',
            'requirements.txt',
            'autograder_config.json',
            'README.md',
            'tests/',
        ]
        for fname in expected_files:
            assert any(f.startswith(fname) for f in namelist), f"Missing {fname} in zip: {namelist}"
        # At least one test file per question (now by number)
        with open(SAMPLE_CONFIG_PATH) as f:
            config_data = json.load(f)
        for idx, q in enumerate(config_data['questions'], 1):
            test_file = f"tests/test_question_{idx}.py"
            assert test_file in namelist, f"Missing {test_file} in zip: {namelist}" 