from pathlib import Path
import re
from typing import Union, Optional, List, Any
import json
import os
import math
import sys
from contextlib import redirect_stdout
import io
import logging

logger = logging.getLogger(__name__)


def normalize_output(s: str) -> str:
    if s is None:
        return ""
    s = s.replace("\r\n", "\n")
    lines = [line.rstrip() for line in s.splitlines()]
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)


def compare_outputs(
    actual: str,
    expected: str,
    strict_float: bool = False,
    rel_tol: float = 1e-4,
    abs_tol: float = 1e-4,
) -> bool:
    if actual == expected:
        return True
    if strict_float:
        return False
    try:
        a_val = float(actual.strip())
        e_val = float(expected.strip())
        return math.isclose(a_val, e_val, rel_tol=rel_tol, abs_tol=abs_tol)
    except (ValueError, TypeError):
        pass
    return False


STUDENT_ID_FALLBACK = 12345678


def get_student_id(
    autograder_root: Union[str, Path, None] = None,
    excluded_ids: Union[List[Any], None] = None,
) -> str:
    print("[INFO] Checking student ID...")
    root = (
        Path(autograder_root)
        if autograder_root
        else Path(os.environ.get("AUTOGRADER_ROOT", "/autograder"))
    )
    metadata_candidates = [
        root / "submission_metadata.json",
        root / "submission" / "submission_metadata.json",
    ]
    metadata = {}
    for p in metadata_candidates:
        if p.exists():
            try:
                with p.open(encoding="utf-8") as f:
                    metadata = json.load(f)
                break
            except Exception:
                pass

    users = metadata.get("users") or []
    first_user = users[0] if users else {}
    raw_sid = str(first_user.get("sid", "")) if first_user.get("sid") is not None else ""
    student_id = re.sub(r"\D+", "", raw_sid)

    if excluded_ids is None:
        excluded_ids = []

    excluded_raw = {str(x).strip() for x in (excluded_ids or []) if str(x).strip()}
    excluded_digits = {re.sub(r"\D+", "", x) for x in excluded_raw if re.sub(r"\D+", "", x)}
    is_excluded = bool(
        raw_sid
        and (
            raw_sid in excluded_raw
            or student_id in excluded_raw
            or (student_id and student_id in excluded_digits)
        )
    )

    if is_excluded:
        print(f"[INFO] Student ID '{raw_sid or student_id}' is excluded; using fallback ID.")
        student_id = str(STUDENT_ID_FALLBACK)
    elif not student_id.strip():
        print(
            "[ERROR] Student ID not found in submission metadata. Please notify the module instructor."
        )
        student_id = str(STUDENT_ID_FALLBACK)

    print(f"[INFO] Using student ID: {student_id}")
    return student_id


def eval_expected_output_script(
    script: str, student_id: str = str(STUDENT_ID_FALLBACK), expected_input: str = ""
) -> str:
    buf = io.StringIO()
    old_stdin = sys.stdin
    sys.stdin = io.StringIO(expected_input)
    scope = {"STUDENT_ID": student_id}
    try:
        with redirect_stdout(buf):
            exec(script, scope)
        return buf.getvalue()
    except Exception as e:
        return f"Error executing expected_output_script: {e}\n"
    finally:
        sys.stdin = old_stdin


def resolve_target(
    source_dir: Union[str, Path],
    target_file: str,
    strict_file_location: bool = False,
    wrong_location_files: Optional[set] = None,
) -> Path:
    s_dir = Path(source_dir)
    target_path = s_dir / target_file
    if not strict_file_location:
        if target_path.exists():
            return target_path
        matches = list(s_dir.rglob(Path(target_file).name))
        if matches:
            if wrong_location_files is not None:
                wrong_location_files.add(target_file)
            resolved = matches[0]
            resolved_parent = str(resolved.parent)
            if resolved_parent not in sys.path:
                sys.path.insert(0, resolved_parent)
            return resolved
    return target_path


def apply_wrong_location_deduction(
    target_file: str,
    total_mark: float,
    deduction_rate: float,
    wrong_location_files: set,
    test_case_instance: Any = None,
) -> Optional[float]:
    if deduction_rate > 0 and target_file in wrong_location_files:
        deduction = round(float(total_mark) * float(deduction_rate), 4)
        awarded = max(0.0, float(total_mark) - float(deduction))
        if test_case_instance is not None:
            method_name = getattr(test_case_instance, "_testMethodName", None)
            if method_name:
                setattr(getattr(test_case_instance.__class__, method_name), "__score__", awarded)
        print(f"[INFO] penalties applied for file in wrong location: -{deduction} pts")
        return awarded
    return None


