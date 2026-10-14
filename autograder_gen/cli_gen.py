from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path
import yaml

parent_dir = str(Path(__file__).resolve().parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

import autograder_gen as ag
from autograder_gen.logger import (
    print_error,
    print_success,
    print_warning,
    setup_logging,
)


def find_configs(target: Path) -> list[Path]:
    if target.is_file():
        return [target] if target.name == "config.yaml" else []
    if target.is_dir():
        direct = target / "config.yaml"
        return [direct] if direct.is_file() else sorted(target.glob("*/config.yaml"))
    return []


def run_batch(
    targets: list[str | Path],
    description: bool = False,
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

    for config_path in all_configs:
        config = ag.Config.parse(config_path)
        with open(config_path, "r", encoding="utf-8") as f:
            if config_path.suffix.lower() == ".yaml":
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="autograder-gen",
        usage="%(prog)s [TARGET ...] [-h] [--version] [--description]",
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
    if argv is None:
        argv = sys.argv[1:]
    if not argv:
        if Path("config.yaml").is_file():
            argv = ["config.yaml"]
        elif find_configs(Path(".")):
            argv = ["."]
        else:
            parser.print_help()
            return 0
    args = parser.parse_args(argv)
    setup_logging()

    targets = list(args.targets)
    if not targets:
        if Path("config.yaml").is_file():
            targets = ["config.yaml"]
        elif find_configs(Path(".")):
            targets = ["."]

    if not targets:
        print_error("Error: target configuration file or directory is required")
        return 2

    if len(targets) > 1 or Path(targets[0]).is_dir():
        return run_batch(
            targets,
            description=args.description,
        )

    try:
        config_arg = targets[0]
        path = Path(config_arg)
        if not path.exists():
            print_error(f"Configuration file not found: {path}")
            return 1

        if path.is_file() and (path.suffix.lower() == ".zip" or zipfile.is_zipfile(path)):
            with zipfile.ZipFile(path, "r") as z:
                if "config.yaml" in z.namelist():
                    raw_config_data = yaml.safe_load(z.read("config.yaml"))
                else:
                    print_error(f"config.yaml not found in zip archive: {path}")
                    return 1
        else:
            with open(path, "r", encoding="utf-8") as f:
                raw_config_data = yaml.safe_load(f)

        validator = ag.Validator()
        is_valid = validator.validate_json(raw_config_data)
        errors = validator.get_errors()
        warnings = validator.get_warnings()
        for warning in warnings:
            print_warning(warning)
        if not is_valid:
            print_error("Configuration validation failed:")
            for error in errors:
                print_error(f"  - {error}")
            return 1
        print_success("Configuration validation passed")

        config = ag.Config.model_validate(raw_config_data)
        original_config_dict = None
        try:
            with open(path, "r", encoding="utf-8") as f:
                if path.suffix.lower() != ".yaml":
                    raise ValueError("File must be a YAML file (.yaml)")
                original_config_dict = yaml.safe_load(f)
        except Exception:
            pass

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
        generator.generate(str(output_dir), description=args.description)
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
