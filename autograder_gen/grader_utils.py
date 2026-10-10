from pathlib import Path
import re
from typing import Union, Optional
import json
import csv
import os
import math
import subprocess
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


def get_student_id(
    autograder_root: Union[str, Path, None] = None,
    classlist_path: Union[str, Path, None] = None,
    default_id: str = "12345678",
) -> str:
    if autograder_root is None and classlist_path is None and os.environ.get("STUDENT_ID"):
        return os.environ["STUDENT_ID"]

    print("[INFO] Checking student ID...")
    root = (
        Path(autograder_root)
        if autograder_root
        else Path(os.environ.get("AUTOGRADER_ROOT", "/autograder"))
    )
    metadata_candidates = [
        root / "submission_metadata.json",
        root / "submission" / "submission_metadata.json",
        root / "source" / "submission_metadata.json",
        Path("submission_metadata.json"),
        Path("source/submission_metadata.json"),
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
    student_id = first_user.get("sid")
    student_id = re.sub(r"\D+", "", str(student_id) if student_id else "")
    email = first_user.get("email")

    if not student_id.strip():
        print("[INFO] Student ID not found in submission metadata; checking classlist.csv...")
        class_entry = ""
        classlist_candidates = [
            Path(classlist_path) if classlist_path else None,
            root / "source" / "classlist.csv",
            root / "classlist.csv",
            Path("source/classlist.csv"),
            Path("classlist.csv"),
        ]
        chosen_classlist = None
        for cp in classlist_candidates:
            if cp and cp.exists():
                chosen_classlist = cp
                break

        if chosen_classlist is None:
            for folder in (root / "source", root, Path("source"), Path(".")):
                if folder.exists() and folder.is_dir():
                    rosters = list(folder.glob("*_roster.csv")) + [
                        p for p in folder.glob("*roster*.csv") if p.name != "classlist.csv"
                    ]
                    if rosters:
                        chosen_classlist = rosters[0]
                        break

        if email and chosen_classlist:
            email_lower = email.strip().lower()
            try:
                with chosen_classlist.open(encoding="utf-8", errors="ignore") as f:
                    reader = csv.DictReader(f)
                    if reader.fieldnames:
                        field_map = {
                            name.strip().lower(): name for name in reader.fieldnames if name
                        }
                        email_col = field_map.get("email") or field_map.get("email address")
                        sid_col = (
                            field_map.get("sid")
                            or field_map.get("spr code")
                            or field_map.get("student id")
                            or field_map.get("id")
                        )
                        if email_col and sid_col:
                            for row in reader:
                                if row.get(email_col, "").strip().lower() == email_lower:
                                    val = row.get(sid_col, "").strip()
                                    val = re.sub(r"\D+", "", val)
                                    if val:
                                        student_id = val
                                        break
            except Exception:
                pass

            if not student_id.strip():
                with chosen_classlist.open(encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        if email_lower in line.lower():
                            class_entry = line
                            break
                match = re.search(r"(\d+)", class_entry) if class_entry else None
                if match:
                    student_id = match.group(1)

        if not student_id.strip():
            print("[INFO] Student not found in classlist.csv; using default ID.")
            student_id = default_id

    if not student_id.strip():
        student_id = default_id

    print(f"[INFO] Using student ID: {student_id}")
    return student_id


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
    INPUT = "### Input:"
    EXPECTED_OUTPUT = "### Expected output:"
    ACTUAL_OUTPUT = "### Actual output:"
    COMPILATION_ERROR = "[COMPILATION_ERROR] Check compile errors above."
    RUNTIME_ERROR = "[RUNTIME_ERROR] Check runtime errors above."
    CORRECT_ANSWER_FILE = StudentMessageStr(
        "[CORRECT_ANSWER] Output matches expected for std output of file {file_name}."
    )
    CORRECT_ANSWER_FUNCTION = StudentMessageStr(
        "[CORRECT_ANSWER] Output matches expected for return of function '{function_name}'."
    )
    WRONG_ANSWER_FILE = StudentMessageStr(
        "[WRONG_ANSWER] Output mismatch for for std output of file '{file_name}'."
    )
    WRONG_ANSWER_FUNCTION = StudentMessageStr(
        "[WRONG_ANSWER] Output mismatch for return of function '{function_name}'."
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
    CORRECT_SIGNATURE = StudentMessageStr(
        "[CORRECT_ANSWER] Function '{function_name}' signature is correct"
    )
    CORRECT_GITLAB_SUBMISSION = "[CORRECT_ANSWER] GitLab repository was found."
    WRONG_GITLAB_NOT_USED = "[WRONG_ANSWER] GitLab repository was not found."


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
        }

        if (result != null) {
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
    cmd = ["java", "-cp", classpath, "JavaRunner", class_name, function_name] + [
        str(a) for a in args
    ]
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
