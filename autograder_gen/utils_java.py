from __future__ import annotations

import json
import logging
import os
import re
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Union

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


def remove_package_line(path: Union[str, Path]) -> None:
    try:
        p = Path(path)
        if not p.exists() or not p.is_file():
            return
        content = p.read_text(encoding="utf-8", errors="replace")
        new_content = re.sub(
            r"^\s*package\s+[\w.]+\s*;[^\S\r\n]*(//.*)?(\r?\n)?",
            "",
            content,
            flags=re.MULTILINE,
        )
        if new_content != content:
            print(f"[INFO] removing not expected package line from {p.name}.")
            p.write_text(new_content, encoding="utf-8")
    except Exception:
        pass


JAVA_RUNNER_CODE = r"""import java.lang.reflect.Array;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.lang.reflect.Modifier;
import java.util.Arrays;
import java.util.ArrayList;
import java.util.List;

public class JavaRunner {
    public static void main(String[] args) throws Exception {
        if (args.length < 2) {
            System.err.println("Usage: JavaRunner <ClassName> <MethodName> [args...]");
            System.exit(1);
        }
        String className = args[0];
        String methodName = args[1];
        String[] methodArgs = Arrays.copyOfRange(args, 2, args.length);

        Class<?> clazz = Class.forName(className);
        Method targetMethod = null;
        for (Method m : clazz.getDeclaredMethods()) {
            if (m.getName().equals(methodName)) {
                if (m.getParameterCount() == methodArgs.length) {
                    targetMethod = m;
                    break;
                }
                if (targetMethod == null) {
                    targetMethod = m;
                }
            }
        }
        if (targetMethod == null) {
            System.err.println("Method " + methodName + " not found in " + className);
            System.exit(1);
        }
        targetMethod.setAccessible(true);
        Object instance = Modifier.isStatic(targetMethod.getModifiers())
                ? null
                : clazz.getDeclaredConstructor().newInstance();

        boolean captureOutput = Boolean.getBoolean("autograder.captureOutput");
        java.io.PrintStream originalOut = System.out;
        if (!captureOutput) {
            System.setOut(new java.io.PrintStream(new java.io.OutputStream() {
                @Override
                public void write(int b) {}
            }));
        }

        Object result;
        try {
            if (targetMethod.getParameterCount() == methodArgs.length) {
                Class<?>[] paramTypes = targetMethod.getParameterTypes();
                Object[] convertedArgs = new Object[methodArgs.length];
                for (int i = 0; i < methodArgs.length; i++) {
                    convertedArgs[i] = convertArg(methodArgs[i], paramTypes[i]);
                }
                result = targetMethod.invoke(instance, convertedArgs);
            } else if (targetMethod.getParameterCount() == 1 && targetMethod.getParameterTypes()[0].isArray()) {
                Class<?> compType = targetMethod.getParameterTypes()[0].getComponentType();
                Object arr = Array.newInstance(compType, methodArgs.length);
                for (int i = 0; i < methodArgs.length; i++) {
                    Array.set(arr, i, convertArg(methodArgs[i], compType));
                }
                result = targetMethod.invoke(instance, new Object[]{arr});
            } else {
                result = targetMethod.invoke(instance, (Object[]) methodArgs);
            }
        } catch (InvocationTargetException e) {
            Throwable cause = e.getCause() != null ? e.getCause() : e;
            System.err.println(cause.getClass().getName() + ": " + cause.getMessage());
            cause.printStackTrace(System.err);
            System.exit(1);
            return;
        } catch (Throwable t) {
            System.err.println("[JAVARUNNER_ERROR] " + t.getMessage());
            t.printStackTrace(System.err);
            System.exit(2);
            return;
        } finally {
            System.setOut(originalOut);
        }

        if (!captureOutput && result != null) {
            System.out.print(formatResult(result));
        }
    }

    private static String formatResult(Object val) {
        if (val == null) return "null";
        if (val.getClass().isArray()) {
            int len = Array.getLength(val);
            StringBuilder sb = new StringBuilder("[");
            for (int i = 0; i < len; i++) {
                if (i > 0) sb.append(", ");
                sb.append(formatResult(Array.get(val, i)));
            }
            return sb.append("]").toString();
        }
        return val.toString();
    }

    private static String unquote(String s) {
        s = s.trim();
        if ((s.startsWith("\"") && s.endsWith("\"")) || (s.startsWith("'") && s.endsWith("'"))) {
            return s.substring(1, s.length() - 1);
        }
        return s;
    }

    private static List<String> splitItems(String s) {
        s = s.trim();
        if ((s.startsWith("{") && s.endsWith("}")) || (s.startsWith("[") && s.endsWith("]"))) {
            s = s.substring(1, s.length() - 1).trim();
        }
        List<String> items = new ArrayList<>();
        if (s.isEmpty()) return items;
        int depth = 0;
        StringBuilder cur = new StringBuilder();
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            if (c == '{' || c == '[') depth++;
            else if (c == '}' || c == ']') depth--;
            if (c == ',' && depth == 0) {
                items.add(cur.toString().trim());
                cur.setLength(0);
            } else {
                cur.append(c);
            }
        }
        if (cur.length() > 0) items.add(cur.toString().trim());
        return items;
    }

    private static Object convertArg(String val, Class<?> targetType) {
        if (targetType.isArray()) {
            Class<?> comp = targetType.getComponentType();
            List<String> items = splitItems(val);
            Object arr = Array.newInstance(comp, items.size());
            for (int i = 0; i < items.size(); i++) {
                Array.set(arr, i, convertArg(items.get(i), comp));
            }
            return arr;
        }
        if (targetType == List.class || targetType == ArrayList.class) {
            List<String> items = splitItems(val);
            List<String> list = new ArrayList<>();
            for (String item : items) {
                list.add(unquote(item));
            }
            return list;
        }
        if (targetType == int.class || targetType == Integer.class) {
            try { return Integer.parseInt(val.trim()); }
            catch (NumberFormatException e) { return (int) Double.parseDouble(val.trim()); }
        }
        if (targetType == double.class || targetType == Double.class) return Double.parseDouble(val.trim());
        if (targetType == boolean.class || targetType == Boolean.class) return Boolean.parseBoolean(val.trim());
        if (targetType == long.class || targetType == Long.class) {
            try { return Long.parseLong(val.trim()); }
            catch (NumberFormatException e) { return (long) Double.parseDouble(val.trim()); }
        }
        if (targetType == float.class || targetType == Float.class) return Float.parseFloat(val.trim());
        if (targetType == char.class || targetType == Character.class) {
            String s = unquote(val);
            return s.isEmpty() ? ' ' : s.charAt(0);
        }
        if (targetType == String.class) return unquote(val);
        return val;
    }
}
"""


