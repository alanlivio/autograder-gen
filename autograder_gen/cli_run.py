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


def display(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(Path.cwd().resolve()))
    except ValueError:
        return str(path)


def java_unavailable(runner: ag.AutograderRun) -> bool:
    cfg_obj = runner.config_obj
    return (
        cfg_obj is not None
        and getattr(cfg_obj, "language", "").lower() == "java"
        and shutil.which("javac") is None
    )


def run_configs(configs: list[Path]) -> int:
    for config_path in sorted(set(configs), key=lambda p: str(p)):
        runner = ag.AutograderRun(config_path)
        if java_unavailable(runner):
            print(f"[SKIPPED] {display(config_path)}: javac is not installed")
            continue

        print(f"# log {display(config_path)}")
        solution_dir = config_path.parent / "solution"
        if solution_dir.is_dir():
            res = runner.run_autograder_for_submission(
                solution_dir, log_path=config_path.parent / "solution.log"
            )
            if "log_path" in res:
                print(display(Path(res["log_path"])))
        runner.run_autograder_for_generated_submissions()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="autograder-run",
        usage="%(prog)s [TARGET ...] [-h] [--version]",
        description="Run Gradescope autograder.zip at a folder against solution/ folder and stub submissions.",
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
        help="Configuration YAML file(s) or directory with autograder.zip",
    )
    if argv is None:
        argv = sys.argv[1:]
    if not argv:
        parser.print_help()
        return 0
    args = parser.parse_args(argv)
    setup_logging()

    if not args.targets:
        print_error("Error: target configuration file or directory is required")
        return 2

    configs: list[Path] = []
    for target in args.targets:
        found = find_configs(Path(target).resolve())
        if not found:
            print_error(f"Error: config.yaml not found in {target}")
            return 1
        configs.extend(found)

    return run_configs(configs)


if __name__ == "__main__":
    sys.exit(main())
