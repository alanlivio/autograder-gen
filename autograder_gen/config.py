import yaml
from pathlib import Path
from typing import Dict, List, Any
from pydantic import BaseModel, Field, field_validator, model_validator, ValidationError


class MarkingItemModel(BaseModel):
    """Represents a single marking item within a question."""

    target_file: str
    total_mark: int
    type: str
    time_limit: int = 30
    visibility: str = "visible"
    name: str = ""
    expected_input: str = ""
    expected_output: str = ""

    # Function testing fields
    function_name: str = ""
    test_cases: List[Dict[str, Any]] = Field(default_factory=list)

    # Signature checking fields
    expected_parameters: str = ""
    expected_return_type: str = ""

    @field_validator("type")
    @classmethod
    def check_type(cls, v: str) -> str:
        allowed = {
            "file_exists",
            "output_comparison",
            "signature_check",
            "function_test",
        }
        if v not in allowed:
            raise ValueError(f"type must be one of: {allowed}")
        return v

    @field_validator("visibility")
    @classmethod
    def check_visibility(cls, v: str) -> str:
        allowed = {"visible", "hidden", "after_due_date", "after_published"}
        if v not in allowed:
            raise ValueError(f"visibility must be one of: {allowed}")
        return v

    @model_validator(mode="after")
    def validate_type_fields(self) -> "MarkingItemModel":
        if self.type == "function_test" and not self.function_name:
            raise ValueError("function_name is required for function_test")
        return self


class QuestionModel(BaseModel):
    """Represents a question with multiple marking items."""

    name: str
    marking_items: List[MarkingItemModel] = Field(min_length=1)


class AutograderConfigModel(BaseModel):
    """Complete autograder configuration."""

    version: str
    language: str
    global_time_limit: int = 300
    setup_commands: List[str] = Field(default_factory=list)
    files_necessary: List[str] = Field(default_factory=list)
    questions: List[QuestionModel] = Field(min_length=1)

    @field_validator("language")
    @classmethod
    def check_language(cls, v: str) -> str:
        allowed = {"python", "java"}
        if v not in allowed:
            raise ValueError(f"language must be one of: {allowed}")
        return v

    @model_validator(mode="after")
    def validate_target_files(self) -> "AutograderConfigModel":
        for i, q in enumerate(self.questions):
            for j, item in enumerate(q.marking_items):
                target = item.target_file
                if target and target not in self.files_necessary:
                    raise ValueError(
                        f"Question '{q.name}', Item {j+1}: Target file '{target}' is not listed in 'files_necessary'"
                    )
        return self


AutograderConfig = AutograderConfigModel
Question = QuestionModel
MarkingItem = MarkingItemModel


class ConfigParser:
    """Parses YAML configuration files for autograder generation."""

    def __init__(self, config_path: str):
        self.config_path = Path(config_path)
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

    def parse(self) -> AutograderConfig:
        """Parse the configuration file (YAML only)."""
        if self.config_path.suffix.lower() not in [".yaml", ".yml"]:
            raise ValueError("Only YAML format (.yml, .yaml) is supported.")

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            return AutograderConfig.model_validate(data)

        except yaml.YAMLError as e:
            raise ValueError(f"Invalid format in YAML configuration file: {e}")
        except ValidationError as e:
            # We let ValidationError bubble up
            raise e
        except Exception as e:
            raise ValueError(f"Error parsing configuration: {e}")

    def parse_and_validate(self) -> AutograderConfig:
        """Parse and validate the configuration file."""
        return self.parse()
