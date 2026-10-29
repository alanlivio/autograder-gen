from __future__ import annotations

import ast
import concurrent.futures
import importlib.util
import inspect
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional, Union

try:
    from utils_submission import (
        STUDENT_ID_FALLBACK,
        StudentMessage,
        eval_expected_output_script,
    )
except ImportError:
    from autograder_gen.utils_submission import (
        STUDENT_ID_FALLBACK,
        StudentMessage,
        eval_expected_output_script,
    )

if TYPE_CHECKING:
    from autograder_gen.config import Config


def call_function_with_timeout(func: Any, args: list, kwargs: dict, timeout_seconds: int) -> Any:
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(func, *args, **kwargs)
        try:
            return future.result(timeout=timeout_seconds)
        except concurrent.futures.TimeoutError:
            raise TimeoutError(f"Function execution timed out after {timeout_seconds} seconds")


def call_function_output_with_timeout(
    func: Any, args: list, kwargs: dict, timeout_seconds: int
) -> str:
    import io
    from contextlib import redirect_stdout

    def _wrapper():
        buf = io.StringIO()
        with redirect_stdout(buf):
            func(*args, **kwargs)
        return buf.getvalue()

    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(_wrapper)
        try:
            return future.result(timeout=timeout_seconds)
        except concurrent.futures.TimeoutError:
            raise TimeoutError(f"Function execution timed out after {timeout_seconds} seconds")


