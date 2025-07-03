"""
Autograder generator for creating Gradescope autograder.zip files.
Uses Jinja2 templates and gradescope-utils for proper test generation.
"""

import os
import shutil
import zipfile
from pathlib import Path
from typing import Dict, List, Optional
import json

from jinja2 import Environment, FileSystemLoader, select_autoescape
from cli.src.config_parser import AutograderConfig, Question, MarkingItem

class AutograderGenerator:
    """Generates Gradescope autograder packages from configuration using Jinja templates."""
    
    def __init__(self, config: AutograderConfig):
        self.config = config
        self.temp_dir: Optional[Path] = None
        self.templates_dir = Path(__file__).parent.parent / "templates"
        
        # Set up Jinja environment
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True
        )
    
    def generate(self, output_dir: str) -> str:
        """Generate the autograder.zip file using Jinja templates."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Create temporary directory for autograder files
        self.temp_dir = output_path / "temp_autograder"
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
        self.temp_dir.mkdir()
        
        # Create source directory within temp
        tests_dir = self.temp_dir / "tests"
        tests_dir.mkdir()
        
        try:
            # Generate all autograder files using templates
            self._generate_setup_sh()
            self._generate_run_autograder()
            self._generate_run_tests(tests_dir)
            self._generate_requirements_txt()
            self._generate_metadata_files()
            
            # Create the zip file
            zip_path = output_path / "autograder.zip"
            self._create_zip(zip_path)
            
            return str(zip_path)
            
        finally:
            # Clean up temporary directory
            if self.temp_dir and self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
    
    def _generate_setup_sh(self):
        """Generate setup.sh using Jinja template."""
        assert self.temp_dir is not None, "temp_dir must be set before generating files"
        
        template = self.jinja_env.get_template('setup.sh.j2')
        content = template.render(config=self.config)
        
        setup_file = self.temp_dir / "setup.sh"
        with open(setup_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Make setup.sh executable
        os.chmod(setup_file, 0o755)
    def _generate_run_autograder(self):
        """Generate run_autograder using Jinja template."""
        assert self.temp_dir is not None, "temp_dir must be set before generating files"
        template = self.jinja_env.get_template('run_autograder.j2')
        content = template.render(config=self.config)
        
        run_autograder_file = self.temp_dir / "run_autograder"
        with open(run_autograder_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Make run_autograder executable
        os.chmod(run_autograder_file, 0o755)
    
    def _generate_run_tests(self, tests_dir: Path):
        """Generate modular test files: main run_tests.py and individual question test files."""
        # Generate main test runner
        assert self.temp_dir is not None, "temp_dir must be set before generating files"
        template = self.jinja_env.get_template('run_tests.py.j2')
        content = template.render(config=self.config)
        
        run_tests_file = self.temp_dir / "run_tests.py"
        with open(run_tests_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Generate individual question test files
        self._generate_question_test_files(tests_dir)
    
    def _generate_question_test_files(self, tests_dir: Path):
        """Generate individual test files for each question."""
        question_template = self.jinja_env.get_template('test_question.py.j2')
        
        for idx, question in enumerate(self.config.questions, 1):
            # Use question number for filename
            question_filename = f"question_{idx}"
            
            # Generate content for this question
            content = question_template.render(
                config=self.config,
                question=question,
                question_number=idx
            )
            
            # Write the question test file
            test_file = tests_dir / f"test_{question_filename}.py"
            with open(test_file, 'w', encoding='utf-8') as f:
                f.write(content)
    
    def _sanitize_filename(self, name: str) -> str:
        """Convert question name to a safe Python module filename."""
        # Convert to lowercase and replace problematic characters
        safe_name = name.lower()
        safe_name = safe_name.replace(' ', '_')
        safe_name = safe_name.replace('-', '_')
        safe_name = safe_name.replace('.', '_')
        safe_name = safe_name.replace('(', '')
        safe_name = safe_name.replace(')', '')
        safe_name = safe_name.replace('[', '')
        safe_name = safe_name.replace(']', '')
        safe_name = safe_name.replace('/', '_')
        safe_name = safe_name.replace('\\', '_')
        safe_name = safe_name.replace(':', '_')
        safe_name = safe_name.replace(';', '_')
        safe_name = safe_name.replace(',', '_')
        safe_name = safe_name.replace('?', '_')
        safe_name = safe_name.replace('!', '_')
        safe_name = safe_name.replace('@', '_')
        safe_name = safe_name.replace('#', '_')
        safe_name = safe_name.replace('$', '_')
        safe_name = safe_name.replace('%', '_')
        safe_name = safe_name.replace('^', '_')
        safe_name = safe_name.replace('&', '_')
        safe_name = safe_name.replace('*', '_')
        safe_name = safe_name.replace('+', '_')
        safe_name = safe_name.replace('=', '_')
        safe_name = safe_name.replace('|', '_')
        safe_name = safe_name.replace('<', '_')
        safe_name = safe_name.replace('>', '_')
        
        # Remove multiple consecutive underscores
        import re
        safe_name = re.sub(r'_+', '_', safe_name)
        
        # Remove leading/trailing underscores
        safe_name = safe_name.strip('_')
        
        # Ensure it's a valid Python identifier
        if not safe_name or safe_name[0].isdigit():
            safe_name = 'question_' + safe_name
        
        return safe_name
        
    
    def _generate_requirements_txt(self):
        """Generate requirements.txt using Jinja template."""
        assert self.temp_dir is not None, "temp_dir must be set before generating files"
        
        template = self.jinja_env.get_template('requirements.txt.j2')
        content = template.render(config=self.config)
        
        requirements_file = self.temp_dir / "requirements.txt"
        with open(requirements_file, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def _generate_metadata_files(self):
        """Generate metadata and configuration files."""
        assert self.temp_dir is not None, "temp_dir must be set before generating files"
        
        # Create autograder configuration reference
        config_data = {
            "generated_by": "TIF Autograder CLI Tool",
            "language": self.config.language,
            "global_time_limit": self.config.global_time_limit,
            "questions_count": len(self.config.questions),
            "total_tests": sum(len(q.marking_items) for q in self.config.questions),
            "total_marks": sum(
                sum(item.total_mark for item in q.marking_items) 
                for q in self.config.questions
            )
        }
        
        config_file = self.temp_dir / "autograder_config.json"
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2)
        
        # Create a README for the autograder
        readme_content = f"""# Autograder Package

            Generated by TIF Autograder CLI Tool

            ## Configuration
            - Language: {self.config.language}
            - Questions: {len(self.config.questions)}
            - Total Tests: {sum(len(q.marking_items) for q in self.config.questions)}
            - Total Points: {sum(sum(item.total_mark for item in q.marking_items) for q in self.config.questions)}

            ## Structure
            - `setup.sh`: Environment setup script
            - `run_autograder`: Main autograder script
            - `source/run_tests.py`: Test runner using gradescope-utils
            - `requirements.txt`: Python dependencies

            ## Test Types
            - Type 0: File existence checks
            - Type 1: Output comparison tests
            - Type 2: Function signature validation

            ## Questions
            """
        
        for i, question in enumerate(self.config.questions, 1):
            readme_content += f"\n### {i}. {question.name}\n"
            for j, item in enumerate(question.marking_items, 1):
                readme_content += f"- Item {j}: {item.type} ({item.total_mark} points)\n"
        
        readme_file = self.temp_dir / "README.md"
        with open(readme_file, 'w', encoding='utf-8') as f:
            f.write(readme_content)
    
    def _create_zip(self, zip_path: Path):
        """Create the autograder.zip file with proper structure."""
        assert self.temp_dir is not None, "temp_dir must be set before creating zip"
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in self.temp_dir.rglob('*'):
                if file_path.is_file():
                    arcname = file_path.relative_to(self.temp_dir)
                    zipf.write(file_path, arcname)