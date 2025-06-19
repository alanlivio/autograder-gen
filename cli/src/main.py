#!/usr/bin/env python3
"""
TIF Autograder CLI Tool
Main entry point for the command-line interface.
"""

import argparse
import json
import sys
from pathlib import Path

from config_parser import ConfigParser
from autograder_generator import AutograderGenerator
from validator import ConfigValidator
from utils import setup_logging, print_success, print_error, print_warning

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
        # Parse configuration
        config_parser = ConfigParser(args.config)
        config = config_parser.parse()
        
        # Validate configuration
        validator = ConfigValidator()
        is_valid = validator.validate(config)
        
        # Display validation results
        errors = validator.get_errors()
        warnings = validator.get_warnings()
        
        for warning in warnings:
            print_warning(warning)
        
        if errors:
            print_error("Configuration validation failed:")
            for error in errors:
                print_error(f"  - {error}")
            return 1
        
        if is_valid:
            print_success("Configuration validation passed")
        
        # If validate-only flag is set, stop here
        if args.validate_only:
            return 0
        
        # Generate autograder
        generator = AutograderGenerator(config)
        output_path = generator.generate(args.output)
        
        print_success(f"Autograder generated successfully: {output_path}")
        return 0
        
    except Exception as e:
        print_error(f"Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
