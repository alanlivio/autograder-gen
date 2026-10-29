import os
import shutil
import zipfile
import tempfile
from typing import Optional, List, Dict, Any, Union
import yaml
import json
import re
from types import SimpleNamespace
from pathlib import Path
from io import BytesIO
from jinja2 import Environment, FileSystemLoader, select_autoescape
from autograder_gen.config import Config
from autograder_gen.logger import print_error, print_success, print_warning
from autograder_gen.utils_description import generate_description_docx_buffer
from autograder_gen.utils_readme import (
    generate_description_md,
    generate_readme_md,
)
from autograder_gen.utils_python import (
    generate_python_skeleton,
    python_compiler_error_content,
)
from autograder_gen.utils_java import (
    generate_java_skeleton,
    java_compiler_error_content,
)


class AutograderGen:
    """Generates Gradescope autograder packages from configuration using Jinja templates."""

    def __init__(
        self,
        config: Config,
        original_config_dict: Optional[dict] = None,
        base_dir: Optional[Union[Path, str]] = None,
    ):
        """
        Initialize generator with configuration.
        Args:
            config: Config object
            original_config_dict: Optional dictionary of original unparsed YAML configuration
            base_dir: Optional base directory for locating extra files (defaults to current working directory)
        """
        self.config = config
        self.original_config_dict = original_config_dict
        self.base_dir = Path(base_dir) if base_dir is not None else Path.cwd()
        self.temp_dir: Optional[Path] = None
        self.templates_dir = Path(__file__).parent / "templates"
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self.retrieve_student_id: bool = any(
            bool(getattr(q, "expected_output_script", None))
            or any(bool(getattr(item, "expected_output_script", None)) for item in q.marking_items)
            for q in self.config.questions
        )

    def generate(
        self,
        output_dir: str,
        description: bool = False,
        generate_description: bool | None = None,
    ) -> str:
        """Generate the autograder.zip file using Jinja templates."""
        if generate_description is not None:
            description = generate_description
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        self.temp_dir = output_path / "temp_autograder"
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
        self.temp_dir.mkdir()
        try:
            self._generate_setup_sh()
            self._generate_run_autograder()
            self._generate_run_tests()
            self._generate_metadata_files()

            zip_path = output_path / "autograder.zip"
            self._create_zip(zip_path)
            verification = self.verify_autograder_zip(zip_path)
            for err in verification.get("errors", []):
                print_error(err)
            for warn in verification.get("warnings", []):
                print_warning(warn)
            if description:
                docx_buffer = self.generate_description_docx()
                with open(output_path / "description.docx", "wb") as f:
                    f.write(docx_buffer.getbuffer())
            correct_buffer = self.generate_correct_answer_zip()
            with open(output_path / "stub_correct_answer.zip", "wb") as f:
                f.write(correct_buffer.getbuffer())
            wrong_buffer = self.generate_wrong_answer_zip()
            with open(output_path / "stub_wrong_answer.zip", "wb") as f:
                f.write(wrong_buffer.getbuffer())
            compiler_buffer = self.generate_compiler_error_zip()
            with open(output_path / "stub_compiler_error.zip", "wb") as f:
                f.write(compiler_buffer.getbuffer())
            wrong_loc_buffer = self.generate_wrong_file_location_zip()
            with open(output_path / "stub_correct_answer_wrong_location.zip", "wb") as f:
                f.write(wrong_loc_buffer.getbuffer())
            return str(zip_path)
        finally:
            if self.temp_dir and self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)

    def verify_autograder_zip(self, zip_source: Any = None) -> Dict[str, Any]:
        """Verify structure and validity of an autograder.zip archive."""
        errors = []
        warnings = []
        checks = []
        try:
            if zip_source is None:
                if self.temp_dir and self.temp_dir.exists():
                    names = [
                        str(f.relative_to(self.temp_dir))
                        for f in self.temp_dir.rglob("*")
                        if f.is_file()
                    ]
                else:
                    return {
                        "valid": False,
                        "checks": [],
                        "errors": ["No zip source or temp directory found to verify"],
                        "warnings": [],
                        "total_files": 0,
                    }
            elif isinstance(zip_source, (str, Path)):
                with zipfile.ZipFile(zip_source, "r") as zf:
                    names = zf.namelist()
            elif isinstance(zip_source, BytesIO):
                with zipfile.ZipFile(zip_source, "r") as zf:
                    names = zf.namelist()
            elif isinstance(zip_source, bytes):
                with zipfile.ZipFile(BytesIO(zip_source), "r") as zf:
                    names = zf.namelist()
            else:
                names = zip_source.namelist() if hasattr(zip_source, "namelist") else []
            if "run_autograder" in names:
                checks.append("Found required executable script: run_autograder")
            else:
                errors.append("Missing required root script: run_autograder")
            if "setup.sh" in names:
                checks.append("Found environment setup script: setup.sh")
            if any(
                n.startswith("source/") or n.startswith("autograder/") or "/" in n for n in names
            ):
                checks.append("Archive contains valid folder structures")
            if self.retrieve_student_id:
                warnings.append(
                    "To allow student id retreive go to Gradescope -> Course dashboard's left sidebar -> click Roster -> Click Sync Roster (if linked to Blackboard/Moodle/Canvas)."
                )
            valid = len(errors) == 0
        except Exception as e:
            valid = False
            errors.append(f"Invalid ZIP archive format: {str(e)}")
            names = []
        return {
            "valid": valid,
            "checks": checks,
            "errors": errors,
            "warnings": warnings,
            "total_files": len(names),
        }

    def generate_description_docx(self) -> BytesIO:
        """Generate a Word document containing the assessment description."""
        return generate_description_docx_buffer(self.config)

    def generate_description_md(self) -> BytesIO:
        md_content = generate_description_md(self.config)
        buffer = BytesIO(md_content.encode("utf-8"))
        buffer.seek(0)
        return buffer

    def generate_correct_answer_zip(self) -> BytesIO:
        """Generate a ZIP file with correct implementation skeletons."""
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
            created_dirs = set()
            for filename in self.config.required_files:
                parent = Path(filename).parent
                if str(parent) != "." and str(parent) not in created_dirs:
                    created_dirs.add(str(parent))
                    zipf.writestr(f"{parent}/", "")
                content = self._generate_skeleton_content(filename, correct=True)
                zipf.writestr(filename, content)

            has_git = any(
                item.type in ("git_submission_test", "git_submission_exists")
                for q in self.config.questions
                for item in q.marking_items
            )
            has_gitlab = any(
                item.type in ("gitlab_submission_test", "gitlab_submission_exists")
                for q in self.config.questions
                for item in q.marking_items
            )
            has_github = any(
                item.type in ("github_submission_test", "github_submission_exists")
                for q in self.config.questions
                for item in q.marking_items
            )
            if has_git or has_gitlab:
                zipf.writestr(
                    "submission_metadata.json",
                    json.dumps({"submission_method": "GitLab"}),
                )
            elif has_github:
                zipf.writestr(
                    "submission_metadata.json",
                    json.dumps({"submission_method": "GitHub"}),
                )
        buffer.seek(0)
        return buffer

    def generate_wrong_answer_zip(self) -> BytesIO:
        """Generate a ZIP file with incorrect implementation skeletons."""
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
            created_dirs = set()
            for filename in self.config.required_files:
                parent = Path(filename).parent
                if str(parent) != "." and str(parent) not in created_dirs:
                    created_dirs.add(str(parent))
                    zipf.writestr(f"{parent}/", "")
                content = self._generate_skeleton_content(filename, correct=False)
                zipf.writestr(filename, content)
            has_git = any(
                item.type in ("git_submission_test", "git_submission_exists")
                for q in self.config.questions
                for item in q.marking_items
            )
            has_gitlab = any(
                item.type in ("gitlab_submission_test", "gitlab_submission_exists")
                for q in self.config.questions
                for item in q.marking_items
            )
            has_github = any(
                item.type in ("github_submission_test", "github_submission_exists")
                for q in self.config.questions
                for item in q.marking_items
            )
            if has_git or has_gitlab:
                zipf.writestr(
                    "submission_metadata.json",
                    json.dumps({"submission_method": "GitLab"}),
                )
            elif has_github:
                zipf.writestr(
                    "submission_metadata.json",
                    json.dumps({"submission_method": "GitHub"}),
                )
        buffer.seek(0)
        return buffer

    def generate_compiler_error_zip(self) -> BytesIO:
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
            created_dirs = set()
            for filename in self.config.required_files:
                parent = Path(filename).parent
                if str(parent) != "." and str(parent) not in created_dirs:
                    created_dirs.add(str(parent))
                    zipf.writestr(f"{parent}/", "")
                content = self._generate_skeleton_content(
                    filename, correct=False, compiler_error=True
                )
                zipf.writestr(filename, content)
            has_git = any(
                item.type in ("git_submission_test", "git_submission_exists")
                for q in self.config.questions
                for item in q.marking_items
            )
            has_gitlab = any(
                item.type in ("gitlab_submission_test", "gitlab_submission_exists")
                for q in self.config.questions
                for item in q.marking_items
            )
            has_github = any(
                item.type in ("github_submission_test", "github_submission_exists")
                for q in self.config.questions
                for item in q.marking_items
            )
            if has_git or has_gitlab:
                zipf.writestr(
                    "submission_metadata.json",
                    json.dumps({"submission_method": "GitLab"}),
                )
            elif has_github:
                zipf.writestr(
                    "submission_metadata.json",
                    json.dumps({"submission_method": "GitHub"}),
                )
        buffer.seek(0)
        return buffer

    def generate_wrong_file_location_zip(self) -> BytesIO:
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
            created_dirs = set()
            zipf.writestr("src/", "")
            created_dirs.add("src")
            for filename in self.config.required_files:
                nested_filename = f"src/{filename}"
                parent = Path(nested_filename).parent
                parts = parent.parts
                accum = ""
                for p in parts:
                    accum = f"{accum}/{p}" if accum else p
                    if accum not in created_dirs:
                        created_dirs.add(accum)
                        zipf.writestr(f"{accum}/", "")
                content = self._generate_skeleton_content(filename, correct=True)
                zipf.writestr(nested_filename, content)

            has_git = any(
                item.type in ("git_submission_test", "git_submission_exists")
                for q in self.config.questions
                for item in q.marking_items
            )
            has_gitlab = any(
                item.type in ("gitlab_submission_test", "gitlab_submission_exists")
                for q in self.config.questions
                for item in q.marking_items
            )
            has_github = any(
                item.type in ("github_submission_test", "github_submission_exists")
                for q in self.config.questions
                for item in q.marking_items
            )
            if has_git or has_gitlab:
                zipf.writestr(
                    "src/submission_metadata.json",
                    json.dumps({"submission_method": "GitLab"}),
                )
            elif has_github:
                zipf.writestr(
                    "src/submission_metadata.json",
                    json.dumps({"submission_method": "GitHub"}),
                )
        buffer.seek(0)
        return buffer

    generate_correct_answer_wrong_location_zip = generate_wrong_file_location_zip
    generate_correct_answer_with_wrong_location_zip = generate_wrong_file_location_zip

    def _generate_skeleton_content(
        self, target_file: str, correct: bool = True, compiler_error: bool = False
    ) -> str:
        if target_file.endswith(".pdf"):
            return ""

        language = self.config.language
        if compiler_error:
            if language == "python":
                return python_compiler_error_content(self.config, target_file)
            if language == "java":
                return java_compiler_error_content(target_file)

        if language == "python":
            return generate_python_skeleton(self.config, target_file, correct)
        if language == "java":
            return generate_java_skeleton(self.config, target_file, correct)
        return "# Skeleton for " + target_file

    def _generate_setup_sh(self):
        """Generate setup.sh using Jinja template."""
        assert self.temp_dir is not None, "temp_dir must be set before generating files"

        template = self.jinja_env.get_template("setup.sh.j2")
        content = template.render(config=self.config, retrieve_student_id=self.retrieve_student_id)

        setup_file = self.temp_dir / "setup.sh"
        with open(setup_file, "w", encoding="utf-8") as f:
            f.write(content)

        os.chmod(setup_file, 0o755)

    def _generate_run_autograder(self):
        """Generate run_autograder using Jinja template."""
        assert self.temp_dir is not None, "temp_dir must be set before generating files"
        template = self.jinja_env.get_template("run_autograder.j2")
        content = template.render(config=self.config, retrieve_student_id=self.retrieve_student_id)

        filepath = self.temp_dir / "run_autograder"
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        os.chmod(filepath, 0o755)

    def _generate_run_tests(self):
        """Generate modular test files: main run_tests.py and individual question test files."""
        assert self.temp_dir is not None, "temp_dir must be set before generating files"
        template = self.jinja_env.get_template("run_tests.py.j2")
        content = template.render(config=self.config, retrieve_student_id=self.retrieve_student_id)

        run_tests_file = self.temp_dir / "run_tests.py"
        with open(run_tests_file, "w", encoding="utf-8") as f:
            f.write(content)

        helpers = ["utils_submission.py"]
        if self.config.language == "java":
            helpers.append("utils_java.py")
        elif self.config.language == "python":
            helpers.append("utils_python.py")
        else:
            helpers.extend(["utils_java.py", "utils_python.py"])

        for helper_name in helpers:
            helper_src = Path(__file__).parent / helper_name
            if helper_src.exists():
                shutil.copy2(helper_src, self.temp_dir / helper_name)

        self._generate_question_test_files()

    def _generate_question_test_files(self):
        """Generate individual test files for each question."""
        assert self.temp_dir is not None, "temp_dir must be set before generating files"
        question_template = self.jinja_env.get_template("question_test.py.j2")

        for idx, question in enumerate(self.config.questions, 1):
            question_filename = f"question_{idx}"

            processed_question = self._preprocess_question_for_output_comparison(question)

            content = question_template.render(
                config=self.config,
                question=processed_question,
                question_number=idx,
                retrieve_student_id=self.retrieve_student_id,
            )

            test_file = self.temp_dir / f"{question_filename}_test.py"
            with open(test_file, "w", encoding="utf-8") as f:
                f.write(content)

    def _preprocess_question_for_output_comparison(self, question):
        """Preprocess question to add newlines to expected output for output comparison tests."""

        processed_question = SimpleNamespace()
        for attr in dir(question):
            if not attr.startswith("_") and not attr.startswith("model_"):
                setattr(processed_question, attr, getattr(question, attr))
        processed_question.marking_items = []

        for item in question.marking_items:
            processed_item = SimpleNamespace()
            for attr in dir(item):
                if not attr.startswith("_") and not attr.startswith("model_"):
                    setattr(processed_item, attr, getattr(item, attr))

            if (
                self.config.language == "python"
                and hasattr(processed_item, "type")
                and processed_item.type == "program_output_test"
                and hasattr(processed_item, "expected_output")
                and processed_item.expected_output
                and not processed_item.expected_output.endswith("\n")
            ):
                processed_item.expected_output += "\n"

            processed_question.marking_items.append(processed_item)

        return processed_question

    def _sanitize_filename(self, name: str) -> str:
        """Convert question name to a safe Python module filename."""
        safe_name = name.lower()
        safe_name = safe_name.replace(" ", "_")
        safe_name = safe_name.replace("-", "_")
        safe_name = safe_name.replace(".", "_")
        safe_name = safe_name.replace("(", "")
        safe_name = safe_name.replace(")", "")
        safe_name = safe_name.replace("[", "")
        safe_name = safe_name.replace("]", "")
        safe_name = safe_name.replace("/", "_")
        safe_name = safe_name.replace("\\", "_")
        safe_name = safe_name.replace(":", "_")
        safe_name = safe_name.replace(";", "_")
        safe_name = safe_name.replace(",", "_")
        safe_name = safe_name.replace("?", "_")
        safe_name = safe_name.replace("!", "_")
        safe_name = safe_name.replace("@", "_")
        safe_name = safe_name.replace("#", "_")
        safe_name = safe_name.replace("$", "_")
        safe_name = safe_name.replace("%", "_")
        safe_name = safe_name.replace("^", "_")
        safe_name = safe_name.replace("&", "_")
        safe_name = safe_name.replace("*", "_")
        safe_name = safe_name.replace("+", "_")
        safe_name = safe_name.replace("=", "_")
        safe_name = safe_name.replace("|", "_")
        safe_name = safe_name.replace("<", "_")
        safe_name = safe_name.replace(">", "_")

        safe_name = re.sub(r"_+", "_", safe_name)

        safe_name = safe_name.strip("_")

        if not safe_name or safe_name[0].isdigit():
            safe_name = "question_" + safe_name

        return safe_name

    def _generate_metadata_files(self):
        """Generate metadata and configuration files."""
        assert self.temp_dir is not None, "temp_dir must be set before generating files"

        readme_file = self.temp_dir / "README.md"
        with open(readme_file, "w", encoding="utf-8") as f:
            f.write(generate_readme_md(self.config))

    def _create_zip(self, zip_path: Path):
        """Create the autograder.zip file with proper structure."""
        assert self.temp_dir is not None, "temp_dir must be set before creating zip"

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for file_path in self.temp_dir.rglob("*"):
                if file_path.is_file():
                    arcname = file_path.relative_to(self.temp_dir)
                    zipf.write(file_path, arcname)


