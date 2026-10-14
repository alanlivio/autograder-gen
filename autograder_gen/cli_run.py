from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

parent_dir = str(Path(__file__).resolve().parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

import autograder_gen as ag
from autograder_gen.cli_gen import find_configs
from autograder_gen.logger import (
    print_error,
    setup_logging,
)


def resolve_config(target: Path) -> Path | None:
    if target.is_file() and target.name == "config.yaml":
        return target
    if target.is_dir() and (target / "config.yaml").is_file():
        return target / "config.yaml"
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="autograder-run",
        usage="%(prog)s [TARGET] SUBMISSION [-h] [--version] [--stubs]",
        description="Run Gradescope autograder against submissions or stubs.",
        allow_abbrev=False,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {ag.__version__}",
    )
    parser.add_argument(
        "args",
        nargs="*",
        metavar="PATH",
        help="Target configuration/directory and/or submission file/directory",
    )
    parser.add_argument(
        "--stubs",
        action="store_true",
        default=False,
        help="Run autograder against stub submissions",
    )
    if argv is None:
        argv = sys.argv[1:]
    if not argv:
        parser.print_help()
        return 0
    args = parser.parse_args(argv)
    setup_logging()

    if args.stubs:
        targets = list(args.args)
        if not targets:
            if Path("config.yaml").is_file():
                targets = ["config.yaml"]
            elif find_configs(Path(".")):
                targets = ["."]

        all_configs: list[Path] = []
        for t in targets:
            all_configs.extend(find_configs(Path(t).resolve()))
        all_configs = sorted(set(all_configs), key=lambda p: str(p))

        if not all_configs:
            print_error("Error: target configuration file or directory is required")
            return 2

        for config_path in all_configs:
            runner = ag.AutograderRun(config_path)
            cfg_obj = runner.config_obj
            if (
                cfg_obj is not None
                and getattr(cfg_obj, "language", "").lower() == "java"
                and shutil.which("javac") is None
            ):
                print(f"[SKIPPED] {config_path}: javac is not installed")
                continue

            try:
                display_path = str(config_path.resolve().relative_to(Path.cwd().resolve()))
            except ValueError:
                display_path = str(config_path)
            print(f"# log stubs for {display_path}")
            runner.run_autograder_for_generated_submissions()
        return 0

    raw_args = list(args.args)
    if len(raw_args) == 0:
        print_error("Error: submission file or directory is required")
        return 2

    if len(raw_args) == 1:
        p0 = Path(raw_args[0])
        cfg0 = resolve_config(p0)
        if cfg0 is not None:
            print_error("Error: submission file or directory is required")
            return 2
        local_cfg = resolve_config(Path("."))
        if local_cfg is None:
            print_error("Error: config.yaml not found in current directory")
            return 1
        target_config = local_cfg
        submission = p0
    elif len(raw_args) == 2:
        p0 = Path(raw_args[0])
        p1 = Path(raw_args[1])
        cfg0 = resolve_config(p0)
        cfg1 = resolve_config(p1)
        if cfg0 is not None and cfg1 is None:
            target_config = cfg0
            submission = p1
        elif cfg1 is not None and cfg0 is None:
            target_config = cfg1
            submission = p0
        elif cfg0 is not None and cfg1 is not None:
            target_config = cfg0
            submission = p1
        else:
            target_config = p0
            submission = p1
    else:
        print_error("Error: too many arguments")
        return 2

    cfg_path = resolve_config(target_config)
    if cfg_path is None or not cfg_path.exists():
        print_error(f"Configuration file not found: {target_config}")
        return 1

    if not submission.exists():
        print_error(f"Submission not found: {submission}")
        return 1

    runner = ag.AutograderRun(cfg_path)
    cfg_obj = runner.config_obj
    if (
        cfg_obj is not None
        and getattr(cfg_obj, "language", "").lower() == "java"
        and shutil.which("javac") is None
    ):
        print(f"[SKIPPED] {cfg_path}: javac is not installed")
        return 0

    log_file = cfg_path.parent / "submission.log"
    res = runner.run_autograder_for_submission(submission, log_path=log_file)
    if "log_path" in res:
        log_p = Path(res["log_path"])
        try:
            display_path = str(log_p.resolve().relative_to(Path.cwd().resolve()))
        except ValueError:
            display_path = str(log_p)
        print(display_path)

    return 0


if __name__ == "__main__":
    sys.exit(main())
