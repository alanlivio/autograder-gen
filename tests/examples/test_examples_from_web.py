import pytest
import os
import json
import yaml
from pathlib import Path

from autograder_gen.web.app import app


def get_examples_dir():
    return Path(__file__).resolve().parent


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def load_example(example_name):
    dir_path = get_examples_dir() / example_name
    file_path = dir_path / "config.yaml"
    if file_path.exists():
        with open(file_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return None


@pytest.mark.parametrize("example_name", ["py_complete", "py_function", "py_simple", "java_simple"])
def test_web_api_validate_examples(client, example_name):
    config_data = load_example(example_name)
    if not config_data:
        pytest.skip(f"No yaml config for {example_name}")

    response = client.post("/api/validate", json=config_data)
    assert response.status_code == 200

    data = response.get_json()
    assert data["valid"] is True, f"Validation failed for {example_name}: {data.get('errors')}"


@pytest.mark.parametrize("example_name", ["py_complete", "py_function", "py_simple", "java_simple"])
def test_web_export_bundle_examples(client, example_name):
    config_data = load_example(example_name)
    if not config_data:
        pytest.skip(f"No yaml config for {example_name}")

    response = client.post("/api/export/bundle", json=config_data)
    assert response.status_code == 200
    assert response.mimetype == "application/zip"
    assert response.data.startswith(b"PK\x03\x04")