def import_function_from_file(file_path: Union[str, Path], function_name: str) -> Any:
    p = Path(file_path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {p}")

    module_name = p.stem
    try:
        spec = importlib.util.spec_from_file_location(module_name, p)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load module from {p}")

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
    except SyntaxError:
        raise
    except ImportError:
        raise
    except Exception as e:
        raise ImportError(f"Failed to import {function_name} from {p.name}: {str(e)}")

    if not hasattr(module, function_name):
        raise ImportError(f"Function '{function_name}' not found in {p.name}")

    return getattr(module, function_name)


def assert_python_function_signature(
    function: Any,
    function_name: str,
    expected_parameters: Optional[str] = None,
    expected_return_type: Optional[str] = None,
) -> None:
    if not callable(function):
        print(StudentMessage.RUNNING)
        print(StudentMessage.ERROR_FUNCTION_NOT_CALLABLE.format(function_name=function_name))
        raise AssertionError(StudentMessage.RUNTIME_ERROR)

    sig = inspect.signature(function)
    return_annotation = sig.return_annotation
    if return_annotation != inspect.Signature.empty:
        print(f"INFO: Function '{function_name}' has return type annotation: {return_annotation}")

    if expected_parameters and expected_parameters.strip():
        expected_params = []
        param_parts = [p.strip() for p in expected_parameters.split(",")]
        for param_part in param_parts:
            param_name = param_part
            param_type = None
            default_value = None
            if ":" in param_part:
                name_part, type_part = param_part.split(":", 1)
                param_name = name_part.strip()
                type_part = type_part.strip()
                if "=" in type_part:
                    type_str, default_str = type_part.split("=", 1)
                    param_type = type_str.strip()
                    default_value = default_str.strip()
                else:
                    param_type = type_part
            elif "=" in param_part:
                param_name, default_value = param_part.split("=", 1)
                param_name = param_name.strip()
                default_value = default_value.strip()

            expected_params.append((param_name, param_type, default_value))

        actual_params = dict(sig.parameters.items())
        if len(actual_params) != len(expected_params):
            raise AssertionError(
                StudentMessage.WRONG_FUNCTION_SIGNATURE.format(
                    function_name=function_name,
                    reason=f"has {len(actual_params)} parameters, expected {len(expected_params)}",
                )
            )

        for expected_name, expected_type, expected_default in expected_params:
            if expected_name not in actual_params:
                raise AssertionError(
                    StudentMessage.WRONG_FUNCTION_SIGNATURE.format(
                        function_name=function_name,
                        reason=f"missing parameter '{expected_name}'",
                    )
                )

            actual_param = actual_params[expected_name]
            if expected_type is not None:
                actual_annotation = actual_param.annotation
                if actual_annotation == inspect.Parameter.empty:
                    raise AssertionError(
                        StudentMessage.WRONG_FUNCTION_SIGNATURE.format(
                            function_name=function_name,
                            reason=f"parameter '{expected_name}' should have type annotation '{expected_type}'",
                        )
                    )
                else:
                    actual_type_str = str(actual_annotation)
                    if (
                        expected_type.lower() not in actual_type_str.lower()
                        and actual_type_str != expected_type
                    ):
                        type_matches = [
                            expected_type == actual_type_str,
                            expected_type.replace("typing.", "")
                            == actual_type_str.replace("typing.", ""),
                            expected_type.lower() == actual_type_str.lower(),
                            (expected_type == "int" and "int" in actual_type_str),
                            (expected_type == "str" and "str" in actual_type_str),
                            (expected_type == "float" and "float" in actual_type_str),
                            (expected_type == "bool" and "bool" in actual_type_str),
                            (expected_type == "list" and "list" in actual_type_str.lower()),
                            (expected_type == "dict" and "dict" in actual_type_str.lower()),
                        ]
                        if not any(type_matches):
                            raise AssertionError(
                                StudentMessage.WRONG_FUNCTION_SIGNATURE.format(
                                    function_name=function_name,
                                    reason=f"parameter '{expected_name}' has type '{actual_type_str}', expected '{expected_type}'",
                                )
                            )

            if expected_default is not None:
                if actual_param.default == inspect.Parameter.empty:
                    raise AssertionError(
                        StudentMessage.WRONG_FUNCTION_SIGNATURE.format(
                            function_name=function_name,
                            reason=f"parameter '{expected_name}' should have default value '{expected_default}'",
                        )
                    )
                else:
                    try:
                        expected_val = ast.literal_eval(expected_default)
                        if type(actual_param.default) != type(expected_val):
                            try:
                                converted_actual = type(expected_val)(actual_param.default)
                                if converted_actual != expected_val:
                                    raise AssertionError(
                                        StudentMessage.WRONG_FUNCTION_SIGNATURE.format(
                                            function_name=function_name,
                                            reason=f"parameter '{expected_name}' has default '{actual_param.default}' ({type(actual_param.default).__name__}), expected '{expected_val}' ({type(expected_val).__name__})",
                                        )
                                    )
                            except (ValueError, TypeError):
                                raise AssertionError(
                                    StudentMessage.WRONG_FUNCTION_SIGNATURE.format(
                                        function_name=function_name,
                                        reason=f"parameter '{expected_name}' has default '{actual_param.default}' ({type(actual_param.default).__name__}), expected '{expected_val}' ({type(expected_val).__name__})",
                                    )
                                )
                        elif actual_param.default != expected_val:
                            raise AssertionError(
                                StudentMessage.WRONG_FUNCTION_SIGNATURE.format(
                                    function_name=function_name,
                                    reason=f"parameter '{expected_name}' has default '{actual_param.default}', expected '{expected_val}'",
                                )
                            )
                    except (ValueError, SyntaxError):
                        actual_str = str(actual_param.default)
                        if actual_str != expected_default:
                            if not (
                                (
                                    expected_default.lower() == "none"
                                    and actual_param.default is None
                                )
                                or (
                                    expected_default.lower() == "true"
                                    and actual_param.default is True
                                )
                                or (
                                    expected_default.lower() == "false"
                                    and actual_param.default is False
                                )
                                or (expected_default == "[]" and actual_param.default == [])
                                or (expected_default == "{}" and actual_param.default == {})
                                or (expected_default.strip("'\"") == actual_str.strip("'\""))
                            ):
                                raise AssertionError(
                                    StudentMessage.WRONG_FUNCTION_SIGNATURE.format(
                                        function_name=function_name,
                                        reason=f"parameter '{expected_name}' has default '{actual_str}', expected '{expected_default}'",
                                    )
                                )

    if expected_return_type and expected_return_type.strip():
        if sig.return_annotation == inspect.Signature.empty:
            raise AssertionError(
                StudentMessage.WRONG_FUNCTION_SIGNATURE.format(
                    function_name=function_name,
                    reason=f"should have return type annotation '{expected_return_type}'",
                )
            )
        else:
            actual_return_str = str(sig.return_annotation)
            type_matches = [
                expected_return_type == actual_return_str,
                expected_return_type.replace("typing.", "")
                == actual_return_str.replace("typing.", ""),
                expected_return_type.lower() == actual_return_str.lower(),
                (expected_return_type == "int" and "int" in actual_return_str),
                (expected_return_type == "str" and "str" in actual_return_str),
                (expected_return_type == "float" and "float" in actual_return_str),
                (expected_return_type == "bool" and "bool" in actual_return_str),
                (expected_return_type == "list" and "list" in actual_return_str.lower()),
                (expected_return_type == "dict" and "dict" in actual_return_str.lower()),
                (expected_return_type == "None" and actual_return_str == "None"),
            ]
            if not any(type_matches):
                raise AssertionError(
                    StudentMessage.WRONG_FUNCTION_SIGNATURE.format(
                        function_name=function_name,
                        reason=f"has return type '{actual_return_str}', expected '{expected_return_type}'",
                    )
                )


check_function_signature = assert_python_function_signature
check_python_function_signature = assert_python_function_signature
call_python_function = call_function_with_timeout
call_python_function_output = call_function_output_with_timeout


def get_python_literal_str(expected_str: str) -> str:
    try:
        val = ast.literal_eval(expected_str)
        return repr(val)
    except Exception:
        return repr(expected_str)


def python_compiler_error_content(config: Config, target_file: str) -> str:
    functions = set()
    for q in config.questions:
        for item in q.marking_items:
            if item.target_file == target_file and getattr(item, "function_name", ""):
                functions.add(item.function_name)
    if functions:
        func = sorted(functions)[0]
        return f"def {func}(*args, **kwargs)\n    pass\n"
    return "def syntax_error(\n    pass\n"


def generate_python_skeleton(config: Config, target_file: str, correct: bool = True) -> str:
    lines = ["# Skeleton for " + target_file, ""]
    functions = set()
    for q in config.questions:
        for item in q.marking_items:
            if item.target_file == target_file:
                if hasattr(item, "function_name") and item.function_name:
                    functions.add(item.function_name)
    for func in sorted(functions):
        expected_params = ""
        expected_return = ""
        for q in config.questions:
            for item in q.marking_items:
                if item.target_file == target_file and getattr(item, "function_name", "") == func:
                    if getattr(item, "expected_parameters", "") and not expected_params:
                        expected_params = item.expected_parameters.strip()
                    if getattr(item, "expected_return_type", "") and not expected_return:
                        expected_return = item.expected_return_type.strip()

        param_names = []
        if expected_params:
            for part in expected_params.split(","):
                name = part.split(":")[0].split("=")[0].strip()
                if name:
                    param_names.append(name)

        if correct and expected_params:
            ret_anno = f" -> {expected_return}" if expected_return else ""
            lines.append(f"def {func}({expected_params}){ret_anno}:")
        else:
            lines.append(f"def {func}(*args, **kwargs):")

        if correct:
            cases = []
            for q in config.questions:
                for item in q.marking_items:
                    if (
                        item.target_file == target_file
                        and getattr(item, "function_name", "") == func
                        and item.type in ("function_return_test", "function_output_test")
                    ):
                        if hasattr(item, "test_cases") and item.test_cases:
                            for tc in item.test_cases:
                                cases.append((tc, item))
            if cases:
                for tc, itm in cases:
                    conds = []
                    args_list = tc.get("args", []) or []
                    kwargs_dict = tc.get("kwargs", {}) or {}
                    if expected_params and param_names:
                        for idx, arg_val in enumerate(args_list):
                            if idx < len(param_names):
                                conds.append(f"{param_names[idx]} == {repr(arg_val)}")
                        if kwargs_dict:
                            for k, v in kwargs_dict.items():
                                if k in param_names:
                                    conds.append(f"{k} == {repr(v)}")
                    else:
                        if args_list:
                            conds.append(f"args == {tuple(args_list)}")
                        else:
                            conds.append("not args")
                        if kwargs_dict:
                            conds.append(f"kwargs == {kwargs_dict}")
                        else:
                            conds.append("not kwargs")
                    cond_str = " and ".join(conds) if conds else "True"
                    expected_val = tc.get("expected", "")
                    expr = get_python_literal_str(expected_val)
                    lines.append(f"    if {cond_str}:")
                    if getattr(itm, "type", "") == "function_output_test":
                        lines.append(f"        print({expr}, end='')")
                        lines.append("        return")
                    else:
                        lines.append(f"        return {expr}")
                lines.append("    pass")
            else:
                lines.append("    pass")
        else:
            func_expected = []
            func_items = []
            for q in config.questions:
                for item in q.marking_items:
                    if (
                        item.target_file == target_file
                        and getattr(item, "function_name", "") == func
                        and item.type in ("function_return_test", "function_output_test")
                    ):
                        func_items.append(item)
                        for tc in getattr(item, "test_cases", []) or []:
                            func_expected.append(str(tc.get("expected", "")).strip())
            if any(getattr(item, "type", "") == "function_output_test" for item in func_items):
                lines.append("    print('wrong_answer', end='')")
            elif any(exp in ("None", "none", "null") for exp in func_expected):
                lines.append("    return 'wrong_answer'")
            else:
                lines.append("    return None")
        lines.append("")
    output_items = [
        (
            item,
            getattr(item, "expected_output_script", None)
            or getattr(q, "expected_output_script", None),
        )
        for q in config.questions
        for item in q.marking_items
        if item.target_file == target_file and item.type == "program_output_test"
    ]

    if output_items:
        lines.append('if __name__ == "__main__":')
        if correct:
            if len(output_items) == 1 and not output_items[0][0].expected_input.strip():
                single_item, single_script = output_items[0]
                has_item_script = bool(single_script)
                if has_item_script:
                    out_val = eval_expected_output_script(
                        single_script,
                        student_id=str(STUDENT_ID_FALLBACK),
                        expected_input=single_item.expected_input,
                    )
                else:
                    out_val = single_item.expected_output
                lines.append("    import sys")
                if has_item_script:
                    lines.append(f"    # Fallback student ID: {STUDENT_ID_FALLBACK}")
                lines.append(f"    sys.stdout.write({repr(out_val)})")
            else:
                lines.append("    import sys, os")
                lines.append("    _raw_in = sys.stdin.read()")
                lines.append("    _in = _raw_in.strip()")
                for idx, (item, item_script) in enumerate(output_items):
                    cond = f"_in == {repr(item.expected_input.strip())}"
                    has_item_script = bool(item_script)
                    if has_item_script:
                        out_val = eval_expected_output_script(
                            item_script,
                            student_id=str(STUDENT_ID_FALLBACK),
                            expected_input=item.expected_input,
                        )
                    else:
                        out_val = item.expected_output
                    branch = "if" if idx == 0 else "elif"
                    lines.append(f"    {branch} {cond}:")
                    if has_item_script:
                        lines.append(f"        # Fallback student ID: {STUDENT_ID_FALLBACK}")
                    lines.append(f"        sys.stdout.write({repr(out_val)})")
                    lines.append("        sys.exit(0)")
                if len(output_items) > 1:
                    first_item, first_script = output_items[0]
                    if first_script:
                        default_out = eval_expected_output_script(
                            first_script,
                            student_id=str(STUDENT_ID_FALLBACK),
                            expected_input=first_item.expected_input,
                        )
                        lines.append("    else:")
                        lines.append(f"        # Fallback student ID: {STUDENT_ID_FALLBACK}")
                        lines.append(f"        sys.stdout.write({repr(default_out)})")
                    else:
                        default_out = first_item.expected_output
                        lines.append("    else:")
                        lines.append(f"        sys.stdout.write({repr(default_out)})")
        else:
            lines.append("    import sys")
            lines.append('    sys.stdout.write("wrong_output\\n")')
        lines.append("")

    if not functions and not output_items:
        lines.append("# No specific functions defined for this file.")
        if not correct:
            lines.append("# This file might be intentionally wrong or missing logic.")
    if any(item_script for _, item_script in output_items):
        lines.insert(0, f"# Fallback student ID: {STUDENT_ID_FALLBACK}")
    return "\n".join(lines)
