from pathlib import Path
from typing import Union, Optional, Any
import importlib.util
import inspect
import ast
import sys
import concurrent.futures

try:
    from run_shared import StudentMessage
except ImportError:
    from autograder_gen.run_shared import StudentMessage


def call_function_with_timeout(
    func: Any, args: list, kwargs: dict, timeout_seconds: int
) -> Any:
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

