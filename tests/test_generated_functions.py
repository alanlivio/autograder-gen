import os
import sys
import unittest
import tempfile
import shutil
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from autograder_core.generator import AutograderGenerator
from autograder_core.config import AutograderConfig, Question, MarkingItem
import zipfile

# Sample test configurations
def create_function_test_config():
    config = AutograderConfig(
        version="1.0",
        language="python"
    )
    
    question = Question(name="Function Test Question")
    marking_item = MarkingItem(
        type="function_test",
        target_file="solution.py",
        total_mark=50,
        function_name="add_numbers",
        test_cases=[
            {"input": [1, 2], "expected": 3},
            {"input": [-1, 1], "expected": 0},
            {"input": [0, 0], "expected": 0}
        ],
        time_limit=30,
        visibility="visible"
    )
    question.marking_items.append(marking_item)
    config.questions.append(question)
    return config

def create_output_test_config():
    config = AutograderConfig(
        version="1.0",
        language="python"
    )
    
    question = Question(name="Output Test Question")
    marking_item = MarkingItem(
        type="output_comparison",
        target_file="solution.py",
        total_mark=50,
        expected_output="Hello, World!",
        time_limit=30,
        visibility="visible"
    )
    question.marking_items.append(marking_item)
    config.questions.append(question)
    return config

@pytest.fixture
def temp_dir():
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d)

@pytest.fixture
def mock_submission():
    """Create a mock submission with a function that will fail some tests"""
    return """
def add_numbers(a, b):
    # Intentionally wrong implementation for some cases
    if a < 0 or b < 0:
        return a - b  # Wrong for negative numbers
    return a + b
"""

@pytest.fixture
def mock_submission_syntax_error():
    """Create a mock submission with a syntax error"""
    return """
def add_numbers(a, b)
    return a + b  # Missing colon
"""

@pytest.fixture
def mock_submission_runtime_error():
    """Create a mock submission that will raise a runtime error"""
    return """
def add_numbers(a, b):
    return a + b + c  # Undefined variable c
"""

def create_test_environment(temp_dir, config, submission_code):
    """Helper function to set up test environment"""
    # Create autograder directory structure
    autograder_dir = Path(temp_dir)
    autograder_dir.mkdir(parents=True, exist_ok=True)
    
    # Create source directory with the expected path
    source_dir = autograder_dir / "temp_autograder" / "autograder" / "source"
    source_dir.mkdir(parents=True, exist_ok=True)
    
    # Create tests directory and make it a package
    tests_dir = autograder_dir / "temp_autograder" / "tests"
    tests_dir.mkdir(parents=True, exist_ok=True)
    (tests_dir / "__init__.py").touch()
    
    # Write submission file
    with open(source_dir / "solution.py", "w") as f:
        f.write(submission_code)
    
    # Generate autograder files
    generator = AutograderGenerator(config)
    zip_path = generator.generate(temp_dir)
    
    # Extract test files from the zip
    with zipfile.ZipFile(zip_path, 'r') as z:
        # Extract all test files
        for name in z.namelist():
            if name.startswith('tests/') and name.endswith('.py'):
                z.extract(name, autograder_dir / "temp_autograder")
    
    # Debug: Print all files in the temp directory structure
    print("\nFull directory structure:")
    for root, dirs, files in os.walk(autograder_dir):
        level = root.replace(str(autograder_dir), '').count(os.sep)
        indent = ' ' * 4 * level
        print(f"{indent}{os.path.basename(root)}/")
        subindent = ' ' * 4 * (level + 1)
        for f in files:
            print(f"{subindent}{f}")
    
    # Debug: Print zip contents
    print("\nZip file contents:")
    with zipfile.ZipFile(zip_path, 'r') as z:
        for name in z.namelist():
            print(f"  {name}")
    
    # Return path to test file (using the correct naming convention from the generator)
    test_file = tests_dir / "test_question_1.py"
    if not test_file.exists():
        raise FileNotFoundError(f"Test file not found at {test_file}")
    return test_file

