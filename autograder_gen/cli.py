#!/usr/bin/env python3
"""
TIF Autograder CLI Tool
Main entry point for the command-line interface.

This tool validates YAML configuration files using pydantic
and generates Gradescope autograder scripts based on the configuration.
"""

import argparse
import sys
import yaml
from pathlib import Path

# Add the project root to Python path so we can import autograder_core
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from autograder_gen.config import ConfigParser
from autograder_gen.generator import AutograderGenerator
from autograder_gen.validator import ConfigValidator
from autograder_gen.utils import (
    setup_logging,
    print_success,
    print_error,
    print_warning,
)


def main():
    parser = argparse.ArgumentParser(
        description="Generate Gradescope autograder scripts from YAML configuration"
    )
    parser.add_argument(
        "--config", "-c", required=True, help="Path to YAML configuration file"
    )
    parser.add_argument(
        "--output",
        "-o",
        default="./output",
        help="Output directory for generated autograder.zip",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate configuration without generating autograder",
    )
    parser.add_argument(
        "--with-description",
        "-d",
        action="store_true",
        help="Generate description.docx assessment documentation",
    )
    parser.add_argument(
        "--with-skeletons",
        action="store_true",
        help="Generate correct_answer.zip and wrong_answer.zip skeletons",
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.verbose)

    try:
        # Validate configuration first using JSON schema
        validator = ConfigValidator()
        is_valid = validator.validate_from_file(args.config)

        # Display validation results
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

        # If validate-only flag is set, stop here
        if args.validate_only:
            return 0

        # Parse configuration after validation
        config_parser = ConfigParser(args.config)
        config = config_parser.parse()

        # Load original config for preservation in zip
        original_config_dict = None
        try:
            path = Path(args.config)
            with open(path, "r", encoding="utf-8") as f:
                if path.suffix.lower() not in [".yaml", ".yml"]:
                    raise ValueError("File must be a YAML file (.yml or .yaml)")
                original_config_dict = yaml.safe_load(f)
        except Exception:
            pass  # If we can't load original config, proceed without it

        # Generate autograder
        generator = AutograderGenerator(config, original_config_dict)
        output_path = generator.generate(args.output)
        print_success(f"Autograder generated successfully: {output_path}")

        # Generate description if requested
        if args.with_description:
            docx_buffer = generator.generate_description_docx()
            docx_path = Path(args.output) / "description.docx"
            with open(docx_path, "wb") as f:
                f.write(docx_buffer.getbuffer())
            print_success(f"Assessment description generated: {docx_path}")

        # Generate answer samples if requested
        if args.answer_samples_with_skeletons:
            # Correct answer
            correct_buffer = generator.generate_correct_answer_zip()
            correct_path = Path(args.output) / "correct_answer.zip"
            with open(correct_path, "wb") as f:
                f.write(correct_buffer.getbuffer())
            print_success(f"Correct answer sample generated: {correct_path}")

            # Wrong answer
            wrong_buffer = generator.generate_wrong_answer_zip()
            wrong_path = Path(args.output) / "wrong_answer.zip"
            with open(wrong_path, "wb") as f:
                f.write(wrong_buffer.getbuffer())
            print_success(f"Wrong answer sample generated: {wrong_path}")

        return 0

    except Exception as e:
        print_error(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
