from __future__ import annotations

import logging
import re
import shutil
import subprocess
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

logger = logging.getLogger(__name__)


def get_octave_executable() -> str:
    if shutil.which("octave-cli"):
        return "octave-cli"
    return "octave"


def escape_matlab_str(s: str) -> str:
    escaped = (
        s.replace("\\", "\\\\")
        .replace("'", "''")
        .replace("\r", "\\r")
        .replace("\n", "\\n")
        .replace("\t", "\\t")
    )
    return f"'{escaped}'"


def format_matlab_arg(arg: Any) -> str:
    if isinstance(arg, bool):
        return "true" if arg else "false"
    if isinstance(arg, (int, float)):
        return str(arg)
    if isinstance(arg, (list, tuple)):
        if arg and isinstance(arg[0], (list, tuple)):
            rows = [", ".join(format_matlab_arg(x) for x in row) for row in arg]
            return f"[{'; '.join(rows)}]"
        items = [format_matlab_arg(x) for x in arg]
        return f"[{', '.join(items)}]"
    if isinstance(arg, str):
        s = arg.strip()
        if (s.startswith("[") and s.endswith("]")) or (s.startswith("{") and s.endswith("}")):
            return s
        if s.lower() in ("true", "false"):
            return s.lower()
        if (s.startswith("'") and s.endswith("'")) or (s.startswith('"') and s.endswith('"')):
            inner = s[1:-1].replace("'", "''")
            return f"'{inner}'"
        escaped = arg.replace("'", "''")
        return f"'{escaped}'"
    return str(arg)


def get_matlab_literal_str(expected_str: str) -> str:
    val_strip = expected_str.strip()
    if val_strip.lower() == "true":
        return "true"
    if val_strip.lower() == "false":
        return "false"
    if (val_strip.startswith("[") and val_strip.endswith("]")) or (
        val_strip.startswith("{") and val_strip.endswith("}")
    ):
        return val_strip
    try:
        int(val_strip)
        return val_strip
    except ValueError:
        pass
    try:
        float(val_strip)
        return val_strip
    except ValueError:
        pass
    escaped = expected_str.replace("'", "''")
    return f"'{escaped}'"


def _check_matlab_syntax(path: Path, cwd: Path) -> None:
    octave_bin = get_octave_executable()
    if not shutil.which(octave_bin):
        return
    escaped_path = str(path.resolve()).replace("'", "''")
    parse_cmd = f"warning('off', 'all'); __parse_file__('{escaped_path}');"
    res = subprocess.run(
        [octave_bin, "--no-gui", "--quiet", "--eval", parse_cmd],
        capture_output=True,
        text=True,
        cwd=cwd,
    )
    if res.returncode != 0:
        err = (res.stderr or res.stdout or "").strip()
        if err:
            print(StudentMessage.COMPILING)
            print(err)
        raise AssertionError(StudentMessage.COMPILATION_ERROR)


def call_matlab_function(
    file_path: Union[str, Path],
    function_name: str,
    args: list,
    timeout_seconds: int,
    source_dir: Union[str, Path],
    capture_output: bool = False,
) -> str:
    path = Path(file_path)
    s_dir = Path(source_dir)
    if not path.exists():
        raise AssertionError(StudentMessage.WRONG_FILE.format(file_name=path.name))

    _check_matlab_syntax(path, s_dir)

    octave_bin = get_octave_executable()
    target_dir_str = str(path.parent.resolve()).replace("'", "''")
    s_dir_str = str(s_dir.resolve()).replace("'", "''")
    file_path_str = str(path.resolve()).replace("'", "''")
    formatted_args = ", ".join(format_matlab_arg(a) for a in (args or []))
    call_expr = f"{function_name}({formatted_args})"

    setup_code = (
        "warning('off', 'all'); "
        f"addpath('{target_dir_str}'); "
        f"addpath('{s_dir_str}'); "
        f"evalc([\"1;\\n\", fileread('{file_path_str}')]); "
    )

    if capture_output:
        eval_code = setup_code + f"{call_expr};"
    else:
        eval_code = (
            setup_code
            + f'[_ag_out, _ag_res] = evalc("{call_expr}"); '
            + "if ischar(_ag_res), "
            + "fprintf('%s', _ag_res); "
            + "elseif islogical(_ag_res) && isscalar(_ag_res), "
            + "if _ag_res, fprintf('true'); else, fprintf('false'); end; "
            + "elseif isnumeric(_ag_res) && isscalar(_ag_res), "
            + "fprintf('%s', num2str(_ag_res, 15)); "
            + "else, "
            + "fprintf('%s', mat2str(_ag_res)); "
            + "end;"
        )

    res = subprocess.run(
        [octave_bin, "--no-gui", "--quiet", "--eval", eval_code],
        input="",
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        cwd=s_dir,
    )
    if res.returncode != 0:
        err = (res.stderr or res.stdout or "").strip()
        if (
            "syntax error" in err.lower()
            or "parse error" in err.lower()
            or "invalid parameter list" in err.lower()
        ):
            if err:
                print(StudentMessage.COMPILING)
                print(err)
            raise AssertionError(StudentMessage.COMPILATION_ERROR)
        raise RuntimeError(f"Error executing {function_name}: {err}")
    return res.stdout


