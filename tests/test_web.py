import yaml
import pytest
import autograder_gen as ag
from autograder_gen.web.app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_index_route(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"What is AutograderGen?" in response.data


def test_docs_route(client):
    response = client.get("/docs")
    assert response.status_code == 200
    assert b"Configuration Schema Explorer" in response.data


def test_generate_route(client):
    response = client.get("/generate")
    assert response.status_code == 200
    assert b"AutograderGen" in response.data


def test_api_validate_missing_data(client):
    response = client.post("/api/validate", json={})
    assert response.status_code == 400
    assert b"No config data provided" in response.data


def test_api_export_bundle_missing_data(client):
    response = client.post("/api/export/bundle", json={})
    assert response.status_code == 400
    assert b"No config data provided" in response.data


@pytest.mark.parametrize(
    "template_name", ["py_simple", "py_function", "py_complete", "java_simple"]
)
def test_web_app_import_and_export_all_templates(client, template_name):
    # 1. Fetch template via web API example endpoint (launch/import at start)
    example_resp = client.get(f"/api/example/{template_name}")
    assert example_resp.status_code == 200
    example_data = example_resp.get_json()
    assert example_data["success"] is True
    config_dict = example_data["config"]

    # 2. Validate configuration
    val_resp = client.post("/api/validate", json=config_dict)
    assert val_resp.status_code == 200
    assert val_resp.get_json()["valid"] is True

    # 3. Export bundle zip
    export_resp = client.post("/api/export/bundle", json=config_dict)
    assert export_resp.status_code == 200
    assert export_resp.headers["Content-Type"] == "application/zip"
    assert export_resp.data.startswith(b"PK\x03\x04")


def test_generate_page_contains_new_fields(client):
    response = client.get("/generate")
    assert response.status_code == 200
    assert b"retrieve_student_id" in response.data
    assert b"wrong_file_location_deduction" in response.data
    assert b'id="wrong_file_location_deduction"' in response.data
    assert b"q-wrong-file-location-deduction-input" not in response.data
    assert b"manual_review" in response.data
    assert b"strict_file_location" in response.data
    assert b"remove_use_of_java_package" in response.data


def test_web_validate_and_export_with_retrieve_student_id(client):
    config = {
        "version": "1.0",
        "language": "python",
        "retrieve_student_id": True,
        "required_files": ["solution.py"],
        "questions": [
            {
                "name": "Q1",
                "marking_items": [
                    {
                        "name": "Check",
                        "target_file": "solution.py",
                        "total_mark": 10.0,
                        "type": "output_comparison",
                        "expected_output": "hello",
                    }
                ],
            }
        ],
    }
    val_resp = client.post("/api/validate", json=config)
    assert val_resp.status_code == 200
    assert val_resp.get_json()["valid"] is True

    export_resp = client.post("/api/export/bundle", json=config)
    assert export_resp.status_code == 200
    assert export_resp.headers["Content-Type"] == "application/zip"
    assert export_resp.data.startswith(b"PK\x03\x04")


def test_web_validate_and_export_with_wrong_file_location_deduction(client):
    config = {
        "version": "1.0",
        "language": "python",
        "wrong_file_location_deduction": 0.5,
        "required_files": ["solution.py"],
        "questions": [
            {
                "name": "Q1",
                "marking_items": [
                    {
                        "name": "Check",
                        "target_file": "solution.py",
                        "total_mark": 10.0,
                        "type": "output_comparison",
                        "expected_output": "hello",
                    }
                ],
            }
        ],
    }
    val_resp = client.post("/api/validate", json=config)
    assert val_resp.status_code == 200
    assert val_resp.get_json()["valid"] is True

    export_resp = client.post("/api/export/bundle", json=config)
    assert export_resp.status_code == 200
    assert export_resp.headers["Content-Type"] == "application/zip"
    assert export_resp.data.startswith(b"PK\x03\x04")


def test_web_validate_and_export_with_manual_review(client):
    config = {
        "version": "1.0",
        "language": "python",
        "required_files": ["report.pdf"],
        "questions": [
            {
                "name": "Report",
                "marking_items": [
                    {
                        "name": "Manual PDF Review",
                        "target_file": "report.pdf",
                        "total_mark": 20.0,
                        "type": "manual_review",
                    },
                    {
                        "name": "Oral Presentation",
                        "total_mark": 10.0,
                        "type": "manual_review",
                    },
                ],
            }
        ],
    }
    val_resp = client.post("/api/validate", json=config)
    assert val_resp.status_code == 200
    assert val_resp.get_json()["valid"] is True

    export_resp = client.post("/api/export/bundle", json=config)
    assert export_resp.status_code == 200
    assert export_resp.headers["Content-Type"] == "application/zip"
    assert export_resp.data.startswith(b"PK\x03\x04")


def test_upload_config_with_new_fields(client):
    import io

    yaml_content = """version: '1.0'
language: python
retrieve_student_id: true
wrong_file_location_deduction: 0.5
required_files:
  - doc.pdf
questions:
  - name: Q1
    marking_items:
      - name: Review
        type: manual_review
        target_file: doc.pdf
        total_mark: 15.0
"""
    data = {"config_file": (io.BytesIO(yaml_content.encode("utf-8")), "config.yaml")}
    resp = client.post("/upload-config", data=data, content_type="multipart/form-data")
    assert resp.status_code == 200
    res_json = resp.get_json()
    assert res_json["success"] is True
    assert res_json["config"]["retrieve_student_id"] is True
    assert res_json["config"]["wrong_file_location_deduction"] == 0.5


def test_web_validate_and_export_with_strict_file_location(client):
    config = {
        "version": "1.0",
        "language": "python",
        "strict_file_location": True,
        "required_files": ["solution.py"],
        "questions": [
            {
                "name": "Q1",
                "marking_items": [
                    {
                        "name": "Check",
                        "target_file": "solution.py",
                        "total_mark": 10.0,
                        "type": "output_comparison",
                        "expected_output": "hello",
                    }
                ],
            }
        ],
    }
    val_resp = client.post("/api/validate", json=config)
    assert val_resp.status_code == 200
    assert val_resp.get_json()["valid"] is True

    export_resp = client.post("/api/export/bundle", json=config)
    assert export_resp.status_code == 200
    assert export_resp.headers["Content-Type"] == "application/zip"
    assert export_resp.data.startswith(b"PK\x03\x04")


def test_web_validate_and_export_with_remove_use_of_java_package(client):
    config = {
        "version": "1.0",
        "language": "java",
        "remove_use_of_java_package": True,
        "required_files": ["Solution.java"],
        "questions": [
            {
                "name": "Q1",
                "marking_items": [
                    {
                        "name": "Check",
                        "target_file": "Solution.java",
                        "total_mark": 10.0,
                        "type": "output_comparison",
                        "expected_output": "hello",
                    }
                ],
            }
        ],
    }
    val_resp = client.post("/api/validate", json=config)
    assert val_resp.status_code == 200
    assert val_resp.get_json()["valid"] is True

    export_resp = client.post("/api/export/bundle", json=config)
    assert export_resp.status_code == 200
    assert export_resp.headers["Content-Type"] == "application/zip"
    assert export_resp.data.startswith(b"PK\x03\x04")


def test_web_validate_rejects_strict_file_location_with_deduction(client):
    config = {
        "version": "1.0",
        "language": "python",
        "strict_file_location": True,
        "wrong_file_location_deduction": 0.5,
        "required_files": ["solution.py"],
        "questions": [
            {
                "name": "Q1",
                "marking_items": [
                    {
                        "name": "Check",
                        "target_file": "solution.py",
                        "total_mark": 10.0,
                        "type": "output_comparison",
                        "expected_output": "hello",
                    }
                ],
            }
        ],
    }
    val_resp = client.post("/api/validate", json=config)
    assert val_resp.status_code == 200
    data = val_resp.get_json()
    assert data["valid"] is False
    assert any(
        "wrong_file_location_deduction is only supported when strict_file_location is False" in err
        for err in data["errors"]
    )


def test_upload_config_with_strict_file_location_and_java_package(client):
    import io

    yaml_content = """version: '1.0'
language: java
strict_file_location: true
remove_use_of_java_package: true
required_files:
  - Solution.java
questions:
  - name: Q1
    marking_items:
      - name: Review
        type: manual_review
        target_file: Solution.java
        total_mark: 15.0
"""
    data = {"config_file": (io.BytesIO(yaml_content.encode("utf-8")), "config.yaml")}
    resp = client.post("/upload-config", data=data, content_type="multipart/form-data")
    assert resp.status_code == 200
    res_json = resp.get_json()
    assert res_json["success"] is True
    assert res_json["config"]["strict_file_location"] is True
    assert res_json["config"]["remove_use_of_java_package"] is True


def test_web_validate_rejects_out_of_bounds_deduction(client):
    config = {
        "version": "1.0",
        "language": "python",
        "wrong_file_location_deduction": 1.5,
        "required_files": ["solution.py"],
        "questions": [
            {
                "name": "Q1",
                "marking_items": [
                    {
                        "name": "Check",
                        "target_file": "solution.py",
                        "total_mark": 10.0,
                        "type": "output_comparison",
                        "expected_output": "hello",
                    }
                ],
            }
        ],
    }
    val_resp = client.post("/api/validate", json=config)
    assert val_resp.status_code == 200
    data = val_resp.get_json()
    assert data["valid"] is False
    assert any(
        "wrong_file_location_deduction must be between 0.0 and 1.0" in err for err in data["errors"]
    )
