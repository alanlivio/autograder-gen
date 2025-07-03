# TIF Autograder CLI Tool

This command-line tool generates Gradescope-compatible autograder zip files from a JSON configuration file. It validates your config, renders test scripts using Jinja2 templates, and packages everything for upload to Gradescope.

## Installation

1. **Create and activate a virtual environment (recommended):**
   ```sh
   python -m venv .venv
   # On Windows:
   .venv\Scripts\activate
   # On macOS/Linux:
   source .venv/bin/activate
   ```
2. **Install dependencies:**
   ```sh
   pip install -r cli/requirements.txt
   ```

## Usage

Run the CLI from the project root:

```sh
python cli/src/main.py --config <path/to/config.json> [--output <output_dir>] [--verbose] [--validate-only]
```

### Arguments
- `--config`, `-c` (required): Path to your JSON configuration file.
- `--output`, `-o`: Output directory for the generated `autograder.zip` (default: `./output`).
- `--verbose`, `-v`: Enable verbose logging.
- `--validate-only`: Only validate the configuration file, do not generate the autograder.

### Example

```sh
python cli/src/main.py --config cli/config/sample_config.json --output ./my_autograder
```

This will:
- Validate the config file
- Generate all necessary autograder scripts and files
- Create `autograder.zip` in `./my_autograder`

## Development & Testing

- To run all tests:
  ```sh
  .venv\Scripts\python -m pytest tests
  ```
- To test the CLI end-to-end:
  ```sh
  .venv\Scripts\python -m pytest tests/test_cli_functionality.py
  ```

## Requirements
- Python 3.8+
- See `cli/requirements.txt` for dependencies

## License
MIT 