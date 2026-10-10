from pathlib import Path
import re
from typing import Union, Optional
import json
import os
import math
import subprocess


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
        print("[INFO] Couldn't find student ID in GradeScope metadata; using classlist.")
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

        if email and chosen_classlist:
            with chosen_classlist.open(encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if email in line:
                        class_entry = line
                        break

        match = re.search(r"(\d+)", class_entry) if class_entry else None
        if match:
            student_id = match.group(1)
        else:
            print(f"[INFO] Couldn't find e-mail in classlist, so using {default_id}.")
            student_id = default_id

    if not student_id.strip():
        student_id = default_id

    print(f"[INFO] Your student ID: {student_id}\n")
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


JAVA_RUNNER_CODE = r"""import java.lang.reflect.Method;
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
        Class<?> clazz = Class.forName(className);
        Method targetMethod = null;
        Object[] methodArgs = new Object[args.length - 2];
        for (int i = 2; i < args.length; i++) {
            methodArgs[i - 2] = args[i];
        }
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
        Object instance = null;
        if (!java.lang.reflect.Modifier.isStatic(targetMethod.getModifiers())) {
            instance = clazz.getDeclaredConstructor().newInstance();
        }
        Object result = null;
        if (targetMethod.getParameterCount() == methodArgs.length) {
            Class<?>[] paramTypes = targetMethod.getParameterTypes();
            Object[] convertedArgs = new Object[methodArgs.length];
            for (int i = 0; i < methodArgs.length; i++) {
                convertedArgs[i] = convertArg(methodArgs[i].toString(), paramTypes[i]);
            }
            result = targetMethod.invoke(instance, convertedArgs);
        } else if (targetMethod.getParameterCount() == 1 && targetMethod.getParameterTypes()[0].isArray()) {
            Class<?> compType = targetMethod.getParameterTypes()[0].getComponentType();
            Object arr = java.lang.reflect.Array.newInstance(compType, methodArgs.length);
            for (int i = 0; i < methodArgs.length; i++) {
                java.lang.reflect.Array.set(arr, i, convertArg(methodArgs[i].toString(), compType));
            }
            result = targetMethod.invoke(instance, new Object[]{arr});
        } else {
            result = targetMethod.invoke(instance, methodArgs);
        }
        if (result != null) {
            if (result.getClass().isArray()) {
                if (result instanceof Object[]) {
                    System.out.print(Arrays.deepToString((Object[]) result));
                } else if (result instanceof int[]) {
                    System.out.print(Arrays.toString((int[]) result));
                } else if (result instanceof double[]) {
                    System.out.print(Arrays.toString((double[]) result));
                } else if (result instanceof long[]) {
                    System.out.print(Arrays.toString((long[]) result));
                } else if (result instanceof boolean[]) {
                    System.out.print(Arrays.toString((boolean[]) result));
                } else if (result instanceof byte[]) {
                    System.out.print(Arrays.toString((byte[]) result));
                } else if (result instanceof char[]) {
                    System.out.print(Arrays.toString((char[]) result));
                } else if (result instanceof float[]) {
                    System.out.print(Arrays.toString((float[]) result));
                } else if (result instanceof short[]) {
                    System.out.print(Arrays.toString((short[]) result));
                }
            } else {
                System.out.print(result.toString());
            }
        }
    }

    private static Object convertArg(String val, Class<?> targetType) {
        if (targetType.isArray()) {
            Class<?> componentType = targetType.getComponentType();
            String s = val.trim();
            if ((s.startsWith("{") && s.endsWith("}")) || (s.startsWith("[") && s.endsWith("]"))) {
                s = s.substring(1, s.length() - 1).trim();
            }
            if (s.isEmpty()) {
                return java.lang.reflect.Array.newInstance(componentType, 0);
            }
            List<String> items = new ArrayList<>();
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
            Object arr = java.lang.reflect.Array.newInstance(componentType, items.size());
            for (int i = 0; i < items.size(); i++) {
                java.lang.reflect.Array.set(arr, i, convertArg(items.get(i), componentType));
            }
            return arr;
        }
        if (targetType == List.class || targetType == ArrayList.class) {
            String s = val.trim();
            if ((s.startsWith("[") && s.endsWith("]")) || (s.startsWith("{") && s.endsWith("}"))) {
                s = s.substring(1, s.length() - 1).trim();
            }
            ArrayList<String> list = new ArrayList<>();
            if (s.isEmpty()) return list;
            int depth = 0;
            StringBuilder cur = new StringBuilder();
            for (int i = 0; i < s.length(); i++) {
                char c = s.charAt(i);
                if (c == '{' || c == '[') depth++;
                else if (c == '}' || c == ']') depth--;
                if (c == ',' && depth == 0) {
                    String it = cur.toString().trim();
                    if ((it.startsWith("\"") && it.endsWith("\"")) || (it.startsWith("'") && it.endsWith("'"))) {
                        it = it.substring(1, it.length() - 1);
                    }
                    list.add(it);
                    cur.setLength(0);
                } else {
                    cur.append(c);
                }
            }
            if (cur.length() > 0) {
                String it = cur.toString().trim();
                if ((it.startsWith("\"") && it.endsWith("\"")) || (it.startsWith("'") && it.endsWith("'"))) {
                    it = it.substring(1, it.length() - 1);
                }
                list.add(it);
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
        if (targetType == char.class || targetType == Character.class) return val.trim().isEmpty() ? ' ' : val.trim().charAt(0);
        if (targetType == String.class) {
            String s = val.trim();
            if ((s.startsWith("\"") && s.endsWith("\"")) || (s.startsWith("'") && s.endsWith("'"))) {
                s = s.substring(1, s.length() - 1);
            }
            return s;
        }
        return val;
    }
}
"""


def ensure_java_runner(source_dir: Union[str, Path], classpath: Optional[str] = None) -> Path:
    s_dir = Path(source_dir)
    runner_path = s_dir / "JavaRunner.java"
    if not runner_path.exists():
        runner_path.write_text(JAVA_RUNNER_CODE, encoding="utf-8")
        cp = classpath if classpath else f"{s_dir}{os.pathsep}."
        subprocess.run(
            ["javac", "-cp", cp, "JavaRunner.java"],
            capture_output=True,
            text=True,
            cwd=s_dir,
            check=True,
        )
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

    ensure_java_runner(s_dir, classpath)

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
        raise RuntimeError(f"Error executing {function_name}: {res.stderr}")
    return res.stdout
