"""
Configuration validation module for autograder JSON files using JSON Schema.
"""

import json
from typing import List, Dict, Any
from jsonschema import validate, ValidationError, Draft7Validator
from cli.src.config_parser import AutograderConfig


class ConfigValidator:
    """Validates autograder configuration files using JSON Schema."""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.schema = self._get_schema()
        self.validator = Draft7Validator(self.schema)
    
    def _get_schema(self) -> Dict[str, Any]:
        """Define the JSON schema for autograder configuration."""
        return {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "required": ["version", "language", "questions"],
            "properties": {
                "version": {
                    "type": "string",
                    "description": "Configuration version"
                },
                "language": {
                    "type": "string",
                    "enum": ["python"],
                    "description": "Programming languages supported by the autograder"
                },
                "global_time_limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 36000,
                    "default": 3000,
                    "description": "Global time limit in milliseconds"
                },
                "setup_commands": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "minLength": 1
                    },
                    "description": "List of setup commands to run"
                },
                "files_necessary": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "minLength": 1
                    },
                    "description": "List of necessary files"
                },
                "questions": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "$ref": "#/definitions/question"
                    },
                    "description": "List of questions"
                }
            },
            "definitions": {
                "question": {
                    "type": "object",
                    "required": ["name", "marking_items"],
                    "properties": {
                        "name": {
                            "type": "string",
                            "minLength": 1,
                            "description": "Question name"
                        },
                        "marking_items": {
                            "type": "array",
                            "minItems": 1,
                            "items": {
                                "$ref": "#/definitions/marking_item"
                            },
                            "description": "List of marking items"
                        }
                    }
                },
                "marking_item": {
                    "type": "object",
                    "required": ["target_file", "total_mark", "type"],
                    "properties": {
                        "target_file": {
                            "type": "string",
                            "minLength": 1,
                            "description": "Target file to be tested"
                        },
                        "total_mark": {
                            "type": "integer",
                            "minimum": 0,
                            "description": "Total marks for this item"
                        },
                        "type": {
                            "type": "string",
                            "enum": ["file_exists", "output_comparison", "signature_check", "function_test", "class_test"],
                            "description": "Type of test to generate"
                        },
                        "time_limit": {
                            "type": "integer",
                            "minimum": 1,
                            "default": 30,
                            "description": "Time limit in seconds"
                        },
                        "visibility": {
                            "type": "string",
                            "enum": ["visible", "hidden", "after_due_date", "after_published"],
                            "default": "visible",
                            "description": "Visibility of test results"
                        },
                        "expected_input": {
                            "type": "string",
                            "description": "Input for output comparison tests"
                        },
                        "expected_output": {
                            "type": "string",
                            "description": "Expected output for comparison tests"
                        },
                        "reference_file": {
                            "type": "string",
                            "description": "Reference file for comparison"
                        },
                        "function_name": {
                            "type": "string",
                            "description": "Name of function to test (for function_test type)"
                        },
                        "test_cases": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "args": {
                                        "type": "array",
                                        "description": "Positional arguments for function call"
                                    },
                                    "kwargs": {
                                        "type": "object",
                                        "description": "Keyword arguments for function call"
                                    },
                                    "expected": {
                                        "type": "string",
                                        "description": "Expected return value as string"
                                    }
                                },
                                "required": ["expected"],
                                "additionalProperties": False
                            },
                            "description": "Test cases for function testing"
                        }
                    }
                }
            }
        }
    
    def validate_json(self, data: Dict[str, Any]) -> bool:
        """Validate JSON data against the schema. Returns True if valid."""
        self.errors.clear()
        self.warnings.clear()
        
        try:
            # Primary schema validation
            validate(instance=data, schema=self.schema)
            
            # Additional custom validations
            self._validate_custom_rules(data)
            
            return len(self.errors) == 0
            
        except ValidationError as e:
            self.errors.append(f"Schema validation error: {e.message}")
            if e.absolute_path:
                path = ".".join(str(p) for p in e.absolute_path)
                self.errors[-1] += f" at path: {path}"
            return False
    
    def validate_from_file(self, file_path: str) -> bool:
        """Validate configuration directly from JSON file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return self.validate_json(data)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            self.errors.append(f"File error: {e}")
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
                            "expected_input": item.expected_input,
                            "expected_output": item.expected_output,
                            "reference_file": item.reference_file,
                            "function_name": item.function_name,
                            "test_cases": item.test_cases,

                        }
                        for item in q.marking_items
                    ]
                }
                for q in config.questions
            ]
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
                
                # Check if target file is in files_necessary
                target_file = item.get("target_file", "")
                if target_file and target_file not in files_necessary:
                    self.warnings.append(
                        f"Question '{question_name}', Item {j+1}: "
                        f"Target file '{target_file}' is not listed in 'files_necessary'"
                    )
                
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
                    self._validate_output_comparison_warnings(item, question_name, j+1)
                elif item_type == "signature_check":
                    self._validate_signature_check_warnings(item, question_name, j+1)
                elif item_type == "function_test":
                    self._validate_function_test_warnings(item, question_name, j+1)
            
            # Check total marks
            if total_marks == 0:
                self.warnings.append(f"Question '{question_name}': Total marks is 0")
            elif total_marks > 100:
                self.warnings.append(
                    f"Question '{question_name}': Total marks is very high ({total_marks})"
                )
    
    def _validate_output_comparison_warnings(self, item: Dict[str, Any], question_name: str, item_num: int):
        """Generate warnings for output comparison items."""
        context = f"Question '{question_name}', Item {item_num}"
        
        if not item.get("expected_output"):
            self.warnings.append(f"{context}: Expected output is empty")
        
        if item.get("expected_input") and item.get("reference_file"):
            self.warnings.append(
                f"{context}: Both expected_input and reference_file provided. "
                "expected_input will be used."
            )
    
    def _validate_signature_check_warnings(self, item: Dict[str, Any], question_name: str, item_num: int):
        """Generate warnings for signature check items."""
        context = f"Question '{question_name}', Item {item_num}"
        
        if item.get("expected_input") or item.get("expected_output"):
            self.warnings.append(
                f"{context}: expected_input/expected_output not needed for signature check"
            )
    
    def _validate_function_test_warnings(self, item: Dict[str, Any], question_name: str, item_num: int):
        """Generate warnings for function test items."""
        context = f"Question '{question_name}', Item {item_num}"
        
        if not item.get("function_name"):
            self.warnings.append(f"{context}: function_name is required for function_test")
        
        test_cases = item.get("test_cases", [])
        if not test_cases:
            self.warnings.append(f"{context}: No test cases provided for function testing")
        
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
        """Get detailed validation errors with paths and suggestions."""
        detailed_errors = []
        
        for error in self.validator.iter_errors({}):
            detailed_errors.append({
                "message": error.message,
                "path": list(error.absolute_path),
                "invalid_value": error.instance,
                "schema_path": list(error.schema_path),
            })
        
        return detailed_errors
