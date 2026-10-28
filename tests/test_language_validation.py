import pytest
from pydantic import ValidationError
from autograder_gen.version import __version__
import autograder_gen as ag


def test_language_validation():

    # Valid languages
    ag.Config.model_validate(
        {
            "version": __version__,
            "language": "python",
            "files_necessary": ["t.py"],
            "questions": [
                {
                    "name": "Q1",
                    "marking_items": [
                        {"target_file": "t.py", "total_mark": 1, "type": "program_output_test"}
                    ],
                }
            ],
        }
    )
    ag.Config.model_validate(
        {
            "version": __version__,
            "language": "java",
            "files_necessary": ["t.py"],
            "questions": [
                {
                    "name": "Q1",
                    "marking_items": [
                        {"target_file": "t.py", "total_mark": 1, "type": "program_output_test"}
                    ],
                }
            ],
        }
    )

    # Invalid language
    with pytest.raises(ValidationError) as excinfo:
        ag.Config.model_validate(
            {
                "version": __version__,
                "language": "r",
                "files_necessary": ["t.py"],
                "questions": [
                    {
                        "name": "Q1",
                        "marking_items": [
                            {
                                "target_file": "t.py",
                                "total_mark": 1,
                                "type": "program_output_test",
                            }
                        ],
                    }
                ],
            }
        )
    assert "language" in str(excinfo.value)


if __name__ == "__main__":
    test_language_validation()
    print("Language validation test passed!")
