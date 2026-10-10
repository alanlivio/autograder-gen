"""
Command Line Interface for AutograderGen.
Provides CLI commands for validating configurations and generating Gradescope autograders.
"""

import argparse
import json
import shutil
import sys
import zipfile
from pathlib import Path
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import autograder_gen as ag
from autograder_gen.logger import (
    print_error,
    print_success,
    print_warning,
    setup_logging,
)


def find_configs(target: Path) -> list[Path]:
    if target.is_file() and target.suffix.lower() in [".yaml", ".yml"]:
        return [target]
    if not target.is_dir():
        return []

    direct_configs = [target / f for f in ("config.yaml", "config.yml") if (target / f).is_file()]
    if direct_configs:
        return [direct_configs[0]]

    sub_configs: list[Path] = []
    for pattern in ("*/config.yaml", "*/config.yml"):
        sub_configs.extend(target.glob(pattern))
    return sorted(set(sub_configs))


def run_batch(
    targets: list[str | Path],
    description: bool = False,
    run_stubs: bool = False,
    run_solution: bool = False,
    verbose: bool = False,
) -> int:
    all_configs: list[Path] = []
    for arg in targets:
        target_path = Path(arg).resolve()
        configs = find_configs(target_path)
        all_configs.extend(configs)

    all_configs = sorted(set(all_configs), key=lambda p: str(p))

    for config_path in all_configs:
        try:
            display_path = str(config_path.resolve().relative_to(Path.cwd().resolve()))
        except ValueError:
            display_path = str(config_path)
        print(f"Found config: {display_path}")

    if run_stubs or run_solution:
        for config_path in all_configs:
            runner = ag.AutograderRun(config_path, verbose=verbose)
            cfg_obj = runner.config_obj
            if (
                cfg_obj is not None
                and getattr(cfg_obj, "language", "").lower() == "java"
                and shutil.which("javac") is None
            ):
                print(f"[SKIPPED] {config_path}: javac is not installed")
                continue

            if run_stubs:
                try:
                    display_path = str(config_path.resolve().relative_to(Path.cwd().resolve()))
                except ValueError:
                    display_path = str(config_path)
                print(f"# log stubs for {display_path}")
                runner.run_autograder_for_generated_submissions(verbose=verbose)

            if run_solution:
                candidate_solution = None
                for candidate_name in ("solution", "solution.zip", "correct_answer", "correct_answer.zip"):
                    cand = config_path.parent / candidate_name
                    if cand.exists():
                        candidate_solution = cand
                        break
                if candidate_solution is None:
                    print(f"[NOT FOUND] {config_path.parent / 'solution'} or {config_path.parent / 'solution.zip'}", file=sys.stderr)
                    continue

                log_file = config_path.parent / "solution.log"
                res = runner.run_autograder_for_submission(
                    candidate_solution,
                    log_path=log_file,
                    verbose=verbose,
                )
                if "log_path" in res:
                    log_p = Path(res["log_path"])
                    try:
                        display_path = str(log_p.resolve().relative_to(Path.cwd().resolve()))
                    except ValueError:
                        display_path = str(log_p)
                    print(display_path)
    else:
        for config_path in all_configs:
            config = ag.Config.parse(config_path)
            with open(config_path, "r", encoding="utf-8") as f:
                if config_path.suffix.lower() in [".yaml", ".yml"]:
                    original_config = yaml.safe_load(f)
                else:
                    original_config = json.load(f)

            engine = ag.AutograderGen(config, original_config)
            out_dir = config_path.parent
            engine.generate(str(out_dir), description=description)
            generated_assets = [
                out_dir / "autograder.zip",
                out_dir / "stub_correct_answer.zip",
                out_dir / "stub_wrong_answer.zip",
                out_dir / "stub_compiler_error.zip",
                out_dir / "stub_correct_answer_wrong_location.zip",
            ]
            if description:
                generated_assets.extend(
                    [
                        out_dir / "description.docx",
                        out_dir / "description.md",
                    ]
                )
            for asset in generated_assets:
                if asset.exists():
                    try:
                        display_path = str(asset.resolve().relative_to(Path.cwd().resolve()))
                    except ValueError:
                        display_path = str(asset)
                    print(display_path)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="autograder-gen",
        usage=(
            "%(prog)s [TARGET ...] [-h] [--version] [--description]\n"
            "                      [--run-solution] [--run-stubs] [--verbose]\n"
            "                      [--schema]"
        ),
        description="Generate Gradescope autograder script from YAML configuration.",
        allow_abbrev=False,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {ag.__version__}",
    )
    parser.add_argument(
        "targets",
        nargs="*",
        metavar="TARGET",
        help="Configuration YAML file(s) or directories with config.yaml inside (default: ./config.yaml)",
    )
    parser.add_argument(
        "--description",
        action="store_true",
        default=False,
        help="Generate description.docx and description.md for the assessment",
    )
    parser.add_argument(
        "--run-solution",
        dest="run_solution",
        action="store_true",
        default=False,
        help="Run autograder for a solution submission (solution/ or solution.zip) in the same directory as config.yaml",
    )
    parser.add_argument(
        "--run-stubs",
        dest="run_stubs",
        action="store_true",
        default=False,
        help="Generate and run stub submissions (stub_correct_answer.zip, stub_wrong_answer.zip, stub_compiler_error.zip, stub_correct_answer_wrong_location.zip)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        default=False,
        help="Print full autograder execution logs instead of only paths to log files",
    )
    parser.add_argument(
        "--schema",
        action="store_true",
        default=False,
        help="Print JSON schema for the YAML configuration file and exit",
    )
    if argv is None:
        argv = sys.argv[1:]
    if not argv:
        if Path("config.yaml").is_file():
            argv = ["config.yaml"]
        elif Path("config.yml").is_file():
            argv = ["config.yml"]
        elif find_configs(Path(".")):
            argv = ["."]
        else:
            parser.print_help()
            return 0
    args = parser.parse_args(argv)
    if args.schema:
        print(json.dumps(ag.Config.model_json_schema(), indent=2))
        return 0
    args.description = args.description
    setup_logging()

    targets = list(args.targets)
    if not targets:
        if Path("config.yaml").is_file():
            targets = ["config.yaml"]
        elif Path("config.yml").is_file():
            targets = ["config.yml"]
        elif find_configs(Path(".")):
            targets = ["."]
        elif args.run_stubs or args.run_solution:
            for candidate in (
                Path("config.yaml"),
                Path("config.yml"),
                Path("output/autograder.zip"),
                Path("autograder.zip"),
            ):
                if candidate.is_file():
                    targets = [str(candidate)]
                    break

    if not targets:
        print_error("Error: target configuration file or directory is required")
        return 2

    if len(targets) > 1 or Path(targets[0]).is_dir():
        return run_batch(
            targets,
            description=args.description,
            run_stubs=bool(args.run_stubs),
            run_solution=bool(args.run_solution),
            verbose=args.verbose,
        )

    try:
        config_arg = targets[0]
        path = Path(config_arg)
        if not path.exists():
            print_error(f"Configuration file not found: {path}")
            return 1

        if path.is_file() and (path.suffix.lower() == ".zip" or zipfile.is_zipfile(path)):
            with zipfile.ZipFile(path, "r") as z:
                if "autograder_gen.yaml" in z.namelist():
                    raw_config_data = yaml.safe_load(z.read("autograder_gen.yaml"))
                else:
                    print_error(f"autograder_gen.yaml not found in zip archive: {path}")
                    return 1
        else:
            with open(path, "r", encoding="utf-8") as f:
                raw_config_data = yaml.safe_load(f)

        validator = ag.Validator()
        is_valid = validator.validate_json(raw_config_data)
        errors = validator.get_errors()
        warnings = validator.get_warnings()
        if not (args.run_solution or args.run_stubs):
            for warning in warnings:
                print_warning(warning)
        if not is_valid:
            print_error("Configuration validation failed:")
            for error in errors:
                print_error(f"  - {error}")
            return 1
        if not (args.run_solution or args.run_stubs):
            print_success("Configuration validation passed")

        output_dir = path.parent if str(path.parent) != "" else Path(".")
        if args.run_stubs or args.run_solution:
            runner = ag.AutograderRun(path, verbose=args.verbose)
            if args.run_stubs:
                try:
                    display_path = str(path.resolve().relative_to(Path.cwd().resolve()))
                except ValueError:
                    display_path = str(path)
                print(f"# log stubs for {display_path}")
                runner.run_autograder_for_generated_submissions(verbose=args.verbose)

            if args.run_solution:
                candidate_solution = None
                for candidate_name in ("solution", "solution.zip", "correct_answer", "correct_answer.zip"):
                    cand = path.parent / candidate_name
                    if cand.exists():
                        candidate_solution = cand
                        break
                if candidate_solution is None:
                    print_error(f"Solution not found: {path.parent / 'solution'} or {path.parent / 'solution.zip'}")
                    return 1

                log_file = output_dir / "solution.log"
                res = runner.run_autograder_for_submission(
                    candidate_solution, log_path=log_file, verbose=args.verbose
                )
                if "log_path" in res:
                    log_p = Path(res["log_path"])
                    try:
                        display_path = str(log_p.resolve().relative_to(Path.cwd().resolve()))
                    except ValueError:
                        display_path = str(log_p)
                    print(display_path)
            return 0
        config = ag.Config.model_validate(raw_config_data)
        original_config_dict = None
        try:
            with open(path, "r", encoding="utf-8") as f:
                if path.suffix.lower() not in [".yaml", ".yml"]:
                    raise ValueError("File must be a YAML file (.yml or .yaml)")
                original_config_dict = yaml.safe_load(f)
        except Exception:
            pass  # If we can't load original config, proceed without it
        # Print assessment summary before generation process
        summary = config.get_config_summary()
        print_success(f"Assessment Summary (Config: {config_arg}):")
        print(f"  Language: {summary['language']}")
        print(f"  Global Time Limit: {summary['global_time_limit']}s")
        print(f"  Total Questions: {summary['total_questions']}")
        print(f"  Total Marking Items: {summary['total_marking_items']}")
        print(f"  Total Marks: {summary['total_marks']}")
        print(f"  Required Files: {', '.join(summary['required_files'])}")

        output_dir = path.parent if str(path.parent) != "" else Path(".")
        generator = ag.AutograderGen(config, original_config_dict, base_dir=path.parent)
        output_path = generator.generate(str(output_dir), description=args.description)
        print_success(f"Autograder package generated successfully at: {output_dir}")
        assets_desc = "description.docx, description.md, " if args.description else ""
        print_success(
            f"Generated assets: autograder.zip, {assets_desc}"
            "stub submissions for testing (stub_correct_answer.zip, stub_wrong_answer.zip, stub_compiler_error.zip, stub_correct_answer_wrong_location.zip)"
        )
        return 0
    except Exception as e:
        print_error(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