def format_function_arg(arg: Any) -> str:
    if isinstance(arg, str):
        s = arg.strip()
        if (s.startswith("{") and s.endswith("}")) or (s.startswith("[") and s.endswith("]")) or s.startswith("new "):
            return s
        if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
            inner = s[1:-1]
            return f'"{inner}"'
        return f'"{s}"'
    if isinstance(arg, bool):
        return str(arg)
    if isinstance(arg, (int, float)):
        return str(arg)
    if isinstance(arg, (list, tuple)):
        items = [format_function_arg(x) for x in arg]
        return f"[{', '.join(items)}]" if isinstance(arg, list) else f"({', '.join(items)})"
    if isinstance(arg, dict):
        items = [f"{format_function_arg(k)}: {format_function_arg(v)}" for k, v in arg.items()]
        return f"{{{', '.join(items)}}}"
    return str(arg)


def format_function_call(
    function_name: str,
    args: Optional[list] = None,
    kwargs: Optional[dict] = None,
) -> str:
    formatted_args = []
    if args:
        for a in args:
            formatted_args.append(format_function_arg(a))
    if kwargs:
        for k, v in kwargs.items():
            formatted_args.append(f"{k}={format_function_arg(v)}")
    return f"{function_name}({', '.join(formatted_args)})"


class StudentMessageStr(str):
    def format(self, *args, **kwargs):
        if "target_file" in kwargs and "file_name" not in kwargs:
            kwargs["file_name"] = kwargs["target_file"]
        if "file_name" in kwargs and "target_file" not in kwargs:
            kwargs["target_file"] = kwargs["file_name"]
        return super().format(*args, **kwargs)


class StudentMessage:
    ENVIRONMENT = StudentMessageStr("Environment: {version}")
    COMPILING = "## Compiling"
    RUNNING = "## Running"
    COMPARING_OUTPUT = "## Comparing output"
    COMPARING_RETURN = "## Comparing return"
    CHECKING_FUNCTION_SIGNATURE = "## Checking signature"
    INPUT = "### Input:"
    FUNCTION_CALL = "### Function call:"
    EXPECTED_OUTPUT = "### Expected output:"
    EXPECTED_RETURN = "### Expected return:"
    ACTUAL_OUTPUT = "### Actual output:"
    ACTUAL_RETURN = "### Actual return:"
    COMPILATION_ERROR = "[COMPILATION_ERROR] Check compile errors above."
    RUNTIME_ERROR = "[RUNTIME_ERROR] Check runtime errors above."
    CORRECT_ANSWER_FILE = StudentMessageStr(
        "[CORRECT_ANSWER] Output matches expected for std output of file {file_name}."
    )
    CORRECT_ANSWER_FUNCTION_RETURN = StudentMessageStr(
        "[CORRECT_ANSWER] Return value matches expected for function '{function_name}'."
    )
    CORRECT_ANSWER_FUNCTION_OUTPUT = StudentMessageStr(
        "[CORRECT_ANSWER] Output matches expected for std output of function '{function_name}'."
    )
    WRONG_ANSWER_FILE = StudentMessageStr(
        "[WRONG_ANSWER] Output mismatch for for std output of file '{file_name}'."
    )
    WRONG_ANSWER_FUNCTION_RETURN = StudentMessageStr(
        "[WRONG_ANSWER] Return value mismatch for function '{function_name}'."
    )
    WRONG_ANSWER_FUNCTION_OUTPUT = StudentMessageStr(
        "[WRONG_ANSWER] Output mismatch for std output of function '{function_name}'."
    )
    TIME_LIMIT_EXCEEDED_FILE = StudentMessageStr(
        "[TIME_LIMIT_EXCEEDED] timed out after {seconds} for {file_name}."
    )
    TIME_LIMIT_EXCEEDED_FUNCTION = StudentMessageStr(
        "[TIME_LIMIT_EXCEEDED] timed out after {seconds} for function {function_name}."
    )
    CORRECT_FILE = StudentMessageStr("[CORRECT_FILE] File '{file_name}' exists.")
    WRONG_FILE = StudentMessageStr("[WRONG_FILE] File '{file_name}' not found.")
    ERROR_FUNCTION_NOT_CALLABLE = StudentMessageStr(
        "Error: Function '{function_name}' is not callable"
    )
    CORRECT_FUNCTION_SIGNATURE = StudentMessageStr(
        "[CORRECT_ANSWER] Function '{function_name}' signature is correct"
    )
    WRONG_FUNCTION_SIGNATURE = StudentMessageStr(
        "[WRONG_ANSWER] Function '{function_name}' signature mismatch: {reason}."
    )
    CORRECT_GITLAB_SUBMISSION = "[CORRECT_ANSWER] GitLab repository was found."
    WRONG_GITLAB_NOT_USED = "[WRONG_ANSWER] GitLab repository was not found."
    CORRECT_GITHUB_SUBMISSION = "[CORRECT_ANSWER] GitHub repository was found."
    WRONG_GITHUB_NOT_USED = "[WRONG_ANSWER] GitHub repository was not found."
    ERROR_GITHUB_NOT_USED = WRONG_GITHUB_NOT_USED


