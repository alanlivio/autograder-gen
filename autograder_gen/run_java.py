from pathlib import Path
import re
from typing import Union, Optional
import os
import subprocess
import logging

try:
    from run_shared import StudentMessage
except ImportError:
    from autograder_gen.run_shared import StudentMessage

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
