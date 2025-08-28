# autograder-gen

Tool for supporting lecturers on creating automatic assessment of students programs submitted to the [GradeScope Platform](https://www.gradescope.com/).
It generates Gradescope-compatible Autograder scripts in a zip file for a JSON configuration file. It validates your config, renders test scripts using Jinja2 templates, and packages everything for upload to Gradescope. It follow a template-based approach based in the [reference GradeScope Autograder scripts samples](https://gradescope-autograders.readthedocs.io/).

The project has command-line and a web version (see more at [web/README.md]).

## command-line

1. **Create and activate a virtual environment (recommended):**

```bash
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate
pip install -r cli/requirements.txt
```

Run the CLI from the project root:

```sh
python autograder_gen/cli.py --config <path/to/config.json> [--output <output_dir>] [--verbose] [--validate-only]
```

Arguments:

- `--config`, `-c` (required): Path to your JSON configuration file.
- `--output`, `-o`: Output directory for the generated `autograder.zip` (default: `./output`).
- `--verbose`, `-v`: Enable verbose logging.
- `--validate-only`: Only validate the configuration file, do not generate the autograder.

Example:

```sh
python autograder_gen/cli.py --config examples/py_simple/config.json
```

This will:

- Validate the config file
- Generate all necessary autograder scripts and files
- Zip file as `autograder.zip` in `./output`

### Main Authors

- **Alan Guedes** – [@alanlivio](https://github.com/alanlivio)  
- **Giorgio Werberich Scur** – [@giorgioscur](https://github.com/giorgioscur)

### License

Contributions from others are welcome and will be credited.  
This project is licensed under the [MIT License](LICENSE).  
The University of Reading retains rights of original contributions.  