def assert_matlab_function_signature(
    file_path: Union[str, Path],
    function_name: str,
    source_dir: Union[str, Path] = ".",
    expected_parameters: Optional[str] = None,
    expected_return_type: Optional[str] = None,
) -> bool:
    path = Path(file_path)
    s_dir = Path(source_dir)
    if not path.exists():
        raise AssertionError(StudentMessage.WRONG_FILE.format(file_name=path.name))

    _check_matlab_syntax(path, s_dir)

    content = path.read_text(encoding="utf-8", errors="replace")
    clean_lines = []
    for line in content.splitlines():
        stripped = re.sub(r"[%#].*$", "", line).strip()
        if stripped:
            clean_lines.append(stripped)
    joined = "\n".join(clean_lines)

    pattern = re.compile(
        r"^\s*function\s+(?:(?:\[([^\]]*)\]|([A-Za-z_]\w*))\s*=\s*)?([A-Za-z_]\w*)\s*(?:\(([^)]*)\))?",
        re.MULTILINE,
    )
    matched = None
    for m in pattern.finditer(joined):
        ret_list, ret_single, fn_name, params_str = m.groups()
        if fn_name == function_name:
            raw_params = (params_str or "").strip()
            actual_params = (
                [p.strip() for p in raw_params.split(",") if p.strip()] if raw_params else []
            )
            ret_vars = []
            if ret_list is not None:
                ret_vars = [r.strip() for r in re.split(r"[,\s]+", ret_list.strip()) if r.strip()]
            elif ret_single is not None:
                ret_vars = [ret_single.strip()]
            matched = (ret_vars, actual_params)
            break

    if matched is None:
        raise AssertionError(
            StudentMessage.WRONG_FUNCTION_SIGNATURE.format(
                function_name=function_name,
                reason=f"function '{function_name}' not found in '{path.name}'",
            )
        )

    actual_ret_vars, actual_params = matched

    if expected_parameters and expected_parameters.strip():
        expected_parts = [p.strip() for p in expected_parameters.split(",") if p.strip()]
        if len(actual_params) != len(expected_parts):
            raise AssertionError(
                StudentMessage.WRONG_FUNCTION_SIGNATURE.format(
                    function_name=function_name,
                    reason=f"has {len(actual_params)} parameters, expected {len(expected_parts)}",
                )
            )
        for part in expected_parts:
            exp_name = part.split(":")[0].split("=")[0].strip()
            if " " in exp_name:
                exp_name = exp_name.split()[-1].strip()
            if exp_name and exp_name not in actual_params:
                raise AssertionError(
                    StudentMessage.WRONG_FUNCTION_SIGNATURE.format(
                        function_name=function_name,
                        reason=f"missing parameter '{exp_name}'",
                    )
                )

    if expected_return_type and expected_return_type.strip():
        exp_ret = expected_return_type.strip()
        if exp_ret.lower() not in ("void", "none") and not actual_ret_vars:
            raise AssertionError(
                StudentMessage.WRONG_FUNCTION_SIGNATURE.format(
                    function_name=function_name,
                    reason=f"has no return value, expected '{exp_ret}'",
                )
            )

    return True


check_matlab_function_signature = assert_matlab_function_signature


def matlab_compiler_error_content(target_file: str) -> str:
    return "x = (1 + 2;\n"


