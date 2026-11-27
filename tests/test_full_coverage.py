import importlib.util
import io
import json
import runpy
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

import autograder_gen as ag
from autograder_gen import cli_gen, cli_run
from autograder_gen.utils_java import (
    assert_java_function_signature,
    call_java_function,
    generate_java_skeleton,
    remove_package_line,
)
from autograder_gen.utils_matlab import call_matlab_function, generate_matlab_skeleton
from autograder_gen.utils_python import (
    _split_top_level_params,
    call_function_output_with_timeout,
    import_function_from_file,
)
from autograder_gen.version import __version__
from autograder_gen.web.app import app

SIMPLE_CFG = {
    "version": __version__,
    "language": "python",
    "required_submission_files": ["solution.py"],
    "questions": [
        {
            "name": "Q1",
            "marking_items": [
                {
                    "name": "Output",
                    "target_file": "solution.py",
                    "total_mark": 10,
                    "type": "program_output_test",
                    "expected_output": "hello",
                }
            ],
        }
    ],
}


def test_entrypoints_and_main_guards(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["autograder-gen", "--version"])
    with pytest.raises(SystemExit) as exc_pkg:
        runpy.run_module("autograder_gen", run_name="__main__")
    assert exc_pkg.value.code == 0

    parent_dir = str(Path(cli_gen.__file__).resolve().parent.parent)
    orig_sys_path = list(sys.path)
    try:
        sys.path[:] = [p for p in sys.path if p != parent_dir]
        sys.path.append(parent_dir)
        monkeypatch.setattr(sys, "argv", ["autograder-gen", "--version"])
        with pytest.raises(SystemExit) as exc_cli_gen:
            runpy.run_path(str(Path(cli_gen.__file__)), run_name="__main__")
        assert exc_cli_gen.value.code == 0

        sys.path[:] = [p for p in orig_sys_path if p != parent_dir]
        monkeypatch.setattr(sys, "argv", ["autograder-gen", "--version"])
        with pytest.raises(SystemExit):
            runpy.run_path(str(Path(cli_gen.__file__)), run_name="__main__")

        sys.path[:] = [p for p in orig_sys_path if p != parent_dir]
        monkeypatch.setattr(sys, "argv", ["autograder-run", "--version"])
        with pytest.raises(SystemExit):
            runpy.run_path(str(Path(cli_run.__file__)), run_name="__main__")
    finally:
        sys.path[:] = orig_sys_path

    runpy.run_path(str(Path(ag.__file__).resolve().parent / "config.py"), run_name="__main__")

    import flask

    ran_web = {}
    monkeypatch.setattr(flask.Flask, "run", lambda self, **kw: ran_web.update(kw))
    monkeypatch.setattr(sys, "argv", ["autograder-gen-web", "--no-debug"])
    runpy.run_path(str(Path(ag.__file__).resolve().parent / "web" / "app.py"), run_name="__main__")
    assert ran_web["debug"] is False

    import gunicorn.app.wsgiapp as gunicorn_wsgi

    ran_gunicorn = {}
    monkeypatch.setattr(
        gunicorn_wsgi, "run", lambda: ran_gunicorn.setdefault("argv", list(sys.argv))
    )
    monkeypatch.setattr(sys, "argv", ["run_dev_wsgi.py", "0.0.0.0:9001"])
    runpy.run_path(
        str(Path(ag.__file__).resolve().parent / "web" / "wsgi" / "run_dev_wsgi.py"),
        run_name="__main__",
    )
    assert "0.0.0.0:9001" in ran_gunicorn["argv"]


