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
    run_stub_submissions: bool = False,
    run_submissions: list[str] = None,
    verbose: bool = False,
) -> int:
    if run_submissions is None:
        run_submissions = []

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

    if run_stub_submissions or run_submissions:
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

            if run_stub_submissions:
                try:
                    display_path = str(config_path.resolve().relative_to(Path.cwd().resolve()))
                except ValueError:
                    display_path = str(config_path)
                print(f"# log stubs for {display_path}")
                runner.run_autograder_for_generated_submissions(verbose=verbose)

            for sub_arg in run_submissions:
                sub_path = config_path.parent / sub_arg
                if not sub_path.exists():
                    alt_path = Path(sub_arg).resolve()
                    if alt_path.exists():
                        sub_path = alt_path
                    else:
                        print(f"[NOT FOUND] {sub_path}", file=sys.stderr)
                        continue

                clean_sub = sub_path.name
                if clean_sub.lower().endswith(".zip"):
                    clean_sub = clean_sub[:-4]

                if len(run_submissions) == 1 and not run_stub_submissions:
                    log_file = config_path.parent / "submission.log"
                else:
                    log_file = config_path.parent / f"{clean_sub}.log"

                res = runner.run_autograder_for_submission(
                    sub_path,
                    log_path=log_file,
                    verbose=verbose,
                )
                if (
                    len(run_submissions) == 1
                    and not run_stub_submissions
                    and clean_sub != "submission"
                ):
                    try:
                        shutil.copy2(log_file, config_path.parent / f"{clean_sub}.log")
                    except Exception:
                        pass
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
        description=(
            "Generate Gradescope autograder script from YAML configuration. "
            "Generated files will be at the same folder as the config "
            "(autograder.zip, stub submissions for testing, "
            "and optionally description.docx and description.md when --description is specified)."
        ),
        allow_abbrev=False,
    )
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--config", "-c", help="Path to YAML configuration file")
    mode_group.add_argument(
        "--batch",
        "-b",
        nargs="+",
        metavar="DIR_OR_CONFIG",
        help="One or more directories to search or config files to batch process",
    )
    parser.add_argument(
        "--description",
        action="store_true",
        default=False,
        help="Generate description.docx and description.md for the assessment",
    )
    parser.add_argument(
        "--run-submission",
        "-r",
        dest="run_submissions",
        action="append",
        default=[],
        metavar="DIR_OR_ZIP",
        help="Use submission directory or zip file relative to config to be run (can be specified multiple times)",
    )
    parser.add_argument(
        "--run-stub-submissions",
        dest="run_stubs_submissions",
        action="store_true",
        default=False,
        help="Run autograder for generated stub submissions (stub_correct_answer.zip, stub_wrong_answer.zip, stub_compiler_error.zip, stub_correct_answer_wrong_location.zip)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        default=False,
        help="Print full autograder execution logs instead of only paths to log files",
    )
    if argv is None:
        argv = sys.argv[1:]
    if not argv:
        parser.print_help()
        return 0
    args = parser.parse_args(argv)
    args.description = args.description
    setup_logging()

    if args.batch:
        return run_batch(
            args.batch,
            description=args.description,
            run_stub_submissions=bool(args.run_stubs_submissions),
            run_submissions=args.run_submissions,
            verbose=args.verbose,
        )

    try:
        config_arg = args.config
        if not config_arg:
            if isinstance(args.run_stubs_submissions, str):
                config_arg = args.run_stubs_submissions
            elif args.run_submissions:
                for sub_arg_candidate in args.run_submissions:
                    sub_p = Path(sub_arg_candidate)
                    for candidate in (
                        sub_p / "config.yaml",
                        sub_p / "config.yml",
                        sub_p.parent / "config.yaml",
                        sub_p.parent / "config.yml",
                    ):
                        if candidate.is_file():
                            config_arg = str(candidate)
                            break
                    if config_arg:
                        break
            elif args.run_stubs_submissions:
                for candidate in (
                    Path("config.yaml"),
                    Path("config.yml"),
                    Path("output/autograder.zip"),
                    Path("autograder.zip"),
                ):
                    if candidate.is_file():
                        config_arg = str(candidate)
                        break
            if not config_arg:
                print_error("Error: --config / -c or --batch / -b is required")
                return 2

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
        if not (args.run_submissions or args.run_stubs_submissions):
            for warning in warnings:
                print_warning(warning)
        if not is_valid:
            print_error("Configuration validation failed:")
            for error in errors:
                print_error(f"  - {error}")
            return 1
        if not (args.run_submissions or args.run_stubs_submissions):
            print_success("Configuration validation passed")

        output_dir = path.parent if str(path.parent) != "" else Path(".")
        if args.run_stubs_submissions or args.run_submissions:
            runner = ag.AutograderRun(path, verbose=args.verbose)
            if args.run_stubs_submissions:
                try:
                    display_path = str(path.resolve().relative_to(Path.cwd().resolve()))
                except ValueError:
                    display_path = str(path)
                print(f"# log stubs for {display_path}")
                runner.run_autograder_for_generated_submissions(verbose=args.verbose)

            for sub_arg in args.run_submissions:
                sub_path = Path(sub_arg)
                if not sub_path.exists():
                    candidate_sub = path.parent / sub_arg
                    if candidate_sub.exists():
                        sub_path = candidate_sub
                    else:
                        print_error(f"Submission path not found: {sub_arg}")
                        return 1

                clean_sub = sub_path.name
                if clean_sub.lower().endswith(".zip"):
                    clean_sub = clean_sub[:-4]

                if len(args.run_submissions) == 1 and not args.run_stubs_submissions:
                    log_file = output_dir / "submission.log"
                else:
                    log_file = output_dir / f"{clean_sub}.log"

                res = runner.run_autograder_for_submission(
                    sub_path, log_path=log_file, verbose=args.verbose
                )
                if (
                    len(args.run_submissions) == 1
                    and not args.run_stubs_submissions
                    and clean_sub != "submission"
                ):
                    try:
                        shutil.copy2(log_file, output_dir / f"{clean_sub}.log")
                    except Exception:
                        pass
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
        print_success(f"Assessment Summary (Config: {args.config}):")
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