def ensure_java_runner(source_dir: Union[str, Path], classpath: Optional[str] = None) -> Path:
    s_dir = Path(source_dir)
    runner_path = s_dir / "JavaRunner.java"
    class_file = s_dir / "JavaRunner.class"
    if not runner_path.exists():
        runner_path.write_text(JAVA_RUNNER_CODE, encoding="utf-8")
    if not class_file.exists():
        cp = classpath if classpath else f"{s_dir}{os.pathsep}."
        compile_res = subprocess.run(
            ["javac", "-cp", cp, "JavaRunner.java"],
            capture_output=True,
            text=True,
            cwd=s_dir,
        )
        if compile_res.returncode != 0:
            err = compile_res.stderr or compile_res.stdout
            logger.error("JavaRunner compilation failed: %s", err)
            raise RuntimeError("Internal runner error")
    return runner_path


def call_java_function(
    file_path: Union[str, Path],
    function_name: str,
    args: list,
    timeout_seconds: int,
    source_dir: Union[str, Path],
    remove_package: bool = False,
    capture_output: bool = False,
) -> str:
    path = Path(file_path)
    s_dir = Path(source_dir)
    if not path.exists():
        raise AssertionError(StudentMessage.WRONG_FILE.format(file_name=path.name))
    if remove_package:
        remove_package_line(path)

    target_dir = path.parent
    classpath = f"{target_dir}{os.pathsep}{s_dir}{os.pathsep}."
    compile_res = subprocess.run(
        ["javac", "-cp", classpath, str(path)],
        capture_output=True,
        text=True,
        cwd=s_dir,
    )
    if compile_res.returncode != 0:
        err = compile_res.stderr or compile_res.stdout
        if err:
            print(StudentMessage.COMPILING)
            print(err.strip())
        raise AssertionError(StudentMessage.COMPILATION_ERROR)

    try:
        ensure_java_runner(s_dir, classpath)
    except Exception as e:
        if not isinstance(e, RuntimeError):
            logger.error("JavaRunner setup failed: %s", e)
        raise RuntimeError("Internal runner error") from None

    class_name = path.stem
    jvm_flags = ["-Dautograder.captureOutput=true"] if capture_output else []
    cmd = (
        ["java"]
        + jvm_flags
        + ["-cp", classpath, "JavaRunner", class_name, function_name]
        + [str(a) for a in args]
    )
    res = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        cwd=s_dir,
    )
    if res.returncode != 0:
        logger.error("JavaRunner execution failed: %s", res.stderr)
        if (
            res.returncode == 2
            or "[JAVARUNNER_ERROR]" in (res.stderr or "")
            or "Could not find or load main class JavaRunner" in (res.stderr or "")
        ):
            raise RuntimeError("Internal runner error")
        raise RuntimeError(f"Error executing {function_name}: {res.stderr}")
    return res.stdout