def test_autograder_gen_remaining_branches(tmp_path: Path, monkeypatch):
    cfg_dict = {
        "version": __version__,
        "language": "python",
        "required_submission_files": ["solution.py"],
        "questions": [
            {
                "name": "Edge Names",
                "marking_items": [
                    {
                        "name": "()",
                        "target_file": "solution.py",
                        "total_mark": 2,
                        "type": "program_output_test",
                        "expected_output": "a",
                    },
                    {
                        "name": "dup",
                        "target_file": "solution.py",
                        "total_mark": 2,
                        "type": "program_output_test",
                        "expected_output": "b",
                    },
                    {
                        "name": "dup_4",
                        "target_file": "solution.py",
                        "total_mark": 2,
                        "type": "program_output_test",
                        "expected_output": "c",
                    },
                    {
                        "name": "dup",
                        "target_file": "solution.py",
                        "total_mark": 2,
                        "type": "program_output_test",
                        "expected_output": "d",
                    },
                ],
            }
        ],
    }
    cfg = ag.Config.model_validate(cfg_dict)
    gen = ag.AutograderGen(cfg, cfg_dict, base_dir=tmp_path)
    monkeypatch.setattr(
        gen,
        "verify_autograder_zip",
        lambda _p: {"valid": False, "errors": ["synthetic error"], "warnings": []},
    )
    gen.generate(str(tmp_path / "out_err"))

    fake_cfg = SimpleNamespace(
        language="custom",
        questions=[],
        required_submission_files=[],
        required_autograder_files=[],
        setup_commands=[],
        excluded_student_ids=[],
        strict_file_location=False,
        wrong_file_location_deduction=0.0,
        remove_use_of_java_package=False,
    )
    gen_custom = ag.AutograderGen(fake_cfg)
    assert gen_custom._generate_skeleton_content("foo.txt") == "# Skeleton for foo.txt"
    gen_custom.temp_dir = tmp_path / "custom_tmp"
    gen_custom.temp_dir.mkdir()
    gen_custom._generate_run_tests()
    assert (gen_custom.temp_dir / "utils_python.py").exists()
    assert (gen_custom.temp_dir / "utils_java.py").exists()
    assert (gen_custom.temp_dir / "utils_matlab.py").exists()


def test_config_remaining_branches(tmp_path: Path, monkeypatch):
    pkg_dir = tmp_path / "pkg_dir.yaml"
    pkg_dir.mkdir()
    with pytest.raises(ValueError, match="Error parsing configuration"):
        ag.Config.parse(pkg_dir)

    real_exists = Path.exists
    real_open = open
    sample_yaml = yaml.dump(SIMPLE_CFG)

    def fake_exists(self: Path) -> bool:
        s = str(self)
        if "tests/examples" in s:
            return False
        if "autograder_gen/examples/python/config.yaml" in s:
            return True
        return real_exists(self)

    def fake_open(file, *args, **kwargs):
        if "autograder_gen/examples/python/config.yaml" in str(file):
            return io.StringIO(sample_yaml)
        return real_open(file, *args, **kwargs)

    monkeypatch.setattr(Path, "exists", fake_exists)
    monkeypatch.setattr("builtins.open", fake_open)
    loaded = ag.Config.get_example_config_yaml("python")
    assert "language: python" in loaded


def test_cli_gen_and_cli_run_remaining_branches(tmp_path: Path, monkeypatch):
    proj_dir = tmp_path / "proj"
    proj_dir.mkdir()
    (proj_dir / "config.yaml").write_text(yaml.dump(SIMPLE_CFG), encoding="utf-8")
    monkeypatch.chdir(proj_dir)
    assert cli_gen.main(["--description"]) == 0
    assert (proj_dir / "description.docx").exists()

    assert cli_run.main(["--"]) == 0

    nested_root = tmp_path / "nested_root"
    nested_sub = nested_root / "hw1"
    nested_sub.mkdir(parents=True)
    (nested_sub / "config.yaml").write_text(yaml.dump(SIMPLE_CFG), encoding="utf-8")
    monkeypatch.chdir(nested_root)
    assert cli_run.main([]) == 0
    assert cli_run.main(["--"]) == 0

    empty_dir = tmp_path / "empty_cli_run"
    empty_dir.mkdir()
    monkeypatch.chdir(empty_dir)
    assert cli_run.main(["--"]) == 2


