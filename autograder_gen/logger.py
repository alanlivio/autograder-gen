import logging
import sys


def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO

    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    existing = [h for h in root_logger.handlers if getattr(h, "_autograder_gen_handler", False)]
    if existing:
        for handler in existing:
            handler.setLevel(level)
    else:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        console_handler._autograder_gen_handler = True
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
