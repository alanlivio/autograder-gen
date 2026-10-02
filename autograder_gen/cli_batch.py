"""
Batch processor for AutograderGen configurations.
Finds all config files in target directories and generates Gradescope autograders,
or runs autograders against stub submissions or specified submission folders.
"""

import argparse
import json
import shutil
import sys
from pathlib import Path
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from autograder_gen.autograder_run import AutograderRun
from autograder_gen.config import Config
from autograder_gen.autograder_gen import AutograderGen, Engine


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


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Batch generate or run autograders for configuration files found in target folders.",
        allow_abbrev=False,
    )
    parser.add_argument(
        "targets",
        nargs="+",
        metavar="folder_or_config_path",
        help="One or more directories or config files to process",
    )
    parser.add_argument(
        "--description",
        action="store_true",
        default=False,
        help="Generate description.docx and description.md assessment description",
    )
    parser.add_argument(
        "--run-stub-submissions",
        action="store_true",
        default=False,
        help="Run autograder for generated stub submissions",
    )
    parser.add_argument(
        "--run-submission",
        "-r",
        dest="run_submissions",
        action="append",
        default=[],
        help="Submission directory or zip file name to run for each config folder (can be specified multiple times)",
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

    all_configs: list[Path] = []
    for arg in args.targets:
        target_path = Path(arg).resolve()
        configs = find_configs(target_path)
        all_configs.extend(configs)

    all_configs = sorted(set(all_configs), key=lambda p: str(p))

    if args.run_stub_submissions or args.run_submissions:
        for config_path in all_configs:
            runner = AutograderRun(config_path, verbose=args.verbose)
            cfg_obj = runner.config_obj
            if (
                cfg_obj is not None
                and getattr(cfg_obj, "language", "").lower() == "java"
                and shutil.which("javac") is None
            ):
                print(f"[SKIPPED] {config_path}: javac is not installed")
                continue

            if args.run_stub_submissions:
                runner.run_autograder_for_generated_submissions(verbose=args.verbose)

            for sub_arg in args.run_submissions:
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

                if len(args.run_submissions) == 1 and not args.run_stub_submissions:
                    log_file = config_path.parent / "submission.log"
                else:
                    log_file = config_path.parent / f"{clean_sub}.log"

                res = runner.run_autograder_for_submission(
                    sub_path,
                    log_path=log_file,
                    verbose=args.verbose,
                )
                if (
                    len(args.run_submissions) == 1
                    and not args.run_stub_submissions
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
            config = Config.parse(config_path)
            with open(config_path, "r", encoding="utf-8") as f:
                if config_path.suffix.lower() in [".yaml", ".yml"]:
                    original_config = yaml.safe_load(f)
                else:
                    original_config = json.load(f)

            engine = AutograderGen(config, original_config)
            out_dir = config_path.parent
            engine.generate(str(out_dir), description=args.description)
            generated_assets = [
                out_dir / "autograder.zip",
                out_dir / "stub_correct_answer.zip",
                out_dir / "stub_wrong_answer.zip",
                out_dir / "stub_compiler_error.zip",
                out_dir / "stub_correct_answer_wrong_location.zip",
            ]
            if args.description:
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


if __name__ == "__main__":
    sys.exit(main())