def test_autograder_run_remaining_branches(tmp_path: Path, monkeypatch):
    dir_cfg = tmp_path / "cfg_folder"
    dir_cfg.mkdir()
    runner_dir = ag.AutograderRun(dir_cfg, save_log=False)
    monkeypatch.setattr(
        runner_dir,
        "_execute",
        lambda _s, _r: {"tests": [{"name": "T1", "score": 5, "max_score": 5, "output": "ok"}]},
    )
    res_dir = runner_dir.run_autograder_for_submission(None, expected_score=5)
    assert res_dir["tests"][0]["score"] == 5

    res_max = runner_dir.run_autograder_for_submission(None)
    assert res_max["tests"][0]["max_score"] == 5

    log_is_dir = tmp_path / "dir_as_log"
    log_is_dir.mkdir()
    runner_dir.run_autograder_for_submission(None, log_path=log_is_dir)

    def _boom(_s, _r):
        raise RuntimeError("exec fail")

    monkeypatch.setattr(runner_dir, "_execute", _boom)
    with pytest.raises(RuntimeError, match="exec fail"):
        runner_dir.run_autograder_for_submission(None, log_path=log_is_dir)

    named_cfg = SimpleNamespace(name="NamedAssessment")
    runner_named = ag.AutograderRun(named_cfg, save_log=False)
    monkeypatch.setattr(runner_named, "_execute", lambda _s, _r: {"tests": []})
    assert runner_named.run_autograder_for_submission(None)["tests"] == []

    runner_dict = ag.AutograderRun(SIMPLE_CFG, save_log=False)
    monkeypatch.setattr(runner_dict, "_execute", lambda _s, _r: {"tests": []})
    runner_dict.run_autograder_for_submission(None)

    assert zipfile.is_zipfile(io.BytesIO(runner_dict._get_wrong_answer_zip_bytes()))
    assert zipfile.is_zipfile(io.BytesIO(runner_dict._get_compiler_error_zip_bytes()))
    assert zipfile.is_zipfile(io.BytesIO(runner_dict._get_wrong_file_location_zip_bytes()))

    empty_req_runner = ag.AutograderRun(
        {
            "version": __version__,
            "language": "python",
            "questions": [
                {
                    "name": "Q1",
                    "marking_items": [{"total_mark": 5, "type": "manual_review"}],
                }
            ],
        },
        save_log=False,
    )
    assert empty_req_runner._get_fallback_file_check_lines(None) == []

    script_cfg = {
        "version": __version__,
        "language": "python",
        "required_submission_files": ["solution.py"],
        "questions": [
            {
                "name": "Q1",
                "expected_output_script": "print(STUDENT_ID)",
                "marking_items": [
                    {
                        "target_file": "solution.py",
                        "total_mark": 5,
                        "type": "program_output_test",
                    }
                ],
            }
        ],
    }
    ag_root_meta = tmp_path / "ag_root_meta"
    ag_root_meta.mkdir()
    (ag_root_meta / "submission_metadata.json").write_text("{corrupt", encoding="utf-8")
    monkeypatch.setenv("AUTOGRADER_ROOT", str(ag_root_meta))
    runner_meta = ag.AutograderRun(script_cfg, autograder_root=ag_root_meta, save_log=False)
    lines = runner_meta._get_fallback_file_check_lines(ag_root_meta)
    assert any("Student ID not found" in line for line in lines)

    sub_zip = tmp_path / "sub_err.zip"
    with zipfile.ZipFile(sub_zip, "w") as zf:
        zf.writestr("solution.py", "print(1)\n")
    real_zipfile = zipfile.ZipFile

    def _bad_zip(*_a, **_kw):
        raise OSError("zip read error")

    monkeypatch.setattr(zipfile, "ZipFile", _bad_zip)
    runner_meta._get_fallback_file_check_lines(sub_zip)
    monkeypatch.setattr(zipfile, "ZipFile", real_zipfile)

    monkeypatch.setattr(
        Path, "rglob", lambda _self, _pat: (_ for _ in ()).throw(OSError("rglob err"))
    )
    runner_meta._get_fallback_file_check_lines(ag_root_meta)

    unreadable_fc_zip = tmp_path / "unreadable_fc.zip"
    with zipfile.ZipFile(unreadable_fc_zip, "w") as zf:
        zf.writestr(
            "run_autograder",
            "#!/bin/bash\n"
            'mkdir -p "$AUTOGRADER_ROOT/results/file_check.log"\n'
            'echo \'{"tests": []}\' > "$AUTOGRADER_ROOT/results/results.json"\n',
        )
    runner_fc = ag.AutograderRun(unreadable_fc_zip, save_log=False)
    res_fc = runner_fc.run_autograder_for_submission(None)
    assert "_file_check_log" not in res_fc


def test_utils_python_remaining_branches(tmp_path: Path, monkeypatch):
    def outer_printer():
        sys.stdout.flush()
        _ = sys.stdout.encoding
        inner = call_function_output_with_timeout(
            lambda: print("inner", end=""), [], {}, timeout_seconds=5
        )
        print(f"outer:{inner}", end="")

    out = call_function_output_with_timeout(outer_printer, [], {}, timeout_seconds=5)
    assert out == "outer:inner"

    mod_imp_err = tmp_path / "imp_err.py"
    mod_imp_err.write_text("import nonexistent_module_xyz_999\n", encoding="utf-8")
    with pytest.raises(ImportError):
        import_function_from_file(mod_imp_err, "fn")

    monkeypatch.setattr(importlib.util, "spec_from_file_location", lambda *_a, **_kw: None)
    with pytest.raises(ImportError, match="Could not load module"):
        import_function_from_file(mod_imp_err, "fn")

    parsed = _split_top_level_params(r'a: str = "x\"y,z", b: int = 1')
    assert parsed == [r'a: str = "x\"y,z"', "b: int = 1"]


