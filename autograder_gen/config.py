import yaml
from pathlib import Path
from typing import Dict, List, Any
from pydantic import BaseModel, Field, field_validator, model_validator, ValidationError


class MarkingItem(BaseModel):
    """Represents a single marking item within a question."""

    target_file: str = Field(default="", title="Target File")
    total_mark: float = Field(ge=0, title="Points", description="Score awarded for this marking item.")
    type: str = Field(
        default="output_comparison",
        title="Test Type",
        json_schema_extra={
            "enum": [
                "output_comparison",
                "signature_check",
                "function_test",
                "gitlab_submission_exists",
                "github_submission_exists",
                "manual_review",
            ]
        },
    )
    time_limit: int = Field(default=30, ge=1, title="Time Limit (s)")
    visibility: str = Field(
        default="visible",
        title="Visibility",
        json_schema_extra={
            "enum": [
                "visible",
                "hidden",
                "after_due_date",
                "after_published",
            ]
        },
    )
    name: str = Field(default="", title="Display Name")
    expected_input: str = Field(default="", title="Standard Input")
    expected_output: str = Field(default="", title="Expected Output")

    # Function testing fields
    function_name: str = Field(default="", title="Function Name")
    test_cases: List[Dict[str, Any]] = Field(default_factory=list, title="Test Cases")

    # Signature checking fields
    expected_parameters: str = Field(default="", title="Expected Parameters")
    expected_return_type: str = Field(default="", title="Expected Return Type")

    @field_validator("type")
    @classmethod
    def check_type(cls, v: str) -> str:
        allowed = {
            "output_comparison",
            "signature_check",
            "function_test",
            "gitlab_submission_exists",
            "github_submission_exists",
            "manual_review",
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
    def validate_type_fields(self) -> "MarkingItem":
        if (
            self.type not in ("output_comparison", "function_test")
            and "time_limit" in self.model_fields_set
        ):
            raise ValueError(f"time_limit is not allowed for type '{self.type}'")
        if self.type == "function_test" and not self.function_name:
            raise ValueError("function_name is required for function_test")
        if (
            self.type
            not in ("gitlab_submission_exists", "github_submission_exists", "manual_review")
            and not self.target_file
        ):
            raise ValueError(f"target_file is required for type '{self.type}'")
        return self


class Question(BaseModel):
    """Represents a question with multiple marking items."""

    name: str = Field(title="Question Name")
    description: str = Field(default="", title="Description (for documentation)")
    strict_float: bool = Field(default=False, title="Strict Float Comparison")
    manual_review: bool = Field(default=False, title="Manual Review Question")
    marking_items: List[MarkingItem] = Field(min_length=1, title="Marking Items")

    @model_validator(mode="before")
    @classmethod
    def handle_manual_review_question(cls, data: Any) -> Any:
        if isinstance(data, dict) and data.get("manual_review"):
            if not data.get("marking_items"):
                data["marking_items"] = [
                    {
                        "name": data.get("name", "Manual Review"),
                        "total_mark": data.get("total_mark", 0.0),
                        "type": "manual_review",
                        "target_file": data.get("target_file", ""),
                    }
                ]
            else:
                for item in data.get("marking_items", []):
                    if isinstance(item, dict) and not item.get("type"):
                        item["type"] = "manual_review"
        return data


DEFAULT_LANGUAGE_RUNTIMES: Dict[str, Dict[str, str]] = {
    "python": {
        "title": "Default Environment: Python 3",
        "name": "Python",
        "version": "Python 3.10",
        "package": "python3 / python3-dev",
        "details": (
            "Gradescope's default Ubuntu environment (22.04 LTS) provisions system "
            "Python 3.10 (via python3 / python3-dev) and gradescope-utils. "
            "Specify custom Python versions or packages in setup_commands."
        ),
        "html_details": (
            "Gradescope's default Ubuntu environment (22.04 LTS) provisions system "
            "<strong>Python 3.10</strong> (via <code>python3</code> / <code>python3-dev</code>) "
            "and <code>gradescope-utils</code>."
        ),
    },
    "java": {
        "title": "Default Environment: Java (OpenJDK 25)",
        "name": "Java",
        "version": "OpenJDK 25",
        "package": "openjdk-25-jdk",
        "details": (
            "Gradescope's default Ubuntu environment provisions OpenJDK 25 via "
            "openjdk-25-jdk. "
            "Custom JDK versions or compilation flags can be specified in setup_commands."
        ),
        "html_details": (
            "Gradescope's default Ubuntu environment provisions "
            "<strong>OpenJDK 25</strong> via <code>openjdk-25-jdk</code>."
        ),
    },
}

DEFAULT_RUNTIME_SUMMARY = (
    "Gradescope autograder containers run on Ubuntu (Ubuntu 22.04 LTS by default). "
    "By default, Python assessments run on system Python 3 (Python 3.10) with python3-dev "
    "and gradescope-utils, and Java assessments run on OpenJDK 25 via openjdk-25-jdk. "
    "Custom versions can be configured via setup_commands."
)

DEFAULT_RUNTIME_TIP = (
    "If you require a different Python or Java version (such as Python 3.11/3.12 or OpenJDK 17/21), "
    "add custom installation steps in the setup_commands list."
)


class Config(BaseModel):
    """Complete autograder configuration."""

    version: str = Field(default="0.1", title="Version")
    language: str = Field(
        default="python",
        title="Language",
        description=DEFAULT_RUNTIME_SUMMARY,
        json_schema_extra={"enum": ["python", "java"]},
    )
    global_time_limit: int = Field(default=300, ge=1, title="Global Time Limit (ms)")
    strict_file_location: bool = Field(default=False, title="Strict File Location")
    remove_use_of_java_package: bool = Field(default=False, title="Remove Java Package Declarations")
    retrieve_student_id: bool = Field(default=False, title="Retrieve Student ID")
    wrong_file_location_deduction: float = Field(
        default=0.0,
        title="Wrong File Location Deduction",
        json_schema_extra={"minimum": 0.0, "maximum": 1.0},
    )
    setup_commands: List[str] = Field(default_factory=list, title="Setup Commands")
    required_files: List[str] = Field(default_factory=list, title="Required Files")
    questions: List[Question] = Field(min_length=1, title="Questions")

    @field_validator("wrong_file_location_deduction")
    @classmethod
    def check_wrong_file_location_deduction(cls, v: float) -> float:
        if v < 0.0 or v > 1.0:
            raise ValueError("wrong_file_location_deduction must be between 0.0 and 1.0")
        return v

    @model_validator(mode="before")
    @classmethod
    def handle_required_files_backwards_compat(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "required_files" not in data or not data["required_files"]:
                if "src_files" in data and data["src_files"]:
                    data["required_files"] = data["src_files"]
                elif "files_necessary" in data and data["files_necessary"]:
                    data["required_files"] = data["files_necessary"]
            if "src_files" not in data and "required_files" in data:
                data["src_files"] = data["required_files"]
            if "files_necessary" not in data and "required_files" in data:
                data["files_necessary"] = data["required_files"]
        return data

    @property
    def files_necessary(self) -> List[str]:
        return self.required_files

    @property
    def src_files(self) -> List[str]:
        return self.required_files

    @field_validator("language")
    @classmethod
    def check_language(cls, v: str) -> str:
        allowed = {"python", "java"}
        if v not in allowed:
            raise ValueError(f"language must be one of: {allowed}")
        return v

    @model_validator(mode="after")
    def validate_target_files(self) -> "Config":
        for i, q in enumerate(self.questions):
            for j, item in enumerate(q.marking_items):
                target = item.target_file
                if target and target not in self.required_files:
                    raise ValueError(
                        f"Question '{q.name}', Item {j+1}: Target file '{target}' is not listed in 'required_files'"
                    )
        return self

    @model_validator(mode="after")
    def validate_wrong_file_location_deduction(self) -> "Config":
        if self.strict_file_location and self.wrong_file_location_deduction > 0:
            raise ValueError(
                "wrong_file_location_deduction is only supported when strict_file_location is False"
            )
        return self

    @model_validator(mode="after")
    def auto_enable_retrieve_student_id(self) -> "Config":
        if not self.retrieve_student_id:
            for q in self.questions:
                for item in q.marking_items:
                    for ph in ("<STUDENT_ID>", "<student_id>"):
                        if (item.expected_output and ph in item.expected_output) or (
                            item.expected_input and ph in item.expected_input
                        ):
                            self.retrieve_student_id = True
                            return self
        return self


    @property
    def total_score(self) -> float:
        return sum(item.total_mark for q in self.questions for item in q.marking_items)

    def get_config_summary(self) -> Dict[str, Any]:
        total_items = 0
        total_marks = 0.0
        visibility_counts: Dict[str, int] = {}
        for q in self.questions:
            for item in q.marking_items:
                total_items += 1
                total_marks += item.total_mark
                vis = item.visibility
                visibility_counts[vis] = visibility_counts.get(vis, 0) + 1

        return {
            "version": self.version,
            "language": self.language,
            "global_time_limit": self.global_time_limit,
            "total_questions": len(self.questions),
            "total_marking_items": total_items,
            "total_marks": total_marks,
            "retrieve_student_id": self.retrieve_student_id,
            "required_files": self.required_files,
            "src_files": self.required_files,
            "files_necessary": self.required_files,
            "visibility_counts": visibility_counts,
        }

    @staticmethod
    def get_example_config_yaml(name: str = "py_simple") -> str:
        """Return example YAML configuration content by example name."""
        key_map = {
            "py_simple": "py_simple",
            "py_function": "py_function",
            "py_complete": "py_complete",
            "java_simple": "java_simple",
        }
        example_key = key_map.get(name.lower(), "py_simple")

        repo_example_path = (
            Path(__file__).parent.parent / "tests" / "examples" / example_key / "config.yaml"
        )
        if repo_example_path.exists():
            with open(repo_example_path, "r", encoding="utf-8") as f:
                return f.read()

        pkg_example_path = Path(__file__).parent / "examples" / example_key / "config.yaml"
        if pkg_example_path.exists():
            with open(pkg_example_path, "r", encoding="utf-8") as f:
                return f.read()

        raise FileNotFoundError(f"Example configuration file not found for example '{name}'")

    @staticmethod
    def parse(config_path: Any) -> "Config":
        """Parse the configuration file (YAML only)."""
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        if path.suffix.lower() not in [".yaml", ".yml"]:
            raise ValueError("Only YAML format (.yml, .yaml) is supported.")

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            return Config.model_validate(data)

        except yaml.YAMLError as e:
            raise ValueError(f"Invalid format in YAML configuration file: {e}")
        except ValidationError as e:
            raise e
        except Exception as e:
            raise ValueError(f"Error parsing configuration: {e}")

    @classmethod
    def normalize(cls, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize configuration data dictionary."""
        model = cls.model_validate(config_data)
        dump = model.model_dump()
        dump["setup_commands"] = [
            cmd.strip() for cmd in dump.get("setup_commands", []) if cmd and cmd.strip()
        ]
        dump["required_files"] = [
            f.strip() for f in dump.get("required_files", []) if f and f.strip()
        ]
        dump["src_files"] = dump["required_files"]
        dump["files_necessary"] = dump["required_files"]
        return dump


def normalize_autograder_config(config_data: Dict[str, Any]) -> Dict[str, Any]:
    return Config.normalize(config_data)


if __name__ == "__main__":
    import json

    print(json.dumps(MarkingItem.model_json_schema(), indent=2))
