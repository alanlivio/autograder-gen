import pytest
from pydantic import ValidationError
from autograder_gen.version import __version__
import autograder_gen as ag


def test_marking_item_schema_valid():
    data = {"target_file": "solution.py", "total_mark": 10, "type": "output_comparison"}
    result = ag.MarkingItem(**data)
    assert result.target_file == "solution.py"
    assert result.total_mark == 10
    assert result.type == "output_comparison"
    assert result.time_limit == 30


def test_marking_item_file_exists_type_invalid():
    data = {"target_file": "solution.py", "total_mark": 10, "type": "file_exists"}
    with pytest.raises(ValidationError):
        ag.MarkingItem(**data)


def test_marking_item_schema_float_total_mark():
    data = {"target_file": "solution.py", "total_mark": 7.5, "type": "output_comparison"}
    result = ag.MarkingItem(**data)
    assert result.total_mark == 7.5
    assert isinstance(result.total_mark, float)


def test_marking_item_schema_invalid_type():
    data = {"target_file": "solution.py", "total_mark": 10, "type": "invalid_type"}
    with pytest.raises(ValidationError) as excinfo:
        ag.MarkingItem(**data)
    # Check that the invalid_type triggered the validation error for 'type'
    errors = excinfo.value.errors()
    assert any(error["loc"] == ("type",) for error in errors)


def test_question_schema_valid():
    data = {
        "name": "Q1",
        "marking_items": [
            {"target_file": "solution.py", "total_mark": 10, "type": "output_comparison"}
        ],
    }
    result = ag.Question(**data)
    assert result.name == "Q1"
    assert len(result.marking_items) == 1


def test_autograder_config_schema_full():
    data = {
        "version": __version__,
        "language": "python",
        "files_necessary": ["solution.py"],
        "questions": [
            {
                "name": "Q1",
                "marking_items": [
                    {
                        "target_file": "solution.py",
                        "total_mark": 10,
                        "type": "output_comparison",
                    }
                ],
            }
        ],
    }
    result = ag.Config(**data)
    assert result.version == __version__
    assert result.language == "python"
    assert len(result.questions) == 1


def test_get_example_config_yaml_python():
    yaml_str = ag.Config.get_example_config_yaml("py_simple")
    assert "language: python" in yaml_str


def test_get_example_config_yaml_java():
    yaml_str = ag.Config.get_example_config_yaml("java_simple")
    assert "language: java" in yaml_str


def test_validator_and_utility_functions():
    data = {
        "version": __version__,
        "language": "python",
        "files_necessary": ["solution.py"],
        "questions": [
            {
                "name": "Question 1",
                "marking_items": [
                    {
                        "target_file": "solution.py",
                        "total_mark": 10,
                        "type": "output_comparison",
                        "name": "check_exists",
                        "expected_output": "expected",
                    }
                ],
            }
        ],
    }
    validator = ag.Validator()
    assert validator.validate_json(data) is True
    assert len(validator.get_warnings()) == 0

    lint_res = ag.Validator.lint_config(data)
    assert lint_res["valid"] is True
    assert lint_res["quality_score"] == 100


def test_validator_output_comparison_no_command_warning():
    data = {
        "version": __version__,
        "language": "python",
        "required_files": ["solution.py"],
        "questions": [
            {
                "name": "Q1",
                "marking_items": [
                    {
                        "target_file": "solution.py",
                        "total_mark": 10,
                        "type": "output_comparison",
                        "name": "Hello Output Check",
                        "expected_output": "Hello World\n",
                    }
                ],
            }
        ],
    }
    validator = ag.Validator()
    assert validator.validate_json(data) is True
    assert len(validator.get_warnings()) == 0