def test_utils_matlab_remaining_branches(tmp_path: Path, monkeypatch):
    m_file = tmp_path / "fake.m"
    m_file.write_text("1;\n", encoding="utf-8")

    monkeypatch.setattr("autograder_gen.utils_matlab._check_matlab_syntax", lambda *_a: None)
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *_a, **_kw: SimpleNamespace(
            returncode=1, stdout="", stderr="parse error near line 1"
        ),
    )
    with pytest.raises(AssertionError, match="COMPILATION_ERROR"):
        call_matlab_function(m_file, "fn", [], 5, tmp_path)

    cfg_static = ag.Config.model_validate(
        {
            "version": __version__,
            "language": "matlab",
            "required_submission_files": ["static.m"],
            "questions": [
                {
                    "name": "Static",
                    "marking_items": [
                        {
                            "target_file": "static.m",
                            "total_mark": 5,
                            "type": "program_output_test",
                            "expected_output": "hello",
                        }
                    ],
                }
            ],
        }
    )
    assert "hello" in generate_matlab_skeleton(cfg_static, "static.m", correct=True)

    cfg_multi_script = ag.Config.model_validate(
        {
            "version": __version__,
            "language": "matlab",
            "required_submission_files": ["multi_script.m"],
            "questions": [
                {
                    "name": "MultiScript",
                    "marking_items": [
                        {
                            "target_file": "multi_script.m",
                            "total_mark": 5,
                            "type": "program_output_test",
                            "expected_input": "a",
                            "expected_output_script": "print('first')",
                        },
                        {
                            "target_file": "multi_script.m",
                            "total_mark": 5,
                            "type": "program_output_test",
                            "expected_input": "b",
                            "expected_output": "second",
                        },
                    ],
                }
            ],
        }
    )
    multi_src = generate_matlab_skeleton(cfg_multi_script, "multi_script.m", correct=True)
    assert "Fallback student ID:" in multi_src


