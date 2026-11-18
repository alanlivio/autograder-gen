import os
import sys
import subprocess
import json
import yaml
import shutil
import tempfile
import zipfile
import pytest
from pathlib import Path
import autograder_gen as ag


def run_autograder_scenario(
    example_name: str,
    subdir: str = "solution",
    expected_score: int | None = None,
    config_file: str = "config.yaml",
):
    base_dir = Path(__file__).parent.parent.parent
    example_dir = base_dir / "tests/examples" / example_name
    config_path = example_dir / config_file
    student_dir = example_dir / subdir

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_dir = Path(tmp_dir)
        config = ag.Config.parse(config_path)

        with open(config_path, "r", encoding="utf-8") as f:
            if config_path.suffix.lower() == ".yaml":
                original_config = yaml.safe_load(f)
            else:
                original_config = json.load(f)

        generator = ag.AutograderGen(config, original_config, base_dir=example_dir)
        gen_dir = tmp_dir / "generated"
        output_zip = generator.generate(str(gen_dir))

        work_dir = tmp_dir / "run"
        work_dir.mkdir()

        with zipfile.ZipFile(output_zip, "r") as z:
            z.extractall(work_dir)

        submission_dir = work_dir / "submission"
        submission_dir.mkdir()

        stub_map = {
            "correct_answer": gen_dir / "stub_correct_answer.zip",
            "wrong_answer": gen_dir / "stub_wrong_answer.zip",
            "compiler_error": gen_dir / "stub_compiler_error.zip",
            "correct_answer_wrong_location": gen_dir / "stub_correct_answer_wrong_location.zip",
        }

        if student_dir.exists():
            for student_file in student_dir.iterdir():
                if student_file.is_dir():
                    shutil.copytree(
                        student_file, submission_dir / student_file.name, dirs_exist_ok=True
                    )
                elif student_file.is_file():
                    shutil.copy(student_file, submission_dir / student_file.name)
        elif subdir in stub_map and stub_map[subdir].exists():
            with zipfile.ZipFile(stub_map[subdir], "r") as z:
                z.extractall(submission_dir)

        results_path = work_dir / "results.json"

        process = subprocess.run(
            [sys.executable, str(work_dir / "run_tests.py")],
            cwd=work_dir,
            capture_output=True,
            text=True,
            env={
                **os.environ,
                "PYTHONPATH": str(work_dir),
                "GRADESCOPE_RESULTS_PATH": str(results_path),
                "GRADESCOPE_SOURCE_PATH": str(submission_dir),
            },
        )

        assert (
            results_path.exists()
        ), f"results.json not created for {example_name}/{subdir} with {config_file}. Error: {process.stderr}"

        with open(results_path, "r") as f:
            results = json.load(f)

        assert "tests" in results
        if expected_score is not None:
            total_score = sum(t.get("score", 0) for t in results["tests"])
            assert (
                total_score == expected_score
            ), f"Score mismatch for {example_name} ({config_file}). Expected {expected_score}, got {total_score}. Results: {results}"


@pytest.mark.parametrize(
    "subdir, expected_score",
    [
        ("solution", 10),
        ("correct_answer", 10),
        ("wrong_answer", 0),
        ("compiler_error", 0),
        ("missing_file", 0),
        ("correct_answer_wrong_location", 10),
    ],
)
def test_autograder_integration_python(subdir, expected_score):
    run_autograder_scenario("python", subdir, expected_score)


@pytest.mark.skipif(shutil.which("javac") is None, reason="javac is not installed")
@pytest.mark.parametrize(
    "subdir, expected_score",
    [
        ("solution", 10),
        ("correct_answer", 10),
        ("wrong_answer", 0),
        ("compiler_error", 0),
        ("missing_file", 0),
        ("correct_answer_wrong_location", 10),
    ],
)
def test_autograder_integration_java_scenarios(subdir, expected_score):
    run_autograder_scenario("java", subdir, expected_score)


@pytest.mark.skipif(
    shutil.which("octave-cli") is None and shutil.which("octave") is None,
    reason="octave is not installed",
)
@pytest.mark.parametrize(
    "subdir, expected_score",
    [
        ("solution", 10),
        ("correct_answer", 10),
        ("wrong_answer", 0),
        ("compiler_error", 0),
        ("missing_file", 0),
        ("correct_answer_wrong_location", 10),
    ],
)
def test_autograder_integration_matlab_scenarios(subdir, expected_score):
    run_autograder_scenario("matlab", subdir, expected_score)