def run_test_file(test_file_path):
    """Helper function to run a test file and capture results"""
    # Add both the source and tests directories to sys.path
    test_dir = test_file_path.parent
    source_dir = test_dir.parent / "autograder" / "source"
    
    # Create the source directory if it doesn't exist
    source_dir.mkdir(parents=True, exist_ok=True)
    
    if str(source_dir) not in sys.path:
        sys.path.insert(0, str(source_dir))
    if str(test_dir) not in sys.path:
        sys.path.insert(0, str(test_dir))
    
    # Load the test module directly
    import importlib.util
    spec = importlib.util.spec_from_file_location("test_module", test_file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load test file: {test_file_path}")
        
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    # Find the test class
    test_class = None
    for item in module.__dict__.values():
        if isinstance(item, type) and issubclass(item, unittest.TestCase) and item != unittest.TestCase:
            test_class = item
            break
    
    if not test_class:
        raise ValueError("No test class found in the test file")
    
    # Run the tests
    suite = unittest.TestLoader().loadTestsFromTestCase(test_class)
    result = unittest.TextTestRunner(stream=None).run(suite)
    return result

def test_function_test_correct_implementation(temp_dir, mock_submission):
    """Test that a correct implementation passes all test cases"""
    correct_submission = """
def add_numbers(a, b):
    return a + b
"""
    test_file = create_test_environment(temp_dir, create_function_test_config(), correct_submission)
    result = run_test_file(test_file)
    assert result.wasSuccessful()
    assert result.testsRun > 0

def test_function_test_partial_implementation(temp_dir, mock_submission):
    """Test that a partially correct implementation fails some test cases"""
    test_file = create_test_environment(temp_dir, create_function_test_config(), mock_submission)
    result = run_test_file(test_file)
    assert not result.wasSuccessful()
    assert result.failures
    assert "Wrong for negative numbers" in str(result.failures[0][1])

def test_function_test_syntax_error(temp_dir, mock_submission_syntax_error):
    """Test that syntax errors are caught and reported"""
    test_file = create_test_environment(temp_dir, create_function_test_config(), mock_submission_syntax_error)
    result = run_test_file(test_file)
    assert not result.wasSuccessful()
    assert result.errors
    assert "SyntaxError" in str(result.errors[0][1])

def test_function_test_runtime_error(temp_dir, mock_submission_runtime_error):
    """Test that runtime errors are caught and reported"""
    test_file = create_test_environment(temp_dir, create_function_test_config(), mock_submission_runtime_error)
    result = run_test_file(test_file)
    assert not result.wasSuccessful()
    assert result.errors
    assert "NameError" in str(result.errors[0][1])

def test_output_comparison(temp_dir):
    """Test output comparison marking item"""
    correct_submission = """
print("Hello, World!")
"""
    test_file = create_test_environment(temp_dir, create_output_test_config(), correct_submission)
    result = run_test_file(test_file)
    assert result.wasSuccessful()
    assert result.testsRun > 0

def test_output_comparison_wrong_output(temp_dir):
    """Test output comparison with incorrect output"""
    wrong_submission = """
print("Wrong output!")
"""
    test_file = create_test_environment(temp_dir, create_output_test_config(), wrong_submission)
    result = run_test_file(test_file)
    assert not result.wasSuccessful()
    assert result.failures
    assert "Expected output not found" in str(result.failures[0][1])

def test_error_messages_are_helpful(temp_dir, mock_submission_runtime_error):
    """Test that error messages provide helpful information"""
    test_file = create_test_environment(temp_dir, create_function_test_config(), mock_submission_runtime_error)
    result = run_test_file(test_file)
    error_message = str(result.errors[0][1])
    assert "NameError" in error_message
    assert "variable" in error_message.lower()
    assert "c" in error_message  # Should mention the undefined variable

def test_test_case_isolation(temp_dir):
    """Test that each test case runs in isolation"""
    submission_with_side_effects = """
counter = 0
def add_numbers(a, b):
    global counter
    counter += 1
    if counter > 1:
        raise Exception("Previous test affected this one!")
    return a + b
"""
    test_file = create_test_environment(temp_dir, create_function_test_config(), submission_with_side_effects)
    result = run_test_file(test_file)
    assert not result.wasSuccessful()  # Should fail due to the counter
    assert "Previous test affected this one!" in str(result.errors[0][1]) 