import logging
import sys


def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO

    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(console_handler)

    root_logger.propagate = False


def print_success(message: str):
    print(f"[OK] {message}")


def print_error(message: str):
    print(f"[ERROR] {message}", file=sys.stderr)


def print_warning(message: str):
    print(f"[WARNING] {message}")


def print_info(message: str):
    print(f"[INFO] {message}")