def assert_file_exists(file_path: Union[str, Path], file_name: str) -> None:
    p = Path(file_path)
    if not p.exists():
        raise AssertionError(StudentMessage.WRONG_FILE.format(file_name=file_name))


def assert_output_matches(
    actual: str,
    expected: str,
    target_file: str,
    strict_float: bool = False,
    normalize: bool = True,
) -> None:
    act = normalize_output(actual) if normalize else actual
    exp = normalize_output(expected) if normalize else expected
    if not compare_outputs(act, exp, strict_float=strict_float):
        raise AssertionError(StudentMessage.WRONG_ANSWER_FILE.format(file_name=target_file))


def assert_function_return_matches(
    actual: str,
    expected: str,
    function_name: str,
    strict_float: bool = False,
    normalize: bool = True,
) -> None:
    act = normalize_output(actual) if normalize else actual
    exp = normalize_output(expected) if normalize else expected
    if not compare_outputs(act, exp, strict_float=strict_float):
        raise AssertionError(
            StudentMessage.WRONG_ANSWER_FUNCTION_RETURN.format(function_name=function_name)
        )


def assert_function_output_matches(
    actual: str,
    expected: str,
    function_name: str,
    strict_float: bool = False,
    normalize: bool = True,
) -> None:
    act = normalize_output(actual) if normalize else actual
    exp = normalize_output(expected) if normalize else expected
    if not compare_outputs(act, exp, strict_float=strict_float):
        raise AssertionError(
            StudentMessage.WRONG_ANSWER_FUNCTION_OUTPUT.format(function_name=function_name)
        )


def assert_gitlab_submission_test(
    source_dir: Union[str, Path],
    autograder_root: Union[str, Path, None] = None,
) -> None:
    s_dir = Path(source_dir)
    ag_root = (
        Path(autograder_root)
        if autograder_root
        else Path(os.environ.get("AUTOGRADER_ROOT", "/autograder"))
    )
    metadata_paths = [
        ag_root / "submission_metadata.json",
        ag_root / "submission" / "submission_metadata.json",
        s_dir.parent / "submission_metadata.json",
        s_dir.parent / "submission" / "submission_metadata.json",
        s_dir / "submission_metadata.json",
        Path("submission_metadata.json"),
    ]
    metadata_path = None
    for p in metadata_paths:
        if p.exists():
            metadata_path = p
            break

    if metadata_path is None:
        raise AssertionError(StudentMessage.WRONG_GITLAB_NOT_USED)

    with metadata_path.open(encoding="utf-8") as f:
        metadata = json.load(f)
    method = metadata.get("submission_method")
    if method and method == "GitLab":
        print(f"## Test Passed: {StudentMessage.CORRECT_GITLAB_SUBMISSION}")
        return
    raise AssertionError(StudentMessage.WRONG_GITLAB_NOT_USED)


assert_gitlab_submission_exists = assert_gitlab_submission_test


def assert_github_submission_test(
    source_dir: Union[str, Path],
    autograder_root: Union[str, Path, None] = None,
) -> None:
    s_dir = Path(source_dir)
    ag_root = (
        Path(autograder_root)
        if autograder_root
        else Path(os.environ.get("AUTOGRADER_ROOT", "/autograder"))
    )
    metadata_paths = [
        ag_root / "submission_metadata.json",
        ag_root / "submission" / "submission_metadata.json",
        s_dir.parent / "submission_metadata.json",
        s_dir.parent / "submission" / "submission_metadata.json",
        s_dir / "submission_metadata.json",
        Path("submission_metadata.json"),
    ]
    metadata_path = None
    for p in metadata_paths:
        if p.exists():
            metadata_path = p
            break

    if metadata_path is None:
        raise AssertionError(StudentMessage.ERROR_GITHUB_NOT_USED)

    with metadata_path.open(encoding="utf-8") as f:
        metadata = json.load(f)
    method = metadata.get("submission_method")
    if method and method == "GitHub":
        print(f"## Test Passed: {StudentMessage.CORRECT_GITHUB_SUBMISSION}")
        return
    raise AssertionError(StudentMessage.ERROR_GITHUB_NOT_USED)


assert_github_submission_exists = assert_github_submission_test

