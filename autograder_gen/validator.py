import json
import yaml
from typing import List, Dict, Any
from autograder_gen.config import AutograderConfig, ConfigParser
from pydantic import ValidationError


class ConfigValidator:
    """Validates autograder configuration files using pydantic."""

    def __init__(self):
        self.errors = []
        self.warnings = []

    def validate_json(self, data: Dict[str, Any]) -> bool:
        """Validate configuration data against the schema. Returns True if valid."""
        self.errors.clear()
        self.warnings.clear()

        try:
            from autograder_gen.config import AutograderConfigModel

            AutograderConfigModel.model_validate(data)

            # Additional custom validations (warnings only since errors are native)
            self._validate_custom_rules(data)

            return len(self.errors) == 0

        except ValidationError as e:
            for error in e.errors():
                loc = ".".join(map(str, error["loc"]))
                self.errors.append(f"{error['msg']} at {loc}")
            return False

    def validate_from_file(self, file_path: str) -> bool:
        """Validate configuration directly from YAML file."""
        try:
            parser = ConfigParser(file_path)
            parser.parse()  # This will raise ValidationError if invalid
            return True
        except ValidationError as e:
            for error in e.errors():
                loc = ".".join(map(str, error["loc"]))
                self.errors.append(f"{error['msg']} at {loc}")
            return False
        except (ValueError, FileNotFoundError) as e:
            self.errors.append(str(e))
            return False

    def _config_to_dict(self, config: AutograderConfig) -> Dict[str, Any]:
        """Convert AutograderConfig object to dictionary."""
        return {
            "version": config.version,
            "language": config.language,
            "global_time_limit": config.global_time_limit,
            "setup_commands": config.setup_commands,
            "files_necessary": config.files_necessary,
            "questions": [
                {
                    "name": q.name,
                    "marking_items": [
                        {
                            "target_file": item.target_file,
                            "total_mark": item.total_mark,
                            "type": item.type,
                            "time_limit": item.time_limit,
                            "visibility": item.visibility,
                            "name": item.name,
                            "expected_input": item.expected_input,
                            "expected_output": item.expected_output,
                            "function_name": item.function_name,
                            "expected_parameters": item.expected_parameters,
                            "expected_return_type": item.expected_return_type,
                            "test_cases": item.test_cases,
                        }
                        for item in q.marking_items
                    ],
                }
                for q in config.questions
            ],
        }

    def _validate_custom_rules(self, data: Dict[str, Any]):
        """Perform additional custom validations not covered by JSON schema."""
        # Check for warnings about time limits
        global_time_limit = data.get("global_time_limit", 300)
        if global_time_limit > 3600:
            self.warnings.append("Global time limit is very high (>1 hour)")

        # Get list of necessary files
        files_necessary = data.get("files_necessary", [])

        # Check questions
        questions = data.get("questions", [])
        question_names = []

        for i, question in enumerate(questions):
            question_name = question.get("name", "")

            # Check for duplicate question names
            if question_name in question_names:
                self.warnings.append(f"Duplicate question name: '{question_name}'")
            question_names.append(question_name)

            # Check marking items
            marking_items = question.get("marking_items", [])
            total_marks = 0

            for j, item in enumerate(marking_items):
                total_marks += item.get("total_mark", 0)

                # Check time limits
                time_limit = item.get("time_limit", 30)
                if time_limit > 300:
                    self.warnings.append(
                        f"Question '{question_name}', Item {j+1}: "
                        f"Time limit is very high ({time_limit}s)"
                    )

                # Type-specific validations
                item_type = item.get("type")
                if item_type == "output_comparison":
                    self._validate_output_comparison_warnings(
                        item, question_name, j + 1
                    )
                elif item_type == "signature_check":
                    self._validate_signature_check_warnings(item, question_name, j + 1)
                elif item_type == "function_test":
                    self._validate_function_test(item, question_name, j + 1)

            # Check total marks
            if total_marks == 0:
                self.warnings.append(f"Question '{question_name}': Total marks is 0")
            elif total_marks > 100:
                self.warnings.append(
                    f"Question '{question_name}': Total marks is very high ({total_marks})"
                )

    def _validate_output_comparison_warnings(
        self, item: Dict[str, Any], question_name: str, item_num: int
    ):
        """Generate warnings for output comparison items."""
        context = f"Question '{question_name}', Item {item_num}"

        if not item.get("expected_output"):
            self.warnings.append(f"{context}: Expected output is empty")

    def _validate_signature_check_warnings(
        self, item: Dict[str, Any], question_name: str, item_num: int
    ):
        """Generate warnings for signature check items."""
        context = f"Question '{question_name}', Item {item_num}"

        if item.get("expected_input") or item.get("expected_output"):
            self.warnings.append(
                f"{context}: expected_input/expected_output not needed for signature check"
            )

    def _validate_function_test(
        self, item: Dict[str, Any], question_name: str, item_num: int
    ):
        """Generate warnings for function test items."""
        context = f"Question '{question_name}', Item {item_num}"

        test_cases = item.get("test_cases", [])
        if not test_cases:
            self.warnings.append(
                f"{context}: No test cases provided for function testing"
            )

        for i, test_case in enumerate(test_cases):
            if not test_case.get("expected") and not test_case.get("should_raise"):
                self.warnings.append(
                    f"{context}: Test case {i+1} has no expected value or exception"
                )

    def get_errors(self) -> List[str]:
        """Get validation errors."""
        return self.errors.copy()

    def get_warnings(self) -> List[str]:
        """Get validation warnings."""
        return self.warnings.copy()

    def get_detailed_errors(self) -> List[Dict[str, Any]]:
        """Get detailed validation errors."""
        detailed = []
        for err in self.errors:
            detailed.append({"message": err})
        return detailed
