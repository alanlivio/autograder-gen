import os
import zipfile
import tempfile
import shutil
import pytest
from cli.src.autograder_generator import AutograderGenerator
from cli.src.config_parser import ConfigParser

SAMPLE_CONFIG_PATH = 'cli/config/sample_config.json'

@pytest.fixture
def temp_output_dir():
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d)

def test_setup_sh_contains_setup_commands(temp_output_dir):
    config_parser = ConfigParser(SAMPLE_CONFIG_PATH)
    config = config_parser.parse()
    generator = AutograderGenerator(config)
    zip_path = generator.generate(temp_output_dir)
    with zipfile.ZipFile(zip_path, 'r') as z:
        with z.open('setup.sh') as f:
            content = f.read().decode()
            assert 'pip install numpy pandas matplotlib' in content
            assert 'Setup completed successfully' in content

def test_run_autograder_copies_files(temp_output_dir):
    config_parser = ConfigParser(SAMPLE_CONFIG_PATH)
    config = config_parser.parse()
    generator = AutograderGenerator(config)
    zip_path = generator.generate(temp_output_dir)
    with zipfile.ZipFile(zip_path, 'r') as z:
        with z.open('run_autograder') as f:
            content = f.read().decode()
            assert 'Copying required submission files to source directory' in content
            # Only check for files currently in files_necessary
            for fname in ['solution.py', 'math_functions.py']:
                assert fname in content

def test_per_question_test_file_content(temp_output_dir):
    config_parser = ConfigParser(SAMPLE_CONFIG_PATH)
    config = config_parser.parse()
    generator = AutograderGenerator(config)
    zip_path = generator.generate(temp_output_dir)
    with zipfile.ZipFile(zip_path, 'r') as z:
        # The first question should now be test_question_1.py
        test_file = 'tests/test_question_1.py'
        assert test_file in z.namelist()
        with z.open(test_file) as f:
            content = f.read().decode()
            # Check for the new test class name
            assert 'class TestQuestion1' in content
            # Check for at least one test method
            assert 'def test_item_1' in content or 'def test_item_2' in content 