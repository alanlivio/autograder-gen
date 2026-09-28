"""
Batch runner for AutograderGen configurations (legacy alias for autograder_gen.batch).
"""

import sys
from autograder_gen.batch import find_configs, main as batch_main


def main():
    if "--run-stub-submissions" not in sys.argv:
        sys.argv.insert(1, "--run-stub-submissions")
    batch_main()


if __name__ == "__main__":
    main()
