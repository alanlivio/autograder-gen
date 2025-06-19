"""
Configuration validation module for autograder JSON files.
"""

from typing import List, Dict, Any
from config_parser import AutograderConfig, Question, MarkingItem

class ConfigValidator:
    """Validates autograder configuration files."""
    
    SUPPORTED_LANGUAGES = ['python', 'java', 'r', 'cpp', 'c']
    SUPPORTED_TYPES = [0, 1, 2]  # file_exists, output_comparison, signature_check
    
    def __init__(self):
        self.errors = []
        self.warnings = []
    
    def validate(self, config: AutograderConfig) -> bool:
        """Validate the complete configuration. Returns True if valid."""
        self.errors.clear()
        self.warnings.clear()
        
        self._validate_global_settings(config)
        self._validate_questions(config.questions)
        
        return len(self.errors) == 0
    
    def get_errors(self) -> List[str]:
        """Get validation errors."""
        return self.errors.copy()
    
    def get_warnings(self) -> List[str]:
        """Get validation warnings."""
        return self.warnings.copy()
    
    def _validate_global_settings(self, config: AutograderConfig):
        """Validate global configuration settings."""
        # Language validation
        if config.language not in self.SUPPORTED_LANGUAGES:
            self.errors.append(
                f"Unsupported language '{config.language}'. "
                f"Supported languages: {', '.join(self.SUPPORTED_LANGUAGES)}"
            )
        
        # Time limit validation
        if config.global_time_limit <= 0:
            self.errors.append("Global time limit must be positive")
        elif config.global_time_limit > 3600:  # 1 hour
            self.warnings.append("Global time limit is very high (>1 hour)")
        
        # Setup commands validation
        if config.setup_commands:
            for i, cmd in enumerate(config.setup_commands):
                if not isinstance(cmd, str) or not cmd.strip():
                    self.errors.append(f"Setup command {i+1} is empty or invalid")
    
    def _validate_questions(self, questions: List[Question]):
        """Validate all questions."""
        if not questions:
            self.errors.append("At least one question is required")
            return
        
        question_names = []
        for i, question in enumerate(questions):
            self._validate_question(question, i+1)
            
            # Check for duplicate question names
            if question.name in question_names:
                self.warnings.append(f"Duplicate question name: '{question.name}'")
            question_names.append(question.name)
    
    def _validate_question(self, question: Question, question_num: int):
        """Validate a single question."""
        context = f"Question {question_num} ('{question.name}')"
        
        # Name validation
        if not question.name or not question.name.strip():
            self.errors.append(f"{context}: Question name cannot be empty")
        
        # Marking items validation
        if not question.marking_items:
            self.errors.append(f"{context}: At least one marking item is required")
            return
        
        total_marks = 0
        target_files = []
        
        for j, item in enumerate(question.marking_items):
            item_context = f"{context}, Item {j+1}"
            self._validate_marking_item(item, item_context)
            total_marks += item.total_mark
            
            if item.target_file:
                target_files.append(item.target_file)
        
        # Check total marks
        if total_marks == 0:
            self.warnings.append(f"{context}: Total marks is 0")
        elif total_marks > 100:
            self.warnings.append(f"{context}: Total marks is very high ({total_marks})")
        
    
    def _validate_marking_item(self, item: MarkingItem, context: str):
        """Validate a single marking item."""
        # Target file validation
        if not item.target_file or not item.target_file.strip():
            self.errors.append(f"{context}: Target file cannot be empty")
        
        # Mark validation
        if item.total_mark < 0:
            self.errors.append(f"{context}: Total mark cannot be negative")
        elif item.total_mark == 0:
            self.warnings.append(f"{context}: Total mark is 0")
        
        # Type validation
        if item.type not in self.SUPPORTED_TYPES:
            self.errors.append(
                f"{context}: Invalid type {item.type}. "
                f"Supported types: {self.SUPPORTED_TYPES}"
            )
        if item.visibility not in ['visible', 'hidden', 'after_due_date', 'after_published' ]:
            self.errors.append(f"{context}: Invalid visibility '{item.visibility}'. Must be 'visible','hidden','after_due_date' or 'after_published'")

        # Time limit validation
        if item.time_limit <= 0:
            self.errors.append(f"{context}: Time limit must be positive")
        elif item.time_limit > 300:  # 5 minutes
            self.warnings.append(f"{context}: Time limit is very high (>{item.time_limit}s)")
        
        # Type-specific validation
        if item.type == 1:  # output_comparison
            self._validate_output_comparison(item, context)
        elif item.type == 2:  # signature_check
            self._validate_signature_check(item, context)
    
    def _validate_output_comparison(self, item: MarkingItem, context: str):
        """Validate output comparison specific fields."""
        if not item.expected_output:
            self.warnings.append(f"{context}: Expected output is empty")
        
        # Check if both expected_input and reference_file are provided
        if item.expected_input and item.reference_file:
            self.warnings.append(
                f"{context}: Both expected_input and reference_file provided. "
                "expected_input will be used."
            )
        
    
    def _validate_signature_check(self, item: MarkingItem, context: str):
        """Validate signature check specific fields."""
        # For signature checks, we don't need input/output
        if item.expected_input or item.expected_output:
            self.warnings.append(
                f"{context}: expected_input/expected_output not needed for signature check"
            )
        
        # Check file extension matches language expectations
        if item.target_file:
            extension = item.target_file.split('.')[-1].lower() if '.' in item.target_file else ''
            # This validation could be enhanced based on specific requirements