def test_schema_includes_expected_output_script_mutual_exclusivity():
    schema = ag.Config.model_json_schema()
    marking_item_props = schema["$defs"]["MarkingItem"]["properties"]
    assert "expected_output_script" in marking_item_props
    assert "expected_output" in marking_item_props

    exp_out_desc = marking_item_props["expected_output"]["description"]
    exp_script_desc = marking_item_props["expected_output_script"]["description"]
    assert "Mutually exclusive with expected_output_script" in exp_out_desc
    assert "Mutually exclusive with expected_output" in exp_script_desc


def test_marking_item_mutual_exclusion_validation():
    with pytest.raises(ValidationError) as excinfo:
        ag.MarkingItem(
            target_file="solution.py",
            total_mark=10,
            type="output_comparison",
            expected_output="Hello",
            expected_output_script="print('Hello')",
        )
    assert "mutually exclusive" in str(excinfo.value)


def test_validator_mutual_exclusion_validation():
    data = {
        "version": __version__,
        "language": "python",
        "required_files": ["solution.py"],
        "questions": [
            {
                "name": "Q1",
                "marking_items": [
                    {
                        "target_file": "solution.py",
                        "total_mark": 10,
                        "type": "output_comparison",
                        "expected_output": "Hello",
                        "expected_output_script": "print('Hello')",
                    }
                ],
            }
        ],
    }
    validator = ag.Validator()
    assert validator.validate_json(data) is False
    assert any("mutually exclusive" in err for err in validator.get_errors())


def test_question_level_expected_output_script():
    schema = ag.Config.model_json_schema()
    question_props = schema["$defs"]["Question"]["properties"]
    assert "expected_output_script" in question_props

    config_dict = {
        "version": __version__,
        "language": "python",
        "required_files": ["solution.py"],
        "questions": [
            {
                "name": "Q1",
                "expected_output_script": "print(f'Hello {STUDENT_ID}')",
                "marking_items": [
                    {
                        "name": "Item 1",
                        "target_file": "solution.py",
                        "total_mark": 5,
                        "type": "output_comparison",
                    },
                    {
                        "name": "Item 2",
                        "target_file": "solution.py",
                        "total_mark": 5,
                        "type": "output_comparison",
                    },
                ],
            }
        ],
    }
    cfg = ag.Config.model_validate(config_dict)
    assert cfg.questions[0].expected_output_script == "print(f'Hello {STUDENT_ID}')"
    assert cfg.questions[0].marking_items[0].expected_output_script is None
    assert cfg.questions[0].marking_items[1].expected_output_script is None

    validator = ag.Validator()
    assert validator.validate_json(config_dict) is True


def test_question_level_expected_output_script_syntax_error():
    config_dict = {
        "version": __version__,
        "language": "python",
        "required_files": ["solution.py"],
        "questions": [
            {
                "name": "Q1",
                "expected_output_script": "print(def",
                "marking_items": [
                    {
                        "target_file": "solution.py",
                        "total_mark": 5,
                        "type": "output_comparison",
                    }
                ],
            }
        ],
    }
    validator = ag.Validator()
    assert validator.validate_json(config_dict) is False
    assert any("invalid expected_output_script syntax" in err for err in validator.get_errors())


def test_marking_item_function_return_comparison_and_signature_check():
    item_fn = ag.MarkingItem(
        target_file="solution.py",
        total_mark=10,
        type="function_return_comparison",
        function_name="calc",
    )
    assert item_fn.type == "function_return_comparison"

    item_sig = ag.MarkingItem(
        target_file="solution.py",
        total_mark=5,
        type="function_signature_check",
        function_name="calc",
    )
    assert item_sig.type == "function_signature_check"

    item_out = ag.MarkingItem(
        target_file="solution.py",
        total_mark=10,
        type="function_output_comparison",
        function_name="display",
    )
    assert item_out.type == "function_output_comparison"

    for legacy_type in ("function_test", "signature_check", "function_output_test"):
        with pytest.raises(ValidationError):
            ag.MarkingItem(
                target_file="solution.py",
                total_mark=10,
                type=legacy_type,
                function_name="calc",
            )
