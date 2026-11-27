import io
import json
import shutil
import zipfile
from pathlib import Path

import pytest
import yaml

import autograder_gen as ag
from autograder_gen import cli_gen, cli_run
from autograder_gen.utils_submission import STUDENT_ID_FALLBACK
from autograder_gen.version import __version__
from autograder_gen.web.app import app, main as web_main

SAMPLE_DICT = {
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


def test_autograder_run_config_obj_and_engine_branches(tmp_path: Path):
    cfg = ag.Config.model_validate(SAMPLE_DICT)
    runner_cfg = ag.AutograderRun(cfg, save_log=False)
    assert runner_cfg.config_obj is cfg
    assert isinstance(runner_cfg._get_engine(), ag.AutograderGen)

    bad_file = tmp_path / "broken.yaml"
    bad_file.write_text("not: [valid", encoding="utf-8")
    runner_bad = ag.AutograderRun(bad_file, save_log=False)
    assert runner_bad.config_obj is None

    runner_missing = ag.AutograderRun(tmp_path / "missing.yaml", save_log=False)
    assert runner_missing.config_obj is None
    with pytest.raises(FileNotFoundError):
        runner_missing._get_engine()

    runner_invalid_type = ag.AutograderRun(12345, save_log=False)
    assert runner_invalid_type.config_obj is None
    with pytest.raises(TypeError):
        runner_invalid_type._get_engine()

    cfg_zip = tmp_path / "bundle.zip"
    with zipfile.ZipFile(cfg_zip, "w") as zf:
        zf.writestr("config.yaml", yaml.dump(SAMPLE_DICT))
    runner_zip = ag.AutograderRun(cfg_zip, save_log=False)
    assert isinstance(runner_zip._get_engine(), ag.AutograderGen)


def test_autograder_run_staging_root_env_verbose_and_error_logging(tmp_path: Path, capsys):
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(yaml.dump(SAMPLE_DICT), encoding="utf-8")

    sol_file = tmp_path / "solution.py"
    sol_file.write_text(
        "import os\nprint(os.environ.get('CUSTOM_MSG', 'hello'))\n", encoding="utf-8"
    )

    ag_root = tmp_path / "custom_root"
    runner = ag.AutograderRun(
        cfg_path,
        autograder_root=ag_root,
        env={"CUSTOM_MSG": "hello"},
        save_log=False,
        verbose=True,
    )
    res_single = runner.run_autograder_for_submission(sol_file)
    assert res_single["tests"][0]["score"] == 10
    captured = capsys.readouterr()
    assert "[AutograderRun: Student View]" in captured.out

    sub_extra_dir = tmp_path / "extra_dir"
    sub_extra_dir.mkdir()
    (sub_extra_dir / "note.txt").write_text("ok", encoding="utf-8")
    res_list = runner.run_autograder_for_submission(
        [sol_file, sub_extra_dir, tmp_path / "nonexistent.py"],
        verbose=False,
    )
    assert res_list["tests"][0]["score"] == 10

    res_none = runner.run_autograder_for_submission(None, verbose=False)
    assert res_none["tests"][0]["score"] == 0

    res_missing = runner.run_autograder_for_submission(tmp_path / "nope", verbose=False)
    assert res_missing["tests"][0]["score"] == 0

    bad_ag_zip = tmp_path / "bad_ag.zip"
    with zipfile.ZipFile(bad_ag_zip, "w") as zf:
        zf.writestr("dummy.txt", "no runner")
    bad_runner = ag.AutograderRun(bad_ag_zip, save_log=True)
    err_log = tmp_path / "err.log"
    with pytest.raises(RuntimeError, match="Autograder runner script not found"):
        bad_runner.run_autograder_for_submission(sol_file, log_path=err_log)
    assert "Error executing autograder:" in err_log.read_text(encoding="utf-8")

    no_results_zip = tmp_path / "no_results.zip"
    with zipfile.ZipFile(no_results_zip, "w") as zf:
        zf.writestr("run_autograder.sh", "#!/bin/bash\necho 'stderr failure' >&2\nexit 1\n")
    no_res_runner = ag.AutograderRun(no_results_zip, save_log=False)
    with pytest.raises(RuntimeError, match="results.json was not created"):
        no_res_runner.run_autograder_for_submission(sol_file)


def test_autograder_run_disk_stubs_and_sibling_dirs(tmp_path: Path):
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(yaml.dump(SAMPLE_DICT), encoding="utf-8")
    cfg = ag.Config.model_validate(SAMPLE_DICT)
    gen = ag.AutograderGen(cfg, SAMPLE_DICT, base_dir=tmp_path)
    gen.generate(str(tmp_path))

    runner_disk = ag.AutograderRun(cfg_path, save_log=True)
    disk_res = runner_disk.run_autograder_for_generated_submissions()
    assert disk_res["correct_answer"]["tests"][0]["score"] == 10
    assert disk_res["wrong_answer"]["tests"][0]["score"] == 0

    dir_case = tmp_path / "sibling_dirs"
    dir_case.mkdir()
    dir_cfg_path = dir_case / "config.yaml"
    dir_cfg_path.write_text(yaml.dump(SAMPLE_DICT), encoding="utf-8")
    for stub_name, code in [
        ("stub_correct_answer", "print('hello')\n"),
        ("stub_wrong_answer", "print('wrong')\n"),
        ("stub_compiler_error", "def broken(\n"),
        ("stub_correct_answer_wrong_location", "print('hello')\n"),
    ]:
        sd = dir_case / stub_name
        sd.mkdir()
        target = sd / "src" / "solution.py" if "wrong_location" in stub_name else sd / "solution.py"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(code, encoding="utf-8")

    runner_dirs = ag.AutograderRun(dir_cfg_path, save_log=False)
    assert zipfile.is_zipfile(io.BytesIO(runner_dirs._get_correct_answer_zip_bytes()))
    assert zipfile.is_zipfile(io.BytesIO(runner_dirs._get_wrong_answer_zip_bytes()))
    assert zipfile.is_zipfile(io.BytesIO(runner_dirs._get_compiler_error_zip_bytes()))
    assert zipfile.is_zipfile(io.BytesIO(runner_dirs._get_wrong_file_location_zip_bytes()))

    zip_case = tmp_path / "sibling_zips"
    zip_case.mkdir()
    zip_cfg_path = zip_case / "config.yaml"
    zip_cfg_path.write_text(yaml.dump(SAMPLE_DICT), encoding="utf-8")
    for zname in (
        "stub_correct_answer.zip",
        "stub_wrong_answer.zip",
        "stub_compiler_error.zip",
        "stub_correct_answer_wrong_location.zip",
    ):
        (zip_case / zname).write_bytes((tmp_path / zname).read_bytes())
    runner_zips = ag.AutograderRun(zip_cfg_path, save_log=False)
    assert zipfile.is_zipfile(io.BytesIO(runner_zips._get_correct_answer_zip_bytes()))
    assert zipfile.is_zipfile(io.BytesIO(runner_zips._get_wrong_answer_zip_bytes()))
    assert zipfile.is_zipfile(io.BytesIO(runner_zips._get_compiler_error_zip_bytes()))
    assert zipfile.is_zipfile(io.BytesIO(runner_zips._get_wrong_file_location_zip_bytes()))


def test_autograder_run_formatting_and_fallback_file_checks(tmp_path: Path, monkeypatch):
    cfg_dict = {
        "version": __version__,
        "language": "python",
        "wrong_file_location_deduction": 0.25,
        "excluded_student_ids": ["99999"],
        "required_submission_files": ["solution.py", "helper.py"],
        "questions": [
            {
                "name": "Question 1",
                "expected_output_script": "print(STUDENT_ID)",
                "marking_items": [
                    {
                        "name": "Item 1",
                        "target_file": "solution.py",
                        "total_mark": 10,
                        "type": "program_output_test",
                        "visibility": "after_due_date",
                    }
                ],
            }
        ],
    }
    runner = ag.AutograderRun(cfg_dict, save_log=False)

    sub_dir = tmp_path / "sub"
    (sub_dir / "nested").mkdir(parents=True)
    (sub_dir / "nested" / "solution.py").write_text("print(1)\n", encoding="utf-8")
    (sub_dir / "helper.py").write_text("x = 1\n", encoding="utf-8")
    (sub_dir / "submission_metadata.json").write_text(
        json.dumps({"users": [{"sid": "99999"}]}), encoding="utf-8"
    )

    lines_excluded = runner._get_fallback_file_check_lines(sub_dir)
    assert any("is excluded; using fallback ID." in line for line in lines_excluded)
    assert any("File 'helper.py' exists." in line for line in lines_excluded)
    assert any("penalties will be applied" in line for line in lines_excluded)
    assert any("has 1 hidden marking item" in line for line in lines_excluded)

    (sub_dir / "submission_metadata.json").unlink()
    lines_missing_sid = runner._get_fallback_file_check_lines(sub_dir)
    assert any("Student ID not found" in line for line in lines_missing_sid)
    assert any(f"Using student ID: {STUDENT_ID_FALLBACK}" in line for line in lines_missing_sid)

    sub_zip = tmp_path / "sub.zip"
    with zipfile.ZipFile(sub_zip, "w") as zf:
        zf.writestr("solution.py", "print(1)\n")
    lines_zip = runner._get_fallback_file_check_lines(sub_zip)
    assert any("File 'solution.py' exists." in line for line in lines_zip)

    single_f = tmp_path / "solution.py"
    single_f.write_text("print(1)\n", encoding="utf-8")
    lines_file = runner._get_fallback_file_check_lines(single_f)
    assert any("File 'solution.py' exists." in line for line in lines_file)
    lines_list = runner._get_fallback_file_check_lines([single_f])
    assert any("File 'solution.py' exists." in line for line in lines_list)

    for lang, expected_env in [("java", "OpenJDK 25"), ("matlab", "GNU Octave")]:
        lang_runner = ag.AutograderRun({**cfg_dict, "language": lang}, save_log=False)
        lang_lines = lang_runner._get_fallback_file_check_lines(single_f)
        assert any(expected_env in line for line in lang_lines)

    fake_results_output = {
        "output": "[INFO] Environment: Python 3.10\n[INFO] File 'solution.py' exists.\n",
        "tests": [
            {
                "name": "Question 1 - Item 1",
                "score": 1.04,
                "max_score": 2.5,
                "output": "Custom output without pass header",
            }
        ],
    }
    monkeypatch.setattr(runner, "_execute", lambda _sub, _root: dict(fake_results_output))
    log_out = tmp_path / "formatted.log"
    runner.run_autograder_for_submission(sub_dir, log_path=log_out, expected_score=2.5)
    log_text = log_out.read_text(encoding="utf-8")
    assert "1.04 / 2.5" in log_text
    assert "## Score: 1.04 / 2.5" in log_text

    fake_results_stdout = {
        "_stdout": "[INFO] Environment: Python 3.10\n[WARNING] Required file missing.py not found in submission\n",
        "tests": [{"name": "NoNumber", "score": 0, "output": "Plain output"}],
    }
    no_cfg_runner = ag.AutograderRun(tmp_path / "missing_cfg.yaml", save_log=False)
    monkeypatch.setattr(no_cfg_runner, "_execute", lambda _sub, _root: dict(fake_results_stdout))
    log_out2 = tmp_path / "formatted2.log"
    no_cfg_runner.run_autograder_for_submission(sub_dir, log_path=log_out2)
    log_text2 = log_out2.read_text(encoding="utf-8")
    assert "# Actual Score = 0" in log_text2
    assert "[INFO] Environment: Python 3.10" in log_text2


def test_cli_gen_in_process_branches(tmp_path: Path, monkeypatch, capsys):
    assert cli_gen.find_configs(tmp_path / "nonexistent") == []

    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    monkeypatch.chdir(empty_dir)
    assert cli_gen.main([]) == 0
    assert "usage: autograder-gen" in capsys.readouterr().out

    assert cli_gen.main(["--description"]) == 2
    assert "target configuration file or directory is required" in capsys.readouterr().err

    assert cli_gen.main([str(empty_dir / "missing.yaml")]) == 1
    assert "Configuration file not found" in capsys.readouterr().err

    nested = empty_dir / "task1"
    nested.mkdir()
    (nested / "config.yaml").write_text(yaml.dump(SAMPLE_DICT), encoding="utf-8")
    assert cli_gen.main([]) == 0
    assert (nested / "autograder.zip").exists()

    assert cli_gen.main(["--description"]) == 0
    assert (nested / "description.docx").exists()

    no_cfg_zip = tmp_path / "empty_cfg.zip"
    with zipfile.ZipFile(no_cfg_zip, "w") as zf:
        zf.writestr("readme.txt", "hello")
    assert cli_gen.main([str(no_cfg_zip)]) == 1
    assert "config.yaml not found in zip archive" in capsys.readouterr().err

    good_zip_dir = tmp_path / "from_zip"
    good_zip_dir.mkdir()
    good_zip = good_zip_dir / "bundle.zip"
    (good_zip_dir / "extra.txt").write_text("hi", encoding="utf-8")
    zip_cfg = {**SAMPLE_DICT, "required_autograder_files": ["extra.txt"]}
    with zipfile.ZipFile(good_zip, "w") as zf:
        zf.writestr("config.yaml", yaml.dump(zip_cfg))
    assert cli_gen.main([str(good_zip)]) == 0
    out_zip = capsys.readouterr().out
    assert "Required Autograder Files: extra.txt" in out_zip
    assert (good_zip_dir / "autograder.zip").exists()

    bad_cfg = tmp_path / "invalid.yaml"
    bad_cfg.write_text("language: python\nquestions: []\n", encoding="utf-8")
    assert cli_gen.main([str(bad_cfg)]) == 1
    assert "Configuration validation failed" in capsys.readouterr().err

    broken_yaml = tmp_path / "broken_syntax.yaml"
    broken_yaml.write_text("questions: [unclosed", encoding="utf-8")
    assert cli_gen.main([str(broken_yaml)]) == 1
    assert "Error:" in capsys.readouterr().err


def test_cli_run_in_process_branches(tmp_path: Path, monkeypatch, capsys):
    empty_dir = tmp_path / "empty_run"
    empty_dir.mkdir()
    monkeypatch.chdir(empty_dir)
    assert cli_run.main([]) == 0
    assert "usage: autograder-run" in capsys.readouterr().out

    assert cli_run.main([str(empty_dir / "missing.yaml")]) == 1
    assert "config.yaml not found" in capsys.readouterr().err

    java_cfg = tmp_path / "java_proj" / "config.yaml"
    java_cfg.parent.mkdir()
    java_cfg.write_text(
        yaml.dump(
            {
                **SAMPLE_DICT,
                "language": "java",
                "required_submission_files": ["Main.java"],
                "questions": [
                    {
                        "name": "Q1",
                        "marking_items": [
                            {
                                "target_file": "Main.java",
                                "total_mark": 5,
                                "type": "program_output_test",
                            }
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    matlab_cfg = tmp_path / "matlab_proj" / "config.yaml"
    matlab_cfg.parent.mkdir()
    matlab_cfg.write_text(
        yaml.dump(
            {
                **SAMPLE_DICT,
                "language": "matlab",
                "required_submission_files": ["main.m"],
                "questions": [
                    {
                        "name": "Q1",
                        "marking_items": [
                            {
                                "target_file": "main.m",
                                "total_mark": 5,
                                "type": "program_output_test",
                            }
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(shutil, "which", lambda _cmd: None)
    assert cli_run.run_configs([java_cfg, matlab_cfg]) == 0
    out = capsys.readouterr().out
    assert "javac is not installed" in out
    assert "octave is not installed" in out


def test_web_app_error_branches_and_main(monkeypatch):
    app.config["TESTING"] = True
    with app.test_client() as client:
        resp_bad_json = client.post("/api/validate", data="not json", content_type="text/plain")
        assert resp_bad_json.status_code == 400
        assert "No config data provided" in resp_bad_json.get_json()["error"]

        resp_bad_yaml = client.post(
            "/upload-config",
            data={"config_file": (io.BytesIO(b"questions: [unclosed"), "config.yaml")},
            content_type="multipart/form-data",
        )
        assert resp_bad_yaml.status_code == 400
        assert "Invalid YAML syntax" in resp_bad_yaml.get_json()["error"]

        resp_bad_bundle = client.post("/api/export/bundle", json={"language": "python"})
        assert resp_bad_bundle.status_code == 400

        resp_bad_norm = client.post("/api/normalize", json={"language": "python"})
        assert resp_bad_norm.status_code == 400

        resp_lint_invalid = client.post(
            "/api/lint", json={"language": "python", "questions": "bad"}
        )
        assert resp_lint_invalid.status_code == 200
        assert resp_lint_invalid.get_json()["report"]["valid"] is False

        monkeypatch.setattr(
            ag.Config,
            "get_example_config_yaml",
            staticmethod(lambda _name: (_ for _ in ()).throw(RuntimeError("ex fail"))),
        )
        assert client.get("/").status_code == 200
        resp_ex_err = client.get("/api/example/python")
        assert resp_ex_err.status_code == 500

    called = {}
    monkeypatch.setattr(app, "run", lambda **kw: called.update(kw))
    monkeypatch.setattr(
        "sys.argv", ["autograder-gen-web", "--host", "0.0.0.0", "-p", "8080", "--no-debug"]
    )
    web_main()
    assert called == {"host": "0.0.0.0", "port": 8080, "debug": False}
