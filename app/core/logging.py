import sys

from loguru import logger


def setup_logging():
    logger.remove()

    # Log no console
    logger.add(
        sys.stdout,
        level="INFO",
        serialize=False,
        backtrace=False,
        diagnose=False,
        enqueue=True,
    )

    # Log em arquivo rotacionado
    logger.add(
        "logs/app.log",
        level="INFO",
        rotation="10 MB",
        retention="7 days",
        compression="zip",
        enqueue=True,
        serialize=True,
    )

    return logger