def test_autograder_integration_java():
    base_dir = Path(__file__).parent.parent.parent
    example_dir = base_dir / "tests/examples/java"
    config_path = example_dir / "config.yaml"
    config = ag.Config.parse(config_path)
    assert config.language == "java"
    with open(config_path, "r", encoding="utf-8") as f:
        original_config = yaml.safe_load(f)
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_dir = Path(tmp_dir)
        generator = ag.AutograderGen(config, original_config)
        gen_dir = tmp_dir / "generated"
        output_zip = generator.generate(str(gen_dir))
        assert Path(output_zip).exists()

        with zipfile.ZipFile(output_zip, "r") as z:
            namelist = z.namelist()
            for fname in ["setup.sh", "run_autograder", "run_tests.py"]:
                assert any(f.startswith(fname) for f in namelist)
            with z.open("setup.sh") as f:
                setup_content = f.read().decode("utf-8")
                assert "apt-get install -y openjdk-25-jdk" in setup_content
        correct_zip_bytes = generator.generate_correct_answer_zip()
        with zipfile.ZipFile(correct_zip_bytes, "r") as z:
            assert "FunctionReturn.java" in z.namelist()
            assert "ProgramOutput.java" in z.namelist()
            content = z.read("FunctionReturn.java").decode("utf-8")
            assert "public class FunctionReturn {" in content
            assert "public static double add(double a, double b) {" in content
            assert "return a + b;" in content
        wrong_zip_bytes = generator.generate_wrong_answer_zip()
        with zipfile.ZipFile(wrong_zip_bytes, "r") as z:
            assert "FunctionReturn.java" in z.namelist()
            content = z.read("FunctionReturn.java").decode("utf-8")
            assert "public class FunctionReturn {" in content
            assert "return 0.0;" in content


def test_strict_file_location_true_fails_wrong_location(tmp_path):
    base_dir = Path(__file__).parent.parent.parent
    config_path = base_dir / "tests/examples/python/config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    data["strict_file_location"] = True
    config = ag.Config.model_validate(data)

    generator = ag.AutograderGen(config, data)
    gen_dir = tmp_path / "generated"
    output_zip = generator.generate(str(gen_dir))

    work_dir = tmp_path / "run"
    work_dir.mkdir()

    with zipfile.ZipFile(output_zip, "r") as z:
        z.extractall(work_dir)

    submission_dir = work_dir / "submission"
    submission_dir.mkdir()
    with zipfile.ZipFile(gen_dir / "stub_correct_answer_wrong_location.zip", "r") as z:
        z.extractall(submission_dir)

    results_path = work_dir / "results.json"
    process = subprocess.run(
        [sys.executable, str(work_dir / "run_tests.py")],
        cwd=work_dir,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "PYTHONPATH": str(work_dir),
            "GRADESCOPE_RESULTS_PATH": str(results_path),
            "GRADESCOPE_SOURCE_PATH": str(submission_dir),
        },
    )
    assert results_path.exists(), f"results.json not created. stderr: {process.stderr}"
    with open(results_path, "r", encoding="utf-8") as f:
        results = json.load(f)
    total_score = sum(t.get("score", 0) for t in results["tests"])
    assert total_score == 0
    assert any("[WRONG_FILE]" in t.get("output", "") for t in results["tests"])


@pytest.mark.skipif(shutil.which("javac") is None, reason="javac is not installed")
def test_java_correct_answer_with_package(tmp_path):
    base_dir = Path(__file__).parent.parent.parent
    java_dir = base_dir / "tests/examples/java"
    config_path = java_dir / "config.yaml"

    student_dir = tmp_path / "student_pkg"
    student_dir.mkdir()
    for f in (java_dir / "solution").iterdir():
        (student_dir / f.name).write_text(
            "package coursework1;\n" + f.read_text(encoding="utf-8"),
            encoding="utf-8",
        )

    runner_without = ag.AutograderRun(config_path, save_log=False)
    res_without = runner_without.run_autograder_for_submission(student_dir)
    assert "tests" in res_without
    score_without = sum(t.get("score", 0) for t in res_without["tests"])
    assert score_without == 0

    with open(config_path, "r", encoding="utf-8") as f:
        data_with = yaml.safe_load(f)
    data_with["remove_use_of_java_package"] = True

    runner_with = ag.AutograderRun(data_with, save_log=False)
    res_with = runner_with.run_autograder_for_submission(student_dir)
    assert "tests" in res_with
    score_with = sum(t.get("score", 0) for t in res_with["tests"])
    assert score_with == 10