def validate_file_path(file_path: str, description: str = "File") -> Path:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"{description} not found: {file_path}")
    if not path.is_file():
        raise ValueError(f"{description} is not a file: {file_path}")
    return path


def validate_directory_path(dir_path: str, description: str = "Directory") -> Path:
    path = Path(dir_path)
    if not path.exists():
        raise FileNotFoundError(f"{description} not found: {dir_path}")
    if not path.is_dir():
        raise ValueError(f"{description} is not a directory: {dir_path}")
    return path


def create_directory(dir_path: str, description: str = "Directory") -> Path:
    path = Path(dir_path)
    try:
        path.mkdir(parents=True, exist_ok=True)
        return path
    except Exception as e:
        raise ValueError(f"Failed to create {description.lower()}: {dir_path}. Error: {e}")


def get_file_extension(file_path: str) -> str:
    return Path(file_path).suffix.lower()


def is_supported_language_file(file_path: str, language: str) -> bool:
    extension = get_file_extension(file_path)
    language_extensions = {"python": [".py"], "java": [".java"]}
    return extension in language_extensions.get(language.lower(), [])


def sanitize_filename(filename: str) -> str:
    sanitized = re.sub(r'[<>:"/\\|?*]', "_", filename)
    sanitized = sanitized.strip(" .")
    return sanitized if sanitized else "unnamed"


def format_error_message(error: Exception, context: str = "") -> str:
    if context:
        return f"{context}: {str(error)}"
    return str(error)