def _normalize_java_type(type_str: str) -> str:
    t = type_str.strip()
    t = re.sub(r"\bjava\.lang\.", "", t)
    t = re.sub(r"\bjava\.util\.", "", t)
    return t


def assert_java_function_signature(
    file_path: Union[str, Path],
    function_name: str,
    source_dir: Union[str, Path],
    expected_parameters: Optional[str] = None,
    expected_return_type: Optional[str] = None,
    remove_package: bool = False,
) -> None:
    path = Path(file_path)
    s_dir = Path(source_dir)
    if not path.exists():
        raise AssertionError(StudentMessage.WRONG_FILE.format(file_name=path.name))
    if remove_package:
        remove_package_line(path)

    class_name = path.stem
    target_dir = path.parent
    classpath = f"{target_dir}{os.pathsep}{s_dir}{os.pathsep}."
    compile_res = subprocess.run(
        ["javac", "-cp", classpath, str(path)],
        capture_output=True,
        text=True,
        cwd=s_dir,
    )
    if compile_res.returncode != 0:
        err = compile_res.stderr or compile_res.stdout
        if err:
            print(StudentMessage.COMPILING)
            print(err.strip())
        raise AssertionError(StudentMessage.COMPILATION_ERROR)

    javap_res = subprocess.run(
        ["javap", "-cp", classpath, "-public", class_name],
        capture_output=True,
        text=True,
        cwd=s_dir,
    )
    if javap_res.returncode != 0:
        raise AssertionError(
            StudentMessage.WRONG_FUNCTION_SIGNATURE.format(
                function_name=function_name,
                reason=f"could not inspect Java class '{class_name}'",
            )
        )

    pattern = re.compile(
        rf"^\s*(?:public\s+)?(?:static\s+)?(?:final\s+)?([\w.<>\[\]]+)\s+{re.escape(function_name)}\s*\(([^)]*)\)"
    )
    matched_methods = []
    for line in javap_res.stdout.splitlines():
        m = pattern.search(line)
        if m:
            ret_type = _normalize_java_type(m.group(1))
            raw_params = m.group(2).strip()
            param_types = (
                [_normalize_java_type(p) for p in raw_params.split(",") if p.strip()]
                if raw_params
                else []
            )
            matched_methods.append((ret_type, param_types))

    if not matched_methods:
        if function_name not in javap_res.stdout:
            raise AssertionError(
                StudentMessage.WRONG_FUNCTION_SIGNATURE.format(
                    function_name=function_name,
                    reason=f"method '{function_name}' not found in class '{class_name}'",
                )
            )
        return True

    actual_ret_type, actual_param_types = matched_methods[0]

    if expected_parameters and expected_parameters.strip():
        expected_parts = [p.strip() for p in expected_parameters.split(",") if p.strip()]
        if len(actual_param_types) != len(expected_parts):
            raise AssertionError(
                StudentMessage.WRONG_FUNCTION_SIGNATURE.format(
                    function_name=function_name,
                    reason=f"has {len(actual_param_types)} parameters, expected {len(expected_parts)}",
                )
            )
        for idx, part in enumerate(expected_parts):
            exp_type = None
            if ":" in part:
                _, t_part = part.split(":", 1)
                exp_type = _normalize_java_type(t_part.split("=", 1)[0])
            else:
                tokens = part.split()
                if len(tokens) >= 2:
                    exp_type = _normalize_java_type(tokens[0])
            if exp_type:
                act_type = actual_param_types[idx]
                if act_type.lower() != exp_type.lower():
                    raise AssertionError(
                        StudentMessage.WRONG_FUNCTION_SIGNATURE.format(
                            function_name=function_name,
                            reason=f"parameter {idx + 1} has type '{act_type}', expected '{exp_type}'",
                        )
                    )

    if expected_return_type and expected_return_type.strip():
        exp_ret = _normalize_java_type(expected_return_type)
        if actual_ret_type.lower() != exp_ret.lower():
            raise AssertionError(
                StudentMessage.WRONG_FUNCTION_SIGNATURE.format(
                    function_name=function_name,
                    reason=f"has return type '{actual_ret_type}', expected '{exp_ret}'",
                )
            )
    return True


