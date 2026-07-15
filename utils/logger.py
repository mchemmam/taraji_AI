"""
Logging configuration for Taraji AI
"""
import sys
from pathlib import Path
from loguru import logger

from config import settings


def setup_logger():
    """Configure loguru logger"""

    # Remove default handler
    logger.remove()

    # Ensure logs directory exists
    settings.LOGS_DIR.mkdir(parents=True, exist_ok=True)

    # Console handler (INFO and above)
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        level=settings.LOG_LEVEL,
        colorize=True,
    )

    # File handler - all logs
    logger.add(
        settings.LOG_FILE,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG",
        rotation="10 MB",
        retention="30 days",
        compression="zip",
    )

    # File handler - errors only
    logger.add(
        settings.ERROR_LOG_FILE,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="ERROR",
        rotation="10 MB",
        retention="90 days",
        compression="zip",
    )

    return logger


# Initialize logger
log = setup_logger()
