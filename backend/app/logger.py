from loguru import logger
from .config import LOG_FILE

# Remove default logger
logger.remove()

# Add file logger
logger.add(
    LOG_FILE,
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    rotation="5 MB",
    enqueue=True
)

# Add console logger (helpful during dev)
logger.add(
    lambda msg: print(msg, end=""),
    level="INFO",
    format="{time:HH:mm:ss} | {level} | {message}"
)

__all__ = ["logger"]