check_java_function_signature = assert_java_function_signature


def get_java_literal_str(expected_str: str) -> str:
    val_strip = expected_str.strip()
    if val_strip == "True":
        return "true"
    if val_strip == "False":
        return "false"
    if val_strip == "None":
        return "null"
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
    escaped = expected_str.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def infer_java_type(val, desc=""):
    if isinstance(val, bool) or (
        str(val).lower() in ("true", "false") and not isinstance(val, (int, float))
    ):
        return "boolean"
    if isinstance(val, int):
        return "long" if abs(val) > 2147483647 else "int"
    if isinstance(val, float):
        return "double"
    if isinstance(val, list):
        if val and isinstance(val[0], list):
            return "double[][]" if any("." in str(x) for row in val for x in row) else "int[][]"
        is_arraylist = "arraylist" in desc.lower() or "list" in desc.lower()
        has_strings = any(isinstance(x, str) and not x.strip().lstrip("-").isdigit() for x in val)
        if has_strings or any(isinstance(x, str) for x in val):
            if is_arraylist:
                return "java.util.ArrayList<String>"
            return "String[]"
        if is_arraylist:
            return (
                "java.util.ArrayList<Double>"
                if any("." in str(x) for x in val)
                else "java.util.ArrayList<Integer>"
            )
        return "double[]" if any("." in str(x) for x in val) else "int[]"
    s = str(val).strip()
    if (s.startswith("{{") and s.endswith("}}")) or (s.startswith("[[") and s.endswith("]]")):
        return "double[][]" if "." in s else "int[][]"
    if (s.startswith("{") and s.endswith("}")) or (s.startswith("[") and s.endswith("]")):
        is_arraylist = "arraylist" in desc.lower() or "list" in desc.lower()
        inner = s[1:-1].strip()
        has_letters = any(c.isalpha() for c in inner)
        if has_letters:
            if is_arraylist:
                return "java.util.ArrayList<String>"
            return "String[]"
        if is_arraylist:
            return "java.util.ArrayList<Double>" if "." in inner else "java.util.ArrayList<Integer>"
        return "double[]" if "." in s else "int[]"
    try:
        v_int = int(s)
        return "long" if abs(v_int) > 2147483647 else "int"
    except ValueError:
        try:
            float(s)
            return "double"
        except ValueError:
            return "String"


def java_compiler_error_content(target_file: str) -> str:
    class_name = Path(target_file).stem
    return f"public class {class_name} {{\n    public static void syntaxError() {{\n        return 0\n    }}\n}}\n"


