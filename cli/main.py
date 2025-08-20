#!/usr/bin/env python3
"""
TIF Autograder CLI Tool
Main entry point for the command-line interface.

This tool validates JSON configuration files using JSON Schema validation
and generates Gradescope autograder scripts based on the configuration.
"""

import argparse
import json
import sys
from pathlib import Path

# Add the project root to Python path so we can import autograder_core
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from autograder_core.config import ConfigParser
from autograder_core.generator import AutograderGenerator
from autograder_core.validator import ConfigValidator
from autograder_core.utils import setup_logging, print_success, print_error, print_warning

def main():
    parser = argparse.ArgumentParser(
        description="Generate Gradescope autograder scripts from JSON configuration"
    )
    parser.add_argument(
        "--config", "-c",
        required=True,
        help="Path to JSON configuration file"
    )
    parser.add_argument(
        "--output", "-o",
        default="./output",
        help="Output directory for generated autograder.zip"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate configuration without generating autograder"
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
            import json
            with open(args.config, 'r', encoding='utf-8') as f:
                original_config_dict = json.load(f)
        except Exception:
            pass  # If we can't load original config, proceed without it
        
        # Generate autograder
        generator = AutograderGenerator(config, original_config_dict)
        output_path = generator.generate(args.output)
        
        print_success(f"Autograder generated successfully: {output_path}")
        return 0
        
    except Exception as e:
        print_error(f"Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