def generate_matlab_skeleton(config: Config, target_file: str, correct: bool = True) -> str:
    lines = ["1;"]
    functions = set()
    for q in config.questions:
        for item in q.marking_items:
            if item.target_file == target_file:
                if hasattr(item, "function_name") and item.function_name:
                    functions.add(item.function_name)

    for func in sorted(functions):
        expected_params = ""
        func_items = []
        for q in config.questions:
            for item in q.marking_items:
                if item.target_file == target_file and getattr(item, "function_name", "") == func:
                    func_items.append(item)
                    if getattr(item, "expected_parameters", "") and not expected_params:
                        expected_params = item.expected_parameters.strip()

        cases = []
        for item in func_items:
            for tc in getattr(item, "test_cases", []) or []:
                cases.append((tc, item))

        param_names = []
        if expected_params:
            for part in expected_params.split(","):
                name = part.split(":")[0].split("=")[0].strip()
                if " " in name:
                    name = name.split()[-1].strip()
                if name:
                    param_names.append(name)
        else:
            max_args = max((len(tc.get("args", []) or []) for tc, _ in cases), default=0)
            param_names = [chr(97 + i) for i in range(max_args)]

        if not correct and any(
            getattr(item, "type", "") == "function_signature_test" for item in func_items
        ):
            bad_params = ", ".join(param_names + ["extra_wrong_param"])
            lines.append(f"function res = {func}({bad_params})")
            lines.append("    res = -999999;")
            lines.append("end")
            lines.append("")
            continue

        param_str = ", ".join(param_names)
        is_output_only = all(
            getattr(item, "type", "") == "function_output_test" for item in func_items
        ) and any(getattr(item, "type", "") == "function_output_test" for item in func_items)

        if is_output_only:
            lines.append(f"function {func}({param_str})")
        else:
            lines.append(f"function res = {func}({param_str})")

        if correct:
            if cases:
                for idx_tc, (tc, itm) in enumerate(cases):
                    args_list = tc.get("args", []) or []
                    cond_parts = []
                    for idx_arg, arg_val in enumerate(args_list):
                        if idx_arg < len(param_names):
                            pn = param_names[idx_arg]
                            arg_lit = format_matlab_arg(arg_val)
                            cond_parts.append(f"isequal({pn}, {arg_lit})")
                    cond_str = " && ".join(cond_parts) if cond_parts else "true"
                    branch = "if" if idx_tc == 0 else "elseif"
                    lines.append(f"    {branch} ({cond_str})")
                    expected_val = str(tc.get("expected", ""))
                    if getattr(itm, "type", "") == "function_output_test":
                        lines.append(f"        fprintf('%s', {escape_matlab_str(expected_val)});")
                    else:
                        lines.append(f"        res = {get_matlab_literal_str(expected_val)};")
                if not is_output_only:
                    lines.append("    else")
                    lines.append("        res = 0;")
                lines.append("    end")
            else:
                if not is_output_only:
                    lines.append("    res = 0;")
        else:
            if is_output_only:
                lines.append("    fprintf('wrong_output');")
            else:
                lines.append("    res = -999999;")

        lines.append("end")
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
        if correct:
            if len(output_items) == 1 and not output_items[0][0].expected_input.strip():
                single_item, single_script = output_items[0]
                if single_script:
                    out_val = eval_expected_output_script(
                        single_script,
                        student_id=str(STUDENT_ID_FALLBACK),
                        expected_input=single_item.expected_input,
                    )
                    lines.append(f"% Fallback student ID: {STUDENT_ID_FALLBACK}")
                else:
                    out_val = single_item.expected_output
                lines.append(f"fprintf('%s', {escape_matlab_str(out_val)});")
            else:
                lines.append("_ag_in = strtrim(char(fread(stdin, Inf, 'char')'));")
                for idx, (item, item_script) in enumerate(output_items):
                    cond = f"strcmp(_ag_in, {escape_matlab_str(item.expected_input.strip())})"
                    if item_script:
                        out_val = eval_expected_output_script(
                            item_script,
                            student_id=str(STUDENT_ID_FALLBACK),
                            expected_input=item.expected_input,
                        )
                    else:
                        out_val = item.expected_output
                    branch = "if" if idx == 0 else "elseif"
                    lines.append(f"{branch} ({cond})")
                    if item_script:
                        lines.append(f"    % Fallback student ID: {STUDENT_ID_FALLBACK}")
                    lines.append(f"    fprintf('%s', {escape_matlab_str(out_val)});")
                if len(output_items) > 1:
                    first_item, first_script = output_items[0]
                    default_out = (
                        eval_expected_output_script(
                            first_script,
                            student_id=str(STUDENT_ID_FALLBACK),
                            expected_input=first_item.expected_input,
                        )
                        if first_script
                        else first_item.expected_output
                    )
                    lines.append("else")
                    if first_script:
                        lines.append(f"    % Fallback student ID: {STUDENT_ID_FALLBACK}")
                    lines.append(f"    fprintf('%s', {escape_matlab_str(default_out)});")
                lines.append("end")
        else:
            lines.append("fprintf('wrong_output\\n');")

    if any(item_script for _, item_script in output_items):
        lines.insert(0, f"% Fallback student ID: {STUDENT_ID_FALLBACK}")
    return "\n".join(lines) + "\n"
