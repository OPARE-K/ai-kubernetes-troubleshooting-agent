import sys

from loguru import logger


def setup_logging() -> None:
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time} | {level} | {message}")
