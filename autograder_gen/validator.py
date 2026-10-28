import ast
import json
import re
import yaml
import zipfile
from io import BytesIO
from typing import List, Dict, Any, Union
from pathlib import Path
from autograder_gen.config import Config
from pydantic import ValidationError


class Validator:
    """Validates autograder configuration files using pydantic."""

    def __init__(self):
        self.errors = []
        self.warnings = []

    def validate_json(self, data: Dict[str, Any]) -> bool:
        """Validate configuration data against the schema. Returns True if valid."""
        self.errors.clear()
        self.warnings.clear()

        try:
            Config.model_validate(data)
            self._validate_custom_rules(data)

            if not self.errors:
                return True
            else:
                return False
        except ValidationError as e:
            for error in e.errors():
                loc = " -> ".join(str(loc_item) for loc_item in error["loc"])
                msg = error["msg"]
                self.errors.append(f"{loc}: {msg}")
            return False
        except Exception as e:
            self.errors.append(f"Unexpected error: {str(e)}")
            return False

    def validate_from_file(self, file_path: str) -> bool:
        """Validate a configuration file (YAML). Returns True if valid."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            data = yaml.safe_load(content)

            if not isinstance(data, dict):
                self.errors.append("YAML file must contain a top-level dictionary")
                return False

            return self.validate_json(data)
        except Exception as e:
            self.errors.append(f"Error reading file: {str(e)}")
            return False

    def _config_to_dict(self, config: Config) -> Dict[str, Any]:
        """Helper to convert config object to dict for validation."""
        if hasattr(config, "model_dump"):
            return config.model_dump()
        return dict(config)

    def _validate_custom_rules(self, data: Dict[str, Any]):
        """Perform additional custom validations not covered by Pydantic schema."""

        # Check total marks > 0
        total_marks = 0.0
        questions = data.get("questions", [])
        for q in questions:
            q_script = q.get("expected_output_script")
            if q_script:
                try:
                    compile(q_script, "<expected_output_script>", "exec")
                except SyntaxError as e:
                    self.errors.append(
                        f"Question '{q.get('name', 'unnamed')}' has invalid expected_output_script syntax: {e}"
                    )
            marking_items = q.get("marking_items", [])
            for item in marking_items:
                total_marks += float(item.get("total_mark", 0))

                # Custom check: program output test warning
                self._validate_program_output_test_warnings(item, q)
                self._validate_function_signature_test_warnings(item)
                self._validate_function_test(item)

        if total_marks <= 0:
            self.warnings.append(
                "Total marks for all questions is 0. Consider adding non-zero marks."
            )

        q_names = [q.get("name") for q in questions if q.get("name")]
        if len(q_names) != len(set(q_names)):
            self.warnings.append("Duplicate question names found.")

    def _validate_program_output_test_warnings(
        self, item: Dict[str, Any], question: Optional[Dict[str, Any]] = None
    ):
        """Check for potentially problematic program_output_test configurations."""
        item_type = item.get("type", "")
        if item_type == "program_output_test":
            expected = item.get("expected_output")
            expected_script = item.get("expected_output_script")
            q_script = question.get("expected_output_script") if question else None
            effective_script = expected_script or q_script
            if (
                expected is not None
                and str(expected).strip()
                and expected_script is not None
                and str(expected_script).strip()
            ):
                self.errors.append(
                    f"Output comparison item '{item.get('name', 'unnamed')}' specifies both expected_output and expected_output_script; they are mutually exclusive."
                )
            if expected is None and effective_script is None:
                self.warnings.append(
                    f"Output comparison item '{item.get('name', 'unnamed')}' has null expected_output"
                )
            if expected_script:
                try:
                    compile(expected_script, "<expected_output_script>", "exec")
                except SyntaxError as e:
                    self.errors.append(
                        f"Output comparison item '{item.get('name', 'unnamed')}' has invalid expected_output_script syntax: {e}"
                    )

    def _validate_function_signature_test_warnings(self, item: Dict[str, Any]):
        """Check for function_signature_test item configurations."""
        item_type = item.get("type", "")
        if item_type == "function_signature_test":
            target_func = item.get("function_name") or item.get("target_function", "")
            if not target_func:
                self.errors.append(
                    f"Signature check item '{item.get('name', 'unnamed')}' missing function_name"
                )

    def _validate_function_test(self, item: Dict[str, Any]):
        """Check function test specific fields."""
        item_type = item.get("type", "")
        if item_type in (
            "function_return_test",
            "function_output_test",
        ):
            target_func = item.get("function_name") or item.get("target_function", "")
            test_cases = item.get("test_cases", [])
            if not target_func:
                self.errors.append(
                    f"Function test item '{item.get('name', 'unnamed')}' missing function_name"
                )
            if not test_cases:
                self.warnings.append(
                    f"Function test item '{item.get('name', 'unnamed')}' has no test_cases defined"
                )
            for tc in test_cases:
                if not isinstance(tc, dict):
                    self.errors.append(
                        f"Function test item '{item.get('name', 'unnamed')}' contains invalid test_case structure"
                    )

    def get_errors(self) -> List[str]:
        return self.errors

    def get_warnings(self) -> List[str]:
        return self.warnings

    @classmethod
    def lint_config(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform linting and quality report checks on configuration dictionary."""
        validator = cls()
        is_valid = validator.validate_json(data)

        issues = []
        for err in validator.get_errors():
            issues.append({"level": "error", "message": err})
        for warn in validator.get_warnings():
            issues.append({"level": "warning", "message": warn})

        quality_score = 100
        quality_score -= len(validator.get_errors()) * 20
        quality_score -= len(validator.get_warnings()) * 5
        quality_score = max(0, min(100, quality_score))

        questions = data.get("questions", [])
        total_marks = 0.0
        for q in questions:
            for item in q.get("marking_items", []):
                total_marks += float(item.get("total_mark", 0))

        return {
            "valid": is_valid,
            "quality_score": quality_score,
            "total_marks": total_marks,
            "issues_summary": {
                "errors": len(validator.get_errors()),
                "warnings": len(validator.get_warnings()),
                "info": 0,
            },
            "issues": issues,
        }