@pytest.mark.skipif(shutil.which("javac") is None, reason="javac is not installed")
def test_utils_java_remaining_branches(tmp_path: Path, monkeypatch):
    f = tmp_path / "PkgTest.java"
    f.write_text(
        "package foo;\npublic class PkgTest { public static int f() { return 1; } }\n",
        encoding="utf-8",
    )

    real_read_text = Path.read_text
    monkeypatch.setattr(Path, "read_text", lambda *_a, **_kw: (_ for _ in ()).throw(OSError("io")))
    remove_package_line(f)
    monkeypatch.setattr(Path, "read_text", real_read_text)

    assert call_java_function(f, "f", [], 10, tmp_path, remove_package=True).strip() == "1"

    monkeypatch.setattr(
        "autograder_gen.utils_java.ensure_java_runner",
        lambda *_a, **_kw: (_ for _ in ()).throw(OSError("runner boom")),
    )
    with pytest.raises(RuntimeError, match="Internal runner error"):
        call_java_function(f, "f", [], 10, tmp_path)

    real_subproc_run = subprocess.run

    def _javap_fail(cmd, *args, **kwargs):
        if cmd and cmd[0] == "javap":
            return SimpleNamespace(returncode=1, stdout="", stderr="javap error")
        return real_subproc_run(cmd, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", _javap_fail)
    with pytest.raises(AssertionError, match="could not inspect Java class"):
        assert_java_function_signature(f, "f", tmp_path)

    def _javap_mention_only(cmd, *args, **kwargs):
        if cmd and cmd[0] == "javap":
            return SimpleNamespace(
                returncode=0,
                stdout="public class PkgTest {\n  // mentions specialFn\n}\n",
                stderr="",
            )
        return real_subproc_run(cmd, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", _javap_mention_only)
    assert assert_java_function_signature(f, "specialFn", tmp_path) is True
    monkeypatch.setattr(subprocess, "run", real_subproc_run)

    rich_cfg = ag.Config.model_validate(
        {
            "version": __version__,
            "language": "java",
            "required_submission_files": ["Rich.java"],
            "questions": [
                {
                    "name": "Rich Java",
                    "marking_items": [
                        {
                            "target_file": "Rich.java",
                            "total_mark": 1,
                            "type": "function_signature_test",
                            "function_name": "colonSig",
                            "expected_parameters": "a: int, bareParam",
                            "expected_return_type": "String",
                        },
                        {
                            "target_file": "Rich.java",
                            "total_mark": 1,
                            "type": "function_return_test",
                            "function_name": "multiLineRet",
                            "test_cases": [{"args": [1], "expected": "line1\nline2"}],
                        },
                        {
                            "target_file": "Rich.java",
                            "total_mark": 1,
                            "type": "function_return_test",
                            "function_name": "doubleArrRet",
                            "test_cases": [{"args": [[1, 2]], "expected": "[1.5, 2.5]"}],
                        },
                        {
                            "target_file": "Rich.java",
                            "total_mark": 1,
                            "type": "function_return_test",
                            "function_name": "doubleRet",
                            "test_cases": [
                                {"args": [1.5], "expected": "2.5"},
                                {"args": ["not_a_float"], "expected": "3.5"},
                            ],
                        },
                        {
                            "target_file": "Rich.java",
                            "total_mark": 1,
                            "type": "function_return_test",
                            "function_name": "intRet",
                            "test_cases": [{"args": [1], "expected": "2"}],
                        },
                        {
                            "target_file": "Rich.java",
                            "total_mark": 1,
                            "type": "function_return_test",
                            "function_name": "strRet",
                            "test_cases": [{"args": ["a"], "expected": "hello_str"}],
                        },
                        {
                            "target_file": "Rich.java",
                            "total_mark": 1,
                            "type": "function_return_test",
                            "function_name": "listStrFromStr",
                            "name": "ArrayList string item",
                            "test_cases": [{"args": ["[a, b]"], "expected": ["x", "y"]}],
                        },
                        {
                            "target_file": "Rich.java",
                            "total_mark": 1,
                            "type": "function_return_test",
                            "function_name": "listIntFromList",
                            "name": "ArrayList int item",
                            "test_cases": [{"args": [[1, 2]], "expected": [3, 4]}],
                        },
                        {
                            "target_file": "Rich.java",
                            "total_mark": 1,
                            "type": "function_return_test",
                            "function_name": "strArrFromStr",
                            "test_cases": [{"args": ["[a, b]"], "expected": ["x", "y"]}],
                        },
                        {
                            "target_file": "Rich.java",
                            "total_mark": 1,
                            "type": "function_return_test",
                            "function_name": "mat2dRet",
                            "test_cases": [{"args": ["{1, 2}"], "expected": "{{1, 2}, {3, 4}}"}],
                        },
                        {
                            "target_file": "Rich.java",
                            "total_mark": 1,
                            "type": "function_signature_test",
                            "function_name": "mat2dSig",
                            "expected_parameters": "int x",
                            "expected_return_type": "int[][]",
                        },
                    ],
                }
            ],
        }
    )
    src_correct = generate_java_skeleton(rich_cfg, "Rich.java", correct=True)
    src_wrong = generate_java_skeleton(rich_cfg, "Rich.java", correct=False)
    assert "return new int[0][0];" in src_correct
    assert "return -999999.0;" in src_wrong
    assert "return -999999;" in src_wrong
    assert 'return "wrong_answer";' in src_wrong


def test_web_app_generic_exception_handlers(monkeypatch):
    app.config["TESTING"] = True
    with app.test_client() as client:
        monkeypatch.setattr(
            yaml, "safe_load", lambda *_a, **_kw: (_ for _ in ()).throw(RuntimeError("yaml boom"))
        )
        r_upload = client.post(
            "/upload-config",
            data={"config_file": (io.BytesIO(b"a: 1\n"), "config.yaml")},
            content_type="multipart/form-data",
        )
        assert r_upload.status_code == 500

        monkeypatch.setattr(
            ag.Config,
            "model_validate",
            classmethod(lambda cls, _d: (_ for _ in ()).throw(RuntimeError("bundle boom"))),
        )
        r_bundle = client.post("/api/export/bundle", json={"language": "python"})
        assert r_bundle.status_code == 500

        monkeypatch.setattr(
            ag.Validator,
            "validate_json",
            lambda _self, _d: (_ for _ in ()).throw(RuntimeError("val boom")),
        )
        r_val = client.post("/api/validate", json={"language": "python"})
        assert r_val.status_code == 500

        monkeypatch.setattr(
            ag.Config,
            "normalize",
            classmethod(lambda cls, _d: (_ for _ in ()).throw(RuntimeError("norm boom"))),
        )
        r_norm = client.post("/api/normalize", json={"language": "python"})
        assert r_norm.status_code == 500

        monkeypatch.setattr(
            ag.Validator,
            "lint_config",
            classmethod(lambda cls, _d: (_ for _ in ()).throw(RuntimeError("lint boom"))),
        )
        r_lint = client.post("/api/lint", json={"language": "python"})
        assert r_lint.status_code == 500
