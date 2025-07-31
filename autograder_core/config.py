import json
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass, field

@dataclass
class MarkingItem:
    """Represents a single marking item within a question."""
    target_file: str
    total_mark: int
    type: str  # file_exists, output_comparison, signature_check, function_test
    time_limit: int = 30
    visibility: str = "visible"  # visible, hidden, after_due_date, after_published
    name: str = ""  # Optional name for the marking item
    expected_input: str = ""
    expected_output: str = ""
    
    # Function testing fields
    function_name: str = ""
    test_cases: List[Dict] = field(default_factory=list)
    
    # Signature checking fields
    expected_parameters: str = ""
    

@dataclass
class Question:
    """Represents a question with multiple marking items."""
    name: str
    marking_items: List[MarkingItem] = field(default_factory=list)

@dataclass
class AutograderConfig:
    """Complete autograder configuration."""
    version: str = "0"  # Changed to string to match schema
    questions: List[Question] = field(default_factory=list)
    global_time_limit: int = 300
    language: str = "python"  # python, java, r
    setup_commands: List[str] = field(default_factory=list)
    files_necessary: List[str] = field(default_factory=list)
    
class ConfigParser:
    """Parses JSON configuration files for autograder generation."""
    
    def __init__(self, config_path: str):
        self.config_path = Path(config_path)
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    def parse(self) -> AutograderConfig:
        """Parse the JSON configuration file."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return self._parse_config(data)
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in configuration file: {e}")
        except Exception as e:
            raise ValueError(f"Error parsing configuration: {e}")
    
    def parse_and_validate(self) -> AutograderConfig:
        """Parse the JSON configuration file with validation."""
        try:
            # Import here to avoid circular import
            from validator import ConfigValidator
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Validate first
            validator = ConfigValidator()
            if not validator.validate_json(data):
                errors = validator.get_errors()
                raise ValueError(f"Configuration validation failed: {'; '.join(errors)}")
            
            return self._parse_config(data)
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in configuration file: {e}")
        except Exception as e:
            raise ValueError(f"Error parsing configuration: {e}")
    
    def _parse_config(self, data: Dict[str, Any]) -> AutograderConfig:
        """Convert JSON data to AutograderConfig object."""
        config = AutograderConfig()
        
        # Parse global settings
        config.version = str(data.get('version', '0'))  # Ensure version is string
        config.global_time_limit = data.get('global_time_limit', 300)
        config.language = data.get('language', 'python')
        config.setup_commands = data.get('setup_commands', [])
        config.files_necessary = data.get('files_necessary', [])
        
        # Parse questions
        questions_data = data.get('questions', [])
        for i, q_data in enumerate(questions_data):
            question = Question(
                name=q_data.get('name', f'Question_{i+1}')
            )
            
            # Parse marking items
            marking_items_data = q_data.get('marking_items', [])
            for j, item_data in enumerate(marking_items_data):
                marking_item = MarkingItem(
                    target_file=item_data['target_file'],
                    total_mark=item_data['total_mark'],
                    type=item_data['type'],
                    time_limit=item_data.get('time_limit', 30),
                    visibility=item_data.get('visibility', 'visible'),
                    name=item_data.get('name', ''),
                    expected_input=item_data.get('expected_input', ''),
                    expected_output=item_data.get('expected_output', ''),
                    # Function testing fields
                    function_name=item_data.get('function_name', ''),
                    test_cases=item_data.get('test_cases', []),
                    # Signature checking fields
                    expected_parameters=item_data.get('expected_parameters', ''),
                )
                question.marking_items.append(marking_item)
            
            config.questions.append(question)
        
        return config