def generate_java_skeleton(config: Config, target_file: str, correct: bool = True) -> str:
    class_name = Path(target_file).stem
    lines = [
        "import java.util.*;",
        "import java.nio.file.*;",
        "",
        f"public class {class_name} {{",
        "",
    ]
    functions = set()
    for q in config.questions:
        for item in q.marking_items:
            if item.target_file == target_file:
                if hasattr(item, "function_name") and item.function_name:
                    functions.add(item.function_name)

    for func in sorted(functions):
        func_items = [
            item
            for q in config.questions
            for item in q.marking_items
            if item.target_file == target_file and getattr(item, "function_name", "") == func
        ]
        desc_text = " ".join(
            [getattr(item, "description", "") for item in func_items]
            + [getattr(item, "name", "") for item in func_items]
            + [
                getattr(q, "description", "")
                for q in config.questions
                for item in q.marking_items
                if item in func_items
            ]
        )
        cases = []
        for item in func_items:
            for tc in getattr(item, "test_cases", []) or []:
                cases.append(tc)

        max_args = 0
        for tc in cases:
            args_len = len(tc.get("args", []) or [])
            if args_len > max_args:
                max_args = args_len

        param_types = []
        for i in range(max_args):
            arg_vals = [tc.get("args", [])[i] for tc in cases if len(tc.get("args", []) or []) > i]
            ptype = infer_java_type(arg_vals[0], desc_text) if arg_vals else "Object"
            param_types.append(ptype)

        param_names = [chr(97 + i) for i in range(max_args)]
        param_str = ", ".join(f"{pt} {pn}" for pt, pn in zip(param_types, param_names))

        ret_type = "double"
        if any(getattr(item, "type", "") == "function_output_test" for item in func_items):
            ret_type = "void"
        elif cases:
            exp0 = str(cases[0].get("expected", ""))
            if "\n" in exp0:
                ret_type = "void"
            elif ("arraylist" in desc_text.lower() or "list" in desc_text.lower()) and (
                (exp0.startswith("[") and exp0.endswith("]"))
                or (exp0.startswith("{") and exp0.endswith("}"))
            ):
                inner = exp0[1:-1].strip()
                if any(c.isalpha() for c in inner) or not inner:
                    ret_type = "java.util.ArrayList<String>"
                elif "." in inner:
                    ret_type = "java.util.ArrayList<Double>"
                else:
                    ret_type = "java.util.ArrayList<Integer>"
            elif (exp0.startswith("[") and exp0.endswith("]")) or (
                exp0.startswith("{") and exp0.endswith("}")
            ):
                inner = exp0[1:-1].strip()
                if any(c.isalpha() for c in inner):
                    ret_type = "String[]"
                elif "." in exp0:
                    ret_type = "double[]"
                else:
                    ret_type = "int[]"
            elif exp0.strip().lower() in ("true", "false"):
                ret_type = "boolean"
            else:
                try:
                    v_int = int(exp0.strip())
                    ret_type = "long" if abs(v_int) > 2147483647 else "int"
                except ValueError:
                    try:
                        float(exp0.strip())
                        ret_type = "double"
                    except ValueError:
                        ret_type = "String"

        if func == "add" and max_args == 2:
            lines.append(f"    public static double {func}(double a, double b) {{")
            if correct:
                lines.append("        return a + b;")
            else:
                lines.append("        return 0.0;")
            lines.append("    }")
            lines.append("")
            continue

        lines.append(f"    public static {ret_type} {func}({param_str}) {{")
        if correct:
            for tc in cases:
                args_list = tc.get("args", []) or []
                cond_parts = []
                for idx, arg_val in enumerate(args_list):
                    pn = param_names[idx]
                    pt = param_types[idx]
                    if pt == "double":
                        try:
                            cond_parts.append(f"Math.abs({pn} - {float(arg_val)}) < 1e-4")
                        except Exception:
                            cond_parts.append(f"{pn} == {arg_val}")
                    elif pt in ("int", "long"):
                        cond_parts.append(f"{pn} == {arg_val}")
                    elif pt == "boolean":
                        cond_parts.append(f"{pn} == {str(arg_val).lower()}")
                    elif pt == "String":
                        cond_parts.append(
                            f"{pn} != null && {pn}.equals({json.dumps(str(arg_val))})"
                        )
                    elif pt == "java.util.ArrayList<String>":
                        if isinstance(arg_val, list):
                            items_code = ", ".join(json.dumps(str(x)) for x in arg_val)
                        else:
                            raw = str(arg_val).strip().lstrip("[").rstrip("]").strip()
                            items = [x.strip().strip("'\"") for x in raw.split(",") if x.strip()]
                            items_code = ", ".join(json.dumps(x) for x in items)
                        cond_parts.append(
                            f"{pn} != null && {pn}.equals(new java.util.ArrayList<>(java.util.Arrays.asList({items_code})))"
                        )
                    elif pt == "String[]":
                        if isinstance(arg_val, list):
                            items_code = ", ".join(json.dumps(str(x)) for x in arg_val)
                        else:
                            raw = str(arg_val).strip().lstrip("[").rstrip("]").strip()
                            items = [x.strip().strip("'\"") for x in raw.split(",") if x.strip()]
                            items_code = ", ".join(json.dumps(x) for x in items)
                        cond_parts.append(
                            f"java.util.Arrays.equals({pn}, new String[]{{{items_code}}})"
                        )
                    elif pt.endswith("[][]"):
                        raw_s = str(arg_val).strip()
                        if raw_s.startswith("["):
                            raw_s = raw_s.replace("[", "{").replace("]", "}")
                        cond_parts.append(f"java.util.Arrays.deepEquals({pn}, new {pt}{raw_s})")
                    elif pt.endswith("[]"):
                        raw_s = str(arg_val).strip()
                        if raw_s.startswith("["):
                            raw_s = raw_s.replace("[", "{").replace("]", "}")
                        cond_parts.append(f"java.util.Arrays.equals({pn}, new {pt}{raw_s})")

                cond = " && ".join(cond_parts) if cond_parts else "true"
                exp_val = tc.get("expected", "")
                if ret_type == "void":
                    lines.append(f"        if ({cond}) {{")
                    lines.append(f"            System.out.print({json.dumps(str(exp_val))});")
                    lines.append("            return;")
                    lines.append("        }")
                elif ret_type == "java.util.ArrayList<String>":
                    if isinstance(exp_val, list):
                        items = [str(x) for x in exp_val]
                    else:
                        raw = str(exp_val).strip().lstrip("[").rstrip("]").strip()
                        items = [x.strip().strip("'\"") for x in raw.split(",") if x.strip()]
                    items_code = ", ".join(json.dumps(x) for x in items)
                    lines.append(f"        if ({cond}) {{")
                    lines.append(
                        f"            return new java.util.ArrayList<>(java.util.Arrays.asList({items_code}));"
                    )
                    lines.append("        }")
                elif ret_type == "String[]":
                    if isinstance(exp_val, list):
                        items = [str(x) for x in exp_val]
                    else:
                        raw = str(exp_val).strip().lstrip("[").rstrip("]").strip()
                        items = [x.strip().strip("'\"") for x in raw.split(",") if x.strip()]
                    items_code = ", ".join(json.dumps(x) for x in items)
                    lines.append(f"        if ({cond}) {{")
                    lines.append(f"            return new String[]{{{items_code}}};")
                    lines.append("        }")
                elif ret_type.endswith("[]"):
                    raw_e = str(exp_val).strip()
                    if raw_e.startswith("["):
                        raw_e = raw_e.replace("[", "{").replace("]", "}")
                    lines.append(f"        if ({cond}) {{")
                    lines.append(f"            return new {ret_type}{raw_e};")
                    lines.append("        }")
                elif ret_type == "double":
                    lines.append(f"        if ({cond}) {{")
                    lines.append(f"            return {float(exp_val)};")
                    lines.append("        }")
                elif ret_type in ("int", "long"):
                    lines.append(f"        if ({cond}) {{")
                    lines.append(f"            return {int(exp_val)};")
                    lines.append("        }")
                elif ret_type == "boolean":
                    lines.append(f"        if ({cond}) {{")
                    lines.append(f"            return {str(exp_val).lower()};")
                    lines.append("        }")
                else:
                    lines.append(f"        if ({cond}) {{")
                    lines.append(f"            return {json.dumps(str(exp_val))};")
                    lines.append("        }")

            if ret_type == "void":
                pass
            elif ret_type == "double":
                lines.append("        return 0.0;")
            elif ret_type == "int":
                lines.append("        return 0;")
            elif ret_type == "long":
                lines.append("        return 0L;")
            elif ret_type == "boolean":
                lines.append("        return false;")
            elif ret_type == "java.util.ArrayList<String>":
                lines.append("        return new java.util.ArrayList<>();")
            elif ret_type.endswith("[]"):
                lines.append(f"        return new {ret_type[:-2]}[0];")
            else:
                lines.append('        return "";')
        else:
            if ret_type == "void":
                lines.append('        System.out.print("wrong_output");')
            elif ret_type == "double":
                lines.append("        return -999999.0;")
            elif ret_type == "int":
                lines.append("        return -999999;")
            elif ret_type == "long":
                lines.append("        return -999999L;")
            elif ret_type == "boolean":
                has_false = any(
                    str(tc.get("expected", "")).strip().lower() == "false" for tc in cases
                )
                lines.append(f"        return {'true' if has_false else 'false'};")
            elif ret_type == "java.util.ArrayList<String>":
                lines.append("        return new java.util.ArrayList<>();")
            elif ret_type.endswith("[]"):
                lines.append("        return null;")
            else:
                lines.append('        return "wrong_answer";')
        lines.append("    }")
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
        lines.append("    public static void main(String[] args) {")
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
                    lines.append(f"        // Fallback student ID: {STUDENT_ID_FALLBACK}")
                else:
                    out_val = single_item.expected_output
                lines.append(f"        System.out.print({json.dumps(out_val)});")
            else:
                lines.append("        java.util.Scanner sc = new java.util.Scanner(System.in);")
                lines.append("        StringBuilder sb = new StringBuilder();")
                lines.append("        while (sc.hasNextLine()) {")
                lines.append('            sb.append(sc.nextLine()).append("\\n");')
                lines.append("        }")
                lines.append("        String inStr = sb.toString().trim();")
                for idx, (item, item_script) in enumerate(output_items):
                    cond = f"inStr.equals({json.dumps(item.expected_input.strip())})"
                    has_item_script = bool(item_script)
                    if has_item_script:
                        out_val = eval_expected_output_script(
                            item_script,
                            student_id=str(STUDENT_ID_FALLBACK),
                            expected_input=item.expected_input,
                        )
                    else:
                        out_val = item.expected_output
                    branch = "if" if idx == 0 else "else if"
                    lines.append(f"        {branch} ({cond}) {{")
                    if has_item_script:
                        lines.append(f"            // Fallback student ID: {STUDENT_ID_FALLBACK}")
                    lines.append(f"            System.out.print({json.dumps(out_val)});")
                    lines.append("            return;")
                    lines.append("        }")
                if len(output_items) > 1:
                    first_item, first_script = output_items[0]
                    if first_script:
                        default_out = eval_expected_output_script(
                            first_script,
                            student_id=str(STUDENT_ID_FALLBACK),
                            expected_input=first_item.expected_input,
                        )
                        lines.append("        else {")
                        lines.append(f"            // Fallback student ID: {STUDENT_ID_FALLBACK}")
                        lines.append(f"            System.out.print({json.dumps(default_out)});")
                        lines.append("        }")
                    elif first_item:
                        default_out = first_item.expected_output
                        lines.append("        else {")
                        lines.append(f"            System.out.print({json.dumps(default_out)});")
                        lines.append("        }")
        else:
            lines.append('        System.out.print("wrong_output\\n");')
        lines.append("    }")
        lines.append("")

    lines.append("}")
    if any(item_script for _, item_script in output_items):
        lines.insert(0, f"// Fallback student ID: {STUDENT_ID_FALLBACK}")
    return "\n".join(lines)
